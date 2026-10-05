"""
per_geo.py
----------
Builds per_geo.csv conforming to the GEO Dataset canonical schema v1.0.

Sources (MINEDU, Peru):
    REGISTER  Numero de matriculados de Educacion Basica Regular (EBR) 2025
              Nu_mero_de_matriculados_de_Educacio_n_Ba_sica_Regular__EBR__2025.csv
              ';'-delimited, UTF-8 with BOM. One row per servicio educativo
              (COD_MOD). Provides COD_MOD, CODLOCAL, names, level, gestion,
              DAREACENSO. NLAT_IE / NLONG_IE in this file are truncated to
              whole degrees and are NOT used.
    COORDS    Padron de instituciones educativas, snapshot 10-09-2018
              Relacio_n_de_instituciones_y_programas_educativos.csv
              ','-delimited. Accented characters corrupted to U+FFFD in the
              file itself, so only numeric fields (cod_mod, anexo, codlocal,
              nlat_ie, nlong_ie) are used from it.

Unit of observation:
    Servicio educativo (COD_MOD). A primaria and a secundaria sharing one
    building are two rows with the same coordinates. COD_MOD is unique
    within scope in the 2025 register.

Scope:
    NIV_MOD in {B0 Primaria, F0 Secundaria}
    GESTION in {1 Publica de gestion directa, 2 Publica de gestion privada}
      - gestion directa: Sector Educacion, Municipalidad, FF.AA.
      - gestion privada = Convenio con Sector Educacion (Fe y Alegria,
        parochial). State-funded teachers; included as public, same logic
        as BGD MPO and BLZ Government Aided.
    D_FORMA == 'Escolarizada'
    Active only. The 2025 enrollment register lists operating servicios
    only, so status = 'open' for all rows.

ISCED mapping:
    B0 Primaria   -> 1
    F0 Secundaria -> 2|3 (5-year cycle spans ISCED 2 and 3; no within-cycle
                          split in the register; BLZ precedent)

Coordinates (two tiers, both MINEDU official EMIS points):
    Tier 1  COD_MOD match to 2018 padron (anexo 0 row preferred)
    Tier 2  CODLOCAL match to 2018 padron (servicio new since 2018 but in an
            existing building; CODLOCAL is stable across snapshots for ~99%
            of COD_MOD-matched servicios)
    Unmatched servicios are dropped (no-imputation rule).
    (0, 0) coordinates in the padron are treated as missing.
    coordinate_source    = 'official_emis'
    coordinate_precision = 'exact' if >= 4 decimal places in the padron
                           string, else 'approximate'

Admin hierarchy:
    adm1-adm3 from GeoBoundaries spatial join (standing rule). Schools that
    fall outside every ADM1 polygon are dropped.

Author: HB
"""

import os
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SRC_DIR     = "/Users/heatherbaier/Documents/research/geo/sources/PER"
REGISTER    = os.path.join(SRC_DIR, "Número de matriculados de Educación Básica Regular (EBR) 2025.csv")
PADRON_2018 = os.path.join(SRC_DIR, "Relación de instituciones y programas educativos.csv")
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/per_geo.csv"

ISO3 = "PER"

ISCED_MAP  = {"B0": "1", "F0": "2|3"}
URBAN_MAP  = {"Urbana": "urban", "Rural": "rural"}
PUBLIC_GES = ["1", "2"]


def norm_code(s: pd.Series) -> pd.Series:
    """Join key only: strip whitespace and leading zeros. source_id stays verbatim."""
    return s.astype(str).str.strip().str.lstrip("0")


def n_decimals(s: pd.Series) -> pd.Series:
    """Number of decimal places in a coordinate string."""
    return s.astype(str).str.split(".").str[1].str.len().fillna(0).astype(int)


# ── 1. Load and filter register ──────────────────────────────────────────
print("Loading 2025 register...")
reg = pd.read_csv(REGISTER, sep=";", dtype=str, encoding="utf-8-sig")
print(f"  Total rows: {len(reg)}")

mask = (
    reg["NIV_MOD"].isin(ISCED_MAP.keys())
    & reg["GESTION"].isin(PUBLIC_GES)
    & reg["D_FORMA"].eq("Escolarizada")
)
reg = reg[mask].copy()
print(f"  Public escolarizada Primaria/Secundaria: {len(reg)}")
print(f"  D_GES_DEP:\n{reg['D_GES_DEP'].value_counts().to_string()}")
print(f"  Duplicate COD_MOD: {reg['COD_MOD'].duplicated().sum()}")

reg["k_codmod"]   = norm_code(reg["COD_MOD"])
reg["k_codlocal"] = norm_code(reg["CODLOCAL"])

# ── 2. Load 2018 padron coordinates ──────────────────────────────────────
print("\nLoading 2018 padron (coordinates only)...")
pad = pd.read_csv(
    PADRON_2018, dtype=str,
    usecols=["cod_mod", "anexo", "codlocal", "nlat_ie", "nlong_ie"],
)
lat = pd.to_numeric(pad["nlat_ie"], errors="coerce")
lon = pd.to_numeric(pad["nlong_ie"], errors="coerce")
bad = lat.isna() | lon.isna() | (lat == 0) | (lon == 0)
print(f"  Padron rows: {len(pad)}  |  missing or (0,0) coords dropped: {bad.sum()}")
pad = pad[~bad].copy()

pad["k_codmod"]   = norm_code(pad["cod_mod"])
pad["k_codlocal"] = norm_code(pad["codlocal"])
pad["anexo_n"]    = pd.to_numeric(pad["anexo"], errors="coerce")

# One coordinate per COD_MOD (prefer anexo 0) and per CODLOCAL
by_codmod = (pad.sort_values("anexo_n")
                .drop_duplicates("k_codmod")[["k_codmod", "nlat_ie", "nlong_ie"]])
by_codlocal = (pad.sort_values(["k_codlocal", "anexo_n"])
                  .drop_duplicates("k_codlocal")[["k_codlocal", "nlat_ie", "nlong_ie"]])

# ── 3. Two-tier coordinate join ──────────────────────────────────────────
print("\nJoining coordinates...")
t1 = reg.merge(by_codmod, on="k_codmod", how="left")
t1["coord_tier"] = np.where(t1["nlat_ie"].notna(), "codmod", pd.NA)

miss = t1["nlat_ie"].isna()
t2 = (t1.loc[miss].drop(columns=["nlat_ie", "nlong_ie"])
        .merge(by_codlocal, on="k_codlocal", how="left"))
t2.index = t1.index[miss]
t1.loc[miss, ["nlat_ie", "nlong_ie"]] = t2[["nlat_ie", "nlong_ie"]].values
t1.loc[miss & t1["nlat_ie"].notna(), "coord_tier"] = "codlocal"

print(f"  Tier 1 (COD_MOD):  {(t1['coord_tier'] == 'codmod').sum()}")
print(f"  Tier 2 (CODLOCAL): {(t1['coord_tier'] == 'codlocal').sum()}")
print(f"  No coordinate (dropped): {t1['nlat_ie'].isna().sum()}")

df = t1[t1["nlat_ie"].notna()].copy()
df["latitude"]  = pd.to_numeric(df["nlat_ie"])
df["longitude"] = pd.to_numeric(df["nlong_ie"])
df["coordinate_precision"] = np.where(
    (n_decimals(df["nlat_ie"]) >= 4) & (n_decimals(df["nlong_ie"]) >= 4),
    "exact", "approximate",
)

# ── 4. Admin boundaries ──────────────────────────────────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326"
)
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])

outside = gdf["adm1"].isna()
print(f"  Outside ADM1 (dropped): {outside.sum()}")
gdf = gdf[~outside].copy()

# ── 5. Build output ──────────────────────────────────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame(index=gdf.index)
out["source_id"]             = gdf["COD_MOD"].str.strip()      # verbatim
out["country"]               = ISO3
out["school_name"]           = gdf["CEN_EDU"].str.strip()
out["school_name_romanized"] = pd.NA
out["isced_level"]           = gdf["NIV_MOD"].map(ISCED_MAP)
out["school_type"]           = gdf["D_NIV_MOD"].str.strip()
out["sector"]                = "public"
out["adm0"]                  = "Peru"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = gdf["DAREACENSO"].map(URBAN_MAP)
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = gdf["coordinate_precision"]
out["status"]                = "open"

# geo_id assigned last, sorted by school name (source_id as tiebreak)
out = out.sort_values(["school_name", "source_id"]).reset_index(drop=True)
out.insert(0, "geo_id", [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(out))])

# ── 6. Validation ────────────────────────────────────────────────────────
print("\n=== PER_geo QA ===")
never_null = ["geo_id", "source_id", "country", "school_name", "isced_level",
              "sector", "adm0", "coordinate_source", "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    print(f"  {'WARNING' if n else 'OK'}: {col} — {n} nulls")

assert out["geo_id"].is_unique, "Duplicate geo_ids"
print(f"  Duplicate source_id: {out['source_id'].duplicated().sum()}")
print(f"  urban_rural unmapped: {out['urban_rural'].isna().sum()}")

print(f"\n  Total schools: {len(out)}")
print(f"  isced_level:\n{out['isced_level'].value_counts().to_string()}")
print(f"  coordinate_precision:\n{out['coordinate_precision'].value_counts().to_string()}")
print(f"  urban_rural:\n{out['urban_rural'].value_counts(dropna=False).to_string()}")
print(f"  adm1 (n = {out['adm1'].nunique()}):\n{out['adm1'].value_counts().to_string()}")
print(f"  adm2 NA: {out['adm2'].isna().sum()}  |  adm3 NA: {out['adm3'].isna().sum()}")

# ── 7. Save ──────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")