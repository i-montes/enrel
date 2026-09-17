"""Lee docs/guia-anotacion.md y devuelve las definiciones estructuradas que usan los prompts y la documentación."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from enrel.esquema.tipos import RELACIONES, SIN_TIPO, TIPOS


@dataclass
class DefTipo:
    nombre: str
    se_marca: str
    no_se_marca: str


@dataclass
class DefRelacionGuia:
    nombre: str
    definicion: str
    ejemplos: list[str] = field(default_factory=list)
    no_es: list[str] = field(default_factory=list)
    confusiones: list[str] = field(default_factory=list)
    atributos: dict[str, str] = field(default_factory=dict)


def _secciones(texto: str, nivel: str) -> list[tuple[str, str]]:
    """Divide por encabezados del nivel dado («## » o «### »): [(titulo, cuerpo)]."""
    patron = re.compile(rf"^{re.escape(nivel)} (.+)$", re.M)
    coincidencias = list(patron.finditer(texto))
    out = []
    for i, m in enumerate(coincidencias):
        fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(texto)
        out.append((m.group(1).strip(), texto[m.end() : fin]))
    return out


def _campo(cuerpo: str, nombre: str) -> str:
    m = re.search(rf"\*\*{re.escape(nombre)}:\*\*\s*(.*?)(?=\n\*\*[^\n]+:\*\*|\n##|\Z)", cuerpo, re.S)
    return m.group(1).strip() if m else ""


def _vinetas(bloque: str) -> list[str]:
    return [linea[2:].strip() for linea in bloque.splitlines() if linea.strip().startswith("- ")]


def _atributos(texto: str) -> dict[str, str]:
    out = {}
    for parte in re.split(r";\s*", texto):
        if ":" in parte:
            k, v = parte.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def cargar_guia(
    ruta: Path = Path("docs/guia-anotacion.md"),
) -> tuple[dict[str, DefTipo], dict[str, DefRelacionGuia], list[str]]:
    texto = Path(ruta).read_text(encoding="utf-8")
    principales = dict(_secciones(texto, "##"))
    convenciones = _vinetas(principales.get("Convenciones", ""))
    tipos = {}
    for nombre, cuerpo in _secciones(principales.get("Tipos de entidad", ""), "###"):
        tipos[nombre] = DefTipo(nombre, _campo(cuerpo, "Se marca"), _campo(cuerpo, "No se marca"))
    relaciones = {}
    for nombre, cuerpo in _secciones(principales.get("Relaciones", ""), "###"):
        relaciones[nombre] = DefRelacionGuia(
            nombre,
            _campo(cuerpo, "Definición"),
            _vinetas(_campo(cuerpo, "Ejemplos")),
            _vinetas(_campo(cuerpo, "No es")),
            _vinetas(_campo(cuerpo, "Confusiones")),
            _atributos(_campo(cuerpo, "Atributos")),
        )
    faltan_t = set(TIPOS) - set(tipos)
    faltan_r = set(RELACIONES) - set(relaciones)
    if faltan_t or faltan_r:
        raise ValueError(f"la guía no define: tipos {sorted(faltan_t)}, relaciones {sorted(faltan_r)}")
    for r in relaciones.values():
        if r.nombre != SIN_TIPO and (len(r.ejemplos) < 3 or len(r.no_es) < 2 or not r.definicion):
            raise ValueError(f"la relación {r.nombre} necesita definición, 3 ejemplos y 2 «no es»")
    for nombre, d in RELACIONES.items():
        if set(relaciones[nombre].atributos) != set(d.atributos):
            raise ValueError(
                f"atributos de {nombre} en la guía {sorted(relaciones[nombre].atributos)}"
                f" ≠ esquema {sorted(d.atributos)}"
            )
    return tipos, relaciones, convenciones
