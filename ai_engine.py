"""
ai_engine.py
Motor que genera sugerencias de respuesta a partir de una conversación de chat.
Soporta dos modos:
  - online: usa la API de Anthropic (Claude), con soporte de visión para capturas.
  - offline: usa un modelo local vía Ollama (texto solamente, requiere OCR previo).
"""

import base64
import json
from pathlib import Path

import requests

import config_manager

TONE_PROMPTS = {
    "coqueto": "coqueto y con picardía, generando tensión y curiosidad sin pasarte de la raya",
    "nerd": "divertido, ingenioso, con referencias sutiles a cultura pop/gaming/anime si encaja natural",
    "directo": "directo, seguro de vos mismo, sin rodeos ni inseguridad",
    "misterioso": "breve, intrigante, dejando algo sin decir para generar curiosidad",
    "tierno": "tierno, cálido y romántico, mostrando interés genuino",
    "sarcastico": "con humor filoso e ingenioso, sarcástico pero simpático, nunca cruel",
}

SYSTEM_PROMPT_TEMPLATE = """Eres un asistente experto en conversaciones de citas (dating). \
Tu tarea es leer el fragmento de chat que te comparte el usuario y sugerir respuestas \
que el usuario podría enviar a continuación.

Instrucciones:
- Genera exactamente 4 sugerencias de respuesta distintas entre sí.
- Todas las sugerencias deben tener un tono {tone_desc}.
- Las respuestas deben sonar naturales, como las escribiría una persona real por chat \
(nada de mensajes largos ni formales).
- Ten en cuenta el contexto y el idioma en que está la conversación; responde en el mismo idioma.
- Devuelve ÚNICAMENTE un JSON válido con este formato, sin texto adicional ni backticks:
{{"suggestions": ["respuesta 1", "respuesta 2", "respuesta 3", "respuesta 4"]}}
"""


class AIEngineError(Exception):
    pass


def _build_system_prompt(tone: str) -> str:
    tone_desc = TONE_PROMPTS.get(tone, TONE_PROMPTS["coqueto"])
    return SYSTEM_PROMPT_TEMPLATE.format(tone_desc=tone_desc)


def _parse_suggestions(raw_text: str) -> list:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        data = json.loads(cleaned)
        suggestions = data.get("suggestions", [])
        if isinstance(suggestions, list) and suggestions:
            return suggestions
    except json.JSONDecodeError:
        pass
    # Fallback: si no pudo parsear JSON, devolvemos el texto crudo como una sola sugerencia
    return [cleaned] if cleaned else ["No se pudo generar una respuesta. Intenta de nuevo."]


def generate_suggestions_online(chat_text: str, tone: str, image_path: str = None) -> list:
    """Genera sugerencias usando la API de Anthropic (Claude)."""
    api_key = config_manager.get_api_key()
    if not api_key:
        raise AIEngineError("No hay API key de Anthropic configurada. Andá a Configuración.")

    config = config_manager.load_config()
    model = config.get("claude_model", "claude-sonnet-4-6")

    content = []
    if image_path:
        img_bytes = Path(image_path).read_bytes()
        media_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.b64encode(img_bytes).decode("utf-8"),
            },
        })
        content.append({
            "type": "text",
            "text": "Esta es una captura de pantalla de una conversación de chat. "
                    "Lee el texto de la imagen y sugiere respuestas."
                    + (f"\n\nContexto adicional escrito por el usuario: {chat_text}" if chat_text.strip() else ""),
        })
    else:
        content.append({"type": "text", "text": chat_text})

    payload = {
        "model": model,
        "max_tokens": 1000,
        "system": _build_system_prompt(tone),
        "messages": [{"role": "user", "content": content}],
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=60,
        )
    except requests.RequestException as e:
        raise AIEngineError(f"Error de conexión con Anthropic: {e}")

    if response.status_code != 200:
        raise AIEngineError(f"Error de la API de Anthropic ({response.status_code}): {response.text[:300]}")

    data = response.json()
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    raw_text = "\n".join(text_blocks)
    return _parse_suggestions(raw_text)


def generate_suggestions_offline(chat_text: str, tone: str) -> list:
    """Genera sugerencias usando un modelo local vía Ollama. Requiere texto (usar OCR antes si es imagen)."""
    config = config_manager.load_config()
    model = config.get("ollama_model", "llama3.2")
    host = config.get("ollama_host", "http://localhost:11434")

    if not chat_text.strip():
        raise AIEngineError("No hay texto de conversación para analizar en modo offline.")

    prompt = (
        _build_system_prompt(tone)
        + "\n\nConversación:\n"
        + chat_text
    )

    try:
        response = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90,
        )
    except requests.exceptions.Timeout:
        raise AIEngineError(
            "Ollama tardó demasiado en responder (más de 90 segundos). "
            "Esto suele indicar que está usando la CPU en vez de la GPU. "
            "Verifica con 'ollama ps' en una terminal si la columna dice CPU o GPU, "
            "y asegúrate de tener la última versión de Ollama instalada."
        )
    except requests.RequestException as e:
        raise AIEngineError(
            f"No se pudo conectar con Ollama en {host}. "
            f"¿Está corriendo Ollama? (ollama serve). Detalle: {e}"
        )

    if response.status_code != 200:
        raise AIEngineError(f"Error de Ollama ({response.status_code}): {response.text[:300]}")

    raw_text = response.json().get("response", "")
    return _parse_suggestions(raw_text)


def generate_suggestions(chat_text: str, tone: str, image_path: str = None) -> list:
    """Punto de entrada único: decide online/offline según configuración."""
    config = config_manager.load_config()
    mode = config.get("mode", "online")
    if mode == "online":
        return generate_suggestions_online(chat_text, tone, image_path)
    return generate_suggestions_offline(chat_text, tone)


def test_ollama_connection() -> tuple:
    """Devuelve (ok: bool, mensaje: str) probando la conexión con Ollama."""
    config = config_manager.load_config()
    host = config.get("ollama_host", "http://localhost:11434")
    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code == 200:
            models = [m["name"] for m in response.json().get("models", [])]
            return True, f"Conectado. Modelos disponibles: {', '.join(models) if models else '(ninguno instalado)'}"
        return False, f"Ollama respondió con error {response.status_code}"
    except requests.RequestException as e:
        return False, f"No se pudo conectar: {e}"


def test_claude_connection() -> tuple:
    """Devuelve (ok: bool, mensaje: str) probando la API key de Anthropic."""
    api_key = config_manager.get_api_key()
    if not api_key:
        return False, "No hay API key configurada."
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config_manager.load_config().get("claude_model", "claude-sonnet-4-6"),
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "hola"}],
            },
            timeout=15,
        )
        if response.status_code == 200:
            return True, "Conexión exitosa con Claude."
        return False, f"Error {response.status_code}: {response.text[:200]}"
    except requests.RequestException as e:
        return False, f"No se pudo conectar: {e}"
