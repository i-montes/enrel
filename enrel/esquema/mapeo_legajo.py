"""Traduce el vocabulario de legajo (los 35 predicados viejos y los 25 nuevos) al esquema de enrel."""

from dataclasses import dataclass

from enrel.esquema.tipos import SIN_TIPO, TIPOS, O, P, admite

_TIPOS_LEGAJO = {"ley": ("norma", False), "cargo*": ("cargo", True)}


def mapear_tipo(tipo_legajo: str) -> tuple[str, bool]:
    if tipo_legajo in _TIPOS_LEGAJO:
        return _TIPOS_LEGAJO[tipo_legajo]
    if tipo_legajo in TIPOS:
        return tipo_legajo, False
    raise ValueError(f"tipo de legajo desconocido: {tipo_legajo!r}")


@dataclass(frozen=True)
class Mapeo:
    relacion: str
    atributo: str | None
    invertir: bool


_CUANDO = {"vigente": "actual", "pasada": "anterior", "futura": "aspirante"}
_NADA = Mapeo(SIN_TIPO, None, False)

# Cada regla es (relacion, atributo, invertir) o una función (tipo_a, tipo_b, cuando) → esa tupla.
_REGLAS = {
    # viejos
    "ocupa el cargo": lambda ta, tb, c: ("ocupa_cargo", _CUANDO.get(c, "actual"), False),
    "aspira a": ("ocupa_cargo", "aspirante", False),
    "renunció a": (lambda ta, tb, c: ("ocupa_cargo", "anterior", False) if tb == "cargo" else (SIN_TIPO, None, False)),
    "nombró a": ("nombro_a", None, False),
    "sucedió a": ("sucedio_a", None, False),
    "trabaja en": ("trabaja_en", None, False),
    "asesor de": (lambda ta, tb, c: ("trabaja_en", None, False) if tb == O else (SIN_TIPO, None, False)),
    "dirige": ("dirige", None, False),
    "miembro de": ("miembro_de", None, False),
    "parte de": (
        lambda ta, tb, c: (
            ("miembro_de", None, False)
            if (ta, tb) == (P, O)
            else ("parte_de", None, False)
            if (ta, tb) == (O, O)
            else (SIN_TIPO, None, False)
        )
    ),
    "fundó": ("fundo", None, False),
    "dueño de": ("propietario_de", None, False),
    "socio de": (
        lambda ta, tb, c: (
            ("socio_de", None, False)
            if (ta, tb) == (P, P)
            else ("propietario_de", None, False)
            if tb == O
            else (SIN_TIPO, None, False)
        )
    ),
    "financia a": ("financia_a", None, False),
    "donó a": ("financia_a", None, False),
    "contrató a": ("contrato_a", None, False),
    "aliado de": ("apoya_a", None, False),
    "apoyó a": ("apoya_a", None, False),
    "opositor de": ("se_opone_a", None, False),
    "criticó a": ("se_opone_a", None, False),
    "investigado por": ("investigado_por", "investigado", False),
    "acusado de": ("investigado_por", "acusado", False),
    "condenado por": ("investigado_por", "condenado", False),
    "ubicado en": ("ubicado_en", None, False),
    "padre o madre de": ("familiar_de", "hijo_de", True),
    "hijo de": ("familiar_de", "hijo_de", False),
    "hermano de": ("familiar_de", "hermano", False),
    "cónyuge o pareja de": ("familiar_de", "conyuge", False),
    "familiar de": ("familiar_de", "otro", False),
    "se reunió con": (SIN_TIPO, None, False),
    "citado en": (SIN_TIPO, None, False),
    "autor de": (SIN_TIPO, None, False),
    "destinado a": (SIN_TIPO, None, False),
    "sanciona con": (SIN_TIPO, None, False),
    "demandó a": (SIN_TIPO, None, False),
    # nuevos (los homónimos ya están arriba)
    "ocupó el cargo": ("ocupa_cargo", "anterior", False),
    "aspira al cargo": ("ocupa_cargo", "aspirante", False),
    "propietario de": ("propietario_de", None, False),
    "apoya a": ("apoya_a", None, False),
    "se opone a": ("se_opone_a", None, False),
    "acusado por": ("investigado_por", "acusado", False),
    "cónyuge de": ("familiar_de", "conyuge", False),
    "vínculo sin tipo": (SIN_TIPO, None, False),
}

PREDICADOS_VIEJOS = frozenset(
    [
        "padre o madre de",
        "hijo de",
        "hermano de",
        "cónyuge o pareja de",
        "familiar de",
        "ocupa el cargo",
        "trabaja en",
        "dirige",
        "fundó",
        "dueño de",
        "asesor de",
        "sucedió a",
        "nombró a",
        "renunció a",
        "parte de",
        "aliado de",
        "opositor de",
        "miembro de",
        "aspira a",
        "apoyó a",
        "se reunió con",
        "criticó a",
        "financia a",
        "contrató a",
        "socio de",
        "donó a",
        "destinado a",
        "investigado por",
        "condenado por",
        "acusado de",
        "demandó a",
        "sanciona con",
        "ubicado en",
        "citado en",
        "autor de",
    ]
)
PREDICADOS_NUEVOS = frozenset(
    [
        "cónyuge de",
        "hijo de",
        "hermano de",
        "familiar de",
        "ocupa el cargo",
        "ocupó el cargo",
        "aspira al cargo",
        "nombró a",
        "sucedió a",
        "trabaja en",
        "dirige",
        "miembro de",
        "fundó",
        "propietario de",
        "socio de",
        "parte de",
        "contrató a",
        "financia a",
        "apoya a",
        "se opone a",
        "investigado por",
        "acusado por",
        "condenado por",
        "ubicado en",
        "vínculo sin tipo",
    ]
)
assert PREDICADOS_VIEJOS | PREDICADOS_NUEVOS == set(_REGLAS)


def mapear_predicado(predicado: str, tipo_a: str, tipo_b: str, cuando: str = "vigente") -> Mapeo:
    """Traduce un predicado de legajo, con los tipos de enrel de sus extremos. Lo que no encaja va a SIN_TIPO."""
    regla = _REGLAS.get(predicado)
    if regla is None:
        raise ValueError(f"predicado de legajo desconocido: {predicado!r}")
    relacion, atributo, invertir = regla(tipo_a, tipo_b, cuando) if callable(regla) else regla
    ta, tb = (tipo_b, tipo_a) if invertir else (tipo_a, tipo_b)
    if relacion != SIN_TIPO and not admite(relacion, ta, tb):
        return _NADA
    return Mapeo(relacion, atributo, invertir)
