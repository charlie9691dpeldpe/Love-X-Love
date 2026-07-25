# ChispaIA 💬✨

Asistente de citas con IA para Windows — alternativa mejorada a 1Flechazo.
Analiza tu conversación (texto o captura de pantalla) y te sugiere respuestas
en distintos tonos: coqueto, nerd/divertido, directo, misterioso, tierno o sarcástico.

## Características

- **Modo online**: usa la API de Claude (Anthropic) — mejor calidad, entiende
  capturas de pantalla directamente sin necesidad de OCR.
- **Modo offline**: usa [Ollama](https://ollama.com) corriendo local en tu PC —
  sin internet, sin API key, 100% privado.
- 6 tonos de respuesta distintos, más que la competencia.
- Historial de conversaciones analizadas.
- API key guardada cifrada localmente (nunca en texto plano).

## Instalación (desarrollo)

```bash
pip install -r requirements.txt
python main.py
```

## Uso

1. Andá a la pestaña **Configuración**.
2. Elegí modo **Online** (pegá tu API key de [console.anthropic.com](https://console.anthropic.com))
   o modo **Offline** (instalá [Ollama](https://ollama.com) y corré `ollama run llama3.2`).
3. En la pestaña **Analizar chat**, pegá el texto de la conversación o cargá una
   captura de pantalla.
4. Elegí el tono deseado y presioná **Generar sugerencias**.
5. Copiá la respuesta que más te guste con un clic.

## Empaquetar como .exe

```bash
pip install pyinstaller
pyinstaller chispaia.spec
```

El ejecutable queda en `dist/ChispaIA.exe`. También hay un workflow de
GitHub Actions (`.github/workflows/build.yml`) que compila automáticamente
al crear un tag `v*` o manualmente desde la pestaña Actions.

## Notas sobre modo offline

- Necesitás tener Ollama instalado y corriendo (`ollama serve`).
- Si cargás una captura de pantalla en modo offline, se usa Tesseract OCR
  para extraer el texto antes de mandarlo al modelo local. Instalá
  Tesseract desde: https://github.com/UB-Mannheim/tesseract/wiki
- La calidad de las sugerencias en modo offline depende del modelo que
  elijas; `llama3.2` o `qwen2.5` son buenos puntos de partida livianos.

## Estructura del proyecto

```
chispaia/
├── main.py             # punto de entrada
├── gui.py               # interfaz Tkinter (dark mode)
├── ai_engine.py          # lógica de generación (Claude + Ollama)
├── ocr_engine.py         # extracción de texto de imágenes (Tesseract)
├── config_manager.py     # configuración y API key cifrada
├── requirements.txt
├── chispaia.spec          # build de PyInstaller
└── .github/workflows/build.yml
```
