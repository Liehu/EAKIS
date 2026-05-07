"""Structured JSON logging and distributed-trace context for EAKIS.

Usage::

    from src.shared.logger import get_logger, bind_trace_context

    log = get_logger("intelligence")
    log.info("analysis started", extra={"task_id": "abc123"})

    with bind_trace_context(trace_id="t-001", span_id="s-042"):
        log.info("inside a traced span")
"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Trace-context context variables
# ---------------------------------------------------------------------------

_trace_id: ContextVar[str | None] = ContextVar("_trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("_span_id", default=None)


# ---------------------------------------------------------------------------
# StructuredFormatter
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """Format every log record as a single JSON line.

    The output always contains ``timestamp``, ``level``, ``logger``, and
    ``message``.  When ``extra`` fields are provided they are merged
    into the top-level object.  If a trace context is active the
    ``trace_id`` and ``span_id`` are included automatically.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge extra fields that the caller passed via extra={...}.
        # logging stashes them as direct attributes on the record.
        reserved = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)
        for key, value in record.__dict__.items():
            if key not in reserved and key not in log_entry:
                log_entry[key] = value

        # Attach distributed-trace identifiers when set.
        trace_id = _trace_id.get()
        span_id = _span_id.get()
        if trace_id is not None:
            log_entry["trace_id"] = trace_id
        if span_id is not None:
            log_entry["span_id"] = span_id

        # Handle real exceptions (created via logger.exception / exc_info).
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``eakis`` namespace with a JSON handler.

    Repeated calls with the same *name* return the same logger without
    adding duplicate handlers.
    """
    logger = logging.getLogger(f"eakis.{name}")

    # Avoid adding handlers when the logger was already configured, or
    # when the root/parent already has handlers that would propagate.
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        # Prevent double-logging when an ancestor also has handlers.
        logger.propagate = False

    return logger


# ---------------------------------------------------------------------------
# Trace-context context manager
# ---------------------------------------------------------------------------

@contextmanager
def bind_trace_context(
    trace_id: str,
    span_id: str | None = None,
) -> Iterator[None]:
    """Context manager that sets ``trace_id`` (and optionally ``span_id``)
    for the duration of the block.

    Example::

        with bind_trace_context("trace-abc", "span-1"):
            log.info("traced event")

    The values are stored in :mod:`contextvars` so they propagate
    correctly across ``asyncio`` task boundaries.
    """
    tok_trace = _trace_id.set(trace_id)
    tok_span: object | None = None
    if span_id is not None:
        tok_span = _span_id.set(span_id)

    try:
        yield
    finally:
        _trace_id.reset(tok_trace)
        if tok_span is not None:
            _span_id.reset(tok_span)  # type: ignore[arg-type]
