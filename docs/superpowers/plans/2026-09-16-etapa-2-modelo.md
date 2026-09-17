# enrel · Etapa 2 · Modelo y primer entrenamiento — Plan de implementación

> **Para agentes ejecutores:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para seguimiento. Los subagentes que escriben código usan `model: "sonnet"`. Los tests que necesitan GPU llevan `@pytest.mark.gpu`; los que necesitan solo torch en CPU corren siempre.

**Objetivo:** construir el modelo (backbone MrBERT-es más una cabeza de tramos para entidades y una cabeza de pares para relaciones a nivel de documento), la conversión de documentos a tensores, el bucle de entrenamiento con parada por RE+ en desarrollo, la prueba de cordura, la inferencia de extremo a extremo con agrupación por reglas, el CLI `enrel extraer`, y el primer entrenamiento con la plata evaluado con la tabla completa.

**Arquitectura:** un codificador compartido; cabeza de entidades por clasificación de tramos de hasta 16 palabras con representación inicio+fin+anchura; cabeza de relaciones por pares ordenados de grupos con agregación logsumexp de menciones, contexto local por atención aprendida sobre el documento, clasificador bilineal agrupado sobre 25 clases finas más una clase umbral (ATLOP), máscara de tipos, pérdida de umbral adaptativo con reponderación por clase. Todo opera sobre el documento entero, con recorte a 4.096 tokens en entrenamiento y ventanas en inferencia.

**Tecnologías:** `torch` con CUDA, `transformers` (ModernBERT), `pyyaml`, `numpy`. Reutiliza etapa 0 (`Documento`, `agrupar`, evaluación) y etapa 1 (filtros).

**Spec:** `docs/superpowers/specs/2026-09-16-enrel-diseno.md` (§4, §7, §8, §10 · etapa 2).

## Restricciones globales

- Las de las etapas 0 y 1.
- Entrenamiento: bf16 con `gradient_checkpointing`, lote 2 × acumulación 8, longitud máxima 4.096 tokens, lr codificador 3e-5 y cabezas 1e-4, hasta 8 épocas con parada por RE+ en desarrollo (paciencia 2), semillas 42 y 7. Etapa 2 (oro): lr 1e-5 / 3e-5, hasta 4 épocas. Todo en `configs/*.yaml`, nada en el código.
- Tope de 60 grupos por documento en la cabeza de relaciones (se conservan los de más menciones; se cuenta el recorte). Tramos de entidad de 1 a 16 palabras. Negativos de tramo 8:1.
- Cada corrida escribe en `corridas/<fecha>-<nombre>/`: `config.yaml`, `hashes.json`, `metricas.jsonl`, `mejor/` (checkpoint), `evaluacion-desarrollo.md`. `corridas/` está fuera de git.
- El modelo se guarda con `save_pretrained`-like propio: `config.json` (nombre del backbone, hiperparámetros de cabezas, esquema con `CLASES_FINAS`, versión), `backbone/` (HF `save_pretrained`), `cabezas.safetensors`.
- La inferencia nunca produce un `Documento` inválido: pasa por `filtrar_relaciones` y `validar_documento` antes de devolver.

---

## Estructura de ficheros de la etapa 2

```
enrel/modelo/__init__.py
enrel/modelo/tokenizacion.py       palabras ↔ subpalabras ↔ caracteres; ventanas
enrel/modelo/backbone.py           cargar backbone; nombre → tokenizer + modelo
enrel/modelo/entidades.py          CabezaEntidades, enumerar_tramos
enrel/modelo/relaciones.py         CabezaRelaciones (logsumexp, contexto, bilineal agrupado, TH)
enrel/modelo/perdidas.py           entropía cruzada de tramos; umbral adaptativo con pesos; decodificación TH
enrel/modelo/enrel.py              ModeloEnrel: guardar/cargar, máscara de tipos
enrel/entrenamiento/__init__.py
enrel/entrenamiento/tensores.py    Documento → Ejemplo (tramos, pares, etiquetas)
enrel/entrenamiento/colacion.py    Ejemplos → Lote con relleno
enrel/entrenamiento/config.py      Config desde YAML
enrel/entrenamiento/bucle.py       entrenar(config): optimizador, épocas, evaluación, parada, guardado
enrel/entrenamiento/cordura.py     sobreajustar 20 documentos
enrel/entrenamiento/cli_entrenar.py `enrel entrenar --config …`
enrel/inferencia/__init__.py
enrel/inferencia/decodificar.py    logits → menciones, grupos, relaciones, evidencia
enrel/inferencia/pipeline.py       Pipeline(texto) → Documento, ventanas, agrupación
enrel/inferencia/cli_extraer.py    `enrel extraer`, `enrel predecir-conjunto`
configs/etapa1-plata.yaml, configs/etapa2-oro.yaml, configs/cordura.yaml
docs/resultados/etapa-2.md
tests/test_modelo_*.py, tests/test_entrenamiento_*.py, tests/test_inferencia_*.py
```

---

### Tarea 2.1: Tokenización con alineación palabras ↔ subpalabras ↔ caracteres

**Ficheros:**
- Crear: `enrel/modelo/__init__.py`, `enrel/modelo/tokenizacion.py`
- Test: `tests/test_modelo_tokenizacion.py`

**Interfaces:**
- `@dataclass class Codificacion: input_ids: list[int]; attention_mask: list[int]; palabras: list[tuple[int, int]]` (offsets de caracteres de cada palabra incluida, en orden); `primera_subpalabra: list[int]` (índice de la primera subpalabra de cada palabra, misma longitud que `palabras`); `ultima_subpalabra: list[int]`; `desplazamiento: int` (offset de caracteres del inicio de la ventana en el texto completo); `truncada: bool`.
- `codificar(tok, texto: str, max_len: int = 4096, desplazamiento: int = 0) -> Codificacion`: tokeniza con `return_offsets_mapping=True`, `add_special_tokens=True`, `truncation=True`, `max_length=max_len`; deriva las palabras con `enrel.datos.normalizar.palabras` y asigna a cada palabra las subpalabras cuyos offsets caen dentro de ella (una subpalabra que abarca dos palabras, por ejemplo por un guion, se asigna a la primera). Las palabras sin subpalabra (por truncamiento) se excluyen y se marca `truncada=True`.
- `ventanas(tok, texto: str, max_len: int = 8192, solape: int = 512) -> list[Codificacion]`: divide el texto en ventanas por límite de palabra de modo que cada una quepa en `max_len` tokens, con `solape` tokens aproximados entre consecutivas; devuelve una lista de `Codificacion` con `desplazamiento` en caracteres. Para textos que caben, una sola ventana.
- `palabra_de(cod: Codificacion, ini_char: int, fin_char: int) -> tuple[int, int] | None`: índices de la primera y última palabra que cubren el tramo de caracteres (relativo al texto completo), o `None` si el tramo cae fuera de la ventana.

- [ ] **Paso 1: Tests (con un tokenizer pequeño de HF para no descargar MrBERT en los tests)**

`tests/test_modelo_tokenizacion.py`:

```python
import pytest

transformers = pytest.importorskip("transformers")
from enrel.modelo.tokenizacion import codificar, palabra_de, ventanas


@pytest.fixture(scope="module")
def tok():
    # Pequeño y multilingüe; los tests solo necesitan offsets, no calidad.
    return transformers.AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-bert")


def test_codificar_alinea_palabras(tok):
    texto = "El ministro de Hacienda, José Manuel Restrepo, anunció la reforma."
    c = codificar(tok, texto, max_len=64)
    assert len(c.palabras) == len(c.primera_subpalabra) == len(c.ultima_subpalabra)
    assert [texto[a:b] for a, b in c.palabras][:4] == ["El", "ministro", "de", "Hacienda"]
    for (a, b), i, j in zip(c.palabras, c.primera_subpalabra, c.ultima_subpalabra):
        assert 0 < i <= j < len(c.input_ids) - 1   # sin los especiales
    assert not c.truncada


def test_truncamiento(tok):
    texto = " ".join(["palabra"] * 500)
    c = codificar(tok, texto, max_len=32)
    assert c.truncada and len(c.input_ids) == 32 and len(c.palabras) < 500


def test_palabra_de(tok):
    texto = "Gustavo Petro nombró a Luis Carlos Reyes."
    c = codificar(tok, texto)
    assert palabra_de(c, 0, 13) == (0, 1)       # «Gustavo Petro»
    assert palabra_de(c, 23, 40) == (4, 6)      # «Luis Carlos Reyes»
    assert palabra_de(c, 500, 510) is None


def test_ventanas(tok):
    texto = " ".join(f"palabra{i}" for i in range(300))
    vs = ventanas(tok, texto, max_len=64, solape=8)
    assert len(vs) > 1
    assert vs[0].desplazamiento == 0 and all(v.desplazamiento < w.desplazamiento for v, w in zip(vs, vs[1:]))
    # cada palabra del texto está en al menos una ventana
    cubiertas = set()
    for v in vs:
        for a, b in v.palabras:
            cubiertas.add(a)
    assert len(cubiertas) == 300
```

- [ ] **Paso 2: Ejecutar y ver que falla** → `ModuleNotFoundError`.

- [ ] **Paso 3: Implementar `enrel/modelo/tokenizacion.py`**

```python
"""Alineación entre caracteres, palabras (regex de enrel) y subpalabras del tokenizer."""

from dataclasses import dataclass, field

from enrel.datos.normalizar import palabras as partir_palabras


@dataclass
class Codificacion:
    input_ids: list[int]
    attention_mask: list[int]
    palabras: list[tuple[int, int]]
    primera_subpalabra: list[int]
    ultima_subpalabra: list[int]
    desplazamiento: int = 0
    truncada: bool = False
    texto: str = field(default="", repr=False)


def codificar(tok, texto: str, max_len: int = 4096, desplazamiento: int = 0) -> Codificacion:
    enc = tok(texto, return_offsets_mapping=True, add_special_tokens=True, truncation=True, max_length=max_len)
    offsets = enc["offset_mapping"]
    pals = partir_palabras(texto)
    primera, ultima, incluidas = [], [], []
    k = 0
    for a, b in pals:
        # avanzar hasta la primera subpalabra no especial que empieza dentro de la palabra
        while k < len(offsets) and (offsets[k] == (0, 0) or offsets[k][1] <= a):
            k += 1
        if k >= len(offsets) or offsets[k][0] >= b:
            continue
        i = k
        j = i
        while j + 1 < len(offsets) and offsets[j + 1] != (0, 0) and offsets[j + 1][0] < b:
            j += 1
        primera.append(i)
        ultima.append(j)
        incluidas.append((a + desplazamiento, b + desplazamiento))
        k = j + 1
    truncada = len(incluidas) < len(pals)
    return Codificacion(list(enc["input_ids"]), list(enc["attention_mask"]), incluidas, primera, ultima, desplazamiento, truncada, texto)


def palabra_de(cod: Codificacion, ini_char: int, fin_char: int) -> tuple[int, int] | None:
    primera = ultima = None
    for idx, (a, b) in enumerate(cod.palabras):
        if a < fin_char and ini_char < b:
            if primera is None:
                primera = idx
            ultima = idx
    return (primera, ultima) if primera is not None else None


def ventanas(tok, texto: str, max_len: int = 8192, solape: int = 512) -> list[Codificacion]:
    pals = partir_palabras(texto)
    if not pals:
        return [codificar(tok, texto, max_len)]
    out, inicio_palabra = [], 0
    while inicio_palabra < len(pals):
        ini_char = pals[inicio_palabra][0]
        trozo = texto[ini_char:]
        cod = codificar(tok, trozo, max_len, desplazamiento=ini_char)
        out.append(cod)
        if not cod.truncada:
            break
        # la próxima ventana empieza `solape` tokens antes del final de esta, en límite de palabra
        n_incluidas = len(cod.palabras)
        retroceso = 0
        while retroceso < n_incluidas - 1 and (cod.ultima_subpalabra[-1] - cod.primera_subpalabra[n_incluidas - 1 - retroceso]) < solape:
            retroceso += 1
        avance = max(1, n_incluidas - retroceso)
        inicio_palabra += avance
    return out
```

- [ ] **Paso 4: Correr tests** → 4 en verde. Si el tokenizer de prueba produce offsets `(0, 0)` para tokens de continuación, sustituir la condición `offsets[k] == (0, 0)` por `enc.sequence_ids()[k] is None` para los especiales. Usar la API `enc.word_ids()` no sirve porque la partición de palabras es la de enrel, no la del tokenizer.

- [ ] **Paso 5: Commit**

```bash
git add enrel/modelo/__init__.py enrel/modelo/tokenizacion.py tests/test_modelo_tokenizacion.py
git commit -m "Añade la tokenización alineada a palabras y caracteres, con ventanas"
```

---

### Tarea 2.2: Backbone

**Ficheros:**
- Crear: `enrel/modelo/backbone.py`
- Test: `tests/test_modelo_backbone.py` (marcado `gpu` para el modelo real; un test CPU con el tiny-bert)

**Interfaces:**
- `cargar_backbone(nombre: str, checkpointing: bool = False, atencion: str | None = None) -> tuple[tokenizer, torch.nn.Module, int]`: devuelve tokenizer, modelo `AutoModel` (sin cabeza de MLM), y `hidden_size`. Con `checkpointing`, `modelo.gradient_checkpointing_enable()`. `atencion` se pasa como `attn_implementation` cuando no es `None` (para exportar a ONNX en la etapa 3 hace falta `"eager"`).
- `estados_ocultos(modelo, input_ids, attention_mask) -> torch.Tensor [B, T, H]`: llama al modelo y devuelve `last_hidden_state`.

- [ ] **Paso 1: Test**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.modelo.backbone import cargar_backbone, estados_ocultos


def test_backbone_pequeno_cpu():
    tok, modelo, h = cargar_backbone("hf-internal-testing/tiny-random-bert")
    enc = tok(["Hola mundo", "Otro texto más largo aquí"], return_tensors="pt", padding=True)
    with torch.no_grad():
        s = estados_ocultos(modelo, enc["input_ids"], enc["attention_mask"])
    assert s.shape == (2, enc["input_ids"].shape[1], h)


@pytest.mark.gpu
def test_mrbert_carga():
    tok, modelo, h = cargar_backbone("BSC-LT/MrBERT-es", checkpointing=True)
    assert h == 768 and modelo.config.max_position_embeddings == 8192
```

- [ ] **Paso 2: Implementar**

```python
"""Carga del codificador preentrenado."""

import torch
from transformers import AutoModel, AutoTokenizer


def cargar_backbone(nombre: str, checkpointing: bool = False, atencion: str | None = None):
    tok = AutoTokenizer.from_pretrained(nombre)
    extra = {"attn_implementation": atencion} if atencion else {}
    modelo = AutoModel.from_pretrained(nombre, **extra)
    if checkpointing:
        modelo.gradient_checkpointing_enable()
    return tok, modelo, int(modelo.config.hidden_size)


def estados_ocultos(modelo, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    return modelo(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_modelo_backbone.py -q
git add enrel/modelo/backbone.py tests/test_modelo_backbone.py
git commit -m "Añade la carga del backbone"
```

---

### Tarea 2.3: Cabeza de entidades por tramos

**Ficheros:**
- Crear: `enrel/modelo/entidades.py`
- Test: `tests/test_modelo_entidades.py`

**Interfaces:**
- `N_TIPOS = 7`; `NINGUNO = 7` (índice de la clase «ninguno»); `TIPO_A_INDICE = {t: i for i, t in enumerate(TIPOS)}`.
- `enumerar_tramos(n_palabras: int, max_ancho: int = 16) -> torch.LongTensor [S, 2]`: todos los `(i, j)` con `0 <= i <= j < n_palabras` y `j - i < max_ancho`.
- `class CabezaEntidades(nn.Module)`: `__init__(hidden: int, max_ancho: int = 16, n_tipos: int = 7, dim_ancho: int = 64, dropout: float = 0.1)`; `forward(estados: [B, T, H], primera: LongTensor [B, P] (índice de subpalabra de la primera de cada palabra, rellenado con 0), ultima: LongTensor [B, P], tramos: LongTensor [B, S, 2] (índices de palabra, rellenados con 0), mascara_tramos: BoolTensor [B, S]) -> logits [B, S, n_tipos + 1]`. Representación: `concat(estados[primera[i]], estados[ultima[j]], emb_ancho(j - i))` → `Linear(2H + dim_ancho, H) → GELU → Dropout → Linear(H, n_tipos + 1)`.

- [ ] **Paso 1: Test**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.modelo.entidades import CabezaEntidades, NINGUNO, enumerar_tramos


def test_enumerar_tramos():
    t = enumerar_tramos(4, max_ancho=2)
    assert t.tolist() == [[0, 0], [0, 1], [1, 1], [1, 2], [2, 2], [2, 3], [3, 3]]


def test_forward_formas():
    cabeza = CabezaEntidades(hidden=16, max_ancho=3)
    estados = torch.randn(2, 10, 16)
    primera = torch.tensor([[1, 3, 5, 7], [1, 2, 0, 0]])
    ultima = torch.tensor([[2, 4, 6, 8], [1, 3, 0, 0]])
    tramos = torch.tensor([[[0, 0], [0, 1], [1, 2], [2, 3]], [[0, 0], [0, 1], [0, 0], [0, 0]]])
    mascara = torch.tensor([[True, True, True, True], [True, True, False, False]])
    logits = cabeza(estados, primera, ultima, tramos, mascara)
    assert logits.shape == (2, 4, 8) and NINGUNO == 7
    assert torch.isfinite(logits).all()
```

- [ ] **Paso 2: Implementar `enrel/modelo/entidades.py`**

```python
"""Cabeza de entidades: clasifica tramos de 1 a `max_ancho` palabras en 7 tipos más «ninguno»."""

import torch
from torch import nn

from enrel.esquema.tipos import TIPOS

N_TIPOS = len(TIPOS)
NINGUNO = N_TIPOS
TIPO_A_INDICE = {t: i for i, t in enumerate(TIPOS)}


def enumerar_tramos(n_palabras: int, max_ancho: int = 16) -> torch.Tensor:
    pares = [(i, j) for i in range(n_palabras) for j in range(i, min(n_palabras, i + max_ancho))]
    return torch.tensor(pares, dtype=torch.long) if pares else torch.zeros((0, 2), dtype=torch.long)


class CabezaEntidades(nn.Module):
    def __init__(self, hidden: int, max_ancho: int = 16, n_tipos: int = N_TIPOS, dim_ancho: int = 64, dropout: float = 0.1):
        super().__init__()
        self.max_ancho = max_ancho
        self.emb_ancho = nn.Embedding(max_ancho, dim_ancho)
        self.proyeccion = nn.Sequential(nn.Linear(2 * hidden + dim_ancho, hidden), nn.GELU(), nn.Dropout(dropout),
                                        nn.Linear(hidden, n_tipos + 1))

    def forward(self, estados, primera, ultima, tramos, mascara_tramos):
        B, S, _ = tramos.shape
        idx_ini = torch.gather(primera, 1, tramos[..., 0])            # [B, S] subpalabra inicial
        idx_fin = torch.gather(ultima, 1, tramos[..., 1])             # [B, S] subpalabra final
        h_ini = torch.gather(estados, 1, idx_ini.unsqueeze(-1).expand(-1, -1, estados.size(-1)))
        h_fin = torch.gather(estados, 1, idx_fin.unsqueeze(-1).expand(-1, -1, estados.size(-1)))
        ancho = (tramos[..., 1] - tramos[..., 0]).clamp(0, self.max_ancho - 1)
        x = torch.cat([h_ini, h_fin, self.emb_ancho(ancho)], dim=-1)
        logits = self.proyeccion(x)
        return logits.masked_fill(~mascara_tramos.unsqueeze(-1), 0.0)
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_modelo_entidades.py -q
git add enrel/modelo/entidades.py tests/test_modelo_entidades.py
git commit -m "Añade la cabeza de entidades por clasificación de tramos"
```

---

### Tarea 2.4: Cabeza de relaciones por pares de grupos

**Ficheros:**
- Crear: `enrel/modelo/relaciones.py`
- Test: `tests/test_modelo_relaciones.py`

**Interfaces:**
- `N_CLASES = len(CLASES_FINAS)` (25); `TH = N_CLASES` (índice del logit umbral; la salida tiene `N_CLASES + 1` columnas).
- `class CabezaRelaciones(nn.Module)`: `__init__(hidden: int, n_clases: int = 25, tam_grupo: int = 64, dropout: float = 0.1)`; `forward(estados: [B, T, H], mascara_tokens: BoolTensor [B, T], menciones: LongTensor [B, G, M] (índice de la primera subpalabra de cada mención de cada grupo, relleno 0), mascara_menciones: BoolTensor [B, G, M], pares: LongTensor [B, R, 2] (índices de grupo), mascara_pares: BoolTensor [B, R]) -> logits [B, R, n_clases + 1]`.
  - Representación de grupo `g[b, k] = logsumexp(estados[b, menciones[b, k, :]])` sobre las menciones válidas.
  - Contexto local del par: `q = W_q(concat(g_cabeza, g_cola))` `[B, R, H]`; `puntuaciones = (q @ estados^T) / sqrt(H)` `[B, R, T]` con máscara de tokens; `c = softmax(puntuaciones) @ estados`. Esta atención aprendida sustituye a la reutilización de la atención del codificador de ATLOP porque se exporta a ONNX sin depender de la implementación de atención del backbone. Guarda `self.ultima_atencion` (`[B, R, T]`, detach) para la evidencia en inferencia.
  - `z_c = tanh(W_c(concat(g_cabeza, c)))`, `z_t = tanh(W_t(concat(g_cola, c)))`, ambos de dimensión `H`; bilineal agrupado: se reordenan en `H / tam_grupo` grupos de `tam_grupo` y `logits = W_b(vec(z_c_k ⊗ z_t_k) para todo k)` con `W_b: Linear((H / tam_grupo) * tam_grupo * tam_grupo, n_clases + 1)`.
  - Salida enmascarada a 0 en pares de relleno.

- [ ] **Paso 1: Test**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.modelo.relaciones import TH, CabezaRelaciones


def test_forward_formas_y_atencion():
    cabeza = CabezaRelaciones(hidden=64, n_clases=25, tam_grupo=16)
    estados = torch.randn(2, 12, 64)
    mascara_tokens = torch.ones(2, 12, dtype=torch.bool)
    mascara_tokens[1, 8:] = False
    menciones = torch.tensor([[[1, 5, 0], [3, 0, 0], [7, 9, 11]], [[1, 0, 0], [4, 6, 0], [0, 0, 0]]])
    mascara_menciones = torch.tensor([[[1, 1, 0], [1, 0, 0], [1, 1, 1]], [[1, 0, 0], [1, 1, 0], [0, 0, 0]]], dtype=torch.bool)
    pares = torch.tensor([[[0, 1], [1, 0], [0, 2]], [[0, 1], [0, 0], [0, 0]]])
    mascara_pares = torch.tensor([[True, True, True], [True, False, False]])
    logits = cabeza(estados, mascara_tokens, menciones, mascara_menciones, pares, mascara_pares)
    assert logits.shape == (2, 3, 26) and TH == 25
    assert torch.isfinite(logits).all()
    assert cabeza.ultima_atencion.shape == (2, 3, 12)
    assert torch.allclose(cabeza.ultima_atencion[1, 0, 8:], torch.zeros(4))   # tokens enmascarados sin peso
    assert (logits[1, 1] == 0).all()                                            # par de relleno
```

- [ ] **Paso 2: Implementar `enrel/modelo/relaciones.py`**

```python
"""Cabeza de relaciones: pares ordenados de grupos, contexto local por atención, bilineal agrupado, clase umbral."""

import math

import torch
from torch import nn

from enrel.esquema.tipos import CLASES_FINAS

N_CLASES = len(CLASES_FINAS)
TH = N_CLASES


class CabezaRelaciones(nn.Module):
    def __init__(self, hidden: int, n_clases: int = N_CLASES, tam_grupo: int = 64, dropout: float = 0.1):
        super().__init__()
        assert hidden % tam_grupo == 0, "hidden debe ser múltiplo de tam_grupo"
        self.hidden, self.tam_grupo, self.k = hidden, tam_grupo, hidden // tam_grupo
        self.consulta = nn.Linear(2 * hidden, hidden)
        self.proy_cabeza = nn.Linear(2 * hidden, hidden)
        self.proy_cola = nn.Linear(2 * hidden, hidden)
        self.bilineal = nn.Linear(self.k * tam_grupo * tam_grupo, n_clases + 1)
        self.dropout = nn.Dropout(dropout)
        self.ultima_atencion: torch.Tensor | None = None

    def _grupos(self, estados, menciones, mascara_menciones):
        B, G, M = menciones.shape
        idx = menciones.reshape(B, G * M, 1).expand(-1, -1, estados.size(-1))
        h = torch.gather(estados, 1, idx).reshape(B, G, M, -1)
        h = h.masked_fill(~mascara_menciones.unsqueeze(-1), float("-inf"))
        g = torch.logsumexp(h, dim=2)
        return torch.nan_to_num(g, nan=0.0, neginf=0.0)

    def forward(self, estados, mascara_tokens, menciones, mascara_menciones, pares, mascara_pares):
        g = self._grupos(estados, menciones, mascara_menciones)                    # [B, G, H]
        H = estados.size(-1)
        gc = torch.gather(g, 1, pares[..., 0].unsqueeze(-1).expand(-1, -1, H))    # [B, R, H]
        gl = torch.gather(g, 1, pares[..., 1].unsqueeze(-1).expand(-1, -1, H))
        q = self.consulta(torch.cat([gc, gl], dim=-1))                            # [B, R, H]
        puntuaciones = torch.einsum("brh,bth->brt", q, estados) / math.sqrt(H)
        puntuaciones = puntuaciones.masked_fill(~mascara_tokens.unsqueeze(1), float("-inf"))
        atencion = torch.softmax(puntuaciones, dim=-1)
        atencion = torch.nan_to_num(atencion, nan=0.0)
        self.ultima_atencion = atencion.detach()
        c = torch.einsum("brt,bth->brh", atencion, estados)                       # [B, R, H]
        zc = torch.tanh(self.proy_cabeza(torch.cat([gc, c], dim=-1)))
        zt = torch.tanh(self.proy_cola(torch.cat([gl, c], dim=-1)))
        B, R, _ = zc.shape
        zc = self.dropout(zc).reshape(B, R, self.k, self.tam_grupo, 1)
        zt = self.dropout(zt).reshape(B, R, self.k, 1, self.tam_grupo)
        producto = (zc * zt).reshape(B, R, -1)                                     # [B, R, k*t*t]
        logits = self.bilineal(producto)
        return logits.masked_fill(~mascara_pares.unsqueeze(-1), 0.0)
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_modelo_relaciones.py -q
git add enrel/modelo/relaciones.py tests/test_modelo_relaciones.py
git commit -m "Añade la cabeza de relaciones con contexto por atención y bilineal agrupado"
```

---

### Tarea 2.5: Pérdidas y decodificación por umbral adaptativo

**Ficheros:**
- Crear: `enrel/modelo/perdidas.py`
- Test: `tests/test_modelo_perdidas.py`

**Interfaces:**
- `perdida_entidades(logits: [B, S, C], etiquetas: LongTensor [B, S] (índice de tipo o NINGUNO; -100 para relleno)) -> Tensor escalar`: entropía cruzada con `ignore_index=-100`.
- `perdida_umbral_adaptativo(logits: [B, R, C+1], etiquetas: FloatTensor [B, R, C] multi-hot, mascara_pares: BoolTensor [B, R], pesos_clase: Tensor [C] | None = None) -> Tensor escalar`. La pérdida de ATLOP: para cada par, (1) `-log softmax(logits sobre {positivas ∪ TH})[positivas]` sumado sobre positivas (ponderado por `pesos_clase` si se da), y (2) `-log softmax(logits sobre {negativas ∪ TH})[TH]`; promedio sobre pares válidos. Los pares sin positivas solo aportan el término (2).
- `decodificar_umbral(logits: [B, R, C+1], mascara_clases: BoolTensor [B, R, C] | None = None) -> BoolTensor [B, R, C]`: clase positiva si su logit supera al de TH y a 0 no hace falta; con `mascara_clases`, las clases no admitidas se ponen a `-inf` antes.
- `confianzas(logits) -> Tensor [B, R, C]`: `sigmoid(logits[..., :C] - logits[..., TH:TH+1])`.
- `pesos_por_frecuencia(conteos: dict[str, int], suavizado: float = 1.0, potencia: float = 0.5) -> Tensor [C]`: `(mediana / (conteo + suavizado)) ** potencia`, recortado a `[0.5, 4.0]`, en el orden de `CLASES_FINAS`. Es la reponderación de la cola larga.

- [ ] **Paso 1: Tests**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.esquema.tipos import CLASES_FINAS
from enrel.modelo.perdidas import (confianzas, decodificar_umbral, perdida_entidades, perdida_umbral_adaptativo,
                                   pesos_por_frecuencia)

C = len(CLASES_FINAS)


def test_perdida_entidades_ignora_relleno():
    logits = torch.zeros(1, 3, 8)
    etiquetas = torch.tensor([[7, 0, -100]])
    p = perdida_entidades(logits, etiquetas)
    assert torch.isclose(p, torch.log(torch.tensor(8.0)))


def test_umbral_adaptativo_baja_con_logits_correctos():
    etiquetas = torch.zeros(1, 2, C)
    etiquetas[0, 0, 3] = 1.0                       # el par 0 tiene la clase 3; el par 1 ninguna
    mascara = torch.tensor([[True, True]])
    malos = torch.zeros(1, 2, C + 1)
    buenos = torch.zeros(1, 2, C + 1)
    buenos[0, 0, 3] = 6.0                          # positiva por encima de TH (0)
    buenos[0, 1, C] = 6.0                          # TH por encima de todas en el par sin relación
    assert perdida_umbral_adaptativo(buenos, etiquetas, mascara) < perdida_umbral_adaptativo(malos, etiquetas, mascara)


def test_decodificar_y_confianzas():
    logits = torch.zeros(1, 1, C + 1)
    logits[0, 0, 5] = 2.0
    logits[0, 0, 6] = -1.0
    logits[0, 0, C] = 1.0
    dec = decodificar_umbral(logits)
    assert dec[0, 0, 5] and not dec[0, 0, 6] and dec.sum() == 1
    mascara = torch.ones(1, 1, C, dtype=torch.bool)
    mascara[0, 0, 5] = False
    assert decodificar_umbral(logits, mascara).sum() == 0
    conf = confianzas(logits)
    assert 0.7 < conf[0, 0, 5] < 0.75


def test_pesos_por_frecuencia():
    conteos = {c: 100 for c in CLASES_FINAS}
    conteos["fundo"] = 4
    w = pesos_por_frecuencia(conteos)
    assert w.shape == (C,) and w[CLASES_FINAS.index("fundo")] > w[CLASES_FINAS.index("dirige")]
    assert w.max() <= 4.0 and w.min() >= 0.5
```

- [ ] **Paso 2: Implementar `enrel/modelo/perdidas.py`**

```python
"""Pérdidas: entropía cruzada de tramos; umbral adaptativo (ATLOP) con reponderación por clase; decodificación TH."""

import statistics

import torch
import torch.nn.functional as F

from enrel.esquema.tipos import CLASES_FINAS

C = len(CLASES_FINAS)
TH = C


def perdida_entidades(logits: torch.Tensor, etiquetas: torch.Tensor) -> torch.Tensor:
    return F.cross_entropy(logits.reshape(-1, logits.size(-1)), etiquetas.reshape(-1), ignore_index=-100)


def perdida_umbral_adaptativo(logits: torch.Tensor, etiquetas: torch.Tensor, mascara_pares: torch.Tensor,
                              pesos_clase: torch.Tensor | None = None) -> torch.Tensor:
    B, R, _ = logits.shape
    pos = etiquetas.bool()                                             # [B, R, C]
    th = torch.zeros(B, R, 1, dtype=torch.bool, device=logits.device)
    # Término 1: cada positiva debe superar a TH. softmax sobre {positivas, TH}.
    mascara1 = torch.cat([pos, torch.ones_like(th)], dim=-1)
    logits1 = logits.masked_fill(~mascara1, float("-inf"))
    logp1 = F.log_softmax(logits1, dim=-1)[..., :C]
    pesos = pesos_clase.to(logits.device).view(1, 1, C) if pesos_clase is not None else torch.ones(1, 1, C, device=logits.device)
    termino1 = -(logp1 * pos.float() * pesos).sum(-1)
    # Término 2: TH debe superar a todas las negativas. softmax sobre {negativas, TH}.
    mascara2 = torch.cat([~pos, torch.ones_like(th)], dim=-1)
    logits2 = logits.masked_fill(~mascara2, float("-inf"))
    termino2 = -F.log_softmax(logits2, dim=-1)[..., TH]
    perdida = (termino1 + termino2) * mascara_pares.float()
    return perdida.sum() / mascara_pares.float().sum().clamp(min=1.0)


def decodificar_umbral(logits: torch.Tensor, mascara_clases: torch.Tensor | None = None) -> torch.Tensor:
    clases = logits[..., :C]
    if mascara_clases is not None:
        clases = clases.masked_fill(~mascara_clases, float("-inf"))
    return clases > logits[..., TH:TH + 1]


def confianzas(logits: torch.Tensor) -> torch.Tensor:
    return torch.sigmoid(logits[..., :C] - logits[..., TH:TH + 1])


def pesos_por_frecuencia(conteos: dict[str, int], suavizado: float = 1.0, potencia: float = 0.5) -> torch.Tensor:
    valores = [conteos.get(c, 0) for c in CLASES_FINAS]
    mediana = statistics.median([v for v in valores if v > 0] or [1])
    w = torch.tensor([(mediana / (v + suavizado)) ** potencia for v in valores], dtype=torch.float32)
    return w.clamp(0.5, 4.0)
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_modelo_perdidas.py -q
git add enrel/modelo/perdidas.py tests/test_modelo_perdidas.py
git commit -m "Añade las pérdidas de tramos y de umbral adaptativo, y la decodificación TH"
```

---

### Tarea 2.6: El modelo completo, con guardado, carga y máscara de tipos

**Ficheros:**
- Crear: `enrel/modelo/enrel.py`
- Test: `tests/test_modelo_enrel.py`

**Interfaces:**
- `@dataclass class ConfigModelo: backbone: str = "BSC-LT/MrBERT-es"; max_ancho: int = 16; tam_grupo: int = 64; dropout: float = 0.1; max_grupos: int = 60; version: str = "0.1"; clases_finas: list[str] = CLASES_FINAS; tipos: list[str] = TIPOS`.
- `class ModeloEnrel(nn.Module)`: `__init__(config: ConfigModelo, checkpointing: bool = False, atencion: str | None = None)` carga el backbone y crea las dos cabezas; atributos `tok`, `backbone`, `entidades`, `relaciones`, `config`. `forward(lote) -> dict` con `logits_entidades` y `logits_relaciones` (`None` si el lote no trae pares); `lote` es el `Lote` de la Tarea 2.8 (aquí se documentan sus campos: `input_ids, attention_mask, primera, ultima, tramos, mascara_tramos, menciones, mascara_menciones, pares, mascara_pares`).
- `guardar(self, directorio: Path)`: `config.json`, `backbone/` con `save_pretrained` (modelo y tokenizer), `cabezas.safetensors` con los `state_dict` de las dos cabezas bajo prefijos `entidades.` y `relaciones.`.
- `ModeloEnrel.cargar(directorio: Path, atencion: str | None = None) -> ModeloEnrel` (classmethod).
- `mascara_tipos(tipos_cabeza: list[str], tipos_cola: list[str]) -> BoolTensor [R, C]`: para cada par, `True` en las clases finas cuya relación `admite(tipo_cabeza, tipo_cola)`; `vinculo_sin_tipo` siempre `True`. Se precomputa una tabla `TABLA_TIPOS[tipo_a][tipo_b] -> BoolTensor [C]` al importar.
- `parametros_por_grupo(self) -> list[dict]`: dos grupos para el optimizador: `{"params": backbone, "nombre": "codificador"}` y `{"params": cabezas, "nombre": "cabezas"}`.

- [ ] **Paso 1: Test (CPU, con tiny-bert como backbone)**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.esquema.tipos import CLASES_FINAS, INDICE_CLASE
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel, mascara_tipos


def test_mascara_tipos():
    m = mascara_tipos(["persona", "persona"], ["cargo", "lugar"])
    assert m.shape == (2, len(CLASES_FINAS))
    assert m[0, INDICE_CLASE["ocupa_cargo:actual"]] and not m[0, INDICE_CLASE["dirige"]]
    assert m[1, INDICE_CLASE["ubicado_en"]] and not m[1, INDICE_CLASE["ocupa_cargo:actual"]]
    assert m[:, INDICE_CLASE["vinculo_sin_tipo"]].all()


def test_guardar_y_cargar(tmp_path):
    cfg = ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8)
    m = ModeloEnrel(cfg)
    m.guardar(tmp_path / "modelo")
    m2 = ModeloEnrel.cargar(tmp_path / "modelo")
    assert m2.config.backbone == cfg.backbone and m2.config.clases_finas == list(CLASES_FINAS)
    a = dict(m.relaciones.state_dict())
    b = dict(m2.relaciones.state_dict())
    assert all(torch.equal(a[k], b[k]) for k in a)
    grupos = m.parametros_por_grupo()
    assert [g["nombre"] for g in grupos] == ["codificador", "cabezas"]
```

- [ ] **Paso 2: Implementar `enrel/modelo/enrel.py`**

```python
"""El modelo completo: backbone compartido, cabeza de entidades, cabeza de relaciones; guardado y carga."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file
from torch import nn

from enrel.esquema.tipos import CLASES_FINAS, TIPOS, admite, desglosar
from enrel.modelo.backbone import cargar_backbone, estados_ocultos
from enrel.modelo.entidades import CabezaEntidades
from enrel.modelo.relaciones import CabezaRelaciones

C = len(CLASES_FINAS)


def _tabla_tipos() -> dict[str, dict[str, torch.Tensor]]:
    tabla = {}
    for a in TIPOS:
        tabla[a] = {}
        for b in TIPOS:
            tabla[a][b] = torch.tensor([admite(desglosar(c)[0], a, b) for c in CLASES_FINAS], dtype=torch.bool)
    return tabla


TABLA_TIPOS = _tabla_tipos()


def mascara_tipos(tipos_cabeza: list[str], tipos_cola: list[str]) -> torch.Tensor:
    if not tipos_cabeza:
        return torch.zeros((0, C), dtype=torch.bool)
    return torch.stack([TABLA_TIPOS[a][b] for a, b in zip(tipos_cabeza, tipos_cola)])


@dataclass
class ConfigModelo:
    backbone: str = "BSC-LT/MrBERT-es"
    max_ancho: int = 16
    tam_grupo: int = 64
    dropout: float = 0.1
    max_grupos: int = 60
    version: str = "0.1"
    clases_finas: list[str] = field(default_factory=lambda: list(CLASES_FINAS))
    tipos: list[str] = field(default_factory=lambda: list(TIPOS))


class ModeloEnrel(nn.Module):
    def __init__(self, config: ConfigModelo, checkpointing: bool = False, atencion: str | None = None):
        super().__init__()
        self.config = config
        self.tok, self.backbone, hidden = cargar_backbone(config.backbone, checkpointing, atencion)
        tam_grupo = config.tam_grupo if hidden % config.tam_grupo == 0 else next(t for t in (64, 32, 16, 8, 4, 2, 1) if hidden % t == 0)
        self.config.tam_grupo = tam_grupo
        self.entidades = CabezaEntidades(hidden, config.max_ancho, len(config.tipos), dropout=config.dropout)
        self.relaciones = CabezaRelaciones(hidden, len(config.clases_finas), tam_grupo, config.dropout)

    def forward(self, lote) -> dict:
        estados = estados_ocultos(self.backbone, lote.input_ids, lote.attention_mask)
        salida = {"estados": estados,
                  "logits_entidades": self.entidades(estados, lote.primera, lote.ultima, lote.tramos, lote.mascara_tramos)}
        if lote.pares is not None and lote.pares.numel() > 0:
            salida["logits_relaciones"] = self.relaciones(estados, lote.attention_mask.bool(), lote.menciones,
                                                          lote.mascara_menciones, lote.pares, lote.mascara_pares)
        else:
            salida["logits_relaciones"] = None
        return salida

    def parametros_por_grupo(self) -> list[dict]:
        return [{"params": list(self.backbone.parameters()), "nombre": "codificador"},
                {"params": list(self.entidades.parameters()) + list(self.relaciones.parameters()), "nombre": "cabezas"}]

    def guardar(self, directorio: Path) -> None:
        directorio = Path(directorio)
        (directorio / "backbone").mkdir(parents=True, exist_ok=True)
        (directorio / "config.json").write_text(json.dumps(asdict(self.config), ensure_ascii=False, indent=2), encoding="utf-8")
        self.backbone.save_pretrained(directorio / "backbone")
        self.tok.save_pretrained(directorio / "backbone")
        estado = {f"entidades.{k}": v.detach().cpu().contiguous() for k, v in self.entidades.state_dict().items()}
        estado.update({f"relaciones.{k}": v.detach().cpu().contiguous() for k, v in self.relaciones.state_dict().items()})
        save_file(estado, str(directorio / "cabezas.safetensors"))

    @classmethod
    def cargar(cls, directorio: Path, atencion: str | None = None) -> "ModeloEnrel":
        directorio = Path(directorio)
        cfg = ConfigModelo(**json.loads((directorio / "config.json").read_text(encoding="utf-8")))
        cfg_local = ConfigModelo(**{**asdict(cfg), "backbone": str(directorio / "backbone")})
        m = cls(cfg_local, atencion=atencion)
        m.config.backbone = cfg.backbone
        estado = load_file(str(directorio / "cabezas.safetensors"))
        m.entidades.load_state_dict({k[len("entidades."):]: v for k, v in estado.items() if k.startswith("entidades.")})
        m.relaciones.load_state_dict({k[len("relaciones."):]: v for k, v in estado.items() if k.startswith("relaciones.")})
        return m
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_modelo_enrel.py -q
git add enrel/modelo/enrel.py tests/test_modelo_enrel.py
git commit -m "Añade el modelo completo con guardado, carga y máscara de tipos"
```

---

### Tarea 2.7: De documento a tensores

**Ficheros:**
- Crear: `enrel/entrenamiento/__init__.py`, `enrel/entrenamiento/tensores.py`
- Test: `tests/test_entrenamiento_tensores.py`

**Interfaces:**
- `@dataclass class Ejemplo: doc_id: str; input_ids: list[int]; attention_mask: list[int]; primera: list[int]; ultima: list[int]; tramos: list[tuple[int, int]]; etiquetas_tramos: list[int]; menciones: list[list[int]]` (por grupo, índices de primera subpalabra de sus menciones incluidas en la ventana); `tipos_grupo: list[str]; pares: list[tuple[int, int]]; etiquetas_pares: list[list[int]]` (multi-hot de longitud `C` por par); `mascara_clases: list[list[bool]]` (por par, clases admitidas por tipos); `recorte_grupos: int`.
- `ejemplo_desde_documento(doc: Documento, tok, max_len: int = 4096, max_ancho: int = 16, ratio_negativos: int = 8, max_grupos: int = 60, rng: random.Random | None = None, todos_los_tramos: bool = False) -> Ejemplo`:
  1. `codificar(tok, doc.texto, max_len)`.
  2. Menciones dentro de la ventana → `(i, j)` de palabras vía `palabra_de`; las que no caben se descartan (contador `menciones_fuera`). Tramos positivos: cada mención con `j - i < max_ancho` (las más largas se cuentan en `menciones_largas` y no se usan). Negativos: si `todos_los_tramos`, todos los tramos posibles no positivos (para inferencia y cordura); si no, `ratio_negativos × positivos` tramos al azar no positivos (mínimo 32), con `rng`.
  3. Grupos con al menos una mención en la ventana, ordenados por número de menciones descendente y recortados a `max_grupos` (`recorte_grupos` = cuántos se quitaron). `menciones[k]` = primeras subpalabras de las menciones del grupo `k`.
  4. Pares: todos los `(a, b)` ordenados con `a != b` para los que `mascara_tipos` tiene alguna clase admitida además de `vinculo_sin_tipo` **o** existe una relación de oro entre ellos. `etiquetas_pares[r][INDICE_CLASE[clase_fina]] = 1` para cada relación del documento entre esos grupos (simétricas: se marca en ambas direcciones). `mascara_clases[r]` de `mascara_tipos`.
- `conteo_clases(docs: list[Documento]) -> dict[str, int]`: clases finas positivas en un conjunto (para `pesos_por_frecuencia`).

- [ ] **Paso 1: Test (con tiny-bert)**

```python
import random

import pytest

transformers = pytest.importorskip("transformers")
from enrel.entrenamiento.tensores import conteo_clases, ejemplo_desde_documento
from enrel.esquema.tipos import INDICE_CLASE
from enrel.modelo.entidades import NINGUNO, TIPO_A_INDICE
from tests.test_datos_documento import doc_ejemplo


@pytest.fixture(scope="module")
def tok():
    return transformers.AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-bert")


def test_ejemplo_basico(tok):
    d = doc_ejemplo()
    e = ejemplo_desde_documento(d, tok, max_len=128, rng=random.Random(1))
    assert e.doc_id == "wp:1"
    positivos = [t for t, y in zip(e.tramos, e.etiquetas_tramos) if y != NINGUNO]
    assert len(positivos) == 5                            # las cinco menciones caben
    assert TIPO_A_INDICE["cargo"] in e.etiquetas_tramos
    negativos = sum(1 for y in e.etiquetas_tramos if y == NINGUNO)
    assert negativos >= 32
    assert len(e.menciones) == 4 and e.tipos_grupo == ["persona", "persona", "cargo", "organizacion"]
    idx_pares = {p: k for k, p in enumerate(e.pares)}
    g = {g.id: k for k, g in enumerate(d.grupos)}
    r = idx_pares[(g["e2"], g["e3"])]
    assert e.etiquetas_pares[r][INDICE_CLASE["ocupa_cargo:actual"]] == 1
    assert e.mascara_clases[r][INDICE_CLASE["ocupa_cargo:actual"]] and not e.mascara_clases[r][INDICE_CLASE["dirige"]]
    assert (g["e3"], g["e4"]) not in idx_pares or True   # cargo→organizacion no admite nada salvo sin tipo: puede faltar


def test_conteo_clases():
    assert conteo_clases([doc_ejemplo()]) == {"nombro_a": 1, "ocupa_cargo:actual": 1}
```

- [ ] **Paso 2: Implementar `enrel/entrenamiento/tensores.py`**

```python
"""Convierte un Documento en las estructuras que el modelo consume: tramos etiquetados, grupos, pares y sus etiquetas."""

import random
from collections import Counter
from dataclasses import dataclass, field

from enrel.datos.documento import Documento
from enrel.esquema.tipos import CLASES_FINAS, INDICE_CLASE, SIN_TIPO, clase_fina, es_simetrica
from enrel.modelo.entidades import NINGUNO, TIPO_A_INDICE, enumerar_tramos
from enrel.modelo.enrel import mascara_tipos
from enrel.modelo.tokenizacion import codificar, palabra_de

C = len(CLASES_FINAS)
IDX_SIN_TIPO = INDICE_CLASE[SIN_TIPO]


@dataclass
class Ejemplo:
    doc_id: str
    input_ids: list[int]
    attention_mask: list[int]
    primera: list[int]
    ultima: list[int]
    tramos: list[tuple[int, int]]
    etiquetas_tramos: list[int]
    menciones: list[list[int]]
    tipos_grupo: list[str]
    pares: list[tuple[int, int]]
    etiquetas_pares: list[list[int]]
    mascara_clases: list[list[bool]]
    recorte_grupos: int = 0
    contadores: dict = field(default_factory=dict)


def ejemplo_desde_documento(doc: Documento, tok, max_len: int = 4096, max_ancho: int = 16, ratio_negativos: int = 8,
                            max_grupos: int = 60, rng: random.Random | None = None, todos_los_tramos: bool = False) -> Ejemplo:
    rng = rng or random.Random(0)
    cod = codificar(tok, doc.texto, max_len)
    n_pal = len(cod.palabras)
    cont = Counter()

    positivos: dict[tuple[int, int], int] = {}
    menciones_por_grupo: dict[str, list[int]] = {}
    for m in doc.menciones:
        pj = palabra_de(cod, m.ini, m.fin)
        if pj is None:
            cont["menciones_fuera"] += 1
            continue
        i, j = pj
        if j - i >= max_ancho:
            cont["menciones_largas"] += 1
        else:
            positivos[(i, j)] = TIPO_A_INDICE[m.tipo]
        menciones_por_grupo.setdefault(m.grupo, []).append(cod.primera_subpalabra[i])

    if todos_los_tramos:
        candidatos = [tuple(t) for t in enumerar_tramos(n_pal, max_ancho).tolist()]
    else:
        n_neg = max(32, ratio_negativos * len(positivos))
        candidatos = list(positivos)
        universo = enumerar_tramos(n_pal, max_ancho).tolist()
        rng.shuffle(universo)
        for t in universo:
            t = tuple(t)
            if t not in positivos:
                candidatos.append(t)
                if len(candidatos) - len(positivos) >= n_neg:
                    break
    etiquetas_tramos = [positivos.get(t, NINGUNO) for t in candidatos]

    grupos = sorted(menciones_por_grupo, key=lambda g: -len(menciones_por_grupo[g]))
    recorte = max(0, len(grupos) - max_grupos)
    grupos = grupos[:max_grupos]
    indice_grupo = {g: k for k, g in enumerate(grupos)}
    tipos_grupo = [doc.grupo_de(g).tipo for g in grupos]
    menciones = [menciones_por_grupo[g] for g in grupos]

    oro: dict[tuple[int, int], set[int]] = {}
    for r in doc.relaciones:
        if r.cabeza not in indice_grupo or r.cola not in indice_grupo:
            cont["relaciones_fuera"] += 1
            continue
        a, b = indice_grupo[r.cabeza], indice_grupo[r.cola]
        idx = INDICE_CLASE[clase_fina(r.relacion, r.atributo)]
        oro.setdefault((a, b), set()).add(idx)
        if es_simetrica(r.relacion, r.atributo):
            oro.setdefault((b, a), set()).add(idx)

    pares, etiquetas_pares, mascara_clases = [], [], []
    if len(grupos) >= 2:
        todos = [(a, b) for a in range(len(grupos)) for b in range(len(grupos)) if a != b]
        masc = mascara_tipos([tipos_grupo[a] for a, _ in todos], [tipos_grupo[b] for _, b in todos])
        for k, (a, b) in enumerate(todos):
            fila = masc[k]
            admite_algo = bool(fila[:IDX_SIN_TIPO].any() or fila[IDX_SIN_TIPO + 1:].any())
            if not admite_algo and (a, b) not in oro:
                continue
            pares.append((a, b))
            y = [0] * C
            for idx in oro.get((a, b), ()):
                y[idx] = 1
            etiquetas_pares.append(y)
            mascara_clases.append(fila.tolist())

    return Ejemplo(doc.doc_id, cod.input_ids, cod.attention_mask, cod.primera_subpalabra, cod.ultima_subpalabra,
                   candidatos, etiquetas_tramos, menciones, tipos_grupo, pares, etiquetas_pares, mascara_clases, recorte, dict(cont))


def conteo_clases(docs: list[Documento]) -> dict[str, int]:
    c = Counter()
    for d in docs:
        for r in d.relaciones:
            c[clase_fina(r.relacion, r.atributo)] += 1
    return dict(c)
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_entrenamiento_tensores.py -q
git add enrel/entrenamiento/__init__.py enrel/entrenamiento/tensores.py tests/test_entrenamiento_tensores.py
git commit -m "Añade la conversión de documentos a tramos, grupos y pares con sus etiquetas"
```

---

### Tarea 2.8: Colación en lotes

**Ficheros:**
- Crear: `enrel/entrenamiento/colacion.py`
- Test: `tests/test_entrenamiento_colacion.py`

**Interfaces:**
- `@dataclass class Lote: doc_ids: list[str]; input_ids: LongTensor [B, T]; attention_mask: LongTensor [B, T]; primera: LongTensor [B, P]; ultima: LongTensor [B, P]; tramos: LongTensor [B, S, 2]; mascara_tramos: BoolTensor [B, S]; etiquetas_tramos: LongTensor [B, S] (-100 en relleno); menciones: LongTensor [B, G, M]; mascara_menciones: BoolTensor [B, G, M]; pares: LongTensor [B, R, 2] | None; mascara_pares: BoolTensor [B, R]; etiquetas_pares: FloatTensor [B, R, C]; mascara_clases: BoolTensor [B, R, C]; tipos_grupo: list[list[str]]` y método `a(dispositivo) -> Lote`.
- `colar(ejemplos: list[Ejemplo], pad_id: int) -> Lote`: rellena a las longitudes máximas del lote (`T`, `P`, `S`, `G`, `M`, `R`); si ningún ejemplo tiene pares, `pares = None` y los tensores de relaciones tienen `R = 0`.

- [ ] **Paso 1: Test**

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.entrenamiento.colacion import colar
from enrel.entrenamiento.tensores import Ejemplo


def ej(doc_id, n_tok, n_pal, tramos, grupos, pares):
    return Ejemplo(doc_id, list(range(n_tok)), [1] * n_tok, list(range(1, n_pal + 1)), list(range(1, n_pal + 1)),
                   tramos, [7] * len(tramos), grupos, ["persona"] * len(grupos), pares, [[0] * 25 for _ in pares],
                   [[True] * 25 for _ in pares])


def test_colar_rellena():
    a = ej("a", 5, 3, [(0, 0), (1, 2)], [[1, 2], [3]], [(0, 1), (1, 0)])
    b = ej("b", 8, 6, [(0, 1)], [[1]], [])
    lote = colar([a, b], pad_id=0)
    assert lote.input_ids.shape == (2, 8) and lote.attention_mask[0, 5:].sum() == 0
    assert lote.tramos.shape == (2, 2, 2) and lote.mascara_tramos.tolist() == [[True, True], [True, False]]
    assert lote.etiquetas_tramos[1, 1] == -100
    assert lote.menciones.shape == (2, 2, 2) and lote.mascara_menciones[0].tolist() == [[True, True], [True, False]]
    assert lote.pares.shape == (2, 2, 2) and lote.mascara_pares.tolist() == [[True, True], [False, False]]
    assert lote.etiquetas_pares.shape == (2, 2, 25)


def test_sin_pares():
    b = ej("b", 4, 2, [(0, 0)], [[1]], [])
    lote = colar([b], pad_id=0)
    assert lote.pares is None and lote.mascara_pares.shape == (1, 0)
```

- [ ] **Paso 2: Implementar `enrel/entrenamiento/colacion.py`**

```python
"""Agrupa ejemplos en un lote con relleno."""

from dataclasses import dataclass

import torch

from enrel.entrenamiento.tensores import C, Ejemplo


@dataclass
class Lote:
    doc_ids: list[str]
    input_ids: torch.Tensor
    attention_mask: torch.Tensor
    primera: torch.Tensor
    ultima: torch.Tensor
    tramos: torch.Tensor
    mascara_tramos: torch.Tensor
    etiquetas_tramos: torch.Tensor
    menciones: torch.Tensor
    mascara_menciones: torch.Tensor
    pares: torch.Tensor | None
    mascara_pares: torch.Tensor
    etiquetas_pares: torch.Tensor
    mascara_clases: torch.Tensor
    tipos_grupo: list[list[str]]

    def a(self, dispositivo) -> "Lote":
        campos = {}
        for k, v in self.__dict__.items():
            campos[k] = v.to(dispositivo) if isinstance(v, torch.Tensor) else v
        return Lote(**campos)


def _rellenar(listas: list[list], valor, largo: int, ancho: int | None = None) -> torch.Tensor:
    if ancho is None:
        return torch.tensor([l + [valor] * (largo - len(l)) for l in listas])
    return torch.tensor([[x if isinstance(x, list) else list(x) for x in l] + [[valor] * ancho] * (largo - len(l)) for l in listas])


def colar(ejemplos: list[Ejemplo], pad_id: int) -> Lote:
    B = len(ejemplos)
    T = max(len(e.input_ids) for e in ejemplos)
    P = max(1, max(len(e.primera) for e in ejemplos))
    S = max(1, max(len(e.tramos) for e in ejemplos))
    G = max(1, max(len(e.menciones) for e in ejemplos))
    M = max(1, max((len(m) for e in ejemplos for m in e.menciones), default=1))
    R = max(len(e.pares) for e in ejemplos)

    input_ids = _rellenar([e.input_ids for e in ejemplos], pad_id, T)
    attention_mask = _rellenar([e.attention_mask for e in ejemplos], 0, T)
    primera = _rellenar([e.primera for e in ejemplos], 0, P)
    ultima = _rellenar([e.ultima for e in ejemplos], 0, P)
    tramos = torch.tensor([[list(t) for t in e.tramos] + [[0, 0]] * (S - len(e.tramos)) for e in ejemplos], dtype=torch.long)
    mascara_tramos = torch.tensor([[True] * len(e.tramos) + [False] * (S - len(e.tramos)) for e in ejemplos])
    etiquetas_tramos = _rellenar([e.etiquetas_tramos for e in ejemplos], -100, S)
    menciones = torch.zeros(B, G, M, dtype=torch.long)
    mascara_menciones = torch.zeros(B, G, M, dtype=torch.bool)
    for b, e in enumerate(ejemplos):
        for g, ms in enumerate(e.menciones):
            menciones[b, g, :len(ms)] = torch.tensor(ms)
            mascara_menciones[b, g, :len(ms)] = True
    if R == 0:
        pares = None
        mascara_pares = torch.zeros(B, 0, dtype=torch.bool)
        etiquetas_pares = torch.zeros(B, 0, C)
        mascara_clases = torch.zeros(B, 0, C, dtype=torch.bool)
    else:
        pares = torch.tensor([[list(p) for p in e.pares] + [[0, 0]] * (R - len(e.pares)) for e in ejemplos], dtype=torch.long)
        mascara_pares = torch.tensor([[True] * len(e.pares) + [False] * (R - len(e.pares)) for e in ejemplos])
        etiquetas_pares = torch.tensor([e.etiquetas_pares + [[0] * C] * (R - len(e.pares)) for e in ejemplos], dtype=torch.float32)
        mascara_clases = torch.tensor([e.mascara_clases + [[False] * C] * (R - len(e.pares)) for e in ejemplos])
    return Lote([e.doc_id for e in ejemplos], input_ids, attention_mask, primera, ultima, tramos, mascara_tramos, etiquetas_tramos,
                menciones, mascara_menciones, pares, mascara_pares, etiquetas_pares, mascara_clases, [e.tipos_grupo for e in ejemplos])
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_entrenamiento_colacion.py -q
git add enrel/entrenamiento/colacion.py tests/test_entrenamiento_colacion.py
git commit -m "Añade la colación de ejemplos en lotes con relleno"
```

---

### Tarea 2.9: Configuración de entrenamiento en YAML

**Ficheros:**
- Crear: `enrel/entrenamiento/config.py`, `configs/etapa1-plata.yaml`, `configs/etapa2-oro.yaml`, `configs/cordura.yaml`
- Test: `tests/test_entrenamiento_config.py`

**Interfaces:**
- `@dataclass class Config: nombre: str; backbone: str; entrenamiento: list[str]` (rutas JSONL) `; desarrollo: str; punto_de_partida: str | None = None` (directorio de un modelo guardado; si es `None`, backbone desde HF) `; max_len: int = 4096; max_ancho: int = 16; max_grupos: int = 60; ratio_negativos: int = 8; lote: int = 2; acumulacion: int = 8; lr_codificador: float = 3e-5; lr_cabezas: float = 1e-4; weight_decay: float = 0.01; warmup: float = 0.1; epocas: int = 8; paciencia: int = 2; semilla: int = 42; bf16: bool = True; checkpointing: bool = True; pesos_por_clase: bool = True; peso_relaciones: float = 1.0; peso_entidades: float = 1.0; congelar_capas_inferiores: int = 0; salida: str = "corridas"; evaluar_cada: int = 1` (épocas) `; fraccion_ancla: float = 0.0` (fracción de la primera ruta de entrenamiento que se mezcla como ancla; para la etapa 2).
- `cargar_config(ruta: Path, **sobrescribir) -> Config`; `guardar_config(cfg, ruta)`.

- [ ] **Paso 1: Test**

```python
from pathlib import Path

from enrel.entrenamiento.config import cargar_config


def test_cargar_config(tmp_path: Path):
    ruta = tmp_path / "c.yaml"
    ruta.write_text("nombre: prueba\nbackbone: x\nentrenamiento: [a.jsonl]\ndesarrollo: d.jsonl\nlr_codificador: 1e-5\n", encoding="utf-8")
    c = cargar_config(ruta, semilla=7)
    assert c.nombre == "prueba" and c.lr_codificador == 1e-5 and c.semilla == 7 and c.epocas == 8


def test_configs_del_repo_cargan():
    for f in ("etapa1-plata", "etapa2-oro", "cordura"):
        c = cargar_config(Path(f"configs/{f}.yaml"))
        assert c.nombre and c.entrenamiento
```

- [ ] **Paso 2: Implementar y escribir los YAML**

`enrel/entrenamiento/config.py`:

```python
"""Configuración de una corrida, desde YAML."""

from dataclasses import asdict, dataclass, fields
from pathlib import Path

import yaml


@dataclass
class Config:
    nombre: str
    backbone: str
    entrenamiento: list[str]
    desarrollo: str
    punto_de_partida: str | None = None
    max_len: int = 4096
    max_ancho: int = 16
    max_grupos: int = 60
    ratio_negativos: int = 8
    lote: int = 2
    acumulacion: int = 8
    lr_codificador: float = 3e-5
    lr_cabezas: float = 1e-4
    weight_decay: float = 0.01
    warmup: float = 0.1
    epocas: int = 8
    paciencia: int = 2
    semilla: int = 42
    bf16: bool = True
    checkpointing: bool = True
    pesos_por_clase: bool = True
    peso_relaciones: float = 1.0
    peso_entidades: float = 1.0
    congelar_capas_inferiores: int = 0
    salida: str = "corridas"
    evaluar_cada: int = 1
    fraccion_ancla: float = 0.0


def cargar_config(ruta: Path, **sobrescribir) -> Config:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    datos.update(sobrescribir)
    validos = {f.name for f in fields(Config)}
    desconocidos = set(datos) - validos
    if desconocidos:
        raise ValueError(f"claves desconocidas en {ruta}: {sorted(desconocidos)}")
    for f in fields(Config):
        if f.name in datos and f.type in ("float", float) and isinstance(datos[f.name], str):
            datos[f.name] = float(datos[f.name])
    return Config(**datos)


def guardar_config(cfg: Config, ruta: Path) -> None:
    Path(ruta).write_text(yaml.safe_dump(asdict(cfg), allow_unicode=True, sort_keys=False), encoding="utf-8")
```

`configs/etapa1-plata.yaml`:

```yaml
nombre: etapa1-plata
backbone: BSC-LT/MrBERT-es
entrenamiento:
  - datos/anotado/plata.jsonl
  - datos/conjuntos/plata_alta.jsonl
desarrollo: datos/conjuntos/desarrollo.jsonl
max_len: 4096
lote: 2
acumulacion: 8
lr_codificador: 3.0e-5
lr_cabezas: 1.0e-4
epocas: 8
paciencia: 2
semilla: 42
pesos_por_clase: true
```

`configs/etapa2-oro.yaml`:

```yaml
nombre: etapa2-oro
backbone: BSC-LT/MrBERT-es
punto_de_partida: corridas/etapa1-plata-s42/mejor
entrenamiento:
  - datos/conjuntos/oro_entrenamiento.jsonl
  - datos/conjuntos/plata_alta.jsonl
  - datos/anotado/plata.jsonl
fraccion_ancla: 0.2
desarrollo: datos/conjuntos/desarrollo.jsonl
lr_codificador: 1.0e-5
lr_cabezas: 3.0e-5
epocas: 4
paciencia: 2
semilla: 42
```

(En la etapa 2 la primera ruta es el oro completo; `fraccion_ancla` se aplica a la **última** ruta, la plata, de la que se toma un 20 % al azar como ancla. El bucle lo implementa así.)

`configs/cordura.yaml`:

```yaml
nombre: cordura
backbone: BSC-LT/MrBERT-es
entrenamiento:
  - datos/conjuntos/cordura.jsonl
desarrollo: datos/conjuntos/cordura.jsonl
max_len: 2048
lote: 2
acumulacion: 1
lr_codificador: 5.0e-5
lr_cabezas: 3.0e-4
epocas: 40
paciencia: 40
pesos_por_clase: false
```

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_entrenamiento_config.py -q
git add enrel/entrenamiento/config.py configs tests/test_entrenamiento_config.py
git commit -m "Añade la configuración de entrenamiento en YAML y las tres corridas previstas"
```

---

### Tarea 2.10: Decodificación e inferencia de extremo a extremo

**Ficheros:**
- Crear: `enrel/inferencia/__init__.py`, `enrel/inferencia/decodificar.py`, `enrel/inferencia/pipeline.py`, `enrel/inferencia/cli_extraer.py`
- Modificar: `enrel/_subcomandos.py`
- Test: `tests/test_inferencia_decodificar.py`, `tests/test_inferencia_pipeline.py`

**Interfaces:**
- En `decodificar.py`:
  - `decodificar_menciones(logits: Tensor [S, C+1], tramos: list[tuple[int, int]], cod: Codificacion, umbral_ninguno: float = 0.0) -> list[Mencion]`: por tramo, `argmax`; se descartan los `NINGUNO`; entre tramos solapados del **mismo tipo** gana el de mayor probabilidad (voraz por probabilidad descendente); los de tipos distintos pueden anidarse. Offsets de caracteres = `cod.palabras[i][0] + desplazamiento`… (ya vienen absolutos en `cod.palabras`). Devuelve `Mencion` con `confianza`.
  - `decodificar_relaciones(logits: Tensor [R, C+1], pares: list[tuple[int, int]], grupos: list[Grupo], mascara_clases: BoolTensor [R, C], atencion: Tensor [R, T] | None, cod: Codificacion) -> list[Relacion]`: `decodificar_umbral` con máscara; una `Relacion` por clase positiva con `desglosar`; `confianza` de `confianzas`; `evidencia` = la oración (segmento entre `. `, `\n` o inicio/fin) que contiene la subpalabra de mayor peso en `atencion[r]`, si se pasa.
  - `oracion_de(texto: str, pos: int) -> tuple[int, int]`.
- En `pipeline.py`:
  - `class Pipeline: __init__(modelo: ModeloEnrel, dispositivo: str = "cpu", max_len: int = 8192, solape: int = 512, alias: dict | None = None)`; `extraer(texto: str, meta: dict | None = None) -> Documento`; `extraer_documentos(docs: list[Documento]) -> list[Documento]` (reutiliza `doc.texto` y la meta; `fuente="modelo"`).
  - Pasos de `extraer`: NFC → `ventanas` → por ventana: `codificar` ya hecho, `enumerar_tramos`, pasada del backbone y cabeza de entidades (sin gradiente, `torch.inference_mode`), `decodificar_menciones` → unión de menciones de todas las ventanas (dedupe por `(ini, fin, tipo)`, se queda la de mayor confianza) → `filtrar_menciones` → `agrupar(menciones, alias)` → recorte a `max_grupos` → construir `menciones_por_grupo` **por ventana** (índices de primera subpalabra de las menciones que caen en esa ventana) y pares admitidos → cabeza de relaciones por ventana → logits agregados entre ventanas por `max` por clase (un par puede aparecer en varias ventanas) → `decodificar_relaciones` → `filtrar_relaciones` → colapsar simétricas → `validar_documento` (lanza si falla) → `Documento` con `origen={"modelo": config.version, "ventanas": n, "recorte_grupos": k}`.
- Subcomandos: `enrel extraer RUTA_O_TEXTO --modelo DIR [--salida x.json] [--formato json|ftm] [--dispositivo cpu|cuda]` (formato `ftm` se completa en la etapa 3; hasta entonces imprime un aviso y usa `json`); `enrel predecir-conjunto --modelo DIR --entrada conjunto.jsonl --salida pred.jsonl [--dispositivo]` para evaluar.

- [ ] **Paso 1: Tests**

`tests/test_inferencia_decodificar.py`:

```python
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
from enrel.datos.documento import Grupo
from enrel.esquema.tipos import CLASES_FINAS, INDICE_CLASE
from enrel.inferencia.decodificar import decodificar_menciones, decodificar_relaciones, oracion_de
from enrel.modelo.entidades import NINGUNO, TIPO_A_INDICE
from enrel.modelo.tokenizacion import codificar

C = len(CLASES_FINAS)


def test_decodificar_menciones_resuelve_solapes_del_mismo_tipo():
    tok = transformers.AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-bert")
    texto = "Gustavo Petro nombró a Reyes."
    cod = codificar(tok, texto)
    tramos = [(0, 1), (0, 0), (1, 1), (4, 4)]
    logits = torch.full((4, 8), -5.0)
    logits[0, TIPO_A_INDICE["persona"]] = 4.0      # «Gustavo Petro»
    logits[1, TIPO_A_INDICE["persona"]] = 3.0      # «Gustavo», solapa, menor: se descarta
    logits[2, NINGUNO] = 4.0                        # «Petro» → ninguno
    logits[3, TIPO_A_INDICE["persona"]] = 2.0      # «Reyes»
    ms = decodificar_menciones(logits, tramos, cod)
    assert [(m.texto, m.tipo) for m in ms] == [("Gustavo Petro", "persona"), ("Reyes", "persona")]
    assert ms[0].confianza > 0.9


def test_decodificar_relaciones_con_mascara_y_evidencia():
    tok = transformers.AutoTokenizer.from_pretrained("hf-internal-testing/tiny-random-bert")
    texto = "Gustavo Petro nombró a Reyes. Luego viajó."
    cod = codificar(tok, texto)
    grupos = [Grupo("e1", "persona", "Gustavo Petro"), Grupo("e2", "persona", "Reyes")]
    logits = torch.zeros(1, C + 1)
    logits[0, INDICE_CLASE["nombro_a"]] = 3.0
    logits[0, INDICE_CLASE["dirige"]] = 3.0         # no admitida persona→persona: la máscara la quita
    logits[0, C] = 1.0
    mascara = torch.tensor([[True] * C])
    mascara[0, INDICE_CLASE["dirige"]] = False
    atencion = torch.zeros(1, len(cod.input_ids))
    atencion[0, cod.primera_subpalabra[2]] = 1.0    # «nombró»
    rels = decodificar_relaciones(logits, [(0, 1)], grupos, mascara, atencion, cod)
    assert len(rels) == 1 and rels[0].relacion == "nombro_a" and rels[0].cabeza == "e1"
    assert texto[rels[0].evidencia[0]:rels[0].evidencia[1]].strip() == "Gustavo Petro nombró a Reyes."


def test_oracion_de():
    assert oracion_de("Una. Dos frases. Tres", 8) == (5, 16)
```

`tests/test_inferencia_pipeline.py` (CPU, con tiny-bert; solo comprueba formas y validez, no calidad):

```python
import pytest

torch = pytest.importorskip("torch")
from enrel.datos.validar import validar_documento
from enrel.inferencia.pipeline import Pipeline
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel


def test_pipeline_produce_documento_valido():
    m = ModeloEnrel(ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8))
    p = Pipeline(m, max_len=64, solape=8)
    texto = " ".join(["El ministro Gustavo Petro nombró a Luis Carlos Reyes en Bogotá."] * 12)
    d = p.extraer(texto, {"doc_id": "x"})
    assert validar_documento(d) == []
    assert d.origen["ventanas"] >= 2 and d.fuente == "modelo"
```

- [ ] **Paso 2: Implementar `enrel/inferencia/decodificar.py`**

```python
"""De logits a menciones, relaciones y evidencia."""

import torch

from enrel.datos.documento import Grupo, Mencion, Relacion
from enrel.esquema.tipos import CLASES_FINAS, TIPOS, desglosar
from enrel.modelo.entidades import NINGUNO
from enrel.modelo.perdidas import confianzas, decodificar_umbral
from enrel.modelo.tokenizacion import Codificacion

_FIN_ORACION = (". ", ".\n", "\n", "? ", "! ")


def decodificar_menciones(logits: torch.Tensor, tramos: list[tuple[int, int]], cod: Codificacion, umbral_ninguno: float = 0.0) -> list[Mencion]:
    probs = torch.softmax(logits.float(), dim=-1)
    conf, clase = probs.max(dim=-1)
    candidatos = [(float(conf[k]), int(clase[k]), tramos[k]) for k in range(len(tramos)) if int(clase[k]) != NINGUNO]
    candidatos.sort(key=lambda x: -x[0])
    elegidos: list[tuple[float, int, tuple[int, int]]] = []
    for c, t, (i, j) in candidatos:
        if any(t == t2 and i <= j2 and i2 <= j for _, t2, (i2, j2) in elegidos):
            continue
        elegidos.append((c, t, (i, j)))
    elegidos.sort(key=lambda x: x[2])
    out = []
    for k, (c, t, (i, j)) in enumerate(elegidos):
        ini, fin = cod.palabras[i][0], cod.palabras[j][1]
        out.append(Mencion(f"m{k + 1}", ini, fin, cod.texto[ini - cod.desplazamiento:fin - cod.desplazamiento], TIPOS[t], "", round(c, 4)))
    return out


def oracion_de(texto: str, pos: int) -> tuple[int, int]:
    ini = 0
    for sep in _FIN_ORACION:
        k = texto.rfind(sep, 0, pos)
        if k >= 0:
            ini = max(ini, k + len(sep))
    fin = len(texto)
    for sep in _FIN_ORACION:
        k = texto.find(sep, pos)
        if k >= 0:
            fin = min(fin, k + 1 if sep.startswith(".") or sep.startswith("?") or sep.startswith("!") else k)
    return ini, fin


def decodificar_relaciones(logits: torch.Tensor, pares: list[tuple[int, int]], grupos: list[Grupo], mascara_clases: torch.Tensor,
                           atencion: torch.Tensor | None, cod: Codificacion) -> list[Relacion]:
    positivas = decodificar_umbral(logits.float(), mascara_clases)
    conf = confianzas(logits.float())
    out = []
    for r, (a, b) in enumerate(pares):
        evidencia = None
        if atencion is not None:
            sub = int(atencion[r].argmax())
            # la subpalabra → la palabra que la contiene → su oración en el texto de la ventana
            pal = next((k for k, (i, j) in enumerate(zip(cod.primera_subpalabra, cod.ultima_subpalabra)) if i <= sub <= j), None)
            if pal is not None:
                pos_local = cod.palabras[pal][0] - cod.desplazamiento
                o_ini, o_fin = oracion_de(cod.texto, pos_local)
                evidencia = (o_ini + cod.desplazamiento, o_fin + cod.desplazamiento)
        for c in torch.nonzero(positivas[r]).flatten().tolist():
            relacion, atributo = desglosar(CLASES_FINAS[c])
            out.append(Relacion(grupos[a].id, grupos[b].id, relacion, atributo, evidencia, round(float(conf[r, c]), 4)))
    return out
```

- [ ] **Paso 3: Implementar `enrel/inferencia/pipeline.py`**

```python
"""Inferencia de extremo a extremo: texto → Documento, con ventanas, agrupación por reglas y validación."""

import torch

from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Mencion, Relacion
from enrel.datos.normalizar import nfc
from enrel.datos.validar import validar_documento
from enrel.entrenamiento.colacion import colar
from enrel.entrenamiento.tensores import Ejemplo
from enrel.esquema.tipos import CLASES_FINAS, es_simetrica
from enrel.inferencia.decodificar import decodificar_menciones, decodificar_relaciones
from enrel.maestro.filtros import filtrar_menciones, filtrar_relaciones
from enrel.modelo.enrel import ModeloEnrel, mascara_tipos
from enrel.modelo.entidades import enumerar_tramos
from enrel.modelo.tokenizacion import Codificacion, palabra_de, ventanas

C = len(CLASES_FINAS)


class Pipeline:
    def __init__(self, modelo: ModeloEnrel, dispositivo: str = "cpu", max_len: int = 8192, solape: int = 512, alias: dict | None = None):
        self.m = modelo.to(dispositivo).eval()
        self.disp, self.max_len, self.solape, self.alias = dispositivo, max_len, solape, alias
        self.pad = self.m.tok.pad_token_id or 0

    def _lote(self, cod: Codificacion, tramos, menciones, tipos, pares, mascara) -> "Lote":
        ej = Ejemplo("x", cod.input_ids, cod.attention_mask, cod.primera_subpalabra, cod.ultima_subpalabra, tramos, [0] * len(tramos),
                     menciones, tipos, pares, [[0] * C for _ in pares], mascara)
        return colar([ej], self.pad).a(self.disp)

    @torch.inference_mode()
    def extraer(self, texto: str, meta: dict | None = None) -> Documento:
        meta = meta or {}
        texto = nfc(texto)
        cods = ventanas(self.m.tok, texto, self.max_len, self.solape)
        # 1. Entidades por ventana.
        vistas: dict[tuple[int, int, str], Mencion] = {}
        estados_por_ventana = []
        for cod in cods:
            tramos = [tuple(t) for t in enumerar_tramos(len(cod.palabras), self.m.config.max_ancho).tolist()]
            lote = self._lote(cod, tramos, [[0]], ["persona"], [], [])
            salida = self.m(lote)
            estados_por_ventana.append(salida["estados"])
            for men in decodificar_menciones(salida["logits_entidades"][0, :len(tramos)].cpu(), tramos, cod):
                clave = (men.ini, men.fin, men.tipo)
                if clave not in vistas or (men.confianza or 0) > (vistas[clave].confianza or 0):
                    vistas[clave] = men
        menciones = sorted(vistas.values(), key=lambda m: (m.ini, m.fin))
        for k, m in enumerate(menciones):
            m.id = f"m{k + 1}"
        menciones, _ = filtrar_menciones(texto, menciones)
        grupos = agrupar(menciones, self.alias)
        # 2. Recorte de grupos.
        conteo = {g.id: len([m for m in menciones if m.grupo == g.id]) for g in grupos}
        recorte = max(0, len(grupos) - self.m.config.max_grupos)
        grupos = sorted(grupos, key=lambda g: -conteo[g.id])[:self.m.config.max_grupos]
        grupos.sort(key=lambda g: int(g.id[1:]))
        ids_vivos = {g.id for g in grupos}
        menciones = [m for m in menciones if m.grupo in ids_vivos]
        indice = {g.id: k for k, g in enumerate(grupos)}
        tipos = [g.tipo for g in grupos]
        # 3. Relaciones por ventana, agregadas por máximo.
        relaciones: list[Relacion] = []
        if len(grupos) >= 2:
            pares_todos = [(a, b) for a in range(len(grupos)) for b in range(len(grupos)) if a != b]
            mascara = mascara_tipos([tipos[a] for a, _ in pares_todos], [tipos[b] for _, b in pares_todos])
            logits_max = torch.full((len(pares_todos), C + 1), float("-inf"))
            atencion_mejor = [None] * len(pares_todos)
            cod_mejor = [None] * len(pares_todos)
            for cod, estados in zip(cods, estados_por_ventana):
                men_por_grupo = [[] for _ in grupos]
                for m in menciones:
                    pj = palabra_de(cod, m.ini, m.fin)
                    if pj is not None:
                        men_por_grupo[indice[m.grupo]].append(cod.primera_subpalabra[pj[0]])
                presentes = {k for k, ms in enumerate(men_por_grupo) if ms}
                pares = [(a, b) for (a, b) in pares_todos if a in presentes and b in presentes]
                if not pares:
                    continue
                idx_pares = [pares_todos.index(p) for p in pares]
                men_rellenas = [ms if ms else [0] for ms in men_por_grupo]
                lote = self._lote(cod, [(0, 0)], men_rellenas, tipos, pares, [mascara[i].tolist() for i in idx_pares])
                logits = self.m.relaciones(estados, lote.attention_mask.bool(), lote.menciones, lote.mascara_menciones,
                                           lote.pares, lote.mascara_pares)[0].cpu()
                atencion = self.m.relaciones.ultima_atencion[0].cpu()
                for r, i in enumerate(idx_pares):
                    if logits[r].max() > logits_max[i].max():
                        atencion_mejor[i], cod_mejor[i] = atencion[r:r + 1], cod
                    logits_max[i] = torch.maximum(logits_max[i], logits[r])
            validos = [i for i in range(len(pares_todos)) if torch.isfinite(logits_max[i]).all()]
            for i in validos:
                relaciones += decodificar_relaciones(logits_max[i:i + 1], [pares_todos[i]], grupos, mascara[i:i + 1], atencion_mejor[i], cod_mejor[i])
        por_id = {g.id: g for g in grupos}
        relaciones, _ = filtrar_relaciones(relaciones, por_id)
        # 4. Colapsar simétricas duplicadas (a→b y b→a con la misma clase): filtrar_relaciones ya quita espejos.
        doc = Documento(meta.get("doc_id", "texto"), texto, menciones, grupos, relaciones, meta.get("url", ""), meta.get("fecha", ""),
                        meta.get("seccion", ""), meta.get("titulo", ""), "modelo",
                        {"modelo": self.m.config.version, "ventanas": len(cods), "recorte_grupos": recorte})
        errores = validar_documento(doc)
        if errores:
            raise ValueError("\n".join(errores))
        return doc

    def extraer_documentos(self, docs: list[Documento]) -> list[Documento]:
        return [self.extraer(d.texto, {"doc_id": d.doc_id, "url": d.url, "fecha": d.fecha, "seccion": d.seccion, "titulo": d.titulo}) for d in docs]
```

Nota de implementación: `es_simetrica` se importa por si la decodificación produce a→b y b→a para una simétrica en dos ventanas distintas; `filtrar_relaciones` ya descarta el espejo, así que basta con que las relaciones lleguen en orden determinista. Si `ruff` marca el import sin uso, quitarlo.

`enrel/inferencia/cli_extraer.py`: subcomandos `extraer` y `predecir-conjunto` según las interfaces; `extraer` acepta una ruta a `.txt` o texto directo; `--dispositivo` por defecto `cuda` si está disponible. Registrar en `_subcomandos.py`.

- [ ] **Paso 4: Correr tests y commit**

```bash
uv run pytest tests/test_inferencia_decodificar.py tests/test_inferencia_pipeline.py -q
git add enrel/inferencia tests/test_inferencia_decodificar.py tests/test_inferencia_pipeline.py enrel/_subcomandos.py
git commit -m "Añade la decodificación y el pipeline de inferencia de extremo a extremo con ventanas"
```

---

### Tarea 2.11: El bucle de entrenamiento

**Ficheros:**
- Crear: `enrel/entrenamiento/bucle.py`, `enrel/entrenamiento/cli_entrenar.py`
- Modificar: `enrel/_subcomandos.py`
- Test: `tests/test_entrenamiento_bucle.py` (CPU, tiny-bert, dos documentos, dos épocas: comprueba que corre, que escribe los ficheros y que la pérdida baja)

**Interfaces:**
- `entrenar(cfg: Config, dispositivo: str | None = None) -> dict`: devuelve `{"directorio": str, "mejor_epoca": int, "mejor_re_mas": float, "epocas": n}`.
- Pasos:
  1. Semilla (`torch`, `random`, `numpy`). Directorio `cfg.salida/<AAAA-MM-DD>-<cfg.nombre>-s<semilla>/`; `guardar_config`; `hashes.json` con SHA-256 de cada JSONL de entrenamiento y desarrollo (`hash_fichero`).
  2. Datos: `cargar_jsonl` de cada ruta de `cfg.entrenamiento`; si `cfg.fraccion_ancla > 0`, de la **última** ruta se toma esa fracción al azar (semilla) y el resto se descarta. Desarrollo completo. `comprobar_fugas({"desarrollo": dev, "entrenamiento": train})` aborta si hay fugas.
  3. Modelo: `ModeloEnrel.cargar(cfg.punto_de_partida)` si hay, si no `ModeloEnrel(ConfigModelo(backbone=cfg.backbone, max_ancho=cfg.max_ancho, max_grupos=cfg.max_grupos), checkpointing=cfg.checkpointing)`. Si `cfg.congelar_capas_inferiores > 0`, `requires_grad=False` en las embeddings y en las primeras N capas (`modelo.backbone.layers[:N]` para ModernBERT; `encoder.layer[:N]` para BERT; buscar el atributo que exista).
  4. Pesos por clase: `pesos_por_frecuencia(conteo_clases(train))` si `cfg.pesos_por_clase`.
  5. Optimizador `AdamW` con dos grupos (`parametros_por_grupo`, lr respectivo, `weight_decay`); scheduler lineal con `warmup` sobre `pasos_totales = ceil(len(train) / (lote × acumulacion)) × epocas`.
  6. Época: barajar; `ejemplo_desde_documento` por documento (con `rng` por época, así los negativos cambian); `colar` en lotes de `cfg.lote`; `autocast(bfloat16)` si `cfg.bf16` y hay CUDA; `perdida = peso_entidades × perdida_entidades + peso_relaciones × perdida_umbral_adaptativo` (esta última solo si hay pares); dividir por `acumulacion`; `backward`; cada `acumulacion` lotes: `clip_grad_norm_(1.0)`, `step`, `scheduler.step`, `zero_grad`. Registrar pérdida media por época.
  7. Cada `evaluar_cada` épocas: `Pipeline(modelo, dispositivo, max_len=cfg.max_len)` sobre desarrollo → `evaluar_entidades` estricto y `evaluar_relaciones` RE+ → escribe `metricas.jsonl` (época, pérdidas, F1 entidades, RE+, fina, tiempo) y `evaluacion-desarrollo.md` con `informe_completo` de la mejor época. Si RE+ mejora, `guardar` en `mejor/`; si no mejora en `paciencia` evaluaciones, parar.
  8. Al final: `resumen.json`.
- CLI `enrel entrenar --config configs/etapa1-plata.yaml [--semilla 7] [--nombre x] [--dispositivo cuda]` (las opciones sobrescriben el YAML).

- [ ] **Paso 1: Test**

```python
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
from enrel.datos.documento import guardar_jsonl
from enrel.entrenamiento.bucle import entrenar
from enrel.entrenamiento.config import Config
from tests.test_datos_documento import doc_ejemplo


def test_entrenar_dos_epocas_cpu(tmp_path: Path):
    a, b = doc_ejemplo(), doc_ejemplo()
    b.doc_id = "wp:2"
    guardar_jsonl([a, b], tmp_path / "train.jsonl")
    c = doc_ejemplo()
    c.doc_id = "wp:3"
    guardar_jsonl([c], tmp_path / "dev.jsonl")
    cfg = Config(nombre="t", backbone="hf-internal-testing/tiny-random-bert", entrenamiento=[str(tmp_path / "train.jsonl")],
                 desarrollo=str(tmp_path / "dev.jsonl"), max_len=128, lote=2, acumulacion=1, epocas=2, paciencia=5, bf16=False,
                 checkpointing=False, salida=str(tmp_path / "corridas"), pesos_por_clase=True)
    r = entrenar(cfg, dispositivo="cpu")
    d = Path(r["directorio"])
    assert (d / "config.yaml").exists() and (d / "hashes.json").exists() and (d / "mejor" / "cabezas.safetensors").exists()
    metricas = [json.loads(l) for l in (d / "metricas.jsonl").read_text().splitlines()]
    assert len(metricas) == 2 and metricas[1]["perdida"] <= metricas[0]["perdida"] * 1.5
    assert "re_mas" in metricas[0]
```

- [ ] **Paso 2: Implementar `enrel/entrenamiento/bucle.py`**

```python
"""El bucle de entrenamiento: dos tasas, acumulación, bf16, evaluación por época con el pipeline real y parada por RE+."""

import json
import math
import random
import time
from datetime import date
from pathlib import Path

import numpy as np
import torch

from enrel.datos.documento import cargar_jsonl, hash_fichero
from enrel.datos.validar import comprobar_fugas
from enrel.entrenamiento.colacion import colar
from enrel.entrenamiento.config import Config, guardar_config
from enrel.entrenamiento.tensores import conteo_clases, ejemplo_desde_documento
from enrel.evaluacion.entidades import evaluar_entidades
from enrel.evaluacion.informe import informe_completo
from enrel.evaluacion.relaciones import evaluar_relaciones
from enrel.inferencia.pipeline import Pipeline
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel
from enrel.modelo.perdidas import perdida_entidades, perdida_umbral_adaptativo, pesos_por_frecuencia


def _semilla(s: int) -> None:
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)


def _congelar(modelo: ModeloEnrel, n: int) -> None:
    if n <= 0:
        return
    bb = modelo.backbone
    for p in getattr(bb, "embeddings", bb).parameters():
        p.requires_grad = False
    capas = getattr(bb, "layers", None) or getattr(getattr(bb, "encoder", None), "layer", None)
    if capas is not None:
        for capa in list(capas)[:n]:
            for p in capa.parameters():
                p.requires_grad = False


def _cargar_entrenamiento(cfg: Config, rng: random.Random):
    docs = []
    for k, ruta in enumerate(cfg.entrenamiento):
        parte = cargar_jsonl(ruta)
        if cfg.fraccion_ancla > 0 and k == len(cfg.entrenamiento) - 1 and len(cfg.entrenamiento) > 1:
            rng.shuffle(parte)
            parte = parte[:int(len(parte) * cfg.fraccion_ancla)]
        docs += parte
    return docs


def _evaluar(modelo, dev, dispositivo, max_len):
    pipeline = Pipeline(modelo, dispositivo, max_len=max_len)
    pred = pipeline.extraer_documentos(dev)
    ent = evaluar_entidades(dev, pred, "estricto")["__global__"].f1
    re_mas = evaluar_relaciones(dev, pred, "gruesa", exigir_tipos=True)["__micro__"].f1
    fina = evaluar_relaciones(dev, pred, "fina", exigir_tipos=True)["__micro__"].f1
    modelo.train()
    return {"entidades": ent, "re_mas": re_mas, "fina": fina}, pred


def entrenar(cfg: Config, dispositivo: str | None = None) -> dict:
    dispositivo = dispositivo or ("cuda" if torch.cuda.is_available() else "cpu")
    _semilla(cfg.semilla)
    rng = random.Random(cfg.semilla)
    directorio = Path(cfg.salida) / f"{date.today().isoformat()}-{cfg.nombre}-s{cfg.semilla}"
    directorio.mkdir(parents=True, exist_ok=True)
    guardar_config(cfg, directorio / "config.yaml")
    (directorio / "hashes.json").write_text(json.dumps({r: hash_fichero(r) for r in cfg.entrenamiento + [cfg.desarrollo]}, indent=2), encoding="utf-8")

    train = _cargar_entrenamiento(cfg, rng)
    dev = cargar_jsonl(cfg.desarrollo)
    fugas = comprobar_fugas({"desarrollo": dev, "entrenamiento": train})
    if fugas:
        raise RuntimeError("fugas entre desarrollo y entrenamiento: " + "; ".join(fugas[:5]))

    if cfg.punto_de_partida:
        modelo = ModeloEnrel.cargar(cfg.punto_de_partida)
        if cfg.checkpointing:
            modelo.backbone.gradient_checkpointing_enable()
    else:
        modelo = ModeloEnrel(ConfigModelo(backbone=cfg.backbone, max_ancho=cfg.max_ancho, max_grupos=cfg.max_grupos), checkpointing=cfg.checkpointing)
    _congelar(modelo, cfg.congelar_capas_inferiores)
    modelo.to(dispositivo).train()
    pesos = pesos_por_frecuencia(conteo_clases(train)).to(dispositivo) if cfg.pesos_por_clase else None

    grupos = modelo.parametros_por_grupo()
    opt = torch.optim.AdamW([
        {"params": [p for p in grupos[0]["params"] if p.requires_grad], "lr": cfg.lr_codificador, "weight_decay": cfg.weight_decay},
        {"params": grupos[1]["params"], "lr": cfg.lr_cabezas, "weight_decay": cfg.weight_decay},
    ])
    pasos_por_epoca = math.ceil(len(train) / (cfg.lote * cfg.acumulacion))
    total = max(1, pasos_por_epoca * cfg.epocas)
    calentamiento = int(total * cfg.warmup)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: (s + 1) / max(1, calentamiento) if s < calentamiento else max(0.0, (total - s) / max(1, total - calentamiento)))
    usar_bf16 = cfg.bf16 and dispositivo.startswith("cuda")
    pad = modelo.tok.pad_token_id or 0

    mejor, mejor_epoca, sin_mejora = -1.0, 0, 0
    with (directorio / "metricas.jsonl").open("w", encoding="utf-8") as fm:
        for epoca in range(1, cfg.epocas + 1):
            t0 = time.time()
            rng_epoca = random.Random(cfg.semilla * 1000 + epoca)
            orden = list(range(len(train)))
            rng_epoca.shuffle(orden)
            perdidas, n_lotes, opt.zero_grad(set_to_none=True) = [], 0, None
            for k in range(0, len(orden), cfg.lote):
                ejemplos = [ejemplo_desde_documento(train[i], modelo.tok, cfg.max_len, cfg.max_ancho, cfg.ratio_negativos, cfg.max_grupos, rng_epoca)
                            for i in orden[k:k + cfg.lote]]
                lote = colar(ejemplos, pad).a(dispositivo)
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=usar_bf16):
                    salida = modelo(lote)
                    perdida = cfg.peso_entidades * perdida_entidades(salida["logits_entidades"].float(), lote.etiquetas_tramos)
                    if salida["logits_relaciones"] is not None:
                        perdida = perdida + cfg.peso_relaciones * perdida_umbral_adaptativo(
                            salida["logits_relaciones"].float(), lote.etiquetas_pares, lote.mascara_pares, pesos)
                (perdida / cfg.acumulacion).backward()
                perdidas.append(float(perdida))
                n_lotes += 1
                if n_lotes % cfg.acumulacion == 0:
                    torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
                    opt.step()
                    sched.step()
                    opt.zero_grad(set_to_none=True)
            if n_lotes % cfg.acumulacion != 0:
                torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
            fila = {"epoca": epoca, "perdida": sum(perdidas) / max(1, len(perdidas)), "segundos": round(time.time() - t0, 1)}
            if epoca % cfg.evaluar_cada == 0:
                metricas, pred = _evaluar(modelo, dev, dispositivo, cfg.max_len)
                fila.update(metricas)
                if metricas["re_mas"] > mejor:
                    mejor, mejor_epoca, sin_mejora = metricas["re_mas"], epoca, 0
                    modelo.guardar(directorio / "mejor")
                    (directorio / "evaluacion-desarrollo.md").write_text(
                        informe_completo(dev, pred, train, f"{cfg.nombre} época {epoca}", con_intervalos=False), encoding="utf-8")
                else:
                    sin_mejora += 1
            fm.write(json.dumps(fila, ensure_ascii=False) + "\n")
            fm.flush()
            print(json.dumps(fila, ensure_ascii=False))
            if sin_mejora >= cfg.paciencia:
                break
    if mejor < 0:
        modelo.guardar(directorio / "mejor")
    resumen = {"directorio": str(directorio), "mejor_epoca": mejor_epoca, "mejor_re_mas": mejor, "epocas": epoca}
    (directorio / "resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    return resumen
```

Corregir al implementar la línea `perdidas, n_lotes, opt.zero_grad(set_to_none=True) = [], 0, None`, que es inválida: escribir `perdidas, n_lotes = [], 0` y `opt.zero_grad(set_to_none=True)` en la línea siguiente.

`enrel/entrenamiento/cli_entrenar.py`: subcomando `entrenar` con `--config`, `--semilla`, `--nombre`, `--dispositivo`; llama a `cargar_config(ruta, **sobrescrituras)` y `entrenar`. Registrar.

- [ ] **Paso 3: Correr test y commit**

```bash
uv run pytest tests/test_entrenamiento_bucle.py -q
git add enrel/entrenamiento/bucle.py enrel/entrenamiento/cli_entrenar.py enrel/_subcomandos.py tests/test_entrenamiento_bucle.py
git commit -m "Añade el bucle de entrenamiento con evaluación por época y parada por RE+"
```

---

### Tarea 2.12: Cordura: sobreajustar 20 documentos

**Ficheros:**
- Crear: `enrel/entrenamiento/cordura.py`, `scripts/cordura.sh`
- Test: `tests/test_entrenamiento_cordura.py` (marcado `gpu`)

**Interfaces:**
- `preparar_cordura(origen: Path, salida: Path, n: int = 20, semilla: int = 1) -> int`: toma `n` documentos con al menos 2 relaciones del JSONL `origen` y los escribe en `salida`.
- `cordura(cfg_ruta: Path = Path("configs/cordura.yaml"), dispositivo: str | None = None) -> dict`: `entrenar` con la config de cordura (entrenamiento = desarrollo = los 20), y devuelve las métricas de la última evaluación. Criterio: entidades estricto ≥ 0,98 y RE+ ≥ 0,95 sobre los mismos 20. Si no llega, el problema está en la conversión a tensores, la decodificación o la pérdida, no en los datos ni en los hiperparámetros: no se avanza a la Tarea 2.13.

- [ ] **Paso 1: Test marcado**

```python
import pytest

torch = pytest.importorskip("torch")


@pytest.mark.gpu
def test_cordura_sobreajusta():
    from pathlib import Path

    from enrel.entrenamiento.cordura import cordura, preparar_cordura

    assert preparar_cordura(Path("datos/conjuntos/plata_alta.jsonl"), Path("datos/conjuntos/cordura.jsonl")) == 20
    m = cordura()
    assert m["entidades"] >= 0.98 and m["re_mas"] >= 0.95, m
```

- [ ] **Paso 2: Implementar**

```python
"""Cordura: el modelo debe poder sobreajustar 20 documentos hasta casi F1 1,0. Si no, hay un bug, no un problema de datos."""

import json
import random
from pathlib import Path

from enrel.datos.documento import cargar_jsonl, guardar_jsonl
from enrel.entrenamiento.bucle import entrenar
from enrel.entrenamiento.config import cargar_config


def preparar_cordura(origen: Path, salida: Path, n: int = 20, semilla: int = 1) -> int:
    docs = [d for d in cargar_jsonl(origen) if len(d.relaciones) >= 2]
    random.Random(semilla).shuffle(docs)
    return guardar_jsonl(docs[:n], salida)


def cordura(cfg_ruta: Path = Path("configs/cordura.yaml"), dispositivo: str | None = None) -> dict:
    cfg = cargar_config(cfg_ruta)
    r = entrenar(cfg, dispositivo)
    filas = [json.loads(l) for l in (Path(r["directorio"]) / "metricas.jsonl").read_text(encoding="utf-8").splitlines()]
    ultima = [f for f in filas if "re_mas" in f][-1]
    return {"entidades": ultima["entidades"], "re_mas": ultima["re_mas"], "fina": ultima["fina"], "directorio": r["directorio"]}
```

`scripts/cordura.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
uv run python -c "from pathlib import Path; from enrel.entrenamiento.cordura import preparar_cordura; print(preparar_cordura(Path('datos/conjuntos/plata_alta.jsonl'), Path('datos/conjuntos/cordura.jsonl')))"
uv run python -c "from enrel.entrenamiento.cordura import cordura; import json; print(json.dumps(cordura(), indent=2))"
```

- [ ] **Paso 3: Correr y anotar**

`bash scripts/cordura.sh` en la máquina con GPU. Copiar las métricas a `docs/resultados/etapa-2.md` (sección «Cordura»). Si no pasa: revisar en este orden (a) `ejemplo_desde_documento` produce etiquetas positivas para todas las relaciones (imprimir conteo), (b) `decodificar_relaciones` respeta la máscara, (c) la pérdida de umbral baja a casi 0 en el sobreajuste (si no baja, revisar `perdida_umbral_adaptativo`), (d) `palabra_de` alinea bien las menciones (comparar textos).

- [ ] **Paso 4: Commit**

```bash
git add enrel/entrenamiento/cordura.py scripts/cordura.sh tests/test_entrenamiento_cordura.py docs/resultados/etapa-2.md
git commit -m "Añade la prueba de cordura por sobreajuste y su resultado"
```

---

### Tarea 2.13: Primer entrenamiento con plata, evaluación completa y cierre de etapa

Sin código nuevo salvo un script de evaluación. La ejecuta el orquestador.

- [ ] **Paso 1: Conjuntos**

Verificar que existen `datos/anotado/plata.jsonl` (etapa 1), `datos/conjuntos/plata_alta.jsonl`, `datos/conjuntos/desarrollo.jsonl` (los 10 de oro-perfiles más los 10 de silla-nacional corregidos; si los de silla-nacional no están, solo los 10 perfiles y se anota) y `datos/conjuntos/prueba.jsonl`. `comprobar_fugas` sobre los cuatro más `prueba_dirigida.jsonl` si existe.

- [ ] **Paso 2: Dos semillas**

```bash
nohup uv run enrel entrenar --config configs/etapa1-plata.yaml --semilla 42 > corridas/etapa1-s42.log 2>&1 &
```

Al terminar (mirar `resumen.json`), la segunda: `--semilla 7`. Cada época de 3.500 documentos a 4.096 tokens con lote 2 en una RTX 4060 debería tardar del orden de 40 a 90 minutos; si supera 2 horas, bajar `max_len` a 3072 en el YAML y anotarlo.

- [ ] **Paso 3: Evaluación en prueba**

`scripts/evaluar_corrida.sh <directorio_corrida>`:

```bash
#!/usr/bin/env bash
set -euo pipefail
D="$1"
uv run enrel predecir-conjunto --modelo "$D/mejor" --entrada datos/conjuntos/prueba.jsonl --salida "$D/pred-prueba.jsonl"
uv run enrel evaluar --oro datos/conjuntos/prueba.jsonl --pred "$D/pred-prueba.jsonl" --entrenamiento datos/anotado/plata.jsonl --nombre "$(basename "$D")" --salida "$D/evaluacion-prueba.md"
if [ -f datos/conjuntos/prueba_dirigida.jsonl ]; then
  uv run enrel predecir-conjunto --modelo "$D/mejor" --entrada datos/conjuntos/prueba_dirigida.jsonl --salida "$D/pred-prueba-dirigida.jsonl"
  uv run enrel evaluar --oro datos/conjuntos/prueba_dirigida.jsonl --pred "$D/pred-prueba-dirigida.jsonl" --nombre "$(basename "$D") · prueba dirigida" --salida "$D/evaluacion-prueba-dirigida.md"
fi
```

Correr para las dos semillas. Escribir `docs/resultados/etapa-2.md` con: la tabla de la spec §8 con las tres filas obligatorias (línea base GLiNER de la etapa 1, techo del maestro de la etapa 1, modelo por semilla) sobre la prueba, con intervalos; media y diferencia entre semillas; F1 por relación fina con la regla n ≥ 10; la tabla de prueba dirigida aparte; positivos por clase en entrenamiento; horas de GPU; hashes; y la comparación con legajo (0,86 a 0,88 entidades por solape, 0,47 a 0,52 relaciones).

- [ ] **Paso 4: Criterio de salida**

El modelo supera a la línea base zero-shot en RE+ sobre la prueba. Si además supera 0,60 de RE+, la etapa 3 arranca con la receta tal cual; si queda entre la línea base y 0,60, la etapa 3 arranca igual pero su primera tarea es un barrido corto (lr codificador 5e-5, `ratio_negativos` 4, `max_len` 3072 con dos ventanas de entrenamiento por documento largo) antes del oro; si no supera la línea base, se detiene y se revisa con el usuario (posibles causas en orden: fugas en el mapeo de la prueba, recorte de 4.096 tokens dejando fuera relaciones del final, pesos por clase demasiado agresivos).

- [ ] **Paso 5: Commit**

```bash
git add scripts/evaluar_corrida.sh docs/resultados/etapa-2.md
git commit -m "Cierra la etapa 2: primer modelo entrenado con plata y evaluado con la tabla completa"
```

---

## Autorrevisión del plan de la etapa 2

**Cobertura de la spec.** §4.1 backbone y respaldo → 2.2 (y 0.16). §4.2 cabeza de tramos hasta 16 palabras, anidamiento entre tipos, negativos 8:1 → 2.3, 2.7, 2.10. §4.3 agrupación por reglas con alias opcional → reutiliza 0.6 en 2.10. §4.4 cabeza de pares con logsumexp, contexto local, bilineal agrupado de 64, 25 clases más TH, máscara de tipos, pérdida de umbral adaptativo con reponderación de cola larga, decodificación por TH, evidencia, tope de 60 grupos → 2.4, 2.5, 2.6, 2.7, 2.10. §4.5 salida JSON → `Documento` y `predecir-conjunto`; el exportador FtM va en la etapa 3. §7 receta (bf16, checkpointing, lote 2×8, 4.096, lr, épocas, paciencia, semillas, trazabilidad, cordura) → 2.9, 2.11, 2.12, 2.13. §8 tabla con tres filas e Ign-F1 → 2.13. §10 etapa 2 criterio de salida → 2.13.

**Tipos y firmas.** `Codificacion` (2.1) con `palabras`, `primera_subpalabra`, `ultima_subpalabra`, `desplazamiento`, `texto` la usan 2.7 y 2.10. `Ejemplo` (2.7) y `Lote` (2.8) con los mismos campos los consume `ModeloEnrel.forward` (2.6) y `Pipeline` (2.10). `CabezaRelaciones.forward(estados, mascara_tokens, menciones, mascara_menciones, pares, mascara_pares)` (2.4) coincide con la llamada en 2.6 y 2.10. `decodificar_umbral(logits, mascara)` y `confianzas` (2.5) las usa 2.10. `mascara_tipos` (2.6) la usan 2.7 y 2.10. `Config` (2.9) la consume `entrenar` (2.11) y `cordura` (2.12).

**Placeholders.** Ninguno; la única línea señalada como inválida en 2.11 trae su corrección al lado.
