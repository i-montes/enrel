from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema.tipos import RELACIONES, TIPOS


def test_guia_completa():
    tipos, relaciones, convenciones = cargar_guia(Path("docs/guia-anotacion.md"))
    assert set(tipos) == set(TIPOS)
    # La guía incluye vinculo_sin_tipo como relación de reserva además de las 17 de RELACIONES.
    assert set(RELACIONES) <= set(relaciones)
    assert len(convenciones) >= 6
    for r in relaciones.values():
        assert len(r.ejemplos) >= 3 and len(r.no_es) >= 2 and r.definicion, r.nombre
    # ocupa_cargo ya no tiene atributos: actual/anterior/aspirante pasaron al eje `vigencia`,
    # propio de toda relación (enrel/esquema/tipos.py, enrel/datos/documento.py).
    assert set(relaciones["ocupa_cargo"].atributos) == set()
    assert set(relaciones["familiar_de"].atributos) == {"conyuge", "hijo_de", "hermano", "otro"}
