"""
Stores manual passages in ChromaDB and searches them.

Each stored passage carries these details: machine_id, manual_id,
manual_name, revision, page and chunk_id.
"""
from dataclasses import dataclass

import chromadb
from django.conf import settings

from .embeddings import embed_texts

COLLECTION_NAME = "manual_chunks"
BATCH_SIZE = 100

_clients = {}


@dataclass
class Hit:
    """One search result."""

    chunk_id: int
    manual_id: int
    manual_name: str
    revision: str
    page: int
    text: str
    score: float  # cosine similarity; higher means a closer match
    machine_id: int


def _client():
    # CHROMA_PATH is None while running tests, which gives an in-memory store.
    path = getattr(settings, "CHROMA_PATH", None)
    key = str(path)

    if key not in _clients:
        if path:
            _clients[key] = chromadb.PersistentClient(path=str(path))
        else:
            _clients[key] = chromadb.EphemeralClient()
    return _clients[key]


def _collection():
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection():
    """Remove every stored passage and start with an empty collection."""
    try:
        _client().delete_collection(COLLECTION_NAME)
    except Exception:
        # The collection does not exist yet, so there is nothing to remove.
        pass
    return _collection()


def remove_manual(manual_id):
    _collection().delete(where={"manual_id": int(manual_id)})


def index_manual(manual):
    """Store all chunks of a manual for searching. Returns how many were stored."""
    chunks = list(manual.chunks.all())

    # Remove old entries first so re-indexing never leaves duplicates behind.
    remove_manual(manual.id)
    if not chunks:
        return 0

    collection = _collection()

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        texts = [chunk.text for chunk in batch]

        collection.upsert(
            ids=[str(chunk.id) for chunk in batch],
            embeddings=embed_texts(texts),
            documents=texts,
            metadatas=[
                {
                    "machine_id": manual.machine_id,
                    "manual_id": manual.id,
                    "manual_name": manual.name,
                    "revision": manual.revision,
                    "page": chunk.page_number,
                    "chunk_id": chunk.id,
                }
                for chunk in batch
            ],
        )

    return len(chunks)


def search(machine_id, question, k=4):
    """
    Return the k best matching passages for one machine, best match first.

    The machine filter is part of the search query itself. Filtering the
    results afterwards could let another machine's text take up the top
    places and push out the right ones.
    """
    result = _collection().query(
        query_embeddings=embed_texts([question]),
        n_results=k,
        where={"machine_id": int(machine_id)},
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for text, meta, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        hits.append(
            Hit(
                chunk_id=meta["chunk_id"],
                manual_id=meta["manual_id"],
                manual_name=meta["manual_name"],
                revision=meta["revision"],
                page=meta["page"],
                text=text,
                # Chroma returns a distance, so convert it to a similarity.
                score=round(1.0 - float(distance), 4),
                machine_id=meta["machine_id"],
            )
        )

    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits
