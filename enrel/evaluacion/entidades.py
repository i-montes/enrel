"""P/R/F1 de menciones por tipo, en modo estricto (tramo y tipo exactos) o parcial (solape y tipo)."""

from enrel.datos.documento import Documento
from enrel.evaluacion.emparejar import PRF, alinear, emparejar_menciones


def evaluar_entidades(oro: list[Documento], pred: list[Documento], modo: str = "estricto") -> dict[str, PRF]:
    por_tipo: dict[str, PRF] = {}
    total = PRF()
    for o, p in alinear(oro, pred):
        pares = emparejar_menciones(o.menciones, p.menciones, modo)
        emparejadas_o = {id(a) for a, _ in pares}
        emparejadas_p = {id(b) for _, b in pares}
        for m in o.menciones:
            por_tipo.setdefault(m.tipo, PRF())
            if id(m) in emparejadas_o:
                por_tipo[m.tipo].tp += 1
            else:
                por_tipo[m.tipo].fn += 1
        for m in p.menciones:
            if id(m) not in emparejadas_p:
                por_tipo.setdefault(m.tipo, PRF()).fp += 1
    for prf in por_tipo.values():
        total.sumar(prf)
    por_tipo["__global__"] = total
    return por_tipo
