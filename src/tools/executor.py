"""ToolExecutor — runs external tools via subprocess with anti-RCE guarantees.

All invocations go through ToolDefinition.build_argv() (validated argv list,
never shell=True). Captures stdout/stderr/exit code, enforces timeout and max
output size. Returns a structured ToolResult.

If a binary is not installed (FileNotFoundError), the executor returns a
result with status='unavailable' rather than crashing — agents can degrade.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.tools.security import ToolDefinition

logger = logging.getLogger(__name__)

# Hard limits to prevent resource exhaustion via tool output.
_MAX_OUTPUT_BYTES = 50 * 1024 * 1024  # 50 MB stdout cap


@dataclass
class ToolResult:
    """Structured result of one tool execution."""
    tool: str
    status: str  # success / failed / timeout / unavailable / invalid_input
    argv: list[str] = field(default_factory=list)
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    error: str | None = None
    started_at: str = ""
    # Parsed output (filled by a parser if provided) — the structured payload.
    parsed: Any = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # stdout may be huge; truncate for storage safety
        if len(d.get("stdout", "")) > 100_000:
            d["stdout"] = d["stdout"][:100_000] + "\n...[truncated]"
        return d


class ToolExecutor:
    """Execute registered ToolDefinitions in a sandboxed, anti-RCE way."""

    def __init__(self, tools_dir: str | None = None, allow_missing: bool = True) -> None:
        # tools_dir is informational (binaries expected on PATH for now);
        # kept for future allowlist-path resolution.
        self.tools_dir = tools_dir
        self.allow_missing = allow_missing
        self._registry: dict[str, ToolDefinition] = {}

    # ── registration ──
    def register(self, tool: ToolDefinition) -> None:
        self._registry[tool.name] = tool
        logger.info("Registered tool: %s (%s)", tool.name, tool.binary)

    def get(self, name: str) -> ToolDefinition | None:
        return self._registry.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._registry.values())

    # ── execution ──
    def run(
        self,
        name: str,
        inputs: dict[str, Any],
        flags: set[str] | None = None,
        timeout: int | None = None,
        parser: Any = None,
    ) -> ToolResult:
        """Run a registered tool synchronously.

        Args:
            name: registered tool name.
            inputs: validated-against-schema input values (domain/ip/...).
            flags: optional boolean flags (whitelisted by the tool def).
            timeout: override tool default timeout (seconds).
            parser: optional callable(stdout, result) -> parsed payload.
        """
        tool = self._registry.get(name)
        started = datetime.now(UTC).isoformat()
        if tool is None:
            return ToolResult(tool=name, status="failed", error=f"Unknown tool: {name}", started_at=started)
        if not tool.enabled:
            return ToolResult(tool=name, status="failed", error="Tool disabled", started_at=started)

        # 1. Build validated argv (anti-RCE chokepoint — raises on hostile input).
        try:
            argv = tool.build_argv(inputs, flags)
        except ValueError as exc:
            logger.warning("Tool %s input rejected: %s", name, exc)
            return ToolResult(tool=name, status="invalid_input", error=str(exc), started_at=started)

        # 2. Binary presence check (graceful degradation).
        if self.allow_missing and shutil.which(tool.binary) is None:
            logger.info("Tool %s binary '%s' not on PATH — unavailable", name, tool.binary)
            return ToolResult(
                tool=name, status="unavailable", argv=argv,
                error=f"Binary '{tool.binary}' not installed", started_at=started,
            )

        # 3. Execute (argv list, NEVER shell=True).
        import time
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout or tool.default_timeout,
                check=False,
                shell=False,  # explicit — anti-RCE invariant
            )
            duration = round(time.monotonic() - t0, 2)
            # Truncate oversized output defensively.
            stdout = proc.stdout or ""
            if len(stdout.encode()) > _MAX_OUTPUT_BYTES:
                stdout = stdout[:_MAX_OUTPUT_BYTES] + "\n...[output truncated]"

            status = "success" if proc.returncode == 0 else "failed"
            result = ToolResult(
                tool=name, status=status, argv=argv, exit_code=proc.returncode,
                stdout=stdout, stderr=proc.stderr or "", duration_s=duration,
                started_at=started,
            )
            if parser is not None:
                try:
                    result.parsed = parser(stdout, result)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Tool %s parser failed: %s", name, exc)
            logger.info("Tool %s finished: %s in %ss (exit %s)", name, status, duration, proc.returncode)
            return result

        except subprocess.TimeoutExpired:
            duration = round(time.monotonic() - t0, 2)
            logger.warning("Tool %s timed out after %ss", name, timeout or tool.default_timeout)
            return ToolResult(
                tool=name, status="timeout", argv=argv, duration_s=duration,
                error=f"Timed out after {timeout or tool.default_timeout}s", started_at=started,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool %s execution error", name)
            return ToolResult(tool=name, status="failed", argv=argv, error=str(exc), started_at=started)


# ── Module-level singleton ───────────────────────────────
_executor: ToolExecutor | None = None


def get_executor() -> ToolExecutor:
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
        # lazy-register tools on first use
        from src.tools.registry import register_all
        register_all(_executor)
    return _executor
