from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from .schemas import AssistResponse, QueryRequest
from .dependencies import get_workflow
from src.workflow.graph import Workflow


router = APIRouter(prefix="/api/v1", tags=["AI Assistant"])


@router.post(
    "/assist",
    response_model=AssistResponse,
    responses={
        500: {
            "model": AssistResponse,
            "description": "Internal server error during workflow execution"
        }
    },
)
async def assist(
    request: QueryRequest,
    workflow: Annotated[Workflow, Depends(get_workflow)],
) -> AssistResponse:
    """
    Main AI assistance endpoint that runs a multi-agent workflow.
    """
    try:
        result = await workflow.run(request.query)

        # Robust error checking
        if isinstance(result, str) and (
            result.startswith("Workflow execution failed")
            or "error" in result.lower()
        ):
            raise ValueError(result)

        return AssistResponse(result=result)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "workflow_execution_failed",
                "message": str(exc),
                "query": request.query
            }
        ) from exc
