# PR — Sistema Multi-Agente para Procesamiento de Videos YouTube

## 1. Resumen

Sistema Python autónomo (vive fuera de Hermes) que orquesta múltiples agentes de IA para procesar videos de YouTube: obtiene la transcripción, la revisa, genera un documento con el formato deseado y lo escribe al filesystem. Cada agente usa un modelo de OpenRouter diferente, configurable por el usuario.

---

## 2. Arquitectura

### 2.1 Agentes

El sistema tiene 4 agentes especializados + 1 coordinador:

| Agente | Rol | Modelo (default) | OpenRouter ID |
|---|---|---|---|---|
| **Transcriber** | Obtiene la transcripción del video (YouTube Transcript API) | MiniMax M3 | `minimax/minimax-m3` |
| **Reviewer** | Revisa, limpia y estructura el texto crudo | MiniMax M3 | `minimax/minimax-m3` |
| **Generator** | Genera el documento final con el formato elegido | DeepSeek | `deepseek/deepseek-chat` |
| **Writer** | Escribe el resultado al filesystem | — | Sin modelo (operación local) |
| **Coordinator** | Orquesta el pipeline, maneja errores, reporta progreso | — | Sin modelo (lógica Python) |

Cada modelo es configurable por CLI con `--transcriber-model`, `--reviewer-model`, `--generator-model` (formato OpenRouter: `proveedor/modelo`).

### 2.2 Pipeline

```
URL(s) YouTube
    │
    ▼
┌──────────────┐
│  Transcriber  │  Obtiene transcripción vía youtube_transcript_api
│  (MiniMax)   │  → texto crudo + metadatos (título, duración, idioma)
└──────┬───────┘
       │ texto_crudo
       ▼
┌──────────────┐
│   Reviewer    │  Limpia: quita marcas de tiempo, corrige segmentación,
│  (MiniMax)   │  detecta cambios de orador, unifica párrafos
└──────┬───────┘
       │ texto_revisado
       ▼
┌──────────────┐
│   Generator   │  Genera documento final según el tipo elegido
│  (DeepSeek)  │  → texto con formato (Markdown)
└──────┬───────┘
       │ documento_final
       ▼
┌──────────────┐
│    Writer     │  Escribe archivo .md en directorio de salida
│  (local)     │  Nombre: <título_normalizado>_<YYYY-MM-DD>_<tipo>.md
└──────────────┘
       │
       ▼
    Archivo .md
```

### 2.3 Comunicación

Toda la comunicación entre agentes es **síncrona y directa**: cada agente es una clase Python que implementa `process(data: dict) -> dict`. El coordinador llama secuencialmente:

```python
transcripcion = transcriber.process({"url": url})
revisado = reviewer.process({"texto": transcripcion["texto"]})
documento = generator.process({"texto": revisado["texto"], "tipo": tipo})
writer.process({"contenido": documento["contenido"], "titulo": transcripcion["titulo"]})
```

Sin colas, sin archivos intermedios, sin procesos separados.

---

## 3. Tipos de Documento

El sistema soporta los siguientes tipos, pasados con `--type`:

| Tipo | Descripción |
|---|---|
| `resumen` | Resumen ejecutivo: bullet points clave + conclusión (2-3 párrafos) |
| `articulo` | Artículo/blog post completo con introducción, desarrollo y conclusión |
| `tldr` | TL;DR ultra conciso: 3-5 líneas máximo |
| `analisis` | Análisis técnico/desglose estructurado con secciones |
| `notas` | Notas de estudio: preguntas, conceptos, referencias |
| `transcripcion` | Transcripción limpia (sin timestamps, oradores marcados) |

Extensible: añadir un tipo nuevo requiere solo agregar un prompt en Generator.

---

## 4. Interfaz CLI

```bash
cd agente_youtube
python main.py \
    --urls urls.txt \
    --type resumen \
    --output-dir ./salidas \
    --transcriber-model minimax/minimax-m3 \
    --reviewer-model minimax/minimax-m3 \
    --generator-model deepseek/deepseek-chat \
    --api-key <OPENROUTER_API_KEY>
```

También por variable de entorno: `OPENROUTER_API_KEY`.

Argumentos:

| Argumento | Requerido | Default | Descripción |
|---|---|---|---|
| `--urls` | Sí | — | Ruta a archivo TXT con una URL por línea |
| `--type` | Sí | — | Tipo de documento a generar |
| `--output-dir` | No | `./output` | Directorio donde guardar los documentos |
| `--transcriber-model` | No | `minimax/minimax-m3` | Modelo para transcripción |
| `--reviewer-model` | No | `minimax/minimax-m3` | Modelo para revisión |
| `--generator-model` | No | `deepseek/deepseek-chat` | Modelo para generación |
| `--api-key` | No | `$OPENROUTER_API_KEY` | API key de OpenRouter |
| `--verbose` | No | `False` | Muestra progreso detallado |

---

## 5. Estructura de Archivos

```
agente_youtube/
├── main.py              # Entry point + CLI parsing
├── coordinator.py       # Pipeline orchestrator
├── agents/
│   ├── __init__.py
│   ├── base.py          # Abstract base class Agent
│   ├── transcriber.py   # YouTube transcript → texto crudo
│   ├── reviewer.py      # Texto crudo → texto revisado
│   ├── generator.py     # Texto revisado → documento formateado
│   └── writer.py        # Documento → archivo en disco
├── models/
│   ├── __init__.py
│   └── openrouter_api.py  # Cliente OpenRouter (OpenAI SDK wrapper)
├── prompts/
│   ├── transcriber.md   # System prompt para Transcriber
│   ├── reviewer.md      # System prompt para Reviewer
│   └── generator.md     # System prompt para Generator (template por tipo)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 6. Dependencias (Python)

- `openai` — SDK para consumir OpenRouter (API compatible con OpenAI)
- `youtube_transcript_api` — Obtener transcripciones de YouTube
- `python-dotenv` — Cargar .env
- `pydantic` — Validación de datos entre agentes
- `rich` — Logging bonito en terminal (progreso, resultados)

---

## 7. Manejo de Errores

- **URL inválida o video sin transcripción**: Transcriber reporta error, Coordinator lo saltea y continúa con la siguiente URL.
- **Fallo en API de OpenRouter (rate limit, timeout)**: Reintento automático (3 intentos con backoff exponencial).
- **Error en Reviewer/Generator**: Se reintenta el paso; si persiste, se usa el texto crudo como fallback.
- **Error de escritura**: Writer reporta error, Coordinator loggea y continúa.
- Resumen final: cuántas URLs se procesaron con éxito y cuántas fallaron.

---

## 8. Seguridad

- La API key se pasa por `--api-key` o variable de entorno `OPENROUTER_API_KEY`. Nunca hardcodeada.
- No se ejecuta código generado por los agentes — solo texto.
- No se sube nada a internet — solo lectura de YouTube + llamadas a OpenRouter.

---

## 9. Próximos Pasos

1. ✅ Este PR.md aprobado
2. ⬜ Crear estructura de directorios y archivos base (`uv init`, etc.)
3. ⬜ Implementar `models/openrouter_api.py` (wrapper OpenRouter con OpenAI SDK)
4. ⬜ Implementar `agents/base.py` (clase abstracta Agent)
5. ⬜ Implementar cada agente en orden: Transcriber → Reviewer → Generator → Writer
6. ⬜ Implementar `coordinator.py` (orquestador del pipeline)
7. ⬜ Implementar `main.py` (CLI con argparse)
8. ⬜ Escribir prompts en `prompts/` (transcriber.md, reviewer.md, generator.md)
9. ⬜ Probar con 1-2 videos reales
10. ⬜ Escribir README.md

---

## 10. Notas

- Usa `uv` para el entorno virtual (ya disponible en el sistema).
- Los prompts son archivos `.md` independientes para facilitar edición sin tocar código.
- Sistema diseñado para ser simple: un solo proceso, sin async, sin colas, sin Docker.
- Modelos default: MiniMax M3 para transcripción/revisión (económico y rápido) y DeepSeek para generación (más calidad de razonamiento).