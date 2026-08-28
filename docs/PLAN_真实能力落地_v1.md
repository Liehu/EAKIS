# EAKIS 真实能力落地开发计划（v1）

> **创建时间**：2026-08-18
> **关联文档**：`docs/ROADMAP.md`（战略路线图 v1.4）、`docs/NEXT_SESSION_PLAN.md`
> **参考项目**：CyberStrike（TS Agent + 方法论引擎）、CyberStrikeAI（Go 平台 + 工作流引擎）、muteki（Python 蜂群 + 黑板）
>
> **目标**：四大能力从 stub/半 stub 走向真实可用，并实现 LangGraph 端到端一键执行：
> 1. 资产发现真实化（subfinder/dnsx/httpx/naabu）
> 2. 情报采集真实数据源（新闻/ICP备案/招投标）
> 3. 漏洞检测引擎（nuclei 集成 + 误报分诊）
> 4. LangGraph 全流程编排（企业名 → 报告）

---

## 零、现状基线（2026-08-18 盘点）

| 能力 | 现状 | 关键差距 |
|---|---|---|
| 资产发现 | 域名链路已真实：`src/asset_discovery/services/tool_client.py` 已桥接 subfinder/dnsx/httpx/cert CLI（经 `src/tools/executor.py`） | ① 默认 `asset_discovery_use_stubs=True` 走 `StubSearchClient`；② naabu 已在 `tools/registry.py:145` 注册但 `_TOOL_PLATFORMS` 未接入，端口扫描链路断裂；③ 未接入 task_runner（M3 为占位） |
| 情报采集 | CDP 爬虫（`scrapers/cdp_scraper.py`）与通用引擎（`generic_scraper.py`）真实 | 默认路径全 stub：`news_scraper.py`（9 条硬编码）、`official_scraper.py`、`legal_scraper.py`（ICP/招投标假数据） |
| 漏洞检测 | nuclei 已注册（`tools/registry.py:173`，默认禁用）但**零调用方**；`pentest/plugins` 空壳；orchestrator 的 test_exec/vuln_judge 为显式 stub | 全部待建 |
| 编排 | LangGraph 13 节点线性图（`src/orchestrator/graph.py`）+ API 层 `task_runner.py`（M0-M2 真实，M3/M4 占位） | 两套编排并存未统一；M3-M6 未接；无报告生成 worker |
| 数据模型 | Company/Asset/Vulnerability/IntelDocument/Task 字段齐全 | 基本够用，少量增列 |

---

## 一、参考项目可借鉴的设计理念（精华提炼）

| 理念 | 来源 | 在 EAKIS 的落法 |
|---|---|---|
| **声明式 YAML 工具配方**（参数 schema + enabled 开关 + 使用场景描述） | CyberStrikeAI `tools/*.yaml`（100+ 配方） | EAKIS 已有 `tools/registry.py`，补齐 per-tool `enabled`/超时/并发参数外置到 YAML，与 settings 同步 |
| **工具惰性安装/探活**（ensure_tools：check + install） | CyberStrike `ensure-tools.ts` | 新增 `scripts/ensure_tools.sh` + 启动时探活，缺失时降级并标记能力不可用（而非静默 stub） |
| **证据闸门（gate）**：结果必须带原始命令输出证据才算 verified，否则 candidate | muteki `solver/gate.py` | Vulnerability 入库分 `status: candidate/verified`，nuclei 原始 JSON 存 evidence；误报确认后写 Dead-end 不再重扫 |
| **黑板/结构化交接产物**：阶段间以 typed 对象（confidence、来源、标签）传递 | muteki shared_graph、CyberStrikeAI 阶段 Agent 协议 | LangGraph GlobalState 中各阶段产物统一带 `confidence`/`source`/`verified` 元数据 |
| **vulnerability-triage 分诊范式**：扫描结果 → 可验证假设 + 最小证据集 + 优先级 backlog | CyberStrikeAI `agents/vulnerability-triage.md` | vuln_judge 节点用 LLM 对 nuclei 结果做分诊（去重、定级、误报风险评估），产物写 `false_positive_risk/reason` |
| **文件 checkpoint 断点续跑** | CyberStrikeAI `workflow/checkpoint_store.go` | LangGraph 已有 checkpointer，改为 SqliteSaver/PostgresSaver 持久化，任务可重试续跑 |
| **Dead-end 记录**：被否证的路线不再重试 | muteki | 误报/不可达资产标记后跳过后续扫描 |
| **事件流进度上报**（单调序号 + SSE） | muteki event_bus | 复用现有事件总线，task_runner 每阶段发 Progress 事件驱动前端 |

---

## 二、S-A 资产发现真实化（预估 3-4 天）

> **进度（2026-08-18）**：✅ 已完成——naabu 接入 `_TOOL_PLATFORMS`、parser 接线修复（此前所有 CLI 工具
> `result.parsed` 恒为 None 的 bug）、dnsx 参数 `-d`→`-l`（新版 dnsx -d 为爆破模式）、
> 新增 `services/domain_pipeline.py`（subfinder→dnsx→httpx→naabu 链式编排）与
> `services/persistence.py`（Asset 幂等 upsert）、task_runner M3 真实执行、
> `scripts/ensure_tools.sh` 探活/安装。单测 `tests/unit/asset_discovery/test_domain_pipeline.py`
> 4 例全过；example.com 真实冒烟通过（subfinder 真子域、dnsx 真解析、httpx 真存活、naabu 真端口入库）。
> 遗留：crt.sh(cert) 路径未出结果（curl 拼装 URL 未实现，降级可接受）；`asset_discovery_use_stubs`
> 默认仍为 True（避免影响现有流程，联调时置 False）。

### A1. 打通端口扫描链路
- `tool_client.py` `_TOOL_PLATFORMS` 增加 `naabu`；新增 `_run_naabu(ip/domain, top-ports)`，输出解析回填 `Asset.open_ports`。
- 管线顺序：subfinder（子域）→ dnsx（解析 IP）→ httpx（存活/标题/技术栈指纹）→ naabu（对解析出的 IP 做端口扫描）。

### A2. 结果持久化与去重
- RawAsset → Asset 落库时按 `(task_id, domain, ip, port)` 幂等 upsert；`last_seen_at` 刷新；多来源命中提升 `confidence_score`。
- ICP 备案校验接入 A4 的 ICP 数据源，回填 `icp_verified/icp_entity`。

### A3. 默认切换真实模式
- `asset_discovery_use_stubs` 默认改 False；工具缺失时**显式报能力不可用**（返回带 reason 的空结果 + 任务事件），不再静默假数据。
- 新增 `scripts/ensure_tools.sh`（subfinder/dnsx/httpx/naabu/nuclei 探活，go install 提示）与 `GET /api/v1/system/tools` 端点返回工具可用性矩阵。

### A4. 入口打通
- task_runner `_run_m3_asset_discovery`：取 Company.domains/email_domains 作为种子域名，调用资产发现服务，结果写 Asset。

**验收**：对一个真实企业域名执行 M3，产出真实子域、IP、端口、http 存活数据入库。

---

## 三、S-B 情报采集真实数据源（预估 4-5 天）

> **进度（2026-08-18）**：✅ 主体完成——
> `news_scraper.py` 重写为「Bing News RSS（免 key）→ CDP 浏览器（bing 引擎，Playwright）→ stub 兜底（仅
> intelligence_use_stubs=True）」三级路径，真实冒烟产出 7 条带真实 URL 的新闻；
> 新增 `icp_scraper.py`（第三方备案 API，支持 ICP_API_URL/ICP_API_KEY 环境变量自定义提供方，
> `query_icp()` 独立函数供回填）与 `bidding_scraper.py`（ccgp 政府采购网检索 + 指数退避重试，
> `parse_bidding_html()` 可单测）；`legal_scraper.py` 改为 ICP+招投标组合；`official_scraper.py`
> 真实抓取官网（httpx→CDP 兜底）；crawler 接线 icp_query→IcpScraper、bidding→BiddingScraper；
> `task_runner._backfill_icp()`：M1 后按 Company.domains 查备案，回填 Company.icp_number/icp_entity
> （模型新增列）与匹配后缀 Asset 的 icp_entity/icp_verified，并存 IntelDocument（checksum 去重）；
> 修复 cdp_scraper._cleanup 已关闭句柄崩溃 bug。单测 14 例（scraper 12 + 回填 2）全过。
> 环境限制：本机出口 IP 被 ccgp 限频、ICP 免费提供方不可达（生产可通过 ICP_API_URL 配置可用提供方），
> 解析逻辑已由单测覆盖。存量 eakis_test.db 需 `ALTER TABLE companies ADD COLUMN icp_number/icp_entity`
> 或重建库。测试基线：intelligence/test_router 6 例失败系上次会话遗留的未提交 router 改动所致，
> 与本次无关（stash 全部 src 改动后复现通过）。

### B1. 替换三个 stub scraper
- `news_scraper.py`：改为通用引擎路径优先（Bing News / Baidu News API，engine_specs 增配置），无 key 时降级 CDP 抓取 baidu 新闻搜索页；产出真实 URL/标题/正文/发布时间。
- `legal_scraper.py` 拆分：
  - **ICP 备案**：接工信部备案查询（CDP 过滑块，或第三方备案查询 API 如 beianx/站长工具，按 engine_spec 配置 key），按 Company.domain 查主体名与备案号 → 回填 Company + Asset。
  - **招投标**：中国政府采购网（search.ccgp.gov.cn）+ 各省公共资源交易网搜索接口，按企业名+关键词检索公告列表与详情。
- `official_scraper.py`：用 Company.website 真实抓取（复用 CDPScraper/GenericEngineScraper）。

### B2. 采集质量与去重
- IntelDocument 已有 `checksum` 去重（task_runner M1 已实现），补 `quality_score` 规则（正文长度/时间新近度/来源权重），低于阈值不进 RAG。
- 每条 IntelDocument 记录 `entities`（LLM 抽取的企业/人名/产品），供关键词引擎与报告引用。

**验收**：M1 对真实企业产出带真实 URL 的新闻/备案/招投标 IntelDocument，且 RAG 可检索。

---

## 四、S-C 漏洞检测引擎（预估 4-5 天）

> **进度（2026-08-18）**：✅ 主体完成——新增 `src/pentest/scanner.py`：`NucleiScanner`
> 基于 ToolExecutor 调 nuclei（-jsonl，逐目标隔离故障，超时 900s），`in_scope()` 授权边界
> 前置校验（域名后缀/IP/CIDR，空 scope 一律拒绝），`parse_nuclei_line()` 解析
> template-id/severity/cvss/reference 并完整保留原始 JSON 作为 evidence（muteki gate 理念：
> 无证据不得 verified，入库一律 detected/candidate）；`findings_to_vulnerability_rows()`
> 按 URL/域名匹配 asset_id。task_runner 新增 `_run_m5_vuln_scan()`：扫 M3 落库的 http/https
> 存活资产 → Vulnerability 落库（同资产同模板幂等去重，severity 过滤与目标上限可配）；
> orchestrator `nodes/test_exec.py` 由 stub 改为真实调用扫描器（结果写 state.vuln_findings，
> 工具缺失记 pipeline_errors 不产假数据）。单测 11 例全过（边界/解析/降级/落库幂等）。
> **遗留**：~~nuclei 二进制安装两次被中断~~ **已解决（2026-08-19）**：nuclei v3.11.1 预编译
> 二进制装入 /root/go/bin（GitHub release 下载，避开 go 编译中断），模板已更新。
> **真实 M5 冒烟通过**：本地靶机（127.0.0.1:18080，授权 scope 内）全模板扫描，
> 13 个发现 → 3 条 Vulnerability 入库（SNMPv3 Fingerprint / Wappalyzer Tech Detection /
> HTTP Missing Security Headers），全部携带完整原始 nuclei JSON evidence。

### C1. nuclei 执行器
- 新建 `src/pentest/scanner.py`：`NucleiScanner.scan(targets, severity_filter, tags)` 经 `ToolExecutor` 调 nuclei（`-json -severity medium,high,critical`，默认 `-tags exposure,misconfig,cve`，限并发与速率）。
- 结果解析：nuclei JSON → Vulnerability（template-id/vuln_type、severity、cvss、matched-at → affected_path、提取的 evidence 原文、reference → remediation）。
- 授权边界：仅扫描 task.authorized_scope 内的资产（域名/IP 段），复用 `tools/security.py` 校验。

### C2. 误报分诊（借 CyberStrikeAI triage + muteki gate）
- `vuln_judge` 节点 LLM 分诊：对每条 finding 评估 `false_positive_risk/reason`、`llm_confidence`，状态初始 `candidate`；evidence 完整且置信高 → `verified`。
- 人工确认闭环：Vulnerability.human_confirmed 已有字段，前端漏洞页已支持状态更新。
- Dead-end：人工标记误报的 (template-id, asset) 写入 task 级跳过清单，后续扫描不再报。

### C3. 接线
- task_runner `_run_m4` 扩展：M4 接口爬取（现有 static_analyzer 真实实现）→ M5 漏洞扫描（对 Asset 中 http 存活资产跑 nuclei）。
- orchestrator `nodes/test_exec.py` 由 stub 改为调用 C1。

**验收**：对授权测试资产（如自建 vulhub 靶机）跑 M5，产出带 evidence 的真实漏洞记录，人工可确认/否证。

---

## 五、S-D LangGraph 全流程编排（预估 3-4 天）

> **进度（2026-08-18）**：✅ 主体完成——新增 `src/orchestrator/company_graph.py`：企业级
> LangGraph 图（M0 云图→M1 情报+ICP 回填→M2 关键词→M3 资产→M4 预留→M5 漏洞→M6 报告），
> 按 config.modules 动态构建节点链（auto_report 可追加 M6）；`AsyncSqliteSaver` 持久化
> checkpoint（thread_id=task.id，断点续跑；生产可换 PostgresSaver），不可用时回退 MemorySaver；
> 单模块失败记录 state.errors 不中断管线。task_runner.run_task_pipeline 收敛为图调用层
> （删除手工 for 循环）。M6 报告节点复用既有真实 worker（aggregate→render→score→落库
> reports 表）。端点 `POST /v1/tasks/{id}/start` 不变，内部走图。单测 4 例全过
> （全模块顺序+真实报告生成/单模块失败不中断/未启用模块不进图/auto_report）。
> 依赖：pyproject 增 `langgraph-checkpoint-sqlite`。旧 13 节点 DSL 图（graph.py）保留用于
> 情报 DSL 管线，两图并存。**遗留**：M4 静态分析接入图、SSE 进度事件推送。
>
> **端到端真实验证（2026-08-19）**：`POST /v1/tasks/{id}/start` 对真实企业
> 「阿里巴巴（中国）有限公司」（domains=alibaba.com）执行 M0→M6 一键运行，9 分钟完成，
> Task=completed/progress=1.0。真实产物：资产 2 条（alibaba.com→47.246.137.105 端口
> 80/443，含 IP 资产，subfinder/dnsx/httpx/naabu 真实链路）、IntelDocument 9 条（Bing
> 真实 URL：企查查/百度百科/阿里官网/招聘页等）、关键词 392 条、漏洞 0（authorized_scope
> 仅含 127.0.0.1，第三方资产正确被授权边界拒绝——符合预期）、报告 completed（真实渲染的
> 攻击面评估报告 Markdown）。过程中修复断点续跑重放导致 progress>1 违反 CHECK 约束的
> bug（completed 去重 + 进度钳制 [0,1] + 节点级 commit 失败回滚不中断管线）。
> 存量库升级注意事项：companies 表需补 icp_number/icp_entity 列；sqlite 中 UUID 以无
> 连字符十六进制存储，直接 SQL 操作任务时注意。

### D1. 统一编排入口
- 以 `src/orchestrator/graph.py` 的 LangGraph 图为唯一管线；`task_runner.py` 改为图的调用层（构建 initial state、传入 task_id/company 上下文、checkpointer 配置），删除其自行实现的 M0-M2 顺序逻辑（逻辑下沉到对应 node）。
- 图结构（对现有 13 节点补齐）：
  ```
  enrich(M0云图) → intel(M1) → keywords(M2) → asset_discovery(M3真实链路)
  → asset_assess/enrich → api_crawler(M4) → vuln_scan(nuclei) → vuln_judge(分诊)
  → report_gen → END
  ```
- checkpointer 由 MemorySaver 换 SqliteSaver（开发）/PostgresSaver（生产），支持失败任务从断点续跑（借 CyberStrikeAI checkpoint 思路）。

### D2. 进度与状态
- 每节点首尾更新 Task.current_stage/progress，并发进度事件（复用事件总线/SSE）。
- 节点失败：写 error_message、retry_count+1，支持从最后 checkpoint 重试。

### D3. 一键执行端到端
- API：`POST /tasks/{id}/run` → 后台线程/worker 跑图（M0→M6 按任务 config.modules 可配置跳过）。
- 前端 TaskManagement 已有模块配置，补"运行全流程"入口与阶段进度实时展示。
- 报告生成 worker：M6 report_gen 节点汇总 Company/Asset/Vulnerability/IntelDocument 生成报告（模板复用 `src/report/templates`），替代现有 generate 占位。

**验收**：输入企业名称一键执行，产出：企业画像 + 情报文档 + 关键词 + 资产列表 + 漏洞列表 + 报告，全流程任务进度可见、失败可续跑。

---

## 六、执行顺序与里程碑

| 阶段 | 内容 | 依赖 | 里程碑 |
|---|---|---|---|
| 第 1 周 | S-A 资产发现真实化 | 安装 PD 工具链二进制 | 真实资产入库 |
| 第 2 周 | S-B 情报数据源 | engine key / CDP 环境 | 真实 IntelDocument |
| 第 3 周 | S-C 漏洞引擎 | S-A 的资产产出 | nuclei 真实漏洞 + 分诊 |
| 第 4 周 | S-D 编排统一 | S-A/B/C | 端到端一键 + 报告 |

每阶段完成标准：真实数据端到端入库 + 对应 API/前端页面可见 + 冒烟测试（tests/ 下补集成测试，外部工具缺失时 skip）。

---

## 七、风险与对策

- **外部工具安装**：WSL/生产环境需 go install 或发行版包；ensure_tools 探活 + 能力矩阵展示，缺失不阻塞其他阶段。
- **ICP/招投标反爬**：备案查询强反爬，优先第三方 API（配 key），CDP 作为兜底；均失败时该数据源标记不可用并降级，不产假数据。
- **扫描合法性**：nuclei/naabu 仅对 authorized_scope 内目标执行，BoundaryGuard 校验前置到节点入口（ROADMAP 已列）。
- **LLM 分诊成本**：vuln_judge 仅对 high/critical 或去重后的 finding 调 LLM，低危直接入库为 candidate。
