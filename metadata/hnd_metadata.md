---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Honduras"
iso3: "HND"
iso2: "HN"
region: "Central America"
last_updated: "2026-05-13"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: true
  outcomes:  true

school_count_total: 16900
school_count_public: 16900
year_range: "2009–2013"
years_available: [2009, 2010, 2011, 2013]

sector_scope: "public"
sector_notes: >
  Source is the SIPLIE (Sistema de Planificación de la Infraestructura
  Educativa) active school registry maintained by the Secretaría de
  Educación. SIPLIE is the MoE's canonical public school register; all
  records are Oficial (government) schools. A small number of Semioficial
  and Comunitaria schools appear in the enrollment files and match SIPLIE
  IDs — these are treated as public schools per Honduran MoE convention
  and are retained via the geo join. Private schools are excluded from all
  tables via the geo join (they do not appear in SIPLIE).

sources:
  - source_id: "hnd_siplie_2020"
    name: "Coordenadas por Centro Educativo — SIPLIE"
    provider: "Secretaría de Educación, Honduras"
    url: "https://data.humdata.org/dataset/centros-educativos-de-honduras"
    url_status: "live"
    access_date: "2020-03-23"
    data_date: "2020-03-23"
    update_frequency: "Unknown"
    format: "XLSX"
    language: "Spanish"
    notes: >
      File dated 23 March 2020 in filename. Contains GPS coordinates and
      basic administrative data for all schools in the public EMIS register.
      Available via the HDX (Humanitarian Data Exchange) portal.

  - source_id: "hnd_emis_2009"
    name: "Matrícula Final por Grados 2009"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: null
    url_status: "not public"
    access_date: "unknown"
    data_date: "2009-12-31"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Grade-level final enrollment statistics for 2009. Contains end-of-year
      flow data (Aprobados, Reprobados, Desertores, Traslados) in addition to
      enrollment counts. Has Consolidada (initial enrollment) column used as
      the dropout denominator for 2009. Available from the Secretaría de
      Educación estadísticas portal.

  - source_id: "hnd_emis_2010_2011"
    name: "Estadística Final 2010–2011"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: null
    url_status: "not public"
    access_date: "unknown"
    data_date: "2011-12-31"
    update_frequency: "Annual"
    format: "CSV"
    language: "Spanish"
    notes: >
      Combined grade-level final enrollment and flow statistics for 2010 and
      2011 in a single file (distinguished by Año column). Includes Aprobados,
      Reprobados, Desertores, Traslados. Does not include Consolidada (initial
      enrollment) — implied initial enrollment computed as Final + Desertores
      + Traslados for dropout calculation.

  - source_id: "hnd_emis_infra_2011"
    name: "Matrícula Inicial 2011 — Infraestructura por Centro Educativo Completo"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: null
    url_status: "not public"
    access_date: "unknown"
    data_date: "2011-01-01"
    update_frequency: "Annual"
    format: "CSV"
    language: "Spanish"
    notes: >
      School-level infrastructure survey collected at start of the 2011
      academic year. One row per school × ISCED level; multi-level schools
      have multiple rows under the same Codigo.1.

  - source_id: "hnd_emis_infra_2010"
    name: "Infraestructura 2010 (42_Infraestrcutura.xlsx)"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: "http://estadisticas.se.gob.hn/see/archivos_descargables.php"
    url_status: "unknown"
    access_date: "unknown"
    data_date: "2010-01-01"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      School-level infrastructure data for 2010 only (despite website
      description suggesting 2010–2012, the file contains only periodo=2010).
      NOT used in the canonical resources table. The id_centro column is an
      internal survey ID, not the EMIS CodigoCentro, and no crosswalk is
      available. A name-based join was considered but rejected due to ambiguous
      duplicate school names in the geo file. Raw file retained in sources/HND/
      for potential future use if a crosswalk becomes available.

  - source_id: "hnd_emis_teachers_2010"
    name: "Estadística Inicial 2010 por Nivel / Sub-nivel"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: "http://estadisticas.se.gob.hn/see/archivos_descargables.php"
    url_status: "unknown"
    access_date: "unknown"
    data_date: "2010-01-01"
    update_frequency: "Annual"
    format: "CSV"
    language: "Spanish"
    notes: >
      School-level initial statistics for 2010. One row per school (already
      aggregated, not by grade). Contains teacher counts (male/female) and
      initial enrollment. Used for teachers_total, teachers_male,
      teachers_female in the personnel table for 2010 only. Initial enrollment
      from this file is not used — final enrollment from hnd_emis_2010_2011
      is preferred for consistency.

  - source_id: "hnd_emis_2013"
    name: "Matrícula Inicial 2013 por Grado — SEE"
    provider: "Secretaría de Educación, Honduras — USINIEH"
    url: "http://estadisticas.se.gob.hn/see/archivos_descargables.php"
    url_status: "unknown"
    access_date: "unknown"
    data_date: "2013-01-01"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      School-level initial (beginning-of-year) enrollment for 2013, with sex
      disaggregation by grade (wide format, one column pair per grade).
      Supersedes 79_201308_USINIEH_Matricula_Inicial_2013_No_Oficial.xlsx,
      which had total enrollment only with no sex disaggregation. The No_Oficial
      file is retained in sources/HND/ as a supplementary record. Neither 2013
      file contains outcome flow columns (Aprobados, Reprobados, Desertores).

---

## GEO

**Status:** Available
**Source(s):** hnd_siplie_2020
**Year of geo data:** 2020 (SIPLIE extract dated 23 March 2020)

### Public school subsetting
Source contains 17,525 rows representing all schools in the SIPLIE active
register. After deduplication (10 fully identical duplicate rows removed,
keep first), 17,515 unique schools remain. 615 schools were dropped due to
missing or sentinel coordinates (see Coordinate construction below), yielding
16,900 schools in the final geo file.

### Deduplication
10 rows shared an identical CodigoCentro with another row and were fully
identical across all columns. These appear to be data entry duplicates in the
source export. First occurrence retained.

### Coordinate construction
Coordinates taken from source `Latitud` and `Longitud` columns.
`coordinate_source = 'official_emis'`, `coordinate_precision = 'exact'`
for all retained schools.

615 schools had missing coordinates encoded as a sentinel value (Latitud ≈
0.0000090, Longitud ≈ −91.489) rather than true null. Both columns were
nulled together when either value triggered the sentinel thresholds
(Latitud < 0.1 OR Longitud < −90.0). Schools with sentinel coordinates
were dropped from the geo file entirely — the schema requires `coordinate_source`
and `coordinate_precision` to be never null, and no fallback coordinate
source was available for these schools.

Coordinate bounding box for validation: 13.0–16.5°N, −89.4–−83.0°E.
One school (J.D.N HORIZONTE FELIZ, CodigoCentro 100300045) had a longitude
of −91.59°W, which falls in Guatemalan territory and was treated as a
sentinel value.

### ID scheme
`geo_id` format: `HND_{zero-padded 6-digit integer}` (e.g. `HND_000001`).
Assigned after sorting schools alphabetically by `NombreCentro` for
reproducibility.

`source_id` = `CodigoCentro` verbatim from SIPLIE. Format is a 9-digit
numeric string with a leading zero (e.g. `010100001`). The leading zero
is part of the official EMIS code structure (first two digits = department
code). Retained as-is — not stripped.

**Important:** enrollment and infrastructure source files store the same ID
*without* the leading zero (e.g. `10100001`). All joins between the geo file
and personnel/resources/outcomes files normalise IDs by stripping leading
zeros before matching, then use `geo_id` for output. This normalisation is
handled in each cleaning script.

### ISCED level mapping
ISCED level mapped from source `Nivel` column, which records the education
level(s) offered at the school. Multi-level schools have slash-separated
values (e.g. `Básica / Pre-Básica-Jardines`). Each component is mapped
independently and the resulting codes are pipe-joined in sorted order:

| Nivel value | ISCED |
|-------------|-------|
| Pre-Básica-Jardines | 0 |
| Pre-Básica-CCPREB | 0 |
| Básica | 1\|2 |
| Básica - Adultos | 1\|2 |
| Media | 3 |

`Básica` (grades 1–9) maps to `1|2` because it spans both primary (grades
1–6, ISCED 1) and lower secondary (grades 7–9, ISCED 2) under a single
administrative record with no within-school disaggregation. 499 schools
have `Nivel = NA` in the source; `isced_level` is set to NA for these.

`school_type` retains the raw `Nivel` string verbatim, including slash-separated
multi-level values, per schema convention.

| isced_level | Count |
|-------------|-------|
| 1\|2 (Básica) | 10263 |
| 0 (Pre-Básica) | 5112 |
| 3 (Media) | 415 |
| 0\|1\|2 (mixed) | ~400 |
| 1\|2\|3 (mixed) | ~111 |
| NA | 499 |

### Administrative hierarchy
`adm0` = "Honduras" (hardcoded).

`adm1`, `adm2`, `adm3` assigned via spatial join to GeoBoundaries ADM1,
ADM2, and ADM3 boundaries using the `join_admin_boundaries` utility.
Source `Departamento` and `Municipio` columns are not used for adm fields —
all admin names come from GeoBoundaries to ensure consistent naming
conventions across countries. GeoBoundaries provides ADM1 (18 departments)
and ADM2 (298 municipalities) for Honduras; ADM3 availability should be
confirmed in the cleaning run output — set to NA if not available.

### Urban/rural classification
`urban_rural` taken directly from source `Urbano / Rural` column, mapped
to schema values: `Urbano` → `urban`, `Rural` → `rural`. No reclassification
applied. Distribution in the final geo file:

| urban_rural | Count |
|-------------|-------|
| rural | 14,589 |
| urban | 2,311 |

### Known issues
- 615 schools dropped due to missing coordinates. These represent ~3.5% of
  the SIPLIE register and are disproportionately likely to be small rural
  schools (SIPLIE GPS collection was incomplete at collection date). They
  have no representation in any of the four tables.
- 499 schools have `Nivel = NA` in the source. These schools have
  `isced_level = NA` and `school_type = NA` in the geo file.
- The SIPLIE register reflects the 2020 active school list. Personnel,
  resources, and outcomes data are from 2009–2011. Schools that opened
  after 2011 or closed before 2020 may appear in the geo file without
  panel data, or vice versa.

---

## PERSONNEL

**Status:** Available — enrollment 2009–2011, 2013; teachers 2010 only
**Source(s):** hnd_emis_2009, hnd_emis_2010_2011, hnd_emis_teachers_2010, hnd_emis_2013
**Years available:** 2009, 2010, 2011, 2013

### Coverage

| Year | Schools with enrollment | Schools with teachers | Enrollment type |
|------|-------------------------|-----------------------|-----------------|
| 2009 | 15,827 | — | Final |
| 2010 | 14,943 | 10,602 | Final |
| 2011 | 15,658 | — | Final |
| 2013 | 16,313 | — | Initial |

### Enrollment columns
`enrollment_total`, `enrollment_male`, `enrollment_female` are populated
for all four years.

**2009:** sourced from `Final F` and `Final M` columns in the grade-level
file. Each school has multiple rows (one per grade); counts are summed to
school level. `enrollment_total` computed as `female + male` — verified to
equal the source `Final T` column with zero discrepancies > 1 student.

**2010 / 2011:** sourced from `MATRICULA FINAL femenino` and `MATRICULA FINAL
masculino` columns in the combined final statistics file. `enrollment_total`
computed as `female + male`.

**2013:** sourced from `90_201311_USINIEH_Matricula_Inicial_2013_SEE_por_Grado.xlsx`.
Wide-format file with one column pair (Femenino/Masculino) per grade. All
grade columns are summed to school level. Uses **initial** (beginning-of-year)
enrollment — the only 2013 source available. Inconsistent with 2009–2011
which use final enrollment. See outstanding issues.

2009–2011 use final (end-of-year) enrollment per UIS convention. The 2009
source also contains `Consolidada` (initial enrollment) and `Ingresos` (new
entrants) columns; these are used in hnd_outcomes.py but not here.

### Teacher columns
`teachers_total`, `teachers_male`, `teachers_female` are populated for
**2010 only**, sourced from `12_Estadistica_inicial_2010_porNivelSubNivel.csv`.
This file is already aggregated to school level (one row per school) and
contains actual headcounts. 10,602 geo schools have teacher data for 2010.

`pupil_teacher_ratio` is computed as `enrollment_total / teachers_total` for
2010 rows where both values are available (10,225 schools). Mean PTR = 29.2,
median = 27.0. `pupil_teacher_ratio` is NA for all other years.

`teachers_qualified` and `classrooms_total` are NA throughout — not collected
in any source file.

Note: `30_Estadistica_inicial_2011` and `49_Estadistica_inicial_2012` both
contain a `Docentes` column but it is a binary 0/1 indicator per school ×
subnivel row, not a teacher headcount. Every school sums to exactly 1 after
aggregation. These files are excluded from the canonical personnel table.

### 2012 exclusion
`49_Estadistica_inicial_2012` covers only pre-basic (subnivel 4, CCEPREB)
rows — it is not a full school enrollment file. No usable enrollment or
teacher count data exists for 2012.

### Null row decision
Schools in the geo file with no enrollment record for a given year are
excluded (no null rows inserted). A row is only written where actual
enrollment data exists. This prevents inflation of school counts in
downstream completeness analyses.

### Sector filtering
2009 source: rows with `Administración == 'Privada'` dropped before
aggregation. Semioficial, Comunitaria, and Municipal schools are retained —
these match SIPLIE IDs and are treated as public per MoE convention.
2010/2011 source: filtered to `Tipo Administracion == 'Publico'`.
2010 teacher source: filtered to Oficial, Comunitaria, Municipal, Semioficial.
2013 source: filtered to Oficial, Comunitaria, Municipal, Semioficial.

### ID normalisation
See geo section. Leading zeros stripped from source EMIS codes before
matching to `source_id` in the geo file.

---

## RESOURCES

**Status:** Available — 2011 only; partial variable coverage
**Source(s):** hnd_emis_infra_2011
**Years available:** 2011

### Coverage
15,844 geo schools have resources data for 2011. 1,056 geo schools have
no infrastructure record.

### Excluded source
The 2010 infrastructure file (hnd_emis_infra_2010 / 42_Infraestrcutura.xlsx)
contains equivalent infrastructure variables but uses an internal survey ID
(`id_centro`) that cannot be linked to the EMIS CodigoCentro. A name-based
join was considered and rejected — school names are not unique in the geo
file (20 ambiguous cases identified). This file is retained in sources/HND/
as a supplementary record.

### Deduplication
The 2011 infrastructure file has one row per school × ISCED level. Multi-level
schools appear under the same `Codigo.1` with one row per level. Deduplicated
to one row per school by taking `max()` across all level rows. For binary
variables (water, electricity, internet, computers), this means a school is
coded `1` if any level row reports the resource — appropriate for physical
infrastructure shared across the building. For `computers`, `max()` captures
the highest PC count reported across levels, which may marginally overstate
availability if PCs are assigned to specific level programmes.

### Variable mapping and coverage

**`water_basic`** — source: `Tipo Agua`

| Tipo Agua | water_basic | water_improved | Count |
|-----------|-------------|----------------|-------|
| Potable | 1 | 1 | 10,727 |
| Pozo | 1 | 0 | 1,590 |
| Río | 0 | 0 | 719 |
| Otro | 0 | 0 | 402 |
| Ninguna | 0 | 0 | 188 |
| NA | NA | NA | 2,218 |

`Pozo` (well) is mapped to `water_basic = 1` per project decision. The JMP
'basic' tier requires a *protected* well; the source does not distinguish
protected from unprotected wells. This mapping is conservative and may
overstate access in areas where wells are unprotected. `water_improved = 0`
for Pozo, since improved status requires a piped/treated source.

**`electricity`** — source: `Suministro Electricidad`. Any non-Ninguno value
coded as 1. Distribution: ENEE (grid) 7,166; Solar 399; Motor (generator)
51; Otros 134; Ninguno 5,876; NA 2,218.

- Schools with electricity: 7,785 (49.1%)
- Schools without electricity: 5,841 (36.9%)
- NA: 2,218 (14.0%)

**`internet`** — source: `Tiene Internet` (Si/No). Only 202 schools (1.3%)
report internet access. `internet_type` is NA throughout — not collected
in source.

**`computers`** — source: `Cant. PC Alumnos` (count of student PCs).
Mapped to binary: ≥ 1 → 1, 0 → 0. Represents whether the school has any
computers available for student instructional use. 2,047 schools (12.9%)
have at least one student PC. No zero-padding issue — field is numeric.

**Not collected in source:** `sanitation_basic`, `sanitation_sex_separated`,
`handwashing_basic`, `library`, `internet_type`, `classrooms_total`.
All set to NA throughout.

### Null row decision
Same as personnel: schools with no infrastructure record for 2011 are
excluded. No null rows inserted.

---

## OUTCOMES

**Status:** Available — 2009, 2010, 2011; within-year flow rates only
**Source(s):** hnd_emis_2009, hnd_emis_2010_2011
**Years available:** 2009, 2010, 2011

### Computation method
`outcome_method = 'within_year_flow'` for all rows. Rates are computed from
end-of-year EMIS flow statistics within a single academic year. This is not
equivalent to the UIS reconstructed cohort method, which tracks students
across consecutive years. Within-year flow rates are the standard reporting
format for school-level outcome data in Honduran and broader Latin American
MoE EMIS systems (LLECE / UNESCO OREALC convention).

| Rate | Formula | Denominator |
|------|---------|-------------|
| `promotion_rate` | Aprobados / Final | End-of-year enrollment |
| `repetition_rate` | Reprobados / Final | End-of-year enrollment |
| `dropout_rate` | Desertores / Initial | Initial enrollment |

The denominator for `promotion_rate` and `repetition_rate` is `Final`
(end-of-year enrollment), because Aprobados and Reprobados are counts of
students present at year end.

The denominator for `dropout_rate` is initial enrollment, because dropouts
exit before the final count:
- **2009:** `Consolidada` column used directly (true initial enrollment,
  explicitly recorded in source).
- **2010 / 2011:** `Consolidada` not available. Implied initial enrollment
  computed as `Final + Desertores + Traslados`. This is a slight undercount
  if any mid-year new entrants (`Ingresos`) subsequently dropped out before
  year end — those students would not be captured in implied initial. The
  resulting dropout rate may be marginally overstated for 2010/2011.

All rates expressed as proportions (0.0–1.0).

### Pre-basic exclusion
Rates are not computed for schools whose SIPLIE `Nivel` is purely pre-basic
(`Pre-Básica-Jardines`, `Pre-Básica-CCPREB`, or combinations of the two).
Pass/fail grading (Aprobados/Reprobados) does not apply at ISCED 0. These
schools have no rows in the outcomes table. Multi-level schools that include
at least one graded level (e.g. `Básica / Pre-Básica-Jardines`) are retained —
their flow counts aggregate across all levels, with graded levels dominating.

### Internal consistency check
Per schema checklist: rows where `|Aprobados + Reprobados − Final| > 2% of
Final` have `promotion_rate` and `repetition_rate` set to NA. `dropout_rate`
is also set to NA for the same rows for consistency, since a failing
internal check indicates unreliable flow data that undermines all three rates.
Schools where `Final == 0` are also set to NA.

| Year | Schools in outcomes | Rates valid | Rates NA (failed check) |
|------|---------------------|-------------|-------------------------|
| 2009 | 11,252 | 10,018 | 1,055 |
| 2010 | 10,812 | 9,793 | 1,018 |
| 2011 | 11,032 | 9,866 | 1,165 |

The internal check failure rate (~9–11% of graded schools per year) is
primarily concentrated in schools with small enrollment where rounding
errors in the source produce non-trivial discrepancies.

### Not available
`completion_rate` and `gross_intake_ratio` are NA throughout. These indicators
require either a terminal-grade cohort count or population denominators not
available in the source EMIS files.

### outcome_reference_grade
`all_grades` for all rows. Rates are aggregated across all grades to the
school level. Grade-level flow data is available in supplementary files
(hnd_emis_2009 and hnd_emis_2010_2011) for users who require grade-level
disaggregation.

### 2013 exclusion
Neither 2013 source file contains outcome flow columns (Aprobados, Reprobados,
Desertores). Both `90_2013` (used for personnel) and `79_2013` record initial
enrollment only. Outcomes cannot be computed for 2013.

---

## GENERAL NOTES

### Source availability
All Honduras source files are internal MoE extracts provided directly.
None are publicly downloadable. Files are retained in `sources/HND/`.

### Harmonization decisions
- `school_name_romanized` set to NA — Honduras school names are in Latin
  script (Spanish). No transliteration required.
- `status = 'open'` assigned to all geo schools — SIPLIE is an active
  school registry; no closure data is present in the source.
- `sector = 'public'` for all rows — SIPLIE contains only public MoE schools.
- Sorted alphabetically by `NombreCentro` before assigning `geo_id` to
  ensure reproducible ID assignment across re-runs.
- GHSL-SMOD classification (`ghsl_smod_code`, `ghsl_urban_rural`) not yet
  applied — pending global raster sampling step.

### Outstanding issues
- 615 schools dropped for missing coordinates. If GPS coordinates become
  available for these schools (e.g. from a more recent SIPLIE extract or
  field survey), they could be added with new `geo_id` values.
- Teacher data available for 2010 only (10,602 schools). No teacher counts
  exist for 2009, 2011, or 2013 in any available source file. The 2011 and
  2012 initial statistics files (30_2011, 49_2012) contain a Docentes column
  but it is a binary indicator, not a headcount.
- Resources data available for 2011 only. The 2010 infrastructure file
  (42_Infraestrcutura.xlsx) cannot be joined without a crosswalk between
  `id_centro` and `CodigoCentro`.
- 2013 enrollment uses initial rather than final enrollment, inconsistent
  with 2009–2011. No final enrollment file exists for 2013 in the available
  sources. Neither 2013 file contains outcome flow data.
- 2012 is absent from all tables. The only 2012 file (49_2012) covers
  pre-basic subnivel rows only and contains no usable enrollment or teacher
  counts for the full school population.
- The gap between the geo register (2020) and the panel data (2009–2013)
  means some schools in the geo file have no panel data, and some schools
  in the panel data do not appear in the geo file. The latter are silently
  dropped via the geo join in all cleaning scripts.

### Change log
2026-05-13 — Initial file created
2026-05-13 — Updated after full source inventory: added hnd_emis_teachers_2010
             and hnd_emis_2013 sources; personnel updated with 2010 teacher
             counts and 2013 sex-disaggregated enrollment (90_2013); SIPLIE
             URL updated; 42_Infraestrcutura year coverage corrected to 2010
             only; 2012 confirmed absent; outstanding issues revised.
