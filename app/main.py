from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.config import ALLOWED_UPLOAD_EXTENSIONS, OUTPUT_DIR, STATIC_DIR, UPLOAD_DIR
from app.models import (
    AskRequest,
    AskResponse,
    DeleteResponse,
    DocumentSummary,
    LLMConfigRequest,
    LLMConfigResponse,
    PdfRequest,
    PdfResponse,
    UploadManualResponse,
)
from app.services.answer_engine import answer_question
from app.services.llm import is_llm_enabled
from app.services.pdf_manual import generate_manual_pdf, resolve_languages
from app.services.products import get_product, list_documents, list_product_summaries
from app.services.upload_manual import delete_uploaded_manual, is_supported_file, upload_manual

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


@app.get("/api/documents", response_model=list[DocumentSummary])
def documents():
    return list_documents()


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
def create_pdf(product_id: str, payload: Optional[PdfRequest] = None):
    languages = payload.languages if payload else None
    try:
        product = get_product(product_id)
        path = generate_manual_pdf(product_id, languages=languages)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PdfResponse(
        product_id=product_id,
        path=str(path),
        download_url=f"/downloads/{path.name}",
        languages=resolve_languages(product, languages),
    )


@app.delete("/api/manual/{product_id}", response_model=DeleteResponse)
def delete_manual(product_id: str):
    try:
        product = get_product(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if product["category"] != "uploaded":
        raise HTTPException(
            status_code=400,
            detail="Built-in product manuals cannot be deleted. Only uploaded documents can be removed.",
        )
    try:
        result = delete_uploaded_manual(product_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DeleteResponse(
        product_id=product_id,
        deleted=True,
        removed_pdfs=result.get("removed_pdfs", 0),
    )


@app.post("/api/manual/upload", response_model=UploadManualResponse)
async def upload(file: UploadFile = File(...), title: str = Form(default="")):
    if not file.filename or not is_supported_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower()
    dest = UPLOAD_DIR / f"{Path(file.filename).stem}_{int(__import__('time').time())}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    try:
        result = upload_manual(dest, file.filename, title=title or None)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return UploadManualResponse(
        product_id=result["product_id"],
        original_filename=result["original_filename"],
        title=result["title"],
        char_count=result["char_count"],
        section_count=result["section_count"],
    )


@app.get("/downloads/{filename}")
def download(filename: str):
    # 安全检查：防止路径遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = OUTPUT_DIR / filename

    # 调试日志
    import logging
    logging.info(f"Download request: filename={filename}, path={path}, exists={path.exists()}")

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/llm/config", response_model=LLMConfigResponse)
def get_llm_config():
    """获取当前 LLM 配置"""
    from app.config import MODEL_API_KEY, MODEL_BASE_URL, MODEL_NAME, MODEL_PROVIDER
    from app.services.translation import is_translation_enabled

    return LLMConfigResponse(
        enabled=is_llm_enabled(),
        provider=MODEL_PROVIDER,
        base_url=MODEL_BASE_URL,
        model_name=MODEL_NAME,
        api_key_configured=bool(MODEL_API_KEY),
        translation_enabled=is_translation_enabled(),
    )


@app.post("/api/llm/config")
def update_llm_config(payload: LLMConfigRequest):
    """更新 LLM 配置（保存到 .env 文件）"""
    from app.config import BASE_DIR

    env_path = BASE_DIR / ".env"

    # 读取现有 .env 内容
    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text(encoding="utf-8").splitlines()

    # 移除旧的 LLM 配置行
    new_lines = [
        line
        for line in existing_lines
        if not any(
            line.startswith(prefix)
            for prefix in [
                "MANUAL_AGENT_MODEL_PROVIDER=",
                "MANUAL_AGENT_MODEL_BASE_URL=",
                "MANUAL_AGENT_MODEL_NAME=",
                "MANUAL_AGENT_MODEL_API_KEY=",
            ]
        )
    ]

    # 添加新配置
    new_lines.extend(
        [
            f"MANUAL_AGENT_MODEL_PROVIDER={payload.provider}",
            f"MANUAL_AGENT_MODEL_BASE_URL={payload.base_url}",
            f"MANUAL_AGENT_MODEL_NAME={payload.model_name}",
            f"MANUAL_AGENT_MODEL_API_KEY={payload.api_key}",
        ]
    )

    # 写回文件
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return {
        "success": True,
        "message": "LLM configuration saved. Please restart the server for changes to take effect.",
    }


@app.post("/api/llm/test-connection")
def test_llm_connection(payload: dict):
    """测试 LLM 连接并获取可用模型列表"""
    import json
    import urllib.request

    base_url = payload.get("base_url", "").rstrip("/")
    api_key = payload.get("api_key", "")
    provider = payload.get("provider", "openai-compatible")

    if not base_url or not api_key:
        raise HTTPException(status_code=400, detail="base_url and api_key are required")

    try:
        # 尝试获取模型列表
        request = urllib.request.Request(
            f"{base_url}/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = []
            if "data" in data:
                models = [m["id"] for m in data["data"] if isinstance(m, dict) and "id" in m]
            return {"success": True, "models": models, "provider": provider}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")


@app.get("/health")
def health():
    from app.services.translation import is_translation_enabled

    return {
        "status": "ok",
        "llm_enabled": is_llm_enabled(),
        "translation_enabled": is_translation_enabled(),
    }

@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": is_llm_enabled()}
