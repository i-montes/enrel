from enrel.corpus.disparadores import DISPARADORES, relaciones_disparadas
from enrel.esquema.tipos import RELACIONES


def test_hay_un_disparador_por_relacion():
    assert set(DISPARADORES) == set(RELACIONES)


def test_relaciones_disparadas():
    t = "El exministro fue imputado por la Fiscalía; su esposa es accionista de la empresa con sede en Cali."
    d = relaciones_disparadas(t)
    assert {"ocupa_cargo", "investigado_por", "familiar_de", "propietario_de", "ubicado_en"} <= d
    assert "sucedio_a" not in d
