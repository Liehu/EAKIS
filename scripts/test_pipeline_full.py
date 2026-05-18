#!/usr/bin/env python3
"""情报采集全链路联调测试 v2.

基于 keyword_extraction_v2.yaml 提示词，对搜索结果进行结构化关键词提取与扩展。

搜索主关键词: "福建联通" ("打造"|"发布"|"招标") ("系统"|"平台")

流水线:
  0. 关键词扩展 — 按提示词模板生成搜索词组合
  1. 搜索结果输入 (标题 + URL + snippet)
  2. 标题相似度去重 (≥90% 视为转载)
  3. 仅爬取去重后的唯一 URL
  4. CleanerAgent 质量评分 + SHA256 内容去重
  5. keyword_extraction_v2 结构化关键词提取
  6. SummarizerAgent LLM 摘要

输出: JSON 格式结果

运行:
    python3 scripts/test_pipeline_full.py                          # 使用内置模拟数据
    python3 scripts/test_pipeline_full.py --no-extract             # 跳过实际爬取
    python3 scripts/test_pipeline_full.py --input test_results/xxx.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")

from src.intelligence.agents.cleaner import CleanerAgent
from src.intelligence.agents.content_extractor import ContentExtractorAgent
from src.intelligence.config import CleanConfig, ExtractionConfig
from src.intelligence.models import CleanedDocument, RawDocument, SourceCategory
from src.intelligence.services.llm_client import StubLLMClient
from src.intelligence.services.rag_client import InMemoryRAGClient
from src.intelligence.services.title_dedup import TitleDeduplicator, title_similarity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("pipeline-v2")

# ---------------------------------------------------------------------------
# keyword_extraction_v2.yaml 提示词模板
# ---------------------------------------------------------------------------

_V2_SYSTEM_PROMPT = """你是网络安全情报分析专家，专精从开源情报中提取攻击面探测关键词。

任务：分析输入的企业情报文本，提取三类关键词。

【分类定义】
- business_keywords：主营业务/产品名称/服务类型/行业标签
- tech_keywords：技术框架/数据库/中间件/协议/部署工具
- entity_keywords：子公司/合作伙伴/投资方/供应商名称

【输出规则 - 严格执行】
1. 只输出合法 JSON，不允许任何多余文字或代码块标记
2. 每类最多 20 个关键词，按 confidence 降序排列
3. 每个关键词必须附 confidence(0.0~1.0) 和 source_idx（来源句子索引）
4. 过滤通用词：公司/系统/平台/管理/服务/技术（confidence < 0.3 的不输出）
5. 关键词长度：2~15 个汉字 或 2~30 个英文字符"""

_V2_USER_TEMPLATE = """情报来源类型: {source_type}
靶标企业: {company_name}
情报文本:
{text_content}

请严格按照系统提示的格式输出 JSON，不要添加任何解释文字："""

# ---------------------------------------------------------------------------
# 模拟搜索结果 — 按 "福建联通" + ("打造"/"发布"/"招标") + ("系统"/"平台") 生成
# ---------------------------------------------------------------------------

STUB_SEARCH_RESULTS = [
    {
        "title": "福建联通两大智·云数据中心启用 以更精的网络打造坚实底座",
        "url": "https://fjca.miit.gov.cn/xwdt/xydt/art/2025/art_b8a7742d0f824d04849852c4fd199e00.html",
        "snippet": "福建联通今日宣布，两大智·云数据中心正式启用。新数据中心采用微服务架构和Kubernetes容器编排，基于Spring Boot框架构建核心业务系统，使用Redis缓存和PostgreSQL数据库，打造坚实的数字化底座。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通两大智·云数据中心启用 以更精的网络打造坚实底座",
        "url": "http://iot.china.com.cn/content/2023-09/12/content_42517212.html",
        "snippet": "福建联通今日宣布，两大智·云数据中心正式启用，以更精的网络打造坚实底座。新系统采用Docker容器化部署。",
        "source_engine": "必应搜索",
    },
    {
        "title": "福建联通打造工业互联网平台 接入企业超3000家",
        "url": "https://www.thepaper.cn/newsDetail_forward_9503975",
        "snippet": "福建联通工业互联网平台已接入企业超过3000家，采用Spring Boot微服务框架，基于Docker容器化部署，使用Nginx作为反向代理网关，打造福建工业互联网第一品牌。",
        "source_engine": "必应搜索",
    },
    {
        "title": "福建联通发布数字化转型白皮书 涉及AI与大数据平台",
        "url": "https://fj.sina.cn/news/2025-04-21/detail-inetxncu5046871.d.html",
        "snippet": "白皮书详细阐述了福建联通在人工智能、大数据分析平台、Nginx负载均衡等方面的技术积累。福建联通联合华为技术有限公司共同打造智能运维系统。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通携手华为建设5G+工业互联网标杆平台",
        "url": "https://fj.sina.cn/news/2025-02-26/detail-inemuvpm8940850.d.html",
        "snippet": "福建联通与华为技术有限公司合作，在福建省内开展5G+工业互联网创新应用，建设智能边缘计算平台，采用gRPC协议通信。",
        "source_engine": "必应搜索",
    },
    {
        "title": "中国联通福建省分公司网络安全态势感知平台招标公告",
        "url": "https://example.com/bid-security-platform",
        "snippet": "项目预算500万元，要求支持Nginx反向代理、Redis缓存、PostgreSQL数据库。投标方须具备网络安全等级保护三级认证。",
        "source_engine": "百度搜索",
    },
    {
        "title": "福建联通发布5G消息系统 助力政企数字化转型",
        "url": "https://example.com/fj-unicom-5g-msg",
        "snippet": "福建联通正式发布5G消息系统，该系统基于RESTful API架构，采用GraphQL查询引擎，支持CI/CD自动化部署流水线，结合DevOps理念建设运维体系。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通打造低空经济服务平台 探索5G+无人机创新",
        "url": "http://www.fj.xinhuanet.com/20250531/8b78d1bf6f6d45e0ae3e403886fcb77b/c.html",
        "snippet": "福建联通积极探索低空经济领域，结合5G网络优势和物联网平台打造新型基础设施。平台使用Vue.js前端框架，Python后端服务，Redis消息队列。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通物联网管理系统升级发布 支持百万级设备接入",
        "url": "https://example.com/fj-unicom-iot-mgmt",
        "snippet": "升级后的物联网管理系统支持MQTT协议和CoAP协议，基于Go语言开发微服务网关，使用MySQL集群存储设备数据，Kubernetes容器编排管理。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通智慧城市综合管理平台招标 覆盖九地市",
        "url": "https://example.com/bid-smart-city",
        "snippet": "项目要求构建统一数据中台，集成Nginx、Redis、PostgreSQL技术栈。投标方需具备智慧城市建设经验，与中国联通福建省分公司签订合同。",
        "source_engine": "百度搜索",
    },
    {
        "title": "福建联通联合中兴通讯打造算力调度平台",
        "url": "https://example.com/fj-unicom-zte-computing",
        "snippet": "福建联通与中兴通讯股份有限公司合作，打造算力调度平台。平台采用容器化Docker+Kubernetes架构，API网关使用Java开发，数据库选用PostgreSQL。",
        "source_engine": "百度新闻",
    },
    {
        "title": "福建联通安全运营中心系统发布 筑牢网络安全防线",
        "url": "https://example.com/fj-unicom-soc",
        "snippet": "新发布的安全运营中心系统集成了SWIFT跨境支付监控能力，结合Rust语言开发的高性能分析引擎，并与国家互联网应急中心合作建立威胁情报共享机制。",
        "source_engine": "百度新闻",
    },
]


def expand_search_keywords(company: str) -> list[str]:
    """按 ('打造'|'发布'|'招标') × ('系统'|'平台') 组合搜索关键词。"""
    verbs = ["打造", "发布", "招标"]
    nouns = ["系统", "平台"]
    combinations = []
    for v in verbs:
        for n in nouns:
            combinations.append(f'"{company}" "{v}" "{n}"')
    return combinations


def _results_to_raw_docs(results: list[dict[str, str]]) -> list[RawDocument]:
    return [
        RawDocument(
            content=f"标题: {r['title']}\n链接: {r['url']}\n摘要: {r.get('snippet', '')}",
            source_type=SourceCategory.NEWS,
            source_name=r.get("source_engine", "unknown"),
            source_url=r["url"],
            metadata={"original_title": r["title"]},
        )
        for r in results
    ]


# ===================================================================
# Pipeline steps
# ===================================================================

async def step_title_dedup(
    docs: list[RawDocument], threshold: float = 0.9,
) -> tuple[dict[str, Any], list[RawDocument]]:
    deduper = TitleDeduplicator(threshold=threshold)
    unique: list[RawDocument] = []
    duplicates: list[dict[str, Any]] = []

    for doc in docs:
        title = doc.metadata.get("original_title", "")
        if deduper.is_duplicate(title):
            matched = ""
            for seen in deduper._titles:
                if title_similarity(title, seen) >= threshold:
                    matched = seen
                    break
            duplicates.append({"title": title, "url": doc.source_url, "similar_to": matched})
        else:
            deduper.add(title)
            unique.append(doc)

    all_titles = [d.metadata.get("original_title", "") for d in docs]
    similarity_matrix = []
    for i in range(len(all_titles)):
        for j in range(i + 1, len(all_titles)):
            sim = title_similarity(all_titles[i], all_titles[j])
            if sim >= 0.5:
                similarity_matrix.append({
                    "title_a": all_titles[i][:50], "title_b": all_titles[j][:50],
                    "similarity": round(sim, 4), "is_duplicate": sim >= threshold,
                })

    result = {
        "input_count": len(docs), "unique_count": len(unique),
        "duplicate_count": len(duplicates), "threshold": threshold,
        "duplicates_removed": duplicates, "similarity_matrix": similarity_matrix,
    }
    return result, unique


async def step_extract(
    unique_docs: list[RawDocument], config: ExtractionConfig,
) -> tuple[dict[str, Any], list[RawDocument]]:
    agent = ContentExtractorAgent(cdp_enabled=False)
    start = time.monotonic()
    result_docs = await agent.extract(unique_docs, config)
    elapsed = time.monotonic() - start

    enriched = [
        {"url": d.source_url, "title": d.metadata.get("original_title", d.source_name),
         "extraction_method": d.metadata.get("extraction_method", "snippet"),
         "word_count": d.metadata.get("extraction_word_count", len(d.content)),
         "content_preview": d.content[:150].replace("\n", " ")}
        for d in result_docs if "extraction_method" in d.metadata
    ]
    passthrough = [
        {"url": d.source_url, "title": d.metadata.get("original_title", d.source_name),
         "reason": "extraction_failed", "content_preview": d.content[:100].replace("\n", " ")}
        for d in result_docs if "extraction_method" not in d.metadata and d.source_url
    ]
    await agent.cleanup()
    info = {
        "elapsed_ms": round(elapsed * 1000), "enriched_count": len(enriched),
        "passthrough_count": len(passthrough), "enriched": enriched, "passthrough": passthrough,
    }
    return info, result_docs


async def step_clean(
    docs: list[RawDocument], config: CleanConfig,
) -> tuple[dict[str, Any], list[CleanedDocument]]:
    rag_client = InMemoryRAGClient()
    cleaner = CleanerAgent(rag_client)
    start = time.monotonic()
    cleaned = await cleaner.clean(docs, task_id="pipeline-v2", config=config)
    elapsed = time.monotonic() - start

    cleaned_output = [
        {
            "source_name": d.source_name, "source_url": d.source_url,
            "quality_score": d.quality_score,
            "checksum": d.checksum[:16] + "...", "entities": d.entities,
            "content_length": len(d.content),
            "content_preview": d.content[:200].replace("\n", " "),
        }
        for d in cleaned
    ]
    info = {
        "elapsed_ms": round(elapsed * 1000), "input_count": len(docs),
        "output_count": len(cleaned),
        "avg_quality": round(sum(d.quality_score for d in cleaned) / len(cleaned), 4) if cleaned else 0.0,
        "documents": cleaned_output,
    }
    return info, cleaned


async def step_keyword_extraction_v2(
    cleaned_docs: list[CleanedDocument],
    company_name: str,
    source_type: str = "新闻搜索",
) -> dict[str, Any]:
    """Step 5: 使用 keyword_extraction_v2.yaml 提示词提取结构化关键词。

    严格遵循提示词格式：
    - business_keywords / tech_keywords / entity_keywords
    - 每条含 word, confidence(0.0~1.0), source_idx
    - 过滤通用词，按 confidence 降序
    """
    llm = StubLLMClient()
    # 拼接情报文本（每条文档为一个句子，索引对应 source_idx）
    sentences: list[str] = []
    for idx, doc in enumerate(cleaned_docs):
        sentences.append(doc.content)

    text_content = "\n".join(f"[{i}] {s}" for i, s in enumerate(sentences))
    user_prompt = _V2_USER_TEMPLATE.format(
        source_type=source_type,
        company_name=company_name,
        text_content=text_content,
    )

    start = time.monotonic()
    raw_response = await llm.generate(_V2_SYSTEM_PROMPT + "\n" + user_prompt)
    elapsed = time.monotonic() - start

    # 解析 JSON — LLM 可能返回 ```json ... ``` 包裹
    json_str = raw_response.strip()
    md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_str)
    if md_match:
        json_str = md_match.group(1).strip()

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试提取第一个 { ... } 块
        brace_match = re.search(r"\{[\s\S]*\}", json_str)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group())
            except json.JSONDecodeError:
                parsed = {"business_keywords": [], "tech_keywords": [], "entity_keywords": [], "_raw": raw_response[:500]}
        else:
            parsed = {"business_keywords": [], "tech_keywords": [], "entity_keywords": [], "_raw": raw_response[:500]}

    # 按 confidence 降序排列（提示词要求）
    for key in ("business_keywords", "tech_keywords", "entity_keywords"):
        items = parsed.get(key, [])
        if isinstance(items, list):
            items.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
            parsed[key] = items[:20]

    # 统计
    bk = parsed.get("business_keywords", [])
    tk = parsed.get("tech_keywords", [])
    ek = parsed.get("entity_keywords", [])
    parsed["_stats"] = {
        "elapsed_ms": round(elapsed * 1000),
        "method": "llm_v2_prompt",
        "prompt_file": "keyword_extraction_v2.yaml",
        "total_keywords": len(bk) + len(tk) + len(ek),
        "business_count": len(bk),
        "tech_count": len(tk),
        "entity_count": len(ek),
    }
    return parsed


async def step_summarize(
    cleaned_docs: list[CleanedDocument], company_name: str,
) -> dict[str, Any]:
    llm = StubLLMClient()
    doc_texts = [d.content for d in cleaned_docs if d.content]
    start = time.monotonic()

    try:
        from src.keywords.summarizer import SummarizerAgent, SummarizerConfig
        summarizer = SummarizerAgent(llm, SummarizerConfig())
        summary = await summarizer.summarize(doc_texts)
        result = {
            "method": "llm_map_reduce",
            "business_info": summary.business_info,
            "tech_mentions": summary.tech_mentions,
            "entity_mentions": summary.entity_mentions,
            "product_mentions": summary.product_mentions,
        }
    except Exception:
        all_entities: list[str] = []
        for d in cleaned_docs:
            all_entities.extend(d.entities)
        result = {
            "method": "statistical_fallback",
            "business_info": "", "tech_mentions": list(dict.fromkeys(all_entities))[:20],
            "entity_mentions": [], "product_mentions": [],
        }

    elapsed = time.monotonic() - start
    result["elapsed_ms"] = round(elapsed * 1000)
    result["source_documents"] = len(doc_texts)
    return result


# ===================================================================
# Main pipeline
# ===================================================================

async def run_pipeline(
    results: list[dict[str, str]],
    company_name: str,
    no_extract: bool = False,
    title_threshold: float = 0.9,
) -> dict[str, Any]:
    pipeline_start = time.monotonic()

    # --- Step 0: 关键词扩展 ---
    search_combos = expand_search_keywords(company_name)
    logger.info("=" * 60)
    logger.info("Step 0: 关键词扩展")
    logger.info("=" * 60)
    for combo in search_combos:
        logger.info("  %s", combo)

    # --- Step 1-2: 标题去重 ---
    logger.info("=" * 60)
    logger.info("Step 1-2: 标题解析 + 相似度去重 (阈值=%.1f)", title_threshold)
    logger.info("=" * 60)
    docs = _results_to_raw_docs(results)
    dedup_result, unique_docs = await step_title_dedup(docs, threshold=title_threshold)
    logger.info(
        "输入 %d 条 → 去重后 %d 条唯一，%d 条转载",
        dedup_result["input_count"], dedup_result["unique_count"], dedup_result["duplicate_count"],
    )
    for dup in dedup_result["duplicates_removed"]:
        logger.info("  转载: %s", dup["title"][:60])

    # --- Step 3: 全文提取 ---
    if no_extract:
        logger.info("跳过全文提取 (--no-extract)")
        extract_result: dict[str, Any] = {
            "elapsed_ms": 0, "enriched_count": 0, "passthrough_count": len(unique_docs),
            "enriched": [], "passthrough": [
                {"url": d.source_url, "title": d.metadata.get("original_title", ""),
                 "reason": "no_extract_mode", "content_preview": d.content[:100]}
                for d in unique_docs
            ],
        }
        docs_for_clean = unique_docs
    else:
        logger.info("Step 3: 全文内容提取（%d 条 URL）", len(unique_docs))
        extract_config = ExtractionConfig(max_concurrent_extractions=3, min_content_length=50)
        extract_result, docs_for_clean = await step_extract(unique_docs, extract_config)
        logger.info("提取完成: %d 增强, %d 透传 (%dms)",
                     extract_result["enriched_count"], extract_result["passthrough_count"],
                     extract_result["elapsed_ms"])

    # --- Step 4: 清洗 ---
    logger.info("Step 4: CleanerAgent 质量评分 + SHA256 去重")
    clean_config = CleanConfig(min_quality_score=0.5)
    clean_result, cleaned_docs = await step_clean(docs_for_clean, clean_config)
    logger.info("清洗完成: %d/%d 条有效，平均质量 %.2f",
                clean_result["output_count"], clean_result["input_count"], clean_result["avg_quality"])
    for doc in clean_result["documents"][:3]:
        logger.info("  [%.2f] %s — %s", doc["quality_score"], doc["source_name"], doc["content_preview"][:80])

    # --- Step 5: keyword_extraction_v2 ---
    logger.info("Step 5: keyword_extraction_v2 结构化关键词提取")
    kw_result = await step_keyword_extraction_v2(cleaned_docs, company_name)
    kw_stats = kw_result.get("_stats", {})
    logger.info(
        "关键词提取完成: biz=%d tech=%d entity=%d (总计 %d, %dms)",
        kw_stats.get("business_count", 0), kw_stats.get("tech_count", 0),
        kw_stats.get("entity_count", 0), kw_stats.get("total_keywords", 0),
        kw_stats.get("elapsed_ms", 0),
    )
    for kw in kw_result.get("business_keywords", [])[:5]:
        logger.info("  [业务 %.2f] %s", kw["confidence"], kw["word"])
    for kw in kw_result.get("tech_keywords", [])[:5]:
        logger.info("  [技术 %.2f] %s", kw["confidence"], kw["word"])
    for kw in kw_result.get("entity_keywords", [])[:5]:
        logger.info("  [实体 %.2f] %s", kw["confidence"], kw["word"])

    # --- Step 6: LLM 摘要 ---
    logger.info("Step 6: SummarizerAgent LLM 摘要")
    summarize_result = await step_summarize(cleaned_docs, company_name)
    logger.info("摘要完成 (%s): %s", summarize_result.get("method", "?"),
                summarize_result.get("business_info", "")[:60])

    total_elapsed = (time.monotonic() - pipeline_start) * 1000

    # --- 组装报告 ---
    report: dict[str, Any] = {
        "pipeline_version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "company_name": company_name,
        "total_elapsed_ms": round(total_elapsed),
        "search_keywords": {
            "primary": f'"{company_name}"',
            "verb_groups": ["打造", "发布", "招标"],
            "noun_groups": ["系统", "平台"],
            "combinations": search_combos,
        },
        "steps": {
            "0_keyword_expansion": {
                "status": "completed",
                "combinations": search_combos,
            },
            "1_title_dedup": {
                "status": "completed",
                **dedup_result,
            },
            "2_content_extraction": {
                "status": "skipped" if no_extract else "completed",
                **extract_result,
            },
            "3_cleaner_quality_sha256": {
                "status": "completed",
                **clean_result,
            },
            "4_keyword_extraction_v2": {
                "status": "completed",
                "prompt_file": "keyword_extraction_v2.yaml",
                "business_keywords": kw_result.get("business_keywords", []),
                "tech_keywords": kw_result.get("tech_keywords", []),
                "entity_keywords": kw_result.get("entity_keywords", []),
                "stats": kw_stats,
            },
            "5_llm_summarization": {
                "status": "completed",
                **{k: v for k, v in summarize_result.items()},
            },
        },
    }
    return report


async def main():
    parser = argparse.ArgumentParser(description="情报采集全链路联调测试 v2")
    parser.add_argument("--input", type=str, help="搜索结果 JSON 文件路径 (含 title/url/snippet)")
    parser.add_argument("--company", type=str, default="福建联通", help="靶标企业名称")
    parser.add_argument("--no-extract", action="store_true", help="跳过实际 URL 爬取，仅测试去重+清洗")
    parser.add_argument("--threshold", type=float, default=0.9, help="标题去重阈值 (默认 0.9)")
    parser.add_argument("--output", type=str, default=None, help="输出 JSON 文件路径")
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("results", data) if isinstance(data, dict) else data
    else:
        results = STUB_SEARCH_RESULTS

    logger.info("靶标企业: %s", args.company)
    logger.info("搜索结果: %d 条", len(results))
    logger.info("标题去重阈值: %.1f", args.threshold)

    report = await run_pipeline(
        results=results,
        company_name=args.company,
        no_extract=args.no_extract,
        title_threshold=args.threshold,
    )

    output_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        logger.info("结果已保存到: %s", out_path)
    else:
        print("\n" + "=" * 60)
        print("JSON OUTPUT")
        print("=" * 60)
        print(output_json)

    steps = report["steps"]
    kw_step = steps["4_keyword_extraction_v2"]
    kw_stats = kw_step.get("stats", {})
    logger.info("=" * 60)
    logger.info("全链路联调完成")
    logger.info("  关键词扩展: %d 组搜索词", len(report["search_keywords"]["combinations"]))
    logger.info("  标题去重: %d → %d (移除 %d 转载)",
                steps["1_title_dedup"]["input_count"],
                steps["1_title_dedup"]["unique_count"],
                steps["1_title_dedup"]["duplicate_count"])
    if steps["2_content_extraction"]["status"] == "completed":
        logger.info("  内容提取: %d 增强, %d 透传 (%dms)",
                    steps["2_content_extraction"]["enriched_count"],
                    steps["2_content_extraction"]["passthrough_count"],
                    steps["2_content_extraction"]["elapsed_ms"])
    logger.info("  清洗去重: %d → %d (平均质量 %.2f)",
                steps["3_cleaner_quality_sha256"]["input_count"],
                steps["3_cleaner_quality_sha256"]["output_count"],
                steps["3_cleaner_quality_sha256"]["avg_quality"])
    logger.info("  V2关键词: biz=%d tech=%d entity=%d (总计 %d, %dms)",
                kw_stats.get("business_count", 0), kw_stats.get("tech_count", 0),
                kw_stats.get("entity_count", 0), kw_stats.get("total_keywords", 0),
                kw_stats.get("elapsed_ms", 0))
    logger.info("  LLM 摘要: %s (%dms)",
                steps["5_llm_summarization"]["method"],
                steps["5_llm_summarization"].get("elapsed_ms", 0))
    logger.info("  总耗时: %dms", report["total_elapsed_ms"])
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
