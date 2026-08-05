"""地下室防水施工方案示例输入。"""

from app.skills.construction import (
    ConstructionDocumentRequest,
    ConstructionDocumentType,
)


def create_basement_waterproofing_request(
    *,
    project_name: str = "示例建筑工程",
    construction_part: str = "地下室底板、外墙及顶板",
    requirements: str = "生成地下室防水施工方案",
) -> ConstructionDocumentRequest:
    """使用现有 Skill 契约封装施工部位，不扩展或破坏协议字段。"""
    return ConstructionDocumentRequest(
        project_name=project_name,
        document_type=ConstructionDocumentType.CONSTRUCTION_SCHEME,
        title="地下室防水施工方案",
        requirements=requirements,
        knowledge_query="施工方案",
        metadata={"construction_part": construction_part},
    )
