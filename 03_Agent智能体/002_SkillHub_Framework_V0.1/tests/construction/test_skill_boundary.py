import ast
from pathlib import Path


SKILL_PATH = Path(__file__).parents[2] / "app" / "skills" / "construction" / "skill.py"


def test_construction_skill_has_no_forbidden_dependencies() -> None:
    tree = ast.parse(SKILL_PATH.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    forbidden = (
        "app.services.office", "app.services.filesystem", "app.services.mcp",
        "app.mcp_servers", "app.tools", "app.knowledge", "app.artifact",
        "app.skills.document",
    )
    assert not any(name.startswith(prefix) for name in imports for prefix in forbidden)


def test_skill_class_only_calls_allowed_services() -> None:
    tree = ast.parse(SKILL_PATH.read_text(encoding="utf-8"))
    skill_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ConstructionDocumentSkill"
    )
    source = ast.unparse(skill_class).casefold()
    forbidden = ("open(", "files(", "mcp", "office", "filesystem", ".execute(")
    assert all(token not in source for token in forbidden)
    assert "_knowledge_service.query(" in source
    assert "_content_service.generate_content(" in source
