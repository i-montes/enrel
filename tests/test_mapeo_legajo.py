import pytest

from enrel.esquema.mapeo_legajo import Mapeo, mapear_predicado, mapear_tipo
from enrel.esquema.tipos import SIN_TIPO


def test_mapear_tipo():
    assert mapear_tipo("ley") == ("norma", False)
    assert mapear_tipo("cargo*") == ("cargo", True)
    assert mapear_tipo("persona") == ("persona", False)
    with pytest.raises(ValueError):
        mapear_tipo("evento")


@pytest.mark.parametrize(
    "pred,ta,tb,cuando,esperado",
    [
        ("ocupa el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "actual", False)),
        ("ocupa el cargo", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", "anterior", False)),
        ("ocupa el cargo", "persona", "cargo", "futura", Mapeo("ocupa_cargo", "aspirante", False)),
        ("aspira a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False)),
        ("renunció a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "anterior", False)),
        ("renunció a", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("padre o madre de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", True)),
        ("hijo de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", False)),
        ("cónyuge o pareja de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False)),
        ("parte de", "persona", "organizacion", "vigente", Mapeo("miembro_de", None, False)),
        ("parte de", "organizacion", "organizacion", "vigente", Mapeo("parte_de", None, False)),
        ("parte de", "persona", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("asesor de", "persona", "persona", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("socio de", "persona", "organizacion", "vigente", Mapeo("propietario_de", None, False)),
        ("socio de", "persona", "persona", "vigente", Mapeo("socio_de", None, False)),
        ("aliado de", "organizacion", "organizacion", "vigente", Mapeo("apoya_a", None, False)),
        ("criticó a", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("acusado de", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("condenado por", "persona", "organizacion", "vigente", Mapeo("investigado_por", "condenado", False)),
        ("ubicado en", "monto", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("citado en", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
        # vocabulario nuevo de legajo
        ("ocupó el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "anterior", False)),
        ("aspira al cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False)),
        ("cónyuge de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False)),
        ("propietario de", "organizacion", "organizacion", "vigente", Mapeo("propietario_de", None, False)),
        ("acusado por", "organizacion", "organizacion", "vigente", Mapeo("investigado_por", "acusado", False)),
        ("se opone a", "persona", "organizacion", "vigente", Mapeo("se_opone_a", None, False)),
        ("vínculo sin tipo", "monto", "obra", "vigente", Mapeo(SIN_TIPO, None, False)),
    ],
)
def test_mapear_predicado(pred, ta, tb, cuando, esperado):
    assert mapear_predicado(pred, ta, tb, cuando) == esperado


def test_predicado_desconocido():
    with pytest.raises(ValueError):
        mapear_predicado("es amigo de", "persona", "persona")
