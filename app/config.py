import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional at runtime
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parents[1]
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "app" / "static"

PRODUCTS_FILE = DATA_DIR / "products.json"
FURNITURE_PRODUCTS_FILE = DATA_DIR / "furniture_products.json"
ALIASES_FILE = DATA_DIR / "language_aliases.json"

MILVUS_HOST = "127.0.0.1"
MILVUS_PORT = "19530"
MILVUS_COLLECTION = "product_manual_chunks"
EMBEDDING_DIM = 384

SUPPORTED_LANGUAGES = ["en", "de", "it", "fr", "es", "jp", "cn"]

MODEL_PROVIDER = os.getenv("MANUAL_AGENT_MODEL_PROVIDER", "local").lower()
MODEL_BASE_URL = os.getenv("MANUAL_AGENT_MODEL_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MANUAL_AGENT_MODEL_NAME", "")
MODEL_API_KEY = os.getenv("MANUAL_AGENT_MODEL_API_KEY", os.getenv("OPENAI_API_KEY", ""))
MODEL_TIMEOUT_SECONDS = float(os.getenv("MANUAL_AGENT_MODEL_TIMEOUT_SECONDS", "12"))

FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
]
