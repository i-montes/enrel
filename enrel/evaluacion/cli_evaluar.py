"""Subcomando `enrel evaluar`."""

from pathlib import Path

from enrel.cli import registrar


@registrar("evaluar", "Evalúa una predicción contra el oro y escribe el informe en markdown")
def evaluar_cmd(args):
    from enrel.datos.documento import cargar_jsonl, hash_fichero
    from enrel.evaluacion.informe import informe_completo

    oro, pred = cargar_jsonl(args.oro), cargar_jsonl(args.pred)
    entrenamiento = cargar_jsonl(args.entrenamiento) if args.entrenamiento else None
    hashes = {"oro": hash_fichero(args.oro), "pred": hash_fichero(args.pred)}
    if args.entrenamiento:
        hashes["entrenamiento"] = hash_fichero(args.entrenamiento)
    md = informe_completo(oro, pred, entrenamiento, args.nombre, not args.sin_intervalos, hashes)
    if args.salida:
        Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
        Path(args.salida).write_text(md, encoding="utf-8")
        print(f"informe → {args.salida}")
    else:
        print(md)


def _configurar(p):
    p.add_argument("--oro", required=True)
    p.add_argument("--pred", required=True)
    p.add_argument("--entrenamiento", default=None)
    p.add_argument("--nombre", default="modelo")
    p.add_argument("--salida", default=None)
    p.add_argument("--sin-intervalos", action="store_true")


evaluar_cmd.configurar = _configurar
