"""Seed mock data into the database for frontend-backend integration testing.

Usage:
    python3 scripts/seed_mock_data.py
"""

from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.database import Base, SessionLocal, engine
from src.models import (
    Task, Keyword, Asset, ApiInterface, Vulnerability, Report,
    IntelDocument, AgentLog,
)

# ---------- Fixed UUIDs so that foreign keys can cross-reference ----------

TASK_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Assets (referenced by interfaces & vulnerabilities)
ASSET_IDS = {
    "asset_001": uuid.UUID("b1000001-0001-4000-a000-000000000001"),
    "asset_002": uuid.UUID("b1000002-0002-4000-a000-000000000002"),
    "asset_003": uuid.UUID("b1000003-0003-4000-a000-000000000003"),
    "asset_004": uuid.UUID("b1000004-0004-4000-a000-000000000004"),
    "asset_005": uuid.UUID("b1000005-0005-4000-a000-000000000005"),
    "asset_006": uuid.UUID("b1000006-0006-4000-a000-000000000006"),
}

# Interfaces (referenced by vulnerabilities)
IFACE_IDS = {
    "iface_001": uuid.UUID("c1000001-0001-4000-b000-000000000001"),
    "iface_002": uuid.UUID("c1000002-0002-4000-b000-000000000002"),
    "iface_003": uuid.UUID("c1000003-0003-4000-b000-000000000003"),
    "iface_004": uuid.UUID("c1000004-0004-4000-b000-000000000004"),
    "iface_005": uuid.UUID("c1000005-0005-4000-b000-000000000005"),
}


def seed_task(session) -> Task:
    existing = session.get(Task, TASK_ID)
    if existing:
        print("  Task already exists, skipping.")
        return existing

    task = Task(
        id=TASK_ID,
        company_name="某金融科技公司",
        company_aliases=["XX金融科技", "XX Fintech"],
        industry="fintech",
        status="running",
        current_stage="api_crawl",
        progress=0.68,
        authorized_scope={
            "domains": ["target.com", "target.cn"],
            "ip_ranges": ["203.0.113.0/24"],
            "exclude": ["mail.target.com"],
        },
        config={"keyword_types": ["business", "tech", "entity"]},
        created_by="admin@eakis.local",
        created_at=datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc),
        started_at=datetime(2024, 1, 1, 8, 1, 0, tzinfo=timezone.utc),
        metadata_={
            "stats": {
                "assets_found": 247,
                "assets_confirmed": 189,
                "interfaces_crawled": 1832,
                "vulns_detected": 43,
                "vulns_confirmed": 31,
            },
            "stage_details": {
                "intelligence": {"status": "completed", "duration_s": 180, "items": 1250},
                "keyword_gen": {"status": "completed", "keywords": 113},
                "asset_discovery": {"status": "completed", "assets": 247, "confirmed": 189},
                "api_crawl": {"status": "running", "progress": 0.76, "interfaces": 1832},
                "pentest": {"status": "pending"},
                "report_gen": {"status": "pending"},
            },
            "estimated_completion": "2024-01-01T16:00:00Z",
        },
    )
    session.add(task)
    session.flush()
    print(f"  Created task '{task.company_name}' ({task.id})")
    return task


def seed_keywords(session, task: Task) -> int:
    count = 0
    kw_data = [
        ("第三方支付", "business", 0.92, 0.96, "新闻报道:36氪", False, True),
        ("金融科技", "business", 0.89, 0.94, "行业分类", False, True),
        ("消费信贷", "business", 0.85, 0.91, "官网产品页", False, True),
        ("Spring Boot", "tech", 0.88, 0.93, "技术栈识别", False, True),
        ("Nginx", "tech", 0.82, 0.90, "HTTP Header", False, True),
        ("Redis", "tech", 0.78, 0.87, "端口扫描", True, True),
        ("XX科技有限公司", "entity", 0.95, 0.98, "企业注册信息", False, True),
        ("XX支付", "entity", 0.93, 0.97, "品牌关联", True, True),
        ("在线转账", "business", 0.81, 0.88, "用户行为分析", True, False),
        ("MySQL", "tech", 0.75, 0.85, "错误页面泄露", True, True),
    ]
    for word, kw_type, weight, confidence, source, derived, used in kw_data:
        kw = Keyword(
            id=uuid.uuid4(),
            task_id=task.id,
            word=word,
            type=kw_type,
            weight=weight,
            confidence=confidence,
            source=source,
            derived=derived,
            used_in_dsl=used,
            created_at=datetime(2024, 1, 1, 8, 30, 0, tzinfo=timezone.utc),
        )
        session.add(kw)
        count += 1
    session.flush()
    print(f"  Created {count} keywords")
    return count


def seed_assets(session, task: Task) -> dict[str, uuid.UUID]:
    asset_defs = [
        ("api.target.com", "203.0.113.45", "api", 0.96, "high", True, None,
         ["Spring Boot 2.7", "Nginx 1.24", "Redis"], [80, 443, 8080],
         {"subject": "api.target.com", "issuer": "Let's Encrypt", "expires_at": "2024-06-01"}, 89),
        ("admin.target.cn", "203.0.113.46", "web", 0.94, "high", True, None,
         ["Vue 3", "Nginx 1.24"], [80, 443],
         {"subject": "admin.target.cn", "issuer": "Let's Encrypt", "expires_at": "2024-06-15"}, 34),
        ("search.target.com", "203.0.113.47", "web", 0.91, "high", True, "Cloudflare",
         ["Elasticsearch 8.x", "Nginx 1.24"], [80, 443, 9200], None, 12),
        ("upload.target.com", "203.0.113.48", "web", 0.88, "medium", True, None,
         ["MinIO", "Nginx 1.24"], [80, 443, 9000],
         {"subject": "upload.target.com", "issuer": "Let's Encrypt", "expires_at": "2024-07-01"}, 8),
        ("h5.target.com", "203.0.113.49", "mobile", 0.90, "medium", True, None,
         ["React", "Webpack 5"], [80, 443],
         {"subject": "h5.target.com", "issuer": "Let's Encrypt", "expires_at": "2024-05-20"}, 22),
        ("static.target.com", "203.0.113.50", "infra", 0.85, "low", True, "Cloudflare",
         ["Nginx 1.24", "CDN"], [80, 443], None, 2),
    ]
    mock_key_to_id = {}
    for i, (domain, ip, atype, conf, risk, icp, waf, tech, ports, cert, iface_count) in enumerate(asset_defs):
        mock_key = f"asset_{i+1:03d}"
        aid = ASSET_IDS[mock_key]
        asset = Asset(
            id=aid,
            task_id=task.id,
            domain=domain,
            ip_address=ip,
            asset_type=atype,
            confidence_score=conf,
            risk_level=risk,
            icp_verified=icp,
            waf_type=waf,
            tech_stack=tech,
            open_ports=ports,
            cert_info=cert,
            confirmed=conf >= 0.90,
            discovered_at=datetime(2024, 1, 1, 9, i * 5, 0, tzinfo=timezone.utc),
        )
        session.add(asset)
        mock_key_to_id[mock_key] = aid
    session.flush()
    print(f"  Created {len(asset_defs)} assets")
    return mock_key_to_id


def seed_interfaces(session, task: Task, asset_ids: dict) -> None:
    iface_defs = [
        ("asset_001", "/api/v2/user/{userId}/orders", "GET", "query",
         [{"name": "userId", "location": "path", "type": "integer", "required": True, "sensitive": True},
          {"name": "page", "location": "query", "type": "integer", "required": False, "sensitive": False}],
         True, True, ["userId"], 9, "dynamic", True, 2),
        ("asset_001", "/api/v2/auth/login", "POST", "auth",
         [{"name": "username", "location": "body", "type": "string", "required": True, "sensitive": False},
          {"name": "password", "location": "body", "type": "string", "required": True, "sensitive": True},
          {"name": "captcha", "location": "body", "type": "string", "required": True, "sensitive": False}],
         False, False, ["password"], 8, "dynamic", True, 1),
        ("asset_002", "/admin/api/users", "GET", "admin",
         [{"name": "role", "location": "query", "type": "string", "required": False, "sensitive": False}],
         True, True, [], 10, "dynamic", True, 1),
        ("asset_001", "/api/v2/transfer", "POST", "operation",
         [{"name": "to_account", "location": "body", "type": "string", "required": True, "sensitive": True},
          {"name": "amount", "location": "body", "type": "number", "required": True, "sensitive": True}],
         True, True, ["to_account", "amount"], 10, "dynamic", False, 0),
        ("asset_003", "/search", "GET", "search",
         [{"name": "q", "location": "query", "type": "string", "required": True, "sensitive": False}],
         False, False, [], 7, "static", True, 1),
    ]
    for i, (asset_key, path, method, api_type, params, auth, priv, sens, priority, crawl, tested, vuln_count) in enumerate(iface_defs):
        mock_key = f"iface_{i+1:03d}"
        iface = ApiInterface(
            id=IFACE_IDS[mock_key],
            task_id=task.id,
            asset_id=asset_ids[asset_key],
            path=path,
            method=method,
            api_type=api_type,
            parameters=params,
            auth_required=auth,
            privilege_sensitive=priv,
            sensitive_params=sens,
            test_priority=priority,
            crawl_method=crawl,
            crawled_at=datetime(2024, 1, 1, 10, i * 5, 0, tzinfo=timezone.utc),
        )
        session.add(iface)
    session.flush()
    print(f"  Created {len(iface_defs)} interfaces")


def seed_vulnerabilities(session, task: Task, asset_ids: dict) -> None:
    vuln_defs = [
        ("asset_001", "iface_001", "PRIVILEGE_ESCALATION", "high", 8.1,
         "订单查询接口存在水平越权", "攻击者可通过修改 userId 参数查看任意用户的订单信息",
         "GET /api/v2/user/{userId}/orders", "将 userId=1001 替换为 userId=9999",
         {"request": "GET /api/v2/user/9999/orders HTTP/1.1", "response_code": 200,
          "response_snippet": '{"data":[{"orderId":"2024xxxx"}]}'},
         0.97, "LOW", "服务端验证当前登录用户ID与请求参数userId是否一致", "confirmed"),
        ("asset_003", "iface_005", "SQL_INJECTION", "critical", 9.8,
         "搜索接口存在SQL注入漏洞", "搜索参数未进行过滤，可注入恶意SQL语句",
         "GET /search?q=", "q=1' OR '1'='1",
         {"request": "GET /search?q=1' OR '1'='1 HTTP/1.1", "response_code": 200,
          "response_snippet": '{"total":15432}'},
         0.99, "LOW", "使用参数化查询，对用户输入进行严格过滤", "confirmed"),
        ("asset_001", "iface_002", "UNAUTHORIZED", "high", 7.5,
         "登录接口缺少速率限制", "登录接口未设置速率限制，可被暴力破解",
         "POST /api/v2/auth/login", "短时间内发送1000次登录请求",
         {"request": "POST /api/v2/auth/login", "response_code": 401,
          "response_snippet": '{"error":"invalid_credentials"}'},
         0.92, "MED", "添加基于IP和账号的速率限制", "confirmed"),
        ("asset_005", "iface_005", "XSS", "medium", 5.4,
         "移动端页面存在反射型XSS", "URL参数未转义直接渲染到页面中",
         "GET /h5/redirect?url=", "url=javascript:alert(document.cookie)",
         {"request": "GET /h5/redirect?url=javascript:alert(1)", "response_code": 200,
          "response_snippet": '<script>window.location="javascript:alert(1)"</script>'},
         0.88, "MED", "对URL参数进行白名单校验", "confirmed"),
        ("asset_004", "iface_005", "FILE_UPLOAD", "medium", 6.5,
         "文件上传接口缺少类型校验", "可上传恶意脚本文件，导致远程代码执行",
         "POST /upload/file", "上传 .jsp webshell 文件",
         {"request": "POST /upload/file", "response_code": 200,
          "response_snippet": '{"url":"/files/shell.jsp","status":"ok"}'},
         0.94, "LOW", "服务端校验文件类型和内容，限制上传目录不可执行", "confirmed"),
    ]
    for (asset_key, iface_key, vtype, severity, cvss, title, desc, path, payload,
         evidence, llm_conf, fp_risk, remediation, vstatus) in vuln_defs:
        vuln = Vulnerability(
            id=uuid.uuid4(),
            task_id=task.id,
            asset_id=asset_ids[asset_key],
            interface_id=IFACE_IDS.get(iface_key),
            vuln_type=vtype,
            severity=severity,
            cvss_score=cvss,
            title=title,
            description=desc,
            affected_path=path,
            test_payload=payload,
            evidence=evidence,
            llm_confidence=llm_conf,
            false_positive_risk=fp_risk,
            remediation=remediation,
            status=vstatus,
            human_confirmed=True,
            discovered_at=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
        )
        session.add(vuln)
    session.flush()
    print(f"  Created {len(vuln_defs)} vulnerabilities")


def seed_reports(session, task: Task) -> None:
    report = Report(
        id=uuid.uuid4(),
        task_id=task.id,
        status="completed",
        template="standard",
        language="zh-CN",
        page_count=47,
        word_count=8234,
        quality_score={"overall": 0.93, "accuracy": 0.96, "completeness": 0.91, "readability": 0.94, "actionability": 0.89},
        generation_duration_s=1080,
        generated_at=datetime(2024, 1, 1, 16, 0, 0, tzinfo=timezone.utc),
    )
    session.add(report)
    session.flush()
    print("  Created 1 report")


def seed_intel_documents(session, task: Task) -> None:
    for i in range(5):
        doc = IntelDocument(
            id=uuid.uuid4(),
            task_id=task.id,
            source_type="news",
            source_name=f"Fofa #{i+1}",
            source_url=f"https://fofa.example.com/result/{i+1}",
            content=f"这是第 {i+1} 条情报采集结果，来源 Fofa 搜索引擎。包含域名、IP 等资产相关信息。",
            quality_score=0.85,
        )
        session.add(doc)
    session.flush()
    print("  Created 5 intel documents")


def main():
    print("Ensuring tables exist...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        print("\nSeeding task...")
        task = seed_task(session)

        print("\nSeeding keywords...")
        seed_keywords(session, task)

        print("\nSeeding assets...")
        asset_ids = seed_assets(session, task)

        print("\nSeeding interfaces...")
        seed_interfaces(session, task, asset_ids)

        print("\nSeeding vulnerabilities...")
        seed_vulnerabilities(session, task, asset_ids)

        print("\nSeeding report...")
        seed_reports(session, task)

        print("\nSeeding intel documents...")
        seed_intel_documents(session, task)

        session.commit()
        print("\nMock data seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"\nSeed failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
