"""
ollama_manager.py
Gestiona Ollama desde dentro de ChispaIA: detecta si está instalado,
lo inicia/detiene automáticamente, lista modelos instalados y permite
descargar nuevos modelos con progreso, todo sin que el usuario toque la terminal.
"""

import json
import shutil
import subprocess
import time
from pathlib import Path

import requests

import config_manager

# Rutas típicas donde se instala Ollama en Windows
WINDOWS_DEFAULT_PATHS = [
    Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
    Path("C:/Program Files/Ollama/ollama.exe"),
]

_server_process = None  # referencia al proceso que ChispaIA arrancó (si lo hizo)


class OllamaManagerError(Exception):
    pass


def find_ollama_executable() -> str | None:
    """Busca el ejecutable de Ollama en el PATH o en rutas típicas de instalación."""
    in_path = shutil.which("ollama")
    if in_path:
        return in_path
    for candidate in WINDOWS_DEFAULT_PATHS:
        if candidate.exists():
            return str(candidate)
    return None


def is_ollama_installed() -> bool:
    return find_ollama_executable() is not None


def is_ollama_running() -> bool:
    """Verifica si el servidor de Ollama está respondiendo en el host configurado."""
    host = config_manager.load_config().get("ollama_host", "http://localhost:11434")
    try:
        r = requests.get(f"{host}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def start_ollama_server(wait_seconds: float = 8.0) -> tuple:
    """
    Inicia 'ollama serve' en segundo plano si no está corriendo ya.
    Devuelve (ok: bool, mensaje: str).
    """
    global _server_process

    if is_ollama_running():
        return True, "Ollama ya está corriendo."

    exe = find_ollama_executable()
    if not exe:
        return False, (
            "Ollama no está instalado en este equipo. "
            "Descárgalo desde https://ollama.com/download e instálalo."
        )

    try:
        _server_process = subprocess.Popen(
            [exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    except Exception as e:
        return False, f"No se pudo iniciar Ollama: {e}"

    # Esperar a que el servidor responda
    waited = 0.0
    step = 0.5
    while waited < wait_seconds:
        if is_ollama_running():
            return True, "Ollama se inició correctamente."
        time.sleep(step)
        waited += step

    return False, "Ollama se lanzó pero no respondió a tiempo. Puede necesitar más segundos."


def stop_ollama_server() -> tuple:
    """Detiene el servidor de Ollama, solo si ChispaIA lo inició."""
    global _server_process
    if _server_process is None:
        return False, "ChispaIA no inició este proceso de Ollama, no se puede detener desde aquí."
    try:
        _server_process.terminate()
        _server_process = None
        return True, "Ollama detenido."
    except Exception as e:
        return False, f"Error al detener Ollama: {e}"


def list_installed_models() -> list:
    """Devuelve la lista de modelos instalados localmente en Ollama."""
    host = config_manager.load_config().get("ollama_host", "http://localhost:11434")
    try:
        r = requests.get(f"{host}/api/tags", timeout=5)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException:
        pass
    return []


def pull_model(model_name: str, progress_callback=None):
    """
    Descarga un modelo mostrando progreso. progress_callback recibe (status: str, percent: float|None).
    Lanza OllamaManagerError si falla.
    """
    host = config_manager.load_config().get("ollama_host", "http://localhost:11434")

    try:
        response = requests.post(
            f"{host}/api/pull",
            json={"name": model_name, "stream": True},
            stream=True,
            timeout=None,
        )
    except requests.RequestException as e:
        raise OllamaManagerError(f"No se pudo conectar con Ollama: {e}")

    if response.status_code != 200:
        raise OllamaManagerError(f"Error al descargar el modelo ({response.status_code})")

    for line in response.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue

        status = data.get("status", "")
        percent = None
        if "completed" in data and "total" in data and data["total"]:
            percent = round(data["completed"] / data["total"] * 100, 1)

        if progress_callback:
            progress_callback(status, percent)

        if data.get("status") == "success" or status.lower().startswith("success"):
            break

    if progress_callback:
        progress_callback("Modelo listo ✓", 100.0)


def ensure_ready(model_name: str) -> tuple:
    """
    Función de conveniencia: asegura que Ollama esté corriendo y el modelo
    esté instalado antes de generar. Devuelve (ok: bool, mensaje: str).
    No descarga el modelo automáticamente (eso lo dispara el usuario desde la UI).
    """
    if not is_ollama_installed():
        return False, "Ollama no está instalado. Descárgalo desde https://ollama.com/download"

    if not is_ollama_running():
        ok, msg = start_ollama_server()
        if not ok:
            return False, msg

    installed = list_installed_models()
    if not any(model_name in m for m in installed):
        return False, (
            f"El modelo '{model_name}' no está descargado todavía. "
            "Descárgalo desde la pestaña Configuración."
        )

    return True, "Listo."
