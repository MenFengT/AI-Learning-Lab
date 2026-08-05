import pytest

from app.mcp_servers.office.runtime import OfficeCLIAdapter, OfficeCLIResponseError

from .helpers import RecordingAudit, context


class InvalidRuntime:
    def create_document(self, request):
        return {"path": "C:/unsafe/result.docx"}


def test_runtime_must_return_managed_file_reference() -> None:
    with pytest.raises(OfficeCLIResponseError):
        OfficeCLIAdapter(InvalidRuntime(), RecordingAudit()).create_document({}, context())
