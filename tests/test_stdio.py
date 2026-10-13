"""Launch `protoreel mcp` as a subprocess and talk to it over stdio, the way desktop clients do."""

import sys

from mcp import Client, StdioServerParameters


async def test_the_cli_serves_mcp_over_stdio(workspace):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "protoreel", "mcp", "--folder", str(workspace.folder)]
    )
    async with Client(params) as client:
        tools = {tool.name for tool in (await client.list_tools()).tools}
        assert "record_video" in tools
        result = await client.call_tool("list_workspace", {})
        assert not result.is_error
