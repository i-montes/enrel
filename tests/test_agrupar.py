from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Mencion


def m(i, texto, tipo):
    return Mencion(f"m{i}", i * 100, i * 100 + len(texto), texto, tipo, "")


def test_misma_cadena_plegada():
    ms = [m(1, "Fiscalía", "organizacion"), m(2, "fiscalia", "organizacion"), m(3, "Fiscalía", "cargo")]
    gs = agrupar(ms)
    assert ms[0].grupo == ms[1].grupo != ms[2].grupo
    assert len(gs) == 2


def test_persona_forma_corta_en_orden_y_apellido():
    ms = [
        m(1, "Carlos Fernando Galán", "persona"),
        m(2, "Carlos Galán", "persona"),
        m(3, "Galán", "persona"),
        m(4, "Luis Carlos Galán", "persona"),
    ]
    agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    # «Galán» es apellido de dos personas distintas: no se une a ninguna
    assert ms[2].grupo not in (ms[0].grupo, ms[3].grupo)
    assert ms[3].grupo != ms[0].grupo


def test_persona_apellido_unico():
    ms = [m(1, "Gustavo Petro", "persona"), m(2, "Petro", "persona"), m(3, "Francia Márquez", "persona")]
    gs = agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    assert gs[0].canonico == "Gustavo Petro"


def test_organizacion_sigla_y_forma_corta():
    ms = [
        m(1, "Empresas Públicas de Medellín", "organizacion"),
        m(2, "EPM", "organizacion"),
        m(3, "Universidad Nacional de Colombia", "organizacion"),
        m(4, "Universidad Nacional", "organizacion"),
    ]
    agrupar(ms)
    assert ms[0].grupo == ms[1].grupo
    assert ms[2].grupo == ms[3].grupo
    assert ms[0].grupo != ms[2].grupo


def test_organizacion_sigla_ambigua_no_se_une():
    # «EPM» es sigla tanto de «Empresas Públicas de Medellín» como de «Escuela Popular de
    # Música»: dos candidatas, ambigüedad real, no se une a ninguna.
    ms = [
        m(1, "Empresas Públicas de Medellín", "organizacion"),
        m(2, "Escuela Popular de Música", "organizacion"),
        m(3, "EPM", "organizacion"),
    ]
    agrupar(ms)
    assert ms[2].grupo not in (ms[0].grupo, ms[1].grupo)
    assert ms[0].grupo != ms[1].grupo


def test_organizacion_forma_corta_ambigua_no_encadena():
    # «Cámara» es secuencia contenida tanto de «Comisión III Cámara» como de «Comisión IV
    # Cámara»: no se une a ninguna, y las dos comisiones (mismo número de palabras entre sí)
    # tampoco se unen entre ellas.
    ms = [
        m(1, "Cámara", "organizacion"),
        m(2, "Comisión III Cámara", "organizacion"),
        m(3, "Comisión IV Cámara", "organizacion"),
    ]
    agrupar(ms)
    assert ms[0].grupo not in (ms[1].grupo, ms[2].grupo)
    assert ms[1].grupo != ms[2].grupo


def test_cargos_solo_por_cadena():
    ms = [m(1, "ministro de Hacienda", "cargo"), m(2, "ministro", "cargo")]
    agrupar(ms)
    assert ms[0].grupo != ms[1].grupo


def test_alias():
    ms = [m(1, "Juan Manuel Santos", "persona"), m(2, "Santos Calderón", "persona")]
    agrupar(ms, alias={"santos calderon": "juan manuel santos", "juan manuel santos": "juan manuel santos"})
    assert ms[0].grupo == ms[1].grupo
