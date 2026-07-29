"""
Shared PyTorch device resolution for every local ML model this app loads.

WHY THIS MODULE EXISTS
-----------------------
Both the embedding model (Milestone 5) and the cross-encoder reranker
(Milestone 9) need to pick a compute device from the same three-way
choice (`auto` / a specific device), with identical "prefer the best
available accelerator" logic. This was originally a private function
inside `embeddings.py`; promoted to a shared module once the reranker
needed the exact same logic, rather than maintaining two copies that
could silently drift apart.
"""

from __future__ import annotations


def resolve_device(configured: str) -> str:
    """Resolve "auto" to the best available accelerator; pass through others."""
    if configured != "auto":
        return configured

    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
