from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Type, Union

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, ValidationError, create_model
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.constants import AppSettings


class Endpoint(Enum):
    """Centralized API endpoint paths"""

    COMMANDS = "/commands"
    EXECUTE = "/execute"


class MCPError(Exception):
    """Base exception for MCP client errors"""
    pass


class CommandNotFoundError(MCPError):
    """Raised when trying to execute non-existent command"""
    pass


class Command(BaseModel):
    """Represents a single command from the MCP server"""

    name: str = Field(..., description="Unique command identifier")
    description: str = Field(..., description="Human-readable description")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON schema properties for command parameters"
    )

    @property
    def has_parameters(self) -> bool:
        return bool(self.parameters.get("properties"))


class MCPClient:
    """
    Client for interacting with MCP (Model Context Protocol) API.

    Features:
    - Lazy loading of commands with caching
    - Retry logic on network failures
    - Proper error handling & custom exceptions
    - Centralized endpoint management with Enum
    - Dynamic Pydantic models for tool schemas
    - Context manager support
    """

    def __init__(
        self,
        base_url: str = AppSettings.MCP_SERVER_URL,
        api_version: str = AppSettings.API_VERSION,
        timeout: float = 15.0,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version.strip("/")
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries

        self._http_client = httpx.Client(
            base_url=f"{self.base_url}/{self.api_version}",
            timeout=self.timeout,
            follow_redirects=True
        )

        # Lazy loading
        self._commands: List[Command] | None = None
        self._command_map: Dict[str, Command] | None = None

    @property
    def commands(self) -> List[Command]:
        """Lazily loaded and cached commands list"""
        if self._commands is None:
            self._load_commands()
        return self._commands  # type: ignore[return-value]

    @property
    def command_map(self) -> Dict[str, Command]:
        """Name → Command lookup dictionary"""
        if self._command_map is None:
            self._command_map = {cmd.name: cmd for cmd in self.commands}
        return self._command_map

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True
    )
    def _load_commands(self) -> None:
        """Fetch available commands from server"""
        try:
            response = self._http_client.get(str(Endpoint.COMMANDS.value))
            response.raise_for_status()

            raw_commands = response.json()
            if not isinstance(raw_commands, list):
                raise ValueError("Expected list of commands from server")

            self._commands = [Command.model_validate(
                cmd) for cmd in raw_commands]
            # Invalidate map cache
            self._command_map = None

        except httpx.HTTPStatusError as e:
            raise MCPError(
                f"Failed to fetch commands: {e.response.status_code}") from e
        except (ValidationError, ValueError) as e:
            raise MCPError(
                "Invalid command schema received from server") from e

    def execute_command(
        self,
        command_name: str,
        parameters: Dict[str, Any] | None = None
    ) -> Any:
        """
        Execute a command on the MCP server

        Raises:
            CommandNotFoundError: When command doesn't exist
            MCPError: On network/server errors
        """
        if command_name not in self.command_map:
            raise CommandNotFoundError(f"Command not found: {command_name}")

        payload = {
            "command": command_name,
            "parameters": parameters or {}
        }

        try:
            response = self._http_client.post(
                str(Endpoint.EXECUTE.value),
                json=payload
            )
            response.raise_for_status()
            return response.json()["result"]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CommandNotFoundError(
                    f"Command execution failed - not found: {command_name}"
                ) from e
            raise MCPError(
                f"Command execution failed: {e.response.status_code}") from e

    def get_tools(self) -> List[StructuredTool]:
        """Convert all available commands to LangChain StructuredTools"""
        tools = []

        # Helper to convert JSON schema type string to Python type
        def json_type_to_py_type(json_type: Union[str, List[str], Dict[str, Any]]) -> Type[Any]:
            if isinstance(json_type, str):
                mapping = {
                    "string": str,
                    "number": float,
                    "integer": int,
                    "boolean": bool,
                    "array": List,
                    "object": Dict,
                    "null": type(None)
                }
                return mapping.get(json_type, Any)

            if isinstance(json_type, list):
                # Union type or nullable
                types = [json_type_to_py_type(t) for t in json_type]
                if type(None) in types:
                    types.remove(type(None))
                    if len(types) == 1:
                        from typing import Optional
                        return Optional[types[0]]
                from typing import Union
                return Union[tuple(types)] if types else Any

            return Any  # fallback

        for cmd in self.commands:
            if not cmd.has_parameters:
                # No parameters → empty schema
                schema_class = create_model(
                    f"{cmd.name}Params",
                    __base__=BaseModel
                )
            else:
                # Build proper Pydantic fields dynamically
                fields: Dict[str, tuple[Type[Any], Any]] = {}
                properties = cmd.parameters.get("properties", {})
                required = set(cmd.parameters.get("required", []))

                for field_name, field_info in properties.items():
                    py_type = json_type_to_py_type(
                        field_info.get("type", "string"))

                    # Prepare Field kwargs
                    field_kwargs: Dict[str, Any] = {}
                    if "description" in field_info:
                        field_kwargs["description"] = field_info["description"]
                    if "enum" in field_info:
                        field_kwargs["enum"] = field_info["enum"]

                    # Required vs optional
                    if field_name in required:
                        fields[field_name] = (py_type, Field(**field_kwargs))
                    else:
                        default = field_info.get("default", ...)
                        fields[field_name] = (py_type, Field(
                            default=default, **field_kwargs))

                # Create the actual model
                schema_class = create_model(
                    f"{cmd.name}Params",
                    __base__=BaseModel,
                    **fields
                )

            # Create the tool function
            def make_tool_func(command_name: str):
                def tool_func(**kwargs) -> str:
                    result = self.execute_command(command_name, kwargs)
                    return str(result)

                return tool_func

            tool = StructuredTool.from_function(
                func=make_tool_func(cmd.name),
                name=cmd.name,
                description=cmd.description,
                args_schema=schema_class,
                return_direct=True,
                coroutine=None
            )
            tools.append(tool)

        return tools

    def close(self) -> None:
        """Close underlying HTTP client"""
        self._http_client.close()

    def __enter__(self) -> 'MCPClient':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
