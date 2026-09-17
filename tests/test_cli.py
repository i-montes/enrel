from pathlib import Path

from enrel.cli import main
from enrel.datos.documento import Relacion, guardar_jsonl
from tests.test_eval_relaciones import ORO, pred


def test_evaluar_cli(tmp_path: Path, capsys):
    o, p = tmp_path / "oro.jsonl", tmp_path / "pred.jsonl"
    guardar_jsonl([ORO], o)
    guardar_jsonl([pred([Relacion("p1", "p2", "nombro_a")])], p)
    salida = tmp_path / "informe.md"
    assert main(["evaluar", "--oro", str(o), "--pred", str(p), "--salida", str(salida), "--sin-intervalos"]) == 0
    texto = salida.read_text(encoding="utf-8")
    assert "Relaciones gruesas, RE+" in texto and "nombro_a" in texto


def test_ayuda(capsys):
    assert main([]) == 0
    assert "evaluar" in capsys.readouterr().out
