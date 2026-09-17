"""Subcomando `enrel muestrear`."""

from pathlib import Path

from enrel.cli import registrar


@registrar("muestrear", "Muestrea la plata en tres estratos: dirigido, perfiles y aleatorio")
def muestrear_cmd(args):
    from enrel.corpus.muestrear import guardar_seleccion, muestrear, resumen

    excluir: set[str] = set()
    if args.excluir:
        ruta = Path(args.excluir)
        if not ruta.exists():
            raise SystemExit(
                f"--excluir apunta a un fichero que no existe: {ruta}. "
                "Si de verdad quieres muestrear sin exclusión, no pases --excluir."
            )
        excluir = {linea.strip() for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()}
    else:
        print("aviso: sin --excluir, la muestra no protege ningún doc_id de fugas")

    sel = muestrear(
        Path(args.corpus),
        excluir,
        semilla=args.semilla,
        cuota_relacion=args.cuota_relacion,
        perfiles=args.perfiles,
        aleatorios=args.aleatorios,
        humo=args.humo,
    )
    guardar_seleccion(sel, Path(args.salida))
    print(resumen(sel))


def _configurar(p):
    p.add_argument("--corpus", default="datos/corpus/articulos.jsonl")
    p.add_argument("--excluir", default=None)
    p.add_argument("--salida", default="datos/conjuntos/seleccion.jsonl")
    p.add_argument("--semilla", type=int, default=2026)
    p.add_argument("--cuota-relacion", type=int, default=120)
    p.add_argument("--perfiles", type=int, default=400)
    p.add_argument("--aleatorios", type=int, default=1100)
    p.add_argument("--humo", type=int, default=30)


muestrear_cmd.configurar = _configurar
