"""Convierte el oro y la plata de legajo (por párrafo, 35 o 25 predicados) al formato interno de enrel."""

import json
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from enrel.corpus.legajo_db import Articulo, parrafos
from enrel.datos.agrupar import agrupar
from enrel.datos.documento import Documento, Grupo, Mencion, Relacion
from enrel.datos.normalizar import palabras, plegar
from enrel.datos.validar import validar_documento
from enrel.esquema.mapeo_legajo import mapear_predicado, mapear_tipo
from enrel.esquema.tipos import clase_fina, es_simetrica


def leer_oro_json(directorio: Path) -> dict[int, dict]:
    out = {}
    for ruta in sorted(Path(directorio).glob("*.json")):
        spec = json.loads(ruta.read_text(encoding="utf-8"))
        out[int(spec["wp_id"])] = spec
    return out


def leer_plata_legajo(ruta_jsonl: Path) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    with Path(ruta_jsonl).open(encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                fila = json.loads(linea)
                out.setdefault(int(fila["wp_id"]), []).append(fila)
    return out


def _sin_diacriticos(texto: str) -> str:
    """Como `plegar`, pero sin bajar a minúsculas: la búsqueda de respaldo compara palabras
    completas y no debe confundir una mención propia («Fiscal») con un sustantivo común
    («fiscal») solo porque el mayúsculas/minúsculas coincide tras plegar."""
    t = unicodedata.normalize("NFD", texto)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _limite_de_palabra(texto: str, ini: int, fin: int, buscado: str) -> bool:
    """La coincidencia no debe quedar pegada a otro carácter alfanumérico.

    Solo se exige el límite en el lado de `buscado` que empieza o termina en un carácter
    alfanumérico: una mención como «@petrogustavo» o «30 %» no tiene ese límite en el
    extremo que no lo es. Evita que «Cali» encaje dentro de «California» o «Fiscal»
    dentro de «Fiscalía».
    """
    if buscado and buscado[0].isalnum() and ini > 0 and texto[ini - 1].isalnum():
        return False
    if buscado and buscado[-1].isalnum() and fin < len(texto) and texto[fin].isalnum():
        return False
    return True


def _apariciones(texto_parrafo: str, buscado: str) -> list[tuple[int, int]]:
    """Todas las apariciones de `buscado` en el párrafo, exactas y en límites de palabra,
    sin solaparse; si no hay ninguna, por palabras completas (sin diacríticos, con mayúsculas)."""
    out, pos = [], 0
    while True:
        i = texto_parrafo.find(buscado, pos)
        if i < 0:
            break
        fin = i + len(buscado)
        if _limite_de_palabra(texto_parrafo, i, fin, buscado):
            out.append((i, fin))
        pos = fin  # nunca solapada con la anterior
    if out:
        return out
    objetivo = [_sin_diacriticos(p) for _, _, p in palabras(buscado)]
    pals = palabras(texto_parrafo)
    n = len(objetivo)
    for k in range(len(pals) - n + 1):
        if [_sin_diacriticos(p) for _, _, p in pals[k : k + n]] == objetivo:
            out.append((pals[k][0], pals[k + n - 1][1]))
    return out


class _Constructor:
    """Acumula menciones y relaciones con offsets globales y produce el Documento."""

    def __init__(self, articulo: Articulo, fuente: str, origen: dict):
        self.art = articulo
        self.fuente = fuente
        self.origen = {"mapeo_legajo": True, "no_localizadas": 0, "predicados_originales": Counter(), **origen}
        self.menciones: list[Mencion] = []
        self.pendientes: list[
            tuple[str, str, str, str | None, tuple[int, int]]
        ] = []  # (mid_a, mid_b, pred, cuando, evidencia)
        self.designa: list[str] = []
        self.grupo_forzado: dict[str, str] = {}
        self.offsets_parrafo = {pi: off for pi, (off, _) in enumerate(parrafos(articulo.texto_plano))}
        self.textos_parrafo = {pi: t for pi, (_, t) in enumerate(parrafos(articulo.texto_plano))}

    def mencion(
        self,
        pi: int,
        ini_local: int,
        fin_local: int,
        texto: str,
        tipo_legajo: str,
        mid: str | None = None,
        designa: bool = False,
        grupo: str | None = None,
    ) -> Mencion:
        tipo, designa_tipo = mapear_tipo(tipo_legajo)
        base = self.art.desplazamiento_cuerpo + self.offsets_parrafo[pi]
        m = Mencion(mid or f"m{len(self.menciones) + 1}", base + ini_local, base + fin_local, texto, tipo, "")
        self.menciones.append(m)
        if designa or designa_tipo:
            self.designa.append(m.id)
        if grupo:
            self.grupo_forzado[m.id] = grupo
        return m

    def evidencia(self, pi: int) -> tuple[int, int]:
        base = self.art.desplazamiento_cuerpo + self.offsets_parrafo[pi]
        return base, base + len(self.textos_parrafo[pi])

    def relacion(self, mid_a: str, mid_b: str, predicado: str, cuando: str | None, pi: int) -> None:
        self.pendientes.append((mid_a, mid_b, predicado, cuando or "vigente", self.evidencia(pi)))
        self.origen["predicados_originales"][predicado] += 1

    def construir(self, pares_mismos: list[tuple[str, str]] = ()) -> Documento:
        grupos = agrupar(self.menciones)
        # Grupos forzados por legajo (columna `grupo` o resoluciones «misma»): fusionar.
        self._fusionar(grupos, pares_mismos)
        por_mid = {m.id: m for m in self.menciones}
        relaciones: list[Relacion] = []
        claves: set[tuple] = set()
        for mid_a, mid_b, pred, cuando, ev in self.pendientes:
            a, b = por_mid.get(mid_a), por_mid.get(mid_b)
            if a is None or b is None:
                continue
            mp = mapear_predicado(pred, a.tipo, b.tipo, cuando)
            cabeza, cola = (b, a) if mp.invertir else (a, b)
            if cabeza.grupo == cola.grupo:
                continue
            fina = clase_fina(mp.relacion, mp.atributo)
            clave = (cabeza.grupo, cola.grupo, fina)
            espejo = (cola.grupo, cabeza.grupo, fina)
            if clave in claves or (es_simetrica(mp.relacion, mp.atributo) and espejo in claves):
                continue
            claves.add(clave)
            relaciones.append(Relacion(cabeza.grupo, cola.grupo, mp.relacion, mp.atributo, ev))
        self.origen["designa"] = self.designa
        self.origen["predicados_originales"] = dict(self.origen["predicados_originales"])
        doc = Documento(
            doc_id=f"wp:{self.art.wp_id}",
            texto=self.art.texto,
            menciones=self.menciones,
            grupos=grupos,
            relaciones=relaciones,
            url=self.art.url,
            fecha=self.art.fecha,
            seccion=self.art.seccion,
            titulo=self.art.titulo,
            fuente=self.fuente,
            origen=self.origen,
        )
        errores = validar_documento(doc)
        if errores:
            raise ValueError("\n".join(errores))
        return doc

    def _fusionar(self, grupos: list[Grupo], pares_mismos) -> None:
        """Une grupos que legajo declaró iguales: por `grupo` de anotaciones o por resoluciones «misma».

        Las uniones se acumulan en un union-find para cerrar la transitividad: si (A=B) y
        (B=C), A, B y C deben terminar en un único grupo aunque nunca se compare A con C
        directamente.
        """
        por_id = {g.id: g for g in grupos}
        padre: dict[str, str] = {g.id: g.id for g in grupos}

        def raiz(x: str) -> str:
            while padre[x] != x:
                padre[x] = padre[padre[x]]
                x = padre[x]
            return x

        def unir(a: str, b: str) -> None:
            ra, rb = raiz(a), raiz(b)
            if ra != rb:
                padre[ra] = rb

        # Por columna grupo: todas las menciones con el mismo valor van juntas.
        por_forzado: dict[str, set[str]] = {}
        for mid, gf in self.grupo_forzado.items():
            m = next(x for x in self.menciones if x.id == mid)
            por_forzado.setdefault(gf, set()).add(m.grupo)
        for s in por_forzado.values():
            s = list(s)
            for otro in s[1:]:
                unir(s[0], otro)

        # Por resoluciones: nombres plegados, mismo tipo.
        canonicos = {plegar(g.canonico): g.id for g in grupos}
        for a, b in pares_mismos:
            ga, gb = canonicos.get(plegar(a)), canonicos.get(plegar(b))
            if ga and gb and por_id[ga].tipo == por_id[gb].tipo:
                unir(ga, gb)

        # El destino de cada componente es el id de grupo más pequeño en él.
        componentes: dict[str, set[str]] = {}
        for gid in padre:
            componentes.setdefault(raiz(gid), set()).add(gid)
        destino_de: dict[str, str] = {}
        for miembros in componentes.values():
            destino = min(miembros, key=lambda gid: int(gid[1:]))
            for gid in miembros:
                destino_de[gid] = destino

        for m in self.menciones:
            m.grupo = destino_de.get(m.grupo, m.grupo)
        vivos = {m.grupo for m in self.menciones}
        grupos[:] = [g for g in grupos if g.id in vivos]


def documento_desde_oro_json(spec: dict, articulo: Articulo, fuente: str = "oro") -> Documento:
    c = _Constructor(articulo, fuente, {"spec": True})
    for pi_str, p in spec.get("parrafos", {}).items():
        pi = int(pi_str)
        if pi not in c.textos_parrafo:
            continue
        texto_p = c.textos_parrafo[pi]
        primera: dict[str, str] = {}
        for texto_e, tipo_e in p.get("E", []):
            aps = _apariciones(texto_p, texto_e)
            if not aps:
                c.origen["no_localizadas"] += 1
                continue
            for ini, fin in aps:
                m = c.mencion(pi, ini, fin, texto_p[ini:fin], tipo_e)
                primera.setdefault(texto_e, m.id)
        for r in p.get("R", []):
            a, pred, b = r[0], r[1], r[2]
            cuando = r[3] if len(r) > 3 else "vigente"
            if a in primera and b in primera:
                c.relacion(primera[a], primera[b], pred, cuando, pi)
    return c.construir()


def documento_desde_sqlite(con: sqlite3.Connection, lote_id: int, articulo: Articulo, fuente: str = "oro") -> Documento:
    c = _Constructor(articulo, fuente, {"lote_id": lote_id})
    filas = con.execute(
        "SELECT mid, pi, ini, fin, texto, tipo, designa, grupo FROM anotaciones"
        " WHERE lote_id = ? AND wp_id = ? ORDER BY pi, ini",
        (lote_id, articulo.wp_id),
    ).fetchall()
    for f in filas:
        pi = int(f["pi"])
        if pi not in c.textos_parrafo or c.textos_parrafo[pi][f["ini"] : f["fin"]] != f["texto"]:
            c.origen["no_localizadas"] += 1
            continue
        c.mencion(
            pi,
            int(f["ini"]),
            int(f["fin"]),
            f["texto"],
            f["tipo"],
            mid=f["mid"],
            designa=bool(f["designa"]),
            grupo=f["grupo"],
        )
    pi_de = {f["mid"]: int(f["pi"]) for f in filas}
    for r in con.execute(
        "SELECT a_mid, b_mid, predicado, cuando FROM relaciones WHERE lote_id = ? AND wp_id = ?",
        (lote_id, articulo.wp_id),
    ):
        if r["a_mid"] in pi_de and r["b_mid"] in pi_de:
            c.relacion(r["a_mid"], r["b_mid"], r["predicado"], r["cuando"], pi_de[r["a_mid"]])
    mismos = [
        (x["a_nombre"], x["b_nombre"])
        for x in con.execute(
            "SELECT a_nombre, b_nombre FROM resoluciones WHERE lote_id = ? AND decision = 'misma'", (lote_id,)
        )
    ]
    return c.construir(mismos)


def documento_desde_plata_legajo(filas: list[dict], articulo: Articulo) -> Documento:
    c = _Constructor(
        articulo, "plata-legajo", {"modelo": filas[0].get("modelo", ""), "prompt": filas[0].get("prompt", "")}
    )
    for fila in filas:
        pi = int(fila["pi"])
        if pi not in c.textos_parrafo:
            continue
        ids = []
        for e in fila.get("entidades", []):
            if c.textos_parrafo[pi][e["ini"] : e["fin"]] != e["texto"]:
                c.origen["no_localizadas"] += 1
                ids.append(None)
                continue
            ids.append(c.mencion(pi, e["ini"], e["fin"], e["texto"], e["tipo"]).id)
        for r in fila.get("relaciones", []):
            a, b = ids[r["a"]] if r["a"] < len(ids) else None, ids[r["b"]] if r["b"] < len(ids) else None
            if a and b:
                c.relacion(a, b, r["predicado"], r.get("cuando"), pi)
    return c.construir()
