from fastapi import Depends
from langchain_ollama import OllamaLLM, ChatOllama
from src.mcp.client import MCPClient
from src.core.config import get_settings, Settings
from src.workflow.graph import Workflow


def get_settings_dependency() -> Settings:
    return get_settings()


def get_ollama(settings: Settings = Depends(get_settings_dependency)) -> ChatOllama:
    return ChatOllama(**settings.ollama_config)


def get_mcp_client(settings: Settings = Depends(get_settings_dependency)) -> MCPClient:
    return MCPClient(base_url=settings.MCP_SERVER_URL, api_version=settings.API_VERSION)


def get_workflow(
    llm: OllamaLLM = Depends(get_ollama),
    mcp_client: MCPClient = Depends(get_mcp_client),
) -> Workflow:
    return Workflow(
        llm=llm,
        mcp_client=mcp_client
    )
