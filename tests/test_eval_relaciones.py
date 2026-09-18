from enrel.datos.documento import Documento, Grupo, Mencion, Relacion
from enrel.datos.validar import validar_documento
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
    [
        Relacion("g1", "g2", "nombro_a"),
        Relacion("g2", "g3", "ocupa_cargo", vigencia="vigente"),
        Relacion("g1", "g2", "socio_de"),
    ],
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
            Relacion("p2", "p3", "ocupa_cargo", vigencia="pasada"),
            Relacion("p2", "p1", "socio_de"),
        ]
    )
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert (r["__micro__"].tp, r["__micro__"].fp, r["__micro__"].fn) == (3, 0, 0)
    fina = evaluar_relaciones([ORO], [p], "fina")
    # ocupa_cargo ya no tiene atributo: una vigencia distinta (aquí, «pasada» contra «vigente»
    # en el oro) no crea clases finas cruzadas ni cuenta como error de RE+ fina.
    assert fina["ocupa_cargo"].tp == 1
    assert "ocupa_cargo:actual" not in fina and "ocupa_cargo:anterior" not in fina
    assert fina["__micro__"].tp == 3


def test_vigencia_es_eje_aparte_de_re():
    # Mismo caso que arriba: la vigencia no entra en la condición de acierto de RE/RE+/fina,
    # pero se reporta aparte en __vigencia__. De las 3 relaciones acertadas en par y etiqueta,
    # 2 aciertan también la vigencia (nombro_a y socio_de, «vigente» por defecto en ambos
    # lados) y 1 no (ocupa_cargo: «vigente» en el oro, «pasada» en la predicción).
    p = pred(
        [
            Relacion("p1", "p2", "nombro_a"),
            Relacion("p2", "p3", "ocupa_cargo", vigencia="pasada"),
            Relacion("p2", "p1", "socio_de"),
        ]
    )
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert (r["__vigencia__"].tp, r["__vigencia__"].fn, r["__vigencia__"].fp) == (2, 1, 0)
    assert r["__vigencia__"].r == 2 / 3


def test_direccion_invertida_cuenta_como_error_y_en_direccion():
    p = pred([Relacion("p2", "p1", "nombro_a")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert r["nombro_a"].tp == 0 and r["nombro_a"].fp == 1 and r["nombro_a"].fn == 1
    assert r["__direccion__"].fn == 1 and r["__direccion__"].tp == 0


def test_re_mas_exige_tipos():
    # la predicción empareja bien el par por solape (mismos extremos que el oro), pero da
    # al primer extremo un tipo distinto del que tiene en el oro («persona» en el oro,
    # «organizacion» en la predicción); `nombro_a` admite organizacion→persona, así que el
    # documento es válido. RE acierta (empareja y la relación es correcta), RE+ no (los
    # tipos de los grupos no coinciden con los del oro).
    ms = [
        Mencion("x", 0, 13, "Gustavo Petro", "organizacion", "p1"),
        Mencion("y", 20, 37, "Luis Carlos Reyes", "persona", "p2"),
    ]
    gs = [Grupo("p1", "organizacion", "Gustavo Petro"), Grupo("p2", "persona", "Luis Carlos Reyes")]
    texto = "Gustavo Petro" + " " * 7 + "Luis Carlos Reyes" + "x" * 263
    p = Documento("d", texto, ms, gs, [Relacion("p1", "p2", "nombro_a")])
    assert validar_documento(p) == []
    assert evaluar_relaciones([ORO], [p], "gruesa", exigir_tipos=False)["nombro_a"].tp == 1
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


def test_macro_excluye_sin_tipo_pero_micro_lo_incluye():
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p1", "p3", "vinculo_sin_tipo")])
    r = evaluar_relaciones([ORO], [p], "gruesa")
    assert "vinculo_sin_tipo" in r and r["vinculo_sin_tipo"].fp == 1
    # `vinculo_sin_tipo` es la reserva (clase 18), no «sin relación»: micro la cuenta ahora,
    # así que su falso positivo entra en `__micro__` pero no en `__micro_sin_reserva__`.
    assert r["__micro__"].fp == 1
    assert r["__micro_sin_reserva__"].fp == 0
    assert 0 < r["__macro__"].f1 < 1  # macro sigue excluyendo la reserva


def test_ign():
    ignorar = tripletas_canonicas([ORO], "gruesa") - {("gustavo petro", "nombro_a", "luis carlos reyes")}
    p = pred([Relacion("p1", "p2", "nombro_a"), Relacion("p2", "p3", "ocupa_cargo")])
    r = evaluar_relaciones([ORO], [p], "gruesa", ignorar=ignorar)
    assert (r["__micro__"].tp, r["__micro__"].fp, r["__micro__"].fn) == (1, 0, 0)


def test_tripletas_canonicas_simetrica_ordenada():
    t = tripletas_canonicas([ORO], "gruesa")
    assert ("gustavo petro", "socio_de", "luis carlos reyes") in t
