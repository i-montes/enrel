# enrel: modelo abierto de entidades y relaciones para noticias en español

Especificación de diseño. Fecha: 2026-09-16. Estado: aprobado en conversación, pendiente de revisión final del usuario.

## 1. Propósito y alcance

enrel es un modelo open source que, dado un artículo de prensa en español, devuelve sus entidades (personas, organizaciones, lugares, cargos, normas, obras, montos), las agrupa por identidad dentro del artículo y extrae las relaciones de poder que el texto afirma entre ellas. Está pensado para que los laboratorios de medios construyan grafos, Graph RAG, hipervínculos automáticos y asistentes internos sin depender de una API externa.

Restricciones que gobiernan todo el diseño:

- Debe correr en el computador de una redacción: CPU de 4 núcleos tipo Intel i5, 16 GB de RAM, sin GPU. Meta: menos de 5 segundos por artículo de 1.000 palabras y menos de 2 GB de memoria residente.
- Debe ser bueno de verdad en relaciones. El intento anterior (legajo) se quedó en F1 0,47 a 0,52 porque el maestro que lo enseñaba solo llegaba a 0,47 a 0,53 contra el oro. Este diseño mide el techo del maestro antes de destilar y no entrena si el techo no alcanza.
- Licencia Apache-2.0 para código y pesos. Solo se usan backbones, librerías y datasets con licencia compatible con uso comercial.
- Primera versión con datos de La Silla Vacía. Otros medios, en una fase posterior fuera de este documento.

Fuera de alcance de la v0.1: enlazado a Wikidata, correferencia entre artículos, resolución de identidades entre documentos, interfaz gráfica, modelos para otros idiomas. Estas cosas se apoyan en la salida de enrel, no forman parte de él.

## 2. Decisiones tomadas y por qué

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| Esquema rediseñado a 17 relaciones con definiciones excluyentes, alineado a FollowTheMoney y Wikidata | Mantener los 35 predicados de legajo | Los predicados que fallaban (parte de, miembro de, trabaja en, aliado de, opositor de, apoyó a) fallaban por solapamiento, no por rareza: dos anotadores LLM coincidían en 0,18 para «parte de». El español tuvo el acuerdo entre anotadores más bajo de los siete idiomas de REDFM. Menos solape, más acuerdo, techo más alto. |
| Codificador con cabezas propias (pipeline cerrado) | GLiNER afinado; LLM pequeño | Tres estudios de 2026 muestran que un codificador de 110 a 125M iguala o supera a LLM afinados de 14 a 70B en RE de esquema cerrado, y que los LLM empeoran con la densidad del grafo. En CPU, un codificador procesa 100k artículos en días; un LLM de 1B en semanas. GLiNER tiene tope de 25 a 30 etiquetas, sigmoides sin competencia, sin umbral por clase, tramo máximo de 12 palabras, y su backbone mDeBERTa no se cuantiza. |
| Backbone MrBERT-es (BSC-LT, 150M, ModernBERT, 8.192 tokens, Apache-2.0) | mDeBERTa-v3-base, XLM-R-base, mmBERT | Mejor NER en español publicado entre los pequeños (87,77 CoNLL-2002). Contexto de 8.192 tokens: un artículo entero entra en una pasada, lo que resuelve las relaciones que cruzan párrafos. Vocabulario podado a 51k, la mitad de parámetros que los multilingües. Se cuantiza. Riesgo: nuevo (diciembre de 2025) y sin extracción construida encima; la etapa 0 lo verifica en un día. |
| Nivel de documento entero, no párrafo | Párrafo aislado (legajo) | El 40,7 % de los hechos de DocRED necesitan varias oraciones; en español con sujeto elidido y roles («el mandatario») es más. Los perfiles del Quién es Quién casi nunca nombran al sujeto en el cuerpo. |
| MiniMax como anotador y verificador, cinco llamadas por artículo | Un solo prompt con 35 predicados; segundo maestro | Definiciones con ejemplos en el prompt valen +13 F1 (GoLLIE); consultar 5 o 6 relaciones por llamada evita la confusión entre esquemas parecidos (IEPile); la verificación ataca el ruido dominante de los LLM, que es de tipo equivocado. Un segundo maestro se suma solo si el primero no pasa la puerta. |
| Oro corregido por el usuario, 15 a 25 horas | Periodistas; ningún oro | Es lo disponible. Se concentra donde nada lo sustituye: el conjunto de prueba congelado. |
| Título antepuesto al cuerpo en todos los documentos | Cuerpo solo | En perfiles y en muchas noticias el sujeto principal aparece nombrado en el título y elidido en el cuerpo. |

## 3. Esquema

### 3.1 Tipos de entidad

Los siete de legajo, para conservar el oro existente. Se admite anidamiento entre tipos distintos («Antioquia» dentro de «Gobernador de Antioquia»); no entre el mismo tipo.

| Tipo | Se marca | No se marca |
|---|---|---|
| persona | nombre propio de una persona, con o sin apellidos; apodos si individualizan | pronombres, roles sueltos («la experta»), gentilicios, grupos («los indígenas») |
| organizacion | institución, empresa, partido, movimiento, medio, colectivo con nombre | «el Estado», «el gobierno», «las empresas» sin nombre |
| lugar | nombre propio de lugar: país, departamento, municipio, barrio, sede física con nombre | «el país», «la región» |
| cargo | cargo, puesto o título, con o sin titular: «ministro de Hacienda», «senador», «Gobernador de Antioquia» | oficios genéricos («abogado», «periodista») salvo como cargo institucional |
| norma | ley, decreto, sentencia, acto, tratado identificable: «Ley 1448 de 2011», «Acuerdo de Paz» | «la ley», «un decreto» |
| obra | título de libro, informe, columna, programa, medio impreso o digital como producto | «el informe», «un libro» |
| monto | cantidad con cifra: «10 mil millones de pesos», «30 %» | «recursos», «plata» |

Convenciones de límites, fijadas y escritas en la guía de anotación:

- Sin artículos ni determinantes: «Petro», no «el Petro»; «Fiscalía», no «la Fiscalía».
- La persona nunca incluye su cargo ni título: en «el exvicepresidente Germán Vargas Lleras» hay dos marcas, cargo «exvicepresidente» y persona «Germán Vargas Lleras».
- Un cargo incluye su complemento institucional o geográfico cuando lo tiene: «ministro de Hacienda», «alcalde de Medellín». El lugar u organización dentro se marca además como entidad anidada.
- Los nombres se copian exactamente como aparecen, con sus tildes y mayúsculas.
- Los tramos son de caracteres sobre el texto normalizado a NFC; nunca índices de tokens.

### 3.2 Relaciones

Diecisiete relaciones tipadas más una de reserva. Cada una tiene dominio y rango por tipo, y en la guía de anotación un párrafo de definición, tres ejemplos positivos y dos negativos cercanos en español. Las relaciones son excluyentes para un mismo par: se elige la más específica que el texto afirme.

| Relación | De → a | Simétrica | Atributo | Absorbe de legajo | FollowTheMoney / Wikidata |
|---|---|---|---|---|---|
| ocupa_cargo | persona → cargo | no | estado: actual, anterior, aspirante | ocupa el cargo, aspira a, renunció a | Occupancy / P39 |
| nombro_a | persona, organizacion → persona | no | — | nombró a | — / P748 |
| sucedio_a | persona → persona | no | — | sucedió a | Succession / P1365 |
| miembro_de | persona → organizacion | no | — | miembro de; parte de (persona→org) | Membership / P102, P463 |
| trabaja_en | persona → organizacion | no | — | trabaja en, asesor de | Employment / P108 |
| dirige | persona → organizacion | no | — | dirige | Directorship / P1037, P169, P488 |
| fundo | persona, organizacion → organizacion | no | — | fundó | — / P112 |
| propietario_de | persona, organizacion → organizacion | no | — | dueño de; socio de (persona→org) | Ownership / P127, P1830 |
| socio_de | persona ↔ persona | sí | — | socio de (persona↔persona) | Associate / P1327 |
| parte_de | organizacion → organizacion | no | — | parte de (org→org) | — / P749, P355 |
| familiar_de | persona ↔ persona | según parentesco | parentesco: conyuge (sim.), hijo_de (dirigida: cabeza es hijo), hermano (sim.), otro (sim.) | padre o madre de, hijo de, hermano de, cónyuge o pareja de, familiar de | Family / P26, P40, P22, P25, P3373, P1038 |
| financia_a | persona, organizacion → persona, organizacion | no | — | financia a, donó a | Payment / P859 |
| contrato_a | organizacion, persona → organizacion, persona | no | — | contrató a | ContractAward |
| investigado_por | persona, organizacion → organizacion | no | etapa: investigado, acusado, condenado | investigado por, acusado de, condenado por | CourtCaseParty / P1399 |
| ubicado_en | persona, organizacion, lugar → lugar | no | — | ubicado en | — / P159, P551, P131 |
| apoya_a | persona, organizacion → persona, organizacion, cargo | no | — | apoyó a, aliado de | — |
| se_opone_a | persona, organizacion → persona, organizacion | no | — | opositor de, criticó a | — |
| vinculo_sin_tipo | cualquiera ↔ cualquiera | sí | — | se reunió con, demandó a, y lo que no encaja | UnknownLink |

Reglas de desambiguación que van a la guía y al prompt:

- ocupa_cargo exige un cargo como objeto. Si el texto da el cargo, es ocupa_cargo y no trabaja_en. «Alcaldesa de Bogotá» produce ocupa_cargo (persona→cargo) y dirige (persona→«Alcaldía de Bogotá») solo si la organización está mencionada.
- estado de ocupa_cargo: «actual» si el texto habla en presente o no marca fin; «anterior» con «ex», «fue», «entonces», «hasta»; «aspirante» con «candidato», «aspira», «precandidato».
- miembro_de es pertenencia sin empleo: militancia en un partido o movimiento, membresía de una junta, comisión o colectivo. Un adjetivo de afiliación («el liberal X») no basta; hace falta que el texto afirme la pertenencia.
- trabaja_en es empleo o asesoría en una organización que no es partido, sin cargo nombrado. Si hay cargo, ocupa_cargo. Si dirige, dirige.
- parte_de solo entre organizaciones («la Facultad es parte de la Universidad», «filial de»). Una persona nunca es parte_de.
- ubicado_en solo para sede o residencia afirmada, o contención geográfica (municipio en departamento). El origen («el caleño X», «de Popayán») y el lugar de los hechos no cuentan.
- apoya_a y se_opone_a exigen una afirmación explícita de respaldo u oposición, no coocurrencia ni inferencia.
- Solo se marca lo que el texto afirma. «Habría», «se dice que», «según fuentes» sin afirmación: no se marca.
- Las simétricas se anotan una sola vez; el exportador las duplica si el entrenamiento lo requiere.
- hijo_de se anota con la cabeza en el hijo; padre o madre se deriva. Nunca se anotan las dos direcciones.

Clases finas del clasificador: las 17 relaciones se despliegan en 24 clases finas (ocupa_cargo ×3 estados, familiar_de ×4 parentescos, investigado_por ×3 etapas, las otras 14 tal cual) más vinculo_sin_tipo. Se evalúa a los dos niveles.

Puertas por relación: una relación se publica en el modelo cuando cumple dos condiciones, medidas al final de la etapa 2: al menos 60 ejemplos positivos en entrenamiento tras filtros, y acuerdo entre el oro humano y el maestro ≥ 0,70 F1 en la prueba. La que no cumpla se entrena igual pero en inferencia se colapsa a vinculo_sin_tipo, y se documenta. apoya_a y se_opone_a son las candidatas a caer.

### 3.3 Mapeo desde los 35 predicados de legajo

Se aplica automáticamente al oro y a la plata existentes (`enrel/esquema/mapeo_legajo.py`). El oro de legajo trae 125 artículos con 5.509 menciones y 1.548 relaciones; el tipo `cargo*` (180 marcas, la designación sin nombre de legajo, «el Gobernador de Antioquia») se mapea a `cargo`. Reglas: los predicados con destino único se traducen directo; «parte de» se reparte por tipos de extremo (persona→org a miembro_de, org→org a parte_de, otros a vinculo_sin_tipo); «socio de» se reparte por tipos; «hijo de» conserva dirección y «padre o madre de» se invierte a hijo_de; «asesor de» persona→persona va a vinculo_sin_tipo; «citado en», «autor de», «destinado a», «sanciona con», «se reunió con», «demandó a» van a vinculo_sin_tipo. El mapeo se registra por relación para poder auditar qué vino de dónde.

## 4. Arquitectura del modelo

Un codificador y dos cabezas, sobre el documento entero en una pasada.

### 4.1 Backbone

`BSC-LT/MrBERT-es`: ModernBERT, 22 capas, dimensión 768, atención local cada capa y global cada tres, 8.192 posiciones, vocabulario de 51.200, 150M de parámetros, Apache-2.0. Se carga con `transformers` (arquitectura `modernbert`). Respaldo, si la etapa 0 lo descalifica: `jhu-clsp/mmBERT-small` (140M, 8.192, MIT) y, como segundo respaldo, `FacebookAI/xlm-roberta-base` con ventanas de 512 y solape.

Entrada: `titulo + "\n\n" + cuerpo`, normalizado a NFC, tokenizado sin truncar hasta 8.192 tokens. Los documentos más largos se procesan por ventanas de 8.192 con solape de 512 y se fusionan las menciones por offset; son menos del 1 % del archivo.

### 4.2 Cabeza de entidades

Clasificación de tramos. Para cada tramo de 1 a 16 palabras se construye una representación a partir de los estados de la primera y la última subpalabra más una codificación de la anchura, y se clasifica en 8 clases (7 tipos más «ninguno»). Trabaja sobre palabras, no sobre subpalabras, con la partición `\w+(?:[-_]\w+)*|\S` y offsets de caracteres. Permite anidamiento entre tipos distintos. Decodificación: se aceptan los tramos con probabilidad máxima en una clase distinta de «ninguno»; entre tramos solapados del mismo tipo gana el de mayor probabilidad. Negativos: durante el entrenamiento se muestrean tramos «ninguno» en proporción fija a los positivos (inicial 8:1).

### 4.3 Agrupación de menciones en entidades

Reglas, no modelo, en `enrel/inferencia/agrupar.py`:

1. Misma cadena normalizada (NFC, minúsculas, sin tildes, espacios colapsados) y mismo tipo.
2. Personas: una mención es forma corta de otra si sus palabras aparecen en orden dentro de la larga («Carlos Galán» dentro de «Carlos Fernando Galán») y la primera palabra coincide (la forma corta conserva el primer nombre), con un único candidato largo, o si es un solo apellido que aparece como último apellido en una sola persona del documento.
3. Organizaciones: sigla y forma larga si la sigla coincide con las iniciales de las palabras con mayúscula de la forma larga; forma corta contenida en la larga.
4. Cargos, normas, montos y obras solo por regla 1.
5. Diccionario opcional de alias (los perfiles de Quién-AI, 21.253 nombres normalizados) que el usuario puede cargar o no.

En entrenamiento los grupos vienen del identificador canónico que asigna el maestro, validado contra estas reglas: si el maestro une dos menciones que las reglas separan, se conserva la unión del maestro pero se cuenta.

### 4.4 Cabeza de relaciones

Para cada par ordenado de grupos (cabeza, cola) de tipos admitidos por al menos una relación:

- Representación de cada grupo: logsumexp sobre las representaciones de sus menciones (estado de la primera subpalabra de cada mención).
- Contexto local del par: agregación de los estados del documento ponderada por la atención que las menciones de cabeza y cola prestan a cada posición, tomada de la última capa del codificador (la técnica de ATLOP, sin parámetros extra).
- Clasificador: proyecciones de cabeza y cola concatenadas con el contexto, bilineal agrupado (grupos de 64), salida de 25 logits (24 clases finas más vinculo_sin_tipo) más un logit de umbral aprendido.
- Máscara de tipos: los logits de las relaciones que no admiten el par de tipos se fijan a −∞ antes de la pérdida y de la decodificación.
- Pérdida: umbral adaptativo (una clase TH por par; las positivas deben superar a TH y TH debe superar a las negativas) con reponderación focal adaptativa para la cola larga (KD-DocRE). Sin umbral global que calibrar.
- Decodificación: toda clase con logit mayor que TH es positiva; si ninguna lo supera, no hay relación. Las simétricas se colapsan a una fila. Se devuelve la confianza como sigmoide de la diferencia con TH.
- Evidencia: la oración con mayor peso en la agregación de contexto del par se devuelve como evidencia.

Tope de grupos por documento: 60. Si hay más, se conservan los 60 con más menciones y se registra el recorte.

### 4.5 Salida

JSON por documento, offsets de caracteres sobre el texto de entrada:

```json
{
  "doc_id": "wp:32061",
  "texto_hash": "sha256…",
  "menciones": [{"id": "m1", "ini": 88, "fin": 99, "texto": "Tomás Uribe", "tipo": "persona", "grupo": "e1", "confianza": 0.98}],
  "grupos": [{"id": "e1", "tipo": "persona", "canonico": "Tomás Uribe", "menciones": ["m1", "m7"]}],
  "relaciones": [{"cabeza": "e1", "cola": "e2", "relacion": "familiar_de", "atributo": "hijo_de", "confianza": 0.91, "evidencia": {"ini": 60, "fin": 140}}],
  "modelo": "enrel-base-es-0.1", "esquema": "0.1"
}
```

Un exportador convierte esta salida a entidades y aristas de FollowTheMoney con `sourceUrl`, `proof` (la evidencia) y `retrievedAt`.

### 4.6 Exportación e inferencia

- ONNX del codificador más las dos cabezas, opset 17. Cuantización dinámica int8 de las capas lineales. Se compara fp32, fp16 e int8 en la prueba: si int8 pierde más de 1 punto de F1 en entidades o 2 en relaciones, se publica fp16 como predeterminado.
- Inferencia en Python con ONNX Runtime. Un motor en Rust queda fuera de la v0.1 y anotado como mejora.
- Medición de rendimiento en la máquina de desarrollo con `taskset` a 4 hilos, sobre 200 artículos de la prueba: segundos por artículo y memoria residente máxima. Meta: mediana < 5 s por 1.000 palabras, RSS < 2 GB.

## 5. Datos

### 5.1 Corpus

La base local de legajo: `~/.local/share/com.legajo.app/legajo.sqlite`, tablas `articles` (wp_id, text_plain, word_count) y `census` (date, link, title). Al 2026-09-16 tiene 81.103 artículos con texto. Secciones principales: en-vivo 33.961, silla-nacional 20.600, red-de-expertos 12.432, detector-de-mentiras 6.070, opinion 3.582, quien-es-quien 1.163, silla-amazonia 1.322, silla-academica 332.

El corpus se lee una vez y se congela en `datos/corpus/articulos.jsonl` con: doc_id, url, fecha, seccion, titulo, texto (título antepuesto), palabras, hash. Se excluyen transcripciones (más del 60 % de párrafos de una sola línea) y artículos de menos de 150 palabras.

### 5.2 Conjuntos y muestreo

Todo se fija por `doc_id` antes de anotar nada, con semilla registrada, y el exportador aborta si un documento de prueba o desarrollo aparece en entrenamiento.

| Conjunto | Tamaño | Origen | Uso |
|---|---|---|---|
| prueba | 50 artículos | los 50 de `prueba.txt` de legajo, mapeados al esquema y corregidos por el usuario; todos tienen texto en la base local | la cifra que se publica; congelado; nunca se mira durante el desarrollo salvo para la evaluación final de cada etapa |
| prueba-dirigida | 15 artículos de oro-perfiles | los perfiles del Quién es Quién concentran las relaciones raras en la prueba (familiar_de, fundo, socio_de, propietario_de, nombro_a, sucedio_a) | cifras por relación de las raras, reportadas aparte y nunca mezcladas con la cifra global |
| oro-perfiles | 40 artículos de quien-es-quien | corregidos por el usuario en la capa de revisión de legajo, sobre propuestas del modelo afinado anterior; exportados de `legajo.sqlite` y mapeados | se reparten: 15 a prueba-dirigida, 10 a desarrollo, 15 a oro-entrenamiento; el reparto se fija por doc_id con semilla antes de mirar las anotaciones |
| desarrollo | 20 artículos | 10 de oro-perfiles y 10 de silla-nacional corregidos por el usuario | elegir hiperparámetros y parar |
| oro-entrenamiento | 15 a 45 artículos, según horas | 15 de oro-perfiles más lo que el tiempo permita | segunda etapa de entrenamiento |
| plata-alta | 75 artículos | los 125 de oro de legajo menos los 50 de prueba, mapeados; son correcciones mayormente de LLM | entrenamiento, marcados como plata-alta |
| plata | 3.500 artículos | tres estratos, descritos abajo: dirigido por relación (2.000), perfiles (400) y aleatorio estratificado (1.100); 150 a 2.000 palabras | entrenamiento principal |
| humo-maestro | 30 artículos de plata | al azar | probar el prompt antes de la puerta |

Los perfiles del Quién es Quién son densos en cargos, parentescos y empresas, por eso pesan más en el oro. Como su registro es biográfico y no noticioso, la prueba se mantiene en noticias para que la cifra publicada refleje el uso real.

**Muestreo de la plata en tres estratos.** El objetivo es que cada relación tenga ejemplos suficientes para aprenderse (la puerta de 60 positivos de 3.2), sin que la distribución se aleje tanto de la real que el modelo aprenda que todo artículo tiene relaciones.

1. **Dirigido por relación, 2.000 artículos.** Para cada una de las 17 relaciones hay un léxico de disparadores en `enrel/corpus/disparadores.py` (verbos, sustantivos de parentesco, fórmulas: «nombró a», «reemplazó a», «fundador», «accionista», «socio de», «filial», «esposa», «financió», «licitación», «imputado», «con sede en», «respaldó», «se opone»). Se toman hasta 120 artículos por relación entre los que contienen al menos un disparador, priorizando los que contienen disparadores de varias relaciones. Dos fuentes con localización ya hecha se aprovechan como disparadores de máxima precisión: `alineado.jsonl` de Quién-AI para familiar_de (unas 2.350 relaciones familiares con cita literal) y `cargos.jsonl` para ocupa_cargo. Medido sobre el archivo, todas las relaciones tienen miles de candidatos salvo ubicado_en (437 con «con sede en»), así que la cuota se cumple en todas.
2. **Perfiles, 400 artículos** de quien-es-quien, por tercios de año.
3. **Aleatorio estratificado, 1.100 artículos**, por sección en proporción al archivo (en-vivo, silla-nacional, red-de-expertos, detector-de-mentiras, opinion, regiones) y por tercios de año, incluyendo artículos sin ningún disparador. Este estrato es el que enseña al modelo a no ver relaciones donde no las hay, y el que mantiene el registro corto de en-vivo (224 palabras de media) en el entrenamiento.

Tras la anotación de la plata se cuentan los positivos por relación fina. Si alguna queda por debajo de 60, se hace una segunda ronda dirigida solo para ella, hasta 300 artículos más en total. La tabla de positivos por relación y por estrato va al informe de la etapa 2.

### 5.3 El maestro

Modelo: el MiniMax disponible por API compatible con OpenAI, sin razonamiento, temperatura 0, JSON estricto. Cliente reanudable que guarda cada respuesta cruda con su prompt, versión, tokens y segundos. Cinco llamadas por artículo:

**Llamada 1, entidades.** Entrada: el texto completo con el título. Salida: lista de menciones `{"texto": literal, "tipo", "entidad": identificador canónico}`. El prompt lleva la tabla de tipos con qué se marca y qué no, las convenciones de límites y la instrucción de copiar el texto exactamente. Nunca se piden offsets.

**Llamadas 2 a 4, relaciones por familia.** Entrada: el texto, la lista de entidades de la llamada 1 con sus identificadores, y la familia:

- Familia A, cargos y trabajo: ocupa_cargo (con estado), nombro_a, sucedio_a, trabaja_en, dirige, miembro_de.
- Familia B, empresa y dinero: fundo, propietario_de, socio_de, parte_de, contrato_a, financia_a.
- Familia C, familia, política, justicia y lugar: familiar_de (con parentesco), apoya_a, se_opone_a, investigado_por (con etapa), ubicado_en.

Cada prompt lleva solo sus 5 o 6 relaciones con definición, tipos admitidos, tres positivos y dos negativos cercanos, y la lista de confusiones frecuentes con la relación correcta. Salida: `{"cabeza": id, "cola": id, "relacion", "atributo", "cita": subcadena literal}`. También puede devolver `vinculo_sin_tipo` cuando ve un vínculo que no encaja.

**Llamada 5, verificación.** Entrada: el texto y todas las relaciones propuestas, cada una con su cita. Pregunta por cada una: ¿el texto afirma exactamente esto entre estas dos entidades, con esta relación y dirección? Salida: `confirmada`, `rechazada` con motivo, o `corregida` con la relación correcta. Solo entran a la plata las confirmadas o corregidas.

Filtros a la salida, en orden, con contadores por corrida:

1. Anclaje: cada mención y cada cita se localiza en el texto (exacta, luego normalizada, luego difusa con tope de 1 error por 5 caracteres); lo no anclado se descarta.
2. Tipos admitidos por relación; sin autorrelaciones; sin duplicados; simétricas colapsadas.
3. Identificadores canónicos validados contra las reglas de agrupación de 4.3.
4. Rechazo de la verificación.
5. Reglas de legajo que siguen valiendo: un monto lleva cifra; un pronombre no es persona; una etiqueta de hablante al inicio de párrafo no es mención.

**La puerta.** Antes de anotar los 3.500, el maestro corre sobre los 50 de prueba ya corregidos por el usuario. Criterio para seguir: entidades F1 estricto ≥ 0,90; relaciones RE+ (extremos por solape, relación gruesa correcta) ≥ 0,75; dirección correcta ≥ 0,95 en las asimétricas. Si no se cumple, se revisan los 30 errores más frecuentes, se ajustan definiciones y ejemplos, y se repite. Tres iteraciones como máximo antes de decidir si se retira alguna relación del esquema o se suma un segundo maestro. La tabla de cada iteración se guarda en `docs/maestro/puerta-<fecha>.md`.

Costo estimado: 3.500 artículos × 5 llamadas × unos 3 segundos con 4 hilos concurrentes, alrededor de 4 a 6 horas de pared, más la cuota de tokens: unos 2.500 tokens de entrada por llamada, del orden de 45 millones de tokens de entrada en total.

### 5.4 Formato interno de documento anotado

Un JSONL por conjunto en `datos/anotado/<conjunto>.jsonl`, una fila por documento:

```json
{
  "doc_id": "wp:32061", "url": "…", "fecha": "2010-05-03", "seccion": "silla-nacional",
  "texto": "Título\n\nCuerpo…",
  "menciones": [{"id": "m1", "ini": 88, "fin": 99, "texto": "Tomás Uribe", "tipo": "persona", "grupo": "e1"}],
  "grupos": [{"id": "e1", "tipo": "persona", "canonico": "Tomás Uribe"}],
  "relaciones": [{"cabeza": "e1", "cola": "e2", "relacion": "familiar_de", "atributo": "hijo_de", "evidencia": {"ini": 60, "fin": 140}}],
  "fuente": "oro | plata-alta | plata", "origen": {"maestro": "MiniMax-M3", "prompt": "1.0", "mapeo_legajo": true}
}
```

Validador que aborta la exportación: offsets dentro del texto y coincidentes con `texto` de la mención; tipos en el esquema; relaciones con tipos admitidos; sin documentos de prueba ni desarrollo en entrenamiento; hash SHA-256 de cada fichero en el informe.

### 5.5 Datos externos

Opcionales, para un experimento de precalentamiento de la cabeza de relaciones, no para la receta principal: la rebanada española de SREDFM filtrada a los identificadores de Wikidata de la tabla 3.2 y REDFM-es (CC BY-SA 4.0), y CoNLL-2002 español para entidades. Se documenta si se usan y se miden con y sin. No se usan MultiNERD, WikiNEuRal, mREBEL ni GLiREL por licencia.

## 6. Oro y anotación

Herramienta principal: la capa de revisión de legajo (paso 6), que el usuario ya domina. Las propuestas las pone el modelo afinado anterior de legajo, que saca bien las entidades; el usuario corrige tramos y tipos, resuelve identidades con `=` y arregla las relaciones, que es lo que estaba mal. El oro queda en las tablas `anotaciones`, `relaciones`, `resoluciones` y `tiempos` de `legajo.sqlite`, con el vocabulario de 35 predicados y el campo `cuando`.

Exportador `enrel/anotacion/desde_legajo.py`: lee un lote de `legajo.sqlite` (ruta configurable, porque el usuario anota en el Mac o en el PC) o los JSON por artículo del formato de `oro_apartado.py`, aplica el mapeo de 3.3, convierte `cuando` (vigente → actual, pasada → anterior; «aspira a» → aspirante), toma los grupos de `resoluciones` («misma») y de las menciones repetidas, recompone el documento entero a partir de los párrafos con offsets globales, valida y escribe el formato interno. Prueba de ida y vuelta sobre los 125 artículos de oro existentes.

Límite conocido de esta vía: la revisión de legajo trabaja por párrafo, así que las relaciones cuyos extremos están en párrafos distintos no se pueden marcar. En la evaluación, una relación correcta del modelo que cruce párrafos aparecerá como falso positivo; la revisión manual de 50 falsos positivos de 8 la cuantifica y se reporta. Label Studio queda como herramienta opcional para una pasada posterior a nivel de documento, si esa cifra resulta alta.

Convenciones que el usuario sigue al anotar en legajo para que el mapeo sea sin pérdidas (van también en la guía):

1. Persona y cargo siempre separados, unidos por «ocupa el cargo»; `cuando` correcto, porque se convierte en el estado de ocupa_cargo; candidaturas con «aspira a».
2. Parentescos con el predicado fino («hijo de» con la cabeza en el hijo, «hermano de», «cónyuge o pareja de»); «familiar de» solo para tíos, primos, sobrinos, cuñados, suegros y similares. «Padre o madre de» se puede usar, el mapeo lo invierte.
3. «Parte de» solo organización → organización; pertenencia de persona a partido, junta o colectivo con «miembro de»; empleo sin cargo nombrado con «trabaja en»; «asesor de» solo persona → organización.
4. «Dueño de» y «socio de» persona → organización van a propietario_de; «socio de» persona ↔ persona se conserva como socio_de.
5. «Ubicado en» solo para sede, residencia o contención geográfica, nunca para origen ni lugar de los hechos.
6. No gastar tiempo en «se reunió con», «citado en», «autor de», «destinado a», «sanciona con» ni «demandó a»: se mapean a vinculo_sin_tipo.
7. «Apoyó a» y «aliado de» son lo mismo (apoya_a); «opositor de» y «criticó a» son lo mismo (se_opone_a). Solo si el texto lo afirma de forma explícita.
8. Marcar todas las apariciones de cada entidad y resolver identidades con `=`, porque de ahí salen los grupos.

Reparto de las horas del usuario, en orden de prioridad:

1. Oro-perfiles: 40 artículos del Quién es Quién, unas 8 horas a 12 minutos por artículo. Ya en marcha.
2. Prueba: los 50 artículos de `prueba.txt`, unas 8 horas. Ya tienen una corrección previa (mayormente de LLM); la pasada del usuario se concentra en relaciones y en lo que falta.
3. Desarrollo: los 10 de silla-nacional, unas 2 horas.
4. Oro de entrenamiento adicional: lo que el tiempo permita.

Con 15 horas se hacen 1 y casi toda 2; con 25, 1 a 3 y parte de 4. Los 40 perfiles sirven para probar el mapeo, el exportador y la evaluación desde la etapa 0, antes de que exista el maestro.

Medida de anclaje: 3 artículos de la prueba se anotan en blanco antes de ver la propuesta y después se corrigen; la diferencia se reporta como cota del sesgo de corrección.

La guía de anotación (`docs/guia-anotacion.md`) es el mismo texto que alimenta los prompts del maestro: definiciones, ejemplos, convenciones de límites y reglas de desambiguación. Una sola fuente para humano y máquina.

## 7. Entrenamiento

Entorno propio en `.venv` del repo, con Python 3.12 gestionado por `uv` (el sistema trae 3.14, para el que no todas las ruedas de CUDA existen), torch con CUDA para la RTX 4060, `transformers` con soporte de ModernBERT, `onnxruntime`. Label Studio en un entorno aparte para no mezclar dependencias. Versiones fijadas en `pyproject.toml`.

Receta inicial, ajustable en desarrollo:

| | Etapa 1, plata | Etapa 2, oro |
|---|---|---|
| Datos | plata 3.500 + plata-alta 75 | oro-entrenamiento 20 a 50 + plata-alta 75, y un 20 % de la plata como ancla |
| Punto de partida | MrBERT-es | mejor checkpoint de etapa 1 |
| lr codificador / cabezas | 3e-5 / 1e-4 | 1e-5 / 3e-5 |
| Lote | 2 documentos × acumulación 8 | igual |
| Longitud máxima en entrenamiento | 4.096 tokens (los documentos más largos se recortan al final) | igual |
| Épocas | hasta 8, parada por RE+ F1 en desarrollo, paciencia 2 | hasta 4 |
| Precisión | bf16 con gradient checkpointing | igual |
| Pérdidas | entidades: entropía cruzada sobre tramos con negativos 8:1; relaciones: umbral adaptativo + focal adaptativa | igual |
| Semillas | 42 y 7; se reporta media y diferencia | igual |

Cada corrida escribe en `corridas/<fecha>-<nombre>/`: configuración, hashes de los datos, métricas por época, checkpoint final, y la evaluación completa. Comprobación de cordura antes de cualquier corrida larga: el modelo debe sobreajustar 20 documentos hasta F1 1,0 en entidades y relaciones; si no, el problema está en los datos o en el código.

Presupuesto de memoria: MrBERT-es a 4.096 tokens, lote 2, bf16 y checkpointing cabe en 8 GB de VRAM según la aritmética (activaciones del orden de 2 a 3 GB); se verifica en la etapa 0 con un documento sintético de 4.096 tokens. Si no cabe: lote 1 con acumulación 16, o 3.072 tokens.

## 8. Evaluación

Herramienta única, `enrel/evaluacion/`, que produce la misma tabla para el maestro, la línea base y el modelo.

Entidades:
- Estricto (tramo exacto y tipo) y parcial (solape y tipo), P, R, F1 por tipo y global.
- Sobre offsets de caracteres, con un solo esquema de emparejamiento documentado.

Relaciones:
- RE: extremos correctos por solape de menciones de sus grupos, relación gruesa correcta, dirección correcta. RE+: además tipos de entidad correctos. Relación fina como tercera columna.
- Micro-F1 excluyendo «sin relación»; macro-F1; P, R, F1 por relación.
- Ign-F1: se excluyen las tripletas (canónico cabeza, relación, canónico cola) que aparecen en entrenamiento.
- Dirección: porcentaje de asimétricas con dirección correcta entre las que aciertan par y relación.
- Por relación solo se publica F1 cuando la prueba tiene al menos 10 casos de esa relación; por debajo se reporta el conteo y «insuficiente». El oro de legajo mapeado a la prueba tiene 579 relaciones, de las que 264 son ocupa_cargo y varias relaciones quedan con menos de 10 (familiar_de ~19 en total, financia_a 1, contrato_a 3, fundo 2, sucedio_a 6, nombro_a 7); de ahí el conjunto prueba-dirigida opcional.

Siempre:
- Intervalos de confianza al 95 % por bootstrap sobre documentos.
- Tres filas obligatorias en la misma tabla: línea base zero-shot (`fastino/gliner2.5-multi-v1` con el esquema en lenguaje natural), techo del maestro (sus anotaciones de la prueba antes de la corrección), y el modelo.
- Revisión manual de 50 falsos positivos de relaciones del modelo en la prueba antes de publicar la precisión: se reporta cuántos eran en realidad omisiones del oro.
- Rendimiento en CPU (4 hilos) y memoria, y el tamaño de los pesos en disco.

Metas de la v0.1 sobre la prueba, con la línea base y el techo al lado:

| Métrica | Meta | Referencia |
|---|---|---|
| Entidades F1 estricto | ≥ 0,88 | legajo 0,86 a 0,88 con solape |
| Relaciones RE+ gruesa micro-F1 | ≥ 0,60 | legajo 0,47 a 0,52; techo del maestro debe ser ≥ 0,75 |
| Relaciones macro-F1 gruesa | ≥ 0,50 | — |
| Dirección correcta | ≥ 0,95 | legajo 0,97 |
| Segundos por 1.000 palabras, CPU 4 hilos | < 5 | GLiNER-relex en CPU: ~5 |
| Memoria residente | < 2 GB | — |

Si el modelo no alcanza la meta de relaciones pero supera a la línea base y a legajo, se publica igual como v0.1 con las cifras reales; lo que no se publica es una cifra sin su tabla completa.

## 9. Entregables y estructura del repositorio

```
enrel/
  pyproject.toml            paquete `enrel`, Apache-2.0
  README.md                 qué es, cómo instalar, cómo usar, cifras
  LICENSE
  enrel/
    esquema/                tipos, relaciones, atributos, dominios; mapeo_legajo.py; exportación a FollowTheMoney
    corpus/                 lectura de legajo.sqlite, congelado y muestreo
    maestro/                cliente, prompts versionados, filtros, puerta
    anotacion/              desde_legajo.py (sqlite y JSON de oro → formato interno), guía como fuente de prompts; Label Studio opcional
    datos/                  formato interno, validador, exportador a tensores
    modelo/                 backbone, cabeza de entidades, agrupación, cabeza de relaciones
    entrenamiento/          bucle, pérdidas, configuración, cordura
    evaluacion/             métricas, bootstrap, tabla, revisión de falsos positivos
    inferencia/             pipeline de extremo a extremo, ONNX Runtime, CLI
    exportar/               a ONNX, cuantización, medición en CPU
  configs/                  YAML por corrida
  scripts/                  puntos de entrada por etapa
  tests/                    unitarios por módulo y de ida y vuelta
  docs/
    guia-anotacion.md       la fuente única de definiciones
    esquema.md              tabla del esquema con equivalencias
    maestro/                tablas de la puerta por iteración
    resultados/             tablas de evaluación por etapa
    investigacion/          los tres informes
    superpowers/specs/      este documento
datos/                      fuera de git: corpus, anotado, corridas
```

Publicación de la v0.1:
- Repositorio `github.com/i-montes/enrel` público con código, guía, esquema y resultados.
- Pesos en Hugging Face, organización a decidir por el usuario: `enrel-base-es` en PyTorch y ONNX (fp16 e int8 si pasa), ficha de modelo en español con datos, métricas por clase, límites conocidos y uso previsto.
- Los datos anotados con texto del archivo no se publican en la v0.1. Su publicación como corpus es una decisión aparte del usuario.

CLI mínima: `enrel extraer articulo.txt --salida json|ftm`, `enrel evaluar --prueba datos/anotado/prueba.jsonl --modelo ruta`, `enrel medir-cpu --hilos 4`.

## 10. Etapas y criterios de salida

| Etapa | Entregables | Criterio de salida | Horas del usuario |
|---|---|---|---|
| 0 · Cimientos | Esquema y guía escritos; `mapeo_legajo.py` y `desde_legajo.py` con prueba de ida y vuelta sobre los 125 de oro y los 40 perfiles; evaluador funcionando sobre ese oro (maestro viejo de legajo contra oro, como primera tabla real); corpus congelado y muestra fijada; entorno CUDA; humo del backbone: carga, pasada de 4.096 tokens en la 4060 con lote 2 bf16, exportación a ONNX, tiempo en CPU a 4 hilos de una pasada de 1.500 tokens | El backbone pasa el humo o se elige el respaldo; la muestra está fijada con semilla; la guía tiene las 17 definiciones con ejemplos; el evaluador produce una tabla sobre los 40 perfiles | 8 h anotando los 40 perfiles, en paralelo |
| 1 · Maestro y prueba | Cliente y prompts; los 50 de prueba corregidos por el usuario en legajo; puerta medida sobre prueba y prueba-dirigida | Puerta pasada: entidades ≥ 0,90, RE+ ≥ 0,75, dirección ≥ 0,95; o decisión documentada de retirar relaciones o sumar maestro | 8 h |
| 2 · Plata y primer modelo | Plata de 3.500; código de modelo y entrenamiento; cordura de sobreajuste; etapa 1 entrenada con dos semillas; evaluación completa con línea base y techo; los 10 de desarrollo de silla-nacional corregidos | Tabla completa en `docs/resultados/etapa-2.md`; el modelo supera a la línea base zero-shot en RE+ | 2 h |
| 3 · Oro y cierre | Oro de entrenamiento; etapa 2; barrido con un backbone alternativo; ONNX y cuantización medidas; revisión de 50 falsos positivos; ficha; publicación v0.1 | Cifras publicadas con intervalos; rendimiento en CPU dentro de meta; repo y pesos públicos | 4 a 10 h |

Ninguna etapa arranca sin el criterio de salida de la anterior escrito en `docs/resultados/`.

## 11. Riesgos y respuestas

| Riesgo | Señal | Respuesta |
|---|---|---|
| MrBERT-es no sirve: no carga, no exporta, es lento o aprende mal | humo de la etapa 0; entidades en desarrollo < 0,80 tras la etapa 1 | mmBERT-small; después XLM-R-base con ventanas |
| El maestro no pasa la puerta | RE+ < 0,75 tras tres iteraciones | retirar del esquema las relaciones que arrastran (medido por relación); si el problema es general, segundo maestro con unión y voto |
| Las horas del usuario no alcanzan | la prueba no está corregida al final de la etapa 1 | la prueba es lo único imprescindible; desarrollo se reduce a 10 y el oro de entrenamiento a cero; se documenta |
| Explosión de pares en documentos densos | memoria en entrenamiento; tiempo en CPU | tope de 60 grupos; máscara de tipos; medir el recorte |
| VRAM insuficiente | OOM en el humo | lote 1 con acumulación 16; 3.072 tokens; congelar las 6 capas inferiores |
| El oro de la prueba hereda errores del LLM que lo pre-anotó | la medida de anclaje da > 10 puntos de diferencia | se reportan las cifras de la prueba como cota inferior de cobertura; se anotan 5 artículos más en blanco |
| Fuga de la prueba al entrenamiento | F1 sospechosamente alto | validador por doc_id que aborta; Ign-F1 |
| Sesgo de género textual por el peso de perfiles en el oro | el modelo rinde mucho mejor en quien-es-quien que en silla-nacional en desarrollo | desarrollo está partido por mitades para verlo; se ajusta el peso de perfiles en la etapa 2 |
| La cuota de MiniMax limita por ventana de tiempo | 429 | cliente reanudable con espera exponencial; correr de noche |

## 12. Referencias

- Informes de investigación: `docs/investigacion/2026-09-16-estado-del-arte-extraccion-conjunta-cpu.md`, `…-destilacion-de-llm-a-modelo-pequeno.md`, `…-recursos-espanol-y-grafos-periodisticos.md`.
- Antecedente: `~/Projects/personal/legajo/docs/{pipeline,llm,entrenamiento,plan-entrenamiento,dudas-de-anotacion}.md` y `sidecar/entrenamiento/*/RESULTADOS.md`.
- MrBERT-es: https://huggingface.co/BSC-LT/MrBERT-es · arXiv 2602.21379.
- ATLOP: arXiv 2010.11304 · KD-DocRE: arXiv 2203.10900 · DREEAM (MIT): github.com/YoumiMa/dreeam.
- GoLLIE: arXiv 2310.03668 · IEPile: arXiv 2402.14710 · Re-DocRED: arXiv 2205.12696.
- FollowTheMoney: https://followthemoney.tech/ (MIT).
