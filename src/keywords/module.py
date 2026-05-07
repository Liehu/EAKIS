"""M2 Keyword Engine Module: orchestrates the full keyword pipeline.

Pipeline: Intelligence Documents → Summarize → Generate → Rank → Expand → Persist

Also provides CRUD for keywords via the API layer.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.keyword import Keyword, KeywordTypeEnum
from src.models.intel_document import IntelDocument
from src.keywords.ranker import KeywordRanker, KeywordCandidate
from src.keywords.summarizer import SummarizerAgent, SummarizerConfig
from src.keywords.generator import KeywordGeneratorAgent
from src.keywords.expander import KeywordExpander
from src.keywords.feedback import FeedbackOptimizer
from src.shared.llm_client import LLMClient

logger = logging.getLogger(__name__)


class KeywordModule:
    """Main orchestration class for the keyword engine pipeline."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        industry: str | None = None,
    ) -> None:
        self._llm = llm or LLMClient()
        self._ranker = KeywordRanker(domain=industry)
        self._summarizer = SummarizerAgent(self._llm)
        self._generator = KeywordGeneratorAgent(self._llm, self._ranker)
        self._expander = KeywordExpander(self._llm)
        self._feedback = FeedbackOptimizer(self._llm)

    async def run_pipeline(
        self,
        session: AsyncSession,
        task_id: UUID,
        company_name: str,
        industry: str | None,
        expand: bool = True,
    ) -> list[Keyword]:
        """Run the full keyword generation pipeline for a task."""
        # Step 1: Load intelligence documents
        docs = await self._load_intel_documents(session, task_id)
        if not docs:
            logger.warning("No intel documents found for task %s", task_id)
            return []

        # Step 2: Summarize
        summary = await self._summarizer.summarize(docs)
        logger.info(
            "Summarized %d intel docs: %s",
            len(docs),
            summary.to_text()[:200],
        )

        # Step 3: Generate keywords
        generated = await self._generator.generate(company_name, industry, summary)
        logger.info(
            "Generated %d keywords (biz=%d, tech=%d, entity=%d)",
            generated.total,
            len(generated.business),
            len(generated.tech),
            len(generated.entity),
        )

        # Step 4: Rank
        all_candidates = generated.all
        ranked = self._ranker.rank(all_candidates)

        # Step 5: Expand (optional)
        if expand and ranked:
            expansion_results = await self._expander.expand(
                ranked[:20],  # Expand top 20 keywords
                company_name=company_name,
            )
            expanded_candidates: list[KeywordCandidate] = []
            for result in expansion_results:
                expanded_candidates.extend(result.expanded)
            # Re-rank expanded keywords
            if expanded_candidates:
                ranked_expanded = self._ranker.rank(expanded_candidates)
                ranked.extend(ranked_expanded)

        # Step 6: Persist to database
        keywords = await self._persist_keywords(session, task_id, ranked)
        logger.info("Persisted %d keywords for task %s", len(keywords), task_id)
        return keywords

    async def run_feedback_cycle(
        self,
        session: AsyncSession,
        task_id: UUID,
        company_name: str,
        industry: str | None,
        hit_count: int,
        result_count: int,
    ) -> list[Keyword]:
        """Run feedback optimization cycle when keyword hit rate is low."""
        existing = await self.get_keywords(session, task_id)
        if not existing:
            return []

        result = await self._feedback.optimize(
            keywords=[self._kw_to_candidate(kw) for kw in existing],
            company_name=company_name,
            industry=industry,
            hit_count=hit_count,
            result_count=result_count,
        )

        if not result.new_keywords:
            return []

        ranked = self._ranker.rank(result.new_keywords)
        return await self._persist_keywords(session, task_id, ranked)

    # --- CRUD operations ---

    async def get_keywords(
        self,
        session: AsyncSession,
        task_id: UUID,
        keyword_type: str | None = None,
        min_weight: float = 0.0,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Keyword]:
        """Get keywords for a task with optional filtering and pagination."""
        stmt = select(Keyword).where(Keyword.task_id == task_id)

        if keyword_type:
            stmt = stmt.where(Keyword.type == keyword_type)
        if min_weight > 0:
            stmt = stmt.where(Keyword.weight >= min_weight)

        stmt = stmt.order_by(Keyword.weight.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_keyword_count(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> dict[str, int]:
        """Get keyword counts by type."""
        stmt = (
            select(Keyword.type, func.count(Keyword.id))
            .where(Keyword.task_id == task_id)
            .group_by(Keyword.type)
        )
        result = await session.execute(stmt)
        counts = {"business": 0, "tech": 0, "entity": 0, "total": 0}
        for kw_type, cnt in result.all():
            if kw_type in counts:
                counts[kw_type] = cnt
            counts["total"] += cnt
        return counts

    async def add_keyword(
        self,
        session: AsyncSession,
        task_id: UUID,
        word: str,
        keyword_type: str,
        weight: float = 0.5,
        reason: str | None = None,
    ) -> Keyword:
        """Manually add a keyword."""
        domain_score = self._ranker._domain_dict.score(word)
        final_weight = self._ranker.compute_weight(
            word, domain_score=domain_score, relevance_score=weight
        )
        confidence = min(1.0, domain_score * 0.4 + weight * 0.6)

        kw = Keyword(
            task_id=task_id,
            word=word,
            type=keyword_type,
            weight=final_weight,
            confidence=confidence,
            source=reason or "manual",
            derived=False,
            used_in_dsl=False,
        )
        session.add(kw)
        await session.flush()
        return kw

    async def delete_keyword(
        self,
        session: AsyncSession,
        keyword_id: UUID,
    ) -> bool:
        """Delete a keyword by ID."""
        kw = await session.get(Keyword, keyword_id)
        if kw is None:
            return False
        await session.delete(kw)
        await session.flush()
        return True

    async def get_keyword_by_id(
        self,
        session: AsyncSession,
        keyword_id: UUID,
    ) -> Keyword | None:
        return await session.get(Keyword, keyword_id)

    # --- Internal helpers ---

    async def _load_intel_documents(
        self,
        session: AsyncSession,
        task_id: UUID,
    ) -> list[str]:
        stmt = (
            select(IntelDocument.content)
            .where(IntelDocument.task_id == task_id)
            .order_by(IntelDocument.quality_score.desc())
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all() if row[0]]

    async def _persist_keywords(
        self,
        session: AsyncSession,
        task_id: UUID,
        candidates: list[KeywordCandidate],
    ) -> list[Keyword]:
        keywords: list[Keyword] = []
        for c in candidates:
            kw = Keyword(
                task_id=task_id,
                word=c.word,
                type=c.keyword_type,
                weight=c.weight,
                confidence=c.confidence,
                source=c.source,
                derived=c.derived,
                used_in_dsl=False,
            )
            session.add(kw)
            keywords.append(kw)
        await session.flush()
        return keywords

    @staticmethod
    def _kw_to_candidate(kw: Keyword) -> KeywordCandidate:
        return KeywordCandidate(
            word=kw.word,
            keyword_type=kw.type,
            weight=kw.weight,
            confidence=kw.confidence,
            source=kw.source,
            derived=kw.derived,
        )
