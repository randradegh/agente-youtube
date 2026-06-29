"""
Entry point del sistema multi-agente para procesar videos de YouTube.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

from dotenv import load_dotenv

from coordinator import Coordinator

VALID_TYPES = {"resumen", "articulo", "tldr", "analisis", "notas", "transcripcion", "ideas_mkt"}


def _read_csv(path: str) -> list[tuple[str, str]]:
    """Lee urls.csv, valida cada fila y retorna lista de (url, tipo)."""
    items: list[tuple[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # i = linea real (header=1)
            url = row.get("urls", "").strip()
            tipo = row.get("type", "").strip().lower()

            if not url:
                continue  # fila vacia, se salta

            if tipo and tipo not in VALID_TYPES:
                print(f"Error [linea {i}]: tipo '{tipo}' no valido para '{url}'")
                print(f"  Tipos validos: {', '.join(sorted(VALID_TYPES))}")
                sys.exit(1)

            if not tipo:
                tipo = "tldr"

            items.append((url, tipo))

    return items


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Agente YouTube - Procesa videos con agentes de IA via OpenRouter"
    )
    parser.add_argument(
        "--csv",
        default="urls.csv",
        help="Archivo CSV con columnas urls,type (default: urls.csv). "
        "Type vacio = tldr",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directorio de salida (default: ./output)",
    )
    parser.add_argument(
        "--transcriber-model",
        default="minimax/minimax-m3",
        help="Modelo OpenRouter para Transcriber (default: minimax/minimax-m3)",
    )
    parser.add_argument(
        "--reviewer-model",
        default="mistralai/mistral-nemo",
        help="Modelo OpenRouter para Reviewer (default: mistralai/mistral-nemo)",
    )
    parser.add_argument(
        "--generator-model",
        default="deepseek/deepseek-chat",
        help="Modelo OpenRouter para Generator (default: deepseek/deepseek-chat)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key de OpenRouter (default: $OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra progreso detallado",
    )

    args = parser.parse_args()

    # Leer CSV
    if not os.path.isfile(args.csv):
        print(f"Error: No se encuentra el archivo: {args.csv}")
        sys.exit(1)

    items = _read_csv(args.csv)

    if not items:
        print("Error: El archivo CSV no contiene URLs validas")
        sys.exit(1)

    print(f"Procesando {len(items)} video(s):")
    for url, tipo in items:
        print(f"  * {url} -> {tipo}")
    print(f"  Transcriber: {args.transcriber_model}")
    print(f"  Reviewer:    {args.reviewer_model}")
    print(f"  Generator:   {args.generator_model}")
    print()

    coordinator = Coordinator(
        output_dir=args.output_dir,
        transcriber_model=args.transcriber_model,
        reviewer_model=args.reviewer_model,
        generator_model=args.generator_model,
        api_key=args.api_key or os.getenv("OPENROUTER_API_KEY", ""),
        verbose=args.verbose,
    )

    resultados = coordinator.process_urls(items)

    # Codigo de salida: 0 si todo OK, 1 si algun fallo
    sys.exit(0 if all(r.get("ok") for r in resultados) else 1)


if __name__ == "__main__":
    main()