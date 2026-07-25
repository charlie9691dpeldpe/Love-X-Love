"""
config_manager.py
Maneja la configuración persistente de ChispaIA: API key de Anthropic (cifrada),
modo de trabajo (online/offline), modelo de Ollama preferido, etc.
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "ChispaIA"
CONFIG_FILE = APP_DIR / "config.json"
KEY_FILE = APP_DIR / "secret.key"

DEFAULT_CONFIG = {
    "mode": "online",           # "online" (Claude) o "offline" (Ollama)
    "ollama_model": "llama3.2",
    "ollama_host": "http://localhost:11434",
    "claude_model": "claude-sonnet-4-6",
    "default_tone": "coqueto",
    "api_key_encrypted": "",
}


def _ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _get_or_create_fernet_key() -> bytes:
    _ensure_app_dir()
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key


def load_config() -> dict:
    _ensure_app_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    _ensure_app_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def set_api_key(plain_api_key: str):
    """Cifra y guarda la API key de Anthropic."""
    fernet = Fernet(_get_or_create_fernet_key())
    encrypted = fernet.encrypt(plain_api_key.encode("utf-8")).decode("utf-8")
    config = load_config()
    config["api_key_encrypted"] = encrypted
    save_config(config)


def get_api_key() -> str:
    """Descifra y devuelve la API key de Anthropic, o cadena vacía si no hay."""
    config = load_config()
    encrypted = config.get("api_key_encrypted", "")
    if not encrypted:
        return ""
    try:
        fernet = Fernet(_get_or_create_fernet_key())
        return fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def has_api_key() -> bool:
    return bool(get_api_key())
