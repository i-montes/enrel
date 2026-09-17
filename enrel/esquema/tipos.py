"""El esquema de enrel: siete tipos de entidad, diecisiete relaciones y una de reserva.

Fuente: docs/superpowers/specs/2026-09-16-enrel-diseno.md §3. Las definiciones en prosa
viven en docs/guia-anotacion.md; aquí solo la estructura que el código necesita.
"""

from dataclasses import dataclass

TIPOS: tuple[str, ...] = ("persona", "organizacion", "lugar", "cargo", "norma", "obra", "monto")
P, O, L, C, N, B, M = TIPOS  # noqa: E741 — nombres de una letra exigidos por la interfaz del esquema


@dataclass(frozen=True)
class DefRelacion:
    nombre: str
    desde: frozenset[str]
    hasta: frozenset[str]
    simetrica: bool
    atributos: tuple[str, ...]
    familia: str


def _r(nombre, desde, hasta, simetrica=False, atributos=(), familia=""):
    return DefRelacion(nombre, frozenset(desde), frozenset(hasta), simetrica, tuple(atributos), familia)


_LISTA = [
    _r("ocupa_cargo", [P], [C], atributos=("actual", "anterior", "aspirante"), familia="A"),
    _r("nombro_a", [P, O], [P], familia="A"),
    _r("sucedio_a", [P], [P], familia="A"),
    _r("trabaja_en", [P], [O], familia="A"),
    _r("dirige", [P], [O], familia="A"),
    _r("miembro_de", [P], [O], familia="A"),
    _r("fundo", [P, O], [O], familia="B"),
    _r("propietario_de", [P, O], [O], familia="B"),
    _r("socio_de", [P], [P], simetrica=True, familia="B"),
    _r("parte_de", [O], [O], familia="B"),
    _r("contrato_a", [O, P], [O, P], familia="B"),
    _r("financia_a", [P, O], [P, O], familia="B"),
    _r("familiar_de", [P], [P], simetrica=True, atributos=("conyuge", "hijo_de", "hermano", "otro"), familia="C"),
    _r("apoya_a", [P, O], [P, O, C], familia="C"),
    _r("se_opone_a", [P, O], [P, O], familia="C"),
    _r("investigado_por", [P, O], [O], atributos=("investigado", "acusado", "condenado"), familia="C"),
    _r("ubicado_en", [P, O, L], [L], familia="C"),
]
RELACIONES: dict[str, DefRelacion] = {d.nombre: d for d in _LISTA}
assert len(RELACIONES) == 17

SIN_TIPO = "vinculo_sin_tipo"
RELACIONES_Y_SIN_TIPO: tuple[str, ...] = tuple(RELACIONES) + (SIN_TIPO,)

FAMILIAS: dict[str, tuple[str, ...]] = {
    fam: tuple(d.nombre for d in _LISTA if d.familia == fam) for fam in ("A", "B", "C")
}


def clase_fina(relacion: str, atributo: str | None) -> str:
    """«relacion:atributo» si la relación tiene atributos; «relacion» si no."""
    if relacion == SIN_TIPO or not RELACIONES[relacion].atributos:
        return relacion
    if atributo not in RELACIONES[relacion].atributos:
        raise ValueError(f"{relacion} exige un atributo de {RELACIONES[relacion].atributos}, no {atributo!r}")
    return f"{relacion}:{atributo}"


def desglosar(clase: str) -> tuple[str, str | None]:
    relacion, sep, atributo = clase.partition(":")
    return relacion, (atributo if sep else None)


CLASES_FINAS: tuple[str, ...] = tuple(clase_fina(d.nombre, a) for d in _LISTA for a in (d.atributos or (None,))) + (
    SIN_TIPO,
)
assert len(CLASES_FINAS) == 25
INDICE_CLASE: dict[str, int] = {c: i for i, c in enumerate(CLASES_FINAS)}


def admite(relacion: str, tipo_cabeza: str, tipo_cola: str) -> bool:
    if relacion == SIN_TIPO:
        return tipo_cabeza in TIPOS and tipo_cola in TIPOS
    d = RELACIONES[relacion]
    return tipo_cabeza in d.desde and tipo_cola in d.hasta


def relaciones_admitidas(tipo_cabeza: str, tipo_cola: str) -> list[str]:
    return [r for r in RELACIONES_Y_SIN_TIPO if admite(r, tipo_cabeza, tipo_cola)]


def es_simetrica(relacion: str, atributo: str | None) -> bool:
    if relacion == SIN_TIPO:
        return True
    if relacion == "familiar_de":
        return atributo != "hijo_de"
    return RELACIONES[relacion].simetrica
