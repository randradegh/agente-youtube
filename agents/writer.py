"""
Writer — Escribe el documento generado al filesystem.
"""

from __future__ import annotations

import os
import re
from typing import Any

from agents.base import Agent


class Writer(Agent):
    """Escribe el contenido generado a un archivo .md."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        contenido: str = data.get("contenido", "")
        titulo: str = data.get("titulo", "video")
        tipo: str = data.get("tipo", "documento")

        if not contenido.strip():
            return {"error": "Contenido vacío, no se escribe nada", "ok": False}

        os.makedirs(self.output_dir, exist_ok=True)

        nombre = self._normalize_name(titulo, tipo)
        ruta = os.path.join(self.output_dir, nombre)

        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            return {"ruta": ruta, "ok": True}
        except OSError as e:
            return {"error": f"No se pudo escribir {ruta}: {e}", "ok": False}

    @staticmethod
    def _normalize_name(titulo: str, tipo: str) -> str:
        """Crea un nombre de archivo limpio: título_tipo.md"""
        limpio = re.sub(r"[^a-zA-Z0-9áéíóúñü\s-]", "", titulo)
        limpio = re.sub(r"\s+", "_", limpio.strip().lower())
        limpio = limpio[:60].rstrip("_")
        return f"{limpio}_{tipo}.md"