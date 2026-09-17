"""Congela el archivo en un JSONL con filtros, para que todo el proyecto lea lo mismo."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from enrel.corpus.legajo_db import es_transcripcion, iterar_articulos

_CLAVES_EXCLUIDOS = ("pocas_palabras", "muchas_palabras", "transcripcion", "sin_texto")


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
            fila = {
                "doc_id": f"wp:{a.wp_id}",
                "wp_id": a.wp_id,
                "url": a.url,
                "fecha": a.fecha,
                "seccion": a.seccion,
                "titulo": a.titulo,
                "texto": a.texto,
                "palabras": a.palabras,
                "hash": hashlib.sha256(a.texto.encode("utf-8")).hexdigest()[:16],
            }
            linea = json.dumps(fila, ensure_ascii=False) + "\n"
            f.write(linea)
            h.update(linea.encode("utf-8"))
            total += 1
            por_seccion[a.seccion or "(sin sección)"] += 1
            por_tramo[tramo_de(a.fecha)] += 1
    resumen = {
        "total": total,
        "excluidos": {k: excluidos.get(k, 0) for k in _CLAVES_EXCLUIDOS},
        "por_seccion": dict(por_seccion.most_common()),
        "por_tramo": dict(por_tramo),
        "hash": h.hexdigest(),
        "parametros": {"minimo_palabras": minimo_palabras, "maximo_palabras": maximo_palabras},
    }
    salida.with_suffix(".resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return resumen
