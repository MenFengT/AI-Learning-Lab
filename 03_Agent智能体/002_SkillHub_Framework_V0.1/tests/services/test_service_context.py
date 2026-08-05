import unittest

from app.services import MCPResponse, ServiceContext


class FakeMCPClient:
    def call(self, request: object) -> MCPResponse:
        raise AssertionError("基础模型测试不应调用MCP")


class FakeAuditService:
    def record(self, event: object) -> None:
        raise AssertionError("基础模型测试不应写入审计")


class FakeRuntimeContext:
    task_id = "task-001"
    trace_id = "trace-001"
    span_id = "span-001"
    skill_id = "local/material_plan@0.2.0"


class FakeServiceConfig:
    default_timeout_seconds = 5.0
    max_timeout_seconds = 30.0


class ServiceContextTests(unittest.TestCase):
    def test_dependencies_are_injected_and_preserved(self) -> None:
        client = FakeMCPClient()
        audit = FakeAuditService()
        runtime = FakeRuntimeContext()
        config = FakeServiceConfig()

        context = ServiceContext(client, audit, runtime, config)

        self.assertIs(context.mcp_client, client)
        self.assertIs(context.audit_service, audit)
        self.assertIs(context.runtime_context, runtime)
        self.assertIs(context.config, config)
        self.assertEqual(vars(context), {
            "mcp_client": client,
            "audit_service": audit,
            "runtime_context": runtime,
            "config": config,
        })

    def test_invalid_runtime_or_config_is_rejected(self) -> None:
        class InvalidRuntime(FakeRuntimeContext):
            skill_id = ""

        class InvalidConfig(FakeServiceConfig):
            default_timeout_seconds = 31.0

        with self.assertRaisesRegex(ValueError, "skill_id"):
            ServiceContext(
                FakeMCPClient(),
                FakeAuditService(),
                InvalidRuntime(),
                FakeServiceConfig(),
            )
        with self.assertRaisesRegex(ValueError, "max_timeout"):
            ServiceContext(
                FakeMCPClient(),
                FakeAuditService(),
                FakeRuntimeContext(),
                InvalidConfig(),
            )


if __name__ == "__main__":
    unittest.main()
