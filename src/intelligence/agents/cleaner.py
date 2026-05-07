import hashlib
import logging
import re
from datetime import datetime, timezone

from src.intelligence.config import CleanConfig
from src.intelligence.models import CleanedDocument, RawDocument
from src.intelligence.services.base import BaseRAGClient

logger = logging.getLogger("eakis.intelligence.cleaner")


class CleanerAgent:
    def __init__(self, rag_client: BaseRAGClient) -> None:
        self.rag_client = rag_client
        self._checksums: set[str] = set()

    async def clean(
        self,
        documents: list[RawDocument],
        task_id: str,
        config: CleanConfig | None = None,
    ) -> list[CleanedDocument]:
        config = config or CleanConfig()
        cleaned: list[CleanedDocument] = []

        for doc in documents:
            text = self._strip_html(doc.content)
            checksum = hashlib.sha256(text.encode()).hexdigest()

            if checksum in self._checksums:
                continue
            self._checksums.add(checksum)

            if len(text) < config.min_text_length:
                continue

            score = self._score_quality(text, doc.published_at, config)
            if score < config.min_quality_score:
                continue

            entities = self._extract_entities(text)

            cleaned_doc = CleanedDocument(
                content=text,
                source_type=doc.source_type,
                source_name=doc.source_name,
                source_url=doc.source_url,
                published_at=doc.published_at,
                quality_score=score,
                entities=entities,
                checksum=checksum,
            )
            cleaned.append(cleaned_doc)

        if cleaned:
            await self.rag_client.upsert(cleaned, task_id)
            logger.info("清洗完成：%d/%d 条文档入库，已写入 RAG", len(cleaned), len(documents))

        return cleaned

    def _strip_html(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _score_quality(self, text: str, published_at: datetime | None, config: CleanConfig) -> float:
        score = 1.0

        word_count = len(text)
        if word_count < 100:
            score *= 0.7

        cn_chars = len(re.findall(r"[一-鿿]", text))
        stop_chars = len(re.findall(r"[的了是在我有着与也而这]", text))
        if cn_chars > 0 and stop_chars / cn_chars > config.max_stopword_ratio:
            score *= 0.6

        if published_at:
            days_old = (datetime.now(timezone.utc) - published_at).days
            if days_old > config.staleness_days:
                score *= 0.5

        return round(max(0.0, min(1.0, score)), 2)

    def _extract_entities(self, text: str) -> list[str]:
        entities: list[str] = []

        tech_patterns = [
            r"Spring\s*Boot", r"Docker", r"Kubernetes", r"K8s",
            r"Nginx", r"Redis", r"MySQL", r"PostgreSQL",
            r"React", r"Vue\.?js?", r"Python", r"Java",
            r"Go", r"Rust", r"TypeScript", r"微服务",
            r"分布式", r"容器化", r"DevOps", r"CI/CD",
            r"API", r"REST", r"GraphQL", r"gRPC",
        ]
        for pattern in tech_patterns:
            match = re.search(pattern, text)
            if match:
                entities.append(match.group())

        org_pattern = r"[一-鿿]{2,10}(?:科技|技术|有限公司|集团|公司|网络|信息)"
        for match in re.findall(org_pattern, text):
            entities.append(match)

        return list(dict.fromkeys(entities))[:10]
