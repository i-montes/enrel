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
            f.write(
                json.dumps(
                    {
                        "doc_id": f"wp:{i}",
                        "wp_id": i,
                        "seccion": secciones[i % 4],
                        "fecha": f"{2009 + (i % 17)}-01-01",
                        "titulo": f"T{i}",
                        "texto": f"T{i}\n\n" + frases[i % 4] + " " * 200,
                        "palabras": 300,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return ruta


def test_muestrear_estratos_y_exclusion(tmp_path):
    corpus = _corpus(tmp_path)
    sel = mu.muestrear(
        corpus, excluir={"wp:0", "wp:1"}, semilla=1, cuota_relacion=5, perfiles=20, aleatorios=40, humo=3
    )
    ids = [s.doc_id for s in sel]
    assert len(ids) == len(set(ids))
    assert "wp:0" not in ids and "wp:1" not in ids
    estratos = {s.estrato for s in sel}
    assert estratos == {"dirigido", "perfiles", "aleatorio"}
    assert sum(1 for s in sel if s.conjunto == "humo_maestro") == 3
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
