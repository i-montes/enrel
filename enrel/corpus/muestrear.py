"""Muestreo de la plata en tres estratos: dirigido por relación, perfiles y aleatorio estratificado (spec §5.2)."""

import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from enrel.corpus.congelar import tramo_de
from enrel.corpus.disparadores import relaciones_disparadas
from enrel.esquema.tipos import RELACIONES


@dataclass
class Seleccionado:
    doc_id: str
    conjunto: str
    estrato: str
    disparadas: list[str]


def _leer(corpus: Path, excluir: set[str]) -> list[dict]:
    filas = []
    with Path(corpus).open(encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            d = json.loads(linea)
            if d["doc_id"] in excluir:
                continue
            d["disparadas"] = sorted(relaciones_disparadas(d["texto"]))
            d["tramo"] = tramo_de(d.get("fecha", ""))
            filas.append(d)
    return filas


def _reparto_por_tramo(cands: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Toma n candidatos repartidos lo más igual posible entre tramos."""
    por_tramo = defaultdict(list)
    for c in cands:
        por_tramo[c["tramo"]].append(c)
    for lista in por_tramo.values():
        rng.shuffle(lista)
    out, tramos = [], sorted(por_tramo)
    while len(out) < n and any(por_tramo[t] for t in tramos):
        for t in tramos:
            if por_tramo[t] and len(out) < n:
                out.append(por_tramo[t].pop())
    return out


def muestrear(
    corpus: Path,
    excluir: set[str],
    semilla: int = 2026,
    cuota_relacion: int = 120,
    perfiles: int = 400,
    aleatorios: int = 1100,
    humo: int = 30,
) -> list[Seleccionado]:
    rng = random.Random(semilla)
    filas = _leer(corpus, excluir)
    rng.shuffle(filas)
    elegidos: dict[str, Seleccionado] = {}

    # 1. Dirigido por relación: los que más relaciones distintas disparan primero.
    for relacion in RELACIONES:
        cands = [d for d in filas if relacion in d["disparadas"] and d["doc_id"] not in elegidos]
        cands.sort(key=lambda d: -len(d["disparadas"]))
        for d in cands[:cuota_relacion]:
            elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "dirigido", d["disparadas"])

    # 2. Perfiles del Quién es Quién, por tramo.
    cands = [d for d in filas if d.get("seccion") == "quien-es-quien" and d["doc_id"] not in elegidos]
    for d in _reparto_por_tramo(cands, perfiles, rng):
        elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "perfiles", d["disparadas"])

    # 3. Aleatorio estratificado por sección (proporcional) y tramo.
    resto = [d for d in filas if d["doc_id"] not in elegidos]
    por_seccion = Counter(d.get("seccion", "") for d in resto)
    total = sum(por_seccion.values()) or 1
    for seccion, n_sec in por_seccion.items():
        cuota = round(aleatorios * n_sec / total)
        cands = [d for d in resto if d.get("seccion", "") == seccion]
        for d in _reparto_por_tramo(cands, cuota, rng):
            elegidos[d["doc_id"]] = Seleccionado(d["doc_id"], "plata", "aleatorio", d["disparadas"])

    sel = list(elegidos.values())
    for s in rng.sample(sel, min(humo, len(sel))):
        s.conjunto = "humo_maestro"
    sel.sort(key=lambda s: s.doc_id)
    return sel


def resumen(sel: list[Seleccionado]) -> dict:
    disparan = Counter()
    for s in sel:
        disparan.update(s.disparadas)
    return {
        "total": len(sel),
        "por_estrato": dict(Counter(s.estrato for s in sel)),
        "por_conjunto": dict(Counter(s.conjunto for s in sel)),
        "disparan": dict(disparan),
    }


def guardar_seleccion(sel: list[Seleccionado], ruta: Path) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        for s in sel:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")
    ruta.with_suffix(".resumen.json").write_text(
        json.dumps(resumen(sel), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def cargar_seleccion(ruta: Path) -> list[Seleccionado]:
    with Path(ruta).open(encoding="utf-8") as f:
        return [Seleccionado(**json.loads(linea)) for linea in f if linea.strip()]
