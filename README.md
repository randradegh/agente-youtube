# Agente YouTube — Sistema Multi-Agente

Procesa videos de YouTube usando una cadena de agentes de IA vía OpenRouter:

1. **Transcriber** — obtiene la transcripción del video
2. **Reviewer** — limpia y estructura el texto (modelo: Nemotron free)
3. **Generator** — genera un documento con el formato deseado (modelo: DeepSeek Chat)
4. **Writer** — escribe el resultado al filesystem

## Setup

```bash
# 1. Sincronizar dependencias
uv sync

# 2. Configurar API key
cp .env.example .env
# Editar .env con: OPENROUTER_API_KEY="sk-or-..."

# 3. Crear urls.csv con las URLs a procesar
```

## Activar el entorno

El script requiere las dependencias del proyecto. Dos formas de ejecutarlo:

```bash
# Opcion A — con uv run (recomendada, activa el entorno automaticamente)
uv run python3 main.py

# Opcion B — activar el venv manualmente
source .venv/bin/activate
python main.py
# ...
deactivate
```

## Uso

```bash
# Ejecutar con el urls.csv por defecto
uv run python3 main.py

# Especificar otro archivo CSV
uv run python3 main.py --csv mi_lista.csv

# Directorio de salida distinto
uv run python3 main.py --output-dir ./mis_reportes

# Modelos personalizados
uv run python3 main.py \
    --reviewer-model minimax/minimax-m3 \
    --generator-model deepseek/deepseek-chat
```

## Formato del CSV

Archivo de entrada por defecto: `urls.csv`

```
urls,type
https://youtu.be/XxYyZz,tldr
https://youtube.com/watch?v=AbCdEf,analisis
https://youtu.be/GhIjKl,
```

- **Cabecera:** `urls,type` (se ignora al procesar)
- **urls:** URL completa de YouTube (cualquier formato: youtube.com/watch, youtu.be, shorts, etc.)
- **type:** Tipo de documento (opcional). Valores validos: `resumen`, `articulo`, `tldr`, `analisis`, `notas`, `transcripcion`
- Si `type` se deja vacio, por defecto es `tldr`
- Cada fila puede tener su propio tipo
- Si un tipo no es valido, el script muestra el error y termina

## Tipos de documento

| Tipo | Descripcion |
|---|---|
| `resumen` | Resumen ejecutivo: bullet points clave + conclusion |
| `articulo` | Articulo/blog post completo |
| `tldr` | TL;DR ultra conciso (3-5 lineas) |
| `analisis` | Analisis tecnico/desglose estructurado |
| `notas` | Notas de estudio: conceptos y referencias |
| `transcripcion` | Transcripcion limpia (sin timestamps) |

## Modelos

| Agente | Modelo por defecto | Costo |
|---|---|---|
| Reviewer | `nvidia/nemotron-3-super-120b-a12b:free` | Gratuito |
| Generator | `deepseek/deepseek-chat` | Pago |
| Transcriber | (no usa LLM) | — |

Se puede sobrescribir con `--reviewer-model` y `--generator-model`.

## Estructura

```
agente_youtube/
├── main.py              # Entry point
├── coordinator.py       # Orquestador del pipeline
├── urls.csv             # Lista de URLs a procesar
├── agents/              # Agentes especializados
├── models/              # Cliente OpenRouter
├── prompts/             # System prompts en markdown
├── output/              # Documentos generados
├── .env                 # API key (no comitear)
└── pyproject.toml       # Dependencias
```