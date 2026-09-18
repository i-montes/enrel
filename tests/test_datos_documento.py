from pathlib import Path

from enrel.datos import normalizar as n
from enrel.datos.documento import Documento, Grupo, Mencion, Relacion, cargar_jsonl, guardar_jsonl
from enrel.datos.validar import comprobar_fugas, validar_documento


def doc_ejemplo() -> Documento:
    texto = n.nfc("Gustavo Petro\n\nEl presidente Gustavo Petro nombró a Luis Carlos Reyes como ministro de Comercio.")
    m = [
        Mencion("m1", 0, 13, "Gustavo Petro", "persona", "e1"),
        Mencion("m2", 29, 42, "Gustavo Petro", "persona", "e1"),
        Mencion("m3", 52, 69, "Luis Carlos Reyes", "persona", "e2"),
        Mencion("m4", 75, 95, "ministro de Comercio", "cargo", "e3"),
        Mencion("m5", 87, 95, "Comercio", "organizacion", "e4"),
    ]
    g = [
        Grupo("e1", "persona", "Gustavo Petro"),
        Grupo("e2", "persona", "Luis Carlos Reyes"),
        Grupo("e3", "cargo", "ministro de Comercio"),
        Grupo("e4", "organizacion", "Comercio"),
    ]
    r = [
        Relacion("e1", "e2", "nombro_a"),
        Relacion("e2", "e3", "ocupa_cargo", vigencia="pasada", evidencia=(15, 96)),
    ]
    return Documento(
        "wp:1",
        texto,
        m,
        g,
        r,
        url="https://x",
        fecha="2023-01-01",
        seccion="silla-nacional",
        titulo="Gustavo Petro",
        fuente="oro",
    )


def test_plegar():
    assert n.plegar("  Álvaro  URIBE “Vélez” ") == 'alvaro uribe "velez"'
    assert n.palabras("Luis-Carlos, 2019.") == [(0, 11, "Luis-Carlos"), (11, 12, ","), (13, 17, "2019"), (17, 18, ".")]


def test_documento_valido_y_offsets():
    d = doc_ejemplo()
    for m in d.menciones:
        assert d.texto[m.ini : m.fin] == m.texto
    assert validar_documento(d) == []
    assert [m.id for m in d.menciones_de("e1")] == ["m1", "m2"]
    assert d.clase_fina_de(d.relaciones[1]) == "ocupa_cargo"  # ocupa_cargo ya no tiene atributos
    assert d.relaciones[0].vigencia == "vigente"  # por defecto
    assert d.relaciones[1].vigencia == "pasada"


def test_ida_y_vuelta_jsonl(tmp_path: Path):
    d = doc_ejemplo()
    ruta = tmp_path / "x.jsonl"
    assert guardar_jsonl([d], ruta) == 1
    [d2] = cargar_jsonl(ruta)
    assert d2 == d
    assert d2.relaciones[1].evidencia == (15, 96)
    assert d2.relaciones[1].vigencia == "pasada"


def test_desde_dict_sin_vigencia_es_compatible():
    # Ficheros escritos antes de que `vigencia` existiera no traen la clave: deben leerse
    # como «vigente», no romper.
    d = doc_ejemplo()
    bruto = d.a_dict()
    for r in bruto["relaciones"]:
        del r["vigencia"]
    d2 = Documento.desde_dict(bruto)
    assert all(r.vigencia == "vigente" for r in d2.relaciones)


def test_validar_detecta_errores():
    d = doc_ejemplo()
    d.menciones[0].fin = 12
    d.relaciones.append(Relacion("e1", "e1", "socio_de"))
    d.relaciones.append(Relacion("e1", "e4", "ocupa_cargo"))
    d.relaciones.append(Relacion("e1", "e2", "nombro_a"))
    errores = validar_documento(d)
    assert any("m1" in e and "texto" in e for e in errores)
    assert any("autorrelación" in e for e in errores)
    assert any("no admite" in e for e in errores)
    assert any("duplicada" in e for e in errores)


def test_validar_vigencia_desconocida():
    d = doc_ejemplo()
    d.relaciones.append(Relacion("e1", "e4", "trabaja_en", vigencia="algun-dia"))
    assert any("vigencia desconocida" in e for e in validar_documento(d))


def test_validar_simetrica_espejo():
    d = doc_ejemplo()
    d.relaciones = [Relacion("e1", "e2", "socio_de"), Relacion("e2", "e1", "socio_de")]
    assert any("espejo" in e for e in validar_documento(d))


def test_fugas():
    a, b = doc_ejemplo(), doc_ejemplo()
    b.doc_id = "wp:2"
    assert comprobar_fugas({"prueba": [a], "plata": [b]}) == []
    assert comprobar_fugas({"prueba": [a], "plata": [a, b]}) == ["wp:1 está en «prueba» y en «plata»"]
