import pytest
from unittest.mock import Mock
from httpx import Response
from src.mcp.client import Command


@pytest.fixture
def fake_mcp_url():
    return "http://fake-mcp:9999"


@pytest.fixture
def sample_commands():
    return [
        Command(
            name="web_search",
            description="Search the internet",
            parameters={
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        ),
        Command(
            name="calculator",
            description="Simple math calculator",
            parameters={
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        ),
        Command(
            name="no_params_command",
            description="Command without parameters",
            parameters={}
        )
    ]


@pytest.fixture
def mock_httpx_client(mocker, sample_commands):
    """Mock httpx.Client completely"""
    mock_client = mocker.Mock()

    # Mock GET /commands
    mock_get_response = Mock(spec=Response)
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = [
        cmd.model_dump() for cmd in sample_commands]

    mock_client.get.return_value = mock_get_response

    # Mock POST /execute
    mock_post_response = Mock(spec=Response)
    mock_post_response.raise_for_status.return_value = None
    mock_post_response.json.side_effect = lambda: {
        "result": "mocked_result_for_" + str(id(mock_post_response))}

    mock_client.post.return_value = mock_post_response

    mocker.patch("httpx.Client", return_value=mock_client)
    return mock_client
