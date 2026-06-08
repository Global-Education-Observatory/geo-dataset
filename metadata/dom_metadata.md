---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Dominican Republic"
iso3: "DOM"
iso2: "DO"
region: "Latin America and the Caribbean"
last_updated: "2026-06-08"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: false
  outcomes:  false

school_count_total: 6021
school_count_public: 6021
year_range: "2022"
years_available: [2022]

sector_scope: "public"
sector_notes: >
  Source dataset contains records across three sector categories: PÚBLICO/PUBLICO
  (public), PRIVADO (private), and SEMIOFICIAL (semi-official, state-subsidised
  Catholic/faith schools). Only PÚBLICO/PUBLICO rows are retained. SEMIOFICIAL
  schools are excluded: unlike the MPO-subsidised schools included in BGD, DR
  semioficial schools are partially fee-charging and not universally free to
  attend for basic education, and are therefore not treated as public schools
  under the GEO schema. PRIVADO schools are excluded per standard V1 scope.
  Within the public sector, adult and non-formal education programs are
  excluded: ADULTOS, BASICA DE ADULTOS, PREPARA REGULAR, PREPARA ACELERA, and
  their combinations. Pre-primary-only centros (Nivel = INICIAL) are excluded
  per dataset scope (ISCED 1–3 only). Centros offering INICIAL alongside PRIMARIO
  or SECUNDARIO are retained, with the ISCED 0 component stripped from the
  isced_level value.

sources:
  - source_id: "dom_minerd_centros"
    name: "Estadísticas de Centros Educativos — Periodo Escolar 2023-2024"
    provider: "Ministerio de Educación de la República Dominicana (MINERD)"
    url: "https://datos.gob.do/dataset/centros-educativos-de-republica-dominicana"
    url_status: "live"
    access_date: "2026-06"
    data_date: "2022-2023 and 2023-2024"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Single XLSX file containing school-level records for two academic years:
      2022-2023 (Año = 20222023, n = 7,735 public rows before Nivel filtering)
      and 2023-2024 (Año = 20232024, n = 10,615 total rows). Each row represents
      one Centro Educativo (administrative school program). Columns include:
      Regional (MINERD administrative region), Distrito (district), Provincia,
      Municipio, Centros (centro code and name), Planta Fisica (physical building
      code and name), Sector, Nivel, Matricula (enrollment), Coordenadas Latitud,
      Coordenadas Longitud, Año. The 2023-2024 latitude values contain trailing
      commas that cause numeric parsing to fail unless stripped before conversion.

  - source_id: "geoboundaries_dom"
    name: "geoBoundaries — Dominican Republic ADM1–ADM3"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-06"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "GeoJSON"
    language: "English"
    notes: >
      Attempted for ADM3 (municipality-level) spatial join. GeoBoundaries does
      not provide ADM3 coverage for the Dominican Republic; adm3 is NA for all
      schools. ADM1 and ADM2 sourced directly from source EMIS columns rather
      than GeoBoundaries spatial join (see Administrative hierarchy section).

---

## GEO

**Status:** Available
**Source(s):** dom_minerd_centros
**Year of geo data:** 2022-2023 academic year

### Unit of observation
The unit of observation is the **Centro Educativo** — the administrative school
program unit as defined by MINERD. The source also contains a **Planta Física**
identifier, which is the physical building code. Multiple centros can share a
single Planta Física (e.g., a primary school and a secondary school occupying
the same building are registered as separate centros with distinct names, codes,
and enrollment figures). These are treated as distinct schools in the GEO
Dataset, consistent with the Colombia precedent (sede-level observation).

The Planta Física code is retained as `source_id_institution` — a supplementary
column outside the canonical schema — to enable joining to building-level data
if needed. This mirrors the `source_id_institution` convention established for
Colombia.

### Public school subsetting
The 2022-2023 year slice of the source file contains 7,735 public sector rows
before Nivel filtering. After applying all exclusions:

| Filter step | Rows remaining |
|-------------|---------------|
| Public sector (PÚBLICO/PUBLICO) | 7,579 |
| Exclude adult/non-formal Nivel | 7,003 |
| Exclude INICIAL-only (pre-primary) | 6,320 |
| Exclude missing/unrecoverable coordinates | 6,021 |

Nivel breakdown after filtering (before coordinate exclusions):

| Nivel (source) | isced_level | Count |
|----------------|-------------|-------|
| INICIAL - PRIMARIO | 1 | 3,209 |
| INICIAL - PRIMARIO - SECUNDARIO | 1\|2\|3 | 1,311 |
| SECUNDARIO | 2\|3 | 1,297 |
| PRIMARIO | 1 | 457 |
| PRIMARIO - SECUNDARIO | 1\|2\|3 | 46 |

### ISCED level mapping
ISCED level assigned from the source Nivel column. Dominican Republic secondary
(Secundario/Medio) spans both lower and upper secondary with no within-secondary
level disaggregation available in the EMIS, so it maps to `2|3` throughout.
Centros offering INICIAL alongside in-scope levels are retained; the ISCED 0
component is stripped from the isced_level value because pre-primary is outside
the dataset scope.

| Nivel (source) | isced_level | Rationale |
|----------------|-------------|-----------|
| PRIMARIO | 1 | Primary education, ISCED 1 |
| SECUNDARIO | 2\|3 | Secondary spans ISCED 2 and 3; no sub-level disaggregation available |
| INICIAL - PRIMARIO | 1 | INICIAL (pre-primary) stripped; primary component in scope |
| INICIAL - PRIMARIO - SECUNDARIO | 1\|2\|3 | INICIAL stripped; primary and secondary in scope |
| PRIMARIO - SECUNDARIO | 1\|2\|3 | Both components in scope |
| INICIAL - SECUNDARIO | 2\|3 | INICIAL stripped; secondary component in scope |
| INICIAL | — | Excluded entirely — pre-primary only, outside ISCED 1–3 scope |

`school_type` retains the source Nivel value verbatim, per schema convention.

### Coordinate construction
Coordinates are taken directly from the source EMIS columns `Coordenadas Latitud`
and `Coordenadas Longitud`.

**Coordinate cleaning steps:**

1. **Trailing comma removal (2023-2024 only):** The 2023-2024 year's latitude
   values contain trailing commas (e.g., `18.032553,`) that must be stripped
   before numeric conversion. This issue is absent in the 2022-2023 rows.

2. **Longitude sign correction:** 278 rows in the 2022-2023 year have positive
   longitude values (e.g., `71.74` instead of `-71.74`). The Dominican Republic
   is entirely in the western hemisphere; all valid longitudes must be negative.
   Positive values are corrected by negation.

**Coordinate disposition (2022-2023, n = 6,320 in-scope rows):**

| Outcome | Count |
|---------|-------|
| Valid (within bounding box after correction) | 6,021 |
| Dropped — non-numeric or unrecoverable | 299 |

All retained coordinates are assigned:
`coordinate_source = 'official_emis'`, `coordinate_precision = 'approximate'`

Coordinates are classified as `approximate` rather than `exact` because the EMIS
does not document collection methodology. Visual inspection of a sample of points
suggests building-level or compound-level precision in many cases, but this cannot
be confirmed from the source metadata alone.

### Administrative hierarchy
`adm0` = "Dominican Republic" (hardcoded).

`adm1` and `adm2` are sourced directly from the EMIS source columns rather than
via GeoBoundaries spatial join, because GeoBoundaries does not provide sub-national
coverage for the Dominican Republic at ADM3 and the source administrative columns
are clean and consistently named.

- `adm1` = MINERD administrative region, derived from the `Regional` column by
  stripping the numeric prefix (e.g., `"01 - BARAHONA"` → `"Barahona"`). Note
  that MINERD's 17 administrative regions (regionales) are education-sector
  administrative divisions, not political-geographic provinces. They do not
  correspond 1:1 to the 31 provinces used in national statistics.
- `adm2` = Province (`Provincia` column), title-cased. Provinces are the standard
  political administrative unit at ADM2 level.
- `adm3` = NA for all schools. GeoBoundaries does not provide ADM3 (municipality)
  polygons for the Dominican Republic. Municipality is available in the source
  `Municipio` column but is not used for `adm3` per the project rule that adm
  fields come from GeoBoundaries spatial joins only.

| adm1 (Regional) | Schools |
|-----------------|---------|
| Santo Domingo | 889 |
| La Vega | 513 |
| Santiago | 459 |
| San Juan De La Maguana | 423 |
| San Pedro De Macoris | 378 |
| Azua | 375 |
| San Francisco De Macoris | 371 |
| San Cristobal | 362 |
| Puerto Plata | 303 |
| Nagua | 302 |
| Cotui | 289 |
| Monte Plata | 286 |
| Higuey | 276 |
| Mao | 211 |
| Monte Cristi | 211 |
| Barahona | 203 |
| Bahoruco | 170 |

### Urban/rural classification
`urban_rural` = NA for all schools. The source EMIS does not include an
urban/rural classification field. GHSL-SMOD classification pending global
raster sampling step.

### Known issues
- `adm3` is NA for all schools — GeoBoundaries does not cover DOM at ADM3.
  Municipality names are available in the source `Municipio` column and could
  be populated via a future ONE (Oficina Nacional de Estadística) shapefile
  spatial join.
- 299 schools dropped due to missing or unrecoverable coordinates. These are
  absent from the personnel table as well.
- MINERD `adm1` regions are education-sector administrative boundaries, not
  political provinces. Cross-country comparisons using `adm1` should treat DOM
  adm1 values as MINERD regions rather than standard geographic subdivisions.
- `status = 'unknown'` assigned to all schools — no closure or operational
  status field is present in the source.
- The 2023-2024 latitude column has a data entry artifact (trailing comma) that
  requires string cleaning before numeric parsing. This is handled in
  dom_personnel.py but should be noted if the source file is used independently.

---

## PERSONNEL

**Status:** Partially available (enrollment only; 2022)
**Source(s):** dom_minerd_centros
**Years available:** 2022

### Enrollment
`enrollment_total` taken directly from the source `Matricula` column. No
computation required — the field is a pre-aggregated headcount of students
enrolled at the centro as of the EMIS reference date for the academic year.

The Dominican Republic academic year runs from approximately August to June.
Per the beginning-year convention, 2022-2023 → `year = 2022`.

**Year 2022 (from 2022-2023 rows):**
- Schools with enrollment data: 6,021 (all schools in geo)
- Enrollment nulls: 0
- Mean enrollment: 270 students per school

**Year 2023 (from 2023-2024 rows):**
The 2023-2024 year slice contains enrollment data for 6,430 in-scope public
centros. However, 1,449 of these are dropped due to unrecoverable coordinate
issues in that year's data (including the trailing-comma parsing problem in
latitudes). Personnel rows for year 2023 are restricted to centros present in
DOM_geo.csv (defined from the 2022-2023 year). Of the 6,021 geo schools, 5,957
appear in the 2023-2024 source data with valid enrollment figures; 64 do not
appear (centros that closed or were not reported in 2023-2024). The 164 centros
appearing only in 2023-2024 (new schools) are not included in personnel because
they have no geo_id.

Note: year 2023 enrollment is included in DOM_personnel.csv as a second panel
year despite coordinates not being usable from the 2023-2024 year slice. Enrollment
figures from that year are clean and valid; only the coordinate columns are
problematic.

### Sex disaggregation
The source Matricula column is a total enrollment figure only. No sex
disaggregation is available in this source. `enrollment_male` and
`enrollment_female` are NA throughout.

### Fields not available from this source

| Field | Status |
|-------|--------|
| enrollment_male | NA — source does not disaggregate by sex |
| enrollment_female | NA — source does not disaggregate by sex |
| teachers_total | NA — not collected at school level in this source |
| teachers_male | NA — not collected |
| teachers_female | NA — not collected |
| teachers_qualified | NA — not collected |
| pupil_teacher_ratio | NA — cannot compute without teachers_total |
| classrooms_total | NA — not collected in this source |

---

## RESOURCES

**Status:** Not available
School-level infrastructure data is not publicly available for the Dominican
Republic. MINERD does not publish WASH, electricity, or ICT variables at the
school level in its open data portal.

---

## OUTCOMES

**Status:** Not available
MINERD publishes national exam results (Pruebas Nacionales) at the school level
via datos.gob.do, covering the terminal exams at the end of Básico and
Secundario/Medio levels. However, these reflect pass/fail rates on the national
exit examination only — not within-year flow rates (promotion, repetition,
dropout) across all enrolled students. They are therefore not compatible with the
GEO Dataset outcomes schema (Cameron/EPDC within-year flow methodology) and are
excluded from this release. No alternative school-level outcomes source was
identified.

---

## GENERAL NOTES

### Harmonization decisions
- `geo_id` assigned as DOM_{zero-padded integer} sorted by centro code ascending
  to ensure reproducible ID assignment across re-runs.
- `source_id` is the 5-digit centro code extracted from the `Centros` column
  (e.g., `"02334 - HERNANDO GORJON"` → `"02334"`). This is the MINERD national
  school identifier used in all MINERD administrative systems including Pruebas
  Nacionales, Matricula reports, and the school directory.
- `source_id_institution` is the Planta Física code extracted from the
  `Planta Fisica` column. This is the physical building identifier and enables
  grouping of co-located centros. Retained as a supplementary column outside the
  canonical schema, following the Colombia precedent for sede/institución
  duality.
- `school_name` is the centro name extracted from the `Centros` column, stripped
  of the leading code (e.g., `"02334 - HERNANDO GORJON"` → `"HERNANDO GORJON"`).
  Names are in Spanish (Latin script); `school_name_romanized` is NA throughout.
- `sector = 'public'` assigned to all rows — only PÚBLICO/PUBLICO centros retained.
- `status = 'unknown'` assigned to all schools — no closure or operational status
  field in the source.
- GHSL-SMOD classification (`ghsl_smod_code`, `ghsl_urban_rural`) not yet applied
  — pending global raster sampling step.

### Change log
2026-06-08 — Initial file created
