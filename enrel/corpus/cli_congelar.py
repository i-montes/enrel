"""Subcomando `enrel congelar`."""

from pathlib import Path

from enrel.cli import registrar


@registrar("congelar", "Congela el archivo de legajo en datos/corpus/articulos.jsonl")
def congelar_cmd(args):
    from enrel.corpus.congelar import congelar
    from enrel.corpus.legajo_db import conectar, ruta_db

    con = conectar(ruta_db(args.legajo_db))
    resumen = congelar(con, Path(args.salida), args.min, args.max)
    print(f"{resumen['total']} artículos → {args.salida}; excluidos {resumen['excluidos']}")


def _configurar(p):
    p.add_argument("--salida", default="datos/corpus/articulos.jsonl")
    p.add_argument("--legajo-db", default=None)
    p.add_argument("--min", type=int, default=150)
    p.add_argument("--max", type=int, default=2000)


congelar_cmd.configurar = _configurar
