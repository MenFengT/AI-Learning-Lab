from app.skills.construction import ConstructionDocumentType, PackageConstructionTemplateProvider


def test_all_fixed_templates_load() -> None:
    provider = PackageConstructionTemplateProvider()
    for document_type in ConstructionDocumentType:
        template = provider.load(document_type)
        assert template.document_type is document_type
        assert template.sections
        assert tuple(item.order for item in template.sections) == tuple(range(1, len(template.sections) + 1))


def test_construction_scheme_has_required_sections() -> None:
    template = PackageConstructionTemplateProvider().load(
        ConstructionDocumentType.CONSTRUCTION_SCHEME
    )
    assert tuple(item.title for item in template.sections) == (
        "1 工程概况", "2 编制依据", "3 施工准备", "4 施工工艺",
        "5 质量控制", "6 安全文明施工",
    )
