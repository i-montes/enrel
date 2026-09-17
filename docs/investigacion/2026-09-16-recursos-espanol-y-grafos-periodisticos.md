# Recursos en español para NER+RE y grafos periodísticos (informe de investigación)

Fecha: 2026-09-16. Producido por un agente de investigación con búsqueda web; cada cifra viene de una fuente primaria consultada ese día. Lo no verificable está marcado.

## Cuatro hallazgos que cambian supuestos

1. **Universal NER (UNER) no tiene español**, ni en v1 ni en v2. https://arxiv.org/html/2604.12744
2. **Los modelos NER de PlanTL sobre CAPITEL y el propio dataset CAPITEL-NERC ya no se pueden descargar** (HTTP 401). Sobreviven espejos: `SantiMB/roberta-base-bne-capitel-ner-plus-ONNX` (Apache-2.0, ONNX cuantizado), `Dulfary/roberta-large-bne-capitel-ner_spanish`.
3. **«Quién es Quién» no es de Cuestión Pública**: QuiénEsQuién.Wiki es de PODER (México). La herramienta de IA de Cuestión Pública es «El Proyecto Odín». No existe «Quién-AI» público.
4. **SREDFM (subconjunto español) ya trae las relaciones de poder que hacen falta** (P39 cargo, P102 partido, P108 empleador, P112 fundador, P127 propietario, P169 CEO, P488 presidente, P355 filial, P1399 condenado por), mientras que REDFM (humano, 32 relaciones) no. Licencia CC BY-SA 4.0. https://huggingface.co/datasets/Babelscape/SREDFM

## 1. Datasets NER en español

| Dataset | Tamaño (es) | Tipos | Licencia | Cobertura |
|---|---|---|---|---|
| CoNLL-2002 es | 8.324 / 1.916 / 1.518 oraciones | PER, LOC, ORG, MISC | **sin licencia declarada**; EFE año 2000 | ibérico, agencia |
| CAPITEL-NERC | 22.647 / 7.549 / 7.549 oraciones | PER, LOC, ORG, OTH | paper CC BY 4.0; **dataset 401** | ibérico, prensa |
| UD_Spanish-AnCora | 17.662 oraciones, 547k tokens; NE + coref en MISC | esquema AnCora | README dice GNU, LICENSE.txt dice CC BY 4.0 | ibérico, prensa |
| AnCora-CO | 400k palabras con correferencia, 89.206 entidades | NE + coref | GNU | referencia de correferencia en español |
| WikiNER es | 126.260 oraciones | LOC, PER, ORG, MISC | **CC BY 4.0** | Wikipedia 2010 |
| WikiNEuRal es | 76.320 / 9.540 / 9.618 | PER, LOC, ORG, MISC | CC-BY-NC-SA — **no comercial** | Wikipedia |
| MultiNERD es | 173.2K oraciones | 15 tipos | CC BY-NC-SA — **no comercial** | Wikipedia + Wikinews |
| MultiCoNER v2 es | 16.453 / 854 / 246.900 | 33 finos / 6 gruesos | CC BY 4.0 | web, consultas cortas |
| Mx-news | 250 documentos, 17 clases | prensa política mexicana | **sin licencia**, un solo anotador | el único corpus de prensa latinoamericana hallado |
| ACE 2007 es | 100k palabras | entidades + expresiones temporales (no relaciones) | LDC, pago | prensa |

Problemas: CoNLL-2002 tiene 26 años y es ibérico. CAPITEL anota solo el tramo más externo (no anidados) y basa la identificación en la ortografía de mayúsculas. **No existe ningún corpus NER de prensa colombiana.** Limpios para uso comercial: WikiNER (CC BY 4.0) y MEDDOCAN (CC BY 4.0).

## 2. Relaciones, correferencia, enlazado

| Dataset | Tamaño (es) | Relaciones | Licencia |
|---|---|---|---|
| REDFM (oro humano) | 5.452 / 611 / 733 | 32 | CC BY-SA 4.0 |
| SREDFM (plata distante) | millones, 18 idiomas | 400 (PIDs Wikidata) | CC BY-SA 4.0 |
| SMiLER es | 12k oraciones | 22 de 36 | sin licencia declarada |
| MultiTACRED es | 65.247 / 21.697 / 14.908 | 41 TACRED | **LDC, pago** (LDC2024T09) |
| RELX es | 502 oraciones | 37 clases | sin licencia |

Techos publicados: mREBEL 50,1 F1 en REDFM-es; MultiTACRED-es micro-F1 75,7 con BETO. La RE en español es bastante más difícil que la NER.

REDFM-es (train) trae: country 646, part of 353, owned by 170, member of 163, headquarters location 110, occupation 105, child 104, founded by 58, replaces 55, spouse 49, director 37, sibling 23. **No trae P39, P102 ni P108.** SREDFM sí; le faltan P749, P1830, P22/P25, P3320.

Correferencia: AnCora-CO / CorefUD_Spanish-AnCora (train+dev públicos, test retenido, CorefUD 1.4, 2026-02). Enlazado: Mewsli-9 (Wikinews es → Wikidata), VoxEL.

Colombia: CNER (Universidad del Valle, arXiv 2405.10485), herramienta web con tipos ACE; sin F1 publicado.

## 3. Codificadores preentrenados

| Modelo | Params | Licencia | Cifras |
|---|---|---|---|
| **BSC-LT/MrBERT-es** | 150M | Apache-2.0 | ModernBERT, 615B tokens 50/50 es-en, ctx 8192; EvalES NER F1 **87,77** |
| BSC-LT/mRoBERTa | 283M | Apache-2.0 | PANX-es 78,30 (XLM-R-large 73,46) |
| roberta-base-bne (MarIA) | 125M | Apache-2.0, **deprecado** | CoNLL-NERC 0,8851; CAPITEL 0,8960 |
| roberta-large-bne | 355M | Apache-2.0, deprecado | CAPITEL 0,9051 |
| BETO cased | 110M | CC-BY-4.0 con reserva | NER-C 88,43 |
| XLM-R base / large | 279M / 561M | MIT | EvalES NER 86,91 (base) |
| mDeBERTa-v3-base | 276M | MIT | XNLI-es 84,4 |
| mmBERT base / small | 307M / 140M | MIT | EvalES NER 87,01 (base); small sin cifras es |
| EuroBERT 210m / 610m | 310M / 756M reales | Apache-2.0 | solo gráficas, sin tablas |
| RigoBERTa 2.0 | 560M | **no comercial** | imágenes |
| Salamandra 2b / 7b | 2,25B / 7,77B | Apache-2.0 | español 16 % del corpus |
| ALIA-40b | 40B | Apache-2.0 | vivo, con GGUF |
| LatamGPT (CENIA) | 70B | Llama 3.1 | lanzado 2026-02, sin benchmarks |

Herramientas con cifras: Flair `ner-spanish-large` **90,54** CoNLL-es (sin licencia en la ficha); spaCy `es_core_news_lg` 0,897 (GPL-3.0; `es_dep_news_trf` **no tiene NER**); Stanza es 88,1 / 88,6 (Apache-2.0); `knowledgator/gliner-relex-base-v1.0` 225M Apache-2.0, sin cifras en español; `numind/NuNER-multilingual-v0.1` MIT; `Babelscape/mrebel-large` **no comercial**.

Banderas de licencia: spaCy es GPL-3.0; mREBEL y WikiNEuRal NC; RigoBERTa NC; ALBETO/DistilBETO sin licencia. Limpios (<400M, Apache/MIT): MrBERT-es, mRoBERTa, mmBERT, EuroBERT-210m, roberta-base-bne, gliner-relex-base, gliner_multi-v2.1, NuNER-multilingual. **No existe un codificador adaptado al español colombiano.**

## 4. Grafos periodísticos: qué usaron

| Proyecto | País | Entidades | Relaciones | Tecnología / licencia |
|---|---|---|---|---|
| Cuestión Pública, Proyecto Odín | CO | no publicado | no publicado | GPT-3.5/4, RAG; propietario |
| Poderopedia | CL | Person, Organization, Company, PoliticalOrganization… | :Connection → Sentimental, Social, Educational, Association (Financier…), Political, Work, Company | OWL; GPL-3; **sitio muerto, vocab de 2018** |
| LittleSis | US | Person, Org + 38 subtipos | **12 categorías**: Position, Education, Membership, Family, Donation, Transaction, Lobbying, Social, Professional, Ownership, Hierarchy, Generic | GPL-3 código, **CC BY-SA datos** |
| OCCRP Aleph + FollowTheMoney | intl | 70 esquemas (Person, Company, PublicBody, Position, Contract, CourtCase, Sanction…) | **17 aristas**: Ownership, Control, Directorship, Employment, Membership, Representation, Succession, Family, Associate, Occupancy, Payment, Debt, ContractAward, CourtCaseParty, UnknownLink… | **MIT**, activo en 2026, traducciones al español |
| ICIJ Datashare + neo4j | intl | Document, NamedEntity (PERSON/ORG/LOC/EMAIL) | APPEARS_IN, SENT, RECEIVED | AGPL-3 |
| PODER QuiénEsQuién.Wiki | MX | Person, Organization, Contract, Membership | **solo Membership** (Popolo) + OCDS | GPL-3; cedido a Abrimos.info en 2025-12 |
| Ojo Público FUNES | PE | contratos, proveedores, funcionarios | no es grafo: 20 indicadores de riesgo | R, sin licencia |
| BBC Juicer | UK | Concepts (DBpedia), Events, Storylines | article→concept | archivado |
| KG dictadura chilena (académico) | CL | Individual, Event, Location, Organization | 7 tipos | GPT-4o-mini, ~40k páginas → 50k entidades / 100k relaciones en 2 h por ~US$30. Personas casi perfectas; **organizaciones 14 correctas / 21 sobrantes** (resolución); eventos 18 / 20 faltantes |

Lecciones de esquema:
- **Toda arista lleva procedencia** (FtM `Interval`: startDate, endDate, sourceUrl, publisher, proof, retrievedAt). El URL del artículo es la evidencia.
- **Modelar el cargo, no solo la persona**: FtM `Position` + `Occupancy` (Popolo Post/Membership). «Our database is built around the office, not the person.»
- **Un sitio legítimo para lo incierto**: FtM `UnknownLink`.
- Latinoamérica eligió esquemas planos; el hueco de una ontología de poder en español está sin llenar.
- Personas es lo fácil; **resolución de organizaciones y granularidad de eventos** es donde viven los errores.

## 5. Esquemas de relaciones para redes de poder

| Esquema | Licencia | Comercial |
|---|---|---|
| **FollowTheMoney** ontología + librería | **MIT** | sí |
| Datos OpenSanctions | CC BY-NC | no |
| Wikidata | **CC0** | sí |
| LittleSis datos | CC BY-SA 4.0 | sí, share-alike |
| BODS (Open Ownership) | Apache-2.0 | sí |
| Popolo | CC BY 4.0 | sí |

FtM es el esquema que de verdad se reutiliza (Aleph, OpenSanctions, ICIJ, CORRECTIV, EveryPolitician…).

PIDs de Wikidata verificados en vivo: P39 position held, P108 employer, P102 party, P127 owned by, P1830 owner of, P3320 board member, P1037 director, P169 CEO, P488 chairman, P112 founder, P355 child org, P749 parent org, P26 spouse, P40 child, P22 father, P25 mother, P3373 sibling, P463 member of, P1327 business partner, P1399 convicted of, P1365 replaces, P1366 replaced by, P159 HQ, P17 country, P131 located in. Cualificadores P580/P582 inicio/fin, P768 circunscripción, P4100 grupo parlamentario. **P642 «of» está borrado.**

## 6. Retos lingüísticos del español periodístico

- **Anidamiento es la norma**: en AnCora casi la mitad de las entidades están anidadas; un CRF plano baja de F1 64,55 a 34,25 evaluando todas las entidades (Finkel & Manning). «Ministerio de Defensa de Colombia».
- Los corpus estándar anotan **solo el tramo externo**: un modelo entrenado en CoNLL/CAPITEL nunca aprende «Colombia» dentro de «Ministerio de Defensa de Colombia».
- **El tipo es contextual**: Santander, Bolívar, Nariño son departamento, persona, moneda, palacio.
- **Los cargos van en minúscula** en la ortografía española («el presidente», «el exalcalde», «el mandatario»): un etiquetador anclado en mayúsculas pierde justo las menciones de rol que cargan la señal relacional. Los roles se resuelven por correferencia, no por NER.
- **Pro-drop** rompe la alineación de argumentos («También presidió el Consejo Constitucional»: sujeto elidido). Español fue de los tres peores idiomas de MultiTACRED en validez de traducción.
- Artículos absorbidos en el tramo, **coordinación** («Ministerio de Comercio, Industria y Turismo»), modificadores posnominales.
- OTH/MISC es el punto débil sistemático: ahí viven leyes, programas, operaciones, tratados.
- Apellidos compuestos y partículas (de, del, de la): FtM modela `fatherName` y `motherName`.
- **Ningún corpus contiene vocabulario institucional colombiano** (Ecopetrol, EPM, Fiscalía General de la Nación, Procuraduría, Contraloría, DIAN, UNGRD, SENA, ICBF). Un gazetteer colombiano más unos miles de oraciones anotadas compra más que cualquier cambio de modelo.

## 7. Borrador de esquema recomendado (18 relaciones, sobre FtM + Wikidata)

| # | Relación | Disparadores | Dominio → Rango | FtM | Wikidata | En SREDFM-es |
|---|---|---|---|---|---|---|
| 1 | holds_position | nombrado ministro, se posesionó | Person → Position | Occupancy | P39 | sí |
| 2 | member_of_party | militante de | Person → Org | Membership | P102 | sí |
| 3 | employed_by | trabajó en, asesor de | Person → Org | Employment | P108 | sí |
| 4 | director_of | junta directiva, director de | Person → Org | Directorship | P3320, P1037, P169, P488 | parcial |
| 5 | owns | dueño de, accionista | LegalEntity → Asset/Company | Ownership (+percentage) | P127 / P1830 | P127 |
| 6 | controls | controla, testaferro de | LegalEntity → LegalEntity | Control (controlType) | — | no |
| 7 | founded | fundó | Person → Org | Directorship role founder | P112 | sí |
| 8 | parent_org_of | filial de, adscrito a | Org → Org | Membership / Control | P749 / P355 | no |
| 9 | member_of_org | miembro de, integra | LegalEntity → Org | Membership | P463 | sí |
| 10 | family_of | hijo de, esposa de, compañero permanente | Person → Person | Family (relationship libre) | P26, P40, P22, P25, P3373, P1038 | parcial |
| 11 | business_partner_of | socio de | Person → Person | Associate | P1327 | sí |
| 12 | represents | abogado de, apoderado de | LegalEntity → LegalEntity | Representation | P1268 | no |
| 13 | awarded_contract | ganó la licitación | Contract → LegalEntity | ContractAward | — | no |
| 14 | paid / donated_to | donó a la campaña | LegalEntity → LegalEntity | Payment (purpose) | P859 | sí |
| 15 | investigated_for / convicted_of | condenado por, imputado | Person → Event | CourtCaseParty, Sanction | P1399, P793 | sí |
| 16 | succeeded | reemplazó a | Person → Person | Succession | P1365 / P1366 | sí |
| 17 | located_in | con sede en | Thing → Territory | country / Address | P159, P17, P131 | sí |
| 18 | unknown_link | bajo umbral | Thing ↔ Thing | UnknownLink | — | no |

Atributos de arista: startDate, endDate, role, status, sourceUrl, publisher, proof, retrievedAt, confidence, extractorVersion. Vocabulario fijo en español para Family (madre, padre, hijo/a, hermano/a, cónyuge, compañero/a permanente, suegro/a, cuñado/a, primo/a, sobrino/a). Distinción LittleSis donación vs transacción para Payment.

## 8. Recomendaciones del agente

- Codificador: **MrBERT-es** (150M, Apache-2.0, mejor NER publicado entre los pequeños, ctx 8192 para RE a nivel de documento). Respaldo: mRoBERTa 283M.
- Arranque: gliner-relex-base-v1.0 para plata, luego corrección humana.
- Datos: WikiNER-es + CoNLL-2002 + rebanada española de SREDFM filtrada a ~20 PIDs + anotación colombiana propia. Evitar MultiNERD, WikiNEuRal, mREBEL si el producto es comercial.
- Esquema: FollowTheMoney (MIT) con QIDs de Wikidata (CC0) como espina de identificadores.
- Líneas base a superar: Flair 90,54 CoNLL-es; Stanza 88,6 AnCora; spaCy lg 89,70.

## 9. No verificado

Licencia de CoNLL-2002; cifras de las fichas CAPITEL borradas; licencia contradictoria de UD_Spanish-AnCora; licencias de SMiLER, RELX, ALBETO, DistilBETO, Flair; cifras españolas de GLiNER-x, gliner-relex, mREBEL, NuExtract; benchmarks de LatamGPT; taxonomía actual de Poderopedia; ontologías BBC/NYT; cifras de ambigüedad de nombres hispanos.
