---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Israel"
iso3: "ISR"
iso2: "IL"
region: "Western Asia"
last_updated: "2026-06-10"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: false
  resources: false
  outcomes:  false

school_count_total: 2864
school_count_public: 2864
year_range: "2011–2015"
years_available: [2011, 2012, 2013, 2014, 2015]

sector_scope: "public"
sector_notes: >
  Source dataset contains ~28,500 unique institutions across all types and
  supervision tracks. Filtered to סוג מסגרת אירגונית = 'בית ספר' (schools),
  פיקוח NOT חרדי (state and state-religious supervision only), and
  סוג חינוך מוסד = 'רגיל' (regular education). After panel deduplication
  (most recent year per school) and exclusion of schools with no coordinates,
  2,864 schools are retained.

  Israel operates four supervision tracks (פיקוח):
    מ"מ (ממלכתי — state secular): 2,167 schools
    חמ"ד (ממלכתי דתי — state religious): 697 schools
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

### Coordinate exclusion
221 schools (7.2% of the 3,085 post-filter schools) had no match in the
MoE coordinate file and are excluded from the final geo table entirely,
per the project-wide rule that schools with no coordinate are not retained.
Final school count: 2,864.

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
| 1 | 1,434 |
| 2\|3 | 804 |
| 1\|2 | 343 |
| 2 | 144 |
| 3 | 120 |
| 1\|2\|3 | 10 |
| NA | 9 |

The 9 schools with NA isced_level have grade ranges of 13–14 only
(post-secondary edge cases that survived the בית ספר filter). These are a
known schema violation; they are retained in the file but flagged here.

### Administrative hierarchy
adm1 and adm2 were assigned via spatial join to GeoBoundaries ADM1 and ADM2
boundary polygons for ISR. GeoBoundaries returned data intermittently during
processing (all levels returned HTTP 403 on initial checks; 6 ADM1 features
and 15 ADM2 features were available on a subsequent run). adm3 is not
available from GeoBoundaries for ISR.

| Level | Features | Matched | Unmatched (NA) |
|-------|----------|---------|----------------|
| ADM1 | 6 | 2,471 | 393 |
| ADM2 | 15 | 2,706 | 158 |
| ADM3 | not available | — | — |

adm1 distribution (matched schools):

| adm1 | Count |
|------|-------|
| Central District | 655 |
| Northern District | 598 |
| Southern District | 437 |
| Haifa | 329 |
| Tel Aviv | 303 |
| Jerusalem District | 149 |

**West Bank schools and unmatched adm values:** 151 schools appear under
the source EMIS district label יו"ש (יהודה ושומרון — Judea and Samaria).
These are Israeli-administered schools in the West Bank, including Israeli
settlements and schools in Area C. The MoE EMIS includes them under its
jurisdiction, and their coordinates (confirmed by visual inspection) fall
in the West Bank — east of Israel's internationally recognized boundary and
outside the GeoBoundaries ADM polygons for ISR.

As a result, these schools receive adm1 = NA and adm2 = NA from the
GeoBoundaries spatial join, as the join correctly finds no containing
polygon within Israel's recognized boundary. The remaining unmatched
schools (393 − 151 = ~242 adm1 NA; 158 − ~151 = ~7 adm2 NA) are likely
near-boundary misses.

These 151 West Bank schools are retained in the dataset without modification,
consistent with the project approach of using the source country's own EMIS
without political boundary adjustment. Researchers conducting spatial analysis
should be aware that these schools will not be captured by any standard
country polygon for Israel and their adm fields will be NA.

Source EMIS geographic columns are retained in a supplementary file
(`isr_geo_supp_geography.csv`) for reference:

| Source column | Translation | Approximate equivalent |
|---------------|-------------|------------------------|
| מחוז גאוגרפי | Geographic district | adm1 (6 districts + יו"ש) |
| שם רשות | Local authority name | adm2 |
| שם ישוב | Locality name | adm3 |

### Coordinate construction
Coordinates taken directly from the MoE coordinate file (isr_moe_coordinates).
The source columns UTM_X / UTM_Y contain WGS84 decimal degrees despite the
column naming. ITM columns (Israeli grid, EPSG:2039) are not used.

`coordinate_source = 'official_emis'` for all schools.

`coordinate_precision` mapped from source RAMAT_DIYUK_MIKUM field:

| RAMAT_DIYUK_MIKUM | coordinate_precision | Count |
|--------------------|---------------------|-------|
| גבוהה מאוד (very high) | exact | ~1,900 |
| גבוהה (high) | exact | ~914 |
| בינונית (medium) | approximate | 50 |
| נמוכה (low) | approximate | 0 in matched set |

| coordinate_precision | Count |
|---------------------|-------|
| exact | 2,814 |
| approximate | 50 |

All 2,864 schools passed a bounding box sanity check
(lat 29.0–34.0, lon 33.5–36.5). No out-of-bounds coordinates found.

### Known issues
- adm1 = NA for 393 schools, adm2 = NA for 158 schools — primarily West Bank
  schools (n≈151) outside GeoBoundaries ISR polygons, plus near-boundary misses.
  adm3 not available from GeoBoundaries for ISR. Source EMIS geography retained
  in supplementary file.
- 221 schools excluded due to no coordinate match (7.2% of post-filter schools).
- 9 schools have NA isced_level (grade range 13–14 only; post-secondary edge cases).
- school_name_romanized is NA for all schools — bulk romanization of Hebrew
  school names is pending. The Academy of the Hebrew Language romanization
  standard would be appropriate.
- school_type values (ממ / חמד) are the פיקוח field with quotation marks
  stripped. Full Hebrew labels are ממלכתי and ממלכתי דתי respectively.
- Data reflects 2011–2015 only. Schools opened or closed after 2015 are
  not represented.
- GeoBoundaries returned HTTP 403 for all ISR ADM levels on initial checks
  during processing; data was available on a subsequent run. GeoBoundaries
  coverage for ISR should be verified before any re-run of this script.

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
- Schools with no coordinate match excluded entirely (n=221), per project-wide
  rule that schools with no coordinate are not retained in the geo table.

### Change log
2026-06-09 — Initial file created
2026-06-10 — Updated: school count corrected to 2,864 after coordinate exclusion;
             adm1/adm2 populated via GeoBoundaries (intermittent availability noted);
             West Bank school handling documented; ISCED and coordinate counts updated