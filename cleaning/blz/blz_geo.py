"""
01_blz_geo.py
-------------
Cleans the Belize schools dataset to produce blz_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    Belize Ministry of Education — Schools WMS / Open Data
    URL: https://gis-education-tbsl.opendata.arcgis.com/datasets/ebdcbfd7309849b8b159748071c5e94f_0/explore
    Format: GeoJSON (schools.geojson)

Scope:
    Public schools only:
      - Sector IN ['Government', 'Government Aided', 'Govern+J617ment Aided']
      - Level_ IN ['Primary', 'Secondary']
    Excluded:
      - Private, Specially Assisted sectors
      - Preschool, Adult and Continuing, Tertiary, Vocational, University levels

    Note: 'Government Aided' schools in Belize are government-funded but
    church-managed. They are treated as public schools per Belizean convention.
    'Govern+J617ment Aided' is a data entry error treated as 'Government Aided'.

ISCED mapping:
    Primary   → 1
    Secondary → 2|3  (Belize secondary spans Forms 1–6, covering ISCED 2 and 3;
                       no within-secondary level disaggregation available)

Admin hierarchy:
    adm1 (district) assigned via spatial join to GeoBoundaries ADM1.
    District column from source used as cross-check.
    adm2+ assigned via GeoBoundaries where available.

Coordinates:
    Longitude/Latitude already in decimal degrees (WGS84).
    coordinate_source = 'official_emis'
    coordinate_precision = 'exact'

Author: HB
Date: 2026-05-04
"""

import pandas as pd
import geopandas as gpd
import os
import sys

# Allow importing from pipeline/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo_old/data/BLZ/schools.geojson"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/blz_geo.csv"

ISO3 = "BLZ"

# ── Load source data ───────────────────────────────────────────────────────
print("Loading source data...")
gdf = gpd.read_file(SOURCE_FILE)
print(f"  Total rows: {len(gdf)}")
print(f"  CRS: {gdf.crs}")
print(f"  Level_ value counts:\n{gdf['Level_'].value_counts()}")
print(f"  Sector value counts:\n{gdf['Sector'].value_counts()}")

# ── Ensure WGS84 ───────────────────────────────────────────────────────────
if gdf.crs is None or gdf.crs.to_epsg() != 4326:
    print("  Reprojecting to EPSG:4326...")
    gdf = gdf.to_crs("EPSG:4326")

# ── Normalise Sector typo ─────────────────────────────────────────────────
gdf["Sector"] = gdf["Sector"].str.replace("Govern+J617ment Aided", "Government Aided", regex=False)

# ── Filter: public schools only ───────────────────────────────────────────
PUBLIC_SECTORS = ["Government", "Government Aided"]
PUBLIC_LEVELS  = ["Primary", "Secondary"]

mask = gdf["Sector"].isin(PUBLIC_SECTORS) & gdf["Level_"].isin(PUBLIC_LEVELS)
gdf  = gdf[mask].copy()
print(f"\n  After filtering to public Primary/Secondary: {len(gdf)} rows")
print(f"  Sector breakdown:\n{gdf['Sector'].value_counts()}")
print(f"  Level breakdown:\n{gdf['Level_'].value_counts()}")

# ── Drop rows with missing coordinates ────────────────────────────────────
before = len(gdf)
gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
if len(gdf) < before:
    print(f"  WARNING: Dropped {before - len(gdf)} rows with missing/empty geometry")

# ── Extract lat/lon from geometry ─────────────────────────────────────────
gdf["longitude"] = gdf.geometry.x
gdf["latitude"]  = gdf.geometry.y

# ── Sort and assign geo_id ────────────────────────────────────────────────
gdf = gdf.sort_values("Name").reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(gdf))]
print(f"\n  geo_id range: {gdf['geo_id'].iloc[0]} to {gdf['geo_id'].iloc[-1]}")

# ── ISCED level mapping ───────────────────────────────────────────────────
isced_map = {
    "Primary":   "1",
    "Secondary": "2|3",
}
gdf["isced_level"] = gdf["Level_"].map(isced_map)

# ── Urban/rural mapping ───────────────────────────────────────────────────
# Source Locality column: 'Urban', 'Rural' — map to schema allowed values
locality_map = {
    "Urban": "urban",
    "Rural": "rural",
}
gdf["urban_rural_src"] = gdf["Locality"].map(locality_map)

# ── Spatial join admin boundaries from GeoBoundaries ─────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# Cross-check adm1 vs source District column
if "adm1" in gdf.columns:
    mismatches = gdf[gdf["adm1"].notna() & (gdf["District"] != gdf["adm1"])]
    if len(mismatches) > 0:
        print(f"\n  NOTE: {len(mismatches)} schools have District != adm1 from GeoBoundaries")
        print(mismatches[["Name", "District", "adm1"]].to_string())

# ── Build output dataframe ────────────────────────────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()

out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["Code"].astype(str).str.strip()
out["country"]               = ISO3
out["school_name"]           = gdf["Name"].str.strip()
out["school_name_romanized"] = pd.NA          # names already in English
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["Level_"]  # retain original level label
out["sector"]                = gdf["Sector"].apply(
    lambda x: "public" if x in PUBLIC_SECTORS else x
)
out["adm0"]                  = "Belize"
out["adm1"]                  = gdf["adm1"]   # district from GeoBoundaries
out["adm2"]                  = gdf.get("adm2", pd.NA)
out["adm3"]                  = gdf.get("adm3", pd.NA)
out["urban_rural"]           = gdf["urban_rural_src"]
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "exact"
out["status"]                = "open"

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].nunique() == len(out), "ERROR: Duplicate geo_ids found"
assert out["geo_id"].notna().all(), "ERROR: Null geo_ids found"
assert out["country"].eq(ISO3).all(), "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(), "ERROR: Non-public schools found"
assert out["latitude"].notna().all(), "ERROR: Null latitudes"
assert out["longitude"].notna().all(), "ERROR: Null longitudes"
assert out["isced_level"].notna().all(), "ERROR: Null isced_level"

# Coordinate range check for Belize (roughly 15.8–18.5N, 87.5–89.2W)
lat_ok = out["latitude"].between(15.8, 18.5)
lon_ok = out["longitude"].between(-89.2, -87.5)
if not lat_ok.all():
    print(f"  WARNING: {(~lat_ok).sum()} schools outside expected latitude range")
    print(out[~lat_ok][["geo_id", "school_name", "latitude", "longitude"]])
if not lon_ok.all():
    print(f"  WARNING: {(~lon_ok).sum()} schools outside expected longitude range")
    print(out[~lon_ok][["geo_id", "school_name", "latitude", "longitude"]])

print(f"\n  Total schools in output: {len(out)}")
print(f"  ISCED level distribution:\n{out['isced_level'].value_counts()}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts()}")
print(f"  Urban/rural distribution:\n{out['urban_rural'].value_counts()}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")