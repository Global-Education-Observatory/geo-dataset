"""
phl_geo.py
----------
Cleans the DepEd Philippines school masterlist (elementary + secondary sheets)
to produce phl_geo.csv conforming to the GEO Dataset canonical schema v1.0.

Source
    DepEd school masterlist, Excel workbook with one sheet for elementary
    schools and one for secondary schools.
    Columns: School Year, Region, Region w/ NIR, Division, District,
    School ID, Mother School ID, School Name, Province, Municipality,
    Latitude, Longitude

Scope
    Public DepEd schools, elementary and secondary.
    No sector column in source, so sector = 'public' is assumed for all rows.
    CONFIRM THIS against the file provenance before release.

Unit of observation
    School ID (DepEd). Annexes / satellite schools have their own School ID and
    coordinates, so they are retained as their own rows (Mother School ID is
    not carried into the canonical schema). Schools whose School ID appears on
    both sheets (integrated schools) are collapsed to one row with
    isced_level = '1|2' (or '1|2|3', see below).

ISCED mapping
    Elementary → 1
    Secondary  → 2 for school years starting before 2016 (pre K-12, four-year
                 high school, Grades 7-10)
                 2|3 for school years starting 2016 or later (Senior High
                 School, Grades 11-12, added under K-12)

Admin hierarchy
    adm1-adm3 from GeoBoundaries spatial join (project rule). Source Region,
    Division, District, Province and Municipality are NOT used for adm columns.
    Schools that do not fall inside an ADM1 polygon (outside country
    boundaries) are dropped.

Coordinates
    Decimal degrees WGS84 from source.
    coordinate_source = 'official_emis', coordinate_precision = 'exact'
    Rows with missing coordinates are dropped. No other coordinate checks.

Author: HB
"""

import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Config ────────────────────────────────────────────────────────────────
ISO3 = "PHL"
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/geo-dataset/sources/PHL/SY 2015-2016 School Geographical Location.xlsx"   # TODO confirm path
ELEM_SHEET  = "ElementarySch"    # TODO confirm sheet names
SEC_SHEET   = "SecondarySch"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/geo-dataset/db/geo/phl_geo.csv"

# ── Load ──────────────────────────────────────────────────────────────────
print("Loading source data...")
elem = pd.read_excel(SOURCE_FILE, sheet_name=ELEM_SHEET, dtype=str)
sec  = pd.read_excel(SOURCE_FILE, sheet_name=SEC_SHEET,  dtype=str)
elem.columns = sec.columns

for d in (elem, sec):
    d.columns = [c.strip() for c in d.columns]      # 'Latitude ' has trailing space

elem["level_src"] = "Elementary"
sec["level_src"]  = "Secondary"
elem["isced_part"] = "1"

df = pd.concat([elem, sec], ignore_index=True)
print(f"  Elementary rows: {len(elem)}  Secondary rows: {len(sec)}  Combined: {len(df)}")

# ── Basic cleaning ────────────────────────────────────────────────────────
df["School ID"]   = df["School ID"].str.strip()
df["School Name"] = df["School Name"].str.strip()
df["Latitude"]    = pd.to_numeric(df["Latitude"],  errors="coerce")
df["Longitude"]   = pd.to_numeric(df["Longitude"], errors="coerce")
df["year_start"]  = pd.to_numeric(df["School Year"].str[:4], errors="coerce")

n_no_id = df["School ID"].isna().sum()
if n_no_id:
    print(f"  WARNING: dropping {n_no_id} rows with no School ID")
    df = df[df["School ID"].notna()].copy()

print(f"  School years present: {sorted(df['School Year'].dropna().unique())}")

# ── ISCED level ───────────────────────────────────────────────────────────
# Secondary depends on school year (Senior High School began 2016-17)
def secondary_isced(year):
    if pd.isna(year):
        return "2|3"
    return "2" if year < 2016 else "2|3"

is_sec = df["level_src"] == "Secondary"
df.loc[is_sec, "isced_part"] = df.loc[is_sec, "year_start"].apply(secondary_isced)

# ── Coordinates ───────────────────────────────────────────────────────────
n_before = len(df)
df = df[df["Latitude"].notna() & df["Longitude"].notna()].copy()
print(f"  Dropped {n_before - len(df)} rows with missing coordinates")


# ── Collapse to one row per School ID ─────────────────────────────────────
# Integrated schools appear on both sheets. Most recent year first, then
# elementary before secondary, so name and coordinates come from the first row.
df = df.sort_values(["School ID", "year_start", "level_src"], ascending=[True, False, True])

def combine_isced(parts):
    levels = sorted({p for part in parts for p in part.split("|")})
    return "|".join(levels)

agg = df.groupby("School ID", sort=False).agg(
    isced_level=("isced_part", combine_isced),
    school_type=("level_src", lambda s: "|".join(sorted(set(s)))),
    school_name=("School Name", "first"),
    latitude=("Latitude", "first"),
    longitude=("Longitude", "first"),
).reset_index().rename(columns={"School ID": "source_id"})

print(f"  Unique School IDs: {len(agg)}  (rows before collapse: {len(df)})")

# Flag conflicting coordinates between sheets for the same School ID
coord_spread = df.groupby("School ID")[["Latitude", "Longitude"]].nunique().max(axis=1)
print(f"  School IDs with differing coordinates across rows: {(coord_spread > 1).sum()}")

# ── Admin boundaries (GeoBoundaries) ──────────────────────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = gpd.GeoDataFrame(
    agg,
    geometry=gpd.points_from_xy(agg["longitude"], agg["latitude"]),
    crs="EPSG:4326",
)
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])



# ── geo_id (after all cleaning, sorted by name) ───────────────────────────
gdf = gdf.sort_values(["school_name", "source_id"]).reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]

# ── Build output ──────────────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["source_id"]
out["country"]               = ISO3
out["school_name"]           = gdf["school_name"]
out["school_name_romanized"] = pd.NA          # Latin script in source
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["school_type"]
out["sector"]                = "public"
out["adm0"]                  = "Philippines"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = pd.NA          # not in source
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "exact"
out["status"]                = "unknown"

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== PHL_geo QA ===")
print(f"Total rows: {len(out)}")
never_null = ["geo_id", "source_id", "country", "school_name", "isced_level",
              "sector", "adm0", "adm1", "coordinate_source",
              "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    print(f"  {'WARNING' if n else 'OK'}: {col} — {n} nulls")

print(f"\nDuplicate geo_ids: {out['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids: {out['source_id'].duplicated().sum()}")
print(f"\nisced_level:\n{out['isced_level'].value_counts()}")
print(f"\nadm1 (n={out['adm1'].nunique()}):\n{out['adm1'].value_counts()}")
print(f"\nadm2 missing: {out['adm2'].isna().sum()}  adm3 missing: {out['adm3'].isna().sum()}")

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE}")