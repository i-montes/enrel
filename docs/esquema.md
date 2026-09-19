# Esquema de enrel

Generado por `scripts/generar_esquema_md.py`. No editar a mano.

## Tipos de entidad

| Tipo | Se marca | No se marca |
|---|---|---|
| persona | nombre propio de una persona, con o sin apellidos («Gustavo Petro», «Petro», «Francia»); apodos y cuentas que individualizan («Epa Colombia», «@petrogustavo»). | pronombres; roles sueltos («la experta», «el mandatario», «el trabajador»); gentilicios; nombres de grupo («los indígenas», «los empresarios»). |
| organizacion | institución, empresa, partido, movimiento, medio, colectivo, junta o corte con nombre («Fiscalía General de la Nación», «Ecopetrol», «Centro Democrático», «El Tiempo», «Clan del Golfo», «Corte Constitucional»). | «el Estado», «el gobierno», «las empresas», «un sindicato», «la oposición» sin nombre; adjetivos de afiliación («uribista», «liberal»). |
| lugar | nombre propio de país, departamento, municipio, corregimiento, barrio, región o sede física con nombre («Colombia», «Antioquia», «Medellín», «Palacio de Nariño»). | «el país», «la región», «la capital», «los municipios» sin nombre. |
| cargo | cargo, puesto o título, con o sin titular, incluyendo su complemento («ministro de Hacienda», «senador», «alcalde de Medellín», «magistrado de la Corte Constitucional», «Gobernador de Antioquia»); también cuando el texto lo usa para designar a alguien sin nombrarlo («el Gobernador de Antioquia»). | oficios genéricos («abogado», «periodista», «empresario», «profesor») salvo como cargo institucional («profesor titular de la Universidad Nacional»); parentescos («esposa de»). |
| norma | ley, decreto, sentencia, acto legislativo, resolución, tratado o acuerdo identificable («Ley 1448 de 2011», «Decreto 1320 de 1998», «Acuerdo de Paz», «Sentencia C-355», «artículo 49 de la Constitución»). | «la ley», «un decreto», «la norma», «la reforma» sin identificar. |

## Relaciones

| Relación | De → a | Simétrica | Atributos | Familia | FollowTheMoney | Wikidata |
|---|---|---|---|---|---|---|
| ocupa_cargo | persona → cargo | no | titular, aspirante | A | Occupancy | P39 |
| nombro_a | organizacion, persona → persona | no | — | A | — | P748 |
| sucedio_a | persona → persona | no | — | A | Succession | P1365 |
| trabaja_en | persona → organizacion | no | — | A | Employment | P108 |
| dirige | persona → organizacion | no | — | A | Directorship | P1037, P169, P488 |
| miembro_de | persona → organizacion | no | — | A | Membership | P102, P463 |
| estudio_en | persona → organizacion | no | — | A | — | — |
| fundo | organizacion, persona → organizacion | no | — | B | — | P112 |
| propietario_de | organizacion, persona → organizacion | no | — | B | Ownership | P127, P1830 |
| socio_de | persona → persona | sí | — | B | Associate | P1327 |
| parte_de | organizacion → organizacion | no | — | B | — | P749, P355 |
| contrato_a | organizacion, persona → organizacion, persona | no | — | B | ContractAward | — |
| financia_a | organizacion, persona → organizacion, persona | no | — | B | Payment | P859 |
| familiar_de | persona → persona | sí | conyuge, hijo_de, hermano, otro | C | Family | P26, P40, P22, P25, P3373, P1038 |
| apoya_a | organizacion, persona → cargo, norma, organizacion, persona | no | — | C | — | — |
| impulsa_norma | organizacion, persona → norma | no | — | C | — | — |
| se_opone_a | organizacion, persona → norma, organizacion, persona | no | — | C | — | — |
| investigado_por | organizacion, persona → organizacion | no | investigado, acusado, condenado | C | CourtCaseParty | P1399 |
| ubicado_en | lugar, organizacion, persona → lugar | no | — | C | — | P159, P551, P131 |
| vinculo_sin_tipo | cualquiera ↔ cualquiera | sí | — | — | UnknownLink | — |

## Mapeo desde legajo

Para cada predicado, el destino con los tipos de extremo más habituales; los demás pares caen en vinculo_sin_tipo si la relación no los admite.

| Predicado de legajo | Vocabulario | persona→persona | persona→organizacion | persona→cargo | organizacion→organizacion |
|---|---|---|---|---|---|
| acusado de | viejo | vinculo_sin_tipo | investigado_por:acusado | vinculo_sin_tipo | investigado_por:acusado |
| acusado por | nuevo | vinculo_sin_tipo | investigado_por:acusado | vinculo_sin_tipo | investigado_por:acusado |
| aliado de | viejo | apoya_a | apoya_a | apoya_a | apoya_a |
| apoya a | nuevo | apoya_a | apoya_a | apoya_a | apoya_a |
| apoyó a | viejo | apoya_a | apoya_a | apoya_a | apoya_a |
| asesor de | viejo | vinculo_sin_tipo | trabaja_en | vinculo_sin_tipo | vinculo_sin_tipo |
| aspira a | viejo | vinculo_sin_tipo | vinculo_sin_tipo | ocupa_cargo:aspirante | vinculo_sin_tipo |
| aspira al cargo | nuevo | vinculo_sin_tipo | vinculo_sin_tipo | ocupa_cargo:aspirante | vinculo_sin_tipo |
| autor de | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| citado en | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| condenado por | viejo y nuevo | vinculo_sin_tipo | investigado_por:condenado | vinculo_sin_tipo | investigado_por:condenado |
| contrató a | viejo y nuevo | contrato_a | contrato_a | vinculo_sin_tipo | contrato_a |
| criticó a | viejo | se_opone_a | se_opone_a | vinculo_sin_tipo | se_opone_a |
| cónyuge de | nuevo | familiar_de:conyuge | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| cónyuge o pareja de | viejo | familiar_de:conyuge | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| demandó a | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| destinado a | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| dirige | viejo y nuevo | vinculo_sin_tipo | dirige | vinculo_sin_tipo | vinculo_sin_tipo |
| donó a | viejo | financia_a | financia_a | vinculo_sin_tipo | financia_a |
| dueño de | viejo | vinculo_sin_tipo | propietario_de | vinculo_sin_tipo | propietario_de |
| estudió en | nuevo | vinculo_sin_tipo | estudio_en | vinculo_sin_tipo | vinculo_sin_tipo |
| familiar de | viejo y nuevo | familiar_de:otro | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| financia a | viejo y nuevo | financia_a | financia_a | vinculo_sin_tipo | financia_a |
| fundó | viejo y nuevo | vinculo_sin_tipo | fundo | vinculo_sin_tipo | fundo |
| hermano de | viejo y nuevo | familiar_de:hermano | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| hijo de | viejo y nuevo | familiar_de:hijo_de | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| impulsa | nuevo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| investigado por | viejo y nuevo | vinculo_sin_tipo | investigado_por:investigado | vinculo_sin_tipo | investigado_por:investigado |
| miembro de | viejo y nuevo | vinculo_sin_tipo | miembro_de | vinculo_sin_tipo | vinculo_sin_tipo |
| nombró a | viejo y nuevo | nombro_a | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| ocupa el cargo | viejo y nuevo | vinculo_sin_tipo | vinculo_sin_tipo | ocupa_cargo:titular | vinculo_sin_tipo |
| ocupó el cargo | nuevo | vinculo_sin_tipo | vinculo_sin_tipo | ocupa_cargo:titular | vinculo_sin_tipo |
| opositor de | viejo | se_opone_a | se_opone_a | vinculo_sin_tipo | se_opone_a |
| padre o madre de | viejo | familiar_de:hijo_de (invertida) | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| parte de | viejo y nuevo | vinculo_sin_tipo | miembro_de | vinculo_sin_tipo | parte_de |
| propietario de | nuevo | vinculo_sin_tipo | propietario_de | vinculo_sin_tipo | propietario_de |
| renunció a | viejo | vinculo_sin_tipo | vinculo_sin_tipo | ocupa_cargo:titular | vinculo_sin_tipo |
| sanciona con | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| se opone a | nuevo | se_opone_a | se_opone_a | vinculo_sin_tipo | se_opone_a |
| se reunió con | viejo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| socio de | viejo y nuevo | socio_de | propietario_de | vinculo_sin_tipo | propietario_de |
| sucedió a | viejo y nuevo | sucedio_a | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| trabaja en | viejo y nuevo | vinculo_sin_tipo | trabaja_en | vinculo_sin_tipo | vinculo_sin_tipo |
| ubicado en | viejo y nuevo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
| vínculo sin tipo | nuevo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo | vinculo_sin_tipo |
