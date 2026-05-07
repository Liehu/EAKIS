import pytest

from src.intelligence.models import SourceCategory
from src.intelligence.module import IntelligenceModule


@pytest.mark.asyncio
async def test_module_full_run():
    module = IntelligenceModule()
    result = await module.run(
        task_id="test-task-001",
        company_name="XX支付科技有限公司",
        industry="fintech",
        keywords=["XX支付", "Spring Boot"],
        domains=["xx-payment.com"],
    )
    assert result.task_id == "test-task-001"
    assert result.status.value in ("completed", "partial_failure")
    assert result.total_sources > 0
    assert result.total_documents >= 0
    assert result.cleaned_documents >= 0


@pytest.mark.asyncio
async def test_module_get_status():
    module = IntelligenceModule()
    await module.run(task_id="test-002", company_name="XX科技")
    status = module.get_status()
    assert status["status"] in ("completed", "partial_failure")
    assert len(status["sources"]) > 0


@pytest.mark.asyncio
async def test_module_get_documents():
    module = IntelligenceModule()
    await module.run(task_id="test-003", company_name="XX科技")
    docs = module.get_documents()
    assert isinstance(docs, list)
    for d in docs:
        assert "content" in d
        assert "quality_score" in d


@pytest.mark.asyncio
async def test_module_get_dsl():
    module = IntelligenceModule()
    await module.run(
        task_id="test-004",
        company_name="XX科技",
        keywords=["XX科技"],
        domains=["xx-tech.com"],
    )
    dsl = module.get_dsl_queries()
    assert isinstance(dsl, list)


@pytest.mark.asyncio
async def test_module_get_sources():
    module = IntelligenceModule()
    await module.run(task_id="test-005", company_name="XX科技")
    sources = module.get_sources()
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert "source_id" in sources[0]


@pytest.mark.asyncio
async def test_module_filter_by_category():
    module = IntelligenceModule()
    result = await module.run(
        task_id="test-006",
        company_name="XX科技",
        enabled_categories=[SourceCategory.NEWS],
    )
    assert result.total_sources > 0
