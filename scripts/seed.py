from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.vector_store import LocalVectorStore, MilvusVectorStore


def main() -> None:
    try:
        store = MilvusVectorStore()
        count = store.seed()
        print(f"Seeded Milvus collection with {count} chunks.")
    except Exception as exc:
        local = LocalVectorStore()
        print(f"Milvus is unavailable, local fallback has {len(local.rows)} chunks.")
        print(f"Reason: {exc}")


if __name__ == "__main__":
    main()
