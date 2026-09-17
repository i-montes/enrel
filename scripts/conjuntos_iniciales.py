"""Fija los conjuntos iniciales a partir del oro de legajo: prueba (50) y plata-alta (75), y protegidos."""

from pathlib import Path

from enrel.datos.documento import cargar_jsonl, guardar_jsonl
from enrel.datos.validar import comprobar_fugas

PRUEBA_TXT = Path("datos-anteriores/entrenamiento/prueba.txt")
ORO = Path("datos/anotado/legajo-oro.jsonl")
SALIDA = Path("datos/conjuntos")


def main() -> None:
    prueba_ids = {
        f"wp:{linea.strip()}"
        for linea in PRUEBA_TXT.read_text().splitlines()
        if linea.strip() and not linea.startswith("#")
    }
    assert len(prueba_ids) == 50
    docs = cargar_jsonl(ORO)
    prueba = [d for d in docs if d.doc_id in prueba_ids]
    resto = [d for d in docs if d.doc_id not in prueba_ids]
    for d in resto:
        d.fuente = "plata-alta"
    assert len(prueba) == 50, len(prueba)
    guardar_jsonl(prueba, SALIDA / "prueba.jsonl")
    guardar_jsonl(resto, SALIDA / "plata_alta.jsonl")
    (SALIDA / "protegidos.txt").write_text("\n".join(sorted(prueba_ids)) + "\n", encoding="utf-8")
    fugas = comprobar_fugas({"prueba": prueba, "plata_alta": resto})
    if fugas:
        raise SystemExit(fugas)
    print("sin fugas")
    print(f"prueba {len(prueba)} · plata-alta {len(resto)} · protegidos {len(prueba_ids)}")


if __name__ == "__main__":
    main()
