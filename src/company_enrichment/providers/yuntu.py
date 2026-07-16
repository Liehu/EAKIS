"""云图 (YunTu) 企业主体关联信息采集 Provider。

对接云图服务的 4 个 API（请求包见 docs/1.添加企业名称）：
- POST   /api/v1/seed/enterprise/batch-create  录入企业种子（按名称）
- GET    /api/v1/seed/enterprise               列出种子（取 id；采集后取全量子公司）
- POST   /api/v1/seed/enterprise/{id}/load     触发分子公司采集（异步，返回 affected 数）
- DELETE /api/v1/seed/enterprise/batch-delete  采集后清理云图侧种子

真实采集流程（经联调验证）：
  1. batch-create 录入种子 → GET list?name=X 取 seed_id
  2. POST {seed_id}/load 触发异步采集（响应仅 {"affected":N}，不含子公司数据）
  3. 等待采集完成 → GET list（分页全量）客户端按 investment_path 过滤
  4. investment_path 字段编码母→子关联，格式形如：
       "路径1（投资占比100.00%）\\n腾讯科技（深圳）有限公司——>（100.00%）广州腾讯科技有限公司"
     解析末行 "——>（X%）子公司名" 得到子公司名 + 持股比例
  5. DELETE 清理本次种子 + 子公司（避免污染共享 workspace）

认证：Cookie: session=xxx + Workspace 头。session 过期改 settings.yuntu_session 重启。
TLS：自建服务自签证书，verify=False（可由 settings.yuntu_verify_tls 控制）。

未配置 session（或 yuntu_use_stubs=True）时走 _stub_enrich 返回模拟数据，便于开发联调。
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime

import httpx

from src.company_enrichment.base import CompanyEnrichmentProvider
from src.company_enrichment.models import (
    EnrichmentResult,
    NormalizedCompany,
    NormalizedRelation,
)
from src.core.settings import get_settings
from src.shared.circuit_breaker import CircuitBreaker
from src.shared.exceptions import CompanyEnrichmentError
from src.shared.logger import get_logger

logger = get_logger("yuntu_provider")

# 云图响应 code 字段成功值
_OK_CODE = 200
# 采集后等待云图异步落库的时间（秒）
_COLLECT_WAIT_SECONDS = 3.0
# 解析 investment_path 中的 "——>（X%）公司名" 片段
_SEG_RE = re.compile(r"——>\s*（([\d.]+)%）\s*(.+?)(?=——>|$)")
# 路径行前缀 "路径N（投资占比X%）"
_PATH_HEADER_RE = re.compile(r"^路径\d+（投资占比[\d.]+%）$")


class YunTuProvider(CompanyEnrichmentProvider):
    """云图商业 API 采集 Provider。"""

    name = "yuntu"

    def __init__(self) -> None:
        s = get_settings()
        self._base_url = s.yuntu_base_url.rstrip("/")
        self._session = s.yuntu_session
        self._workspace = s.yuntu_workspace_id
        self._verify_tls = s.yuntu_verify_tls
        self._timeout = s.yuntu_request_timeout
        self._use_stubs = s.yuntu_use_stubs or not self._session
        self._breaker = CircuitBreaker(failure_threshold=4, recovery_timeout=30.0)

    # ── 公开入口 ───────────────────────────────────────────
    async def enrich(
        self,
        company_name: str,
        *,
        depth: int = 3,
        holding_min: float = 50.0,
    ) -> EnrichmentResult:
        if self._use_stubs:
            logger.info("yuntu stub 模式：返回模拟关联企业 (company=%s)", company_name)
            return self._stub_enrich(company_name, depth=depth, holding_min=holding_min)

        return await self._real_enrich(company_name, depth=depth, holding_min=holding_min)

    # ── 真实采集流程 ───────────────────────────────────────
    async def _real_enrich(self, company_name: str, *, depth: int, holding_min: float) -> EnrichmentResult:
        fetched_at = datetime.now(UTC)
        try:
            # 1. 录入种子
            await self._post_with_retry(
                "/api/v1/seed/enterprise/batch-create",
                json={"confidence": "100", "level": 1, "name": [company_name]},
            )
            # 2. 取种子 id
            seed = await self._find_seed_by_name(company_name)
            if seed is None:
                raise CompanyEnrichmentError(f"云图未返回种子企业: {company_name}")
            seed_id = seed["id"]
            # 3. 触发分子公司采集（异步，响应仅返回 affected 数）
            load_resp = await self._post_with_retry(
                f"/api/v1/seed/enterprise/{seed_id}/load",
                json={
                    "level": depth,
                    "equity": int(holding_min),
                    "enable": True,
                    "confidence": "100",
                },
            )
            affected = (load_resp or {}).get("affected", 0)
            logger.info("云图 load 触发采集: seed=%s affected=%d", seed_id, affected)
            # 4. 等待异步落库
            await asyncio.sleep(_COLLECT_WAIT_SECONDS)
            # 5. 取全量种子（分页），解析所有母→子关系（含多级）
            all_items = await self._list_all_seeds()
            raw_rels = self._parse_relations(all_items, company_name)
            # 构建 name -> status 映射（云图条目的存续状态）
            name_status: dict[str, str | None] = {}
            for it in all_items:
                nm = it.get("name")
                if nm:
                    name_status[nm] = it.get("status")
            # 清理云图侧所有相关种子
            related_ids = [it["id"] for it in all_items if company_name in (it.get("investment_path", "") or "")]
            try:
                await self._delete_with_retry(
                    "/api/v1/seed/enterprise/batch-delete",
                    json={"pk": [seed_id, *related_ids]},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("云图种子清理失败（忽略）: %s", exc)
        except CompanyEnrichmentError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("云图采集异常: %s", exc)
            raise CompanyEnrichmentError(f"云图采集失败: {exc}") from exc

        # 归一化：raw_rels 含 root→子、子→孙 等多级关系
        root = self._normalize(seed, provider=self.name)
        relations: list[NormalizedRelation] = []
        for r in raw_rels:
            child_name = r["child"]
            ratio = r["ratio"]
            child = NormalizedCompany(
                name=child_name,
                business_status=name_status.get(child_name),
                provider=self.name,
            )
            rtype = "holding" if (ratio is not None and ratio >= holding_min) else "minority_stake"
            relations.append(
                NormalizedRelation(
                    parent_name=r["parent"],
                    child=child,
                    relation_type=rtype,
                    holding_ratio=ratio,
                    provider=self.name,
                )
            )
        logger.info(
            "云图采集到 %d 条母→子关系（含多级）(company=%s)",
            len(relations), company_name,
        )
        return EnrichmentResult(
            root=root,
            relations=relations,
            provider=self.name,
            fetched_at=fetched_at,
            external_root_id=str(seed_id),
        )

    # ── 子公司提取：解析 investment_path 多级路径 ─────────
    @staticmethod
    def _parse_relations(items: list[dict], root_name: str) -> list[dict]:
        """从全量 seeds 解析所有母→子关系（含多级：子公司、孙公司）。

        investment_path 每行形如（以 root 开头）：
          "路径1（投资占比X%）"  ← 头部
          "阿里巴巴——>（100.00%）杭州瀚云——>（98.04%）杭州灏云"  ← 链路

        返回去重后的关系列表，每项 {parent, child, ratio}。
        root→子公司、子公司→孙公司 都会被提取。
        """
        relations: dict[tuple[str, str], dict] = {}  # (parent, child) -> {parent, child, ratio}
        for item in items:
            ip = item.get("investment_path", "") or ""
            if root_name not in ip:
                continue
            for line in ip.split("\n"):
                line = line.strip()
                if not line or _PATH_HEADER_RE.match(line):
                    continue
                # line 形如: root——>（X%）A——>（Y%）B——>（Z%）C
                # 拆成链: [root, A, B, C] 配 ratios [X, Y, Z]
                # 先用 _SEG_RE 找所有 "——>（%）名" 片段
                # 起点是 line 开头到第一个 ——> 之前的公司名
                if "——>" not in line:
                    continue
                # 从行首提取 root 公司名（——> 之前的部分）
                first_split = line.split("——>", 1)
                current = root_name  # 链的起点固定是 root（investment_path 以 root 开头）
                # 逐段解析
                remaining = line
                while "——>" in remaining:
                    m = _SEG_RE.search(remaining)
                    if not m:
                        break
                    ratio = float(m.group(1))
                    child_name = m.group(2).strip()
                    # 去掉 child_name 末尾可能残留的后续 ——>
                    if "——>" in child_name:
                        child_name = child_name.split("——>")[0].strip()
                    key = (current, child_name)
                    if key not in relations:
                        relations[key] = {"parent": current, "child": child_name, "ratio": ratio}
                    current = child_name
                    # 推进 remaining 到这段之后
                    remaining = remaining[m.end():]
                    # 如果 remaining 不以 ——> 开头，说明链结束
                    break_remaining = remaining.lstrip()
                    if not break_remaining.startswith("——>"):
                        break
                # 处理行内多段（用 _SEG_RE findall 整行）
            # 上面逐段逻辑可能漏，用整行 findall 兜底
            for line in ip.split("\n"):
                line = line.strip()
                if not line or _PATH_HEADER_RE.match(line) or "——>" not in line:
                    continue
                parts = line.split("——>")
                chain_names = []
                chain_ratios = []
                # 第一段是 root 名
                chain_names.append(root_name)
                for seg in parts[1:]:
                    m = re.search(r"（([\d.]+)%）\s*(.+)", seg)
                    if m:
                        chain_ratios.append(float(m.group(1)))
                        chain_names.append(m.group(2).strip())
                for i in range(len(chain_names) - 1):
                    key = (chain_names[i], chain_names[i + 1])
                    if key not in relations:
                        relations[key] = {
                            "parent": chain_names[i],
                            "child": chain_names[i + 1],
                            "ratio": chain_ratios[i] if i < len(chain_ratios) else None,
                        }
        return list(relations.values())

    # ── 云图字段 → 归一化 ─────────────────────────────────
    @staticmethod
    def _normalize(item: dict, *, provider: str) -> NormalizedCompany:
        """云图条目 → NormalizedCompany。

        云图返回字段：name / equity / level / status(存续/开业/注销) /
        equity_string / level_string / investment_path / created_at 等。
        云图不提供的工商字段（法人/信用代码/邮箱/工号等）留空。
        """
        return NormalizedCompany(
            name=item.get("name", "") or "",
            business_status=item.get("status"),
            provider=provider,
            raw={k: v for k, v in item.items() if not k.startswith("_")},
        )

    # ── HTTP 封装 ──────────────────────────────────────────
    def _client(self) -> httpx.AsyncClient:
        headers = {
            "Workspace": self._workspace,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        cookies = {"session": self._session} if self._session else {}
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            cookies=cookies,
            timeout=httpx.Timeout(self._timeout, connect=10.0),
            verify=self._verify_tls,
        )

    async def _request(self, method: str, path: str, **kwargs: object) -> dict:
        async with self._client() as c:
            resp = await c.request(method, path, **kwargs)
            resp.raise_for_status()
            data = resp.json()
        if isinstance(data, dict) and data.get("code") != _OK_CODE:
            raise CompanyEnrichmentError(f"云图返回非 200 code: {data.get('message') or data}")
        return (data or {}).get("data", {}) if isinstance(data, dict) else {}

    async def _post_with_retry(self, path: str, *, json: dict) -> dict:
        return await self._breaker.call(self._request, "POST", path, json=json)

    async def _delete_with_retry(self, path: str, *, json: dict) -> dict:
        # httpx 的 delete() 不接受 json 参数，统一走 request("DELETE", ...)。
        return await self._breaker.call(self._request, "DELETE", path, json=json)

    async def _find_seed_by_name(self, name: str) -> dict | None:
        """列出种子，按名称匹配返回条目（含 id）。"""
        data = await self._breaker.call(
            self._request, "GET", "/api/v1/seed/enterprise",
            params={"name": name, "page": 1, "size": 20, "sort": "level"},
        )
        items = (data or {}).get("items", []) if isinstance(data, dict) else []
        for it in items:
            if it.get("name") == name:
                return it
        return items[0] if items else None

    async def _list_all_seeds(self, page_size: int = 100) -> list[dict]:
        """分页拉取 workspace 全量种子（load 后含子公司）。"""
        all_items: list[dict] = []
        page = 1
        while True:
            data = await self._breaker.call(
                self._request, "GET", "/api/v1/seed/enterprise",
                params={"page": page, "size": page_size, "sort": "level"},
            )
            items = (data or {}).get("items", []) if isinstance(data, dict) else []
            total = (data or {}).get("total", 0) if isinstance(data, dict) else 0
            all_items.extend(items)
            if not items or len(all_items) >= total:
                break
            page += 1
            if page > 50:  # 安全上限
                break
        return all_items

    # ── Stub 模式（开发联调）──────────────────────────────
    @staticmethod
    def _stub_enrich(company_name: str, *, depth: int, holding_min: float) -> EnrichmentResult:
        now = datetime.now(UTC)
        root = NormalizedCompany(name=company_name, business_status="存续", provider="yuntu")
        sample_subs = [
            ("科技股份有限公司", 100.0, "开业"),
            ("信息技术有限公司", 67.5, "存续"),
            ("数据服务分公司", None, "存续"),
        ]
        relations: list[NormalizedRelation] = []
        for suffix, ratio, status in sample_subs:
            short = company_name[: company_name.find("有限公司")] if "有限公司" in company_name else company_name
            child = NormalizedCompany(name=f"{short}{suffix}", business_status=status, provider="yuntu")
            rtype = "branch" if ratio is None else ("holding" if ratio >= holding_min else "minority_stake")
            relations.append(
                NormalizedRelation(
                    parent_name=company_name,
                    child=child,
                    relation_type=rtype,
                    holding_ratio=ratio,
                    provider="yuntu",
                )
            )
        return EnrichmentResult(
            root=root, relations=relations[: max(1, depth)], provider="yuntu", fetched_at=now
        )
