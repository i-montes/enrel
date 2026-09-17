from pathlib import Path

import pytest

from enrel.anotacion import desde_legajo as dl
from enrel.corpus.legajo_db import Articulo
from enrel.datos.validar import validar_documento

CUERPO = (
    "Álvaro Uribe fue presidente de Colombia.\n\n"
    "Tomás Uribe, hijo de Álvaro Uribe, es empresario. Álvaro Uribe fundó el Centro Democrático."
)
ART = Articulo(
    wp_id=7,
    titulo="Los Uribe",
    texto_plano=CUERPO,
    palabras=20,
    url="https://www.lasillavacia.com/quien-es-quien/uribe/",
    fecha="2020-01-01",
    seccion="quien-es-quien",
)

SPEC = {
    "wp_id": 7,
    "parrafos": {
        "0": {
            "E": [["Álvaro Uribe", "persona"], ["presidente de Colombia", "cargo*"], ["Colombia", "lugar"]],
            "R": [["Álvaro Uribe", "ocupa el cargo", "presidente de Colombia", "pasada"]],
        },
        "1": {
            "E": [["Tomás Uribe", "persona"], ["Álvaro Uribe", "persona"], ["Centro Democrático", "organizacion"]],
            "R": [["Álvaro Uribe", "padre o madre de", "Tomás Uribe"], ["Álvaro Uribe", "fundó", "Centro Democrático"]],
        },
    },
}


def test_oro_json_offsets_y_todas_las_apariciones():
    d = dl.documento_desde_oro_json(SPEC, ART)
    assert validar_documento(d) == []
    assert d.texto.startswith("Los Uribe\n\n")
    uribes = [m for m in d.menciones if m.texto == "Álvaro Uribe"]
    assert len(uribes) == 3  # una en el párrafo 0, dos en el 1
    assert len({m.grupo for m in uribes}) == 1
    for m in d.menciones:
        assert d.texto[m.ini : m.fin] == m.texto
    assert "presidente de Colombia" in [m.texto for m in d.menciones]
    assert len(d.origen["designa"]) == 1


def test_oro_json_mapeo_e_inversion():
    d = dl.documento_desde_oro_json(SPEC, ART)
    finas = {(d.grupo_de(r.cabeza).canonico, d.clase_fina_de(r), d.grupo_de(r.cola).canonico) for r in d.relaciones}
    assert ("Álvaro Uribe", "ocupa_cargo:anterior", "presidente de Colombia") in finas
    assert ("Tomás Uribe", "familiar_de:hijo_de", "Álvaro Uribe") in finas  # invertida
    assert ("Álvaro Uribe", "fundo", "Centro Democrático") in finas
    assert len(d.relaciones) == 3
    assert d.origen["predicados_originales"]["padre o madre de"] == 1


def test_plata_legajo():
    filas = [
        {
            "wp_id": 7,
            "pi": 1,
            "texto": ART.texto_plano.split("\n\n")[1],
            "entidades": [
                {"ini": 0, "fin": 11, "tipo": "persona", "texto": "Tomás Uribe"},
                {"ini": 21, "fin": 33, "tipo": "persona", "texto": "Álvaro Uribe"},
            ],
            "relaciones": [{"a": 0, "b": 1, "predicado": "hijo de", "cuando": "vigente"}],
        }
    ]
    d = dl.documento_desde_plata_legajo(filas, ART)
    assert validar_documento(d) == []
    assert d.fuente == "plata-legajo"
    assert d.clase_fina_de(d.relaciones[0]) == "familiar_de:hijo_de"


@pytest.mark.skipif(not Path("datos-anteriores/entrenamiento/oro").exists(), reason="sin datos reales")
def test_oro_real_completo():
    from enrel.corpus import legajo_db as db

    specs = dl.leer_oro_json(Path("datos-anteriores/entrenamiento/oro"))
    assert len(specs) == 125
    con = db.conectar(db.ruta_db())
    errores, docs, no_loc = 0, 0, 0
    for wp, spec in specs.items():
        art = db.articulo(con, wp)
        assert art is not None, wp
        d = dl.documento_desde_oro_json(spec, art)
        docs += 1
        no_loc += d.origen.get("no_localizadas", 0)
        errores += len(validar_documento(d))
    assert docs == 125 and errores == 0
    # Las menciones que no se pudieron localizar en el texto local deben ser pocas (texto editado en WordPress).
    assert no_loc < 60
