# Humo del backbone

Fecha: 2026-09-17 · comando: `taskset -c 0-3 uv run python scripts/humo_backbone.py --modelo BSC-LT/MrBERT-es --tokens 4096 --lote 2`

## Entorno CUDA

Máquina: Ryzen 7 5700X (16 hilos), 31 GB RAM, RTX 4060 8 GB, driver NVIDIA 610.57 (CUDA 13). El índice `cu124` de PyTorch (`https://download.pytorch.org/whl/cu124`, añadido a `pyproject.toml` en `[tool.uv.sources]`/`[[tool.uv.index]]`) resolvió sin problemas con `uv sync --all-extras`: `torch==2.6.0+cu124`, `transformers==5.17.0` (soporta `modernbert`), `onnx==1.22.0`, `onnxruntime==1.30.0`. No hizo falta probar `cu126` ni `cu128`. `torch.cuda.is_available()` → `True`, dispositivo `NVIDIA GeForce RTX 4060`.

La exportación a ONNX de MrBERT-es (arquitectura ModernBERT) funcionó con la atención por defecto (`sdpa`); no hizo falta el arreglo `attn_implementation="eager"` que preveía el guion (queda implementado en `exportar_onnx` como reintento automático por si un modelo distinto lo necesita, con el campo `arreglo_atencion_eager` en el informe indicando si se usó).

## BSC-LT/MrBERT-es

**Carga**: modelo = BSC-LT/MrBERT-es, parametros = 149653248, vocabulario = 51200, max_posiciones = 8192

**Tokens**: tokens_por_palabra = 1.35, p50_tokens = 574, p95_tokens = 1206, max_tokens = 2462, articulos = 200

**Paso GPU**: gpu = NVIDIA GeForce RTX 4060, tokens = 4096, lote = 2, vram_pico_gb = 1.53, segundos_paso = 1.47

**ONNX**: onnx = datos/humo/MrBERT-es.onnx, mb = 571.4, diferencia_max = 0.0003299713134765625, arreglo_atencion_eager = False

**CPU fp32**: fichero = MrBERT-es.onnx, tokens = 1557, hilos = 4, mediana_s = 1.671, p95_s = 1.703, rss_gb = 6.03

**CPU int8**: fichero = MrBERT-es-int8.onnx, tokens = 1557, hilos = 4, mediana_s = 1.287, p95_s = 1.306, rss_gb = 6.03


Criterio: carga sin errores; paso GPU con VRAM pico < 8 GB; diferencia torch-ONNX < 1e-3; mediana int8 < 3 s por ~1.500 tokens con 4 hilos. Si se cumple, el respaldo se mide solo como referencia.

**Nota sobre el RSS reportado**: el `rss_gb` de las tablas CPU fp32/CPU int8 es la memoria residente de todo el proceso de `scripts/humo_backbone.py` (`resource.getrusage(RUSAGE_SELF)`), que en la misma ejecución carga torch, transformers y ONNX Runtime, y va cargando sucesivamente los dos modelos (fp32 e int8) de MrBERT-es y después los del respaldo. No es la memoria del pipeline final en CPU: esa se medirá en la etapa 3 con un proceso que solo cargue ONNX Runtime y un único modelo, y será notablemente menor que los 6,03 GB aquí reportados.

## jhu-clsp/mmBERT-small

**Carga**: modelo = jhu-clsp/mmBERT-small, parametros = 140493696, vocabulario = 256000, max_posiciones = 8192

**Tokens**: tokens_por_palabra = 1.38, p50_tokens = 579, p95_tokens = 1266, max_tokens = 2508, articulos = 200

**Paso GPU**: gpu = NVIDIA GeForce RTX 4060, tokens = 4096, lote = 2, vram_pico_gb = 1.12, segundos_paso = 0.53

**ONNX**: onnx = datos/humo/mmBERT-small.onnx, mb = 536.4, diferencia_max = 0.0012054443359375, arreglo_atencion_eager = False

**CPU fp32**: fichero = mmBERT-small.onnx, tokens = 1429, hilos = 4, mediana_s = 0.76, p95_s = 0.77, rss_gb = 6.03

**CPU int8**: fichero = mmBERT-small-int8.onnx, tokens = 1429, hilos = 4, mediana_s = 0.585, p95_s = 0.595, rss_gb = 6.03

## Aviso: calidad de la cuantización dinámica a int8

`medir_cpu` solo cronometra; no compara salidas. Se hizo aparte una comparación puntual de `last_hidden_state` entre la sesión ONNX fp32 y la int8, sobre el mismo artículo de ~1.500 tokens, para las dos arquitecturas:

- MrBERT-es: diferencia máxima = 64.19, diferencia media = 1.07 (norma de la salida fp32 ≈ 3286.95).
- mmBERT-small: diferencia máxima = 177.19, diferencia media = 2.34 (norma de la salida fp32 ≈ 2496.10).

En ambos casos la diferencia máxima supera claramente el umbral de 1 que el brief usa como señal de salida degradada: `quantize_dynamic` (cuantización dinámica por pesos, sin calibración de activaciones) degrada notablemente la representación de estos backbones tipo ModernBERT. Esto no bloquea el humo (el criterio de velocidad int8 < 3 s sí se cumple), pero descarta int8 dinámico como ruta de despliegue sin más trabajo; la decisión fp16/int8 para producción se retoma en la etapa 3 con el modelo ya entrenado (calibración estática, per-channel, o cuantizar solo capas concretas).

## Decisión

**MrBERT-es sigue como backbone.** Cumple los cuatro criterios de humo: carga sin errores (149.653.248 parámetros, vocabulario 51.200, `max_position_embeddings` = 8.192); el paso de entrenamiento (retropropagación incluida, bf16, `gradient_checkpointing_enable()`, lote 2 × 4.096 tokens) usa 1,53 GB de VRAM pico en 1,47 s, muy por debajo de los 8 GB de la RTX 4060; la exportación a ONNX (opset 17, sin necesitar el arreglo `eager`) difiere de torch en 3,3e-4, por debajo de 1e-3; y la mediana de 20 pasadas en CPU a 4 hilos sobre un artículo real de 1.557 tokens es 1,287 s en int8 (y 1,671 s en fp32), por debajo de los 3 s. La tokenización sobre 200 artículos del corpus congelado da 1,35 tokens por palabra y p95 = 1.206 tokens, lo que sugiere `max_len` ≈ 1.280–1.536 para el entrenamiento (con margen sobre el máximo observado de 2.462).

El respaldo `jhu-clsp/mmBERT-small` se midió solo como referencia (no fue necesario activarlo): carga más rápida y más liviana en CPU (fp32 0,76 s, int8 0,585 s) pero con un vocabulario mucho mayor (256.000 frente a 51.200) y una diferencia torch-ONNX algo mayor (1,2e-3, justo en el límite del criterio). Con MrBERT-es cumpliendo todo, no hace falta cambiar de backbone.

Queda anotada la degradación de `quantize_dynamic` a int8 (ver aviso arriba) como pendiente para la etapa 3, sin que bloquee esta tarea.
