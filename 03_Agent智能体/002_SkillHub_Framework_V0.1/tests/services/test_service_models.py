import unittest

from app.services import MCPRequest, MCPResponse, ServiceResult


class FakeRuntimeContext:
    task_id = "task-001"
    trace_id = "trace-001"
    span_id = "span-001"
    skill_id = "local/material_plan@0.2.0"


class ServiceModelsTests(unittest.TestCase):
    def test_service_result_success_contract(self) -> None:
        source_data = {"result": {"items": ["ok"]}}
        result = ServiceResult[dict[str, str]](
            success=True,
            data=source_data,
            error_code=None,
            message="执行成功",
            trace_id="trace-001",
            metadata={"source": "test"},
        )
        source_data["result"]["items"].append("changed")

        self.assertTrue(result.success)
        self.assertIsNone(result.error_code)
        self.assertEqual(result.schema_version, "0.1")
        self.assertEqual(result.data, {"result": {"items": ["ok"]}})

    def test_service_result_failure_requires_error_code(self) -> None:
        with self.assertRaisesRegex(ValueError, "必须包含error_code"):
            ServiceResult[None](
                success=False,
                data=None,
                error_code=None,
                message="执行失败",
                trace_id="trace-001",
            )

        result = ServiceResult[None](
            success=False,
            data=None,
            error_code="SHF-SVC-FILE-NOT_FOUND",
            message="文件不存在",
            trace_id="trace-001",
        )
        self.assertFalse(result.success)

    def test_request_arguments_are_deeply_isolated_and_immutable(self) -> None:
        arguments = {"document": {"pages": [1, 2]}}
        request = MCPRequest(
            server_name="office-server",
            tool_name="read-document",
            arguments=arguments,
            runtime_context=FakeRuntimeContext(),
            timeout=5.0,
        )
        arguments["document"]["pages"].append(3)

        self.assertEqual(request.arguments["document"]["pages"], (1, 2))
        with self.assertRaises(TypeError):
            request.arguments["document"] = {}

    def test_response_contract_and_metadata_isolation(self) -> None:
        metadata = {"source": {"pages": [1]}}
        response = MCPResponse(
            success=True,
            content={"value": "ok"},
            error_code=None,
            message="调用成功",
            server_name="office-server",
            tool_name="read-document",
            trace_id="trace-001",
            span_id="span-002",
            duration_ms=10.5,
            attempts=1,
            metadata=metadata,
        )
        metadata["source"]["pages"].append(2)

        self.assertEqual(response.metadata["source"]["pages"], (1,))
        self.assertEqual(response.attempts, 1)

    def test_sensitive_metadata_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "敏感字段"):
            ServiceResult[None](
                success=True,
                data=None,
                error_code=None,
                message="执行成功",
                trace_id="trace-001",
                metadata={"authorization": "secret-value"},
            )


if __name__ == "__main__":
    unittest.main()
