---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Uruguay"
iso3: "URY"
iso2: "UY"
region: "South America"
last_updated: "2026-10-02"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true    # primary (DGEIP) only
  resources: false
  outcomes:  false

school_count_total: TBD   # fill from ury_geo.py output
school_count_public: TBD
year_range: "2023"        # PROVISIONAL, inferred from file modified date
years_available: [2023]

sector_scope: "public"
sector_notes: >
  The source is ANEP's offering file for its own centers, so every record
  is treated as public. The files carry no sector or management column
  and no private flag, so this is an assumption based on the provider and
  has not been confirmed with ANEP. Retained from DGEIP (initial and
  primary) were tipo_de_educacion values ESCUELAS COMUNES and ESCUELA
  ESPECIAL. Excluded from DGEIP were JARDIN DE INFANTES (n=231, ISCED 0),
  three ESCUELAS COMUNES whose only offered level is inicial (ISCED 0
  only), and two schools with no name. DGES (secondary) was retained in
  full. DGETP (technical, UTU) is not yet included pending a scope
  decision on vocational programs, and CFE (teacher training) is excluded
  as tertiary.

sources:
  - source_id: "anep_siganep_oferta"
    name: "Oferta educativa ANEP (SIGANEP) — DGEIP and DGES"
    provider: "Administración Nacional de Educación Pública (ANEP), Uruguay"
    url: "https://catalogodatos.gub.uy/dataset/anep-http-sig-anep-edu-uy-siganep-formatos"
    url_status: "live"
    access_date: "2026-10-02"
    data_date: "unknown (inferred 2023)"
    update_frequency: "Annual (March), per the catalog description"
    contact: "siganep@anep.edu.uy (to be confirmed)"
    format: "XLSX"
    language: "Spanish"
    notes: >
      Offering files by ANEP subsystem (DGEIP initial and primary, DGES
      secondary, DGETP technical, CFE teacher training), received in an
      archive named CENTROS_ANEP.rar. No year column. The file modified
      date is 2023-08-30, which suggests the March 2023 offering but the
      reference year has not been confirmed with ANEP. DGEIP is one row per
      school. DGES is one row per school by plan, grade, orientation and
      shift and was collapsed to one row per school (ruee_calculado).
      Coordinates are projected X and Y in UTM zone 21S (EPSG:32721). The
      CRS is inferred from coordinate ranges and from Montevideo points
      landing in Montevideo, since the xlsx files carry no CRS metadata.

  - source_id: "geoboundaries_ury"
    name: "geoBoundaries — Uruguay"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-10"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "GeoJSON"
    language: "English"
    notes: >
      Used to assign adm1 to adm3 by spatial join and as the only
      coordinate sanity check (schools outside ADM1 are dropped). ADM
      levels available for Uruguay to be recorded after running the join.

---

## GEO

**Status:** Available
**Source(s):** anep_siganep_oferta, geoboundaries_ury
**Year of geo data:** Unknown. Inferred 2023 from file modified date (2023-08-30), unconfirmed.

### Public school subsetting

**DGEIP (initial and primary).**

| tipo_de_educacion | Raw rows | Treatment |
|-------------------|----------|-----------|
| ESCUELAS COMUNES | 1,965 | Retained (3 inicial-only schools and 2 unnamed schools dropped) |
| ESCUELA ESPECIAL | 81 | Retained, flagged in school_type |
| JARDÍN DE INFANTES | 231 | Excluded (ISCED 0) |

Three ESCUELAS COMUNES (all UNIDOCENTE rural schools with one classroom and
0 to 2 students) list only a nivel inicial level in unofrece and were
excluded under the ISCED 0 rule. Eight ESCUELAS COMUNES have no grade
information at all and zero enrollment. Six of these have names and were
retained as ISCED 1 with status unknown, and two have no school name and
were dropped because school_name is never null.

**DGES (secondary).** All 320 centers retained before the coordinate and
ADM1 checks. The source has 0 centers with more than one location and 0
with missing coordinates.

**Not included.** DGETP (technical and vocational) is pending a scope
decision. CFE is tertiary and excluded.

Final counts after the coordinate and ADM1 checks are in the table below
and should be filled from the script output.

| Subsystem | Schools after filters | Schools after ADM1 check |
|-----------|----------------------|--------------------------|
| DGEIP | TBD | TBD |
| DGES | 320 | TBD |

### Unit of observation
DGES is one row per school by plan, grade, orientation and shift in the
source. The 320 school keys (ruee_calculado) each map to exactly one X/Y
pair and one rule_calculado and depend value, so collapsing to one row per
school loses no location information. depend and dependid are school-level
codes and not parent-child links, so no annexes were identified. DGEIP
ruee is unique after filtering and is used as source_id.

### Coordinate construction
Coordinates come from the X and Y columns of the source, converted from
UTM zone 21S (EPSG:32721) to WGS84 with pyproj. coordinate_source is
official_emis for all schools. coordinate_precision is set to exact as a
placeholder because ANEP does not document how the points were captured,
and this should be confirmed with ANEP and changed to approximate if the
points turn out to be locality or building-block level.

Shared buildings are expected. DGEIP has a comparte column and some
schools legitimately share identical coordinates.

### Administrative hierarchy
adm0 is hardcoded as Uruguay. adm1 to adm3 are assigned by spatial join to
geoBoundaries, never from the source department and locality columns.
Schools falling outside every ADM1 polygon are dropped, which is the
standing coordinate check.

| Level | Meaning for Uruguay | Coverage |
|-------|---------------------|----------|
| adm1 | Department (19) | TBD |
| adm2 | TBD | TBD |
| adm3 | TBD | TBD |

### ISCED level
DGEIP schools are coded 1 for all schools, since no grade above 6 appears
in the file. This means rural primary schools that also teach ciclo básico
(grades 7 to 9) are coded as ISCED 1 only and their scope is understated
until the separate 7_8_9 offering file is obtained and matched.

DGES levels come from the oferta_ciclobasico and oferta_bachillergral
flags, which never conflict with the grade ranges in the file. Ciclo
básico (grades 1 to 3 and 7 to 9, two numberings coexist across plans) is
ISCED 2, and bachillerato (grades 4 to 6) is ISCED 3. Schools with both
are coded 2|3.

| isced_level | Count |
|-------------|-------|
| 1 | TBD |
| 2 | TBD |
| 3 | TBD |
| 2\|3 | TBD |

### Urban/rural classification
urban_rural is mapped from the DGEIP area column (URBANA to urban, RURAL to
rural). DGES has no urban or rural column, so urban_rural is NA for all
secondary schools. Mapped values should be checked against
df["area"].value_counts() for any category other than URBANA and RURAL,
which would otherwise become NA. ghsl_smod_code and ghsl_urban_rural are
filled later by add_ghsl.py.

### Known issues
- The reference year is not in the source and is inferred.
- The CRS is inferred and not documented in the files.
- coordinate_precision is a placeholder.
- DGES school_type is NA because the source has no type column.
- status is unknown for all schools because the source has no operational
  status field. Zero-enrollment schools in DGEIP may be inactive.
- Eight DGEIP schools have no grade information and zero enrollment, and
  six were retained with ISCED 1 by default.

---

## PERSONNEL

**Status:** Partially available (primary only, enrollment and classrooms)
**Source(s):** anep_siganep_oferta
**Years available:** 2023 (provisional)

DGEIP provides matricula (enrollment_total) and cant_aulas
(classrooms_total). cant_aulas equal to 0 where matricula is above 0 was
set to NA (48 schools), because students with no classrooms indicates the
value was not recorded. Zero enrollment is retained as a real zero.

matricula appears to include nivel inicial (ISCED 0) children in some
primary schools, indicated by pnofrece2 values such as 3 AÑOS and 4 AÑOS.
The two cannot be separated in the source, so enrollment_total for those
schools overstates ISCED 1 enrollment.

DGES matricula and cant_aulas are entirely empty (0% non-null), so no
secondary school has personnel rows.

| Field | Status |
|-------|--------|
| enrollment_male | NA, source does not disaggregate by sex |
| enrollment_female | NA, source does not disaggregate by sex |
| teachers_total | NA, total_docentes is entirely empty in DGEIP |
| teachers_male | NA, not present |
| teachers_female | NA, not present |
| teachers_qualified | NA, not collected |
| pupil_teacher_ratio | NA, cannot compute without teachers_total |

The alumnos_por_docente column in DGEIP was not used. Its values (about 1
to 3) are not plausible pupil-teacher ratios for schools with hundreds of
students, and the schema computes the ratio from enrollment_total and
teachers_total.

---

## RESOURCES

**Status:** Not available
No school-level infrastructure data was found in the sources used. The
ANEP Monitores Educativo portal publishes school-level indicators, but a
bulk download was not identified and access has not been secured.

---

## OUTCOMES

**Status:** Not available
DGEIP has no repetition or dropout columns. DGES contains repeticion and
desercion columns, but they appeared empty in the sample inspected and
their null rates still need to be confirmed. If they prove empty, no
outcomes table will be produced for Uruguay.

---

## GENERAL NOTES

### Harmonization decisions
- source_id is ruee (DGEIP) and ruee_calculado (DGES), stored as strings
  without reformatting. The two use different prefixes (11 and 12), so
  IDs should not collide across subsystems, which the script reports.
- geo_id is assigned after all cleaning, sorted alphabetically by school
  name, with source_id as a tiebreaker.
- school_name_romanized is NA because names are in Latin script.
- school_type retains the DGEIP tipo_de_educacion value verbatim and is NA
  for DGES.
- isced_level uses pipe-delimited values (2|3), consistent with other
  country scripts. This differs from the allowed values listed in
  schema.md (123, 12) and is on the cleanup list.
- Admin names come only from geoBoundaries, not from the source department
  and locality columns.

### Outstanding issues
- Confirm the reference year with ANEP (siganep@anep.edu.uy).
- Confirm the CRS and how the coordinates were captured, then update
  coordinate_precision.
- Decide the scope of DGETP (technical and vocational programs) and add a
  loader if any centers qualify as ISCED 2 or 3.
- Obtain the 7_8_9 offering file and match it to DGEIP so rural primary
  schools with ciclo básico can be coded 1|2.
- Confirm whether the Monitores Educativos can be obtained in bulk for
  resources and outcomes, and whether they share IDs with ruee.
- Record the exact download URL for the archive.
- Fill in all TBD counts after running ury_geo.py and ury_personnel.py.

### Change log
2026-10-02 — Initial draft