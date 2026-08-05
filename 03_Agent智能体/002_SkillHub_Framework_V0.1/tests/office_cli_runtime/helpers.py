import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace


TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {
            "type": ["string", "array"],
            "items": {"type": "string"},
        }
    },
    "required": ["command"],
}


def initialize_result(
    *,
    name="officecli",
    version="1.0.143",
    protocol="2024-11-05",
):
    return SimpleNamespace(
        protocolVersion=protocol,
        capabilities=SimpleNamespace(
            tools=SimpleNamespace(listChanged=False)
        ),
        serverInfo=SimpleNamespace(name=name, version=version),
    )


def tools_result(*, name="officecli", schema=None):
    return SimpleNamespace(
        tools=(
            SimpleNamespace(
                name=name,
                inputSchema=schema or TOOL_SCHEMA,
            ),
        )
    )


class FakeSession:
    def __init__(
        self,
        *,
        initialize=None,
        tools=None,
        call_result=None,
        call_delay=0.0,
        call_error=None,
    ) -> None:
        self.initialize_result = initialize or initialize_result()
        self.tools_result = tools or tools_result()
        self.call_result = call_result or SimpleNamespace(
            isError=False,
            content=(SimpleNamespace(type="text", text="ok"),),
        )
        self.call_delay = call_delay
        self.call_error = call_error
        self.calls = []
        self.entered = 0
        self.exited = 0

    async def __aenter__(self):
        self.entered += 1
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exited += 1

    async def initialize(self):
        return self.initialize_result

    async def list_tools(self):
        return self.tools_result

    async def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments))
        if self.call_delay:
            await asyncio.sleep(self.call_delay)
        if self.call_error is not None:
            raise self.call_error
        return self.call_result


class FakeSDK:
    def __init__(self, session=None) -> None:
        self.session = session or FakeSession()
        self.parameters = []
        self.stdio_entered = 0
        self.stdio_exited = 0

    def session_factory(self, read, write):
        return self.session

    def stdio_factory(self, parameters):
        owner = self

        @asynccontextmanager
        async def context():
            owner.parameters.append(parameters)
            owner.stdio_entered += 1
            try:
                yield object(), object()
            finally:
                owner.stdio_exited += 1

        return context()
