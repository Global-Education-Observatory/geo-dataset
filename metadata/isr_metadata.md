---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Israel"
iso3: "ISR"
iso2: "IL"
region: "Western Asia"
last_updated: "2026-06-09"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: false
  resources: false
  outcomes:  false

school_count_total: 3085
school_count_public: 3085
year_range: "2011–2015"
years_available: [2011, 2012, 2013, 2014, 2015]

sector_scope: "public"
sector_notes: >
  Source dataset contains ~28,500 unique institutions across all types and
  supervision tracks. Filtered to סוג מסגרת אירגונית = 'בית ספר' (schools),
  פיקוח NOT חרדי (state and state-religious supervision only), and
  סוג חינוך מוסד = 'רגיל' (regular education). After panel deduplication
  (most recent year per school), 3,085 schools are retained.
  
  Israel operates four supervision tracks (פיקוח):
    מ"מ (ממלכתי — state secular): 2,328 schools
    חמ"ד (ממלכתי דתי — state religious): 757 schools
    חרדי (ultra-Orthodox): excluded
  
  Ultra-Orthodox schools are excluded because, despite receiving some
  government funding, they operate under independent religious supervision,
  follow a non-state curriculum, and are not subject to standard MoE
  oversight. This is structurally different from the MPO subsidized
  schools retained in BGD, where government salary funding is channelled
  through a national EMIS with full registration and oversight.
  
  Special education institutions (סוג חינוך מוסד = 'מיוחד') are excluded
  for cross-country consistency. Kindergartens (גן ילדים), colleges,
  yeshivas, seminaries, ulpanot, and other non-school institution types
  are excluded by the סוג מסגרת אירגונית filter.

sources:
  - source_id: "isr_moe_mosdot"
    name: "Institutional Registry — Israel Ministry of Education"
    provider: "Israel Ministry of Education (משרד החינוך)"
    url: "https://data.gov.il/he/datasets/ministry_of_education/mosdot/5548fd63-5868-4053-ad81-98caddc5e232"
    url_status: "live"
    access_date: "2026-06"
    data_date: "2011–2015"
    update_frequency: "Annual"
    format: "XLSX"
    language: "Hebrew"
    notes: >
      Panel dataset covering academic years 2011–2015. Contains one row per
      school per year with institutional attributes including school code
      (סמל מוסד), name, supervision track (פיקוח), sector (מגזר),
      institution type (סוג מסגרת אירגונית), education type (regular/special),
      grade range (משכבה / עד שכבה), and source geographic columns
      (district, local authority, locality). No coordinates in this file.

  - source_id: "isr_moe_coordinates"
    name: "School Coordinates — Israel Ministry of Education"
    provider: "Israel Ministry of Education (משרד החינוך)"
    url: "https://data.gov.il/he/datasets/ministry_of_education/coordinates"
    url_status: "live"
    access_date: "2026-06"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "CSV"
    language: "Hebrew/English"
    notes: >
      28,312 school-level coordinate records. Columns include school code
      (SEMEL_MOSAD), school name (SHEM_MOSAD), ITM coordinates
      (Israeli Transverse Mercator, EPSG:2039), WGS84 decimal degree
      coordinates (mislabelled as UTM_X/UTM_Y), and a precision flag
      (RAMAT_DIYUK_MIKUM). The WGS84 columns are used for latitude/longitude.
      The ITM columns are not used.

---

## GEO

**Status:** Available
**Source(s):** isr_moe_mosdot, isr_moe_coordinates
**Year of geo data:** 2011–2015 (panel; most recent year per school used)

### Public school subsetting
The source registry contains ~28,500 unique institutions across all types.
Three filters are applied sequentially:

1. `סוג מסגרת אירגונית == 'בית ספר'`: retains schools only, excluding
   kindergartens (גן ילדים, n=~15,500), community centres (מתנ"ס),
   yeshivas, seminaries, colleges, universities, ulpanot, and other
   non-school frameworks.

2. `פיקוח NOT חרדי`: retains state (מ"מ) and state-religious (חמ"ד)
   supervision tracks only. Ultra-Orthodox (חרדי) schools excluded — see
   sector_notes above.

3. `סוג חינוך מוסד == 'רגיל'`: retains regular education only, excluding
   special education institutions.

After filtering: 14,500 rows across 3,085 unique schools.

### Panel deduplication
The source is a panel (2011–2015). One row per school is retained using the
most recent available year. Year distribution of retained rows:

| Year | Schools |
|------|---------|
| 2015 | 3,003 |
| 2014 | 16 |
| 2013 | 9 |
| 2012 | 34 |
| 2011 | 23 |

The 82 schools with a retained year earlier than 2015 were not present in
the 2015 data — likely schools that closed or were reclassified between
their last observed year and 2015.

### ISCED level mapping
ISCED level assigned from grade range columns (משכבה = from grade,
עד שכבה = to grade) using the Israeli school structure:

| Israeli grades | Level | ISCED |
|----------------|-------|-------|
| 1–6 | Primary (יסודי) | 1 |
| 7–9 | Middle school (חטיבת ביניים) | 2 |
| 10–12 | High school (תיכון) | 3 |

Where from_grade = 0 and to_grade >= 1, from_grade is treated as 1
(some schools record a pre-primary intake year as grade 0 but are
functionally primary schools). Pipe-delimited values assigned for schools
spanning multiple levels.

| isced_level | Count |
|-------------|-------|
| 1 | 1,490 |
| 2\|3 | 874 |
| 1\|2 | 376 |
| 2 | 181 |
| 3 | 142 |
| 1\|2\|3 | 10 |
| NA | 12 |

The 12 schools with NA isced_level have grade ranges of 13–14 only
(post-secondary edge cases that survived the בית ספר filter). These are a
known schema violation; they are retained in the file but flagged here.

### Administrative hierarchy
GeoBoundaries does not provide boundary data for Israel — all ADM levels
(1–3) return HTTP 403. adm1, adm2, and adm3 are therefore set to NA for
all schools. This is a known GeoBoundaries coverage gap, likely related to
contested boundary classifications for Israeli-administered territories.

Source EMIS geographic columns are retained in a supplementary file
(`isr_geo_supp_geography.csv`) alongside the canonical output:

| Source column | Translation | Approximate equivalent |
|---------------|-------------|------------------------|
| מחוז גאוגרפי | Geographic district | adm1 (6 districts + יו"ש) |
| שם רשות | Local authority name | adm2 (252 unique values) |
| שם ישוב | Locality name | adm3 (500 unique values) |

These columns are NOT used for adm1/adm2/adm3 in the canonical file, per
project rule that all adm fields are assigned via GeoBoundaries spatial join.

**Note on יו"ש (יהודה ושומרון):** 160 schools appear under the district
label יו"ש (Judea and Samaria / West Bank). These are Israeli-administered
schools in the West Bank and are included in the MoE EMIS. They are
retained in the dataset with no special flag, consistent with the approach
of using the source country's own administrative data without political
boundary modification. Researchers should be aware of this when using
adm-level aggregations from the supplementary geography file.

### Coordinate construction
Coordinates taken directly from the MoE coordinate file (isr_moe_coordinates).
The source columns UTM_X / UTM_Y contain WGS84 decimal degrees despite the
column naming. ITM columns (Israeli grid) are not used.

`coordinate_source = 'official_emis'` for all schools.

`coordinate_precision` mapped from source RAMAT_DIYUK_MIKUM field:

| RAMAT_DIYUK_MIKUM | coordinate_precision | Count |
|--------------------|---------------------|-------|
| גבוהה מאוד (very high) | exact | ~1,900 |
| גבוהה (high) | exact | ~914 |
| בינונית (medium) | approximate | ~50 |
| נמוכה (low) | approximate | 0 in matched set |
| No match in coordinate file | unknown | 221 |

| coordinate_precision | Count |
|---------------------|-------|
| exact | 2,814 |
| approximate | 50 |
| unknown (no coordinate) | 221 |

All 2,864 geocoded schools passed a bounding box sanity check
(lat 29.0–34.0, lon 33.5–36.5). No out-of-bounds coordinates found.

### Known issues
- adm1/adm2/adm3 are NA for all schools — GeoBoundaries not available for ISR.
  Source EMIS geography retained in supplementary file.
- 221 schools (7.2%) have no coordinate match in the coordinate file.
- 12 schools have NA isced_level (grade range 13–14 only; post-secondary).
- school_name_romanized is NA for all schools — bulk romanization of Hebrew
  school names is pending. The ISO 843 / Academy of the Hebrew Language
  romanization standard would be appropriate.
- school_type values (ממ / חמד) are the פיקוח field with quotation marks
  stripped. Full Hebrew labels are ממלכתי and ממלכתי דתי respectively.
- 160 schools are in the West Bank (adm1 source value יו"ש) and are
  included without modification.
- Data reflects 2011–2015 only. Schools opened or closed after 2015 are
  not represented.

---

## PERSONNEL

**Status:** Not available
The source file contains a total students column (סהכ תלמידים במוסד) but it
has substantial missingness in the panel and has not been processed into a
personnel table. A dedicated personnel table could be built from this column
if cleaned; flagged for future work.

---

## RESOURCES

**Status:** Not available
School-level infrastructure data not available in current sources.

---

## OUTCOMES

**Status:** Not available
School-level outcomes data not available in current sources. The MoE
publishes school-level matriculation (בגרות) statistics at
`education.gov.il/netuney_bchinot` for secondary schools, but this portal
was not accessible during data collection. Flagged for future work.

---

## GENERAL NOTES

### Harmonization decisions
- `sector = 'public'` for all rows; חרדי schools excluded per sector_notes.
- `status = 'open'` for all schools — no closure data in source.
- `school_name_romanized = NA` — names in Hebrew script; romanization pending.
- `urban_rural = NA` — not in source; GHSL-SMOD classification pending.
- `geo_id` assigned as ISR_{zero-padded integer} sorted alphabetically by
  school name (שם מוסד) to ensure reproducible ID assignment across re-runs.
- Panel deduplication uses most-recent-year row per school.

### Change log
2026-06-09 — Initial file created