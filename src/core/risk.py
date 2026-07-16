"""Risk calculation per ROADMAP A.7.

Formula (A.7-决策1 漏洞加权求和):
    severity_weight = {critical: 1.0, high: 0.7, medium: 0.4, low: 0.1, info: 0.0}
    asset_risk   = Σ over vulns (cvss_score × severity_weight)   # capped per asset
    company_risk = Σ over assets (asset_risk)                    # capped per company

NOTE: Per A.7-决策1 the user chose 漏洞加权求和 (NOT the three-factor multiply),
so asset value_score (A.4-决策3) is used only for asset sorting/display, NOT in
the risk formula. Risk is driven solely by vulnerability CVSS × severity weight.
"""

from __future__ import annotations

from typing import Any

# Severity → weight. Tunable; mirrored in config when a settings hook is added.
SEVERITY_WEIGHT: dict[str, float] = {
    "critical": 1.0,
    "high": 0.7,
    "medium": 0.4,
    "low": 0.1,
    "info": 0.0,
}

# Caps to keep scores in a sane 0-100 range (A.7 formula note).
ASSET_RISK_CAP = 100.0
COMPANY_RISK_CAP = 100.0


def vuln_contribution(cvss_score: float | None, severity: str | None) -> float:
    """Contribution of one vulnerability to its asset's risk."""
    weight = SEVERITY_WEIGHT.get((severity or "").lower(), 0.0)
    cvss = cvss_score or 0.0
    return cvss * weight


def calc_asset_risk(vulns: list[Any]) -> float:
    """asset_risk = Σ(cvss × severity_weight), capped at ASSET_RISK_CAP.

    `vulns`: iterable of objects with .cvss_score and .severity attributes
    (or dicts with those keys).
    """
    total = 0.0
    for v in vulns:
        cvss = getattr(v, "cvss_score", None) if not isinstance(v, dict) else v.get("cvss_score")
        sev = getattr(v, "severity", None) if not isinstance(v, dict) else v.get("severity")
        total += vuln_contribution(cvss, sev)
    return min(total, ASSET_RISK_CAP)


def calc_company_risk(asset_risks: list[float]) -> float:
    """company_risk = Σ(asset_risk), capped at COMPANY_RISK_CAP."""
    return min(sum(asset_risks), COMPANY_RISK_CAP)


def severity_counts(vulns: list[Any]) -> dict[str, int]:
    """Tally vulnerabilities by severity → {critical, high, medium, low, info}."""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for v in vulns:
        sev = (getattr(v, "severity", None) if not isinstance(v, dict) else v.get("severity")) or "info"
        sev = sev.lower()
        if sev in counts:
            counts[sev] += 1
    return counts
