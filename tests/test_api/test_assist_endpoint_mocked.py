import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_assist_endpoint_mocked_workflow(client, mocker):
    mock_workflow = mocker.AsyncMock()
    mock_workflow.run.return_value = "Fast mocked multi-agent answer"

    with mocker.patch("src.api.dependencies.get_workflow", return_value=mock_workflow):
        response = client.post(
            "/api/v1/assist",
            json={"query": "Say hello in 5 languages"}
        )

        assert response.status_code == 200
        assert response.json()["result"] == "Fast mocked multi-agent answer"
        mock_workflow.run.assert_awaited_once_with("Say hello in 5 languages")


@pytest.mark.asyncio
async def test_assist_validation_error(client):
    response = client.post(
        "/api/v1/assist",
        json={}
    )
    assert response.status_code == 422
