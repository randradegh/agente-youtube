"""
Transcriber — Obtiene la transcripción de YouTube y extrae metadatos.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from agents.base import Agent


class Transcriber(Agent):
    """Obtiene transcripción y título de videos de YouTube."""

    TITLE_PATTERNS = [
        r'<title[^>]*>(.*?)</title>',
    ]

    def __init__(self):
        self._api = YouTubeTranscriptApi()

    def _fetch_title(self, video_id: str) -> str:
        """Obtiene el título real del video desde la página de YouTube."""
        try:
            resp = requests.get(
                f"https://www.youtube.com/watch?v={video_id}",
                timeout=10,
                headers={
                    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 Chrome/120.0.0.0"
                    ),
                },
            )
            match = re.search(
                r'<title[^>]*>(.*?)</title>',
                resp.text,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                title = match.group(1)
                title = re.sub(r'\s*-\s*YouTube\s*$', '', title).strip()
                return title
        except Exception:
            pass
        return video_id

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        url: str = data["url"]
        video_id = self._extract_video_id(url)
        if not video_id:
            return {"error": f"URL inválida: {url}", "url": url}

        try:
            transcript = self._api.fetch(
                video_id, languages=["es", "en"]
            )
            texto = " ".join(
                segment.text for segment in transcript
            )
            titulo = self._fetch_title(video_id)

            return {
                "video_id": video_id,
                "titulo": titulo,
                "url": url,
                "texto": texto.strip(),
                "idioma": "auto",
                "ok": True,
            }
        except Exception as e:
            return {
                "error": f"No se pudo obtener transcripción: {e}",
                "url": url,
                "video_id": video_id,
                "ok": False,
            }

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extrae el ID del video de una URL de YouTube."""
        import re

        patterns = [
            r"v=([a-zA-Z0-9_-]{11})",
            r"youtu\.be/([a-zA-Z0-9_-]{11})",
            r"embed/([a-zA-Z0-9_-]{11})",
            r"shorts/([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None