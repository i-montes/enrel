"""Normalización de texto: NFC para persistir, plegado para comparar."""

import re
import unicodedata

PALABRA = re.compile(r"\w+(?:[-_]\w+)*|\S")
_COMILLAS = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'"})


def nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def plegar(texto: str) -> str:
    """Minúsculas, sin diacríticos, comillas rectas, espacios colapsados. Solo para comparar, nunca para guardar."""
    t = unicodedata.normalize("NFD", texto.translate(_COMILLAS))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def palabras(texto: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in PALABRA.finditer(texto)]
