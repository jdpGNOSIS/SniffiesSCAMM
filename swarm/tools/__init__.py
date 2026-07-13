from .http_client import HttpClientTool
from .filesystem import FileSystemTool
from .email_provisioner import EmailProvisionerTool

TOOL_REGISTRY = {
    "http_client": HttpClientTool,
    "filesystem": FileSystemTool,
    "email_provisioner": EmailProvisionerTool,
}

INSTANTIATED = {}


def get_tool(name: str):
    if name in INSTANTIATED:
        return INSTANTIATED[name]
    cls = TOOL_REGISTRY.get(name)
    if cls is None:
        from unittest.mock import AsyncMock
        mock = AsyncMock()
        mock.ensure = AsyncMock()
        INSTANTIATED[name] = mock
        return mock
    instance = cls()
    INSTANTIATED[name] = instance
    return instance
