from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000,
                       description="User question or command")


class AssistResponse(BaseModel):
    result: str | None = None
    error: str | None = None
