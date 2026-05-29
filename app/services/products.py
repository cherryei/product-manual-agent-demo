from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

from app.config import FURNITURE_PRODUCTS_FILE, PRODUCTS_FILE, SUPPORTED_LANGUAGES


def _builtin_products() -> list[dict[str, Any]]:
    products = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    if FURNITURE_PRODUCTS_FILE.exists():
        products.extend(json.loads(FURNITURE_PRODUCTS_FILE.read_text(encoding="utf-8")))
    return products


def _uploaded_products() -> list[dict[str, Any]]:
    """Build product entries from uploaded manual records."""
    from app.services.upload_manual import load_uploaded_manuals

    manuals = load_uploaded_manuals()
    products = []
    for m in manuals:
        entry = m.get("product_entry")
        if entry:
            products.append(entry)
        else:
            products.append(
                {
                    "id": m["product_id"],
                    "category": "uploaded",
                    "image": "",
                    "source_notes": f"Uploaded manual: {m['original_filename']}",
                    "reference_sources": [m["original_filename"]],
                    "languages": {
                        m.get("language", "en"): {
                            "name": m["title"],
                            "title": f"{m['title']} — Uploaded Manual",
                            "summary": f"Uploaded from {m['original_filename']} ({m.get('section_count', 0)} sections).",
                            "bullets": [f"Source: {m['original_filename']}"],
                            "specs": {"Source": m["original_filename"]},
                            "installation": [],
                            "safety": [],
                            "care": [],
                            "faq": [],
                        }
                    },
                }
            )
    return products


@lru_cache
def _cached_builtins() -> list[dict[str, Any]]:
    return _builtin_products()


def load_products() -> list[dict[str, Any]]:
    """Load all products: built-in + uploaded. Returns a new list each call."""
    return [*_cached_builtins(), *_uploaded_products()]


def get_product(product_id: Optional[str] = None) -> dict[str, Any]:
    products = load_products()
    if product_id is None:
        return products[0]
    for product in products:
        if product["id"] == product_id:
            return product
    raise KeyError(f"Unknown product_id: {product_id}")


def list_product_summaries(language: str = "en") -> list[dict[str, str]]:
    summaries = []
    for product in load_products():
        localized = product["languages"].get(language) or product["languages"]["en"]
        summaries.append(
            {
                "id": product["id"],
                "category": product["category"],
                "name": localized["name"],
                "title": localized["title"],
            }
        )
    return summaries


def product_languages(product: dict[str, Any]) -> list[str]:
    """Languages a product has, ordered by SUPPORTED_LANGUAGES first."""
    have = set(product["languages"].keys())
    ordered = [lang for lang in SUPPORTED_LANGUAGES if lang in have]
    ordered += [lang for lang in product["languages"] if lang not in ordered]
    return ordered


def list_documents(language: str = "en") -> list[dict[str, Any]]:
    """Document-management view: every product as a downloadable document."""
    documents = []
    for product in load_products():
        localized = product["languages"].get(language) or product["languages"]["en"]
        is_uploaded = product["category"] == "uploaded"
        documents.append(
            {
                "id": product["id"],
                "category": product["category"],
                "name": localized["name"],
                "title": localized["title"],
                "languages": product_languages(product),
                "deletable": is_uploaded,
                "source": "uploaded" if is_uploaded else "builtin",
            }
        )
    return documents


def _match_score(query: str, value: str) -> int:
    if not value:
        return 0
    query_lower = query.lower()
    value_lower = value.lower()
    if value_lower in query_lower:
        return len(value_lower) * 10
    if any("\u3400" <= char <= "\u9fff" for char in value_lower):
        return sum(1 for char in value_lower if char in query_lower)
    return 0


def match_product_id(query: str, language: str) -> Optional[str]:
    best_product_id: Optional[str] = None
    best_score = 0
    for product in load_products():
        data = product["languages"].get(language) or product["languages"]["en"]
        candidates = [
            product["id"],
            data["name"],
            data["title"],
            *product.get("aliases", {}).get(language, []),
            *product.get("aliases", {}).get("en", []),
        ]
        score = max(_match_score(query, candidate) for candidate in candidates)
        if score > best_score:
            best_score = score
            best_product_id = product["id"]
    return best_product_id if best_score >= 2 else None


def product_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for product in load_products():
        for language, data in product["languages"].items():
            alias_text = " ".join(product.get("aliases", {}).get(language) or product.get("aliases", {}).get("en", []))
            search_prefix = f"{product['id']} {alias_text} {data['name']} {data['title']}"
            chunks.append(
                {
                    "id": f"{product['id']}:{language}:overview",
                    "product_id": product["id"],
                    "language": language,
                    "section": "overview",
                    "text": "\n".join([data["name"], data["title"], data["summary"], *data["bullets"]]),
                    "search_text": "\n".join([search_prefix, data["summary"], *data["bullets"]]),
                }
            )
            chunks.append(
                {
                    "id": f"{product['id']}:{language}:specs",
                    "product_id": product["id"],
                    "language": language,
                    "section": "specs",
                    "text": "\n".join(f"{key}: {value}" for key, value in data["specs"].items()),
                    "search_text": "\n".join([search_prefix, "specs", *[f"{key}: {value}" for key, value in data["specs"].items()]]),
                }
            )
            for section in ["installation", "safety", "care"]:
                chunks.append(
                    {
                        "id": f"{product['id']}:{language}:{section}",
                        "product_id": product["id"],
                        "language": language,
                        "section": section,
                        "text": "\n".join(data[section]),
                        "search_text": "\n".join([search_prefix, section, *data[section]]),
                    }
                )
            chunks.append(
                {
                    "id": f"{product['id']}:{language}:faq",
                    "product_id": product["id"],
                    "language": language,
                    "section": "faq",
                    "text": "\n".join(f"{item['q']} {item['a']}" for item in data["faq"]),
                    "search_text": "\n".join([search_prefix, "faq", *[f"{item['q']} {item['a']}" for item in data["faq"]]]),
                }
            )
    return chunks
