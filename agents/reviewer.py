"""
Reviewer — Limpia y estructura el texto crudo de la transcripción.
"""

from __future__ import annotations

from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Reviewer(Agent):
    """Revisa el texto de la transcripción: elimina ruido, unifica párrafos,
    detecta cambios de orador, corrige segmentación."""

    def __init__(self, model: str = "nvidia/nemotron-3-super-120b-a12b:free", api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)
        self._system_prompt = self._load_prompt()

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        texto_crudo: str = data.get("texto", "")

        if not texto_crudo.strip():
            return {"error": "Texto vacío para revisar", "ok": False}

        try:
            texto_revisado = self.client.chat(
                message=texto_crudo,
                system=self._system_prompt,
            )
            return {"texto": texto_revisado, "ok": True}

        except Exception as e:
            # Fallback: devolver el texto crudo
            return {
                "texto": texto_crudo,
                "ok": False,
                "error": f"Reviewer falló, se usa texto crudo: {e}",
            }

    @staticmethod
    def _load_prompt() -> str:
        """Carga el system prompt desde el archivo de prompts."""
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "reviewer.md"
        )
        try:
            with open(prompt_path, encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return (
                "Eres un revisor de transcripciones. Tu tarea es limpiar "
                "el texto crudo de una transcripción de YouTube. "
                "Elimina marcas de tiempo, corrige la segmentación en párrafos "
                "lógicos, detecta cambios de orador con interlineados, "
                "y unifica el texto. Conserva todo el contenido."
            )