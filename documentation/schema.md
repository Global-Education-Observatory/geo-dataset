# GEO Dataset — Canonical Schema
**Version 1.0 · Four-Table Structure: Geo · Personnel · Resources · Outcomes**

---

## 1. Purpose

This document defines the canonical, authoritative schema for the Global Education Observatory (GEO) multi-country school dataset. It is the single reference against which all country-level data must be cleaned. Once cleaning is complete to this specification, the schema does not change — only new country files are added.

The schema is organized as four flat, joinable CSV files per country. All four tables share `geo_id` as the primary join key. The geo table is the unique school register (no year column). The personnel, resources, and outcomes tables each have a year column and may have multiple rows per school where panel data is available.

> **Rule:** If a column cannot be populated for a given country, it is present in the file with NA values — the column is never dropped. This ensures all country files have identical structure.

---

## 2. Unit of Observation & Key Decisions

### Unit of observation
One row = one school (geo table) or one school × one year (personnel, resources, outcomes tables). A school is defined as a single administrative unit assigned a unique `source_id` by the national MoE EMIS. Compound schools offering multiple ISCED levels under one administrative record are treated as one row, with `isced_level` recording all levels offered (pipe-delimited).

### Year convention
The `year` column records the calendar year in which the academic year begins. For a 2022/23 school year, `year = 2022`. This is the UIS survey convention. Where a country deviates from this, document in the harmonization note — do not alter the year value.

### Scope: public schools only
The dataset covers public (government) schools only. The `sector` column records `'public'` for all rows in scope. Private, faith-based, and community schools are excluded unless they are government-subsidised and appear in the national EMIS as a managed school (document any such inclusions in the harmonization note).

### Identifier scheme
Each school has two identifiers:

- **`geo_id`** — project-assigned, format `{ISO3}_{zero-padded integer}`, e.g., `PHL_000001`. Permanent and never reused. Primary join key across all four tables.
- **`source_id`** — the national MoE school code, verbatim from the source EMIS (DepEd ID for Philippines, CUEANEXO for Argentina, etc.). Only present in the geo table. Used for external joins to source data.

---

## 3. Standards Anchors

| Standard | Description |
|----------|-------------|
| UNESCO ISCED 2011 | Defines education levels 0–8. Used for `isced_level` classification. `uis.unesco.org/en/isced-mappings` |
| UIS Glossary | Authoritative definitions for enrollment, teaching staff, repetition, promotion, dropout, PTR, GIR. `uis.unesco.org/en/glossary` |
| UIS Indicators | Indicator metadata and computation formulas. `data.uis.unesco.org` |
| WHO/UNICEF JMP 2018 | Defines basic/limited/no service tiers for WASH in schools. `washdata.org` |
| UNICEF Giga | School connectivity definitions and school mapping methodology. `giga.global` |
| ISO 3166-1 | Country codes (alpha-3). Used for `country` column and `geo_id` prefix. |
| GADM | Global Administrative Areas — reference for adm1/adm2/adm3 names. `gadm.org` |
| WGS84 / EPSG:4326 | Coordinate reference system. All coordinates in decimal degrees, WGS84. |
| GHSL-SMOD R2023 | GHSL Settlement Model Grid, epoch 2020, 1km resolution. Used for standardized urban/rural classification. `human-settlement.ec.europa.eu` |
| Project standard | Conventions defined in this document with no direct external equivalent. |

---

## 4. Table Schemas

### 4.1 GEO TABLE — `{ISO3}_geo.csv`

One row per school · No year column · This is the unique school register.

> `source_id` lives only in this table. Use `geo_id` for all joins between the four project tables.

| Column | Type | Required | NA Rule | Definition | Standard |
|--------|------|----------|---------|------------|----------|
| `geo_id` | String | Yes | Never null | Project-assigned unique school identifier. Format: `{ISO3}_{zero-padded integer}` (e.g., `PHL_000001`). Primary join key across all four tables. Assigned once and never changed. | Project standard |
| `source_id` | String | Yes | Never null | National MoE-assigned school identifier as it appears in the source EMIS. Retained verbatim — do not zero-pad or reformat. Used for external joins to source data. | National EMIS |
| `country` | String | Yes | Never null | ISO 3166-1 alpha-3 country code (e.g., `PHL`, `HND`, `ARG`). Uppercase. | ISO 3166-1 |
| `school_name` | String | Yes | Never null | Official school name as recorded in the national EMIS, in the original language and script. Do not translate or romanize. | National EMIS |
| `school_name_romanized` | String | No | NA if unavailable | Romanized version of `school_name` where the original is in a non-Latin script. Use official MoE romanization if provided; otherwise ISO 233 or ALA-LC transliteration. Omit for Latin-script countries. | ISO 233 / ALA-LC |
| `isced_level` | String | Yes | Never null | ISCED 2011 level(s) offered, pipe-delimited if multiple. Allowed values: `0`, `1`, `2`, `3`, `02`, `12`, `123`. | UNESCO ISCED 2011 |
| `school_type` | String | No | NA if not classified | National school type classification from source EMIS. Retained in original terminology — not harmonized across countries. | National EMIS |
| `sector` | String | Yes | Never null | School management sector. Allowed values: `public`, `private`, `faith_based`, `community`. Should be `public` for all V1 rows. | UIS Glossary |
| `adm0` | String | Yes | Never null | Country name (English). UN official short name. | UN M.49 |
| `adm1` | String | Yes | NA if not available | First administrative subdivision (region, province, state). Official English or romanized name. | GADM Level 1 |
| `adm2` | String | No | NA if not available | Second administrative subdivision (province, department, district). | GADM Level 2 |
| `adm3` | String | No | NA if not available | Third administrative subdivision (municipality, commune, barangay). | GADM Level 3 |
| `urban_rural` | String | No | NA if not classified | Country-reported urban/rural classification. Allowed values: `urban`, `rural`, `peri_urban`. Do not reclassify using external sources. | UIS Glossary |
| `ghsl_smod_code` | Integer | No | NA until GHSL applied | GHSL SMOD class code (10–30) for the 1km cell containing the school coordinate. Source: GHS-SMOD R2023, epoch 2020. | GHSL-SMOD R2023 |
| `ghsl_urban_rural` | String | No | NA until GHSL applied | Simplified 3-class label derived from `ghsl_smod_code`. Allowed values: `urban` (codes 22–30), `peri_urban` (code 21), `rural` (codes 10–13). Use for cross-country comparisons. | GHSL-SMOD R2023 |
| `latitude` | Float | Yes | NA if unavailable | Geographic latitude in decimal degrees (WGS84). Positive = North. | WGS84 / EPSG:4326 |
| `longitude` | Float | Yes | NA if unavailable | Geographic longitude in decimal degrees (WGS84). Positive = East. | WGS84 / EPSG:4326 |
| `coordinate_source` | String | Yes | Never null | Method by which coordinates were obtained. Allowed values: `gps_field`, `official_emis`, `address_geocoded`, `toponym_geocoded`, `satellite_detected`, `admin_centroid`. | Project standard |
| `coordinate_precision` | String | Yes | Never null | Precision flag. Allowed values: `exact`, `approximate`, `admin_centroid`. | Project standard |
| `status` | String | Yes | Never null | Operational status at time of data collection. Allowed values: `open`, `closed_temporary`, `closed_permanent`, `unknown`. | Project standard |

---

### 4.2 PERSONNEL TABLE — `{ISO3}_personnel.csv`

One row per school × year · Captures human resource inputs.

> UIS definition of 'teaching staff' explicitly excludes principals, administrators, and classroom aides unless they also deliver instruction.

| Column | Type | Required | NA Rule | Definition | Standard |
|--------|------|----------|---------|------------|----------|
| `geo_id` | String | Yes | Never null | Project-assigned unique school identifier. Foreign key to geo table. | Project standard |
| `year` | Integer | Yes | Never null | Beginning year of the academic year (e.g., 2022 for 2022/23). | UIS survey convention |
| `enrollment_total` | Integer | Yes | NA if unavailable | Total students enrolled on the EMIS reference date. Headcount, not FTE. Includes all grades. | UIS Indicator: ENR |
| `enrollment_male` | Integer | No | NA if not disaggregated | Male students enrolled. Subset of `enrollment_total`. | UIS Indicator: ENR.M |
| `enrollment_female` | Integer | No | NA if not disaggregated | Female students enrolled. Subset of `enrollment_total`. | UIS Indicator: ENR.F |
| `teachers_total` | Integer | Yes | NA if unavailable | Total teaching staff. Headcount, not FTE. Excludes administrative and support staff. | UIS Indicator: TEACH |
| `teachers_male` | Integer | No | NA if not disaggregated | Male teaching staff. Subset of `teachers_total`. | UIS Indicator: TEACH.M |
| `teachers_female` | Integer | No | NA if not disaggregated | Female teaching staff. Subset of `teachers_total`. | UIS Indicator: TEACH.F |
| `teachers_qualified` | Integer | No | NA if not collected | Teachers meeting the national minimum qualification standard. Document the national standard in the harmonization note. | UIS Indicator: TEACH.TRAIN |
| `pupil_teacher_ratio` | Float | No | Computed, NA if either input is NA | `enrollment_total / teachers_total`. Computed — do not source directly from EMIS. | UIS Indicator: PTR |
| `classrooms_total` | Integer | No | NA if not collected | Total instructional rooms. Excludes offices, storage, latrines, kitchens. | UIS / IIEP EMIS |

---

### 4.3 RESOURCES TABLE — `{ISO3}_resources.csv`

One row per school × year · Captures physical infrastructure inputs.

> All infrastructure variables are binary (0/1). Where source data uses a more granular scale, retain the original in a supplementary file and map to binary here. Document the mapping threshold in the harmonization note.

| Column | Type | Required | NA Rule | Definition | Standard |
|--------|------|----------|---------|------------|----------|
| `geo_id` | String | Yes | Never null | Project-assigned unique school identifier. Foreign key to geo table. | Project standard |
| `year` | Integer | Yes | Never null | Beginning year of the academic year. | UIS survey convention |
| `water_basic` | Integer | Yes | NA if not collected | School has access to a basic drinking water service. Binary: 1 = yes, 0 = no. JMP definition of 'basic': improved water source available at the school. | WHO/UNICEF JMP 2018 |
| `water_improved` | Integer | No | NA if not collected | School has an improved water source on or near premises. Binary: 1 = yes, 0 = no. Only populate if source distinguishes service levels. | WHO/UNICEF JMP 2018 |
| `sanitation_basic` | Integer | Yes | NA if not collected | School has access to a basic sanitation facility. Binary: 1 = yes, 0 = no. JMP definition: improved facility that is usable. | WHO/UNICEF JMP 2018 |
| `sanitation_sex_separated` | Integer | No | NA if not collected | Sanitation facilities are separated by sex. Binary: 1 = yes, 0 = no. | WHO/UNICEF JMP 2018 |
| `handwashing_basic` | Integer | No | NA if not collected | Functional handwashing facility with water and soap or ash available. Binary: 1 = yes, 0 = no. | WHO/UNICEF JMP 2018 |
| `electricity` | Integer | Yes | NA if not collected | School has access to electricity from any source (grid, solar, generator). Binary: 1 = yes, 0 = no. | UIS / SE4All |
| `internet` | Integer | No | NA if not collected | School has internet connectivity of any type. Binary: 1 = yes, 0 = no. | UNICEF Giga / ITU |
| `internet_type` | String | No | NA if not collected or internet = 0 | Type of internet connection. Allowed values: `fiber`, `cable_modem`, `dsl`, `mobile_3g`, `mobile_4g`, `mobile_5g`, `satellite`, `other`. | ITU / UNICEF Giga |
| `computer_lab` | Integer | No | NA if not collected | School has a functioning computer laboratory. Binary: 1 = yes, 0 = no. | UIS ICT indicator |
| `library` | Integer | No | NA if not collected | School has a library or reading room with books available. Binary: 1 = yes, 0 = no. | IIEP EMIS standard |
| `permanent_building` | Integer | No | NA if not collected | School has at least one permanent (non-temporary) instructional building. Binary: 1 = yes, 0 = no. | IIEP EMIS / GPE |

---

### 4.4 OUTCOMES TABLE — `{ISO3}_outcomes.csv`

One row per school × year · Captures educational output indicators.

> Outcomes data is the sparsest dimension in LMIC EMIS systems. Only include rows where data is genuinely school-level — do not impute national or provincial averages down to the school level.

| Column | Type | Required | NA Rule | Definition | Standard |
|--------|------|----------|---------|------------|----------|
| `geo_id` | String | Yes | Never null | Project-assigned unique school identifier. Foreign key to geo table. | Project standard |
| `year` | Integer | Yes | Never null | Academic year from which outcomes are reported. Document the convention used in the harmonization note. | UIS survey convention |
| `promotion_rate` | Float | No | NA if not collected | Proportion of students enrolled in grade g who enroll in grade g+1 the following year. Expressed as proportion (0.0–1.0), not percentage. UIS reconstructed cohort method. | UIS Indicator: PROM |
| `repetition_rate` | Float | No | NA if not collected | Proportion of students enrolled in grade g who re-enroll in the same grade the following year. Expressed as proportion (0.0–1.0). | UIS Indicator: REP |
| `dropout_rate` | Float | No | NA if not collected | Proportion of students enrolled in grade g who are neither promoted nor retained the following year. Expressed as proportion (0.0–1.0). Flag in harmonization note whether sourced directly or computed as `1 − promotion_rate − repetition_rate`. | UIS Indicator: DROP |
| `completion_rate` | Float | No | NA if not collected | Proportion of students who complete the final grade of the school's ISCED level. Expressed as proportion (0.0–1.0). | UIS Indicator: COMP |
| `gross_intake_ratio` | Float | No | NA if not collected | Ratio of new entrants in first grade to the population of official primary entry age. Can exceed 1.0 due to over-age entrants. Only include if explicitly provided by source. | UIS Indicator: GIR |
| `outcome_reference_grade` | String | No | NA if outcomes not collected | Grade or level to which outcome rates refer. Use national grade notation (e.g., `Grade 6`, `CM2`) or `all_grades` if averaged across all grades. | Project standard |

---

## 5. NA Rules Reference

| NA Rule | Meaning | Example columns |
|---------|---------|-----------------|
| Never null | Must always have a value. Missing value = data error. | `geo_id`, `country`, `year`, `enrollment_total` |
| NA if unavailable | Data was sought but could not be obtained. | `latitude`/`longitude` where not in EMIS |
| NA if not collected | National EMIS does not collect this variable at all. Document in harmonization note. | `teachers_qualified`, `internet_type`, `completion_rate` |
| NA if not disaggregated | Aggregate available but sex disaggregation not reported at school level. | `enrollment_male`, `enrollment_female`, `teachers_male` |
| Computed, NA if inputs NA | Derived from other fields. NA if inputs are NA. | `pupil_teacher_ratio` |

---

## 6. Country Cleaning Checklist

### Geo table
- [ ] Every school has a unique `geo_id` in `{ISO3}_{N}` format
- [ ] `source_id` is verbatim from EMIS — not reformatted
- [ ] `isced_level` is coded to ISCED 2011 values
- [ ] `sector = 'public'` for all rows (or deviation is documented)
- [ ] `latitude` and `longitude` are in decimal degrees, WGS84
- [ ] `coordinate_source` and `coordinate_precision` are populated for every row — no NA
- [ ] `status` is populated for every row
- [ ] All adm fields use official names, not abbreviations

### Personnel table
- [ ] `year` follows beginning-year convention (document any deviation)
- [ ] `enrollment_total` is headcount on reference date — not annual admissions
- [ ] `teachers_total` excludes non-teaching staff (document any deviation)
- [ ] `pupil_teacher_ratio` computed as `enrollment_total / teachers_total` — not sourced from EMIS
- [ ] Disaggregated counts (male/female) sum to total — flag discrepancy > 1%

### Resources table
- [ ] All variables are binary integers (0 or 1) — no strings, no nulls where source has data
- [ ] `water_basic` and `sanitation_basic` mapped to JMP 'basic' tier — document mapping
- [ ] `internet_type` is populated only where `internet = 1`

### Outcomes table
- [ ] Rates are proportions (0.0–1.0) — not percentages
- [ ] `promotion_rate + repetition_rate + dropout_rate ≈ 1.0` (within ±0.02 rounding tolerance)
- [ ] `outcome_reference_grade` is populated where rates are grade-specific
- [ ] School-level status confirmed — no provincial/national averages assigned to schools

### All tables
- [ ] All four files have identical column order to schema
- [ ] No extra columns (country-specific variables go in supplementary file)
- [ ] Harmonization note is complete and matches the cleaning decisions made
- [ ] Row counts in personnel/resources/outcomes are consistent with school count in geo