Esta tabla compara, sobre los 50 documentos de `datos/conjuntos/prueba.jsonl`, el oro de legajo
—mayormente corrección humana sobre una propuesta de LLM— mapeado al esquema nuevo de enrel,
contra la plata que MiniMax-M3 produjo con el prompt v5 sin pistas para esos mismos 100
artículos del lote 8 (`oro100-sin-pistas.jsonl`), filtrada a los 50 de prueba y mapeada con el
mismo esquema.

La cifra es el techo del maestro de legajo medido con el evaluador nuevo de enrel: el modelo que
generó la plata de legajo, evaluado contra el oro corregido a mano, con el mismo criterio (RE,
RE+, tipos finos) que usará la etapa 1 para juzgar al maestro nuevo. Es la referencia que ese
maestro nuevo debe superar; no es una medida de un sistema de enrel, que todavía no existe.

Lo que esta tabla no mide: relaciones entre párrafos. Tanto el oro de legajo como la plata de
MiniMax se anotaron párrafo a párrafo, así que ninguna de las dos fuentes podía marcar una
relación entre entidades que aparecen en párrafos distintos del mismo artículo; esas relaciones
están ausentes de ambos lados y no entran en el cálculo de precisión, cobertura ni F1.

La tabla se rehizo tras el cambio de vigencia (ocupa_cargo recuperó el atributo titular/aspirante,
ortogonal a la vigencia) y de rangos (apoya_a y se_opone_a admiten norma): el oro y la plata de
esta versión se reexportaron con ese esquema, así que la fila de vigencia ya no sale en 1,00 por
defecto.

**Nota (2026-09-17, salida de monto y obra):** `monto` y `obra` salieron de `TIPOS` (ver
`enrel/esquema/tipos.py`; motivo y cifras completas en `etapa-0-cierre.md`). El oro y la plata se
reexportaron otra vez con el exportador que descarta esos dos grupos y las relaciones que los
tocan. La tabla de abajo, por eso, ya no tiene filas `monto` ni `obra` y el `n` global de
entidades bajó de 2290 a 2183: el denominador de entidades cambió de 7 tipos a 5, así que el F1
estricto y parcial que suben (0,75→0,76 estricto; 0,78→0,79 parcial) **no son una mejora del
maestro** — es la misma predicción de siempre, sin las dos categorías que peor promediaban
(`obra` con F1 0,39 estricto era la más floja de la tabla vieja). Las filas de relaciones bajan
de 530 a 523 en RE/RE+ micro porque siete de las relaciones `vinculo_sin_tipo` de este conjunto
de prueba tocaban una entidad `obra` u `monto`; ninguna otra relación cambia de valor, porque
ninguna otra tocaba esos dos tipos.

# Evaluación de MiniMax v5 sin pistas (techo del maestro de legajo), esquema sin monto/obra

Fecha: 2026-09-17 · documentos: 50

- `oro`: `2d54c8da3e05788bb6607a7006cfb53b4354615e08a62d1d1f48553ec10f7bbf`
- `pred`: `69fb0754babd4ba72098406a517e0c9aa152ce34c40f88ed51f79578f25eda1c`

### Entidades, estricto

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| cargo | 376 | 0.73 | 0.59 | 0.65 |  |
| lugar | 252 | 0.73 | 0.73 | 0.73 |  |
| norma | 66 | 0.64 | 0.35 | 0.45 |  |
| organizacion | 746 | 0.78 | 0.75 | 0.76 |  |
| persona | 743 | 0.87 | 0.81 | 0.84 |  |
| global | 2183 | 0.79 | 0.73 | 0.76 | [0.73, 0.79] |

### Entidades, parcial

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| cargo | 376 | 0.82 | 0.67 | 0.74 |  |
| lugar | 252 | 0.75 | 0.75 | 0.75 |  |
| norma | 66 | 0.72 | 0.39 | 0.51 |  |
| organizacion | 746 | 0.81 | 0.79 | 0.80 |  |
| persona | 743 | 0.88 | 0.82 | 0.85 |  |
| global | 2183 | 0.83 | 0.76 | 0.79 | [0.76, 0.82] |

### Relaciones gruesas, RE

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| apoya_a | 39 | 0.65 | 0.33 | 0.44 |  |
| contrato_a | 3 | insuficiente | insuficiente | insuficiente |  |
| dirige | 40 | 0.47 | 0.17 | 0.25 |  |
| familiar_de | 19 | 0.73 | 0.84 | 0.78 |  |
| financia_a | 1 | insuficiente | insuficiente | insuficiente |  |
| fundo | 2 | insuficiente | insuficiente | insuficiente |  |
| investigado_por | 18 | 0.50 | 0.11 | 0.18 |  |
| miembro_de | 56 | 0.48 | 0.50 | 0.49 |  |
| nombro_a | 7 | insuficiente | insuficiente | insuficiente |  |
| ocupa_cargo | 245 | 0.75 | 0.60 | 0.67 |  |
| parte_de | 11 | 0.13 | 0.36 | 0.19 |  |
| propietario_de | 12 | 1.00 | 1.00 | 1.00 |  |
| se_opone_a | 17 | 0.50 | 0.35 | 0.41 |  |
| socio_de | 2 | insuficiente | insuficiente | insuficiente |  |
| sucedio_a | 6 | insuficiente | insuficiente | insuficiente |  |
| trabaja_en | 18 | 0.27 | 0.44 | 0.33 |  |
| ubicado_en | 8 | insuficiente | insuficiente | insuficiente |  |
| vinculo_sin_tipo | 19 | 0.23 | 0.37 | 0.29 |  |
| micro | 523 | 0.54 | 0.50 | 0.52 | [0.46, 0.56] |
| micro sin reserva | 504 | 0.56 | 0.50 | 0.53 |  |
| macro |  |  |  | 0.45 |  |
| direccion (tasa = R) | 250 |  | 0.98 |  |  |
| vigencia (tasa = R) | 260 |  | 0.93 |  |  |

### Relaciones gruesas, RE+

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| apoya_a | 39 | 0.65 | 0.33 | 0.44 |  |
| contrato_a | 3 | insuficiente | insuficiente | insuficiente |  |
| dirige | 40 | 0.47 | 0.17 | 0.25 |  |
| familiar_de | 19 | 0.73 | 0.84 | 0.78 |  |
| financia_a | 1 | insuficiente | insuficiente | insuficiente |  |
| fundo | 2 | insuficiente | insuficiente | insuficiente |  |
| investigado_por | 18 | 0.50 | 0.11 | 0.18 |  |
| miembro_de | 56 | 0.48 | 0.50 | 0.49 |  |
| nombro_a | 7 | insuficiente | insuficiente | insuficiente |  |
| ocupa_cargo | 245 | 0.75 | 0.60 | 0.67 |  |
| parte_de | 11 | 0.13 | 0.36 | 0.19 |  |
| propietario_de | 12 | 1.00 | 1.00 | 1.00 |  |
| se_opone_a | 17 | 0.50 | 0.35 | 0.41 |  |
| socio_de | 2 | insuficiente | insuficiente | insuficiente |  |
| sucedio_a | 6 | insuficiente | insuficiente | insuficiente |  |
| trabaja_en | 18 | 0.27 | 0.44 | 0.33 |  |
| ubicado_en | 8 | insuficiente | insuficiente | insuficiente |  |
| vinculo_sin_tipo | 19 | 0.23 | 0.37 | 0.29 |  |
| micro | 523 | 0.54 | 0.50 | 0.51 | [0.46, 0.56] |
| micro sin reserva | 504 | 0.56 | 0.50 | 0.53 |  |
| macro |  |  |  | 0.45 |  |
| direccion (tasa = R) | 249 |  | 0.98 |  |  |
| vigencia (tasa = R) | 259 |  | 0.93 |  |  |

### Relaciones finas, RE+

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| apoya_a | 39 | 0.65 | 0.33 | 0.44 |  |
| contrato_a | 3 | insuficiente | insuficiente | insuficiente |  |
| dirige | 40 | 0.47 | 0.17 | 0.25 |  |
| familiar_de:conyuge | 1 | insuficiente | insuficiente | insuficiente |  |
| familiar_de:hermano | 6 | insuficiente | insuficiente | insuficiente |  |
| familiar_de:hijo_de | 8 | insuficiente | insuficiente | insuficiente |  |
| familiar_de:otro | 4 | insuficiente | insuficiente | insuficiente |  |
| financia_a | 1 | insuficiente | insuficiente | insuficiente |  |
| fundo | 2 | insuficiente | insuficiente | insuficiente |  |
| investigado_por:condenado | 0 | insuficiente | insuficiente | insuficiente |  |
| investigado_por:investigado | 18 | 1.00 | 0.11 | 0.20 |  |
| miembro_de | 56 | 0.48 | 0.50 | 0.49 |  |
| nombro_a | 7 | insuficiente | insuficiente | insuficiente |  |
| ocupa_cargo:aspirante | 11 | 0.50 | 0.64 | 0.56 |  |
| ocupa_cargo:titular | 234 | 0.77 | 0.60 | 0.67 |  |
| parte_de | 11 | 0.13 | 0.36 | 0.19 |  |
| propietario_de | 12 | 1.00 | 1.00 | 1.00 |  |
| se_opone_a | 17 | 0.50 | 0.35 | 0.41 |  |
| socio_de | 2 | insuficiente | insuficiente | insuficiente |  |
| sucedio_a | 6 | insuficiente | insuficiente | insuficiente |  |
| trabaja_en | 18 | 0.27 | 0.44 | 0.33 |  |
| ubicado_en | 8 | insuficiente | insuficiente | insuficiente |  |
| vinculo_sin_tipo | 19 | 0.23 | 0.37 | 0.29 |  |
| micro | 523 | 0.54 | 0.50 | 0.51 |  |
| micro sin reserva | 504 | 0.56 | 0.50 | 0.53 |  |
| macro |  |  |  | 0.47 |  |
| direccion (tasa = R) | 249 |  | 0.98 |  |  |
| vigencia (tasa = R) | 259 |  | 0.93 |  |  |
