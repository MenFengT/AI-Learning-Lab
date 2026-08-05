"""Artifact Delivery Layer 异常。"""


class ArtifactDeliveryError(Exception):
    """交付异常基类。"""


class DeliveryRequestError(ArtifactDeliveryError):
    """交付请求契约无效。"""


class DeliveryPermissionError(ArtifactDeliveryError):
    """交付目标或产物访问未授权。"""


class DeliveryTransportError(ArtifactDeliveryError):
    """外部交付通道失败。"""


class DeliveryResultError(ArtifactDeliveryError):
    """交付通道返回结果无效。"""
