---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Costa Rica"
iso3: "CRI"
iso2: "CR"
region: "Central America"
last_updated: "2026-05-19"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: false
  outcomes:  true

school_count_total: ~4800
school_count_public: ~4800
year_range: "2014-2025"
years_available: [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

sector_scope: "public"
sector_notes: >
  Source enrollment files use SECTOR codes: 1 = Público, 2 = Privado,
  3 = Subvencionado. The 2023-2025 edited nómina files use DEPENDENCIA
  codes: PUB, PRI, SUB. Retained SECTOR IN {1, 3} / DEPENDENCIA IN
  {PUB, SUB}. SECTOR=2 / DEPENDENCIA=PRI (private schools) excluded.
  Subvencionadas (SECTOR=3 / SUB) are church-managed but receive full
  government salary funding and appear in the MEP EMIS as managed
  institutions. Treated as public per schema definition and Costa Rican
  convention. For colegios, nocturno programs (RAMA IN {12, 22}) excluded
  — these serve a distinct adult and repeater population whose enrollment
  is not comparable to daytime schools. Artístico (RAMA=31, n=2 schools)
  also excluded — specialised admissions, not representative of the
  general public school system.

sources:
  - source_id: "cri_mep_enroll_l1_2014_2022"
    name: "Matrícula Inicial Escuelas Diurnas 2014-2022, por Año Cursado y Sexo"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2022"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Initial enrollment (matrícula inicial, reference date March) for
      daytime primary schools (I y II Ciclos, grades 1-6), 2014-2022.
      Contains total and sex-disaggregated enrollment by grade. Includes
      SECTOR (1=Público, 2=Privado, 3=Subvencionado), ZONA (1=Urbana,
      2=Rural), RAMA not present (file is diurnas only by construction).
      Identifier is CODIGO (Código Presupuestario).

  - source_id: "cri_mep_enroll_l2_2014_2022"
    name: "Matrícula Inicial Colegios 2014-2022, por Año Cursado y Sexo"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2022"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Initial enrollment (matrícula inicial) for secondary schools (III
      Ciclo + Educación Diversificada, grades 7-12), 2014-2022. Contains
      total and sex-disaggregated enrollment by grade. Includes SECTOR,
      ZONA, and RAMA (11=Académica Diurna, 12=Académica Nocturna,
      21=Técnica Diurna, 22=Técnica Nocturna). Identifier is CODIGO
      (Código Presupuestario).

  - source_id: "cri_mep_nomina_2023"
    name: "Nómina de Centros Educativos 2023 (edited)"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2023"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Matrícula inicial for 2023, structured as a school registry rather
      than the grade-disaggregated format of the 2014-2022 series. Contains
      a single enrollment total per school (I Y II CICLOS for primary, DE
      7° A 12° AÑO for secondary). No sex or grade disaggregation available.
      Pre-cleaned (*_edited version) to normalise column names and remove
      formatting rows. DEPENDENCIA codes: PUB, PRI, SUB. ZONA codes: URB,
      RUR. Secondary sheet includes RAMA-HORARIO as text.

  - source_id: "cri_mep_nomina_2024"
    name: "Nómina de Centros Educativos 2024 (edited)"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2024"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Same structure as cri_mep_nomina_2023. Single enrollment total per
      school, no sex or grade disaggregation. Pre-cleaned (*_edited version).

  - source_id: "cri_mep_nomina_2025"
    name: "Nómina de Centros Educativos 2025 (edited)"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2025"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Same structure as cri_mep_nomina_2023. Single enrollment total per
      school, no sex or grade disaggregation. Pre-cleaned (*_edited version).

  - source_id: "cri_saber_coords_2024"
    name: "Centros Educativos Públicos SABER — Coordenadas Junio 2024"
    provider: "Ministerio de Educación Pública de Costa Rica"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2024-06"
    update_frequency: "Unknown"
    format: "Shapefile"
    language: "Spanish"
    notes: >
      GPS coordinates for public schools from the MEP SABER asset registry
      system (Sistema de Administración de Bienes Educativos y Recursos),
      June 2024 snapshot. Contains CODSABER (internal asset ID), CODPRES
      (Código Presupuestario, join key to enrollment files), school name,
      and point geometry in WGS84. Some schools have multiple entries under
      one CODPRES (satellite locations/annexes); deduplicated by retaining
      the entry with CODSABER ending in '-00' (main campus), falling back
      to first row.

  - source_id: "cri_poblados_centroids"
    name: "Poblados de Costa Rica — Shapefile"
    provider: "Instituto Geográfico Nacional de Costa Rica"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "Unknown"
    update_frequency: "Unknown"
    format: "Shapefile"
    language: "Spanish"
    notes: >
      Point shapefile of Costa Rican populated places (poblados). Used as
      a fallback coordinate source for schools present in the enrollment
      files but absent from the SABER coordinates file. Matched to schools
      on PROVINCIA + CANTON + POBLADO. Reprojected from CRTM05 (EPSG:5367)
      to WGS84 before extracting lat/lon.

  - source_id: "cri_mep_outcomes_l2_despues"
    name: "Matrícula Final y Rendimiento Definitivo, III Ciclo y Educación Diversificada, 2014-2021 (después de convocatorias)"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2021"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      End-of-year enrollment and outcomes for secondary schools after the
      resit examination period (convocatorias). Contains MFT/MFH/MFM
      (matrícula final total/male/female) and APT/APH/APM (aprobados),
      RET/REH/REM (reprobados) by grade. Aplazados category does not appear
      because all students have been definitively resolved after resits.
      Used in preference to the antes de convocatorias file because it
      reflects true end-of-year status. Coverage is 2014-2021 only; 2022
      outcomes for secondary are therefore NA.

  - source_id: "cri_mep_outcomes_l1_despues"
    name: "Matrícula Final y Rendimiento Definitivo, I y II Ciclos, (después de convocatorias)"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2022"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      End-of-year enrollment and outcomes for primary schools after resits.
      Same structure as secondary file. Contains MFT/MFH/MFM and APT/APH/APM,
      RET/REH/REM by grade.

  - source_id: "cri_mep_exclusion_l1"
    name: "Exclusión Intra-Anual, I y II Ciclos"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2022"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Mid-year dropout (exclusión intra-anual) for primary schools. Computed
      by the MEP as the difference between matrícula inicial and matrícula
      final. Contains EXC INTRAT/H/M (total/male/female) and grade-level
      breakdowns (EXC INTRAT1-6, EXC INTRAH1-6, EXC INTRAM1-6). Also
      contains school self-reported exclusión (EXCT/H/M) which was not
      used — see harmonization decisions.

  - source_id: "cri_mep_exclusion_l2"
    name: "Exclusión Intra-Anual, III Ciclo y Educación Diversificada"
    provider: "Ministerio de Educación Pública de Costa Rica, Departamento de Análisis Estadístico"
    url: "https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2014-2022"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Same structure as primary exclusión file but for secondary schools
      (grades 7-12). Grade-level columns cover grades 7-12
      (EXC INTRAT1-6 = grades 7-12 respectively).

---

## GEO

**Status:** Available
**Source(s):** cri_saber_coords_2024, cri_mep_enroll_l1_2014_2022, cri_mep_enroll_l2_2014_2022, cri_mep_nomina_2023, cri_mep_nomina_2024, cri_mep_nomina_2025, cri_poblados_centroids
**Year of geo data:** School universe drawn from 2014-2025 enrollment files; coordinates from SABER June 2024 snapshot.

### Public school subsetting
The school universe was constructed by taking the union of all unique CODIGO values across the 2014-2022 enrollment files (primary and secondary), filtered to SECTOR ∈ {1, 3}, with CODIGO = 0 or null excluded. This was then extended with new CODIGOs appearing in the 2023-2025 nómina files (DEPENDENCIA ∈ {PUB, SUB}) to capture schools that opened after 2022. For colegios, RAMA ∈ {11, 21} (daytime academic and technical) retained; RAMA ∈ {12, 22} (nocturno) and RAMA = 31 (artístico) excluded.

### Coordinate assignment
Coordinates assigned through a three-tier process:

**Tier 1 — SABER GPS file (n ≈ 4,550 schools):**
Joined on CODPRES (= CODIGO Presupuestario). Where a CODPRES had multiple entries (satellite locations/annexes), the entry with CODSABER ending in '-00' was retained as the main campus, falling back to the first row.
- `coordinate_source = 'official_emis'`
- `coordinate_precision = 'exact'`

**Tier 2 — Poblados centroid fallback (n = 42 schools):**
Schools present in the enrollment universe but absent from the SABER file were matched to the poblados shapefile on PROVINCIA + CANTON + POBLADO. Centroids reprojected from CRTM05 to WGS84 before extracting lat/lon. Of the 42 matched schools, approximately 23 are ZONA=2 (rural) and 18 are ZONA=1 (urban). Urban centroid matches carry higher positional error as the centroid may be distant from the actual school building.
- `coordinate_source = 'admin_centroid'`
- `coordinate_precision = 'approximate'`

**Tier 3 — No match (n ≈ 130 schools):**
Schools with no SABER match and no poblado centroid match were dropped from the geo table per schema rule. These schools are excluded from all four tables.

### Administrative hierarchy
`adm0` = "Costa Rica" (hardcoded).

`adm1`, `adm2`, `adm3` assigned via spatial join to GeoBoundaries ADM1-ADM3 boundaries for CRI using the shared pipeline utility (geo_boundaries.py).

### ISCED level
ISCED level assigned from the source file structure rather than a column in the source data:
- Schools from the escuelas (I y II Ciclos) file → `1`
- Schools from the colegios (III Ciclo + Educación Diversificada) file → `2|3`

No within-secondary disaggregation is available. Grades 7-9 (III Ciclo) correspond to ISCED 2 and grades 10-12 (Educación Diversificada) to ISCED 3, but both are administered under a single CODIGO with no split in the source data.

### Urban/rural classification
Mapped from source ZONA column: 1 → `urban`, 2 → `rural`. No peri_urban classification exists in the MEP source. GHSL-SMOD classification applied separately via add_ghsl.py for cross-country standardised urban/rural.

### school_type
Set to NA — the MEP source files do not include a national school type classification column at the school level that is distinct from ISCED level and RAMA.

### status
Set to `unknown` for all schools — no operational status or closure field is available in any MEP source file.

### geo_id assignment
Sorted by source_id (CODIGO Presupuestario) ascending before assigning geo_id to ensure reproducible ID assignment across re-runs.

### Known issues
- SABER coordinates reflect a June 2024 snapshot. Schools that opened or closed between the enrollment period (2014-2025) and June 2024 may have coordinates that do not reflect their operational period.
- ~130 schools in the enrollment universe have no coordinate and are excluded from all four tables.
- 18 of the 42 poblado centroid matches are in urban zones where centroid positional error may be substantial.
- CODPRES = 0 rows appear in source files and are excluded — these are data entry errors or placeholder rows with no valid school identifier.

---

## PERSONNEL

**Status:** Available
**Source(s):** cri_mep_enroll_l1_2014_2022, cri_mep_enroll_l2_2014_2022, cri_mep_nomina_2023, cri_mep_nomina_2024, cri_mep_nomina_2025
**Years available:** 2014-2025

### Enrollment
`enrollment_total`, `enrollment_male`, `enrollment_female` sourced from matrícula inicial (reference date: March of each year). This is the UIS ENR headcount definition — students enrolled at the start of the year, not annual admissions or end-of-year counts.

For 2014-2022, enrollment is available with full sex and grade disaggregation:
- Primary source columns: T (total), H (hombres), M (mujeres)
- Secondary source columns: TOTAL, HOMBRES, MUJERES

For 2023-2025 (nómina files), only a single enrollment total is available per school — no sex or grade disaggregation. `enrollment_male` and `enrollment_female` are NA for these years.

### Teacher data
Not available in any MEP source file accessed. `teachers_total`, `teachers_male`, `teachers_female`, `teachers_qualified`, `classrooms_total` are all NA for all years. `pupil_teacher_ratio` is therefore also NA (computed field; NA if either input is NA).

### Scope restriction
Personnel rows restricted to schools present in cri_geo.csv. Schools without coordinates (dropped from geo) are excluded from personnel per schema rule.

### Known issues
- Sex-disaggregated enrollment is unavailable for 2023-2025, creating an asymmetry in the panel.
- No teacher data is publicly available from the MEP at the school level.

---

## RESOURCES

**Status:** Not available
School-level infrastructure data is not publicly available from the MEP at the school level.

---

## OUTCOMES

**Status:** Available
**Source(s):** cri_mep_outcomes_l1_despues, cri_mep_outcomes_l2_despues, cri_mep_exclusion_l1, cri_mep_exclusion_l2
**Years available:** 2014-2021 (secondary); 2014-2022 (primary)

### Methodology
All outcome rates use the within-year flow method rather than the UIS reconstructed cohort method. Within-year flow rates are computed from single-year EMIS administrative data and are standard practice in school-level EMIS analysis (Cameron, EPDC, 2005). Under this method, promotion_rate + repetition_rate + dropout_rate do not necessarily sum to 1.0 because dropout uses matrícula inicial as its denominator while promotion and repetition use matrícula final.

### Promotion rate
`promotion_rate` = APT / MFT (total aprobados / matrícula final total)
`promotion_rate_male` = APH / MFH
`promotion_rate_female` = APM / MFM

Sourced from the después de convocatorias file, which reflects outcomes after the resit examination period. This is preferred over the antes de convocatorias file because all aplazados have been definitively resolved — students either passed on resit (moved to aprobados) or failed definitively (moved to reprobados). The aplazados category does not appear in the después file.

### Repetition rate
`repetition_rate` = RET / MFT (total reprobados / matrícula final total)
`repetition_rate_male` = REH / MFH
`repetition_rate_female` = REM / MFM

Reprobados are students who failed and must repeat the grade. Since the después de convocatorias file is used, this represents only definitively failed students after all resit opportunities have been exhausted.

Note: in the antes de convocatorias file, aplazados (students awaiting resits) are a separate category. In the schema, aplazados would contribute to repetition_rate if the antes file were used. Since the después file is used here, this distinction does not apply.

### Dropout rate
`dropout_rate` = EXC INTRAT / enrollment_total (matrícula inicial, from personnel table)
`dropout_rate_male` = EXC INTRAH / enrollment_male
`dropout_rate_female` = EXC INTRAM / enrollment_female

Sourced from the MEP exclusión intra-anual files. The MEP defines exclusión intra-anual as the difference between matrícula inicial and matrícula final (Ministerio de Educación Pública, Departamento de Análisis Estadístico, "Porcentaje de Deserción Intra-Anual", methodology sheet). Matrícula inicial is the correct denominator per the MEP's own published formula.

**Negative value treatment:** Negative exclusión values occur when a school has net mid-year student inflow (transfers in exceed dropouts), producing MF > MI. This is a known feature of the MEP's system-derived calculation, not a data error. Negative values were handled at the grade level before aggregation:
1. Grade-level male and female exclusión columns (EXC INTRAH1-6, EXC INTRAM1-6) clipped to 0.
2. Grade-level totals recomputed from clipped male + female.
3. Annual totals (EXC INTRAT, EXC INTRAH, EXC INTRAM) recomputed from recalculated grade totals.

This approach preserves real dropout at grades where it occurred while treating net-inflow grades as contributing zero dropout rather than negative dropout.

Dropout rates exceeding 1.0 (more dropouts recorded than matrícula inicial) and rows where enrollment_total = 0 are set to NA.

**School self-reported exclusión not used:** The source files also contain school-reported exclusión (EXCT/H/M). These were not used because the Pearson correlation between school-reported and system-derived exclusión was r = 0.26 (after removing negatives), indicating the two measures diverge substantially. The system-derived intra-anual figures are more reliable as they are computed mechanically from the two enrollment counts rather than depending on school-level reporting.

### Completion rate
`completion_rate` = AP6T / MF6T (aprobados in final grade / matrícula final in final grade)
`completion_rate_male` = AP6H / MF6H
`completion_rate_female` = AP6M / MF6M

Final grade is grade 6 for primary (I y II Ciclos) and grade 12 for secondary (III Ciclo + Educación Diversificada). Rates exceeding 1.0 set to NA.

### Year coverage
Secondary outcomes (promotion, repetition, completion) cover 2014-2021 only — the después de convocatorias file does not extend to 2022. Primary outcomes cover 2014-2022. Dropout covers 2014-2022 for both levels.

### Scope restriction
Outcomes rows restricted to schools present in cri_geo.csv.

---

## GENERAL NOTES

### Source availability
All sources downloaded from the MEP Departamento de Análisis Estadístico statistics portal at `https://www.mep.go.cr/acerca-del-mep/analisis-estadistico/estadisticas-educativas#!`. All URLs live as of May 2026. Files are provided as downloadable XLSX; no API access available.

### Harmonization decisions
- CODIGO Presupuestario used as the join key across all files, consistent with the MEP's own identifier system. CODINS (Código Institucional) also appears in some files but was not used as it differs from CODPRES and does not appear in all sources.
- `school_name_romanized` set to NA — school names are already in Latin script (Spanish).
- `sector = 'public'` for all rows including subvencionadas, per schema definition and Costa Rican convention.
- `geo_id` assigned as CRI_{zero-padded integer} sorted by CODIGO Presupuestario ascending for reproducibility.
- GHSL-SMOD classification pending global raster sampling step (add_ghsl.py).
- Costa Rica academic year runs January-December (single calendar year). `year` = CURSO LECTIVO value verbatim, consistent with UIS beginning-year convention (no adjustment needed).
- Matrícula inicial used as the enrollment reference throughout (personnel and as dropout denominator), consistent with the UIS ENR definition and the MEP's own published dropout methodology.
- Después de convocatorias (after resits) used for promotion and repetition rates in preference to antes de convocatorias (before resits) to ensure outcomes reflect definitively resolved student status.

### Outstanding issues
- Teacher data not available at school level — pupil_teacher_ratio cannot be computed for any year.
- Secondary outcomes limited to 2014-2021; 2022 secondary promotion, repetition, and completion rates are NA pending availability of a después de convocatorias file for 2022.
- Sex-disaggregated enrollment unavailable for 2023-2025.
- ~130 schools in the enrollment universe lack coordinates and are excluded from all tables.
- Urban poblado centroid matches (n=18) carry higher positional uncertainty than rural matches.
- `status = 'unknown'` for all schools — no operational status field in MEP sources.

### Change log
2026-05-19 — Initial file created
