"""utils/device.py — Detects whether a CUDA GPU is available and logs it once.

Used by the embedder, the reranker, and the OCR engines so they all actually
use a GPU when one is present, instead of silently defaulting to CPU.
"""
from utils.logger import get_logger
logger = get_logger(__name__)

_DEVICE = None
_ANNOUNCED = False


def get_device() -> str:
    """Return 'cuda' if a GPU is available and usable, else 'cpu'. Cached after first call."""
    global _DEVICE, _ANNOUNCED
    if _DEVICE is not None:
        return _DEVICE
    try:
        import torch
        if torch.cuda.is_available():
            _DEVICE = "cuda"
        else:
            _DEVICE = "cpu"
            _tune_cpu_threads()
    except ImportError:
        _DEVICE = "cpu"

    if not _ANNOUNCED:
        if _DEVICE == "cuda":
            try:
                import torch
                name = torch.cuda.get_device_name(0)
                logger.info(f"GPU detected — running on CUDA ({name})")
            except Exception:
                logger.info("GPU detected — running on CUDA")
        else:
            logger.info("No GPU detected (or torch/CUDA not installed) — running on CPU (multi-threaded)")
        _ANNOUNCED = True
    return _DEVICE


def _tune_cpu_threads():
    """No GPU available — at least make sure CPU work uses all cores instead
    of whatever conservative default the libraries picked. This alone can
    meaningfully cut embedding/reranking time on multi-core machines."""
    import os as _os
    n = _os.cpu_count() or 4
    try:
        import torch
        torch.set_num_threads(n)
    except Exception:
        pass
    try:
        import faiss
        faiss.omp_set_num_threads(n)
    except Exception:
        pass
    logger.info(f"CPU mode: using {n} threads for torch/faiss")


def gpu_available() -> bool:
    return get_device() == "cuda"
