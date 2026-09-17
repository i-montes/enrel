from enrel.datos.documento import Documento, Grupo, Mencion, Relacion
from enrel.evaluacion.relaciones import evaluar_relaciones, tripletas_canonicas


def doc(doc_id, menciones, grupos, relaciones):
    return Documento(doc_id, "x" * 300, menciones, grupos, relaciones)


ORO = doc(
    "d",
    [
        Mencion("a", 0, 13, "Gustavo Petro", "persona", "g1"),
        Mencion("b", 20, 37, "Luis Carlos Reyes", "persona", "g2"),
        Mencion("c", 40, 60, "ministro de Comercio", "cargo", "g3"),
        Mencion("d", 70, 78, "Colombia", "lugar", "g4"),
    ],
    [
        Grupo("g1", "persona", "Gustavo Petro"),
        Grupo("g2", "persona", "Luis Carlos Reyes"),
        Grupo("g3", "cargo", "ministro de Comercio"),
        Grupo("g4", "lugar", "Colombia"),
    ],
    [Relacion("g1", "g2", "nombro_a"), Relacion("g2", "g3", "ocupa_cargo", "actual"), Relacion("g1", "g2", "socio_de")],
)


def pred(relaciones, menciones=None):
    ms = menciones or [
        Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"),
        Mencion("y", 20, 37, "Luis Carlos Reyes", "persona", "p2"),
        Mencion("z", 40, 60, "ministro de Comercio", "cargo", "p3"),
    ]
    gs = {m.grupo: Grupo(m.grupo, m.tipo, m.texto) for m in ms}
    return doc("d", ms, list(gs.values()), relaciones)


def test_acierto_direccion_y_simetrica():
    p = pred(
        [
            Relacion("p1", "p2", "nombro_a"),
            Relacion("p2", "p3", "ocupa_cargo", "anterior"),
            Relacion("p2", "p1", "socio_de"),
        ]
    )
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
    ms = [
        Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"),
        Mencion("y", 20, 37, "Luis Carlos Reyes", "organizacion", "p2"),
    ]
    p = pred([Relacion("p1", "p2", "nombro_a")], ms)
    assert (
        evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=False)["nombro_a"].tp == 0
    )  # tipo distinto: no hay grupo emparejado
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=True)["nombro_a"].tp == 0


def test_re_mas_difiere_de_re_con_tipo_de_grupo_erroneo():
    # aquí sí hay grupo emparejado (la mención solapada tiene el tipo correcto), pero el
    # grupo predicho quedó etiquetado con un tipo distinto al del oro: RE acierta, RE+ no.
    ms = [
        Mencion("x", 0, 13, "Gustavo Petro", "persona", "p1"),
        Mencion("y", 20, 37, "Luis Carlos Reyes", "persona", "p2"),
    ]
    gs = [Grupo("p1", "persona", "Gustavo Petro"), Grupo("p2", "organizacion", "Luis Carlos Reyes")]
    p = doc("d", ms, gs, [Relacion("p1", "p2", "nombro_a")])
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=False)["nombro_a"].tp == 1
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=True)["nombro_a"].tp == 0


def test_macro_y_sin_tipo_excluido():
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p1", "p3", "vinculo_sin_tipo")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert r["__micro__"].fp == 0  # vinculo_sin_tipo no cuenta en micro
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
