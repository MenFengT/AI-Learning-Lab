import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class KnowledgeBoundaryTests(unittest.TestCase):
    def test_service_does_not_access_router_or_files(self) -> None:
        service_root = PROJECT_ROOT / "app" / "services" / "knowledge"
        forbidden = ("app.knowledge", "pathlib", "os", "subprocess")
        for path in service_root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            violations = [
                name for name in imports if name.startswith(forbidden)
            ]
            self.assertEqual(violations, [], f"{path.name}: {violations}")

    def test_service_does_not_depend_directly_on_mcp_client(self) -> None:
        service_path = (
            PROJECT_ROOT / "app" / "services" / "knowledge" / "service.py"
        )
        source = service_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(service_path))
        imported_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.append(node.module)

        self.assertNotIn("MCPClientProtocol", source)
        self.assertNotIn("_mcp_client", source)
        self.assertFalse(
            any(name.startswith("app.services.mcp") for name in imported_names)
        )
        self.assertIn("ServiceCallExecutorProtocol", source)

    def test_skills_do_not_access_knowledge_or_mcp(self) -> None:
        skills_root = PROJECT_ROOT / "app" / "skills"
        for path in skills_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("app.knowledge", source)
            self.assertNotIn("services.mcp", source)

    def test_no_rag_or_database_dependencies_are_introduced(self) -> None:
        roots = [
            PROJECT_ROOT / "app" / "services" / "knowledge",
            PROJECT_ROOT / "app" / "knowledge",
            PROJECT_ROOT / "app" / "mcp_servers" / "knowledge",
        ]
        forbidden = ("langchain", "embedding", "vector", "sqlalchemy", "redis")
        for root in roots:
            for path in root.glob("*.py"):
                source = path.read_text(encoding="utf-8").casefold()
                violations = [item for item in forbidden if item in source]
                self.assertEqual(violations, [], f"{path.name}: {violations}")


if __name__ == "__main__":
    unittest.main()
