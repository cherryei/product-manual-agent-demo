from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import OUTPUT_DIR, STATIC_DIR
from app.models import AskRequest, AskResponse, PdfResponse
from app.services.answer_engine import answer_question
from app.services.llm import is_llm_enabled
from app.services.pdf_manual import generate_manual_pdf
from app.services.products import get_product, list_product_summaries

app = FastAPI(title="Product Manual Agent Demo")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/")
def home(request: Request):
    product = get_product()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": list_product_summaries(),
            "product": product,
            "localized": product["languages"]["en"],
        },
    )


@app.get("/api/products")
def products():
    return list_product_summaries()


@app.post("/api/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    try:
        answer, language, product_id, sources = answer_question(
            payload.question,
            product_id=payload.product_id,
            language=payload.language,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AskResponse(
        answer=answer,
        language=language,
        product_id=product_id,
        sources=[source.to_dict() for source in sources],
    )


@app.post("/api/manual/{product_id}/pdf", response_model=PdfResponse)
def create_pdf(product_id: str):
    try:
        path = generate_manual_pdf(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PdfResponse(
        product_id=product_id,
        path=str(path),
        download_url=f"/downloads/{path.name}",
    )


@app.get("/downloads/{filename}")
def download(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": is_llm_enabled()}
