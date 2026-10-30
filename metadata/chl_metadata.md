---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Chile"
iso3: "CHL"
iso2: "CL"
region: "South America"
last_updated: "2026-09-24"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: false
  outcomes:  true

school_count_total: 4562
school_count_public: 4562
# geo is a single 2025 snapshot. Personnel covers 2004-2025 for enrollment and 2013-2025 for teachers. Outcomes covers 2002-2025.
year_range: "2002-2025"
years_available: [2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

sector_scope: "public"
sector_notes: >
  Public schools are defined from the grouped dependency code COD_DEPE2 in
  the 2025 directory. Retained values are 1 (Municipal, n=4,696) and 5
  (Servicio Local de Educación Pública, n=2,161), 6,857 schools before any
  other filter. Excluded values are 2 (Particular subvencionado, n=7,658),
  3 (Particular pagado, n=2,183), and 4 (Corporación de administración
  delegada, DL 3166, n=70). Particular subvencionado schools are privately
  run and voucher funded, so they are treated as private. This differs from
  the Bangladeshi MPO institutions, where the state pays teacher salaries
  directly at institutions in the national register. Dependency is read from
  the 2025 directory only and is not re-checked for earlier years.

sources:
  - source_id: "chl_mineduc_directorio_2025"
    name: "Directorio Oficial de Establecimientos Educacionales 2025"
    provider: "Centro de Estudios, Ministerio de Educación de Chile (MINEDUC)"
    url: "https://datosabiertos.mineduc.cl/"
    url_status: "unverified"
    access_date: "2026-09"
    data_date: "2025-04-30"
    update_frequency: "Annual"
    contact: "Centro de Estudios MINEDUC"
    format: "CSV"
    language: "Spanish"
    notes: >
      File 20250926_Directorio_Oficial_EE_2025_20250430_WEB.csv. Semicolon
      delimited, UTF-8 with byte order mark, comma decimal separator. One row
      per school (16,768 rows, unique RBD). Contains the national school
      identifier (RBD), name, dependency, urban or rural flag, operating
      status, region, province and commune codes, program codes (ENS_01 to
      ENS_11), 2025 enrollment, and latitude and longitude. The exact dataset
      page URL should be added before release.

  - source_id: "chl_mineduc_matricula"
    name: "Matrícula por estudiante 2004-2025 (bases públicas con MRUN)"
    provider: "Centro de Estudios, Ministerio de Educación de Chile (MINEDUC), from SIGE"
    url: "https://datosabiertos.mineduc.cl/"
    url_status: "unverified"
    access_date: "2026-09"
    data_date: "2004-2025 (30 April of each year)"
    update_frequency: "Annual"
    contact: "Centro de Estudios MINEDUC"
    format: "CSV"
    language: "Spanish"
    notes: >
      One file per year, about 3.5 million student records each. Used to
      derive isced_level in the geo table (grades with enrolled students) and
      to build enrollment counts in the personnel table. Encoding is a local
      code page through 2017 and headers vary across years (lowercase, byte
      order mark, quoted names), so files are read as Latin-1 with normalised
      column names. The 2025 file drops 7 records with a non-binary sex code
      for privacy reasons. Student identifiers (MRUN) are used only to count
      and are not stored in the GEO Dataset.

  - source_id: "chl_mineduc_docentes"
    name: "Cargos Docentes 2003-2025 (bases públicas con MRUN)"
    provider: "Centro de Estudios, Ministerio de Educación de Chile (MINEDUC), from SIGE (SIDOC before 2011)"
    url: "https://datosabiertos.mineduc.cl/"
    url_status: "unverified"
    access_date: "2026-09"
    data_date: "2003-2025 (30 June of each year)"
    update_frequency: "Annual"
    contact: "Centro de Estudios MINEDUC"
    format: "CSV"
    language: "Spanish"
    notes: >
      One row per teaching position, so one person can appear more than once.
      The PERSONAS flag marks each person's principal position. Used to build
      teacher counts in the personnel table. Several columns needed for the
      2015 and later definition are absent in early years (HORAS_AULA before
      2013, COD_ENS and TIT_ID_2 before 2011), so teacher fields are blank
      for those years. Teacher identifiers (MRUN) are not stored.

  - source_id: "chl_mineduc_rendimiento"
    name: "Rendimiento escolar por estudiante 2002-2025 (bases públicas con MRUN)"
    provider: "Centro de Estudios, Ministerio de Educación de Chile (MINEDUC), from RECH (2002-2008) and SIGE (2009 onward)"
    url: "https://datosabiertos.mineduc.cl/"
    url_status: "unverified"
    access_date: "2026-09"
    data_date: "2002-2025 (end of school year status)"
    update_frequency: "Annual"
    contact: "Centro de Estudios MINEDUC"
    format: "CSV"
    language: "Spanish"
    notes: >
      One row per student per year with the final status at the school
      (promoted, repeated, withdrawn, or transferred). Used to compute the
      outcomes table. The 2025 file adds special education students, who are
      excluded here with all other non-regular programs. Coverage in 2002 is
      lower than in later years (3.38 million students against 3.53 million in
      2003).

  - source_id: "geoboundaries_chl"
    name: "geoBoundaries - Chile ADM1 to ADM4"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-09"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "GeoJSON"
    language: "English"
    notes: >
      Used for the spatial join that assigns adm1 to adm3. Source codes for
      region, province and commune in the directory are used only as a
      cross-check.

---

## GEO

**Status:** Available
**Source(s):** chl_mineduc_directorio_2025, chl_mineduc_matricula, geoboundaries_chl
**Year of geo data:** 2025 (directory reference date 30 April 2025)

### Public school subsetting
The directory holds 16,768 schools of all dependencies. Public schools are
selected with COD_DEPE2 equal to 1 or 5.

| COD_DEPE2 | Dependency | Schools | Retained as public |
|-----------|------------|---------|--------------------|
| 1 | Municipal | 4,696 | Yes |
| 5 | Servicio Local de Educación Pública | 2,161 | Yes |
| 2 | Particular subvencionado | 7,658 | No |
| 3 | Particular pagado | 2,183 | No |
| 4 | Corporación de administración delegada | 70 | No |

From the 6,857 municipal and SLEP schools, 4,562 are retained. The other
2,295 are dropped because no ISCED 1 to 3 level can be derived. This count
was worked out during development from the directory and should be checked
against the final run.

| Reason for dropping | Schools |
|---------------------|---------|
| Closed (ESTADO_ESTAB 3) | 1,388 |
| In recess (ESTADO_ESTAB 2) | 338 |
| Authorised without enrollment (ESTADO_ESTAB 4) | 3 |
| Operating, zero enrollment | 227 |
| Operating, enrollment only in pre-primary, special education or adult programs | 339 |

Closed and in-recess schools carry no program codes in the directory and no
regular enrollment, so none has a derivable level. As a result every retained
school has status open.

### ISCED level
isced_level is derived from the grades that have enrolled students in the 2025
matrícula file, using regular child and youth programs only (COD_ENSE 110,
310, and 410 to 910).

- Basic education (110), grades 1 to 6 map to ISCED 1 and grades 7 to 8 map to ISCED 2.
- Secondary programs (310 and the technical-professional and artistic codes), grades 1 to 2 (1º and 2º medio) map to ISCED 2 and grades 3 to 4 map to ISCED 3.
- The level is the union across enrolled grades, pipe-delimited (for example 1|2).
- Pre-primary, adult, and special education students do not count towards level.
- Schools with no youth enrollment in the matrícula file fall back to the directory program codes (110 gives 1|2, 310 and the technical-professional codes give 2|3).

The grade to ISCED rule (basic 1 to 6 as ISCED 1, basic 7 to 8 and 1º to 2º medio as ISCED 2) should be confirmed against the UIS ISCED mapping for Chile before publication.

| isced_level | Count |
|-------------|-------|
| 1\|2 | [FILL] |
| 1\|2\|3 | [FILL] |
| 2\|3 | [FILL] |
| other | [FILL] |

Level derived from matrícula for [FILL] schools and from the directory
fallback for [FILL] schools (printed by chl_geo.py).

### Coordinate construction
Coordinates are taken directly from LATITUD and LONGITUD in the directory
(comma decimals converted). coordinate_source is official_emis for all
schools. The source has no precision flag but the number of reported decimals
varies from 3 to 8, so coordinate_precision is set from that. Four or more
decimals is exact and fewer is approximate.

| coordinate_precision | Count |
|----------------------|-------|
| exact | 4,538 |
| approximate | 24 |

These counts come from a development run and should be checked against the
final output. No retained school is missing a coordinate. Schools outside the
mainland bounding box are printed for review and not dropped. The legitimate
ones (Rapa Nui, Juan Fernández, and any Antarctic territory school) are kept.
[FILL - list any school that was reviewed and changed.]

### Administrative hierarchy
adm0 is "Chile" (hardcoded).

adm1 to adm3 are assigned by spatial join to geoBoundaries [FILL - confirm
which levels were returned, expected region, province and commune]. adm4 is
not part of the schema. Source codes for region, province and commune in the
directory were not used to assign names, only to cross-check the commune name.
[FILL - match rate between adm3 and the source commune name, and the number
of schools left NA at each level.]

### Urban/rural classification
urban_rural is mapped from RURAL_RBD (0 is urban, 1 is rural). This is the
country-reported flag and it is not reclassified.

| urban_rural | Count |
|-------------|-------|
| urban | [FILL] |
| rural | [FILL] |

ghsl_smod_code and ghsl_urban_rural are not yet applied.

### Known issues
- The register is a 2025 snapshot. Schools that closed before April 2025 are not present, even if they operated in earlier years covered by the personnel and outcomes tables.
- Sector is taken from the 2025 directory. A school that changed dependency over time is not identified.
- Coordinate precision is inferred from the number of decimals in the source, not from a provider flag.
- Special education schools that enroll only in special education programs are outside scope and are dropped.

---

## PERSONNEL

**Status:** Available (enrollment 2004 to 2025, teachers 2013 to 2025)
**Source(s):** chl_mineduc_matricula, chl_mineduc_docentes
**Years available:** 2004 to 2025 [FILL - confirm from final file]

One definition is used for every year and follows the 2015 and later files. If
a year's file lacks a column that the definition needs, that source's fields
are left blank for the year and are not approximated.

### Enrollment
enrollment_total is a headcount of students at 30 April in regular child and
youth programs (COD_ENSE 110, 310, and 410 to 910). Pre-primary, adult and
special education students are excluded so that the count matches the ISCED 1
to 3 scope of the geo table and the teacher definition. Schools with an
operating status other than 1 are excluded where ESTADO_ESTAB exists (2015
onward). Earlier files have no such column, but the codebooks report their
totals for operating schools only, so no filter is applied. This assumption
comes from the codebooks and has not been checked against the data.

enrollment_male and enrollment_female come from GEN_ALU (1 and 2). Students
with an undefined sex are counted in the total only, so male plus female can
fall below the total. [FILL - overall gap from the validation printout.]

### Teachers
teachers_total is a headcount at 30 June. Each person is counted once at their
principal school (PERSONAS equal to 1). A person counts as a teacher if their
main function is classroom teaching (ID_IFP equal to 1) or they have more than
zero classroom contract hours (HORAS_AULA), which keeps directors who also
teach and excludes non-teaching directors, technical-pedagogical staff,
inspectors and staff working for the sostenedor. The teacher must also teach
in a program counted in the enrollment above (COD_ENS_1 or COD_ENS_2).

Because each person is assigned to one school only, a teacher working at
several schools is counted at their principal school. The count is a
headcount and not full-time equivalent.

teachers_male and teachers_female come from DOC_GENERO (1 and 2). Non-binary
teachers (code 3) are counted in the total only.

teachers_qualified counts teachers holding a teaching degree, meaning
TIT_ID_1 or TIT_ID_2 equal to 1 (titled in education). This is the national
qualification standard used here.

pupil_teacher_ratio is computed as enrollment_total divided by teachers_total.
It is blank wherever either input is blank or teachers_total is zero.

### Fields not available

| Field | Status |
|-------|--------|
| teachers_total, _male, _female, _qualified | Blank before 2013 because HORAS_AULA is absent |
| pupil_teacher_ratio | Blank wherever teachers are blank |
| classrooms_total | NA - not collected in these sources |

### Known issues
- The reference dates differ between enrollment (30 April) and teachers (30 June).
- Teacher counts use principal-school assignment, so schools that share teachers with other schools can be undercounted.
- The panel covers only schools in the 2025 register. Dependency in earlier years is not checked, so a school that was private in an earlier year but is public in 2025 still appears.
- Pre-2015 files have no operating status column (see the enrollment note above).

### Planned validation
The Resumen de Matrícula por establecimiento and the Dotación Docente por
establecimiento files (codebooks received) are candidates for an external
reconciliation. The first gives official school totals for enrollment and the
second gives classroom teacher counts (DC_A) for 2003 to 2025. Neither has been
run yet. [FILL - add results once available.]

---

## RESOURCES

**Status:** Not available
No school-level source for water, sanitation, electricity, or other
infrastructure has been identified in MINEDUC's public data at the time of
drafting. [FILL - confirm, or update if a source is found.]

---

## OUTCOMES

**Status:** Available
**Source(s):** chl_mineduc_rendimiento
**Years available:** 2002 to 2025 [see outstanding issues]

Outcomes are computed at school level from the final status of each student in
regular child and youth programs (COD_ENSE 110, 310, and 410 to 910). Adult,
special education and pre-primary records are excluded. ESTADO_ESTAB equal to
1 is applied from 2015 (see the note in the personnel section for earlier
years).

### Final status
SIT_FIN_R is used and not SIT_FIN. In SIT_FIN, students who transferred
between schools during the year are coded as withdrawn. In 2016, 188,264 of
the 281,514 students coded withdrawn in SIT_FIN are coded as transferred in
SIT_FIN_R, and only 93,250 are genuine withdrawals. Using SIT_FIN would
overstate dropout about threefold. Students coded transferred, or with no
status, are excluded from all rates. All transferred students in 2016 have a
final status at another record in the same file, so no student is lost.
Attribution is to the school where the year ended.

### Rates
All rates are proportions between 0 and 1. The denominator n is the number of
students promoted, repeated or withdrawn.

| Column | Definition |
|--------|------------|
| promotion_rate | Promoted divided by n |
| repetition_rate | Repeated divided by n |
| dropout_rate | Withdrawn divided by n |
| completion_rate | Promoted divided by n among students in the final grade of their program (8º básico for COD_ENSE 110, 4º medio for all secondary codes) |

The three rates sum to 1 by construction, so this is not an independent
validation check. The _male and _female columns use GEN_ALU 1 and 2 with only
that sex's students in both numerator and denominator. Overall rates also
include students with an undefined or non-binary sex code.

dropout_rate is computed from formal and informal withdrawals during the year.
It is not the UIS cohort based dropout rate. A student who finishes the year
but does not enroll the next year is not counted. completion_rate is the
promotion rate in the last grade of the level, which is a proxy for the schema
definition and not an age cohort completion rate. It is NA for schools with no
students in a final grade (roughly 28 percent of school years, mostly rural
schools that stop at 6º básico).

### Validation results
- 108,387 school-year rows for 4,562 schools (2002 to 2025), no rate outside 0 to 1.
- The count of students with a final status divided by personnel enrollment has a median of 1.002 (5th percentile 0.949, 95th percentile 1.118). Late enrollment after 30 April and students dropped as transfers offset each other.
- Median school-level rates for 2016 are about 96.2 percent promotion, 2.7 percent repetition and 0.4 percent dropout. Pooled rates across all students in 2016 are lower on promotion because small rural schools with high promotion carry equal weight in the median.

### Known issues
- 2020 and 2021 show median dropout of zero and (in 2020) median repetition of zero. This is consistent with relaxed promotion rules and students remaining formally enrolled during the pandemic. The values are kept and should be interpreted with care. [FILL - confirm the policy details before citing.]
- Source system changes in 2009 (RECH before, SIGE after). No clear break is visible in medians, but the change should be noted.
- 2002 coverage is lower than in later years. [DECISION PENDING - keep or drop 2002.]
- From 2018 the median completion rate is 1.000, so completion has limited discriminating power in recent years.
- Rates for very small schools rest on few students. No minimum denominator is applied. [DECISION PENDING.]
- Sex-specific rates are NA for about 1.5 percent of school-years because the school has no students of that sex.

---

## GENERAL NOTES

### Harmonization decisions
- Sorted by RBD ascending before assigning geo_id so IDs are reproducible across reruns. IDs are assigned before rows without coordinates are dropped, so they stay stable if coordinates are recovered later.
- source_id is RBD verbatim. It is a persistent national identifier.
- school_type is set to Municipal or Servicio Local de Educación Pública from COD_DEPE2.
- school_name_romanized is NA because names are already in Latin script.
- status is open for all retained schools (see the geo section).
- One definition applies to every year. Where a year's file lacks a needed column, that source's fields are blank and not approximated.
- Source files are read as Latin-1 with normalised column names. Only numeric code columns are used, so accents in text columns do not matter.
- No student or teacher identifiers are stored. The GEO Dataset holds school-level aggregates only.

### Outstanding issues
- Decide whether to keep 2002 in outcomes (lower coverage) and whether to blank or flag 2020 and 2021.
- Decide whether to apply a minimum denominator to outcome rates.
- Confirm the grade to ISCED rule against the UIS mapping.
- Special education schools with no regular program are out of scope. Confirm this is the intended treatment.
- Confirm that pre-2015 files hold operating schools only, by comparing 2014 and 2015 totals.
- Run the external reconciliation against the Resumen de Matrícula and Dotación Docente files.
- Add exact dataset page URLs, access dates and the terms of use for MINEDUC open data.
- Historical dependency is not checked. The COD_DEPE and COD_DEPE2 columns in the yearly files would allow restricting each school-year to years when the school was municipal or SLEP.
- Apply GHSL-SMOD once all countries are cleaned.
- Fill every [FILL] marker in this file from the final run output.

### Change log
2026-09-24 - Initial file drafted