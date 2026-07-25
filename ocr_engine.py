"""
ocr_engine.py
Extrae texto de una imagen (captura de chat) usando Tesseract OCR.
Se usa principalmente en modo offline, ya que Claude puede leer imágenes directamente.
"""

from pathlib import Path

import pytesseract
from PIL import Image


class OCRError(Exception):
    pass


def extract_text_from_image(image_path: str) -> str:
    """Extrae texto de una imagen. Lanza OCRError si Tesseract no está instalado."""
    path = Path(image_path)
    if not path.exists():
        raise OCRError(f"No se encontró la imagen: {image_path}")

    try:
        image = Image.open(path)
        text = pytesseract.image_to_string(image, lang="spa+eng")
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        raise OCRError(
            "Tesseract OCR no está instalado en el sistema. "
            "Descargalo de https://github.com/UB-Mannheim/tesseract/wiki e instalalo, "
            "o usá el modo online (Claude) que lee imágenes directamente sin OCR."
        )
    except Exception as e:
        raise OCRError(f"Error al procesar la imagen: {e}")
