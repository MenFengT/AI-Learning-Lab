from .helpers import build_skill, context


def test_runtime_context_is_preserved_for_both_services() -> None:
    skill, content, knowledge = build_skill()
    skill.execute(context())
    content_context = content.requests[0].runtime_context
    knowledge_context = knowledge.requests[0].runtime_context
    for field in ("task_id", "trace_id", "span_id", "skill_id", "user_id"):
        assert getattr(content_context, field) == getattr(knowledge_context, field)
    assert content_context.task_id == "task-construction-001"
    assert content_context.skill_id == "local/construction_document@0.1.0"
