# DSL + Crawler 真实模式实现说明

## 修改概述

本次修改让 DSL + Crawler 模块支持**真实 API 调用**，无需额外业务代码，直接使用现有代码和配置。

## 修改的文件

### 1. 配置文件：`config/engines/engines.yaml`

**添加字段到每个引擎**：

```yaml
engines:
  fofa:
    # ... 原有配置 ...
    # 新增：API 密钥配置
    api_key: ""  # 填写 Fofa API Key
    email: ""    # 填写 Fofa 注册邮箱
    enabled: false  # 是否启用真实 API（false = stub 模式）
    max_results: 100
    request_timeout: 30

  hunter:
    # ... 原有配置 ...
    api_key: ""  # 填写 Hunter API Key
    enabled: false
    max_results: 100
    request_timeout: 30
```

**设计原则**：
- `enabled=false` → 默认 stub 模式，确保安全
- `enabled=true` + `api_key` → 启用真实 API
- 与现有配置保持一致的风格

### 2. 核心代码：`src/intelligence/services/generic_scraper.py`

**修改内容**：

1. 添加 `__init__` 参数支持配置字典传入
2. 添加 `_real_search()` 方法实现真实 API 调用
3. 修改 `scrape()` 方法根据 `enabled` 选择模式
4. 添加 `_extract_results()` 和 `_format_result()` 辅助方法

**关键逻辑**：

```python
def scrape(self, query: str, config: CrawlConfig | None = None) -> list[RawDocument]:
    # 根据配置选择真实 API 或 stub 模式
    use_real_api = self._config.get("enabled", False)
    api_key = self._config.get("api_key", "")

    if use_real_api and api_key:
        return await self._real_search(query, config)
    else:
        return self._stub_response(query, display_name)
```

### 3. 工具代码：`src/core/config_paths.py`

**添加函数**：

```python
def get_engine_specs() -> dict:
    """Get engine specifications from engines.yaml."""
    import yaml

    if not ENGINES_YAML.exists():
        return {}

    with open(ENGINES_YAML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("engines", {})
```

### 4. 测试脚本：`scripts/test_dsl_crawler.py`

**修改内容**：

- 删除之前创建的新业务代码引用
- 使用 `build_scraper_map()` 构建爬虫映射
- 支持从 `engines.yaml` 读取配置

**使用方式**：

```bash
# Stub 模式测试（无需 API Key）
python scripts/test_dsl_crawler.py --preset alibaba

# 真实 API 模式测试
# 方法 1：修改 engines.yaml
vi config/engines/engines.yaml
# 设置 fofa.enabled = true 并填写 api_key

# 方法 2：使用环境变量（可选）
export FOFA_API_KEY="your_key"
export FOFA_EMAIL="your_email"

python scripts/test_dsl_crawler.py --real --preset alibaba
```

## 删除的文件

以下文件已删除，因为它们是冗余的：

- ❌ `src/intelligence/services/scrapers/real_engine_scraper.py` - 不再需要
- ❌ `config/real_test.yaml` - 使用现有的 `engines.yaml`
- ❌ `docs/DSL_CRAWLER_TEST_GUIDE.md` - 已合并到本文档

## 架构对比

### 修改前（新增文件方式）

```
test_dsl_crawler_real.py
    ├── real_engine_scraper.py (新增）
    └── real_test.yaml (新增）

IntelligenceModule (原代码）
    └── GenericEngineScraper (stub only)
```

### 修改后（使用现有代码）

```
test_dsl_crawler.py
    ├── generic_scraper.py (修改后支持 real 模式）
    └── engines.yaml (修改后添加 api_key 配置）
```

## 好处

1. **一致性** - 配置集中在一个文件 `engines.yaml`
2. **兼容性** - 保留 stub 模式作为默认
3. **可维护性** - 修改现有代码而非新增，减少重复
4. **安全性** - 默认禁用真实 API，需显式启用

## 验证步骤

```bash
# 1. 验证配置文件
cat config/engines/engines.yaml | grep "api_key"

# 2. 运行 stub 测试
python scripts/test_dsl_crawler.py --preset example

# 3. 配置 API Key（可选）
# vi config/engines/engines.yaml
# 设置 fofa.api_key = "your_key"

# 4. 运行真实测试
python scripts/test_dsl_crawler.py --real --preset example
```

## 支持的 API 引擎

| 引擎 | API 密钥 | 配置字段 |
|-----|---------|---------|
| Fofa | `api_key`, `email` | `enabled` |
| Hunter | `api_key` | `enabled` |
| 百度 | 无 | - |
| Bing | 无 | - |

新增引擎只需在 `engines.yaml` 中添加配置即可。
