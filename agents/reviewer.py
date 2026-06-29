"""
Reviewer — Limpia y estructura el texto crudo de la transcripción.
"""

from __future__ import annotations

from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Reviewer(Agent):
    """Revisa el texto de la transcripción: elimina ruido, unifica párrafos,
    detecta cambios de orador, corrige segmentación.

    Para transcripciones largas (>50K chars) se omite la revisión porque
    el modelo gratuito (Nemotron) tiende a rate-limit o devolver basura
    con entradas muy grandes. El Generator (DeepSeek V3) maneja bien
    el texto crudo directamente.
    """

    MAX_CHARS = 50000

    def __init__(self, model: str = "mistralai/mistral-nemo", api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)
        self._system_prompt = self._load_prompt()

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        texto_crudo: str = data.get("texto", "")

        if not texto_crudo.strip():
            return {"error": "Texto vacío para revisar", "ok": False}

        # Si el texto es muy largo, pasar crudo — el Generator
        # (DeepSeek V3) lo maneja bien
        if len(texto_crudo) > self.MAX_CHARS:
            return {
                "texto": texto_crudo,
                "ok": False,
                "error": (
                    f"Texto muy largo ({len(texto_crudo)} chars), "
                    f"se omite revisión para evitar corrupción"
                ),
            }

        try:
            texto_revisado = self.client.chat(
                message=texto_crudo,
                system=self._system_prompt,
                timeout=180,
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
                "Eres un revisor de transcripciones en español de México. Tu tarea es limpiar "
                "el texto crudo de una transcripción de YouTube. "
                "Elimina marcas de tiempo, corrige la segmentación en párrafos "
                "lógicos, detecta cambios de orador con interlineados, "
                "y unifica el texto. Conserva todo el contenido."
                "Prioriza el español de México."
            )