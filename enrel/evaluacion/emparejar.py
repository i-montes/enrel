"""Emparejamiento de menciones y grupos entre oro y predicción, y el contador P/R/F1."""

from dataclasses import dataclass

from enrel.datos.documento import Documento, Mencion


@dataclass
class PRF:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def p(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def r(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        return 2 * self.p * self.r / (self.p + self.r) if self.p + self.r else 0.0

    @property
    def n(self) -> int:
        return self.tp + self.fn

    def sumar(self, otro: "PRF") -> None:
        self.tp += otro.tp
        self.fp += otro.fp
        self.fn += otro.fn


def solapan(a: Mencion, b: Mencion) -> bool:
    return a.ini < b.fin and b.ini < a.fin


def _solape(a: Mencion, b: Mencion) -> int:
    return max(0, min(a.fin, b.fin) - max(a.ini, b.ini))


def emparejar_menciones(oro: list[Mencion], pred: list[Mencion], modo: str) -> list[tuple[Mencion, Mencion]]:
    if modo == "estricto":
        indice = {(m.ini, m.fin, m.tipo): m for m in pred}
        return [(o, indice[(o.ini, o.fin, o.tipo)]) for o in oro if (o.ini, o.fin, o.tipo) in indice]
    if modo != "parcial":
        raise ValueError(modo)
    pares = [
        (_solape(o, p), i, j)
        for i, o in enumerate(oro)
        for j, p in enumerate(pred)
        if o.tipo == p.tipo and solapan(o, p)
    ]
    pares.sort(reverse=True)
    usados_o, usados_p, out = set(), set(), []
    for _, i, j in pares:
        if i not in usados_o and j not in usados_p:
            usados_o.add(i)
            usados_p.add(j)
            out.append((oro[i], pred[j]))
    return out


def emparejar_grupos(oro: Documento, pred: Documento) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for g in oro.grupos:
        votos: dict[str, int] = {}
        for mo in oro.menciones_de(g.id):
            for mp in pred.menciones:
                if mp.tipo == g.tipo and solapan(mo, mp):
                    votos[mp.grupo] = votos.get(mp.grupo, 0) + 1
        out[g.id] = max(votos, key=votos.get) if votos else None
    return out


def por_doc_id(docs: list[Documento]) -> dict[str, Documento]:
    return {d.doc_id: d for d in docs}


def alinear(oro_docs: list[Documento], pred_docs: list[Documento]) -> list[tuple[Documento, Documento]]:
    pred = por_doc_id(pred_docs)
    faltan = [d.doc_id for d in oro_docs if d.doc_id not in pred]
    if faltan:
        raise ValueError(f"la predicción no trae {len(faltan)} documentos del oro, por ejemplo {faltan[:3]}")
    return [(d, pred[d.doc_id]) for d in oro_docs]
