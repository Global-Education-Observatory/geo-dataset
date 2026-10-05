"""
01_ury_geo.py
-------------
Cleans the Uruguay ANEP (SIGANEP) school offering files to produce ury_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    ANEP - Sistema de Informacion Geografica (SIGANEP), Oferta educativa
    Catalog: https://catalogodatos.gub.uy/dataset/anep-http-sig-anep-edu-uy-siganep-formatos
    Files:   DGEIP.xlsx (initial + primary), DGES.xlsx (secondary)
    Format:  XLSX, coordinates in UTM zone 21S (EPSG:32721)

Scope:
    Public primary and secondary schools only.
      - DGEIP: tipo_de_educacion IN ['ESCUELAS COMUNES', 'ESCUELA ESPECIAL']
      - DGES:  all centers (liceos)
    Excluded:
      - JARDIN DE INFANTES (ISCED 0)
      - Schools whose only offered level is inicial (unofrece = '3 AÑOS' / '5 AÑOS')
      - Rows with no school name or no coordinates
      - DGETP (technical / UTU): NOT YET INCLUDED, pending scope decision
      - CFE (teacher training, tertiary)

Grain:
    DGES is one row per school x plan x grade x orientation x shift and is
    collapsed to one row per ruee_calculado (verified: one X/Y per school).
    DGEIP is one row per school (ruee verified unique after filtering).

ISCED mapping:
    DGEIP -> 1 for all schools (no grade above 6 in the file)
    DGES  -> from oferta_ciclobasico / oferta_bachillergral flags
             ciclo basico only -> 2 ; bachillerato only -> 3 ; both -> 2|3

Admin hierarchy:
    adm1+ assigned via spatial join to GeoBoundaries.
    Schools outside every ADM1 polygon are DROPPED (standing coordinate check).

Coordinates:
    UTM 21S converted to WGS84. coordinate_source = 'official_emis'.
    coordinate_precision = 'exact' is a PLACEHOLDER (capture method undocumented;
    confirm with ANEP and update).

Reference year:
    Not in the source. File modified date suggests the 2023 offering (March 2023
    report), unconfirmed. Geo table has no year column, so nothing to set here,
    but record in ury_metadata.md.

Author: HB
Date: 2026-10-02
"""

import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Transformer

# Allow importing from pipeline/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_DIR  = "../../sources/URY/centros_anep"
DGEIP_FILE  = os.path.join(SOURCE_DIR, "DGEIP.xlsx")
DGES_FILE   = os.path.join(SOURCE_DIR, "DGES.xlsx")
OUTPUT_FILE = "../../db/geo/ury_geo.csv"

ISO3 = "URY"
SRC_CRS = "EPSG:32721"   # WGS84 / UTM zone 21S


# ── DGEIP (initial + primary) ─────────────────────────────────────────────
def load_dgeip(path):
    d = pd.read_excel(path)
    d.columns = d.columns.str.lower()
    print(f"  DGEIP raw rows: {len(d)}")
    print(f"  tipo_de_educacion:\n{d['tipo_de_educacion'].value_counts(dropna=False)}")

    # Scope: drop jardines (ISCED 0)
    d = d[d["tipo_de_educacion"].isin(["ESCUELAS COMUNES", "ESCUELA ESPECIAL"])].copy()

    # Drop schools whose only offered level is inicial (ISCED 0 only)
    n = d["unofrece"].astype(str).isin(["3 AÑOS", "5 AÑOS"]).sum()
    d = d[~d["unofrece"].astype(str).isin(["3 AÑOS", "5 AÑOS"])]
    print(f"  Dropped {n} inicial-only schools")

    # school_name is never-null
    n = d["nombre"].isna().sum()
    d = d[d["nombre"].notna()]
    print(f"  Dropped {n} schools with no name")

    # No coordinates and no fallback -> excluded
    n = (d["x"].isna() | d["y"].isna()).sum()
    d = d[d["x"].notna() & d["y"].notna()]
    print(f"  Dropped {n} schools with no coordinates")

    assert d["ruee"].is_unique, "ERROR: DGEIP ruee not unique"

    out = pd.DataFrame({
        "source_id":   pd.to_numeric(d["ruee"]).astype("Int64").astype(str),
        "school_name": d["nombre"].astype(str).str.strip(),
        "isced_level": "1",
        "school_type": d["tipo_de_educacion"].str.strip(),
        # Country-reported classification, mapped to schema values
        "urban_rural": d["area"].astype(str).str.strip().str.upper()
                         .map({"URBANA": "urban", "RURAL": "rural"}),
        "x": d["x"].astype(float),
        "y": d["y"].astype(float),
        "subsystem": "DGEIP",
    })
    print(f"  DGEIP schools kept: {len(out)}")
    return out.reset_index(drop=True)


# ── DGES (secondary) ──────────────────────────────────────────────────────
def load_dges(path):
    d = pd.read_excel(path)
    d.columns = d.columns.str.lower()
    print(f"  DGES raw rows: {len(d)}")

    d = d[d["ruee_calculado"].notna()].copy()

    # Verify one location per school before collapsing
    loc = d.groupby("ruee_calculado")[["x", "y"]].nunique()
    assert (loc <= 1).all().all(), "ERROR: DGES school with more than one location"

    g = (d.groupby("ruee_calculado", as_index=False)
           .agg(school_name=("nombre", "first"),
                cb=("oferta_ciclobasico", "max"),
                bach=("oferta_bachillergral", "max"),
                x=("x", "first"),
                y=("y", "first")))
    print(f"  DGES schools after collapse: {len(g)}")

    g[["cb", "bach"]] = g[["cb", "bach"]].fillna(0)
    g["isced_level"] = np.select(
        [(g["cb"] == 1) & (g["bach"] == 1), g["cb"] == 1, g["bach"] == 1],
        ["2|3", "2", "3"],
        default=None,
    )
    assert g["isced_level"].notna().all(), "ERROR: DGES school with no level flag"

    n = (g["school_name"].isna()).sum()
    g = g[g["school_name"].notna()]
    print(f"  Dropped {n} schools with no name")

    n = (g["x"].isna() | g["y"].isna()).sum()
    g = g[g["x"].notna() & g["y"].notna()]
    print(f"  Dropped {n} schools with no coordinates")

    out = pd.DataFrame({
        "source_id":   pd.to_numeric(g["ruee_calculado"]).astype("Int64").astype(str),
        "school_name": g["school_name"].astype(str).str.strip(),
        "isced_level": g["isced_level"],
        "school_type": pd.NA,       # no school type column in DGES
        "urban_rural": pd.NA,       # no urban/rural column in DGES
        "x": g["x"].astype(float),
        "y": g["y"].astype(float),
        "subsystem": "DGES",
    })
    print(f"  DGES schools kept: {len(out)}")
    return out.reset_index(drop=True)


# ── Load and combine ──────────────────────────────────────────────────────
print("Loading DGEIP...")
primary = load_dgeip(DGEIP_FILE)
print("\nLoading DGES...")
secondary = load_dges(DGES_FILE)

df = pd.concat([primary, secondary], ignore_index=True)
print(f"\n  Combined schools: {len(df)}")

# Duplicate source_ids are retained verbatim per project rule, but report them
dupes = df["source_id"].duplicated().sum()
print(f"  Duplicate source_ids across subsystems: {dupes}")

# ── Coordinates: UTM 21S -> WGS84 ─────────────────────────────────────────
transformer = Transformer.from_crs(SRC_CRS, "EPSG:4326", always_xy=True)
df["longitude"], df["latitude"] = transformer.transform(df["x"].values, df["y"].values)

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326",
)

# ── Spatial join admin boundaries from GeoBoundaries ──────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# ── Coordinate sanity check: drop schools outside ADM1 ────────────────────
outside = gdf["adm1"].isna()
print(f"\n  Schools outside ADM1 boundaries (dropped): {outside.sum()}")
if outside.sum() > 0:
    print(gdf.loc[outside, ["source_id", "school_name", "subsystem"]].to_string())
gdf = gdf[~outside].copy()

# ── Assign geo_id after all cleaning, sorted alphabetically by name ───────
gdf = gdf.sort_values(["school_name", "source_id"]).reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]
print(f"\n  geo_id range: {gdf['geo_id'].iloc[0]} to {gdf['geo_id'].iloc[-1]}")

# ── Build output dataframe in schema column order ─────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()
out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["source_id"]
out["country"]               = ISO3
out["school_name"]           = gdf["school_name"]
out["school_name_romanized"] = pd.NA            # Latin script (Spanish)
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["school_type"]
out["sector"]                = "public"
out["adm0"]                  = "Uruguay"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = gdf["urban_rural"]
out["ghsl_smod_code"]        = pd.NA            # applied later by add_ghsl.py
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "exact"          # PLACEHOLDER, confirm with ANEP
out["status"]                = "unknown"        # no operational status in source

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].nunique() == len(out), "ERROR: Duplicate geo_ids found"
assert out["geo_id"].notna().all(), "ERROR: Null geo_ids found"
assert out["country"].eq(ISO3).all(), "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(), "ERROR: Non-public schools found"
assert out["latitude"].notna().all(), "ERROR: Null latitudes"
assert out["longitude"].notna().all(), "ERROR: Null longitudes"
assert out["isced_level"].notna().all(), "ERROR: Null isced_level"
assert out["school_name"].notna().all(), "ERROR: Null school_name"
assert out["source_id"].notna().all(), "ERROR: Null source_id"
assert out["adm1"].notna().all(), "ERROR: Null adm1"

print(f"\n  Total schools in output: {len(out)}")
print(f"  By subsystem:\n{gdf['subsystem'].value_counts()}")
print(f"  ISCED level distribution:\n{out['isced_level'].value_counts()}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts()}")
print(f"  ADM2 non-null: {out['adm2'].notna().sum()}  ADM3 non-null: {out['adm3'].notna().sum()}")
print(f"  Urban/rural distribution:\n{out['urban_rural'].value_counts(dropna=False)}")
print(f"  school_type distribution:\n{out['school_type'].value_counts(dropna=False)}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")