"""Report generation worker (S2 M6).

Background task that aggregates task data, renders the report, computes quality
score, and persists the result. Called by the reports router's generate endpoint.
"""

from __future__ import annotations

import logging
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report import Report
from src.models.template import Template
from src.reporting.aggregator import aggregate_task_data, estimate_quality
from src.reporting.renderer import render_report

logger = logging.getLogger(__name__)


async def generate_report_task(
    db: AsyncSession,
    report_id: UUID,
    task_id: UUID,
    template_name: str | None = None,
    use_llm: bool = False,
) -> None:
    """Aggregate → render → score → persist. Updates the Report row in place.

    Must be called within a DB session; the caller commits.
    """
    start = time.monotonic()
    report = await db.get(Report, report_id)
    if report is None:
        logger.error("Report %s not found", report_id)
        return

    try:
        # 1. Aggregate task data
        ctx = await aggregate_task_data(db, task_id)

        # 2. Resolve S4 report template (by name) if provided
        report_template: dict | None = None
        if template_name:
            tmpl = (await db.execute(
                select(Template).where(
                    Template.template_type == "report", Template.name == template_name
                )
            )).scalars().first()
            if tmpl is not None:
                report_template = tmpl.content

        # 3. Render (LLM optional)
        llm_client = None
        if use_llm:
            try:
                from src.shared.llm_client import LLMClient
                llm_client = LLMClient()
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM client unavailable, falling back to template mode: %s", exc)

        markdown = render_report(ctx, report_template=report_template, use_llm=use_llm, llm_client=llm_client)

        # 4. Quality score (heuristic)
        quality = estimate_quality(ctx)

        # 5. Word/page count (rough: 1 page ≈ 500 words)
        word_count = len(markdown)
        page_count = max(1, word_count // 1500)

        # 6. Persist
        report.content = markdown
        report.markdown_path = f"reports/{task_id}/{report_id}.md"  # logical key (MinIO upload optional)
        report.status = "completed"
        report.quality_score = quality
        report.word_count = word_count
        report.page_count = page_count
        report.generation_duration_s = int(time.monotonic() - start)
        report.generated_at = report.generated_at  # set below
        from datetime import UTC, datetime
        report.generated_at = datetime.now(UTC)

        await db.commit()
        logger.info("Report %s generated in %ds", report_id, report.generation_duration_s)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Report generation failed for %s", report_id)
        report.status = "failed"
        report.error_message = str(exc)[:500]
        from datetime import UTC, datetime
        report.generated_at = datetime.now(UTC)
        await db.commit()
