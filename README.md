# Multi-Agent Research & Development Assistant

A modular, production-ready multi-agent system powered by local open-source LLMs (via Ollama) and a lightweight custom MCP (Model Context Protocol) server.

Exposed via **FastAPI**, designed with separation of concerns, dependency injection, and SOLID principles.

## Key Features

- Multi-agent architecture with Supervisor + Researcher / Developer / Tester agents
- Local LLM execution (Ollama) → zero external API costs
- Custom lightweight MCP client for tool execution
- FastAPI-based API with clean endpoint `/api/v1/assist`
- Strong focus on testability (heavy mocking, fast unit tests)

## Why a Custom MCP Client? (instead of langchain-mcp-adapters)

- **Dependency Minimization**  
  Built a lightweight MCP client to avoid the overhead of heavy integration libraries, ensuring faster startup times in serverless environments.

- **Custom Schema Control**  
  Implemented a custom Pydantic dynamic model generator to handle non-standard JSON schemas that strict adapters might reject.

- **Resilience Engineering**  
  Integrated manual exponential backoff + connection pooling via `httpx` to handle high-latency custom MCP server environments.

## Main Components

- **MCP Server** — separate FastAPI app providing tools (web search, code execution, ...)
- **Agents** — use LangChain + tools from MCP
- **Workflow** — LangGraph graph with supervisor node
- **API** — single powerful endpoint `/api/v1/assist`

## Quick Start

```bash
# 1. Start Ollama with your model
ollama run llama3.1   # or any model with tool calling support
```

### 2. Start MCP server (provides tools)

```
uvicorn mcp_server.main:app --port 8001
```

### 3. Start main assistant API

```
uvicorn src.api.main:app --port 8000
```

### 3. Start main assistant API4. Test it

```
curl -X POST http://localhost:8000/api/v1/assist \
  -H "Content-Type: application/json" \
  -d '{"query": "Write a small FastAPI CRUD example"}'
```
