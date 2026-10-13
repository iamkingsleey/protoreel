"""The MCP server, exercised through a real MCP client connected in-process."""

import json

from mcp import Client

from protoreel.mcp_server import build_server


async def test_tools_are_listed(workspace):
    async with Client(build_server(workspace)) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
    assert {"list_workspace", "record_video", "render_take", "preview_frame", "open_studio", "check_setup"} <= names


async def test_list_workspace_shows_the_prototype(workspace):
    async with Client(build_server(workspace)) as client:
        result = await client.call_tool("list_workspace", {})
    data = result.structured_content or json.loads(result.content[0].text)
    assert "like-button.html" in data["prototypes"]


async def test_record_video_through_mcp(workspace, quick_script):
    async with Client(build_server(workspace)) as client:
        result = await client.call_tool(
            "record_video", {"prototype": "like-button.html", "script": quick_script, "format": "1x1", "fps": 30}
        )
    assert not result.is_error, result.content
    assert "Saved" in result.content[0].text
    assert list(workspace.renders.glob("*.mp4"))


async def test_preview_frame_returns_an_image(workspace):
    async with Client(build_server(workspace)) as client:
        result = await client.call_tool("preview_frame", {"prototype": "like-button.html", "format": "1x1"})
    assert result.content[0].type == "image"


async def test_errors_are_readable(workspace):
    async with Client(build_server(workspace)) as client:
        result = await client.call_tool("record_video", {"prototype": "missing.html", "script": {"actions": []}})
    assert result.is_error and "Could not find" in result.content[0].text
