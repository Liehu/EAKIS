# EAKIS 功能逐模块测试指南

## 前置准备

### 1. 启动开发服务
```bash
# 在项目根目录执行
python scripts/run_dev.py
```
服务启动后访问 http://localhost:8000/docs 可看到 Swagger UI。

### 2. 获取认证 Token（所有写操作都需要）
```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -d "username=admin&password=eakis2024"
```
返回的 `access_token` 在后续请求中放到 Header：
```
Authorization: Bearer <access_token>
```

---

## 模块 1：Health — 健康检查

**目标**：确认服务启动正常。

```bash
curl http://localhost:8000/v1/health
```

**预期**：`{"status":"ok","version":"2.0.0"}`

---

## 模块 2：Auth — 认证

| 测试 | 命令 | 预期 |
|------|------|------|
| 正确登录 | `curl -X POST /v1/auth/token -d "username=admin&password=eakis2024"` | 200 + token |
| 错误密码 | `curl -X POST /v1/auth/token -d "username=admin&password=wrong"` | 401 |
| 不存在用户 | `curl -X POST /v1/auth/token -d "username=nobody&password=eakis2024"` | 401 |

---

## 模块 3：Intelligence — 情报采集 (M1)

**保存变量**（后续步骤使用）：
```bash
TASK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "TASK_ID=$TASK_ID"
```

### 3.1 启动情报采集
```bash
curl -X POST http://localhost:8000/v1/tasks/$TASK_ID/intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "测试科技公司",
    "industry": "tech",
    "domains": ["example.com"],
    "keywords": ["API接口", "数据泄露"],
    "enabled_categories": ["news", "security", "asset_engine"]
  }'
```
**预期**：201，返回 `status=completed`，`total_sources>0`

### 3.2 查看采集状态
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/intelligence
```

### 3.3 查看文档列表
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/intelligence/documents
```

### 3.4 查看DSL查询
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/intelligence/dsl
```

### 3.5 查看数据源
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/intelligence/sources
```

### 3.6 RAG语义检索
```bash
curl -X POST http://localhost:8000/v1/intelligence/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "API安全漏洞", "top_k": 5}'
```

### 3.7 RAG健康检查
```bash
curl http://localhost:8000/v1/intelligence/rag/health
```

**验证要点**：
- [ ] 采集能完成（status=completed 或 partial）
- [ ] 返回了数据源（total_sources > 0）
- [ ] DSL查询列表非空（因提供了 keywords）
- [ ] 文档有内容（data 非空或合理）
- [ ] RAG 搜索有返回结果

---

## 模块 4：Assets — 资产发现 (M3)

### 4.1 启动资产发现
```bash
curl -X POST http://localhost:8000/v1/tasks/$TASK_ID/assets/discover \
  -H "Content-Type: application/json" \
  -d '{
    "dsl_queries": [
      {"platform": "fofa", "query": "domain=\"example.com\""},
      {"platform": "hunter", "query": "example.com"}
    ],
    "company_name": "测试科技公司",
    "target_domains": ["example.com"],
    "target_ip_ranges": ["93.184.216.0/24"]
  }'
```
**预期**：201，`total_searched>0`，`total_enriched>0`

### 4.2 查看发现状态
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/assets/status
```

### 4.3 列出资产
```bash
# 全部
curl http://localhost:8000/v1/tasks/$TASK_ID/assets

# 按风险过滤
curl "http://localhost:8000/v1/tasks/$TASK_ID/assets?risk=high"

# 按类型过滤
curl "http://localhost:8000/v1/tasks/$TASK_ID/assets?asset_type=web"
```

### 4.4 查看资产详情（从列表中取一个 id）
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/assets/<ASSET_ID>
```

### 4.5 更新资产
```bash
curl -X PATCH http://localhost:8000/v1/tasks/$TASK_ID/assets/<ASSET_ID> \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true, "risk_level": "high", "notes": "测试确认"}'
```

**验证要点**：
- [ ] 发现完成（status=completed）
- [ ] 返回了资产（total_candidates > 0）
- [ ] 资产列表可过滤、可分页
- [ ] 资产详情含完整字段
- [ ] 更新操作生效

---

## 模块 5：Interfaces — 接口爬取 (M4)

### 5.1 启动接口爬取（用上面发现的资产URL）
```bash
curl -X POST http://localhost:8000/v1/tasks/$TASK_ID/interfaces/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"asset_id": "asset-1", "url": "https://example.com"},
      {"asset_id": "asset-2", "url": "https://api.example.com"}
    ]
  }'
```
**预期**：201，`total_classified>0`

### 5.2 查看爬取状态
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/interfaces/status
```

### 5.3 列出接口
```bash
# 全部
curl http://localhost:8000/v1/tasks/$TASK_ID/interfaces

# 按方法过滤
curl "http://localhost:8000/v1/tasks/$TASK_ID/interfaces?method=POST"

# 按敏感接口过滤
curl "http://localhost:8000/v1/tasks/$TASK_ID/interfaces?privilege_sensitive=true"
```

### 5.4 查看接口详情
```bash
curl http://localhost:8000/v1/tasks/$TASK_ID/interfaces/<INTERFACE_ID>
```

### 5.5 更新接口
```bash
curl -X PATCH http://localhost:8000/v1/tasks/$TASK_ID/interfaces/<INTERFACE_ID> \
  -H "Content-Type: application/json" \
  -d '{"test_priority": 10, "skip_test": false, "notes": "高优先级测试"}'
```

**验证要点**：
- [ ] 爬取完成，分类了接口（total_classified > 0）
- [ ] 接口列表有不同 method/api_type
- [ ] 权限敏感接口被标记
- [ ] 更新操作生效

---

## 模块 6：Inference — 推理服务

### 6.1 健康检查
```bash
curl http://localhost:8000/v1/inference/health
```

### 6.2 模型列表
```bash
curl http://localhost:8000/v1/inference/models
```

### 6.3 文本生成
```bash
curl -X POST http://localhost:8000/v1/inference/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "什么是SQL注入漏洞？请简要说明。"}'
```

### 6.4 Chat对话
```bash
curl -X POST http://localhost:8000/v1/inference/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "列出3种常见的Web安全漏洞"}]}'
```

### 6.5 OpenAI兼容接口
```bash
curl -X POST http://localhost:8000/v1/inference/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "igorls/gemma-4-E4B-it-heretic-GGUF:latest",
    "messages": [{"role": "user", "content": "你好"}],
    "temperature": 0.3,
    "max_tokens": 100
  }'
```

**验证要点**：
- [ ] Ollama 运行中则 health=healthy，否则返回连接错误
- [ ] 有可用模型列表
- [ ] generate/chat 能返回文本
- [ ] OpenAI 兼容格式正确

---

## 模块 7：Keywords — 关键词引擎 (M2)

> **注意**：关键词 API 需要 PostgreSQL 数据库，stub 模式下只能测试 Pydantic 验证。
> 如需完整测试，需先启动 PostgreSQL 并创建数据库。

### 7.1 验证参数校验
```bash
# 错误类型 → 422
curl -X POST http://localhost:8000/v1/tasks/$TASK_ID/keywords \
  -H "Content-Type: application/json" \
  -d '{"word": "测试", "type": "invalid", "weight": 0.5}'
```

---

## 模块 7.5：DSL + Crawler 独立联调测试

> **本模块测试 DSL 查询生成和资产爬虫的独立联调**，支持真实 API 调用。

### 7.5.1 快速验证（Stub 模式）

```bash
# 使用预设目标测试
python scripts/test_dsl_crawler.py --preset example

# 使用真实公司测试
python scripts/test_dsl_crawler.py --preset alibaba

# 自定义目标测试
python scripts/test_dsl_crawler.py \
    --company "腾讯科技" \
    --domains qq.com wechat.com \
    --keywords 腾讯 微信 QQ
```

**预期输出**：
```
生成的 DSL 查询 (2 条):
  [fofa] domain="qq.com" && title="腾讯"
  [hunter] domain.suffix="qq.com" && web.title="腾讯"

爬取完成，共获取 4 条文档
  [Fofa] 2 条
  [奇安信Hunter] 2 条
```

### 7.5.2 真实 API 测试

**配置方式**：

编辑 `config/engines/engines.yaml`，填写 API 密钥并启用：

```yaml
engines:
  fofa:
    api_key: "your_fofa_api_key"
    email: "your_fofo_email"
    enabled: true
```

**运行测试**：

```bash
# Stub 模式（默认，无需 API Key）
python scripts/test_dsl_crawler.py --preset alibaba

# 真实 API 模式
python scripts/test_dsl_crawler.py --real --preset alibaba
```

**详细文档**：参见 [DSL_CRAWLER_REAL_MODE_GUIDE.md](DSL_CRAWLER_REAL_MODE_GUIDE.md)

### 7.5.3 测试结果

结果保存在 `test_results/dsl_crawler_test_*.json`，包含：

- 生成的 DSL 查询（platform, query, valid）
- 爬取的文档（source, content, url）
- 错误信息

### 7.5.4 验证要点

- [ ] DSL 查询使用正确的域名和关键词
- [ ] DSL 语法符合各引擎规范
- [ ] 爬虫返回正确的文档数
- [ ] 真实 API 模式下数据来自实际搜索

**详细文档**：参见 [DSL_CRAWLER_TEST_GUIDE.md](DSL_CRAWLER_TEST_GUIDE.md)

---

## 联调测试：M1 → M3 → M4 全链路

用同一个 TASK_ID 串联全流程：

```bash
# 1. 情报采集 → 得到 DSL 查询
# 2. DSL 查询喂给资产发现 → 得到资产列表
# 3. 资产列表喂给接口爬取 → 得到接口清单
```

### 步骤 1：情报采集 + 提取 DSL
```bash
TASK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# 启动采集
curl -s -X POST http://localhost:8000/v1/tasks/$TASK_ID/intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "联调测试公司",
    "industry": "finance",
    "keywords": ["网上银行", "API网关", "数据接口"],
    "enabled_categories": ["asset_engine", "security"]
  }' | python -m json.tool

# 获取 DSL
curl -s http://localhost:8000/v1/tasks/$TASK_ID/intelligence/dsl | python -m json.tool
```

### 步骤 2：用 DSL 发现资产
```bash
# 用上一步返回的 DSL queries
curl -s -X POST http://localhost:8000/v1/tasks/$TASK_ID/assets/discover \
  -H "Content-Type: application/json" \
  -d '{
    "dsl_queries": <从步骤1的DSL data中复制>,
    "company_name": "联调测试公司",
    "target_domains": ["example.com"]
  }' | python -m json.tool

# 获取资产列表
curl -s http://localhost:8000/v1/tasks/$TASK_ID/assets | python -m json.tool
```

### 步骤 3：爬取资产接口
```bash
# 用上一步返回的资产构建请求
curl -s -X POST http://localhost:8000/v1/tasks/$TASK_ID/interfaces/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "assets": <从步骤2的资产data中构建 [{"asset_id":..., "url":...}]>
  }' | python -m json.tool
```

### 步骤 4：查看最终结果
```bash
# 接口清单
curl -s http://localhost:8000/v1/tasks/$TASK_ID/interfaces | python -m json.tool
```

---

## 推荐测试顺序

### HTTP API 测试（模块 1-7）

1. **Health** → 确认服务正常
2. **Auth** → 拿到 Token
3. **Inference** → 确认 Ollama 是否可用（如未启动不影响其他模块）
4. **Intelligence** → 采集情报，生成 DSL
5. **Assets** → 用 DSL 发现资产
6. **Interfaces** → 爬取资产接口
7. **Keywords** → 需 PostgreSQL
8. **联调** → 全链路串通

### 编排层测试（模块 8）

1. **快速验证** → `python scripts/test_orchestrator_quick.py`
2. **分阶段测试** → `python scripts/test_orchestrator.py --phase intelligence`
3. **完整流程** → `python scripts/test_orchestrator.py`

---

## 模块 8：Orchestrator — LangGraph 编排层测试

> **重要说明**：本模块测试 LangGraph Agent 编排流程，与模块 3 的 Intelligence API 测试是**两套独立实现**。
> - 模块 3 测试的是 `IntelligenceModule` 的**顺序执行**流程
> - 本模块测试的是 `orchestrator/graph.py` 的**有状态图编排**流程

### 8.0 依赖安装

编排层测试需要 LangGraph 相关依赖：

```bash
# 安装编排层依赖
pip install langgraph langchain-core

# 或使用项目依赖安装
pip install -e ".[orchestrator]"
```

### 8.1 架构对比

| 维度 | Intelligence API (模块3) | Orchestrator 编排层 (本模块) |
|-----|------------------------|---------------------------|
| 入口 | `/v1/tasks/{id}/intelligence` | `orchestrator.build_graph()` |
| 执行方式 | 顺序执行 (`await module.run()`) | LangGraph StateGraph |
| 状态管理 | 内存字典 | TypedDict GlobalState + 检查点 |
| Agent 数量 | 4 个 (datasource/dsl/crawler/cleaner) | 14 个（全链路） |
| 反馈回路 | 无 | 支持循环、条件边、人工干预 |

### 8.2 编排层完整流程

LangGraph 定义的 14 个 Agent 节点：

```
datasource → dsl_gen → crawler → summarizer → keyword_gen
    → asset_search → asset_assess → asset_enrich → api_crawler
    → api_static → test_gen → test_exec → vuln_judge → report_gen
```

### 8.3 Python 脚本测试（推荐）

项目提供了两个编排层测试脚本：

#### 快速验证（推荐先执行）

验证编排层核心功能是否正常：

```bash
# 快速验证（约 30 秒）
python scripts/test_orchestrator_quick.py
```

**验证内容**：
- 图构建是否成功
- 14 个节点是否全部注册
- 情报采集阶段能否正常执行
- 状态是否正确传递

#### 完整流程测试

执行完整的编排层流程：

```bash
# 完整测试（包含所有 14 个节点）
python scripts/test_orchestrator.py

# 只测试情报采集阶段
python scripts/test_orchestrator.py --phase intelligence

# 只测试资产发现阶段
python scripts/test_orchestrator.py --phase assets

# 详细输出模式
python scripts/test_orchestrator.py --verbose
```

**阶段划分**：
- `intelligence`: datasource → dsl_gen → crawler → summarizer → keyword_gen
- `assets`: asset_search → asset_assess → asset_enrich
- `interfaces`: api_crawler → api_static
- `pentest`: test_gen → test_exec → vuln_judge
- `report`: report_gen

### 8.4 分阶段验证（逐步执行）

#### 阶段 1：情报采集子流程 (datasource → dsl_gen → crawler)

```python
from src.orchestrator.graph import build_graph

async def test_intelligence_phase():
    graph = build_graph()
    task_id = str(uuid4())

    state: GlobalState = {
        "task_id": task_id,
        "company_name": "测试公司",
        "industry": "tech",
        "domains": ["example.com"],
        "keywords": ["API", "安全"],
        "current_stage": "",
    }

    # 执行到 crawler 后停止
    config = {"configurable": {"thread_id": task_id}}
    async for event in graph.astream(state, config):
        node_name = list(event.keys())[0]
        print(f"执行: {node_name}")
        if node_name == "crawler":
            break
```

#### 阶段 2：摘要与关键词生成 (summarizer → keyword_gen)

```python
# 验证 summarizer 和 keyword_gen 节点
# 这两个节点在 Intelligence API 中不存在，是编排层独有
```

#### 阶段 3：资产发现子流程 (asset_search → asset_assess → asset_enrich)

```python
# 验证资产搜索、评估、富化流程
```

### 8.5 状态检查点测试

LangGraph 支持断点恢复：

```python
from langgraph.checkpoint.memory import MemorySaver

async def test_checkpoint_recovery():
    graph = build_graph()  # 已配置 checkpointer
    task_id = str(uuid4())

    # 第一次执行 - 执行到某个阶段中断
    config = {"configurable": {"thread_id": task_id}}

    # ... 执行流程 ...

    # 从检查点恢复
    state_snapshot = graph.get_state(config)
    print(f"恢复时的阶段: {state_snapshot.next}")
```

### 8.6 条件路由测试

```python
# 测试无资产时的关键词生成反馈回路
from src.orchestrator.router import route_by_asset_count

state_no_assets: GlobalState = {
    "assets": [],
    "current_stage": "asset_search",
}
next_node = route_by_asset_count(state_no_assets)
# 预期: 返回 "keyword_gen"（重新生成关键词）

state_with_assets: GlobalState = {
    "assets": [{"domain": "example.com"}],
    "current_stage": "asset_search",
}
next_node = route_by_asset_count(state_with_assets)
# 预期: 返回 "asset_enrich"（继续流程）
```

### 8.7 验证要点

- [ ] 图构建成功（`build_graph()` 无报错）
- [ ] 14 个节点全部注册
- [ ] 状态在各节点间正确传递
- [ ] `summarizer` 节点生成摘要（Intelligence API 无此功能）
- [ ] `keyword_gen` 节点生成关键词（Intelligence API 无此功能）
- [ ] 检查点可保存和恢复状态
- [ ] 条件路由按预期工作
- [ ] 全链路无阻塞地执行到 `report_gen`

### 8.8 当前限制

1. **API 层未暴露编排端点**：`src/api/main.py` 未注册 orchestrator 路由
2. **需 Python 直接调用**：目前只能通过 Python 脚本测试，无 HTTP API
3. **部分 Agent 为 Stub**：资产发现、接口爬取等后端 Agent 可能返回模拟数据

---

## 测试架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    EAKIS 测试架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HTTP API 测试 (模块 3-7)                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Intelligence API → Assets API → Interfaces API     │   │
│  │  (顺序执行，4 个 Agent)                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                   │
│  LangGraph 编排测试 (模块 8)  ← 本模块新增                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  datasource → dsl_gen → crawler → summarizer → ...  │   │
│  │  (有状态图，14 个 Agent，支持反馈回路)                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 注意事项

- 当前为 **Stub 模式**：所有外部服务（搜索引擎、爬虫、LLM）返回模拟数据
- Stub 模式下数据是预设的，主要验证**流程通畅、API 格式正确、状态管理无误**
- 切换真实模式需修改 `.env` 中的 `INTELLIGENCE_USE_STUBS=false` 等
- Keywords 模块需要 PostgreSQL 数据库才能完整测试
- **编排层测试** 需要完整依赖（Qdrant、Kafka 等）才能运行完整流程
