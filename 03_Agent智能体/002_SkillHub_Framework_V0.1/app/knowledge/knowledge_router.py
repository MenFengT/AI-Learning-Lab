"""MD + INDEX知识入口，固定执行Domain优先、Standards补充。"""

from datetime import datetime, timezone
from pathlib import Path
import re

from .models import (
    KnowledgeCategory,
    KnowledgeConflict,
    KnowledgeDocument,
    KnowledgeQueryResult,
    SourceReference,
)


class KnowledgeRouter:
    """只读取已注册Markdown文档，不接受调用方文件路径。"""

    LINK_PATTERN = re.compile(r"\[([^]]+)]\(([^)]+\.md)\)(.*)$")
    METADATA_PATTERN = re.compile(r"\|\s*([a-z_]+)\s*=\s*([^|]+)")
    RULE_PATTERN = re.compile(
        r"<!--\s*knowledge-rule:\s*([a-zA-Z0-9_.-]+)\s*=\s*([^>]+?)\s*-->"
    )

    def __init__(
        self,
        knowledge_root: Path,
        standards_root: Path | None = None,
    ) -> None:
        self._domain_root = knowledge_root.resolve()
        inferred_standards = knowledge_root.parent / "standards"
        self._standards_root = (standards_root or inferred_standards).resolve()
        self._documents: dict[str, tuple[Path, KnowledgeDocument]] = {}

    def refresh(self) -> None:
        documents: dict[str, tuple[Path, KnowledgeDocument]] = {}
        self._load_index(
            self._domain_root, KnowledgeCategory.DOMAIN, documents
        )
        self._load_index(
            self._standards_root,
            KnowledgeCategory.STANDARD,
            documents,
            optional=True,
        )
        self._documents = documents

    def get(self, name: str) -> str:
        """兼容V0.1：按稳定条目名返回Markdown正文。"""
        return self.get_document(name).content

    def available_entries(self) -> tuple[str, ...]:
        self._ensure_loaded()
        return tuple(self._documents)

    def get_document(self, document_id: str) -> KnowledgeDocument:
        self._validate_document_id(document_id)
        self._ensure_loaded()
        try:
            _, document = self._documents[document_id]
        except KeyError as exc:
            raise KeyError(f"知识文档不存在：{document_id}") from exc
        if document.status != "ACTIVE":
            raise ValueError(f"知识文档不是ACTIVE状态：{document_id}")
        return document

    def get_metadata(self, document_id: str) -> SourceReference:
        return self.get_document(document_id).source

    def search(
        self,
        query_text: str,
        *,
        category: KnowledgeCategory | None = None,
    ) -> tuple[KnowledgeDocument, ...]:
        query = query_text.strip().casefold()
        if not query:
            raise ValueError("知识查询不能为空")
        self._ensure_loaded()
        terms = tuple(term for term in re.split(r"\s+", query) if term)
        matches = []
        for _, document in self._documents.values():
            if document.status != "ACTIVE":
                continue
            if category is not None and document.source.category is not category:
                continue
            searchable = f"{document.title}\n{document.content}".casefold()
            if all(term in searchable for term in terms):
                matches.append(document)
        return tuple(matches)

    def query(self, query_text: str) -> KnowledgeQueryResult:
        """Domain查询永远先于Standards查询。"""
        domain = self.search(query_text, category=KnowledgeCategory.DOMAIN)
        standards = self.search(
            query_text, category=KnowledgeCategory.STANDARD
        )
        return KnowledgeQueryResult(
            domain_results=domain,
            standards_results=standards,
            conflicts=self._detect_conflicts(domain, standards),
        )

    def _load_index(
        self,
        root: Path,
        category: KnowledgeCategory,
        documents: dict[str, tuple[Path, KnowledgeDocument]],
        *,
        optional: bool = False,
    ) -> None:
        index_path = root / "INDEX.md"
        if optional and not index_path.exists():
            return
        try:
            index_content = index_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"知识INDEX读取失败：{category.value}") from exc
        for line in index_content.splitlines():
            match = self.LINK_PATTERN.search(line)
            if match is None:
                continue
            document_id, relative_path, suffix = match.groups()
            self._validate_document_id(document_id)
            if document_id in documents:
                raise ValueError(f"重复document_id：{document_id}")
            path = self._resolve_registered_path(root, relative_path)
            metadata = {
                key: value.strip()
                for key, value in self.METADATA_PATTERN.findall(suffix)
            }
            try:
                content = path.read_text(encoding="utf-8")
                timestamp = metadata.get(
                    "timestamp",
                    datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                )
            except OSError as exc:
                raise ValueError(f"知识文档读取失败：{document_id}") from exc
            source = SourceReference(
                document_id=document_id,
                version=metadata.get("version", "0.1.0"),
                timestamp=timestamp,
                source=metadata.get("source", f"{category.value}:{path.name}"),
                fragment_id=f"{document_id}#document",
                category=category,
            )
            documents[document_id] = (
                path,
                KnowledgeDocument(
                    title=document_id,
                    content=content,
                    source=source,
                    status=metadata.get("status", "ACTIVE").upper(),
                ),
            )

    @staticmethod
    def _resolve_registered_path(root: Path, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute():
            raise ValueError("知识INDEX禁止绝对路径")
        resolved = (root / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"知识路径超出根目录：{relative_path}") from exc
        if resolved.suffix.casefold() != ".md":
            raise ValueError("知识文档必须为Markdown")
        return resolved

    @classmethod
    def _detect_conflicts(
        cls,
        domain: tuple[KnowledgeDocument, ...],
        standards: tuple[KnowledgeDocument, ...],
    ) -> tuple[KnowledgeConflict, ...]:
        domain_rules = cls._rules(domain)
        standard_rules = cls._rules(standards)
        conflicts = []
        for key in sorted(domain_rules.keys() & standard_rules.keys()):
            domain_value, domain_source = domain_rules[key]
            standard_value, standard_source = standard_rules[key]
            if domain_value != standard_value:
                conflicts.append(
                    KnowledgeConflict(
                        rule_key=key,
                        domain_value=domain_value,
                        standard_value=standard_value,
                        domain_source=domain_source,
                        standard_source=standard_source,
                    )
                )
        return tuple(conflicts)

    @classmethod
    def _rules(
        cls, documents: tuple[KnowledgeDocument, ...]
    ) -> dict[str, tuple[str, SourceReference]]:
        rules: dict[str, tuple[str, SourceReference]] = {}
        for document in documents:
            for key, value in cls.RULE_PATTERN.findall(document.content):
                rules[key] = (value.strip(), document.source)
        return rules

    @staticmethod
    def _validate_document_id(document_id: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_.-]*", document_id):
            raise ValueError(f"document_id格式无效：{document_id}")

    def _ensure_loaded(self) -> None:
        if not self._documents:
            self.refresh()
