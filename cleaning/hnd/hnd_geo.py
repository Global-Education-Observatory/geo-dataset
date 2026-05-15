"""
hnd_geo.py
----------
Cleans the Honduras SIPLIE school coordinates dataset to produce hnd_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    Secretaría de Educación Honduras — SIPLIE (Sistema de Planificación de la
    Infraestructura Educativa)
    File: coordenadasporcentroeducativo_siplie_23marzo2020.xlsx
    Access date: 23 March 2020

Scope:
    Public schools only. Source is the MoE EMIS (SIPLIE) active school
    registry — all records are public. Schools with missing coordinates
    are dropped (615 rows use a sentinel value lat≈0, lon≈-91.49).

Admin hierarchy:
    adm1–adm3 assigned via spatial join to GeoBoundaries ADM1–ADM3.
    Source Departamento/Municipio columns are not used for adm fields.

Coordinates:
    Taken from Latitud/Longitud columns.
    coordinate_source = 'official_emis'
    coordinate_precision = 'exact'

ISCED mapping:
    Pre-Básica-Jardines  → ISCED 0  (kindergarten, age 4-6)
    Pre-Básica-CCPREB    → ISCED 0  (community pre-básica, age 3-5)
    Básica               → ISCED 1|2 (grades 1-9, primary + lower secondary)
    Básica - Adultos     → ISCED 1|2 (adult basic education)
    Media                → ISCED 3  (grades 10-12, upper secondary)
    Multi-level schools: component codes parsed, deduplicated, pipe-joined.

Author: HB
"""

import os
import sys
import pandas as pd
import geopandas as gpd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries


# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(BASE_DIR)
SOURCE_FILE = os.path.join(BASE_DIR, "sources", "HND", "coordenadasporcentroeducativo_siplie_23marzo2020.xlsx")
OUTPUT_FILE = os.path.join(BASE_DIR, "db", "geo", "hnd_geo.csv")
ISO3        = "HND"


# ── ISCED mapping ─────────────────────────────────────────────────────────────
NIVEL_ISCED = {
    "Pre-Básica-Jardines": ["0"],
    "Pre-Básica-CCPREB":   ["0"],
    "Básica":              ["1", "2"],
    "Básica - Adultos":    ["1", "2"],
    "Media":               ["3"],
}

def nivel_to_isced(value):
    if pd.isna(value):
        return pd.NA
    codes = []
    for part in str(value).split(" / "):
        codes.extend(NIVEL_ISCED.get(part.strip(), []))
    seen = []
    for c in codes:
        if c not in seen:
            seen.append(c)
    return "|".join(sorted(seen)) if seen else pd.NA


# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading source data...")
raw = pd.read_excel(SOURCE_FILE, header=6, dtype={"CodigoCentro": str})
print(f"  Total rows: {len(raw)}")

# ── Deduplicate ───────────────────────────────────────────────────────────────
# 10 fully identical duplicate rows; keep first.
raw = raw.drop_duplicates(subset=["CodigoCentro"], keep="first").reset_index(drop=True)
print(f"  After dedup: {len(raw)} rows")

# ── Drop missing coordinates ──────────────────────────────────────────────────
# Sentinel value (lat ≈ 0, lon ≈ -91.49) marks missing GPS data.
bad = (raw["Latitud"] < 0.1) | (raw["Longitud"] < -90.0)
print(f"  Dropping {bad.sum()} rows with missing/sentinel coordinates")
raw = raw[~bad].reset_index(drop=True)
print(f"  Remaining: {len(raw)} rows")

# ── ISCED ─────────────────────────────────────────────────────────────────────
raw["isced_level"] = raw["Nivel"].apply(nivel_to_isced)
unparsed = raw["isced_level"].isna().sum()
if unparsed > 0:
    print(f"  WARNING: {unparsed} rows have no parseable Nivel — isced_level = NA")

# ── Sort and assign geo_id ────────────────────────────────────────────────────
raw = raw.sort_values("NombreCentro").reset_index(drop=True)
raw["geo_id"] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(raw))]

# ── Build GeoDataFrame for spatial join ───────────────────────────────────────
print("\nBuilding GeoDataFrame...")
gdf = gpd.GeoDataFrame(
    raw,
    geometry=gpd.points_from_xy(raw["Longitud"], raw["Latitud"]),
    crs="EPSG:4326",
)

# ── Spatial join admin boundaries ─────────────────────────────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])

# ── Build output dataframe ────────────────────────────────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()

out["geo_id"]               = gdf["geo_id"]
out["source_id"]            = gdf["CodigoCentro"]
out["country"]              = ISO3
out["school_name"]          = gdf["NombreCentro"]
out["school_name_romanized"]= pd.NA               # Latin-script country; omit
out["isced_level"]          = gdf["isced_level"]
out["school_type"]          = gdf["Nivel"]        # Retained verbatim
out["sector"]               = "public"
out["adm0"]                 = "Honduras"
out["adm1"]                 = gdf["adm1"]
out["adm2"]                 = gdf["adm2"]
out["adm3"]                 = gdf["adm3"]
out["urban_rural"]          = gdf["Urbano / Rural"].map({"Urbano": "urban", "Rural": "rural"})
out["ghsl_smod_code"]       = pd.NA               # Applied downstream
out["ghsl_urban_rural"]     = pd.NA               # Applied downstream
out["latitude"]             = gdf["Latitud"]
out["longitude"]            = gdf["Longitud"]
out["coordinate_source"]    = "official_emis"
out["coordinate_precision"] = "exact"
out["status"]               = "open"

# ── Validation ────────────────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].nunique() == len(out),    "ERROR: Duplicate geo_ids"
assert out["geo_id"].notna().all(),            "ERROR: Null geo_ids"
assert out["country"].eq(ISO3).all(),          "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(),       "ERROR: Non-public schools"
assert out["latitude"].notna().all(),          "ERROR: Null latitudes"
assert out["longitude"].notna().all(),         "ERROR: Null longitudes"
assert out["coordinate_source"].notna().all(), "ERROR: Null coordinate_source"
assert out["status"].notna().all(),            "ERROR: Null status"

# Coordinate range for Honduras (approx 13–16N, -89.4 to -83.1E)
# lat_ok = out["latitude"].between(13.0, 16.5)
# lon_ok = out["longitude"].between(-89.4, -83.0)
# if not lat_ok.all():
#     print(f"  WARNING: {(~lat_ok).sum()} schools outside expected latitude range")
#     print(out[~lat_ok][["geo_id", "school_name", "latitude", "longitude"]])
# if not lon_ok.all():
#     print(f"  WARNING: {(~lon_ok).sum()} schools outside expected longitude range")
#     print(out[~lon_ok][["geo_id", "school_name", "latitude", "longitude"]])

out = out[~out["adm1"].isna()]

print(f"\n  Total schools in output : {len(out)}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts()}")
print(f"  ADM2 null count         : {out['adm2'].isna().sum()}")
print(f"  ADM3 null count         : {out['adm3'].isna().sum()}")
print(f"  ISCED distribution:\n{out['isced_level'].value_counts(dropna=False)}")

# ── Save ──────────────────────────────────────────────────────────────────────
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")
