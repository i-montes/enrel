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
        # ocupa_cargo ya no tiene atributo: la distinción actual/anterior/aspirante vive en `vigencia`.
        ("ocupa el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", None, False, "vigente")),
        ("ocupa el cargo", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", None, False, "pasada")),
        ("ocupa el cargo", "persona", "cargo", "futura", Mapeo("ocupa_cargo", None, False, "futura")),
        # «aspira a» y «renunció a» ya llevan el tiempo en el nombre: su vigencia es fija y
        # gana sobre `cuando`, aunque llegue otra cosa.
        ("aspira a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", None, False, "futura")),
        ("aspira a", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", None, False, "futura")),
        ("renunció a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", None, False, "pasada")),
        ("renunció a", "persona", "cargo", "futura", Mapeo("ocupa_cargo", None, False, "pasada")),
        # incluso mapeando a SIN_TIPO (aquí, sin cargo como objeto) la vigencia forzada se aplica.
        ("renunció a", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False, "pasada")),
        ("padre o madre de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", True, "vigente")),
        ("hijo de", "persona", "persona", "vigente", Mapeo("familiar_de", "hijo_de", False, "vigente")),
        ("cónyuge o pareja de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False, "vigente")),
        ("parte de", "persona", "organizacion", "vigente", Mapeo("miembro_de", None, False, "vigente")),
        ("parte de", "organizacion", "organizacion", "vigente", Mapeo("parte_de", None, False, "vigente")),
        ("parte de", "persona", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("asesor de", "persona", "persona", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("socio de", "persona", "organizacion", "vigente", Mapeo("propietario_de", None, False, "vigente")),
        ("socio de", "persona", "persona", "vigente", Mapeo("socio_de", None, False, "vigente")),
        ("aliado de", "organizacion", "organizacion", "vigente", Mapeo("apoya_a", None, False, "vigente")),
        ("criticó a", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("acusado de", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
        (
            "condenado por",
            "persona",
            "organizacion",
            "vigente",
            Mapeo("investigado_por", "condenado", False, "vigente"),
        ),
        ("ubicado en", "monto", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("citado en", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
        # vocabulario nuevo de legajo
        ("ocupó el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", None, False, "pasada")),
        ("aspira al cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", None, False, "futura")),
        ("cónyuge de", "persona", "persona", "vigente", Mapeo("familiar_de", "conyuge", False, "vigente")),
        ("propietario de", "organizacion", "organizacion", "vigente", Mapeo("propietario_de", None, False, "vigente")),
        (
            "acusado por",
            "organizacion",
            "organizacion",
            "vigente",
            Mapeo("investigado_por", "acusado", False, "vigente"),
        ),
        ("se opone a", "persona", "organizacion", "vigente", Mapeo("se_opone_a", None, False, "vigente")),
        ("vínculo sin tipo", "monto", "obra", "vigente", Mapeo(SIN_TIPO, None, False)),
        # `cuando` se propaga tal cual en relaciones que no son de cargo.
        ("trabaja en", "persona", "organizacion", "pasada", Mapeo("trabaja_en", None, False, "pasada")),
        ("miembro de", "persona", "organizacion", "pasada", Mapeo("miembro_de", None, False, "pasada")),
        ("dirige", "persona", "organizacion", "futura", Mapeo("dirige", None, False, "futura")),
    ],
)
def test_mapear_predicado(pred, ta, tb, cuando, esperado):
    assert mapear_predicado(pred, ta, tb, cuando) == esperado


def test_predicado_desconocido():
    with pytest.raises(ValueError):
        mapear_predicado("es amigo de", "persona", "persona")
