from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .audio import ffmpeg_available
from .config import configure_data_dir, get_config
from .constants import DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT
from .downloads import delete_model, download_model
from .errors import JobBusyError, QwenTTSError
from .generation import generate_clone, generate_design, list_outputs
from .jobs import JobManager
from .models import list_models
from .voices import create_voice_profile, delete_voice_profile, list_voice_profiles

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - exercised by manual startup
    raise SystemExit("FastAPI backend dependencies are missing. Run: pip install fastapi uvicorn python-multipart") from exc


app = FastAPI(title="QwenTTS Local Backend", version=__version__)
job_manager = JobManager()


class VoiceCreateRequest(BaseModel):
    name: str
    reference_audio_path: str
    transcript: str = ""


class CloneGenerateRequest(BaseModel):
    model_id: str
    voice_id: str
    text: str
    autoplay: bool = False


class DesignGenerateRequest(BaseModel):
    model_id: str
    instruct: str
    text: str
    autoplay: bool = False


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, QwenTTSError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
def health() -> dict:
    cfg = get_config()
    return {
        "ok": True,
        "version": __version__,
        "repo_root": str(cfg.repo_root),
        "data_dir": str(cfg.data_dir),
        "models_dir": str(cfg.models_dir),
        "python": sys.executable,
        "ffmpeg_available": ffmpeg_available(),
    }


@app.get("/models")
def models() -> list[dict]:
    return list_models()


@app.get("/voices")
def voices() -> list[dict]:
    return list_voice_profiles()


@app.post("/voices")
def create_voice(request: VoiceCreateRequest) -> dict:
    try:
        return create_voice_profile(request.name, request.reference_audio_path, request.transcript)
    except Exception as exc:
        raise _http_error(exc)


@app.delete("/voices/{voice_id}")
def delete_voice(voice_id: str) -> dict:
    try:
        delete_voice_profile(voice_id)
        return {"ok": True}
    except Exception as exc:
        raise _http_error(exc)


@app.post("/generate/clone")
def generate_clone_endpoint(request: CloneGenerateRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    try:
        job = job_manager.create_clone_job(
            lambda: generate_clone(
                model_id=request.model_id,
                voice_id=request.voice_id,
                text=request.text,
                autoplay=request.autoplay,
            )
        )
        return job_manager.to_dict(job)
    except JobBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise _http_error(exc)


@app.post("/generate/design")
def generate_design_endpoint(request: DesignGenerateRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    if not request.instruct.strip():
        raise HTTPException(status_code=400, detail="Voice description is required.")

    try:
        job = job_manager.create_generation_job(
            lambda: generate_design(
                model_id=request.model_id,
                instruct=request.instruct,
                text=request.text,
                autoplay=request.autoplay,
            )
        )
        return job_manager.to_dict(job)
    except JobBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise _http_error(exc)


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_manager.to_dict(job)


@app.post("/models/{model_id}/download")
def start_model_download(model_id: str) -> dict:
    try:
        job = job_manager.create_download_job(
            lambda report: download_model(model_id, on_progress=report)
        )
        return job_manager.to_dict(job)
    except JobBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise _http_error(exc)


@app.delete("/models/{model_id}")
def delete_model_endpoint(model_id: str) -> dict:
    try:
        removed = delete_model(model_id)
        return {"ok": True, "removed": removed}
    except Exception as exc:
        raise _http_error(exc)


@app.get("/outputs")
def outputs() -> list[dict]:
    return list_outputs()


def run_server(host: str, port: int, data_dir: str | Path | None = None) -> None:
    configure_data_dir(data_dir)
    cfg = get_config()
    cfg.models_dir.mkdir(parents=True, exist_ok=True)
    cfg.voices_dir.mkdir(parents=True, exist_ok=True)
    cfg.outputs_dir.mkdir(parents=True, exist_ok=True)
    cfg.temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("uvicorn is missing. Run: pip install uvicorn") from exc

    uvicorn.run(app, host=host, port=port, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_SERVER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    run_server(args.host, args.port, args.data_dir)

if __name__ == "__main__":
    main()
