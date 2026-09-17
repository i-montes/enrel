"""Intervalos de confianza al 95 % por bootstrap sobre documentos."""

import random
from collections.abc import Callable

from enrel.datos.documento import Documento
from enrel.evaluacion.emparejar import alinear


def intervalo(
    oro: list[Documento],
    pred: list[Documento],
    metrica: Callable[[list, list], float],
    n: int = 1000,
    semilla: int = 42,
) -> tuple[float, float]:
    pares = alinear(oro, pred)
    rng = random.Random(semilla)
    valores = []
    for _ in range(n):
        muestra = [pares[rng.randrange(len(pares))] for _ in pares]
        valores.append(metrica([o for o, _ in muestra], [p for _, p in muestra]))
    valores.sort()
    return valores[int(0.025 * n)], valores[min(n - 1, int(0.975 * n))]
