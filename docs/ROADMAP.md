# EAKIS 后续开发路线图 (ROADMAP)

> **版本**：v1.4（2026-06-17）
> - v1.0 初稿：现状基线 + S0–S7 路线图 + 附录 A 议程
> - v1.1：附录 A.1 企业关系穿透、A.2 知识库管理 **决策沉淀完成**（6 + 4 项决策），回填 S1/S3 交付物
> - v1.2：附录 A.4 资产管理、A.7 风险评估关联 **决策沉淀完成**（4 + 3 项决策），回填 S1/S2/S5 交付物
> - v1.3：附录 A.3 任务管理、A.5 漏洞管理、A.6 模板管理 **决策沉淀完成**（4 + 4 + 6 项决策），回填 S4/S5/S6 交付物。附录 A 全部 7 主题决策完成。
> - **v1.4**：新增**附录 C 前端 UI 构想决策**（4 块 17 项：菜单结构/Tab 列定义/任务管理/详情页），与附录 A 后端决策对齐，回填 S0/S1/S4 前后端交付物。
> **状态**：附录 A（后端 7 主题）+ 附录 C（前端 4 块）全部已决策；进入执行规划阶段
> **关联文档**：`docs/extract/01_02_项目概述与系统架构设计.md`、`docs/extract/14_功能开发进度表.md`、`plan.md`（前端对接收尾子计划）
>
> 本文档分三部分：
> 1. **项目现状基线** —— 当前已完成 / 缺口盘点
> 2. **战略路线图 (S0–S7)** —— 12–24 个月分阶段交付
> 3. **新功能头脑风暴框架** —— 7 个主题的待决策清单（附录 A）

---

## 一、项目现状基线

### 1.1 后端（FastAPI，12 个 router，约 65 个端点）

| 领域 | 状态 | 说明 |
|------|------|------|
| 基础设施 | ✅ | FastAPI + JWT 认证 + 令牌桶限流 + 审计日志中间件 + 结构化 JSON 日志（trace_id） + 熔断器 + TTL 缓存 + 事件总线 + MinIO + Prometheus 指标 + Alembic |
| RBAC | ✅ | `users/teams/audit_logs` 三个 router（15 端点）+ `deps/permissions.py`（约 50 个 `PermissionAction` + 资源归属校验）+ `seed_rbac.py`（角色/权限/默认组织/默认管理员/默认团队） |
| M1 情报采集 | ✅ | datasource/dsl/crawler/cleaner + 反爬（代理池 Redis/内存 + UA 池 + 指纹）+ RAG（Qdrant + 内存双模式 + OpenAI Embedding） + CDP 爬虫 |
| M2 关键词引擎 | ✅ | generator/ranker/summarizer/expander/feedback + 6 行业领域词库 |
| M3 资产发现 | ✅ | search_engine/feature_extractor/assessor/enricher（多数 `use_stubs=True`，需真实数据源联调） |
| M4 接口爬取 | ✅ | static_analyzer/classifier/version_tracker 真实实现；browser_agent/cdp_interceptor 部分为 Stub |
| M2 推理服务 | ✅ | Ollama 本地推理 + OpenAI 兼容 `/v1/chat/completions` |
| M5 自动渗透 | 🚧 未实现 | `vulnerabilities` router 仅列表/统计/详情/状态更新，**无真实扫描/插件** |
| M6 报告生成 | 🚧 占位 | `reports` router 的 `generate` 仅插入 `generating` 占位行返回，**无生成 worker** |
| 编排层 | 🚧 | LangGraph 14 节点图 + MemorySaver；M5/M6 节点为 stub；**BoundaryGuard 授权边界未实现**；全流程串联未做 |

### 1.2 前端（React 18 + TS + Vite + Ant Design 暗色 + MSW + Zustand + ECharts）

**A. 已对接真实 API（dev 模式可用）**
Login、Companies（列表/创建/删除 + Detail 企业信息/下属单位/OSINT 真实部分）、Assets、Vulnerabilities、Keywords、TaskManagement、Reports、AgentManagement、Settings（系统状态/AI Provider/Agent 配置/Webhook）、StatusPage。

**B. Mock 耦合（切真实后端会崩）**
- `Dashboard` —— Agent 日志直接硬编码 `mockLogs` 数组，未接 `useTaskEvents` WebSocket。
- `Companies/Detail` —— 资产/漏洞 Tab 直接 `import { mockVulnerabilities, mockIPAssets } from '@/api/mock/data/*'`。
- `Settings` —— 搜索网站 / 关键词模板 / 并发设置 3 个 Tab 用内联数组。
- `ExportRecords` —— 纯内联 mock。

**C. 孤儿代码 / 路由不一致**
- `OrchestrationPage`、`Pentest` 页面已完整实现但未挂路由（死代码）。
- `Interfaces` 页面已实现，但 `router.tsx` 中其路由是 `PlaceholderPage`，**App 内不可达**。
- `AgentManagement` 路由可达但不在 Sidebar。
- `web/src/api/mock/handlers/` 目录（6/11 旧版）与 `handlers.ts`（6/17 单文件版）并存，`browser.ts` 实际 import 单文件版；旧目录无人引用，存在 resolver 歧义风险。

**D. MSW 致命隐患**
`handlers.ts` 把任务作用域 URL 硬编码成 `TASK_ID='task_01J9XXXXX'`，而 Sidebar 通过 `listTasks()` 取真实 task 的 `task_id` 存入 `taskStore`。**mock 模式下** Assets/Keywords/Interfaces/Vulnerabilities/Reports 请求 `/v1/tasks/<真实id>/...`，路由不匹配 → MSW 透传 → 落到 Vite dev server 404。**mock 模式当前实质不可用于任务作用域页面。**

**E. API 模块状态对照**

| 前端 api 模块 | 后端 router | Mock | 页面 | 备注 |
|---|---|---|---|---|
| auth | auth.py | ✅ | ✅ Login | — |
| tasks | tasks.py | ✅ | ✅ TaskManagement | 缺 `getTaskStatus`/`updateTask` 封装 |
| assets | assets.py | ✅ | ✅ Assets | 缺 `discoverAssets`/`getAssetDiscoverStatus` |
| interfaces | interfaces.py | ✅ | ⚠️ 页面有但路由是占位 | 缺 `crawlInterfaces`/`getInterfaceCrawlStatus` |
| vulnerabilities | vulnerabilities.py | ✅ | ✅ Vulnerabilities | — |
| keywords | keywords.py | ✅ | ✅ Keywords | — |
| reports | reports.py | ✅ | ✅ Reports | generate 为后端占位 |
| companies | （无独立 router） | ✅ | ✅ Companies | 后端缺独立 router，详情部分走 mock |
| system | main.py 内联 | ✅ | ✅ Settings/Status | — |
| providers/webhooks | （无后端 router） | ✅ | ✅ Settings | **后端未实现** |
| users | users.py | ❌ | ❌ | **后端就绪，前端 0 UI 0 mock** |
| teams | teams.py | ❌ | ❌ | **后端就绪，前端 0 UI 0 mock** |
| auditLogs | audit_logs.py | ❌ | ❌ | **后端就绪，前端 0 UI 0 mock** |
| intelligence/inference/tools/osint/knowledge/templates/orchestrations/pentest | 部分/无 | ❌ | 部分/无 | 全为 Stub |

### 1.3 已发现的契约不一致（需在 S0 修复）

1. `updateUser` / `updateTeam` / `updateTeamMemberRole` 前端用 `PUT`，后端暴露 `PATCH`。→ 统一为 `PATCH`。
2. `CreateUserRequest.role_name` 前端为必填，但后端创建端点的角色字段命名/是否必填需核对（`seed_rbac.py` 角色为独立表，user 表存 `role_id` vs `role_name` 待确认）。
3. tasks.py `_count_task_stats` 注释"暂无 Interface model"，但 `models/interface.py` 的 `ApiInterface` 已存在 —— 顺手修复统计。

---

## 二、战略路线图 (S0–S7)

> 排期以"阶段 (Stage)"而非绝对日历组织，便于并行推进。每阶段含：**目标 / 交付物 / 依赖 / 验收指标 / 风险 / 负责人(占位)**。

### S0 — 前后端对接收尾（2–3 周）

**目标**：消除所有"后端就绪但前端缺失/契约不一致"缺口，使 dev + mock 双模式都能跑通核心闭环。

**交付物**
- RBAC 管理：`/admin/users`、`/admin/teams`、`/admin/audit-logs` 三个页面（建议独立路由 + Sidebar 入口，而非塞进 Settings Tab，便于权限隔离）。
- 契约修复：PUT→PATCH、role 字段对齐、task 统计修复。
- MSW 修复：`handlers.ts` 改用通配 `*/tasks/:taskId/*` 路由；删除废弃 `handlers/` 目录；为 users/teams/auditLogs 补 mock。
- 操作收口：补 `discoverAssets`/`getAssetDiscoverStatus`/`crawlInterfaces`/`getInterfaceCrawlStatus`/`getTaskStatus`/`updateTask` 封装，并在 Assets/Interfaces 页接入"启动发现/爬取"按钮与状态展示；激活 Interfaces 路由。
- 去 mock 耦合：Dashboard 接 `useTaskEvents`；Companies/Detail 资产/漏洞改为按 company_id 过滤的真实查询；Settings 三 Tab 定义后端契约或本地持久化。
- 清理：决策 OrchestrationPage/Pentest 去留；Sidebar 补 AgentManagement。

**依赖**：无（纯前端 + 少量后端字段对齐）。
**验收**：`tsc --noEmit` 通过；`npm run build` 通过；`pytest` 通过；dev/mock 双模式手动验证 Settings/TaskManagement 全流程；MSW 任务作用域页面不再 404。
**风险**：低。
**负责人**：前端组 + 后端组（字段对齐）。

---

### S1 — 数据贯通：企业↔资产↔漏洞↔接口关系建模（4–6 周）

**目标**：建立四元组的关系模型与级联查询能力，为关系图可视化、风险评估、报告聚合打地基。

**交付物**
- 后端
  - 独立 `companies` router（当前缺失）：企业 CRUD + 子公司/控股关系 + OSINT 字段持久化。
  - 关系模型：`company ↔ asset`（asset 表已有 company 字段，补索引与级联）、`asset ↔ interface`、`asset/interface ↔ vulnerability`、`vulnerability ↔ report`。
  - 级联查询 API：`GET /v1/companies/{id}/assets|vulnerabilities|interfaces`、`GET /v1/assets/{id}/vulnerabilities|interfaces`、聚合统计端点。
  - 资产按 `company_id` 过滤参数（解 Companies/Detail mock 耦合的后端侧）。
- 前端
  - 关系图：复用现有 `GraphPanel` + ECharts，实现企业/资产/攻击/模块四种 graphType 真实数据驱动（当前 graphStore 仅切类型无数据）。
  - Companies/Detail 改为真实级联查询。
- 数据
  - 制定去重与归一规则（资产：ip+port+domain 三元组；漏洞：rule+target+param 三元组）。

**依赖**：S0（契约对齐）。
**验收**：从企业节点可下钻到资产→接口→漏洞全链路；关系图节点/边数据来自真实查询；去重规则单测覆盖率 ≥ 80%。
**风险**：中 —— 历史数据回填去重；关系图性能（大数据量需服务端聚合/分页）。
**负责人**：后端组（建模/API）+ 前端组（图）+ 算法组（去重规则）。

---

### S2 — M6 报告生成落地（6–8 周）

**目标**：替换 `reports.generate` 占位，实现"数据聚合 → LLM 生成 → 模板渲染 → 质量评分"真实流水线。

**交付物**
- 报告数据聚合器：从 task 聚合企业/资产/接口/漏洞/情报全量数据为中间结构。
- LLM 生成 Prompt（各章节：摘要/资产清单/风险分析/修复建议/附录），`config/prompts/` 管理。
- 模板：Markdown + PDF（weasyprint 或 pandoc）双格式；质量评分 Prompt。
- 异步 worker：Celery 或 FastAPI BackgroundTask，状态写入 report 行，前端轮询/WebSocket。
- 替换 reports router 占位 + 接 Reports 页面进度展示与下载。
- MinIO 存储成品 PDF，presigned URL 下载。

**依赖**：S1（聚合需要关系贯通）。
**验收**：单任务报告生成 ≤ 30 分钟；LLM-Judge 质量分 ≥ 0.90；PDF 可下载。
**风险**：高 —— LLM 长文本质量与耗时；PDF 中文字体；成本控制（路由到 qwen/gpt-4o）。
**负责人**：算法组（Prompt/Judge）+ 后端组（聚合/worker/存储）+ 前端组（进度/下载）。

---

### S3 — 知识库管理（4–6 周）

**目标**：把前端 `knowledge.ts` stub 落地为后端持久化的可治理知识库。

**交付物**
- 后端 `knowledge` router：nuclei-pocs / 路径字典 / 密码字典 / 指纹库 / Handbook 的 CRUD + 版本化 + 来源同步（如 nuclei upstream）。
- 知识贡献审核流（可选 v1：管理员直接发布）。
- 前端知识库 6 个子页面（替换 router.tsx 中的 PlaceholderPage）。
- 与 M4/M5 的集成：指纹库供 feature_extractor，字典供扫描插件，nuclei-pocs 供漏洞扫描。

**依赖**：S0。
**验收**：6 类知识可 CRUD；指纹库被资产增强模块消费；nuclei-pocs 可被 M5 扫描调用。
**风险**：中 —— 外部源同步频率与冲突合并。
**负责人**：后端组 + 安全组。

---

### S4 — 模板管理（3–4 周）

**目标**：落地任务模板 / Prompt 模板 / 攻击路径模板（替换 `templates.ts` stub）。

**交付物**
- 后端 `templates` router：三类模板 CRUD + 参数化 + 继承。
- 前端模板 3 个子页面；任务创建 Modal 支持"从模板创建"。
- Prompt 模板被 M2/M6 消费。

**依赖**：S0、S2（Prompt 模板复用）。
**验收**：任务可从模板一键创建；Prompt 模板被报告生成消费。
**风险**：低。
**负责人**：后端组 + 前端组。

---

### S5 — M5 自动渗透测试（8–10 周）

**目标**：实现接口类型→漏洞映射、Payload 库、测试执行引擎、插件集、LLM-as-Judge 验证、BoundaryGuard 授权边界。

**交付物**
- 规则库：接口类型→漏洞映射 + Payload 库（SQLi/XSS/SSRF/越权/IDOR/未授权/文件上传）。
- 测试执行引擎：限速/超时/并发控制/单测容错。
- 插件集：SQLi（报错/盲注/联合）、越权（水平+垂直）、未授权+IDOR+XSS、SSRF+上传、GraphQL/gRPC。
- LLM-as-Judge 漏洞验证 + 误报样本库。
- **BoundaryGuard 授权边界校验模块**（设计文档标注"待启动"，是合规前置）。
- vulnerabilities router 接入真实扫描结果写入；前端 Vulnerabilities 页接入扫描触发。

**依赖**：S1（接口数据）、S3（Payload/nuclei）。
**验收**：漏洞覆盖率 ≥ 92%，误报 ≤ 18%（设计指标 M2.3）；DVWA/WebGoat 靶场通过；授权边界零越界。
**风险**：高 —— 合规风险（BoundaryGuard 必须先行）；插件误报率；并发对靶标压力。
**负责人**：安全组（规则/插件）+ 算法组（Judge）+ 后端组（引擎）。

---

### S6 — 端到端验证（4 周）

**目标**：LangGraph 全流程串联 + 5 个真实项目落地。

**交付物**
- 替换 M5/M6 stub 节点为真实模块；打通 13 阶段线性流水线 + 反馈回路。
- `useTaskEvents` WebSocket 全链路事件流接入 Dashboard。
- 5 个真实授权项目跑通，收集效率/覆盖率数据。
- 性能基准测试 + 瓶颈优化。

**依赖**：S1–S5 全部。
**验收**：全流程探测周期 ≤ 2–3 天（设计指标）；效率提升 ≥ 60%；5 项目数据归档。
**风险**：高 —— 真实环境不确定性；LangGraph 状态机稳定性。
**负责人**：架构组 + 全团队。

---

### S7 — 运维交付（3 周）

**目标**：生产可部署。

**交付物**
- Docker Compose（开发）+ K8s（生产）配置（含 Kafka/Redis/Qdrant/MinIO/Prometheus/Grafana）—— 14.2 表中"待启动 (WSL 部署)"项。
- CI/CD（lint/test/build/push）。
- 完整 API 文档 + 部署指南 + 培训材料 + 第一阶段技术文档。

**依赖**：S6。
**验收**：`docker compose up` 一键起；K8s helm chart 可部署；文档齐全。
**风险**：低–中。
**负责人**：DevOps + 全团队。

---

### 路线图总览（甘特视图）

```
阶段    W1--W2--W3--W4--W5--W6--W7--W8--W9-W10-W11..W20..W30..W40
S0 对接收尾  [====]
S1 数据贯通       [========]
S2 M6 报告             [==========]
S3 知识库             [========]          (可与 S2 并行)
S4 模板管理                [======]       (可与 S3 并行)
S5 M5 自动渗透                   [==================]
S6 端到端验证                                      [========]
S7 运维交付                                              [======]
```

> 并行建议：S0 串行先行；S1 完成后 S2/S3/S4 可三线并行；S5 依赖 S1/S3；S6/S7 收尾串行。

---

## 附录 A — 新功能头脑风暴框架（待与用户逐项讨论）

> 以下为后续头脑风暴的**议程输入**，每项给出：问题空间、候选方案、开放问题。决策后回填到对应 S 阶段。

### A.1 企业关系穿透 ✅ 已决策（2026-06-17）

- **问题空间**：当前企业是扁平记录，无母子公司/控股/参股/ICP 关联。攻击面探测需穿透集团架构发现关联资产（共享 ICP、共享域名根、共享 IP 段）。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 数据源 | **多源融合** | 商业 API（天眼查/爱企查/企查查，付费结构化）为主 + ICP 备案反查（共享备案主体=关联线索）+ OSINT 补充，多源交叉验证提高准确率。**待办：确认采购哪家商业 API 及预算。** |
| 2. 存储建模 | **关系表 PostgreSQL** | `companies` 表加 `parent_id`/`holding_ratio` 自引用；另建 `company_relations` 表存任意关系类型（控股/参股/分支机构/历史关联）。不引入 Neo4j，与现有栈一致。 |
| 3. 穿透策略 | **可配置** | 默认 3 层 + 持股 ≥ 51%（控股）；每个任务创建时可调（层数 1–N / 阈值 / 是否含参股）。适配不同项目需求。 |
| 4. 资产继承 | **自动继承 + 可关** | 子公司资产自动计入集团攻击面，但标记来源（`direct`/`inherited`）。默认开启，可在任务配置中关闭。 |
| 5. 授权边界 | **沿用现有 RBAC** | super_admin 看全部，org_admin 看本组织，team 看本团队负责的企业；继承资产同样受边界约束。不新增"企业可见域"粒度。 |
| 6. 可视化 | **ECharts graph** | 复用现有 `GraphPanel` + ECharts graph（`graphType=enterprise` 骨架已存在），后端返回 `{nodes, edges}` JSON。零新依赖。 |

**对 S1（数据贯通）的交付物补充**：
- `companies` router：企业 CRUD + 关系 CRUD + `GET /v1/companies/{id}/relations`（多层穿透，支持 depth/holding_ratio/include_partial 参数）。
- 关系图端点：`GET /v1/companies/{id}/graph?depth=N` → `{nodes:[{id,name,type,holding_ratio,source}], edges:[{from,to,relation_type,ratio}]}`。
- 资产继承：集团资产聚合查询时按 `source` 区分，统计页分别展示"直接/继承"。
- RBAC：穿透与聚合查询全部走 `require_resource_access`，与现有公司归属校验一致。

### A.2 知识库管理 ✅ 已决策（2026-06-17）

- **问题空间**：nuclei-pocs / 字典 / 指纹当前散落文件或 stub，无版本、无审核、无来源同步。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 存储方式 | **DB 元数据 + MinIO 内容** | PG 表存元数据（名称/类型/版本/标签/状态/来源/upstream_ref）；大文本（POC YAML、字典内容、指纹 JSON）存 MinIO 对象存储。查询快、内容不限大小，与现有栈一致。 |
| 2. 上游同步 | **仅 nuclei 自动同步** | nuclei-pocs 从 GitHub upstream 定时 pull（APScheduler/Celery beat 定时任务）；指纹库（Wappalyzer）、字典（SecLists 等）由管理员手动维护导入。**降低冲突合并复杂度。** |
| 3. 贡献审核 | **提交 + 审核流** | engineer/analyst 可提交 → auditor/admin 审核 → 发布。引入版本状态机：`draft → pending_review → published → deprecated`。比 v1 仅管理员更严格，质量可控。 |
| 4. 适用范围 | **按标签过滤** | 知识条目可打"行业/技术栈/场景"标签；M4（指纹消费）/M5（POC/Payload 消费）调用时按当前资产特征过滤匹配，提高精准度。需维护标签体系（建议复用 A.4 资产标签体系，保持一致）。 |

**对 S3（知识库）的交付物补充**：
- `knowledge` router：6 类（nuclei-pocs / 路径字典 / 密码字典 / 指纹库 / Handbook / Hook）统一 CRUD + 版本列表 + diff + 审核动作（submit/approve/reject/deprecate）。
- `knowledge_tags`：标签体系表，与资产标签共用。
- nuclei 同步 worker：定时拉取 `projectdiscovery/nuclei-templates`，写入 MinIO + DB 元数据，记录 `upstream_commit`。
- 权限：`KNOWLEDGE_CONTRIBUTE`（提交）、`KNOWLEDGE_REVIEW`（审核，auditor/admin）、`KNOWLEDGE_READ`（默认）。
- 与 M4/M5 集成：feature_extractor 调指纹库（按技术栈 tag）；M5 扫描调 nuclei-pocs + 字典（按场景 tag）。

### A.3 任务管理 ✅ 已决策（2026-06-17）

- **问题空间**：当前任务是一次性手动创建。缺模板化、调度、子任务编排、断点恢复、并发配额。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 周期调度 | **Celery beat 周期调度** | 支持 cron 周期复扫（如每周一全量、每天增量）；复扫与首次任务共用 A.6 任务模板。支撑 A.4 变更 diff 与 A.7 风险趋势。引入 Celery + Redis（Redis 已在栈中）。 |
| 2. 子任务模型 | **parent_id 自引用** | `task` 表加 `parent_id` 自引用，主任务拆为情报/资产/接口/漏洞子任务，独立状态与统计。与现有 task 模型平滑扩展，子阶段可独立重跑。 |
| 3. 断点恢复 | **暴露 checkpoint 恢复** | 暴露 LangGraph MemorySaver 检查点：失败/中断后从最近 checkpoint 恢复，提供 `POST /v1/tasks/{id}/resume` + UI 按钮。复用现有检查点机制，避免整体重跑浪费。 |
| 4. 并发配额 | **全局 + 团队配额** | 全局并发上限 + 按团队配额（每团队 N 个并发任务，超限排队）。区别于现有按 IP 的 rate_limit，此处是任务级并发控制。与 RBAC 团队模型一致。 |

**对 S4/S6 的交付物补充**：
- `tasks` 表：加 `parent_id`、`schedule_cron`（周期表达式）、`schedule_id`（Celery beat 任务 id）、`checkpoint_id`（最近 MemorySaver 检查点）字段。
- 调度：Celery worker + beat；`POST /v1/tasks` 支持 `schedule_cron` 参数创建周期任务；任务结束触发 A.4 归档检查 + A.7 风险快照。
- 断点恢复：`POST /v1/tasks/{id}/resume` 从 checkpoint 恢复；`POST /v1/tasks/{id}/subtasks/{stage}/retry` 子任务级重跑。
- 并发控制：新增任务并发管理器（全局信号量 + 团队配额表 `team_quotas`），任务入队前校验，超限 `pending` 排队。
- 前端：任务创建 Modal 支持"从模板创建"（A.6）+ 周期调度配置；任务详情展示子任务状态树 + 恢复/重跑按钮。

### A.4 资产管理 ✅ 已决策（2026-06-17）

- **问题空间**：资产去重、生命周期（发现→确认→归档）、分组/标签、变更 diff 未定义。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 去重规则 | **三元组主键** | `(ip + port + domain)` 三元组为主键去重，同一三元组多次发现合并为一条；ICP 主体归一（同一企业名不同写法）。与现有 `search_engine.py` 去重逻辑一致。 |
| 2. 生命周期 | **三态 + 自动归档** | `discovered → confirmed → archived`；自动归档：连续 N 次复扫未再发现则归档（**默认 N=3**，可配置）。人工确认靶标归属走 `discovered→confirmed`。 |
| 3. 资产价值评分 | **多维加权公式** | `value = f(资产类型, 暴露面, 业务重要性)`：类型权重（数据库 > API > 后台 > 前台）、暴露面（公网 > 内网）、业务重要性（人工标注 1–5）。归一 0–100。**注：经 A.7 决策，价值评分用于资产排序/展示，不进入风险公式。** |
| 4. 变更 diff | **v1 要做** | 复扫对比，记录 `asset_history`（字段级：新增端口/技术栈变化/证书变更/风险等级变化），前端展示"新增/消失/变更"三列。 |

**对 S1（数据贯通）的交付物补充**：
- `assets` 表：加 `status`（discovered/confirmed/archived）、`value_score`、`last_seen_at`、`miss_count`（连续未发现次数，达 N 归档）字段。
- `asset_history` 表：字段级变更日志（asset_id/field/old_value/new_value/changed_at/task_id）。
- `asset_tags` 表：用户自定义 tag + 系统自动标签（按技术栈/行业），**与 A.2 知识库标签体系共用**。
- 资产去重：在 `search_engine.py` 现有三元组去重基础上，DB 层加唯一约束 + ICP 归一工具函数。
- 自动归档：复扫任务结束时触发归档检查 job。
- 资产价值评分：新增 `value_score` 计算函数（M3 enricher 阶段或独立 job），权重配置放 `config/`。

### A.5 漏洞管理 ✅ 已决策（2026-06-17）

- **问题空间**：漏洞去重/合并、生命周期、误报反馈闭环、SLA 缺失。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 去重规则 | **三元组主键** | `rule(漏洞规则/类型) + target(资产 ID) + param(参数/路径)` 三元组去重，同一三元组多次扫描合并为一条，保留首次发现 + 最近确认时间。 |
| 2. 生命周期 + SLA | **五态 + SLA** | `open → confirmed → fixing → retesting → closed`，可 `reopened`。状态机校验非法转换；按严重度定义修复时限（critical=7d/high=15d/medium=30d/low=90d，可配），超期接 webhook 告警。 |
| 3. 误报闭环 | **反哺 LLM Judge** | 用户标记误报 → 进入误报样本库 → 周期性反哺 M5 LLM Judge 训练/调优。闭环提升检测准确率。 |
| 4. 责任指派 | **v1 不指派** | v1 仅记录归属企业/任务创建者，SLA 告警发到企业关联团队（A.1 RBAC）或任务创建者。**后续按需加 owner_id 个人级指派。** |

**对 S5/S6 的交付物补充**：
- `vulnerabilities` 表：加 `status`（五态）、`first_found_at`、`last_confirmed_at`、`sla_deadline`、`is_false_positive`、`false_positive_reason` 字段；唯一约束 `(rule_id, target_asset_id, param)`。
- `vuln_status_transitions` 表：状态流转日志（vuln_id/from/to/by/at/comment），状态机校验函数。
- `false_positive_samples` 表：误报样本（rule/payload/response 特征），供 M5 Judge 调优。
- SLA：扫描写入漏洞时按严重度计算 `sla_deadline`；定时 job 扫超期漏洞 → 触发 webhook（复用 A.2/S0 的 webhook 配置）。
- 与 A.7 联动：漏洞状态变化（confirmed/closed）触发所属资产/企业 risk 重算（A.7）。
- 复测：v1 手动触发（`POST /v1/tasks/{id}/vulnerabilities/{vid}/retest` 调 M5 重扫该漏洞），自动复测推迟。
- 前端：漏洞详情加状态流转操作 + SLA 倒计时 + 误报标记。

### A.6 模板管理 ✅ 已决策（2026-06-17）

- **问题空间**：用户重新定义为 **4 类模板**：① 任务模板 ② 报告模板（资产/企业/漏洞报告，按类型输出指定字段，md+html）③ LLM 提示词（按任务类型）④ 可视化攻击路径定制。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 报告模板 | **字段勾选 + 布局** | 报告模板 = 字段选择器（勾选要输出的字段，如资产报告勾选 IP/域名/端口/技术栈/风险等级…）+ 格式（md/html）+ 排版布局（封面/页眉页脚）。后台按勾选字段聚合数据渲染。所见即所得。 |
| 2. 攻击路径模板 | **可视化 DAG 编辑器** | 用户在画布上拖拽节点（资产/漏洞/利用步骤）+ 连线，定义攻击路径模板；存为 DAG JSON，可可视化重现与复用。建议前端用 React Flow / AntV X6。 |
| 3. 任务模板 | **参数预设** | 任务模板 = 任务参数预设（目标企业、穿透深度、启用模块 M1–M6、并发配额、关联知识库/模板）。创建任务时选模板一键填充。与 A.3 调度配合。 |
| 4. 继承机制 | **4 类均支持继承** | 子模板可 override 父模板部分字段（如报告模板继承默认布局后改字段集；Prompt 继承基础指令后加场景限定）。`parent_template_id` 自引用。 |
| 5. 共享范围 | **三级可见域** | `scope: org(组织级,默认) / team(团队级) / private(个人)`，CRUD 时校验可见性，与 RBAC 一致。 |
| 6. Prompt 模板存储 | **DB 为主 + 文件种子** | Prompt 模板入库（支持在线编辑、版本、继承），`config/prompts/` 文件作为默认种子（首次启动 seed 到 DB）。M2(关键词)/M6(报告) 按 `template_id` 加载并填参。 |

**对 S4（模板管理）的交付物补充**：
- `templates` 表：统一存 4 类模板（`type: task/report/prompt/attack_path`），字段含 `parent_template_id`（继承）、`scope`（可见域）、`owner_id`、`version`、`content`（JSON：任务=参数预设，报告=字段勾选+布局，Prompt=Jinja2 文本，攻击路径=DAG JSON）。
- `templates` router：4 类统一 CRUD + 继承解析（读取时合并父模板字段）+ 可见域校验 + 版本列表。
- 报告渲染：`POST /v1/reports/render` 接 `report_template_id`，按字段勾选聚合数据（接 S2 报告生成）→ 输出 md/html。
- 攻击路径：前端 React Flow/X6 编辑器，保存 DAG JSON；M5 可按攻击路径模板编排测试顺序。
- Prompt 种子：启动时若 DB 无 Prompt 模板，从 `config/prompts/` 导入为 `scope=org` 种子模板。
- 权限：`TEMPLATE_MANAGE`（创建/编辑，受 scope 约束），`TEMPLATE_READ`（按 scope 可见）。

### A.7 企业-资产-漏洞关联（风险评估） ✅ 已决策（2026-06-17）

- **问题空间**：需要把企业/资产/漏洞串成"风险视图"，量化风险、追踪趋势、明确归属。

**决策结论**：

| 决策点 | 结论 | 说明 |
|---|---|---|
| 1. 风险公式 | **漏洞加权求和** | `asset_risk = Σ(vuln_cvss × severity_weight)`，按资产聚合漏洞分数。企业风险 = Σ(各资产 risk)。**不依赖 A.4 资产价值**（简化实现）。⚠️ 注：放弃了推荐的三维乘法，资产价值仅用于排序展示不进公式。 |
| 2. 风险视图 | **企业风险总览 + 趋势** | 聚合卡片（总资产/总漏洞/风险分） + 风险分时间序列曲线（ECharts） + 下钻到资产/漏洞。SLA 看板推迟到 A.5 漏洞生命周期定后。 |
| 3. 外部情报 | **v1 不接** | 风险分仅基于内部漏洞 CVSS + 严重度权重。CVE 利用情报/威胁情报黑名单后续按需加。 |

**风险公式细化**（建议权重，可调）：

```
severity_weight = {critical: 1.0, high: 0.7, medium: 0.4, low: 0.1}
asset_risk   = Σ over vulns (cvss_score × severity_weight)      # 0 ~ ∞，可加 cap
company_risk = Σ over assets (asset_risk)                        # 按企业聚合
```

- 漏洞 CVSS 归一或 capped（如单资产 risk cap = 100）避免极高值。
- 趋势：每次任务结束计算并写入 `risk_history`（snapshot：company_id/risk_score/asset_count/vuln_count/snapshot_at）。

**对 S1/S2/S5 的交付物补充**：
- S1：`risk_history` 快照表 + `GET /v1/companies/{id}/risk`（当前风险）+ `GET /v1/companies/{id}/risk/trend`（时间序列）。
- S1：风险计算函数（漏洞聚合，severity_weight 配置化放 `config/`）。
- S1：企业风险总览页（前端，复用 ECharts 折线 + 卡片，下钻接 S1 级联查询）。
- S2：报告生成时调用风险快照，作为"风险分析"章节输入。
- S5：漏洞扫描产生新漏洞后触发所属资产/企业 risk 重算。

---

## 附录 B — 阶段-主题映射速查

| 头脑风暴主题 | 主要归属阶段 | 次要阶段 | 状态 |
|---|---|---|---|
| A.1 企业关系穿透 | S1 | S6 | ✅ 已决策 (v1.1) |
| A.2 知识库管理 | S3 | S5 | ✅ 已决策 (v1.1) |
| A.3 任务管理 | S4 | S6 | ✅ 已决策 (v1.3) |
| A.4 资产管理 | S1 | S6 | ✅ 已决策 (v1.2) |
| A.5 漏洞管理 | S5 | S6 | ✅ 已决策 (v1.3) |
| A.6 模板管理 | S4 | — | ✅ 已决策 (v1.3) |
| A.7 风险评估关联 | S1+S2+S5 | S6 | ✅ 已决策 (v1.2) |

---

## 附录 C — 前端 UI 构想决策 ✅（2026-06-17）

> 基于用户提出的前端功能构想（左侧菜单、中间数据区、任务管理、详情页），与附录 A 后端决策对齐后沉淀。共 4 块 17 项决策。

### C.1 菜单结构与三栏布局

**决策**：

| 决策点 | 结论 |
|---|---|
| 任务管理菜单 | **拆为两个菜单**：① 任务管理（演练/扫描/导入）② 导出记录（独立菜单）。用户描述里"任务管理"出现两次，确认拆分。 |
| 资产页组织 | **多 Tab 分类**：资产页顶部 Tab = IP / 域名 / 证书 / 小程序 / APP / 企业信息（新增）。每 Tab 独立列定义与筛选。替换现有单表 + category 筛选。 |
| 企业管理 | **独立菜单 + 详情 Tab**：企业管理独立菜单；列表点击进详情（Drawer 或独立路由），详情内 Tab：企业信息 / 子单位 / 资产 / 风险 / 开源情报。对接 A.1 关系穿透。 |
| 右侧图谱 | **可收缩 + 随菜单切换**：图谱随菜单切 graphType（企业/资产/攻击/模块），可拖拽缩放到右侧。复用现有 GraphPanel + ECharts（A.1 已定 ECharts graph）。 |

**左侧菜单最终结构**（可收缩为图标）：
```
总览
企业管理
资产管理          # Tab: IP/域名/证书/小程序/APP/企业信息
漏洞管理
知识库管理        # nuclei-poc/关键词/数据源/路径字典/密码字典/攻防手册/指纹库
工具管理          # CLI工具/脚本
模板管理          # 任务模板/提示词/可视化攻击路径
任务管理          # 演练/扫描/导入
报告管理
导出记录          # 新增独立菜单
─────────────
系统设置 | 用户退出 | 系统状态(组件/资源)   # 左下角
```
（注：相比现有 Sidebar，新增"导出记录"独立菜单；知识库/模板的占位路由需激活；工具管理需新建。）

### C.2 中间数据区 — Tab 列定义

**决策**：

| 决策点 | 结论 |
|---|---|
| 企业信息字段读写 | **工商只读 + 业务可编辑**：工商字段（名称/行业/信用代码/注册资本/成立时间/法人/存续状态）由 A.1 商业 API/OSINT 采集只读；业务字段（邮箱域名/员工工号规则/标签/备注/图标/关键词）可人工编辑补充。 |
| 员工工号规则用途 | **生成账号/邮箱字典**：工号规则（如"6 位数字"）用于生成邮箱/账号字典（`user000001@domain`），支撑钓鱼检测与弱口令爆破字典生成。与 A.2 密码字典/社工场景关联。 |
| IP/域名/证书列 | **基础列 + 风险/关联列**：IP Tab = IP/区域/是否 CDN/ASN/更新时间/状态/**风险等级(A.7)**；域名 Tab = 域名/备案号/状态/whois；证书 Tab = 域名/颁发者/有效期/状态/更新时间/**关联企业(A.1)**。 |
| 小程序/APP 列 | **定义标准列**：小程序 = 名称/AppID/主体企业/类目/更新时间/状态；APP = 应用名/包名/签名证书主体/下载源/更新时间/状态。从应用商店/备案采集。 |

**企业信息 Tab 完整字段**：企业名称、行业、信用代码、邮箱域名、员工工号规则、存续状态、注册资本、成立时间、法定代表人、标签、备注、图标、关键词。

### C.3 任务管理 — 新建任务/编排/导出

**决策**：

| 决策点 | 结论 |
|---|---|
| 任务类型映射 | **type 字段区分 4 种**：`enterprise_penetration`（企业穿透，调 M1+M2）/ `asset_detection`（资产探测，调 M3）/ `risk_assessment`（风险评估，调 M5）/ `orchestration`（任务编排）。现有单一 task.type 需扩展枚举。 |
| 编排拆分 | **三层级联子任务**：编排创建主任务（parent_id=null），每个企业/IP 各拆子任务（parent_id=主任务）：企业→穿透子任务、IP/域名→探测子任务、资产→评估子任务。对接 A.3 parent_id。 |
| 智能 C 段扫描 | **后台自动拆子任务**：资产探测子任务结束后检查发现 IP，同 C 段 ≥4 个则自动生成新探测子任务加入当前编排。后台 job 实现，默认开、可关。与 A.4 去重 + 关联联动。 |
| 企业简称匹配 | **后端模糊匹配 + 用户确认**：用户输入简称 → 后端 `GET /v1/companies/search?q=简称` 调 A.1 商业 API/OSINT 模糊匹配 → 返回候选 → 用户确认全称。 |
| 导出存储 | **MinIO + 元数据表**：导出文件存 MinIO，DB 存 `export_records` 元数据（类型/范围/大小/创建人/状态/MinIO key）。下载走 presigned URL。 |
| 批量打包 | **后端动态 zip**：勾选多条 → 后端动态生成 zip 返回（或异步生成通知）。 |

**新建任务表单（按类型动态输入框）**：
- **企业穿透**：企业名称（简称则智能匹配确认）。→ 挖掘主体及 3 级下属公司的全称/行业/官网/业务关键词/法人/ICP 域名/证书。
- **资产探测**：IP、域名 + 开关"智能资产关联（扫描到的资产关联到企业）"。→ IP 端口扫描/指纹识别/DNS 枚举/域名解析/页面截图。
- **风险评估**：IP 或 IP:端口、域名（可从探测结果带入）+ 选择扫描模板。→ 漏洞扫描/前端接口检测。

**任务编排表单**（2 输入框 + 1 选择框 + 2 开关）：
- 企业名称（批量，每单位执行穿透）+ IP/域名（批量导入，每记录执行探测）+ 风险评估模板（每资产按模板评估）+ 开关"智能 C 段扫描"（默认开）+ 开关"智能资产关联"。

### C.4 详情页钻取

**决策**：

| 决策点 | 结论 |
|---|---|
| 详情页形态 | **右侧 Drawer**：点记录右侧滑出 Drawer 展示详情。复用现有 Assets/Vulnerabilities Drawer 模式，不离开列表。 |
| IP 详情维度 | **全维度展示**：端口开放表（端口/服务/版本/状态）+ 指纹列表 + 关联域名 + 端口关联漏洞 + 关联单位。对接 A.1 级联查询。 |
| 证书管理 | **资产 Tab + 独立模型**：证书作为资产子类入资产页证书 Tab；独立 `Certificate` 模型（域名/颁发者/有效期/序列号/签名算法/关联企业/证书透明度日志）。 |
| 漏洞详情 | **详情 + 跨资产关联**：漏洞详情（CVSS/PoC/证据/修复）+ 同一漏洞规则跨资产的关联资产列表（对接 A.1）。与 A.5 漏洞生命周期状态流转操作合并。 |

**新增后端模型/端点（回填各 S 阶段）**：
- **S1**：`Certificate` 模型 + 证书 CRUD；`GET /v1/companies/search`（简称模糊匹配）；IP/资产/漏洞详情级联端点（`GET /v1/assets/{id}/full` 返回端口+指纹+关联域名+漏洞+单位）；资产 Tab 按类型查询端点。
- **S1**：企业风险/资产/漏洞列的"风险等级/关联企业"需在列表端点返回关联字段（JOIN 或预聚合）。
- **S4**：`tasks.type` 枚举扩展 4 种；任务编排创建端点（批量拆子任务）；`POST /v1/tasks/orchestration`。
- **S4**：智能 C 段后台 job（探测后检查 C 段阈值）。
- **S0/S1**：`export_records` 表 + 导出 router + 批量 zip 端点（替换前端 ExportRecords 内联 mock）。
- **前端**：资产页改多 Tab（含企业信息 Tab）；企业管理详情 Tab；任务新建按类型动态表单 + 编排表单；各 Drawer 详情（IP/漏洞/证书）；导出记录页对接真实 API。

---

## 评审与迭代

- 本路线图为 **v1.4**，附录 A（后端 7 主题）+ 附录 C（前端 4 块）已全部决策完成，需与各负责人（前端/后端/算法/安全/DevOps）评审排期与资源。
- 附录 A 的 7 个主题建议**每次头脑风暴聚焦 1–2 个**，决策结论回填到对应 S 阶段的"交付物"，并更新本文档版本号。附录 C 同理。
- `plan.md` 是 S0 阶段的前端对接收尾子计划，本文档 S0 与其保持一致；S0 编码启动前以 `plan.md` 为准并据本路线图"1.3 契约不一致"补充 PATCH 修复。
