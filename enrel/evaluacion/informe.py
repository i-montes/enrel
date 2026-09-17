"""El informe completo de una evaluación: entidades, relaciones gruesas y finas, con intervalos."""

from datetime import date

from enrel.datos.documento import Documento
from enrel.evaluacion.bootstrap import intervalo
from enrel.evaluacion.entidades import evaluar_entidades
from enrel.evaluacion.relaciones import evaluar_relaciones, tripletas_canonicas
from enrel.evaluacion.tabla import fila, tabla_markdown

_GLOBALES = ("__micro__", "__macro__", "__direccion__", "__global__")


def _tabla(resultados: dict, titulo: str, oro, pred, metrica_global=None, con_intervalos=True) -> str:
    filas = []
    for nombre in sorted(k for k in resultados if k not in _GLOBALES):
        filas.append(fila(nombre, resultados[nombre]))
    for g in _GLOBALES:
        if g in resultados:
            ic = (
                intervalo(oro, pred, metrica_global(g))
                if (con_intervalos and metrica_global and g in ("__micro__", "__global__"))
                else None
            )
            filas.append(fila(g.strip("_"), resultados[g], minimo_n=0, ic=ic))
    return tabla_markdown(filas, titulo)


def informe_completo(
    oro: list[Documento],
    pred: list[Documento],
    entrenamiento: list[Documento] | None = None,
    nombre_modelo: str = "modelo",
    con_intervalos: bool = True,
    hashes: dict[str, str] | None = None,
) -> str:
    partes = [f"# Evaluación de {nombre_modelo}", "", f"Fecha: {date.today().isoformat()} · documentos: {len(oro)}"]
    if hashes:
        partes += ["", *[f"- `{k}`: `{v}`" for k, v in hashes.items()]]
    partes.append("")

    for modo in ("estricto", "parcial"):

        def metrica_entidades(g, modo=modo):
            def _f(o, p):
                return evaluar_entidades(o, p, modo)[g].f1

            return _f

        res = evaluar_entidades(oro, pred, modo)
        partes.append(_tabla(res, f"Entidades, {modo}", oro, pred, metrica_entidades, con_intervalos))

    for exigir, titulo in ((False, "Relaciones gruesas, RE"), (True, "Relaciones gruesas, RE+")):

        def metrica_relaciones(g, e=exigir):
            def _f(o, p):
                return evaluar_relaciones(o, p, "gruesa", exigir_tipos=e)[g].f1

            return _f

        res = evaluar_relaciones(oro, pred, "gruesa", exigir_tipos=exigir)
        partes.append(_tabla(res, titulo, oro, pred, metrica_relaciones, con_intervalos))

    if entrenamiento:
        ign = tripletas_canonicas(entrenamiento, "gruesa")
        res = evaluar_relaciones(oro, pred, "gruesa", exigir_tipos=True, ignorar=ign)
        partes.append(
            _tabla(
                res,
                f"Relaciones gruesas, RE+ Ign ({len(ign)} tripletas vistas en entrenamiento)",
                oro,
                pred,
                None,
                False,
            )
        )

    res = evaluar_relaciones(oro, pred, "fina", exigir_tipos=True)
    partes.append(_tabla(res, "Relaciones finas, RE+", oro, pred, None, False))
    return "\n".join(partes)
