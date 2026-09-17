from pathlib import Path

import pytest

from enrel.cli import main
from tests.test_muestrear import _corpus


def test_excluir_inexistente_aborta(tmp_path: Path):
    corpus = _corpus(tmp_path)
    salida = tmp_path / "seleccion.jsonl"
    with pytest.raises(SystemExit):
        main(
            [
                "muestrear",
                "--corpus",
                str(corpus),
                "--excluir",
                str(tmp_path / "no-existe.txt"),
                "--salida",
                str(salida),
                "--cuota-relacion",
                "5",
                "--perfiles",
                "5",
                "--aleatorios",
                "10",
                "--humo",
                "2",
            ]
        )
    assert not salida.exists()


def test_sin_excluir_avisa_y_funciona(tmp_path: Path, capsys):
    corpus = _corpus(tmp_path)
    salida = tmp_path / "seleccion.jsonl"
    codigo = main(
        [
            "muestrear",
            "--corpus",
            str(corpus),
            "--salida",
            str(salida),
            "--cuota-relacion",
            "5",
            "--perfiles",
            "5",
            "--aleatorios",
            "10",
            "--humo",
            "2",
        ]
    )
    assert (codigo or 0) == 0
    assert salida.exists()
    assert "aviso" in capsys.readouterr().out
