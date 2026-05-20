---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Brazil"
iso3: "BRA"
iso2: "BR"
region: "Latin America and the Caribbean"
last_updated: "2026-05-20"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: true
  outcomes:  false

school_count_total: null   # TODO: populate after bra_geo.py run
school_count_public: null  # TODO: populate after bra_geo.py run
year_range: "2007–2025"
years_available: [2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

sector_scope: "public"
sector_notes: >
  Source dataset contains all Brazilian basic education schools across all
  management types and education levels. Filtered to public schools using:
    Categoria Administrativa == 'Pública'
    Dependência Administrativa IN ['Municipal', 'Estadual', 'Federal']
    Conveniada Poder Público == 'Não'
  Escolas conveniadas (privately-owned schools contracted by municipal or state
  government to absorb students when public capacity is insufficient) are
  excluded. Although they receive government-referred students and partial
  public funding, they are privately operated and do not meet the threshold
  for government-subsidised inclusion used in other countries (e.g. Bangladesh
  MPO schools, Belize Government Aided schools), where the government directly
  funds salaries at schools fully integrated into the national EMIS.
  Schools offering only Educação Infantil (pre-primary), Educação Profissional
  (vocational), or Educação de Jovens e Adultos (adult education) are excluded.
  Schools offering Ensino Fundamental or Ensino Médio alongside other levels
  are retained; only in-scope enrollments are counted in the personnel table.

sources:
  - source_id: "bra_inep_catalogo"
    name: "Catálogo de Escolas — INEP Data"
    provider: "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP), Brazil"
    url: "https://anonymousdata.inep.gov.br/analytics/saw.dll?Dashboard&PortalPath=%2Fshared%2FCenso%20da%20Educa%C3%A7%C3%A3o%20B%C3%A1sica%2F_portal%2FCat%C3%A1logo%20de%20Escolas"
    url_status: "live"
    access_date: "2026-05-20"
    data_date: "unknown"  # TODO: confirm which Censo year the Catálogo export reflects
    update_frequency: "Annual (updated with each Censo Escolar)"
    format: "CSV (exported from INEP Data portal)"
    language: "Portuguese"
    notes: >
      Used for geo table only. Contains school name, administrative category,
      dependência, localização (urban/rural), localidade diferenciada,
      coordinates (Latitude/Longitude), education stages offered, and address.
      Updated annually from the Censo Escolar; the specific Censo year reflected
      in this export was not clearly stated on the portal at time of download
      and should be confirmed.

  - source_id: "bra_inep_censo_microdata"
    name: "Microdados do Censo Escolar da Educação Básica — INEP (2007–2024)"
    provider: "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP), Brazil"
    url: "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar"
    url_status: "live"
    access_date: "2026-05-20"
    data_date: "2007–2024 (annual)"
    update_frequency: "Annual"
    format: "CSV (semicolon-delimited, latin-1 encoding)"
    language: "Portuguese"
    notes: >
      Used for personnel and resources tables (2007–2024). One school-level CSV
      per year containing pre-aggregated enrollment, teacher, classroom, and
      infrastructure counts. Reference date is the last Wednesday of May each
      year (Dia Nacional do Censo Escolar), except 2020 where an extraordinary
      reference date of 11 March 2020 was used due to the COVID-19 pandemic.
      IMPORTANT — teacher count correction: QT_DOC_* fields for 2007–2021 were
      affected by a row-shift error in INEP releases prior to November 2022,
      causing teacher counts to be misassigned across schools. INEP issued a
      formal correction notice (SEI/INEP 0972964, 01 November 2022) and released
      corrected files. All files for this project re-downloaded May 2026 and
      reflect the corrected versions. Users of data downloaded before November
      2022 should re-download 2007–2021 files.

  - source_id: "bra_inep_censo_2025"
    name: "Microdados do Censo Escolar da Educação Básica 2025 — INEP"
    provider: "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP), Brazil"
    url: "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-escolar"
    url_status: "live"
    access_date: "2026-05-20"
    data_date: "2025"
    update_frequency: "Annual"
    format: "CSV (semicolon-delimited, latin-1 encoding) — split into three separate tables"
    language: "Portuguese"
    notes: >
      Used for personnel and resources tables (2025). Published as three
      separate files: Tabela_Matricula_2025 (enrollment by stage),
      Tabela_Docente_2025 (teacher counts by stage), Tabela_Escola_2025
      (school infrastructure and classrooms). All three joined on CO_ENTIDADE.
      Structure differs from the single-file format used in 2007–2024.

  - source_id: "geoboundaries_bra"
    name: "geoBoundaries — Brazil ADM1–ADM3"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-05-20"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "GeoJSON"
    language: "English"
    notes: >
      Used for adm1–adm3 assignment via spatial join to school coordinates
      from the Catálogo. Source UF and Município columns are not used for
      adm fields — GeoBoundaries spatial join is authoritative per pipeline
      standard.

---

## GEO

**Status:** Available
**Source(s):** bra_inep_catalogo, geoboundaries_bra
**Year of geo data:** Unknown — Catálogo export year to be confirmed (TODO)

### Public school subsetting
The Catálogo contains all Brazilian basic education schools across all
management types and education levels. Four filters applied sequentially:

**Filter 1 — Administrative category:**
`Categoria Administrativa == 'Pública'`. Removes all private schools.

**Filter 2 — Dependência administrativa:**
`Dependência Administrativa IN ['Municipal', 'Estadual', 'Federal']`. All three
public dependency types are in scope — these are straightforwardly
government-managed schools at the municipal, state, and federal level
respectively.

**Filter 3 — Conveniadas excluded:**
`Conveniada Poder Público == 'Não'`. Escolas conveniadas are privately-owned
institutions (for-profit or non-profit) that receive government-referred
students under a partnership agreement when public school capacity is
insufficient. They are sometimes described as Brazil's charter school
equivalent. Despite public funding flows, they are privately operated and
excluded per V1 scope. They should not be confused with Bangladesh's MPO
schools or Belize's Government Aided schools, where government directly
funds salaries at schools fully integrated into the national EMIS.

**Filter 4 — Education stage:**
`Etapas e Modalidade de Ensino Oferecidas` must contain `'Ensino Fundamental'`
or `'Ensino Médio'` (or both). Schools offering only Educação Infantil,
Educação Profissional, or Educação de Jovens e Adultos are excluded. Schools
offering in-scope levels alongside out-of-scope levels are retained; the
`isced_level` field reflects only the in-scope portion.

### ISCED level mapping
ISCED level derived from the `Etapas e Modalidade de Ensino Oferecidas` field
by checking for the presence of in-scope stage labels:

| Source stages present | `isced_level` |
|---|---|
| Ensino Fundamental only | `1` |
| Ensino Médio only | `3` |
| Both Ensino Fundamental and Ensino Médio | `1\|3` |

ISCED 2 is not represented in the geo file. Brazil's 9-year Ensino Fundamental
spans ISCED 1 (Anos Iniciais, years 1–5) and lower ISCED 2 (Anos Finais, years
6–9) but the Catálogo provides no within-Ensino Fundamental disaggregation —
no field indicates whether a school runs Anos Iniciais only, Anos Finais only,
or the full 9-year cycle. All Ensino Fundamental schools are therefore mapped
to `1` only. Researchers requiring ISCED 1/2 distinction should consult
grade-level enrollment data from the Censo Escolar microdata.

### Coordinates
Coordinates taken directly from source columns `Latitude` and `Longitude`
in the Catálogo export. Assumed WGS84 decimal degrees. Schools with missing
coordinates dropped entirely per pipeline rule (not nulled).

`coordinate_source = 'official_emis'`
`coordinate_precision = 'approximate'`

Precision set to `approximate` rather than `exact`: the Catálogo does not
document coordinate collection methodology. Coordinates are assumed to
reflect school building location but this is unconfirmed.

### Administrative hierarchy
`adm0` = "Brazil" (hardcoded).

`adm1`–`adm3` assigned via spatial join to GeoBoundaries ADM1–ADM3 for BRA
using the shared `join_admin_boundaries` pipeline utility. Source `UF` and
`Município` columns from the Catálogo are not used for adm fields.

### Urban/rural classification
`urban_rural` mapped from source `Localização` column:

| Source value | `urban_rural` |
|---|---|
| Urbana | `urban` |
| Rural | `rural` |

### school_type
Populated from `Localidade Diferenciada` where the school is in a
differentiated area, retaining the source label verbatim. Values include
"Terra indígena", "Área de assentamento", "Comunidade quilombola", and
"Área onde se localizam povos e comunidades tradicionais" (added 2023).
Set to NA where `Localidade Diferenciada` indicates no differentiated area
or is blank.

### Status
`status = 'open'` assigned to all schools. The Catálogo represents the active
school register at time of export; paralisada and extinta schools are not
included. `TP_SITUACAO_FUNCIONAMENTO` in the microdata (1=Em Atividade,
2=Paralisada, 3=Extinta current year, 4=Extinta prior years) could be used
to refine this field if the geo table is rebuilt from the microdata directly.

### Known issues
- Catálogo export year unconfirmed — affects interpretation of school counts
  and status. Should be confirmed and updated.
- ISCED 2 not represented due to lack of within-Ensino Fundamental
  disaggregation in source. All Ensino Fundamental schools mapped to `1`.
- `coordinate_precision = 'approximate'` — coordinate collection methodology
  not documented by INEP.

---

## PERSONNEL

**Status:** Available
**Source(s):** bra_inep_censo_microdata, bra_inep_censo_2025
**Years available:** 2007–2025

### Year coverage
Panel begins 2007. Pre-2007 Censo Escolar files use a legacy school identifier
(`MASCARA`/`CODESC`, 10-character alphanumeric) that does not reliably join
to `CO_ENTIDADE` (8-digit numeric used from 2007 onward). Pre-2007 years are
excluded to avoid silent school mismatches across years.

### Enrollment
`enrollment_total` = `QT_MAT_FUND` + `QT_MAT_MED`

Ensino Fundamental and Ensino Médio enrollments summed. `QT_MAT_BAS` (total
basic education enrollments) is deliberately excluded — it includes Educação
Infantil (pre-primary, ISCED 0) and EJA (adult education), which are out of
scope. Where both `QT_MAT_FUND` and `QT_MAT_MED` are null the row is set to
NA; where one is null and the other is not, the null is treated as 0.

**2025:** `QT_MAT_MED` from 2025 onward covers Ensino Médio Regular only,
excluding students in the Itinerário Formativo Técnico Profissional (IFTP)
track introduced by the Novo Ensino Médio reform. `QT_MAT_MED_IFTP_CT` is
added to the 2025 enrollment sum to maintain comparability with prior years,
where integrated technical Ensino Médio was included within `QT_MAT_MED`.

### Sex-disaggregated enrollment
`enrollment_female` and `enrollment_male` are set to NA for all years.

The only sex-disaggregated enrollment field in the Censo Escolar school-level
microdata is `QT_MAT_BAS_FEM` / `QT_MAT_BAS_MASC`, which covers all basic
education stages including Educação Infantil and EJA. In approximately 62% of
schools in the filtered dataset, `QT_MAT_BAS_FEM + QT_MAT_BAS_MASC` exceeds
`enrollment_total` (Ensino Fundamental + Ensino Médio only), because those
schools also operate pre-primary classrooms. Populating `enrollment_female`
and `enrollment_male` from the basic education totals would violate the schema
requirement that sex subtotals are subsets of `enrollment_total` in the
majority of rows. Both fields are therefore set to NA.

### Teachers
`teachers_total` = `QT_DOC_FUND` + `QT_DOC_MED`

Ensino Fundamental and Ensino Médio teaching staff summed. Same null-handling
logic as enrollment. `QT_DOC_BAS` (total basic education teachers) excluded
for the same reasons as `QT_MAT_BAS`.

The Censo Escolar counts teachers by school-stage combination at the reference
date. A teacher active in both Ensino Fundamental and Ensino Médio at the same
school is counted once per stage. Summing `QT_DOC_FUND + QT_DOC_MED` may
therefore slightly overcount unique individuals at schools offering both
levels. INEP does not publish a deduplicated within-school teacher count at
the school level; this is the best available approximation.

`teachers_male`, `teachers_female`, `teachers_qualified`: not available at
school level in the Censo Escolar school-level microdata file. Sex
disaggregation for teachers is available in the individual-level
Profissional Escolar em Sala de Aula file (restricted access via SEDAP)
but not in the public microdata.

### Pupil-teacher ratio
`pupil_teacher_ratio` = `enrollment_total / teachers_total`. Set to NA where
`teachers_total` is 0 or NA to avoid infinite or undefined values.

### Classrooms
`classrooms_total` sourced from `QT_SALAS_UTILIZADAS` (total classrooms used,
inside and outside the building). Available all years. From 2019 onward this
is a derived variable combining `QT_SALAS_UTILIZADAS_DENTRO` and
`QT_SALAS_UTILIZADAS_FORA`; prior years reported the total directly.

### Teacher data quality note
`QT_DOC_*` fields for 2007–2021 were affected by a row-shift error in INEP
microdata releases prior to November 2022, causing teacher counts to be
misassigned to incorrect schools. INEP issued a formal correction notice
(SEI/INEP 0972964, 01 November 2022). All files re-downloaded May 2026;
corrected versions used throughout.

---

## RESOURCES

**Status:** Available
**Source(s):** bra_inep_censo_microdata, bra_inep_censo_2025
**Years available:** 2007–2025

### water_basic
**2013–2025:** `IN_AGUA_POTAVEL` — school provides potable water for human
consumption (binary, direct mapping).

**2007–2012:** `IN_AGUA_FILTRADA` — water consumed by students is filtered.
Used as best available proxy. Note that filtered water is a narrower concept
than JMP 'basic' service (an improved water source available at the school):
filtered water could theoretically be sourced from an unimproved supply.
Pre-2013 `water_basic` values should be interpreted with this caveat; direct
comparability with 2013+ values is not guaranteed.

### water_improved
`1` if any of `IN_AGUA_REDE_PUBLICA` (public network) or
`IN_AGUA_POCO_ARTESIANO` (artesian well) = 1; `0` if both = 0.

Both public network and artesian wells qualify as improved water sources under
JMP 2018 definitions. Cacimba/cisterna/poço (hand-dug well or cistern,
`IN_AGUA_CACIMBA`) and fonte/rio/igarapé (surface water, `IN_AGUA_FONTE_RIO`)
are unimproved sources and excluded from this computation.

### sanitation_basic
**2013–2025:** `IN_BANHEIRO` — school has any bathroom (binary, direct).

**2007–2012:** OR of `IN_BANHEIRO_DENTRO_PREDIO` (bathroom inside building)
and `IN_BANHEIRO_FORA_PREDIO` (bathroom outside building). Set to `1` if
either = 1. The 2013+ unified `IN_BANHEIRO` field replaced these two separate
fields; the OR mapping is the conceptual equivalent.

### sanitation_sex_separated
Not available in Censo Escolar microdata at any year. Set to NA.

### handwashing_basic
Not available in Censo Escolar microdata at any year. Set to NA.

### electricity
`1` if the school has any electricity source; `0` if explicitly no electricity.

Source fields used (OR logic):

| Field | Years available | Source |
|---|---|---|
| `IN_ENERGIA_REDE_PUBLICA` | All years | Grid electricity |
| `IN_ENERGIA_GERADOR` | 2007–2012 | Generator (any type) |
| `IN_ENERGIA_GERADOR_FOSSIL` | 2013–2025 | Fossil fuel generator |
| `IN_ENERGIA_RENOVAVEL` | 2013–2025 | Renewable/alternative sources |

`IN_ENERGIA_INEXISTENTE` = 1 forces the result to `0` regardless of other
fields. The pre/post 2013 generator field renaming reflects a methodological
split (fossil vs. renewable) rather than a substantive change; the OR
aggregation to a single binary is consistent across years.

### internet
`IN_INTERNET` — direct binary, available all years. Set to `1` if the school
has internet access of any type.

### internet_type
Not available at school level in the Censo Escolar. Set to NA. The microdata
contains `IN_BANDA_LARGA` (broadband yes/no, 2008+) and `TP_REDE_LOCAL`
(local network type) but neither maps cleanly to the `internet_type` allowed
values (`fiber`, `cable_modem`, `dsl`, `mobile_3g`, etc.).

### computers
**2013–2025:** `1` if any of `IN_DESKTOP_ALUNO` (desktop computers used by
students), `IN_COMP_PORTATIL_ALUNO` (laptops used by students), or
`IN_TABLET_ALUNO` (tablets used by students) = 1; `0` if all = 0.

**2007–2012:** Derived from `QT_COMP_ALUNO` (count of computers in use by
students). Set to `1` if `QT_COMP_ALUNO > 0`, `0` if = 0. The pre-2013
field is a count rather than a set of binary indicators; the derivation is
conceptually equivalent.

### library
`IN_BIBLIOTECA_SALA_LEITURA` — library and/or reading room (binary). Available
from 2009 onward. For 2007–2008, fallback to `IN_BIBLIO` (existence of
library), which is the predecessor field covering the same concept.

---

## OUTCOMES

**Status:** Not available
School-level promotion, repetition, dropout, and completion rates are not
published in the Censo Escolar school-level microdata. INEP computes flow
rate indicators (rendimento escolar) from student-level data but publishes
these only in aggregate form via the Sinopses Estatísticas (municipality and
state level) and as school-level IDEB components (which combine flow rates
with SAEB assessment scores). Neither source provides the raw rate fields
required by the outcomes schema in a directly extractable form.

The individual-level student file (Aluno) held under restricted access via
SEDAP contains the data needed to reconstruct school-level flow rates, but
access requires a formal research agreement with INEP.

---

## GENERAL NOTES

### Source availability
All microdata files downloaded from the INEP open data portal in May 2026.
Files are retained locally in `sources/bra/microdados/` organised by year.
The Catálogo export is retained in `sources/bra/catalogo_escolas.csv`.

### Harmonization decisions
- `geo_id` assigned as `BRA_{zero-padded integer}` sorted by `Código INEP`
  (`CO_ENTIDADE`) ascending, ensuring reproducible ID assignment across re-runs.
- `school_name_romanized` set to NA — Portuguese uses Latin script.
- `sector = 'public'` for all rows per filtering logic above.
- `status = 'open'` for all geo rows — Catálogo does not include inactive
  schools.
- All adm fields sourced from GeoBoundaries spatial join, not from source
  administrative columns, per pipeline standard.
- ISCED 2 not coded — Ensino Fundamental mapped to `1` only due to lack of
  Anos Iniciais/Finais disaggregation in the Catálogo.
- `enrollment_female` and `enrollment_male` set to NA — see Personnel section.
- `QT_DOC_FUND + QT_DOC_MED` used for `teachers_total` rather than `QT_DOC_BAS`
  to match the in-scope enrollment definition.
- 2025 `enrollment_total` includes `QT_MAT_MED_IFTP_CT` for comparability
  with prior years.

### Outstanding issues
- Catálogo export year must be confirmed and `data_date` updated in sources.
- `school_count_total` and `school_count_public` in the header must be
  populated after running `bra_geo.py`.
- ISCED 2 gap: consider whether grade-level enrollment from the microdata
  could be used to split Ensino Fundamental schools into Anos Iniciais (ISCED 1)
  and Anos Finais (ISCED 2) in a future version.
- Outcomes table cannot be populated from public microdata. If SEDAP access
  is obtained for the restricted Aluno file, school-level flow rates could
  be reconstructed.
- `IN_AGUA_POCO_ARTESIANO` field name should be verified in 2007–2012 files
  — earlier Censo dictionaries used the abbreviated form `IN_AGUA_ART`. If
  mismatched, `water_improved` will be underestimated for early years.
- 2025 `QT_DOC_MED` field name should be verified — the 2025 dictionary
  renamed it to `QT_DOC_MED` (Ensino Médio Regular); confirm the Tabela_Docente
  file uses this name and not a variant.

### Change log
2026-05-20 — Initial file created
