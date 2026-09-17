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
    return (
        tok,
        modelo,
        {
            "modelo": nombre,
            "parametros": params,
            "vocabulario": len(tok),
            "max_posiciones": getattr(modelo.config, "max_position_embeddings", None),
        },
    )


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
    return {
        "tokens_por_palabra": round(statistics.mean(razones), 2),
        "p50_tokens": int(np.percentile(longitudes, 50)),
        "p95_tokens": int(np.percentile(longitudes, 95)),
        "max_tokens": max(longitudes),
        "articulos": len(textos),
    }


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
    r = {
        "gpu": torch.cuda.get_device_name(0),
        "tokens": tokens,
        "lote": lote,
        "vram_pico_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "segundos_paso": round(time.time() - t0, 2),
    }
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


def exportar_onnx(modelo, tok, ruta: Path, texto: str, nombre: str):
    modelo.eval()
    ids = tok(texto, return_tensors="pt")
    try:
        torch.onnx.export(
            _Envoltura(modelo),
            (ids["input_ids"], ids["attention_mask"]),
            str(ruta),
            input_names=["input_ids", "attention_mask"],
            output_names=["ultimo_estado"],
            dynamic_axes={
                "input_ids": {0: "lote", 1: "secuencia"},
                "attention_mask": {0: "lote", 1: "secuencia"},
                "ultimo_estado": {0: "lote", 1: "secuencia"},
            },
            opset_version=17,
        )
        arreglo_atencion = False
    except Exception:  # noqa: BLE001
        # ModernBERT exporta mal con sdpa/flash-attention; se reintenta con atención eager solo para exportar.
        modelo_eager = AutoModel.from_pretrained(nombre, attn_implementation="eager")
        modelo_eager.eval()
        torch.onnx.export(
            _Envoltura(modelo_eager),
            (ids["input_ids"], ids["attention_mask"]),
            str(ruta),
            input_names=["input_ids", "attention_mask"],
            output_names=["ultimo_estado"],
            dynamic_axes={
                "input_ids": {0: "lote", 1: "secuencia"},
                "attention_mask": {0: "lote", 1: "secuencia"},
                "ultimo_estado": {0: "lote", 1: "secuencia"},
            },
            opset_version=17,
        )
        arreglo_atencion = True
    import onnxruntime as ort

    sesion = ort.InferenceSession(str(ruta), providers=["CPUExecutionProvider"])
    salida_onnx = sesion.run(
        None, {"input_ids": ids["input_ids"].numpy(), "attention_mask": ids["attention_mask"].numpy()}
    )[0]
    with torch.no_grad():
        salida_torch = modelo(**ids).last_hidden_state.numpy()
    return {
        "onnx": str(ruta),
        "mb": round(ruta.stat().st_size / 2**20, 1),
        "diferencia_max": float(np.abs(salida_onnx - salida_torch).max()),
        "arreglo_atencion_eager": arreglo_atencion,
    }


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
    return {
        "fichero": ruta.name,
        "tokens": int(ids["input_ids"].shape[1]),
        "hilos": hilos,
        "mediana_s": round(statistics.median(tiempos), 3),
        "p95_s": round(np.percentile(tiempos, 95), 3),
        "rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2),
    }


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
    filas.append(("ONNX", exportar_onnx(modelo, tok, ruta, texto, nombre)))
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
    comando = (
        f"taskset -c 0-3 uv run python scripts/humo_backbone.py --modelo {a.modelo} --tokens {a.tokens} --lote {a.lote}"
    )
    partes = [f"# Humo del backbone\n\nFecha: {date.today().isoformat()} · comando: `{comando}`\n"]
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
            partes.append(
                "\nCriterio: carga sin errores; paso GPU con VRAM pico < 8 GB; "
                "diferencia torch-ONNX < 1e-3; mediana int8 < 3 s por ~1.500 tokens con 4 hilos. "
                "Si se cumple, el respaldo se mide solo como referencia.\n"
            )
    Path(a.salida).write_text("\n".join(partes), encoding="utf-8")
    print(Path(a.salida).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
