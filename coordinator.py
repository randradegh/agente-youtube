"""
Coordinator — Orquesta el pipeline de agentes para cada URL.
"""

from __future__ import annotations

from typing import Any

from agents.transcriber import Transcriber
from agents.reviewer import Reviewer
from agents.generator import Generator
from agents.writer import Writer

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


class Coordinator:
    """Orquesta el pipeline: Transcriber → Reviewer → Generator → Writer."""

    def __init__(
        self,
        output_dir: str = "./output",
        transcriber_model: str = "minimax/minimax-m3",
        reviewer_model: str = "nvidia/nemotron-3-super-120b-a12b:free",
        generator_model: str = "deepseek/deepseek-chat",
        api_key: str = "",
        verbose: bool = False,
    ):
        self.transcriber = Transcriber()
        self.reviewer = Reviewer(model=reviewer_model, api_key=api_key)
        self.generator = Generator(model=generator_model, api_key=api_key)
        self.writer = Writer(output_dir=output_dir)
        self.verbose = verbose
        self.console = Console()

    def process_urls(
        self, items: list[tuple[str, str]]
    ) -> list[dict[str, Any]]:
        """Procesa una lista de (url, tipo) y devuelve los resultados."""
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

            for url, tipo in items:
                resultado = self._process_single(url, tipo, progress)
                resultados.append(resultado)
                progress.update(task, advance=1)

        self._print_resumen(resultados)
        return resultados

    def _process_single(
        self, url: str, tipo: str, progress: Progress
    ) -> dict[str, Any]:
        """Procesa una URL individual a través del pipeline completo."""
        if self.verbose:
            progress.print(f"  URL: {url}")

        # Paso 1: Transcripción
        progress.print(f"  [bold cyan]▶ Transcriber[/] — obteniendo transcripción...")
        transcripcion = self.transcriber.process({"url": url})
        if not transcripcion.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error:[/] {transcripcion.get('error', 'desconocido')}"
            )
            return {"url": url, "ok": False, "error": transcripcion.get("error")}

        if self.verbose:
            chars = len(transcripcion.get("texto", ""))
            progress.print(f"    {chars} caracteres obtenidos")

        # Paso 2: Revisión
        progress.print(f"  [bold cyan]▶ Reviewer[/] — revisando texto...")
        revisado = self.reviewer.process(
            {"texto": transcripcion["texto"]}
        )
        texto_revisado = revisado.get("texto", transcripcion["texto"])
        if not revisado.get("ok", False) and self.verbose:
            progress.print(
                f"    ⚠ {revisado.get('error', '')} — usando texto crudo"
            )

        # Paso 3: Generación
        progress.print(
            f"  [bold cyan]▶ Generator[/] — generando {tipo}..."
        )
        documento = self.generator.process(
            {"texto": texto_revisado, "tipo": tipo}
        )
        if not documento.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error al generar:[/] {documento.get('error')}"
            )
            return {"url": url, "ok": False, "error": documento.get("error")}

        # Paso 4: Escritura
        progress.print(f"  [bold cyan]▶ Writer[/] — escribiendo archivo...")
        escritura = self.writer.process(
            {
                "contenido": documento["contenido"],
                "titulo": transcripcion.get("titulo", transcripcion.get("video_id", url)),
                "tipo": tipo,
            }
        )
        if not escritura.get("ok", False):
            progress.print(
                f"  [bold red]✗ Error al escribir:[/] {escritura.get('error')}"
            )
            return {"url": url, "ok": False, "error": escritura.get("error")}

        progress.print(
            f"  [bold green]✓ OK[/] → {escritura['ruta']}"
        )
        return {
            "url": url,
            "ok": True,
            "ruta": escritura["ruta"],
        }

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