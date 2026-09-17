"""Subcomando `enrel exportar-legajo`: oro JSON, lote de la base o plata de legajo → formato interno."""

from pathlib import Path

from enrel.cli import registrar


@registrar("exportar-legajo", "Convierte oro o plata de legajo al formato interno de enrel")
def exportar_cmd(args):
    from enrel.anotacion import desde_legajo as dl
    from enrel.corpus import legajo_db as db
    from enrel.datos.documento import guardar_jsonl

    con = db.conectar(db.ruta_db(args.legajo_db))
    docs, no_loc, errores = [], 0, []

    def agregar(constructor, wp):
        nonlocal no_loc
        art = db.articulo(con, wp)
        if art is None:
            errores.append(f"wp:{wp} sin texto en la base")
            return
        try:
            d = constructor(art)
        except ValueError as e:
            errores.append(f"wp:{wp}: {e}")
            return
        no_loc += d.origen.get("no_localizadas", 0)
        docs.append(d)

    if args.oro_json:
        for wp, spec in dl.leer_oro_json(Path(args.oro_json)).items():
            agregar(lambda art, spec=spec: dl.documento_desde_oro_json(spec, art), wp)
    elif args.lote is not None:
        consulta = "SELECT DISTINCT wp_id FROM anotaciones WHERE lote_id = ?"
        if args.solo_validos:
            consulta = (
                "SELECT DISTINCT a.wp_id FROM anotaciones a"
                " JOIN tiempos t ON t.lote_id = a.lote_id AND t.wp_id = a.wp_id"
                " WHERE a.lote_id = ? AND t.valido = 1 AND t.cerrado = 1"
            )
        for (wp,) in con.execute(consulta, (args.lote,)):
            agregar(lambda art: dl.documento_desde_sqlite(con, args.lote, art), wp)
    elif args.plata:
        for wp, filas in dl.leer_plata_legajo(Path(args.plata)).items():
            agregar(lambda art, filas=filas: dl.documento_desde_plata_legajo(filas, art), wp)
    else:
        raise SystemExit("hace falta --oro-json, --lote o --plata")
    n = guardar_jsonl(docs, Path(args.salida))
    print(f"{n} documentos → {args.salida}; menciones no localizadas: {no_loc}; errores: {len(errores)}")
    for e in errores[:20]:
        print("  ", e)


def _configurar(p):
    p.add_argument("--oro-json", default=None)
    p.add_argument("--lote", type=int, default=None)
    p.add_argument("--solo-validos", action="store_true")
    p.add_argument("--plata", default=None)
    p.add_argument("--salida", required=True)
    p.add_argument("--legajo-db", default=None)


exportar_cmd.configurar = _configurar
