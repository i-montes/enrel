"""El formato interno: un documento con menciones, grupos y relaciones sobre offsets de caracteres."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from enrel.esquema.tipos import clase_fina


@dataclass
class Mencion:
    id: str
    ini: int
    fin: int
    texto: str
    tipo: str
    grupo: str
    confianza: float | None = None


@dataclass
class Grupo:
    id: str
    tipo: str
    canonico: str


@dataclass
class Relacion:
    cabeza: str
    cola: str
    relacion: str
    atributo: str | None = None
    evidencia: tuple[int, int] | None = None
    confianza: float | None = None


@dataclass
class Documento:
    doc_id: str
    texto: str
    menciones: list[Mencion]
    grupos: list[Grupo]
    relaciones: list[Relacion]
    url: str = ""
    fecha: str = ""
    seccion: str = ""
    titulo: str = ""
    fuente: str = ""
    origen: dict = field(default_factory=dict)

    def grupo_de(self, grupo_id: str) -> Grupo:
        for g in self.grupos:
            if g.id == grupo_id:
                return g
        raise KeyError(grupo_id)

    def menciones_de(self, grupo_id: str) -> list[Mencion]:
        return [m for m in self.menciones if m.grupo == grupo_id]

    def clase_fina_de(self, rel: Relacion) -> str:
        return clase_fina(rel.relacion, rel.atributo)

    def a_dict(self) -> dict:
        d = asdict(self)
        for r in d["relaciones"]:
            ev = r["evidencia"]
            r["evidencia"] = None if ev is None else {"ini": ev[0], "fin": ev[1]}
        return d

    @classmethod
    def desde_dict(cls, d: dict) -> "Documento":
        rels = []
        for r in d.get("relaciones", []):
            ev = r.get("evidencia")
            rels.append(
                Relacion(
                    r["cabeza"],
                    r["cola"],
                    r["relacion"],
                    r.get("atributo"),
                    None if ev is None else (ev["ini"], ev["fin"]),
                    r.get("confianza"),
                )
            )
        return cls(
            doc_id=d["doc_id"],
            texto=d["texto"],
            menciones=[Mencion(**m) for m in d.get("menciones", [])],
            grupos=[Grupo(**g) for g in d.get("grupos", [])],
            relaciones=rels,
            url=d.get("url", ""),
            fecha=d.get("fecha", ""),
            seccion=d.get("seccion", ""),
            titulo=d.get("titulo", ""),
            fuente=d.get("fuente", ""),
            origen=d.get("origen", {}),
        )


def guardar_jsonl(docs: Iterable[Documento], ruta: Path) -> int:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with ruta.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d.a_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def cargar_jsonl(ruta: Path) -> list[Documento]:
    with Path(ruta).open(encoding="utf-8") as f:
        return [Documento.desde_dict(json.loads(linea)) for linea in f if linea.strip()]


def hash_fichero(ruta: Path) -> str:
    h = hashlib.sha256()
    with Path(ruta).open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()
