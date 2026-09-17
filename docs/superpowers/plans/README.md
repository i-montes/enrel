# Planes de implementación de enrel

Especificación: `docs/superpowers/specs/2026-09-16-enrel-diseno.md`. Los planes argumentan desde ella; quien ejecute lee ambos.

Cuatro planes, uno por etapa. Cada etapa produce software que funciona y se mide por sí solo, y termina con una tabla escrita en `docs/resultados/`. Ninguna etapa arranca sin el criterio de salida de la anterior.

| Plan | Etapa | Produce | Depende de |
|---|---|---|---|
| `2026-09-16-etapa-0-cimientos.md` | 0 | Paquete `enrel`, esquema, mapeo desde legajo, exportador de oro, corpus congelado y muestreado, evaluador completo, guía de anotación, humo del backbone. Primera tabla real: plata de legajo contra oro. | nada |
| `2026-09-16-etapa-1-maestro.md` | 1 | Cliente MiniMax, prompts desde la guía, anclaje y filtros, anotación por documento, puerta medida sobre la prueba, línea base GLiNER zero-shot. | etapa 0; los 50 de prueba corregidos por el usuario |
| `2026-09-16-etapa-2-modelo.md` | 2 | Modelo (backbone + dos cabezas), tensores, bucle de entrenamiento, cordura, agrupación, decodificación, pipeline torch y CLI `enrel extraer`; primer entrenamiento con plata y evaluación completa. | etapa 1 con puerta pasada; plata anotada |
| `2026-09-16-etapa-3-cierre.md` | 3 | Segunda etapa con oro, exportación ONNX y cuantización, pipeline ONNX Runtime, medición en CPU, exportador FollowTheMoney, revisión de falsos positivos, ficha de modelo y publicación v0.1. | etapa 2 |

## Cómo orquestar

- Skill requerida: `superpowers:subagent-driven-development`. Un subagente fresco por tarea, con `model: "sonnet"`; el orquestador revisa entre tareas. El usuario pidió explícitamente esta división: Opus orquesta, Sonnet escribe.
- Cada tarea lleva sus ficheros, sus interfaces (lo que consume y lo que produce, con firmas exactas), pasos con casillas, tests primero, y un commit.
- Todo el código, los identificadores, los comentarios, los mensajes de commit y la documentación van en español, como en la especificación. Las librerías se usan con sus nombres.
- Nada bajo `datos/` ni `datos-anteriores/` se commitea; el `.gitignore` ya lo excluye. Los tests que necesitan texto real leen de `datos-anteriores/` y se saltan (`pytest.skip`) si no existe, para que la suite corra en cualquier máquina.
- Los resultados medidos se escriben siempre en `docs/resultados/<etapa>-<tema>.md` con la fecha, los hashes de los datos y el comando exacto que los produjo.

## Convenciones técnicas comunes

- Python 3.12 con `uv`; `pyproject.toml` con `[project]` y `[tool.uv]`; entorno en `.venv`. Comandos: `uv run pytest`, `uv run enrel …`.
- Tests con `pytest`; los que tocan la GPU o la red llevan `@pytest.mark.gpu` o `@pytest.mark.red` y se excluyen por defecto (`-m "not gpu and not red"`).
- Formato con `ruff format` y lint con `ruff check`; ambos en `pyproject.toml`.
- Offsets siempre de caracteres sobre `Documento.texto` normalizado a NFC. Nunca índices de tokens en datos persistidos.
- Semillas fijas y registradas. Ficheros de datos con hash SHA-256 en cada informe.
