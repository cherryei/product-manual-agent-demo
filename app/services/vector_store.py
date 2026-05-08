from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from app.config import EMBEDDING_DIM, MILVUS_COLLECTION, MILVUS_HOST, MILVUS_PORT
from app.services.embedding import cosine_similarity, embed_text
from app.services.products import product_chunks


_STORE_CACHE: Optional[Union["LocalVectorStore", "MilvusVectorStore"]] = None

SECTION_KEYWORDS = {
    "installation": [
        "assemble",
        "assembly",
        "install",
        "montage",
        "montieren",
        "montare",
        "montar",
        "組み立て",
        "安装",
        "组装",
    ],
    "safety": ["safe", "safety", "warning", "danger", "sicher", "sicurezza", "seguridad", "安全", "警告"],
    "care": ["clean", "care", "maintain", "pflege", "cura", "entretien", "cuidado", "手入れ", "保养", "清洁"],
    "specs": ["size", "dimension", "weight", "load", "masse", "dimensioni", "dimensions", "仕様", "尺寸", "重量"],
}


def section_boost(query: str, section: str) -> float:
    lowered = query.lower()
    keywords = SECTION_KEYWORDS.get(section, [])
    return 0.18 if any(keyword in lowered for keyword in keywords) else 0.0


@dataclass
class SearchResult:
    product_id: str
    language: str
    section: str
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "language": self.language,
            "section": self.section,
            "text": self.text,
            "score": round(self.score, 4),
        }


class LocalVectorStore:
    def __init__(self) -> None:
        self.rows = [
            {
                **chunk,
                "embedding": embed_text(
                    f"{chunk['product_id']} {chunk['language']} {chunk['section']} {chunk.get('search_text', chunk['text'])}"
                ),
            }
            for chunk in product_chunks()
        ]

    def search(
        self,
        query: str,
        *,
        product_id: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 4,
    ) -> list[SearchResult]:
        query_embedding = embed_text(query)
        candidates = self.rows
        if product_id:
            candidates = [row for row in candidates if row["product_id"] == product_id]
        if language:
            preferred = [row for row in candidates if row["language"] == language]
            candidates = preferred or candidates
        scored = [
            SearchResult(
                product_id=row["product_id"],
                language=row["language"],
                section=row["section"],
                text=row["text"],
                score=cosine_similarity(query_embedding, row["embedding"])
                + section_boost(query, row["section"]),
            )
            for row in candidates
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]


class MilvusVectorStore:
    def __init__(self) -> None:
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

        self.Collection = Collection
        self.utility = utility
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT, timeout=3)

        if not utility.has_collection(MILVUS_COLLECTION):
            fields = [
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="product_id", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=16),
                FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            ]
            schema = CollectionSchema(fields, description="Product manual chunks")
            self.collection = Collection(MILVUS_COLLECTION, schema=schema)
            self.collection.create_index(
                field_name="embedding",
                index_params={"metric_type": "IP", "index_type": "AUTOINDEX", "params": {}},
            )
        else:
            self.collection = Collection(MILVUS_COLLECTION)

        self.collection.load()

    def seed(self) -> int:
        if self.collection.num_entities > 0:
            return self.collection.num_entities
        chunks = product_chunks()
        self.collection.insert(
            [
                [chunk["id"] for chunk in chunks],
                [chunk["product_id"] for chunk in chunks],
                [chunk["language"] for chunk in chunks],
                [chunk["section"] for chunk in chunks],
                [chunk["text"][:4096] for chunk in chunks],
                [
                    embed_text(
                        f"{chunk['product_id']} {chunk['language']} {chunk['section']} {chunk.get('search_text', chunk['text'])}"
                    )
                    for chunk in chunks
                ],
            ]
        )
        self.collection.flush()
        self.collection.load()
        return len(chunks)

    def search(
        self,
        query: str,
        *,
        product_id: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 4,
    ) -> list[SearchResult]:
        expr_parts = []
        if product_id:
            expr_parts.append(f'product_id == "{product_id}"')
        if language:
            expr_parts.append(f'language == "{language}"')
        expr = " and ".join(expr_parts) if expr_parts else None
        rows = self.collection.search(
            data=[embed_text(query)],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {}},
            limit=limit,
            expr=expr,
            output_fields=["product_id", "language", "section", "text"],
        )
        results = [
            SearchResult(
                product_id=hit.entity.get("product_id"),
                language=hit.entity.get("language"),
                section=hit.entity.get("section"),
                text=hit.entity.get("text"),
                score=float(hit.score) + section_boost(query, hit.entity.get("section")),
            )
            for hit in rows[0]
        ]
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]


def get_vector_store() -> Union[LocalVectorStore, MilvusVectorStore]:
    global _STORE_CACHE
    if _STORE_CACHE is not None:
        return _STORE_CACHE
    try:
        store = MilvusVectorStore()
        store.seed()
        _STORE_CACHE = store
    except Exception:
        _STORE_CACHE = LocalVectorStore()
    return _STORE_CACHE
