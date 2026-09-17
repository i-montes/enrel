"""Filas y tablas markdown; por debajo de `minimo_n` casos de oro no se publica la cifra."""

from enrel.evaluacion.emparejar import PRF

_COLUMNAS_TODAS = ("n", "p", "r", "f1")


def fila(
    nombre: str,
    prf: PRF,
    minimo_n: int = 10,
    ic: tuple[float, float] | None = None,
    columnas: tuple[str, ...] = _COLUMNAS_TODAS,
) -> dict:
    """Una fila de tabla. `columnas` dice qué celdas tienen una cifra real; el resto queda en blanco.

    Por ejemplo, `columnas=("f1",)` publica solo F1 (n, P y R en blanco) para una fila como
    «macro», cuyo n/P/R no son cifras reales; `columnas=("n", "r")` publica n y R (P y F1 en
    blanco) para una fila como «direccion», cuya única cifra real es la tasa de aciertos R.
    """
    if prf.n < minimo_n and not nombre.startswith("__"):
        return {"nombre": nombre, "n": prf.n, "p": "insuficiente", "r": "insuficiente", "f1": "insuficiente", "ic": ""}
    valores = {"n": prf.n, "p": f"{prf.p:.2f}", "r": f"{prf.r:.2f}", "f1": f"{prf.f1:.2f}"}
    return {
        "nombre": nombre,
        **{c: (valores[c] if c in columnas else "") for c in _COLUMNAS_TODAS},
        "ic": f"[{ic[0]:.2f}, {ic[1]:.2f}]" if ic else "",
    }


def tabla_markdown(filas: list[dict], titulo: str) -> str:
    lineas = [f"### {titulo}", "", "| | n | P | R | F1 | IC 95 % |", "|---|---:|---:|---:|---:|---|"]
    for f in filas:
        lineas.append(f"| {f['nombre']} | {f['n']} | {f['p']} | {f['r']} | {f['f1']} | {f['ic']} |")
    return "\n".join(lineas) + "\n"
