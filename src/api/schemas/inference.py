"""Pydantic schemas for inference API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas ---


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for generation")
    model: str | None = Field(default=None, description="Model name (default from config)")
    system: str | None = Field(default=None, description="System prompt")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)


class ChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(
        ..., min_length=1, description="Chat messages [{role, content}]"
    )
    model: str | None = Field(default=None, description="Model name")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)


class OpenAIChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(
        ..., min_length=1, description="Chat messages [{role, content}]"
    )
    model: str | None = Field(default=None, description="Model name")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32768)


# --- Response schemas ---


class ModelItem(BaseModel):
    name: str
    size: int = 0
    quantization: str = ""
    family: str = ""
    parameter_size: str = ""
    format: str = ""


class ModelListResponse(BaseModel):
    models: list[ModelItem]
    total: int


class ModelDetailResponse(BaseModel):
    name: str
    license: str = ""
    modelfile: str = ""
    parameters: str = ""
    template: str = ""
    details: dict = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    model: str
    response: str
    total_duration_ns: int = 0
    load_duration_ns: int = 0
    prompt_eval_count: int = 0
    eval_count: int = 0
    context: list[int] = Field(default_factory=list)
    done: bool = True


class ChatResponse(BaseModel):
    model: str
    message: dict = Field(default_factory=dict)
    total_duration_ns: int = 0
    load_duration_ns: int = 0
    prompt_eval_count: int = 0
    eval_count: int = 0
    done: bool = True


class OpenAIChatResponse(BaseModel):
    id: str = ""
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: list[dict] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)


class InferenceHealthResponse(BaseModel):
    status: str
    ollama_version: str = ""
    default_model: str = ""
    models_available: int = 0
    latency_ms: float = 0.0
