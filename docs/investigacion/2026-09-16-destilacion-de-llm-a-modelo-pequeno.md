# Destilar NER+RE de esquema cerrado de un LLM grande a un modelo pequeño (informe de investigación)

Fecha: 2026-09-16. Producido por un agente de investigación con búsqueda web. Cada afirmación lleva fuente; lo no verificado está marcado.

## 0. Diagnóstico mecánico de por qué falla un afinado tipo GLiNER con 35 predicados

1. **35 tipos de relación exceden el presupuesto de etiquetas de la arquitectura.** GLiREL limita a 25 etiquetas por instancia de entrenamiento; GLiNER entrena con 25 tipos por oración; Knowledgator documenta que «el rendimiento se degrada con más de 30 tipos». IEPile consulta **4 esquemas por instrucción en RE** precisamente por «disparidad de consulta de esquema» y «confusión semántica entre esquemas parecidos».
2. **Bug de la librería gliner en el enmascarado de etiquetas negativas, corregido el 2025-09-23 (PR #296).** Produce modelos que «etiquetan todo» o no aprenden nada; en el mismo hilo un usuario afinando GLiNER en español médico tenía pérdida estancada en 3,0.
3. **Sin muestreo de tipos negativos, nada funciona.** Es la ablación más grande de la literatura: UniversalNER 31,5 F1 sin negativos → 47,7 uniforme → 53,4 por frecuencia. GLiNER: 53,3 → 60,9 con 50 % de negativos (la precisión sube de 49,3 a 62,3).
4. **Desajuste silencioso de cadenas de tipo entre NER y RE** (filtros por igualdad exacta que descartan todo sin error).
5. Configuraciones de ejemplo que son pruebas de humo (`num_steps: 21` en GLiREL).

## 1. Trabajo fundacional

- **UniversalNER** (2023): ChatGPT anota 50k pasajes del Pile → 45.889 pares, 13.020 tipos; prompt abierto por tipo; **muestreo negativo por frecuencia**; alumnos LLaMA 7B/13B; con datos supervisados 53,4 → 61,8.
- **GLiNER / Pile-NER**: 44.889 pasajes, ~240k tramos; DeBERTa-v3; anchura máxima de tramo 12 palabras; 25 tipos por oración; negativos 50 %; lr 1e-5 codificador / 5e-5 cabezas; umbral 0,5. **Español zero-shot MultiCoNER: GLiNER-Multi 42,1, GLiNER-En 38,7, ChatGPT 58,7.**
- **GoLLIE** (ICLR 2024): guías de anotación como docstrings. Ablación zero-shot: **etiquetas desnudas 42,3 → guías completas 55,3**; **+5,4 solo por incluir menciones de ejemplo dentro de la guía**. Es el hallazgo más transferible del informe. Corroborado por SLIMER y SLIMER-IT (italiano).
- **IEPile** (ACL 2024): 2M instancias; `split_num` = 4 esquemas por instrucción en RE, 6 en NER; **diccionario de esquemas negativos difíciles** para que los confundibles coexistan en el mismo prompt.
- **B2NERD**: taxonomía universal de 400 tipos con estandarización de definiciones; supera a GPT-4 en 6,8–12 F1 en 6 idiomas.
- **NuNER**: 1M oraciones anotadas por GPT-3.5 → RoBERTa-base; «el tamaño y la diversidad de tipos son la clave».
- **GLiNER-BioMed**: el análogo más cercano. Maestro 70B anota 10k semillas, destila a 8B para escalar a 105k, después 19k instancias de alta calidad. +5,96 F1 sobre GLiNER v2.5-large.
- **Destilación clínica (NPJ Digital Medicine 2025)**: Llama-3.1-70B genera 634k pares; alumnos 8B/3B/1B con QLoRA; **1.000 ejemplos revisados a mano** para control; el 8B superó al maestro en varias tareas.
- Distilling Step-by-Step: 770M supera a PaLM 540B con racionales del maestro, pero demostrado en NLI/QA, no en IE de tramos.
- «Is GPT-3 a good annotator» (ACL 2023): anotar datos reales es lo correcto con espacios de etiquetas pequeños; con espacios grandes, **descomponer el esquema**.

## 2. Calidad de la plata

### 2.1 Anclaje de tramos: gratis y primero
Formato de salida del maestro (Zhan et al. 2026, 8 LLM × 4 datasets): texto marcado en línea **91,91 F1** · XML en línea 91,71 · JSON por ocurrencia 91,17 · **JSON con offsets 53,91** (anidado 34,53). **Nunca pedir offsets de caracteres al maestro**: pedir subcadenas literales y calcular offsets después; descartar lo no anclado. Alinear con normalización NFC → exacto → difuso con tope de Levenshtein → descartar.

### 2.2 Generar y luego organizar (G&O)
El LLM responde primero en lenguaje natural y después estructura su propia respuesta; mejora NER y RE zero-shot y se compone con autoconsistencia.

### 2.3 Autoconsistencia y votación
Self-Improving NER (NAACL 2024): las ganancias vienen de **elegir mejor qué anotaciones son fiables**, no de más datos («aumentar el corpus o las iteraciones no garantiza mejora»). Votación 2 de 3 sobre tramos como valor práctico por defecto.

### 2.4 Conjuntos de maestros: unión para cobertura, verificación para precisión
EL4NER: unión de tramos de tres LLM pequeños → votación de tipos → autoverificación. ACE05 69,32 vs GPT-4o 62,17. **No intersectar** (mata la cola larga); unir y verificar.

### 2.5 Extraer y verificar
Segunda llamada «¿es correcto? sí/no» por ítem (GPT-NER); Chain-of-Verification corrige solo lo falso. Para RE, verificador + refinador de racionales.

### 2.6 Filtrado por confianza
ProgGen: marcar anotaciones con log-prob < −0,02, tope del 20 %, y autocorregirlas: +1–2 F1, más precisión que cobertura. **~1.500 muestras por dataset bastan**; «anotar con precisión respecto a las definiciones de clase es el cuello de botella», cuesta 12–14 F1 frente a supervisión real. Industria: umbral ~90 % de confianza.

### 2.7 Qué ruido tienes
DS-NER (2025): las reglas/diccionarios producen **entidades sin etiquetar** (UEP); los LLM producen **tipos equivocados** (NEP). ChatGPT en CoNLL03: F1 77,47 como anotador. **El presupuesto de filtrado debe ir a verificar tipos, no a recuperar entidades faltantes.** Pérdidas robustas al ruido existen, pero el estudio controlado más reciente de pérdidas para NER multilingüe tipo GLiNER (Golde, Haller, Akbik 2026) encontró **BCE 0,575 ≈ focal 0,585 ≈ Dice 0,577**: «arregla los datos, no la pérdida».

### 2.8 Cuánto oro hace falta
- Kamath & Vajjala 2025: **100 ejemplos orgánicos (F1 0,85) superan a 4.112 sintéticos de GPT-4.1 (0,82)** en danés. (Compara texto generado vs real; acota el valor del texto sintético.)
- **GLiDRE en Re-DocRED: zero-shot 17,3; N=1 24,5; N=10 41,7; N=100 60,0; N=1000 72,1.** ~100 documentos de oro compran 60 F1 en RE de documento. Es la justificación más fuerte para 200–500 documentos corregidos por humanos.
- Orden en dos etapas: plata filtrada primero, oro después con lr menor. Lo hacen GLiNER-BioMed, GLiNER-Relex (1M sintético → 3k Gemini), gliner-multitask, Million-Label.
- **Calidad LLM vs humano depende de la tarea** (Ul Haq et al. 2025): CoNLL-2003 89,72 vs 92,12 (brecha 2,7 %); **SKILLSPAN 34,06 vs 54,79 (brecha 20,7 %)** porque las categorías blandas «no siguen estructura sintáctica ni semántica fija». **Relaciones difusas («criticó a», «aliado de») se comportan como SKILLSPAN, no como CoNLL.**
- Corregir plata es 3–5× más rápido que anotar de cero; el oro debe ser salida del maestro revisada por un periodista.

## 3. Diseño del esquema

- **Límite de tipos**: GLiREL 25; GLiNER 25 (docs: degrada con >30); IEPile 4 por instrucción en RE; gliner-multitask 30. Remedio: **consultas por lotes de 4–6 tipos semánticamente confundibles**, varias pasadas, fusión.
- **Definiciones y guías > nombres de etiqueta**: +13 F1 (GoLLIE). Escribir para cada relación un párrafo de definición en español, 3 positivos, 2 negativos cercanos y los tipos de extremo admitidos.
- **Cola larga**: todos los algoritmos rinden mal en clases con poca representación; <5 % Hits@10 con menos de 100 instancias (PCNN+ATT). Los extractores conjuntos caen «cuando hay más de 5 relaciones en una oración». Esquemas jerárquicos grueso-a-fino ayudan (EMNLP 2018); GLiNER2 soporta jerarquía pero **no la evaluó**.
- **Pipeline vs conjunto**: PURE gana 1,7–2,8 F1 a los conjuntos y es 8–16× más rápido («NER y RE necesitan representaciones distintas»); Yan & Jia 2022: el mejor conjunto supera al mejor pipeline con la misma representación de tramo, pero «conjuntos mal diseñados rinden mal»; GLiNER-Relex nació porque los errores de NER se propagaban a GLiREL. **Veredicto tras un intento fallido: pipeline en dos etapas por depurabilidad y evaluación separada; conjunto como segundo experimento.**

## 4. Recetas de afinado

### 4.1 Codificadores de tramo (familia GLiNER)

| Fuente | lr codificador | lr cabezas | lote | pasos |
|---|---|---|---|---|
| GLiNER paper | 1e-5 | 5e-5 | — | ≤30k, warmup 10 %, coseno |
| gliner-multitask etapa 2 | **5e-6** | **7e-6** | 8 | **1.000** |
| GLiNER-BioMed post | 5e-6 | 1e-5 | 4 | 10.000 |
| NERCat (catalán) | 5e-6 | 1e-5 | 8 | — |
| GLiREL | 1e-5 | 1e-4 | 8 | 20.000 |
| GLiDRE | 1e-5 | 1e-4 | 16 | 50k / 10k |
| GLiNER-Relex etapa 1 / 2 | 1e-5 / 1e-6 | igual | 8 | 1 época (1M) / 5 épocas (3k) |

Otros: weight_decay codificador 0,1, otros 0,01; dropout 0,3; `negatives` 1,0–1,5; `max_neg_type_ratio` 1; congelar el codificador para adaptación rápida. **No sobreentrenar**: una reproducción de GLiNER-large dio 61,0 en el paso 4.000 y 58,0 en el 5.000. Focal en gliner-multitask: 0,75 / 0,25. LoRA en codificadores de 100–600M: atajo de memoria, no ganancia de precisión.

### 4.2 Decodificadores ≤4B
- Los de 1–4B quedan hasta 10 F1 por debajo de los 7–8B en NER (LLaMA3.2-1B 73,3 en GENIA). Receta: LoRA r 256, α 512, todas las lineales, lr 2e-5, 2 épocas, ctx 2048, **salida XML en línea**.
- «Sub-Billion, Super-Frontier» (2026): QLoRA NF4, r 16/32/64 según tamaño, lr 1e-4, 2 épocas; **«para los sub-1B, incluir 2 demostraciones durante el afinado ayuda siempre»**. Llama-3.2-3B afinado 0,844 vs GPT-5.4 0,693; Qwen2.5-0.5B 0,83.
- LoRA ≈ full FT en NER (93,85 vs 93,61) y mitiga el olvido.

### 4.3 Mezclar datos generales con plata de dominio
- MixTune: mezcla general+dominio cuesta **2–3 F1** frente a especialistas.
- RA-IT: las ganancias saturan en **10–20k muestras** (50k añade +0,19). **Un corpus de 3k–20k documentos está en la banda productiva; el cuello es la calidad.**
- Mezclar Pile-NER con datos propios en GLiNER «no mejoró» en un caso reportado, porque la causa era el bug de enmascarado: **confirmar que la instalación es posterior al 2025-09-23**.

### 4.4 Backbone, multilingüe, español
- Golde et al. 2026 (único estudio sistemático de backbones para GLiNER multilingüe): **mmBERT 0,509 > RemBERT > mDeBERTa-v3-base > XLM-R-base > mT5-base**. Cross-encoder 0,484 > bi-encoder 0,460. Entrenar con datos multilingües supera al inglés solo (0,529 → 0,612). **Umbrales por idioma: 0,484 → 0,501**; bi-encoders óptimos en 0,2–0,3, cross en 0,4–0,5. Pero mmBERT en NER/POS «rinde igual que la generación anterior».
- EvalES (PlanTL): roberta-base-bne CoNLL 0,8851 > roberta-**large**-bne 0,8823; CAPITEL 0,8960 / 0,9051. **La escala compra casi nada en NER plano en español a este tamaño de datos.**
- **No hay cifras publicadas de NER en español para EuroBERT, mmBERT ni mDeBERTa-v3** en CoNLL-2002/CAPITEL.

## 5. RE de documento con noticias largas en español

- Límite de 512 tokens en GLiREL y GLiDRE; GLiNER `max_len` inconsistente (384 en la doc). Con más contexto: GLiNER2 2048, gliner-multitask 768, GLiNER-Relex 2048 palabras, EuroBERT 8192, MrBERT-es 8192.
- Troceo: entradilla + ventanas de 3–5 oraciones con solape; la entradilla trae los nombres completos que después se pronominalizan.
- Correferencia: resolver antes (CorefQA en pipelines de DocRE), o pedir al maestro **por cada mención el tramo literal y un id canónico** → correferencia gratis y tramos anclados. GLiREL modela correferencia como relación `SELF`.
- Formato del maestro: `{"mention": "<subcadena literal>", "canonical": "...", "type": ..., "cluster_id": ...}`; nunca offsets; normalizar NFC ambos lados.
- **Explosión cuadrática de pares**: GLiDRE y GLiNER-Relex la nombran como su primera limitación; «la precisión se degrada en pasajes densos». Mitigar con distancia máxima entre entidades y restricciones de tipo.

## 6. Evaluación

- **No usar kappa para tramos** (la clase O aplasta la estadística); usar **F1 por pares entre anotadores** con el mismo esquema de emparejamiento que se usará para el modelo. Referencias: OntoNotes ≥90 %; Re-DocRED Fleiss 0,73/0,66; **REDFM español Krippendorff α 0,61, el más bajo de sus 7 idiomas, y el mayor porcentaje de tripletas filtradas (12,5 %)**. Presupuestar adjudicación.
- Tamaño: dimensionar por la relación más rara que importe; la práctica clínica agrupa 200–250 documentos doblemente anotados; GLiDRE: 100 documentos → 60 F1. Reportar IC bootstrap al 95 %.
- Esquemas SemEval-2013 (nervaluate): estricto, exacto, parcial, tipo. Reportar estricto **y** parcial: si parcial ≫ estricto, el problema es la convención de límites, no el modelo. Trampa de seqeval: modo por defecto 1,00 vs estricto 0,00 sobre la misma predicción.
- RE: **micro-F1 excluyendo «sin relación»** (convención TACRED, 78,6 % negativos); **RE y RE+** (RE+ exige también tipos de entidad correctos); **Ign-F1** excluyendo tripletas vistas en entrenamiento (en prensa colombiana «Petro — presidente de — Colombia» estará en train y test); macro-F1 y por clase.
- **Cuánto «error del modelo» es ruido de anotación**: TACRED Revisited +8 F1 al corregir etiquetas; Re-TACRED 23,9 % de etiquetas incorrectas, +14,3 F1; Re-DocRED: **la cobertura de KD-DocRE pasó de 32,07 a 69,40 solo por completar el oro**; CoNLL-2003 5,38 % de oraciones con error. **Cuando el alumno produce una relación que no está en el oro, asumir por defecto que puede ser un falso negativo del oro hasta revisar una muestra.**
- Trampas: desalineación de offsets que descarta entidades en silencio (evaluar en caracteres); modo BIO; anidados; **convención de determinantes y títulos** («el presidente Gustavo Petro»: no hay guía española publicada, hay que fijarla; OntoNotes excluye determinantes); mayúsculas (modelos cased pierden >40 F1 en texto sin casar; **aumentar con copias en mayúsculas cuesta 0,4 pp**; titulares en versales); ruido dentro de la entidad ~9 % peor que en el contexto (MultiCoNER v2, incluye español).

## 7. Fallos conocidos de GLiNER / GLiREL

1. Instalar gliner posterior a 2025-09-23 (PR #296).
2. No usar `config_finetuning.yaml` de GLiREL; partir de `config_wiki_zsl.yaml` (20k pasos, focal α 0,3 γ 3, parada temprana, `fixed_relation_types: true`, búsqueda de umbral por macro-F1).
3. Cadenas de tipo idénticas entre NER y RE; índices inclusivos.
4. Lista de depuración del mantenedor: `fixed_relation_types: true`; anotaciones bidireccionales completas; **¿puede sobreajustar 20 ejemplos hasta F1 = 1,0?** (el mejor primer diagnóstico); índices de tokens correctos; partir de un checkpoint, no de cero.
5. `max_width` 12 palabras: una entidad de oro más larga es invisible en entrenamiento e inferencia («Ministerio de Ambiente y Desarrollo Sostenible de la República de Colombia»). GLiNER2.5 «Boundary» escapa de la rejilla.
6. Umbral global 0,5 por defecto; **sin umbrales por clase en GLiNER**; en GLiREL es una petición abierta. Con 35 relaciones desbalanceadas un umbral único cuesta varios puntos de macro-F1.
7. Focal apagado por defecto en ambas librerías. NERCat (catalán, 9.242 oraciones) lo usó (0,75 / 2) contra «tendencia a clasificar nombres comunes como entidades».
8. GLiREL: exige entidades de oro en inferencia; sus 94,2 / 83,3 no son de extremo a extremo; datos de entrenamiento con mayoría `NO_RELATION`; issue abierta con duplicados, autorrelaciones y cónyuges basura; licencia NC; poco no inglés.
9. Fragmentar etiquetas más allá del tope: issue #116 sin respuesta del mantenedor; IEPile llegó al mismo diseño desde el entrenamiento.
10. Tokenización por palabras con `\w+(?:[-_]\w+)*|\S`.
11. Para *sesgar* un modelo hacia pocos tipos bastan decenas de ejemplos; para *aprender 35 relaciones*, no. 3k–20k documentos es el orden correcto: **el fallo anterior no fue de volumen**.

## 8. Los diez errores al destilar IE a un modelo pequeño

1. Todas las etiquetas en una pasada o un prompt.
2. Entrenar solo con positivos, sin tipos negativos (31,5 → 53,4; 53,3 → 60,9).
3. Nombres de etiqueta desnudos en vez de definiciones + guías + ejemplos (42,3 → 55,3).
4. Pedir offsets al maestro (91,9 → 53,9).
5. Instalación vieja de gliner o config de humo.
6. Desajuste silencioso de cadenas de tipo.
7. Umbral global único sobre un esquema de cola larga.
8. Confiar en un oro incompleto (cobertura 32 → 69 al completar el oro; 23,9 % de TACRED mal etiquetado).
9. Convenciones de límites, mayúsculas y tokenización distintas entre maestro, oro y alumno.
10. Escalar la plata en vez de mejorarla (saturación en 10–20k; 1.500 bastan; 100 orgánicos > 4.112 sintéticos).

## 9. Pipeline recomendado por el agente

**Paso 0, cirugía de esquema**: agrupar las relaciones en 6–8 familias coherentes; definición de un párrafo en español + 3 positivos + 2 negativos cercanos + tipos de extremo por relación; fijar la convención de límites (sin determinantes ni títulos); diccionario de negativos difíciles por relación.

**Paso 1, maestro**: dos pasadas por documento: A) NER abierto estilo UniversalNER; B) RE con **una llamada por familia (4–6 relaciones + guías + negativos difíciles)** condicionada a las entidades de A. Salida: texto marcado o subcadenas literales + nombre canónico + id de clúster; nunca offsets. G&O. Trozos de ~5 oraciones con la entradilla siempre antepuesta. Pedir explícitamente pares «sin relación» a tasa controlada. Pedir logprobs si la API los da.

**Paso 2, filtrado en orden**: anclaje de tramos → validez de esquema (tipos admitidos, autorrelaciones, duplicados) → **pasada de verificación de tipo** (donde debe ir el presupuesto) → filtro de confianza (20 % más bajo) → conjunto de maestros solo para el subconjunto difícil (unión, voto de tipos, verificación).

**Paso 3, oro**: 50 documentos doblemente anotados para calibrar + 200–450 con adjudicación, todos corrigiendo salida del maestro. Partición: oro-train 200–300, oro-dev 100, oro-test 100–150. F1 por pares entre anotadores, no kappa. Priorizar la cola larga y los documentos donde los maestros discrepan.

**Paso 4, entrenamiento**: etapa 0 opcional con datos generales en español (CoNLL, CAPITEL, AnCora vía OpenNER, REDFM-es, SREDFM); etapa 1 plata (lr 1e-5 / 5e-5, lote 8, 10–20k pasos, negativos 50 %, `max_width` mayor de 12 o arquitectura Boundary); etapa 2 oro (lr 2–4× menor, ~1.000 pasos). Decodificador ≤4B como alternativa: QLoRA r 32–64, lr 1e-4, 2 épocas, XML en línea, 2 demostraciones si es sub-1B, penalización ~10 F1. BCE basta; focal solo si la cola es severa. Aumento de mayúsculas. Evaluar en dev cada 500–1.000 pasos.

**Paso 5, evaluación**: puerta de cordura (sobreajustar 20 ejemplos a F1 1,0); NER y RE por separado y luego extremo a extremo; RE y RE+; estricto y parcial; micro sin «sin relación», macro y por clase; Ign-F1; offsets de caracteres, un modo BIO, IC bootstrap; umbrales por clase barridos en dev; **inspeccionar a mano 50 «falsos positivos» antes de creer la precisión**.

**Paso 6, iterar**: aprendizaje activo sobre la cola larga por discrepancia entre maestros; parar de añadir plata cuando dev se estanque (10–20k).

## 10. No verificado

IAA de ACE 2005; cifras de Huang et al. 2022; errores de OntoNotes 5.0; guía española sobre determinantes; NER español de EuroBERT/mmBERT/mDeBERTa; efecto de quitar tildes; F1 por idioma de mREBEL; receta oficial de fragmentación de etiquetas en GLiNER; umbrales por clase en GLiNER; que `max_width` 12 descarte entidades largas (derivado del diseño); omitir `no_relation` en GLiREL; que el español de GLiNER supere al inglés (la tabla del paper lo contradice); Euro-GLiNER-x / FiNERweb en español; Distilling Step-by-Step en IE; CanDist en IE.
