from typing import Any, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    product_id: Optional[str] = None
    language: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    language: str
    product_id: str
    sources: list[dict[str, Any]]


class PdfRequest(BaseModel):
    languages: Optional[list[str]] = None


class PdfResponse(BaseModel):
    product_id: str
    path: str
    download_url: str
    languages: list[str] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    id: str
    category: str
    name: str
    title: str
    languages: list[str]
    deletable: bool
    source: str


class DeleteResponse(BaseModel):
    product_id: str
    deleted: bool
    removed_pdfs: int = 0


class ProductSummary(BaseModel):
    id: str
    category: str
    name: str
    title: str


class UploadManualResponse(BaseModel):
    product_id: str
    original_filename: str
    title: str
    char_count: int
    section_count: int


class LLMConfigRequest(BaseModel):
    provider: str  # "openai-compatible", "anthropic", etc.
    base_url: str
    model_name: str
    api_key: str


class LLMConfigResponse(BaseModel):
    enabled: bool
    provider: str
    base_url: str
    model_name: str
    api_key_configured: bool
    translation_enabled: bool
