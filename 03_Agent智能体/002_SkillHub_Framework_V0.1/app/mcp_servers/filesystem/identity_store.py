"""FileReference稳定身份存储契约与V0.2内存实现。"""

from dataclasses import dataclass
from threading import RLock
from typing import Protocol


@dataclass(frozen=True)
class FileIdentity:
    file_id: str
    version: int
    checksum: str
    source_file_id: str | None = None


class FileIdentityStoreProtocol(Protocol):
    """保存Workspace内部路径与稳定文件身份的映射。"""

    def get(self, identity_key: str) -> FileIdentity | None: ...

    def save(self, identity_key: str, identity: FileIdentity) -> None: ...

    def remove(self, identity_key: str) -> FileIdentity | None: ...

    def move(self, source_key: str, target_key: str) -> FileIdentity: ...


class InMemoryFileIdentityStore:
    """线程安全的进程内实现；可跨Tool实例显式复用。"""

    def __init__(self) -> None:
        self._identities: dict[str, FileIdentity] = {}
        self._lock = RLock()

    def get(self, identity_key: str) -> FileIdentity | None:
        with self._lock:
            return self._identities.get(identity_key)

    def save(self, identity_key: str, identity: FileIdentity) -> None:
        with self._lock:
            self._identities[identity_key] = identity

    def remove(self, identity_key: str) -> FileIdentity | None:
        with self._lock:
            return self._identities.pop(identity_key, None)

    def move(self, source_key: str, target_key: str) -> FileIdentity:
        with self._lock:
            try:
                identity = self._identities.pop(source_key)
            except KeyError as exc:
                raise KeyError(f"文件身份不存在：{source_key}") from exc
            self._identities[target_key] = identity
            return identity
