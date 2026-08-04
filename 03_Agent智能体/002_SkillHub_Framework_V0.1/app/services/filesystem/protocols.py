"""FileSystem Service与Security Scanner接口。"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from app.services.models import ServiceResult

from .models import (
    DeleteConfirmation,
    DeleteRequest,
    FileOperationRequest,
    FileOperationResult,
)


@runtime_checkable
class FileSystemServiceProtocol(Protocol):
    def list_files(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def read_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def write_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def copy_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def move_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def rename_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...
    def request_delete(self, request: DeleteRequest) -> ServiceResult[DeleteConfirmation]: ...
    def confirm_delete(self, request: DeleteRequest) -> ServiceResult[FileOperationResult]: ...
    def archive_file(self, request: FileOperationRequest) -> ServiceResult[FileOperationResult]: ...


class SecurityScanStatus(str, Enum):
    CLEAN = "CLEAN"
    SUSPICIOUS = "SUSPICIOUS"
    INFECTED = "INFECTED"
    ERROR = "ERROR"
    NOT_SCANNED = "NOT_SCANNED"


@dataclass(frozen=True)
class SecurityScanResult:
    status: SecurityScanStatus
    file_id: str
    version: str
    checksum: str


@runtime_checkable
class SecurityScannerProtocol(Protocol):
    def scan(self, file_id: str, version: str, checksum: str) -> SecurityScanResult: ...
