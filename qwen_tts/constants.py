SAMPLE_RATE = 24000
FILENAME_MAX_LEN = 20
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8765

MODELS = {
    "custom-1.7b": {
        "name": "Custom Voice 1.7B",
        "folder": "Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
        "mode": "custom",
        "output_subfolder": "CustomVoice",
        "cli_key": "1",
    },
    "design-1.7b": {
        "name": "Voice Design 1.7B",
        "folder": "Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
        "mode": "design",
        "output_subfolder": "VoiceDesign",
        "cli_key": "2",
    },
    "base-1.7b": {
        "name": "Voice Cloning 1.7B",
        "folder": "Qwen3-TTS-12Hz-1.7B-Base-8bit",
        "mode": "clone",
        "output_subfolder": "Clones",
        "cli_key": "3",
    },
    "custom-0.6b": {
        "name": "Custom Voice 0.6B",
        "folder": "Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
        "mode": "custom",
        "output_subfolder": "CustomVoice",
        "cli_key": "4",
    },
    "design-0.6b": {
        "name": "Voice Design 0.6B",
        "folder": "Qwen3-TTS-12Hz-0.6B-VoiceDesign-8bit",
        "mode": "design",
        "output_subfolder": "VoiceDesign",
        "cli_key": "5",
    },
    "base-0.6b": {
        "name": "Voice Cloning 0.6B",
        "folder": "Qwen3-TTS-12Hz-0.6B-Base-8bit",
        "mode": "clone",
        "output_subfolder": "Clones",
        "cli_key": "6",
    },
}

CLI_MODEL_KEYS = {info["cli_key"]: model_id for model_id, info in MODELS.items()}

SPEAKER_MAP = {
    "English": ["Ryan", "Aiden", "Ethan", "Chelsie", "Serena", "Vivian"],
    "Chinese": ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"],
    "Japanese": ["Ono_Anna"],
    "Korean": ["Sohee"],
}

EMOTION_EXAMPLES = [
    "Sad and crying, speaking slowly",
    "Excited and happy, speaking very fast",
    "Angry and shouting",
    "Whispering quietly",
]

