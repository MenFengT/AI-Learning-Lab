"""File Ingestion Layer稳定错误。"""

INGESTION_TASK_MISMATCH = "SHF-INGESTION-REQUEST-TASK_MISMATCH"
INGESTION_REQUEST_INVALID = "SHF-INGESTION-REQUEST-INVALID"
INGESTION_FILESYSTEM_FAILED = "SHF-INGESTION-FILESYSTEM-FAILED"
INGESTION_FILE_NOT_FOUND = "SHF-INGESTION-FILE-NOT_FOUND"
INGESTION_FILE_CONFLICT = "SHF-INGESTION-FILE-CONFLICT"
INGESTION_CHECKSUM_MISMATCH = "SHF-INGESTION-FILE-CHECKSUM_MISMATCH"


class FileIngestionError(RuntimeError):
    """附件登记解析失败，不包含文件内容或内部异常堆栈。"""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class FileIngestionValidationError(FileIngestionError, ValueError):
    """请求、文件身份或checksum不符合契约。"""
