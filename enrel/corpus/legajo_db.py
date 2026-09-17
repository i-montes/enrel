"""Lectura del archivo desde la base de legajo (solo lectura)."""

import html
import os
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from enrel.datos.normalizar import nfc

RUTA_POR_DEFECTO = Path("~/.local/share/com.legajo.app/legajo.sqlite").expanduser()
_PREFIJO = "https://www.lasillavacia.com/"


def ruta_db(explicita: str | None = None) -> Path:
    if explicita:
        return Path(explicita).expanduser()
    if os.environ.get("ENREL_LEGAJO_DB"):
        return Path(os.environ["ENREL_LEGAJO_DB"]).expanduser()
    return RUTA_POR_DEFECTO


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    ruta = Path(ruta) if ruta else RUTA_POR_DEFECTO
    if not ruta.exists():
        raise FileNotFoundError(f"no existe la base de legajo en {ruta}")
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def seccion_de(link: str) -> str:
    if not link or not link.startswith(_PREFIJO):
        return ""
    resto = link[len(_PREFIJO) :]
    return resto.split("/", 1)[0] if "/" in resto else ""


@dataclass
class Articulo:
    wp_id: int
    titulo: str
    texto_plano: str
    palabras: int
    url: str
    fecha: str
    seccion: str

    @property
    def desplazamiento_cuerpo(self) -> int:
        return len(self.titulo) + 2 if self.titulo else 0

    @property
    def texto(self) -> str:
        return f"{self.titulo}\n\n{self.texto_plano}" if self.titulo else self.texto_plano


def _fila_a_articulo(fila: sqlite3.Row) -> Articulo:
    titulo = nfc(html.unescape(fila["title"] or "")).strip()
    return Articulo(
        wp_id=int(fila["wp_id"]),
        titulo=titulo,
        texto_plano=nfc(fila["text_plain"] or ""),
        palabras=int(fila["word_count"] or 0),
        url=fila["link"] or "",
        fecha=(fila["date"] or "")[:10],
        seccion=seccion_de(fila["link"] or ""),
    )


_CONSULTA = """
SELECT a.wp_id, a.text_plain, a.word_count, c.date, c.link, c.title
FROM articles a JOIN census c ON c.connection_id = a.connection_id AND c.wp_id = a.wp_id
"""


def articulo(con: sqlite3.Connection, wp_id: int) -> Articulo | None:
    fila = con.execute(_CONSULTA + " WHERE a.wp_id = ?", (wp_id,)).fetchone()
    return _fila_a_articulo(fila) if fila else None


def iterar_articulos(con: sqlite3.Connection, minimo_palabras: int = 0) -> Iterator[Articulo]:
    for fila in con.execute(
        _CONSULTA + " WHERE a.text_plain IS NOT NULL AND a.word_count >= ? ORDER BY a.wp_id",
        (minimo_palabras,),
    ):
        yield _fila_a_articulo(fila)


def parrafos(texto_plano: str) -> list[tuple[int, str]]:
    out, pos = [], 0
    for trozo in texto_plano.split("\n\n"):
        out.append((pos, trozo))
        pos += len(trozo) + 2
    return out


def es_transcripcion(texto_plano: str) -> bool:
    ps = [p for _, p in parrafos(texto_plano) if p.strip()]
    if len(ps) <= 40:
        return False
    cortos = sum(1 for p in ps if "\n" not in p and len(p.split()) < 12)
    return cortos / len(ps) > 0.6
