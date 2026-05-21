import sys

from qwen_tts.audio import AudioConversionError, clean_path
from qwen_tts.config import get_config
from qwen_tts.constants import CLI_MODEL_KEYS, EMOTION_EXAMPLES, MODELS, SPEAKER_MAP
from qwen_tts.errors import GenerationError, ModelNotFoundError, VoiceNotFoundError
from qwen_tts.generation import generate_clone, generate_custom, generate_design, play_audio
from qwen_tts.models import get_model_path
from qwen_tts.voices import create_voice_profile, list_voice_profiles

AUTO_PLAY = True


def flush_input():
    try:
        import termios

        termios.tcflush(sys.stdin, termios.TCIOFLUSH)
    except (ImportError, OSError):
        pass


def get_safe_input(prompt="\nEnter text (or drag .txt file): "):
    try:
        raw_input = input(prompt).strip()
        if raw_input.lower() in ["exit", "quit", "q"]:
            return None

        clean_p = clean_path(raw_input)
        path = get_config().repo_root / clean_p if not clean_p.startswith("/") else None
        candidates = [clean_p]
        if path:
            candidates.append(str(path))

        for candidate in candidates:
            try:
                from pathlib import Path

                file_path = Path(candidate)
                if file_path.exists() and file_path.suffix == ".txt":
                    print(f"Reading from: {file_path.name}")
                    return file_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                print(f"Error reading file: {exc}")
                return None

        return raw_input
    except KeyboardInterrupt:
        flush_input()
        return None


def enroll_new_voice():
    print("\n--- Enroll New Voice ---")
    flush_input()

    name = input("1. Voice name (e.g. Boss, Mom): ").strip()
    if not name:
        return

    ref_input = input("2. Drag & Drop Reference File: ").strip()
    raw_path = clean_path(ref_input)
    if len(raw_path) > 300 or "\n" in raw_path:
        print("Error: Input too long.")
        flush_input()
        return

    print("3. Transcript (important for quality):")
    ref_text = input("   Type EXACTLY what the audio says: ").strip()

    try:
        voice = create_voice_profile(name, raw_path, ref_text)
        print(f"Voice saved as '{voice['id']}'")
    except AudioConversionError as exc:
        print(f"Error: {exc}")
    except VoiceNotFoundError as exc:
        print(f"Error: {exc}")


def run_custom_session(model_id):
    info = MODELS[model_id]
    try:
        get_model_path(model_id)
    except ModelNotFoundError:
        print("Error: Model not found.")
        return

    print(f"\nLoading {info['name']}...")
    print(f"\n--- {info['name']} ---")
    speaker = "Vivian"
    all_speakers = [n for names in SPEAKER_MAP.values() for n in names]
    print("Available Speakers: " + ", ".join(all_speakers))

    user_choice = input("\nSelect Speaker (Name): ").strip()
    for _, names in SPEAKER_MAP.items():
        if user_choice in names:
            speaker = user_choice
            break
    print(f"Using: {speaker}")

    print("\nEmotion Examples:")
    for ex in EMOTION_EXAMPLES:
        print(f"  - {ex}")
    base_instruct = input("Emotion Instruction: ").strip() or "Normal tone"

    print("\nSpeed:")
    print("  1. Normal (1.0x)")
    print("  2. Fast (1.3x)")
    print("  3. Slow (0.8x)")
    sp = input("Choice (1-3): ").strip()
    speed = 1.0
    if sp == "2":
        speed = 1.3
    elif sp == "3":
        speed = 0.8

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("Generating...")
        try:
            result = generate_custom(model_id, speaker, base_instruct, speed, text, autoplay=False)
            print(f"Saved: outputs/{info['output_subfolder']}/{result.filename}")
            if AUTO_PLAY:
                print("Playing...")
                play_audio(result.output_path)
        except GenerationError as exc:
            print(f"Error: {exc}")


def run_design_session(model_id):
    info = MODELS[model_id]
    try:
        get_model_path(model_id)
    except ModelNotFoundError:
        print("Error: Model not found.")
        return

    print(f"\nLoading {info['name']}...")
    print(f"\n--- {info['name']} ---")
    instruct = input("Describe the voice: ").strip()
    if not instruct:
        return

    while True:
        text = get_safe_input()
        if text is None:
            break
        print("Generating...")
        try:
            result = generate_design(model_id, instruct, text, autoplay=False)
            print(f"Saved: outputs/{info['output_subfolder']}/{result.filename}")
            if AUTO_PLAY:
                print("Playing...")
                play_audio(result.output_path)
        except GenerationError as exc:
            print(f"Error: {exc}")


def run_clone_manager(model_id):
    print("\n--- Voice Cloning Manager ---")
    print("  1. Pick from Saved Voices")
    print("  2. Enroll New Voice")
    print("  3. Quick Clone")
    print("  4. Back")

    sub_choice = input("\nChoice: ").strip()
    if sub_choice == "2":
        enroll_new_voice()
        return
    if sub_choice == "4":
        return

    info = MODELS[model_id]
    try:
        get_model_path(model_id)
    except ModelNotFoundError:
        print("Error: Model not found.")
        return

    voice_id = None
    temporary_voice_id = None

    if sub_choice == "1":
        saved = list_voice_profiles()
        if not saved:
            print("No saved voices found.")
            return
        print("\nSaved Voices:")
        for i, voice in enumerate(saved):
            print(f"  {i + 1}. {voice['id']}")
        try:
            idx = int(input("\nPick Number: ")) - 1
            if idx < 0 or idx >= len(saved):
                print("Invalid selection.")
                return
            voice_id = saved[idx]["id"]
            print(f"Loaded: {voice_id}")
        except (ValueError, IndexError):
            print("Invalid selection.")
            return

    elif sub_choice == "3":
        ref_input = input("\nDrag Reference Audio: ").strip()
        raw_path = clean_path(ref_input)
        ref_text = input("   Transcript (Optional): ").strip() or "."
        temporary_voice_id = f"quick_clone_{abs(hash(raw_path))}"
        try:
            voice = create_voice_profile(temporary_voice_id, raw_path, ref_text)
            voice_id = voice["id"]
        except Exception as exc:
            print(f"Error: {exc}")
            return

    else:
        return

    print("\nLoading Base Model...")
    while True:
        text = get_safe_input(f"\nText for '{voice_id}' (or 'exit'): ")
        if text is None:
            break
        print("Cloning...")
        try:
            result = generate_clone(model_id, voice_id, text, autoplay=False)
            print(f"Saved: outputs/{info['output_subfolder']}/{result.filename}")
            if AUTO_PLAY:
                print("Playing...")
                play_audio(result.output_path)
        except GenerationError as exc:
            print(f"Error: {exc}")


def main_menu():
    print("\n" + "=" * 40)
    print(" Qwen3-TTS Manager")
    print("=" * 40)

    print("\n  Pro Models (1.7B - Best Quality)")
    print("  ---------------------------------")
    print("  1. Custom Voice")
    print("  2. Voice Design")
    print("  3. Voice Cloning")

    print("\n  Lite Models (0.6B - Faster)")
    print("  ---------------------------")
    print("  4. Custom Voice")
    print("  5. Voice Design")
    print("  6. Voice Cloning")

    print("\n  q. Exit")

    choice = input("\nSelect: ").strip().lower()

    if choice == "q":
        sys.exit()

    if choice not in CLI_MODEL_KEYS:
        print("Invalid selection.")
        flush_input()
        return

    model_id = CLI_MODEL_KEYS[choice]
    mode = MODELS[model_id]["mode"]

    if mode == "custom":
        run_custom_session(model_id)
    elif mode == "design":
        run_design_session(model_id)
    elif mode == "clone":
        run_clone_manager(model_id)


if __name__ == "__main__":
    try:
        get_config().outputs_dir.mkdir(parents=True, exist_ok=True)
        while True:
            main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
