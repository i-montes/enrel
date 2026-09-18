from enrel.datos.documento import Relacion
from enrel.evaluacion.bootstrap import intervalo
from enrel.evaluacion.emparejar import PRF
from enrel.evaluacion.informe import informe_completo
from enrel.evaluacion.relaciones import evaluar_relaciones
from enrel.evaluacion.tabla import fila, tabla_markdown
from tests.test_eval_relaciones import ORO, pred


def test_fila_insuficiente():
    f = fila("fundo", PRF(tp=2, fp=0, fn=1))
    assert f["n"] == 3 and f["f1"] == "insuficiente"
    f2 = fila("ocupa_cargo", PRF(tp=8, fp=2, fn=2), ic=(0.6, 0.9))
    assert f2["f1"] == "0.80" and f2["ic"] == "[0.60, 0.90]"


def test_fila_columnas_en_blanco():
    # «macro» solo publica F1; n, P y R quedan en blanco.
    f = fila("macro", PRF(tp=5, fp=1, fn=1), minimo_n=0, columnas=("f1",))
    assert f["n"] == "" and f["p"] == "" and f["r"] == "" and f["f1"] != ""
    # «direccion» publica n y R (la tasa de aciertos); P y F1 quedan en blanco.
    f2 = fila("direccion", PRF(tp=9, fp=0, fn=1), minimo_n=0, columnas=("n", "r"))
    assert f2["n"] != "" and f2["r"] != "" and f2["p"] == "" and f2["f1"] == ""


def test_tabla_markdown():
    md = tabla_markdown([fila("x", PRF(tp=10, fp=0, fn=0))], "Prueba")
    assert md.startswith("### Prueba") and "| x | 10 | 1.00 | 1.00 | 1.00 |" in md


def test_informe_macro_y_direccion_en_blanco_y_micro_doble():
    p = pred(
        [
            Relacion("p1", "p2", "nombro_a"),
            Relacion("p2", "p3", "ocupa_cargo"),
            Relacion("p1", "p2", "socio_de"),
        ]
    )
    md = informe_completo([ORO], [p], nombre_modelo="prueba", con_intervalos=False)
    tabla_re = md.split("### Relaciones gruesas, RE\n")[1].split("###")[0]
    lineas = {ln.split("|")[1].strip(): ln for ln in tabla_re.splitlines() if ln.startswith("|")}
    celdas_macro = [c.strip() for c in lineas["macro"].split("|")]
    # nombre, n, P, R, F1, IC — n/P/R en blanco, F1 no.
    assert celdas_macro[2] == "" and celdas_macro[3] == "" and celdas_macro[4] == "" and celdas_macro[5] != ""
    fila_direccion = next(v for k, v in lineas.items() if k.startswith("direccion"))
    celdas_direccion = [c.strip() for c in fila_direccion.split("|")]
    assert celdas_direccion[2] != "" and celdas_direccion[4] != ""  # n y R
    assert celdas_direccion[3] == "" and celdas_direccion[5] == ""  # P y F1 en blanco
    # «vigencia» recibe el mismo tratamiento que «direccion»: solo n y R.
    fila_vigencia = next(v for k, v in lineas.items() if k.startswith("vigencia"))
    celdas_vigencia = [c.strip() for c in fila_vigencia.split("|")]
    assert celdas_vigencia[2] != "" and celdas_vigencia[4] != ""  # n y R
    assert celdas_vigencia[3] == "" and celdas_vigencia[5] == ""  # P y F1 en blanco
    assert "micro sin reserva" in lineas
    assert list(lineas).index("micro") < list(lineas).index("micro sin reserva")


def test_intervalo_cubre_el_valor():
    p = pred(
        [
            Relacion("p1", "p2", "nombro_a"),
            Relacion("p2", "p3", "ocupa_cargo"),
            Relacion("p1", "p2", "socio_de"),
        ]
    )

    def f(o, q):
        return evaluar_relaciones(o, q, "gruesa")["__micro__"].f1

    bajo, alto = intervalo([ORO] * 5, [p] * 5, f, n=50)
    assert bajo <= 1.0 <= alto
