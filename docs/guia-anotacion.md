# Guía de anotación de enrel

Esta guía es la fuente única de las definiciones. La leen las personas que corrigen y la lee el código que construye los prompts del maestro (`enrel/anotacion/guia.py`). Si algo cambia, cambia aquí.

## Convenciones

- Se marca solo lo que el texto afirma. «Habría», «se dice que», «según fuentes» sin afirmación: no se marca.
- Sin artículos ni determinantes: «Petro», no «el Petro»; «Fiscalía», no «la Fiscalía». Salvo que el artículo sea parte del nombre: «La Silla Vacía», «El Tiempo».
- La persona nunca incluye su cargo ni su título: en «el exvicepresidente Germán Vargas Lleras» hay dos marcas, cargo «exvicepresidente» y persona «Germán Vargas Lleras».
- Un cargo incluye su complemento institucional o geográfico: «ministro de Hacienda», «alcalde de Medellín». La organización o el lugar de dentro se marca además como entidad anidada.
- Los nombres se copian exactamente como aparecen, con sus tildes y mayúsculas.
- Se marcan todas las apariciones de cada entidad, y las menciones de la misma entidad se agrupan.
- Una relación se marca una sola vez por par de entidades y tipo, aunque el texto la repita. Las simétricas, en una sola dirección.
- Si dos relaciones aplican al mismo par, se elige la más específica. Si el texto afirma dos hechos distintos (dirige y fundó), se marcan las dos.
- El título del artículo forma parte del texto y sus entidades se marcan.
- Los offsets de las menciones son de caracteres sobre el texto normalizado a NFC; los nombres se comparan con NFC y nunca se guardan índices de tokens.

## Tipos de entidad

### persona
**Se marca:** nombre propio de una persona, con o sin apellidos («Gustavo Petro», «Petro», «Francia»); apodos y cuentas que individualizan («Epa Colombia», «@petrogustavo»).
**No se marca:** pronombres; roles sueltos («la experta», «el mandatario», «el trabajador»); gentilicios; nombres de grupo («los indígenas», «los empresarios»).

### organizacion
**Se marca:** institución, empresa, partido, movimiento, medio, colectivo, junta o corte con nombre («Fiscalía General de la Nación», «Ecopetrol», «Centro Democrático», «El Tiempo», «Clan del Golfo», «Corte Constitucional»).
**No se marca:** «el Estado», «el gobierno», «las empresas», «un sindicato», «la oposición» sin nombre; adjetivos de afiliación («uribista», «liberal»).

### lugar
**Se marca:** nombre propio de país, departamento, municipio, corregimiento, barrio, región o sede física con nombre («Colombia», «Antioquia», «Medellín», «Palacio de Nariño»).
**No se marca:** «el país», «la región», «la capital», «los municipios» sin nombre.

### cargo
**Se marca:** cargo, puesto o título, con o sin titular, incluyendo su complemento («ministro de Hacienda», «senador», «alcalde de Medellín», «magistrado de la Corte Constitucional», «Gobernador de Antioquia»); también cuando el texto lo usa para designar a alguien sin nombrarlo («el Gobernador de Antioquia»).
**No se marca:** oficios genéricos («abogado», «periodista», «empresario», «profesor») salvo como cargo institucional («profesor titular de la Universidad Nacional»); parentescos («esposa de»).

### norma
**Se marca:** ley, decreto, sentencia, acto legislativo, resolución, tratado o acuerdo identificable («Ley 1448 de 2011», «Decreto 1320 de 1998», «Acuerdo de Paz», «Sentencia C-355», «artículo 49 de la Constitución»).
**No se marca:** «la ley», «un decreto», «la norma», «la reforma» sin identificar.

### obra
**Se marca:** título de libro, informe, columna, programa, película, canción, medio como producto («Tierra de Nadie», «Detector de Mentiras», «Huevos Revueltos», «Revista Semana» cuando se nombra la publicación como obra).
**No se marca:** «el informe», «un libro», «el artículo» sin título.

### monto
**Se marca:** cantidad con cifra o palabra de cantidad: «10 mil millones de pesos», «30 %», «48 a 108 meses», «un millón de dólares».
**No se marca:** «recursos», «plata», «salarios», cifras hipotéticas («supongamos dos millones»).

## Relaciones

### ocupa_cargo
**Definición:** Una persona ejerce, ejerció o busca un cargo. La cabeza es la persona; la cola es el cargo. Es la relación central del grafo de poder y la más frecuente. Si el texto da el cargo, se usa esta relación y no trabaja_en ni dirige.
**Ejemplos:**
- «El ministro de Hacienda, José Manuel Restrepo, anunció…» → Restrepo ocupa_cargo:actual «ministro de Hacienda».
- «El exalcalde de Medellín Daniel Quintero» → Quintero ocupa_cargo:anterior «exalcalde de Medellín».
- «Vicky Dávila, candidata presidencial» → Dávila ocupa_cargo:aspirante «candidata presidencial».
- «El entonces gobernador de Antioquia, Luis Alfredo Ramos» → Ramos ocupa_cargo:anterior «gobernador de Antioquia».
**No es:**
- «Trabajó en el Ministerio de Hacienda» sin cargo nombrado: es trabaja_en con la organización.
- «El abogado Pérez»: «abogado» es oficio, no cargo; no se marca relación.
**Confusiones:**
- Con trabaja_en: si hay cargo nombrado, ocupa_cargo; si solo hay organización, trabaja_en.
- Con dirige: «alcaldesa de Bogotá» es ocupa_cargo con el cargo; dirige solo si además se menciona la organización («la Alcaldía»).
- Con nombro_a: «Petro nombró a X ministro» produce nombro_a (Petro → X) y ocupa_cargo:actual (X → ministro).

### nombro_a
**Definición:** Una persona u organización designa a una persona para un cargo o función. La cabeza es quien nombra; la cola es la persona nombrada.
**Ejemplos:**
- «Petro nombró a Luis Carlos Reyes como ministro de Comercio» → Petro nombro_a Reyes.
- «La Corte Suprema eligió a Francisco Barbosa como fiscal general» → Corte Suprema nombro_a Barbosa.
- «El Senado designó a la magistrada Cristina Pardo» → Senado nombro_a Pardo.
**No es:**
- «Reyes fue nombrado ministro» sin decir quién lo nombró: solo ocupa_cargo.
- «Petro propuso a X para el cargo» sin nombramiento: no se marca, o apoya_a si es respaldo explícito a una candidatura.
**Confusiones:**
- Con sucedio_a: nombro_a es quién designa; sucedio_a es a quién reemplaza el nombrado.
- Con apoya_a: proponer o respaldar no es nombrar.

### sucedio_a
**Definición:** Una persona reemplaza a otra en un cargo o función. La cabeza es quien llega; la cola es quien se va.
**Ejemplos:**
- «Reyes reemplazó a Germán Umaña en el Ministerio de Comercio» → Reyes sucedio_a Umaña.
- «Claudia Dangond fue elegida en reemplazo del magistrado Antonio Lizarazo» → Dangond sucedio_a Lizarazo.
- «Su sucesor, Carlos Fernando Galán» → Galán sucedio_a (la persona anterior mencionada).
**No es:**
- «Dejó el cargo» sin decir quién lo ocupó después: solo ocupa_cargo:anterior.
- Dos personas que ocuparon el mismo cargo en años distintos sin que el texto diga que una reemplazó a la otra: no se marca.
**Confusiones:**
- Con nombro_a: el que nombra no es el que se va.

### trabaja_en
**Definición:** Una persona trabaja, asesora o presta servicios en una organización, sin que el texto nombre un cargo. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Adriana Camacho, de la Universidad del Rosario» → Camacho trabaja_en Universidad del Rosario.
- «Trabajó en Ecopetrol durante diez años» → (persona) trabaja_en Ecopetrol.
- «Asesor del Ministerio de Defensa» → (persona) trabaja_en Ministerio de Defensa.
**No es:**
- «Ministro de Defensa»: hay cargo, es ocupa_cargo.
- «Militante del Partido Liberal»: es miembro_de.
**Confusiones:**
- Con miembro_de: empleo o asesoría es trabaja_en; pertenencia sin empleo (partido, junta, colectivo) es miembro_de.
- Con dirige: si preside o gerencia, dirige.

### dirige
**Definición:** Una persona encabeza, preside o gerencia una organización. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Ricardo Roa, presidente de Ecopetrol» → Roa dirige Ecopetrol, y Roa ocupa_cargo:actual «presidente de Ecopetrol».
- «La firma es gerenciada por Juan Pérez» → Pérez dirige (la firma).
- «Roy Barreras preside el Senado» → Barreras dirige Senado.
**No es:**
- «Trabaja en la gerencia de X» sin decir que la encabeza: trabaja_en.
- «Fundó la empresa» sin decir que la dirige: fundo.
**Confusiones:**
- Con ocupa_cargo: cuando hay cargo y organización, se marcan las dos: ocupa_cargo con el cargo y dirige con la organización.

### miembro_de
**Definición:** Una persona pertenece a una organización sin que sea empleo: militancia en un partido o movimiento, pertenencia a una junta, comisión, bancada o colectivo. La cabeza es la persona; la cola es la organización.
**Ejemplos:**
- «Militante del Partido Liberal» → (persona) miembro_de Partido Liberal.
- «Senador de Cambio Radical» → (persona) miembro_de Cambio Radical, además de ocupa_cargo «senador».
- «Integra la junta directiva de EPM» → (persona) miembro_de EPM.
**No es:**
- «El liberal Pérez», «el uribista X»: el adjetivo no afirma pertenencia; no se marca.
- «Trabaja en el partido como asesor»: trabaja_en.
**Confusiones:**
- Con parte_de: parte_de es entre organizaciones; una persona nunca es parte_de.
- Con trabaja_en: pertenencia sin empleo frente a empleo.

### fundo
**Definición:** Una persona u organización creó una organización. La cabeza es el fundador; la cola es lo fundado.
**Ejemplos:**
- «Álvaro Uribe fundó el Centro Democrático» → Uribe fundo Centro Democrático.
- «Cofundador de Rappi» → (persona) fundo Rappi.
- «La fundación fue creada por el Grupo Aval» → Grupo Aval fundo (la fundación).
**No es:**
- «Dueño de la empresa» sin decir que la fundó: propietario_de.
- «Lideró la creación de la ley»: no es una organización.
**Confusiones:**
- Con dirige y propietario_de: fundar no implica dirigir ni poseer hoy; se marcan aparte si el texto lo dice.

### propietario_de
**Definición:** Una persona u organización posee total o parcialmente una organización: dueño, accionista, socio de una empresa. La cabeza es el propietario; la cola es la organización.
**Ejemplos:**
- «Luis Carlos Sarmiento Angulo, dueño del Grupo Aval» → Sarmiento propietario_de Grupo Aval.
- «Accionista de Avianca» → (persona) propietario_de Avianca.
- «El Grupo Gilinski controla el 40 % de Nutresa» → Grupo Gilinski propietario_de Nutresa.
**No es:**
- «Presidente de la empresa» sin propiedad: dirige.
- «Socio de Juan Pérez» entre dos personas: socio_de.
**Confusiones:**
- Con parte_de: una filial es parte_de la matriz; la matriz es propietario_de la filial solo si el texto habla de propiedad. Si el texto dice «filial», parte_de.

### socio_de
**Definición:** Dos personas son socias en un negocio o empresa. Simétrica. Si el texto dice de qué empresa, además cada uno es propietario_de esa empresa.
**Ejemplos:**
- «Pérez y Gómez, socios en la constructora» → Pérez socio_de Gómez.
- «Su socio de toda la vida, Carlos Mattos» → (persona) socio_de Mattos.
- «Fundaron juntos la firma; son socios desde 2010» → socio_de entre los dos.
**No es:**
- «Socio del club»: es miembro_de.
- «Aliado político»: apoya_a.
**Confusiones:**
- Con propietario_de: socio de una empresa es propietario_de; socio de una persona es socio_de.

### parte_de
**Definición:** Una organización está dentro de otra: filial, dependencia, adscrita, unidad. La cabeza es la parte; la cola es el todo.
**Ejemplos:**
- «La Unidad de Víctimas, adscrita al Departamento para la Prosperidad Social» → Unidad de Víctimas parte_de DPS.
- «Ópticas Saludcoop, filial de Saludcoop» → Ópticas Saludcoop parte_de Saludcoop.
- «La Facultad de Derecho de la Universidad de los Andes» → Facultad de Derecho parte_de Universidad de los Andes.
**No es:**
- «Militante del partido»: miembro_de.
- Dos organizaciones que colaboran: no es parte_de; si el texto afirma respaldo, apoya_a.
**Confusiones:**
- Con propietario_de: propiedad frente a estructura.

### contrato_a
**Definición:** Una organización o persona contrata a otra: contratación pública o privada, adjudicación, licitación ganada. La cabeza es quien contrata; la cola es el contratista.
**Ejemplos:**
- «La Gobernación contrató a la firma Ingeniería SAS por 10 mil millones» → Gobernación contrato_a Ingeniería SAS.
- «El consorcio ganó la licitación de la Alcaldía» → Alcaldía contrato_a (el consorcio).
- «Contratista del Invías» → Invías contrato_a (persona u organización).
**No es:**
- «Trabaja en la Gobernación»: trabaja_en.
- «Financió la campaña»: financia_a.
**Confusiones:**
- Con financia_a: un contrato es intercambio; una financiación o donación no.

### financia_a
**Definición:** Una persona u organización financia, dona o aporta dinero a otra. La cabeza es quien da; la cola es quien recibe.
**Ejemplos:**
- «Odebrecht financió la campaña de Santos» → Odebrecht financia_a Santos.
- «Donó 500 millones al Partido Conservador» → (persona) financia_a Partido Conservador.
- «Los aportes de la empresa a la fundación» → (empresa) financia_a (fundación).
**No es:**
- «Le pagó por el contrato»: contrato_a.
- «Apoyó la candidatura» sin dinero: apoya_a.
**Confusiones:**
- Con contrato_a: pago por servicios frente a aporte sin contraprestación.

### familiar_de
**Definición:** Dos personas tienen un parentesco afirmado por el texto. Simétrica salvo hijo_de, donde la cabeza es el hijo.
**Atributos:** conyuge: esposo, esposa, pareja, compañero permanente, ex pareja; hijo_de: hijo o hija, la cabeza es el hijo, el padre o madre es la cola; hermano: hermanos y hermanastros; otro: tío, primo, sobrino, cuñado, suegro, nuera, yerno, nieto, abuelo, padrino, o «familiar» sin precisar.
**Ejemplos:**
- «Su esposa, Verónica Alcocer» → Petro familiar_de:conyuge Alcocer.
- «Nicolás Petro, hijo del presidente Gustavo Petro» → Nicolás Petro familiar_de:hijo_de Gustavo Petro.
- «Los hermanos Char» → Char familiar_de:hermano Char (entre los nombrados).
- «Es nieto del expresidente Alberto Lleras» → (persona) familiar_de:otro Lleras.
**No es:**
- «La familia Char» como grupo: no hay dos personas nombradas.
- «Su padrino político»: no es parentesco; apoya_a si el texto afirma respaldo.
**Confusiones:**
- Con hijo_de invertido: «su papá, Ricardo Romero» dicho de Camilo Romero produce Camilo familiar_de:hijo_de Ricardo, nunca al revés.

### apoya_a
**Definición:** Una persona u organización respalda explícitamente a otra persona, organización o candidatura: apoyo, alianza, adhesión, coalición. La cabeza es quien apoya; la cola es lo apoyado.
**Ejemplos:**
- «El Partido Liberal respaldó la candidatura de Petro» → Partido Liberal apoya_a Petro.
- «Aliado del gobierno» → (persona) apoya_a (gobierno nombrado).
- «Cambio Radical se sumó a la coalición de Duque» → Cambio Radical apoya_a Duque.
**No es:**
- Dos personas que aparecen en el mismo evento: no se marca.
- «Petro nombró a X»: nombro_a.
**Confusiones:**
- Con miembro_de: militar en un partido no es apoyar a su candidato salvo que el texto lo diga.
- Con se_opone_a: el signo contrario.

### se_opone_a
**Definición:** Una persona u organización se opone o critica explícitamente a otra persona u organización. La cabeza es quien se opone; la cola es el criticado.
**Ejemplos:**
- «Uribe criticó al gobierno de Petro» → Uribe se_opone_a Petro.
- «El Centro Democrático, en oposición al gobierno» → Centro Democrático se_opone_a (gobierno nombrado).
- «Rival político de Char» → (persona) se_opone_a Char.
**No es:**
- «Criticó la reforma»: la cola es una norma, no se marca.
- Dos candidatos al mismo cargo sin que el texto afirme rivalidad: no se marca.
**Confusiones:**
- Con investigado_por: denunciar penalmente ante una autoridad es se_opone_a solo si el texto lo presenta como oposición; la investigación la marca la autoridad.

### investigado_por
**Definición:** Una persona u organización está siendo investigada, imputada, acusada o fue condenada por una autoridad. La cabeza es el investigado; la cola es la autoridad. El delito no es una entidad y no se marca.
**Atributos:** investigado: investigación abierta, indagación, «investigado por»; acusado: imputación o acusación formal, «imputado», «acusado», «llamado a juicio»; condenado: condena, sanción, destitución, «condenado», «sancionado», «destituido».
**Ejemplos:**
- «Investigado por la Fiscalía por peculado» → (persona) investigado_por:investigado Fiscalía.
- «La Procuraduría lo destituyó e inhabilitó» → (persona) investigado_por:condenado Procuraduría.
- «Imputado por la Fiscalía» → (persona) investigado_por:acusado Fiscalía.
**No es:**
- «Acusado de corrupción» sin autoridad: no hay cola; no se marca.
- «Demandó a la empresa»: vinculo_sin_tipo.
**Confusiones:**
- Con se_opone_a: la autoridad que investiga no «se opone».

### ubicado_en
**Definición:** Una organización tiene su sede en un lugar, una persona reside en un lugar, o un lugar está dentro de otro. La cabeza es lo ubicado; la cola es el lugar.
**Ejemplos:**
- «La empresa, con sede en Barranquilla» → (empresa) ubicado_en Barranquilla.
- «Reside en Bogotá desde 2015» → (persona) ubicado_en Bogotá.
- «El municipio de Tumaco, en Nariño» → Tumaco ubicado_en Nariño.
**No es:**
- «El caleño Pérez», «de Popayán»: origen, no ubicación.
- «La reunión fue en Cartagena»: lugar de los hechos, no de la entidad.
**Confusiones:**
- Con el complemento del cargo: «alcalde de Medellín» no produce ubicado_en; Medellín va anidado dentro del cargo.

### vinculo_sin_tipo
**Definición:** El texto afirma un vínculo entre dos entidades que no encaja en ninguna relación del esquema: se reunieron, se demandaron, negociaron, se conocen. Se conserva para revisión humana. Simétrica.
**Ejemplos:**
- «Petro se reunió con Uribe» → Petro vinculo_sin_tipo Uribe.
- «La empresa demandó a la Nación» → (empresa) vinculo_sin_tipo Nación.
- «Negoció con las Farc» → (persona) vinculo_sin_tipo Farc.
**No es:**
- Dos entidades en la misma oración sin vínculo afirmado: no se marca nada.
- Un vínculo que sí encaja en otra relación: se usa esa.
**Confusiones:**
- Con apoya_a y se_opone_a: si el texto afirma respaldo u oposición, esas; si solo narra un encuentro, vinculo_sin_tipo.
