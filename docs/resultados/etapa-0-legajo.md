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

# Evaluación de MiniMax v5 sin pistas (techo del maestro de legajo), esquema con vigencia

Fecha: 2026-09-17 · documentos: 50

- `oro`: `73c6efeacbd2d1446413d53ef02e20d28aad94e85e97462e1fdc1bff50fca147`
- `pred`: `2c39e8f6294c7793a5394da051ee406d8ac0506ecccec2d0003186f0cf5a02f8`

### Entidades, estricto

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| cargo | 376 | 0.73 | 0.59 | 0.65 |  |
| lugar | 252 | 0.73 | 0.73 | 0.73 |  |
| monto | 78 | 0.66 | 0.53 | 0.59 |  |
| norma | 66 | 0.64 | 0.35 | 0.45 |  |
| obra | 29 | 0.29 | 0.62 | 0.39 |  |
| organizacion | 746 | 0.78 | 0.75 | 0.76 |  |
| persona | 743 | 0.87 | 0.81 | 0.84 |  |
| global | 2290 | 0.78 | 0.72 | 0.75 | [0.71, 0.78] |

### Entidades, parcial

| | n | P | R | F1 | IC 95 % |
|---|---:|---:|---:|---:|---|
| cargo | 376 | 0.82 | 0.67 | 0.74 |  |
| lugar | 252 | 0.75 | 0.75 | 0.75 |  |
| monto | 78 | 0.77 | 0.62 | 0.69 |  |
| norma | 66 | 0.72 | 0.39 | 0.51 |  |
| obra | 29 | 0.33 | 0.72 | 0.46 |  |
| organizacion | 746 | 0.81 | 0.79 | 0.80 |  |
| persona | 743 | 0.88 | 0.82 | 0.85 |  |
| global | 2290 | 0.81 | 0.76 | 0.78 | [0.75, 0.82] |

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
| miembro_de | 56 | 0.47 | 0.48 | 0.47 |  |
| nombro_a | 7 | insuficiente | insuficiente | insuficiente |  |
| ocupa_cargo | 245 | 0.75 | 0.60 | 0.67 |  |
| parte_de | 11 | 0.13 | 0.36 | 0.19 |  |
| propietario_de | 12 | 1.00 | 1.00 | 1.00 |  |
| se_opone_a | 17 | 0.50 | 0.35 | 0.41 |  |
| socio_de | 2 | insuficiente | insuficiente | insuficiente |  |
| sucedio_a | 6 | insuficiente | insuficiente | insuficiente |  |
| trabaja_en | 18 | 0.27 | 0.44 | 0.33 |  |
| ubicado_en | 8 | insuficiente | insuficiente | insuficiente |  |
| vinculo_sin_tipo | 26 | 0.20 | 0.38 | 0.27 |  |
| micro | 530 | 0.52 | 0.49 | 0.51 | [0.45, 0.55] |
| micro sin reserva | 504 | 0.56 | 0.50 | 0.53 |  |
| macro |  |  |  | 0.45 |  |
| direccion (tasa = R) | 249 |  | 0.98 |  |  |
| vigencia (tasa = R) | 262 |  | 0.93 |  |  |

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
| miembro_de | 56 | 0.47 | 0.48 | 0.47 |  |
| nombro_a | 7 | insuficiente | insuficiente | insuficiente |  |
| ocupa_cargo | 245 | 0.75 | 0.60 | 0.67 |  |
| parte_de | 11 | 0.13 | 0.36 | 0.19 |  |
| propietario_de | 12 | 1.00 | 1.00 | 1.00 |  |
| se_opone_a | 17 | 0.50 | 0.35 | 0.41 |  |
| socio_de | 2 | insuficiente | insuficiente | insuficiente |  |
| sucedio_a | 6 | insuficiente | insuficiente | insuficiente |  |
| trabaja_en | 18 | 0.27 | 0.44 | 0.33 |  |
| ubicado_en | 8 | insuficiente | insuficiente | insuficiente |  |
| vinculo_sin_tipo | 26 | 0.16 | 0.31 | 0.21 |  |
| micro | 530 | 0.51 | 0.49 | 0.50 | [0.45, 0.55] |
| micro sin reserva | 504 | 0.55 | 0.50 | 0.52 |  |
| macro |  |  |  | 0.45 |  |
| direccion (tasa = R) | 248 |  | 0.98 |  |  |
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
| miembro_de | 56 | 0.47 | 0.48 | 0.47 |  |
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
| vinculo_sin_tipo | 26 | 0.16 | 0.31 | 0.21 |  |
| micro | 530 | 0.51 | 0.49 | 0.50 |  |
| micro sin reserva | 504 | 0.55 | 0.50 | 0.52 |  |
| macro |  |  |  | 0.46 |  |
| direccion (tasa = R) | 248 |  | 0.98 |  |  |
| vigencia (tasa = R) | 259 |  | 0.93 |  |  |
