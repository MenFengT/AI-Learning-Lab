import pytest

from app.mcp_servers.office.runtime import OfficeCLIAdapter, OfficeCLIRequestError

from .helpers import FakeOfficeRuntime, RecordingAudit, context


@pytest.mark.parametrize("arguments", [
    {"path": "C:/secret.docx"},
    {"content": {"command": "remove-all"}},
    {"shell": True},
    {"executable": "office-cli"},
])
def test_command_and_path_parameters_are_rejected(arguments) -> None:
    runtime = FakeOfficeRuntime()
    with pytest.raises(OfficeCLIRequestError):
        OfficeCLIAdapter(runtime, RecordingAudit()).create_document(arguments, context())
    assert runtime.calls == []


def test_arguments_are_isolated_from_caller_mutation() -> None:
    runtime = FakeOfficeRuntime()
    arguments = {"content": {"sections": ["one"]}}
    OfficeCLIAdapter(runtime, RecordingAudit()).create_document(arguments, context())
    arguments["content"]["sections"].append("two")
    assert runtime.calls[0].arguments["content"]["sections"] == ("one",)
