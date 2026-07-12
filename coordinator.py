"""
Coordinator — Orquesta el pipeline de agentes para cada URL.

Modo normal: Transcriber → Reviewer → Generator → Writer
Modo MoA:    Transcriber → [Proponentes en paralelo] → Aggregator → Writer
"""

from __future__ import annotations

import os
import threading
from datetime import date
from typing import Any

from agents.transcriber import Transcriber
from agents.reviewer import Reviewer
from agents.generator import Generator
from agents.writer import Writer
from agents.proponent import Proponent
from agents.aggregator import Aggregator

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


class Coordinator:
    """Orquesta el pipeline.

    Cada video puede procesarse en modo secuencial (Transcriber → Reviewer
    → Generator → Writer) o MoA (Transcriber → [Proponentes en paralelo]
    → Aggregator → Writer), según el flag booleano en la tupla (url, tipo, moa).
    """

    def __init__(
        self,
        output_dir: str = "./output",
        transcriber_model: str = "minimax/minimax-m3",
        reviewer_model: str = "nvidia/nemotron-3-super-120b-a12b:free",
        generator_model: str = "deepseek/deepseek-chat",
        api_key: str = "",
        verbose: bool = False,
        aggregator_model: str = "deepseek/deepseek-v4-flash",
        proponent_models: list[str] | None = None,
    ):
        self.transcriber = Transcriber()
        self.reviewer = Reviewer(model=reviewer_model, api_key=api_key)
        self.generator = Generator(model=generator_model, api_key=api_key)
        self.writer = Writer(output_dir=output_dir)
        self.output_dir = output_dir
        self.api_key = api_key
        self.verbose = verbose
        self.console = Console()

        # MoA config (global — aplica a todos los videos con moa=True)
        self.aggregator_model = aggregator_model
        self.proponent_models = proponent_models or [
            "deepseek/deepseek-v4-flash",
            "qwen/qwen3.6-flash",
        ]

    def process_urls(
        self, items: list[tuple[str, str, bool]]
    ) -> list[dict[str, Any]]:
        """Procesa una lista de (url, tipo, moa) y devuelve los resultados."""
        resultados = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:

            task = progress.add_task(
                f"Procesando {len(items)} video(s)...", total=len(items)
            )

            for url, tipo, usar_moa in items:
                if usar_moa:
                    resultado = self._process_single_moa(url, tipo, progress)
                else:
                    resultado = self._process_single(url, tipo, progress)
                resultados.append(resultado)
                progress.update(task, advance=1)

        self._print_resumen(resultados)
        return resultados

    # ── Modo secuencial (existente) ──────────────────────────────

    def _process_single(
        self, url: str, tipo: str, progress: Progress
    ) -> dict[str, Any]:
        """Procesa una URL a través del pipeline secuencial."""
        if self.verbose:
            progress.print(f"  URL: {url}")

        progress.print(f"  [bold cyan]▶ Transcriber[/] — obteniendo transcripción...")
        transcripcion = self.transcriber.process({"url": url})
        if not transcripcion.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error:[/] {transcripcion.get('error', 'desconocido')}"
            )
            return {"url": url, "ok": False, "error": transcripcion.get("error")}

        # Extraer metadatos del transcriptor
        autor = transcripcion.get("autor", "")
        sitio = transcripcion.get("sitio", "")

        if self.verbose:
            chars = len(transcripcion.get("texto", ""))
            progress.print(f"    {chars} caracteres obtenidos")

        progress.print(f"  [bold cyan]▶ Reviewer[/] — revisando texto...")
        revisado = self.reviewer.process({"texto": transcripcion["texto"]})
        texto_revisado = revisado.get("texto", transcripcion["texto"])
        if not revisado.get("ok", False) and self.verbose:
            progress.print(
                f"    ⚠ {revisado.get('error', '')} — usando texto crudo"
            )

        hoy = date.today().isoformat()

        progress.print(f"  [bold cyan]▶ Generator[/] — generando {tipo}...")
        documento = self.generator.process(
            {"texto": texto_revisado, "tipo": tipo, "fecha": hoy, "autor": autor, "sitio": sitio}
        )
        if not documento.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error al generar:[/] {documento.get('error')}"
            )
            return {"url": url, "ok": False, "error": documento.get("error")}

        progress.print(f"  [bold cyan]▶ Writer[/] — escribiendo archivo...")
        return self._write_result(
            documento["contenido"],
            transcripcion.get("titulo", transcripcion.get("video_id", url)),
            tipo,
            url,
        )

    # ── Modo MoA ────────────────────────────────────────────────

    def _process_single_moa(
        self, url: str, tipo: str, progress: Progress
    ) -> dict[str, Any]:
        """Procesa una URL con MoA: transcripción única → proponentes paralelos → agregación."""
        if self.verbose:
            progress.print(f"  URL: {url}")

        # Paso 1: Transcripción (única)
        progress.print(
            f"  [bold cyan]▶ Transcriber[/] — obteniendo transcripción (una vez)..."
        )
        transcripcion = self.transcriber.process({"url": url})
        if not transcripcion.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error:[/] {transcripcion.get('error', 'desconocido')}"
            )
            return {"url": url, "ok": False, "error": transcripcion.get("error")}

        texto = transcripcion["texto"]
        titulo = transcripcion.get("titulo", transcripcion.get("video_id", url))
        autor = transcripcion.get("autor", "")
        sitio = transcripcion.get("sitio", "")
        chars = len(texto)
        progress.print(f"    {chars} caracteres obtenidos")

        # Guardar transcripción cruda en disco (por si algo falla después)
        raw_dir = os.path.join(self.output_dir, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        raw_path = os.path.join(
            raw_dir, f"{self._safe_filename(titulo)}.txt"
        )
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(texto)
        if self.verbose:
            progress.print(f"    Transcripción guardada: {raw_path}")

        # Paso 2: Proponentes en paralelo
        hoy = date.today().isoformat()
        n = len(self.proponent_models)
        progress.print(
            f"  [bold cyan]▶ Proponentes ({n})[/] — lanzando en paralelo..."
        )

        resultados_props: list[dict[str, Any]] = [{}] * n
        threads: list[threading.Thread] = []

        def _run_proponent(idx: int, model: str) -> None:
            """Ejecuta un proponente en su propio hilo."""
            prop = Proponent(model=model, api_key=self.api_key)
            resultados_props[idx] = prop.process(
                {"texto": texto, "tipo": tipo, "fecha": hoy, "autor": autor, "sitio": sitio}
            )

        for i, model in enumerate(self.proponent_models):
            t = threading.Thread(target=_run_proponent, args=(i, model))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Filtrar propuestas exitosas
        propuestas_validas = [
            r for r in resultados_props if r and r.get("ok")
        ]

        if not propuestas_validas:
            progress.print(
                f"  [bold red]✗ Todas las propuestas fallaron[/]"
            )
            for r in resultados_props:
                if r:
                    progress.print(f"    • {r.get('modelo', '?')}: {r.get('error')}")
            return {
                "url": url,
                "ok": False,
                "error": "Todos los proponentes fallaron",
            }

        if self.verbose:
            for r in propuestas_validas:
                progress.print(
                    f"    ✓ {r['modelo']}: {len(r.get('contenido', ''))} caracteres"
                )
            fallaron = n - len(propuestas_validas)
            if fallaron:
                progress.print(f"    ⚠ {fallaron} proponente(s) fallaron")

        # Paso 3: Agregación
        progress.print(
            f"  [bold cyan]▶ Aggregator[/] ({self.aggregator_model}) — sintetizando..."
        )
        aggregator = Aggregator(model=self.aggregator_model, api_key=self.api_key)
        documento = aggregator.process(
            {
                "texto": texto,
                "propuestas": propuestas_validas,
                "tipo": tipo,
                "fecha": hoy,
                "autor": autor,
                "sitio": sitio,
            }
        )

        if not documento.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error en agregación:[/] {documento.get('error')}"
            )
            return {"url": url, "ok": False, "error": documento.get("error")}

        # Paso 4: Escritura
        progress.print(f"  [bold cyan]▶ Writer[/] — escribiendo archivo...")
        return self._write_result(documento["contenido"], titulo, tipo, url)

    # ── Helpers ──────────────────────────────────────────────────

    def _write_result(
        self, contenido: str, titulo: str, tipo: str, url: str
    ) -> dict[str, Any]:
        """Escribe el contenido final y retorna resultado."""
        escritura = self.writer.process(
            {
                "contenido": contenido,
                "titulo": titulo,
                "tipo": tipo,
            }
        )
        if not escritura.get("ok", False):
            self.console.print(
                f"  [bold red]✗ Error al escribir:[/] {escritura.get('error')}"
            )
            return {"url": url, "ok": False, "error": escritura.get("error")}

        self.console.print(f"  [bold green]✓ OK[/] → {escritura['ruta']}")
        return {"url": url, "ok": True, "ruta": escritura["ruta"]}

    @staticmethod
    def _safe_filename(titulo: str) -> str:
        """Limpia un título para usarlo como nombre de archivo."""
        import re
        limpio = re.sub(r"[^a-zA-Z0-9áéíóúñü\s-]", "", titulo)
        limpio = re.sub(r"\s+", "_", limpio.strip().lower())
        return limpio[:80].rstrip("_")

    def _print_resumen(self, resultados: list[dict[str, Any]]) -> None:
        """Imprime resumen final de todo el lote."""
        exitosos = sum(1 for r in resultados if r.get("ok"))
        fallidos = len(resultados) - exitosos

        self.console.print()
        self.console.print("[bold]═══ Resumen ═══[/]")
        self.console.print(f"  Total: {len(resultados)}")
        self.console.print(f"  [green]Exitosos: {exitosos}[/]")
        if fallidos:
            self.console.print(f"  [red]Fallidos: {fallidos}[/]")
            for r in resultados:
                if not r.get("ok"):
                    self.console.print(f"    • {r['url']} → {r.get('error')}")
        self.console.print("[bold]══════════════[/]")