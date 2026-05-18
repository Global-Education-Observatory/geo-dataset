# ═══════════════════════════════════════════════════════════════════
# GEO Dataset — Country Harmonisation Note
# ═══════════════════════════════════════════════════════════════════

country:        "Colombia"
iso3:           "COL"
iso2:           "CO"
region:         "South America"
last_updated:   "2026-05-18"
prepared_by:    "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: false
  outcomes:  false

school_count_geo: ~39000   # exact count pending final spatial join
year_range_personnel: "TBD"
years_available_personnel: []   # to be populated after personnel script run

sector_scope: "public"

---

## 1. Country Overview

Colombia's national school EMIS is administered by the Ministerio de Educación Nacional (MEN) through the SIMAT system (Sistema Integrado de Matrícula). SIMAT registers schools at two administrative levels: the **institución educativa** (establishment), which is the legal and administrative unit, and the **sede** (physical campus), which is the operational unit. Each establishment may operate one or more sedes, each with its own location, enrollment, and physical characteristics.

The Colombian education system covers Preescolar (ISCED 0), Educación Básica Primaria (ISCED 1, Grades 1–5), Educación Básica Secundaria (ISCED 2, Grades 6–9), and Educación Media (ISCED 3, Grades 10–11). Adult education (*Educación para Adultos*) is delivered in parallel through a separate track using Ciclo designations (Ciclo 1–6 Adultos) and is not part of the regular school-age system.

---

## 2. Unit of Observation — Country Deviation

**The unit of observation in all four tables is the SEDE, not the establishment.**

This is a documented deviation from the default schema convention. The rationale is as follows:

- Colombia's SIMAT assigns a unique national identifier (`CODIGO_DANE_SEDE`) to each sede. This code is stable across years and is the finest-grained unit for which SIMAT reports enrollment, infrastructure, and outcomes.
- Sedes within the same establishment frequently differ substantially in their characteristics. Analysis of the 2019 source data found that 1,098 establishments contain sedes classified as both urban and rural; the median geographic spread between sedes of the same establishment is 5.5 km, and 2,011 establishments have sedes more than 10 km apart. The most dispersed establishment has sedes 342 km apart, distributed across the Amazon basin.
- Enrollment ratios between the largest and smallest sede within an establishment have a median of 13.5x, ranging up to 845x. Infrastructure access (electricity, internet, water) plausibly differs between principal urban sedes and remote rural annexes of the same institution.
- Aggregating to the establishment level would mask exactly the kind of within-country spatial and resource inequality the GEO dataset is designed to study.

**Identifiers:**
- `source_id` = `CODIGO_DANE_SEDE` — the unique sede code, retained verbatim as the primary school identifier across all four tables.
- `source_id_institution` = `CODIGO_DANE` — the parent establishment code, appended as a supplementary column (after canonical schema columns) in all four tables. Allows grouping by institution for users who need establishment-level aggregation.

---

## 3. Sources

### 3.1 Geo Table

- **source_id:** `col_men_sedes_2019`
- **Name:** MEN Sedes Educativas Preescolar, Básica y Media
- **Provider:** Ministerio de Educación Nacional (MEN), Colombia
- **URL:** https://www.datos.gov.co/Educaci-n/MEN_SEDES_EDUCATIVAS_PREESCOLAR_B-SICA_Y_MEDIA/x5ay-984n/about_data
- **Portal:** datos.gov.co (Colombia Open Data Portal)
- **Access date:** 2026-05-04
- **Data date:** 2019
- **Format:** CSV
- **Language:** Spanish
- **Notes:** Contains one row per sede with CODIGO_DANE_SEDE, CODIGO_DANE (establishment), sede name, establishment name, department, municipality, zone (urban/rural), PRINCIPAL flag (sede principal vs. sede anexa), and GPS coordinates (COORDENADA_Y_SEDE, COORDENADA_X_SEDE). This file defines the geo register — schools present in this extract are those active in SIMAT as of 2019. Schools that opened after 2019 or closed before 2019 are not represented.

### 3.2 Personnel Table

- **source_id:** `col_men_matricula_full`
- **Name:** MEN Matrícula en Educación en Preescolar, Básica y Media
- **Provider:** Ministerio de Educación Nacional (MEN), Colombia
- **URL:** https://www.datos.gov.co/Educaci-n/MEN_MATRICULA_EN_EDUCACION_EN_PREESCOLAR-B-SICA-Y-/ngw5-c5nw/about_data
- **Portal:** datos.gov.co (Colombia Open Data Portal)
- **Access date:** 2026-05-18
- **Data date:** Multi-year (years TBD pending full script run)
- **Format:** CSV
- **Language:** Spanish
- **Notes:** Disaggregated enrollment extract from SIMAT. Each row represents a unique combination of sede × year × jornada × grade × methodology × gender × age × ethnic group. Enrollment figures are summed across all in-scope combinations to produce sede × year totals. See filtering decisions in Section 5.1.

---

## 4. Geo Table — Decisions and Coverage

### 4.1 Coordinate Source and Precision

Coordinates are taken verbatim from the MEN sedes file (`COORDENADA_Y_SEDE` = latitude, `COORDENADA_X_SEDE` = longitude). All coordinates in the source are recorded to exactly **2 decimal places** (~1.1 km precision at Colombia's latitudes) — this is a systematic SIMAT data entry convention, not GPS precision. No coordinates with 3 or more decimal places were found across the full 39,000+ sede extract.

A further consequence of this rounding is that **29% of sedes share an identical coordinate pair** with at least one other sede. This is visually apparent as a regular grid pattern when plotted in GIS software. Likely causes are: (1) rural anexa sedes assigned the coordinates of their parent principal sede, and (2) manual coordinate entry rounded to 2 decimal places.

- `coordinate_source = "official_emis"` for all sedes
- `coordinate_precision = "approximate"` for all sedes
- Users should not use these coordinates for proximity analysis below ~2 km resolution. GHSL sampling at 1 km resolution remains meaningful given this precision level.

### 4.2 Missing Coordinates

Sedes with zero values in either coordinate field are treated as missing (zero is a common SIMAT placeholder, not a valid Colombian coordinate). Sedes with missing coordinates are **dropped from the geo file** — they cannot be spatially located or joined to administrative boundaries.

Approximately 4,700 sedes (of 43,956 public sedes in the raw source) had missing or zero coordinates and were excluded.

### 4.3 Spatial Sanity Check — adm1 Boundary Drop

After parsing coordinates, each sede is spatially joined to GeoBoundaries ADM1 (department) boundaries for Colombia. Sedes that do not fall within any department boundary are dropped. This serves as the coordinate sanity check — erroneous coordinates that happen to be non-zero but fall outside Colombian territory are caught and excluded here rather than through bounding-box filters.

### 4.4 Administrative Geography

`adm1` (department) and `adm2` (municipality) are assigned via spatial join to GeoBoundaries ADM1 and ADM2 boundaries respectively, using the `join_admin_boundaries` pipeline utility. The source file contains `DEPARTAMENTO` and `MUNICIPIO` columns in Spanish, which were used for cross-checking but not as the canonical adm values.

`adm3` is set to NA — Colombia's GeoBoundaries ADM3 was not available at time of processing.

### 4.5 ISCED Level

The source file does not disaggregate ISCED level by sede — the file title indicates coverage of Preescolar, Básica, and Media (ISCED 0–3) but individual sedes are not labelled by level. `isced_level = "0123"` is assigned to all rows. A future join to a grade-level SIMAT extract could refine this to the sede level.

### 4.6 School Register Provenance

The geo file is derived from the 2019 MEN sedes extract. It represents a snapshot of active public sedes as of 2019. `status = "open"` should be interpreted as "active in SIMAT as of 2019." Sedes that opened after 2019 or closed before 2019 are absent from the register and consequently from all four pipeline tables.

### 4.7 School Type

`school_type` is populated from the SIMAT `PRINCIPAL` flag:
- `sede_principal` — the main campus of the institution, where the director is based
- `sede_anexa` — a satellite campus under the same establishment

This is a Colombia-specific classification retained in national terminology per schema convention.

### 4.8 Urban / Rural

`urban_rural` is mapped from the source `ZONA` field:
- `URBANA` → `urban`
- `RURAL` → `rural`

No `peri_urban` category exists in the Colombian source. GHSL-derived `ghsl_urban_rural` will provide a standardised cross-country classification once applied.

---

## 5. Personnel Table — Decisions and Coverage

### 5.1 Enrollment Filtering

The SIMAT enrollment extract is highly disaggregated (sede × year × jornada × grade × methodology × gender × age × ethnic group). The following filters are applied before aggregating to sede × year totals:

**Jornada (school shift) filter — excluded:**
- `Fin de Semana` (weekend) — adult education delivery slot (*Educación para Adultos*, Ciclo 1–6 Adultos via CAFAM methodology). Excluded.
- `Nocturna` (night shift) — weeknight equivalent of Fin de Semana; same adult Ciclo population. Excluded.

**Jornada retained:** Mañana, Tarde, Unica, Completa — all regular school-age delivery shifts.

**Grade filter — retained (ISCED 1–3 only):**
Primero, Segundo, Tercero, Cuarto, Quinto (ISCED 1), Sexto, Séptimo, Octavo, Noveno (ISCED 2), Décimo, Once (ISCED 3).

**Grades excluded:**
- Prejardín, Prejardin II, Jardín I, Transición — ISCED 0 (preschool). Excluded for cross-country consistency; no other pipeline country includes ISCED 0 enrollment. Documented here; ISCED 0 enrollment exists in the source for users who need it.
- Ciclo 1–6 Adultos — adult education cycles, confirmed excluded via jornada filter but also excluded here as a belt-and-suspenders check.
- 12º Normal, 13º Normal — *Escuela Normal Superior* teacher training program, post-secondary (ISCED 5). Excluded.
- PFC1–PFC4 (*Programa de Formación Complementaria*) — formal teacher certification track, ISCED 5. Excluded.
- INTR-Semestre Introductorio — introductory semester of teacher training program. Excluded.
- Aceleración del Aprendizaje — remedial catch-up program for overage students; not standard grade enrollment. Excluded.
- Grade code `20` — unresolvable numeric code with no label match; excluded pending source clarification.

**Methodology filter:** No methodology filter applied after jornada and grade filters. The two remaining methodology values are:
- `Educación tradicional` — conventional classroom instruction (urban/standard)
- `Post primaria` — flexible rural multigrade model (*Modelos Educativos Flexibles*). Included. PTR figures for Post primaria schools will be structurally lower than traditional schools by design — one teacher covers multiple grades. Users should filter by `urban_rural` when comparing PTR cross-school.

**Sector filter:** `SECTOR == "OFICIAL"` only.

### 5.2 Gender Disaggregation

`enrollment_female` and `enrollment_male` are produced by pivoting on the `GENERO` field (`Femenino` / `Masculino`) after summing across all other dimensions within scope. `enrollment_total` is computed as the sum of the two.

### 5.3 Teachers and Classrooms

Teacher headcounts and classroom counts are not available in the SIMAT enrollment extract. `teachers_total`, `teachers_male`, `teachers_female`, `teachers_qualified`, `pupil_teacher_ratio`, and `classrooms_total` are NA for all rows.

### 5.4 Merge Logic

Personnel rows are restricted to sedes present in `col_geo.csv` via an inner join on `source_id` (`CODIGO_DANE_SEDE`). Sedes in the enrollment extract that were dropped from geo (missing coordinates, outside ADM1 boundary) are excluded from personnel. Sedes in geo with no enrollment data in a given year are excluded per schema convention (no null rows inserted).

---

## 6. Resources Table

Not available.

---

## 7. Outcomes Table

Not available.

---

## 8. Known Limitations and Caveats

1. **Coordinate precision:** All coordinates are rounded to 2 decimal places (~1.1 km). 29% of sedes share a coordinate pair with another sede. Not suitable for fine-grained proximity analysis.
2. **2019 geo snapshot:** The school register reflects active sedes as of 2019 only. Panel coverage in personnel is limited to sedes present in the 2019 register.
3. **ISCED level unresolved:** `isced_level = "0123"` is a placeholder; true sede-level ISCED breakdown requires a grade-level join not yet performed.
4. **No teacher data:** SIMAT enrollment extracts do not include teacher counts. PTR cannot be computed for any year.
5. **Adult education in source:** Fin de Semana and Nocturna jornadas, and all Ciclo Adultos grades, are present in the raw source and have been excluded. Users requiring adult enrollment figures should use the raw SIMAT extract.
6. **ISCED 0 excluded:** Preschool enrollment (Prejardín, Jardín, Transición) exists in the source but is excluded for cross-country consistency.

---

## 9. Changelog

| Date       | Change |
|------------|--------|
| 2026-05-18 | Initial metadata created. Geo and personnel decisions documented. |