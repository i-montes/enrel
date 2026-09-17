# Estado del arte: extracción conjunta de entidades y relaciones, liviana y en CPU (informe de investigación)

Fecha: 2026-09-16. Producido por un agente de investigación con búsqueda web. Se separan siempre tres regímenes de cifras que no son comparables entre sí: zero-shot, supervisado de extremo a extremo, y clasificación de relaciones con entidades de oro dadas. Lo no verificado está marcado.

## Tres hallazgos principales

1. **Un codificador de 100 a 300M supera a LLM afinados de 8B a 70B en RE de esquema cerrado, y aplasta a los de frontera.** RoBERTa-base (125M) con marcadores de entidad: F1 0,826 promedio en 7 benchmarks generales, frente a 0,853 del mejor de 30 LLM pequeños afinados y 0,693 / 0,662 de GPT-5.4 / Claude Sonnet 4.6 zero-shot (arXiv 2606.22606, tabla 11). Un parser de grafos sobre BERT de 110M iguala a Qwen3-14B/32B y Llama-3.3-70B afinados en CoNLL04 y los supera por 13,2 F1 en los grafos más densos (arXiv 2604.08752).
2. **La precisión de los LLM cae a medida que el grafo se densifica**, que es justo el régimen de un artículo de 2.000 palabras: correlación entre número de aristas y F1 de −0,639 para Qwen3-14B frente a −0,206 para el parser.
3. **Zero-shot no sirve para producción en ninguna familia.** Mejor zero-shot conjunto de extremo a extremo: DocRED 31,3 (GLiNER-Relex), CoNLL04 40,4. Supervisado ATG en CoNLL04: 78,5. **Hay que anotar datos en español.**

## 1. Familia GLiNER

| Variante | Params medidos | Backbone | Ctx | Multilingüe | Licencia | Notas |
|---|---|---|---|---|---|---|
| urchade/gliner_multi-v2.1 | 289M | mDeBERTa-v3-base | 384 | sí | Apache-2.0 | la ficha dice 209M, es falso |
| urchade/gliner_multi (v1) | 292M | mDeBERTa-v3-base | 384 | sí | **CC-BY-NC** | no comercial |
| fastino/gliner2.5-multi-v1 | 287M | mDeBERTa-v3-base | **4096** | sí, incl. es | Apache-2.0 | **relaciones soportadas**; 158k descargas/mes |
| fastino/gliner2.5-small-v1 | 74M | deberta-v3-xsmall | 4096 | **no, inglés** | Apache-2.0 | |
| knowledgator/gliner-relex-multi-v1.0 | 319M | mDeBERTa-v3-base | **2048** | backbone sí | Apache-2.0 | NER+RE conjunto en una pasada |
| knowledgator/gliner-x-small/base/large | 300M / 494M / 865M | mT5 | 1024 | 20 idiomas incl. es | Apache-2.0 | solo NER |
| gliner-community/*-v2.5 | 166M–460M | DeBERTa-v3 **inglés** | 384–768 | etiqueta engañosa | Apache-2.0 | |

**GLiNER2** (arXiv 2507.18546): 194–205M, esquema declarativo, 2048 tokens. Latencia CPU publicada (entradas cortas): 130 ms con 5 etiquetas, 163 ms con 20, **208 ms con 50**. La planitud respecto al número de etiquetas es la ventaja arquitectónica.

**GLiREL** (NAACL 2025): 467M, DeBERTa-v3-large, solo clasifica relaciones con entidades ya dadas. Zero-shot Wiki-ZSL 83,67, FewRel 87,60. CPU 4,6–4,9 oraciones/s. **Licencia CC BY-NC-SA o ninguna: evitar.** Solo inglés. Con entidades de oro colapsa fuera de FewRel: CoNLL04 4,5, DocRED 2,4.

**GLiNER-Relex** (arXiv 2605.10108, mayo 2026): conjunto NER+RE en un codificador. Zero-shot micro-F1: CoNLL04 40,4, **DocRED 31,3** (GPT-5-mini 18,6), FewRel 12,5, CrossRE 18,1, promedio 25,6. 0,9 s/documento en una L4 (GPU); sin cifra CPU. El paper tiene inconsistencias entre prosa y tabla. **El paper no contiene la palabra "Spanish".**

**La única cifra publicada de GLiNER en español** (paper original, tabla 3, MultiCoNER zero-shot): XLM-R supervisado 58,7 · ChatGPT 34,7 · GLiNER-En 38,7 · **GLiNER-Multi 42,1**. Transfiere, pero queda 16,6 puntos bajo un XLM-R supervisado. **No existe ningún resultado publicado de extracción de relaciones en español para ningún modelo GLiNER.**

**GLiNER bi-encoder / Million-Label** (arXiv 2602.18487): etiquetas precomputadas, 130× más rápido con 1024 etiquetas; útil si el esquema crece. Cross-encoder es mejor en calidad (0,484 vs 0,460, Golde et al. 2026).

## 2. Modelos supervisados clásicos (techos de referencia)

| Modelo | SciERC ENT/REL/REL+ | ACE05 | CoNLL04 |
|---|---|---|---|
| PURE | 66,6 / 48,2 / 35,6 | 88,7 / 66,7 / 63,9 | — |
| TablERT | — | 87,8 / 65,0 / 61,8 | 90,5 / 73,2 / 72,2 |
| ASP | — | 91,3 / 72,7 / 70,5 | 90,3 / — / 76,3 |
| **ATG** (AAAI 2024) | 69,7 / 51,1 / 38,6 | 90,1 / 68,7 / 66,2 | **90,5 / 78,5 / 78,5** |

ATG: codificador + decodificador con puntero; una sola capa de decodificador casi iguala a seis. PL-Marker (ACL 2022): +4 F1 estricto y 2–3× más rápido. SpanMarker (Apache-2.0): solo NER, CoNLL03 93,1 con xlm-roberta-large. TPLinker/OneRel/UniRel: tripletas sin tipo de entidad, inglés; no aplican.

## 3. Nivel de documento

- DocRED: **40,7 % de los hechos requieren varias oraciones**; 17,6 % requieren correferencia. En español (pro-drop, «el mandatario», «la exministra») será mayor. DocRED promedia 198 palabras por documento; un artículo de La Silla es 2,5–10× más largo. **No hay evaluación publicada de DocRE a esa longitud.**
- **Re-DocRED**: el DocRED original tenía un 64,6 % de tripletas faltantes. Mismos modelos, +14 F1 al reanotar. Usar Ign-F1.
- Techo Re-DocRED: ~80–81 F1, plano desde 2023. DREEAM 81,44 / 80,39 (**MIT**, 115M); ATLOP 77,56 (**sin licencia**); KD-DocRE 81,04 (**sin licencia**), con focal adaptativo: +4,1 F1 en la cola larga; DocuNet (MIT); SSAN (Apache-2.0).
- JacRED (japonés): DREEAM 68,73 nativo vs GPT-4 27,45; **traducir Re-DocRED dio 54,87 frente a 68,73 con la mitad de datos anotados nativos**. Transferencia zero-shot entre idiomas cuesta ~30 F1.
- **GLiDRE** (arXiv 2508.00757): bi-encoder para DocRE, ~800M. Supervisado 77,83. Con pocos datos: **N=10 docs 41,73; N=50 54,54; N=100 60,04; N=1000 72,09** (DREEAM en N=10: 27,07). Existe `cea-list-ia/glidre_multi` (613M, mdeberta + gte-multilingual, español declarado, Apache-2.0, **0 descargas, sin F1 publicado**); necesita NER y correferencia por delante.
- LLM con documentos largos: LoRA naive LLaMA2-7B 53,0; AutoRE 53,8; LMRC (BERT poda pares + LLM 13B) 74,6. Todos por debajo de DREEAM de 115M.
- **«Reality Check» (ACL 2023)**: los 78 F1 de DocRE asumen entidades y correferencia perfectas. NER de fábrica sobre DocRED: 63,5 F1; correferencia: 38,7. Con perturbaciones realistas los modelos pierden 23–44 % relativo. **Anclar las metas a las cifras de extremo a extremo (30–55), no a las de leaderboard.**

## 4. Codificadores multilingües para español

| Modelo | Params medidos | Embeddings | Ctx | Licencia | Evidencia es |
|---|---|---|---|---|---|
| **BSC-LT/MrBERT-es** | 150M | 39M (vocab 51k) | 8192 | Apache-2.0 | CoNLL-2002 NER **87,77**; EvalES 89,83 |
| mmBERT-small / base | 140M / 307M | 98M / 197M | 8192 | MIT | NER 87,01 (base); **más débil que XLM-R en NER** (WikiANN 58,2 vs 61,4) |
| mDeBERTa-v3-base | 276M | **190M (69 %)** | 512 | MIT | XNLI-es 84,4 |
| XLM-R base / large | 279M / 561M | 192M / 256M | 514 | MIT | CoNLL-2002 es 87,99 / 89,72 |
| EuroBERT-210m | 310M reales | 98M | 8192 | Apache-2.0 | XNLI-es 76,7; sin NER |
| roberta-base-bne (MarIA) | 125M | — | 512 | **deprecado, pesos retirados** | CoNLL 0,8851 histórico |
| BETO | 110M | 24M | 512 | CC-BY-4.0 con reserva comercial | NER 88,24 |

Claves: MarIA está muerto (el repo solo tiene README con aviso de deprecación). **MrBERT-es** (BSC, arXiv 2602.21379, dic 2025) es el backbone pequeño más fuerte para español: ModernBERT, vocabulario podado a 51k, 615B tokens es/en, 8192 de contexto. Nadie ha entrenado una cabeza GLiNER ni de RE sobre él. El 69 % de mDeBERTa y XLM-R es tabla de embeddings de 250k filas que en español casi no se usa.

## 5. Realidad de la inferencia en CPU

**No existe ningún benchmark publicado en un i5 de 4 núcleos para ninguno de estos modelos.**

- ONNX Runtime int8: 1,8–3,0× sobre fp32 **con VNNI**; en CPUs viejas puede ser peor. Pérdida int8 en NER: 1–3 % de recall, concentrada en ORG/LOC. DistilBERT en 2 núcleos Ice Lake, seq 512: 12 req/s cuantizado vs 4 fp32.
- GLiNER en CPU (i9 8c/12t, gliner-multitask-large, 3 etiquetas): Python oficial **1,61 seq/s**; gline-rs (Rust/ONNX) **6,67 seq/s** (4,1×). GLiNER.cpp existe sin benchmarks. **GLiNER int8 necesita QAT según sus autores**; un practicante midió recall 0 con int8. fp16 es lo seguro.
- llama.cpp: el techo lo pone el ancho de banda de memoria. Ryzen 5700X (AVX2) con Phi-4-mini 3.8B Q4: 9 tok/s; i7-12700 (AVX-512): 12. Un i5 portátil queda por debajo.
- **Cuantizar a 4 bits duele más cuanto más pequeño el modelo**: Llama-3.2-1B −10,1 % promedio (−25 % en GSM8K); a 1B «8 bits puede ser necesario».

Estimación del agente para 100.000 artículos en un i5 de 4 núcleos:

| Enfoque | 100k artículos |
|---|---|
| spaCy CNN | ~3 h |
| **Codificador base, ONNX int8** | **0,5–1 día** |
| GLiNER small/base (Rust/ONNX) | 1,5–3 días |
| Codificador large int8 | 1,5–3,5 días |
| GLiNER large (Python) | 2–5 semanas |
| LLM 1B Q4 | 2–3,5 semanas (4–6 con Q8) |
| LLM 4B Q4 | 1,5–2,5 meses |

## 6. Referencia real: el pipeline de élites políticas europeas (arXiv 2606.27347, julio 2026)

GLiNER-X-Large para NER (7 etiquetas) → enlazado a Wikidata en cascada (alias exacto ~55 %, lematización, Qwen3-Embedding-0.6B) → Qwen3.6-35B-A3B en vLLM con decodificación guiada, ontología de 109 tipos de entidad y 98 relaciones. NER F1 83,8 contra oro humano alemán de 100 artículos. Relaciones: **68,2 % estricto / 93,7 % laxo**; 27,9 % de lo extraído era válido pero faltaba en el oro; **suelo irreducible de alucinación 6,3 %**. La decodificación guiada eliminó el 25,6 % de salidas fuera de ontología. Mejor caso: 1,86 artículos/s **con GPU**. Cambiar el esquema dio +138 % de rendimiento.

## 7. Modelos nuevos 2025–2026 a tener en cuenta

GLiNER2.5 (74/194/287M, 4096 ctx, relaciones), GLiNER-Relex, GLiNER bi-encoder, GLiDRE-multi, GLiNER-X, **MrBERT-es**, mmBERT, EuroBERT, NuExtract3 (Qwen3.5-4B, Apache-2.0, no viable en CPU a este volumen), XGrammar-2, GLiNER Guard / GLiNER2-PII. Falcon-H1 y LFM2 sin verificar.

## 8. Conclusiones del agente

1. **Construir un codificador, no un LLM.** Tres estudios independientes de 2026 convergen. En el hardware objetivo: 0,5–4 días para 100k artículos frente a semanas o meses, con mejor precisión a esta densidad de grafo y sin suelo de alucinación.
2. **Planear anotación.** GLiDRE llega a 60 F1 con 100 documentos; GLiNER gana +5,6 F1 con 100 ejemplos. Presupuesto: 100–300 artículos anotados.
3. **No traducir datasets ingleses; anotar español nativo.** Mitad de datos nativos, +14 F1 (JacRED). Usar REDFM-es (2,38k filas, 32 relaciones, 13 tipos) para arrancar.
4. **Licencias**: seguros gliner2*, gliner-relex, gliner-x, gliner_multi-v2.1, DREEAM, DocuNet, SSAN, XLM-R, mDeBERTa, mmBERT, MrBERT-es, EuroBERT, REDFM/SREDFM. Evitar GLiREL, mREBEL, gliner_multi v1, ATLOP y KD-DocRE (sin licencia), MultiNERD, WikiNEuRal, NuExtract-2.0-4B.
5. **La ingeniería pesa tanto como el modelo**: Rust/ONNX 4×; fp16 antes que int8 ingenuo en GLiNER; focal adaptativo +4,1 F1 en la cola larga.
6. **El F1 honesto de extremo a extremo estará muy por debajo de los leaderboards: 50–70 % de tripletas estrictamente correctas es una meta realista.**

Propuesta del agente: (0) anotar 100 artículos y evaluar primero; (1) línea base zero-shot con gliner2.5-multi y gliner-relex-multi vía ONNX fp16, medida en el i5; (2) afinar con REDFM-es más los artículos propios; (3) los dos experimentos que nadie ha hecho: cabeza GLiNER/RE sobre **MrBERT-es**, y evaluar glidre_multi; (4) destilar de un modelo grande una vez, correr el pequeño siempre; (5) correferencia en español y enlazado a Wikidata como cascada de alias.

## 9. No verificado

Cualquier benchmark en i5 de 4 núcleos; degradación int8 de GLiNER; rendimiento CPU de DeBERTa/XLM-R/ModernBERT con ONNX int8; latencia GLiNER en documentos de más de 1000 palabras; resultados en español de cualquier GLiNER para relaciones; rendimiento de glidre_multi; licencia de ATG; GenRDK; Falcon-H1 y LFM2.
