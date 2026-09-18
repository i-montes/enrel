import sqlite3
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
    # «ocupa el cargo» siempre es `titular` (modalidad), con la vigencia de `cuando` tal cual.
    assert ("Álvaro Uribe", "ocupa_cargo:titular", "presidente de Colombia") in finas
    assert ("Tomás Uribe", "familiar_de:hijo_de", "Álvaro Uribe") in finas  # invertida
    assert ("Álvaro Uribe", "fundo", "Centro Democrático") in finas
    assert len(d.relaciones) == 3
    assert d.origen["predicados_originales"]["padre o madre de"] == 1
    ocupa = next(r for r in d.relaciones if r.relacion == "ocupa_cargo")
    assert ocupa.vigencia == "pasada"  # SPEC lo anota «pasada» («ocupa el cargo», cuando="pasada")
    assert d.origen["vigencias"] == {"pasada": 1, "vigente": 2}


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


def test_apariciones_no_cruza_limites_de_palabra():
    # «Cali» no debe encajar dentro de «California»; solo la aparición real cuenta.
    assert dl._apariciones("En California y en Cali.", "Cali") == [(19, 23)]
    # «Fiscal» aparece pegado dentro de «Fiscalía» (se descarta por el límite de palabra) y
    # la búsqueda de respaldo, que compara palabras completas conservando mayúsculas, tampoco
    # debe confundirlo con el sustantivo común «fiscal».
    assert dl._apariciones("La Fiscalía y el fiscal.", "Fiscal") == []
    # Aside: sin el anclaje al primer carácter de la mención, «ana» encajaría dentro de «banana».
    assert dl._apariciones("banana", "ana") == []


def test_apariciones_no_se_solapan():
    assert dl._apariciones("tata tata", "tata") == [(0, 4), (5, 9)]
    # Solapada consigo misma: tras la primera coincidencia se avanza al final de la mención,
    # no rebusca dentro de ella, así que no queda ningún resto en el que encajar de nuevo.
    assert dl._apariciones("tatata", "tata") == []


def _esquema_legajo(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE anotaciones (
            lote_id INTEGER NOT NULL, wp_id INTEGER NOT NULL, mid TEXT NOT NULL, pi INTEGER NOT NULL,
            ini INTEGER NOT NULL, fin INTEGER NOT NULL, texto TEXT NOT NULL, tipo TEXT NOT NULL,
            designa INTEGER NOT NULL DEFAULT 0, auto INTEGER NOT NULL DEFAULT 0, grupo TEXT,
            PRIMARY KEY (lote_id, wp_id, mid)
        );
        CREATE TABLE relaciones (
            lote_id INTEGER NOT NULL, wp_id INTEGER NOT NULL, rid TEXT NOT NULL, a_mid TEXT NOT NULL,
            b_mid TEXT NOT NULL, predicado TEXT NOT NULL, cuando TEXT NOT NULL DEFAULT 'vigente',
            PRIMARY KEY (lote_id, wp_id, rid)
        );
        CREATE TABLE resoluciones (
            lote_id INTEGER NOT NULL, clave TEXT NOT NULL, a_nombre TEXT NOT NULL, b_nombre TEXT NOT NULL,
            tipo TEXT NOT NULL, decision TEXT NOT NULL, confianza REAL NOT NULL DEFAULT 0,
            fuente TEXT NOT NULL DEFAULT 'persona', motivo TEXT,
            PRIMARY KEY (lote_id, clave)
        );
    """)


PARRAFO_TRES_PERSONAS = "Ana Pérez, Beto Ruiz y Caro Díaz llegaron juntos."
ART_TRES_PERSONAS = Articulo(
    wp_id=42,
    titulo="",
    texto_plano=PARRAFO_TRES_PERSONAS,
    palabras=8,
    url="https://www.lasillavacia.com/silla-nacional/x/",
    fecha="2020-01-01",
    seccion="silla-nacional",
)


def _insertar_anotacion(con, lote_id, wp_id, mid, texto, ini, grupo=None):
    con.execute(
        "INSERT INTO anotaciones (lote_id, wp_id, mid, pi, ini, fin, texto, tipo, designa, grupo)"
        " VALUES (?, ?, ?, 0, ?, ?, ?, 'persona', 0, ?)",
        (lote_id, wp_id, mid, ini, ini + len(texto), texto, grupo),
    )


def test_fusionar_cierre_transitivo_por_resoluciones():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    _esquema_legajo(con)
    lote_id = 1
    _insertar_anotacion(con, lote_id, ART_TRES_PERSONAS.wp_id, "m1", "Ana Pérez", 0)
    _insertar_anotacion(con, lote_id, ART_TRES_PERSONAS.wp_id, "m2", "Beto Ruiz", 11)
    _insertar_anotacion(con, lote_id, ART_TRES_PERSONAS.wp_id, "m3", "Caro Díaz", 23)
    # decision='misma' encadenada: (Ana=Beto) y (Beto=Caro) deben cerrar en un único grupo,
    # aunque nunca se compare directamente a Ana con Caro.
    con.executemany(
        "INSERT INTO resoluciones (lote_id, clave, a_nombre, b_nombre, tipo, decision)"
        " VALUES (?, ?, ?, ?, 'persona', 'misma')",
        [(lote_id, "k1", "Ana Pérez", "Beto Ruiz"), (lote_id, "k2", "Beto Ruiz", "Caro Díaz")],
    )
    con.commit()

    d = dl.documento_desde_sqlite(con, lote_id, ART_TRES_PERSONAS)
    assert validar_documento(d) == []
    grupos = {m.grupo for m in d.menciones}
    assert len(grupos) == 1  # Ana, Beto y Caro terminan en el mismo grupo


def test_fusionar_tolera_grupo_nulo_y_resoluciones_vacias():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    _esquema_legajo(con)
    lote_id = 2
    # `grupo` NULL (columna no forzada) y ninguna fila en `resoluciones`: no debe romper.
    _insertar_anotacion(con, lote_id, ART_TRES_PERSONAS.wp_id, "m1", "Ana Pérez", 0)
    _insertar_anotacion(con, lote_id, ART_TRES_PERSONAS.wp_id, "m2", "Beto Ruiz", 11)
    con.commit()

    d = dl.documento_desde_sqlite(con, lote_id, ART_TRES_PERSONAS)
    assert validar_documento(d) == []
    assert len(d.menciones) == 2
    assert len({m.grupo for m in d.menciones}) == 2  # sin resoluciones, cada una en su grupo


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
