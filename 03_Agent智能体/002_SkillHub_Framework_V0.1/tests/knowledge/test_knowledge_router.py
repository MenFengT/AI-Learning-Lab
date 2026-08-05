import tempfile
import unittest
from pathlib import Path

from app.knowledge import KnowledgeCategory, KnowledgeRouter


def build_roots(base: Path) -> tuple[Path, Path]:
    domain = base / "domain"
    standards = base / "standards"
    domain.mkdir()
    standards.mkdir()
    (domain / "INDEX.md").write_text(
        "- [domain.concrete](concrete.md) | version=1.2.0 | "
        "timestamp=2026-01-01T00:00:00+00:00 | source=企业施工制度\n",
        encoding="utf-8",
    )
    (domain / "concrete.md").write_text(
        "# 混凝土施工\n混凝土强度要求。\n"
        "<!-- knowledge-rule: concrete.grade=C25 -->",
        encoding="utf-8",
    )
    (standards / "INDEX.md").write_text(
        "- [standard.concrete](standard.md) | version=2.0.0 | "
        "timestamp=2026-02-01T00:00:00+00:00 | source=国家标准\n",
        encoding="utf-8",
    )
    (standards / "standard.md").write_text(
        "# 混凝土标准\n混凝土强制要求。\n"
        "<!-- knowledge-rule: concrete.grade=C30 -->",
        encoding="utf-8",
    )
    return domain, standards


class KnowledgeRouterTests(unittest.TestCase):
    def test_domain_precedes_standards_and_conflicts_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            result = KnowledgeRouter(domain, standards).query("混凝土")

        self.assertEqual(
            result.domain_results[0].source.category,
            KnowledgeCategory.DOMAIN,
        )
        self.assertEqual(
            result.standards_results[0].source.category,
            KnowledgeCategory.STANDARD,
        )
        self.assertEqual(result.conflicts[0].rule_key, "concrete.grade")
        self.assertEqual(result.conflicts[0].domain_value, "C25")
        self.assertEqual(result.conflicts[0].standard_value, "C30")

    def test_index_document_id_query_and_source_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            router = KnowledgeRouter(domain, standards)
            document = router.get_document("domain.concrete")

        self.assertEqual(document.source.document_id, "domain.concrete")
        self.assertEqual(document.source.version, "1.2.0")
        self.assertEqual(
            document.source.timestamp, "2026-01-01T00:00:00+00:00"
        )
        self.assertEqual(document.source.source, "企业施工制度")
        self.assertEqual(
            document.source.fragment_id, "domain.concrete#document"
        )

    def test_index_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            domain = base / "domain"
            domain.mkdir()
            (domain / "INDEX.md").write_text(
                "- [unsafe](../outside.md)\n", encoding="utf-8"
            )
            (base / "outside.md").write_text("unsafe", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "超出根目录"):
                KnowledgeRouter(domain).refresh()

    def test_direct_file_path_is_not_a_document_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            domain, standards = build_roots(Path(directory))
            router = KnowledgeRouter(domain, standards)
            with self.assertRaisesRegex(ValueError, "document_id"):
                router.get_document("../concrete.md")


if __name__ == "__main__":
    unittest.main()
