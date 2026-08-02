import re
from pathlib import Path


class KnowledgeRouter:
    """MD + INDEX 知识入口，未来可替换为 RAG 实现。"""

    LINK_PATTERN = re.compile(r"\[([^]]+)]\(([^)]+\.md)\)")

    def __init__(self, knowledge_root: Path) -> None:
        self._root = knowledge_root.resolve()
        self._index: dict[str, Path] = {}

    def refresh(self) -> None:
        content = (self._root / "INDEX.md").read_text(encoding="utf-8")
        entries: dict[str, Path] = {}
        for name, relative_path in self.LINK_PATTERN.findall(content):
            document_path = (self._root / relative_path).resolve()
            if self._root not in document_path.parents:
                raise ValueError(f"知识路径超出根目录：{relative_path}")
            entries[name] = document_path
        self._index = entries

    def get(self, name: str) -> str:
        if not self._index:
            self.refresh()
        try:
            path = self._index[name]
        except KeyError as exc:
            raise KeyError(f"知识条目不存在：{name}") from exc
        return path.read_text(encoding="utf-8")

    def available_entries(self) -> tuple[str, ...]:
        if not self._index:
            self.refresh()
        return tuple(self._index)
