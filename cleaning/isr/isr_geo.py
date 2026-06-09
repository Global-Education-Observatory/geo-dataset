"""
isr_geo.py
----------
Builds ISR_geo.csv from the Israel Ministry of Education institutional
registry and official MoE coordinate file.

GEO Dataset canonical schema v1.0

Sources:
    1. MoE institutional registry (mosdot__1_.xlsx)
       Panel: 2011–2015, ~28,500 unique institutions
       Provider: Israel Ministry of Education, via data.gov.il
       URL: https://data.gov.il/he/datasets/ministry_of_education/mosdot/5548fd63-5868-4053-ad81-98caddc5e232
    2. MoE school coordinates (moe_mosdot_coordinates.csv)
       Provider: Israel Ministry of Education, via data.gov.il
       URL: https://data.gov.il/he/datasets/ministry_of_education/coordinates

Scope:
    Public primary and secondary schools only.
    Filters applied:
      - סוג מסגרת אירגונית == 'בית ספר'   (schools only; excludes kindergartens,
                                             colleges, yeshivas, seminaries, etc.)
      - פיקוח NOT חרדי                      (state and state-religious supervision only;
                                             excludes ultra-Orthodox, which operate
                                             under independent religious supervision
                                             outside the state curriculum)
      - סוג חינוך מוסד == 'רגיל'           (regular education; excludes special ed)

    Unit of observation: one row per unique סמל מוסד (school code).
    Where a school appears in multiple years, the most recent year's
    attributes are used (panel deduplication by most-recent-year).

ISCED mapping (from משכבה / עד שכבה grade range):
    Grades 1–6   → ISCED 1 (primary)
    Grades 7–9   → ISCED 2 (lower secondary / middle school)
    Grades 10–12 → ISCED 3 (upper secondary / high school)
    Grades 13–14 → post-secondary edge cases; isced_level set to NA
    Pipe-delimited where school spans multiple levels (e.g. '1|2|3')
    Grade 0 in משכבה with עד שכבה >= 1 treated as grade 1.

Administrative hierarchy:
    GeoBoundaries does not provide boundary data for Israel (all ADM levels
    return 403). adm1, adm2, adm3 are therefore set to NA for all schools.
    The source EMIS columns מחוז גאוגרפי, שם רשות, שם ישוב are retained
    as supplementary columns outside the canonical schema.

Coordinates:
    Taken from the MoE coordinate file. The source columns are named
    UTM_X / UTM_Y but contain WGS84 decimal degrees (longitude / latitude).
    ITM_X / ITM_Y (Israeli Transverse Mercator, EPSG:2039) are not used.
    coordinate_source = 'official_emis' for all matched schools.
    coordinate_precision mapped from RAMAT_DIYUK_MIKUM:
        גבוהה מאוד / גבוהה → 'exact'
        בינונית / נמוכה    → 'approximate'
    Schools with no coordinate match receive latitude/longitude = NA and
    coordinate_precision = 'unknown'.

Author: HB
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────────
REGISTRY_FILE = "/Users/heatherbaier/Documents/research/geo/sources/ISR/mosdot (1).xlsx"            # fill in
COORDS_FILE   = "/Users/heatherbaier/Documents/research/geo/sources/ISR/moe_mosdot_coordinates.csv" # fill in
OUTPUT_FILE   = "/Users/heatherbaier/Documents/research/geo/db/geo/isr_geo.csv"                     # fill in

ISO3 = "ISR"

# ── Load registry ─────────────────────────────────────────────────────────────
print("Loading institutional registry...")
df = pd.read_excel(REGISTRY_FILE)
print(f"  Loaded {len(df):,} rows, {df['סמל מוסד'].nunique():,} unique schools")
print(f"  Years: {sorted(df['שנה'].unique())}")

# ── Apply scope filters ───────────────────────────────────────────────────────
print("\nApplying scope filters...")

# Normalise פיקוח — raw Excel values contain escaped quotes
df['_pikuach'] = df['פיקוח'].astype(str).str.replace('"', '', regex=False).str.strip()

mask = (
    (df['סוג מסגרת אירגונית'] == 'בית ספר') &
    (~df['_pikuach'].str.contains('חרדי', na=False)) &
    (~df['_pikuach'].isin(['nan'])) &
    (df['סוג חינוך מוסד'] == 'רגיל')
)

filtered = df[mask].copy()
print(f"  After filters: {len(filtered):,} rows, {filtered['סמל מוסד'].nunique():,} unique schools")
print(f"  פיקוח distribution:")
for v, c in filtered['_pikuach'].value_counts().items():
    print(f"    {v}: {c:,}")

# ── Deduplicate: most recent year per school ──────────────────────────────────
print("\nDeduplicating — keeping most recent year per school...")
filtered_sorted = filtered.sort_values('שנה', ascending=False)
schools = filtered_sorted.drop_duplicates(subset='סמל מוסד', keep='first').copy()
print(f"  Unique schools: {len(schools):,}")
print(f"  Year of retained row:")
for yr, cnt in schools['שנה'].value_counts().sort_index().items():
    print(f"    {yr}: {cnt:,}")

# ── ISCED level ───────────────────────────────────────────────────────────────
def assign_isced(from_grade, to_grade):
    """
    Map Israeli grade range (משכבה / עד שכבה) to ISCED 2011 levels.

    Grade system:
        1–6   → ISCED 1 (primary)
        7–9   → ISCED 2 (lower secondary / middle school)
        10–12 → ISCED 3 (upper secondary / high school)
        13–14 → post-secondary edge cases, returns NA

    Grade 0 in from_grade with to_grade >= 1 is treated as grade 1.
    """
    try:
        lo = int(from_grade) if pd.notna(from_grade) else None
        hi = int(to_grade)   if pd.notna(to_grade)   else None
    except (ValueError, TypeError):
        return pd.NA

    if lo is None or hi is None:
        return pd.NA

    if lo == 0 and hi >= 1:
        lo = 1
    elif lo == 0 and hi == 0:
        return pd.NA

    levels = []
    if lo <= 6 and hi >= 1:
        levels.append('1')
    if hi >= 7 and lo <= 9:
        levels.append('2')
    if hi >= 10 and lo <= 12:
        levels.append('3')

    if not levels:
        return pd.NA

    return '|'.join(levels)

schools['isced_level'] = schools.apply(
    lambda r: assign_isced(r['משכבה'], r['עד שכבה']), axis=1
)

# ── Load and join coordinates ─────────────────────────────────────────────────
print("\nLoading coordinates...")
coords = pd.read_csv(COORDS_FILE)
print(f"  {len(coords):,} school coordinates loaded")

PRECISION_MAP = {
    'גבוהה מאוד': 'exact',
    'גבוהה':      'exact',
    'בינונית':    'approximate',
    'נמוכה':      'approximate',
}
coords['coordinate_precision'] = coords['RAMAT_DIYUK_MIKUM'].map(PRECISION_MAP)
coords = coords.rename(columns={
    'SEMEL_MOSAD': 'סמל מוסד',
    'UTM_X':       'longitude',
    'UTM_Y':       'latitude',
})

schools = schools.merge(
    coords[['סמל מוסד', 'latitude', 'longitude', 'coordinate_precision']],
    on='סמל מוסד',
    how='left',
)

n_matched = schools['latitude'].notna().sum()
n_missing = schools['latitude'].isna().sum()
print(f"  Matched: {n_matched:,} ({n_matched/len(schools)*100:.1f}%)")
print(f"  No coordinate: {n_missing:,}")

schools['coordinate_source'] = 'official_emis'
schools.loc[schools['latitude'].isna(), 'coordinate_precision'] = 'unknown'

# ── ADM boundaries — GeoBoundaries spatial join ───────────────────────────────
# GeoBoundaries does not provide boundary data for Israel (all ADM levels
# return HTTP 403). adm1/adm2/adm3 are set to NA.
# Source EMIS geographic columns are retained as supplementary fields below.
print("\nAdmin boundaries: GeoBoundaries not available for ISR — adm1/adm2/adm3 set to NA")

# ── Coordinate sanity check — drop points outside Israel bounding box ─────────
# Broad box including West Bank: lat 29.4–33.4, lon 34.2–35.9
before = len(schools)
valid_coords = (
    schools['latitude'].isna() |
    (
        (schools['latitude']  >= 29.0) & (schools['latitude']  <= 34.0) &
        (schools['longitude'] >= 33.5) & (schools['longitude'] <= 36.5)
    )
)
schools = schools[valid_coords].copy()
dropped = before - len(schools)
if dropped > 0:
    print(f"  WARNING: Dropped {dropped} schools with coordinates outside bounding box")
else:
    print(f"  Coordinate sanity check: all points within bounding box")

# ── sort and assign geo_id ────────────────────────────────────────────────────
# Assigned after all cleaning, sorted alphabetically by school name
schools = schools.sort_values('שם מוסד').reset_index(drop=True)
schools['geo_id'] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(schools))]

# ── Assemble output ───────────────────────────────────────────────────────────
geo = pd.DataFrame({
    'geo_id':                schools['geo_id'],
    'source_id':             schools['סמל מוסד'].astype(str),
    'country':               ISO3,
    'school_name':           schools['שם מוסד'].astype(str).str.strip(),
    'school_name_romanized': pd.NA,  # Hebrew script; romanization pass pending
    'isced_level':           schools['isced_level'],
    'school_type':           schools['_pikuach'],  # state / state-religious verbatim
    'sector':                'public',
    'adm0':                  'Israel',
    'adm1':                  pd.NA,  # GeoBoundaries not available for ISR
    'adm2':                  pd.NA,
    'adm3':                  pd.NA,
    'urban_rural':           pd.NA,  # not in source; GHSL pending
    'ghsl_smod_code':        pd.NA,
    'ghsl_urban_rural':      pd.NA,
    'latitude':              pd.to_numeric(schools['latitude'],  errors='coerce'),
    'longitude':             pd.to_numeric(schools['longitude'], errors='coerce'),
    'coordinate_source':     schools['coordinate_source'],
    'coordinate_precision':  schools['coordinate_precision'],
    'status':                'open',
    # Supplementary columns — source EMIS geography (outside canonical schema)
    'src_district':          schools['מחוז גאוגרפי'].astype(str).str.strip(),
    'src_local_authority':   schools['שם רשות'].astype(str).str.strip(),
    'src_locality':          schools['שם ישוב'].astype(str).str.strip(),
})

# ── QA ────────────────────────────────────────────────────────────────────────
print("\n=== ISR_geo QA ===")
print(f"Total rows: {len(geo)}")
print()

never_null = [
    'geo_id', 'source_id', 'country', 'school_name',
    'sector', 'adm0', 'coordinate_source', 'coordinate_precision', 'status',
]
for col in never_null:
    n = geo[col].isna().sum()
    print(f"  {'WARNING' if n > 0 else 'OK'}: {col} — {n} nulls")

print()
print("isced_level distribution:")
print(geo['isced_level'].value_counts(dropna=False).to_string())

print()
print("school_type distribution:")
print(geo['school_type'].value_counts().to_string())

print()
print("coordinate_precision distribution:")
print(geo['coordinate_precision'].value_counts(dropna=False).to_string())

print()
print("src_district distribution (supplementary):")
print(geo['src_district'].value_counts().to_string())

print()
print(f"Missing latitude:  {geo['latitude'].isna().sum()}")
print(f"Missing longitude: {geo['longitude'].isna().sum()}")
print(f"Duplicate geo_ids: {geo['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids: {geo['source_id'].duplicated().sum()}")
print(f"adm1/adm2/adm3: all NA = {geo['adm1'].isna().all()} (GeoBoundaries unavailable)")
print(f"school_name_romanized: all NA = {geo['school_name_romanized'].isna().all()} (romanization pending)")

# ── Save — canonical schema columns only ─────────────────────────────────────
GEO_COLS = [
    'geo_id', 'source_id', 'country', 'school_name', 'school_name_romanized',
    'isced_level', 'school_type', 'sector', 'adm0', 'adm1', 'adm2', 'adm3',
    'urban_rural', 'ghsl_smod_code', 'ghsl_urban_rural',
    'latitude', 'longitude', 'coordinate_source', 'coordinate_precision', 'status',
]
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
geo[GEO_COLS].to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE}")

# # Save supplementary geography file alongside
# SUPP_FILE = OUTPUT_FILE.replace('_geo.csv', '_geo_supp_geography.csv')
# geo[['geo_id', 'source_id', 'src_district', 'src_local_authority', 'src_locality']].to_csv(SUPP_FILE, index=False)
# print(f"Saved supplementary geography: {SUPP_FILE}")