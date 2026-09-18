# enrel · Etapa 3 · Oro, exportación y publicación — Plan de implementación

> **Para agentes ejecutores:** SUB-SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para seguimiento. Los subagentes que escriben código usan `model: "sonnet"`.

**Objetivo:** llevar el modelo de la etapa 2 a la v0.1 publicable: segunda etapa de entrenamiento con el oro, barrido corto si hace falta, exportación a ONNX con cuantización medida, pipeline de inferencia sin torch sobre ONNX Runtime, medición en CPU a 4 hilos, exportador a FollowTheMoney, revisión manual de 50 falsos positivos, ficha de modelo y publicación en Hugging Face y GitHub.

**Arquitectura:** el modelo se exporta como tres grafos ONNX (codificador, cabeza de entidades, cabeza de relaciones) con ejes dinámicos; un pipeline en numpy reproduce la lógica de `Pipeline` sin torch; la cuantización int8 dinámica se compara con fp32 y fp16 sobre la prueba y se publica la que cumpla la tolerancia; la salida se convierte a entidades y aristas de FollowTheMoney con procedencia.

**Tecnologías:** `torch.onnx`, `onnx`, `onnxruntime` (con `quantization`), `numpy`, `huggingface_hub`, `followthemoney` (opcional, solo para validar el exportador), `psutil`.

**Spec:** `docs/superpowers/specs/2026-09-16-enrel-diseno.md` (§4.5, §4.6, §7 etapa 2, §8, §9, §10 · etapa 3, §11).

## Restricciones globales

- Las de las etapas anteriores.
- Tolerancias para publicar una variante cuantizada: pierde como mucho 1 punto de F1 estricto de entidades y 2 de RE+ respecto a fp32 sobre la prueba; si int8 no cumple, se publica fp16 como predeterminado y se documenta.
- Medición de CPU siempre bajo `taskset -c 0-3`, `intra_op_num_threads = 4`, sobre 200 artículos de la prueba y la selección (los de la prueba primero), reportando mediana y p95 de segundos por 1.000 palabras y RSS máximo. Metas: mediana < 5 s por 1.000 palabras, RSS < 2 GB.
- La ficha de modelo, el README y el informe de resultados van en español, con las cifras con intervalos, la tabla de las tres filas obligatorias, límites conocidos y uso previsto. Los datos con texto del archivo no se publican.
- Nada se publica en Hugging Face sin que el usuario confirme la organización o cuenta destino y el nombre del repositorio; el script de subida exige `--confirmar`.

---

## Estructura de ficheros de la etapa 3

```
enrel/exportar/__init__.py
enrel/exportar/onnx.py            exportar_modelo(modelo, dir) → codificador.onnx, entidades.onnx, relaciones.onnx, meta.json
enrel/exportar/cuantizar.py       int8 dinámico y fp16 de los tres grafos; comparación con la prueba
enrel/exportar/medir_cpu.py       medir(pipeline, docs, hilos) → tabla; `enrel medir-cpu`
enrel/exportar/cli_exportar.py    `enrel exportar-onnx`, `enrel cuantizar`
enrel/inferencia/onnx_pipeline.py PipelineONNX: la misma lógica que Pipeline con sesiones de ONNX Runtime
enrel/esquema/ftm.py              a_followthemoney(doc, fuente_url, publisher) → lista de entidades FtM
enrel/esquema/cli_ftm.py          `enrel extraer --formato ftm` (completa el CLI de la etapa 2)
scripts/revisar_falsos_positivos.py  50 FP de relaciones de la prueba → markdown para el usuario
scripts/publicar_hf.py            sube pesos, ONNX y ficha a Hugging Face (con --confirmar)
docs/ficha-modelo.md              la ficha (también se copia como README.md del repo de HF)
docs/resultados/etapa-3-*.md, docs/resultados/v0.1.md
tests/test_exportar_*.py, tests/test_onnx_pipeline.py, tests/test_ftm.py
```

---

### Tarea 3.1: Segunda etapa con el oro, y barrido corto si la etapa 2 lo pidió

Sin código nuevo. La ejecuta el orquestador.

- [ ] **Paso 1: Confirmar el punto de partida**

Leer `docs/resultados/etapa-2.md`. Poner en `configs/etapa2-oro.yaml` el `punto_de_partida` de la mejor semilla de la etapa 2 (`corridas/<fecha>-etapa1-plata-s42/mejor` o `-s7`). Verificar que `datos/conjuntos/oro_entrenamiento.jsonl` existe (los 15 perfiles del reparto de la etapa 0 más lo que el usuario haya corregido después, reexportado con `enrel exportar-legajo --lote N --solo-validos`); si está vacío, la etapa 2 con oro se salta y se anota.

- [ ] **Paso 2: Barrido corto, solo si RE+ de la etapa 2 quedó por debajo de 0,60**

Tres corridas de la etapa 1 con un cambio cada una, semilla 42, sobre la plata: `lr_codificador: 5.0e-5`; `ratio_negativos: 4`; `max_len: 3072`. Comando: `uv run enrel entrenar --config configs/etapa1-plata.yaml --nombre barrido-lr5e5 …` (crear tres YAML copiando el de plata con el cambio). Evaluar cada una en desarrollo (ya lo hace el bucle) y tomar la mejor como punto de partida. Anotar la tabla en `docs/resultados/etapa-3-barrido.md`.

- [ ] **Paso 3: Etapa 2 con oro, dos semillas**

```bash
nohup uv run enrel entrenar --config configs/etapa2-oro.yaml --semilla 42 > corridas/etapa2-s42.log 2>&1 &
```

y después `--semilla 7`. Evaluar con `scripts/evaluar_corrida.sh` (etapa 2, tarea 2.13). Escribir `docs/resultados/etapa-3-oro.md` con las filas: etapa 1 (mejor semilla), etapa 2 por semilla, línea base, techo del maestro; intervalos; prueba dirigida aparte. Decidir el modelo candidato a v0.1: el de mayor RE+ en prueba, con la restricción de que sus entidades estrictas no bajen más de 1 punto respecto al de la etapa 1.

- [ ] **Paso 4: Barrido de backbone alternativo (una corrida)**

`configs/etapa1-mmbert.yaml`: igual que `etapa1-plata.yaml` con `backbone: jhu-clsp/mmBERT-small` y `nombre: etapa1-mmbert`. Una semilla. Evaluar en prueba. Fila adicional en `docs/resultados/etapa-3-oro.md`. Si supera a MrBERT-es en RE+ por más de 2 puntos, repetir la etapa 2 con oro sobre él y reconsiderar el candidato; si no, queda como referencia.

- [ ] **Paso 5: Commit**

```bash
git add configs docs/resultados/etapa-3-barrido.md docs/resultados/etapa-3-oro.md
git commit -m "Etapa 3: segunda etapa con oro, barrido corto y backbone alternativo medidos"
```

---

### Tarea 3.2: Exportar el modelo a ONNX en tres grafos

**Ficheros:**
- Crear: `enrel/exportar/__init__.py`, `enrel/exportar/onnx.py`, `enrel/exportar/cli_exportar.py`
- Modificar: `enrel/_subcomandos.py`, `enrel/modelo/relaciones.py` (un método `forward_exportable` sin efectos laterales), `enrel/modelo/entidades.py` (nada; ya es exportable)
- Test: `tests/test_exportar_onnx.py` (CPU, tiny-bert)

**Interfaces:**
- `exportar_modelo(modelo: ModeloEnrel, directorio: Path, opset: int = 17) -> dict`: escribe `codificador.onnx` (entradas `input_ids [B,T]`, `attention_mask [B,T]`; salida `estados [B,T,H]`), `entidades.onnx` (entradas `estados`, `primera [B,P]`, `ultima [B,P]`, `tramos [B,S,2]`, `mascara_tramos [B,S]`; salida `logits_entidades [B,S,6]`), `relaciones.onnx` (entradas `estados`, `mascara_tokens [B,T]`, `menciones [B,G,M]`, `mascara_menciones [B,G,M]`, `pares [B,R,2]`, `mascara_pares [B,R]`; salidas `logits_relaciones [B,R,26]`, `atencion [B,R,T]` y `logits_vigencia [B,R,3]`), todos con ejes dinámicos, y `meta.json` con la `ConfigModelo`, `CLASES_FINAS`, `TIPOS`, el nombre del tokenizer (se copia `backbone/` con solo los ficheros del tokenizer) y `opset`. Devuelve tamaños en MB y la diferencia máxima entre torch y ONNX sobre una entrada real (`{"codificador": 1e-4, …}`).
- El codificador se exporta desde una instancia cargada con `atencion="eager"` (ModernBERT con `sdpa`/flash no exporta); las cabezas desde el mismo modelo.
- `CabezaRelaciones.forward_exportable(...)` devuelve `(logits, atencion, logits_vigencia)` sin escribir `self.ultima_atencion`.
- Subcomando `enrel exportar-onnx --modelo DIR --salida DIR_ONNX`.

- [ ] **Paso 1: Test**

```python
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnxruntime")
from enrel.exportar.onnx import exportar_modelo
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel


def test_exportar_tres_grafos(tmp_path: Path):
    m = ModeloEnrel(ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8), atencion="eager")
    r = exportar_modelo(m, tmp_path)
    for f in ("codificador.onnx", "entidades.onnx", "relaciones.onnx", "meta.json"):
        assert (tmp_path / f).exists(), f
    assert max(r["diferencia_max"].values()) < 1e-3
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["clases_finas"][-1] == "vinculo_sin_tipo" and (tmp_path / "backbone" / "tokenizer.json").exists() or (tmp_path / "backbone").exists()
```

- [ ] **Paso 2: Implementar**

En `enrel/modelo/relaciones.py`, extraer el cuerpo de `forward` a `forward_exportable(...) -> tuple[Tensor, Tensor, Tensor]` que devuelve `(logits, atencion, logits_vigencia)`; `forward` lo llama, guarda `self.ultima_atencion = atencion.detach()` y devuelve `(logits, logits_vigencia)` (la firma ya establecida en la etapa 2, Tarea 2.4).

`enrel/exportar/onnx.py`:

```python
"""Exporta el modelo a tres grafos ONNX con ejes dinámicos y verifica contra torch."""

import json
import shutil
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from enrel.esquema.tipos import CLASES_FINAS, TIPOS
from enrel.modelo.enrel import ModeloEnrel
from enrel.modelo.entidades import enumerar_tramos


class _Codificador(torch.nn.Module):
    def __init__(self, bb):
        super().__init__()
        self.bb = bb

    def forward(self, input_ids, attention_mask):
        return self.bb(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state


class _Relaciones(torch.nn.Module):
    def __init__(self, cabeza):
        super().__init__()
        self.c = cabeza

    def forward(self, estados, mascara_tokens, menciones, mascara_menciones, pares, mascara_pares):
        return self.c.forward_exportable(estados, mascara_tokens, menciones, mascara_menciones, pares, mascara_pares)


def _sesion(ruta: Path):
    import onnxruntime as ort
    return ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])


def exportar_modelo(modelo: ModeloEnrel, directorio: Path, opset: int = 17) -> dict:
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    modelo = modelo.cpu().eval()
    tok = modelo.tok
    texto = "El ministro de Hacienda, José Manuel Restrepo, anunció la reforma tributaria en Bogotá."
    enc = tok(texto, return_tensors="pt")
    ids, mask = enc["input_ids"], enc["attention_mask"]
    T = ids.shape[1]
    H = modelo.backbone.config.hidden_size
    dif = {}

    # 1. Codificador
    cod = _Codificador(modelo.backbone)
    with torch.no_grad():
        estados = cod(ids, mask)
    torch.onnx.export(cod, (ids, mask), str(directorio / "codificador.onnx"), input_names=["input_ids", "attention_mask"],
                      output_names=["estados"], opset_version=opset,
                      dynamic_axes={"input_ids": {0: "B", 1: "T"}, "attention_mask": {0: "B", 1: "T"}, "estados": {0: "B", 1: "T"}})
    s = _sesion(directorio / "codificador.onnx")
    est_onnx = s.run(None, {"input_ids": ids.numpy(), "attention_mask": mask.numpy()})[0]
    dif["codificador"] = float(np.abs(est_onnx - estados.numpy()).max())

    # 2. Entidades
    n_pal = 12
    primera = torch.arange(1, n_pal + 1).unsqueeze(0)
    ultima = primera.clone()
    tramos = enumerar_tramos(n_pal, 4).unsqueeze(0)
    masc_t = torch.ones(1, tramos.shape[1], dtype=torch.bool)
    with torch.no_grad():
        le = modelo.entidades(estados, primera, ultima, tramos, masc_t)
    torch.onnx.export(modelo.entidades, (estados, primera, ultima, tramos, masc_t), str(directorio / "entidades.onnx"),
                      input_names=["estados", "primera", "ultima", "tramos", "mascara_tramos"], output_names=["logits_entidades"],
                      opset_version=opset,
                      dynamic_axes={"estados": {0: "B", 1: "T"}, "primera": {0: "B", 1: "P"}, "ultima": {0: "B", 1: "P"},
                                    "tramos": {0: "B", 1: "S"}, "mascara_tramos": {0: "B", 1: "S"}, "logits_entidades": {0: "B", 1: "S"}})
    s = _sesion(directorio / "entidades.onnx")
    le_onnx = s.run(None, {"estados": estados.numpy(), "primera": primera.numpy(), "ultima": ultima.numpy(),
                           "tramos": tramos.numpy(), "mascara_tramos": masc_t.numpy()})[0]
    dif["entidades"] = float(np.abs(le_onnx - le.numpy()).max())

    # 3. Relaciones
    menciones = torch.tensor([[[1, 5, 0], [3, 0, 0], [7, 9, 0]]])
    masc_m = torch.tensor([[[1, 1, 0], [1, 0, 0], [1, 1, 0]]], dtype=torch.bool)
    pares = torch.tensor([[[0, 1], [1, 2], [2, 0]]])
    masc_p = torch.ones(1, 3, dtype=torch.bool)
    rel = _Relaciones(modelo.relaciones)
    with torch.no_grad():
        lr, at, lrv = rel(estados, mask.bool(), menciones, masc_m, pares, masc_p)
    torch.onnx.export(rel, (estados, mask.bool(), menciones, masc_m, pares, masc_p), str(directorio / "relaciones.onnx"),
                      input_names=["estados", "mascara_tokens", "menciones", "mascara_menciones", "pares", "mascara_pares"],
                      output_names=["logits_relaciones", "atencion", "logits_vigencia"], opset_version=opset,
                      dynamic_axes={"estados": {0: "B", 1: "T"}, "mascara_tokens": {0: "B", 1: "T"}, "menciones": {0: "B", 1: "G", 2: "M"},
                                    "mascara_menciones": {0: "B", 1: "G", 2: "M"}, "pares": {0: "B", 1: "R"}, "mascara_pares": {0: "B", 1: "R"},
                                    "logits_relaciones": {0: "B", 1: "R"}, "atencion": {0: "B", 1: "R", 2: "T"}, "logits_vigencia": {0: "B", 1: "R"}})
    s = _sesion(directorio / "relaciones.onnx")
    lr_onnx, _, lrv_onnx = s.run(None, {"estados": estados.numpy(), "mascara_tokens": mask.bool().numpy(), "menciones": menciones.numpy(),
                                        "mascara_menciones": masc_m.numpy(), "pares": pares.numpy(), "mascara_pares": masc_p.numpy()})
    dif["relaciones"] = max(float(np.abs(lr_onnx - lr.numpy()).max()), float(np.abs(lrv_onnx - lrv.numpy()).max()))

    # 4. Tokenizer y meta
    tok.save_pretrained(directorio / "backbone")
    for f in (directorio / "backbone").glob("*.safetensors"):
        f.unlink()
    meta = {"config": asdict(modelo.config), "clases_finas": list(CLASES_FINAS), "tipos": list(TIPOS), "opset": opset,
            "hidden": H, "tokenizer": "backbone", "precision": "fp32"}
    (directorio / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"mb": {f.name: round(f.stat().st_size / 2**20, 1) for f in directorio.glob("*.onnx")}, "diferencia_max": dif}
```

`enrel/exportar/cli_exportar.py`: subcomando `exportar-onnx` (`--modelo`, `--salida`) que carga con `ModeloEnrel.cargar(dir, atencion="eager")` y llama a `exportar_modelo`, imprimiendo el resultado. Registrar.

- [ ] **Paso 3: Correr test, exportar el candidato y commit**

```bash
uv run pytest tests/test_exportar_onnx.py -q
uv run enrel exportar-onnx --modelo corridas/<candidato>/mejor --salida datos/onnx/v0.1-fp32
git add enrel/exportar/__init__.py enrel/exportar/onnx.py enrel/exportar/cli_exportar.py enrel/modelo/relaciones.py enrel/_subcomandos.py tests/test_exportar_onnx.py
git commit -m "Exporta el modelo a tres grafos ONNX con verificación contra torch"
```

Si la exportación del codificador falla con ModernBERT por operadores no soportados (`unpad`/`flash`), probar `opset 18` y `dynamo=False`; si sigue fallando, exportar con `torch.onnx.export(..., dynamo=True)`; anotar cuál funcionó en `meta.json`.

---

### Tarea 3.3: Pipeline de inferencia sobre ONNX Runtime

**Ficheros:**
- Crear: `enrel/inferencia/onnx_pipeline.py`
- Test: `tests/test_onnx_pipeline.py`

**Interfaces:**
- `class PipelineONNX: __init__(directorio: Path, hilos: int = 4, max_len: int = 8192, solape: int = 512, alias: dict | None = None)`: carga `meta.json`, el tokenizer de `backbone/`, y tres `InferenceSession` con `intra_op_num_threads = hilos` (busca `codificador-int8.onnx` si `meta["precision"] == "int8"`, etc.). `extraer(texto, meta=None) -> Documento` y `extraer_documentos(docs)` con **la misma lógica** que `Pipeline` (Tarea 2.10) pero con numpy: para no duplicar la lógica, refactorizar `Pipeline` en la etapa 2 de modo que los pasos de decodificación, agrupación, recorte y agregación estén en funciones puras que reciben arrays (`decodificar_menciones` ya recibe tensores; aceptar `numpy` convirtiendo con `torch.from_numpy` es aceptable porque `torch` sigue instalado en desarrollo, **pero** el pipeline ONNX publicado no debe importar torch). Decisión: `onnx_pipeline.py` reimplementa `decodificar_menciones` y `decodificar_umbral`/`confianzas` en numpy (`_decodificar_menciones_np`, `_decodificar_relaciones_np`) y reutiliza `agrupar`, `filtrar_*`, `ventanas`, `enumerar_tramos` (devuelve lista) y `mascara_tipos` (convertir a numpy con `.numpy()`; `mascara_tipos` vive en `modelo/enrel.py`, que importa torch: mover `TABLA_TIPOS` y `mascara_tipos` a `enrel/esquema/mascaras.py` **sin torch**, devolviendo `numpy.ndarray`, y hacer que `modelo/enrel.py` la envuelva con `torch.from_numpy`). Esta refactorización es parte de la tarea.
- Test de equivalencia: `Pipeline` (torch) y `PipelineONNX` sobre el mismo texto y el mismo modelo tiny producen el mismo `Documento` (menciones, grupos, relaciones y su vigencia iguales; confianzas con tolerancia 1e-3). `relaciones.onnx` tiene ahora tres salidas (`logits_relaciones`, `atencion`, `logits_vigencia`); `PipelineONNX` decodifica la vigencia por par con `VIGENCIAS[argmax(logits_vigencia)]`, igual que `Pipeline`.

- [ ] **Paso 1: Test**

```python
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnxruntime")
from enrel.exportar.onnx import exportar_modelo
from enrel.inferencia.onnx_pipeline import PipelineONNX
from enrel.inferencia.pipeline import Pipeline
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel


def test_onnx_equivale_a_torch(tmp_path: Path):
    m = ModeloEnrel(ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8), atencion="eager")
    exportar_modelo(m, tmp_path)
    texto = " ".join(["El ministro Gustavo Petro nombró a Luis Carlos Reyes en Bogotá."] * 6)
    a = Pipeline(m, max_len=96, solape=8).extraer(texto, {"doc_id": "x"})
    b = PipelineONNX(tmp_path, hilos=2, max_len=96, solape=8).extraer(texto, {"doc_id": "x"})
    assert [(x.ini, x.fin, x.tipo, x.grupo) for x in a.menciones] == [(x.ini, x.fin, x.tipo, x.grupo) for x in b.menciones]
    assert {(r.cabeza, r.cola, r.relacion, r.atributo, r.vigencia) for r in a.relaciones} == {(r.cabeza, r.cola, r.relacion, r.atributo, r.vigencia) for r in b.relaciones}
```

- [ ] **Paso 2: Implementar**

Primero la refactorización: `enrel/esquema/mascaras.py` con `TABLA_TIPOS: dict[str, dict[str, np.ndarray]]` y `mascara_tipos(tipos_cabeza, tipos_cola) -> np.ndarray [R, C] bool`; `enrel/modelo/enrel.py` importa de ahí y expone `mascara_tipos` como `torch.from_numpy(mascaras.mascara_tipos(...))` para no romper a 2.7 y 2.10. Ejecutar la suite completa después.

`enrel/inferencia/onnx_pipeline.py`:

```python
"""Inferencia con ONNX Runtime, sin torch: la misma lógica que Pipeline con arrays de numpy."""

import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Mencion, Relacion
from enrel.datos.normalizar import nfc
from enrel.datos.validar import validar_documento
from enrel.esquema.mascaras import mascara_tipos
from enrel.esquema.tipos import CLASES_FINAS, TIPOS, VIGENCIAS, desglosar
from enrel.inferencia.decodificar import oracion_de
from enrel.maestro.filtros import filtrar_menciones, filtrar_relaciones
from enrel.modelo.tokenizacion import Codificacion, palabra_de, ventanas

C = len(CLASES_FINAS)
NINGUNO = len(TIPOS)


def _enumerar_tramos(n: int, max_ancho: int) -> list[tuple[int, int]]:
    return [(i, j) for i in range(n) for j in range(i, min(n, i + max_ancho))]


def _softmax(x: np.ndarray, eje: int = -1) -> np.ndarray:
    e = np.exp(x - x.max(axis=eje, keepdims=True))
    return e / e.sum(axis=eje, keepdims=True)


def _decodificar_menciones_np(logits: np.ndarray, tramos: list[tuple[int, int]], cod: Codificacion) -> list[Mencion]:
    probs = _softmax(logits.astype(np.float32))
    clase = probs.argmax(-1)
    conf = probs.max(-1)
    cand = sorted(((float(conf[k]), int(clase[k]), tramos[k]) for k in range(len(tramos)) if int(clase[k]) != NINGUNO), key=lambda x: -x[0])
    elegidos = []
    for c, t, (i, j) in cand:
        if any(t == t2 and i <= j2 and i2 <= j for _, t2, (i2, j2) in elegidos):
            continue
        elegidos.append((c, t, (i, j)))
    elegidos.sort(key=lambda x: x[2])
    out = []
    for k, (c, t, (i, j)) in enumerate(elegidos):
        ini, fin = cod.palabras[i][0], cod.palabras[j][1]
        out.append(Mencion(f"m{k + 1}", ini, fin, cod.texto[ini - cod.desplazamiento:fin - cod.desplazamiento], TIPOS[t], "", round(c, 4)))
    return out


class PipelineONNX:
    def __init__(self, directorio: Path, hilos: int = 4, max_len: int = 8192, solape: int = 512, alias: dict | None = None):
        d = Path(directorio)
        self.meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        self.tok = AutoTokenizer.from_pretrained(d / self.meta.get("tokenizer", "backbone"))
        sufijo = {"fp32": "", "fp16": "-fp16", "int8": "-int8"}[self.meta.get("precision", "fp32")]
        op = ort.SessionOptions()
        op.intra_op_num_threads = hilos
        self.s_cod = ort.InferenceSession(str(d / f"codificador{sufijo}.onnx"), op, providers=["CPUExecutionProvider"])
        self.s_ent = ort.InferenceSession(str(d / f"entidades{sufijo}.onnx"), op, providers=["CPUExecutionProvider"])
        self.s_rel = ort.InferenceSession(str(d / f"relaciones{sufijo}.onnx"), op, providers=["CPUExecutionProvider"])
        self.max_len, self.solape, self.alias = max_len, solape, alias
        self.max_ancho = self.meta["config"]["max_ancho"]
        self.max_grupos = self.meta["config"]["max_grupos"]

    def _estados(self, cod: Codificacion) -> np.ndarray:
        ids = np.array([cod.input_ids], dtype=np.int64)
        mask = np.array([cod.attention_mask], dtype=np.int64)
        return self.s_cod.run(None, {"input_ids": ids, "attention_mask": mask})[0]

    def extraer(self, texto: str, meta: dict | None = None) -> Documento:
        meta = meta or {}
        texto = nfc(texto)
        cods = ventanas(self.tok, texto, self.max_len, self.solape)
        vistas: dict[tuple[int, int, str], Mencion] = {}
        estados = []
        for cod in cods:
            est = self._estados(cod)
            estados.append(est)
            tramos = _enumerar_tramos(len(cod.palabras), self.max_ancho)
            if not tramos:
                continue
            logits = self.s_ent.run(None, {
                "estados": est, "primera": np.array([cod.primera_subpalabra], dtype=np.int64), "ultima": np.array([cod.ultima_subpalabra], dtype=np.int64),
                "tramos": np.array([tramos], dtype=np.int64), "mascara_tramos": np.ones((1, len(tramos)), dtype=bool)})[0][0]
            for m in _decodificar_menciones_np(logits, tramos, cod):
                clave = (m.ini, m.fin, m.tipo)
                if clave not in vistas or (m.confianza or 0) > (vistas[clave].confianza or 0):
                    vistas[clave] = m
        menciones = sorted(vistas.values(), key=lambda m: (m.ini, m.fin))
        for k, m in enumerate(menciones):
            m.id = f"m{k + 1}"
        menciones, _ = filtrar_menciones(texto, menciones)
        grupos = agrupar(menciones, self.alias)
        conteo = {g.id: sum(1 for m in menciones if m.grupo == g.id) for g in grupos}
        recorte = max(0, len(grupos) - self.max_grupos)
        grupos = sorted(sorted(grupos, key=lambda g: -conteo[g.id])[:self.max_grupos], key=lambda g: int(g.id[1:]))
        vivos = {g.id for g in grupos}
        menciones = [m for m in menciones if m.grupo in vivos]
        indice = {g.id: k for k, g in enumerate(grupos)}
        tipos = [g.tipo for g in grupos]
        relaciones: list[Relacion] = []
        if len(grupos) >= 2:
            pares_todos = [(a, b) for a in range(len(grupos)) for b in range(len(grupos)) if a != b]
            masc = mascara_tipos([tipos[a] for a, _ in pares_todos], [tipos[b] for _, b in pares_todos])
            logits_max = np.full((len(pares_todos), C + 1), -np.inf, dtype=np.float32)
            evidencia_mejor: list[tuple[int, int] | None] = [None] * len(pares_todos)
            vigencia_mejor: list[str] = ["vigente"] * len(pares_todos)
            for cod, est in zip(cods, estados):
                por_grupo = [[] for _ in grupos]
                for m in menciones:
                    pj = palabra_de(cod, m.ini, m.fin)
                    if pj is not None:
                        por_grupo[indice[m.grupo]].append(cod.primera_subpalabra[pj[0]])
                presentes = {k for k, ms in enumerate(por_grupo) if ms}
                pares = [p for p in pares_todos if p[0] in presentes and p[1] in presentes]
                if not pares:
                    continue
                M = max(len(ms) for ms in por_grupo) or 1
                men = np.zeros((1, len(grupos), M), dtype=np.int64)
                mm = np.zeros((1, len(grupos), M), dtype=bool)
                for k, ms in enumerate(por_grupo):
                    men[0, k, :len(ms)] = ms
                    mm[0, k, :len(ms)] = True
                logits, atencion, logits_vig = self.s_rel.run(None, {
                    "estados": est, "mascara_tokens": np.array([cod.attention_mask], dtype=bool), "menciones": men, "mascara_menciones": mm,
                    "pares": np.array([pares], dtype=np.int64), "mascara_pares": np.ones((1, len(pares)), dtype=bool)})
                for r, p in enumerate(pares):
                    i = pares_todos.index(p)
                    if logits[0, r].max() > logits_max[i].max():
                        sub = int(atencion[0, r].argmax())
                        pal = next((k for k, (a, b) in enumerate(zip(cod.primera_subpalabra, cod.ultima_subpalabra)) if a <= sub <= b), None)
                        if pal is not None:
                            o = oracion_de(cod.texto, cod.palabras[pal][0] - cod.desplazamiento)
                            evidencia_mejor[i] = (o[0] + cod.desplazamiento, o[1] + cod.desplazamiento)
                        vigencia_mejor[i] = VIGENCIAS[int(logits_vig[0, r].argmax())]
                    logits_max[i] = np.maximum(logits_max[i], logits[0, r])
            for i, (a, b) in enumerate(pares_todos):
                if not np.isfinite(logits_max[i]).all():
                    continue
                clases = np.where(masc[i], logits_max[i, :C], -np.inf)
                th = logits_max[i, C]
                conf = 1 / (1 + np.exp(-(logits_max[i, :C] - th)))
                for c in np.nonzero(clases > th)[0].tolist():
                    rel, atr = desglosar(CLASES_FINAS[c])
                    relaciones.append(Relacion(grupos[a].id, grupos[b].id, rel, atr, evidencia_mejor[i], round(float(conf[c]), 4),
                                               vigencia=vigencia_mejor[i]))
        relaciones, _ = filtrar_relaciones(relaciones, {g.id: g for g in grupos})
        doc = Documento(meta.get("doc_id", "texto"), texto, menciones, grupos, relaciones, meta.get("url", ""), meta.get("fecha", ""),
                        meta.get("seccion", ""), meta.get("titulo", ""), "modelo",
                        {"modelo": self.meta["config"]["version"], "ventanas": len(cods), "recorte_grupos": recorte, "motor": "onnxruntime",
                         "precision": self.meta.get("precision", "fp32")})
        errores = validar_documento(doc)
        if errores:
            raise ValueError("\n".join(errores))
        return doc

    def extraer_documentos(self, docs: list[Documento]) -> list[Documento]:
        return [self.extraer(d.texto, {"doc_id": d.doc_id, "url": d.url, "fecha": d.fecha, "seccion": d.seccion, "titulo": d.titulo}) for d in docs]
```

Actualizar `enrel extraer` y `enrel predecir-conjunto` (etapa 2) para aceptar `--onnx DIR` en vez de `--modelo DIR`, usando `PipelineONNX`. `transformers` sigue siendo dependencia del pipeline ONNX solo por el tokenizer; anotar como mejora futura sustituirlo por `tokenizers`.

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest -q
git add enrel/esquema/mascaras.py enrel/modelo/enrel.py enrel/inferencia/onnx_pipeline.py enrel/inferencia/cli_extraer.py tests/test_onnx_pipeline.py
git commit -m "Añade el pipeline de inferencia sobre ONNX Runtime, equivalente al de torch"
```

---

### Tarea 3.4: Cuantización y comparación fp32 / fp16 / int8 sobre la prueba

**Ficheros:**
- Crear: `enrel/exportar/cuantizar.py`
- Modificar: `enrel/exportar/cli_exportar.py`
- Test: `tests/test_exportar_cuantizar.py` (CPU, tiny)

**Interfaces:**
- `cuantizar_int8(dir_fp32: Path, dir_salida: Path) -> dict`: `quantize_dynamic` con `QuantType.QInt8` sobre los tres grafos → `*-int8.onnx`, copia `backbone/` y escribe `meta.json` con `precision = "int8"`; devuelve MB por fichero.
- `convertir_fp16(dir_fp32: Path, dir_salida: Path) -> dict`: `onnxconverter_common.float16.convert_float_to_float16` (añadir `onnxconverter-common` al extra `modelo`) con `keep_io_types=True` → `*-fp16.onnx`, `precision = "fp16"`. Si la conversión falla en el codificador por operadores sin soporte fp16 en CPU, se anota y se omite fp16.
- `comparar_precisiones(dirs: dict[str, Path], prueba: Path, hilos: int = 4) -> str`: corre `PipelineONNX` de cada variante sobre la prueba, evalúa con `evaluar_entidades` estricto y `evaluar_relaciones` RE+, mide segundos por documento y RSS, y devuelve una tabla markdown con la decisión según la tolerancia (int8 si pierde ≤ 1 punto de entidades y ≤ 2 de RE+ respecto a fp32; si no, fp16 si existe; si no, fp32).
- Subcomando `enrel cuantizar --fp32 DIR --salida-int8 DIR --salida-fp16 DIR --prueba datos/conjuntos/prueba.jsonl --informe docs/resultados/etapa-3-cuantizacion.md`.

- [ ] **Paso 1: Test**

```python
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnxruntime")
from enrel.exportar.cuantizar import cuantizar_int8
from enrel.exportar.onnx import exportar_modelo
from enrel.inferencia.onnx_pipeline import PipelineONNX
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel


def test_int8_corre(tmp_path: Path):
    m = ModeloEnrel(ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8), atencion="eager")
    exportar_modelo(m, tmp_path / "fp32")
    r = cuantizar_int8(tmp_path / "fp32", tmp_path / "int8")
    assert (tmp_path / "int8" / "codificador-int8.onnx").exists() and r["codificador-int8.onnx"] > 0
    d = PipelineONNX(tmp_path / "int8", hilos=1, max_len=64).extraer("Gustavo Petro nombró a Reyes.")
    assert d.origen["precision"] == "int8"
```

- [ ] **Paso 2: Implementar `enrel/exportar/cuantizar.py`**

```python
"""Cuantización int8 dinámica y conversión fp16 de los grafos ONNX, y su comparación sobre la prueba."""

import json
import resource
import shutil
import statistics
import time
from pathlib import Path

from enrel.datos.documento import cargar_jsonl
from enrel.evaluacion.entidades import evaluar_entidades
from enrel.evaluacion.relaciones import evaluar_relaciones

GRAFOS = ("codificador", "entidades", "relaciones")


def _copiar_base(origen: Path, destino: Path, precision: str) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    if (destino / "backbone").exists():
        shutil.rmtree(destino / "backbone")
    shutil.copytree(origen / "backbone", destino / "backbone")
    meta = json.loads((origen / "meta.json").read_text(encoding="utf-8"))
    meta["precision"] = precision
    (destino / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def cuantizar_int8(dir_fp32: Path, dir_salida: Path) -> dict:
    from onnxruntime.quantization import QuantType, quantize_dynamic
    dir_fp32, dir_salida = Path(dir_fp32), Path(dir_salida)
    _copiar_base(dir_fp32, dir_salida, "int8")
    out = {}
    for g in GRAFOS:
        destino = dir_salida / f"{g}-int8.onnx"
        quantize_dynamic(str(dir_fp32 / f"{g}.onnx"), str(destino), weight_type=QuantType.QInt8)
        out[destino.name] = round(destino.stat().st_size / 2**20, 1)
    return out


def convertir_fp16(dir_fp32: Path, dir_salida: Path) -> dict:
    import onnx
    from onnxconverter_common import float16
    dir_fp32, dir_salida = Path(dir_fp32), Path(dir_salida)
    _copiar_base(dir_fp32, dir_salida, "fp16")
    out = {}
    for g in GRAFOS:
        modelo = onnx.load(str(dir_fp32 / f"{g}.onnx"))
        m16 = float16.convert_float_to_float16(modelo, keep_io_types=True)
        destino = dir_salida / f"{g}-fp16.onnx"
        onnx.save(m16, str(destino))
        out[destino.name] = round(destino.stat().st_size / 2**20, 1)
    return out


def comparar_precisiones(dirs: dict[str, Path], prueba: Path, hilos: int = 4) -> str:
    from enrel.inferencia.onnx_pipeline import PipelineONNX
    oro = cargar_jsonl(prueba)
    filas, base = [], None
    for nombre, d in dirs.items():
        p = PipelineONNX(d, hilos=hilos)
        tiempos, preds = [], []
        for doc in oro:
            t0 = time.perf_counter()
            preds.append(p.extraer(doc.texto, {"doc_id": doc.doc_id}))
            tiempos.append((time.perf_counter() - t0) / max(1, len(doc.texto.split()) / 1000))
        ent = evaluar_entidades(oro, preds, "estricto")["__global__"].f1
        re_mas = evaluar_relaciones(oro, preds, "gruesa", exigir_tipos=True)["__micro__"].f1
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20
        fila = {"variante": nombre, "entidades": ent, "re_mas": re_mas, "s_por_1000_pal": statistics.median(tiempos), "rss_gb": rss}
        if nombre == "fp32":
            base = fila
        filas.append(fila)
    decision = "fp32"
    for cand in ("int8", "fp16"):
        f = next((x for x in filas if x["variante"] == cand), None)
        if f and base and base["entidades"] - f["entidades"] <= 0.01 and base["re_mas"] - f["re_mas"] <= 0.02:
            decision = cand
            break
    lineas = ["| Variante | Entidades F1 | RE+ F1 | s / 1.000 palabras (mediana, 4 hilos) | RSS GB |", "|---|---:|---:|---:|---:|"]
    for f in filas:
        lineas.append(f"| {f['variante']} | {f['entidades']:.3f} | {f['re_mas']:.3f} | {f['s_por_1000_pal']:.2f} | {f['rss_gb']:.2f} |")
    lineas.append(f"\n**Decisión:** se publica **{decision}** como predeterminada (tolerancia: ≤ 1 punto de entidades y ≤ 2 de RE+ frente a fp32).")
    return "\n".join(lineas)
```

Subcomando `cuantizar` en `cli_exportar.py`: llama a `cuantizar_int8`, intenta `convertir_fp16` (captura la excepción y la anota), corre `comparar_precisiones` bajo el aviso de usar `taskset -c 0-3`, y escribe el informe.

- [ ] **Paso 3: Correr, medir y commit**

```bash
uv run pytest tests/test_exportar_cuantizar.py -q
taskset -c 0-3 uv run enrel cuantizar --fp32 datos/onnx/v0.1-fp32 --salida-int8 datos/onnx/v0.1-int8 --salida-fp16 datos/onnx/v0.1-fp16 --prueba datos/conjuntos/prueba.jsonl --informe docs/resultados/etapa-3-cuantizacion.md
git add enrel/exportar/cuantizar.py enrel/exportar/cli_exportar.py pyproject.toml uv.lock tests/test_exportar_cuantizar.py docs/resultados/etapa-3-cuantizacion.md
git commit -m "Cuantiza a int8 y fp16 y decide la variante publicada midiendo sobre la prueba"
```

---

### Tarea 3.5: Medición en CPU a cuatro hilos

**Ficheros:**
- Crear: `enrel/exportar/medir_cpu.py`
- Modificar: `enrel/exportar/cli_exportar.py`
- Test: `tests/test_medir_cpu.py` (CPU, tiny, 3 documentos)

**Interfaces:**
- `medir(pipeline, docs: list[Documento], repeticiones_calentamiento: int = 2) -> dict`: calienta con los primeros documentos, después mide cada documento: segundos, palabras, tokens aproximados (`len(texto) / 4`), y devuelve `{"n", "mediana_s_por_1000_pal", "p95_s_por_1000_pal", "mediana_s_por_doc", "rss_gb", "docs_por_hora"}`.
- `informe_cpu(resultados: dict, meta: dict) -> str`: markdown con la tabla, el comando, la CPU (`/proc/cpuinfo` `model name`), los hilos y si cumple las metas (< 5 s por 1.000 palabras, RSS < 2 GB).
- Subcomando `enrel medir-cpu --onnx DIR --entrada datos/conjuntos/prueba.jsonl [--extra datos/corpus/articulos.jsonl --n 200] --hilos 4 --informe docs/resultados/etapa-3-cpu.md`. Se ejecuta con `taskset -c 0-3`. Si se pasa `--extra`, completa hasta `n` documentos con artículos del corpus congelado (los primeros `n - len(prueba)` de la selección de plata, por reproducibilidad).

- [ ] **Paso 1: Test**

```python
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnxruntime")
from enrel.datos.documento import Documento
from enrel.exportar.medir_cpu import medir
from enrel.exportar.onnx import exportar_modelo
from enrel.inferencia.onnx_pipeline import PipelineONNX
from enrel.modelo.enrel import ConfigModelo, ModeloEnrel


def test_medir(tmp_path: Path):
    m = ModeloEnrel(ConfigModelo(backbone="hf-internal-testing/tiny-random-bert", tam_grupo=8), atencion="eager")
    exportar_modelo(m, tmp_path)
    p = PipelineONNX(tmp_path, hilos=1, max_len=64)
    docs = [Documento(f"d{i}", "Gustavo Petro nombró a Reyes. " * 20, [], [], []) for i in range(3)]
    r = medir(p, docs, repeticiones_calentamiento=1)
    assert r["n"] == 3 and r["mediana_s_por_1000_pal"] > 0 and r["rss_gb"] > 0
```

- [ ] **Paso 2: Implementar**

```python
"""Mide el pipeline ONNX en CPU: segundos por 1.000 palabras, por documento, y memoria."""

import platform
import resource
import statistics
import time
from datetime import date
from pathlib import Path

from enrel.datos.documento import Documento


def _cpu() -> str:
    try:
        for linea in Path("/proc/cpuinfo").read_text().splitlines():
            if linea.startswith("model name"):
                return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "desconocida"


def medir(pipeline, docs: list[Documento], repeticiones_calentamiento: int = 2) -> dict:
    for d in docs[:repeticiones_calentamiento]:
        pipeline.extraer(d.texto, {"doc_id": d.doc_id})
    por_mil, por_doc = [], []
    for d in docs:
        palabras = max(1, len(d.texto.split()))
        t0 = time.perf_counter()
        pipeline.extraer(d.texto, {"doc_id": d.doc_id})
        s = time.perf_counter() - t0
        por_doc.append(s)
        por_mil.append(s * 1000 / palabras)
    por_mil.sort()
    return {"n": len(docs), "mediana_s_por_1000_pal": statistics.median(por_mil), "p95_s_por_1000_pal": por_mil[int(0.95 * (len(por_mil) - 1))],
            "mediana_s_por_doc": statistics.median(por_doc), "rss_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20,
            "docs_por_hora": 3600 / statistics.mean(por_doc), "cpu": _cpu()}


def informe_cpu(r: dict, meta: dict, hilos: int, comando: str) -> str:
    cumple = r["mediana_s_por_1000_pal"] < 5.0 and r["rss_gb"] < 2.0
    return "\n".join([
        f"# Rendimiento en CPU · {meta.get('precision', 'fp32')}", "",
        f"Fecha: {date.today().isoformat()} · CPU: {r['cpu']} · hilos: {hilos} · documentos: {r['n']} · comando: `{comando}`", "",
        "| Métrica | Valor | Meta |", "|---|---:|---|",
        f"| Mediana s / 1.000 palabras | {r['mediana_s_por_1000_pal']:.2f} | < 5 |",
        f"| p95 s / 1.000 palabras | {r['p95_s_por_1000_pal']:.2f} | — |",
        f"| Mediana s / documento | {r['mediana_s_por_doc']:.2f} | — |",
        f"| Documentos / hora | {r['docs_por_hora']:.0f} | — |",
        f"| RSS máximo GB | {r['rss_gb']:.2f} | < 2 |", "",
        f"**{'Cumple' if cumple else 'No cumple'} las metas de la spec §4.6.**",
        "", "Un i5 de portátil con 4 núcleos y sin AVX-512 rinde por debajo de este Ryzen limitado a 4 hilos; la cifra es una cota optimista y se dice así en la ficha.",
    ])
```

- [ ] **Paso 3: Correr, medir y commit**

```bash
uv run pytest tests/test_medir_cpu.py -q
taskset -c 0-3 uv run enrel medir-cpu --onnx datos/onnx/v0.1-<decision> --entrada datos/conjuntos/prueba.jsonl --extra datos/corpus/articulos.jsonl --n 200 --hilos 4 --informe docs/resultados/etapa-3-cpu.md
git add enrel/exportar/medir_cpu.py enrel/exportar/cli_exportar.py tests/test_medir_cpu.py docs/resultados/etapa-3-cpu.md
git commit -m "Mide el pipeline ONNX en CPU a cuatro hilos"
```

---

### Tarea 3.6: Exportador a FollowTheMoney

**Ficheros:**
- Crear: `enrel/esquema/ftm.py`, `enrel/esquema/cli_ftm.py`
- Modificar: `enrel/inferencia/cli_extraer.py` (formato `ftm`)
- Test: `tests/test_ftm.py`

**Interfaces:**
- `a_followthemoney(doc: Documento, publisher: str = "", extractor: str = "enrel") -> list[dict]`: una entidad FtM por grupo y una por relación, en el formato JSON de FtM (`{"id", "schema", "properties": {...}}`):
  - Grupos: `persona → Person {name, alias (las demás menciones distintas)}`; `organizacion → Organization {name, alias}`; `lugar → Address {full}`; `cargo → Position {name}`; `norma → Document {title}` (FtM no tiene esquema de norma; se usa `Document` con `title` y `summary = "norma"`). `obra` y `monto` no llegan aquí: se retiraron del esquema de tipos (§3.1), así que el modelo no los produce. `id` = `sha1(doc_id + "|" + grupo.id + "|" + plegar(canonico))` en hexadecimal.
  - Relaciones → esquema FtM y propiedades según la tabla de la spec §3.2: `ocupa_cargo → Occupancy {holder, post, status}` con `status` derivado de la vigencia y del atributo (ver abajo), no solo del atributo; `nombro_a → UnknownLink {subject, object, role: "nombró a"}`; `sucedio_a → Succession {predecessor, successor}`; `miembro_de → Membership {member, organization}`; `trabaja_en → Employment {employee, employer}`; `dirige → Directorship {director, organization}`; `fundo → Directorship {director, organization, role: "fundador"}`; `propietario_de → Ownership {owner, asset}`; `socio_de → Associate {person, associate}`; `parte_de → Membership {member, organization, role: "parte de"}`; `familiar_de → Family {person, relative, relationship: <parentesco en español>}` (para `hijo_de`, `person` es el hijo y `relationship = "hijo/a"`); `financia_a → Payment {payer, beneficiary}`; `contrato_a → ContractAward` no encaja sin un `Contract`: se emite `UnknownLink {subject, object, role: "contrató a"}`; `investigado_por → UnknownLink {subject, object, role: "investigado por" | "acusado por" | "condenado por"}`; `ubicado_en → UnknownLink {subject, object, role: "ubicado en"}`; `apoya_a → UnknownLink {role: "apoya a"}` (destino persona, organizacion, cargo o, desde la corrección del esquema, norma; `UnknownLink` no distingue tipo de nodo, así que no necesita cambio de código); `impulsa_norma → UnknownLink {subject, object, role: "impulsó la norma"}` (relación nueva, separada de apoya_a por el acto legislativo); `se_opone_a → UnknownLink {role: "se opone a"}` (mismo caso, destino puede ser norma); `vinculo_sin_tipo → UnknownLink`.
  - La vigencia mapea al estado de toda arista, sustituyendo la vieja lógica que derivaba `status` solo del atributo de `ocupa_cargo`: `vigente` → `status: current` y `date = doc.fecha`; `pasada` → `status: ended` y `endDate = doc.fecha` (como cota superior, no como fecha exacta del cese); `futura` → `status: current` con una nota en `summary` («anunciado, aún no vigente en la fecha del artículo»). Solo `Occupancy` tiene `status`; en las demás relaciones la vigencia solo mueve `date`/`endDate` y la nota de `summary`. En `ocupa_cargo`, el atributo (titular/aspirante) se combina con la vigencia: aspirante vigente o futura → `status: candidate`; aspirante pasada → `status: ended` (ya no es candidato); titular sigue la regla general de arriba.
  - Todas las aristas llevan `sourceUrl = doc.url`, `publisher`, `retrievedAt` (fecha de hoy ISO), `summary` (la evidencia recortada a 300 caracteres, con la nota de «anunciado» antepuesta si la vigencia es futura), `description = f"confianza {confianza:.2f}; extractor {extractor} {doc.origen.get('modelo', '')}"`, y `date` o `endDate` según la vigencia (arriba).
- `escribir_ftm(entidades: list[dict], ruta: Path)`: JSONL, una entidad por línea (formato que `ftm` y Aleph importan).
- Si el paquete `followthemoney` está instalado (extra `ftm`), un test opcional valida cada entidad con `model.get_proxy(d)` y `proxy.schema.validate`.

- [ ] **Paso 1: Test**

```python
from enrel.datos.documento import Relacion
from enrel.esquema.ftm import _arista, a_followthemoney
from tests.test_datos_documento import doc_ejemplo


def test_ftm_basico():
    d = doc_ejemplo()
    ents = a_followthemoney(d, publisher="La Silla Vacía")
    esquemas = {e["schema"] for e in ents}
    assert {"Person", "Position", "Organization", "Occupancy", "UnknownLink"} <= esquemas
    occ = next(e for e in ents if e["schema"] == "Occupancy")
    assert occ["properties"]["status"] == ["current"] and occ["properties"]["sourceUrl"] == ["https://x"]
    assert "endDate" not in occ["properties"]                                                 # vigente por defecto
    if d.fecha:
        assert occ["properties"]["date"] == [d.fecha]
    assert all(len(e["id"]) == 40 for e in ents)
    persona = next(e for e in ents if e["schema"] == "Person" and "Gustavo Petro" in e["properties"]["name"])
    assert persona["properties"]["name"] == ["Gustavo Petro"]


def test_ftm_vigencia_a_estado_y_fechas():
    d = doc_ejemplo()
    d.fecha = "2020-01-01"          # fecha del artículo conocida, sin depender de lo que traiga el fixture
    ids = {g.id: f"id-{g.id}" for g in d.grupos}
    fecha = d.fecha
    # titular + pasada → ended, endDate como cota superior.
    r_pasada = Relacion("e1", "e2", "ocupa_cargo", "titular", vigencia="pasada")
    a = _arista(d, r_pasada, ids, "", "enrel")
    assert a["properties"]["status"] == ["ended"] and a["properties"]["endDate"] == [fecha] and "date" not in a["properties"]
    # titular + futura → current, con nota de anunciado en el resumen.
    r_futura = Relacion("e1", "e2", "ocupa_cargo", "titular", vigencia="futura")
    b = _arista(d, r_futura, ids, "", "enrel")
    assert b["properties"]["status"] == ["current"] and b["properties"]["date"] == [fecha]
    assert "anunciado" in b["properties"].get("summary", [""])[0]
    # aspirante + vigente → candidate; aspirante + pasada → ended (ya no es candidato).
    c = _arista(d, Relacion("e1", "e2", "ocupa_cargo", "aspirante", vigencia="vigente"), ids, "", "enrel")
    assert c["properties"]["status"] == ["candidate"]
    e = _arista(d, Relacion("e1", "e2", "ocupa_cargo", "aspirante", vigencia="pasada"), ids, "", "enrel")
    assert e["properties"]["status"] == ["ended"]
    # una relación sin status propio (no Occupancy) igual mueve date/endDate con la vigencia.
    f = _arista(d, Relacion("e1", "e2", "trabaja_en", vigencia="pasada"), ids, "", "enrel")
    assert f["properties"]["endDate"] == [fecha] and "date" not in f["properties"] and "status" not in f["properties"]
```

- [ ] **Paso 2: Implementar `enrel/esquema/ftm.py`**

```python
"""Exporta un Documento a entidades y aristas de FollowTheMoney (JSON), con procedencia por arista."""

import hashlib
from datetime import date

from enrel.datos.documento import Documento, Grupo, Relacion
from enrel.datos.normalizar import plegar

_ESQUEMA_GRUPO = {"persona": ("Person", "name"), "organizacion": ("Organization", "name"), "lugar": ("Address", "full"),
                  "cargo": ("Position", "name"), "norma": ("Document", "title")}
_PARENTESCO = {"conyuge": "cónyuge", "hijo_de": "hijo/a", "hermano": "hermano/a", "otro": "familiar"}
_ETAPA = {"investigado": "investigado por", "acusado": "acusado por", "condenado": "condenado por"}
_STATUS_DE_VIGENCIA = {"vigente": "current", "pasada": "ended", "futura": "current"}
_NOTA_FUTURA = "anunciado, aún no vigente en la fecha del artículo"


def _estado_ocupa_cargo(vigencia: str, atributo: str | None) -> str:
    # El atributo (titular/aspirante) es una modalidad, no un tiempo (spec §3.2); la vigencia manda en la fecha,
    # y solo aspirante desvía el status hacia "candidate" en vez del genérico current/ended de la vigencia.
    if atributo == "aspirante":
        return "ended" if vigencia == "pasada" else "candidate"
    return _STATUS_DE_VIGENCIA[vigencia]


def _id(*partes: str) -> str:
    return hashlib.sha1("|".join(partes).encode("utf-8")).hexdigest()


def _entidad(doc: Documento, g: Grupo) -> dict:
    esquema, prop = _ESQUEMA_GRUPO[g.tipo]
    alias = sorted({m.texto for m in doc.menciones_de(g.id) if m.texto != g.canonico})
    props = {prop: [g.canonico]}
    if esquema in ("Person", "Organization") and alias:
        props["alias"] = alias
    if g.tipo == "norma":
        props["summary"] = [g.tipo]
    return {"id": _id(doc.doc_id, g.id, plegar(g.canonico)), "schema": esquema, "properties": props}


def _arista(doc: Documento, r: Relacion, ids: dict[str, str], publisher: str, extractor: str) -> dict:
    a, b = ids[r.cabeza], ids[r.cola]
    rel, atr = r.relacion, r.atributo
    if rel == "ocupa_cargo":
        esquema, props = "Occupancy", {"holder": [a], "post": [b], "status": [_estado_ocupa_cargo(r.vigencia, atr)]}
    elif rel == "sucedio_a":
        esquema, props = "Succession", {"successor": [a], "predecessor": [b]}
    elif rel == "miembro_de":
        esquema, props = "Membership", {"member": [a], "organization": [b]}
    elif rel == "parte_de":
        esquema, props = "Membership", {"member": [a], "organization": [b], "role": ["parte de"]}
    elif rel == "trabaja_en":
        esquema, props = "Employment", {"employee": [a], "employer": [b]}
    elif rel == "dirige":
        esquema, props = "Directorship", {"director": [a], "organization": [b]}
    elif rel == "fundo":
        esquema, props = "Directorship", {"director": [a], "organization": [b], "role": ["fundador"]}
    elif rel == "propietario_de":
        esquema, props = "Ownership", {"owner": [a], "asset": [b]}
    elif rel == "socio_de":
        esquema, props = "Associate", {"person": [a], "associate": [b]}
    elif rel == "familiar_de":
        esquema, props = "Family", {"person": [a], "relative": [b], "relationship": [_PARENTESCO[atr]]}
    elif rel == "financia_a":
        esquema, props = "Payment", {"payer": [a], "beneficiary": [b]}
    else:
        rol = {"nombro_a": "nombró a", "contrato_a": "contrató a", "ubicado_en": "ubicado en", "apoya_a": "apoya a",
               "impulsa_norma": "impulsó la norma", "se_opone_a": "se opone a",
               "vinculo_sin_tipo": "vínculo sin tipo"}.get(rel) or _ETAPA.get(atr, rel)
        esquema, props = "UnknownLink", {"subject": [a], "object": [b], "role": [rol]}
    if doc.url:
        props["sourceUrl"] = [doc.url]
    if publisher:
        props["publisher"] = [publisher]
    if doc.fecha:
        # La vigencia manda en la fecha de la arista: pasada usa endDate como cota superior, no una fecha exacta de cese.
        props["endDate" if r.vigencia == "pasada" else "date"] = [doc.fecha]
    props["retrievedAt"] = [date.today().isoformat()]
    resumen = doc.texto[r.evidencia[0]:r.evidencia[1]][:300] if r.evidencia else ""
    if r.vigencia == "futura":
        resumen = f"{resumen} ({_NOTA_FUTURA})".strip()
    if resumen:
        props["summary"] = [resumen]
    props["description"] = [f"confianza {r.confianza if r.confianza is not None else 1.0:.2f}; extractor {extractor} {doc.origen.get('modelo', '')}".strip()]
    return {"id": _id(doc.doc_id, a, b, rel, atr or ""), "schema": esquema, "properties": props}


def a_followthemoney(doc: Documento, publisher: str = "", extractor: str = "enrel") -> list[dict]:
    entidades = [_entidad(doc, g) for g in doc.grupos]
    ids = {g.id: e["id"] for g, e in zip(doc.grupos, entidades)}
    return entidades + [_arista(doc, r, ids, publisher, extractor) for r in doc.relaciones]


def escribir_ftm(entidades: list[dict], ruta) -> None:
    import json
    from pathlib import Path
    with Path(ruta).open("w", encoding="utf-8") as f:
        for e in entidades:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
```

Completar `enrel extraer --formato ftm` para que escriba JSONL de FtM. Test opcional con `followthemoney` bajo `pytest.importorskip`.

- [ ] **Paso 3: Correr tests y commit**

```bash
uv run pytest tests/test_ftm.py -q
git add enrel/esquema/ftm.py enrel/inferencia/cli_extraer.py tests/test_ftm.py pyproject.toml
git commit -m "Añade el exportador a FollowTheMoney, con la vigencia mapeada al estado y las fechas de la arista"
```

---

### Tarea 3.7: Revisión manual de 50 falsos positivos de relaciones

**Ficheros:**
- Crear: `scripts/revisar_falsos_positivos.py`
- Crear: `docs/resultados/etapa-3-falsos-positivos.md` (lo llena el usuario)

**Interfaces:**
- `python scripts/revisar_falsos_positivos.py --oro datos/conjuntos/prueba.jsonl --pred <corrida>/pred-prueba.jsonl --n 50 --semilla 3 --salida docs/resultados/etapa-3-falsos-positivos.md`: toma al azar 50 relaciones de la predicción que no están en el oro (con `emparejar_grupos`, misma lógica que `errores_frecuentes` de la etapa 1), y escribe un markdown con una fila por caso: `doc_id`, cabeza → relación:atributo → cola, confianza, evidencia, y tres casillas para que el usuario marque **una**: `[ ] el modelo se equivoca`, `[ ] el oro omitía una relación correcta`, `[ ] cruza párrafos (el oro no podía marcarla)`. Al final, una sección «Resumen» con tres contadores que el usuario rellena.

- [ ] **Paso 1: Escribir el script**

```python
"""Muestra 50 falsos positivos de relaciones para que una persona diga si son error del modelo, omisión del oro o relación entre párrafos."""

import argparse
import random
from pathlib import Path

from enrel.datos.documento import cargar_jsonl
from enrel.evaluacion.emparejar import alinear, emparejar_grupos


def falsos_positivos(oro, pred):
    out = []
    for o, p in alinear(oro, pred):
        mapa = emparejar_grupos(o, p)
        oro_claves = set()
        for r in o.relaciones:
            gc, gl = mapa.get(r.cabeza), mapa.get(r.cola)
            oro_claves.add((gc, gl, r.relacion))
            oro_claves.add((gl, gc, r.relacion))
        for r in p.relaciones:
            if (r.cabeza, r.cola, r.relacion) not in oro_claves:
                ev = p.texto[r.evidencia[0]:r.evidencia[1]].replace("\n", " ") if r.evidencia else ""
                cruza = bool(r.evidencia) and ("\n\n" in p.texto[min(m.ini for m in p.menciones_de(r.cabeza) + p.menciones_de(r.cola)):
                                                                max(m.fin for m in p.menciones_de(r.cabeza) + p.menciones_de(r.cola))])
                out.append({"doc_id": p.doc_id, "cabeza": p.grupo_de(r.cabeza).canonico, "cola": p.grupo_de(r.cola).canonico,
                            "relacion": r.relacion + (f":{r.atributo}" if r.atributo else ""), "confianza": r.confianza, "evidencia": ev,
                            "posible_cruce": cruza})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oro", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--semilla", type=int, default=3)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    fps = falsos_positivos(cargar_jsonl(a.oro), cargar_jsonl(a.pred))
    random.Random(a.semilla).shuffle(fps)
    muestra = fps[:a.n]
    lineas = [f"# Revisión de {len(muestra)} falsos positivos de relaciones", "",
              f"Total de falsos positivos en la prueba: {len(fps)}. Marca una casilla por caso.", ""]
    for i, f in enumerate(muestra, 1):
        lineas += [f"## {i}. {f['doc_id']} · {f['cabeza']} —{f['relacion']}→ {f['cola']} · confianza {f['confianza']}"
                   + (" · posible cruce de párrafos" if f["posible_cruce"] else ""),
                   f"> {f['evidencia']}", "", "- [ ] el modelo se equivoca", "- [ ] el oro omitía una relación correcta",
                   "- [ ] cruza párrafos (el oro no podía marcarla)", ""]
    lineas += ["## Resumen", "", "- error del modelo: ", "- omisión del oro: ", "- cruce de párrafos: ", ""]
    Path(a.salida).write_text("\n".join(lineas), encoding="utf-8")
    print(a.salida)


if __name__ == "__main__":
    main()
```

- [ ] **Paso 2: Generar y entregar al usuario**

Correr sobre la predicción del modelo candidato. Pedir al usuario que marque los 50 (una hora). Con el resumen, calcular la precisión corregida: `P_corregida = (tp + omisiones_del_oro + cruces) / (tp + fp)` y reportarla en la ficha junto a la estricta.

- [ ] **Paso 3: Commit**

```bash
git add scripts/revisar_falsos_positivos.py docs/resultados/etapa-3-falsos-positivos.md
git commit -m "Añade la revisión manual de falsos positivos y su resultado"
```

---

### Tarea 3.8: Ficha de modelo, README y publicación

**Ficheros:**
- Crear: `docs/ficha-modelo.md`, `scripts/publicar_hf.py`, `docs/resultados/v0.1.md`
- Modificar: `README.md`, `pyproject.toml` (versión `0.1.0`), `enrel/__init__.py`

**Interfaces:**
- `docs/ficha-modelo.md` con estas secciones, en este orden, todas rellenas con cifras de `docs/resultados/`: qué es y para quién; esquema (enlace a `docs/esquema.md`); datos de entrenamiento (fuente, tamaños por conjunto, cómo se anotó la plata, cómo se corrigió el oro, quién lo corrigió, qué no se publica); resultados sobre la prueba con la tabla de tres filas (línea base, techo del maestro, modelo) con intervalos, RE y RE+, por relación con n ≥ 10, la fila «vigencia (tasa = R)» junto a la línea base léxica de referencia, la prueba dirigida aparte, la precisión corregida por la revisión de falsos positivos; rendimiento en CPU con la CPU real usada y el aviso sobre el i5; límites conocidos (relaciones entre párrafos, relaciones colapsadas a vinculo_sin_tipo, sesgo hacia prensa política colombiana, tope de 60 grupos, ventanas); uso previsto y no previsto; licencia y cita; cómo reproducir (comandos por etapa).
- `scripts/publicar_hf.py --repo <org>/enrel-base-es --pesos corridas/<candidato>/mejor --onnx datos/onnx/v0.1-<decision> --ficha docs/ficha-modelo.md --confirmar`: usa `huggingface_hub.HfApi` para crear el repositorio (privado por defecto; `--publico` lo hace público), subir `backbone/`, `cabezas.safetensors`, `config.json`, la carpeta ONNX bajo `onnx/`, y la ficha como `README.md` con el bloque YAML de metadatos (`language: es`, `license: apache-2.0`, `tags: [ner, relation-extraction, spanish, journalism]`, `base_model: BSC-LT/MrBERT-es`). Sin `--confirmar` solo imprime lo que haría.

- [ ] **Paso 1: Escribir la ficha y el script; actualizar README y versión**

`scripts/publicar_hf.py`:

```python
"""Publica pesos, ONNX y ficha en Hugging Face. Sin --confirmar solo describe lo que haría."""

import argparse
from pathlib import Path

CABECERA = """---
language: es
license: apache-2.0
tags: [ner, relation-extraction, spanish, journalism, knowledge-graph]
base_model: BSC-LT/MrBERT-es
pipeline_tag: token-classification
---
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pesos", required=True)
    ap.add_argument("--onnx", required=True)
    ap.add_argument("--ficha", default="docs/ficha-modelo.md")
    ap.add_argument("--publico", action="store_true")
    ap.add_argument("--confirmar", action="store_true")
    a = ap.parse_args()
    plan = [f"crear repo {a.repo} ({'público' if a.publico else 'privado'})", f"subir {a.pesos} → /", f"subir {a.onnx} → /onnx",
            f"subir {a.ficha} → /README.md con cabecera YAML"]
    print("\n".join(plan))
    if not a.confirmar:
        print("\n(sin --confirmar: no se sube nada)")
        return
    from huggingface_hub import HfApi
    api = HfApi()
    api.create_repo(a.repo, private=not a.publico, exist_ok=True)
    api.upload_folder(repo_id=a.repo, folder_path=a.pesos, path_in_repo=".", commit_message="Pesos v0.1")
    api.upload_folder(repo_id=a.repo, folder_path=a.onnx, path_in_repo="onnx", commit_message="ONNX v0.1")
    readme = CABECERA + Path(a.ficha).read_text(encoding="utf-8")
    api.upload_file(path_or_fileobj=readme.encode("utf-8"), path_in_repo="README.md", repo_id=a.repo, commit_message="Ficha v0.1")
    print("publicado")


if __name__ == "__main__":
    main()
```

`README.md` del repositorio: qué es, instalación (`uv sync` o `pip install enrel` cuando exista), uso en tres líneas (`enrel extraer articulo.txt --onnx ruta`), la tabla de resultados resumida con enlace a la ficha, licencias de los componentes (MrBERT-es Apache-2.0; datos no publicados), cómo reproducir, cómo contribuir, y crédito a La Silla Vacía.

`docs/resultados/v0.1.md`: la tabla final definitiva y los enlaces a todos los informes de la etapa 3.

- [ ] **Paso 2: Verificar y confirmar con el usuario**

```bash
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run python scripts/publicar_hf.py --repo <org>/enrel-base-es --pesos corridas/<candidato>/mejor --onnx datos/onnx/v0.1-<decision>
```

Mostrar al usuario el plan de publicación impreso y la ficha, y **esperar su confirmación explícita** del nombre del repositorio y de si es público. Solo entonces añadir `--confirmar`.

- [ ] **Paso 3: Publicar y etiquetar**

```bash
uv run python scripts/publicar_hf.py --repo <org>/enrel-base-es --pesos … --onnx … --confirmar [--publico]
git add README.md docs/ficha-modelo.md docs/resultados/v0.1.md scripts/publicar_hf.py pyproject.toml enrel/__init__.py
git commit -m "Publica enrel v0.1: ficha de modelo, README y subida a Hugging Face"
git tag -a v0.1.0 -m "enrel v0.1.0"
git push origin main --tags
```

---

## Autorrevisión del plan de la etapa 3

**Cobertura de la spec.** §7 etapa 2 con oro y ancla → 3.1. §4.6 exportación ONNX, int8 con tolerancia y fp16 de respaldo, medición a 4 hilos con metas → 3.2, 3.4, 3.5. §4.5 exportador FollowTheMoney con `sourceUrl`, `proof`/evidencia, `retrievedAt` → 3.6. §8 revisión de 50 falsos positivos → 3.7. §9 entregables (repo, pesos en HF en PyTorch y ONNX, ficha en español, datos no publicados, CLI) → 3.3 (`--onnx` en el CLI), 3.8. §10 etapa 3 (backbone alternativo, cifras con intervalos, rendimiento dentro de meta, repo y pesos públicos) → 3.1, 3.5, 3.8. §11 riesgos: VRAM (3.1 barrido), int8 que degrada (3.4), cruces de párrafos (3.7).

**Tipos y firmas.** `exportar_modelo` produce los tres grafos con los nombres de entrada y salida que `PipelineONNX` (3.3) usa literalmente. `CabezaRelaciones.forward_exportable` devuelve `(logits, atencion, logits_vigencia)` y así lo consume `_Relaciones`. `mascara_tipos` pasa a `enrel/esquema/mascaras.py` en numpy y `modelo/enrel.py` la envuelve; 2.7 y 2.10 siguen recibiendo tensores. `PipelineONNX.extraer(texto, meta)` tiene la misma firma que `Pipeline.extraer`, y `medir` y `comparar_precisiones` la usan.

**Placeholders.** Los `<candidato>`, `<decision>` y `<org>` son valores que se conocen al ejecutar (la corrida elegida, la precisión decidida por la tolerancia, la cuenta de Hugging Face que el usuario confirme); cada uno dice de qué informe o decisión sale.
