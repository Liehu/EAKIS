"""Specialized asset-type tables (table-per-subclass).

Per ROADMAP C.2-决策2 (拆多表) and the user's asset page vision: IP / 域名 /
证书 / 小程序 / APP each get dedicated columns beyond the base Asset. The base
assets table retains shared columns (task_id, company_id, risk_level, status,
discovered_at, ...) for unified queries; these tables hold type-specific detail
and are 1:1 with an asset row (matched on asset_type).

Base Asset.asset_type values: "ip", "domain", "certificate", "miniprogram", "app",
"web". The legacy "web" type stays on the base table (no extra columns needed).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base


class IPAsset(Base):
    """IP-type asset detail (C.2 IP Tab: IP/区域/是否CDN/ASN/更新时间/状态)."""

    __tablename__ = "asset_ips"

    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    ip_address = Column(String(45), nullable=False)
    is_cdn = Column(Boolean, nullable=False, default=False)
    asn = Column(String(50), nullable=True, comment="AS 号")
    region = Column(String(100), nullable=True, comment="区域/地理位置")
    isp = Column(String(100), nullable=True, comment="运营商")
    open_ports = Column(String(200), nullable=True, comment="开放端口 (逗号分隔，详情在 base.open_ports)")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    asset = relationship("Asset", backref="ip_detail")

    __table_args__ = (
        Index("idx_asset_ips_ip", "ip_address"),
    )

    def __repr__(self) -> str:
        return f"<IPAsset {self.ip_address}>"


class DomainAsset(Base):
    """Domain-type asset detail (C.2 域名 Tab: 域名/备案号/状态/whois)."""

    __tablename__ = "asset_domains"

    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    domain = Column(String(500), nullable=False)
    icp_license = Column(String(100), nullable=True, comment="备案号")
    icp_entity = Column(String(500), nullable=True, comment="备案主体")
    whois_info = Column(Text, nullable=True, comment="whois 信息 (注册商/注册时间/到期时间)")
    registrant = Column(String(300), nullable=True, comment="注册人")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="域名到期时间")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    asset = relationship("Asset", backref="domain_detail")

    __table_args__ = (
        Index("idx_asset_domains_domain", "domain"),
    )

    def __repr__(self) -> str:
        return f"<DomainAsset {self.domain}>"


class Certificate(Base):
    """SSL/TLS certificate (C.4-决策3 独立模型 + 资产页证书 Tab).

    C.2 证书 Tab: 域名/颁发者/有效期/状态/更新时间 + 关联企业.
    """

    __tablename__ = "asset_certificates"

    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    common_name = Column(String(500), nullable=False, comment="证书域名 (CN/SAN)")
    issuer = Column(String(300), nullable=True, comment="颁发者")
    serial_number = Column(String(200), nullable=True, comment="序列号")
    signature_algorithm = Column(String(100), nullable=True, comment="签名算法")
    issued_at = Column(DateTime(timezone=True), nullable=True, comment="颁发时间")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="有效期至")
    is_expired = Column(Boolean, nullable=False, default=False)
    is_self_signed = Column(Boolean, nullable=False, default=False)
    ct_log_count = Column(Integer, nullable=True, comment="证书透明度日志数")
    fingerprint = Column(String(128), nullable=True, comment="指纹 SHA256")
    raw_pem = Column(Text, nullable=True, comment="原始证书 PEM")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    asset = relationship("Asset", backref="certificate_detail")

    __table_args__ = (
        Index("idx_asset_certs_cn", "common_name"),
        Index("idx_asset_certs_issuer", "issuer"),
    )

    def __repr__(self) -> str:
        return f"<Certificate {self.common_name} issuer={self.issuer}>"


class MiniProgramAsset(Base):
    """Mini-program (小程序) asset detail (C.2: 名称/AppID/主体企业/类目/状态)."""

    __tablename__ = "asset_miniprograms"

    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String(200), nullable=False, comment="小程序名称")
    app_id = Column(String(100), nullable=True, comment="AppID")
    platform = Column(String(50), nullable=False, server_default="wechat", comment="wechat/alipay/baidu/douyin")
    subject_entity = Column(String(300), nullable=True, comment="主体企业")
    category = Column(String(100), nullable=True, comment="类目")
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    asset = relationship("Asset", backref="miniprogram_detail")

    __table_args__ = (
        Index("idx_asset_mp_appid", "app_id"),
    )

    def __repr__(self) -> str:
        return f"<MiniProgramAsset {self.name}>"


class AppAsset(Base):
    """Mobile APP asset detail (C.2: 应用名/包名/签名证书主体/下载源/状态)."""

    __tablename__ = "asset_apps"

    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String(200), nullable=False, comment="应用名")
    package_name = Column(String(200), nullable=True, comment="包名 (Android) / Bundle ID (iOS)")
    platform = Column(String(20), nullable=False, comment="android/ios/harmony")
    sign_cert_subject = Column(String(300), nullable=True, comment="签名证书主体")
    download_source = Column(String(300), nullable=True, comment="下载源 (应用商店/官网)")
    version = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    asset = relationship("Asset", backref="app_detail")

    __table_args__ = (
        Index("idx_asset_app_pkg", "package_name"),
    )

    def __repr__(self) -> str:
        return f"<AppAsset {self.name} pkg={self.package_name}>"
