"""Punto de entrada `enrel`. Los subcomandos se registran en `SUBCOMANDOS`."""

import argparse
import sys

SUBCOMANDOS: dict[str, tuple[str, callable]] = {}


def registrar(nombre: str, ayuda: str):
    def decorador(fn):
        SUBCOMANDOS[nombre] = (ayuda, fn)
        return fn

    return decorador


def main(argv: list[str] | None = None) -> int:
    # Importar aquí los módulos que registran subcomandos, para no cargar torch al arrancar.
    from enrel import _subcomandos  # noqa: F401

    parser = argparse.ArgumentParser(prog="enrel", description="Entidades y relaciones de noticias en español.")
    sub = parser.add_subparsers(dest="orden")
    for nombre, (ayuda, fn) in SUBCOMANDOS.items():
        p = sub.add_parser(nombre, help=ayuda)
        fn.configurar(p)
        p.set_defaults(ejecutar=fn)
    args = parser.parse_args(argv)
    if not args.orden:
        parser.print_help()
        return 0
    return int(args.ejecutar(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
