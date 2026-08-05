"""Document V0.3 Prompt加载器兼容实现；新流程由ContentService管理模板。"""

from importlib.resources import files

from .errors import PromptLoadError


class PackagePromptLoader:
    """只读取随Document包发布的固定Markdown模板。"""

    ALLOWED_TEMPLATES = frozenset({"proposal", "report", "paper"})

    def load(self, template_name: str) -> str:
        if template_name not in self.ALLOWED_TEMPLATES:
            raise PromptLoadError(f"不支持的Prompt模板：{template_name}")
        content = (
            files("app.skills.document.prompts")
            .joinpath(f"{template_name}.md")
            .read_text(encoding="utf-8")
            .strip()
        )
        if not content:
            raise PromptLoadError(f"Prompt模板为空：{template_name}")
        return content
