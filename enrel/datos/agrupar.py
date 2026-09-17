"""Agrupa las menciones de un documento en entidades, por reglas (spec §4.3)."""

from collections import defaultdict
from itertools import combinations

from enrel.datos.documento import Grupo, Mencion
from enrel.datos.normalizar import plegar

PARTICULAS = {"de", "del", "la", "las", "los", "y", "e", "da", "do", "van", "von"}


def _palabras(texto: str) -> list[str]:
    return [p for p in plegar(texto).split() if p not in PARTICULAS]


def _en_orden(corta: list[str], larga: list[str]) -> bool:
    """Las palabras de `corta` aparecen en orden dentro de `larga`, anclada al primer nombre.

    Se exige además que la primera palabra coincida (`corta[0] == larga[0]`): una forma
    corta española suele conservar el primer nombre y el apellido, y omitir los nombres
    intermedios, nunca el primer nombre. Sin este anclaje, «Carlos Galán» sería una
    subsecuencia válida tanto de «Carlos Fernando Galán» como de «Luis Carlos Galán»
    (nombre intermedio del segundo), una ambigüedad espuria que el anclaje evita.
    """
    if not corta or len(corta) >= len(larga) or corta[0] != larga[0]:
        return False
    i = 0
    for p in larga:
        if i < len(corta) and p == corta[i]:
            i += 1
    return i == len(corta)


def _secuencia_contenida(corta: list[str], larga: list[str]) -> bool:
    n = len(corta)
    return 0 < n < len(larga) and any(larga[i : i + n] == corta for i in range(len(larga) - n + 1))


def _sigla_de(texto: str) -> str:
    return "".join(p[0] for p in texto.split() if p[:1].isupper() and p.lower() not in PARTICULAS)


def _es_sigla(texto: str) -> bool:
    t = texto.replace(".", "")
    return t.isupper() and t.isalpha() and 2 <= len(t) <= 6


class _Union:
    def __init__(self, n: int):
        self.p = list(range(n))

    def raiz(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def unir(self, a: int, b: int) -> None:
        self.p[self.raiz(a)] = self.raiz(b)


def agrupar(menciones: list[Mencion], alias: dict[str, str] | None = None) -> list[Grupo]:
    """Agrupa `menciones` en entidades y MUTA el campo `grupo` de cada una con el id asignado.

    Devuelve la lista de `Grupo` (una por entidad). Efecto secundario deliberado: las
    `Mencion` que se reciben quedan modificadas in place, no se copian.
    """
    n = len(menciones)
    uf = _Union(n)
    plegadas = [plegar(m.texto) for m in menciones]
    palabras = [_palabras(m.texto) for m in menciones]
    alias = alias or {}

    # Regla 1 y regla 5, para todos los tipos.
    for i in range(n):
        for j in range(i + 1, n):
            if menciones[i].tipo != menciones[j].tipo:
                continue
            if plegadas[i] == plegadas[j]:
                uf.unir(i, j)
            elif alias and alias.get(plegadas[i]) is not None and alias.get(plegadas[i]) == alias.get(plegadas[j]):
                uf.unir(i, j)

    # Regla 2: personas.
    personas = [i for i in range(n) if menciones[i].tipo == "persona"]
    multipalabra = [i for i in personas if len(palabras[i]) >= 2]
    for i in personas:
        if len(palabras[i]) >= 2:
            # Une solo si hay un único candidato multipalabra más largo donde la corta
            # aparece en orden: «Carlos Galán» aparece en orden dentro de «Carlos Fernando
            # Galán» y también dentro de «Luis Carlos Galán» — ambigüedad real, no se une.
            candidatos = {
                uf.raiz(j)
                for j in multipalabra
                if j != i and len(palabras[j]) > len(palabras[i]) and _en_orden(palabras[i], palabras[j])
            }
            if len(candidatos) == 1:
                uf.unir(i, candidatos.pop())
        elif len(palabras[i]) == 1 and len(palabras[i][0]) >= 4:
            apellido = palabras[i][0]
            candidatos = {uf.raiz(j) for j in multipalabra if palabras[j][-1] == apellido}
            if len(candidatos) == 1:
                uf.unir(i, candidatos.pop())

    # Regla 3: organizaciones. Para cada par se decide cuál es la forma corta (menos
    # palabras) y se comprueba sigla-igual-a-iniciales o secuencia-contenida en ese sentido;
    # cada par no ordenado se examina una sola vez. Igual que en la regla 2, la forma corta
    # se une a la larga solo si hay una única candidata: «EPM» con «Empresas Públicas de
    # Medellín» y «Escuela Popular de Música» presentes no se une a ninguna (ambigüedad
    # real), evitando que se fusionen organizaciones distintas.
    orgs = [i for i in range(n) if menciones[i].tipo == "organizacion"]
    candidatas: dict[int, set[int]] = defaultdict(set)
    for a, b in combinations(orgs, 2):
        if len(palabras[a]) == len(palabras[b]):
            continue
        corta, larga = (a, b) if len(palabras[a]) < len(palabras[b]) else (b, a)
        es_sigla_de_larga = _es_sigla(menciones[corta].texto) and menciones[corta].texto.replace(".", "") == _sigla_de(
            menciones[larga].texto
        )
        if es_sigla_de_larga or _secuencia_contenida(palabras[corta], palabras[larga]):
            candidatas[corta].add(larga)
    for i, largas in candidatas.items():
        raices = {uf.raiz(j) for j in largas}
        if len(raices) == 1:
            uf.unir(i, raices.pop())

    # Ids en orden de primera aparición; canónico = la mención más larga.
    grupos: list[Grupo] = []
    id_de_raiz: dict[int, str] = {}
    for i in sorted(range(n), key=lambda k: menciones[k].ini):
        r = uf.raiz(i)
        if r not in id_de_raiz:
            id_de_raiz[r] = f"e{len(grupos) + 1}"
            miembros = [menciones[k] for k in range(n) if uf.raiz(k) == r]
            canonico = max(miembros, key=lambda m: (len(m.texto), -m.ini)).texto
            grupos.append(Grupo(id_de_raiz[r], menciones[i].tipo, canonico))
        menciones[i].grupo = id_de_raiz[r]
    return grupos
