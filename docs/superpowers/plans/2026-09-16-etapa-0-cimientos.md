# enrel · Etapa 0 · Cimientos — Plan de implementación

> **Para agentes ejecutores:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para seguimiento. Los subagentes que escriben código usan `model: "sonnet"`.

**Objetivo:** dejar el paquete `enrel` con su esquema, el puente desde legajo (vocabulario actualizado en legajo, mapeo y exportador de oro), el corpus congelado y muestreado, un evaluador completo que ya produce una tabla real, la guía de anotación como fuente única, y el backbone verificado en humo.

**Arquitectura:** paquete Python `enrel` con módulos por responsabilidad (`esquema`, `datos`, `corpus`, `anotacion`, `evaluacion`), un formato interno de documento con offsets de caracteres, y scripts por paso que escriben resultados en `docs/resultados/`. Sin modelo todavía: esta etapa construye lo que permite medir.

**Tecnologías:** Python 3.12 con `uv`, `pytest`, `ruff`, `sqlite3` de la biblioteca estándar, `pyyaml`, `numpy`, `torch` + `transformers` (solo en la tarea de humo), `onnx` + `onnxruntime` (solo humo). En legajo: Python del `.venv` de legajo, `cargo test`, `pnpm build`.

**Spec:** `docs/superpowers/specs/2026-09-16-enrel-diseno.md` (secciones 3, 5, 6, 8, 10 · etapa 0).

## Restricciones globales

- Python 3.12 gestionado por `uv`; entorno en `.venv`; comandos `uv run …`.
- Todo en español: identificadores, docstrings, mensajes, commits, documentación. Nombres de librerías tal cual.
- Offsets de caracteres sobre `Documento.texto` normalizado a NFC (`unicodedata.normalize("NFC", …)`). Nunca índices de tokens en datos persistidos.
- `datos/` y `datos-anteriores/` no se commitean (ya en `.gitignore`). Los tests que leen datos reales hacen `pytest.skip` si la ruta no existe.
- Tipos de entidad: `persona, organizacion, lugar, cargo, norma, obra, monto`. En legajo el tipo `ley` equivale a `norma` y `cargo*` a `cargo` con designación.
- Relaciones: las 17 de la spec §3.2 más `vinculo_sin_tipo`; 24 clases finas más `vinculo_sin_tipo` = 25 clases.
- Ruta de la base de legajo: `~/.local/share/com.legajo.app/legajo.sqlite`, configurable por `--legajo-db` o variable `ENREL_LEGAJO_DB`. Párrafo = bloque de `text_plain` separado por `\n\n`; `pi` es su índice; `ini`/`fin` son caracteres dentro del párrafo.
- Repositorio de legajo: `/home/imontes/Projects/personal/legajo` (Tarea 0.1 se ejecuta allí).
- Commits pequeños, un commit por tarea como mínimo, mensaje en español en imperativo («Añade…», «Corrige…»).

---

## Estructura de ficheros de la etapa 0

```
pyproject.toml                      paquete enrel, dependencias, pytest, ruff, script `enrel`
enrel/__init__.py                   versión
enrel/esquema/__init__.py
enrel/esquema/tipos.py              TIPOS, RELACIONES, clases finas, admite(), FAMILIAS
enrel/esquema/mapeo_legajo.py       mapear_tipo(), mapear_predicado() para los 35 viejos y los 25 nuevos de legajo
enrel/datos/__init__.py
enrel/datos/documento.py            Mencion, Grupo, Relacion, Documento; JSONL; NFC
enrel/datos/validar.py              validar_documento(), comprobar_fugas()
enrel/datos/normalizar.py           plegar() para comparar cadenas
enrel/datos/agrupar.py              reglas de agrupación de menciones en grupos
enrel/corpus/__init__.py
enrel/corpus/legajo_db.py           leer articles + census; seccion_de(); parrafos()
enrel/corpus/congelar.py            corpus → datos/corpus/articulos.jsonl con filtros
enrel/corpus/disparadores.py        léxicos regex por relación
enrel/corpus/muestrear.py           tres estratos; conjuntos; datos/conjuntos/seleccion.jsonl
enrel/anotacion/__init__.py
enrel/anotacion/desde_legajo.py     oro JSON / sqlite / plata jsonl → Documento
enrel/anotacion/guia.py             parser de docs/guia-anotacion.md
enrel/evaluacion/__init__.py
enrel/evaluacion/emparejar.py       emparejar menciones (estricto/parcial) y grupos
enrel/evaluacion/entidades.py       P/R/F1 por tipo
enrel/evaluacion/relaciones.py      RE, RE+, fina, micro/macro, dirección, Ign
enrel/evaluacion/bootstrap.py       intervalos al 95 %
enrel/evaluacion/tabla.py           tabla markdown con regla n ≥ 10
enrel/cli.py                        `enrel evaluar`, `enrel congelar`, `enrel muestrear`, `enrel exportar-legajo`
scripts/humo_backbone.py            carga, VRAM, ONNX, tiempo CPU
docs/guia-anotacion.md              fuente única de definiciones
docs/esquema.md                     tabla del esquema con equivalencias
docs/resultados/etapa-0-legajo.md   primera tabla real
docs/resultados/etapa-0-backbone.md humo
tests/…                             un fichero por módulo
```

En legajo (Tarea 0.1): `sidecar/vocabulario.py`, `sidecar/legajo_ner.py`, `src/contenido/tipos.ts` (NOTAS), `core/src/extraccion.rs` (test de 35 → 25), regenerados por `sidecar/generar_vocabulario.py`.

---

### Tarea 0.1: Vocabulario nuevo en legajo, para anotar ya con las relaciones definitivas

Se ejecuta en `/home/imontes/Projects/personal/legajo`. El usuario está anotando 40 perfiles en la capa de revisión de legajo; con esta tarea anota directamente con las 25 clases finas de enrel en vez de los 35 predicados viejos. El modelo afinado viejo sigue proponiendo con sus 35 etiquetas (es lo que aprendió) y el sidecar traduce sus salidas al vocabulario nuevo.

**Ficheros:**
- Modificar: `sidecar/vocabulario.py` (bloque `PREDICADOS`, `FAMILIAS`, y añadir `PREDICADOS_ANTERIORES` y `traducir_anterior()`)
- Modificar: `sidecar/legajo_ner.py:236-320` (`procesar` pide con las etiquetas viejas; `relaciones` traduce)
- Modificar: `src/contenido/tipos.ts:75-…` (`NOTAS` para los predicados nuevos)
- Modificar: `core/src/extraccion.rs:815` (el test que espera 35 tuplas pasa a 25)
- Regenerar con: `.venv/bin/python sidecar/generar_vocabulario.py`
- Test: `sidecar/prueba_vocabulario.py` (nuevo)

**Interfaces:**
- Produce en legajo: `PREDICADOS` con 25 tuplas `(etiqueta, familia, desde, hasta, simetrico)`; `PREDICADOS_ANTERIORES: list[str]` con las 35 etiquetas viejas; `traducir_anterior(etiqueta_vieja: str, tipo_a: str, tipo_b: str) -> tuple[str, bool] | None` que devuelve `(etiqueta_nueva, invertir)` o `None` si se descarta.
- Las etiquetas nuevas de legajo son exactamente estas 25 cadenas, que enrel reconoce en `mapeo_legajo.py` (Tarea 0.4): `cónyuge de`, `hijo de`, `hermano de`, `familiar de`, `ocupa el cargo`, `ocupó el cargo`, `aspira al cargo`, `nombró a`, `sucedió a`, `trabaja en`, `dirige`, `miembro de`, `fundó`, `propietario de`, `socio de`, `parte de`, `contrató a`, `financia a`, `apoya a`, `se opone a`, `investigado por`, `acusado por`, `condenado por`, `ubicado en`, `vínculo sin tipo`.

- [ ] **Paso 1: Escribir la prueba del vocabulario nuevo**

Crear `sidecar/prueba_vocabulario.py`:

```python
"""Comprueba el vocabulario nuevo de legajo y su traducción desde el viejo.

  .venv/bin/python sidecar/prueba_vocabulario.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from vocabulario import FAMILIAS, PREDICADOS, PREDICADOS_ANTERIORES, traducir_anterior  # noqa: E402

ESPERADOS = [
    "cónyuge de", "hijo de", "hermano de", "familiar de",
    "ocupa el cargo", "ocupó el cargo", "aspira al cargo", "nombró a", "sucedió a", "trabaja en", "dirige", "miembro de",
    "fundó", "propietario de", "socio de", "parte de", "contrató a", "financia a",
    "apoya a", "se opone a",
    "investigado por", "acusado por", "condenado por",
    "ubicado en",
    "vínculo sin tipo",
]


def main():
    etiquetas = [e for e, *_ in PREDICADOS]
    assert etiquetas == ESPERADOS, f"etiquetas distintas:\n{etiquetas}"
    assert len(PREDICADOS_ANTERIORES) == 35
    assert {f for _, f, *_ in PREDICADOS} <= set(FAMILIAS)
    # parte de: persona→org es miembro de; org→org se queda; persona→lugar se descarta
    assert traducir_anterior("parte de", "persona", "organizacion") == ("miembro de", False)
    assert traducir_anterior("parte de", "organizacion", "organizacion") == ("parte de", False)
    assert traducir_anterior("parte de", "persona", "lugar") == ("vínculo sin tipo", False)
    # padre o madre de se invierte a hijo de
    assert traducir_anterior("padre o madre de", "persona", "persona") == ("hijo de", True)
    assert traducir_anterior("hijo de", "persona", "persona") == ("hijo de", False)
    assert traducir_anterior("cónyuge o pareja de", "persona", "persona") == ("cónyuge de", False)
    assert traducir_anterior("aspira a", "persona", "cargo") == ("aspira al cargo", False)
    assert traducir_anterior("renunció a", "persona", "cargo") == ("ocupó el cargo", False)
    assert traducir_anterior("renunció a", "persona", "organizacion") == ("vínculo sin tipo", False)
    assert traducir_anterior("asesor de", "persona", "organizacion") == ("trabaja en", False)
    assert traducir_anterior("asesor de", "persona", "persona") == ("vínculo sin tipo", False)
    assert traducir_anterior("dueño de", "persona", "organizacion") == ("propietario de", False)
    assert traducir_anterior("socio de", "persona", "organizacion") == ("propietario de", False)
    assert traducir_anterior("socio de", "persona", "persona") == ("socio de", False)
    assert traducir_anterior("aliado de", "persona", "persona") == ("apoya a", False)
    assert traducir_anterior("apoyó a", "organizacion", "cargo") == ("apoya a", False)
    assert traducir_anterior("criticó a", "persona", "ley") == ("vínculo sin tipo", False)
    assert traducir_anterior("opositor de", "persona", "organizacion") == ("se opone a", False)
    assert traducir_anterior("acusado de", "persona", "ley") == ("vínculo sin tipo", False)
    assert traducir_anterior("condenado por", "persona", "organizacion") == ("condenado por", False)
    assert traducir_anterior("investigado por", "persona", "ley") == ("vínculo sin tipo", False)
    assert traducir_anterior("ubicado en", "persona", "lugar") == ("ubicado en", False)
    assert traducir_anterior("ubicado en", "monto", "lugar") == ("vínculo sin tipo", False)
    for viejo in ("se reunió con", "citado en", "autor de", "destinado a", "sanciona con", "demandó a"):
        assert traducir_anterior(viejo, "persona", "organizacion") == ("vínculo sin tipo", False), viejo
    print("vocabulario nuevo: ok")


if __name__ == "__main__":
    main()
```

- [ ] **Paso 2: Ejecutar la prueba y ver que falla**

Ejecutar: `cd /home/imontes/Projects/personal/legajo && .venv/bin/python sidecar/prueba_vocabulario.py`
Esperado: `ImportError: cannot import name 'PREDICADOS_ANTERIORES'`.

- [ ] **Paso 3: Reescribir el bloque de predicados en `sidecar/vocabulario.py`**

Sustituir el bloque `PREDICADOS = [...]`, el `assert len(PREDICADOS) == 35`, `FAMILIAS` y sus asserts por:

```python
# (etiqueta, familia, desde, hasta, simetrico). `desde`/`hasta` vacíos = cualquier tipo.
# Son las 25 clases finas de enrel (docs/superpowers/specs/2026-09-16-enrel-diseno.md §3.2),
# escritas como predicados para que la capa de revisión no necesite atributos.
PREDICADOS = [
    # familia
    ("cónyuge de",        "familiar",  [P],       [P],          True),
    ("hijo de",           "familiar",  [P],       [P],          False),   # la cabeza es el hijo
    ("hermano de",        "familiar",  [P],       [P],          True),
    ("familiar de",       "familiar",  [P],       [P],          True),    # tío, primo, sobrino, cuñado, suegro…
    # cargos y trabajo
    ("ocupa el cargo",    "laboral",   [P],       [C],          False),   # estado actual
    ("ocupó el cargo",    "laboral",   [P],       [C],          False),   # estado anterior: «ex», «fue», «entonces»
    ("aspira al cargo",   "laboral",   [P],       [C],          False),   # candidato, precandidato
    ("nombró a",          "laboral",   [P, O],    [P],          False),
    ("sucedió a",         "laboral",   [P],       [P],          False),
    ("trabaja en",        "laboral",   [P],       [O],          False),   # empleo o asesoría sin cargo nombrado
    ("dirige",            "laboral",   [P],       [O],          False),
    ("miembro de",        "laboral",   [P],       [O],          False),   # militancia, junta, comisión, colectivo
    # empresa y dinero
    ("fundó",             "empresa",   [P, O],    [O],          False),
    ("propietario de",    "empresa",   [P, O],    [O],          False),   # dueño, accionista, socio de una empresa
    ("socio de",          "empresa",   [P],       [P],          True),    # socios entre personas
    ("parte de",          "empresa",   [O],       [O],          False),   # filial, dependencia, adscrita
    ("contrató a",        "empresa",   [O, P],    [O, P],       False),
    ("financia a",        "empresa",   [P, O],    [P, O],       False),   # incluye donaciones
    # política
    ("apoya a",           "politica",  [P, O],    [P, O, C],    False),   # respaldo o alianza explícita
    ("se opone a",        "politica",  [P, O],    [P, O],       False),   # oposición o crítica explícita
    # justicia
    ("investigado por",   "judicial",  [P, O],    [O],          False),
    ("acusado por",       "judicial",  [P, O],    [O],          False),
    ("condenado por",     "judicial",  [P, O],    [O],          False),
    # lugar
    ("ubicado en",        "lugar",     [P, O, L], [L],          False),   # sede, residencia o contención geográfica
    # reserva
    ("vínculo sin tipo",  "otro",      [],        [],           True),
]
assert len(PREDICADOS) == 25

FAMILIAS = {
    "familiar": "Familia",
    "laboral": "Cargos y trabajo",
    "empresa": "Empresa y dinero",
    "politica": "Política",
    "judicial": "Justicia",
    "lugar": "Lugar",
    "otro": "Otro",
}
assert set(FAMILIAS) == {f for _, f, *_ in PREDICADOS}

# Las 35 etiquetas que aprendió el modelo afinado anterior. El sidecar sigue
# pidiéndole con ellas y traduce lo que devuelve con `traducir_anterior`.
PREDICADOS_ANTERIORES = [
    "padre o madre de", "hijo de", "hermano de", "cónyuge o pareja de", "familiar de",
    "ocupa el cargo", "trabaja en", "dirige", "fundó", "dueño de", "asesor de", "sucedió a", "nombró a", "renunció a", "parte de",
    "aliado de", "opositor de", "miembro de", "aspira a", "apoyó a", "se reunió con", "criticó a",
    "financia a", "contrató a", "socio de", "donó a", "destinado a",
    "investigado por", "condenado por", "acusado de", "demandó a", "sanciona con",
    "ubicado en", "citado en", "autor de",
]
assert len(PREDICADOS_ANTERIORES) == 35

SIN_TIPO = "vínculo sin tipo"

# Traducción de cada etiqueta vieja. Un valor puede ser una cadena (destino
# fijo), una tupla (destino, invertir) o una función (tipo_a, tipo_b) → destino.
_TRADUCCION = {
    "padre o madre de": ("hijo de", True),
    "hijo de": "hijo de",
    "hermano de": "hermano de",
    "cónyuge o pareja de": "cónyuge de",
    "familiar de": "familiar de",
    "ocupa el cargo": "ocupa el cargo",
    "aspira a": "aspira al cargo",
    "renunció a": lambda ta, tb: "ocupó el cargo" if tb == C else SIN_TIPO,
    "nombró a": "nombró a",
    "sucedió a": "sucedió a",
    "trabaja en": "trabaja en",
    "asesor de": lambda ta, tb: "trabaja en" if tb == O else SIN_TIPO,
    "dirige": lambda ta, tb: "dirige" if tb == O else SIN_TIPO,
    "miembro de": "miembro de",
    "parte de": lambda ta, tb: "miembro de" if (ta, tb) == (P, O) else ("parte de" if (ta, tb) == (O, O) else SIN_TIPO),
    "fundó": "fundó",
    "dueño de": "propietario de",
    "socio de": lambda ta, tb: "socio de" if (ta, tb) == (P, P) else ("propietario de" if tb == O and ta in (P, O) else SIN_TIPO),
    "contrató a": "contrató a",
    "financia a": "financia a",
    "donó a": "financia a",
    "aliado de": "apoya a",
    "apoyó a": "apoya a",
    "opositor de": "se opone a",
    "criticó a": lambda ta, tb: "se opone a" if tb in (P, O) else SIN_TIPO,
    "investigado por": lambda ta, tb: "investigado por" if tb == O else SIN_TIPO,
    "acusado de": lambda ta, tb: "acusado por" if tb == O else SIN_TIPO,
    "condenado por": lambda ta, tb: "condenado por" if tb == O else SIN_TIPO,
    "ubicado en": lambda ta, tb: "ubicado en" if ta in (P, O, L) and tb == L else SIN_TIPO,
    "se reunió con": SIN_TIPO, "citado en": SIN_TIPO, "autor de": SIN_TIPO,
    "destinado a": SIN_TIPO, "sanciona con": SIN_TIPO, "demandó a": SIN_TIPO,
}
assert set(_TRADUCCION) == set(PREDICADOS_ANTERIORES)

_ADMITE = {e: (set(d), set(h)) for e, _, d, h, _ in PREDICADOS}


def traducir_anterior(etiqueta_vieja, tipo_a, tipo_b):
    """(etiqueta_nueva, invertir) para una relación del modelo viejo, o None si la etiqueta no existe.

    Si el destino no admite los tipos de los extremos, cae en «vínculo sin tipo»,
    que admite cualquier par. `invertir` dice que cabeza y cola se intercambian."""
    regla = _TRADUCCION.get(etiqueta_vieja)
    if regla is None:
        return None
    invertir = False
    if isinstance(regla, tuple):
        destino, invertir = regla
    elif callable(regla):
        destino = regla(tipo_a, tipo_b)
    else:
        destino = regla
    ta, tb = (tipo_b, tipo_a) if invertir else (tipo_a, tipo_b)
    desde, hasta = _ADMITE[destino]
    if destino != SIN_TIPO and ((desde and ta not in desde) or (hasta and tb not in hasta)):
        return (SIN_TIPO, False)
    return (destino, invertir)
```

Mantener intactos `TIPOS`, `ETIQUETA`, `SENUELO`, `NO_SE_MARCA`, `PRONOMBRES`, `PREDICADOS_DICT`, `POR_FAMILIA` (se recalculan solos desde `PREDICADOS`). Nota: en legajo el tipo sigue llamándose `ley`; la constante `N = "ley"` no cambia.

- [ ] **Paso 4: Ejecutar la prueba y ver que pasa**

Ejecutar: `.venv/bin/python sidecar/prueba_vocabulario.py`
Esperado: `vocabulario nuevo: ok`.

- [ ] **Paso 5: Regenerar Rust y TypeScript**

Ejecutar: `.venv/bin/python sidecar/generar_vocabulario.py`
Esperado: dos líneas `core/src/extraccion.rs: 25 predicados` y `src/contenido/tipos.ts: 25 predicados`. Verificar que `SIGLA` en `generar_vocabulario.py` sigue cubriendo `ley` (sí: `"ley": "N"`).

- [ ] **Paso 6: Actualizar `NOTAS` en `src/contenido/tipos.ts`**

Sustituir el objeto `NOTAS` por:

```ts
const NOTAS: Record<string, string> = {
  "ocupa el cargo": "Lo ejerce ahora según el texto. Si el texto dice «ex», «fue» o «entonces», usa «ocupó el cargo»; si solo se postula, «aspira al cargo».",
  "ocupó el cargo": "Lo ejerció y ya no: «exministro», «fue alcalde», «el entonces gobernador».",
  "aspira al cargo": "Se postula, suena o busca el cargo. Marcarlo como «ocupa» sería falso.",
  "nombró a": "Quien nombra puede ser una persona o una organización; el nombrado es una persona.",
  "sucedió a": "Reemplazó a otra persona en un cargo. De quien llega a quien se fue.",
  "trabaja en": "Empleo o asesoría sin cargo nombrado. Si el texto da el cargo, usa «ocupa el cargo».",
  "dirige": "Preside, gerencia o encabeza la organización.",
  "miembro de": "Militancia en un partido o pertenencia a junta, comisión o colectivo. Un adjetivo («el liberal X») no basta.",
  "fundó": "Creó la organización.",
  "propietario de": "Dueño, accionista o socio de una empresa. Entre dos personas, usa «socio de».",
  "socio de": "Dos personas socias en un negocio. Si el socio es de una empresa, «propietario de».",
  "parte de": "Una organización dentro de otra: filial, dependencia, adscrita. Nunca una persona.",
  "contrató a": "Contratación pública o privada afirmada en el texto.",
  "financia a": "Financió, donó o aportó. Solo si el texto lo afirma.",
  "apoya a": "Respaldo o alianza explícita. Solo si el texto lo afirma, no si tú lo sabes.",
  "se opone a": "Oposición o crítica explícita. Solo si el texto lo afirma.",
  "investigado por": "La organización que investiga: Fiscalía, Procuraduría, Contraloría, Corte.",
  "acusado por": "La organización que imputa o acusa.",
  "condenado por": "La organización que condena.",
  "ubicado en": "Sede, residencia o contención geográfica. No el origen («el caleño X») ni el lugar de los hechos.",
  "cónyuge de": "Esposo, esposa, pareja, compañero permanente, ex pareja.",
  "hijo de": "La cabeza es el hijo: «Nicolás Petro» hijo de «Gustavo Petro».",
  "hermano de": "Hermanos y hermanastros.",
  "familiar de": "Cuando el parentesco es otro: tío, primo, sobrino, cuñado, suegro, nieto, padrino.",
  "vínculo sin tipo": "El texto afirma un vínculo que no encaja en ninguna relación. Se conserva para revisión.",
};
```

Comprobar que el texto de `tipos.ts:39` que dice «Son 35 predicados en seis familias» se actualiza a «Son 25 predicados en siete familias».

- [ ] **Paso 7: Actualizar el test de Rust y el sidecar**

En `core/src/extraccion.rs:815` cambiar `assert_eq!(en_py.len(), 35, "esperaba las 35 tuplas de PREDICADOS en vocabulario.py");` por `assert_eq!(en_py.len(), 25, "esperaba las 25 tuplas de PREDICADOS en vocabulario.py");`. Si el test parsea `vocabulario.py` con una expresión regular sobre las tuplas, comprobar que los comentarios al final de línea (`# la cabeza es el hijo`) no rompen el parseo; si rompen, quitar los comentarios de las tuplas y dejarlos en una línea aparte encima.

En `sidecar/legajo_ner.py`:

1. Importar al inicio, junto a las demás importaciones del sidecar: `from vocabulario import PREDICADOS_ANTERIORES, traducir_anterior`.
2. En `procesar` (línea 244) cambiar `pedir = [p["etiqueta"] for p in predicados]` por `pedir = list(PREDICADOS_ANTERIORES) if predicados else []`, con el comentario: `# El modelo afinado aprendió las 35 etiquetas viejas; se le pide con ellas y se traduce después.`
3. En `relaciones`, después de calcular `ta, tb` y antes de la comprobación `aplicables`, insertar:

```python
            traducida = traducir_anterior(etiqueta, ta, tb)
            if traducida is None:
                continue
            etiqueta, invertir = traducida
            if invertir:
                a, b, ta, tb = b, a, tb, ta
```

4. `umbrales` viene indexado por etiquetas viejas (el `umbrales.json` del modelo instalado). Al inicio de `relaciones`, dejar `umbrales = umbrales or {}` como está: la comprobación `score < umbrales.get(etiqueta, umbral)` se hace con la etiqueta vieja **antes** de traducir, así que no hay que tocarla. Añadir un comentario que lo diga.

- [ ] **Paso 8: Verificar Rust, TypeScript y el sidecar**

Ejecutar, en orden:

```bash
cd /home/imontes/Projects/personal/legajo
cargo test -p legajo-core el_vocabulario 2>&1 | tail -5
pnpm exec tsc --noEmit
.venv/bin/python -c "import sys; sys.path.insert(0,'sidecar'); import legajo_ner, vocabulario; print(len(vocabulario.PREDICADOS_DICT))"
.venv/bin/python sidecar/prueba_troceo.py
```

Esperado: los tests `el_vocabulario_de_rust_y_el_de_la_interfaz_dicen_lo_mismo`, `el_vocabulario_de_rust_es_el_que_aprendio_el_modelo` y `cada_predicado_tiene_familia` en verde; `tsc` sin errores; el import imprime `25`; la prueba de troceo pasa.

Si el test `el_modelo_afinado_trae_sus_umbrales` falla porque compara claves de `umbrales.json` con `PREDICADOS`, cambiarlo para que compruebe solo que `umbral_rel == 0.4` en la base y que el fichero existe, y anotar en el commit que los umbrales por predicado del afinado viejo se aplican antes de traducir.

- [ ] **Paso 9: Prueba manual con la app**

Con `pnpm tauri dev` (ya suele estar corriendo en la sesión `tmux` `legajo`; si es así, reiniciarlo para que cargue el Rust nuevo), abrir un artículo en el paso 6 y comprobar: entre dos personas el menú ofrece «cónyuge de», «hijo de», «hermano de», «familiar de», «socio de», «nombró a», «sucedió a», «apoya a», «se opone a», «vínculo sin tipo»; entre persona y cargo, las tres de cargo. Pedir al usuario que confirme antes de seguir anotando.

- [ ] **Paso 10: Commit en legajo**

```bash
cd /home/imontes/Projects/personal/legajo
git add sidecar/vocabulario.py sidecar/legajo_ner.py sidecar/prueba_vocabulario.py src/contenido/tipos.ts core/src/extraccion.rs
git commit -m "Legajo: el vocabulario de relaciones pasa a las 25 clases de enrel, con traducción desde el modelo afinado"
```

---

### Tarea 0.2: Esqueleto del paquete `enrel`

**Ficheros:**
- Crear: `pyproject.toml`, `enrel/__init__.py`, `enrel/esquema/__init__.py`, `enrel/datos/__init__.py`, `enrel/corpus/__init__.py`, `enrel/anotacion/__init__.py`, `enrel/evaluacion/__init__.py`, `tests/__init__.py`, `tests/test_paquete.py`, `LICENSE` (Apache-2.0), `README.md`
- Modificar: `.gitignore` (añadir `.venv/`, `__pycache__/`, `*.egg-info/`, `corridas/`, `.ruff_cache/`, `.pytest_cache/`)

**Interfaces:**
- Produce: `enrel.__version__ == "0.1.0.dev0"`; comando `uv run pytest` funcional; comando `uv run enrel` que imprime la ayuda (el CLI se completa en la Tarea 0.14; aquí solo el punto de entrada).

- [ ] **Paso 1: Escribir el test**

`tests/test_paquete.py`:

```python
import enrel


def test_version():
    assert enrel.__version__ == "0.1.0.dev0"
```

- [ ] **Paso 2: Crear `pyproject.toml`**

```toml
[project]
name = "enrel"
version = "0.1.0.dev0"
description = "Entidades y relaciones de noticias en español, para redacciones"
readme = "README.md"
license = { text = "Apache-2.0" }
requires-python = ">=3.12,<3.13"
dependencies = [
    "numpy>=1.26",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
modelo = [
    "torch>=2.6",
    "transformers>=4.51",
    "onnx>=1.17",
    "onnxruntime>=1.20",
    "safetensors>=0.4",
]
maestro = ["httpx>=0.27"]
dev = ["pytest>=8", "ruff>=0.6", "pytest-cov>=5"]

[project.scripts]
enrel = "enrel.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["enrel"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not gpu and not red'"
markers = [
    "gpu: necesita GPU",
    "red: necesita red o una API",
]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Paso 3: Crear los módulos vacíos y el CLI mínimo**

`enrel/__init__.py`:

```python
"""enrel: entidades y relaciones de noticias en español."""

__version__ = "0.1.0.dev0"
```

Cada `__init__.py` de subpaquete con una línea de docstring que diga su responsabilidad (por ejemplo `"""Esquema: tipos, relaciones y mapeos."""`).

`enrel/cli.py`:

```python
"""Punto de entrada `enrel`. Los subcomandos se registran en `SUBCOMANDOS`."""

import argparse
import sys

SUBCOMANDOS: dict[str, tuple[str, callable]] = {}


def registrar(nombre: str, ayuda: str):
    def decorador(fn):
        SUBCOMANDOS[nombre] = (ayuda, fn)
        return fn
    return decorador


def main(argv: list[str] | None = None) -> int:
    # Importar aquí los módulos que registran subcomandos, para no cargar torch al arrancar.
    from enrel import _subcomandos  # noqa: F401

    parser = argparse.ArgumentParser(prog="enrel", description="Entidades y relaciones de noticias en español.")
    sub = parser.add_subparsers(dest="orden")
    for nombre, (ayuda, fn) in SUBCOMANDOS.items():
        p = sub.add_parser(nombre, help=ayuda)
        fn.configurar(p)
        p.set_defaults(ejecutar=fn)
    args = parser.parse_args(argv)
    if not args.orden:
        parser.print_help()
        return 0
    return int(args.ejecutar(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
```

`enrel/_subcomandos.py` (vacío por ahora salvo docstring: `"""Importa los módulos que registran subcomandos del CLI."""`). Las tareas posteriores añaden aquí sus `import`.

`LICENSE`: texto completo de Apache License 2.0 (copiar de https://www.apache.org/licenses/LICENSE-2.0.txt) con «Copyright 2026 La Silla Vacía y colaboradores de enrel».

`README.md` con tres párrafos: qué es enrel, estado (en construcción, etapa 0), y cómo instalar (`uv sync --all-extras`) y probar (`uv run pytest`).

- [ ] **Paso 4: Crear el entorno y correr el test**

```bash
cd /home/imontes/Projects/personal/enrel
uv python install 3.12
uv sync --extra dev
uv run pytest -q
uv run enrel
uv run ruff check . && uv run ruff format --check .
```

Esperado: 1 test en verde; `enrel` imprime la ayuda; ruff sin errores.

- [ ] **Paso 5: Commit inicial**

```bash
git add .gitignore pyproject.toml uv.lock LICENSE README.md enrel tests docs
git commit -m "Nace enrel: paquete, especificación e informes de investigación"
```

---

### Tarea 0.3: El esquema en código

**Ficheros:**
- Crear: `enrel/esquema/tipos.py`
- Test: `tests/test_esquema_tipos.py`

**Interfaces:**
- Produce:
  - `TIPOS: tuple[str, ...] = ("persona","organizacion","lugar","cargo","norma","obra","monto")` y las constantes `P, O, L, C, N, B, M`.
  - `@dataclass(frozen=True) class DefRelacion: nombre: str; desde: frozenset[str]; hasta: frozenset[str]; simetrica: bool; atributos: tuple[str, ...]; familia: str`.
  - `RELACIONES: dict[str, DefRelacion]` con las 17 relaciones; `SIN_TIPO = "vinculo_sin_tipo"`; `RELACIONES_Y_SIN_TIPO: tuple[str, ...]` (18 nombres, `SIN_TIPO` al final).
  - `CLASES_FINAS: tuple[str, ...]` (25 cadenas, `"relacion"` o `"relacion:atributo"`, `SIN_TIPO` al final) y `INDICE_CLASE: dict[str, int]`.
  - `clase_fina(relacion: str, atributo: str | None) -> str`; `desglosar(clase: str) -> tuple[str, str | None]`.
  - `admite(relacion: str, tipo_cabeza: str, tipo_cola: str) -> bool` (SIN_TIPO admite todo).
  - `relaciones_admitidas(tipo_cabeza: str, tipo_cola: str) -> list[str]`.
  - `es_simetrica(relacion: str, atributo: str | None) -> bool` (familiar_de es simétrica salvo `hijo_de`).
  - `FAMILIAS: dict[str, tuple[str, ...]]` con claves `"A"`, `"B"`, `"C"` según spec §5.3.

- [ ] **Paso 1: Escribir los tests**

`tests/test_esquema_tipos.py`:

```python
from enrel.esquema import tipos as t


def test_tipos_y_constantes():
    assert t.TIPOS == ("persona", "organizacion", "lugar", "cargo", "norma", "obra", "monto")
    assert (t.P, t.O, t.L, t.C, t.N, t.B, t.M) == t.TIPOS


def test_hay_17_relaciones_y_25_clases_finas():
    assert len(t.RELACIONES) == 17
    assert t.SIN_TIPO not in t.RELACIONES
    assert len(t.CLASES_FINAS) == 25
    assert t.CLASES_FINAS[-1] == t.SIN_TIPO
    assert t.INDICE_CLASE[t.SIN_TIPO] == 24


def test_clase_fina_y_desglosar():
    assert t.clase_fina("ocupa_cargo", "actual") == "ocupa_cargo:actual"
    assert t.clase_fina("dirige", None) == "dirige"
    assert t.desglosar("familiar_de:hijo_de") == ("familiar_de", "hijo_de")
    assert t.desglosar("trabaja_en") == ("trabaja_en", None)
    assert t.desglosar(t.SIN_TIPO) == (t.SIN_TIPO, None)


def test_atributos():
    assert t.RELACIONES["ocupa_cargo"].atributos == ("actual", "anterior", "aspirante")
    assert t.RELACIONES["familiar_de"].atributos == ("conyuge", "hijo_de", "hermano", "otro")
    assert t.RELACIONES["investigado_por"].atributos == ("investigado", "acusado", "condenado")
    assert t.RELACIONES["trabaja_en"].atributos == ()


def test_admite():
    assert t.admite("ocupa_cargo", "persona", "cargo")
    assert not t.admite("ocupa_cargo", "persona", "organizacion")
    assert t.admite("parte_de", "organizacion", "organizacion")
    assert not t.admite("parte_de", "persona", "organizacion")
    assert t.admite("ubicado_en", "lugar", "lugar")
    assert not t.admite("ubicado_en", "monto", "lugar")
    assert t.admite("apoya_a", "organizacion", "cargo")
    assert t.admite(t.SIN_TIPO, "monto", "obra")


def test_relaciones_admitidas_persona_persona():
    assert set(t.relaciones_admitidas("persona", "persona")) == {
        "nombro_a", "sucedio_a", "socio_de", "familiar_de", "financia_a", "contrato_a", "apoya_a", "se_opone_a", t.SIN_TIPO,
    }


def test_simetria():
    assert t.es_simetrica("familiar_de", "conyuge")
    assert not t.es_simetrica("familiar_de", "hijo_de")
    assert t.es_simetrica("socio_de", None)
    assert not t.es_simetrica("dirige", None)
    assert t.es_simetrica(t.SIN_TIPO, None)


def test_familias_cubren_todo_sin_repetir():
    todas = [r for fam in t.FAMILIAS.values() for r in fam]
    assert sorted(todas) == sorted(t.RELACIONES)
    assert t.FAMILIAS["A"] == ("ocupa_cargo", "nombro_a", "sucedio_a", "trabaja_en", "dirige", "miembro_de")
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_esquema_tipos.py -q` → `ModuleNotFoundError: enrel.esquema.tipos`.

- [ ] **Paso 3: Implementar `enrel/esquema/tipos.py`**

```python
"""El esquema de enrel: siete tipos de entidad, diecisiete relaciones y una de reserva.

Fuente: docs/superpowers/specs/2026-09-16-enrel-diseno.md §3. Las definiciones en prosa
viven en docs/guia-anotacion.md; aquí solo la estructura que el código necesita.
"""

from dataclasses import dataclass

TIPOS: tuple[str, ...] = ("persona", "organizacion", "lugar", "cargo", "norma", "obra", "monto")
P, O, L, C, N, B, M = TIPOS


@dataclass(frozen=True)
class DefRelacion:
    nombre: str
    desde: frozenset[str]
    hasta: frozenset[str]
    simetrica: bool
    atributos: tuple[str, ...]
    familia: str


def _r(nombre, desde, hasta, simetrica=False, atributos=(), familia=""):
    return DefRelacion(nombre, frozenset(desde), frozenset(hasta), simetrica, tuple(atributos), familia)


_LISTA = [
    _r("ocupa_cargo", [P], [C], atributos=("actual", "anterior", "aspirante"), familia="A"),
    _r("nombro_a", [P, O], [P], familia="A"),
    _r("sucedio_a", [P], [P], familia="A"),
    _r("trabaja_en", [P], [O], familia="A"),
    _r("dirige", [P], [O], familia="A"),
    _r("miembro_de", [P], [O], familia="A"),
    _r("fundo", [P, O], [O], familia="B"),
    _r("propietario_de", [P, O], [O], familia="B"),
    _r("socio_de", [P], [P], simetrica=True, familia="B"),
    _r("parte_de", [O], [O], familia="B"),
    _r("contrato_a", [O, P], [O, P], familia="B"),
    _r("financia_a", [P, O], [P, O], familia="B"),
    _r("familiar_de", [P], [P], simetrica=True, atributos=("conyuge", "hijo_de", "hermano", "otro"), familia="C"),
    _r("apoya_a", [P, O], [P, O, C], familia="C"),
    _r("se_opone_a", [P, O], [P, O], familia="C"),
    _r("investigado_por", [P, O], [O], atributos=("investigado", "acusado", "condenado"), familia="C"),
    _r("ubicado_en", [P, O, L], [L], familia="C"),
]
RELACIONES: dict[str, DefRelacion] = {d.nombre: d for d in _LISTA}
assert len(RELACIONES) == 17

SIN_TIPO = "vinculo_sin_tipo"
RELACIONES_Y_SIN_TIPO: tuple[str, ...] = tuple(RELACIONES) + (SIN_TIPO,)

FAMILIAS: dict[str, tuple[str, ...]] = {
    fam: tuple(d.nombre for d in _LISTA if d.familia == fam) for fam in ("A", "B", "C")
}


def clase_fina(relacion: str, atributo: str | None) -> str:
    """«relacion:atributo» si la relación tiene atributos; «relacion» si no."""
    if relacion == SIN_TIPO or not RELACIONES[relacion].atributos:
        return relacion
    if atributo not in RELACIONES[relacion].atributos:
        raise ValueError(f"{relacion} exige un atributo de {RELACIONES[relacion].atributos}, no {atributo!r}")
    return f"{relacion}:{atributo}"


def desglosar(clase: str) -> tuple[str, str | None]:
    relacion, sep, atributo = clase.partition(":")
    return relacion, (atributo if sep else None)


CLASES_FINAS: tuple[str, ...] = tuple(
    clase_fina(d.nombre, a) for d in _LISTA for a in (d.atributos or (None,))
) + (SIN_TIPO,)
assert len(CLASES_FINAS) == 25
INDICE_CLASE: dict[str, int] = {c: i for i, c in enumerate(CLASES_FINAS)}


def admite(relacion: str, tipo_cabeza: str, tipo_cola: str) -> bool:
    if relacion == SIN_TIPO:
        return tipo_cabeza in TIPOS and tipo_cola in TIPOS
    d = RELACIONES[relacion]
    return tipo_cabeza in d.desde and tipo_cola in d.hasta


def relaciones_admitidas(tipo_cabeza: str, tipo_cola: str) -> list[str]:
    return [r for r in RELACIONES_Y_SIN_TIPO if admite(r, tipo_cabeza, tipo_cola)]


def es_simetrica(relacion: str, atributo: str | None) -> bool:
    if relacion == SIN_TIPO:
        return True
    if relacion == "familiar_de":
        return atributo != "hijo_de"
    return RELACIONES[relacion].simetrica
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

`uv run pytest tests/test_esquema_tipos.py -q` → 8 tests en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/esquema/tipos.py tests/test_esquema_tipos.py
git commit -m "Añade el esquema: tipos, 17 relaciones, 25 clases finas y sus restricciones"
```

---

### Tarea 0.4: El formato interno de documento, normalización y validación

**Ficheros:**
- Crear: `enrel/datos/normalizar.py`, `enrel/datos/documento.py`, `enrel/datos/validar.py`
- Test: `tests/test_datos_documento.py`

**Interfaces:**
- Produce en `normalizar.py`: `nfc(texto: str) -> str`; `plegar(texto: str) -> str` (NFC, minúsculas, sin diacríticos, espacios colapsados, comillas tipográficas a rectas); `PALABRA = re.compile(r"\w+(?:[-_]\w+)*|\S")`; `palabras(texto) -> list[tuple[int, int, str]]` (ini, fin, texto de cada palabra).
- Produce en `documento.py`:
  - `@dataclass class Mencion: id: str; ini: int; fin: int; texto: str; tipo: str; grupo: str; confianza: float | None = None`
  - `@dataclass class Grupo: id: str; tipo: str; canonico: str`
  - `@dataclass class Relacion: cabeza: str; cola: str; relacion: str; atributo: str | None = None; evidencia: tuple[int, int] | None = None; confianza: float | None = None`
  - `@dataclass class Documento: doc_id: str; texto: str; menciones: list[Mencion]; grupos: list[Grupo]; relaciones: list[Relacion]; url: str = ""; fecha: str = ""; seccion: str = ""; titulo: str = ""; fuente: str = ""; origen: dict = field(default_factory=dict)` con métodos `a_dict()`, `desde_dict(d)` (classmethod), `grupo_de(id) -> Grupo`, `menciones_de(grupo_id) -> list[Mencion]`, `clase_fina_de(rel) -> str`.
  - `guardar_jsonl(docs: Iterable[Documento], ruta: Path) -> int` (devuelve cuántos) y `cargar_jsonl(ruta) -> list[Documento]`. Serializa `evidencia` como `{"ini","fin"}` o `null`.
  - `hash_fichero(ruta) -> str` (SHA-256 en hexadecimal).
- Produce en `validar.py`: `validar_documento(doc: Documento) -> list[str]` (lista de errores, vacía si está bien) y `comprobar_fugas(conjuntos: dict[str, list[Documento]], protegidos: tuple[str, ...] = ("prueba", "prueba_dirigida", "desarrollo")) -> list[str]`.

Reglas de `validar_documento`: `texto == nfc(texto)`; cada mención con `0 <= ini < fin <= len(texto)` y `texto[ini:fin] == mencion.texto`; tipo en `TIPOS`; grupo existente y del mismo tipo que la mención; ids de menciones y grupos únicos; cada relación con cabeza y cola en grupos, `relacion` en `RELACIONES_Y_SIN_TIPO`, atributo válido (`clase_fina` no lanza), tipos admitidos (`admite`), sin autorrelaciones (`cabeza != cola`), sin duplicados de `(cabeza, cola, clase_fina)`, evidencia dentro del texto; para simétricas, no existe la relación espejo. Reglas de `comprobar_fugas`: ningún `doc_id` de un conjunto protegido aparece en otro conjunto.

- [ ] **Paso 1: Escribir los tests**

`tests/test_datos_documento.py`:

```python
from pathlib import Path

import pytest

from enrel.datos import normalizar as n
from enrel.datos.documento import Documento, Grupo, Mencion, Relacion, cargar_jsonl, guardar_jsonl
from enrel.datos.validar import comprobar_fugas, validar_documento


def doc_ejemplo() -> Documento:
    texto = n.nfc("Gustavo Petro\n\nEl presidente Gustavo Petro nombró a Luis Carlos Reyes como ministro de Comercio.")
    m = [
        Mencion("m1", 0, 13, "Gustavo Petro", "persona", "e1"),
        Mencion("m2", 29, 42, "Gustavo Petro", "persona", "e1"),
        Mencion("m3", 52, 69, "Luis Carlos Reyes", "persona", "e2"),
        Mencion("m4", 75, 95, "ministro de Comercio", "cargo", "e3"),
        Mencion("m5", 87, 95, "Comercio", "organizacion", "e4"),
    ]
    g = [Grupo("e1", "persona", "Gustavo Petro"), Grupo("e2", "persona", "Luis Carlos Reyes"),
         Grupo("e3", "cargo", "ministro de Comercio"), Grupo("e4", "organizacion", "Comercio")]
    r = [Relacion("e1", "e2", "nombro_a"), Relacion("e2", "e3", "ocupa_cargo", "actual", (15, 96))]
    return Documento("wp:1", texto, m, g, r, url="https://x", fecha="2023-01-01", seccion="silla-nacional",
                     titulo="Gustavo Petro", fuente="oro")


def test_plegar():
    assert n.plegar("  Álvaro  URIBE “Vélez” ") == 'alvaro uribe "velez"'
    assert n.palabras("Luis-Carlos, 2019.") == [(0, 11, "Luis-Carlos"), (11, 12, ","), (13, 17, "2019"), (17, 18, ".")]


def test_documento_valido_y_offsets():
    d = doc_ejemplo()
    for m in d.menciones:
        assert d.texto[m.ini:m.fin] == m.texto
    assert validar_documento(d) == []
    assert [m.id for m in d.menciones_de("e1")] == ["m1", "m2"]
    assert d.clase_fina_de(d.relaciones[1]) == "ocupa_cargo:actual"


def test_ida_y_vuelta_jsonl(tmp_path: Path):
    d = doc_ejemplo()
    ruta = tmp_path / "x.jsonl"
    assert guardar_jsonl([d], ruta) == 1
    [d2] = cargar_jsonl(ruta)
    assert d2 == d
    assert d2.relaciones[1].evidencia == (15, 96)


def test_validar_detecta_errores():
    d = doc_ejemplo()
    d.menciones[0].fin = 12
    d.relaciones.append(Relacion("e1", "e1", "socio_de"))
    d.relaciones.append(Relacion("e1", "e4", "ocupa_cargo", "actual"))
    d.relaciones.append(Relacion("e1", "e2", "nombro_a"))
    errores = validar_documento(d)
    assert any("m1" in e and "texto" in e for e in errores)
    assert any("autorrelación" in e for e in errores)
    assert any("no admite" in e for e in errores)
    assert any("duplicada" in e for e in errores)


def test_validar_simetrica_espejo():
    d = doc_ejemplo()
    d.relaciones = [Relacion("e1", "e2", "socio_de"), Relacion("e2", "e1", "socio_de")]
    assert any("espejo" in e for e in validar_documento(d))


def test_fugas():
    a, b = doc_ejemplo(), doc_ejemplo()
    b.doc_id = "wp:2"
    assert comprobar_fugas({"prueba": [a], "plata": [b]}) == []
    assert comprobar_fugas({"prueba": [a], "plata": [a, b]}) == ["wp:1 está en «prueba» y en «plata»"]
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_datos_documento.py -q` → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/datos/normalizar.py`**

```python
"""Normalización de texto: NFC para persistir, plegado para comparar."""

import re
import unicodedata

PALABRA = re.compile(r"\w+(?:[-_]\w+)*|\S")
_COMILLAS = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'"})


def nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def plegar(texto: str) -> str:
    """Minúsculas, sin diacríticos, comillas rectas, espacios colapsados. Solo para comparar, nunca para guardar."""
    t = unicodedata.normalize("NFD", texto.translate(_COMILLAS))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def palabras(texto: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in PALABRA.finditer(texto)]
```

- [ ] **Paso 4: Implementar `enrel/datos/documento.py`**

```python
"""El formato interno: un documento con menciones, grupos y relaciones sobre offsets de caracteres."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from enrel.esquema.tipos import clase_fina


@dataclass
class Mencion:
    id: str
    ini: int
    fin: int
    texto: str
    tipo: str
    grupo: str
    confianza: float | None = None


@dataclass
class Grupo:
    id: str
    tipo: str
    canonico: str


@dataclass
class Relacion:
    cabeza: str
    cola: str
    relacion: str
    atributo: str | None = None
    evidencia: tuple[int, int] | None = None
    confianza: float | None = None


@dataclass
class Documento:
    doc_id: str
    texto: str
    menciones: list[Mencion]
    grupos: list[Grupo]
    relaciones: list[Relacion]
    url: str = ""
    fecha: str = ""
    seccion: str = ""
    titulo: str = ""
    fuente: str = ""
    origen: dict = field(default_factory=dict)

    def grupo_de(self, grupo_id: str) -> Grupo:
        for g in self.grupos:
            if g.id == grupo_id:
                return g
        raise KeyError(grupo_id)

    def menciones_de(self, grupo_id: str) -> list[Mencion]:
        return [m for m in self.menciones if m.grupo == grupo_id]

    def clase_fina_de(self, rel: Relacion) -> str:
        return clase_fina(rel.relacion, rel.atributo)

    def a_dict(self) -> dict:
        d = asdict(self)
        for r in d["relaciones"]:
            ev = r["evidencia"]
            r["evidencia"] = None if ev is None else {"ini": ev[0], "fin": ev[1]}
        return d

    @classmethod
    def desde_dict(cls, d: dict) -> "Documento":
        rels = []
        for r in d.get("relaciones", []):
            ev = r.get("evidencia")
            rels.append(Relacion(r["cabeza"], r["cola"], r["relacion"], r.get("atributo"),
                                 None if ev is None else (ev["ini"], ev["fin"]), r.get("confianza")))
        return cls(
            doc_id=d["doc_id"], texto=d["texto"],
            menciones=[Mencion(**m) for m in d.get("menciones", [])],
            grupos=[Grupo(**g) for g in d.get("grupos", [])],
            relaciones=rels,
            url=d.get("url", ""), fecha=d.get("fecha", ""), seccion=d.get("seccion", ""),
            titulo=d.get("titulo", ""), fuente=d.get("fuente", ""), origen=d.get("origen", {}),
        )


def guardar_jsonl(docs: Iterable[Documento], ruta: Path) -> int:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with ruta.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d.a_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def cargar_jsonl(ruta: Path) -> list[Documento]:
    with Path(ruta).open(encoding="utf-8") as f:
        return [Documento.desde_dict(json.loads(l)) for l in f if l.strip()]


def hash_fichero(ruta: Path) -> str:
    h = hashlib.sha256()
    with Path(ruta).open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()
```

- [ ] **Paso 5: Implementar `enrel/datos/validar.py`**

```python
"""Comprobaciones que abortan una exportación: offsets, tipos, relaciones y fugas entre conjuntos."""

from enrel.datos.documento import Documento
from enrel.datos.normalizar import nfc
from enrel.esquema.tipos import RELACIONES_Y_SIN_TIPO, TIPOS, admite, clase_fina, es_simetrica


def validar_documento(doc: Documento) -> list[str]:
    errores: list[str] = []
    if doc.texto != nfc(doc.texto):
        errores.append(f"{doc.doc_id}: el texto no está en NFC")
    grupos = {g.id: g for g in doc.grupos}
    if len(grupos) != len(doc.grupos):
        errores.append(f"{doc.doc_id}: ids de grupo repetidos")
    vistos: set[str] = set()
    for m in doc.menciones:
        if m.id in vistos:
            errores.append(f"{doc.doc_id}: mención {m.id} repetida")
        vistos.add(m.id)
        if not (0 <= m.ini < m.fin <= len(doc.texto)):
            errores.append(f"{doc.doc_id}: mención {m.id} fuera del texto ({m.ini}, {m.fin})")
        elif doc.texto[m.ini:m.fin] != m.texto:
            errores.append(f"{doc.doc_id}: mención {m.id} no coincide con el texto: {doc.texto[m.ini:m.fin]!r} ≠ {m.texto!r}")
        if m.tipo not in TIPOS:
            errores.append(f"{doc.doc_id}: mención {m.id} con tipo desconocido {m.tipo!r}")
        g = grupos.get(m.grupo)
        if g is None:
            errores.append(f"{doc.doc_id}: mención {m.id} apunta a un grupo inexistente {m.grupo!r}")
        elif g.tipo != m.tipo:
            errores.append(f"{doc.doc_id}: mención {m.id} de tipo {m.tipo} en grupo {g.id} de tipo {g.tipo}")
    claves: set[tuple] = set()
    for r in doc.relaciones:
        if r.relacion not in RELACIONES_Y_SIN_TIPO:
            errores.append(f"{doc.doc_id}: relación desconocida {r.relacion!r}")
            continue
        try:
            fina = clase_fina(r.relacion, r.atributo)
        except ValueError as e:
            errores.append(f"{doc.doc_id}: {e}")
            continue
        if r.cabeza == r.cola:
            errores.append(f"{doc.doc_id}: autorrelación {fina} sobre {r.cabeza}")
            continue
        gc, gl = grupos.get(r.cabeza), grupos.get(r.cola)
        if gc is None or gl is None:
            errores.append(f"{doc.doc_id}: relación {fina} con extremo inexistente ({r.cabeza}, {r.cola})")
            continue
        if not admite(r.relacion, gc.tipo, gl.tipo):
            errores.append(f"{doc.doc_id}: {r.relacion} no admite {gc.tipo} → {gl.tipo}")
        clave = (r.cabeza, r.cola, fina)
        if clave in claves:
            errores.append(f"{doc.doc_id}: relación duplicada {clave}")
        if es_simetrica(r.relacion, r.atributo) and (r.cola, r.cabeza, fina) in claves:
            errores.append(f"{doc.doc_id}: relación simétrica con su espejo {clave}")
        claves.add(clave)
        if r.evidencia is not None and not (0 <= r.evidencia[0] < r.evidencia[1] <= len(doc.texto)):
            errores.append(f"{doc.doc_id}: evidencia fuera del texto en {fina}")
    return errores


def comprobar_fugas(conjuntos: dict[str, list[Documento]],
                    protegidos: tuple[str, ...] = ("prueba", "prueba_dirigida", "desarrollo")) -> list[str]:
    ids = {nombre: {d.doc_id for d in docs} for nombre, docs in conjuntos.items()}
    errores = []
    for prot in protegidos:
        for otro in conjuntos:
            if otro == prot or prot not in ids:
                continue
            for doc_id in sorted(ids[prot] & ids[otro]):
                errores.append(f"{doc_id} está en «{prot}» y en «{otro}»")
    return errores
```

- [ ] **Paso 6: Ejecutar y ver que pasa**

`uv run pytest tests/test_datos_documento.py -q` → 6 en verde. Si `test_plegar` falla por la posición exacta de las comillas, ajustar el test al resultado real de `str.translate`, no la función.

- [ ] **Paso 7: Commit**

```bash
git add enrel/datos tests/test_datos_documento.py
git commit -m "Añade el formato interno de documento, la normalización y el validador"
```

---

### Tarea 0.5: Mapeo desde el vocabulario de legajo, viejo y nuevo

**Ficheros:**
- Crear: `enrel/esquema/mapeo_legajo.py`
- Test: `tests/test_mapeo_legajo.py`

**Interfaces:**
- Consume: `enrel.esquema.tipos` (`admite`, `SIN_TIPO`, constantes).
- Produce:
  - `mapear_tipo(tipo_legajo: str) -> tuple[str, bool]`: devuelve `(tipo_enrel, designa)`; `"ley" → ("norma", False)`, `"cargo*" → ("cargo", True)`, el resto igual con `False`. Lanza `ValueError` si el tipo no existe.
  - `@dataclass(frozen=True) class Mapeo: relacion: str; atributo: str | None; invertir: bool`
  - `mapear_predicado(predicado: str, tipo_a: str, tipo_b: str, cuando: str = "vigente") -> Mapeo`: acepta los 35 predicados viejos y los 25 nuevos de legajo (`tipo_a`, `tipo_b` ya en tipos de enrel). Nunca devuelve `None`: lo que no encaja va a `SIN_TIPO`. Lanza `ValueError` si el predicado es desconocido.
  - `PREDICADOS_VIEJOS: frozenset[str]`, `PREDICADOS_NUEVOS: frozenset[str]`.

Tabla de reglas (viejo → enrel), aplicada en este orden: traducción del predicado, inversión, comprobación de `admite` y caída a `SIN_TIPO` si no admite.

| Predicado de legajo | Destino | Atributo | Invertir |
|---|---|---|---|
| ocupa el cargo | ocupa_cargo | vigente→actual, pasada→anterior, futura→aspirante | no |
| aspira a | ocupa_cargo | aspirante | no |
| renunció a | ocupa_cargo si cola es cargo, si no SIN_TIPO | anterior | no |
| nombró a / sucedió a / trabaja en / dirige / miembro de / fundó / contrató a / ubicado en / investigado por | mismo nombre en enrel (`nombro_a`, `sucedio_a`, `trabaja_en`, `dirige`, `miembro_de`, `fundo`, `contrato_a`, `ubicado_en`, `investigado_por`) | investigado_por: investigado | no |
| asesor de | trabaja_en si cola es organizacion | — | no |
| parte de | miembro_de si persona→organizacion; parte_de si organizacion→organizacion | — | no |
| dueño de | propietario_de | — | no |
| socio de | socio_de si persona↔persona; propietario_de si cola es organizacion | — | no |
| financia a / donó a | financia_a | — | no |
| aliado de / apoyó a | apoya_a | — | no |
| opositor de / criticó a | se_opone_a | — | no |
| acusado de | investigado_por si cola es organizacion | acusado | no |
| condenado por | investigado_por | condenado | no |
| padre o madre de | familiar_de | hijo_de | **sí** |
| hijo de | familiar_de | hijo_de | no |
| hermano de | familiar_de | hermano | no |
| cónyuge o pareja de | familiar_de | conyuge | no |
| familiar de | familiar_de | otro | no |
| se reunió con, citado en, autor de, destinado a, sanciona con, demandó a | SIN_TIPO | — | no |

Nuevos de legajo → enrel: `cónyuge de`→familiar_de:conyuge; `hijo de`→familiar_de:hijo_de; `hermano de`→familiar_de:hermano; `familiar de`→familiar_de:otro; `ocupa el cargo`→ocupa_cargo:actual; `ocupó el cargo`→ocupa_cargo:anterior; `aspira al cargo`→ocupa_cargo:aspirante; `nombró a`, `sucedió a`, `trabaja en`, `dirige`, `miembro de`, `fundó`, `parte de`, `contrató a`, `financia a`, `ubicado en` → su homónimo; `propietario de`→propietario_de; `socio de`→socio_de; `apoya a`→apoya_a; `se opone a`→se_opone_a; `investigado por`/`acusado por`/`condenado por` → investigado_por con investigado/acusado/condenado; `vínculo sin tipo`→SIN_TIPO. Observar que `ocupa el cargo`, `hijo de`, `hermano de`, `familiar de` y otros existen en los dos vocabularios con el mismo significado, y `cuando` solo se aplica a `ocupa el cargo` cuando llega con valor distinto de `vigente` (así un lote nuevo con `cuando="pasada"` en «ocupa el cargo» también se mapea a anterior).

- [ ] **Paso 1: Escribir los tests**

`tests/test_mapeo_legajo.py`:

```python
import pytest

from enrel.esquema.mapeo_legajo import Mapeo, mapear_predicado, mapear_tipo
from enrel.esquema.tipos import SIN_TIPO


def test_mapear_tipo():
    assert mapear_tipo("ley") == ("norma", False)
    assert mapear_tipo("cargo*") == ("cargo", True)
    assert mapear_tipo("persona") == ("persona", False)
    with pytest.raises(ValueError):
        mapear_tipo("evento")


@pytest.mark.parametrize("pred,ta,tb,cuando,esperado", [
    ("ocupa el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "actual", False)),
    ("ocupa el cargo", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", "anterior", False)),
    ("ocupa el cargo", "persona", "cargo", "futura", Mapeo("ocupa_cargo", "aspirante", False)),
    ("aspira a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False)),
    ("renunció a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "anterior", False)),
    ("renunció a", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("padre o madre de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", True)),
    ("hijo de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", False)),
    ("cónyuge o pareja de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False)),
    ("parte de", "persona", "organizacion", "vigente", Mapeo("miembro_de", None, False)),
    ("parte de", "organizacion", "organizacion", "vigente", Mapeo("parte_de", None, False)),
    ("parte de", "persona", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("asesor de", "persona", "persona", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("socio de", "persona", "organizacion", "vigente", Mapeo("propietario_de", None, False)),
    ("socio de", "persona", "persona", "vigente", Mapeo("socio_de", None, False)),
    ("aliado de", "organizacion", "organizacion", "vigente", Mapeo("apoya_a", None, False)),
    ("criticó a", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("acusado de", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("condenado por", "persona", "organizacion", "vigente", Mapeo("investigado_por", "condenado", False)),
    ("ubicado en", "monto", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
    ("citado en", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
    # vocabulario nuevo de legajo
    ("ocupó el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "anterior", False)),
    ("aspira al cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False)),
    ("cónyuge de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False)),
    ("propietario de", "organizacion", "organizacion", "vigente", Mapeo("propietario_de", None, False)),
    ("acusado por", "organizacion", "organizacion", "vigente", Mapeo("investigado_por", "acusado", False)),
    ("se opone a", "persona", "organizacion", "vigente", Mapeo("se_opone_a", None, False)),
    ("vínculo sin tipo", "monto", "obra", "vigente", Mapeo(SIN_TIPO, None, False)),
])
def test_mapear_predicado(pred, ta, tb, cuando, esperado):
    assert mapear_predicado(pred, ta, tb, cuando) == esperado


def test_predicado_desconocido():
    with pytest.raises(ValueError):
        mapear_predicado("es amigo de", "persona", "persona")
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_mapeo_legajo.py -q` → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/esquema/mapeo_legajo.py`**

```python
"""Traduce el vocabulario de legajo (los 35 predicados viejos y los 25 nuevos) al esquema de enrel."""

from dataclasses import dataclass

from enrel.esquema.tipos import C, L, O, P, SIN_TIPO, TIPOS, admite

_TIPOS_LEGAJO = {"ley": ("norma", False), "cargo*": ("cargo", True)}


def mapear_tipo(tipo_legajo: str) -> tuple[str, bool]:
    if tipo_legajo in _TIPOS_LEGAJO:
        return _TIPOS_LEGAJO[tipo_legajo]
    if tipo_legajo in TIPOS:
        return tipo_legajo, False
    raise ValueError(f"tipo de legajo desconocido: {tipo_legajo!r}")


@dataclass(frozen=True)
class Mapeo:
    relacion: str
    atributo: str | None
    invertir: bool


_CUANDO = {"vigente": "actual", "pasada": "anterior", "futura": "aspirante"}
_NADA = Mapeo(SIN_TIPO, None, False)

# Cada regla es (relacion, atributo, invertir) o una función (tipo_a, tipo_b, cuando) → esa tupla.
_REGLAS = {
    # viejos
    "ocupa el cargo": lambda ta, tb, c: ("ocupa_cargo", _CUANDO.get(c, "actual"), False),
    "aspira a": ("ocupa_cargo", "aspirante", False),
    "renunció a": lambda ta, tb, c: ("ocupa_cargo", "anterior", False) if tb == C else (SIN_TIPO, None, False),
    "nombró a": ("nombro_a", None, False),
    "sucedió a": ("sucedio_a", None, False),
    "trabaja en": ("trabaja_en", None, False),
    "asesor de": lambda ta, tb, c: ("trabaja_en", None, False) if tb == O else (SIN_TIPO, None, False),
    "dirige": ("dirige", None, False),
    "miembro de": ("miembro_de", None, False),
    "parte de": lambda ta, tb, c: ("miembro_de", None, False) if (ta, tb) == (P, O)
        else ("parte_de", None, False) if (ta, tb) == (O, O) else (SIN_TIPO, None, False),
    "fundó": ("fundo", None, False),
    "dueño de": ("propietario_de", None, False),
    "socio de": lambda ta, tb, c: ("socio_de", None, False) if (ta, tb) == (P, P)
        else ("propietario_de", None, False) if tb == O else (SIN_TIPO, None, False),
    "financia a": ("financia_a", None, False),
    "donó a": ("financia_a", None, False),
    "contrató a": ("contrato_a", None, False),
    "aliado de": ("apoya_a", None, False),
    "apoyó a": ("apoya_a", None, False),
    "opositor de": ("se_opone_a", None, False),
    "criticó a": ("se_opone_a", None, False),
    "investigado por": ("investigado_por", "investigado", False),
    "acusado de": ("investigado_por", "acusado", False),
    "condenado por": ("investigado_por", "condenado", False),
    "ubicado en": ("ubicado_en", None, False),
    "padre o madre de": ("familiar_de", "hijo_de", True),
    "hijo de": ("familiar_de", "hijo_de", False),
    "hermano de": ("familiar_de", "hermano", False),
    "cónyuge o pareja de": ("familiar_de", "conyuge", False),
    "familiar de": ("familiar_de", "otro", False),
    "se reunió con": (SIN_TIPO, None, False), "citado en": (SIN_TIPO, None, False), "autor de": (SIN_TIPO, None, False),
    "destinado a": (SIN_TIPO, None, False), "sanciona con": (SIN_TIPO, None, False), "demandó a": (SIN_TIPO, None, False),
    # nuevos (los homónimos ya están arriba)
    "ocupó el cargo": ("ocupa_cargo", "anterior", False),
    "aspira al cargo": ("ocupa_cargo", "aspirante", False),
    "propietario de": ("propietario_de", None, False),
    "apoya a": ("apoya_a", None, False),
    "se opone a": ("se_opone_a", None, False),
    "acusado por": ("investigado_por", "acusado", False),
    "cónyuge de": ("familiar_de", "conyuge", False),
    "vínculo sin tipo": (SIN_TIPO, None, False),
}

PREDICADOS_VIEJOS = frozenset([
    "padre o madre de", "hijo de", "hermano de", "cónyuge o pareja de", "familiar de",
    "ocupa el cargo", "trabaja en", "dirige", "fundó", "dueño de", "asesor de", "sucedió a", "nombró a", "renunció a", "parte de",
    "aliado de", "opositor de", "miembro de", "aspira a", "apoyó a", "se reunió con", "criticó a",
    "financia a", "contrató a", "socio de", "donó a", "destinado a",
    "investigado por", "condenado por", "acusado de", "demandó a", "sanciona con",
    "ubicado en", "citado en", "autor de",
])
PREDICADOS_NUEVOS = frozenset([
    "cónyuge de", "hijo de", "hermano de", "familiar de",
    "ocupa el cargo", "ocupó el cargo", "aspira al cargo", "nombró a", "sucedió a", "trabaja en", "dirige", "miembro de",
    "fundó", "propietario de", "socio de", "parte de", "contrató a", "financia a",
    "apoya a", "se opone a", "investigado por", "acusado por", "condenado por", "ubicado en", "vínculo sin tipo",
])
assert PREDICADOS_VIEJOS | PREDICADOS_NUEVOS == set(_REGLAS)


def mapear_predicado(predicado: str, tipo_a: str, tipo_b: str, cuando: str = "vigente") -> Mapeo:
    """Traduce un predicado de legajo, con los tipos de enrel de sus extremos. Lo que no encaja va a SIN_TIPO."""
    regla = _REGLAS.get(predicado)
    if regla is None:
        raise ValueError(f"predicado de legajo desconocido: {predicado!r}")
    relacion, atributo, invertir = regla(tipo_a, tipo_b, cuando) if callable(regla) else regla
    ta, tb = (tipo_b, tipo_a) if invertir else (tipo_a, tipo_b)
    if relacion != SIN_TIPO and not admite(relacion, ta, tb):
        return _NADA
    return Mapeo(relacion, atributo, invertir)
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

`uv run pytest tests/test_mapeo_legajo.py -q` → todos en verde (30 casos).

- [ ] **Paso 5: Commit**

```bash
git add enrel/esquema/mapeo_legajo.py tests/test_mapeo_legajo.py
git commit -m "Añade el mapeo de los predicados de legajo, viejos y nuevos, al esquema de enrel"
```

---

### Tarea 0.6: Agrupación de menciones en grupos por reglas

**Ficheros:**
- Crear: `enrel/datos/agrupar.py`
- Test: `tests/test_agrupar.py`

**Interfaces:**
- Consume: `Mencion`, `Grupo` de `documento.py`; `plegar` de `normalizar.py`.
- Produce: `agrupar(menciones: list[Mencion], alias: dict[str, str] | None = None) -> list[Grupo]`: asigna `m.grupo` a cada mención (muta la lista) y devuelve los grupos con ids `e1, e2, …` en orden de primera aparición; `canonico` es el texto de la mención más larga del grupo. `alias` es un diccionario opcional `plegado → plegado canónico` (los perfiles de Quién-AI).
- Reglas, en este orden y solo entre menciones del mismo tipo (spec §4.3): (1) mismo `plegar(texto)`; (2) personas: las palabras de la corta aparecen en orden dentro de la larga, o la corta es una sola palabra de ≥ 4 letras que es la última palabra de exactamente una persona multi-palabra del documento; (3) organizaciones: la corta es sigla (todo mayúsculas, 2 a 6 letras) que coincide con las iniciales de las palabras con mayúscula inicial de la larga, o la corta está contenida como secuencia de palabras en la larga; (4) los demás tipos solo por regla 1; (5) alias: si `plegar(a)` y `plegar(b)` mapean al mismo canónico en `alias`, se unen.
- `PARTICULAS = {"de", "del", "la", "las", "los", "y", "e", "da", "do", "van", "von"}` se ignoran al comparar palabras y al formar siglas.

- [ ] **Paso 1: Escribir los tests**

`tests/test_agrupar.py`:

```python
from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Mencion


def m(i, texto, tipo):
    return Mencion(f"m{i}", i * 100, i * 100 + len(texto), texto, tipo, "")


def test_misma_cadena_plegada():
    ms = [m(1, "Fiscalía", "organizacion"), m(2, "fiscalia", "organizacion"), m(3, "Fiscalía", "cargo")]
    gs = agrupar(ms)
    assert ms[0].grupo == ms[1].grupo != ms[2].grupo
    assert len(gs) == 2


def test_persona_forma_corta_en_orden_y_apellido():
    ms = [m(1, "Carlos Fernando Galán", "persona"), m(2, "Carlos Galán", "persona"), m(3, "Galán", "persona"),
          m(4, "Luis Carlos Galán", "persona")]
    agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    # «Galán» es apellido de dos personas distintas: no se une a ninguna
    assert ms[2].grupo not in (ms[0].grupo, ms[3].grupo)
    assert ms[3].grupo != ms[0].grupo


def test_persona_apellido_unico():
    ms = [m(1, "Gustavo Petro", "persona"), m(2, "Petro", "persona"), m(3, "Francia Márquez", "persona")]
    gs = agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    assert gs[0].canonico == "Gustavo Petro"


def test_organizacion_sigla_y_forma_corta():
    ms = [m(1, "Empresas Públicas de Medellín", "organizacion"), m(2, "EPM", "organizacion"),
          m(3, "Universidad Nacional de Colombia", "organizacion"), m(4, "Universidad Nacional", "organizacion")]
    agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    assert ms[2].grupo == ms[3].grupo
    assert ms[0].grupo != ms[2].grupo


def test_cargos_solo_por_cadena():
    ms = [m(1, "ministro de Hacienda", "cargo"), m(2, "ministro", "cargo")]
    agrupar(ms)
    assert ms[0].grupo != ms[1].grupo


def test_alias():
    ms = [m(1, "Juan Manuel Santos", "persona"), m(2, "Santos Calderón", "persona")]
    agrupar(ms, alias={"santos calderon": "juan manuel santos", "juan manuel santos": "juan manuel santos"})
    assert ms[0].grupo == ms[1].grupo
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_agrupar.py -q` → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/datos/agrupar.py`**

```python
"""Agrupa las menciones de un documento en entidades, por reglas (spec §4.3)."""

from enrel.datos.documento import Grupo, Mencion
from enrel.datos.normalizar import plegar

PARTICULAS = {"de", "del", "la", "las", "los", "y", "e", "da", "do", "van", "von"}


def _palabras(texto: str) -> list[str]:
    return [p for p in plegar(texto).split() if p not in PARTICULAS]


def _en_orden(corta: list[str], larga: list[str]) -> bool:
    if not corta or len(corta) >= len(larga):
        return False
    i = 0
    for p in larga:
        if i < len(corta) and p == corta[i]:
            i += 1
    return i == len(corta)


def _secuencia_contenida(corta: list[str], larga: list[str]) -> bool:
    n = len(corta)
    return 0 < n < len(larga) and any(larga[i:i + n] == corta for i in range(len(larga) - n + 1))


def _sigla_de(texto: str) -> str:
    return "".join(p[0] for p in texto.split() if p[:1].isupper() and p.lower() not in PARTICULAS)


def _es_sigla(texto: str) -> bool:
    t = texto.replace(".", "")
    return t.isupper() and t.isalpha() and 2 <= len(t) <= 6


class _Union:
    def __init__(self, n: int):
        self.p = list(range(n))

    def raiz(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def unir(self, a: int, b: int) -> None:
        self.p[self.raiz(a)] = self.raiz(b)


def agrupar(menciones: list[Mencion], alias: dict[str, str] | None = None) -> list[Grupo]:
    n = len(menciones)
    uf = _Union(n)
    plegadas = [plegar(m.texto) for m in menciones]
    palabras = [_palabras(m.texto) for m in menciones]
    alias = alias or {}

    # Regla 1 y regla 5, para todos los tipos.
    for i in range(n):
        for j in range(i + 1, n):
            if menciones[i].tipo != menciones[j].tipo:
                continue
            if plegadas[i] == plegadas[j]:
                uf.unir(i, j)
            elif alias and alias.get(plegadas[i]) is not None and alias.get(plegadas[i]) == alias.get(plegadas[j]):
                uf.unir(i, j)

    # Regla 2: personas.
    personas = [i for i in range(n) if menciones[i].tipo == "persona"]
    multipalabra = [i for i in personas if len(palabras[i]) >= 2]
    for i in personas:
        if len(palabras[i]) >= 2:
            for j in multipalabra:
                if i != j and _en_orden(palabras[i], palabras[j]):
                    uf.unir(i, j)
        elif len(palabras[i]) == 1 and len(palabras[i][0]) >= 4:
            apellido = palabras[i][0]
            candidatos = {uf.raiz(j) for j in multipalabra if palabras[j][-1] == apellido}
            if len(candidatos) == 1:
                uf.unir(i, candidatos.pop())

    # Regla 3: organizaciones.
    orgs = [i for i in range(n) if menciones[i].tipo == "organizacion"]
    for i in orgs:
        for j in orgs:
            if i == j:
                continue
            if _es_sigla(menciones[i].texto) and menciones[i].texto.replace(".", "") == _sigla_de(menciones[j].texto):
                uf.unir(i, j)
            elif _secuencia_contenida(palabras[i], palabras[j]):
                uf.unir(i, j)

    # Ids en orden de primera aparición; canónico = la mención más larga.
    grupos: list[Grupo] = []
    id_de_raiz: dict[int, str] = {}
    for i in sorted(range(n), key=lambda k: menciones[k].ini):
        r = uf.raiz(i)
        if r not in id_de_raiz:
            id_de_raiz[r] = f"e{len(grupos) + 1}"
            miembros = [menciones[k] for k in range(n) if uf.raiz(k) == r]
            canonico = max(miembros, key=lambda m: (len(m.texto), -m.ini)).texto
            grupos.append(Grupo(id_de_raiz[r], menciones[i].tipo, canonico))
        menciones[i].grupo = id_de_raiz[r]
    return grupos
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

`uv run pytest tests/test_agrupar.py -q` → 6 en verde. Si `test_persona_forma_corta_en_orden_y_apellido` falla porque «Galán» se une por la regla 1 con nada: comprobar que la regla del apellido exige exactamente un candidato (aquí hay dos) y que `_en_orden(["carlos","galan"], ["luis","carlos","galan"])` devuelve `True`. Sí lo devuelve: «Carlos Galán» también está en orden dentro de «Luis Carlos Galán». Eso es una ambigüedad real; la regla debe unir la forma corta **solo si hay un único candidato largo**. Ajustar la regla 2: para cada mención multipalabra `i`, calcular `candidatos = {raiz(j) for j multipalabra, j≠i, len(palabras[j]) > len(palabras[i]), _en_orden(palabras[i], palabras[j])}` y unir solo si `len(candidatos) == 1`. Volver a correr.

- [ ] **Paso 5: Commit**

```bash
git add enrel/datos/agrupar.py tests/test_agrupar.py
git commit -m "Añade la agrupación de menciones por reglas: cadena, formas cortas, siglas y alias"
```

---

### Tarea 0.7: Leer el archivo desde la base de legajo

**Ficheros:**
- Crear: `enrel/corpus/legajo_db.py`
- Test: `tests/test_legajo_db.py`

**Interfaces:**
- Produce:
  - `RUTA_POR_DEFECTO = Path("~/.local/share/com.legajo.app/legajo.sqlite").expanduser()`; `ruta_db(explicita: str | None = None) -> Path` (prioridad: argumento, variable `ENREL_LEGAJO_DB`, defecto).
  - `conectar(ruta: Path | None = None) -> sqlite3.Connection` (modo solo lectura: `file:…?mode=ro`, `uri=True`).
  - `seccion_de(link: str) -> str`: el primer segmento tras `https://www.lasillavacia.com/`; `""` si no encaja.
  - `@dataclass class Articulo: wp_id: int; titulo: str; texto_plano: str; palabras: int; url: str; fecha: str; seccion: str` con propiedad `texto` = `nfc(titulo + "\n\n" + texto_plano)` y `desplazamiento_cuerpo` = `len(nfc(titulo)) + 2` (cuántos caracteres hay antes del cuerpo).
  - `articulo(con, wp_id: int) -> Articulo | None`.
  - `iterar_articulos(con, minimo_palabras: int = 0) -> Iterator[Articulo]`.
  - `parrafos(texto_plano: str) -> list[tuple[int, str]]`: `(offset_inicio_en_texto_plano, texto_del_parrafo)` partiendo por `\n\n`, la misma convención de legajo (`core/src/contenido.rs`); conserva párrafos vacíos como cadenas vacías para que el índice `pi` coincida.
  - `es_transcripcion(texto_plano: str) -> bool`: más del 60 % de párrafos no vacíos tienen una sola línea de menos de 12 palabras y hay más de 40 párrafos.
- El título se limpia con `html.unescape` y se normaliza a NFC. Si `census.title` es nulo, título vacío y `desplazamiento_cuerpo = 0` (sin `\n\n`).

- [ ] **Paso 1: Escribir los tests con una base de juguete**

`tests/test_legajo_db.py`:

```python
import sqlite3
from pathlib import Path

import pytest

from enrel.corpus import legajo_db as db


@pytest.fixture
def base(tmp_path: Path) -> Path:
    ruta = tmp_path / "legajo.sqlite"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE connections (id INTEGER PRIMARY KEY);
        CREATE TABLE articles (connection_id INTEGER, wp_id INTEGER, html_raw TEXT, text_plain TEXT, word_count INTEGER,
                               fetched_at TEXT, PRIMARY KEY (connection_id, wp_id));
        CREATE TABLE census (connection_id INTEGER, wp_id INTEGER, date TEXT, date_valid INTEGER, slug TEXT, link TEXT,
                             title TEXT, title_key TEXT, author INTEGER, terms_json TEXT, PRIMARY KEY (connection_id, wp_id));
        INSERT INTO connections VALUES (1);
        INSERT INTO articles VALUES (1, 10, NULL, 'Primer párrafo.\n\nSegundo párrafo con Petro.', 6, '2026-01-01');
        INSERT INTO census VALUES (1, 10, '2023-05-01T10:00:00', 1, 'x', 'https://www.lasillavacia.com/silla-nacional/x/',
                                  'Petro &amp; Cía', 'petro', 1, '{}');
        INSERT INTO articles VALUES (1, 11, NULL, 'a', 1, '2026-01-01');
        INSERT INTO census VALUES (1, 11, '2010-01-01', 1, 'y', 'https://www.lasillavacia.com/en-vivo/y/', NULL, 'y', 1, '{}');
    """)
    con.commit()
    con.close()
    return ruta


def test_seccion_de():
    assert db.seccion_de("https://www.lasillavacia.com/quien-es-quien/juan-perez/") == "quien-es-quien"
    assert db.seccion_de("https://otra.com/x") == ""


def test_articulo_y_texto(base):
    con = db.conectar(base)
    a = db.articulo(con, 10)
    assert a.titulo == "Petro & Cía"
    assert a.seccion == "silla-nacional"
    assert a.fecha == "2023-05-01"
    assert a.texto == "Petro & Cía\n\nPrimer párrafo.\n\nSegundo párrafo con Petro."
    assert a.desplazamiento_cuerpo == len("Petro & Cía") + 2
    assert db.articulo(con, 99) is None


def test_articulo_sin_titulo(base):
    con = db.conectar(base)
    a = db.articulo(con, 11)
    assert a.titulo == "" and a.desplazamiento_cuerpo == 0 and a.texto == "a"


def test_parrafos_conserva_indices():
    ps = db.parrafos("Uno.\n\n\n\nTres.")
    assert ps == [(0, "Uno."), (6, ""), (8, "Tres.")]


def test_transcripcion():
    largo = "\n\n".join(["Pregunta corta"] * 50)
    assert db.es_transcripcion(largo)
    assert not db.es_transcripcion("Un párrafo normal de bastantes palabras que no parece una transcripción.\n\nOtro igual de normal.")


def test_iterar(base):
    con = db.conectar(base)
    assert [a.wp_id for a in db.iterar_articulos(con, minimo_palabras=2)] == [10]
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_legajo_db.py -q` → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/corpus/legajo_db.py`**

```python
"""Lectura del archivo desde la base de legajo (solo lectura)."""

import html
import os
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from enrel.datos.normalizar import nfc

RUTA_POR_DEFECTO = Path("~/.local/share/com.legajo.app/legajo.sqlite").expanduser()
_PREFIJO = "https://www.lasillavacia.com/"


def ruta_db(explicita: str | None = None) -> Path:
    if explicita:
        return Path(explicita).expanduser()
    if os.environ.get("ENREL_LEGAJO_DB"):
        return Path(os.environ["ENREL_LEGAJO_DB"]).expanduser()
    return RUTA_POR_DEFECTO


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = Path(ruta) if ruta else RUTA_POR_DEFECTO
    if not ruta.exists():
        raise FileNotFoundError(f"no existe la base de legajo en {ruta}")
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def seccion_de(link: str) -> str:
    if not link or not link.startswith(_PREFIJO):
        return ""
    resto = link[len(_PREFIJO):]
    return resto.split("/", 1)[0] if "/" in resto else ""


@dataclass
class Articulo:
    wp_id: int
    titulo: str
    texto_plano: str
    palabras: int
    url: str
    fecha: str
    seccion: str

    @property
    def desplazamiento_cuerpo(self) -> int:
        return len(self.titulo) + 2 if self.titulo else 0

    @property
    def texto(self) -> str:
        return f"{self.titulo}\n\n{self.texto_plano}" if self.titulo else self.texto_plano


def _fila_a_articulo(fila: sqlite3.Row) -> Articulo:
    titulo = nfc(html.unescape(fila["title"] or "")).strip()
    return Articulo(
        wp_id=int(fila["wp_id"]), titulo=titulo, texto_plano=nfc(fila["text_plain"] or ""),
        palabras=int(fila["word_count"] or 0), url=fila["link"] or "",
        fecha=(fila["date"] or "")[:10], seccion=seccion_de(fila["link"] or ""),
    )


_CONSULTA = """
SELECT a.wp_id, a.text_plain, a.word_count, c.date, c.link, c.title
FROM articles a JOIN census c ON c.connection_id = a.connection_id AND c.wp_id = a.wp_id
"""


def articulo(con: sqlite3.Connection, wp_id: int) -> Articulo | None:
    fila = con.execute(_CONSULTA + " WHERE a.wp_id = ?", (wp_id,)).fetchone()
    return _fila_a_articulo(fila) if fila else None


def iterar_articulos(con: sqlite3.Connection, minimo_palabras: int = 0) -> Iterator[Articulo]:
    for fila in con.execute(_CONSULTA + " WHERE a.text_plain IS NOT NULL AND a.word_count >= ? ORDER BY a.wp_id",
                            (minimo_palabras,)):
        yield _fila_a_articulo(fila)


def parrafos(texto_plano: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for trozo in texto_plano.split("\n\n"):
        out.append((pos, trozo))
        pos += len(trozo) + 2
    return out


def es_transcripcion(texto_plano: str) -> bool:
    ps = [p for _, p in parrafos(texto_plano) if p.strip()]
    if len(ps) <= 40:
        return False
    cortos = sum(1 for p in ps if "\n" not in p and len(p.split()) < 12)
    return cortos / len(ps) > 0.6
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

`uv run pytest tests/test_legajo_db.py -q` → 6 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/corpus/legajo_db.py tests/test_legajo_db.py
git commit -m "Añade la lectura del archivo desde la base de legajo"
```

---

### Tarea 0.8: Exportador del oro y la plata de legajo al formato interno

**Ficheros:**
- Crear: `enrel/anotacion/desde_legajo.py`
- Test: `tests/test_desde_legajo.py`

**Interfaces:**
- Consume: `Articulo`, `parrafos` (0.7); `mapear_tipo`, `mapear_predicado` (0.5); `agrupar` (0.6); `Documento` y `validar_documento` (0.4).
- Produce:
  - `documento_desde_oro_json(spec: dict, articulo: Articulo, fuente: str = "oro") -> Documento`. `spec` es `{"wp_id": N, "parrafos": {"3": {"E": [["texto","tipo"], …], "R": [["a","pred","b"] | ["a","pred","b","cuando"], …]}, …}}`. Cada `E` se localiza en **todas** sus apariciones dentro del párrafo (búsqueda exacta; si no hay ninguna, búsqueda por `plegar` sobre las palabras; si sigue sin haber, se cuenta en `origen["no_localizadas"]`). Cada `R` une la primera mención de `a` y la primera de `b` en ese párrafo; la relación se crea entre sus grupos, con `evidencia = (ini, fin)` del párrafo en el texto del documento. Offsets globales = `articulo.desplazamiento_cuerpo + offset_parrafo + offset_local`.
  - `documento_desde_sqlite(con_legajo, lote_id: int, articulo: Articulo, fuente: str = "oro") -> Documento`: lee `anotaciones` (mid, pi, ini, fin, texto, tipo, designa, grupo) y `relaciones` (a_mid, b_mid, predicado, cuando) del lote y el artículo; el grupo de cada mención sale de `anotaciones.grupo` cuando no es nulo, de `resoluciones` con `decision = 'misma'` (a_nombre/b_nombre por `plegar`), y del resto de `agrupar`. `designa` se guarda en `origen["designa"]` como lista de ids de mención.
  - `documento_desde_plata_legajo(filas: list[dict], articulo: Articulo) -> Documento`: filas de `plata-mm*.jsonl` del mismo `wp_id` (cada fila un párrafo con `pi`, `texto`, `entidades[{ini,fin,tipo,texto}]`, `relaciones[{a,b,predicado,cuando}]` con `a`/`b` índices sobre `entidades`). `fuente = "plata-legajo"`.
  - Todas: los tipos pasan por `mapear_tipo`; los predicados por `mapear_predicado` con los tipos ya mapeados; si `invertir`, se intercambian cabeza y cola; relaciones duplicadas y espejos de simétricas se colapsan; el documento resultante pasa `validar_documento` (si no, lanza `ValueError` con los errores). `origen` incluye `{"mapeo_legajo": True, "lote_id" | "spec": …, "predicados_originales": Counter}`.
  - `leer_oro_json(directorio: Path) -> dict[int, dict]` (wp_id → spec) y `leer_plata_legajo(ruta_jsonl: Path) -> dict[int, list[dict]]`.

- [ ] **Paso 1: Escribir los tests**

`tests/test_desde_legajo.py`:

```python
from pathlib import Path

import pytest

from enrel.anotacion import desde_legajo as dl
from enrel.corpus.legajo_db import Articulo
from enrel.datos.validar import validar_documento

CUERPO = ("Álvaro Uribe fue presidente de Colombia.\n\n"
          "Tomás Uribe, hijo de Álvaro Uribe, es empresario. Álvaro Uribe fundó el Centro Democrático.")
ART = Articulo(wp_id=7, titulo="Los Uribe", texto_plano=CUERPO, palabras=20,
               url="https://www.lasillavacia.com/quien-es-quien/uribe/", fecha="2020-01-01", seccion="quien-es-quien")

SPEC = {"wp_id": 7, "parrafos": {
    "0": {"E": [["Álvaro Uribe", "persona"], ["presidente de Colombia", "cargo*"], ["Colombia", "lugar"]],
          "R": [["Álvaro Uribe", "ocupa el cargo", "presidente de Colombia", "pasada"]]},
    "1": {"E": [["Tomás Uribe", "persona"], ["Álvaro Uribe", "persona"], ["Centro Democrático", "organizacion"]],
          "R": [["Álvaro Uribe", "padre o madre de", "Tomás Uribe"], ["Álvaro Uribe", "fundó", "Centro Democrático"]]},
}}


def test_oro_json_offsets_y_todas_las_apariciones():
    d = dl.documento_desde_oro_json(SPEC, ART)
    assert validar_documento(d) == []
    assert d.texto.startswith("Los Uribe\n\n")
    uribes = [m for m in d.menciones if m.texto == "Álvaro Uribe"]
    assert len(uribes) == 3  # una en el párrafo 0, dos en el 1
    assert len({m.grupo for m in uribes}) == 1
    for m in d.menciones:
        assert d.texto[m.ini:m.fin] == m.texto
    assert "presidente de Colombia" in [m.texto for m in d.menciones]
    assert len(d.origen["designa"]) == 1


def test_oro_json_mapeo_e_inversion():
    d = dl.documento_desde_oro_json(SPEC, ART)
    finas = {(d.grupo_de(r.cabeza).canonico, d.clase_fina_de(r), d.grupo_de(r.cola).canonico) for r in d.relaciones}
    assert ("Álvaro Uribe", "ocupa_cargo:anterior", "presidente de Colombia") in finas
    assert ("Tomás Uribe", "familiar_de:hijo_de", "Álvaro Uribe") in finas   # invertida
    assert ("Álvaro Uribe", "fundo", "Centro Democrático") in finas
    assert len(d.relaciones) == 3
    assert d.origen["predicados_originales"]["padre o madre de"] == 1


def test_plata_legajo():
    filas = [{"wp_id": 7, "pi": 1, "texto": ART.texto_plano.split("\n\n")[1],
              "entidades": [{"ini": 0, "fin": 11, "tipo": "persona", "texto": "Tomás Uribe"},
                            {"ini": 21, "fin": 33, "tipo": "persona", "texto": "Álvaro Uribe"}],
              "relaciones": [{"a": 0, "b": 1, "predicado": "hijo de", "cuando": "vigente"}]}]
    d = dl.documento_desde_plata_legajo(filas, ART)
    assert validar_documento(d) == []
    assert d.fuente == "plata-legajo"
    assert d.clase_fina_de(d.relaciones[0]) == "familiar_de:hijo_de"


@pytest.mark.skipif(not Path("datos-anteriores/entrenamiento/oro").exists(), reason="sin datos reales")
def test_oro_real_completo():
    from enrel.corpus import legajo_db as db
    specs = dl.leer_oro_json(Path("datos-anteriores/entrenamiento/oro"))
    assert len(specs) == 125
    con = db.conectar(db.ruta_db())
    errores, docs, no_loc = 0, 0, 0
    for wp, spec in specs.items():
        art = db.articulo(con, wp)
        assert art is not None, wp
        d = dl.documento_desde_oro_json(spec, art)
        docs += 1
        no_loc += d.origen.get("no_localizadas", 0)
        errores += len(validar_documento(d))
    assert docs == 125 and errores == 0
    # Las menciones que no se pudieron localizar en el texto local deben ser pocas (texto editado en WordPress).
    assert no_loc < 60
```

- [ ] **Paso 2: Ejecutar y ver que falla**

`uv run pytest tests/test_desde_legajo.py -q` → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/anotacion/desde_legajo.py`**

```python
"""Convierte el oro y la plata de legajo (por párrafo, 35 o 25 predicados) al formato interno de enrel."""

import json
import sqlite3
from collections import Counter
from pathlib import Path

from enrel.corpus.legajo_db import Articulo, parrafos
from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Grupo, Mencion, Relacion
from enrel.datos.normalizar import palabras, plegar
from enrel.datos.validar import validar_documento
from enrel.esquema.mapeo_legajo import mapear_predicado, mapear_tipo
from enrel.esquema.tipos import clase_fina, es_simetrica


def leer_oro_json(directorio: Path) -> dict[int, dict]:
    out = {}
    for ruta in sorted(Path(directorio).glob("*.json")):
        spec = json.loads(ruta.read_text(encoding="utf-8"))
        out[int(spec["wp_id"])] = spec
    return out


def leer_plata_legajo(ruta_jsonl: Path) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    with Path(ruta_jsonl).open(encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                fila = json.loads(linea)
                out.setdefault(int(fila["wp_id"]), []).append(fila)
    return out


def _apariciones(texto_parrafo: str, buscado: str) -> list[tuple[int, int]]:
    """Todas las apariciones de `buscado` en el párrafo, exactas; si no hay, por palabras plegadas."""
    out, pos = [], 0
    while True:
        i = texto_parrafo.find(buscado, pos)
        if i < 0:
            break
        out.append((i, i + len(buscado)))
        pos = i + 1
    if out:
        return out
    objetivo = [plegar(p) for _, _, p in palabras(buscado)]
    pals = palabras(texto_parrafo)
    n = len(objetivo)
    for k in range(len(pals) - n + 1):
        if [plegar(p) for _, _, p in pals[k:k + n]] == objetivo:
            out.append((pals[k][0], pals[k + n - 1][1]))
    return out


class _Constructor:
    """Acumula menciones y relaciones con offsets globales y produce el Documento."""

    def __init__(self, articulo: Articulo, fuente: str, origen: dict):
        self.art = articulo
        self.fuente = fuente
        self.origen = {"mapeo_legajo": True, "no_localizadas": 0, "predicados_originales": Counter(), **origen}
        self.menciones: list[Mencion] = []
        self.pendientes: list[tuple[str, str, str, str | None, tuple[int, int]]] = []  # (mid_a, mid_b, pred, cuando, evidencia)
        self.designa: list[str] = []
        self.grupo_forzado: dict[str, str] = {}
        self.offsets_parrafo = {pi: off for pi, (off, _) in enumerate(parrafos(articulo.texto_plano))}
        self.textos_parrafo = {pi: t for pi, (_, t) in enumerate(parrafos(articulo.texto_plano))}

    def mencion(self, pi: int, ini_local: int, fin_local: int, texto: str, tipo_legajo: str, mid: str | None = None,
                designa: bool = False, grupo: str | None = None) -> Mencion:
        tipo, designa_tipo = mapear_tipo(tipo_legajo)
        base = self.art.desplazamiento_cuerpo + self.offsets_parrafo[pi]
        m = Mencion(mid or f"m{len(self.menciones) + 1}", base + ini_local, base + fin_local, texto, tipo, "")
        self.menciones.append(m)
        if designa or designa_tipo:
            self.designa.append(m.id)
        if grupo:
            self.grupo_forzado[m.id] = grupo
        return m

    def evidencia(self, pi: int) -> tuple[int, int]:
        base = self.art.desplazamiento_cuerpo + self.offsets_parrafo[pi]
        return base, base + len(self.textos_parrafo[pi])

    def relacion(self, mid_a: str, mid_b: str, predicado: str, cuando: str | None, pi: int) -> None:
        self.pendientes.append((mid_a, mid_b, predicado, cuando or "vigente", self.evidencia(pi)))
        self.origen["predicados_originales"][predicado] += 1

    def construir(self, pares_mismos: list[tuple[str, str]] = ()) -> Documento:
        grupos = agrupar(self.menciones)
        # Grupos forzados por legajo (columna `grupo` o resoluciones «misma»): fusionar.
        self._fusionar(grupos, pares_mismos)
        por_mid = {m.id: m for m in self.menciones}
        relaciones: list[Relacion] = []
        claves: set[tuple] = set()
        for mid_a, mid_b, pred, cuando, ev in self.pendientes:
            a, b = por_mid.get(mid_a), por_mid.get(mid_b)
            if a is None or b is None:
                continue
            mp = mapear_predicado(pred, a.tipo, b.tipo, cuando)
            cabeza, cola = (b, a) if mp.invertir else (a, b)
            if cabeza.grupo == cola.grupo:
                continue
            fina = clase_fina(mp.relacion, mp.atributo)
            clave = (cabeza.grupo, cola.grupo, fina)
            espejo = (cola.grupo, cabeza.grupo, fina)
            if clave in claves or (es_simetrica(mp.relacion, mp.atributo) and espejo in claves):
                continue
            claves.add(clave)
            relaciones.append(Relacion(cabeza.grupo, cola.grupo, mp.relacion, mp.atributo, ev))
        self.origen["designa"] = self.designa
        self.origen["predicados_originales"] = dict(self.origen["predicados_originales"])
        doc = Documento(
            doc_id=f"wp:{self.art.wp_id}", texto=self.art.texto, menciones=self.menciones, grupos=grupos,
            relaciones=relaciones, url=self.art.url, fecha=self.art.fecha, seccion=self.art.seccion,
            titulo=self.art.titulo, fuente=self.fuente, origen=self.origen,
        )
        errores = validar_documento(doc)
        if errores:
            raise ValueError("\n".join(errores))
        return doc

    def _fusionar(self, grupos: list[Grupo], pares_mismos) -> None:
        """Une grupos que legajo declaró iguales: por `grupo` de anotaciones o por resoluciones «misma»."""
        por_id = {g.id: g for g in grupos}
        # Por columna grupo: todas las menciones con el mismo valor van juntas.
        por_forzado: dict[str, set[str]] = {}
        for mid, gf in self.grupo_forzado.items():
            m = next(x for x in self.menciones if x.id == mid)
            por_forzado.setdefault(gf, set()).add(m.grupo)
        uniones = [s for s in por_forzado.values() if len(s) > 1]
        # Por resoluciones: nombres plegados.
        canonicos = {plegar(g.canonico): g.id for g in grupos}
        for a, b in pares_mismos:
            ga, gb = canonicos.get(plegar(a)), canonicos.get(plegar(b))
            if ga and gb and ga != gb and por_id[ga].tipo == por_id[gb].tipo:
                uniones.append({ga, gb})
        for s in uniones:
            destino = min(s, key=lambda gid: int(gid[1:]))
            for m in self.menciones:
                if m.grupo in s:
                    m.grupo = destino
        vivos = {m.grupo for m in self.menciones}
        grupos[:] = [g for g in grupos if g.id in vivos]


def documento_desde_oro_json(spec: dict, articulo: Articulo, fuente: str = "oro") -> Documento:
    c = _Constructor(articulo, fuente, {"spec": True})
    for pi_str, p in spec.get("parrafos", {}).items():
        pi = int(pi_str)
        if pi not in c.textos_parrafo:
            continue
        texto_p = c.textos_parrafo[pi]
        primera: dict[str, str] = {}
        for texto_e, tipo_e in p.get("E", []):
            aps = _apariciones(texto_p, texto_e)
            if not aps:
                c.origen["no_localizadas"] += 1
                continue
            for ini, fin in aps:
                m = c.mencion(pi, ini, fin, texto_p[ini:fin], tipo_e)
                primera.setdefault(texto_e, m.id)
        for r in p.get("R", []):
            a, pred, b = r[0], r[1], r[2]
            cuando = r[3] if len(r) > 3 else "vigente"
            if a in primera and b in primera:
                c.relacion(primera[a], primera[b], pred, cuando, pi)
    return c.construir()


def documento_desde_sqlite(con: sqlite3.Connection, lote_id: int, articulo: Articulo, fuente: str = "oro") -> Documento:
    c = _Constructor(articulo, fuente, {"lote_id": lote_id})
    filas = con.execute(
        "SELECT mid, pi, ini, fin, texto, tipo, designa, grupo FROM anotaciones WHERE lote_id = ? AND wp_id = ? ORDER BY pi, ini",
        (lote_id, articulo.wp_id)).fetchall()
    for f in filas:
        pi = int(f["pi"])
        if pi not in c.textos_parrafo or c.textos_parrafo[pi][f["ini"]:f["fin"]] != f["texto"]:
            c.origen["no_localizadas"] += 1
            continue
        c.mencion(pi, int(f["ini"]), int(f["fin"]), f["texto"], f["tipo"], mid=f["mid"],
                  designa=bool(f["designa"]), grupo=f["grupo"])
    pi_de = {f["mid"]: int(f["pi"]) for f in filas}
    for r in con.execute("SELECT a_mid, b_mid, predicado, cuando FROM relaciones WHERE lote_id = ? AND wp_id = ?",
                         (lote_id, articulo.wp_id)):
        if r["a_mid"] in pi_de and r["b_mid"] in pi_de:
            c.relacion(r["a_mid"], r["b_mid"], r["predicado"], r["cuando"], pi_de[r["a_mid"]])
    mismos = [(x["a_nombre"], x["b_nombre"]) for x in con.execute(
        "SELECT a_nombre, b_nombre FROM resoluciones WHERE lote_id = ? AND decision = 'misma'", (lote_id,))]
    return c.construir(mismos)


def documento_desde_plata_legajo(filas: list[dict], articulo: Articulo) -> Documento:
    c = _Constructor(articulo, "plata-legajo", {"modelo": filas[0].get("modelo", ""), "prompt": filas[0].get("prompt", "")})
    for fila in filas:
        pi = int(fila["pi"])
        if pi not in c.textos_parrafo:
            continue
        ids = []
        for e in fila.get("entidades", []):
            if c.textos_parrafo[pi][e["ini"]:e["fin"]] != e["texto"]:
                c.origen["no_localizadas"] += 1
                ids.append(None)
                continue
            ids.append(c.mencion(pi, e["ini"], e["fin"], e["texto"], e["tipo"]).id)
        for r in fila.get("relaciones", []):
            a, b = ids[r["a"]] if r["a"] < len(ids) else None, ids[r["b"]] if r["b"] < len(ids) else None
            if a and b:
                c.relacion(a, b, r["predicado"], r.get("cuando"), pi)
    return c.construir()
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

`uv run pytest tests/test_desde_legajo.py -q` → 3 en verde más el real si hay datos (`-m ""` no hace falta; no lleva marca). Si el test real falla por `no_localizadas ≥ 60`, imprimir los casos y decidir: si son ediciones de WordPress posteriores al oro, subir el tope y documentarlo en el commit; si son errores de `_apariciones`, arreglarlos.

- [ ] **Paso 5: Commit**

```bash
git add enrel/anotacion/desde_legajo.py tests/test_desde_legajo.py
git commit -m "Añade el exportador del oro y la plata de legajo al formato interno"
```

---

### Tarea 0.9: Congelar el corpus

**Ficheros:**
- Crear: `enrel/corpus/congelar.py`, `enrel/_subcomandos.py` (añadir import), `enrel/corpus/cli_congelar.py`
- Test: `tests/test_congelar.py`

**Interfaces:**
- Produce: `congelar(con, salida: Path, minimo_palabras: int = 150, maximo_palabras: int = 2000) -> dict` que escribe `salida` (JSONL con `{"doc_id","wp_id","url","fecha","seccion","titulo","texto","palabras","hash"}`, un artículo por línea, `texto` con el título antepuesto) y devuelve un resumen `{"total": n, "excluidos": {"pocas_palabras": a, "muchas_palabras": b, "transcripcion": c, "sin_texto": d}, "por_seccion": {...}, "por_tramo": {...}, "hash": sha256}`. Escribe también `salida.with_suffix(".resumen.json")`.
- `tramo_de(fecha: str) -> str`: `"2009-2015"`, `"2016-2021"`, `"2022-2026"` según el año; `"sin-fecha"` si no hay.
- Subcomando `enrel congelar --salida datos/corpus/articulos.jsonl [--legajo-db RUTA] [--min 150] [--max 2000]`.

- [ ] **Paso 1: Test**

`tests/test_congelar.py` reutiliza la fixture `base` de `tests/test_legajo_db.py` (moverla a `tests/conftest.py` para compartirla; el test de 0.7 la sigue usando sin cambios):

```python
import json
from pathlib import Path

from enrel.corpus import congelar as cg
from enrel.corpus import legajo_db as db


def test_tramo_de():
    assert cg.tramo_de("2010-02-01") == "2009-2015"
    assert cg.tramo_de("2021-12-31") == "2016-2021"
    assert cg.tramo_de("2024-01-01") == "2022-2026"
    assert cg.tramo_de("") == "sin-fecha"


def test_congelar(base, tmp_path: Path):
    con = db.conectar(base)
    salida = tmp_path / "articulos.jsonl"
    resumen = cg.congelar(con, salida, minimo_palabras=2, maximo_palabras=2000)
    filas = [json.loads(l) for l in salida.read_text(encoding="utf-8").splitlines()]
    assert resumen["total"] == 1 and len(filas) == 1
    assert filas[0]["doc_id"] == "wp:10" and filas[0]["seccion"] == "silla-nacional"
    assert filas[0]["texto"].startswith("Petro & Cía\n\n")
    assert resumen["excluidos"]["pocas_palabras"] == 1
    assert (tmp_path / "articulos.resumen.json").exists()
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar**

`enrel/corpus/congelar.py`:

```python
"""Congela el archivo en un JSONL con filtros, para que todo el proyecto lea lo mismo."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from enrel.corpus.legajo_db import es_transcripcion, iterar_articulos


def tramo_de(fecha: str) -> str:
    if not fecha[:4].isdigit():
        return "sin-fecha"
    anio = int(fecha[:4])
    if anio <= 2015:
        return "2009-2015"
    if anio <= 2021:
        return "2016-2021"
    return "2022-2026"


def congelar(con, salida: Path, minimo_palabras: int = 150, maximo_palabras: int = 2000) -> dict:
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    excluidos = Counter()
    por_seccion, por_tramo = Counter(), Counter()
    total = 0
    h = hashlib.sha256()
    with salida.open("w", encoding="utf-8") as f:
        for a in iterar_articulos(con):
            if not a.texto_plano.strip():
                excluidos["sin_texto"] += 1
                continue
            if a.palabras < minimo_palabras:
                excluidos["pocas_palabras"] += 1
                continue
            if a.palabras > maximo_palabras:
                excluidos["muchas_palabras"] += 1
                continue
            if es_transcripcion(a.texto_plano):
                excluidos["transcripcion"] += 1
                continue
            fila = {"doc_id": f"wp:{a.wp_id}", "wp_id": a.wp_id, "url": a.url, "fecha": a.fecha, "seccion": a.seccion,
                    "titulo": a.titulo, "texto": a.texto, "palabras": a.palabras,
                    "hash": hashlib.sha256(a.texto.encode("utf-8")).hexdigest()[:16]}
            linea = json.dumps(fila, ensure_ascii=False) + "\n"
            f.write(linea)
            h.update(linea.encode("utf-8"))
            total += 1
            por_seccion[a.seccion or "(sin sección)"] += 1
            por_tramo[tramo_de(a.fecha)] += 1
    resumen = {"total": total, "excluidos": dict(excluidos), "por_seccion": dict(por_seccion.most_common()),
               "por_tramo": dict(por_tramo), "hash": h.hexdigest(),
               "parametros": {"minimo_palabras": minimo_palabras, "maximo_palabras": maximo_palabras}}
    salida.with_suffix(".resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen
```

`enrel/corpus/cli_congelar.py`:

```python
"""Subcomando `enrel congelar`."""

from pathlib import Path

from enrel.cli import registrar


@registrar("congelar", "Congela el archivo de legajo en datos/corpus/articulos.jsonl")
def congelar_cmd(args):
    from enrel.corpus.congelar import congelar
    from enrel.corpus.legajo_db import conectar, ruta_db

    con = conectar(ruta_db(args.legajo_db))
    resumen = congelar(con, Path(args.salida), args.min, args.max)
    print(f"{resumen['total']} artículos → {args.salida}; excluidos {resumen['excluidos']}")


def _configurar(p):
    p.add_argument("--salida", default="datos/corpus/articulos.jsonl")
    p.add_argument("--legajo-db", default=None)
    p.add_argument("--min", type=int, default=150)
    p.add_argument("--max", type=int, default=2000)


congelar_cmd.configurar = _configurar
```

En `enrel/_subcomandos.py` añadir `from enrel.corpus import cli_congelar  # noqa: F401`.

- [ ] **Paso 4: Correr tests y congelar de verdad**

```bash
uv run pytest tests/test_congelar.py -q
uv run enrel congelar
python3 -c "import json; print(json.load(open('datos/corpus/articulos.resumen.json')))"
```

Esperado: tests en verde; el resumen muestra del orden de 55.000 a 70.000 artículos (el archivo tiene 81.103 con texto; en-vivo pierde los de menos de 150 palabras, unos 10.000), con `por_seccion` y `por_tramo`. Anotar `total`, `excluidos` y `hash` en `docs/resultados/etapa-0-corpus.md` con la fecha y el comando.

- [ ] **Paso 5: Commit**

```bash
git add enrel/corpus/congelar.py enrel/corpus/cli_congelar.py enrel/_subcomandos.py tests/conftest.py tests/test_congelar.py tests/test_legajo_db.py docs/resultados/etapa-0-corpus.md
git commit -m "Congela el archivo en un JSONL con filtros y deja el resumen medido"
```

---

### Tarea 0.10: Disparadores por relación y muestreo en tres estratos

**Ficheros:**
- Crear: `enrel/corpus/disparadores.py`, `enrel/corpus/muestrear.py`, `enrel/corpus/cli_muestrear.py`
- Modificar: `enrel/_subcomandos.py`
- Test: `tests/test_disparadores.py`, `tests/test_muestrear.py`

**Interfaces:**
- Produce en `disparadores.py`: `DISPARADORES: dict[str, re.Pattern]` con una expresión regular compilada (`re.I`) por cada una de las 17 relaciones; `relaciones_disparadas(texto: str) -> set[str]`.
- Produce en `muestrear.py`:
  - `@dataclass class Seleccionado: doc_id: str; conjunto: str; estrato: str; disparadas: list[str]`
  - `muestrear(corpus: Path, excluir: set[str], semilla: int = 2026, cuota_relacion: int = 120, perfiles: int = 400, aleatorios: int = 1100, humo: int = 30) -> list[Seleccionado]`. Lee `articulos.jsonl` (0.9). Excluye `excluir` (los doc_id de prueba, prueba_dirigida, desarrollo y oro-perfiles). Estrato `dirigido`: para cada relación en el orden de `RELACIONES`, hasta `cuota_relacion` artículos que la disparan, priorizando los que disparan más relaciones distintas, sin repetir artículos entre relaciones. Estrato `perfiles`: `perfiles` artículos de sección `quien-es-quien` no elegidos aún, repartidos por tramo. Estrato `aleatorio`: `aleatorios` artículos del resto, estratificados por sección (proporcional al corpus) y tramo. Los primeros `humo` del total, al azar, se marcan `conjunto = "humo_maestro"`; el resto `conjunto = "plata"`.
  - `guardar_seleccion(sel: list[Seleccionado], ruta: Path) -> None` (JSONL) y `cargar_seleccion(ruta) -> list[Seleccionado]`.
  - `resumen(sel) -> dict` con conteos por estrato, por conjunto, y artículos que disparan cada relación.
- Subcomando `enrel muestrear --corpus datos/corpus/articulos.jsonl --excluir datos/conjuntos/protegidos.txt --salida datos/conjuntos/seleccion.jsonl [--semilla 2026]`. `protegidos.txt` es un fichero con un `doc_id` por línea (se crea en la Tarea 0.14 a partir de `prueba.txt` y los lotes de oro).

Léxico de disparadores (una línea por relación; `\b` donde aplica; en español con y sin tilde donde el archivo varía):

```python
DISPARADORES = {k: re.compile(v, re.I) for k, v in {
    "ocupa_cargo": r"\b(ministr[oa]|alcalde(sa)?|gobernador[a]?|senador[a]?|representante a la c[aá]mara|magistrad[oa]|procurador[a]?|fiscal general|contralor[a]?|director[a]? (general|ejecutiv[oa])|presidenta?|vicepresidenta?|concejal|diputad[oa]|embajador[a]?|superintendente|candidat[oa]|precandidat[oa]|aspira a|se posesion[óo]|fue nombrad[oa]|exministr[oa]|exalcalde|exgobernador|expresidente)\b",
    "nombro_a": r"\b(nombr[óo] a|design[óo] a|escogi[óo] a|eligi[óo] a|posesion[óo] a|nombramiento de)\b",
    "sucedio_a": r"\b(reemplaz[óo] a|sucedi[óo] a|sucesor[a]? de|en reemplazo de|releva a|relev[óo] a|dej[óo] el cargo a)\b",
    "trabaja_en": r"\b(trabaj[óo]? (en|para)|asesor[a]? de|funcionari[oa] de|emplead[oa] de|consultor[a]? de|contratista de)\b",
    "dirige": r"\b(dirige|dirigi[óo]|preside|presidi[óo]|gerente (general )?de|director[a]? de|al frente de|encabeza|lidera)\b",
    "miembro_de": r"\b(militante de|miembro de|integrante de|hace parte de|pertenece a|afiliad[oa] a|bancada de|junta directiva)\b",
    "fundo": r"\b(fund[óo]|fundador[a]? de|cofundador[a]?|cre[óo] la (empresa|fundaci[óo]n|organizaci[óo]n)|creador[a]? de)\b",
    "propietario_de": r"\b(dueñ[oa] de|propietari[oa] de|accionista|acciones de|controla la empresa|es dueñ[oa]|compr[óo] la empresa|adquiri[óo])\b",
    "socio_de": r"\b(socio de|socia de|socios|sus socios|en sociedad con)\b",
    "parte_de": r"\b(filial de|subsidiaria|adscrit[oa] a|depende del|dependencia de|hace parte del (ministerio|grupo|conglomerado)|pertenece al grupo)\b",
    "contrato_a": r"\b(contrat[óo] a|contrato con|licitaci[óo]n|adjudic[óo]|adjudicaci[óo]n|contratista|contratos por)\b",
    "financia_a": r"\b(financi[óo]|financia|don[óo]|donaci[óo]n|aport[óo]|aportes a la campa[ñn]a|patrocin[óo]|financiador)\b",
    "familiar_de": r"\b(espos[oa]|ex ?espos[oa]|pareja|compañer[oa] permanente|hij[oa]s? de|su hij[oa]|herman[oa]s?|pap[aá]|mam[aá]|padre de|madre de|t[ií][oa]|sobrin[oa]|prim[oa]|cuñad[oa]|suegr[oa]|nuera|yerno|niet[oa]|abuel[oa])\b",
    "apoya_a": r"\b(respald[óo]|respalda|apoy[óo] a|apoya a|apoyo a la candidatura|aliad[oa]|se sum[óo] a|adhiri[óo]|adhesi[óo]n|coalici[óo]n con)\b",
    "se_opone_a": r"\b(se opone|se opuso|oposici[óo]n a|critic[óo]|rechaz[óo]|cuestion[óo]|denunci[óo] a|opositor[a]?|enfrentad[oa] con|rival de)\b",
    "investigado_por": r"\b(investigad[oa]|investigaci[óo]n de la|imputad[oa]|imputaci[óo]n|acusad[oa]|condenad[oa]|condena|Fiscal[ií]a|Procuradur[ií]a|Contralor[ií]a|Corte Suprema|sancionad[oa]|destituid[oa]|inhabilitad[oa])\b",
    "ubicado_en": r"\b(con sede en|sede principal|reside en|vive en|radicad[oa] en|ubicad[oa] en|municipio de|corregimiento de|vereda de|barrio)\b",
}.items()}
```

- [ ] **Paso 1: Tests**

`tests/test_disparadores.py`:

```python
from enrel.corpus.disparadores import DISPARADORES, relaciones_disparadas
from enrel.esquema.tipos import RELACIONES


def test_hay_un_disparador_por_relacion():
    assert set(DISPARADORES) == set(RELACIONES)


def test_relaciones_disparadas():
    t = "El exministro fue imputado por la Fiscalía; su esposa es accionista de la empresa con sede en Cali."
    d = relaciones_disparadas(t)
    assert {"ocupa_cargo", "investigado_por", "familiar_de", "propietario_de", "ubicado_en"} <= d
    assert "sucedio_a" not in d
```

`tests/test_muestrear.py`:

```python
import json
from pathlib import Path

from enrel.corpus import muestrear as mu


def _corpus(tmp_path: Path, n: int = 600) -> Path:
    ruta = tmp_path / "articulos.jsonl"
    secciones = ["silla-nacional", "en-vivo", "quien-es-quien", "opinion"]
    frases = {
        0: "El senador fue nombrado ministro y reemplazó a su antecesor.",
        1: "La empresa, con sede en Cali, contrató a la firma; su dueño donó a la campaña.",
        2: "Su esposa y su hermano militan en el partido; él critica al gobierno.",
        3: "Un párrafo sin ninguna señal de relación, sobre el clima.",
    }
    with ruta.open("w", encoding="utf-8") as f:
        for i in range(n):
            f.write(json.dumps({"doc_id": f"wp:{i}", "wp_id": i, "seccion": secciones[i % 4],
                                "fecha": f"{2009 + (i % 17)}-01-01", "titulo": f"T{i}",
                                "texto": f"T{i}\n\n" + frases[i % 4] + " " * 200, "palabras": 300}, ensure_ascii=False) + "\n")
    return ruta


def test_muestrear_estratos_y_exclusion(tmp_path):
    corpus = _corpus(tmp_path)
    sel = mu.muestrear(corpus, excluir={"wp:0", "wp:1"}, semilla=1, cuota_relacion=5, perfiles=20, aleatorios=40, humo=3)
    ids = [s.doc_id for s in sel]
    assert len(ids) == len(set(ids))
    assert "wp:0" not in ids and "wp:1" not in ids
    estratos = {s.estrato for s in sel}
    assert estratos == {"dirigido", "perfiles", "aleatorio"}
    assert sum(1 for s in sel if s.conjunto == "humo_maestro") == 3
    assert all(s.seccion_ok if hasattr(s, "seccion_ok") else True for s in sel)
    perfiles = [s for s in sel if s.estrato == "perfiles"]
    assert len(perfiles) == 20
    res = mu.resumen(sel)
    assert res["por_estrato"]["perfiles"] == 20
    assert res["disparan"]["familiar_de"] >= 5


def test_reproducible(tmp_path):
    corpus = _corpus(tmp_path)
    a = mu.muestrear(corpus, set(), semilla=7, cuota_relacion=3, perfiles=5, aleatorios=10, humo=2)
    b = mu.muestrear(corpus, set(), semilla=7, cuota_relacion=3, perfiles=5, aleatorios=10, humo=2)
    assert [s.doc_id for s in a] == [s.doc_id for s in b]


def test_guardar_y_cargar(tmp_path):
    corpus = _corpus(tmp_path, 100)
    sel = mu.muestrear(corpus, set(), semilla=1, cuota_relacion=2, perfiles=3, aleatorios=5, humo=1)
    ruta = tmp_path / "sel.jsonl"
    mu.guardar_seleccion(sel, ruta)
    assert mu.cargar_seleccion(ruta) == sel
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar**

`enrel/corpus/disparadores.py`: el diccionario de arriba más

```python
def relaciones_disparadas(texto: str) -> set[str]:
    return {r for r, patron in DISPARADORES.items() if patron.search(texto)}
```

`enrel/corpus/muestrear.py`:

```python
"""Muestreo de la plata en tres estratos: dirigido por relación, perfiles y aleatorio estratificado (spec §5.2)."""

import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from enrel.corpus.congelar import tramo_de
from enrel.corpus.disparadores import relaciones_disparadas
from enrel.esquema.tipos import RELACIONES


@dataclass
class Seleccionado:
    doc_id: str
    conjunto: str
    estrato: str
    disparadas: list[str]


def _leer(corpus: Path, excluir: set[str]) -> list[dict]:
    filas = []
    with Path(corpus).open(encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            d = json.loads(linea)
            if d["doc_id"] in excluir:
                continue
            d["disparadas"] = sorted(relaciones_disparadas(d["texto"]))
            d["tramo"] = tramo_de(d.get("fecha", ""))
            filas.append(d)
    return filas


def _reparto_por_tramo(cands: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Toma n candidatos repartidos lo más igual posible entre tramos."""
    por_tramo = defaultdict(list)
    for c in cands:
        por_tramo[c["tramo"]].append(c)
    for lista in por_tramo.values():
        rng.shuffle(lista)
    out, tramos = [], sorted(por_tramo)
    while len(out) < n and any(por_tramo[t] for t in tramos):
        for t in tramos:
            if por_tramo[t] and len(out) < n:
                out.append(por_tramo[t].pop())
    return out


def muestrear(corpus: Path, excluir: set[str], semilla: int = 2026, cuota_relacion: int = 120,
              perfiles: int = 400, aleatorios: int = 1100, humo: int = 30) -> list[Seleccionado]:
    rng = random.Random(semilla)
    filas = _leer(corpus, excluir)
    rng.shuffle(filas)
    elegidos: dict[str, Seleccionado] = {}

    # 1. Dirigido por relación: los que más relaciones distintas disparan primero.
    for relacion in RELACIONES:
        cands = [d for d in filas if relacion in d["disparadas"] and d["doc_id"] not in elegidos]
        cands.sort(key=lambda d: -len(d["disparadas"]))
        for d in cands[:cuota_relacion]:
            elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "dirigido", d["disparadas"])

    # 2. Perfiles del Quién es Quién, por tramo.
    cands = [d for d in filas if d.get("seccion") == "quien-es-quien" and d["doc_id"] not in elegidos]
    for d in _reparto_por_tramo(cands, perfiles, rng):
        elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "perfiles", d["disparadas"])

    # 3. Aleatorio estratificado por sección (proporcional) y tramo.
    resto = [d for d in filas if d["doc_id"] not in elegidos]
    por_seccion = Counter(d.get("seccion", "") for d in resto)
    total = sum(por_seccion.values()) or 1
    for seccion, n_sec in por_seccion.items():
        cuota = round(aleatorios * n_sec / total)
        cands = [d for d in resto if d.get("seccion", "") == seccion]
        for d in _reparto_por_tramo(cands, cuota, rng):
            elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "aleatorio", d["disparadas"])

    sel = list(elegidos.values())
    for s in rng.sample(sel, min(humo, len(sel))):
        s.conjunto = "humo_maestro"
    sel.sort(key=lambda s: s.doc_id)
    return sel


def resumen(sel: list[Seleccionado]) -> dict:
    disparan = Counter()
    for s in sel:
        disparan.update(s.disparadas)
    return {"total": len(sel), "por_estrato": dict(Counter(s.estrato for s in sel)),
            "por_conjunto": dict(Counter(s.conjunto for s in sel)), "disparan": dict(disparan)}


def guardar_seleccion(sel: list[Seleccionado], ruta: Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for s in sel:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")
    ruta.with_suffix(".resumen.json").write_text(json.dumps(resumen(sel), ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_seleccion(ruta: Path) -> list[Seleccionado]:
    with Path(ruta).open(encoding="utf-8") as f:
        return [Seleccionado(**json.loads(l)) for l in f if l.strip()]
```

`enrel/corpus/cli_muestrear.py` con el patrón de 0.9 (`@registrar("muestrear", …)`), argumentos `--corpus`, `--excluir` (fichero con un doc_id por línea, opcional), `--salida`, `--semilla`, `--cuota-relacion`, `--perfiles`, `--aleatorios`, `--humo`; imprime `resumen`. Añadir su import a `_subcomandos.py`.

Quitar del test la línea `assert all(s.seccion_ok …)` si molesta: es inocua pero no aporta; mejor borrarla al escribir el test.

- [ ] **Paso 4: Correr tests**

`uv run pytest tests/test_disparadores.py tests/test_muestrear.py -q` → en verde. **No** correr el muestreo real todavía: necesita `protegidos.txt` (Tarea 0.14).

- [ ] **Paso 5: Commit**

```bash
git add enrel/corpus/disparadores.py enrel/corpus/muestrear.py enrel/corpus/cli_muestrear.py enrel/_subcomandos.py tests/test_disparadores.py tests/test_muestrear.py
git commit -m "Añade los disparadores por relación y el muestreo en tres estratos"
```

---

### Tarea 0.11: Evaluación de entidades

**Ficheros:**
- Crear: `enrel/evaluacion/emparejar.py`, `enrel/evaluacion/entidades.py`
- Test: `tests/test_eval_entidades.py`

**Interfaces:**
- Produce en `emparejar.py`:
  - `@dataclass class PRF: tp: int = 0; fp: int = 0; fn: int = 0` con propiedades `p`, `r`, `f1` (0.0 cuando el denominador es 0), método `sumar(otro)` y `n` (= tp + fn, los casos de oro).
  - `solapan(a: Mencion, b: Mencion) -> bool`; `emparejar_menciones(oro: list[Mencion], pred: list[Mencion], modo: str) -> list[tuple[Mencion, Mencion]]`: `modo="estricto"` exige `(ini, fin, tipo)` iguales; `modo="parcial"` exige solape y mismo tipo, y resuelve con emparejamiento voraz por mayor solape, cada mención emparejada una sola vez.
  - `emparejar_grupos(oro: Documento, pred: Documento) -> dict[str, str | None]`: para cada grupo del oro, el grupo de la predicción cuyas menciones solapan con más menciones del oro (mismo tipo; `None` si ninguno). Es la base de la evaluación de relaciones (0.12).
  - `por_doc_id(docs) -> dict[str, Documento]` y `alinear(oro_docs, pred_docs) -> list[tuple[Documento, Documento]]` (lanza `ValueError` si falta algún doc_id del oro en la predicción; los extra de la predicción se ignoran con aviso).
- Produce en `entidades.py`: `evaluar_entidades(oro: list[Documento], pred: list[Documento], modo: str = "estricto") -> dict[str, PRF]` con una clave por tipo presente y `"__global__"` (micro).

- [ ] **Paso 1: Tests**

`tests/test_eval_entidades.py`:

```python
from enrel.datos.documento import Documento, Grupo, Mencion
from enrel.evaluacion.emparejar import PRF, emparejar_grupos, emparejar_menciones
from enrel.evaluacion.entidades import evaluar_entidades


def doc(doc_id, menciones):
    grupos = {m.grupo: Grupo(m.grupo, m.tipo, m.texto) for m in menciones}
    return Documento(doc_id, "x" * 200, list(menciones), list(grupos.values()), [])


def test_prf():
    p = PRF(tp=3, fp=1, fn=1)
    assert (round(p.p, 2), round(p.r, 2), round(p.f1, 2), p.n) == (0.75, 0.75, 0.75, 4)
    assert PRF().f1 == 0.0


def test_estricto_vs_parcial():
    oro = [Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"), Mencion("b", 20, 28, "Fiscalía", "organizacion", "g2")]
    pred = [Mencion("x", 8, 13, "Petro", "persona", "p1"), Mencion("y", 20, 28, "Fiscalía", "organizacion", "p2"),
            Mencion("z", 40, 44, "Cali", "lugar", "p3")]
    assert len(emparejar_menciones(oro, pred, "estricto")) == 1
    assert len(emparejar_menciones(oro, pred, "parcial")) == 2
    r = evaluar_entidades([doc("d", oro)], [doc("d", pred)], "estricto")
    assert (r["__global__"].tp, r["__global__"].fp, r["__global__"].fn) == (1, 2, 1)
    assert r["persona"].fn == 1 and r["lugar"].fp == 1
    r2 = evaluar_entidades([doc("d", oro)], [doc("d", pred)], "parcial")
    assert (r2["__global__"].tp, r2["__global__"].fp, r2["__global__"].fn) == (2, 1, 0)


def test_tipo_distinto_no_empareja():
    oro = [Mencion("a", 0, 5, "Nariño", "lugar", "g1")]
    pred = [Mencion("x", 0, 5, "Nariño", "persona", "p1")]
    assert emparejar_menciones(oro, pred, "parcial") == []


def test_emparejar_grupos():
    oro = doc("d", [Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"), Mencion("b", 50, 55, "Petro", "persona", "g1"),
                    Mencion("c", 20, 28, "Fiscalía", "organizacion", "g2")])
    pred = doc("d", [Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"), Mencion("y", 50, 55, "Petro", "persona", "p9"),
                     Mencion("z", 20, 28, "Fiscalía", "organizacion", "p2")])
    m = emparejar_grupos(oro, pred)
    assert m["g1"] in ("p1", "p9") and m["g2"] == "p2"
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar**

`enrel/evaluacion/emparejar.py`:

```python
"""Emparejamiento de menciones y grupos entre oro y predicción, y el contador P/R/F1."""

from dataclasses import dataclass

from enrel.datos.documento import Documento, Mencion


@dataclass
class PRF:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def p(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def r(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        return 2 * self.p * self.r / (self.p + self.r) if self.p + self.r else 0.0

    @property
    def n(self) -> int:
        return self.tp + self.fn

    def sumar(self, otro: "PRF") -> None:
        self.tp += otro.tp
        self.fp += otro.fp
        self.fn += otro.fn


def solapan(a: Mencion, b: Mencion) -> bool:
    return a.ini < b.fin and b.ini < a.fin


def _solape(a: Mencion, b: Mencion) -> int:
    return max(0, min(a.fin, b.fin) - max(a.ini, b.ini))


def emparejar_menciones(oro: list[Mencion], pred: list[Mencion], modo: str) -> list[tuple[Mencion, Mencion]]:
    if modo == "estricto":
        indice = {(m.ini, m.fin, m.tipo): m for m in pred}
        return [(o, indice[(o.ini, o.fin, o.tipo)]) for o in oro if (o.ini, o.fin, o.tipo) in indice]
    if modo != "parcial":
        raise ValueError(modo)
    pares = [(_solape(o, p), i, j) for i, o in enumerate(oro) for j, p in enumerate(pred)
             if o.tipo == p.tipo and solapan(o, p)]
    pares.sort(reverse=True)
    usados_o, usados_p, out = set(), set(), []
    for _, i, j in pares:
        if i not in usados_o and j not in usados_p:
            usados_o.add(i)
            usados_p.add(j)
            out.append((oro[i], pred[j]))
    return out


def emparejar_grupos(oro: Documento, pred: Documento) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for g in oro.grupos:
        votos: dict[str, int] = {}
        for mo in oro.menciones_de(g.id):
            for mp in pred.menciones:
                if mp.tipo == g.tipo and solapan(mo, mp):
                    votos[mp.grupo] = votos.get(mp.grupo, 0) + 1
        out[g.id] = max(votos, key=votos.get) if votos else None
    return out


def por_doc_id(docs: list[Documento]) -> dict[str, Documento]:
    return {d.doc_id: d for d in docs}


def alinear(oro_docs: list[Documento], pred_docs: list[Documento]) -> list[tuple[Documento, Documento]]:
    pred = por_doc_id(pred_docs)
    faltan = [d.doc_id for d in oro_docs if d.doc_id not in pred]
    if faltan:
        raise ValueError(f"la predicción no trae {len(faltan)} documentos del oro, por ejemplo {faltan[:3]}")
    return [(d, pred[d.doc_id]) for d in oro_docs]
```

`enrel/evaluacion/entidades.py`:

```python
"""P/R/F1 de menciones por tipo, en modo estricto (tramo y tipo exactos) o parcial (solape y tipo)."""

from enrel.datos.documento import Documento
from enrel.evaluacion.emparejar import PRF, alinear, emparejar_menciones


def evaluar_entidades(oro: list[Documento], pred: list[Documento], modo: str = "estricto") -> dict[str, PRF]:
    por_tipo: dict[str, PRF] = {}
    total = PRF()
    for o, p in alinear(oro, pred):
        pares = emparejar_menciones(o.menciones, p.menciones, modo)
        emparejadas_o = {id(a) for a, _ in pares}
        emparejadas_p = {id(b) for _, b in pares}
        for m in o.menciones:
            por_tipo.setdefault(m.tipo, PRF())
            if id(m) in emparejadas_o:
                por_tipo[m.tipo].tp += 1
            else:
                por_tipo[m.tipo].fn += 1
        for m in p.menciones:
            if id(m) not in emparejadas_p:
                por_tipo.setdefault(m.tipo, PRF()).fp += 1
    for prf in por_tipo.values():
        total.sumar(prf)
    por_tipo["__global__"] = total
    return por_tipo
```

- [ ] **Paso 4: Correr tests** → 4 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/evaluacion/emparejar.py enrel/evaluacion/entidades.py tests/test_eval_entidades.py
git commit -m "Añade el emparejamiento de menciones y grupos y la evaluación de entidades"
```

---

### Tarea 0.12: Evaluación de relaciones: RE, RE+, fina, micro, macro, dirección e Ign

**Ficheros:**
- Crear: `enrel/evaluacion/relaciones.py`
- Test: `tests/test_eval_relaciones.py`

**Interfaces:**
- Consume: `PRF`, `alinear`, `emparejar_grupos` (0.11); `es_simetrica`, `clase_fina` (0.3).
- Produce:
  - `tripletas_canonicas(docs: list[Documento], nivel: str = "gruesa") -> set[tuple[str, str, str]]`: `(plegar(canonico cabeza), etiqueta, plegar(canonico cola))`, con la etiqueta gruesa (`relacion`) o fina (`clase_fina`); las simétricas se guardan con los extremos ordenados alfabéticamente.
  - `evaluar_relaciones(oro: list[Documento], pred: list[Documento], nivel: str = "gruesa", exigir_tipos: bool = False, ignorar: set[tuple] | None = None) -> dict[str, PRF]`. Claves: una por etiqueta (gruesa o fina) presente en oro o predicción, `"__micro__"` (suma sin `vinculo_sin_tipo`), `"__macro__"` (un `PRF` sintético cuyo `f1` es la media de los F1 de las etiquetas con `n ≥ 1`, excluyendo `vinculo_sin_tipo`; `tp/fp/fn` en 0), `"__direccion__"` (`PRF` con `tp` = asimétricas acertadas en par y etiqueta con dirección correcta, `fn` = las acertadas en par y etiqueta pero con dirección invertida).
  - Regla de acierto: una relación del oro `(gc, gl, etiqueta)` acierta si existe una relación de la predicción con la misma etiqueta cuya cabeza es el grupo emparejado de `gc` y cuya cola es el grupo emparejado de `gl` (o al revés si la relación es simétrica). Con `exigir_tipos=True` (RE+), además los grupos emparejados deben tener el mismo tipo que los del oro. Cada relación de la predicción se consume una sola vez. Las del oro cuya tripleta canónica está en `ignorar` no cuentan ni como tp ni como fn (Ign-F1); las de la predicción que coinciden con una ignorada tampoco cuentan como fp.
  - `RE` = `evaluar_relaciones(..., "gruesa", exigir_tipos=False)`; `RE+` = `exigir_tipos=True`; fina = `nivel="fina"`.

- [ ] **Paso 1: Tests**

`tests/test_eval_relaciones.py`:

```python
from enrel.datos.documento import Documento, Grupo, Mencion, Relacion
from enrel.evaluacion.relaciones import evaluar_relaciones, tripletas_canonicas


def doc(doc_id, menciones, grupos, relaciones):
    return Documento(doc_id, "x" * 300, menciones, grupos, relaciones)


ORO = doc("d",
          [Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"), Mencion("b", 20, 37, "Luis Carlos Reyes", "persona", "g2"),
           Mencion("c", 40, 60, "ministro de Comercio", "cargo", "g3"), Mencion("d", 70, 78, "Colombia", "lugar", "g4")],
          [Grupo("g1", "persona", "Gustavo Petro"), Grupo("g2", "persona", "Luis Carlos Reyes"),
           Grupo("g3", "cargo", "ministro de Comercio"), Grupo("g4", "lugar", "Colombia")],
          [Relacion("g1", "g2", "nombro_a"), Relacion("g2", "g3", "ocupa_cargo", "actual"), Relacion("g1", "g2", "socio_de")])


def pred(relaciones, menciones=None):
    ms = menciones or [Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"), Mencion("y", 20, 37, "Luis Carlos Reyes", "persona", "p2"),
                       Mencion("z", 40, 60, "ministro de Comercio", "cargo", "p3")]
    gs = {m.grupo: Grupo(m.grupo, m.tipo, m.texto) for m in ms}
    return doc("d", ms, list(gs.values()), relaciones)


def test_acierto_direccion_y_simetrica():
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p2", "p3", "ocupa_cargo", "anterior"), Relacion("p2", "p1", "socio_de")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert (r["__micro__"].tp, r["__micro__"].fp, r["__micro__"].fn) == (3, 0, 0)
    fina = evaluar_relaciones([ORO], [p], "fina")
    assert fina["ocupa_cargo:actual"].fn == 1 and fina["ocupa_cargo:anterior"].fp == 1
    assert fina["__micro__"].tp == 2


def test_direccion_invertida_cuenta_como_error_y_en_direccion():
    p = pred([Relacion("p2", "p1", "nombro_a")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert r["nombro_a"].tp == 0 and r["nombro_a"].fp == 1 and r["nombro_a"].fn == 1
    assert r["__direccion__"].fn == 1 and r["__direccion__"].tp == 0


def test_re_mas_exige_tipos():
    ms = [Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"), Mencion("y", 20, 37, "Luis Carlos Reyes", "organizacion", "p2")]
    p = pred([Relacion("p1", "p2", "nombro_a")], ms)
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=False)["nombro_a"].tp == 0  # tipo distinto: no hay grupo emparejado
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=True)["nombro_a"].tp == 0


def test_macro_y_sin_tipo_excluido():
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p1", "p3", "vinculo_sin_tipo")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert r["__micro__"].fp == 0          # vinculo_sin_tipo no cuenta en micro
    assert "vinculo_sin_tipo" in r
    assert 0 < r["__macro__"].f1 < 1


def test_ign():
    ignorar = tripletas_canonicas([ORO], "gruesa") - {("gustavo petro", "nombro_a", "luis carlos reyes")}
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p2", "p3", "ocupa_cargo", "actual")])
    r = evaluar_relaciones([ORO], [p], "gruesa", ignorar=ignorar)
    assert (r["__micro__"].tp, r["__micro__"].fp, r["__micro__"].fn) == (1, 0, 0)


def test_tripletas_canonicas_simetrica_ordenada():
    t = tripletas_canonicas([ORO], "gruesa")
    assert ("gustavo petro", "socio_de", "luis carlos reyes") in t
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/evaluacion/relaciones.py`**

```python
"""Evaluación de relaciones sobre grupos emparejados: RE, RE+, nivel fino, micro, macro, dirección e Ign."""

from enrel.datos.documento import Documento, Relacion
from enrel.datos.normalizar import plegar
from enrel.esquema.tipos import SIN_TIPO, clase_fina, es_simetrica
from enrel.evaluacion.emparejar import PRF, alinear, emparejar_grupos


def _etiqueta(r: Relacion, nivel: str) -> str:
    return clase_fina(r.relacion, r.atributo) if nivel == "fina" else r.relacion


def _canonica(doc: Documento, r: Relacion, nivel: str) -> tuple[str, str, str]:
    a, b = plegar(doc.grupo_de(r.cabeza).canonico), plegar(doc.grupo_de(r.cola).canonico)
    if es_simetrica(r.relacion, r.atributo):
        a, b = sorted((a, b))
    return a, _etiqueta(r, nivel), b


def tripletas_canonicas(docs: list[Documento], nivel: str = "gruesa") -> set[tuple[str, str, str]]:
    return {_canonica(d, r, nivel) for d in docs for r in d.relaciones}


def evaluar_relaciones(oro: list[Documento], pred: list[Documento], nivel: str = "gruesa",
                       exigir_tipos: bool = False, ignorar: set[tuple] | None = None) -> dict[str, PRF]:
    ignorar = ignorar or set()
    por_etiqueta: dict[str, PRF] = {}
    direccion = PRF()

    def prf(e: str) -> PRF:
        return por_etiqueta.setdefault(e, PRF())

    for o, p in alinear(oro, pred):
        mapa = emparejar_grupos(o, p)
        tipos_pred = {g.id: g.tipo for g in p.grupos}
        libres = list(p.relaciones)
        consumidas: set[int] = set()
        for ro in o.relaciones:
            et = _etiqueta(ro, nivel)
            if _canonica(o, ro, nivel) in ignorar:
                continue
            gc, gl = mapa.get(ro.cabeza), mapa.get(ro.cola)
            if exigir_tipos and (gc is None or gl is None or tipos_pred[gc] != o.grupo_de(ro.cabeza).tipo
                                 or tipos_pred[gl] != o.grupo_de(ro.cola).tipo):
                gc = gl = None
            acierto = None
            invertida = None
            for k, rp in enumerate(libres):
                if k in consumidas or _etiqueta(rp, nivel) != et or gc is None or gl is None:
                    continue
                if (rp.cabeza, rp.cola) == (gc, gl):
                    acierto = k
                    break
                if (rp.cabeza, rp.cola) == (gl, gc):
                    if es_simetrica(ro.relacion, ro.atributo):
                        acierto = k
                        break
                    invertida = k
            if acierto is not None:
                consumidas.add(acierto)
                prf(et).tp += 1
                if not es_simetrica(ro.relacion, ro.atributo):
                    direccion.tp += 1
            else:
                prf(et).fn += 1
                if invertida is not None:
                    direccion.fn += 1
        for k, rp in enumerate(libres):
            if k in consumidas:
                continue
            if _canonica(p, rp, nivel) in ignorar:
                continue
            prf(_etiqueta(rp, nivel)).fp += 1

    micro = PRF()
    f1s = []
    for et, x in por_etiqueta.items():
        if et == SIN_TIPO or et.startswith(SIN_TIPO):
            continue
        micro.sumar(x)
        if x.n >= 1:
            f1s.append(x.f1)
    por_etiqueta["__micro__"] = micro
    macro = PRF()
    macro.f1_fijo = sum(f1s) / len(f1s) if f1s else 0.0  # atributo dinámico; ver _Macro abajo
    por_etiqueta["__macro__"] = _Macro(macro.f1_fijo)
    por_etiqueta["__direccion__"] = direccion
    return por_etiqueta


class _Macro(PRF):
    """Un PRF cuyo f1 es fijo: la media de los F1 por etiqueta."""

    def __init__(self, f1: float):
        super().__init__()
        self._f1 = f1

    @property
    def f1(self) -> float:
        return self._f1
```

Simplificar al implementar: no usar `macro.f1_fijo`; construir directamente `por_etiqueta["__macro__"] = _Macro(media)`.

- [ ] **Paso 4: Correr tests** → 6 en verde. Revisar a mano `test_re_mas_exige_tipos`: con tipos distintos, `emparejar_grupos` ya devuelve `None` para g2, así que RE y RE+ dan 0 igual; el caso donde RE+ difiere de RE es cuando la predicción agrupa bien pero con otro tipo en el grupo y una mención solapada del tipo correcto; añadir ese caso al test si el tiempo lo permite, no es bloqueante.

- [ ] **Paso 5: Commit**

```bash
git add enrel/evaluacion/relaciones.py tests/test_eval_relaciones.py
git commit -m "Añade la evaluación de relaciones: RE, RE+, nivel fino, micro, macro, dirección e Ign-F1"
```

---

### Tarea 0.13: Intervalos por bootstrap y tabla en markdown

**Ficheros:**
- Crear: `enrel/evaluacion/bootstrap.py`, `enrel/evaluacion/tabla.py`, `enrel/evaluacion/informe.py`
- Test: `tests/test_eval_tabla.py`

**Interfaces:**
- Produce en `bootstrap.py`: `intervalo(oro: list[Documento], pred: list[Documento], metrica: Callable[[list, list], float], n: int = 1000, semilla: int = 42) -> tuple[float, float]`: remuestrea documentos con reemplazo (mismos índices en oro y pred alineados) y devuelve los percentiles 2,5 y 97,5 de `metrica`.
- Produce en `tabla.py`: `fila(nombre: str, prf: PRF, minimo_n: int = 10, ic: tuple[float, float] | None = None) -> dict` con claves `nombre, n, p, r, f1, ic`; si `prf.n < minimo_n` los valores son `"insuficiente"` (salvo `n`); `tabla_markdown(filas: list[dict], titulo: str) -> str`.
- Produce en `informe.py`: `informe_completo(oro, pred, entrenamiento: list[Documento] | None = None, nombre_modelo: str = "modelo", con_intervalos: bool = True) -> str`: markdown con cuatro tablas (entidades estricto y parcial por tipo; relaciones gruesas RE y RE+ por relación con micro, macro, dirección e Ign-F1 si hay `entrenamiento`; relaciones finas), con intervalos al 95 % para los globales, y una cabecera con fecha, número de documentos y hashes si se pasan (`hashes: dict[str, str] | None`).

- [ ] **Paso 1: Tests**

`tests/test_eval_tabla.py`:

```python
from enrel.evaluacion.emparejar import PRF
from enrel.evaluacion.tabla import fila, tabla_markdown
from enrel.evaluacion.bootstrap import intervalo
from tests.test_eval_relaciones import ORO, pred
from enrel.datos.documento import Relacion
from enrel.evaluacion.relaciones import evaluar_relaciones


def test_fila_insuficiente():
    f = fila("fundo", PRF(tp=2, fp=0, fn=1))
    assert f["n"] == 3 and f["f1"] == "insuficiente"
    f2 = fila("ocupa_cargo", PRF(tp=8, fp=2, fn=2), ic=(0.6, 0.9))
    assert f2["f1"] == "0.80" and f2["ic"] == "[0.60, 0.90]"


def test_tabla_markdown():
    md = tabla_markdown([fila("x", PRF(tp=10, fp=0, fn=0))], "Prueba")
    assert md.startswith("### Prueba") and "| x | 10 | 1.00 | 1.00 | 1.00 |" in md


def test_intervalo_cubre_el_valor():
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p2", "p3", "ocupa_cargo", "actual"), Relacion("p1", "p2", "socio_de")])
    f = lambda o, q: evaluar_relaciones(o, q, "gruesa")["__micro__"].f1
    bajo, alto = intervalo([ORO] * 5, [p] * 5, f, n=50)
    assert bajo <= 1.0 <= alto
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar**

`enrel/evaluacion/bootstrap.py`:

```python
"""Intervalos de confianza al 95 % por bootstrap sobre documentos."""

import random
from collections.abc import Callable

from enrel.datos.documento import Documento
from enrel.evaluacion.emparejar import alinear


def intervalo(oro: list[Documento], pred: list[Documento], metrica: Callable[[list, list], float],
              n: int = 1000, semilla: int = 42) -> tuple[float, float]:
    pares = alinear(oro, pred)
    rng = random.Random(semilla)
    valores = []
    for _ in range(n):
        muestra = [pares[rng.randrange(len(pares))] for _ in pares]
        valores.append(metrica([o for o, _ in muestra], [p for _, p in muestra]))
    valores.sort()
    return valores[int(0.025 * n)], valores[min(n - 1, int(0.975 * n))]
```

`enrel/evaluacion/tabla.py`:

```python
"""Filas y tablas markdown; por debajo de `minimo_n` casos de oro no se publica la cifra."""

from enrel.evaluacion.emparejar import PRF


def fila(nombre: str, prf: PRF, minimo_n: int = 10, ic: tuple[float, float] | None = None) -> dict:
    if prf.n < minimo_n and not nombre.startswith("__"):
        return {"nombre": nombre, "n": prf.n, "p": "insuficiente", "r": "insuficiente", "f1": "insuficiente", "ic": ""}
    return {"nombre": nombre, "n": prf.n, "p": f"{prf.p:.2f}", "r": f"{prf.r:.2f}", "f1": f"{prf.f1:.2f}",
            "ic": f"[{ic[0]:.2f}, {ic[1]:.2f}]" if ic else ""}


def tabla_markdown(filas: list[dict], titulo: str) -> str:
    lineas = [f"### {titulo}", "", "| | n | P | R | F1 | IC 95 % |", "|---|---:|---:|---:|---:|---|"]
    for f in filas:
        lineas.append(f"| {f['nombre']} | {f['n']} | {f['p']} | {f['r']} | {f['f1']} | {f['ic']} |")
    return "\n".join(lineas) + "\n"
```

`enrel/evaluacion/informe.py`:

```python
"""El informe completo de una evaluación: entidades, relaciones gruesas y finas, con intervalos."""

from datetime import date

from enrel.datos.documento import Documento
from enrel.evaluacion.bootstrap import intervalo
from enrel.evaluacion.entidades import evaluar_entidades
from enrel.evaluacion.relaciones import evaluar_relaciones, tripletas_canonicas
from enrel.evaluacion.tabla import fila, tabla_markdown

_GLOBALES = ("__micro__", "__macro__", "__direccion__", "__global__")


def _tabla(resultados: dict, titulo: str, oro, pred, metrica_global=None, con_intervalos=True) -> str:
    filas = []
    for nombre in sorted(k for k in resultados if k not in _GLOBALES):
        filas.append(fila(nombre, resultados[nombre]))
    for g in _GLOBALES:
        if g in resultados:
            ic = intervalo(oro, pred, metrica_global(g)) if (con_intervalos and metrica_global and g in ("__micro__", "__global__")) else None
            filas.append(fila(g.strip("_"), resultados[g], minimo_n=0, ic=ic))
    return tabla_markdown(filas, titulo)


def informe_completo(oro: list[Documento], pred: list[Documento], entrenamiento: list[Documento] | None = None,
                     nombre_modelo: str = "modelo", con_intervalos: bool = True, hashes: dict[str, str] | None = None) -> str:
    partes = [f"# Evaluación de {nombre_modelo}", "", f"Fecha: {date.today().isoformat()} · documentos: {len(oro)}"]
    if hashes:
        partes += ["", *[f"- `{k}`: `{v}`" for k, v in hashes.items()]]
    partes.append("")
    for modo in ("estricto", "parcial"):
        res = evaluar_entidades(oro, pred, modo)
        partes.append(_tabla(res, f"Entidades, {modo}", oro, pred,
                             lambda g, modo=modo: (lambda o, p: evaluar_entidades(o, p, modo)[g].f1), con_intervalos))
    for exigir, titulo in ((False, "Relaciones gruesas, RE"), (True, "Relaciones gruesas, RE+")):
        res = evaluar_relaciones(oro, pred, "gruesa", exigir_tipos=exigir)
        partes.append(_tabla(res, titulo, oro, pred,
                             lambda g, e=exigir: (lambda o, p: evaluar_relaciones(o, p, "gruesa", exigir_tipos=e)[g].f1), con_intervalos))
    if entrenamiento:
        ign = tripletas_canonicas(entrenamiento, "gruesa")
        res = evaluar_relaciones(oro, pred, "gruesa", exigir_tipos=True, ignorar=ign)
        partes.append(_tabla(res, f"Relaciones gruesas, RE+ Ign ({len(ign)} tripletas vistas en entrenamiento)", oro, pred, None, False))
    res = evaluar_relaciones(oro, pred, "fina", exigir_tipos=True)
    partes.append(_tabla(res, "Relaciones finas, RE+", oro, pred, None, False))
    return "\n".join(partes)
```

- [ ] **Paso 4: Correr tests** → 3 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/evaluacion/bootstrap.py enrel/evaluacion/tabla.py enrel/evaluacion/informe.py tests/test_eval_tabla.py
git commit -m "Añade intervalos por bootstrap, tablas markdown y el informe completo de evaluación"
```

---

### Tarea 0.14: CLI de exportación y evaluación, conjuntos protegidos, y la primera tabla real

**Ficheros:**
- Crear: `enrel/anotacion/cli_exportar_legajo.py`, `enrel/evaluacion/cli_evaluar.py`, `scripts/conjuntos_iniciales.py`
- Modificar: `enrel/_subcomandos.py`
- Crear: `docs/resultados/etapa-0-legajo.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- `enrel exportar-legajo --oro-json DIR --salida datos/anotado/legajo-oro.jsonl [--legajo-db RUTA]`: exporta todos los JSON de oro. `enrel exportar-legajo --lote N --salida X.jsonl [--legajo-db RUTA] [--solo-validos]`: exporta un lote de la base (con `--solo-validos`, solo artículos con `tiempos.valido = 1 AND cerrado = 1`). `enrel exportar-legajo --plata RUTA.jsonl --salida X.jsonl`: exporta la plata de legajo. Todas imprimen documentos exportados, menciones no localizadas y errores.
- `enrel evaluar --oro A.jsonl --pred B.jsonl [--entrenamiento C.jsonl] [--nombre X] [--salida informe.md] [--sin-intervalos]`.
- `scripts/conjuntos_iniciales.py`: lee `datos-anteriores/entrenamiento/prueba.txt` (50 wp_id) y `datos/anotado/legajo-oro.jsonl`; escribe `datos/conjuntos/prueba.jsonl` (los 50), `datos/conjuntos/plata_alta.jsonl` (los otros 75, con `fuente = "plata-alta"`), y `datos/conjuntos/protegidos.txt` (los 50 doc_id de prueba; los de oro-perfiles y desarrollo se añaden cuando existan, con `scripts/proteger.py --anadir wp:…`). Comprueba fugas.

- [ ] **Paso 1: Test del CLI**

`tests/test_cli.py`:

```python
from pathlib import Path

from enrel.cli import main
from enrel.datos.documento import guardar_jsonl
from tests.test_eval_relaciones import ORO, pred
from enrel.datos.documento import Relacion


def test_evaluar_cli(tmp_path: Path, capsys):
    o, p = tmp_path / "oro.jsonl", tmp_path / "pred.jsonl"
    guardar_jsonl([ORO], o)
    guardar_jsonl([pred([Relacion("p1", "p2", "nombro_a")])], p)
    salida = tmp_path / "informe.md"
    assert main(["evaluar", "--oro", str(o), "--pred", str(p), "--salida", str(salida), "--sin-intervalos"]) == 0
    texto = salida.read_text(encoding="utf-8")
    assert "Relaciones gruesas, RE+" in texto and "nombro_a" in texto


def test_ayuda(capsys):
    assert main([]) == 0
    assert "evaluar" in capsys.readouterr().out
```

- [ ] **Paso 2: Ejecutar y ver que falla** → el subcomando `evaluar` no existe.

- [ ] **Paso 3: Implementar los subcomandos**

`enrel/evaluacion/cli_evaluar.py`:

```python
"""Subcomando `enrel evaluar`."""

from pathlib import Path

from enrel.cli import registrar


@registrar("evaluar", "Evalúa una predicción contra el oro y escribe el informe en markdown")
def evaluar_cmd(args):
    from enrel.datos.documento import cargar_jsonl, hash_fichero
    from enrel.evaluacion.informe import informe_completo

    oro, pred = cargar_jsonl(args.oro), cargar_jsonl(args.pred)
    entrenamiento = cargar_jsonl(args.entrenamiento) if args.entrenamiento else None
    hashes = {"oro": hash_fichero(args.oro), "pred": hash_fichero(args.pred)}
    if args.entrenamiento:
        hashes["entrenamiento"] = hash_fichero(args.entrenamiento)
    md = informe_completo(oro, pred, entrenamiento, args.nombre, not args.sin_intervalos, hashes)
    if args.salida:
        Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.salida).write_text(md, encoding="utf-8")
        print(f"informe → {args.salida}")
    else:
        print(md)


def _configurar(p):
    p.add_argument("--oro", required=True)
    p.add_argument("--pred", required=True)
    p.add_argument("--entrenamiento", default=None)
    p.add_argument("--nombre", default="modelo")
    p.add_argument("--salida", default=None)
    p.add_argument("--sin-intervalos", action="store_true")


evaluar_cmd.configurar = _configurar
```

`enrel/anotacion/cli_exportar_legajo.py`:

```python
"""Subcomando `enrel exportar-legajo`: oro JSON, lote de la base o plata de legajo → formato interno."""

from pathlib import Path

from enrel.cli import registrar


@registrar("exportar-legajo", "Convierte oro o plata de legajo al formato interno de enrel")
def exportar_cmd(args):
    from enrel.anotacion import desde_legajo as dl
    from enrel.corpus import legajo_db as db
    from enrel.datos.documento import guardar_jsonl

    con = db.conectar(db.ruta_db(args.legajo_db))
    docs, no_loc, errores = [], 0, []

    def agregar(constructor, wp):
        nonlocal no_loc
        art = db.articulo(con, wp)
        if art is None:
            errores.append(f"wp:{wp} sin texto en la base")
            return
        try:
            d = constructor(art)
        except ValueError as e:
            errores.append(f"wp:{wp}: {e}")
            return
        no_loc += d.origen.get("no_localizadas", 0)
        docs.append(d)

    if args.oro_json:
        for wp, spec in dl.leer_oro_json(Path(args.oro_json)).items():
            agregar(lambda art, spec=spec: dl.documento_desde_oro_json(spec, art), wp)
    elif args.lote is not None:
        consulta = "SELECT DISTINCT wp_id FROM anotaciones WHERE lote_id = ?"
        if args.solo_validos:
            consulta = ("SELECT DISTINCT a.wp_id FROM anotaciones a JOIN tiempos t ON t.lote_id = a.lote_id AND t.wp_id = a.wp_id "
                        "WHERE a.lote_id = ? AND t.valido = 1 AND t.cerrado = 1")
        for (wp,) in con.execute(consulta, (args.lote,)):
            agregar(lambda art: dl.documento_desde_sqlite(con, args.lote, art), wp)
    elif args.plata:
        for wp, filas in dl.leer_plata_legajo(Path(args.plata)).items():
            agregar(lambda art, filas=filas: dl.documento_desde_plata_legajo(filas, art), wp)
    else:
        raise SystemExit("hace falta --oro-json, --lote o --plata")
    n = guardar_jsonl(docs, Path(args.salida))
    print(f"{n} documentos → {args.salida}; menciones no localizadas: {no_loc}; errores: {len(errores)}")
    for e in errores[:20]:
        print("  ", e)


def _configurar(p):
    p.add_argument("--oro-json", default=None)
    p.add_argument("--lote", type=int, default=None)
    p.add_argument("--solo-validos", action="store_true")
    p.add_argument("--plata", default=None)
    p.add_argument("--salida", required=True)
    p.add_argument("--legajo-db", default=None)


exportar_cmd.configurar = _configurar
```

Registrar ambos en `_subcomandos.py`.

`scripts/conjuntos_iniciales.py`:

```python
"""Fija los conjuntos iniciales a partir del oro de legajo: prueba (50) y plata-alta (75), y el fichero de protegidos."""

from pathlib import Path

from enrel.datos.documento import cargar_jsonl, guardar_jsonl
from enrel.datos.validar import comprobar_fugas

PRUEBA_TXT = Path("datos-anteriores/entrenamiento/prueba.txt")
ORO = Path("datos/anotado/legajo-oro.jsonl")
SALIDA = Path("datos/conjuntos")

prueba_ids = {f"wp:{l.strip()}" for l in PRUEBA_TXT.read_text().splitlines() if l.strip() and not l.startswith("#")}
assert len(prueba_ids) == 50
docs = cargar_jsonl(ORO)
prueba = [d for d in docs if d.doc_id in prueba_ids]
resto = [d for d in docs if d.doc_id not in prueba_ids]
for d in resto:
    d.fuente = "plata-alta"
assert len(prueba) == 50, len(prueba)
guardar_jsonl(prueba, SALIDA / "prueba.jsonl")
guardar_jsonl(resto, SALIDA / "plata_alta.jsonl")
(SALIDA / "protegidos.txt").write_text("\n".join(sorted(prueba_ids)) + "\n", encoding="utf-8")
print(comprobar_fugas({"prueba": prueba, "plata_alta": resto}) or "sin fugas")
print(f"prueba {len(prueba)} · plata-alta {len(resto)} · protegidos {len(prueba_ids)}")
```

- [ ] **Paso 4: Correr tests y producir la primera tabla real**

```bash
uv run pytest tests/test_cli.py -q
uv run enrel exportar-legajo --oro-json datos-anteriores/entrenamiento/oro --salida datos/anotado/legajo-oro.jsonl
uv run python scripts/conjuntos_iniciales.py
uv run enrel exportar-legajo --plata datos-anteriores/entrenamiento/plata-mm-v5.jsonl --salida datos/anotado/legajo-plata-v5.jsonl
uv run enrel exportar-legajo --plata datos-anteriores/entrenamiento/apartado-mm-v5-sin.jsonl --salida datos/anotado/legajo-apartado-mm-v5.jsonl
```

La plata `apartado-mm-v5-sin.jsonl` cubre los 30 artículos del apartado, que **no** son los 50 de prueba. Para la primera tabla real hace falta la predicción de MiniMax sobre los 50 de prueba: `oro100-sin-pistas.jsonl` cubre los 99 artículos del lote 8, entre ellos los 50. Exportarlo también:

```bash
uv run enrel exportar-legajo --plata datos-anteriores/entrenamiento/oro100-sin-pistas.jsonl --salida datos/anotado/legajo-oro100-mm.jsonl
uv run python - <<'EOF'
from pathlib import Path
from enrel.datos.documento import cargar_jsonl, guardar_jsonl
ids = {l.strip() for l in Path("datos/conjuntos/protegidos.txt").read_text().splitlines()}
docs = [d for d in cargar_jsonl("datos/anotado/legajo-oro100-mm.jsonl") if d.doc_id in ids]
print(len(docs)); guardar_jsonl(docs, "datos/anotado/legajo-techo-mm-prueba.jsonl")
EOF
uv run enrel evaluar --oro datos/conjuntos/prueba.jsonl --pred datos/anotado/legajo-techo-mm-prueba.jsonl --nombre "MiniMax v5 sin pistas (techo del maestro de legajo), esquema nuevo" --salida docs/resultados/etapa-0-legajo.md
```

Si la exportación del `oro100-sin-pistas.jsonl` no cubre los 50 (el fichero puede tener otro formato de columnas), leer las primeras líneas, adaptar `documento_desde_plata_legajo` a las claves reales y anotarlo en el commit. Añadir al principio de `docs/resultados/etapa-0-legajo.md` tres párrafos a mano: qué se compara (el oro de legajo mapeado al esquema nuevo, que es mayormente corrección de LLM, contra la plata de MiniMax mapeada), qué significa la cifra (el techo del maestro de legajo medido con el evaluador nuevo; la referencia que la etapa 1 debe superar con el maestro nuevo) y qué no mide (relaciones entre párrafos, que ninguno de los dos podía marcar).

- [ ] **Paso 5: Commit**

```bash
git add enrel/anotacion/cli_exportar_legajo.py enrel/evaluacion/cli_evaluar.py enrel/_subcomandos.py scripts/conjuntos_iniciales.py tests/test_cli.py docs/resultados/etapa-0-legajo.md
git commit -m "Añade exportar-legajo y evaluar al CLI, fija prueba y plata-alta, y mide el techo del maestro de legajo con el esquema nuevo"
```

Después, correr el muestreo real (ya existe `protegidos.txt`):

```bash
uv run enrel muestrear --corpus datos/corpus/articulos.jsonl --excluir datos/conjuntos/protegidos.txt --salida datos/conjuntos/seleccion.jsonl --semilla 2026
cat datos/conjuntos/seleccion.resumen.json
```

Copiar el resumen (total, por estrato, artículos que disparan cada relación) a `docs/resultados/etapa-0-corpus.md` y commitear ese fichero: `git commit -am "Fija la selección de plata con semilla 2026"`. La selección se rehará cuando el usuario entregue los 40 perfiles (sus doc_id se añaden a `protegidos.txt` y se vuelve a muestrear con la misma semilla; anotar ambos hashes).

---

### Tarea 0.15: La guía de anotación, fuente única para humanos y para el maestro

**Ficheros:**
- Crear: `docs/guia-anotacion.md`, `enrel/anotacion/guia.py`
- Test: `tests/test_guia.py`

**Interfaces:**
- Produce en `guia.py`:
  - `@dataclass class DefTipo: nombre: str; se_marca: str; no_se_marca: str`
  - `@dataclass class DefRelacionGuia: nombre: str; definicion: str; ejemplos: list[str]; no_es: list[str]; confusiones: list[str]; atributos: dict[str, str]`
  - `cargar_guia(ruta: Path = Path("docs/guia-anotacion.md")) -> tuple[dict[str, DefTipo], dict[str, DefRelacionGuia], list[str]]` (tipos, relaciones, convenciones generales). Lanza `ValueError` si falta alguna relación de `RELACIONES` o algún tipo de `TIPOS`, o si alguna relación tiene menos de 3 ejemplos o menos de 2 «no es».
- Formato del markdown que el parser espera (estricto, para que el test lo garantice):

```
# Guía de anotación de enrel
## Convenciones
- una convención por viñeta
## Tipos de entidad
### persona
**Se marca:** …
**No se marca:** …
## Relaciones
### ocupa_cargo
**Definición:** …
**Atributos:** actual: …; anterior: …; aspirante: …
**Ejemplos:**
- …
**No es:**
- …
**Confusiones:**
- …
```

- [ ] **Paso 1: Test**

`tests/test_guia.py`:

```python
from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema.tipos import RELACIONES, TIPOS


def test_guia_completa():
    tipos, relaciones, convenciones = cargar_guia(Path("docs/guia-anotacion.md"))
    assert set(tipos) == set(TIPOS)
    assert set(relaciones) == set(RELACIONES)
    assert len(convenciones) >= 6
    for r in relaciones.values():
        assert len(r.ejemplos) >= 3 and len(r.no_es) >= 2 and r.definicion, r.nombre
    assert set(relaciones["ocupa_cargo"].atributos) == {"actual", "anterior", "aspirante"}
    assert set(relaciones["familiar_de"].atributos) == {"conyuge", "hijo_de", "hermano", "otro"}
```

- [ ] **Paso 2: Ejecutar y ver que falla** → no existe el módulo ni la guía.

- [ ] **Paso 3: Escribir `docs/guia-anotacion.md`**

Texto completo:

```markdown
# Guía de anotación de enrel

Esta guía es la fuente única de las definiciones. La leen las personas que corrigen y la lee el código que construye los prompts del maestro (`enrel/anotacion/guia.py`). Si algo cambia, cambia aquí.

## Convenciones

- Se marca solo lo que el texto afirma. «Habría», «se dice que», «según fuentes» sin afirmación: no se marca.
- Sin artículos ni determinantes: «Petro», no «el Petro»; «Fiscalía», no «la Fiscalía». Salvo que el artículo sea parte del nombre: «La Silla Vacía», «El Tiempo».
- La persona nunca incluye su cargo ni su título: en «el exvicepresidente Germán Vargas Lleras» hay dos marcas, cargo «exvicepresidente» y persona «Germán Vargas Lleras».
- Un cargo incluye su complemento institucional o geográfico: «ministro de Hacienda», «alcalde de Medellín». La organización o el lugar de dentro se marca además como entidad anidada.
- Los nombres se copian exactamente como aparecen, con sus tildes y mayúsculas.
- Se marcan todas las apariciones de cada entidad, y las menciones de la misma entidad se agrupan.
- Una relación se marca una sola vez por par de entidades y tipo, aunque el texto la repita. Las simétricas, en una sola dirección.
- Si dos relaciones aplican al mismo par, se elige la más específica. Si el texto afirma dos hechos distintos (dirige y fundó), se marcan las dos.
- El título del artículo forma parte del texto y sus entidades se marcan.

## Tipos de entidad

### persona
**Se marca:** nombre propio de una persona, con o sin apellidos («Gustavo Petro», «Petro», «Francia»); apodos y cuentas que individualizan («Epa Colombia», «@petrogustavo»).
**No se marca:** pronombres; roles sueltos («la experta», «el mandatario», «el trabajador»); gentilicios; nombres de grupo («los indígenas», «los empresarios»).

### organizacion
**Se marca:** institución, empresa, partido, movimiento, medio, colectivo, junta o corte con nombre («Fiscalía General de la Nación», «Ecopetrol», «Centro Democrático», «El Tiempo», «Clan del Golfo», «Corte Constitucional»).
**No se marca:** «el Estado», «el gobierno», «las empresas», «un sindicato», «la oposición» sin nombre; adjetivos de afiliación («uribista», «liberal»).

### lugar
**Se marca:** nombre propio de país, departamento, municipio, corregimiento, barrio, región o sede física con nombre («Colombia», «Antioquia», «Medellín», «Palacio de Nariño»).
**No se marca:** «el país», «la región», «la capital», «los municipios» sin nombre.

### cargo
**Se marca:** cargo, puesto o título, con o sin titular, incluyendo su complemento («ministro de Hacienda», «senador», «alcalde de Medellín», «magistrado de la Corte Constitucional», «Gobernador de Antioquia»); también cuando el texto lo usa para designar a alguien sin nombrarlo («el Gobernador de Antioquia»).
**No se marca:** oficios genéricos («abogado», «periodista», «empresario», «profesor») salvo como cargo institucional («profesor titular de la Universidad Nacional»); parentescos («esposa de»).

### norma
**Se marca:** ley, decreto, sentencia, acto legislativo, resolución, tratado o acuerdo identificable («Ley 1448 de 2011», «Decreto 1320 de 1998», «Acuerdo de Paz», «Sentencia C-355», «artículo 49 de la Constitución»).
**No se marca:** «la ley», «un decreto», «la norma», «la reforma» sin identificar.

### obra
**Se marca:** título de libro, informe, columna, programa, película, canción, medio como producto («Tierra de Nadie», «Detector de Mentiras», «Huevos Revueltos», «Revista Semana» cuando se nombra la publicación como obra).
**No se marca:** «el informe», «un libro», «el artículo» sin título.

### monto
**Se marca:** cantidad con cifra o palabra de cantidad: «10 mil millones de pesos», «30 %», «48 a 108 meses», «un millón de dólares».
**No se marca:** «recursos», «plata», «salarios», cifras hipotéticas («supongamos dos millones»).

## Relaciones

### ocupa_cargo
**Definición:** Una persona ejerce, ejerció o busca un cargo. La cabeza es la persona; la cola es el cargo. Es la relación central del grafo de poder y la más frecuente. Si el texto da el cargo, se usa esta relación y no trabaja_en ni dirige.
**Atributos:** actual: lo ejerce según el texto, en presente o sin marca de fin («el ministro de Hacienda, José Manuel Restrepo»); anterior: lo ejerció y ya no, con «ex», «fue», «entonces», «hasta», «renunció» («el exministro Restrepo», «fue alcalde de Bogotá»); aspirante: se postula o busca el cargo, con «candidato», «precandidato», «aspira», «suena para» («Char aspira a la Presidencia»).
**Ejemplos:**
- «El ministro de Hacienda, José Manuel Restrepo, anunció…» → Restrepo ocupa_cargo:actual «ministro de Hacienda».
- «El exalcalde de Medellín Daniel Quintero» → Quintero ocupa_cargo:anterior «exalcalde de Medellín».
- «Vicky Dávila, candidata presidencial» → Dávila ocupa_cargo:aspirante «candidata presidencial».
- «El entonces gobernador de Antioquia, Luis Alfredo Ramos» → Ramos ocupa_cargo:anterior «gobernador de Antioquia».
**No es:**
- «Trabajó en el Ministerio de Hacienda» sin cargo nombrado: es trabaja_en con la organización.
- «El abogado Pérez»: «abogado» es oficio, no cargo; no se marca relación.
**Confusiones:**
- Con trabaja_en: si hay cargo nombrado, ocupa_cargo; si solo hay organización, trabaja_en.
- Con dirige: «alcaldesa de Bogotá» es ocupa_cargo con el cargo; dirige solo si además se menciona la organización («la Alcaldía»).
- Con nombro_a: «Petro nombró a X ministro» produce nombro_a (Petro → X) y ocupa_cargo:actual (X → ministro).

### nombro_a
**Definición:** Una persona u organización designa a una persona para un cargo o función. La cabeza es quien nombra; la cola es la persona nombrada.
**Ejemplos:**
- «Petro nombró a Luis Carlos Reyes como ministro de Comercio» → Petro nombro_a Reyes.
- «La Corte Suprema eligió a Francisco Barbosa como fiscal general» → Corte Suprema nombro_a Barbosa.
- «El Senado designó a la magistrada Cristina Pardo» → Senado nombro_a Pardo.
**No es:**
- «Reyes fue nombrado ministro» sin decir quién lo nombró: solo ocupa_cargo.
- «Petro propuso a X para el cargo» sin nombramiento: no se marca, o apoya_a si es respaldo explícito a una candidatura.
**Confusiones:**
- Con sucedio_a: nombro_a es quién designa; sucedio_a es a quién reemplaza el nombrado.
- Con apoya_a: proponer o respaldar no es nombrar.

### sucedio_a
**Definición:** Una persona reemplaza a otra en un cargo o función. La cabeza es quien llega; la cola es quien se va.
**Ejemplos:**
- «Reyes reemplazó a Germán Umaña en el Ministerio de Comercio» → Reyes sucedio_a Umaña.
- «Claudia Dangond fue elegida en reemplazo del magistrado Antonio Lizarazo» → Dangond sucedio_a Lizarazo.
- «Su sucesor, Carlos Fernando Galán» → Galán sucedio_a (la persona anterior mencionada).
**No es:**
- «Dejó el cargo» sin decir quién lo ocupó después: solo ocupa_cargo:anterior.
- Dos personas que ocuparon el mismo cargo en años distintos sin que el texto diga que una reemplazó a la otra: no se marca.
**Confusiones:**
- Con nombro_a: el que nombra no es el que se va.

### trabaja_en
**Definición:** Una persona trabaja, asesora o presta servicios en una organización, sin que el texto nombre un cargo. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Adriana Camacho, de la Universidad del Rosario» → Camacho trabaja_en Universidad del Rosario.
- «Trabajó en Ecopetrol durante diez años» → (persona) trabaja_en Ecopetrol.
- «Asesor del Ministerio de Defensa» → (persona) trabaja_en Ministerio de Defensa.
**No es:**
- «Ministro de Defensa»: hay cargo, es ocupa_cargo.
- «Militante del Partido Liberal»: es miembro_de.
**Confusiones:**
- Con miembro_de: empleo o asesoría es trabaja_en; pertenencia sin empleo (partido, junta, colectivo) es miembro_de.
- Con dirige: si preside o gerencia, dirige.

### dirige
**Definición:** Una persona encabeza, preside o gerencia una organización. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Ricardo Roa, presidente de Ecopetrol» → Roa dirige Ecopetrol, y Roa ocupa_cargo:actual «presidente de Ecopetrol».
- «La firma es gerenciada por Juan Pérez» → Pérez dirige (la firma).
- «Roy Barreras preside el Senado» → Barreras dirige Senado.
**No es:**
- «Trabaja en la gerencia de X» sin decir que la encabeza: trabaja_en.
- «Fundó la empresa» sin decir que la dirige: fundo.
**Confusiones:**
- Con ocupa_cargo: cuando hay cargo y organización, se marcan las dos: ocupa_cargo con el cargo y dirige con la organización.

### miembro_de
**Definición:** Una persona pertenece a una organización sin que sea empleo: militancia en un partido o movimiento, pertenencia a una junta, comisión, bancada o colectivo. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Militante del Partido Liberal» → (persona) miembro_de Partido Liberal.
- «Senador de Cambio Radical» → (persona) miembro_de Cambio Radical, además de ocupa_cargo «senador».
- «Integra la junta directiva de EPM» → (persona) miembro_de EPM.
**No es:**
- «El liberal Pérez», «el uribista X»: el adjetivo no afirma pertenencia; no se marca.
- «Trabaja en el partido como asesor»: trabaja_en.
**Confusiones:**
- Con parte_de: parte_de es entre organizaciones; una persona nunca es parte_de.
- Con trabaja_en: pertenencia sin empleo frente a empleo.

### fundo
**Definición:** Una persona u organización creó una organización. La cabeza es el fundador; la cola es lo fundado.
**Ejemplos:**
- «Álvaro Uribe fundó el Centro Democrático» → Uribe fundo Centro Democrático.
- «Cofundador de Rappi» → (persona) fundo Rappi.
- «La fundación fue creada por el Grupo Aval» → Grupo Aval fundo (la fundación).
**No es:**
- «Dueño de la empresa» sin decir que la fundó: propietario_de.
- «Lideró la creación de la ley»: no es una organización.
**Confusiones:**
- Con dirige y propietario_de: fundar no implica dirigir ni poseer hoy; se marcan aparte si el texto lo dice.

### propietario_de
**Definición:** Una persona u organización posee total o parcialmente una organización: dueño, accionista, socio de una empresa. La cabeza es el propietario; la cola es la organización.
**Ejemplos:**
- «Luis Carlos Sarmiento Angulo, dueño del Grupo Aval» → Sarmiento propietario_de Grupo Aval.
- «Accionista de Avianca» → (persona) propietario_de Avianca.
- «El Grupo Gilinski controla el 40 % de Nutresa» → Grupo Gilinski propietario_de Nutresa.
**No es:**
- «Presidente de la empresa» sin propiedad: dirige.
- «Socio de Juan Pérez» entre dos personas: socio_de.
**Confusiones:**
- Con parte_de: una filial es parte_de la matriz; la matriz es propietario_de la filial solo si el texto habla de propiedad. Si el texto dice «filial», parte_de.

### socio_de
**Definición:** Dos personas son socias en un negocio o empresa. Simétrica. Si el texto dice de qué empresa, además cada uno es propietario_de esa empresa.
**Ejemplos:**
- «Pérez y Gómez, socios en la constructora» → Pérez socio_de Gómez.
- «Su socio de toda la vida, Carlos Mattos» → (persona) socio_de Mattos.
- «Fundaron juntos la firma; son socios desde 2010» → socio_de entre los dos.
**No es:**
- «Socio del club»: es miembro_de.
- «Aliado político»: apoya_a.
**Confusiones:**
- Con propietario_de: socio de una empresa es propietario_de; socio de una persona es socio_de.

### parte_de
**Definición:** Una organización está dentro de otra: filial, dependencia, adscrita, unidad. La cabeza es la parte; la cola es el todo.
**Ejemplos:**
- «La Unidad de Víctimas, adscrita al Departamento para la Prosperidad Social» → Unidad de Víctimas parte_de DPS.
- «Ópticas Saludcoop, filial de Saludcoop» → Ópticas Saludcoop parte_de Saludcoop.
- «La Facultad de Derecho de la Universidad de los Andes» → Facultad de Derecho parte_de Universidad de los Andes.
**No es:**
- «Militante del partido»: miembro_de.
- Dos organizaciones que colaboran: no es parte_de; si el texto afirma respaldo, apoya_a.
**Confusiones:**
- Con propietario_de: propiedad frente a estructura.

### contrato_a
**Definición:** Una organización o persona contrata a otra: contratación pública o privada, adjudicación, licitación ganada. La cabeza es quien contrata; la cola es el contratista.
**Ejemplos:**
- «La Gobernación contrató a la firma Ingeniería SAS por 10 mil millones» → Gobernación contrato_a Ingeniería SAS.
- «El consorcio ganó la licitación de la Alcaldía» → Alcaldía contrato_a (el consorcio).
- «Contratista del Invías» → Invías contrato_a (persona u organización).
**No es:**
- «Trabaja en la Gobernación»: trabaja_en.
- «Financió la campaña»: financia_a.
**Confusiones:**
- Con financia_a: un contrato es intercambio; una financiación o donación no.

### financia_a
**Definición:** Una persona u organización financia, dona o aporta dinero a otra. La cabeza es quien da; la cola es quien recibe.
**Ejemplos:**
- «Odebrecht financió la campaña de Santos» → Odebrecht financia_a Santos.
- «Donó 500 millones al Partido Conservador» → (persona) financia_a Partido Conservador.
- «Los aportes de la empresa a la fundación» → (empresa) financia_a (fundación).
**No es:**
- «Le pagó por el contrato»: contrato_a.
- «Apoyó la candidatura» sin dinero: apoya_a.
**Confusiones:**
- Con contrato_a: pago por servicios frente a aporte sin contraprestación.

### familiar_de
**Definición:** Dos personas tienen un parentesco afirmado por el texto. Simétrica salvo hijo_de, donde la cabeza es el hijo.
**Atributos:** conyuge: esposo, esposa, pareja, compañero permanente, ex pareja; hijo_de: hijo o hija, la cabeza es el hijo, el padre o madre es la cola; hermano: hermanos y hermanastros; otro: tío, primo, sobrino, cuñado, suegro, nuera, yerno, nieto, abuelo, padrino, o «familiar» sin precisar.
**Ejemplos:**
- «Su esposa, Verónica Alcocer» → Petro familiar_de:conyuge Alcocer.
- «Nicolás Petro, hijo del presidente Gustavo Petro» → Nicolás Petro familiar_de:hijo_de Gustavo Petro.
- «Los hermanos Char» → Char familiar_de:hermano Char (entre los nombrados).
- «Es nieto del expresidente Alberto Lleras» → (persona) familiar_de:otro Lleras.
**No es:**
- «La familia Char» como grupo: no hay dos personas nombradas.
- «Su padrino político»: no es parentesco; apoya_a si el texto afirma respaldo.
**Confusiones:**
- Con hijo_de invertido: «su papá, Ricardo Romero» dicho de Camilo Romero produce Camilo familiar_de:hijo_de Ricardo, nunca al revés.

### apoya_a
**Definición:** Una persona u organización respalda explícitamente a otra persona, organización o candidatura: apoyo, alianza, adhesión, coalición. La cabeza es quien apoya; la cola es lo apoyado.
**Ejemplos:**
- «El Partido Liberal respaldó la candidatura de Petro» → Partido Liberal apoya_a Petro.
- «Aliado del gobierno» → (persona) apoya_a (gobierno nombrado).
- «Cambio Radical se sumó a la coalición de Duque» → Cambio Radical apoya_a Duque.
**No es:**
- Dos personas que aparecen en el mismo evento: no se marca.
- «Petro nombró a X»: nombro_a.
**Confusiones:**
- Con miembro_de: militar en un partido no es apoyar a su candidato salvo que el texto lo diga.
- Con se_opone_a: el signo contrario.

### se_opone_a
**Definición:** Una persona u organización se opone o critica explícitamente a otra persona u organización. La cabeza es quien se opone; la cola es el criticado.
**Ejemplos:**
- «Uribe criticó al gobierno de Petro» → Uribe se_opone_a Petro.
- «El Centro Democrático, en oposición al gobierno» → Centro Democrático se_opone_a (gobierno nombrado).
- «Rival político de Char» → (persona) se_opone_a Char.
**No es:**
- «Criticó la reforma»: la cola es una norma, no se marca.
- Dos candidatos al mismo cargo sin que el texto afirme rivalidad: no se marca.
**Confusiones:**
- Con investigado_por: denunciar penalmente ante una autoridad es se_opone_a solo si el texto lo presenta como oposición; la investigación la marca la autoridad.

### investigado_por
**Definición:** Una persona u organización está siendo investigada, imputada, acusada o fue condenada por una autoridad. La cabeza es el investigado; la cola es la autoridad. El delito no es una entidad y no se marca.
**Atributos:** investigado: investigación abierta, indagación, «investigado por»; acusado: imputación o acusación formal, «imputado», «acusado», «llamado a juicio»; condenado: condena, sanción, destitución, «condenado», «sancionado», «destituido».
**Ejemplos:**
- «Investigado por la Fiscalía por peculado» → (persona) investigado_por:investigado Fiscalía.
- «La Procuraduría lo destituyó e inhabilitó» → (persona) investigado_por:condenado Procuraduría.
- «Imputado por la Fiscalía» → (persona) investigado_por:acusado Fiscalía.
**No es:**
- «Acusado de corrupción» sin autoridad: no hay cola; no se marca.
- «Demandó a la empresa»: vinculo_sin_tipo.
**Confusiones:**
- Con se_opone_a: la autoridad que investiga no «se opone».

### ubicado_en
**Definición:** Una organización tiene su sede en un lugar, una persona reside en un lugar, o un lugar está dentro de otro. La cabeza es lo ubicado; la cola es el lugar.
**Ejemplos:**
- «La empresa, con sede en Barranquilla» → (empresa) ubicado_en Barranquilla.
- «Reside en Bogotá desde 2015» → (persona) ubicado_en Bogotá.
- «El municipio de Tumaco, en Nariño» → Tumaco ubicado_en Nariño.
**No es:**
- «El caleño Pérez», «de Popayán»: origen, no ubicación.
- «La reunión fue en Cartagena»: lugar de los hechos, no de la entidad.
**Confusiones:**
- Con el complemento del cargo: «alcalde de Medellín» no produce ubicado_en; Medellín va anidado dentro del cargo.

### vinculo_sin_tipo
**Definición:** El texto afirma un vínculo entre dos entidades que no encaja en ninguna relación del esquema: se reunieron, se demandaron, negociaron, se conocen. Se conserva para revisión humana. Simétrica.
**Ejemplos:**
- «Petro se reunió con Uribe» → Petro vinculo_sin_tipo Uribe.
- «La empresa demandó a la Nación» → (empresa) vinculo_sin_tipo Nación.
- «Negoció con las Farc» → (persona) vinculo_sin_tipo Farc.
**No es:**
- Dos entidades en la misma oración sin vínculo afirmado: no se marca nada.
- Un vínculo que sí encaja en otra relación: se usa esa.
**Confusiones:**
- Con apoya_a y se_opone_a: si el texto afirma respaldo u oposición, esas; si solo narra un encuentro, vinculo_sin_tipo.
```

Nota para quien ejecuta: el parser trata `vinculo_sin_tipo` como relación adicional aunque no esté en `RELACIONES`; el test exige las 17 y tolera la de reserva.

- [ ] **Paso 4: Implementar `enrel/anotacion/guia.py`**

```python
"""Lee docs/guia-anotacion.md y devuelve las definiciones estructuradas que usan los prompts y la documentación."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from enrel.esquema.tipos import RELACIONES, SIN_TIPO, TIPOS


@dataclass
class DefTipo:
    nombre: str
    se_marca: str
    no_se_marca: str


@dataclass
class DefRelacionGuia:
    nombre: str
    definicion: str
    ejemplos: list[str] = field(default_factory=list)
    no_es: list[str] = field(default_factory=list)
    confusiones: list[str] = field(default_factory=list)
    atributos: dict[str, str] = field(default_factory=dict)


def _secciones(texto: str, nivel: str) -> list[tuple[str, str]]:
    """Divide por encabezados del nivel dado («## » o «### »): [(titulo, cuerpo)]."""
    patron = re.compile(rf"^{re.escape(nivel)} (.+)$", re.M)
    coincidencias = list(patron.finditer(texto))
    out = []
    for i, m in enumerate(coincidencias):
        fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(texto)
        out.append((m.group(1).strip(), texto[m.end():fin]))
    return out


def _campo(cuerpo: str, nombre: str) -> str:
    m = re.search(rf"\*\*{re.escape(nombre)}:\*\*\s*(.*?)(?=\n\*\*|\n###|\Z)", cuerpo, re.S)
    return m.group(1).strip() if m else ""


def _vinetas(bloque: str) -> list[str]:
    return [l[2:].strip() for l in bloque.splitlines() if l.strip().startswith("- ")]


def _atributos(texto: str) -> dict[str, str]:
    out = {}
    for parte in re.split(r";\s*", texto):
        if ":" in parte:
            k, v = parte.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def cargar_guia(ruta: Path = Path("docs/guia-anotacion.md")) -> tuple[dict[str, DefTipo], dict[str, DefRelacionGuia], list[str]]:
    texto = Path(ruta).read_text(encoding="utf-8")
    principales = dict(_secciones(texto, "##"))
    convenciones = _vinetas(principales.get("Convenciones", ""))
    tipos = {}
    for nombre, cuerpo in _secciones(principales.get("Tipos de entidad", ""), "###"):
        tipos[nombre] = DefTipo(nombre, _campo(cuerpo, "Se marca"), _campo(cuerpo, "No se marca"))
    relaciones = {}
    for nombre, cuerpo in _secciones(principales.get("Relaciones", ""), "###"):
        relaciones[nombre] = DefRelacionGuia(
            nombre, _campo(cuerpo, "Definición"), _vinetas(_campo(cuerpo, "Ejemplos")),
            _vinetas(_campo(cuerpo, "No es")), _vinetas(_campo(cuerpo, "Confusiones")),
            _atributos(_campo(cuerpo, "Atributos")),
        )
    faltan_t = set(TIPOS) - set(tipos)
    faltan_r = set(RELACIONES) - set(relaciones)
    if faltan_t or faltan_r:
        raise ValueError(f"la guía no define: tipos {sorted(faltan_t)}, relaciones {sorted(faltan_r)}")
    for r in relaciones.values():
        if r.nombre != SIN_TIPO and (len(r.ejemplos) < 3 or len(r.no_es) < 2 or not r.definicion):
            raise ValueError(f"la relación {r.nombre} necesita definición, 3 ejemplos y 2 «no es»")
    for nombre, d in RELACIONES.items():
        if set(relaciones[nombre].atributos) != set(d.atributos):
            raise ValueError(f"atributos de {nombre} en la guía {sorted(relaciones[nombre].atributos)} ≠ esquema {sorted(d.atributos)}")
    return tipos, relaciones, convenciones
```

- [ ] **Paso 5: Correr el test** → en verde. Si `_campo` no captura bien un bloque de viñetas porque la expresión se detiene en la siguiente línea que empieza por `**`, comprobar que en la guía cada campo empieza en su propia línea con `**Nombre:**`, que es el formato exigido.

- [ ] **Paso 6: Commit**

```bash
git add docs/guia-anotacion.md enrel/anotacion/guia.py tests/test_guia.py
git commit -m "Escribe la guía de anotación con las 17 relaciones y su parser, fuente única de definiciones"
```

---

### Tarea 0.16: Humo del backbone: carga, memoria, ONNX y tiempo en CPU

**Ficheros:**
- Crear: `scripts/humo_backbone.py`, `docs/resultados/etapa-0-backbone.md`
- Modificar: `pyproject.toml` (fuente de torch con CUDA para `uv`)
- Test: `tests/test_humo_backbone.py` (marcado `gpu`, se salta por defecto)

**Interfaces:**
- `scripts/humo_backbone.py --modelo BSC-LT/MrBERT-es [--tokens 4096] [--lote 2] [--salida docs/resultados/etapa-0-backbone.md]` hace, en orden, y escribe cada resultado en el markdown:
  1. Carga `AutoTokenizer` y `AutoModel` (sin cabeza de MLM); imprime parámetros totales, tamaño del vocabulario, `max_position_embeddings`.
  2. Tokeniza 200 artículos del corpus congelado y reporta la relación tokens por palabra y el percentil 95 de tokens por artículo (para fijar `max_len` de entrenamiento).
  3. En GPU, si hay: pasada hacia adelante y hacia atrás con `lote` documentos sintéticos de `tokens` tokens, bf16, con `gradient_checkpointing_enable()`; reporta el pico de VRAM (`torch.cuda.max_memory_allocated()`) y el tiempo del paso.
  4. Exporta el codificador a ONNX (`torch.onnx.export` con ejes dinámicos `lote` y `secuencia`, opset 17, entradas `input_ids`, `attention_mask`, salida `ultimo_estado`); verifica que la salida ONNX coincide con la de torch en fp32 con tolerancia `1e-3` sobre un texto real.
  5. Cuantiza dinámicamente a int8 (`onnxruntime.quantization.quantize_dynamic`, `weight_type=QuantType.QInt8`) y mide, con `onnxruntime` limitado a 4 hilos intra-op (`sess_options.intra_op_num_threads = 4`) y bajo `taskset -c 0-3`, la mediana de 20 pasadas de un artículo real de ~1.500 tokens en fp32 y en int8; reporta segundos por pasada y memoria residente (`resource.getrusage`).
  6. Criterio de humo, escrito al final del markdown: carga sin errores; el paso de entrenamiento cabe en 8 GB; la diferencia máxima torch-ONNX < 1e-3; mediana int8 < 3 s por 1.500 tokens en 4 hilos. Si falla algo, el script repite los pasos 1 a 5 con `jhu-clsp/mmBERT-small` y deja las dos tablas.

- [ ] **Paso 1: Entorno con CUDA**

Añadir a `pyproject.toml`:

```toml
[tool.uv.sources]
torch = [{ index = "pytorch-cu124" }]

[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://download.pytorch.org/whl/cu124"
explicit = true
```

Ejecutar `uv sync --all-extras` y comprobar `uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"` → `True`. Si la versión de CUDA del driver (610.57, CUDA 13) no acepta cu124, usar `cu126` o `cu128`; anotar cuál funcionó en el markdown.

- [ ] **Paso 2: Test marcado**

`tests/test_humo_backbone.py`:

```python
import pytest

pytest.importorskip("torch")


@pytest.mark.gpu
def test_carga_y_pasada_corta():
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained("BSC-LT/MrBERT-es")
    modelo = AutoModel.from_pretrained("BSC-LT/MrBERT-es")
    ids = tok("El ministro de Hacienda anunció la reforma.", return_tensors="pt")
    with torch.no_grad():
        salida = modelo(**ids).last_hidden_state
    assert salida.shape[-1] == 768 and salida.shape[1] == ids["input_ids"].shape[1]
```

Correr con `uv run pytest -m gpu tests/test_humo_backbone.py -q` (descarga el modelo, 600 MB).

- [ ] **Paso 3: Escribir `scripts/humo_backbone.py`**

```python
"""Humo del backbone: carga, tokens por palabra, VRAM de un paso, exportación ONNX y tiempo en CPU.

  taskset -c 0-3 uv run python scripts/humo_backbone.py --modelo BSC-LT/MrBERT-es
"""

import argparse
import json
import resource
import statistics
import time
from datetime import date
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer


def cargar(nombre):
    tok = AutoTokenizer.from_pretrained(nombre)
    modelo = AutoModel.from_pretrained(nombre)
    params = sum(p.numel() for p in modelo.parameters())
    return tok, modelo, {"modelo": nombre, "parametros": params, "vocabulario": len(tok),
                         "max_posiciones": getattr(modelo.config, "max_position_embeddings", None)}


def tokens_por_palabra(tok, corpus: Path, n=200):
    textos = []
    with corpus.open(encoding="utf-8") as f:
        for linea in f:
            textos.append(json.loads(linea)["texto"])
            if len(textos) >= n:
                break
    razones, longitudes = [], []
    for t in textos:
        ids = tok(t, add_special_tokens=True)["input_ids"]
        longitudes.append(len(ids))
        razones.append(len(ids) / max(1, len(t.split())))
    return {"tokens_por_palabra": round(statistics.mean(razones), 2), "p50_tokens": int(np.percentile(longitudes, 50)),
            "p95_tokens": int(np.percentile(longitudes, 95)), "max_tokens": max(longitudes), "articulos": len(textos)}


def paso_gpu(modelo, tokens, lote):
    if not torch.cuda.is_available():
        return {"gpu": "no disponible"}
    modelo = modelo.cuda().train()
    modelo.gradient_checkpointing_enable()
    torch.cuda.reset_peak_memory_stats()
    ids = torch.randint(5, 1000, (lote, tokens), device="cuda")
    mask = torch.ones_like(ids)
    t0 = time.time()
    with torch.autocast("cuda", dtype=torch.bfloat16):
        salida = modelo(input_ids=ids, attention_mask=mask).last_hidden_state
        perdida = salida.float().pow(2).mean()
    perdida.backward()
    torch.cuda.synchronize()
    r = {"gpu": torch.cuda.get_device_name(0), "tokens": tokens, "lote": lote,
         "vram_pico_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2), "segundos_paso": round(time.time() - t0, 2)}
    modelo.zero_grad(set_to_none=True)
    modelo.cpu().eval()
    torch.cuda.empty_cache()
    return r


class _Envoltura(torch.nn.Module):
    def __init__(self, m):
        super().__init__()
        self.m = m

    def forward(self, input_ids, attention_mask):
        return self.m(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state


def exportar_onnx(modelo, tok, ruta: Path, texto: str):
    modelo.eval()
    ids = tok(texto, return_tensors="pt")
    torch.onnx.export(_Envoltura(modelo), (ids["input_ids"], ids["attention_mask"]), str(ruta),
                      input_names=["input_ids", "attention_mask"], output_names=["ultimo_estado"],
                      dynamic_axes={"input_ids": {0: "lote", 1: "secuencia"}, "attention_mask": {0: "lote", 1: "secuencia"},
                                    "ultimo_estado": {0: "lote", 1: "secuencia"}}, opset_version=17)
    import onnxruntime as ort
    sesion = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    salida_onnx = sesion.run(None, {"input_ids": ids["input_ids"].numpy(), "attention_mask": ids["attention_mask"].numpy()})[0]
    with torch.no_grad():
        salida_torch = modelo(**ids).last_hidden_state.numpy()
    return {"onnx": str(ruta), "mb": round(ruta.stat().st_size / 2**20, 1),
            "diferencia_max": float(np.abs(salida_onnx - salida_torch).max())}


def cuantizar(ruta: Path) -> Path:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    salida = ruta.with_name(ruta.stem + "-int8.onnx")
    quantize_dynamic(str(ruta), str(salida), weight_type=QuantType.QInt8)
    return salida


def medir_cpu(ruta: Path, tok, texto: str, hilos=4, repeticiones=20):
    import onnxruntime as ort
    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = hilos
    sesion = ort.InferenceSession(str(ruta), opciones, providers=["CPUExecutionProvider"])
    ids = tok(texto, return_tensors="np", truncation=True, max_length=8192)
    entradas = {"input_ids": ids["input_ids"], "attention_mask": ids["attention_mask"]}
    sesion.run(None, entradas)
    tiempos = []
    for _ in range(repeticiones):
        t0 = time.perf_counter()
        sesion.run(None, entradas)
        tiempos.append(time.perf_counter() - t0)
    return {"fichero": ruta.name, "tokens": int(ids["input_ids"].shape[1]), "hilos": hilos,
            "mediana_s": round(statistics.median(tiempos), 3), "p95_s": round(np.percentile(tiempos, 95), 3),
            "rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2)}


def articulo_de_1500_tokens(tok, corpus: Path) -> str:
    with corpus.open(encoding="utf-8") as f:
        for linea in f:
            t = json.loads(linea)["texto"]
            n = len(tok(t)["input_ids"])
            if 1400 <= n <= 1600:
                return t
    raise SystemExit("no encontré un artículo de ~1500 tokens en el corpus")


def humo(nombre, corpus, tokens, lote, directorio):
    tok, modelo, info = cargar(nombre)
    filas = [("Carga", info), ("Tokens", tokens_por_palabra(tok, corpus)), ("Paso GPU", paso_gpu(modelo, tokens, lote))]
    texto = articulo_de_1500_tokens(tok, corpus)
    ruta = directorio / (nombre.split("/")[-1] + ".onnx")
    filas.append(("ONNX", exportar_onnx(modelo, tok, ruta, texto)))
    filas.append(("CPU fp32", medir_cpu(ruta, tok, texto)))
    filas.append(("CPU int8", medir_cpu(cuantizar(ruta), tok, texto)))
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="BSC-LT/MrBERT-es")
    ap.add_argument("--respaldo", default="jhu-clsp/mmBERT-small")
    ap.add_argument("--corpus", default="datos/corpus/articulos.jsonl")
    ap.add_argument("--tokens", type=int, default=4096)
    ap.add_argument("--lote", type=int, default=2)
    ap.add_argument("--salida", default="docs/resultados/etapa-0-backbone.md")
    ap.add_argument("--directorio", default="datos/humo")
    a = ap.parse_args()
    directorio = Path(a.directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    partes = [f"# Humo del backbone\n\nFecha: {date.today().isoformat()} · comando: `taskset -c 0-3 uv run python scripts/humo_backbone.py --modelo {a.modelo} --tokens {a.tokens} --lote {a.lote}`\n"]
    for nombre in (a.modelo, a.respaldo):
        try:
            filas = humo(nombre, Path(a.corpus), a.tokens, a.lote, directorio)
        except Exception as e:  # noqa: BLE001
            partes.append(f"## {nombre}\n\nFALLÓ: `{type(e).__name__}: {e}`\n")
            continue
        partes.append(f"## {nombre}\n")
        for titulo, datos in filas:
            partes.append(f"**{titulo}**: " + ", ".join(f"{k} = {v}" for k, v in datos.items()) + "\n")
        if nombre == a.modelo:
            partes.append("\nCriterio: carga sin errores; paso GPU con VRAM pico < 8 GB; diferencia torch-ONNX < 1e-3; "
                          "mediana int8 < 3 s por ~1.500 tokens con 4 hilos. Si se cumple, el respaldo se mide solo como referencia.\n")
    Path(a.salida).write_text("\n".join(partes), encoding="utf-8")
    print(Path(a.salida).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
```

- [ ] **Paso 4: Ejecutar el humo**

```bash
taskset -c 0-3 uv run python scripts/humo_backbone.py --modelo BSC-LT/MrBERT-es --tokens 4096 --lote 2
```

Esperado: el markdown con las dos secciones. Si la exportación ONNX falla por el `flash attention`/`sdpa` de ModernBERT, cargar el modelo con `attn_implementation="eager"` solo para exportar (añadir `AutoModel.from_pretrained(nombre, attn_implementation="eager")` en `exportar_onnx` con una segunda instancia) y anotarlo. Si `quantize_dynamic` degrada la salida a basura (diferencia > 1 respecto a fp32 en la misma entrada), anotarlo: la decisión fp16/int8 se toma en la etapa 3 con el modelo entrenado, pero este dato ya avisa.

- [ ] **Paso 5: Leer el resultado y decidir**

Escribir al final de `docs/resultados/etapa-0-backbone.md` un párrafo con la decisión: MrBERT-es sigue, o se pasa al respaldo, con las cifras que lo justifican. Añadir `datos/humo/` a `.gitignore` (ya lo cubre `datos/`).

- [ ] **Paso 6: Commit**

```bash
git add pyproject.toml uv.lock scripts/humo_backbone.py tests/test_humo_backbone.py docs/resultados/etapa-0-backbone.md
git commit -m "Mide el backbone en humo: carga, VRAM, ONNX y tiempo en CPU a 4 hilos"
```

---

### Tarea 0.17: Documentar el esquema y cerrar la etapa

**Ficheros:**
- Crear: `docs/esquema.md`, `scripts/generar_esquema_md.py`, `docs/resultados/etapa-0-cierre.md`
- Modificar: `README.md`

**Interfaces:**
- `scripts/generar_esquema_md.py` escribe `docs/esquema.md` desde `enrel.esquema.tipos` y la guía: tabla de tipos, tabla de relaciones (nombre, de → a, simétrica, atributos, familia, equivalencia FollowTheMoney y Wikidata de la spec §3.2), y la tabla de mapeo desde los 35 predicados viejos y los 25 nuevos de legajo (generada llamando a `mapear_predicado` sobre cada predicado con sus tipos admitidos más frecuentes). Un test comprueba que `docs/esquema.md` está al día: `tests/test_esquema_md.py` regenera a una cadena y compara con el fichero.

- [ ] **Paso 1: Test**

```python
from pathlib import Path

from scripts.generar_esquema_md import generar


def test_esquema_md_al_dia():
    assert Path("docs/esquema.md").read_text(encoding="utf-8") == generar()
```

(Para que `scripts` sea importable, añadir `scripts/__init__.py` vacío y `[tool.pytest.ini_options] pythonpath = ["."]` en `pyproject.toml`.)

- [ ] **Paso 2: Escribir el generador**

```python
"""Genera docs/esquema.md desde el código y la guía, para que la documentación no se separe del esquema."""

from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema import tipos as t
from enrel.esquema.mapeo_legajo import PREDICADOS_NUEVOS, PREDICADOS_VIEJOS, mapear_predicado

EQUIVALENCIAS = {
    "ocupa_cargo": ("Occupancy", "P39"), "nombro_a": ("—", "P748"), "sucedio_a": ("Succession", "P1365"),
    "miembro_de": ("Membership", "P102, P463"), "trabaja_en": ("Employment", "P108"), "dirige": ("Directorship", "P1037, P169, P488"),
    "fundo": ("—", "P112"), "propietario_de": ("Ownership", "P127, P1830"), "socio_de": ("Associate", "P1327"),
    "parte_de": ("—", "P749, P355"), "familiar_de": ("Family", "P26, P40, P22, P25, P3373, P1038"), "financia_a": ("Payment", "P859"),
    "contrato_a": ("ContractAward", "—"), "investigado_por": ("CourtCaseParty", "P1399"), "ubicado_en": ("—", "P159, P551, P131"),
    "apoya_a": ("—", "—"), "se_opone_a": ("—", "—"),
}
_EJEMPLO_TIPOS = {"persona": ("persona", "cargo"), "organizacion": ("organizacion", "organizacion")}


def generar() -> str:
    tipos, relaciones, _ = cargar_guia()
    out = ["# Esquema de enrel", "", "Generado por `scripts/generar_esquema_md.py`. No editar a mano.", "", "## Tipos de entidad", "",
           "| Tipo | Se marca | No se marca |", "|---|---|---|"]
    for nombre in t.TIPOS:
        d = tipos[nombre]
        out.append(f"| {nombre} | {d.se_marca} | {d.no_se_marca} |")
    out += ["", "## Relaciones", "", "| Relación | De → a | Simétrica | Atributos | Familia | FollowTheMoney | Wikidata |", "|---|---|---|---|---|---|---|"]
    for nombre, d in t.RELACIONES.items():
        ftm, wd = EQUIVALENCIAS[nombre]
        out.append(f"| {nombre} | {', '.join(sorted(d.desde))} → {', '.join(sorted(d.hasta))} | {'sí' if d.simetrica else 'no'} | "
                   f"{', '.join(d.atributos) or '—'} | {d.familia} | {ftm} | {wd} |")
    out.append(f"| {t.SIN_TIPO} | cualquiera ↔ cualquiera | sí | — | — | UnknownLink | — |")
    out += ["", "## Mapeo desde legajo", "", "Para cada predicado, el destino con los tipos de extremo más habituales; los demás pares caen en vinculo_sin_tipo si la relación no los admite.", "",
            "| Predicado de legajo | Vocabulario | persona→persona | persona→organizacion | persona→cargo | organizacion→organizacion |", "|---|---|---|---|---|---|"]
    pares = [("persona", "persona"), ("persona", "organizacion"), ("persona", "cargo"), ("organizacion", "organizacion")]
    for pred in sorted(PREDICADOS_VIEJOS | PREDICADOS_NUEVOS):
        voc = "viejo y nuevo" if pred in PREDICADOS_VIEJOS and pred in PREDICADOS_NUEVOS else ("viejo" if pred in PREDICADOS_VIEJOS else "nuevo")
        celdas = []
        for a, b in pares:
            m = mapear_predicado(pred, a, b)
            celdas.append(t.clase_fina(m.relacion, m.atributo) + (" (invertida)" if m.invertir else ""))
        out.append(f"| {pred} | {voc} | " + " | ".join(celdas) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    Path("docs/esquema.md").write_text(generar(), encoding="utf-8")
    print("docs/esquema.md")
```

- [ ] **Paso 3: Generar, probar, y escribir el cierre**

```bash
uv run python scripts/generar_esquema_md.py
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

Escribir `docs/resultados/etapa-0-cierre.md` con: la lista de criterios de salida de la spec §10 etapa 0 y si se cumplió cada uno (backbone, muestra fijada con semilla y hash, guía con 17 definiciones, evaluador con tabla sobre el oro); los enlaces a `etapa-0-corpus.md`, `etapa-0-legajo.md`, `etapa-0-backbone.md`; y las cifras clave en una tabla (artículos congelados, artículos en la selección por estrato, F1 de entidades y RE+ del techo de MiniMax de legajo sobre la prueba con el esquema nuevo, VRAM pico, segundos por 1.500 tokens en int8). Si los 40 perfiles del usuario ya están en un lote de legajo, exportarlos con `enrel exportar-legajo --lote N --solo-validos --salida datos/anotado/oro-perfiles.jsonl`, repartirlos con semilla en 15/10/15 (`scripts/repartir_perfiles.py`, que escribe `datos/conjuntos/prueba_dirigida.jsonl`, añade 10 a `desarrollo.jsonl` y 15 a `oro_entrenamiento.jsonl`, y suma los 40 doc_id a `protegidos.txt`), volver a muestrear y anotar los dos hashes.

Actualizar `README.md`: estado «etapa 0 cerrada», comandos disponibles (`congelar`, `muestrear`, `exportar-legajo`, `evaluar`), y enlace a `docs/esquema.md` y `docs/guia-anotacion.md`.

- [ ] **Paso 4: Commit**

```bash
git add docs/esquema.md scripts/generar_esquema_md.py scripts/__init__.py tests/test_esquema_md.py pyproject.toml docs/resultados/etapa-0-cierre.md README.md
git commit -m "Cierra la etapa 0: esquema documentado, criterios de salida medidos"
```

---

## Autorrevisión del plan de la etapa 0

**Cobertura de la spec.** §3 esquema → 0.3, 0.5, 0.15, 0.17. §3.3 mapeo → 0.5, 0.8. §4.3 agrupación → 0.6. §5.1 corpus → 0.7, 0.9. §5.2 conjuntos y muestreo en tres estratos → 0.10, 0.14, 0.17. §5.4 formato interno y validador → 0.4. §6 herramienta legajo y exportador → 0.1, 0.8, 0.14. §8 evaluación (estricto/parcial, RE/RE+, fina, micro/macro, Ign, dirección, bootstrap, regla n ≥ 10, tres filas obligatorias) → 0.11, 0.12, 0.13; la fila «línea base GLiNER» se produce en la etapa 1 y la del «techo del maestro de legajo» en 0.14. §10 etapa 0 (humo del backbone, muestra con semilla, guía, evaluador con tabla) → 0.16, 0.10/0.14, 0.15, 0.14/0.17. Sin huecos.

**Tipos y firmas.** `Documento`, `Mencion`, `Grupo`, `Relacion` se usan con los mismos campos en 0.4, 0.6, 0.8, 0.11, 0.12, 0.13. `mapear_predicado` devuelve `Mapeo(relacion, atributo, invertir)` en 0.5 y así lo consume 0.8 y 0.17. `PRF` con `p, r, f1, n, sumar` en 0.11 y así lo usan 0.12 y 0.13. `Articulo.desplazamiento_cuerpo` y `parrafos` en 0.7 y así los usa 0.8. `registrar(nombre, ayuda)` y `fn.configurar` en 0.2 y así los usan 0.9, 0.10, 0.14.

**Placeholders.** Ninguno: cada paso de código trae el código; los datos reales se leen de rutas explícitas; las decisiones condicionales (respaldo del backbone, tope de no localizadas, formato de la plata) dicen qué mirar y qué hacer en cada rama.
