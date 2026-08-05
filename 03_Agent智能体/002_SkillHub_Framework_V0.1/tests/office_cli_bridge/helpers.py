from app.mcp_servers.office.runtime import OfficeCLIRequest
from app.mcp_servers.office.runtime.mcp_bridge import OfficeCLIMCPResult
from tests.office.helpers import file_payload


class RecordingTransport:
    def __init__(self, response=None, error=None) -> None:
        self.response = response or OfficeCLIMCPResult(
            True, {"file": file_payload(), "format": "docx", "metadata": {}}
        )
        self.error = error
        self.calls = []
        self.connect_count = 0
        self.close_count = 0

    def connect(self) -> None:
        self.connect_count += 1

    def call(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.response

    def close(self) -> None:
        self.close_count += 1


class Provider:
    def __init__(self, transport) -> None:
        self.transport = transport
        self.create_count = 0

    def create(self):
        self.create_count += 1
        return self.transport


def request(operation="create_document", arguments=None) -> OfficeCLIRequest:
    return OfficeCLIRequest(
        operation=operation,
        arguments=arguments or {"output_name": "result.docx", "content": {"title": "报告"}},
        task_id="task-001",
        trace_id="trace-001",
        span_id="span-001",
        skill_id="local/document_automation@0.3.0",
    )
