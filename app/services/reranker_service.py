import asyncio
import logging
from typing import List, Dict
from sentence_transformers import CrossEncoder
from app.config import settings

logger = logging.getLogger(__name__)

_model: CrossEncoder | None = None
_model_device: str | None = None

def get_reranker_model(device: str | None = None) -> CrossEncoder:
    """Lazy loads and caches the CrossEncoder model in memory."""
    global _model, _model_device
    requested_device = device if device is not None else settings.reranker_device
    
    import torch
    if requested_device in ("cuda", "gpu"):
        if not torch.cuda.is_available():
            logger.info("CUDA requested for reranker, but CUDA GPU is not available. Falling back to 'cpu'.")
            target_device = "cpu"
        else:
            try:
                free_bytes, _ = torch.cuda.mem_get_info()
                # Require at least 400 MB of free VRAM to load and predict on GPU
                if free_bytes < 400 * 1024 * 1024:
                    logger.warning(
                        f"CUDA GPU has insufficient free VRAM ({free_bytes / (1024*1024):.1f} MB free). "
                        "Falling back to 'cpu'."
                    )
                    target_device = "cpu"
                else:
                    target_device = requested_device
            except Exception:
                target_device = requested_device
    else:
        target_device = requested_device
    
    if _model is None or _model_device != target_device:
        model_name = settings.reranker_model
        logger.info(f"Initializing Cross-Encoder model {model_name} on device {target_device}...")
        local_only = getattr(settings, "hf_hub_offline", False)
        try:
            _model = CrossEncoder(model_name, device=target_device, local_files_only=local_only)
            _model_device = target_device
            logger.info(f"Cross-Encoder model {model_name} loaded successfully on {target_device}.")
        except Exception as exc:
            if not local_only:
                try:
                    logger.info(f"Attempting to load {model_name} from local cache...")
                    _model = CrossEncoder(model_name, device=target_device, local_files_only=True)
                    _model_device = target_device
                    logger.info(f"Cross-Encoder model loaded from local cache on {target_device}.")
                    return _model
                except Exception:
                    pass

            if target_device != "cpu":
                logger.warning(
                    f"Failed to load Cross-Encoder on device {target_device}: {exc}. "
                    f"Attempting automatic fallback to 'cpu'..."
                )
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                try:
                    _model = CrossEncoder(model_name, device="cpu", local_files_only=local_only)
                except Exception:
                    _model = CrossEncoder(model_name, device="cpu", local_files_only=True)
                _model_device = "cpu"
                settings.reranker_device = "cpu"
                logger.info(f"Cross-Encoder model {model_name} loaded successfully on cpu (fallback).")
            else:
                raise exc
    return _model


def _predict_sync(query: str, passages: List[str]) -> List[float]:
    """Synchronous CPU/GPU bound prediction run with fallback to CPU on error."""
    global _model, _model_device
    pairs = [(query, passage) for passage in passages]
    
    try:
        model = get_reranker_model()
        scores = model.predict(pairs)
        return [float(score) for score in scores]
    except Exception as exc:
        logger.warning(
            f"Reranker prediction failed on device {_model_device}: {exc}. "
            f"Attempting CPU fallback for prediction..."
        )
        try:
            _model = None
            _model_device = "cpu"
            settings.reranker_device = "cpu"
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            model = get_reranker_model(device="cpu")
            scores = model.predict(pairs)
            return [float(score) for score in scores]
        except Exception as cpu_exc:
            logger.error(f"CPU fallback for reranker prediction failed: {cpu_exc}")
            raise cpu_exc


async def rerank_candidates(query: str, candidates: List[Dict]) -> List[Dict]:
    """
    Rerank candidate passages using BAAI/bge-reranker-base.
    Runs in a background thread to prevent blocking the async loop.
    """
    if not candidates:
        return []

    passages = [c["text"] for c in candidates]
    
    # Offload CPU/GPU execution to thread pool
    scores = await asyncio.to_thread(_predict_sync, query, passages)
    
    reranked = []
    for idx, candidate in enumerate(candidates):
        item = dict(candidate)
        item["rerank_score"] = scores[idx]
        reranked.append(item)
        
    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    return reranked
