import pytest

from app.mcp_servers.office.runtime import OfficeCLIAdapter, OfficeCLIInvocationError

from .helpers import FakeOfficeRuntime, RecordingAudit, context


def test_runtime_context_and_audit_are_preserved() -> None:
    audit = RecordingAudit()
    runtime = FakeOfficeRuntime()

    OfficeCLIAdapter(runtime, audit).create_document({"output_name": "result.docx"}, context())

    request = runtime.calls[0]
    assert (request.task_id, request.trace_id, request.span_id, request.skill_id) == (
        "task-001", "trace-001", "span-001", "local/document_automation@0.3.0"
    )
    assert [event.metadata["event_type"] for event in audit.events] == [
        "OFFICE_CLI_STARTED", "OFFICE_CLI_SUCCEEDED"
    ]


class FailingRuntime(FakeOfficeRuntime):
    def create_document(self, request):
        raise RuntimeError("vendor details")


def test_external_exception_is_standardized_and_audited() -> None:
    audit = RecordingAudit()
    with pytest.raises(OfficeCLIInvocationError) as captured:
        OfficeCLIAdapter(FailingRuntime(), audit).create_document({}, context())
    assert captured.value.error_code == "SHF-OFFICE-CLI-INVOCATION_FAILED"
    assert audit.events[-1].error_code == "SHF-OFFICE-CLI-INVOCATION_FAILED"
    assert audit.events[-1].metadata["event_type"] == "OFFICE_CLI_FAILED"
