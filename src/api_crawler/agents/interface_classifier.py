from __future__ import annotations

import re

from src.api_crawler.models import (
    ClassifiedInterface,
    CrawlMethod,
    InterfaceType,
    ParameterInfo,
    RawInterface,
)

_TYPE_RULES: list[tuple[re.Pattern[str], InterfaceType]] = [
    (
        re.compile(
            r"/auth|/login|/logout|/register|/token|/session|/signin|/signup", re.I
        ),
        InterfaceType.AUTH,
    ),
    (re.compile(r"/admin|/manage|/superuser", re.I), InterfaceType.ADMIN),
    (
        re.compile(r"/upload|/file|/download|/attachment|/export|/import", re.I),
        InterfaceType.UPLOAD,
    ),
    (re.compile(r"/search|/query|/find|/lookup", re.I), InterfaceType.SEARCH),
    (re.compile(r"/webhook|/callback|/notify|/hook", re.I), InterfaceType.WEBHOOK),
    (re.compile(r"/config|/setting|/preference", re.I), InterfaceType.CONFIG),
]

_METHOD_TYPE_MAP: dict[str, InterfaceType] = {
    "POST": InterfaceType.OPERATION,
    "PUT": InterfaceType.OPERATION,
    "PATCH": InterfaceType.OPERATION,
    "DELETE": InterfaceType.OPERATION,
}

_SENSITIVE_PARAM_NAMES = {
    "userid",
    "user_id",
    "uid",
    "roleid",
    "role_id",
    "rid",
    "tenantid",
    "tenant_id",
    "tid",
    "orgid",
    "org_id",
    "organizationid",
    "accountid",
    "account_id",
    "companyid",
    "company_id",
    "projectid",
    "project_id",
    "groupid",
    "group_id",
}

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_NUMERIC_RE = re.compile(r"^\d+$")


class InterfaceClassifier:
    def classify(self, raw: RawInterface, asset_id: str) -> ClassifiedInterface:
        api_type = self._determine_type(raw.path, raw.method)
        sensitive_params = self._find_sensitive_params(raw.parameters)
        path_pattern = self._normalize_path(raw.path)
        priority = self._calculate_priority(api_type, sensitive_params, raw.method)

        return ClassifiedInterface(
            asset_id=asset_id,
            path=raw.path,
            path_pattern=path_pattern,
            method=raw.method,
            api_type=api_type,
            parameters=raw.parameters,
            request_headers=raw.request_headers,
            response_schema=raw.response_schema,
            auth_required=raw.auth_required,
            privilege_sensitive=len(sensitive_params) > 0,
            sensitive_params=sensitive_params,
            trigger_scenario=raw.trigger_scenario,
            test_priority=priority,
            crawl_method=raw.crawl_method,
        )

    def classify_batch(
        self, raws: list[RawInterface], asset_id: str
    ) -> list[ClassifiedInterface]:
        return [self.classify(r, asset_id) for r in raws]

    def _determine_type(self, path: str, method: str) -> InterfaceType:
        for pattern, iface_type in _TYPE_RULES:
            if pattern.search(path):
                return iface_type
        return _METHOD_TYPE_MAP.get(method.upper(), InterfaceType.QUERY)

    def _find_sensitive_params(self, params: list[ParameterInfo]) -> list[str]:
        return [p.name for p in params if p.name.lower() in _SENSITIVE_PARAM_NAMES]

    def _normalize_path(self, path: str) -> str:
        segments = path.split("/")
        normalized: list[str] = []
        for seg in segments:
            if not seg:
                normalized.append(seg)
                continue
            if _UUID_RE.match(seg) or _NUMERIC_RE.match(seg):
                normalized.append("{id}")
            else:
                normalized.append(seg)
        return "/".join(normalized)

    def _calculate_priority(
        self,
        api_type: InterfaceType,
        sensitive_params: list[str],
        method: str,
    ) -> int:
        score = 5
        if api_type == InterfaceType.ADMIN:
            score += 3
        if api_type == InterfaceType.AUTH:
            score += 2
        if api_type in (InterfaceType.OPERATION, InterfaceType.UPLOAD):
            score += 1
        if sensitive_params:
            score += 3
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            score += 1
        return min(max(score, 1), 10)
