"""Genera docs/esquema.md desde el código y la guía, para que la documentación no se separe del esquema."""

from pathlib import Path

from enrel.anotacion.guia import cargar_guia
from enrel.esquema import tipos as t
from enrel.esquema.mapeo_legajo import PREDICADOS_NUEVOS, PREDICADOS_VIEJOS, mapear_predicado

EQUIVALENCIAS = {
    "ocupa_cargo": ("Occupancy", "P39"),
    "nombro_a": ("—", "P748"),
    "sucedio_a": ("Succession", "P1365"),
    "miembro_de": ("Membership", "P102, P463"),
    "trabaja_en": ("Employment", "P108"),
    "dirige": ("Directorship", "P1037, P169, P488"),
    "fundo": ("—", "P112"),
    "propietario_de": ("Ownership", "P127, P1830"),
    "socio_de": ("Associate", "P1327"),
    "parte_de": ("—", "P749, P355"),
    "familiar_de": ("Family", "P26, P40, P22, P25, P3373, P1038"),
    "financia_a": ("Payment", "P859"),
    "contrato_a": ("ContractAward", "—"),
    "investigado_por": ("CourtCaseParty", "P1399"),
    "ubicado_en": ("—", "P159, P551, P131"),
    "apoya_a": ("—", "—"),
    "impulsa_norma": ("—", "—"),
    "se_opone_a": ("—", "—"),
}
_EJEMPLO_TIPOS = {"persona": ("persona", "cargo"), "organizacion": ("organizacion", "organizacion")}


def generar() -> str:
    tipos, relaciones, _ = cargar_guia()
    out = [
        "# Esquema de enrel",
        "",
        "Generado por `scripts/generar_esquema_md.py`. No editar a mano.",
        "",
        "## Tipos de entidad",
        "",
        "| Tipo | Se marca | No se marca |",
        "|---|---|---|",
    ]
    for nombre in t.TIPOS:
        d = tipos[nombre]
        out.append(f"| {nombre} | {d.se_marca} | {d.no_se_marca} |")
    out += [
        "",
        "## Relaciones",
        "",
        "| Relación | De → a | Simétrica | Atributos | Familia | FollowTheMoney | Wikidata |",
        "|---|---|---|---|---|---|---|",
    ]
    for nombre, d in t.RELACIONES.items():
        ftm, wd = EQUIVALENCIAS[nombre]
        out.append(
            f"| {nombre} | {', '.join(sorted(d.desde))} → {', '.join(sorted(d.hasta))} | "
            f"{'sí' if d.simetrica else 'no'} | {', '.join(d.atributos) or '—'} | {d.familia} | {ftm} | {wd} |"
        )
    out.append(f"| {t.SIN_TIPO} | cualquiera ↔ cualquiera | sí | — | — | UnknownLink | — |")
    out += [
        "",
        "## Mapeo desde legajo",
        "",
        "Para cada predicado, el destino con los tipos de extremo más habituales; los demás pares caen en "
        "vinculo_sin_tipo si la relación no los admite.",
        "",
        "| Predicado de legajo | Vocabulario | persona→persona | persona→organizacion | persona→cargo | "
        "organizacion→organizacion |",
        "|---|---|---|---|---|---|",
    ]
    pares = [
        ("persona", "persona"),
        ("persona", "organizacion"),
        ("persona", "cargo"),
        ("organizacion", "organizacion"),
    ]
    for pred in sorted(PREDICADOS_VIEJOS | PREDICADOS_NUEVOS):
        voc = (
            "viejo y nuevo"
            if pred in PREDICADOS_VIEJOS and pred in PREDICADOS_NUEVOS
            else ("viejo" if pred in PREDICADOS_VIEJOS else "nuevo")
        )
        celdas = []
        for a, b in pares:
            m = mapear_predicado(pred, a, b)
            celdas.append(t.clase_fina(m.relacion, m.atributo) + (" (invertida)" if m.invertir else ""))
        out.append(f"| {pred} | {voc} | " + " | ".join(celdas) + " |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    Path("docs/esquema.md").write_text(generar(), encoding="utf-8")
    print("docs/esquema.md")
