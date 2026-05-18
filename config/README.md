# EAKIS 配置文件目录

本目录包含所有用户可自定义的配置文件。

## 目录结构

```
config/
├── domain_dicts/          # 领域词库
│   ├── ecommerce.txt      # 电子商务领域关键词
│   ├── finance.txt        # 金融领域关键词
│   ├── government.txt     # 政府机构关键词
│   ├── healthcare.txt     # 医疗健康关键词
│   ├── security.txt       # 网络安全关键词
│   └── tech_stack.txt     # 技术栈关键词
├── engines/               # 搜索引擎规格配置
│   └── engines.yaml       # 引擎 API 规范定义
├── prompts/               # LLM 提示词版本管理
│   ├── asset_assessment_v2.yaml
│   ├── browser_control_v2.yaml
│   ├── keyword_extraction_v2.yaml
│   └── vuln_case_gen_v2.yaml
├── datasources.yaml       # 数据源配置定义
└── crawler.yaml           # CDP 爬虫配置（M1 情报采集）
```

## 配置文件说明

### domain_dicts/

领域词库文件，每行一个关键词或用逗号分隔的多个关键词。

**格式：**
```
keyword1, keyword2, keyword3
another_keyword
```

**自定义：**
- 可添加新的行业词库文件（`.txt` 格式）
- 每个文件的词汇会用于关键词权重计算中的 `DomainScore`

### engines/engines.yaml

搜索引擎 API 规格配置，定义各引擎的：

- `search_url`: 搜索接口 URL
- `auth_type`: 认证方式 (apikey/basic/bearer)
- `fields`: 支持的搜索字段及模板
- `query_encoding`: 查询编码方式 (base64/url/none)
- `operators`: 支持的操作符
- `pagination`: 分页参数
- `rate_limit`: 请求限流

**添加新引擎：**
1. 在 `engines.yaml` 中添加引擎配置
2. 重启服务即可生效

### prompts/

LLM Agent 提示词版本管理。每个 YAML 文件包含：

- `version`: 版本号
- `description`: 提示词描述
- `system_prompt`: 系统提示词
- `user_template`: 用户输入模板
- `parameters`: 参数定义

**自定义提示词：**
1. 复制现有文件并修改版本号
2. 在代码中引用新版本

### datasources.yaml

数据源配置定义，包含各类情报数据源：

- `sourceId`: 数据源唯一标识
- `name`: 数据源显示名称
- `category`: 类别 (NEWS/OFFICIAL/LEGAL/SECURITY)
- `priority`: 优先级 (1-9，越高越优先)
- `expectedYield`: 预期产出率 (0-1)
- `rateLimit`: 请求限流 (请求/秒)

**添加新数据源：**
1. 在 `dataSources` 数组中添加新条目
2. 重启服务或调用 `reload_datasource_catalog()`

### crawler.yaml

CDP 爬虫配置文件，用于 M1 情报采集模块的浏览器自动化爬取。

**配置项：**

- `cdp_mode.enabled`: 是否启用 CDP 爬虫模式（默认：false）
- `cdp_mode.max_pages`: 并发浏览器页面数（默认：5）
- `cdp_mode.timeout`: 单页面超时时间，单位秒（默认：30）
- `cdp_mode.headless`: 是否无头模式运行（默认：true）
- `cdp_mode.launch_args`: 浏览器启动参数列表

**搜索引擎 CDP 配置：**

支持普通搜索引擎（百度/Bing/Google）的浏览器访问模式：
- `search_url`: 搜索接口 URL
- `query_param`: 查询参数名
- `result_selector`: 结果容器选择器
- `title_selector`: 标题选择器
- `link_selector`: 链接选择器
- `snippet_selector`: 摘要选择器

**反爬对抗策略：**

- `anti_crawl.delay_range`: 请求间隔范围，单位秒（默认：[1.5, 4.0]）
- `anti_crawl.retry_attempts`: 重试次数（默认：3）
- `anti_crawl.retry_backoff`: 重试退避系数（默认：2.0）
- `anti_crawl.random_wait`: 是否启用随机等待（默认：true）

**降级策略：**

- `fallback.on_failure`: CDP 失败时是否降级到 httpx API 调用（默认：true）
- `fallback.failure_types`: 触发降级的错误类型列表
- `fallback.max_fallback_attempts`: 最大降级次数（默认：2）

**使用方式：**

```python
from src.intelligence.agents.crawler import CrawlerAgent

# 启用 CDP 模式
crawler = CrawlerAgent(cdp_mode=True)

# 或通过配置文件控制（设置 crawler.yaml 中 cdp_mode.enabled = true）
crawler = CrawlerAgent()
```

## 配置引用

在代码中通过 `src.core.config_paths` 模块引用配置文件：

```python
from src.core.config_paths import (
    DOMAIN_DICTS_DIR,
    ENGINES_YAML,
    PROMPTS_DIR,
    CRAWLER_YAML,
    get_domain_dict_path,
    get_prompt_path,
)
```
