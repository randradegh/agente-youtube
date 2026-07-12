"""
Aggregator — Sintetiza múltiples propuestas en un documento final.

Recibe la transcripción original + N borradores de distintos modelos
y produce una versión consolidada que aprovecha lo mejor de cada uno.
"""

from __future__ import annotations

import os
from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Aggregator(Agent):
    """Sintetiza múltiples propuestas en un documento final."""

    def __init__(self, model: str, api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)
        self.model_name = model

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        transcripcion: str = data.get("texto", "")
        propuestas: list[dict] = data.get("propuestas", [])
        tipo: str = data.get("tipo", "tldr")
        fecha: str = data.get("fecha", "")
        autor: str = data.get("autor", "")
        sitio: str = data.get("sitio", "")

        if not propuestas:
            return {"error": "No hay propuestas para agregar", "ok": False}

        # Construir el mensaje con transcripción + propuestas
        mensaje = self._build_message(transcripcion, propuestas)
        system_prompt = self._build_prompt(tipo, fecha, autor, sitio)
        max_tokens = self._max_tokens_for(tipo)

        try:
            contenido = self.client.chat(
                message=mensaje,
                system=system_prompt,
                temperature=0.3,  # baja temperatura para síntesis precisa
                max_tokens=max_tokens,
                timeout=240,  # más tiempo porque el input es grande
            )

            return {"contenido": contenido, "tipo": tipo, "ok": True}

        except Exception as e:
            return {
                "error": f"Aggregator falló: {e}",
                "ok": False,
                "propuestas_count": len(propuestas),
            }

    @staticmethod
    def _build_message(transcripcion: str, propuestas: list[dict]) -> str:
        """Construye el mensaje con transcripción original + todas las propuestas."""
        partes = []

        partes.append("=== TRANSCRIPCIÓN ORIGINAL ===")
        # Truncar transcripción si es muy larga para no exceder contexto
        if len(transcripcion) > 80000:
            partes.append(transcripcion[:80000])
            partes.append(
                "\n[... transcripción truncada a 80K caracteres por límite de contexto ...]"
            )
        else:
            partes.append(transcripcion)

        partes.append("\n\n=== PROPUESTAS DE CADA MODELO ===")

        for i, prop in enumerate(propuestas, 1):
            modelo = prop.get("modelo", f"modelo_{i}")
            contenido = prop.get("contenido", "[sin contenido]")
            partes.append(f"\n--- Propuesta #{i}: {modelo} ---")
            partes.append(contenido)

        partes.append(
            "\n\n=== INSTRUCCIÓN ===\n"
            "Sintetiza el mejor documento posible combinando las fortalezas "
            "de cada propuesta. Usa la transcripción original como fuente de "
            "verdad cuando haya discrepancias. Elimina redundancias."
        )

        return "\n".join(partes)

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
        """Carga y completa el prompt de agregador."""
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "aggregator.md"
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
                f"Eres un agregador. Sintetiza el mejor documento de tipo '{tipo}' "
                f"a partir de la transcripción y múltiples propuestas. "
                f"Usa Markdown. Escribe SIEMPRE en español de México."
            )