"""Inference API router — local Ollama inference service endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas.inference import (
    ChatRequest,
    ChatResponse,
    GenerateRequest,
    GenerateResponse,
    InferenceHealthResponse,
    ModelDetailResponse,
    ModelItem,
    ModelListResponse,
    OpenAIChatRequest,
    OpenAIChatResponse,
)
from src.inference.service import get_inference_service
from src.shared.exceptions import LLMError
from src.shared.logger import get_logger

logger = get_logger("inference_router")

router = APIRouter(tags=["inference"])


def _get_service():
    return get_inference_service()


# -- Health -------------------------------------------------------------------


@router.get("/inference/health", response_model=InferenceHealthResponse)
async def inference_health():
    """Check Ollama inference service health."""
    svc = _get_service()
    health = await svc.check_health()
    return InferenceHealthResponse(**health.model_dump())


# -- Models -------------------------------------------------------------------


@router.get("/inference/models", response_model=ModelListResponse)
async def list_models():
    """List all locally available Ollama models."""
    svc = _get_service()
    models = await svc.list_models()
    return ModelListResponse(
        models=[ModelItem(**m.model_dump()) for m in models],
        total=len(models),
    )


@router.get("/inference/models/{model_name:path}", response_model=ModelDetailResponse)
async def model_detail(model_name: str):
    """Get details for a specific model."""
    svc = _get_service()
    try:
        info = await svc.model_info(model_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found: {exc}") from exc
    return ModelDetailResponse(
        name=model_name,
        license=info.get("license", ""),
        modelfile=info.get("modelfile", ""),
        parameters=info.get("parameters", ""),
        template=info.get("template", ""),
        details=info.get("details", {}),
    )


# -- Generate -----------------------------------------------------------------


@router.post("/inference/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    """Generate text using Ollama native generate endpoint."""
    svc = _get_service()
    try:
        result = await svc.generate(
            req.prompt,
            model=req.model,
            system=req.system,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerateResponse(
        model=result.get("model", ""),
        response=result.get("response", ""),
        total_duration_ns=result.get("total_duration", 0),
        load_duration_ns=result.get("load_duration", 0),
        prompt_eval_count=result.get("prompt_eval_count", 0),
        eval_count=result.get("eval_count", 0),
        context=result.get("context", []),
        done=result.get("done", True),
    )


# -- Chat ---------------------------------------------------------------------


@router.post("/inference/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat completion using Ollama native chat endpoint."""
    svc = _get_service()
    try:
        result = await svc.chat(
            req.messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(
        model=result.get("model", ""),
        message=result.get("message", {}),
        total_duration_ns=result.get("total_duration", 0),
        load_duration_ns=result.get("load_duration", 0),
        prompt_eval_count=result.get("prompt_eval_count", 0),
        eval_count=result.get("eval_count", 0),
        done=result.get("done", True),
    )


# -- OpenAI-compatible --------------------------------------------------------


@router.post("/inference/v1/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat(req: OpenAIChatRequest):
    """OpenAI-compatible chat completions via Ollama /v1/chat/completions."""
    svc = _get_service()
    try:
        result = await svc.openai_chat(
            req.messages,
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return OpenAIChatResponse(
        id=result.get("id", ""),
        object=result.get("object", "chat.completion"),
        created=result.get("created", 0),
        model=result.get("model", ""),
        choices=result.get("choices", []),
        usage=result.get("usage", {}),
    )
