# EAKIS 后续开发计划（新会话交接文档）

> **目的**：本文档为下一个会话提供完整的项目上下文，避免重新扫描代码库。
> **创建时间**：2026-06-23
> **关联文档**：`docs/ROADMAP.md`（战略路线图 v1.4）、`docs/extract/14_功能开发进度表.md`

---

## 一、项目快速认知（必读）

### 1.1 这是什么项目
**EAKIS（安鉴·天穹）** — AI 赋能攻击面探测系统。核心流程：
```
企业信息挖掘 → 资产发现(IP/域名/证书/APP/小程序) → 接口爬取 → 漏洞测试 → 报告生成
```
后端 FastAPI + LangGraph，前端 React 18 + TypeScript + Ant Design 暗色主题。

### 1.2 技术栈
- **后端**：Python 3.13 + FastAPI + SQLAlchemy(async) + PostgreSQL(生产) / SQLite(开发)
- **前端**：React 18 + TypeScript + Vite 5 + Ant Design 5 + Zustand + MSW(mock) + ECharts
- **AI/工具**：LangGraph 编排 + OpenAI/Ollama LLM + ProjectDiscovery 工具链(subfinder/dnsx/httpx/naabu/nmap/nuclei)
- **虚拟环境**：`venv/`（Python），前端在 `web/`

### 1.3 开发环境启动
```bash
# 后端 (默认 sqlite, 端口 8000)
source venv/bin/activate
python scripts/run_dev.py  # 或: PYTHONPATH=. venv/bin/uvicorn src.api.main:app --reload

# 前端 (端口 5173, mock 模式)
cd web && npm run dev

# 联调模式 (前端调真实后端)
# 修改 web/.env.development: VITE_API_MOCK=false, VITE_API_BASE_URL=http://localhost:8000
cd web && npm run dev

# 数据初始化 (按顺序执行)
python scripts/seed_rbac.py          # RBAC (角色/权限/组织/管理员)
python scripts/seed_mock_data.py     # 任务/资产/漏洞/报告样例
python scripts/seed_companies.py     # 企业回填 (从 Task.company_name)
python scripts/seed_companies.py     # 再跑一次 (修复 task 关联)
python scripts/seed_knowledge.py     # 知识库 (漏洞/指纹/字典/数据源/手册)
python scripts/seed_templates.py     # 模板 (4类: 任务/报告/Prompt/攻击路径)
```

### 1.4 测试账号
```
username: admin              password: eakis2024    (super_admin, dev 硬编码)
username: admin@eakis.local  password: eakis2024    (super_admin, DB 真实账号)
username: analyst            password: eakis2024    (analyst, dev 硬编码)
```
- 登录走 `POST /v1/auth/token`，**form-urlencoded**（非 JSON）
- `auth.py` 的 `_authenticate_db_user()` 优先查 DB，DB 查不到 fallback 到 `_DEV_USERS`

### 1.5 关键文件索引

| 文件 | 用途 |
|------|------|
| `docs/ROADMAP.md` | **战略路线图 v1.4**（S0-S7 阶段 + 附录 A 头脑风暴 7 主题 + 附录 C 前端 UI 4 块决策） |
| `docs/extract/14_功能开发进度表.md` | 已完成功能清单（含 2026-06 新增的 S0-S4+S2 章节） |
| `docs/extract/01_02_项目概述与系统架构设计.md` | 原始设计文档（10 章 + API 规范 + 数据模型） |
| `docs/前端原型.html` | 原型图（粗略草图） |
| `plan.md` | S0 前端对接收尾子计划（已过时，被 ROADMAP S0 取代） |
| `config/` | 用户可自定义配置：`domain_dicts/`(行业词库) + `engines/`(引擎规格) + `prompts/`(LLM Prompt 种子) |

---

## 二、当前系统规模与状态

### 2.1 后端
- **16 个 router 文件** → **125 个 API 端点**
- **36 张数据库表**（含 S1/S3/S4/S5 新增的 16 张）
- **业务模块**：`asset_discovery/` `intelligence/` `api_crawler/` `keywords/` `reporting/` `tools/` `inference/` `orchestrator/`

#### 后端 router 清单（全部已在 main.py 注册）
```
assets       — 资产管理 (task维度的旧端点 + 全局/v1/assets 新端点 + /assets/{id}/full)
audit_logs   — 审计日志 (RBAC)
companies    — 企业管理 (CRUD + 关系 + 级联查询 + 图 + 风险 + 搜索) [13 端点]
inference    — Ollama 本地推理
intelligence — 情报采集 (M1)
interfaces   — 接口爬取 (M4)
keywords     — 关键词引擎 (M2)
knowledge    — 知识库 (漏洞库/Payloads/指纹/数据源/手册) [26 端点]
reports      — 报告生成 (M6, 真实生成) [3 端点]
tasks        — 任务管理
teams        — 团队管理 (RBAC)
templates    — 模板管理 (4类: task/report/prompt/attack_path) [6 端点]
tools        — 工具执行器 (subfinder/dnsx/httpx/naabu/nmap/cert/nuclei) [6 端点]
users        — 用户管理 (RBAC)
vulnerabilities — 漏洞管理
auth         — 认证 (JWT + DB优先验证 + dev fallback)
```

#### 数据库表清单（36 张）
```
organizations, users, user_refresh_tokens, roles, permissions, role_permissions,
teams, team_members, audit_logs,                          # RBAC
tasks, keywords, assets, asset_enrichments,               # M2/M3 核心
asset_ips, asset_domains, asset_certificates,             # S1 资产多表
asset_miniprograms, asset_apps,                           # S1 资产多表
asset_history, asset_tags, risk_history,                  # S1 元数据
interfaces, vulnerabilities, intel_documents,             # M4/M5/M1
reports, agent_logs,                                      # M6/日志
companies, company_relations,                             # S1 企业关系
vuln_knowledge, fingerprints, payloads,                   # S3 知识库
knowledge_datasources, knowledge_handbooks, knowledge_tags,# S3 知识库
templates,                                                # S4 模板
tool_executions,                                          # S5 工具执行记录
```

### 2.2 前端
- **30+ 页面组件**，全部 build 通过
- **MSW mock 覆盖**：所有端点（dev 模式可用，无需后端）

#### 前端页面状态
| 页面 | 路由 | 状态 |
|------|------|------|
| Dashboard 总览 | `/` | ✅ |
| 企业管理 | `/companies` | ✅ 重构完成（列表+批量操作+详情Tab） |
| 企业详情 | `/companies/{id}` | ✅ (Drawer, 5 Tab: 信息/下属/资产/风险/情报) |
| 资产管理 | `/assets` | ✅ 重构完成（6类Tab: IP/域名/Web/APP/小程序/证书） |
| 漏洞管理 | `/vulnerabilities` | ✅ 重构完成（query筛选+批量+详情） |
| 工具管理 | `/tools` | ✅ 新建（工具卡片+在线执行+历史） |
| 报告管理 | `/reports` | ✅ 重构完成（生成+内容查看+下载） |
| 知识库 ×5 | `/knowledge/*` | ✅ (漏洞库/Payloads/指纹/数据源/手册) |
| 模板管理 ×4 | `/templates/*` | ✅ (任务/报告/Prompt/攻击路径+DAG) |
| RBAC ×3 | `/admin/*` | ✅ (用户/团队/审计日志) |
| Agent管理 | `/agent-management` | ✅ |
| 任务管理 | `/tasks` | ✅ |
| 导出记录 | `/tasks/export` | ⚠️ 纯内联 mock |
| 系统设置 | `/settings` | ⚠️ 部分（搜索网站/关键词模板/并发 tab 内联 mock） |
| 扫描任务 | `/tasks/scan` | ❌ PlaceholderPage |
| 导入任务 | `/tasks/import` | ❌ PlaceholderPage |
| 演练任务 | `/tasks/drill` | ❌ PlaceholderPage |
| 自动渗透 | `/pentest` | ❌ PlaceholderPage |

#### 前端 API 模块状态
```
✅ 已对齐后端: auth, tasks, companies, assets, vulnerabilities, keywords,
              interfaces, reports, knowledge, templates, tools,
              users, teams, auditLogs, system(health)
❌ 纯 stub (调不存在的后端): providers, webhooks, orchestrations, pentest, osint(部分)
⚠️ system.ts 的 getMetrics/getAgentConfigs 调的端点后端不存在
```

### 2.3 工具执行器（S5 框架）
- **7 个工具注册**：subfinder / dnsx / httpx / naabu / nmap / cert(crt.sh) / nuclei(disabled)
- **防 RCE**：subprocess 数组调用(无 shell) + 输入白名单校验(domain/ip/url 正则) + flag 白名单
- **Agent 集成**：`ToolBackedSearchClient`（`src/asset_discovery/services/tool_client.py`）已接入 AssetDiscoveryModule
- **当前状态**：`settings.asset_discovery_use_stubs = True`（走 stub），改为 `False` 后自动走真实工具
- **依赖**：服务器需安装 subfinder/dnsx/httpx 二进制（`go install` 或下载 release）

---

## 三、已完成阶段（S0-S5 框架）

| 阶段 | 状态 | 完成内容 |
|------|------|---------|
| **S0 对接收尾** | ✅ | RBAC 3页 + 契约修复(PATCH) + MSW参数化 + Dashboard WebSocket + 孤儿清理 |
| **S1 数据贯通** | ✅ | Company实体 + 资产拆6表 + 风险计算 + companies router(13端点) + 前端去mock |
| **S2 报告生成** | ✅ | 聚合器 + 渲染器(Jinja2+LLM可选) + 质量评分 + reports router真实生成 |
| **S3 知识库** | ✅ | 6表(漏洞库/Payloads/指纹/数据源/手册/标签) + 26端点 + 审核状态机 + 5前端页 |
| **S4 模板** | ✅ | 统一表+type+JSON + 继承合并 + 6端点 + 4类前端页(Tab+DAG) |
| **S5 工具框架** | ✅ | ToolExecutor(防RCE) + 7工具注册 + tool_executions表 + tools router(6端点) + 前端页 + Agent集成 |

---

## 四、未完成任务与后续计划

### 4.1 P0 — 立即需要修复的问题

#### 4.1.1 前端调不存在的后端端点（mock-off 会崩）
| 前端模块 | 缺失的后端 | 影响 |
|----------|-----------|------|
| `providers.ts` (7函数) | `/config/providers/*` router | Settings AI Provider Tab |
| `webhooks.ts` (5函数) | `/config/webhooks/*` router | Settings Webhook Tab |
| `system.ts` getMetrics/getAgentConfigs | `/metrics`, `/config/agents` | Settings/AgentManagement/Status |
| `osint.ts` getCompanyOsint | `/companies/{id}/osint` | Companies/Detail OSINT Tab |
| `assets.ts` exportAssets | `/tasks/{id}/assets/export` | 资产导出 |
| `reports.ts` downloadReport | `/reports/{id}/download` | 报告下载(现走content blob降级) |

**处理建议**：补后端 router（config/ 用于 Settings；其余补子端点），或前端改用已有端点。

#### 4.1.2 Stub 模式未关闭
`settings.py` 四个 `use_stubs = True`：
```python
intelligence_use_stubs = True      # 情报采集跑假数据
crawler_use_stubs = True           # 爬虫跑假数据
asset_discovery_use_stubs = True   # 资产发现跑假数据 (改为 False 自动走 ToolBackedSearchClient)
rag_use_stubs = True               # RAG 用内存版 (生产改 Qdrant)
```
**注意**：`asset_discovery_use_stubs` 改 False 后，需服务器安装 subfinder/dnsx/httpx。

### 4.2 P1 — 核心业务流程缺口（对照用户 5 步流程）

用户的核心流程：
```
1. 输入企业名 → 挖掘企业信息 + 控股子单位
2. 五路资产挖掘: (1)证书 (2)域名(dnsx/dnsdb) (3)IP(端口/C段/指纹) (4)关键词OSINT (5)空间搜索引擎反查
3. 去重降噪: CDN判断 + ip:port+页面相似度去重 + 情报去重
4. 资产关联验证
5. AI渗透(暂不做)
```

#### 缺口明细
| 缺失功能 | 影响 | 对应步骤 |
|----------|------|---------|
| **企业工商信息真实采集**（天眼查/爱企查 API / ICP 反查） | 第 1 步 Company 字段无人填 | 1 |
| **证书挖掘链路**（CT 日志 crt.sh → 同证书关联域名） | cert 工具已注册但 crt.sh API 调用逻辑需完善 | 2(1) |
| **DNS 挖掘链路**（dnsx 子域枚举 + DNS 解析 + dnsdb 历史） | dnsx 工具已注册，Agent 已集成，但 dnsdb 历史解析未实现 | 2(2) |
| **端口扫描真实化**（naabu/nmap 真实调用 → enricher 接真实结果） | enricher 的 _scan_ports 是 stub | 2(3) |
| **智能 C 段扫描**（≥4 个同 C 段 IP → 自动加 C 段到探测任务） | 模型字段 `smart_c_segment` 存在，逻辑未实现（C.3 决策） | 2(3) |
| **关键词 OSINT 真实爬虫**（news/bidding/wechat scraper 换真实源 + 网盘/源码泄露/账密） | 4 个 scraper 全是 StubScraper 返回硬编码假数据 | 2(4) |
| **空间搜索引擎真实调用**（Fofa/Shodan API Key 配置 + generic_scracer 发真实请求） | 框架就绪但 stub | 2(5) |
| **CDN IP 判断**（CDN IP 段库 / CNAME 判断） | 模型有 `is_cdn` 字段但无人填 | 3 |
| **页面相似度去重**（HTML hash / 指纹对比） | 三元组去重在，页面相似度无实现 | 3 |
| **智能资产关联**（扫描资产 → 自动匹配企业） | `smart_asset_link` 字段存在，逻辑未实现 | 4 |

### 4.3 P2 — 前端功能补全

| 缺失 | 说明 |
|------|------|
| 任务管理重构（扫描/导入/演练） | `/tasks/scan` `/tasks/import` `/tasks/drill` 是 PlaceholderPage；按 C.3 决策实现（任务模板 + 类型分输入框 + 编排） |
| ExportRecords 接真实 API | `pages/ExportRecords/index.tsx` 用内联 mock |
| Settings 三 Tab 去内联 mock | 搜索网站/关键词模板/并发设置 tab 用硬编码数组 |
| 企业简称智能匹配前端交互 | C.3 决策的"输入简称 → 模糊匹配 → 确认"未接入任务创建 |
| 企业详情关联图谱可视化 | 详情页有"关联图谱功能开发中..."占位 |

### 4.4 P3 — 长期路线图（S6-S7）

| 阶段 | 内容 |
|------|------|
| **S5 完整** | 自动渗透测试：Payload 库 + 测试执行引擎 + 插件集(SQLi/越权/IDOR/XSS/SSRF) + LLM-as-Judge + BoundaryGuard 授权边界 |
| **S6 端到端** | LangGraph 全流程串联 + WebSocket 事件流 + 5 个真实项目验证 + 性能优化 |
| **S7 运维** | Docker Compose + K8s + CI/CD + 完整文档 |

---

## 五、关键架构决策（头脑风暴结论摘要）

> 详见 `docs/ROADMAP.md` 附录 A（7 主题）+ 附录 C（前端 4 块），均为已决策。

### A.1 企业关系穿透
- 多源融合（商业 API + ICP 反查 + OSINT）| 关系表 PG（parent_id + company_relations）| 可配置穿透（默认 3 层 + ≥51%）| 自动继承+可关 | 沿用 RBAC | ECharts graph

### A.4 资产管理
- 三元组去重（ip+port+domain）| 三态+自动归档（discovered→confirmed→archived, N=3）| 多维加权价值评分 | 字段级变更 diff

### A.7 风险评估
- **漏洞加权求和**（`risk = Σ(cvss × severity_weight)`，不依赖资产价值）| 企业风险总览+趋势 | v1 不接外部威胁情报

### A.2 知识库
- DB 元数据 + MinIO 内容 | 仅 nuclei 自动同步 | 提交+审核流（draft→pending_review→published→deprecated）| 按标签过滤

### A.6 模板
- 统一表+type+JSON | 4 类（task/report/prompt/attack_path）均支持继承 | 三级可见域（org/team/private）| Prompt DB 为主+文件种子

### C.3 任务管理（前端构想）
- 4 种任务类型 type 区分（enterprise_penetration/asset_detection/risk_assessment/orchestration）| 编排三层级联子任务 | 智能 C 段后台自动拆 | 企业简称后端模糊匹配 | 导出 MinIO+动态 zip

### C.2 资产页
- 6 类 Tab（IP/域名/Web/APP/小程序/证书）| 工商只读+业务可编辑 | 员工工号规则→生成账号字典

---

## 六、已知 Bug / 待修复（非阻塞）

| 问题 | 文件 | 说明 |
|------|------|------|
| `/auth/me` 返回 404 | `src/api/auth.py` | `/auth/me` 端点未注册（不影响登录，影响前端获取当前用户信息） |
| `seed_companies.py` 需跑两次 | `scripts/seed_companies.py` | 第一次创建 Company（task.company_id 未立即可见），第二次才关联 task+assets |
| `seed_mock_data.py` 列不匹配 | `scripts/seed_mock_data.py` | 新增的 company_id/status 等列导致旧 seed 的 INSERT 报错（RBAC seed 正常，mock_data 部分失败） |
| Alembic 迁移为空 | `migrations/versions/` | 生产部署前需补迁移脚本（当前用 create_all 建表） |
| 旧前端 API stub 残留 | `web/src/api/{orchestrations,pentest}.ts` | 演练/渗透已删页面，API stub 文件残留（无害但应清理） |
| settings 模块 src/pages | `src/pages/` | 后端有个空的 `src/pages/` 目录（与前端无关） |

---

## 七、新会话快速上手建议

1. **先读本文档** → 了解全局
2. **读 `docs/ROADMAP.md`** → 了解 S0-S7 阶段和头脑风暴决策
3. **如果要继续 S5（渗透测试）** → 读 `src/tools/`（执行器框架）+ `src/asset_discovery/`（Agent 编排）+ ROADMAP A.5（漏洞管理决策）
4. **如果要补业务流程** → 读本文档「四、未完成任务」的 P1 缺口表 + 用户 5 步流程
5. **如果要修前端** → `cd web && npm run dev`（mock 模式）或联调真实后端

### 验证当前系统可用的命令
```bash
# 后端导入检查
venv/bin/python -c "from src.api.main import app; print(len([r for r in app.routes if hasattr(r,'path')]), 'routes')"

# 前端构建检查
cd web && npm run build

# 真实 API 联调（需先 seed 数据）
PYTHONPATH=. venv/bin/uvicorn src.api.main:app --port 8000
curl -X POST http://localhost:8000/v1/auth/token -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin&password=eakis2024&grant_type=password"
```
