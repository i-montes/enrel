import sqlite3
from pathlib import Path

import pytest


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
