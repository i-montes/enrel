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

<!--
Tabla generada desde datos/corpus/articulos.resumen.json (secciones con >= 5 artículos en filas propias,
el resto agrupado en "otras N secciones") con este script de una sola vez:

  python3 -c "
  import json
  r = json.load(open('datos/corpus/articulos.resumen.json', encoding='utf-8'))
  secciones = r['por_seccion']
  principales = [(s, n) for s, n in secciones.items() if n >= 5]
  resto = [(s, n) for s, n in secciones.items() if n < 5]
  for s, n in principales:
      print(f'| {s} | {n} |')
  print(f'| otras {len(resto)} secciones | {sum(n for _, n in resto)} |')
  suma = sum(n for _, n in principales) + sum(n for _, n in resto)
  print('comprobación:', suma, '==', r['total'], suma == r['total'])
  "

Comprobación de esa corrida: suma de la tabla = 63991; total del resumen = 63991; OK.
-->

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
| especiales | 15 |
| sobre-nosotros | 9 |
| otras 17 secciones (con 1 artículo cada una, en su mayoría slugs sueltos sin sección real) | 17 |
| **total** | **63991** |

Suma de la tabla: 25363+14289+11078+5902+3258+1353+1344+1236+79+48+15+9+17 = 63991, igual al `total` del resumen.

## Por tramo

| tramo | artículos |
|---|---|
| 2009-2015 | 8201 |
| 2016-2021 | 20395 |
| 2022-2026 | 35394 |
| sin-fecha | 1 |
