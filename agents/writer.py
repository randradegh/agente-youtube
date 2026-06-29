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

    @staticmethod
    def _validate_content(contenido: str) -> tuple[bool, str]:
        """Valida que el contenido sea texto útil antes de escribirlo."""
        text = contenido.strip()
        if not text:
            return False, "contenido vacío"

        # Rechazar si se ve a objeto Python serializado
        garbage_starters = [
            "(Session(", "(Response(", "(object at 0x", "<class '",
            "<openai.", "<requests.",
        ]
        for gs in garbage_starters:
            if text.startswith(gs):
                return False, f"comienza con '{gs}' — parece garbage de API"

        # Rechazar si >40% son paréntesis sueltos
        if len(text) > 200:
            paren_count = sum(1 for c in text if c in "()[]{}")
            if paren_count > len(text) * 0.4:
                return False, f"{paren_count}/{len(text)} son paréntesis"

        return True, ""

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        contenido: str = data.get("contenido", "")
        titulo: str = data.get("titulo", "video")
        tipo: str = data.get("tipo", "documento")

        if not contenido.strip():
            return {"error": "Contenido vacío, no se escribe nada", "ok": False}

        # Validar contenido antes de escribir
        valido, razon = self._validate_content(contenido)
        if not valido:
            return {
                "error": f"Contenido inválido: {razon}",
                "ok": False,
                "preview": contenido[:300],
            }

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