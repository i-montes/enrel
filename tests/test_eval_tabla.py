from enrel.datos.documento import Relacion
from enrel.evaluacion.bootstrap import intervalo
from enrel.evaluacion.emparejar import PRF
from enrel.evaluacion.relaciones import evaluar_relaciones
from enrel.evaluacion.tabla import fila, tabla_markdown
from tests.test_eval_relaciones import ORO, pred


def test_fila_insuficiente():
    f = fila("fundo", PRF(tp=2, fp=0, fn=1))
    assert f["n"] == 3 and f["f1"] == "insuficiente"
    f2 = fila("ocupa_cargo", PRF(tp=8, fp=2, fn=2), ic=(0.6, 0.9))
    assert f2["f1"] == "0.80" and f2["ic"] == "[0.60, 0.90]"


def test_tabla_markdown():
    md = tabla_markdown([fila("x", PRF(tp=10, fp=0, fn=0))], "Prueba")
    assert md.startswith("### Prueba") and "| x | 10 | 1.00 | 1.00 | 1.00 |" in md


def test_intervalo_cubre_el_valor():
    p = pred(
        [
            Relacion("p1", "p2", "nombro_a"),
            Relacion("p2", "p3", "ocupa_cargo", "actual"),
            Relacion("p1", "p2", "socio_de"),
        ]
    )

    def f(o, q):
        return evaluar_relaciones(o, q, "gruesa")["__micro__"].f1

    bajo, alto = intervalo([ORO] * 5, [p] * 5, f, n=50)
    assert bajo <= 1.0 <= alto
