"""
Converts text into vectors so passages can be compared by meaning.

Two backends are available, chosen with RAG_EMBEDDING_BACKEND:
  sentence-transformers  the real model, runs locally (default)
  hash                   a tiny offline stand-in used by the automated tests

If the organisers provide an embedding API, add a backend here. The rest of
the project only calls embed_texts(), so nothing else has to change.
"""
import hashlib
import math
import re

from django.conf import settings

# The hash backend only measures shared words, so it is much weaker than the
# real model. It exists so the tests run fast, offline and without a download.
_HASH_SIZE = 768
_SKIPPED_WORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it of on or "
    "should that the this to was what when where which who why will with you "
    "your my our we".split()
)

_loaded_models = {}


def _hash_embed(text):
    vector = [0.0] * _HASH_SIZE

    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in _SKIPPED_WORDS:
            continue
        digest = hashlib.md5(word.encode()).digest()
        vector[int.from_bytes(digest[:4], "big") % _HASH_SIZE] += 1.0

    length = math.sqrt(sum(value * value for value in vector))
    if length == 0:
        return vector
    return [value / length for value in vector]


def _load_model():
    name = getattr(settings, "RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Loading the model takes a few seconds, so it is only done once.
    if name not in _loaded_models:
        from sentence_transformers import SentenceTransformer

        _loaded_models[name] = SentenceTransformer(name)
    return _loaded_models[name]


def embed_texts(texts):
    """Return one unit-length vector (a list of floats) for each text."""
    if not texts:
        return []

    backend = getattr(settings, "RAG_EMBEDDING_BACKEND", "sentence-transformers")

    if backend == "hash":
        return [_hash_embed(text) for text in texts]

    if backend == "sentence-transformers":
        vectors = _load_model().encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    raise ValueError(f"Unknown RAG_EMBEDDING_BACKEND: {backend!r}")
