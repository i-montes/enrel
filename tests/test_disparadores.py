from enrel.corpus.disparadores import DISPARADORES, relaciones_disparadas
from enrel.esquema.tipos import RELACIONES


def test_hay_un_disparador_por_relacion():
    assert set(DISPARADORES) == set(RELACIONES)


def test_relaciones_disparadas():
    t = "El exministro fue imputado por la Fiscalía; su esposa es accionista de la empresa con sede en Cali."
    d = relaciones_disparadas(t)
    assert {"ocupa_cargo", "investigado_por", "familiar_de", "propietario_de", "ubicado_en"} <= d
    assert "sucedio_a" not in d


def test_relaciones_disparadas_impulsa_norma():
    t = "El senador radicó el proyecto y logró sacar adelante la reforma tributaria."
    d = relaciones_disparadas(t)
    assert "impulsa_norma" in d
    assert "apoya_a" not in d


def test_relaciones_disparadas_estudio_en():
    t = "Estudió Economía en la Universidad de los Andes y tiene un Ph. D. de New York University."
    d = relaciones_disparadas(t)
    assert "estudio_en" in d
    assert "trabaja_en" not in d
