"""
Model registry — file-based, with MLflow-compatible interface.

Stores trained XGBoost models as JSON files and metadata as JSON.
Can be swapped for MLflow by replacing the backend while keeping
the same ``save_model`` / ``load_model`` / ``list_models`` API.

Models directory: ``ml/models/``
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from utils.time import utc_now

# Models directory
MODELS_DIR = Path(__file__).resolve().parent / "models"
os.makedirs(MODELS_DIR, exist_ok=True)


def _model_path(name: str) -> Path:
    return MODELS_DIR / f"{name}.json"


def _metadata_path(name: str) -> Path:
    return MODELS_DIR / f"{name}_meta.json"


def save_model(model_json: str, name: str, metrics: dict | None = None) -> str:
    """Save an XGBoost model (as JSON string) to the registry.

    Parameters
    ----------
    model_json : str
        XGBoost booster serialized to JSON (``model.save_model()`` with json format).
    name : str
        Model name/version identifier (e.g. ``"risk_v1"``).
    metrics : dict, optional
        Evaluation metrics to store alongside the model.

    Returns
    -------
    str
        The model name (for reference).
    """
    # Save model
    mp = _model_path(name)
    with open(mp, "w", encoding="utf-8") as f:
        f.write(model_json)

    # Save metadata
    meta = {
        "name": name,
        "saved_at": utc_now().isoformat(),
        "metrics": metrics or {},
    }
    with open(_metadata_path(name), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return name


def load_model(name: str) -> str | None:
    """Load an XGBoost model (JSON string) from the registry.

    Returns ``None`` if the model does not exist.
    """
    mp = _model_path(name)
    if not mp.exists():
        return None
    with open(mp, encoding="utf-8") as f:
        return f.read()


def load_metadata(name: str) -> dict | None:
    """Load metadata for a registered model."""
    mp = _metadata_path(name)
    if not mp.exists():
        return None
    with open(mp, encoding="utf-8") as f:
        return json.load(f)


def list_models() -> list[dict]:
    """List all registered models with their metadata."""
    models = []
    seen = set()
    for f in sorted(MODELS_DIR.iterdir()):
        if f.name.endswith("_meta.json") and f.stem not in seen:
            seen.add(f.stem)
            meta = load_metadata(f.stem.replace("_meta", ""))
            if meta:
                models.append(meta)
    return models


def delete_model(name: str) -> bool:
    """Delete a model and its metadata from the registry.

    Returns ``True`` if the model was deleted, ``False`` if not found.
    """
    mp = _model_path(name)
    metap = _metadata_path(name)
    found = False
    if mp.exists():
        os.remove(mp)
        found = True
    if metap.exists():
        os.remove(metap)
        found = True
    return found


def get_latest_model() -> str | None:
    """Get the name of the most recently saved model.

    Returns ``None`` if no models are registered.
    """
    models = list_models()
    if not models:
        return None
    # Sort by saved_at descending
    models.sort(key=lambda m: m.get("saved_at", ""), reverse=True)
    return models[0]["name"]
