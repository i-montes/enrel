from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema.tipos import RELACIONES, TIPOS


def test_guia_completa():
    tipos, relaciones, convenciones = cargar_guia(Path("docs/guia-anotacion.md"))
    assert set(tipos) == set(TIPOS)
    # La guía incluye vinculo_sin_tipo como relación de reserva además de las 19 de RELACIONES.
    assert set(RELACIONES) <= set(relaciones)
    assert len(convenciones) >= 6
    for r in relaciones.values():
        assert len(r.ejemplos) >= 3 and len(r.no_es) >= 2 and r.definicion, r.nombre
    # ocupa_cargo tiene un atributo de modalidad (titular/aspirante), ortogonal a la vigencia,
    # que es un eje propio de toda relación (enrel/esquema/tipos.py, enrel/datos/documento.py).
    assert set(relaciones["ocupa_cargo"].atributos) == {"titular", "aspirante"}
    assert set(relaciones["familiar_de"].atributos) == {"conyuge", "hijo_de", "hermano", "otro"}
    # estudio_en: sin atributos; su separación de trabaja_en y miembro_de queda explícita
    # en las confusiones de las tres entradas.
    assert relaciones["estudio_en"].atributos == {}
    assert any("trabaja_en" in c for c in relaciones["estudio_en"].confusiones)
    assert any("miembro_de" in c for c in relaciones["estudio_en"].confusiones)
    assert any("estudio_en" in c for c in relaciones["trabaja_en"].confusiones)
    assert any("estudio_en" in c for c in relaciones["miembro_de"].confusiones)
