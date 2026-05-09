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

1. **Health** → 确认服务正常
2. **Auth** → 拿到 Token
3. **Inference** → 确认 Ollama 是否可用（如未启动不影响其他模块）
4. **Intelligence** → 采集情报，生成 DSL
5. **Assets** → 用 DSL 发现资产
6. **Interfaces** → 爬取资产接口
7. **Keywords** → 需 PostgreSQL
8. **联调** → 全链路串通

## 注意事项

- 当前为 **Stub 模式**：所有外部服务（搜索引擎、爬虫、LLM）返回模拟数据
- Stub 模式下数据是预设的，主要验证**流程通畅、API 格式正确、状态管理无误**
- 切换真实模式需修改 `.env` 中的 `INTELLIGENCE_USE_STUBS=false` 等
- Keywords 模块需要 PostgreSQL 数据库才能完整测试
