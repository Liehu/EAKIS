"""Tool execution security primitives (防 RCE).

Security model:
  1. NEVER use shell=True — always pass argv list to subprocess.
  2. Input normalization: every user-supplied input (domain/ip/cidr/url) is
     validated against a strict regex whitelist; anything failing is rejected
     BEFORE reaching the binary. No shell metacharacters can survive.
  3. Argument whitelist: each tool declares the exact flags it accepts; unknown
     flags are dropped.
  4. Resource limits: timeout + max output bytes per execution.
  5. Binary path resolved from a configured allowlist dir, not from user input.

This is the single chokepoint through which all external tool invocations pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# ── Input validators (strict regex whitelists) ────────────
# These intentionally reject anything that could be a shell escape. Domains/IPs/
# CIDRs/URLs have well-defined character sets; anything else is hostile.

# Domain: labels of [a-z0-9-], dot-separated, no leading/trailing dot/hyphen.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$",
    re.IGNORECASE,
)

# IPv4
_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")

# CIDR: ipv4/prefix
_CIDR_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})$")

# URL: scheme://host[:port][/path] — restrictive, no query injection surface.
_URL_RE = re.compile(r"^https?://[a-z0-9.\-]+(:\d{1,5})?(/[^\s]*)?$", re.IGNORECASE)

# Bare word: alphanumeric + dash/underscore/dot only (for tool-specific tokens).
_WORD_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_domain(value: str) -> str:
    if not _DOMAIN_RE.match(value):
        raise ValueError(f"Invalid domain: {value!r}")
    return value.lower()


def validate_ip(value: str) -> str:
    m = _IPV4_RE.match(value)
    if not m or any(int(octet) > 255 for octet in m.groups()):
        raise ValueError(f"Invalid IPv4: {value!r}")
    return value


def validate_cidr(value: str) -> str:
    m = _CIDR_RE.match(value)
    if not m:
        raise ValueError(f"Invalid CIDR: {value!r}")
    *octets, prefix = m.groups()
    if any(int(octet) > 255 for octet in octets) or int(prefix) > 32:
        raise ValueError(f"Invalid CIDR: {value!r}")
    return value


def validate_url(value: str) -> str:
    if not _URL_RE.match(value):
        raise ValueError(f"Invalid URL: {value!r}")
    return value


def validate_word(value: str, max_len: int = 100) -> str:
    if len(value) > max_len or not _WORD_RE.match(value):
        raise ValueError(f"Invalid word (alphanumeric/._- only, ≤{max_len}): {value!r}")
    return value


# Map of named input types → validator function.
VALIDATORS: dict[str, Callable[[str], str]] = {
    "domain": validate_domain,
    "ip": validate_ip,
    "cidr": validate_cidr,
    "url": validate_url,
    "word": validate_word,
}


# ── Tool input/output schema ─────────────────────────────

@dataclass
class ToolParam:
    """One declared input parameter of a tool."""
    name: str
    input_type: str  # domain/ip/cidr/url/word → maps to a VALIDATORS entry
    flag: str  # CLI flag, e.g. "-d" / "-domain"; value passed after it
    required: bool = False
    multiple: bool = False  # if True, accepts a list (repeats the flag)


@dataclass
class ToolDefinition:
    """Static metadata + security envelope for an external tool."""
    name: str
    binary: str  # resolved against tools_dir allowlist
    description: str
    category: str  # recon / dns / portscan / vulnscan / cert
    params: list[ToolParam] = field(default_factory=list)
    # Fixed flags always appended (e.g. ["-silent", "-json"]). User cannot change these.
    fixed_flags: list[str] = field(default_factory=list)
    # Allowlist of optional boolean flags the caller may toggle (presence/absence).
    allowed_flags: set[str] = field(default_factory=set)
    default_timeout: int = 300
    enabled: bool = True

    def build_argv(self, inputs: dict[str, Any], flags: set[str] | None = None) -> list[str]:
        """Build the argv list from validated inputs. Raises on any invalid input.

        This is the anti-RCE core: inputs are validated by type, flags are
        whitelisted, the result is a plain list (no shell).
        """
        argv: list[str] = [self.binary]
        argv.extend(self.fixed_flags)

        # user-requested boolean flags — only those in allowed_flags survive
        for f in (flags or set()):
            if f in self.allowed_flags:
                argv.append(f)

        for p in self.params:
            if p.name not in inputs:
                if p.required:
                    raise ValueError(f"Missing required param: {p.name}")
                continue
            raw = inputs[p.name]
            values = raw if (p.multiple and isinstance(raw, list)) else [raw]
            validator = VALIDATORS.get(p.input_type)
            if validator is None:
                raise ValueError(f"Unknown input_type {p.input_type} for param {p.name}")
            for v in values:
                # Normalize/validate — hostile values raise here, before subprocess.
                safe = validator(str(v))
                argv.append(p.flag)
                argv.append(safe)
        return argv
