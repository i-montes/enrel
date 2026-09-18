"""Léxico de disparadores léxicos por relación: una expresión regular por cada una de las 18 relaciones."""

import re

DISPARADORES = {
    k: re.compile(v, re.I)
    for k, v in {
        "ocupa_cargo": r"\b(ministr[oa]|alcalde(sa)?|gobernador[a]?|senador[a]?|representante a la c[aá]mara|"
        r"magistrad[oa]|procurador[a]?|fiscal general|contralor[a]?|director[a]? (general|ejecutiv[oa])|"
        r"presidenta?|vicepresidenta?|concejal|diputad[oa]|embajador[a]?|superintendente|candidat[oa]|"
        r"precandidat[oa]|aspira a|se posesion[óo]|fue nombrad[oa]|exministr[oa]|exalcalde|exgobernador|"
        r"expresidente)\b",
        "nombro_a": r"\b(nombr[óo] a|design[óo] a|escogi[óo] a|eligi[óo] a|posesion[óo] a|nombramiento de)\b",
        "sucedio_a": r"\b(reemplaz[óo] a|sucedi[óo] a|sucesor[a]? de|en reemplazo de|releva a|relev[óo] a|"
        r"dej[óo] el cargo a)\b",
        "trabaja_en": r"\b(trabaj[óo]? (en|para)|asesor[a]? de|funcionari[oa] de|emplead[oa] de|consultor[a]? de|"
        r"contratista de)\b",
        "dirige": r"\b(dirige|dirigi[óo]|preside|presidi[óo]|gerente (general )?de|director[a]? de|al frente de|"
        r"encabeza|lidera)\b",
        "miembro_de": r"\b(militante de|miembro de|integrante de|hace parte de|pertenece a|afiliad[oa] a|"
        r"bancada de|junta directiva)\b",
        "fundo": r"\b(fund[óo]|fundador[a]? de|cofundador[a]?|cre[óo] la (empresa|fundaci[óo]n|organizaci[óo]n)|"
        r"creador[a]? de)\b",
        "propietario_de": r"\b(dueñ[oa] de|propietari[oa] de|accionista|acciones de|controla la empresa|"
        r"es dueñ[oa]|compr[óo] la empresa|adquiri[óo])\b",
        "socio_de": r"\b(socio de|socia de|socios|sus socios|en sociedad con)\b",
        "parte_de": r"\b(filial de|subsidiaria|adscrit[oa] a|depende del|dependencia de|"
        r"hace parte del (ministerio|grupo|conglomerado)|pertenece al grupo)\b",
        "contrato_a": r"\b(contrat[óo] a|contrato con|licitaci[óo]n|adjudic[óo]|adjudicaci[óo]n|contratista|"
        r"contratos por)\b",
        "financia_a": r"\b(financi[óo]|financia|don[óo]|donaci[óo]n|aport[óo]|aportes a la campa[ñn]a|"
        r"patrocin[óo]|financiador)\b",
        "familiar_de": r"\b(espos[oa]|ex ?espos[oa]|pareja|compañer[oa] permanente|hij[oa]s? de|su hij[oa]|"
        r"herman[oa]s?|pap[aá]|mam[aá]|padre de|madre de|t[ií][oa]|sobrin[oa]|prim[oa]|cuñad[oa]|suegr[oa]|"
        r"nuera|yerno|niet[oa]|abuel[oa])\b",
        "apoya_a": r"\b(respald[óo]|respalda|apoy[óo] a|apoya a|apoyo a la candidatura|aliad[oa]|se sum[óo] a|"
        r"adhiri[óo]|adhesi[óo]n|coalici[óo]n con)\b",
        "impulsa_norma": r"\b(radic[óo]|redact[óo]|ponente de|sac[óo] adelante|sacar adelante|sancion[óo]|"
        r"aprob[óo]|aprobaci[óo]n de)\b",
        "se_opone_a": r"\b(se opone|se opuso|oposici[óo]n a|critic[óo]|rechaz[óo]|cuestion[óo]|denunci[óo] a|"
        r"opositor[a]?|enfrentad[oa] con|rival de)\b",
        "investigado_por": r"\b(investigad[oa]|investigaci[óo]n de la|imputad[oa]|imputaci[óo]n|acusad[oa]|"
        r"condenad[oa]|condena|Fiscal[ií]a|Procuradur[ií]a|Contralor[ií]a|Corte Suprema|sancionad[oa]|"
        r"destituid[oa]|inhabilitad[oa])\b",
        "ubicado_en": r"\b(con sede en|sede principal|reside en|vive en|radicad[oa] en|ubicad[oa] en|"
        r"municipio de|corregimiento de|vereda de|barrio)\b",
    }.items()
}


def relaciones_disparadas(texto: str) -> set[str]:
    return {r for r, patron in DISPARADORES.items() if patron.search(texto)}
