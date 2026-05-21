from __future__ import annotations

from pathlib import Path

from .config import AppConfig, get_config
from .constants import MODELS
from .errors import ModelNotFoundError


def resolve_model_path(folder_name: str, config: AppConfig | None = None) -> Path | None:
    cfg = config or get_config()
    full_path = cfg.models_dir / folder_name
    if not full_path.exists():
        return None

    snapshots_dir = full_path / "snapshots"
    if snapshots_dir.exists():
        subfolders = sorted(p for p in snapshots_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
        if subfolders:
            return subfolders[0]

    return full_path


def get_model_definition(model_id: str) -> dict:
    if model_id not in MODELS:
        raise ModelNotFoundError(f"Unknown model: {model_id}")
    return {"id": model_id, **MODELS[model_id]}


def get_model_path(model_id: str, config: AppConfig | None = None) -> Path:
    info = get_model_definition(model_id)
    model_path = resolve_model_path(info["folder"], config=config)
    if not model_path:
        raise ModelNotFoundError(f"Model not found: {info['folder']}")
    return model_path


def list_models(config: AppConfig | None = None) -> list[dict]:
    cfg = config or get_config()
    result = []
    for model_id, info in MODELS.items():
        path = resolve_model_path(info["folder"], cfg)
        result.append(
            {
                "id": model_id,
                "name": info["name"],
                "mode": info["mode"],
                "folder": info["folder"],
                "output_subfolder": info["output_subfolder"],
                "installed": path is not None,
                "path": str(path) if path else None,
            }
        )
    return result

