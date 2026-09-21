"""
mex_geo.py
----------
Cleans the SEP Catalogo de Centros de Trabajo (CCT) state files to produce
mex_geo.csv conforming to the GEO Dataset canonical schema v1.0.

Source:
    Secretaria de Educacion Publica (SEP) — Catalogo de Centros de Trabajo
    URL: https://www.datos.gob.mx/dataset/catalogo_centros_trabajo_sep
    Format: CSV, one file per entidad federativa (catalogo_centro_trabajo_01 ... _32)
    Unit: one row per CCT (clave de centro de trabajo). A CCT is one school
    administrative unit, so it maps to one GEO row. Several CCTs can share a
    building (inmueble_cv_inmueble), typically one per shift, and are NOT deduplicated.

Scope:
    Public schools only, ISCED 1-3, currently active:
      - c_tipo IN ['ESCUELA', 'PLANTEL (MEDIA SUPERIOR)']
      - c_estatus = 'ACTIVO'
      - sostenimiento_c_control = 'PÚBLICO'
      - tiponivelsub_c_servicion2 IN ['PRIMARIA', 'SECUNDARIA', 'MEDIA SUPERIOR']
    Excluded:
      - Non-school CCTs (supervision zones, libraries, admin offices, CONAFE initial
        education centres, teacher centres, etc.)
      - INACTIVO CCTs (the catalog keeps historical CCTs; the motive field does not
        distinguish temporary from permanent closure, so none are kept)
      - Private schools
      - Preescolar / Inicial (ISCED 0, excluded project-wide), Superior,
        Formacion para el trabajo, CAM (special education), other

    Note: CONAFE community courses (K prefix) are classified PÚBLICO in the source
    and are retained as sector = 'public'.

ISCED mapping:
    PRIMARIA       → 1
    SECUNDARIA     → 2   (general, tecnica, telesecundaria, comunitaria)
    MEDIA SUPERIOR → 3   (bachillerato general, tecnologico, profesional tecnico)
    Planteles with c_tipo = 'PLANTEL (MEDIA SUPERIOR)' (CCT prefix MMS) carry no
    tiponivelsub fields at all in the source, so c_tipo itself is used as the
    level marker → 3.

Admin hierarchy:
    adm1+ assigned via spatial join to GeoBoundaries (standing project rule —
    source INEGI names/codes are NOT used). Schools that fall outside ADM1
    boundaries are dropped, not nulled.

Coordinates:
    latitud/longitud from the catalog, already decimal degrees (WGS84).
    Points shared by several distinct buildings (inmuebles) are locality-level
    placeholders (e.g. ~100 buildings stacked on one point in the city centre).
    Those get coordinate_source = 'admin_centroid', coordinate_precision = 'admin_centroid'.
    All others get 'official_emis', with precision 'approximate' if the source
    coordinate has <= 3 decimals and 'exact' otherwise.

Privacy:
    contacto_* columns (CURP, RFC, names, emails, phones) are never loaded.

Author: HB
Date: 2026-09-21
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
import geopandas as gpd

# Allow importing from pipeline/
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────
SRC_DIR     = "/Users/heatherbaier/Documents/research/geo/sources/MEX"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/mex_geo.csv"

ISO3 = "MEX"

# ── Constants ─────────────────────────────────────────────────────────────
# Only the columns we need are read (keeps the redacted contacto_* block out entirely)
USECOLS = [
    "cv_cct",
    "c_nombre",
    "c_tipo",
    "c_estatus",
    "inmueble_cv_inmueble",
    "latitud",
    "longitud",
    "sostenimiento_c_control",
    "tiponivelsub_c_servicion2",
    "tiponivelsub_c_servicion3",
]

SCHOOL_TYPES = ["ESCUELA", "PLANTEL (MEDIA SUPERIOR)"]
PLANTEL_MS   = "PLANTEL (MEDIA SUPERIOR)"

LEVEL_TO_ISCED = {
    "PRIMARIA":       "1",
    "SECUNDARIA":     "2",
    "MEDIA SUPERIOR": "3",
}

# Planteles that are offices or support centres attached to another school, not
# schools in their own right (printed at run time so the list can be reviewed)
NON_SCHOOL_PLANTEL_PATTERN = r"^(?:OFICINA|CENTRO DE ATENCI[OÓ]N PARA ESTUDIANTES)"

# Placeholder detection — a coordinate shared by this many distinct buildings
# (inmueble ids) or more is treated as a locality-level placeholder
PLACEHOLDER_MIN_INMUEBLES = 3
LOW_PRECISION_DECIMALS    = 3


# ── Per-file processing ───────────────────────────────────────────────────
def process_file(path: str) -> pd.DataFrame:
    """
    Load one state catalog file, flag coordinate quality, filter to public
    active ISCED 1-3 schools, and return a partial GEO frame (no adm, no geo_id).
    """
    name = os.path.basename(path)

    try:
        df = pd.read_csv(path, dtype=str, usecols=USECOLS, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, usecols=USECOLS, encoding="latin-1")
        print(f"  NOTE: {name} is not UTF-8 — read as latin-1, check accents")

    for c in USECOLS:
        df[c] = df[c].str.strip()

    n_raw = len(df)

    # ── Coordinate quality flags (computed on ALL rows in the file, before filtering) ──
    # Placeholders are mostly inactive CCTs and admin offices, so they must be
    # counted before those are filtered out.
    lat_s = df["latitud"]
    lon_s = df["longitud"]
    df["latitude"]  = pd.to_numeric(lat_s, errors="coerce")
    df["longitude"] = pd.to_numeric(lon_s, errors="coerce")

    df["coord_decimals"] = lat_s.str.split(".").str[1].str.len().fillna(0)
    point_key = lat_s + "|" + lon_s
    df["n_inm_at_point"] = df.groupby(point_key)["inmueble_cv_inmueble"].transform("nunique")

    # ── Filters ───────────────────────────────────────────────────────────
    steps = [("raw rows", n_raw)]

    df = df[df["c_tipo"].isin(SCHOOL_TYPES)]
    steps.append(("school/plantel", len(df)))

    df = df[df["c_estatus"] == "ACTIVO"]
    steps.append(("active", len(df)))

    df = df[df["sostenimiento_c_control"] == "PÚBLICO"]
    steps.append(("public", len(df)))

    # ISCED level
    isced = df["tiponivelsub_c_servicion2"].map(LEVEL_TO_ISCED)
    is_plantel = df["c_tipo"] == PLANTEL_MS
    isced = isced.mask(is_plantel & isced.isna(), "3")
    df = df.assign(isced_level=isced)
    df = df[df["isced_level"].notna()]
    steps.append(("ISCED 1-3", len(df)))

    # Office / support-centre planteles
    is_office = (df["c_tipo"] == PLANTEL_MS) & df["c_nombre"].str.contains(
        NON_SCHOOL_PLANTEL_PATTERN, na=False
    )
    if is_office.any():
        print(f"  Excluding {is_office.sum()} non-school plantel(s)")
        for nm in df.loc[is_office, "c_nombre"]:
            print(f"    - {nm}")
    df = df[~is_office]
    steps.append(("not office", len(df)))

    # Coordinates present
    df = df[df["latitude"].notna() & df["longitude"].notna()]
    steps.append(("has coords", len(df)))

    print(f"  {name}: " + " → ".join(f"{label} {n}" for label, n in steps))

    # ── Build partial output ──────────────────────────────────────────────
    out = pd.DataFrame(index=df.index)
    out["source_id"]   = df["cv_cct"]
    out["school_name"] = df["c_nombre"]
    out["isced_level"] = df["isced_level"]

    # National school type, retained in source terminology (GENERAL, COMUNITARIO,
    # TELESECUNDARIA, TÉCNICA, BACHILLERATO GENERAL ...). MMS planteles have no
    # subtype in the source, so fall back to c_tipo.
    out["school_type"] = df["tiponivelsub_c_servicion3"].fillna(df["c_tipo"])

    out["latitude"]  = df["latitude"]
    out["longitude"] = df["longitude"]

    stacked  = df["n_inm_at_point"] >= PLACEHOLDER_MIN_INMUEBLES
    low_prec = df["coord_decimals"] <= LOW_PRECISION_DECIMALS
    out["coordinate_source"] = np.where(stacked, "admin_centroid", "official_emis")
    out["coordinate_precision"] = np.where(
        stacked, "admin_centroid", np.where(low_prec, "approximate", "exact")
    )

    return out.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════
# RUN MODE
# ══════════════════════════════════════════════════════════════════════════

# ── TEST MODE: one file only ──────────────────────────────────────────────
# (comment this block out and uncomment the FULL RUN block below to run all states)
# TEST_FILE = os.path.join(SRC_DIR, "catalogo_centro_trabajo_03_csv.csv")
# print(f"TEST MODE — processing single file: {TEST_FILE}")
# frames = [process_file(TEST_FILE)]

# ── FULL RUN: loop over all state files ───────────────────────────────────
files = sorted(glob.glob(os.path.join(SRC_DIR, "catalogo_centro_trabajo_*.csv")))
print(f"Found {len(files)} catalog files")
if len(files) != 32:
    print(f"  WARNING: expected 32 state files, found {len(files)}")

frames = []
for f in files:
    frames.append(process_file(f))


# ── Combine ───────────────────────────────────────────────────────────────
print("\nCombining...")
geo = pd.concat(frames, ignore_index=True)
print(f"  Total rows after filtering: {len(geo)}")

# Duplicate source_ids are retained verbatim (standing rule) — just report them
n_dup_src = geo["source_id"].duplicated().sum()
print(f"  Duplicate source_ids (retained): {n_dup_src}")

# ── Spatial join admin boundaries from GeoBoundaries ─────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = gpd.GeoDataFrame(
    geo,
    geometry=gpd.points_from_xy(geo["longitude"], geo["latitude"]),
    crs="EPSG:4326",
)
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3, 4])

# ── Coordinate sanity check: drop schools outside ADM1 boundaries ─────────
if gdf["adm1"].isna().all():
    raise RuntimeError(
        "ADM1 is NA for every school — GeoBoundaries ADM1 fetch probably failed. "
        "Aborting rather than dropping the whole dataset."
    )

outside = gdf["adm1"].isna()
if outside.any():
    print(f"\n  Dropping {outside.sum()} schools outside ADM1 boundaries:")
    print(gdf.loc[outside, ["source_id", "school_name", "latitude", "longitude"]].head(20).to_string())
gdf = gdf[~outside].copy()

# ── geo_id ────────────────────────────────────────────────────────────────
# Assigned after all cleaning, sorted alphabetically by school name.
# source_id breaks ties so assignment is reproducible across re-runs.
gdf = gdf.sort_values(["school_name", "source_id"]).reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]

# ── Remaining schema columns ──────────────────────────────────────────────
gdf["country"]               = ISO3
gdf["school_name_romanized"] = pd.NA      # Latin script
gdf["sector"]                = "public"   # filtered on sostenimiento_c_control = PÚBLICO
gdf["adm0"]                  = "Mexico"

# No urban/rural field in the catalog — NA (GHSL applied downstream by add_ghsl.py)
gdf["urban_rural"]     = pd.NA
gdf["ghsl_smod_code"]  = pd.NA
gdf["ghsl_urban_rural"] = pd.NA

# Filtered to c_estatus = ACTIVO; inactive CCTs excluded
gdf["status"] = "open"

# ── Assemble output in schema column order ────────────────────────────────
GEO_COLS = [
    "geo_id",
    "source_id",
    "country",
    "school_name",
    "school_name_romanized",
    "isced_level",
    "school_type",
    "sector",
    "adm0",
    "adm1",
    "adm2",
    "adm3",
    "urban_rural",
    "ghsl_smod_code",
    "ghsl_urban_rural",
    "latitude",
    "longitude",
    "coordinate_source",
    "coordinate_precision",
    "status",
]

out = pd.DataFrame(gdf[GEO_COLS]).copy()

# ── QA checks ────────────────────────────────────────────────────────────
print("\n=== MEX_geo QA ===")
print(f"Total rows: {len(out)}")
print()

never_null = ["geo_id", "source_id", "country", "school_name",
              "isced_level", "sector", "adm0", "coordinate_source",
              "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    if n > 0:
        print(f"  WARNING: {col} has {n} null values — schema violation")
    else:
        print(f"  OK: {col} — no nulls")

print()
print("isced_level distribution:")
print(out["isced_level"].value_counts())
print()
print("school_type distribution:")
print(out["school_type"].value_counts(dropna=False))
print()
print("coordinate_source distribution:")
print(out["coordinate_source"].value_counts())
print()
print("coordinate_precision distribution:")
print(out["coordinate_precision"].value_counts())
print()
print("adm1 distribution:")
print(out["adm1"].value_counts())
print()
print(f"adm2 NA: {out['adm2'].isna().sum()} | adm3 NA: {out['adm3'].isna().sum()}")
print()
print(f"Missing latitude:  {out['latitude'].isna().sum()}")
print(f"Missing longitude: {out['longitude'].isna().sum()}")
print()
print(f"Duplicate geo_ids: {out['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids (retained verbatim): {out['source_id'].duplicated().sum()}")

# ── Save ─────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print()
print(f"Saved: {OUTPUT_FILE}")
