from pathlib import Path

from scripts.generar_esquema_md import generar


def test_esquema_md_al_dia():
    assert Path("docs/esquema.md").read_text(encoding="utf-8") == generar()
