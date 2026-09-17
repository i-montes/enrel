# Etapa 0 — Congelado del corpus

**Fecha:** 2026-09-17

**Comando:**

```bash
uv run enrel congelar
```

(parámetros por defecto: `--salida datos/corpus/articulos.jsonl --min 150 --max 2000`, base de legajo en
`~/.local/share/com.legajo.app/legajo.sqlite`)

## Resumen

- **total:** 63991 artículos escritos en `datos/corpus/articulos.jsonl`
- **excluidos:**
  - `pocas_palabras`: 14843
  - `muchas_palabras`: 4653
  - `transcripcion`: 218
  - `sin_texto`: 386
- **hash:** `c0d277fbe9f61a06d21e87b41792951fed9321fc918e8269c1f9088c2bd0dafd`

La base tiene 84.091 artículos con `text_plain` no nulo (63991 + 14843 + 4653 + 218 + 386 = 84091, cifra que
coincide exactamente con la consulta directa a la base; la cifra de 81.103 mencionada como referencia previa
resultó algo por debajo del conteo real). Los 386 `sin_texto` corresponden a `text_plain` vacío o solo espacios.
El total congelado (63991) queda dentro del rango esperado (55.000–70.000).

## Por sección (29 secciones)

| sección | artículos |
|---|---|
| en-vivo | 25363 |
| silla-nacional | 14289 |
| red-de-expertos | 11078 |
| detector-de-mentiras | 5902 |
| opinion | 3258 |
| silla-amazonia | 1353 |
| quien-es-quien | 1344 |
| podcasts | 1236 |
| silla-academica | 79 |
| silla-datos | 48 |
| (18 secciones adicionales con 1 artículo cada una, en su mayoría slugs sueltos sin sección real) | 18 |

## Por tramo

| tramo | artículos |
|---|---|
| 2009-2015 | 8201 |
| 2016-2021 | 20395 |
| 2022-2026 | 35394 |
| sin-fecha | 1 |
