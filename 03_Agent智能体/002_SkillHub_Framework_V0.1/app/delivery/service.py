"""Artifact引用到DeliveryReference的无文件访问交付服务。"""

from .errors import (
    DeliveryPermissionError,
    DeliveryResultError,
    DeliveryTransportError,
)
from .models import DeliveryRequest, DeliveryResult, DeliveryStatus
from .protocols import (
    ArtifactDeliveryCatalogProtocol,
    DeliveryAccessPolicyProtocol,
    DeliveryTransportProtocol,
)


class ArtifactDeliveryService:
    """仅编排引用、权限与交付端口，不读取产物文件。"""

    def __init__(
        self,
        artifact_catalog: ArtifactDeliveryCatalogProtocol,
        transport: DeliveryTransportProtocol,
        access_policy: DeliveryAccessPolicyProtocol,
    ) -> None:
        self._artifact_catalog = artifact_catalog
        self._transport = transport
        self._access_policy = access_policy

    def deliver(self, request: DeliveryRequest) -> DeliveryResult:
        if not isinstance(request, DeliveryRequest):
            raise TypeError("request必须是DeliveryRequest")
        artifact = self._artifact_catalog.get_reference(
            request.artifact_id, request.runtime_context
        )
        if artifact.artifact_id != request.artifact_id or artifact.task_id != request.task_id:
            raise DeliveryPermissionError("Artifact引用与交付任务不一致")
        if not self._access_policy.allows(
            artifact, request.target, request.runtime_context
        ):
            raise DeliveryPermissionError("Artifact交付未授权")
        try:
            reference = self._transport.deliver(
                artifact, request.target, request.runtime_context
            )
        except DeliveryPermissionError:
            raise
        except Exception as exc:
            raise DeliveryTransportError("交付通道调用失败") from exc
        if reference.artifact_id != artifact.artifact_id:
            raise DeliveryResultError("交付结果Artifact引用不一致")
        return DeliveryResult(
            delivery_id=reference.delivery_id,
            artifact_id=artifact.artifact_id,
            external_reference=reference.external_reference,
            status=DeliveryStatus.DELIVERED,
            metadata={
                "artifact_version": artifact.version,
                "target_type": request.target.target_type.value,
            },
        )
