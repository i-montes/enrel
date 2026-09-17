# enrel

**enrel** es un paquete Python para la extracción de entidades y relaciones en noticias en español, pensado para su uso en redacciones periodísticas. Identifica personas, organizaciones, lugares, cargos, normas, obras y montos, y las relaciones que las vinculan dentro de un texto, para apoyar el trabajo de investigación y verificación de datos.

**Estado: etapa 0 cerrada** (cimientos). Están fijados el esquema, la guía de anotación, el corpus congelado, la
selección de plata y el humo del backbone; el evaluador ya produce una tabla completa sobre el oro de legajo
mapeado al esquema nuevo. Ver `docs/resultados/etapa-0-cierre.md` para los criterios de salida medidos. Todavía
no hay un modelo de extracción entrenado: eso es la etapa 1 en adelante.

El esquema (tipos de entidad, relaciones, equivalencias y mapeo desde legajo) está documentado en
[`docs/esquema.md`](docs/esquema.md), generado desde el código por `scripts/generar_esquema_md.py`. Las
definiciones de anotación, con ejemplos y casos límite, están en
[`docs/guia-anotacion.md`](docs/guia-anotacion.md).

Para instalar el entorno de desarrollo con `uv`, ejecuta `uv sync --all-extras`. Para correr las pruebas, ejecuta `uv run pytest`.

## Comandos disponibles

- `enrel congelar` — congela el corpus de artículos desde la base de legajo a un JSONL estable.
- `enrel muestrear` — construye la selección de plata (dirigida, por perfiles y aleatoria) con semilla fija.
- `enrel exportar-legajo` — exporta un lote anotado de legajo al formato interno de oro.
- `enrel evaluar` — evalúa predicciones contra el oro: entidades, relaciones gruesas y finas, con intervalos por bootstrap.

Cada subcomando acepta `--help` para ver sus parámetros.
