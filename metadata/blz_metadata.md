---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Belize"
iso3: "BLZ"
iso2: "BZ"
region: "Central America"
last_updated: "2026-05-14"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: false
  resources: false
  outcomes:  false

school_count_total: 307
school_count_public: 307
year_range: null
years_available: []

sector_scope: "public"
sector_notes: >
  Source dataset contains 638 facilities across all sectors and levels.
  Filtered to Sector IN ['Government', 'Government Aided', 'Govern+J617ment Aided']
  AND Level_ IN ['Primary', 'Secondary']. 'Government Aided' schools in Belize
  are government-funded but managed by religious or community organisations
  (Catholic, Anglican, SDA, Methodist, etc.). They are treated as public schools
  per Belizean convention and national EMIS practice. 'Govern+J617ment Aided'
  is a data entry error in the source treated as 'Government Aided'.
  Excluded: Private (n=127), Specially Assisted (n=16).
  Excluded levels: Preschool (n=225), Adult and Continuing (n=12),
  Tertiary (n=11), Vocational (n=6), University (n=3).

sources:
  - source_id: "blz_moe_wms"
    name: "Belize Schools — Ministry of Education GIS Open Data"
    provider: "Ministry of Education, Culture, Science and Technology, Belize"
    url: "https://gis-education-tbsl.opendata.arcgis.com/datasets/ebdcbfd7309849b8b159748071c5e94f_0/explore"
    url_status: "live"
    access_date: "2026-01-10"
    data_date: "unknown"
    update_frequency: "Continuously updated WMS — no versioning or publication date available"
    format: "GeoJSON (downloaded from WMS in QGIS)"
    language: "English"
    notes: >
      Data is served from a live WMS endpoint maintained by the Belize Ministry
      of Education. No publication date or version number is available. Access
      date is approximate (early 2026). As a continuously updated source, the
      snapshot may not reflect the current school register. The downloaded
      GeoJSON is retained in sources/BLZ/ as the record of the snapshot used.

---

## GEO

**Status:** Available
**Source(s):** blz_moe_wms
**Year of geo data:** Unknown — snapshot taken in 2026

### Public school subsetting
Source dataset contains 638 facilities. After filtering to public sectors
(Government, Government Aided) and in-scope levels (Primary, Secondary),
307 schools were retained:

| Sector | Count |
|--------|-------|
| Government Aided | 229 |
| Government | 78 |

| Level | Count | ISCED |
|-------|-------|-------|
| Primary | 258 | 1 |
| Secondary | 49 | 2\|3 |

Note on Government Aided schools: Belize's school system is largely managed
by religious denominations (Catholic, Anglican, SDA, Methodist, Nazarene,
Baptist, Presbyterian) under government funding agreements. These schools
are included in the national EMIS and treated as public schools throughout
this dataset. Provider column in source data lists 85 distinct providers —
not retained in the canonical schema but available in the source GeoJSON.

### ISCED level mapping
ISCED level assigned from source `Level_` column:

- `Primary` → `1` (Belize primary covers Standards 1–6, ISCED 1)
- `Secondary` → `2|3` (Belize secondary covers Forms 1–6, spanning
  ISCED 2 lower secondary and ISCED 3 upper secondary; no within-secondary
  disaggregation available in source)

### Coordinate construction
Coordinates taken directly from source GeoJSON geometry (point features)
in EPSG:4326. No reprojection required.
`coordinate_source = 'official_emis'`, `coordinate_precision = 'exact'`
for all 307 schools.

### Administrative hierarchy
`adm0` = "Belize" (hardcoded).

`adm1`, `adm2` and `adm3` assigned via spatial join to GeoBoundaries
boundaries for BLZ.


`adm1` counts:
| District | Schools |
|----------|---------|
| Cayo | 68 |
| Belize | 61 |
| Toledo | 52 |
| Corozal | 46 |
| Orange Walk | 40 |
| Stann Creek | 26 |



`adm3` and `adm4` not available in GeoBoundaries for Belize — set to NA.

### Urban/rural classification
`urban_rural` taken directly from source `Locality` column, which provides
Urban/Rural classification for all schools.

| urban_rural | Count |
|-------------|-------|
| rural | 204 |
| urban | 103 |


### Known issues
- Data reflects a continuously updated WMS with no fixed publication date.
  The snapshot used may be from a different point in time than other countries
  in the dataset.
- `source_id` uses the source `Code` column (e.g., P19004, K12104). The
  prefix letter appears to indicate level (P=Primary, K=Kindergarten/Preschool,
  S=Secondary) but this is not confirmed in source documentation.
- No school-level data available beyond geo for Belize.

---

## PERSONNEL

**Status:** Not available
School-level personnel data not publicly available for Belize.

---

## RESOURCES

**Status:** Not available
School-level infrastructure data not publicly available for Belize.

---

## OUTCOMES

**Status:** Not available
School-level outcomes data not publicly available for Belize.

---

## GENERAL NOTES

### Source availability
The source WMS is live as of the cleaning date. The downloaded GeoJSON
snapshot is retained in `sources/BLZ/schools.geojson` as the record of
the data used for cleaning.

### Harmonization decisions
- `school_name_romanized` set to NA — all school names already in English.
- `status = 'uknown'` assigned to all schools — no closure data in source.
- `sector = 'public'` assigned to both Government and Government Aided schools
  per Belizean convention.
- Sorted by school name alphabetically before assigning `geo_id` to ensure
  reproducible ID assignment across re-runs.
- `Govern+J617ment Aided` normalised to `Government Aided` before filtering.
- GHSL-SMOD classification (`ghsl_smod_code`, `ghsl_urban_rural`) not yet
  applied — pending global raster sampling step.

### Change log
2026-05-04 — Initial file created
2026-05-14 - Through data validation done

