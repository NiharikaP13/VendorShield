"""Lazy, thread-safe access to the supplied XGBoost + SHAP model.

The API can become healthy before the heavy ML stack finishes loading. The
launcher warms the model in the background so the dashboard opens quickly,
while scoring still uses the original trained pipeline and SHAP logic.
"""
from __future__ import annotations

import importlib
import json
import threading
import warnings
from pathlib import Path
from types import ModuleType

_MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
with (_MODEL_DIR / "metrics_summary.json").open(encoding="utf-8") as handle:
    _METRICS = json.load(handle)

FEATURE_COLUMNS: list[str] = list(_METRICS["feature_columns"])
RISK_HIGH: float = float(_METRICS["risk_bands"]["high"])
RISK_MEDIUM: float = float(_METRICS["risk_bands"]["medium"])

_model_module: ModuleType | None = None
_load_error: str | None = None
_lock = threading.Lock()


def _get_model() -> ModuleType:
    global _model_module, _load_error
    if _model_module is not None:
        return _model_module
    with _lock:
        if _model_module is not None:
            return _model_module
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                _model_module = importlib.import_module("backend.model.vendorshield_predict")
            _load_error = None
        except Exception as exc:  # noqa: BLE001
            _load_error = f"{type(exc).__name__}: {exc}"
            raise
    return _model_module


def warm_model() -> None:
    """Load model artifacts once in a background thread."""
    try:
        _get_model()
    except Exception:
        # The error is retained and exposed through model_status(). Scoring will
        # raise the original error if an incompatible local environment is used.
        pass


def model_status() -> dict[str, object]:
    return {
        "loaded": _model_module is not None,
        "warming": _model_module is None and _load_error is None,
        "error": _load_error,
    }


def score_one(transaction: dict, top_k: int = 3) -> dict:
    normalized = {key: transaction[key] for key in FEATURE_COLUMNS}
    return _get_model().predict_fraud(normalized, top_k=top_k)
