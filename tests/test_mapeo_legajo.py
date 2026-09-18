import pytest

from enrel.esquema.mapeo_legajo import Mapeo, mapear_predicado, mapear_tipo
from enrel.esquema.tipos import SIN_TIPO


def test_mapear_tipo():
    assert mapear_tipo("ley") == ("norma", False)
    assert mapear_tipo("cargo*") == ("cargo", True)
    assert mapear_tipo("persona") == ("persona", False)
    with pytest.raises(ValueError):
        mapear_tipo("evento")
    # `monto` y `obra` salieron del esquema de enrel (decisión del 2026-09-17): legajo sigue
    # anotándolos, pero para enrel son, igual que `evento`, un tipo sin equivalente.
    with pytest.raises(ValueError):
        mapear_tipo("monto")
    with pytest.raises(ValueError):
        mapear_tipo("obra")


@pytest.mark.parametrize(
    "pred,ta,tb,cuando,esperado",
    [
        # ocupa_cargo tiene un atributo de modalidad (titular/aspirante), ortogonal a la vigencia:
        # «ocupa el cargo» siempre es `titular`, con la vigencia de `cuando` tal cual (incluida
        # `futura`, que aquí es un nombramiento anunciado, no una candidatura).
        ("ocupa el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "titular", False, "vigente")),
        ("ocupa el cargo", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", "titular", False, "pasada")),
        ("ocupa el cargo", "persona", "cargo", "futura", Mapeo("ocupa_cargo", "titular", False, "futura")),
        # «ocupó el cargo» y «renunció a» ya llevan el tiempo en el nombre: su vigencia es fija,
        # siempre `titular` + `pasada`, y gana sobre `cuando`, aunque llegue otra cosa.
        ("renunció a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "titular", False, "pasada")),
        ("renunció a", "persona", "cargo", "futura", Mapeo("ocupa_cargo", "titular", False, "pasada")),
        # incluso mapeando a SIN_TIPO (aquí, sin cargo como objeto) la vigencia forzada se aplica.
        ("renunció a", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False, "pasada")),
        # «aspira a» y «aspira al cargo» son la modalidad `aspirante`, no un tiempo: la vigencia
        # es la de `cuando` tal cual, incluida una candidatura pasada (perdió, ya no es candidato).
        ("aspira a", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False, "vigente")),
        ("aspira a", "persona", "cargo", "pasada", Mapeo("ocupa_cargo", "aspirante", False, "pasada")),
        ("aspira a", "persona", "cargo", "futura", Mapeo("ocupa_cargo", "aspirante", False, "futura")),
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
        # apoya_a y se_opone_a admiten norma en la cola (postura de apoyo o crítica/hundimiento
        # de una ley, sin acto); impulsa_norma es el acto legislativo propio (radicar, redactar,
        # ser ponente, sacar adelante, sancionar, aprobar).
        ("criticó a", "persona", "norma", "vigente", Mapeo("se_opone_a", None, False, "vigente")),
        ("apoyó a", "persona", "norma", "vigente", Mapeo("apoya_a", None, False, "vigente")),
        ("impulsa", "persona", "norma", "vigente", Mapeo("impulsa_norma", None, False, "vigente")),
        ("impulsa", "organizacion", "norma", "pasada", Mapeo("impulsa_norma", None, False, "pasada")),
        # impulsa_norma no admite persona → cargo: cae en la reserva sin tipo.
        ("impulsa", "persona", "cargo", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("acusado de", "persona", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
        (
            "condenado por",
            "persona",
            "organizacion",
            "vigente",
            Mapeo("investigado_por", "condenado", False, "vigente"),
        ),
        ("ubicado en", "cargo", "lugar", "vigente", Mapeo(SIN_TIPO, None, False)),
        ("citado en", "persona", "organizacion", "vigente", Mapeo(SIN_TIPO, None, False)),
        # vocabulario nuevo de legajo
        ("ocupó el cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "titular", False, "pasada")),
        ("aspira al cargo", "persona", "cargo", "vigente", Mapeo("ocupa_cargo", "aspirante", False, "vigente")),
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
        ("vínculo sin tipo", "cargo", "norma", "vigente", Mapeo(SIN_TIPO, None, False)),
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
