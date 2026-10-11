import os
from fastapi import APIRouter
from app.schemas import HealthResponse, ModelStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return API health status and model adapter availability."""
    mode = os.getenv("MODEL_INFERENCE_MODE", "offline")
    model_name = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
    
    is_configured = mode in ("local", "hosted")
    
    # In offline mode or MVP baseline, model is optional
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        model_adapter=ModelStatus(
            configured=is_configured,
            mode=mode,
            model_name=model_name if is_configured else None,
            available=False if mode == "offline" else True,
            details=f"Inference mode set to '{mode}'. Local deterministic scanners active."
        )
    )
