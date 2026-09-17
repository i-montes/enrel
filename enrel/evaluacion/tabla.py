"""Filas y tablas markdown; por debajo de `minimo_n` casos de oro no se publica la cifra."""

from enrel.evaluacion.emparejar import PRF


def fila(nombre: str, prf: PRF, minimo_n: int = 10, ic: tuple[float, float] | None = None) -> dict:
    if prf.n < minimo_n and not nombre.startswith("__"):
        return {"nombre": nombre, "n": prf.n, "p": "insuficiente", "r": "insuficiente", "f1": "insuficiente", "ic": ""}
    return {
        "nombre": nombre,
        "n": prf.n,
        "p": f"{prf.p:.2f}",
        "r": f"{prf.r:.2f}",
        "f1": f"{prf.f1:.2f}",
        "ic": f"[{ic[0]:.2f}, {ic[1]:.2f}]" if ic else "",
    }


def tabla_markdown(filas: list[dict], titulo: str) -> str:
    lineas = [f"### {titulo}", "", "| | n | P | R | F1 | IC 95 % |", "|---|---:|---:|---:|---:|---|"]
    for f in filas:
        lineas.append(f"| {f['nombre']} | {f['n']} | {f['p']} | {f['r']} | {f['f1']} | {f['ic']} |")
    return "\n".join(lineas) + "\n"
