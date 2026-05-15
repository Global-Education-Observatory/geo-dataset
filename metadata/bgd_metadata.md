---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Bangladesh"
iso3: "BGD"
iso2: "BD"
region: "South Asia"
last_updated: "2026-05-15"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: true
  resources: false
  outcomes:  false

school_count_total: 7500
school_count_public: 7500
year_range: "2016"
years_available: [2016]

sector_scope: "public"
sector_notes: >
  Source dataset contains ~35,000 institutions across all management types
  and education levels. Filtered to MANAGEMENT_TYPE IN ['GOVERNMENT',
  'GOVERNMENT PRIMARY', 'LOCAL GOVERNMENT'] OR MPO_STATUS = 'YES'
  AND EDUCATION_LEVEL IN ['Dakhil', 'Alim', 'Junior Secondary',
  'TECHNICAL SCHOOL AND COLLEGE', 'H.S.C (B.M Independent)'].
  Bangladesh operates a Monthly Pay Order (MPO) system under which the
  government directly funds teacher salaries at recognised non-government
  institutions. MPO-listed schools are registered in the national EMIS,
  regulated by the Ministry of Education, and treated as public schools
  per the GEO schema provision for government-subsidised institutions.
  Excluded management types: AUTONOMOUS (n=257), OTHERS (n=480),
  Run by Christian Missionaries (n=50), and NON-GOVERNMENT schools
  without MPO status.
  Excluded education levels: Secondary, Higher Secondary (predominantly
  non-MPO non-government; removed by management-type filter),
  Degree (Pass), Degree (Honors), Masters, Kamil, Fazil (tertiary/ISCED 5+),
  POLYTECHNIC INSTITUTE, NURSHING COLLEGE, AGRICULTURE TRAINING INSTITUTE,
  INSTITUTE OF HEALTH TECHNOLOGY, SURVEY INSTITUTE, TEXTILE TECHNOLOGY
  COLLEGE, TEXTILE (Vocational Institute), TECHNICALTRAINING CENTER,
  GRAPHIC ARTS, GLASS AND CERAMICS INSTITUTE, TEXTILE INSTITUTE, BASIC
  TRADE, OTHER.

sources:
  - source_id: "bgd_banbeis_institutional"
    name: "Institutional Information — BANBEIS EMIS"
    provider: "Bangladesh Bureau of Educational Information and Statistics (BANBEIS)"
    url: "https://uat-ogd.oss.net.bd/single-data-set/LaiPQ7c"
    url_status: "live"
    access_date: "2026-05"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "XLSX"
    language: "English"
    notes: >
      National EMIS school register. Contains institutional attributes
      including EIIN (national school ID), school name, institute type,
      management type, MPO status, education level, administrative
      hierarchy (Division through Mauza with numeric codes), area status,
      and contact information. No coordinates in source.

  - source_id: "bgd_banbeis_students_age"
    name: "Number of Students by Age and Class — BANBEIS EMIS"
    provider: "Bangladesh Bureau of Educational Information and Statistics (BANBEIS)"
    url: "https://uat-ogd.oss.net.bd/single-data-set/G5nBior"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2016"
    update_frequency: "unknown"
    format: "XLS"
    language: "English"
    notes: >
      Student counts disaggregated by class (Classes 6–10) and age band
      (under 11, 11, 12, 13, 14, 15, over 15). No sex disaggregation.
      No teacher counts. Used to populate enrollment_total in
      BGD_personnel.csv. Covers Classes 6–10 only; Alim-level institutions
      (Classes 11–12 equivalent) will show incomplete enrollment figures.

  - source_id: "bgd_mauza_2022"
    name: "Official Bangladesh Mouza Shapefile (2022 Census GIS Data)"
    provider: "Bangladesh Bureau of Statistics (BBS) via justinelliotmeyers/Official_Bangladesh_Mouza_Shapefile"
    url: "https://revolutionarygis.wordpress.com/2021/05/10/bangladesh-mouza-shapefile/"
    url_status: "live"
    access_date: "2026-05"
    data_date: "2022"
    update_frequency: "Census cycle"
    format: "Shapefile"
    language: "English / Bengali"
    notes: >
      Mauza-level polygon shapefile derived from the 2022 Bangladesh Census
      GIS data. Used to generate admin_centroid coordinates for schools
      where geocoding failed validation. Mauza names matched to EMIS
      MAUZA_NAME field using rapidfuzz token_sort_ratio (threshold = 80).
      Centroids computed from polygon geometry in EPSG:4326.

  - source_id: "geoboundaries_bgd"
    name: "geoBoundaries — Bangladesh ADM1–ADM4"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-05"
    data_date: "unknown"
    update_frequency: "unknown"
    format: "Shapefile"
    language: "English"
    notes: >
      Used for two purposes: (1) fuzzy matching of EMIS administrative
      names to gB shapeName values to produce adm1–adm4 columns;
      (2) spatial validation of geocoded school coordinates against
      ADM1–ADM3 polygons. Known issue: gB ADM1 file contains 'Rajshani'
      which should be 'Rajshahi' — retained verbatim in adm1 column.

---

## GEO

**Status:** Available
**Source(s):** bgd_banbeis_institutional, bgd_mauza_2022, geoboundaries_bgd
**Year of geo data:** Unknown — EMIS snapshot accessed May 2026

### Public school subsetting
Source dataset contains ~35,000 institutions. After filtering to public
management types and in-scope education levels, 7,500 schools were retained.

| MANAGEMENT_TYPE | Count |
|-----------------|-------|
| NON-GOVERNMENT (MPO = YES) | 6,753 |
| GOVERNMENT PRIMARY | 602 |
| LOCAL GOVERNMENT | 69 |
| GOVERNMENT | 37 |
| OTHERS | 33 |
| Run by Christian Missionaries | 4 |
| AUTONOMOUS | 2 |

| EDUCATION_LEVEL | ISCED | Count |
|-----------------|-------|-------|
| Dakhil | 2 | 4,893 |
| Alim | 3 | 1,455 |
| Junior Secondary | 2 | 1,111 |
| TECHNICAL SCHOOL AND COLLEGE | 3 | 38 |
| H.S.C (B.M Independent) | 3 | 3 |

### ISCED level mapping
ISCED level assigned from source EDUCATION_LEVEL column:

- `Junior Secondary` → `2` (equivalent to JSC level, ISCED 2)
- `Dakhil` → `2` (madrasha stream secondary certificate, equivalent to SSC/ISCED 2)
- `Alim` → `3` (madrasha stream higher secondary certificate, equivalent to HSC/ISCED 3)
- `TECHNICAL SCHOOL AND COLLEGE` → `3`
- `H.S.C (B.M Independent)` → `3`

### Coordinate construction
Coordinates were assigned through a two-stage process. No coordinates were
available in the source EMIS.

**Stage 1 — Google Places API geocoding**
All schools were submitted to the Google Places API (New) Text Search
endpoint (`places.googleapis.com/v1/places:searchText`) using the query:
`{INSTITUTE NAME}, {adm1_gb}, {adm2_gb}, {adm3_gb}, {adm4_gb}, Bangladesh`
Results were filtered to prefer educational institution types (`school`,
`secondary_school`, `primary_school`, `university`, `educational_institution`,
`library`). Where multiple results were returned and none matched an
educational type, all candidates were retained for manual review.

Each geocoded point was spatially validated against geoBoundaries ADM1,
ADM2, and ADM3 polygons. A coordinate was accepted only if the point fell
within the correct Division, District, and Thana simultaneously. ADM4
(Union) was excluded from the validation threshold because geoBoundaries
Union boundaries are imprecise enough to cause false failures for correctly
geocoded schools near Union boundaries.

Validation was motivated by a quality assessment on ~320 Comilla District
schools showing the following match rates prior to filtering:

| Level | Match rate |
|-------|------------|
| ADM1 (Division) | 90.6% |
| ADM2 (District) | 73.0% |
| ADM3 (Thana) | 49.6% |
| ADM4 (Union) | 30.5% |

Schools passing ADM1–ADM3 validation:
`coordinate_source = 'address_geocoded'`, `coordinate_precision = 'approximate'`

**Stage 2 — Mauza centroid fallback**
Schools failing geocode validation or returning no result were assigned the
centroid of their matched Mauza polygon from bgd_mauza_2022. EMIS MAUZA_NAME
was fuzzy-matched to shapefile shapeName using rapidfuzz token_sort_ratio
(threshold = 80, case-normalised).

Schools assigned Mauza centroid:
`coordinate_source = 'admin_centroid'`, `coordinate_precision = 'approximate'`

**Coordinate assignment summary (n = 7,500):**

| coordinate_source | Count | Share |
|-------------------|-------|-------|
| address_geocoded | 3,121 | 41.6% |
| admin_centroid | 4,379 | 58.4% |
| No coordinate (latitude/longitude = NA) | 42 | 0.6% |

The 42 schools with no coordinate are cases where geocoding failed validation
and the Mauza fuzzy match did not find a confident match. All BGD coordinates
are approximate — neither source provides school building-level precision.

### Administrative hierarchy
`adm0` = "Bangladesh" (hardcoded).

`adm1`–`adm4` assigned by fuzzy matching EMIS administrative names
(DIVISION, DISTRICT, THANA, UNION_NAME) to geoBoundaries shapeName values
using rapidfuzz token_sort_ratio with lowercase normalisation.

- `adm1` = Division (8 divisions)
- `adm2` = District
- `adm3` = Thana/Upazila
- `adm4` = Union

### Urban/rural classification
`urban_rural` mapped from source AREA_STATUS column:

| Source AREA_STATUS | urban_rural |
|--------------------|-------------|
| RURAL | rural |
| UPZILA SADAR MUNICIPALITY | urban |
| DISTRICT SADAR MUNICIPALITY | urban |
| METROPOLITAN | urban |
| OTHER MUNICIPALITY AREA | urban |
| CityCorp | urban |
| UPZILA SADAR BUT NOT MUNICIPALITY | peri_urban |

| urban_rural | Count |
|-------------|-------|
| rural | 6,694 |
| urban | 628 |
| peri_urban | 178 |

### Known issues
- All coordinates are approximate. `address_geocoded` points reflect Google's
  place index location, which in rural areas is typically a locality or Mauza
  centroid rather than the school building. `admin_centroid` points are Mauza
  polygon centroids.
- 42 schools have no coordinate — geocoding failed and Mauza match was
  below confidence threshold.
- gB ADM1 shapeName contains 'Rajshani' (should be 'Rajshahi') — retained
  verbatim in adm1 column.
- EMIS source does not include an operational status field; `status = 'open'`
  assigned to all schools by assumption.

---

## PERSONNEL

**Status:** Partially available (enrollment only; 2016)
**Source(s):** bgd_banbeis_students_age
**Years available:** 2016

### Enrollment
`enrollment_total` computed as the sum of all age-band columns across
Classes 6–10 (5 classes × 7 age bands = 35 columns). Bangladesh secondary
schools follow a January–December academic year; `year = 2016` per UIS
beginning-year convention.

Of 18,195 schools in the student source file, 479 matched to schools in
BGD_geo.csv. The low match rate reflects the partial geographic coverage
of BGD_geo.csv at time of writing. Match rates will increase as the geo
table is expanded nationally.

### Fields not available from this source

| Field | Status |
|-------|--------|
| enrollment_male | NA — source does not disaggregate by sex |
| enrollment_female | NA — source does not disaggregate by sex |
| teachers_total | NA — not present in source file |
| teachers_male | NA — not present in source file |
| teachers_female | NA — not present in source file |
| teachers_qualified | NA — not collected |
| pupil_teacher_ratio | NA — cannot compute without teachers_total |
| classrooms_total | NA — not collected in this source |

---

## RESOURCES

**Status:** Not available
School-level infrastructure data not publicly available for Bangladesh.

---

## OUTCOMES

**Status:** Not available
School-level outcomes data not publicly available for Bangladesh.

---

## GENERAL NOTES

### Harmonization decisions
- `school_name_romanized` set to NA — EMIS names are already in Latin-script
  romanized Bengali; the school_name field serves this purpose.
- `status = 'open'` assigned to all schools — no closure data in source.
- `sector = 'public'` assigned to all schools per MPO system logic (see
  sector_notes above).
- `geo_id` assigned as BGD_{zero-padded integer} sorted by EIIN ascending
  to ensure reproducible ID assignment across re-runs.
- GHSL-SMOD classification (`ghsl_smod_code`, `ghsl_urban_rural`) not yet
  applied — pending global raster sampling step.
- `school_type` retains source INSTITUTE_TYPE verbatim (e.g. 'Madrasha',
  'School') — not harmonized across countries per schema rule.

### Change log
2026-05-15 — Initial file created
