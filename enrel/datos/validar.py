"""Comprobaciones que abortan una exportación: offsets, tipos, relaciones y fugas entre conjuntos."""

from enrel.datos.documento import Documento
from enrel.datos.normalizar import nfc
from enrel.esquema.tipos import RELACIONES_Y_SIN_TIPO, TIPOS, VIGENCIAS, admite, clase_fina, es_simetrica


def validar_documento(doc: Documento) -> list[str]:
    errores: list[str] = []
    if doc.texto != nfc(doc.texto):
        errores.append(f"{doc.doc_id}: el texto no está en NFC")
    grupos = {g.id: g for g in doc.grupos}
    if len(grupos) != len(doc.grupos):
        errores.append(f"{doc.doc_id}: ids de grupo repetidos")
    vistos: set[str] = set()
    for m in doc.menciones:
        if m.id in vistos:
            errores.append(f"{doc.doc_id}: mención {m.id} repetida")
        vistos.add(m.id)
        if not (0 <= m.ini < m.fin <= len(doc.texto)):
            errores.append(f"{doc.doc_id}: mención {m.id} fuera del texto ({m.ini}, {m.fin})")
        elif doc.texto[m.ini : m.fin] != m.texto:
            errores.append(
                f"{doc.doc_id}: mención {m.id} no coincide con el texto: {doc.texto[m.ini : m.fin]!r} ≠ {m.texto!r}"
            )
        if m.tipo not in TIPOS:
            errores.append(f"{doc.doc_id}: mención {m.id} con tipo desconocido {m.tipo!r}")
        g = grupos.get(m.grupo)
        if g is None:
            errores.append(f"{doc.doc_id}: mención {m.id} apunta a un grupo inexistente {m.grupo!r}")
        elif g.tipo != m.tipo:
            errores.append(f"{doc.doc_id}: mención {m.id} de tipo {m.tipo} en grupo {g.id} de tipo {g.tipo}")
    claves: set[tuple] = set()
    for r in doc.relaciones:
        if r.relacion not in RELACIONES_Y_SIN_TIPO:
            errores.append(f"{doc.doc_id}: relación desconocida {r.relacion!r}")
            continue
        try:
            fina = clase_fina(r.relacion, r.atributo)
        except ValueError as e:
            errores.append(f"{doc.doc_id}: {e}")
            continue
        if r.vigencia not in VIGENCIAS:
            errores.append(f"{doc.doc_id}: vigencia desconocida {r.vigencia!r} en {fina}")
        if r.cabeza == r.cola:
            errores.append(f"{doc.doc_id}: autorrelación {fina} sobre {r.cabeza}")
            continue
        gc, gl = grupos.get(r.cabeza), grupos.get(r.cola)
        if gc is None or gl is None:
            errores.append(f"{doc.doc_id}: relación {fina} con extremo inexistente ({r.cabeza}, {r.cola})")
            continue
        if not admite(r.relacion, gc.tipo, gl.tipo):
            errores.append(f"{doc.doc_id}: {r.relacion} no admite {gc.tipo} → {gl.tipo}")
        clave = (r.cabeza, r.cola, fina)
        if clave in claves:
            errores.append(f"{doc.doc_id}: relación duplicada {clave}")
        if es_simetrica(r.relacion, r.atributo) and (r.cola, r.cabeza, fina) in claves:
            errores.append(f"{doc.doc_id}: relación simétrica con su espejo {clave}")
        claves.add(clave)
        if r.evidencia is not None and not (0 <= r.evidencia[0] < r.evidencia[1] <= len(doc.texto)):
            errores.append(f"{doc.doc_id}: evidencia fuera del texto en {fina}")
    return errores


def comprobar_fugas(
    conjuntos: dict[str, list[Documento]], protegidos: tuple[str, ...] = ("prueba", "prueba_dirigida", "desarrollo")
) -> list[str]:
    ids = {nombre: {d.doc_id for d in docs} for nombre, docs in conjuntos.items()}
    errores = []
    for prot in protegidos:
        for otro in conjuntos:
            if otro == prot or prot not in ids:
                continue
            for doc_id in sorted(ids[prot] & ids[otro]):
                errores.append(f"{doc_id} está en «{prot}» y en «{otro}»")
    return errores
