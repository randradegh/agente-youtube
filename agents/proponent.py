"""
Proponent — Genera una propuesta/borrador para el sistema MoA.

Cada proponente recibe la misma transcripción y produce un borrador
con su propio estilo/perspectiva. El agregador luego sintetiza.
"""

from __future__ import annotations

import os
from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Proponent(Agent):
    """Genera un borrador usando un modelo específico.

    Misma interfaz que Generator pero con modelo configurable
    y prompt adaptado para el pipeline MoA.
    """

    def __init__(self, model: str, api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)
        self.model_name = model

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        texto: str = data.get("texto", "")
        tipo: str = data.get("tipo", "tldr")
        fecha: str = data.get("fecha", "")
        autor: str = data.get("autor", "")
        sitio: str = data.get("sitio", "")

        if not texto.strip():
            return {"error": "Texto vacío para generar propuesta", "ok": False}

        system_prompt = self._build_prompt(tipo, fecha, autor, sitio)
        max_tokens = self._max_tokens_for(tipo)

        try:
            contenido = self.client.chat(
                message=texto,
                system=system_prompt,
                temperature=0.7,  # un poco más creativo para variedad entre proponentes
                max_tokens=max_tokens,
                timeout=180,
            )

            return {
                "contenido": contenido,
                "modelo": self.model_name,
                "tipo": tipo,
                "ok": True,
            }

        except Exception as e:
            return {
                "error": f"Proponente ({self.model_name}) falló: {e}",
                "modelo": self.model_name,
                "ok": False,
            }

    @staticmethod
    def _max_tokens_for(tipo: str) -> int:
        limites = {
            "tldr": 3072,
            "resumen": 2048,
            "notas": 2048,
            "analisis": 3072,
            "articulo": 4096,
            "transcripcion": 4096,
            "ideas_mkt": 4096,
        }
        return limites.get(tipo, 4096)

    @staticmethod
    def _build_prompt(tipo: str, fecha: str = "", autor: str = "", sitio: str = "") -> str:
        """Carga y completa el prompt de proponente."""
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "proponent.md"
        )
        try:
            with open(prompt_path, encoding="utf-8") as f:
                template = f.read()
                template = template.replace("{{TIPO}}", tipo)
                if fecha:
                    template = template.replace("{{FECHA}}", fecha)
                if autor:
                    template = template.replace("{{AUTOR}}", autor)
                if sitio:
                    template = template.replace("{{SITIO}}", sitio)
                return template
        except FileNotFoundError:
            return (
                f"Genera un borrador de tipo '{tipo}' basado en la transcripción "
                f"que se te proporciona. Usa formato Markdown. "
                f"Escribe SIEMPRE en español de México. "
                f"Sé claro, conciso y bien estructurado."
            )