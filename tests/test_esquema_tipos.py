from enrel.esquema import tipos as t


def test_tipos_y_constantes():
    assert t.TIPOS == ("persona", "organizacion", "lugar", "cargo", "norma", "obra", "monto")
    assert (t.P, t.O, t.L, t.C, t.N, t.B, t.M) == t.TIPOS


def test_hay_18_relaciones_y_25_clases_finas():
    assert len(t.RELACIONES) == 18
    assert t.SIN_TIPO not in t.RELACIONES
    assert len(t.CLASES_FINAS) == 25
    assert t.CLASES_FINAS[-1] == t.SIN_TIPO
    assert t.INDICE_CLASE[t.SIN_TIPO] == 24


def test_clase_fina_y_desglosar():
    assert t.clase_fina("ocupa_cargo", "titular") == "ocupa_cargo:titular"
    assert t.clase_fina("ocupa_cargo", "aspirante") == "ocupa_cargo:aspirante"
    assert t.clase_fina("familiar_de", "hijo_de") == "familiar_de:hijo_de"
    assert t.clase_fina("dirige", None) == "dirige"
    assert t.desglosar("familiar_de:hijo_de") == ("familiar_de", "hijo_de")
    assert t.desglosar("trabaja_en") == ("trabaja_en", None)
    assert t.desglosar(t.SIN_TIPO) == (t.SIN_TIPO, None)


def test_atributos():
    # `ocupa_cargo` tiene un atributo de modalidad (titular/aspirante), ortogonal a la vigencia:
    # ese eje (`vigencia`) es propio de toda relación (véase test_datos_documento.py).
    assert t.RELACIONES["ocupa_cargo"].atributos == ("titular", "aspirante")
    assert t.RELACIONES["familiar_de"].atributos == ("conyuge", "hijo_de", "hermano", "otro")
    assert t.RELACIONES["investigado_por"].atributos == ("investigado", "acusado", "condenado")
    assert t.RELACIONES["trabaja_en"].atributos == ()


def test_vigencias_y_defecto():
    assert t.VIGENCIAS == ("vigente", "pasada", "futura")
    assert t.VIGENCIA_POR_DEFECTO == "vigente"


def test_es_suceso():
    assert t.es_suceso("nombro_a")
    assert t.es_suceso("sucedio_a")
    assert t.es_suceso("fundo")
    assert t.es_suceso("contrato_a")
    assert t.es_suceso("financia_a")
    assert t.es_suceso("impulsa_norma")
    assert not t.es_suceso("ocupa_cargo")
    assert not t.es_suceso("dirige")
    assert not t.es_suceso(t.SIN_TIPO)


def test_admite():
    assert t.admite("ocupa_cargo", "persona", "cargo")
    assert not t.admite("ocupa_cargo", "persona", "organizacion")
    assert t.admite("parte_de", "organizacion", "organizacion")
    assert not t.admite("parte_de", "persona", "organizacion")
    assert t.admite("ubicado_en", "lugar", "lugar")
    assert not t.admite("ubicado_en", "monto", "lugar")
    assert t.admite("apoya_a", "organizacion", "cargo")
    assert t.admite("apoya_a", "persona", "norma")
    assert t.admite("se_opone_a", "organizacion", "norma")
    assert not t.admite("investigado_por", "persona", "norma")
    assert t.admite(t.SIN_TIPO, "monto", "obra")
    # impulsa_norma: acto legislativo (radicar, redactar, ser ponente, sacar adelante,
    # sancionar, aprobar) de persona u organización sobre una norma; direccional, no al revés.
    assert t.admite("impulsa_norma", "persona", "norma")
    assert t.admite("impulsa_norma", "organizacion", "norma")
    assert not t.admite("impulsa_norma", "persona", "cargo")
    assert not t.admite("impulsa_norma", "norma", "persona")


def test_relaciones_admitidas_persona_persona():
    assert set(t.relaciones_admitidas("persona", "persona")) == {
        "nombro_a",
        "sucedio_a",
        "socio_de",
        "familiar_de",
        "financia_a",
        "contrato_a",
        "apoya_a",
        "se_opone_a",
        t.SIN_TIPO,
    }


def test_simetria():
    assert t.es_simetrica("familiar_de", "conyuge")
    assert not t.es_simetrica("familiar_de", "hijo_de")
    assert t.es_simetrica("socio_de", None)
    assert not t.es_simetrica("dirige", None)
    assert t.es_simetrica(t.SIN_TIPO, None)


def test_familias_cubren_todo_sin_repetir():
    todas = [r for fam in t.FAMILIAS.values() for r in fam]
    assert sorted(todas) == sorted(t.RELACIONES)
    assert t.FAMILIAS["A"] == ("ocupa_cargo", "nombro_a", "sucedio_a", "trabaja_en", "dirige", "miembro_de")
