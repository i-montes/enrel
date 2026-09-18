"""Traduce el vocabulario de legajo (los 35 predicados viejos y los 26 nuevos) al esquema de enrel."""

from dataclasses import dataclass

from enrel.esquema.tipos import SIN_TIPO, TIPOS, VIGENCIA_POR_DEFECTO, VIGENCIAS, O, P, admite

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
    vigencia: str = VIGENCIA_POR_DEFECTO


_NADA = Mapeo(SIN_TIPO, None, False)

# Predicados que ya llevan el tiempo en el nombre: su vigencia es fija y gana sobre `cuando`,
# que en legajo trae la columna del mismo nombre pero aquí sería redundante o contradictorio.
# «aspira al cargo» y «aspira a» no están aquí: aspirar es una modalidad (atributo `aspirante`),
# no un tiempo, así que su vigencia es la que traiga `cuando`, tal cual.
_VIGENCIA_FORZADA = {
    "ocupó el cargo": "pasada",
    "renunció a": "pasada",
}

# Cada regla es (relacion, atributo, invertir) o una función (tipo_a, tipo_b, cuando) → esa tupla.
# El atributo de ocupa_cargo distingue una modalidad ortogonal a la vigencia: `titular` (ejerce,
# ejerció o ejercerá el cargo) frente a `aspirante` (se postula o se postuló). La vigencia sigue
# siendo independiente en ambos casos (ver `_VIGENCIA_FORZADA` y la regla general en `mapear_predicado`).
_REGLAS = {
    # viejos
    "ocupa el cargo": ("ocupa_cargo", "titular", False),
    "aspira a": ("ocupa_cargo", "aspirante", False),
    "renunció a": (lambda ta, tb, c: ("ocupa_cargo", "titular", False) if tb == "cargo" else (SIN_TIPO, None, False)),
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
    # apoya_a y se_opone_a admiten norma en la cola (postura de apoyo u oposición a una ley,
    # sin acto); impulsa_norma (más abajo, entre los nuevos) es el acto legislativo propio
    # (radicar, redactar, ser ponente, sacar adelante, sancionar, aprobar). La comprobación
    # genérica de `admite` en `mapear_predicado` descarta lo que no encaje.
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
    "ocupó el cargo": ("ocupa_cargo", "titular", False),
    "aspira al cargo": ("ocupa_cargo", "aspirante", False),
    "propietario de": ("propietario_de", None, False),
    "apoya a": ("apoya_a", None, False),
    "impulsa": ("impulsa_norma", None, False),
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
        "impulsa",
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
    """Traduce un predicado de legajo, con los tipos de enrel de sus extremos. Lo que no encaja va a SIN_TIPO.

    La vigencia es, en general, `cuando` (si no es una de VIGENCIAS, se usa la por defecto);
    los predicados de `_VIGENCIA_FORZADA` ya llevan el tiempo en el nombre y ganan sobre `cuando`.
    """
    regla = _REGLAS.get(predicado)
    if regla is None:
        raise ValueError(f"predicado de legajo desconocido: {predicado!r}")
    relacion, atributo, invertir = regla(tipo_a, tipo_b, cuando) if callable(regla) else regla
    vigencia = _VIGENCIA_FORZADA.get(predicado) or (cuando if cuando in VIGENCIAS else VIGENCIA_POR_DEFECTO)
    ta, tb = (tipo_b, tipo_a) if invertir else (tipo_a, tipo_b)
    if relacion != SIN_TIPO and not admite(relacion, ta, tb):
        return _NADA
    return Mapeo(relacion, atributo, invertir, vigencia)
