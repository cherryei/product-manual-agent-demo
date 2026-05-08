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


class PdfResponse(BaseModel):
    product_id: str
    path: str
    download_url: str


class ProductSummary(BaseModel):
    id: str
    category: str
    name: str
    title: str
