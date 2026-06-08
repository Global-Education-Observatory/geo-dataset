"""
dom_geo.py
----------
Builds DOM_geo.csv from the MINERD centros educativos dataset
(Periodo Escolar 2022-2023 / 2023-2024).

GEO Dataset canonical schema v1.0

Source:
    Ministerio de Educación (MINERD) — Portal de Datos Abiertos
    "Estadísticas de Centros Educativos, Periodo Escolar 2023-2024"
    https://datos.gob.do/dataset/centros-educativos-de-republica-dominicana
    Format: XLSX (single sheet "2022-2023" contains both 2022-2023 and
            2023-2024 academic years; distinguished by Año column)

Unit of observation:
    One row = one Centro Educativo (administrative school program).
    Multiple centros can share the same Planta Física (physical building).
    The centro is the correct unit — distinct named schools, distinct
    enrollments, distinct administrative codes — even when co-located.

Scope:
    - Sector: PÚBLICO / PUBLICO only (PRIVADO and SEMIOFICIAL excluded)
    - Nivel: INICIAL, PRIMARIO, SECUNDARIO, and combinations thereof
      Adult/non-formal programs excluded:
        ADULTOS, BASICA DE ADULTOS, PREPARA REGULAR, PREPARA ACELERA,
        and their combinations
    - Year: 2022-2023 (Año == 20222023) used to define the school register

ISCED mapping:
    INICIAL                        → 0
    PRIMARIO                       → 1
    SECUNDARIO                     → 2|3   (DR secondary spans ISCED 2–3;
                                            no within-secondary disaggregation)
    INICIAL - PRIMARIO             → 0|1
    INICIAL - PRIMARIO - SECUNDARIO→ 0|1|2|3
    PRIMARIO - SECUNDARIO          → 1|2|3
    INICIAL - SECUNDARIO           → 0|2|3

Coordinate handling:
    - Coordinates sourced from source columns Coordenadas Latitud / Longitud
    - Non-numeric values set to NA
    - Positive longitude values (missing negative sign) corrected by negating
    - Rows still outside DR bounding box (lat 17–21, lon -73 to -68) after
      correction are treated as unrecoverable and dropped from geo
    - coordinate_source = 'official_emis'
    - coordinate_precision = 'approximate' (EMIS-reported; school-level
      precision not verified)

Administrative hierarchy:
    adm1 (region) and adm2 (province) sourced from source columns
    Regional and Provincia after stripping numeric prefixes.
    adm3 assigned via GeoBoundaries spatial join (municipality level).

Author: HB
"""

import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/DOM/X3I-8sq-centros-educativos-de-republica-dominicana-periodo-escolar-2023-2024xlsx.xlsx"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/dom_geo.csv"

ISO3 = "DOM"

# ── Nivel values to exclude ───────────────────────────────────────────────
# Adult/non-formal programs (not ISCED 1-3)
ADULT_NIVELES = {
    "ADULTOS",
    "BASICA DE ADULTOS",
    "PREPARA REGULAR",
    "PREPARA ACELERA",
    "PREPARA REGULAR - PREPARA ACELERA",
    "BASICA DE ADULTOS - PREPARA REGULAR",
}
# Pre-primary only (ISCED 0) — dataset scope is ISCED 1-3 only
PREPRIMARY_ONLY_NIVELES = {
    "INICIAL",
}
EXCLUDE_NIVELES = ADULT_NIVELES | PREPRIMARY_ONLY_NIVELES

# ── ISCED mapping ─────────────────────────────────────────────────────────
# INICIAL - PRIMARIO and similar combinations are retained but ISCED 0
# stripped from the level string — these schools offer ISCED 1+ in addition
# to pre-primary and are in scope.
# Harmonization note: "INICIAL - SECUNDARIO" (3 schools) has no ISCED 1
# component; retained as 2|3 since they operate secondary programs.
ISCED_MAP = {
    "PRIMARIO":                         "1",
    "SECUNDARIO":                       "2|3",
    "INICIAL - PRIMARIO":               "1",
    "INICIAL - PRIMARIO - SECUNDARIO":  "1|2|3",
    "PRIMARIO - SECUNDARIO":            "1|2|3",
    "INICIAL - SECUNDARIO":             "2|3",
}

# DR bounding box (generous)
LAT_MIN, LAT_MAX = 17.0, 21.0
LON_MIN, LON_MAX = -73.0, -68.0

# ── Load ──────────────────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_excel(SOURCE_FILE)
print(f"  Total rows: {len(df)}")

# ── Filter to 2022-2023 year ──────────────────────────────────────────────
df = df[df["Año"] == 20222023].copy()
print(f"  After year filter (2022-2023): {len(df)} rows")

# ── Filter sector ─────────────────────────────────────────────────────────
df = df[df["Sector"].isin(["PÚBLICO", "PUBLICO"])].copy()
print(f"  After public sector filter: {len(df)} rows")

# ── Filter Nivel ──────────────────────────────────────────────────────────
df = df[~df["Nivel"].isin(EXCLUDE_NIVELES)].copy()
print(f"  After excluding adult/non-formal and pre-primary-only Nivel: {len(df)} rows")
print(f"  Nivel distribution:\n{df['Nivel'].value_counts().to_string()}")

# ── Parse coordinates ─────────────────────────────────────────────────────
df["lat"] = pd.to_numeric(df["Coordenadas Latitud"], errors="coerce")
df["lon"] = pd.to_numeric(df["Coordenadas Longitud"], errors="coerce")

# Fix missing negative sign on longitude
pos_lon_mask = df["lon"].notna() & (df["lon"] > 0)
n_fixed = pos_lon_mask.sum()
df.loc[pos_lon_mask, "lon"] = -df.loc[pos_lon_mask, "lon"]
print(f"\n  Longitude sign corrected: {n_fixed} rows")

# Drop rows still outside bounding box or with null coords
before = len(df)
valid_coords = (
    df["lat"].notna() & df["lon"].notna() &
    (df["lat"] >= LAT_MIN) & (df["lat"] <= LAT_MAX) &
    (df["lon"] >= LON_MIN) & (df["lon"] <= LON_MAX)
)
df = df[valid_coords].copy()
n_dropped = before - len(df)
print(f"  Dropped {n_dropped} rows with missing or unrecoverable coordinates")
print(f"  Remaining after coordinate filter: {len(df)} rows")

# ── Parse admin fields ────────────────────────────────────────────────────
# Regional: "01 - BARAHONA" → strip numeric prefix
df["adm1_src"] = df["Regional"].str.split(" - ", n=1).str[1].str.strip().str.title()

# Provincia: already clean
df["adm2_src"] = df["Provincia"].str.strip().str.title()

# ── Parse Centros and Planta Fisica ──────────────────────────────────────
# Centros: "02334 - HERNANDO GORJON" → code + name
df["centro_code"] = df["Centros"].str.split(" - ", n=1).str[0].str.strip()
df["centro_name"] = df["Centros"].str.split(" - ", n=1).str[1].str.strip()

# Planta Fisica: "16000218 - HERNANDO GORJON" → code only for source_id_institution
df["planta_fisica_code"] = df["Planta Fisica"].str.split(" - ", n=1).str[0].str.strip()

# ── Sort and assign geo_id ────────────────────────────────────────────────
df = df.sort_values("centro_code").reset_index(drop=True)
df["geo_id"] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(df))]
print(f"\n  geo_id range: {df['geo_id'].iloc[0]} to {df['geo_id'].iloc[-1]}")

# ── ISCED level ───────────────────────────────────────────────────────────
df["isced_level"] = df["Nivel"].map(ISCED_MAP)
unmapped = df["isced_level"].isna().sum()
if unmapped > 0:
    print(f"  WARNING: {unmapped} rows with unmapped Nivel:")
    print(df[df["isced_level"].isna()]["Nivel"].value_counts())

# ── Build GeoDataFrame for spatial join ──────────────────────────────────
print("\nJoining admin boundaries from GeoBoundaries (ADM3 only)...")
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["lon"], df["lat"]),
    crs="EPSG:4326",
)
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[3])

# ── Assemble output ───────────────────────────────────────────────────────
print("\nAssembling output...")
out = pd.DataFrame()

out["geo_id"]                  = df["geo_id"]
out["source_id"]               = df["centro_code"]
out["source_id_institution"]   = df["planta_fisica_code"]
out["country"]                 = ISO3
out["school_name"]             = df["centro_name"].str.strip()
out["school_name_romanized"]   = pd.NA          # Spanish — already Latin script
out["isced_level"]             = df["isced_level"]
out["school_type"]             = df["Nivel"]    # retain source classification
out["sector"]                  = "public"
out["adm0"]                    = "Dominican Republic"
out["adm1"]                    = df["adm1_src"]
out["adm2"]                    = df["adm2_src"]
out["adm3"]                    = gdf["adm3"].values
out["urban_rural"]             = pd.NA          # not in source
out["ghsl_smod_code"]          = pd.NA
out["ghsl_urban_rural"]        = pd.NA
out["latitude"]                = df["lat"]
out["longitude"]               = df["lon"]
out["coordinate_source"]       = "official_emis"
out["coordinate_precision"]    = "approximate"
out["status"]                  = "unknown"

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== DOM_geo QA ===")
print(f"Total rows: {len(out)}")

never_null = ["geo_id", "source_id", "country", "school_name",
              "isced_level", "sector", "adm0", "coordinate_source",
              "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    flag = "WARNING" if n > 0 else "OK"
    print(f"  {flag}: {col} — {n} nulls")

print(f"\nDuplicate geo_ids: {out['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids: {out['source_id'].duplicated().sum()}")

print("\nisced_level distribution:")
print(out["isced_level"].value_counts().to_string())

print("\nadm1 distribution (top 10):")
print(out["adm1"].value_counts().head(10).to_string())

print(f"\nMissing adm3: {out['adm3'].isna().sum()}")
print(f"Missing latitude:  {out['latitude'].isna().sum()}")
print(f"Missing longitude: {out['longitude'].isna().sum()}")

# ── Save ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved: {OUTPUT_FILE}")