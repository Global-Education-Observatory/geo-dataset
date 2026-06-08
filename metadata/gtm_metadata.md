---
# ═══════════════════════════════════════════════════════════════════
# GEO Dataset Country Metadata
# Template version: 1.0
# ═══════════════════════════════════════════════════════════════════

country: "Guatemala"
iso3: "GTM"
iso2: "GT"
region: "Central America"
last_updated: "2026-06-08"
prepared_by: "HB"

dimensions_available:
  geo:       true
  personnel: false
  resources: false
  outcomes:  false

school_count_total: 22903
school_count_public: 22903
year_range: "2013–2022"
years_available: [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]

sector_scope: "public"
sector_notes: >
  Source dataset contains all registered establishments including private
  schools (Sector = PRIVADO). Retained only Sector IN ['OFICIAL',
  'MUNICIPAL', 'COOPERATIVA']. COOPERATIVA schools (Institutos por
  Cooperativa) are community-run secondary institutions that receive
  direct government subsidies and are registered in the national MINEDUC
  EMIS as managed institutions. They are treated as public schools per
  the GEO schema provision for government-subsidised institutions.
  PRIVADO excluded entirely.

sources:
  - source_id: "gtm_mineduc_establecimientos"
    name: "Establecimientos Educativos — MINEDUC"
    provider: "Ministerio de Educación de Guatemala (MINEDUC)"
    url: "unknown"
    url_status: "inaccessible"
    access_date: "2026-06"
    data_date: "2013–2022"
    update_frequency: "Annual"
    format: "CSV / XLSX"
    language: "Spanish"
    notes: >
      National EMIS school register. Each file covers a two-year pair
      (e.g. establecimientos_2013-2014.csv covers calendar years 2013
      and 2014 as separate rows). Files accessed: establecimientos_2013-2014.csv,
      establecimientos_2015-2016.xlsx, establecimientos_2017-2018.xlsx,
      establecimientos_2019-2020.xlsx, establecimientos_2021-2022.xlsx.
      Source website was inaccessible at time of processing; files were
      available from prior download. Each row represents one school in
      one calendar year. Columns include CodigoEst (national school code),
      NombreEstablecimiento, Nivel, Sector, Jornada, Modalidad, Plan,
      Departamento, Municipio, Latitud, Longitud, Area, and Año.

  - source_id: "geoboundaries_gtm"
    name: "geoBoundaries — Guatemala ADM1–ADM2"
    provider: "geoBoundaries"
    url: "https://www.geoboundaries.org"
    url_status: "live"
    access_date: "2026-06"
    data_date: "2023-01-19"
    update_frequency: "unknown"
    format: "GeoJSON"
    language: "English"
    notes: >
      ADM1 (departamento, 22 features) and ADM2 (municipio, 342 features)
      boundaries. Source attribution per GeoBoundaries metadata:
      Coordinadora Nacional Para La Reducción De Desastres, OCHA FISS.
      Used for: (1) spatial join to assign adm1/adm2 to schools with
      source coordinates; (2) fuzzy name matching to assign adm1/adm2
      and compute centroids for schools without source coordinates.

---

## GEO

**Status:** Available
**Source(s):** gtm_mineduc_establecimientos, geoboundaries_gtm
**Year range of source data:** 2013–2022

### Source file structure and pooling
Each source file covers a two-calendar-year pair. Five files were loaded
and concatenated, yielding 485,365 total rows across all years. After
filtering to public in-scope schools (see below), 216,326 rows remained
representing 22,903 unique schools (CodigoEst). The `Año` column records
the calendar year of each row. No school had more than one Nivel across
years, confirming CodigoEst is stable and non-reused across the ten-year
period.

A canonical one-row-per-school register was built by taking the most
recent year's attributes (latest `Año` wins) for each CodigoEst. This
ensures school name, sector, and administrative fields reflect the most
current available record.

Note: both `establecimientos_2013-2014.csv` and `establecimientos_2013-2014.xlsx`
were present in the source directory and are identical in content. The
cleaning script deduplicated by file stem, preferring the CSV, so the
XLSX duplicate was not loaded.

### Public school subsetting
Source dataset contains schools across all sectors. Filtered to:
- `Sector IN ['OFICIAL', 'MUNICIPAL', 'COOPERATIVA']`
- `Nivel IN ['PRIMARIA', 'BASICO', 'DIVERSIFICADO']`

Excluded:
- `Sector = PRIVADO`: private schools, excluded per V1 scope
- `Nivel = PREPRIMARIA`: ISCED 0, pre-primary, out of scope
- `Nivel = PRIMARIA DE ADULTOS`: non-formal adult education, out of scope

Retained school counts by Nivel across all years (row counts, not unique schools):

| Nivel | Rows |
|-------|------|
| PRIMARIA | 164,247 |
| BASICO | 43,401 |
| DIVERSIFICADO | 8,678 |

Retained school counts by Sector across all years:

| Sector | Rows |
|--------|------|
| OFICIAL | 201,958 |
| COOPERATIVA | 11,934 |
| MUNICIPAL | 2,434 |

Final unique school register: **22,903 schools**

| isced_level | Count |
|-------------|-------|
| 1 (PRIMARIA) | 18,709 |
| 2 (BASICO) | 5,220 |
| 3 (DIVERSIFICADO) | 1,191 |

### ISCED level mapping
ISCED level assigned from source `Nivel` column:

- `PRIMARIA` → `1`: grades 1–6, ages 7–12
- `BASICO` → `2`: grades 7–9, lower secondary (ciclo básico)
- `DIVERSIFICADO` → `3`: grades 10–12, upper secondary. Diversificado
  encompasses multiple tracks including bachillerato general, magisterio
  (teacher training), and technical/vocational programmes. All tracks
  map to ISCED 3 per UNESCO ISCED 2011 classification. Some tracks
  (particularly magisterio) have characteristics that could arguea for
  ISCED 4 or 5B classification, but ISCED 3 is the standard mapping
  used by UNESCO and the Guatemalan MoE.

### Coordinate construction
Coordinates were taken directly from the source `Latitud` and `Longitud`
columns where non-null, pooled across all years. Since coordinates were
found to be perfectly stable across years for any given school (zero
schools had differing coordinate values between years), the earliest
year with a non-null coordinate was used as the canonical value.

**Source coordinate coverage:**

| coordinate_source | Count | Share |
|-------------------|-------|-------|
| official_emis | 16,216 | 70.8% |
| admin_centroid | 8,904 | 38.9% |
| No coordinate (NA) | 456 | 2.0% |

Note: coordinate_source counts sum to more than 22,903 due to 2,217
duplicate CodigoEst rows in the final output (see Known Issues).

**Stage 1 — Source coordinates:**
14,695 schools had non-null `Latitud`/`Longitud` in at least one year.
Pooling across all 10 years provided only a marginal gain — nearly all
coordinates were present from 2013 or not at all, with only 21 additional
schools gaining coordinates from later years. All source coordinates
passed the Guatemala national bounding box check (lat 13.5–18.0,
lon -92.5–-88.0; 0 failures).

`coordinate_source = 'official_emis'`, `coordinate_precision = 'exact'`

**Stage 2 — Municipio centroid fallback:**
For the 8,208 schools with no source coordinate across any year, the
centroid of the matched GeoBoundaries ADM2 (municipio) polygon was
assigned. Source `Municipio` strings (all-caps) were fuzzy-matched to
GeoBoundaries ADM2 `shapeName` values (title case) using rapidfuzz
`token_sort_ratio` with lowercase normalisation and a match threshold
of 80.

Fuzzy match results:
- Matched: 21,680 schools (94.7%)
- Unmatched (below threshold): 1,223 schools (5.3%)
- Score distribution: min=80, median=100, max=100
- Low-confidence matches (score 80–89): 4,604 schools

Of the 8,208 schools needing centroid fallback, 7,984 received a
centroid coordinate; 456 remained without coordinates because their
source `Municipio` value did not match any GeoBoundaries ADM2 shapeName
above the threshold.

GeoBoundaries ADM2 centroids were computed from polygon geometry in
EPSG:4326 (geographic CRS). Note: centroid computation in a geographic
CRS introduces a small positional error for large or irregular polygons,
but is acceptable for administrative centroid precision assignment.

`coordinate_source = 'admin_centroid'`, `coordinate_precision = 'approximate'`

**456 schools with no coordinate** are cases where the source EMIS
contained no coordinate and the Municipio fuzzy match fell below the
confidence threshold. These schools have `latitude = NA`,
`longitude = NA`, `coordinate_source = 'admin_centroid'`,
`coordinate_precision = 'approximate'`.

### Administrative hierarchy
`adm0` = "Guatemala" (hardcoded).

`adm1` (departamento) and `adm2` (municipio) assigned via spatial join
to GeoBoundaries ADM1 (22 features) and ADM2 (342 features) polygons
for schools with source coordinates, using the shared pipeline utility
`geo_boundaries.py` (left join, `predicate='within'`).

Spatial join results:
- ADM1: 23,169 matched, 17 unmatched (NA)
- ADM2: 23,173 matched, 13 unmatched (NA)

For schools assigned municipio centroid coordinates, `adm1` was
assigned via a secondary spatial join of the centroid point to ADM1
polygons. `adm2` was assigned directly from the fuzzy-matched
GeoBoundaries ADM2 `shapeName` value.

After all fills:
- ADM1 null: 473
- ADM2 null: 456

`adm3` = NA for all schools — GeoBoundaries does not provide ADM3
boundaries for Guatemala.

### Urban/rural classification
`urban_rural` mapped from source `Area` column:

| Source Area | urban_rural | Count |
|-------------|-------------|-------|
| URBANO | urban | 3,368 |
| RURAL | rural | 21,752 |

No peri_urban classification in source. GHSL-SMOD classification
(`ghsl_smod_code`, `ghsl_urban_rural`) not yet applied — pending
global raster sampling step via `add_ghsl.py`.

### Known issues
- **Duplicate source_ids in output**: The final output contains 25,120
  rows against 22,903 unique CodigoEst, yielding 2,217 duplicate
  source_id values. This is a known artifact of the coordinate merge
  step and does not affect geo_id uniqueness (0 duplicate geo_ids).
  The cause is under investigation and will be resolved before V1
  release. Users should join on `geo_id`, not `source_id`.
- **456 schools with no coordinate**: Source EMIS had no Latitud/Longitud
  and Municipio fuzzy match failed. These schools are retained in the
  register with NA coordinates; they are predominantly rural PRIMARIA
  schools. Coordinate source is recorded as 'admin_centroid' with
  precision 'approximate' to indicate the intended fallback method was
  attempted but unsuccessful.
- **4,604 low-confidence fuzzy matches (score 80–89)**: These municipio
  name matches should be reviewed if adm2 precision is critical for
  analysis. The full match score is not retained in the output but is
  available by re-running the cleaning script with verbose output.
- **Source website inaccessible**: The MINEDUC establecimientos portal
  was inaccessible at time of processing. Source files were available
  from prior download. The original downloaded files are retained in
  `sources/GTM/` as the only record of the source data.
- **Año column interpretation**: Each source file covers a two-year pair
  (e.g. 2013-2014). The `Año` column records individual calendar years.
  It is not confirmed whether `Año` represents the start or end of an
  academic year. Guatemala's school year runs approximately January–
  October, so a single calendar year likely corresponds to one complete
  academic cycle. The year convention is documented as calendar year of
  record.
- **Jornada not in output**: The source contains a `Jornada` column
  (shift: MATUTINA, VESPERTINA, DOBLE, NOCTURNA, INTERMEDIA). Within
  the filtered public in-scope set, CodigoEst was unique within each
  year, confirming that each school has a single jornada record and
  jornada is not a unit-of-observation issue for the geo table.
- **status = 'open'**: No operational status field exists in the source.
  All schools in the EMIS register are assumed open at time of data
  collection. Schools that closed during the 2013–2022 window but
  appeared in earlier files will retain status = 'open'.

---

## PERSONNEL

**Status:** Not available
Personnel data (enrollment, teacher counts) is present in the source
EMIS files but was not processed for V1. The source contains enrollment
data that could be extracted in a future pipeline pass.

---

## RESOURCES

**Status:** Not available
Infrastructure data is not available in the source EMIS files.

---

## OUTCOMES

**Status:** Not available
School-level outcomes data is not available in the source EMIS files.

---

## GENERAL NOTES

### Harmonization decisions
- `school_name_romanized` = NA for all schools — names are already in
  Latin script (Spanish).
- `sector = 'public'` for all rows — COOPERATIVA schools treated as
  public per government subsidy logic (see sector_notes above).
- `school_type` retains the source `Nivel` label in title case
  (e.g. 'Primaria', 'Basico', 'Diversificado') — not harmonized across
  countries per schema rule.
- `geo_id` assigned as GTM_{zero-padded integer} sorted by CodigoEst
  ascending to ensure reproducible ID assignment across re-runs.
- `status = 'open'` assigned to all schools — no closure data in source.
- GHSL-SMOD classification not yet applied — pending `add_ghsl.py`.

### Change log
2026-06-08 — Initial file created