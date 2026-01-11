from enum import Enum


class OllamaModels(Enum):
    """Supported Ollama model identifiers"""

    LLAMA3_8B = "llama3.1:8b"
    LLAMA3_70B = "llama3:70b"
    MISTRAL_7B = "mistral:7b"
    GEMMA_2_9B = "gemma2:9b"


class AppSettings:
    """Central place for all application-level configuration"""

    OLLAMA_MODEL: OllamaModels = OllamaModels.LLAMA3_8B
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MCP_HOST: str = "localhost"
    MCP_PORT: int = 8765
    MCP_SERVER_URL = "http://localhost:8001"
    API_VERSION = "/v1"
