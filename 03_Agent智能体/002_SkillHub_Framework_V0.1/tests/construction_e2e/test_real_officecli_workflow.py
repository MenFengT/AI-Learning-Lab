from pathlib import Path

import pytest

from app.artifact.models import Artifact, ArtifactStatus
from app.composition.officecli import create_real_officecli_runtime
from app.config.models import (
    ApplicationConfig,
    LLMConfig,
    OfficeConfig,
    SecretValue,
    TelegramConfig,
)
from app.delivery.models import (
    ArtifactDeliveryReference,
    DeliveryReference,
    DeliveryRequest,
    DeliveryStatus,
    DeliveryTarget,
    DeliveryTargetType,
)
from app.delivery.service import ArtifactDeliveryService
from app.demo.construction_demo import (
    create_construction_demo_application,
    run_construction_demo,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_provider import (
    OfficeCLIMCPTransportProvider,
)
from app.mcp_servers.office.runtime.mcp_bridge.sdk_transport import (
    OfficeCLIMCPTransportConfig,
)


OFFICECLI = Path(r"C:\Users\MF\AppData\Local\OfficeCLI\officecli.exe")
PROJECT_ROOT = Path(__file__).parents[2]


class _ArtifactCatalog:
    def __init__(self, artifact: Artifact) -> None:
        self._artifact = artifact

    def get_reference(self, artifact_id, context):
        assert artifact_id == self._artifact.artifact_id
        assert context.task_id == self._artifact.task_id
        return ArtifactDeliveryReference(
            artifact_id=self._artifact.artifact_id,
            task_id=self._artifact.task_id,
            version=self._artifact.version,
            name=self._artifact.name,
        )


class _ReferenceDeliveryTransport:
    def deliver(self, artifact, target, context):
        return DeliveryReference(
            delivery_id="delivery-construction-officecli-001",
            artifact_id=artifact.artifact_id,
            external_reference=f"artifact://{artifact.artifact_id}@{artifact.version}",
            target_type=target.target_type,
        )


class _AllowDelivery:
    def allows(self, artifact, target, context):
        return artifact.task_id == context.task_id


def _config() -> ApplicationConfig:
    return ApplicationConfig(
        environment="integration",
        llm=LLMConfig("test", SecretValue("not-a-real-api-key")),
        office=OfficeConfig(str(OFFICECLI), "1.0.143"),
        telegram=TelegramConfig(False, None),
    )


@pytest.mark.skipif(not OFFICECLI.is_file(), reason="OfficeCLI 1.0.143未安装")
def test_real_construction_document_officecli_artifact_delivery() -> None:
    expected_output = (
        PROJECT_ROOT
        / "workspace"
        / "output"
        / "task-construction-demo-001"
        / "地下室防水施工方案.docx"
    )
    if expected_output.is_file():
        expected_output.unlink()

    provider = OfficeCLIMCPTransportProvider(
        OfficeCLIMCPTransportConfig(str(OFFICECLI))
    )
    transport = provider.create()
    transport.connect()
    try:
        assert transport.contract is not None
        assert transport.contract.server_name == "officecli"
        assert transport.contract.server_version == "1.0.143"
        assert transport.contract.protocol_version == "2024-11-05"
        assert transport.contract.tool_name == "officecli"
    finally:
        transport.close()

    runtime = create_real_officecli_runtime(_config(), PROJECT_ROOT)
    application = create_construction_demo_application(runtime)
    result = run_construction_demo(application=application)
    reference = result.artifact.file_reference
    output = PROJECT_ROOT / "workspace" / reference.relative_path

    try:
        assert output.is_file()
        assert output.read_bytes().startswith(b"PK")
        assert output.suffix.casefold() == ".docx"
        assert reference.file_id.startswith("office-")
        assert reference.version == "1"
        assert len(reference.checksum) == 64
        assert reference.metadata.size == output.stat().st_size
        assert result.artifact.status is ArtifactStatus.COMPLETED

        delivery = ArtifactDeliveryService(
            _ArtifactCatalog(result.artifact),
            _ReferenceDeliveryTransport(),
            _AllowDelivery(),
        ).deliver(
            DeliveryRequest(
                artifact_id=result.artifact.artifact_id,
                task_id=result.runtime_context.task_id,
                runtime_context=result.runtime_context,
                target=DeliveryTarget(
                    DeliveryTargetType.WEB,
                    "construction-demo-user",
                ),
            )
        )
        assert delivery.status is DeliveryStatus.DELIVERED
        assert delivery.artifact_id == result.artifact.artifact_id
        assert delivery.external_reference.startswith("artifact://")
    finally:
        if output.is_file():
            output.unlink()
