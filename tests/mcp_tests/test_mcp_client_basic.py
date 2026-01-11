import pytest
from src.mcp.client import MCPClient, CommandNotFoundError, MCPError


@pytest.mark.asyncio
async def test_mcp_client_lazy_loading(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)

    # Before access → no request
    assert client._commands is None

    # Access triggers load
    _ = client.commands

    assert len(client.commands) == 3
    assert client._commands is not None
    mock_httpx_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_execute_known_command(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)

    result = client.execute_command("web_search", {"query": "python 3.13"})

    assert "mocked_result" in result
    mock_httpx_client.post.assert_called_once()

    call_args = mock_httpx_client.post.call_args[1]
    assert call_args["json"] == {
        "command": "web_search",
        "parameters": {"query": "python 3.13"}
    }


@pytest.mark.asyncio
async def test_execute_unknown_command_raises(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)

    with pytest.raises(CommandNotFoundError) as exc:
        client.execute_command("magic_nonexistent")

    assert "magic_nonexistent" in str(exc.value)


@pytest.mark.asyncio
async def test_command_without_parameters(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)

    result = client.execute_command("no_params_command")
    assert "mocked_result" in result


@pytest.mark.asyncio
async def test_commands_are_cached(fake_mcp_url, mock_httpx_client):
    client = MCPClient(base_url=fake_mcp_url)

    _ = client.commands
    _ = client.commands

    assert mock_httpx_client.get.call_count == 1
