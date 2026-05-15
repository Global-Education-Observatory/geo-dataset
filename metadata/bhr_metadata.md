---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Bahrain"
iso3: "BHR"
iso2: "BH"
region: "Western Asia"
last_updated: "2026-05-14"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: false
  resources: false
  outcomes:  false

school_count_total: 211
school_count_public: 211
year_range: "2016"
years_available: [2016]

sector_scope: "public"
sector_notes: "Source dataset includes private schools (n=79), nurseries (n=20), kindergartens (n=113), training institutes (n=101), universities (n=20), and libraries (n=16). All non-public-school records excluded. Retained only SUBTYPE EN values 'PUBLIC SCHOOLS - BOYS' (n=106) and 'PUBLIC SCHOOLS - GIRLS' (n=105)."

sources:
  - source_id: "bahrain_opengov_edu"
    name: "Educational Institutions — Bahrain Open Data Portal"
    provider: "Information & eGovernment Authority (iGA), Kingdom of Bahrain"
    url: "https://www.data.gov.bh/explore/dataset/educational-institutions/table/"
    url_status: "dead"
    access_date: "2022-01-01"
    data_date: "2016-12-01"
    update_frequency: "Unknown"
    contact: "Unknown"
    format: "CSV"
    language: "English and Arabic"
    notes: "Source data reflects a field survey and the Ministry of Education official website as of December 2016. URL was live at time of download (~2022) but has since been taken down. Unclear whether subsequent updates were published before URL went dead."

---

## GEO

**Status:** Available  
**Source(s):** bahrain_opengov_edu  
**Year of geo data:** 2016 (last update per source metadata: December 2016)

### Public school subsetting
Source dataset contains mixed facility types under the category `TYPE EN = 'EDUCATIONAL INSTITUTIONS'`. Public schools identified by filtering `SUBTYPE EN` to `['PUBLIC SCHOOLS - BOYS', 'PUBLIC SCHOOLS - GIRLS']`. This yielded 211 schools (106 boys, 105 girls). All other subtypes excluded:

- KINDERGARTEN (n=113): pre-primary facilities, outside ISCED 1+ scope
- PRIVATE SCHOOLS (n=79): excluded per V1 public-only scope
- TRAINING INSTITUTES (n=101): vocational/non-formal, not ISCED 1–3
- NURSERIES (n=20): pre-primary, outside scope
- UNIVERSITIES (n=20): ISCED 6+, outside scope
- LIBRARIES (n=16): non-school facilities

### Coordinate construction
Coordinates taken directly from source columns `POINT_X_Longitude` and `POINT_Y_Latitude` → `coordinate_source = 'official_emis'`, `coordinate_precision = 'exact'` for all 211 schools.

### Coordinate precision notes
No precision flags present in the source data. Visual inspection not performed but, no schools fell outside the expected Bahrain bounding box.

### Administrative hierarchy
`adm0` = "Bahrain" (hardcoded).

`adm1` (governorate) assigned via spatial join to GeoBoundaries ADM1 boundaries for BHR (4 features). All 211 schools matched successfully:

| Governorate | Schools |
|-------------|---------|
| Capital Governorate | 66 |
| Northern Governorate | 62 |
| Southern Governorate | 43 |
| Muharraq Governorate | 40 |

`adm2` set to NA — GeoBoundaries does not provide ADM2 boundaries for Bahrain.

`adm3` set to NA — GeoBoundaries does not provide ADM3 boundaries for Bahrain.

### ISCED level
ISCED level parsed from school name text rather than assigned from a schema field, as the source data does not include a level column. Parsing logic:

- Name contains "PRIMARY" only → `1`
- Name contains "INTERMEDIATE" only → `2`
- Name contains "SECONDARY" only → `3`
- Name contains "PRIMARY & INTERMEDIATE" → `1|2`

Results:

| isced_level | Count |
|-------------|-------|
| 1 (Primary) | 113 |
| 2 (Intermediate) | 39 |
| 3 (Secondary) | 34 |
| 1\|2 (Primary & Intermediate) | 21 |

4 schools had unparseable names. 3 are Religious Institutes with no level infomration and the fourth is a Technology Insittute. All 4 are labled as 'PUBLIC SCHOOLS - BOYS'

### Known issues
- `source_id` is the row number from the source CSV (`#` column), not necessarily a persistent national MoE school identifier. The source data does not clearly include a Bahrain Ministry of Education school code. Use caution when using `source_id` for joining to external data.
- School names contain encoding artifacts in the original source (e.g., `ª` character in some Arabic-transliterated names). These were cleaned during the standardization step.
- Data reflects December 2016 per source metadata. Schools opened or closed between 2016 and download date (~2022) will not be reflected.

---

## PERSONNEL

**Status:** Not available  
Personnel data (enrollment, teacher counts) is not publicly available for Bahrain at the school level. The Ministry of Education publishes aggregate statistics in annual reports but no school-level microdata is publicly released.

---

## RESOURCES

**Status:** Not available  
Infrastructure data is not publicly available for Bahrain at the school level.

---

## OUTCOMES

**Status:** Not available  
School-level outcomes data is not publicly available for Bahrain.

---

## GENERAL NOTES

### Source availability
The source dataset was downloaded from the Bahrain Open Data Portal in 2022. The URL `https://www.data.gov.bh/explore/dataset/educational-institutions/table/` is no longer accessible as of 2026. The original downloaded CSV is retained in `sources/bhr/` as the only record of the source data.

### Harmonization decisions
- Sorted by school name alphabetically before assigning `geo_id` to ensure reproducible ID assignment across re-runs.
- `status = 'unknown'` assigned to all schools — no closure data available in source.

### Outstanding issues
- No persistent national school ID available — `source_id` is a row number only. If a Bahrain MoE school code is identified in a future data request, this field should be updated.
- `adm2` is NA for all schools due to limated data coverage in gB. If municipality-level boundaries become available (e.g., from Bahrain's official GIS portal), adm2 could be populated via spatial join.
- Access date for source data is approximate. Exact download date should be updated if recoverable from file metadata.

### Change log
2026-05-04 — Initial file created
2026-05-14 - Through data validation done