"""
Generator — Genera el documento con el formato deseado.
"""

from __future__ import annotations

import re
from typing import Any

from agents.base import Agent
from models.openrouter_api import OpenRouterClient


class Generator(Agent):
    """Genera el documento final según el tipo solicitado."""

    # Patrones de garbage — outputs que no son texto válido
    _GARBAGE_PATTERNS: list[re.Pattern] = [
        re.compile(r"^\(\w+\("),  # (Session(Session(...
        re.compile(r"^[\(\)\[\]\{\}]{10,}"),  # solo paréntesis repetidos
        re.compile(r"^<class\s+['\"]"),  # <class '...'>
        re.compile(r"^(object at 0x|<\w+\.\w+\s+object)"),  # <Foo.Bar object at 0x...
    ]

    def __init__(self, model: str = "deepseek/deepseek-chat", api_key: str = ""):
        self.client = OpenRouterClient(api_key=api_key, model=model)

    @staticmethod
    def _is_garbage(content: str) -> tuple[bool, str]:
        """Verifica si el output parece basura en vez de texto útil."""
        text = content.strip()
        if not text:
            return True, "output vacío"

        for pattern in Generator._GARBAGE_PATTERNS:
            if pattern.match(text):
                return True, f"coincide con patrón de garbage: {pattern.pattern[:40]}"

        # Si >80% son paréntesis/llaves sueltos, es basura
        parens = sum(1 for c in text if c in "()[]{}")
        if len(text) > 100 and parens > len(text) * 0.3:
            return True, f">30% de caracteres son paréntesis ({parens}/{len(text)})"

        return False, ""

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        texto: str = data.get("texto", "")
        tipo: str = data.get("tipo", "resumen")
        fecha: str = data.get("fecha", "")
        autor: str = data.get("autor", "")
        sitio: str = data.get("sitio", "")

        if not texto.strip():
            return {"error": "Texto vacío para generar", "ok": False}

        system_prompt = self._build_prompt(tipo, fecha, autor, sitio)
        max_tokens = self._max_tokens_for(tipo)

        try:
            contenido = self.client.chat(
                message=texto,
                system=system_prompt,
                temperature=0.5,
                max_tokens=max_tokens,
                timeout=180,
            )

            # Validar que el output no sea garbage
            is_garbage, reason = self._is_garbage(contenido)
            if is_garbage:
                return {
                    "error": f"El modelo devolvió contenido no válido: {reason}",
                    "ok": False,
                    "contenido_bruto": contenido[:500],
                }

            return {"contenido": contenido, "tipo": tipo, "ok": True}

        except Exception as e:
            return {
                "error": f"Generator falló: {e}",
                "ok": False,
            }

    @staticmethod
    def _max_tokens_for(tipo: str) -> int:
        """Retorna max_tokens según el tipo de documento."""
        limites = {
            "tldr": 3072,
            "resumen": 2048,
            "notas": 4096,
            "analisis": 3072,
            "articulo": 4096,
            "transcripcion": 4096,
            "ideas_mkt": 4096,
        }
        return limites.get(tipo, 4096)

    @staticmethod
    def _build_prompt(tipo: str, fecha: str = "", autor: str = "", sitio: str = "") -> str:
        """Construye el system prompt según el tipo de documento."""
        import os

        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "prompts", "generator.md"
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
                f"Genera un documento de tipo '{tipo}' basado en la transcripción "
                f"que se te proporciona. Usa formato Markdown. "
                f"Escribe SIEMPRE en español de México. "
                f"Sé claro, conciso y bien estructurado."
            )