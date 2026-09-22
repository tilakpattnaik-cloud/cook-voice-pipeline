from sentence_transformers import SentenceTransformer
import chromadb
import json

MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = "data/chroma_db"
COLLECTION_NAME = "catalog_items"


def build():
    with open("data/catalog/mock_catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)

    seen_items = set()
    seen_brand_item_pairs = set()
    entries = []  # (unique_id, searchable_text, canonical_item)

    for entry in catalog:
        item = entry["item"]
        brand = entry["brand"]

        if item not in seen_items:
            entries.append((f"item::{item}", item, item))
            seen_items.add(item)

        brand_item_key = (brand.lower(), item.lower())
        if brand.lower() != "loose" and brand_item_key not in seen_brand_item_pairs:
            entries.append((f"brand::{brand}::{item}", brand, item))
            seen_brand_item_pairs.add(brand_item_key)

    ids = [e[0] for e in entries]
    documents = [e[1] for e in entries]
    canonical_items = [e[2] for e in entries]

    print(f"Indexing {len(entries)} searchable terms ({len(seen_items)} canonical items + brand aliases)")
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(documents, show_progress_bar=True).tolist()

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=[{"canonical_item": ci} for ci in canonical_items],
    )
    print(f"Stored {len(entries)} embeddings in ChromaDB at {CHROMA_PATH}")


if __name__ == "__main__":
    build()