"""
col_geo_clean.py
----------------
Cleans the Colombia MEN SIMAT schools dataset to produce col_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    Colombia Ministry of Education (MEN) — SIMAT EMIS
    File: MEN_SEDES_EDUCATIVAS_PREESCOLAR_BA_SICA_Y_MEDIA_20260504.csv
    Year: 2019

Scope:
    Public sedes only: CTE_ID_SECTOR == 'OFICIAL'
    Excluded: 'NO OFICIAL' (private schools)

Country deviation — unit of observation:
    The unit of observation is the SEDE (physical campus), not the
    establishment (institución educativa). Colombia's SIMAT assigns a
    unique CODIGO_DANE_SEDE to each sede; sedes of the same establishment
    frequently differ in zone (urban vs. rural), coordinates, and
    enrollment, and can be 50–300 km apart. The sede is therefore the
    operationally meaningful unit for cross-country comparison.
    An extra column `source_id_institution` (appended after canonical
    schema columns) carries CODIGO_DANE, the parent establishment code,
    to allow grouping by institution.

ISCED mapping:
    Source file covers Preescolar (0), Básica Primaria (1), Básica
    Secundaria (2), and Media (3) but does not disaggregate by sede.
    isced_level = '0123' assigned to all rows. A future join to a
    SIMAT grade-level extract can refine this.

Admin hierarchy:
    adm1 (department) and adm2 (municipality) assigned via spatial join
    to GeoBoundaries ADM1 and ADM2. Schools with no adm1 match (i.e.
    no valid coordinates or coordinates outside any Colombian department
    boundary) are dropped.

Coordinates:
    COORDENADA_Y_SEDE = latitude, COORDENADA_X_SEDE = longitude.
    Zeros treated as missing (common SIMAT placeholder).
    coordinate_source = 'official_emis'
    coordinate_precision = 'approximate'
    (MEN coordinates are GPS-quality for principal sedes but interpolated
    for many rural annexes.)

geo_id assignment:
    After all cleaning and the spatial join, rows are sorted
    alphabetically by school_name, then geo_id is assigned.

Author: HB / GEO Data Team
Date: 2026-05-15
"""

import os
import sys
import pandas as pd
import geopandas as gpd

# Allow importing from pipeline/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ──────────────────────────────────────────────────────────────────
SOURCE_FILE  = "/Users/heatherbaier/Documents/research/geo/sources/COL/MEN_SEDES_EDUCATIVAS_PREESCOLAR_BÁSICA_Y_MEDIA_20260504.csv"
OUTPUT = "/Users/heatherbaier/Documents/research/geo/db/geo/col_geo.csv"

ISO3 = "COL"

# ── Load source data ───────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_csv(SOURCE_FILE, encoding="utf-8", sep=None, engine="python")
print(f"  Total rows: {len(df):,}")
print(f"  Sector breakdown:\n{df['CTE_ID_SECTOR'].value_counts()}")

# ── Filter: public (OFICIAL) schools only ─────────────────────────────────
before = len(df)
df = df[df["CTE_ID_SECTOR"] == "OFICIAL"].copy()
print(f"\n  After filtering to OFICIAL: {len(df):,} rows ({before - len(df):,} dropped)")

# ── Clean source IDs (strip thousand-separator commas) ────────────────────
# SIMAT exports numeric codes with comma thousand-separators — strip verbatim
df["source_id"]             = df["CODIGO_DANE_SEDE"].astype(str).str.replace(",", "", regex=False).str.strip()
df["source_id_institution"] = df["CODIGO_DANE"].astype(str).str.replace(",", "", regex=False).str.strip()

# ── Parse coordinates — zeros are missing placeholders ────────────────────
df["latitude"]  = pd.to_numeric(df["COORDENADA_Y_SEDE"], errors="coerce")
df["longitude"] = pd.to_numeric(df["COORDENADA_X_SEDE"], errors="coerce")
df.loc[df["latitude"]  == 0, "latitude"]  = None
df.loc[df["longitude"] == 0, "longitude"] = None

# ── Drop rows with no coordinates (cannot spatially join or locate) ────────
before = len(df)
df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
print(f"\n  Dropped {before - len(df):,} rows with missing coordinates → {len(df):,} remaining")


full = pd.read_csv("/Users/heatherbaier/Documents/research/geo/sources/COL/new/MEN_MATRICULA_EN_EDUCACION_EN_PREESCOLAR,_BÁSICA_Y_MEDIA_20260518_full.csv")
full = full[~full["TIPO_JORNADA"].isin(["Fin de Semana", "Nocturna"])]
full = full[full["GRADO"].isin(['Noveno', 'Once', 'Segundo', 'Tercero', 'Decimo', 'Sexto', 'Quinto', 'Octavo', 'Primero', 'Cuarto', 'Septimo'])]
full = full[full["SECTOR"] == "OFICIAL"]

df = df[~df["CODIGO_DANE_SEDE"].isin(full["CODIGO_DANE_SEDE"].unique())]

print(f"\n  {len(df):,} remaining after droppping the ones filtered through the full dataframe.")


# ── Build GeoDataFrame ─────────────────────────────────────────────────────
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326",
)

# ── Spatial join admin boundaries from GeoBoundaries ──────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# ── Drop schools with no adm1 match (coordinate sanity check) ─────────────
# Schools that don't fall within any Colombian department boundary have
# coordinates that are erroneous — drop rather than carry bad data.
before = len(gdf)
gdf = gdf[gdf["adm1"].notna()].copy()
print(f"\n  Dropped {before - len(gdf):,} schools with no adm1 boundary match → {len(gdf):,} remaining")

# ── ISCED level ───────────────────────────────────────────────────────────
# See harmonisation note — '0123' assigned globally
gdf["isced_level"] = "0123"

# ── school_type — retain PRINCIPAL flag in national terminology ───────────
gdf["school_type"] = gdf["PRINCIPAL"].map({"S": "sede_principal", "N": "sede_anexa"})

# ── Urban / rural ─────────────────────────────────────────────────────────
gdf["urban_rural"] = gdf["ZONA"].map({"URBANA": "urban", "RURAL": "rural"})

# ── Sort alphabetically by school name, then assign geo_id ────────────────
gdf = gdf.sort_values("NOMBRE_SEDE").reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]
print(f"\n  geo_id range: {gdf['geo_id'].iloc[0]} → {gdf['geo_id'].iloc[-1]}")

# ── Build output dataframe in schema column order ──────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()

out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["source_id"]
out["country"]               = ISO3
out["school_name"]           = gdf["NOMBRE_SEDE"].str.strip()
out["school_name_romanized"] = pd.NA          # names already in Latin script
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["school_type"]
out["sector"]                = "public"
out["adm0"]                  = "Colombia"
out["adm1"]                  = gdf["adm1"]   # from GeoBoundaries
out["adm2"]                  = gdf["adm2"]   # from GeoBoundaries
out["adm3"]                  = gdf["adm3"]   # from GeoBoundaries (NA if unavailable)
out["urban_rural"]           = gdf["urban_rural"]
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "approximate"
out["status"]                = "open"
# Colombia-specific supplementary column — appended after canonical schema
out["source_id_institution"] = gdf["source_id_institution"]

# ── Validation checks ──────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].nunique() == len(out),    "ERROR: Duplicate geo_ids"
assert out["geo_id"].notna().all(),            "ERROR: Null geo_ids"
assert out["source_id"].nunique() == len(out), "ERROR: Duplicate source_ids"
assert out["country"].eq(ISO3).all(),          "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(),       "ERROR: Non-public schools found"
assert out["latitude"].notna().all(),          "ERROR: Null latitudes"
assert out["longitude"].notna().all(),         "ERROR: Null longitudes"
assert out["isced_level"].notna().all(),       "ERROR: Null isced_level"
assert out["adm1"].notna().all(),              "ERROR: Null adm1 (should have been dropped)"

print(f"\n  Total sedes in output:      {len(out):,}")
print(f"  Unique institutions:        {out['source_id_institution'].nunique():,}")
print(f"  Departments (adm1):         {out['adm1'].nunique()}")
print(f"  Municipalities (adm2):      {out['adm2'].nunique()}")
print(f"  ISCED level distribution:\n{out['isced_level'].value_counts()}")
print(f"  school_type distribution:\n{out['school_type'].value_counts()}")
print(f"  urban_rural distribution:\n{out['urban_rural'].value_counts()}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts()}")

# ── Save output ────────────────────────────────────────────────────────────
out.to_csv(OUTPUT, index=False, encoding="utf-8")
print(f"\n✓ Saved to {OUTPUT}")