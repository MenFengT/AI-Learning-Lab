import pytest

from app.skills.construction import ConstructionDocumentType

from .helpers import build_skill, context


@pytest.mark.parametrize("document_type", tuple(ConstructionDocumentType))
def test_skill_calls_knowledge_and_content_services(document_type) -> None:
    skill, content, knowledge = build_skill()
    result = skill.execute(context(document_type))
    assert "地下室施工技术方案" in result
    assert len(knowledge.requests) == 1
    assert len(content.requests) == 1
    content_request = content.requests[0]
    assert content_request.document_type == "report"
    assert content_request.metadata["construction_document_type"] == document_type.value
    assert content_request.metadata["knowledge_sources"] == ("domain-construction-001",)
    assert content_request.requested_sections
