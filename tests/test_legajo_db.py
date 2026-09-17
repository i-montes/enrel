from enrel.corpus import legajo_db as db


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
