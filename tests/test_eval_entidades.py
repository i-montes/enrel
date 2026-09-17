import pytest

from enrel.datos.documento import Documento, Grupo, Mencion
from enrel.evaluacion.emparejar import PRF, alinear, emparejar_grupos, emparejar_menciones
from enrel.evaluacion.entidades import evaluar_entidades


def doc(doc_id, menciones):
    grupos = {m.grupo: Grupo(m.grupo, m.tipo, m.texto) for m in menciones}
    return Documento(doc_id, "x" * 200, list(menciones), list(grupos.values()), [])


def test_prf():
    p = PRF(tp=3, fp=1, fn=1)
    assert (round(p.p, 2), round(p.r, 2), round(p.f1, 2), p.n) == (0.75, 0.75, 0.75, 4)
    assert PRF().f1 == 0.0


def test_estricto_vs_parcial():
    oro = [
        Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"),
        Mencion("b", 20, 28, "Fiscalía", "organizacion", "g2"),
    ]
    pred = [
        Mencion("x", 8, 13, "Petro", "persona", "p1"),
        Mencion("y", 20, 28, "Fiscalía", "organizacion", "p2"),
        Mencion("z", 40, 44, "Cali", "lugar", "p3"),
    ]
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
    oro = doc(
        "d",
        [
            Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"),
            Mencion("b", 50, 55, "Petro", "persona", "g1"),
            Mencion("c", 20, 28, "Fiscalía", "organizacion", "g2"),
        ],
    )
    pred = doc(
        "d",
        [
            Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"),
            Mencion("y", 50, 55, "Petro", "persona", "p9"),
            Mencion("z", 20, 28, "Fiscalía", "organizacion", "p2"),
        ],
    )
    m = emparejar_grupos(oro, pred)
    assert m["g1"] in ("p1", "p9") and m["g2"] == "p2"


def test_alinear_avisa_de_documentos_de_mas():
    oro = [doc("d1", [Mencion("a", 0, 5, "Cali", "lugar", "g1")])]
    pred = [
        doc("d1", [Mencion("x", 0, 5, "Cali", "lugar", "p1")]),
        doc("d2", [Mencion("y", 0, 5, "Cali", "lugar", "p1")]),
    ]
    with pytest.warns(UserWarning, match="d2"):
        pares = alinear(oro, pred)
    assert [o.doc_id for o, _ in pares] == ["d1"]
