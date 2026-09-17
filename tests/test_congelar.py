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
    filas = [json.loads(linea) for linea in salida.read_text(encoding="utf-8").splitlines()]
    assert resumen["total"] == 1 and len(filas) == 1
    assert filas[0]["doc_id"] == "wp:10" and filas[0]["seccion"] == "silla-nacional"
    assert filas[0]["texto"].startswith("Petro & Cía\n\n")
    assert resumen["excluidos"]["pocas_palabras"] == 1
    assert (tmp_path / "articulos.resumen.json").exists()
