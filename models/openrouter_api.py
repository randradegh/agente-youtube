"""
Cliente OpenRouter usando la SDK de OpenAI.

Modo de uso:
    client = OpenRouterClient(api_key="sk-or-...", model="minimax/minimax-m3")
    respuesta = client.chat("Hola", system="Eres un asistente")
"""

import os
import time
import warnings
from typing import Optional

from openai import OpenAI


class OpenRouterClient:
    """Wrapper para llamadas a OpenRouter vía OpenAI SDK."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "minimax/minimax-m3",
        max_retries: int = 3,
        base_delay: float = 2.0,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY no configurada. "
                "Pásala con --api-key o en el archivo .env"
            )
        self.model = model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._client = OpenAI(api_key=self.api_key, base_url=self.BASE_URL)

    def chat(
        self,
        message: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> str:
        """Envía un mensaje al modelo y devuelve la respuesta."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    extra_headers={
                        "HTTP-Referer": "https://github.com/randradegh/agente-youtube",
                        "X-Title": "Agente YouTube",
                        "Accept-Language": "es-MX",
                    },
                )
                content = resp.choices[0].message.content
                if content is None:
                    raise ValueError(
                        "Modelo devolvió respuesta vacía (content=None) — "
                        "posiblemente una llamada a herramienta o error de formato"
                    )

                # Detectar si el modelo cortó la respuesta por límite de tokens
                finish_reason = resp.choices[0].finish_reason
                if finish_reason == "length":
                    warnings.warn(
                        f"Respuesta truncada por límite de tokens (max_tokens={max_tokens}). "
                        f"Se recibieron ~{len(content.split())} palabras. "
                        "Considera aumentar max_tokens para este tipo."
                    )

                return content.strip()

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

        raise RuntimeError(
            f"Falló tras {self.max_retries} intentos: {last_error}"
        )