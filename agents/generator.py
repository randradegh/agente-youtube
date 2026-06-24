"""
Generator — Genera el documento con el formato deseado.
"""

from __future__ import annotations

from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Generator(Agent):
    """Genera el documento final según el tipo solicitado."""

    def __init__(self, model: str = "deepseek/deepseek-chat", api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        texto: str = data.get("texto", "")
        tipo: str = data.get("tipo", "resumen")

        if not texto.strip():
            return {"error": "Texto vacío para generar", "ok": False}

        system_prompt = self._build_prompt(tipo)

        try:
            contenido = self.client.chat(
                message=texto,
                system=system_prompt,
                temperature=0.5,
            )
            return {"contenido": contenido, "tipo": tipo, "ok": True}

        except Exception as e:
            return {
                "error": f"Generator falló: {e}",
                "ok": False,
            }

    @staticmethod
    def _build_prompt(tipo: str) -> str:
        """Construye el system prompt según el tipo de documento."""
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "generator.md"
        )
        try:
            with open(prompt_path, encoding="utf-8") as f:
                template = f.read()
                return template.replace("{{TIPO}}", tipo)
        except FileNotFoundError:
            return (
                f"Genera un documento de tipo '{tipo}' basado en la transcripción "
                f"que se te proporciona. Usa formato Markdown. "
                f"Sé claro, conciso y bien estructurado."
            )