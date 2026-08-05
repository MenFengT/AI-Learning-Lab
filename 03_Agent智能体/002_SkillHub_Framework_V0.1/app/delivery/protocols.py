"""Artifact Delivery Layer 依赖端口。"""

from typing import Protocol, runtime_checkable

from app.runtime.invocation_context import InvocationContext

from .models import (
    ArtifactDeliveryReference,
    DeliveryReference,
    DeliveryRequest,
    DeliveryResult,
    DeliveryTarget,
)


@runtime_checkable
class ArtifactDeliveryServiceProtocol(Protocol):
    def deliver(self, request: DeliveryRequest) -> DeliveryResult: ...


@runtime_checkable
class ArtifactDeliveryCatalogProtocol(Protocol):
    """只返回最小Artifact引用，不向交付层暴露Artifact或FileReference。"""

    def get_reference(
        self, artifact_id: str, context: InvocationContext
    ) -> ArtifactDeliveryReference: ...


@runtime_checkable
class DeliveryTransportProtocol(Protocol):
    def deliver(
        self,
        artifact: ArtifactDeliveryReference,
        target: DeliveryTarget,
        context: InvocationContext,
    ) -> DeliveryReference: ...


@runtime_checkable
class DeliveryAccessPolicyProtocol(Protocol):
    def allows(
        self,
        artifact: ArtifactDeliveryReference,
        target: DeliveryTarget,
        context: InvocationContext,
    ) -> bool: ...
