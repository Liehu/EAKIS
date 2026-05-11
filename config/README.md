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
└── prompts/               # LLM 提示词版本管理
    ├── asset_assessment_v2.yaml
    ├── browser_control_v2.yaml
    ├── keyword_extraction_v2.yaml
    └── vuln_case_gen_v2.yaml
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

## 配置引用

在代码中通过 `src.core.config_paths` 模块引用配置文件：

```python
from src.core.config_paths import (
    DOMAIN_DICTS_DIR,
    ENGINES_YAML,
    PROMPTS_DIR,
    get_domain_dict_path,
    get_prompt_path,
)
```
