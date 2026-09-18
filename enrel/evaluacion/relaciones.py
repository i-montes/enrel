"""Evaluación de relaciones sobre grupos emparejados: RE, RE+, nivel fino, micro, macro, dirección e Ign.

Asimetría deliberada entre micro y macro sobre `vinculo_sin_tipo` (clase 19 del esquema, la
reserva para vínculos reales que no encajan en ninguna de las 18 relaciones — no es «sin
relación», que la representa el umbral del modelo, no esta clase): `__micro__` la INCLUYE,
para que un maestro que vuelque en la reserva lo que no sabe clasificar pague sus falsos
positivos igual que cualquier otra clase. `__micro_sin_reserva__` la excluye, para poder
comparar. `__macro__` sigue excluyéndola siempre: una media de F1 por clase no debe dejarse
dominar por una clase que por definición no tiene un límite claro de qué admite.

La vigencia (vigente/pasada/futura) es, como la dirección, un eje ortogonal a RE y RE+: no
entra en la condición de acierto de ninguna relación, gruesa o fina. Mezclarla haría el F1 de
relaciones ilegible (una relación con la dirección o la vigencia correctas pero cambiadas de
sitio no es lo mismo que no haberla encontrado). Se reporta aparte, en `__vigencia__`: de las
relaciones que ya acertaron en par y etiqueta, cuántas también acertaron la vigencia (tp) y
cuántas no (fn); no tiene fp propio, así que su cifra publicable es la tasa `r` = aciertos de
vigencia entre las relaciones acertadas, igual que `__direccion__`.
"""

from enrel.datos.documento import Documento, Relacion
from enrel.datos.normalizar import plegar
from enrel.esquema.tipos import SIN_TIPO, clase_fina, es_simetrica
from enrel.evaluacion.emparejar import PRF, alinear, emparejar_grupos


def _etiqueta(r: Relacion, nivel: str) -> str:
    return clase_fina(r.relacion, r.atributo) if nivel == "fina" else r.relacion


def _canonica(doc: Documento, r: Relacion, nivel: str) -> tuple[str, str, str]:
    a, b = plegar(doc.grupo_de(r.cabeza).canonico), plegar(doc.grupo_de(r.cola).canonico)
    if es_simetrica(r.relacion, r.atributo):
        a, b = sorted((a, b))
    return a, _etiqueta(r, nivel), b


def tripletas_canonicas(docs: list[Documento], nivel: str = "gruesa") -> set[tuple[str, str, str]]:
    return {_canonica(d, r, nivel) for d in docs for r in d.relaciones}


class _Macro(PRF):
    """Un `PRF` sintético cuyo `f1` es fijo: la media de los F1 por etiqueta (`tp`/`fp`/`fn` quedan en 0)."""

    def __init__(self, f1: float):
        super().__init__()
        self._f1 = f1

    @property
    def f1(self) -> float:
        return self._f1


def evaluar_relaciones(
    oro: list[Documento],
    pred: list[Documento],
    nivel: str = "gruesa",
    exigir_tipos: bool = False,
    ignorar: set[tuple] | None = None,
) -> dict[str, PRF]:
    ignorar = ignorar or set()
    por_etiqueta: dict[str, PRF] = {}
    direccion = PRF()
    vigencia = PRF()

    def prf(etiqueta: str) -> PRF:
        return por_etiqueta.setdefault(etiqueta, PRF())

    for o, p in alinear(oro, pred):
        mapa = emparejar_grupos(o, p)
        tipos_pred = {g.id: g.tipo for g in p.grupos}
        libres = list(p.relaciones)
        consumidas: set[int] = set()

        for ro in o.relaciones:
            if _canonica(o, ro, nivel) in ignorar:
                continue
            et = _etiqueta(ro, nivel)
            simetrica = es_simetrica(ro.relacion, ro.atributo)
            gc, gl = mapa.get(ro.cabeza), mapa.get(ro.cola)
            if gc is not None and gl is not None and exigir_tipos:
                if tipos_pred[gc] != o.grupo_de(ro.cabeza).tipo or tipos_pred[gl] != o.grupo_de(ro.cola).tipo:
                    gc = gl = None

            acierto = None
            invertida = None
            if gc is not None and gl is not None:
                for k, rp in enumerate(libres):
                    if k in consumidas or _etiqueta(rp, nivel) != et:
                        continue
                    if (rp.cabeza, rp.cola) == (gc, gl):
                        acierto = k
                        break
                    if (rp.cabeza, rp.cola) == (gl, gc):
                        if simetrica:
                            acierto = k
                            break
                        invertida = k

            if acierto is not None:
                consumidas.add(acierto)
                prf(et).tp += 1
                if not simetrica:
                    direccion.tp += 1
                if libres[acierto].vigencia == ro.vigencia:
                    vigencia.tp += 1
                else:
                    vigencia.fn += 1
            else:
                prf(et).fn += 1
                if invertida is not None:
                    direccion.fn += 1

        for k, rp in enumerate(libres):
            if k in consumidas:
                continue
            if _canonica(p, rp, nivel) in ignorar:
                continue
            prf(_etiqueta(rp, nivel)).fp += 1

    micro = PRF()
    micro_sin_reserva = PRF()
    f1s = []
    for etiqueta, x in por_etiqueta.items():
        micro.sumar(x)
        if etiqueta != SIN_TIPO:
            micro_sin_reserva.sumar(x)
            if x.n >= 1:
                f1s.append(x.f1)
    por_etiqueta["__micro__"] = micro
    por_etiqueta["__micro_sin_reserva__"] = micro_sin_reserva
    por_etiqueta["__macro__"] = _Macro(sum(f1s) / len(f1s) if f1s else 0.0)
    por_etiqueta["__direccion__"] = direccion
    por_etiqueta["__vigencia__"] = vigencia
    return por_etiqueta
