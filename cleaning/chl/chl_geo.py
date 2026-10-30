"""
chl_geo.py
----------
Cleans the Chile school directory to produce chl_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    MINEDUC (Ministerio de Educación de Chile) — Directorio Oficial de
    Establecimientos Educacionales 2025 (Centro de Estudios / Datos Abiertos)
    File: 20250926_Directorio_Oficial_EE_2025_20250430_WEB.csv
    Format: CSV (semicolon-delimited, UTF-8 with BOM, comma decimal separator)
    Reference year: 2025 (file dated 2025-04-30)

Scope:
    Public schools only, defined via COD_DEPE2 (dependency):
      1 = Municipal                              → public
      5 = Servicio Local de Educación Pública    → public
    Excluded:
      2 = Particular subvencionado (privately run, voucher funded)
      3 = Particular pagado
      4 = Corporación de administración delegada
    Only schools with at least one ISCED 1–3 level are retained.
    Schools offering only pre-primary, special-education, or adult programmes
    (or with zero enrolment) are dropped (see ISCED mapping).

ISCED mapping (primary method — from 2025 student-level matrícula file):
    Youth/child programmes only (COD_ENSE 110, 310, 410–910), by COD_GRADO with
    at least one enrolled student:
      110 (básica)                grades 1–6 → ISCED 1, grades 7–8 → ISCED 2
      310 and TP/artistic (x10)   grades 1–2 (1º–2º medio) → ISCED 2,
                                  grades 3–4 (3º–4º medio) → ISCED 3
    isced_level is the union of levels with enrolled students (e.g. '1|2').
    Adult (x60/x61/x63), special-education (2xx), and parvularia (10) students
    are ignored for level derivation.
    Fallback — schools with no youth enrolment rows in the matrícula file use
    the directory program codes (ENS_01..ENS_11) mapped as
      110 → 1|2 ; 310 → 2|3 ; 410–910 → 2|3
    Schools with no derivable level under either method are dropped (pre-primary,
    special-ed, adult-only, or zero enrolment).

Admin hierarchy:
    adm1 (region), adm2 (province), adm3 (commune) assigned via spatial join
    to GeoBoundaries. Source COD_REG / COD_PRO / COD_COM are retained only for
    the cross-check printed below, not in the output.

Coordinates:
    LATITUD / LONGITUD in source (WGS84, comma decimals).
    coordinate_source = 'official_emis'
    coordinate_precision = 'exact' if >= EXACT_MIN_DECIMALS decimal places,
                           else 'approximate' (source carries no precision flag
                           and decimal places range from 3 to 8).
    Schools with no coordinate are dropped (same rule as BGD).

Author: HB
Date: 2026-09-24
"""

import os
import sys
import unicodedata

import geopandas as gpd
import pandas as pd

# Allow importing from pipeline/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/CHL/Directorio-Oficial-EE-2025/20250926_Directorio_Oficial_EE_2025_20250430_WEB.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/chl_geo.csv"
MATRICULA_FILE = "/Users/heatherbaier/Documents/research/geo/sources/CHL/Matricula-por-estudiante-2025/20250923_Matrícula_unica_2025_20250430_WEB.CSV"  # student-level, 2025

ISO3 = "CHL"

# ── Settings ──────────────────────────────────────────────────────────────
PUBLIC_DEPE2 = {"1": "Municipal", "5": "Servicio Local de Educación Pública"}
KEEP_CLOSED = True          # keep closed schools in the register (status records it)
EXACT_MIN_DECIMALS = 4      # >= this many decimals → 'exact', else 'approximate'

# Directory ENS code → set of ISCED levels (FALLBACK only, see docstring)
ENS_ISCED = {
    "110": {1, 2},
    "310": {2, 3},
    "410": {2, 3}, "510": {2, 3}, "610": {2, 3}, "710": {2, 3}, "810": {2, 3}, "910": {2, 3},
}

# Matrícula (primary method) — youth programmes and grade → ISCED rules
YOUTH_ENSE = {"110", "310", "410", "510", "610", "710", "810", "910"}
def grade_to_isced(cod_ense: str, grade: int):
    if cod_ense == "110":
        return 1 if 1 <= grade <= 6 else 2 if grade in (7, 8) else None
    # media HC / TP / artistic (grades 1–4 = 1º–4º medio)
    return 2 if grade in (1, 2) else 3 if grade in (3, 4) else None
ENS_COLS = [f"ENS_{i:02d}" for i in range(1, 12)]

STATUS_MAP = {
    "1": "open",               # funcionando
    "2": "closed_temporary",   # en receso
    "3": "closed_permanent",   # cerrada
    "4": "unknown",            # autorizada sin matrícula
}

URBAN_RURAL_MAP = {"0": "urban", "1": "rural"}

# ── Load source data ──────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_csv(SOURCE_FILE, sep=";", encoding="utf-8-sig", dtype=str)
df.columns = df.columns.str.strip()
print(f"  Total rows: {len(df)}")
print(f"  RBD unique: {df['RBD'].is_unique}")
print(f"  COD_DEPE2 value counts:\n{df['COD_DEPE2'].value_counts()}")

# ── Filter: public schools only ───────────────────────────────────────────
df = df[df["COD_DEPE2"].isin(PUBLIC_DEPE2)].copy()
print(f"\n  After filtering to Municipal + SLEP: {len(df)} rows")

if not KEEP_CLOSED:
    df = df[df["ESTADO_ESTAB"] == "1"].copy()
    print(f"  After dropping closed schools: {len(df)} rows")

# ── ISCED level ───────────────────────────────────────────────────────────
# Primary method: grades with enrolled students in the 2025 matrícula file.
print("\nDeriving ISCED levels from matrícula (chunked)...")
rbds = set(df["RBD"].astype(str).str.strip())
pairs = []
for chunk in pd.read_csv(
    MATRICULA_FILE, sep=";", encoding="utf-8-sig", dtype=str,
    usecols=["AGNO", "RBD", "COD_ENSE", "COD_GRADO"], chunksize=500_000,
):
    chunk = chunk.apply(lambda c: c.str.strip())
    chunk = chunk[chunk["RBD"].isin(rbds) & chunk["COD_ENSE"].isin(YOUTH_ENSE)]
    pairs.append(chunk.drop_duplicates(["RBD", "COD_ENSE", "COD_GRADO", "AGNO"]))
mat = pd.concat(pairs).drop_duplicates(["RBD", "COD_ENSE", "COD_GRADO", "AGNO"])
print(f"  Matrícula years present: {sorted(mat['AGNO'].unique())}")
mat["_lvl"] = [
    grade_to_isced(e, int(g)) if g.isdigit() else None
    for e, g in zip(mat["COD_ENSE"], mat["COD_GRADO"])
]
mat = mat.dropna(subset=["_lvl"])
mat_levels = mat.groupby("RBD")["_lvl"].agg(lambda x: "|".join(str(int(l)) for l in sorted(set(x))))

# Fallback: directory program codes
def derive_isced_dir(row):
    levels = set()
    for c in ENS_COLS:
        code = str(row[c]).strip()
        if code in ENS_ISCED:
            levels |= ENS_ISCED[code]
    return "|".join(str(l) for l in sorted(levels)) if levels else pd.NA

df["_rbd_str"] = df["RBD"].astype(str).str.strip()
df["isced_level"] = df["_rbd_str"].map(mat_levels).astype("object")
if len(mat_levels) == 0:
    print("  WARNING: no youth matrícula rows matched — check MATRICULA_FILE")
n_mat = df["isced_level"].notna().sum()
fb = df["isced_level"].isna()
df.loc[fb, "isced_level"] = df[fb].apply(derive_isced_dir, axis=1)
print(f"  Level from matrícula: {n_mat}; fallback to directory codes: "
      f"{df.loc[fb, 'isced_level'].notna().sum()}")

no_level = df["isced_level"].isna()
print(f"\n  Dropping {no_level.sum()} schools with no derivable ISCED 1–3 level "
      f"(pre-primary / special-ed / adult only, or zero enrolment)")
df = df[~no_level].copy()
print(f"  ISCED distribution:\n{df['isced_level'].value_counts()}")

# ── Sort and assign geo_id ────────────────────────────────────────────────
# Assigned before dropping rows without coordinates so IDs stay stable if
# coordinates are recovered later (same approach as BGD).
df["_rbd_int"] = pd.to_numeric(df["RBD"], errors="coerce")
df = df.sort_values("_rbd_int").reset_index(drop=True)
df["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(df))]
print(f"\n  geo_id range: {df['geo_id'].iloc[0]} to {df['geo_id'].iloc[-1]}")

# ── Coordinates ───────────────────────────────────────────────────────────
lat_str = df["LATITUD"].astype(str).str.strip().str.replace(",", ".", regex=False)
lon_str = df["LONGITUD"].astype(str).str.strip().str.replace(",", ".", regex=False)
df["latitude"]  = pd.to_numeric(lat_str, errors="coerce")
df["longitude"] = pd.to_numeric(lon_str, errors="coerce")

# decimal places as reported in the source string
n_dec = lat_str.str.split(".").str[1].str.len().fillna(0)
df["coordinate_precision"] = n_dec.apply(
    lambda n: "exact" if n >= EXACT_MIN_DECIMALS else "approximate"
)
df["coordinate_source"] = "official_emis"

missing = df["latitude"].isna() | df["longitude"].isna()
print(f"\n  Schools with missing coordinates: {missing.sum()}")
print(f"  Missing by status:\n{df.loc[missing, 'ESTADO_ESTAB'].map(STATUS_MAP).value_counts()}")
df = df[~missing].copy()
print(f"  Rows after dropping missing coordinates: {len(df)}")

# ── Bounding box check (flag, do not drop) ────────────────────────────────
# Mainland Chile approx; Rapa Nui, Juan Fernández and Chilean Antarctic
# Territory legitimately fall outside and are listed for review.
oob = df[
    (df["latitude"] < -56.5) | (df["latitude"] > -17.4)
    | (df["longitude"] < -76.0) | (df["longitude"] > -66.3)
]
print(f"\n  Outside mainland bounding box (review, not dropped): {len(oob)}")
if len(oob) > 0:
    print(oob[["geo_id", "RBD", "NOM_RBD", "NOM_COM_RBD", "latitude", "longitude"]].to_string())

# ── Spatial join admin boundaries from GeoBoundaries ─────────────────────
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326",
)
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# ── Cross-check adm3 vs source commune name (informational) ──────────────
def _norm(s):
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())

if "adm3" in gdf.columns and gdf["adm3"].notna().any():
    both = gdf["adm3"].notna()
    match = gdf.loc[both, "adm3"].map(_norm) == gdf.loc[both, "NOM_COM_RBD"].map(_norm)
    print(f"\n  adm3 (gB) vs source commune name exact-match rate: {match.mean():.1%} "
          f"({match.sum()}/{both.sum()})")

# ── Build output dataframe ────────────────────────────────────────────────
print("\nBuilding output dataframe...")
out = pd.DataFrame()

out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["RBD"].astype(str).str.strip()
out["country"]               = ISO3
out["school_name"]           = gdf["NOM_RBD"].astype(str).str.strip()
out["school_name_romanized"] = pd.NA              # Latin script
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["COD_DEPE2"].map(PUBLIC_DEPE2)
out["sector"]                = "public"
out["adm0"]                  = "Chile"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = gdf["RURAL_RBD"].astype(str).str.strip().map(URBAN_RURAL_MAP)
out["ghsl_smod_code"]        = pd.NA              # applied by add_ghsl.py
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = gdf["coordinate_source"]
out["coordinate_precision"]  = gdf["coordinate_precision"]
out["status"]                = gdf["ESTADO_ESTAB"].map(STATUS_MAP)

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].is_unique, "ERROR: Duplicate geo_ids found"
assert out["source_id"].is_unique, "ERROR: Duplicate source_ids found"
assert out["geo_id"].notna().all(), "ERROR: Null geo_ids found"
assert out["country"].eq(ISO3).all(), "ERROR: Country code mismatch"
assert out["sector"].eq("public").all(), "ERROR: Non-public schools found"
assert out["latitude"].notna().all(), "ERROR: Null latitudes"
assert out["longitude"].notna().all(), "ERROR: Null longitudes"
assert out["isced_level"].notna().all(), "ERROR: Null isced_level"
assert out["status"].notna().all(), "ERROR: Null status"
assert out["coordinate_source"].notna().all(), "ERROR: Null coordinate_source"
assert out["coordinate_precision"].notna().all(), "ERROR: Null coordinate_precision"

print(f"\n  Total schools in output: {len(out)}")
print(f"  ISCED level distribution:\n{out['isced_level'].value_counts()}")
print(f"  Status distribution:\n{out['status'].value_counts()}")
print(f"  Coordinate precision distribution:\n{out['coordinate_precision'].value_counts()}")
print(f"  ADM1 distribution:\n{out['adm1'].value_counts(dropna=False)}")
print(f"  Unmatched adm2: {out['adm2'].isna().sum()}, adm3: {out['adm3'].isna().sum()}")
print(f"  Urban/rural distribution:\n{out['urban_rural'].value_counts(dropna=False)}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")