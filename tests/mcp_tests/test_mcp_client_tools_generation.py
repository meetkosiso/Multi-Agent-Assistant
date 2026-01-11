import pytest
from langchain_core.tools import StructuredTool
from src.mcp.client import MCPClient


@pytest.mark.asyncio
async def test_get_tools_creates_valid_structured_tools(fake_mcp_url, mock_httpx_client, sample_commands):
    client = MCPClient(base_url=fake_mcp_url)
    tools = client.get_tools()

    assert len(tools) == len(sample_commands)
    assert all(isinstance(t, StructuredTool) for t in tools)

    # Check names
    tool_names = {t.name for t in tools}
    assert tool_names == {"web_search", "calculator", "no_params_command"}

    # Check one concrete tool
    search_tool = next(t for t in tools if t.name == "web_search")
    assert search_tool.description == "Search the internet"

    # Check schema existence
    assert search_tool.args_schema is not None
    assert "query" in search_tool.args_schema.model_fields


@pytest.mark.asyncio
async def test_tool_function_calls_execute(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)
    tools = client.get_tools()

    search_tool = next(t for t in tools if t.name == "web_search")

    result = search_tool.func(query="test query")

    assert "mocked_result" in result
    mock_httpx_client.post.assert_called()
