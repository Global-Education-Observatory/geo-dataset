"""
01_bhr_geo.py
-------------
Cleans the Bahrain educational institutions dataset to produce bhr_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    Bahrain Open Data Portal — Educational Institutions
    URL: https://www.data.gov.bh/explore/dataset/educational-institutions/table/
    Access date: ~2022 (exact date unknown; URL now returns 404)
    Format: CSV

Scope:
    Public schools only (SUBTYPE EN in ['PUBLIC SCHOOLS - BOYS',
    'PUBLIC SCHOOLS - GIRLS']). Private schools, nurseries, kindergartens,
    training institutes, universities, and libraries excluded from V1.

Admin hierarchy:
    adm1 (governorate) and adm2 (municipality) assigned via spatial join
    to GeoBoundaries ADM1 and ADM2 boundaries respectively.
    adm3 (block) taken directly from source BLOCK column.
    adm4 not available.

Coordinates:
    Taken directly from source POINT_X_Longitude / POINT_Y_Latitude columns.
    coordinate_source = 'official_emis'
    coordinate_precision = 'exact'

ISCED level:
    Bahrain public schools cover Grades 1-9 (primary + intermediate),
    mapping to ISCED 1 (primary) and ISCED 2 (lower secondary).
    isced_level = '1|2' for all rows.

Author: HB
Date: 2026-05-04
"""

import pandas as pd
import geopandas as gpd
import os
import sys

# Allow importing from pipeline/ regardless of working directory
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries


# ── Parse ISCED level from school name ────────────────────────────────────
def parse_isced(name):
    name = str(name).upper()
    has_primary      = "PRIMARY" in name
    has_intermediate = "INTERMEDIATE" in name
    has_secondary    = "SECONDARY" in name

    if has_primary and has_intermediate:
        return "1|2"
    elif has_primary and has_secondary:
        return "1|3"
    elif has_intermediate and has_secondary:
        return "2|3"
    elif has_primary:
        return "1"
    elif has_intermediate:
        return "2"
    elif has_secondary:
        return "3"
    else:
        return pd.NA  # name doesn't contain level info


# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/BHR/bahrain_school_locations.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/bhr_geo.csv"

ISO3 = "BHR"

# ── Load source data ───────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_csv(SOURCE_FILE)
print(f"  Total rows: {len(df)}")
print(f"  SUBTYPE EN value counts:\n{df['SUBTYPE EN'].value_counts()}\n")

# ── Filter to public schools only ─────────────────────────────────────────
PUBLIC_TYPES = ["PUBLIC SCHOOLS - BOYS", "PUBLIC SCHOOLS - GIRLS"]
df = df[df["SUBTYPE EN"].isin(PUBLIC_TYPES)].copy()
print(f"  After filtering to public schools: {len(df)} rows")

# ── Drop rows with missing coordinates ────────────────────────────────────
before = len(df)
df = df.dropna(subset=["POINT_X_Longitude", "POINT_Y_Latitude"])
if len(df) < before:
    print(f"  WARNING: Dropped {before - len(df)} rows with missing coordinates")

# ── Reset index ───────────────────────────────────────────────────────────
df = df.reset_index(drop=True)

# ── Assign geo_id ──────────────────────────────────────────────────────────
# Sort by school name first for reproducibility
df = df.sort_values("NAME").reset_index(drop=True)
df["geo_id"] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(df))]
print(f"\n  geo_id range: {df['geo_id'].iloc[0]} to {df['geo_id'].iloc[-1]}")

# ── Build GeoDataFrame for spatial join ───────────────────────────────────
print("\nBuilding GeoDataFrame...")
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["POINT_X_Longitude"], df["POINT_Y_Latitude"]),
    crs="EPSG:4326"
)

gdf["isced_level"] = gdf["NAME"].apply(parse_isced)

# Check how many couldn't be parsed
unparsed = gdf["isced_level"].isna().sum()
if unparsed > 0:
    print(f"  WARNING: {unparsed} schools have no level in name — isced_level = NA")
    print(gdf[gdf["isced_level"].isna()][["NAME", "SUBTYPE EN"]])

print(f"\n  ISCED level distribution:\n{gdf['isced_level'].value_counts()}")

# ── Spatial join admin boundaries from GeoBoundaries ─────────────────────
# Attempts ADM1–ADM4; silently sets NA for any level not available for BHR.
# BHR has ADM1 (governorates) only — ADM2+ will be set to NA automatically.
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# ── Build output dataframe ────────────────────────────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()

out["geo_id"]               = gdf["geo_id"]
out["source_id"]            = gdf["#"].astype(str)   # row number from source — not a true MoE ID
out["country"]              = ISO3
out["school_name"]          = gdf["NAME ARABIC"]     # official name in Arabic script
out["school_name_romanized"]= gdf["NAME"]            # English/romanized version
out["isced_level"]          = gdf["isced_level"]     # primary + intermediate
out["school_type"]          = gdf["SUBTYPE EN"]      # retain original classification
out["sector"]               = "public"
out["adm0"]                 = "Bahrain"
out["adm1"]                 = gdf["adm1"]            # governorate from GeoBoundaries
out["adm2"]                 = gdf["adm2"]            # NA — not available in GeoBoundaries
out["adm3"]                 = gdf["BLOCK"].astype(str).str.strip()  # block from source
out["urban_rural"]          = pd.NA                  # not in source
out["ghsl_smod_code"]       = pd.NA                  # to be applied globally post-cleaning
out["ghsl_urban_rural"]     = pd.NA                  # to be applied globally post-cleaning
out["latitude"]             = gdf["POINT_Y_Latitude"]
out["longitude"]            = gdf["POINT_X_Longitude"]
out["coordinate_source"]    = "official_emis"
out["coordinate_precision"] = "exact"
out["status"]               = "open"                 # no closure data available

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].nunique() == len(out), "ERROR: Duplicate geo_ids found"
assert out["geo_id"].notna().all(), "ERROR: Null geo_ids found"
assert out["country"].eq(ISO3).all(), "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(), "ERROR: Non-public schools found"
assert out["latitude"].notna().all(), "ERROR: Null latitudes"
assert out["longitude"].notna().all(), "ERROR: Null longitudes"
assert out["coordinate_source"].notna().all(), "ERROR: Null coordinate_source"
assert out["coordinate_precision"].notna().all(), "ERROR: Null coordinate_precision"
assert out["status"].notna().all(), "ERROR: Null status"

# Coordinate range check for Bahrain (roughly 25.5–26.5N, 50.3–50.8E)
lat_ok = out["latitude"].between(25.5, 26.5)
lon_ok = out["longitude"].between(50.3, 50.8)
if not lat_ok.all():
    print(f"  WARNING: {(~lat_ok).sum()} schools have latitude outside expected Bahrain range")
    print(out[~lat_ok][["geo_id", "school_name", "latitude", "longitude"]])
if not lon_ok.all():
    print(f"  WARNING: {(~lon_ok).sum()} schools have longitude outside expected Bahrain range")

print(f"\n  Total schools in output: {len(out)}")
print(f"  Boys schools: {(out['school_type'] == 'PUBLIC SCHOOLS - BOYS').sum()}")
print(f"  Girls schools: {(out['school_type'] == 'PUBLIC SCHOOLS - GIRLS').sum()}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts()}")
print(f"  ADM2 distribution:\n{out['adm2'].value_counts()}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")
print(f"  Columns: {list(out.columns)}")
