from __future__ import annotations

import re
import shutil
from pathlib import Path

from .audio import convert_audio_if_needed
from .config import AppConfig, get_config
from .errors import VoiceNotFoundError


def safe_voice_name(name: str) -> str:
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_")


def _voice_paths(voice_id: str, config: AppConfig) -> tuple[Path, Path]:
    return config.voices_dir / f"{voice_id}.wav", config.voices_dir / f"{voice_id}.txt"


def list_voice_profiles(config: AppConfig | None = None) -> list[dict]:
    cfg = config or get_config()
    if not cfg.voices_dir.exists():
        return []

    profiles = []
    for wav_path in sorted(cfg.voices_dir.glob("*.wav")):
        voice_id = wav_path.stem
        txt_path = cfg.voices_dir / f"{voice_id}.txt"
        transcript = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        profiles.append(
            {
                "id": voice_id,
                "name": voice_id,
                "audio_path": str(wav_path.resolve()),
                "transcript_path": str(txt_path.resolve()) if txt_path.exists() else None,
                "transcript": transcript,
            }
        )
    return profiles


def get_voice_profile(voice_id: str, config: AppConfig | None = None) -> dict:
    cfg = config or get_config()
    wav_path, txt_path = _voice_paths(voice_id, cfg)
    if not wav_path.exists():
        raise VoiceNotFoundError(f"Voice not found: {voice_id}")
    transcript = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
    return {
        "id": voice_id,
        "name": voice_id,
        "audio_path": str(wav_path.resolve()),
        "transcript_path": str(txt_path.resolve()) if txt_path.exists() else None,
        "transcript": transcript,
    }


def create_voice_profile(
    name: str,
    reference_audio_path: str | Path,
    transcript: str,
    config: AppConfig | None = None,
) -> dict:
    cfg = config or get_config()
    voice_id = safe_voice_name(name)
    if not voice_id:
        raise VoiceNotFoundError("Voice name is required.")

    cfg.voices_dir.mkdir(parents=True, exist_ok=True)
    converted_path = convert_audio_if_needed(reference_audio_path, cfg)
    target_wav, target_txt = _voice_paths(voice_id, cfg)

    shutil.copy(converted_path, target_wav)
    target_txt.write_text(transcript.strip(), encoding="utf-8")

    source = Path(reference_audio_path).expanduser()
    if converted_path != source and converted_path.exists():
        converted_path.unlink()

    return get_voice_profile(voice_id, cfg)


def delete_voice_profile(voice_id: str, config: AppConfig | None = None) -> None:
    cfg = config or get_config()
    wav_path, txt_path = _voice_paths(voice_id, cfg)
    if not wav_path.exists():
        raise VoiceNotFoundError(f"Voice not found: {voice_id}")
    wav_path.unlink()
    if txt_path.exists():
        txt_path.unlink()

