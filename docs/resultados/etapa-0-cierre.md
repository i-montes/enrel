# Etapa 0 — Cierre

**Fecha:** 2026-09-17

Cierra la etapa 0 (cimientos) de la spec `docs/superpowers/specs/2026-09-16-enrel-diseno.md`. Los informes de
detalle están en `docs/resultados/etapa-0-corpus.md` (corpus congelado y selección de plata),
`docs/resultados/etapa-0-legajo.md` (techo del maestro de legajo sobre la prueba) y
`docs/resultados/etapa-0-backbone.md` (humo del backbone).

## Criterios de salida (spec §10, etapa 0)

| Criterio | Cumplido | Cifra |
|---|---|---|
| El backbone pasa el humo o se elige el respaldo | Sí | `BSC-LT/MrBERT-es` cumple los cuatro criterios de humo: carga sin errores (149.653.248 parámetros), VRAM pico 1,53 GB con lote 2×4.096 bf16 (< 8 GB), diferencia torch-ONNX 3,3e-4 (< 1e-3), mediana en CPU a 4 hilos sobre ~1.500 tokens 1,29 s en int8 y 1,67 s en fp32 (< 3 s). No hizo falta el respaldo `jhu-clsp/mmBERT-small`. |
| La muestra está fijada con semilla | Sí | Corpus congelado: 63.991 artículos (hash `c0d277fbe9f61a06d21e87b41792951fed9321fc918e8269c1f9088c2bd0dafd`). Selección de plata con semilla 2026: 3.539 artículos (dirigido 2.040, perfiles 400, aleatorio 1.099; 30 de humo del maestro), hash `1b886fa7a32dac821b626eba2c1c0be054c10b0013318cd291e711d30ab1a18f`. |
| La guía tiene las 17 definiciones con ejemplos | Sí | `docs/guia-anotacion.md` define los 7 tipos y las 17 relaciones, cada una con definición, ≥ 3 ejemplos y ≥ 2 «no es»; lo comprueba `enrel/anotacion/guia.py:cargar_guia` y `tests/test_guia.py`. |
| El evaluador produce una tabla sobre los 40 perfiles | Parcial | El evaluador (`enrel evaluar`, `enrel/evaluacion/`) ya produce la tabla completa (entidades estricto/parcial, RE, RE+, clases finas, intervalos por bootstrap) sobre los 50 documentos de `datos/conjuntos/prueba.jsonl`, como primera tabla real (`docs/resultados/etapa-0-legajo.md`). Los 40 perfiles del Quién es Quién todavía no están anotados por el usuario, así que la tabla específica sobre ellos queda pendiente (ver «Pendiente» abajo). |

## Cifras clave

| Cifra | Valor |
|---|---|
| Artículos congelados | 63.991 |
| Selección de plata, total | 3.539 (dirigido 2.040 · perfiles 400 · aleatorio 1.099; 30 de humo del maestro) |
| Entidades, F1 estricto (techo del maestro de legajo, esquema nuevo, prueba) | 0,75 [0,71, 0,78] |
| Entidades, F1 parcial | 0,78 |
| RE+, F1 micro | 0,56 [0,50, 0,61] |
| RE+, F1 micro a clases finas | 0,53 |
| Backbone: parámetros | 149,7 M |
| Backbone: tokens por palabra | 1,35 |
| Backbone: p95 tokens | 1.206 |
| VRAM pico (lote 2×4.096 bf16) | 1,53 GB |
| ONNX: tamaño / diferencia vs. torch | 571 MB / 3,3e-4 |
| CPU a 4 hilos, ~1.557 tokens, fp32 | 1,67 s |
| CPU a 4 hilos, ~1.557 tokens, int8 | 1,29 s |

Decisión de backbone: sigue `MrBERT-es`. Aviso: la cuantización dinámica a int8 (`quantize_dynamic`) degrada
notablemente la salida de este backbone (diferencia máxima muy por encima del umbral de referencia); no bloquea
el humo de velocidad, pero la ruta de despliegue int8 se decide en la etapa 3 con el modelo ya entrenado.

## Pendiente: cuando el usuario cierre el lote de los 40 perfiles

Los 40 perfiles del Quién es Quién todavía no están anotados por el usuario. Cuando el usuario cierre ese lote
en legajo, quedan estos pasos, que este cierre deja anotados pero no ejecuta:

1. Exportar el lote: `enrel exportar-legajo --lote N --solo-validos --salida datos/anotado/oro-perfiles.jsonl`.
2. Repartir los 40 documentos con `scripts/repartir_perfiles.py` (semilla fija): 15 a
   `datos/conjuntos/prueba_dirigida.jsonl`, 10 sumados a `datos/conjuntos/desarrollo.jsonl`, 15 sumados a
   `datos/conjuntos/oro_entrenamiento.jsonl`, y los 40 `doc_id` sumados a `datos/conjuntos/protegidos.txt`.
3. Volver a muestrear (`enrel muestrear`, misma semilla 2026) ahora con `protegidos.txt` ampliado, y anotar aquí
   los dos hashes: el de `protegidos.txt` ampliado y el de la nueva `seleccion.jsonl`.

Esto ya está anotado como pendiente en `docs/resultados/etapa-0-corpus.md` (sección «Selección de plata»).
`scripts/repartir_perfiles.py` no existe todavía; se escribe cuando el usuario entregue el lote.

## Estado

La etapa 0 queda cerrada con los criterios anteriores cumplidos, salvo la tabla específica sobre los 40
perfiles, que depende de una anotación del usuario todavía pendiente y no bloquea el arranque de la etapa 1
(el evaluador y el techo de legajo ya están medidos sobre los 50 documentos de prueba).
