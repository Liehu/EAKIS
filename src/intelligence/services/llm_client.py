import json
from typing import Any

from src.intelligence.services.base import BaseLLMClient


class StubLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        if "DSL" in prompt or "fofa" in prompt.lower() or "搜索语法" in prompt:
            import re

            domain_match = re.search(r"域名[：:]\s*([^\n]+)", prompt)
            domains = domain_match.group(1).split(", ") if domain_match else ["example.com"]
            primary_domain = domains[0].strip()

            keyword_match = re.search(r"关键词[：:]\s*([^\n]+)", prompt)
            keywords = keyword_match.group(1).split(", ") if keyword_match else ["目标"]
            primary_kw = keywords[0].strip()

            platforms = ["fofa", "hunter", "shodan"]
            for platform in ["fofa", "hunter", "shodan", "quake", "bing"]:
                if platform in prompt.lower():
                    if platform not in platforms:
                        platforms.append(platform)

            result = {}
            if "fofa" in prompt.lower():
                result["fofa"] = f'domain="{primary_domain}" && title="{primary_kw}"'
            if "hunter" in prompt.lower():
                result["hunter"] = f'domain.suffix="{primary_domain}" && web.title="{primary_kw}"'
            if "shodan" in prompt.lower():
                result["shodan"] = f'org:"{primary_kw}" http.title:"{primary_kw}"'
            if "quake" in prompt.lower():
                result["quake"] = f'app:"{primary_kw}"'

            return json.dumps(result, ensure_ascii=False)

        # keyword_extraction_v2 — 必须在数据源匹配之前，因为 v2 提示词含 "source_idx"
        if "关键词" in prompt and ("business_keywords" in prompt or "source_idx" in prompt or "网络安全情报" in prompt):
            import re as _re
            # 只从 "情报文本:" 之后的内容提取，避免匹配提示词本身
            text_marker = _re.search(r"情报文本[：:]\s*\n?", prompt)
            text_block = prompt[text_marker.end():] if text_marker else prompt
            company_match = _re.search(r"靶标企业[：:]\s*(.+)", prompt)
            company = company_match.group(1).strip() if company_match else ""

            biz_patterns = [
                (r"(?:打造|建设|构建|发布|推出|上线|部署)[^\n]{2,20}?(?:平台|系统|项目|服务|方案|网络)", 0),
                (r"(\S+(?:平台|系统|中心|基地|门户|中台|引擎))", 1),
                (r"(工业互联网|低空经济|数字化转型|网络安全|态势感知|数据中心|云数据|算力)", 1),
                (r"(5G\+?\S*|物联网|大数据|人工智能|区块链)", 1),
            ]
            biz_kw: list[dict] = []
            seen_biz: set[str] = set()
            for pat, group_idx in biz_patterns:
                for m in _re.finditer(pat, text_block):
                    w = m.group(group_idx).strip()
                    w = _re.sub(r"^[，。、\s]+|[，。、\s]+$", "", w)
                    if 2 <= len(w) <= 15 and w not in seen_biz and "公司" not in w and "技术" not in w:
                        seen_biz.add(w)
                        biz_kw.append({"word": w, "confidence": 0.90, "source_idx": 0})

            tech_patterns = [
                r"(Spring\s*Boot)", r"(Kubernetes|K8s)", r"(Docker)", r"(Nginx)",
                r"(Redis)", r"(PostgreSQL)", r"(MySQL)", r"(微服务)",
                r"(容器化)", r"(API)", r"(REST)", r"(gRPC)", r"(GraphQL)",
                r"(DevOps)", r"(CI/CD)", r"(Vue\.?js?)", r"(React)",
                r"(Java)", r"(Python)", r"(Go\b)", r"(Rust)",
                r"(SWIFT)", r"(5G)", r"(AI)", r"(IoT|物联网)",
            ]
            tech_kw: list[dict] = []
            seen_tech: set[str] = set()
            for pat in tech_patterns:
                for m in _re.finditer(pat, text_block, _re.IGNORECASE):
                    w = m.group(1)
                    wl = w.lower()
                    if wl not in seen_tech:
                        seen_tech.add(wl)
                        tech_kw.append({"word": w, "confidence": 0.92, "source_idx": 0})

            entity_patterns = [
                r"([一-鿿]{2,6}(?:有限公司|集团|公司|网络|科技|技术|信息|通信))",
                r"(华为(?:技术|有限公司)?)", r"(阿里(?:云|巴巴)?)", r"(腾讯)",
                r"(中国联通|中国移动|中国电信|福建省分公司)",
                r"(中兴通讯(?:股份)?有限公司?)",
                r"(国际清算组织)",
            ]
            entity_kw: list[dict] = []
            seen_ent: set[str] = set()
            for pat in entity_patterns:
                for m in _re.finditer(pat, text_block):
                    w = m.group(1)
                    if w not in seen_ent and 2 <= len(w) <= 15:
                        seen_ent.add(w)
                        entity_kw.append({"word": w, "confidence": 0.88, "source_idx": 0})

            if company and company not in seen_ent:
                entity_kw.insert(0, {"word": company, "confidence": 0.99, "source_idx": 0})

            for kw_list in [biz_kw, tech_kw, entity_kw]:
                kw_list.sort(key=lambda x: x["confidence"], reverse=True)
                del kw_list[20:]

            return json.dumps({
                "business_keywords": biz_kw[:20],
                "tech_keywords": tech_kw[:20],
                "entity_keywords": entity_kw[:20],
            }, ensure_ascii=False)

        if "数据源" in prompt or ("source" in prompt.lower() and "数据源推荐" in prompt):
            return json.dumps({
                "recommended_sources": ["news", "official", "legal", "asset_engine"],
                "reasoning": "基于目标企业规模和行业特征推荐全类别数据源",
            })

        if "情报分析员" in prompt and "关键信息" in prompt:
            import re as _re
            tech_found = _re.findall(
                r"(Spring\s*Boot|Docker|Kubernetes|K8s|Nginx|Redis|MySQL|PostgreSQL"
                r"|React|Vue|Python|Java|Go|Rust|微服务|API|REST|GraphQL|gRPC"
                r"|5G|AI|大数据|容器化|DevOps|CI/CD)",
                prompt,
            )
            org_found = _re.findall(r"([一-鿿]{2,10}(?:科技|技术|有限公司|集团|公司|网络|信息))", prompt)
            return json.dumps({
                "business_info": "基于模拟摘要的业务描述",
                "tech_mentions": list(dict.fromkeys(tech_found))[:10],
                "entity_mentions": list(dict.fromkeys(org_found))[:5],
                "product_mentions": [],
            }, ensure_ascii=False)

        return f"LLM模拟响应：已处理请求"
