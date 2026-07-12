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
    """Obtiene transcripción y metadatos de videos de YouTube."""

    def __init__(self):
        self._api = YouTubeTranscriptApi()

    def _fetch_metadata(self, video_id: str) -> dict[str, str]:
        """Obtiene título, nombre del canal y URL del canal desde la página de YouTube."""
        meta = {"titulo": video_id, "autor": "", "sitio": ""}
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
            html = resp.text

            # Título desde <title>
            match = re.search(
                r'<title[^>]*>(.*?)</title>',
                html,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                titulo = match.group(1)
                titulo = re.sub(r'\s*-\s*YouTube\s*$', '', titulo).strip()
                meta["titulo"] = titulo

            # Autor y canal desde ytInitialData
            init_match = re.search(
                r'ytInitialData\s*=\s*({.*?});\s*</script>',
                html,
                re.DOTALL,
            )
            if init_match:
                import json
                data = json.loads(init_match.group(1))
                contents = (
                    data.get("contents", {})
                    .get("twoColumnWatchNextResults", {})
                    .get("results", {})
                    .get("results", {})
                    .get("contents", [])
                )
                for c in contents:
                    owner = (
                        c.get("videoSecondaryInfoRenderer", {})
                        .get("owner", {})
                        .get("videoOwnerRenderer", {})
                    )
                    if owner:
                        runs = owner.get("title", {}).get("runs", [])
                        if runs:
                            meta["autor"] = runs[0].get("text", "")
                        nav = owner.get("navigationEndpoint", {}).get("browseEndpoint", {})
                        canonical = nav.get("canonicalBaseUrl", "")
                        if canonical:
                            meta["sitio"] = f"https://www.youtube.com{canonical}"
                        break

        except Exception:
            pass

        return meta

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
            meta = self._fetch_metadata(video_id)
            titulo = meta["titulo"]
            autor = meta["autor"]
            sitio = meta["sitio"]

            return {
                "video_id": video_id,
                "titulo": titulo,
                "autor": autor,
                "sitio": sitio,
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