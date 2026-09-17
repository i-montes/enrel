import sqlite3
from pathlib import Path

import pytest

from enrel.corpus import legajo_db as db


@pytest.fixture
def base(tmp_path: Path) -> Path:
    ruta = tmp_path / "legajo.sqlite"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE connections (id INTEGER PRIMARY KEY);
        CREATE TABLE articles (connection_id INTEGER, wp_id INTEGER, html_raw TEXT, text_plain TEXT, word_count INTEGER,
                               fetched_at TEXT, PRIMARY KEY (connection_id, wp_id));
        CREATE TABLE census (connection_id INTEGER, wp_id INTEGER, date TEXT, date_valid INTEGER, slug TEXT, link TEXT,
                             title TEXT, title_key TEXT, author INTEGER, terms_json TEXT,
                             PRIMARY KEY (connection_id, wp_id));
        INSERT INTO connections VALUES (1);
        INSERT INTO articles VALUES (1, 10, NULL, 'Primer párrafo.\n\nSegundo párrafo con Petro.', 6, '2026-01-01');
        INSERT INTO census VALUES (1, 10, '2023-05-01T10:00:00', 1, 'x',
                                  'https://www.lasillavacia.com/silla-nacional/x/',
                                  'Petro &amp; Cía', 'petro', 1, '{}');
        INSERT INTO articles VALUES (1, 11, NULL, 'a', 1, '2026-01-01');
        INSERT INTO census VALUES (1, 11, '2010-01-01', 1, 'y', 'https://www.lasillavacia.com/en-vivo/y/',
                                  NULL, 'y', 1, '{}');
    """)
    con.commit()
    con.close()
    return ruta


def test_seccion_de():
    assert db.seccion_de("https://www.lasillavacia.com/quien-es-quien/juan-perez/") == "quien-es-quien"
    assert db.seccion_de("https://otra.com/x") == ""


def test_articulo_y_texto(base):
    con = db.conectar(base)
    a = db.articulo(con, 10)
    assert a.titulo == "Petro & Cía"
    assert a.seccion == "silla-nacional"
    assert a.fecha == "2023-05-01"
    assert a.texto == "Petro & Cía\n\nPrimer párrafo.\n\nSegundo párrafo con Petro."
    assert a.desplazamiento_cuerpo == len("Petro & Cía") + 2
    assert db.articulo(con, 99) is None


def test_articulo_sin_titulo(base):
    con = db.conectar(base)
    a = db.articulo(con, 11)
    assert a.titulo == "" and a.desplazamiento_cuerpo == 0 and a.texto == "a"


def test_parrafos_conserva_indices():
    ps = db.parrafos("Uno.\n\n\n\nTres.")
    assert ps == [(0, "Uno."), (6, ""), (8, "Tres.")]


def test_transcripcion():
    largo = "\n\n".join(["Pregunta corta"] * 50)
    assert db.es_transcripcion(largo)
    normal = "Un párrafo normal de bastantes palabras que no parece una transcripción.\n\nOtro igual de normal."
    assert not db.es_transcripcion(normal)


def test_iterar(base):
    con = db.conectar(base)
    assert [a.wp_id for a in db.iterar_articulos(con, minimo_palabras=2)] == [10]
