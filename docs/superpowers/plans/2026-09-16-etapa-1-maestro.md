# enrel · Etapa 1 · Maestro y prueba — Plan de implementación

> **Para agentes ejecutores:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para seguimiento. Los subagentes que escriben código usan `model: "sonnet"`.

**Objetivo:** construir el maestro (MiniMax por API) que anota artículos enteros con el esquema de enrel en cinco llamadas, medirlo contra la prueba corregida por el usuario hasta pasar la puerta (entidades ≥ 0,90, RE+ ≥ 0,75, dirección ≥ 0,95), producir la línea base GLiNER zero-shot, y anotar la plata de 3.500 artículos.

**Arquitectura:** cliente HTTP compatible con OpenAI con caché en disco y reintentos; prompts construidos desde la guía de anotación (fuente única); anclaje de cada mención y cita al texto; filtros de esquema; verificación como quinta llamada; una puerta que compara contra el oro con el evaluador de la etapa 0 y escribe la tabla y los errores más frecuentes.

**Tecnologías:** `httpx` (cliente y `MockTransport` para tests), `concurrent.futures` para paralelismo, `gliner2` para la línea base. Todo lo demás viene de la etapa 0.

**Spec:** `docs/superpowers/specs/2026-09-16-enrel-diseno.md` (§5.3, §5.4, §8, §10 · etapa 1).

## Restricciones globales

- Las de la etapa 0 (Python 3.12 con `uv`, español, offsets de caracteres NFC, `datos/` fuera de git).
- El maestro se pide con `temperature = 0`, sin razonamiento, JSON estricto. Nunca se le piden offsets: solo subcadenas literales que después se anclan.
- Cada respuesta cruda se guarda en `datos/maestro/crudo/<doc_id>/<llamada>.json` con el prompt, la versión del prompt, tokens y segundos. Rehacer una llamada con el mismo prompt no gasta cuota: la caché devuelve lo guardado.
- Cinco llamadas por documento: `entidades`, `relaciones_A`, `relaciones_B`, `relaciones_C`, `verificacion`. Las familias son las de `enrel.esquema.tipos.FAMILIAS`.
- Credenciales: variables `ENREL_MAESTRO_URL` (por defecto `https://api.minimax.io/v1`), `ENREL_MAESTRO_CLAVE`, `ENREL_MAESTRO_MODELO` (por defecto `MiniMax-M3`); si no hay clave en la variable, se busca en `~/.config/enrel/maestro.key` y después en `~/.config/legajo/*.key` (donde legajo la guardaba). Nunca se imprime ni se guarda la clave.
- La puerta se mide sobre `datos/conjuntos/prueba.jsonl` corregido por el usuario en legajo y reexportado (`enrel exportar-legajo --lote N --solo-validos`). Hasta que exista esa corrección, se mide contra el oro de legajo mapeado, y la tabla lo dice.

---

## Estructura de ficheros de la etapa 1

```
enrel/maestro/__init__.py
enrel/maestro/cliente.py          Cliente compatible con OpenAI, caché, reintentos, credenciales
enrel/maestro/anclar.py           localizar() y anclar_todas(): exacto → plegado → difuso
enrel/maestro/prompts.py          los cinco prompts desde la guía; esquemas JSON de salida; PROMPT_VERSION
enrel/maestro/filtros.py          filtros de esquema y reglas de legajo, con contadores
enrel/maestro/anotar.py           anotar_documento() y anotar_lote() reanudable
enrel/maestro/cli_anotar.py       `enrel anotar`
enrel/maestro/puerta.py           medir el maestro contra la prueba; tabla y errores frecuentes
enrel/maestro/cli_puerta.py       `enrel puerta`
enrel/evaluacion/linea_base_gliner.py   gliner2.5-multi zero-shot → Documento
enrel/evaluacion/cli_linea_base.py      `enrel linea-base-gliner`
docs/maestro/puerta-<fecha>.md    una tabla por iteración
docs/resultados/etapa-1-cierre.md
tests/test_maestro_*.py
```

---

### Tarea 1.1: Cliente del maestro con caché y reintentos

**Ficheros:**
- Crear: `enrel/maestro/__init__.py`, `enrel/maestro/cliente.py`
- Test: `tests/test_maestro_cliente.py`

**Interfaces:**
- `@dataclass class Respuesta: texto: str; tokens_entrada: int; tokens_salida: int; segundos: float; cacheado: bool; modelo: str`
- `class Cliente:` con `__init__(self, url: str | None = None, clave: str | None = None, modelo: str | None = None, cache: Path = Path("datos/maestro/cache"), transporte: httpx.BaseTransport | None = None, reintentos: int = 6, tiempo_maximo: float = 120.0)`; `completar(self, mensajes: list[dict], esquema: dict | None = None, temperatura: float = 0.0, max_tokens: int = 4000) -> Respuesta`.
- `credenciales() -> tuple[str, str, str]` (url, clave, modelo) según las restricciones globales; lanza `RuntimeError` con instrucciones si no hay clave.
- `json_estricto(texto: str) -> dict`: quita vallas de código, toma del primer `{` al último `}`, `json.loads`; lanza `ValueError` si no parsea.
- Caché: clave SHA-256 de `json.dumps({"modelo", "mensajes", "esquema", "temperatura"}, sort_keys=True)`; fichero `cache/<hash>.json` con la respuesta. Con `esquema`, el cuerpo lleva `response_format = {"type": "json_schema", "json_schema": {"name": "salida", "schema": esquema}}`; si la API responde 400 por no soportarlo, se reintenta una vez con `{"type": "json_object"}` y se anota `origen["formato"] = "json_object"`.
- Reintentos: en 429 y 5xx, espera `min(60, 2**intento + aleatorio)`; respeta `Retry-After` si viene.

- [ ] **Paso 1: Tests con transporte falso**

`tests/test_maestro_cliente.py`:

```python
import json
from pathlib import Path

import httpx
import pytest

from enrel.maestro.cliente import Cliente, json_estricto


def respuesta_ok(contenido: str, entrada=100, salida=20):
    return httpx.Response(200, json={"choices": [{"message": {"content": contenido}}],
                                     "usage": {"prompt_tokens": entrada, "completion_tokens": salida}, "model": "MiniMax-M3"})


def test_completar_y_cache(tmp_path: Path):
    llamadas = []

    def manejador(req: httpx.Request):
        llamadas.append(json.loads(req.content))
        return respuesta_ok('{"entidades": []}')

    c = Cliente(url="https://falsa/v1", clave="k", modelo="M", cache=tmp_path, transporte=httpx.MockTransport(manejador))
    r1 = c.completar([{"role": "user", "content": "hola"}], esquema={"type": "object"})
    r2 = c.completar([{"role": "user", "content": "hola"}], esquema={"type": "object"})
    assert r1.texto == '{"entidades": []}' and not r1.cacheado and r2.cacheado
    assert len(llamadas) == 1
    assert llamadas[0]["temperature"] == 0 and llamadas[0]["response_format"]["type"] == "json_schema"
    assert r1.tokens_entrada == 100 and r1.modelo == "MiniMax-M3"


def test_reintento_en_429(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("enrel.maestro.cliente._esperar", lambda s: None)
    intentos = {"n": 0}

    def manejador(req):
        intentos["n"] += 1
        if intentos["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": "rate"})
        return respuesta_ok("ok")

    c = Cliente(url="https://falsa/v1", clave="k", modelo="M", cache=tmp_path, transporte=httpx.MockTransport(manejador))
    assert c.completar([{"role": "user", "content": "x"}]).texto == "ok"
    assert intentos["n"] == 3


def test_cae_a_json_object_si_no_soporta_esquema(tmp_path: Path):
    formatos = []

    def manejador(req):
        cuerpo = json.loads(req.content)
        formatos.append(cuerpo["response_format"]["type"])
        if cuerpo["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": "unsupported response_format"})
        return respuesta_ok("{}")

    c = Cliente(url="https://falsa/v1", clave="k", modelo="M", cache=tmp_path, transporte=httpx.MockTransport(manejador))
    c.completar([{"role": "user", "content": "x"}], esquema={"type": "object"})
    assert formatos == ["json_schema", "json_object"]


def test_json_estricto():
    assert json_estricto('```json\n{"a": 1}\n```') == {"a": 1}
    assert json_estricto('Aquí va: {"a": [1, 2]} fin') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        json_estricto("nada")
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/cliente.py`**

```python
"""Cliente del maestro: API compatible con OpenAI, caché en disco, reintentos y credenciales."""

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

URL_POR_DEFECTO = "https://api.minimax.io/v1"
MODELO_POR_DEFECTO = "MiniMax-M3"


def _esperar(segundos: float) -> None:
    time.sleep(segundos)


def credenciales() -> tuple[str, str, str]:
    url = os.environ.get("ENREL_MAESTRO_URL", URL_POR_DEFECTO)
    modelo = os.environ.get("ENREL_MAESTRO_MODELO", MODELO_POR_DEFECTO)
    clave = os.environ.get("ENREL_MAESTRO_CLAVE", "")
    if not clave:
        for ruta in [Path("~/.config/enrel/maestro.key").expanduser(), *sorted(Path("~/.config/legajo").expanduser().glob("*.key"))]:
            if ruta.exists():
                clave = ruta.read_text(encoding="utf-8").strip()
                break
    if not clave:
        raise RuntimeError("sin clave del maestro: define ENREL_MAESTRO_CLAVE o escribe ~/.config/enrel/maestro.key")
    return url, clave, modelo


def json_estricto(texto: str) -> dict:
    t = texto.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("la respuesta no contiene un objeto JSON")
    return json.loads(t[i:j + 1])


@dataclass
class Respuesta:
    texto: str
    tokens_entrada: int
    tokens_salida: int
    segundos: float
    cacheado: bool
    modelo: str


class Cliente:
    def __init__(self, url: str | None = None, clave: str | None = None, modelo: str | None = None,
                 cache: Path = Path("datos/maestro/cache"), transporte: httpx.BaseTransport | None = None,
                 reintentos: int = 6, tiempo_maximo: float = 120.0):
        if url is None or clave is None or modelo is None:
            u, k, m = credenciales()
            url, clave, modelo = url or u, clave or k, modelo or m
        self.url, self._clave, self.modelo = url.rstrip("/"), clave, modelo
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.reintentos = reintentos
        self._http = httpx.Client(transport=transporte, timeout=tiempo_maximo)

    def _clave_cache(self, mensajes, esquema, temperatura) -> Path:
        crudo = json.dumps({"modelo": self.modelo, "mensajes": mensajes, "esquema": esquema, "temperatura": temperatura},
                           sort_keys=True, ensure_ascii=False)
        return self.cache / (hashlib.sha256(crudo.encode("utf-8")).hexdigest() + ".json")

    def completar(self, mensajes: list[dict], esquema: dict | None = None, temperatura: float = 0.0,
                  max_tokens: int = 4000) -> Respuesta:
        ruta = self._clave_cache(mensajes, esquema, temperatura)
        if ruta.exists():
            d = json.loads(ruta.read_text(encoding="utf-8"))
            return Respuesta(d["texto"], d["tokens_entrada"], d["tokens_salida"], d["segundos"], True, d["modelo"])
        formato = {"type": "json_schema", "json_schema": {"name": "salida", "schema": esquema}} if esquema else {"type": "json_object"}
        cuerpo = {"model": self.modelo, "messages": mensajes, "temperature": temperatura, "max_tokens": max_tokens,
                  "response_format": formato}
        t0 = time.perf_counter()
        for intento in range(self.reintentos):
            r = self._http.post(f"{self.url}/chat/completions", json=cuerpo,
                                headers={"Authorization": f"Bearer {self._clave}", "Content-Type": "application/json"})
            if r.status_code == 400 and formato["type"] == "json_schema":
                cuerpo["response_format"] = formato = {"type": "json_object"}
                continue
            if r.status_code == 429 or r.status_code >= 500:
                espera = float(r.headers.get("Retry-After", 0)) or min(60.0, 2 ** intento + random.random())
                _esperar(espera)
                continue
            r.raise_for_status()
            d = r.json()
            texto = d["choices"][0]["message"]["content"] or ""
            uso = d.get("usage", {})
            resp = Respuesta(texto, int(uso.get("prompt_tokens", 0)), int(uso.get("completion_tokens", 0)),
                             round(time.perf_counter() - t0, 3), False, d.get("model", self.modelo))
            ruta.write_text(json.dumps({"texto": resp.texto, "tokens_entrada": resp.tokens_entrada, "tokens_salida": resp.tokens_salida,
                                        "segundos": resp.segundos, "modelo": resp.modelo, "formato": formato["type"]},
                                       ensure_ascii=False), encoding="utf-8")
            return resp
        raise RuntimeError(f"el maestro no respondió tras {self.reintentos} intentos (último estado {r.status_code})")
```

Añadir `httpx` a las dependencias base de `pyproject.toml` (no solo al extra `maestro`), porque los tests lo importan.

- [ ] **Paso 4: Correr tests** → 4 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/__init__.py enrel/maestro/cliente.py tests/test_maestro_cliente.py pyproject.toml uv.lock
git commit -m "Añade el cliente del maestro con caché en disco, reintentos y credenciales"
```

---

### Tarea 1.2: Anclar menciones y citas al texto

**Ficheros:**
- Crear: `enrel/maestro/anclar.py`
- Test: `tests/test_maestro_anclar.py`

**Interfaces:**
- `localizar(texto: str, buscado: str, desde: int = 0) -> tuple[int, int] | None`: primera aparición desde `desde`, en tres niveles: (1) exacta; (2) por palabras plegadas (misma secuencia de palabras tras `plegar`, respetando límites de palabra); (3) difusa: ventana del mismo número de palabras ±1 con `difflib.SequenceMatcher(None, plegar(ventana), plegar(buscado)).ratio() ≥ 0.85`. Devuelve offsets sobre `texto`, ajustados a límites de palabra. Registra el nivel usado en `localizar.ultimo_nivel` (1, 2 o 3) para contadores.
- `anclar_todas(texto: str, buscado: str) -> list[tuple[int, int]]`: todas las apariciones por los niveles 1 y 2 (la difusa solo devuelve la mejor).
- `recortar_articulo(texto: str, ini: int, fin: int) -> tuple[int, int]`: si el tramo empieza por artículo o determinante (`el, la, los, las, un, una, unos, unas, del, al`) seguido de espacio, lo quita, salvo que el resto quede vacío.

- [ ] **Paso 1: Tests**

```python
from enrel.maestro.anclar import anclar_todas, localizar, recortar_articulo

T = "El presidente Gustavo Petro nombró a Luis Carlos Reyes. Petro dijo que Reyes es idóneo. La Fiscalia investiga."


def test_exacta_y_todas():
    assert localizar(T, "Gustavo Petro") == (14, 27)
    assert anclar_todas(T, "Petro") == [(22, 27), (57, 62)]


def test_plegada_por_palabras():
    assert localizar(T, "la fiscalía") == (86, 97)   # el texto trae «La Fiscalia» sin tilde
    assert localizar.ultimo_nivel == 2


def test_difusa():
    assert localizar(T, "Luis Carlos Reies") == (37, 54)
    assert localizar.ultimo_nivel == 3


def test_no_encontrada():
    assert localizar(T, "Uribe") is None


def test_recortar_articulo():
    assert recortar_articulo(T, 86, 97) == (89, 97)   # «La Fiscalia» → «Fiscalia»
    assert recortar_articulo("El Tiempo", 0, 9) == (3, 9)  # se recorta igual: la excepción de nombres con artículo la decide la guía
    assert recortar_articulo("la", 0, 2) == (0, 2)
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/anclar.py`**

```python
"""Ancla al texto las subcadenas que devuelve el maestro: exacto, por palabras plegadas o difuso."""

import difflib

from enrel.datos.normalizar import palabras, plegar

ARTICULOS = {"el", "la", "los", "las", "un", "una", "unos", "unas", "del", "al"}


def _por_palabras(texto: str, buscado: str, desde: int, todas: bool) -> list[tuple[int, int]]:
    objetivo = [plegar(p) for _, _, p in palabras(buscado)]
    if not objetivo:
        return []
    pals = [(i, f, plegar(p)) for i, f, p in palabras(texto) if i >= desde]
    n, out = len(objetivo), []
    for k in range(len(pals) - n + 1):
        if [p for _, _, p in pals[k:k + n]] == objetivo:
            out.append((pals[k][0], pals[k + n - 1][1]))
            if not todas:
                break
    return out


def _difusa(texto: str, buscado: str, desde: int) -> tuple[int, int] | None:
    objetivo = plegar(buscado)
    n = max(1, len(objetivo.split()))
    pals = [(i, f) for i, f, _ in palabras(texto) if i >= desde]
    mejor, mejor_ratio = None, 0.0
    for ancho in (n, n + 1, max(1, n - 1)):
        for k in range(len(pals) - ancho + 1):
            ini, fin = pals[k][0], pals[k + ancho - 1][1]
            ratio = difflib.SequenceMatcher(None, plegar(texto[ini:fin]), objetivo).ratio()
            if ratio > mejor_ratio:
                mejor, mejor_ratio = (ini, fin), ratio
    return mejor if mejor_ratio >= 0.85 else None


def localizar(texto: str, buscado: str, desde: int = 0) -> tuple[int, int] | None:
    buscado = buscado.strip()
    if not buscado:
        return None
    i = texto.find(buscado, desde)
    if i >= 0:
        localizar.ultimo_nivel = 1
        return i, i + len(buscado)
    por_pal = _por_palabras(texto, buscado, desde, todas=False)
    if por_pal:
        localizar.ultimo_nivel = 2
        return por_pal[0]
    dif = _difusa(texto, buscado, desde)
    if dif:
        localizar.ultimo_nivel = 3
    return dif


localizar.ultimo_nivel = 0


def anclar_todas(texto: str, buscado: str) -> list[tuple[int, int]]:
    buscado = buscado.strip()
    out, pos = [], 0
    while buscado:
        i = texto.find(buscado, pos)
        if i < 0:
            break
        out.append((i, i + len(buscado)))
        pos = i + 1
    return out or _por_palabras(texto, buscado, 0, todas=True)


def recortar_articulo(texto: str, ini: int, fin: int) -> tuple[int, int]:
    tramo = texto[ini:fin]
    primera, _, resto = tramo.partition(" ")
    if primera.lower() in ARTICULOS and resto.strip():
        return ini + len(primera) + 1, fin
    return ini, fin
```

- [ ] **Paso 4: Correr tests** → 5 en verde. Comprobar a mano los offsets del test (`T.find("Gustavo Petro")` es 14) antes de tocar la implementación si falla por uno.

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/anclar.py tests/test_maestro_anclar.py
git commit -m "Añade el anclaje de menciones y citas al texto en tres niveles"
```

---

### Tarea 1.3: Los cinco prompts, construidos desde la guía

**Ficheros:**
- Crear: `enrel/maestro/prompts.py`
- Test: `tests/test_maestro_prompts.py`

**Interfaces:**
- `PROMPT_VERSION = "1.0"`.
- `SISTEMA: str` (mensaje de sistema común).
- `prompt_entidades(texto: str, guia) -> tuple[list[dict], dict]`: devuelve `(mensajes, esquema_json)`. El usuario recibe: tipos con «se marca / no se marca», convenciones, instrucciones de salida (`menciones literales`, `entidad` = identificador canónico por entidad, `tipo`), y el texto. Esquema JSON: `{"entidades": [{"texto": str, "tipo": enum TIPOS, "entidad": str}]}`.
- `prompt_relaciones(texto: str, entidades: list[dict], familia: str, guia, fecha: str) -> tuple[list[dict], dict]`: `entidades` es la lista `[{"id": "e1", "canonico": "…", "tipo": "…", "menciones": ["…", …]}]`; el prompt lleva solo las relaciones de `FAMILIAS[familia]` con definición, tipos admitidos, atributos, tres ejemplos, «no es» y confusiones, más `vinculo_sin_tipo` como salida permitida, más un bloque de vigencia que explica los tres valores (vigente, pasada, futura) relativos a `fecha` y las marcas del texto que los señalan; pide `{"relaciones": [{"cabeza": id, "cola": id, "relacion": enum, "atributo": str | null, "vigencia": "vigente" | "pasada" | "futura", "cita": str}]}` con la cita como subcadena literal del texto que afirma la relación.
- `prompt_verificacion(texto: str, entidades: list[dict], relaciones: list[dict], guia, fecha: str) -> tuple[list[dict], dict]`: lista numerada de relaciones con canónicos, vigencia y cita; pide por cada una `{"indice": int, "veredicto": "confirmada" | "rechazada" | "corregida", "relacion": enum | null, "atributo": str | null, "vigencia": "vigente" | "pasada" | "futura" | null, "motivo": str}`.
- `enumerar_clases(familia) -> list[str]` para los `enum` del esquema JSON.

- [ ] **Paso 1: Tests**

```python
from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema.tipos import FAMILIAS, SIN_TIPO, TIPOS
from enrel.maestro import prompts as pr

GUIA = cargar_guia(Path("docs/guia-anotacion.md"))
T = "Gustavo Petro nombró a Luis Carlos Reyes como ministro de Comercio."


def test_prompt_entidades_lleva_tipos_y_no_pide_offsets():
    mensajes, esquema = pr.prompt_entidades(T, GUIA)
    cuerpo = mensajes[-1]["content"]
    for tipo in TIPOS:
        assert f"- {tipo}:" in cuerpo
    assert "No se marca" in cuerpo and "exactamente como aparece" in cuerpo
    assert "offset" not in cuerpo.lower() and "posición" not in cuerpo.lower()
    assert esquema["properties"]["entidades"]["items"]["properties"]["tipo"]["enum"] == list(TIPOS)
    assert T in cuerpo


def test_prompt_relaciones_solo_su_familia():
    ents = [{"id": "e1", "canonico": "Gustavo Petro", "tipo": "persona", "menciones": ["Gustavo Petro"]},
            {"id": "e2", "canonico": "Luis Carlos Reyes", "tipo": "persona", "menciones": ["Luis Carlos Reyes"]}]
    mensajes, esquema = pr.prompt_relaciones(T, ents, "A", GUIA, "2024-05-01")
    cuerpo = mensajes[-1]["content"]
    for r in FAMILIAS["A"]:
        assert f"### {r}" in cuerpo
    for r in FAMILIAS["B"]:
        assert f"### {r}" not in cuerpo
    assert "e1" in cuerpo and "Gustavo Petro" in cuerpo
    assert set(esquema["properties"]["relaciones"]["items"]["properties"]["relacion"]["enum"]) == set(FAMILIAS["A"]) | {SIN_TIPO}
    assert "Ejemplos" in cuerpo and "No es" in cuerpo and "cita" in cuerpo
    assert "2024-05-01" in cuerpo and "VIGENCIA" in cuerpo
    assert esquema["properties"]["relaciones"]["items"]["properties"]["vigencia"]["enum"] == ["vigente", "pasada", "futura"]


def test_prompt_verificacion():
    ents = [{"id": "e1", "canonico": "Gustavo Petro", "tipo": "persona", "menciones": []},
            {"id": "e2", "canonico": "Luis Carlos Reyes", "tipo": "persona", "menciones": []}]
    rels = [{"cabeza": "e1", "cola": "e2", "relacion": "nombro_a", "atributo": None, "vigencia": "vigente",
             "cita": "Gustavo Petro nombró a Luis Carlos Reyes"}]
    mensajes, esquema = pr.prompt_verificacion(T, ents, rels, GUIA, "2024-05-01")
    cuerpo = mensajes[-1]["content"]
    assert "1. Gustavo Petro —nombro_a→ Luis Carlos Reyes" in cuerpo
    assert esquema["properties"]["veredictos"]["items"]["properties"]["veredicto"]["enum"] == ["confirmada", "rechazada", "corregida"]
    assert "vigencia" in esquema["properties"]["veredictos"]["items"]["properties"]
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/prompts.py`**

```python
"""Los prompts del maestro, construidos desde la guía de anotación. Cambiar la guía cambia el prompt; subir PROMPT_VERSION al hacerlo."""

from enrel.esquema.tipos import FAMILIAS, RELACIONES, SIN_TIPO, TIPOS

PROMPT_VERSION = "1.0"

SISTEMA = (
    "Eres un anotador experto de prensa política colombiana para un grafo de poder. Marcas entidades y relaciones "
    "solo si el texto las afirma, nunca lo que sabes por fuera. Copias las menciones exactamente como aparecen en el texto. "
    "Respondes únicamente con el JSON pedido."
)


def _bloque_tipos(guia) -> str:
    tipos, _, _ = guia
    return "\n".join(f"- {t}: {tipos[t].se_marca} No se marca: {tipos[t].no_se_marca}" for t in TIPOS)


def _bloque_convenciones(guia) -> str:
    return "\n".join(f"- {c}" for c in guia[2])


def _bloque_relacion(nombre: str, guia) -> str:
    _, relaciones, _ = guia
    r = relaciones[nombre]
    if nombre == SIN_TIPO:
        tipos = "cualquiera → cualquiera"
        atributos = ""
    else:
        d = RELACIONES[nombre]
        tipos = f"{'/'.join(sorted(d.desde))} → {'/'.join(sorted(d.hasta))}" + (" (simétrica)" if d.simetrica else "")
        atributos = ("\n**Atributos:** " + "; ".join(f"{k}: {v}" for k, v in r.atributos.items())) if r.atributos else ""
    partes = [f"### {nombre}", f"**Tipos:** {tipos}", f"**Definición:** {r.definicion}{atributos}",
              "**Ejemplos:**", *[f"- {e}" for e in r.ejemplos], "**No es:**", *[f"- {e}" for e in r.no_es]]
    if r.confusiones:
        partes += ["**Confusiones:**", *[f"- {e}" for e in r.confusiones]]
    return "\n".join(partes)


def _bloque_entidades(entidades: list[dict]) -> str:
    return "\n".join(f"- {e['id']} · {e['tipo']} · {e['canonico']}" + (f" (menciones: {', '.join(e['menciones'][:5])})" if e.get("menciones") else "")
                     for e in entidades)


def enumerar_clases(familia: str) -> list[str]:
    return list(FAMILIAS[familia]) + [SIN_TIPO]


def prompt_entidades(texto: str, guia) -> tuple[list[dict], dict]:
    cuerpo = (
        "TIPOS DE ENTIDAD (usa exactamente estas claves):\n" + _bloque_tipos(guia) +
        "\n\nCONVENCIONES:\n" + _bloque_convenciones(guia) +
        "\n\nINSTRUCCIONES DE SALIDA:\n"
        "- Devuelve una entrada por cada mención, con el texto copiado exactamente como aparece en el texto (mismas mayúsculas y tildes), su tipo, "
        "y un identificador «entidad» que sea el nombre canónico más completo de esa entidad en el texto; todas las menciones de la misma "
        "entidad llevan el mismo identificador (por ejemplo, «Petro» y «Gustavo Petro» llevan «Gustavo Petro»).\n"
        "- Incluye las menciones del título.\n"
        "- No devuelvas posiciones ni números de línea: solo el texto literal.\n"
        "- Una descripción que designa a alguien sin nombrarlo («el Gobernador de Antioquia») es un cargo.\n\n"
        f"TEXTO:\n«{texto}»"
    )
    esquema = {"type": "object", "properties": {"entidades": {"type": "array", "items": {
        "type": "object", "properties": {"texto": {"type": "string"}, "tipo": {"type": "string", "enum": list(TIPOS)},
                                         "entidad": {"type": "string"}},
        "required": ["texto", "tipo", "entidad"], "additionalProperties": False}}},
        "required": ["entidades"], "additionalProperties": False}
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": cuerpo}], esquema


def _bloque_vigencia(fecha: str) -> str:
    return (
        f"VIGENCIA (relativa a la fecha del artículo, {fecha}; no a cuándo lees esto):\n"
        "- vigente (por defecto): el texto habla en presente o no marca fin.\n"
        "- pasada: con «ex», «fue», «entonces», «hasta», «exministro» y marcas similares de que ya terminó.\n"
        "- futura: con lo anunciado («asumirá», «será»).\n"
        "- No confundir con la modalidad de ocupa_cargo (titular/aspirante, en sus Atributos arriba): aspirar es una "
        "modalidad, no un tiempo; un aspirante puede estarlo vigente (aspira hoy) o pasada (aspiró y ya no).\n"
        "- En nombro_a, sucedio_a, fundo, contrato_a y financia_a (son sucesos, no estados) casi siempre es vigente."
    )


def prompt_relaciones(texto: str, entidades: list[dict], familia: str, guia, fecha: str) -> tuple[list[dict], dict]:
    clases = enumerar_clases(familia)
    cuerpo = (
        f"RELACIONES A BUSCAR (solo estas {len(clases)}; si el texto afirma un vínculo que no encaja en ninguna, usa {SIN_TIPO}):\n\n" +
        "\n\n".join(_bloque_relacion(r, guia) for r in clases) +
        "\n\nCONVENCIONES:\n" + _bloque_convenciones(guia) +
        "\n\n" + _bloque_vigencia(fecha) +
        "\n\nENTIDADES YA IDENTIFICADAS (usa sus identificadores):\n" + _bloque_entidades(entidades) +
        "\n\nINSTRUCCIONES DE SALIDA:\n"
        "- Una relación por cada par de entidades que el texto afirme con alguna de las relaciones de arriba, en la dirección que la definición indica.\n"
        "- «atributo» solo para las relaciones que lo tienen; en las demás, null.\n"
        "- «vigencia»: vigente, pasada o futura, según el bloque de arriba; por defecto vigente.\n"
        "- «cita»: la frase o fragmento del texto, copiado literalmente, que afirma la relación.\n"
        "- No inventes relaciones por coocurrencia ni por conocimiento externo. Si no hay ninguna, devuelve la lista vacía.\n\n"
        f"TEXTO:\n«{texto}»"
    )
    esquema = {"type": "object", "properties": {"relaciones": {"type": "array", "items": {
        "type": "object", "properties": {"cabeza": {"type": "string"}, "cola": {"type": "string"},
                                         "relacion": {"type": "string", "enum": clases},
                                         "atributo": {"type": ["string", "null"]},
                                         "vigencia": {"type": "string", "enum": ["vigente", "pasada", "futura"]},
                                         "cita": {"type": "string"}},
        "required": ["cabeza", "cola", "relacion", "atributo", "vigencia", "cita"], "additionalProperties": False}}},
        "required": ["relaciones"], "additionalProperties": False}
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": cuerpo}], esquema


def prompt_verificacion(texto: str, entidades: list[dict], relaciones: list[dict], guia, fecha: str) -> tuple[list[dict], dict]:
    canon = {e["id"]: e["canonico"] for e in entidades}
    lista = "\n".join(
        f"{i + 1}. {canon.get(r['cabeza'], r['cabeza'])} —{r['relacion']}{(':' + r['atributo']) if r.get('atributo') else ''}→ "
        f"{canon.get(r['cola'], r['cola'])} · vigencia: {r.get('vigencia', 'vigente')} · cita: «{r.get('cita', '')}»"
        for i, r in enumerate(relaciones))
    _, defs, _ = guia
    definiciones = "\n".join(f"- {n}: {defs[n].definicion}" for n in list(RELACIONES) + [SIN_TIPO])
    cuerpo = (
        "Verifica cada relación propuesta contra el texto, incluida su vigencia. Para cada una responde «confirmada» si el texto afirma exactamente esa "
        "relación entre esas dos entidades, en esa dirección, con ese atributo y con esa vigencia (vigente, pasada o futura, relativa a la fecha del "
        f"artículo, {fecha}); «rechazada» si el texto no la afirma (coocurrencia, inferencia, dirección invertida sin arreglo posible, "
        "entidades equivocadas); «corregida» si el vínculo existe pero la relación, el atributo o la vigencia correctos son otros, e indica cuáles.\n\n"
        "DEFINICIONES BREVES:\n" + definiciones +
        "\n\nRELACIONES PROPUESTAS:\n" + lista +
        f"\n\nTEXTO:\n«{texto}»"
    )
    esquema = {"type": "object", "properties": {"veredictos": {"type": "array", "items": {
        "type": "object", "properties": {"indice": {"type": "integer"},
                                         "veredicto": {"type": "string", "enum": ["confirmada", "rechazada", "corregida"]},
                                         "relacion": {"type": ["string", "null"]}, "atributo": {"type": ["string", "null"]},
                                         "vigencia": {"type": ["string", "null"], "enum": ["vigente", "pasada", "futura", None]},
                                         "motivo": {"type": "string"}},
        "required": ["indice", "veredicto", "relacion", "atributo", "vigencia", "motivo"], "additionalProperties": False}}},
        "required": ["veredictos"], "additionalProperties": False}
    return [{"role": "system", "content": SISTEMA}, {"role": "user", "content": cuerpo}], esquema
```

- [ ] **Paso 4: Correr tests** → 3 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/prompts.py tests/test_maestro_prompts.py
git commit -m "Añade los cinco prompts del maestro construidos desde la guía de anotación"
```

---

### Tarea 1.4: Filtros a la salida del maestro

**Ficheros:**
- Crear: `enrel/maestro/filtros.py`
- Test: `tests/test_maestro_filtros.py`

**Interfaces:**
- `PRONOMBRES: frozenset[str]` (los de legajo: yo, tú, usted, él, ella, ellos, nosotros, me, mí, te, se, uno, otro, quien, alguien, nadie, todos, ambos y sus variantes).
- `ETIQUETA_HABLANTE = re.compile(r"^[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ .]{1,40}:\s")`: si dos o más párrafos empiezan así, esos prefijos son hablantes de entrevista y las menciones dentro de ellos se descartan.
- `filtrar_menciones(texto: str, menciones: list[Mencion]) -> tuple[list[Mencion], Counter]`: descarta personas que son pronombre, personas todo en minúscula sin `@`, menciones vacías o de más de 16 palabras, menciones dentro de etiqueta de hablante; devuelve las que quedan y el contador por motivo. (`monto` ya no es un tipo del esquema desde la corrección de tipos; el filtro de cifra que tenía se retira con él.)
- `VIGENCIAS = frozenset({"vigente", "pasada", "futura"})`.
- `filtrar_relaciones(relaciones: list[Relacion], grupos: dict[str, Grupo]) -> tuple[list[Relacion], Counter]`: descarta relación desconocida, extremos inexistentes, autorrelaciones, vigencia fuera de `VIGENCIAS`, tipos no admitidos (`admite`), atributo inválido (`clase_fina` lanza), duplicados y espejos de simétricas. Cuenta por motivo.

- [ ] **Paso 1: Tests**

```python
from enrel.datos.documento import Grupo, Mencion, Relacion
from enrel.maestro.filtros import filtrar_menciones, filtrar_relaciones


def test_filtrar_menciones():
    texto = "Adriana Camacho: Yo creo que el presupuesto es alto.\n\nEntrevistador: ¿Cuánto?\n\nAdriana Camacho: 10 mil millones."
    ms = [Mencion("m1", 0, 15, "Adriana Camacho", "persona", ""), Mencion("m2", 17, 19, "Yo", "persona", ""),
          Mencion("m5", 80, 95, "Adriana Camacho", "persona", ""), Mencion("m6", 40, 44, "alto", "persona", "")]
    quedan, motivos = filtrar_menciones(texto, ms)
    assert [m.id for m in quedan] == []
    assert motivos["hablante"] == 2 and motivos["pronombre"] == 1 and motivos["minuscula"] == 1


def test_filtrar_relaciones():
    grupos = {"e1": Grupo("e1", "persona", "A"), "e2": Grupo("e2", "persona", "B"), "e3": Grupo("e3", "lugar", "C")}
    rels = [Relacion("e1", "e2", "socio_de"), Relacion("e2", "e1", "socio_de"), Relacion("e1", "e1", "nombro_a"),
            Relacion("e1", "e3", "familiar_de", "hijo_de"), Relacion("e1", "e2", "ocupa_cargo", "x"),
            Relacion("e1", "e9", "nombro_a"), Relacion("e1", "e2", "es_amigo_de"),
            Relacion("e1", "e2", "nombro_a", vigencia="ayer"),
            Relacion("e1", "e2", "nombro_a"), Relacion("e1", "e2", "nombro_a")]
    quedan, motivos = filtrar_relaciones(rels, grupos)
    assert [(r.cabeza, r.cola, r.relacion) for r in quedan] == [("e1", "e2", "socio_de"), ("e1", "e2", "nombro_a")]
    assert motivos["espejo"] == 1 and motivos["autorrelacion"] == 1 and motivos["tipos_no_admitidos"] == 1
    assert motivos["atributo_invalido"] == 1 and motivos["extremo_inexistente"] == 1 and motivos["relacion_desconocida"] == 1 and motivos["duplicada"] == 1
    assert motivos["vigencia_invalida"] == 1
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/filtros.py`**

```python
"""Lo que se descarta de la salida del maestro antes de que entre a la plata, con contadores por motivo."""

import re
from collections import Counter

from enrel.datos.documento import Grupo, Mencion, Relacion
from enrel.esquema.tipos import RELACIONES_Y_SIN_TIPO, admite, clase_fina, es_simetrica

PRONOMBRES = frozenset({
    "yo", "tú", "tu", "vos", "usted", "ustedes", "él", "ella", "ellos", "ellas", "nosotros", "nosotras",
    "me", "mí", "te", "ti", "se", "sí", "uno", "una", "otro", "otra", "otros", "otras", "quien", "quién",
    "alguien", "nadie", "cualquiera", "todos", "todas", "ambos", "ambas", "le", "les", "lo", "la",
})
ETIQUETA_HABLANTE = re.compile(r"^[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ .]{1,40}:\s", re.M)
MAX_PALABRAS = 16
VIGENCIAS = frozenset({"vigente", "pasada", "futura"})


def _tramos_hablante(texto: str) -> list[tuple[int, int]]:
    tramos = [(m.start(), m.end() - 1) for m in ETIQUETA_HABLANTE.finditer(texto)]
    return tramos if len(tramos) >= 2 else []


def filtrar_menciones(texto: str, menciones: list[Mencion]) -> tuple[list[Mencion], Counter]:
    motivos: Counter = Counter()
    hablantes = _tramos_hablante(texto)
    quedan = []
    for m in menciones:
        t = m.texto.strip()
        if not t:
            motivos["vacia"] += 1
            continue
        if len(t.split()) > MAX_PALABRAS:
            motivos["demasiado_larga"] += 1
            continue
        if any(h_ini <= m.ini and m.fin <= h_fin for h_ini, h_fin in hablantes):
            motivos["hablante"] += 1
            continue
        if m.tipo == "persona" and t.lower() in PRONOMBRES:
            motivos["pronombre"] += 1
            continue
        if m.tipo == "persona" and not t.startswith("@") and t == t.lower():
            motivos["minuscula"] += 1
            continue
        quedan.append(m)
    return quedan, motivos


def filtrar_relaciones(relaciones: list[Relacion], grupos: dict[str, Grupo]) -> tuple[list[Relacion], Counter]:
    motivos: Counter = Counter()
    quedan, claves = [], set()
    for r in relaciones:
        if r.relacion not in RELACIONES_Y_SIN_TIPO:
            motivos["relacion_desconocida"] += 1
            continue
        if r.cabeza not in grupos or r.cola not in grupos:
            motivos["extremo_inexistente"] += 1
            continue
        if r.cabeza == r.cola:
            motivos["autorrelacion"] += 1
            continue
        if r.vigencia not in VIGENCIAS:
            motivos["vigencia_invalida"] += 1
            continue
        try:
            fina = clase_fina(r.relacion, r.atributo)
        except ValueError:
            motivos["atributo_invalido"] += 1
            continue
        if not admite(r.relacion, grupos[r.cabeza].tipo, grupos[r.cola].tipo):
            motivos["tipos_no_admitidos"] += 1
            continue
        clave, espejo = (r.cabeza, r.cola, fina), (r.cola, r.cabeza, fina)
        if clave in claves:
            motivos["duplicada"] += 1
            continue
        if es_simetrica(r.relacion, r.atributo) and espejo in claves:
            motivos["espejo"] += 1
            continue
        claves.add(clave)
        quedan.append(r)
    return quedan, motivos
```

- [ ] **Paso 4: Correr tests** → 2 en verde (revisar los offsets del test contra el texto; ajustar el test, no los filtros, si un offset está corrido).

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/filtros.py tests/test_maestro_filtros.py
git commit -m "Añade los filtros de menciones y relaciones a la salida del maestro"
```

---

### Tarea 1.5: Anotar un documento en cinco llamadas, y un lote reanudable

**Ficheros:**
- Crear: `enrel/maestro/anotar.py`, `enrel/maestro/cli_anotar.py`
- Modificar: `enrel/_subcomandos.py`
- Test: `tests/test_maestro_anotar.py`

**Interfaces:**
- `anotar_documento(cliente: Cliente, texto: str, meta: dict, guia, crudo_dir: Path | None = None) -> Documento`. `meta` trae `doc_id, url, fecha, seccion, titulo`. Pasos:
  1. Llamada `entidades` → `json_estricto` (una repetición con `temperatura=0.2` si no parsea; si vuelve a fallar, `origen["invalido"] = "entidades"` y documento sin menciones).
  2. Por cada entrada: `anclar_todas(texto, e["texto"])` → una `Mencion` por aparición, tipo `e["tipo"]`, `grupo` provisional = `e["entidad"]`; cuenta `no_localizadas`. Se aplica `recortar_articulo` salvo que el texto recortado deje de coincidir con la mención.
  3. `filtrar_menciones`. Después `agrupar(menciones)` por reglas; el identificador canónico del maestro se usa para **unir** grupos que las reglas separaron pero el maestro juntó (misma `entidad`, mismo tipo): unión, no partición. Se cuenta `uniones_maestro`.
  4. Entidades para el prompt: `[{"id": g.id, "canonico": g.canonico, "tipo": g.tipo, "menciones": [textos únicos]}]`.
  5. Tres llamadas `relaciones_A/B/C`, pasando la `fecha` del artículo, → `Relacion(cabeza, cola, relacion, atributo, evidencia, vigencia)` con `evidencia = localizar(texto, cita)` (None si no ancla; se cuenta `citas_no_ancladas` pero la relación sigue hasta la verificación) y `vigencia` tomada de la salida del maestro (por defecto `vigente` si falta).
  6. `filtrar_relaciones` sobre la unión de las tres.
  7. Llamada `verificacion` con todas, incluida su vigencia y la `fecha`; se conservan `confirmada` y `corregida` (con la relación, el atributo o la vigencia corregidos, revalidados con `admite` y `clase_fina`); las `rechazada` se cuentan por relación en `origen["rechazadas"]`.
  8. `filtrar_relaciones` otra vez (las corregidas pueden duplicar). Documento con `fuente="plata"`, `origen = {"maestro": cliente.modelo, "prompt": PROMPT_VERSION, "tokens_entrada", "tokens_salida", "segundos", "no_localizadas", "citas_no_ancladas", "uniones_maestro", "motivos_menciones", "motivos_relaciones", "rechazadas", "invalido"}`. `validar_documento` debe devolver vacío; si no, lanza.
  9. Si `crudo_dir`, guarda cada respuesta cruda en `crudo_dir/<doc_id sin ':'>/<llamada>.json` con `{"mensajes", "esquema", "texto", "tokens", "segundos", "prompt": PROMPT_VERSION}`.
- `anotar_lote(cliente, corpus: Path, seleccion: Path, conjunto: str, salida: Path, guia, hilos: int = 4, crudo_dir: Path = Path("datos/maestro/crudo"), limite: int | None = None) -> dict`: lee el corpus congelado a un índice `doc_id → fila`, toma los `doc_id` de `seleccion` con `conjunto` dado, salta los ya presentes en `salida` (reanudable), anota en paralelo con `ThreadPoolExecutor(hilos)`, añade cada documento a `salida` al terminar (una línea, `flush`), y devuelve un resumen (documentos, fallos, tokens, segundos de pared, suma de contadores). Los fallos (excepción por documento) se registran en `salida.with_suffix(".fallos.jsonl")` con el `doc_id` y el error, y no detienen el lote.
- `anotar_textos(cliente, docs: list[Documento], guia, crudo_dir) -> list[Documento]`: anota documentos ya existentes (los de la prueba) usando su `texto` y meta; para la puerta.
- Subcomando `enrel anotar --seleccion datos/conjuntos/seleccion.jsonl --conjunto humo_maestro|plata --corpus datos/corpus/articulos.jsonl --salida datos/anotado/plata.jsonl [--hilos 4] [--limite N]`.

- [ ] **Paso 1: Test con cliente falso**

`tests/test_maestro_anotar.py`:

```python
import json
from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.datos.validar import validar_documento
from enrel.maestro.anotar import anotar_documento

GUIA = cargar_guia(Path("docs/guia-anotacion.md"))
T = "Los Uribe\n\nÁlvaro Uribe fundó el Centro Democrático. Tomás Uribe, hijo de Álvaro Uribe, es empresario. Uribe se reunió con Petro."


class ClienteFalso:
    modelo = "falso"

    def __init__(self):
        self.llamadas = []

    def completar(self, mensajes, esquema=None, temperatura=0.0, max_tokens=4000):
        from enrel.maestro.cliente import Respuesta
        cuerpo = mensajes[-1]["content"]
        self.llamadas.append(cuerpo[:40])
        if "TIPOS DE ENTIDAD" in cuerpo:
            salida = {"entidades": [
                {"texto": "Álvaro Uribe", "tipo": "persona", "entidad": "Álvaro Uribe"},
                {"texto": "Uribe", "tipo": "persona", "entidad": "Álvaro Uribe"},
                {"texto": "Centro Democrático", "tipo": "organizacion", "entidad": "Centro Democrático"},
                {"texto": "Tomás Uribe", "tipo": "persona", "entidad": "Tomás Uribe"},
                {"texto": "Petro", "tipo": "persona", "entidad": "Gustavo Petro"},
                {"texto": "empresario", "tipo": "cargo", "entidad": "empresario"},
                {"texto": "él", "tipo": "persona", "entidad": "él"}]}
        elif "RELACIONES A BUSCAR" in cuerpo and "### fundo" in cuerpo:
            salida = {"relaciones": [{"cabeza": "e1", "cola": "e2", "relacion": "fundo", "atributo": None, "vigencia": "vigente",
                                       "cita": "Álvaro Uribe fundó el Centro Democrático"}]}
        elif "RELACIONES A BUSCAR" in cuerpo and "### familiar_de" in cuerpo:
            salida = {"relaciones": [
                {"cabeza": "e1", "cola": "e3", "relacion": "familiar_de", "atributo": "hijo_de", "vigencia": "vigente",
                 "cita": "Tomás Uribe, hijo de Álvaro Uribe"},
                {"cabeza": "e1", "cola": "e4", "relacion": "vinculo_sin_tipo", "atributo": None, "vigencia": "vigente",
                 "cita": "Uribe se reunió con Petro"},
                {"cabeza": "e1", "cola": "e4", "relacion": "apoya_a", "atributo": None, "vigencia": "vigente",
                 "cita": "Uribe se reunió con Petro"}]}
        elif "RELACIONES A BUSCAR" in cuerpo:
            salida = {"relaciones": []}
        elif "Verifica cada relación" in cuerpo:
            # 1 fundo confirmada; 2 hijo_de invertida → corregida (la cabeza debe ser Tomás); 3 sin tipo confirmada; 4 apoya_a rechazada
            salida = {"veredictos": [
                {"indice": 1, "veredicto": "confirmada", "relacion": None, "atributo": None, "vigencia": None, "motivo": ""},
                {"indice": 2, "veredicto": "rechazada", "relacion": None, "atributo": None, "vigencia": None, "motivo": "dirección invertida"},
                {"indice": 3, "veredicto": "confirmada", "relacion": None, "atributo": None, "vigencia": None, "motivo": ""},
                {"indice": 4, "veredicto": "rechazada", "relacion": None, "atributo": None, "vigencia": None, "motivo": "no afirma apoyo"}]}
        else:
            raise AssertionError(cuerpo[:80])
        return Respuesta(json.dumps(salida, ensure_ascii=False), 10, 5, 0.1, False, "falso")


def test_anotar_documento(tmp_path):
    c = ClienteFalso()
    d = anotar_documento(c, T, {"doc_id": "wp:1", "titulo": "Los Uribe"}, GUIA, crudo_dir=tmp_path)
    assert validar_documento(d) == []
    assert len(c.llamadas) == 5
    textos = sorted(m.texto for m in d.menciones)
    assert "él" not in textos and "Petro" in textos
    uribes = {m.grupo for m in d.menciones if m.texto in ("Álvaro Uribe", "Uribe")}
    assert len(uribes) == 1
    finas = {d.clase_fina_de(r) for r in d.relaciones}
    assert finas == {"fundo", "vinculo_sin_tipo"}
    assert all(r.vigencia == "vigente" for r in d.relaciones)
    assert d.origen["rechazadas"] == {"familiar_de:hijo_de": 1, "apoya_a": 1}
    assert d.origen["prompt"] == "1.0" and d.fuente == "plata"
    assert (tmp_path / "wp_1" / "verificacion.json").exists()
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/anotar.py`**

```python
"""Anota un documento entero con el maestro en cinco llamadas y produce un Documento de plata."""

import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from enrel.corpus.muestrear import cargar_seleccion
from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Mencion, Relacion, cargar_jsonl
from enrel.datos.normalizar import nfc, plegar
from enrel.datos.validar import validar_documento
from enrel.esquema.tipos import FAMILIAS, RELACIONES_Y_SIN_TIPO, admite, clase_fina
from enrel.maestro import prompts
from enrel.maestro.anclar import anclar_todas, localizar, recortar_articulo
from enrel.maestro.cliente import Cliente, Respuesta, json_estricto
from enrel.maestro.filtros import filtrar_menciones, filtrar_relaciones


def _llamar(cliente, mensajes, esquema, contadores, nombre, crudo_dir, doc_id) -> dict | None:
    resp: Respuesta = cliente.completar(mensajes, esquema)
    contadores["tokens_entrada"] += resp.tokens_entrada
    contadores["tokens_salida"] += resp.tokens_salida
    contadores["segundos"] += resp.segundos
    try:
        salida = json_estricto(resp.texto)
    except ValueError:
        resp = cliente.completar(mensajes, esquema, temperatura=0.2)
        try:
            salida = json_estricto(resp.texto)
        except ValueError:
            salida = None
    if crudo_dir is not None:
        carpeta = Path(crudo_dir) / doc_id.replace(":", "_")
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / f"{nombre}.json").write_text(json.dumps(
            {"mensajes": mensajes, "esquema": esquema, "texto": resp.texto, "tokens": [resp.tokens_entrada, resp.tokens_salida],
             "segundos": resp.segundos, "prompt": prompts.PROMPT_VERSION, "modelo": resp.modelo}, ensure_ascii=False), encoding="utf-8")
    return salida


def anotar_documento(cliente: Cliente, texto: str, meta: dict, guia, crudo_dir: Path | None = None) -> Documento:
    texto = nfc(texto)
    doc_id = meta["doc_id"]
    cont: Counter = Counter()
    origen = {"maestro": cliente.modelo, "prompt": prompts.PROMPT_VERSION, "invalido": None}

    # 1-2. Entidades y anclaje.
    mensajes, esquema = prompts.prompt_entidades(texto, guia)
    salida = _llamar(cliente, mensajes, esquema, cont, "entidades", crudo_dir, doc_id)
    menciones: list[Mencion] = []
    canon_maestro: dict[str, str] = {}
    if salida is None:
        origen["invalido"] = "entidades"
    else:
        vistos: set[tuple[int, int]] = set()
        for e in salida.get("entidades", []):
            tipo = e.get("tipo")
            if tipo not in ("persona", "organizacion", "lugar", "cargo", "norma"):
                cont["tipo_desconocido"] += 1
                continue
            tramos = anclar_todas(texto, str(e.get("texto", "")))
            if not tramos:
                cont["no_localizadas"] += 1
                continue
            for ini, fin in tramos:
                ini2, fin2 = recortar_articulo(texto, ini, fin)
                if (ini2, fin2) in vistos:
                    continue
                vistos.add((ini2, fin2))
                m = Mencion(f"m{len(menciones) + 1}", ini2, fin2, texto[ini2:fin2], tipo, "")
                menciones.append(m)
                canon_maestro[m.id] = plegar(str(e.get("entidad", "")) or m.texto)

    # 3. Filtros y agrupación.
    menciones, motivos_m = filtrar_menciones(texto, menciones)
    grupos = agrupar(menciones)
    # Unión por identificador canónico del maestro (misma entidad y mismo tipo).
    por_canon: dict[tuple[str, str], set[str]] = {}
    for m in menciones:
        por_canon.setdefault((canon_maestro.get(m.id, ""), m.tipo), set()).add(m.grupo)
    for (canon, _), gids in por_canon.items():
        if canon and len(gids) > 1:
            destino = min(gids, key=lambda g: int(g[1:]))
            for m in menciones:
                if m.grupo in gids:
                    m.grupo = destino
            cont["uniones_maestro"] += 1
    vivos = {m.grupo for m in menciones}
    grupos = [g for g in grupos if g.id in vivos]
    por_id = {g.id: g for g in grupos}
    entidades_prompt = [{"id": g.id, "canonico": g.canonico, "tipo": g.tipo,
                         "menciones": sorted({m.texto for m in menciones if m.grupo == g.id})} for g in grupos]

    # 4-5. Relaciones por familia.
    relaciones: list[Relacion] = []
    citas: dict[int, str] = {}
    fecha = meta.get("fecha", "")
    if len(grupos) >= 2:
        for familia in FAMILIAS:
            mensajes, esquema = prompts.prompt_relaciones(texto, entidades_prompt, familia, guia, fecha)
            salida = _llamar(cliente, mensajes, esquema, cont, f"relaciones_{familia}", crudo_dir, doc_id)
            if salida is None:
                cont["relaciones_invalidas"] += 1
                continue
            for r in salida.get("relaciones", []):
                cita = str(r.get("cita", "") or "")
                ev = localizar(texto, cita) if cita else None
                if cita and ev is None:
                    cont["citas_no_ancladas"] += 1
                rel = Relacion(str(r.get("cabeza", "")), str(r.get("cola", "")), str(r.get("relacion", "")), r.get("atributo"), ev,
                              vigencia=r.get("vigencia") or "vigente")
                citas[id(rel)] = cita
                relaciones.append(rel)
    relaciones, motivos_r = filtrar_relaciones(relaciones, por_id)

    # 6-7. Verificación.
    rechazadas: Counter = Counter()
    if relaciones:
        lista = [{"cabeza": r.cabeza, "cola": r.cola, "relacion": r.relacion, "atributo": r.atributo, "vigencia": r.vigencia,
                  "cita": citas.get(id(r), "")} for r in relaciones]
        mensajes, esquema = prompts.prompt_verificacion(texto, entidades_prompt, lista, guia, fecha)
        salida = _llamar(cliente, mensajes, esquema, cont, "verificacion", crudo_dir, doc_id)
        if salida is None:
            cont["verificacion_invalida"] += 1
        else:
            veredictos = {int(v["indice"]): v for v in salida.get("veredictos", []) if "indice" in v}
            finales = []
            for i, r in enumerate(relaciones, start=1):
                v = veredictos.get(i)
                if v is None or v.get("veredicto") == "confirmada":
                    finales.append(r)
                elif v.get("veredicto") == "corregida" and v.get("relacion") in RELACIONES_Y_SIN_TIPO:
                    nueva = Relacion(r.cabeza, r.cola, v["relacion"], v.get("atributo"), r.evidencia,
                                     vigencia=v.get("vigencia") or r.vigencia)
                    try:
                        clase_fina(nueva.relacion, nueva.atributo)
                        if admite(nueva.relacion, por_id[r.cabeza].tipo, por_id[r.cola].tipo):
                            finales.append(nueva)
                            cont["corregidas"] += 1
                            continue
                    except ValueError:
                        pass
                    rechazadas[clase_fina(r.relacion, r.atributo)] += 1
                else:
                    rechazadas[clase_fina(r.relacion, r.atributo)] += 1
            relaciones = finales
        relaciones, motivos_r2 = filtrar_relaciones(relaciones, por_id)
        motivos_r.update(motivos_r2)

    origen.update({k: cont[k] for k in ("tokens_entrada", "tokens_salida", "no_localizadas", "citas_no_ancladas",
                                        "uniones_maestro", "corregidas", "tipo_desconocido", "relaciones_invalidas", "verificacion_invalida")})
    origen["segundos"] = round(cont["segundos"], 2)
    origen["motivos_menciones"] = dict(motivos_m)
    origen["motivos_relaciones"] = dict(motivos_r)
    origen["rechazadas"] = dict(rechazadas)
    doc = Documento(doc_id=doc_id, texto=texto, menciones=menciones, grupos=grupos, relaciones=relaciones,
                    url=meta.get("url", ""), fecha=meta.get("fecha", ""), seccion=meta.get("seccion", ""),
                    titulo=meta.get("titulo", ""), fuente="plata", origen=origen)
    errores = validar_documento(doc)
    if errores:
        raise ValueError("\n".join(errores))
    return doc


def anotar_textos(cliente: Cliente, docs: list[Documento], guia, crudo_dir: Path | None = None) -> list[Documento]:
    out = []
    for d in docs:
        meta = {"doc_id": d.doc_id, "url": d.url, "fecha": d.fecha, "seccion": d.seccion, "titulo": d.titulo}
        out.append(anotar_documento(cliente, d.texto, meta, guia, crudo_dir))
    return out


def anotar_lote(cliente: Cliente, corpus: Path, seleccion: Path, conjunto: str, salida: Path, guia, hilos: int = 4,
                crudo_dir: Path = Path("datos/maestro/crudo"), limite: int | None = None) -> dict:
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    hechos = {d.doc_id for d in cargar_jsonl(salida)} if salida.exists() else set()
    pendientes = [s.doc_id for s in cargar_seleccion(seleccion) if s.conjunto == conjunto and s.doc_id not in hechos]
    if limite:
        pendientes = pendientes[:limite]
    filas = {}
    with Path(corpus).open(encoding="utf-8") as f:
        for linea in f:
            d = json.loads(linea)
            if d["doc_id"] in pendientes:
                filas[d["doc_id"]] = d
    t0 = time.time()
    resumen = Counter()
    fallos = salida.with_suffix(".fallos.jsonl")
    with salida.open("a", encoding="utf-8") as out, fallos.open("a", encoding="utf-8") as ferr, ThreadPoolExecutor(hilos) as pool:
        futuros = {pool.submit(anotar_documento, cliente, filas[i]["texto"],
                               {k: filas[i].get(k, "") for k in ("doc_id", "url", "fecha", "seccion", "titulo")}, guia, crudo_dir): i
                   for i in pendientes if i in filas}
        for fut in as_completed(futuros):
            doc_id = futuros[fut]
            try:
                d = fut.result()
            except Exception as e:  # noqa: BLE001
                ferr.write(json.dumps({"doc_id": doc_id, "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False) + "\n")
                ferr.flush()
                resumen["fallos"] += 1
                continue
            out.write(json.dumps(d.a_dict(), ensure_ascii=False) + "\n")
            out.flush()
            resumen["documentos"] += 1
            resumen["tokens_entrada"] += d.origen["tokens_entrada"]
            resumen["tokens_salida"] += d.origen["tokens_salida"]
            resumen["relaciones"] += len(d.relaciones)
            resumen["menciones"] += len(d.menciones)
    resumen["segundos_pared"] = round(time.time() - t0, 1)
    resumen["pendientes_iniciales"] = len(pendientes)
    return dict(resumen)
```

`enrel/maestro/cli_anotar.py` con `@registrar("anotar", "Anota con el maestro los documentos de un conjunto de la selección")`, argumentos `--seleccion`, `--conjunto`, `--corpus`, `--salida`, `--hilos`, `--limite`, `--crudo`; construye `Cliente()` con credenciales del entorno, carga la guía, llama a `anotar_lote` e imprime el resumen. Registrar en `_subcomandos.py`.

- [ ] **Paso 4: Correr tests** → en verde. Comprobar en el test que la relación `hijo_de` con la cabeza equivocada quedó rechazada y contada.

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/anotar.py enrel/maestro/cli_anotar.py enrel/_subcomandos.py tests/test_maestro_anotar.py
git commit -m "Añade la anotación por documento en cinco llamadas y el lote reanudable"
```

---

### Tarea 1.6: La puerta: medir el maestro contra la prueba

**Ficheros:**
- Crear: `enrel/maestro/puerta.py`, `enrel/maestro/cli_puerta.py`
- Modificar: `enrel/_subcomandos.py`
- Test: `tests/test_maestro_puerta.py`

**Interfaces:**
- `CRITERIOS = {"entidades_estricto": 0.90, "re_mas": 0.75, "direccion": 0.95}`.
- `medir(oro: list[Documento], pred: list[Documento]) -> dict`: `{"entidades_estricto": f1, "entidades_parcial": f1, "re": f1, "re_mas": f1, "fina": f1, "direccion": tasa, "vigencia": tasa, "vigencia_n": int, "pasa": bool, "por_relacion": {nombre: PRF}}` usando `evaluar_entidades` y `evaluar_relaciones`. `vigencia` es solo informativa (no entra en `pasa`): la tasa de acierto de vigencia sobre las relaciones donde ya acertaron par y relación gruesa.
- `errores_frecuentes(oro, pred, n: int = 30) -> list[dict]`: los falsos negativos y falsos positivos de relaciones gruesas agrupados por `(relacion, tipo_error)` con conteo y hasta 3 ejemplos cada uno (`doc_id`, canónicos, y 120 caracteres del texto alrededor de la evidencia del oro o de la predicción). Ordenados por conteo.
- `informe_puerta(oro, pred, iteracion: int, nota: str) -> str`: markdown con fecha, `PROMPT_VERSION`, modelo, número de documentos, la tabla de criterios (valor, umbral, pasa), el `informe_completo` de la etapa 0, y la lista de errores frecuentes.
- Subcomando `enrel puerta --oro datos/conjuntos/prueba.jsonl [--pred datos/anotado/maestro-prueba.jsonl] [--iteracion N] [--nota "…"] [--salida docs/maestro/puerta-<fecha>-<N>.md]`: si no se pasa `--pred`, anota la prueba con el maestro (`anotar_textos`) y la guarda en `datos/anotado/maestro-prueba-v<PROMPT_VERSION>.jsonl` antes de medir. Sale con código 0 si pasa, 1 si no.

- [ ] **Paso 1: Test**

```python
from enrel.datos.documento import Relacion
from enrel.maestro.puerta import CRITERIOS, errores_frecuentes, medir
from tests.test_eval_relaciones import ORO, pred


def test_medir_pasa_y_no_pasa():
    perfecto = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p2", "p3", "ocupa_cargo", "titular"), Relacion("p1", "p2", "socio_de")])
    m = medir([ORO], [perfecto])
    assert m["re_mas"] == 1.0 and m["direccion"] == 1.0 and m["entidades_estricto"] < 1.0  # falta Colombia en la predicción
    assert not m["pasa"]  # entidades 3/4 = 0.86 < 0.90
    assert set(CRITERIOS) == {"entidades_estricto", "re_mas", "direccion"}
    assert "vigencia" in m and "vigencia" not in CRITERIOS  # informativa, no criterio


def test_errores_frecuentes():
    p = pred([Relacion("p2", "p1", "nombro_a")])
    errs = errores_frecuentes([ORO], [p])
    tipos = {(e["relacion"], e["tipo_error"]) for e in errs}
    assert ("nombro_a", "falso_negativo") in tipos and ("nombro_a", "falso_positivo") in tipos
    assert all("ejemplos" in e and e["conteo"] >= 1 for e in errs)
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/maestro/puerta.py`**

```python
"""La puerta del maestro: se mide contra la prueba y solo con la puerta pasada se anota a escala."""

from collections import defaultdict
from datetime import date

from enrel.datos.documento import Documento
from enrel.evaluacion.emparejar import alinear, emparejar_grupos
from enrel.evaluacion.entidades import evaluar_entidades
from enrel.evaluacion.informe import informe_completo
from enrel.evaluacion.relaciones import evaluar_relaciones
from enrel.maestro.prompts import PROMPT_VERSION

CRITERIOS = {"entidades_estricto": 0.90, "re_mas": 0.75, "direccion": 0.95}


def medir(oro: list[Documento], pred: list[Documento]) -> dict:
    ent_e = evaluar_entidades(oro, pred, "estricto")["__global__"].f1
    ent_p = evaluar_entidades(oro, pred, "parcial")["__global__"].f1
    re = evaluar_relaciones(oro, pred, "gruesa")
    re_mas = evaluar_relaciones(oro, pred, "gruesa", exigir_tipos=True)
    fina = evaluar_relaciones(oro, pred, "fina", exigir_tipos=True)["__micro__"].f1
    d = re_mas["__direccion__"]
    direccion = d.tp / (d.tp + d.fn) if d.tp + d.fn else 1.0
    # Vigencia: eje aparte, no entra en la condición de acierto de RE ni de RE+; solo se informa (§8 de la spec).
    vig = re_mas["__vigencia__"]
    vigencia_n = vig.tp + vig.fn
    vigencia = vig.tp / vigencia_n if vigencia_n else 1.0
    valores = {"entidades_estricto": ent_e, "entidades_parcial": ent_p, "re": re["__micro__"].f1,
               "re_mas": re_mas["__micro__"].f1, "fina": fina, "direccion": direccion,
               "vigencia": vigencia, "vigencia_n": vigencia_n}
    valores["pasa"] = all(valores[k] >= v for k, v in CRITERIOS.items())
    valores["por_relacion"] = {k: v for k, v in re_mas.items() if not k.startswith("__")}
    return valores


def _contexto(doc: Documento, ini: int | None, fin: int | None, ancho: int = 120) -> str:
    if ini is None:
        return ""
    a, b = max(0, ini - ancho // 2), min(len(doc.texto), (fin or ini) + ancho // 2)
    return doc.texto[a:b].replace("\n", " ")


def errores_frecuentes(oro: list[Documento], pred: list[Documento], n: int = 30) -> list[dict]:
    grupos: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for o, p in alinear(oro, pred):
        mapa = emparejar_grupos(o, p)
        pred_claves = {(r.cabeza, r.cola, r.relacion) for r in p.relaciones}
        oro_claves = set()
        for r in o.relaciones:
            gc, gl = mapa.get(r.cabeza), mapa.get(r.cola)
            oro_claves.add((gc, gl, r.relacion))
            if (gc, gl, r.relacion) not in pred_claves and (gl, gc, r.relacion) not in pred_claves:
                grupos[(r.relacion, "falso_negativo")].append({
                    "doc_id": o.doc_id, "cabeza": o.grupo_de(r.cabeza).canonico, "cola": o.grupo_de(r.cola).canonico,
                    "contexto": _contexto(o, *(r.evidencia or (None, None)))})
        inverso = {v: k for k, v in mapa.items() if v}
        for r in p.relaciones:
            if (r.cabeza, r.cola, r.relacion) not in oro_claves and (r.cola, r.cabeza, r.relacion) not in oro_claves:
                grupos[(r.relacion, "falso_positivo")].append({
                    "doc_id": p.doc_id, "cabeza": p.grupo_de(r.cabeza).canonico, "cola": p.grupo_de(r.cola).canonico,
                    "contexto": _contexto(p, *(r.evidencia or (None, None))), "oro_tiene_grupos": bool(inverso.get(r.cabeza) and inverso.get(r.cola))})
    out = [{"relacion": rel, "tipo_error": tipo, "conteo": len(ej), "ejemplos": ej[:3]} for (rel, tipo), ej in grupos.items()]
    out.sort(key=lambda e: -e["conteo"])
    return out[:n]


def informe_puerta(oro: list[Documento], pred: list[Documento], iteracion: int, nota: str) -> str:
    m = medir(oro, pred)
    modelo = pred[0].origen.get("maestro", "?") if pred else "?"
    lineas = [f"# Puerta del maestro · iteración {iteracion}", "",
              f"Fecha: {date.today().isoformat()} · prompt {PROMPT_VERSION} · maestro {modelo} · documentos {len(oro)}", ""]
    if nota:
        lineas += [nota, ""]
    lineas += ["| Criterio | Valor | Umbral | Pasa |", "|---|---:|---:|---|"]
    for k, umbral in CRITERIOS.items():
        lineas.append(f"| {k} | {m[k]:.3f} | {umbral:.2f} | {'sí' if m[k] >= umbral else 'no'} |")
    lineas += [f"| entidades_parcial | {m['entidades_parcial']:.3f} | — | |", f"| re | {m['re']:.3f} | — | |", f"| fina | {m['fina']:.3f} | — | |",
               f"| vigencia (tasa = R, n={m['vigencia_n']}) | {m['vigencia']:.3f} | — | |",
               "", f"**Resultado: {'PASA' if m['pasa'] else 'NO PASA'}.**", "", "## Errores más frecuentes", ""]
    for e in errores_frecuentes(oro, pred):
        lineas.append(f"- **{e['relacion']} · {e['tipo_error']} · {e['conteo']}**")
        for ej in e["ejemplos"]:
            lineas.append(f"  - {ej['doc_id']}: {ej['cabeza']} → {ej['cola']} · «{ej['contexto']}»")
    lineas += ["", informe_completo(oro, pred, None, f"maestro {modelo} prompt {PROMPT_VERSION}", con_intervalos=True)]
    return "\n".join(lineas)
```

`enrel/maestro/cli_puerta.py`: subcomando `puerta` con los argumentos descritos; si no hay `--pred`, construye `Cliente()`, carga la guía, `anotar_textos` sobre el oro, guarda la predicción, mide, escribe el informe en `docs/maestro/puerta-<fecha>-<iteracion>.md` y devuelve `0 if pasa else 1`. Registrar.

- [ ] **Paso 4: Correr tests** → 2 en verde.

- [ ] **Paso 5: Commit**

```bash
git add enrel/maestro/puerta.py enrel/maestro/cli_puerta.py enrel/_subcomandos.py tests/test_maestro_puerta.py
git commit -m "Añade la puerta del maestro: criterios, errores frecuentes e informe por iteración"
```

---

### Tarea 1.7: Línea base GLiNER zero-shot

**Ficheros:**
- Crear: `enrel/evaluacion/linea_base_gliner.py`, `enrel/evaluacion/cli_linea_base.py`
- Modificar: `pyproject.toml` (extra `lineabase = ["gliner2>=1.0"]`), `enrel/_subcomandos.py`
- Test: `tests/test_linea_base_gliner.py` (marcado `gpu`, porque descarga 1 GB y es lento en CPU)

**Interfaces:**
- `ETIQUETAS_ENTIDAD: dict[str, str]` = tipo de enrel → etiqueta en lenguaje natural para GLiNER («persona con nombre propio», «nombre de organización, institución, empresa o partido», «nombre propio de lugar», «cargo público o título de un puesto», «nombre de ley, decreto, sentencia o norma jurídica»), las mismas cadenas que legajo midió como mejores (redacción G); solo los cinco tipos del esquema (§3.1), sin obra ni monto.
- `ETIQUETAS_RELACION: dict[str, str]` = relación gruesa → descripción corta en español (la primera frase de la definición de la guía).
- `predecir_documento(extractor, doc: Documento) -> Documento`: corre el extractor sobre `doc.texto` en trozos de 380 palabras con solape de 40 (el modelo recibe 4.096 tokens, pero se trocea igual para la predicción de relaciones, que se degrada con pasajes densos), une menciones por offset, agrupa con `agrupar`, y convierte las relaciones a `Relacion` entre grupos (cabeza/cola por solape de menciones). `fuente="linea-base-gliner"`, `origen={"modelo": nombre, "umbral": 0.5}`.
- Subcomando `enrel linea-base-gliner --oro datos/conjuntos/prueba.jsonl --salida datos/anotado/linea-base-gliner-prueba.jsonl [--modelo fastino/gliner2.5-multi-v1] [--umbral 0.5]`, y después `enrel evaluar` produce la tabla.

La API exacta de `gliner2` se comprueba leyendo el README del paquete instalado (`uv run python -c "import gliner2, inspect; print(gliner2.__file__)"` y `cat` del README en el `site-packages`). Según la documentación pública de GLiNER2 en septiembre de 2026, el uso es: `from gliner2 import GLiNER2; ex = GLiNER2.from_pretrained("fastino/gliner2.5-multi-v1")`; `ex.extract_entities(texto, {"persona": "descripción", …}, threshold=0.5)` devuelve un diccionario tipo → lista de menciones con `text`, `start`, `end`, `score`; y `esquema = ex.create_schema().entities({...}).relations({...})` con `ex.extract(texto, esquema)` para relaciones, que devuelve `{"entities": …, "relations": [{"head": …, "tail": …, "type": …, "score": …}]}`. Si los nombres difieren en la versión instalada, adaptar `predecir_documento` a la API real y anotarlo en el commit; el resto del módulo no cambia.

- [ ] **Paso 1: Test marcado**

```python
import pytest

pytest.importorskip("gliner2")


@pytest.mark.gpu
def test_linea_base_sobre_un_documento():
    from enrel.datos.documento import Documento
    from enrel.datos.validar import validar_documento
    from enrel.evaluacion.linea_base_gliner import cargar_extractor, predecir_documento

    ex = cargar_extractor("fastino/gliner2.5-multi-v1")
    d = Documento("x", "Gustavo Petro nombró a Luis Carlos Reyes como ministro de Comercio.", [], [], [])
    p = predecir_documento(ex, d)
    assert validar_documento(p) == []
    assert any(m.tipo == "persona" for m in p.menciones)
```

- [ ] **Paso 2: Implementar `enrel/evaluacion/linea_base_gliner.py`**

```python
"""Línea base zero-shot con GLiNER2.5 multilingüe, con el esquema de enrel en lenguaje natural."""

from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Mencion, Relacion
from enrel.datos.normalizar import palabras
from enrel.esquema.tipos import RELACIONES, admite
from enrel.maestro.filtros import filtrar_menciones, filtrar_relaciones

ETIQUETAS_ENTIDAD = {
    "persona": "persona con nombre propio",
    "organizacion": "nombre de organización, institución, empresa o partido",
    "lugar": "nombre propio de lugar",
    "cargo": "cargo público o título de un puesto",
    "norma": "nombre de ley, decreto, sentencia o norma jurídica",
}
_TIPO_DE_ETIQUETA = {v: k for k, v in ETIQUETAS_ENTIDAD.items()}


def etiquetas_relacion() -> dict[str, str]:
    _, defs, _ = cargar_guia(Path("docs/guia-anotacion.md"))
    return {n: defs[n].definicion.split(".")[0] for n in RELACIONES}


def cargar_extractor(nombre: str = "fastino/gliner2.5-multi-v1"):
    from gliner2 import GLiNER2
    return GLiNER2.from_pretrained(nombre)


def _trozos(texto: str, ancho: int = 380, solape: int = 40) -> list[tuple[int, int]]:
    pals = palabras(texto)
    if not pals:
        return []
    out, i = [], 0
    while i < len(pals):
        j = min(len(pals), i + ancho)
        out.append((pals[i][0], pals[j - 1][1]))
        if j == len(pals):
            break
        i = j - solape
    return out


def predecir_documento(extractor, doc: Documento, umbral: float = 0.5, nombre: str = "fastino/gliner2.5-multi-v1") -> Documento:
    rel_desc = etiquetas_relacion()
    menciones: list[Mencion] = []
    crudas: list[tuple[int, int, int, int, str]] = []  # (ini_c, fin_c, ini_t, fin_t, relacion)
    vistos: set[tuple[int, int, str]] = set()
    for ini, fin in _trozos(doc.texto):
        trozo = doc.texto[ini:fin]
        esquema = extractor.create_schema().entities(ETIQUETAS_ENTIDAD.values()).relations(rel_desc)
        salida = extractor.extract(trozo, esquema, threshold=umbral)
        for etiqueta, lista in salida.get("entities", {}).items():
            tipo = _TIPO_DE_ETIQUETA.get(etiqueta)
            if tipo is None:
                continue
            for e in lista:
                a, b = ini + int(e["start"]), ini + int(e["end"])
                if (a, b, tipo) in vistos:
                    continue
                vistos.add((a, b, tipo))
                menciones.append(Mencion(f"m{len(menciones) + 1}", a, b, doc.texto[a:b], tipo, "", float(e.get("score", 0))))
        for r in salida.get("relations", []):
            h, t = r.get("head", {}), r.get("tail", {})
            crudas.append((ini + int(h["start"]), ini + int(h["end"]), ini + int(t["start"]), ini + int(t["end"]), r["type"]))
    menciones, _ = filtrar_menciones(doc.texto, menciones)
    grupos = agrupar(menciones)
    por_id = {g.id: g for g in grupos}

    def grupo_en(a: int, b: int) -> str | None:
        for m in menciones:
            if m.ini < b and a < m.fin:
                return m.grupo
        return None

    relaciones = []
    for ha, hb, ta, tb, rel in crudas:
        gc, gl = grupo_en(ha, hb), grupo_en(ta, tb)
        if gc and gl and rel in RELACIONES and admite(rel, por_id[gc].tipo, por_id[gl].tipo):
            atributo = RELACIONES[rel].atributos[0] if RELACIONES[rel].atributos else None
            relaciones.append(Relacion(gc, gl, rel, atributo))
    relaciones, _ = filtrar_relaciones(relaciones, por_id)
    return Documento(doc.doc_id, doc.texto, menciones, grupos, relaciones, doc.url, doc.fecha, doc.seccion, doc.titulo,
                     "linea-base-gliner", {"modelo": nombre, "umbral": umbral})
```

Nota: GLiNER no predice atributos; se asigna el primer atributo de la relación cuando la relación tiene atributos (p. ej. `familiar_de` → `conyuge`, `ocupa_cargo` → `titular`), y ninguno cuando no los tiene. Tampoco predice vigencia: se queda en `vigente` por defecto, así que su tasa de vigencia informada es solo la proporción de casos donde el oro también es `vigente`. La evaluación fina penaliza el atributo por defecto que no coincide. Es la línea base; se documenta.

`enrel/evaluacion/cli_linea_base.py`: subcomando `linea-base-gliner` que carga el oro, corre `predecir_documento` sobre cada documento, guarda y muestra el tiempo por documento (también es un dato de CPU si se corre con `taskset -c 0-3`).

- [ ] **Paso 3: Correr, medir y guardar**

```bash
uv sync --all-extras
uv run pytest -m gpu tests/test_linea_base_gliner.py -q
taskset -c 0-3 uv run enrel linea-base-gliner --oro datos/conjuntos/prueba.jsonl --salida datos/anotado/linea-base-gliner-prueba.jsonl
uv run enrel evaluar --oro datos/conjuntos/prueba.jsonl --pred datos/anotado/linea-base-gliner-prueba.jsonl --nombre "GLiNER2.5-multi zero-shot" --salida docs/resultados/etapa-1-linea-base-gliner.md
```

Añadir al informe el tiempo medido por documento en 4 hilos.

- [ ] **Paso 4: Commit**

```bash
git add enrel/evaluacion/linea_base_gliner.py enrel/evaluacion/cli_linea_base.py enrel/_subcomandos.py tests/test_linea_base_gliner.py pyproject.toml uv.lock docs/resultados/etapa-1-linea-base-gliner.md
git commit -m "Añade la línea base GLiNER2.5 zero-shot y su tabla sobre la prueba"
```

---

### Tarea 1.8: Iterar el maestro hasta pasar la puerta, y anotar la plata

Sin código nuevo salvo cambios en la guía (y por tanto en los prompts) y el registro de resultados. Esta tarea la ejecuta el orquestador con el usuario, no un subagente ciego: cada iteración lee errores y decide.

- [ ] **Paso 1: Humo del maestro sobre 30 documentos**

```bash
uv run enrel anotar --seleccion datos/conjuntos/seleccion.jsonl --conjunto humo_maestro --salida datos/anotado/humo-maestro.jsonl --hilos 2
```

Leer 10 documentos a mano (`uv run python -c "..."` que imprima menciones y relaciones con su evidencia). Comprobar: menciones literales bien ancladas (`no_localizadas` bajo), grupos razonables, relaciones con cita, atributos correctos, `rechazadas` con sentido. Corregir formulaciones de la guía si algo sistemático aparece. Subir `PROMPT_VERSION` a `1.1` en cada cambio de guía.

- [ ] **Paso 2: Reexportar la prueba corregida por el usuario**

Cuando el usuario haya corregido los 50 en legajo (lote N, `--solo-validos`):

```bash
uv run enrel exportar-legajo --lote N --solo-validos --salida datos/anotado/prueba-corregida.jsonl
uv run python - <<'EOF'
from enrel.datos.documento import cargar_jsonl, guardar_jsonl
from pathlib import Path
ids = {l.strip() for l in Path("datos/conjuntos/protegidos.txt").read_text().splitlines()}
docs = [d for d in cargar_jsonl("datos/anotado/prueba-corregida.jsonl") if d.doc_id in ids]
print(len(docs)); guardar_jsonl(docs, "datos/conjuntos/prueba.jsonl")
EOF
```

Anotar en `docs/resultados/etapa-1-cierre.md` cuántos de los 50 quedaron corregidos y el hash. Si aún no están, la puerta se mide contra el oro mapeado de legajo y el informe lo dice en la nota.

- [ ] **Paso 3: Puerta, hasta tres iteraciones**

```bash
uv run enrel puerta --oro datos/conjuntos/prueba.jsonl --iteracion 1 --nota "Prompt 1.0 contra la prueba corregida por el usuario"
```

Leer `docs/maestro/puerta-<fecha>-1.md`. Por cada grupo de errores frecuentes, decidir: (a) definición o ejemplo de la guía que lo arregla, (b) error del oro (anotar para revisar con el usuario), (c) límite del maestro. Cambiar la guía, subir `PROMPT_VERSION`, repetir con `--iteracion 2` y `3`. Si tras la tercera no pasa: escribir en `docs/resultados/etapa-1-cierre.md` qué relaciones arrastran (F1 por relación bajo 0,5 con n ≥ 10), proponer al usuario retirarlas del esquema para la v0.1 (pasan a `vinculo_sin_tipo`) o sumar un segundo maestro, y no seguir sin su decisión.

- [ ] **Paso 4: Anotar la plata**

Con la puerta pasada:

```bash
nohup uv run enrel anotar --seleccion datos/conjuntos/seleccion.jsonl --conjunto plata --salida datos/anotado/plata.jsonl --hilos 4 > datos/maestro/plata.log 2>&1 &
```

Reanudable: si se corta, el mismo comando sigue donde quedó. Al terminar: contar positivos por clase fina (`uv run python scripts/contar_positivos.py datos/anotado/plata.jsonl`, un script de 20 líneas que imprime un `Counter` de `clase_fina` y de tipos), comparar con el umbral de 60, y si alguna relación queda corta hacer la segunda ronda dirigida (Tarea 0.10 con `--cuota-relacion` solo para esas relaciones, hasta 300 artículos, añadiendo a la selección con `conjunto = "plata"`).

- [ ] **Paso 5: Cierre**

`docs/resultados/etapa-1-cierre.md` con: la iteración que pasó la puerta y sus cifras; la tabla de la línea base GLiNER al lado; tokens y horas gastadas en la plata; positivos por clase fina y estrato; fallos del lote; hashes de `plata.jsonl`, `prueba.jsonl`, `seleccion.jsonl`. Commit:

```bash
git add docs/maestro docs/resultados/etapa-1-cierre.md docs/guia-anotacion.md enrel/maestro/prompts.py scripts/contar_positivos.py
git commit -m "Cierra la etapa 1: puerta del maestro pasada, línea base medida y plata anotada"
```

---

## Autorrevisión del plan de la etapa 1

**Cobertura de la spec.** §5.3 maestro: cinco llamadas (1.5), prompts desde la guía con definiciones, ejemplos, negativos y confusiones (1.3), menciones literales más identificador canónico y nunca offsets (1.3, 1.5), verificación (1.5), filtros en orden (1.4, 1.5), puerta con sus tres criterios y tres iteraciones máximo (1.6, 1.8), costo y reanudación (1.1, 1.5). §8 tres filas obligatorias: la línea base (1.7), el techo del maestro (1.6 produce la predicción del maestro sobre la prueba, que es su techo) y el modelo (etapa 2). §10 etapa 1: criterio de salida escrito (1.8).

**Tipos y firmas.** `Cliente.completar(mensajes, esquema, temperatura, max_tokens) -> Respuesta` en 1.1 y así lo llama 1.5 y lo imita `ClienteFalso`. `localizar`/`anclar_todas`/`recortar_articulo` en 1.2 y así los usa 1.5. `prompt_*` devuelven `(mensajes, esquema)` en 1.3 y así los consume 1.5. `filtrar_menciones(texto, menciones) -> (lista, Counter)` y `filtrar_relaciones(relaciones, grupos_dict) -> (lista, Counter)` en 1.4 y así en 1.5 y 1.7. `medir`, `errores_frecuentes`, `informe_puerta` en 1.6 los usa el CLI de 1.6 y la Tarea 1.8.

**Placeholders.** La API de `gliner2` está descrita con la reserva explícita de comprobarla contra el paquete instalado; el resto está completo.
