"""
mex_resources.py
-----------------
Cleans the INIFED school infrastructure census files to produce
mex_resources.csv conforming to the GEO Dataset canonical schema v1.0.

Source:
    Instituto Nacional de la Infraestructura Fisica Educativa (INIFED)
    school infrastructure census. Two files provided:
      - inifed_2013-2018_csv.csv
      - inifed_2020-2022_csv.csv
    (no 2019 file — gap between sources)
    Format: CSV, one row per school (cct) per year.

Join to geo:
    This file has no status/control/level filter columns of its own — scope
    (public, active, ISCED 1-3) is enforced entirely by inner-joining `cct`
    against `source_id` in MEX_geo.csv, which is already filtered. Per the
    standing project rule, schools with no match in the geo table are
    excluded from this table rather than given a null row.

Binary field encoding:
    Most categorical columns in this source follow a CON_x / SIN_x
    ("with x" / "without x") convention. A generic parser handles those.
    A few columns (alimentacion_agua, condicion_fis_wc) are multi-level
    categorical, not binary — those are mapped through explicit dicts below.

    IMPORTANT: the explicit dicts (WATER_SOURCE_MAP, CONDITION_MAP) were
    built from a 5-row sample and almost certainly do NOT cover every
    category value in the full file. Unmapped values become NA and are
    printed in the QA section at the end of the run — extend the dicts
    with whatever shows up there before trusting the output.

Known gaps (no schema field, or no source field):
    - No library, internet_type, or water_improved distinction available.
    - handwashing_basic is mapped from `bebederos` (drinking fountains) as
      a PROVISIONAL proxy — this is not verified to satisfy the JMP
      "handwashing with soap and water" definition. Comment out that line
      below if a real handwashing/lavamanos field turns up elsewhere.
    - `descarga_agua_residual`, `telefonia_fija`, `nivel_accesibilidad`,
      furniture counts, classroom/building counts, and civil-protection
      plan status have no home in the canonical schema and are dropped.
      Consider a supplementary file per the schema's "no extra columns"
      rule if these matter later.

Author: HB
Date: 2026-09-21
"""

import os
import sys
import glob
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
SRC_DIR   = "/Users/heatherbaier/Documents/research/geo/sources/MEX"
GEO_FILE  = "/Users/heatherbaier/Documents/research/geo/db/geo/mex_geo.csv"
OUT_FILE  = "/Users/heatherbaier/Documents/research/geo/db/resources/mex_resources.csv"

INIFED_FILES = [
    os.path.join(SRC_DIR, "inifed_2013-2018_csv.csv"),
    os.path.join(SRC_DIR, "inifed_2020-2022_csv.csv"),
]

ISO3 = "MEX"

# ── Columns actually used ───────────────────────────────────────────────
USECOLS = [
    "anio", "cct",
    "alimentacion_agua", "bebederos", "con_luz", "internet",
    "wc_alumnos", "wc_alumnas", "wc_docentes", "wc_discapacitados",
    "condicion_fis_wc", "computadora", "laptop",
]

# ── Generic CON_x / SIN_x binary parser ───────────────────────────────────
def parse_con_sin(series: pd.Series, colname: str) -> pd.Series:
    """
    Map values like 'CON LUZ' -> 1, 'SIN LUZ' -> 0. Anything not starting
    with CON/SIN (after normalising whitespace/case) becomes NA and is
    reported by the caller.
    """
    s = series.str.strip().str.upper()
    out = pd.Series(pd.NA, index=s.index, dtype="object")
    out = out.mask(s.str.startswith("CON"), 1)
    out = out.mask(s.str.startswith("SIN"), 0)

    unmapped = s[out.isna() & s.notna()].unique()
    if len(unmapped) > 0:
        print(f"    WARNING: {colname} has {len(unmapped)} unrecognized value(s) -> NA: {list(unmapped)[:10]}")

    return pd.to_numeric(out, errors="coerce")


# ── Explicit categorical maps ─────────────────────────────────────────────
# PROVISIONAL — built from a small sample. Extend with real category lists
# from the full file. Values not in the dict become NA (never silently 0).
WATER_SOURCE_MAP = {
    "RED MUNICIPAL": 1,
    # add e.g. "POZO": ?, "PIPA": ?, "RIO ARROYO O LAGO": 0, "SIN AGUA": 0, ...
}

# JMP 'basic' sanitation requires a usable facility. BUENAS/REGULARES are
# treated as usable here — this threshold is a judgment call, confirm it.
USABLE_WC_CONDITIONS = {"BUENAS", "REGULARES"}


def map_categorical(series: pd.Series, mapping: dict, colname: str) -> pd.Series:
    s = series.str.strip().str.upper()
    out = s.map(mapping)
    unmapped = s[out.isna() & s.notna()].unique()
    if len(unmapped) > 0:
        print(f"    WARNING: {colname} has {len(unmapped)} unmapped value(s) -> NA: {list(unmapped)[:10]}")
    return out


# ── Mojibake fix (Mac Roman misread as UTF-8, seen throughout MEX sources) ─
def fix_mojibake(series: pd.Series) -> pd.Series:
    def _fix(x):
        if not isinstance(x, str) or "\ufffd" not in x and "√" not in x:
            return x
        try:
            return x.encode("mac_roman").decode("utf-8")
        except Exception:
            return x
    return series.map(_fix)


# ── Per-file processing ───────────────────────────────────────────────────
def process_file(path: str) -> pd.DataFrame:
    name = os.path.basename(path)
    if not os.path.exists(path):
        print(f"  SKIPPING (not found): {name}")
        return pd.DataFrame(columns=USECOLS)

    try:
        df = pd.read_csv(path, dtype=str, usecols=USECOLS, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, usecols=USECOLS, encoding="latin-1")
        print(f"  NOTE: {name} is not UTF-8 — read as latin-1")

    for c in ["alimentacion_agua", "bebederos", "con_luz", "internet", "condicion_fis_wc"]:
        df[c] = fix_mojibake(df[c].str.strip())

    print(f"  {name}: {len(df)} rows")
    df["__source_file"] = name
    return df


# ══════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════

print(f"Reading {len(INIFED_FILES)} INIFED file(s)...")
frames = [process_file(f) for f in INIFED_FILES]
raw = pd.concat(frames, ignore_index=True)
print(f"\nCombined raw rows: {len(raw)}")

dup = raw.duplicated(subset=["cct", "anio"]).sum()
if dup > 0:
    # INIFED_FILES lists 2013-2018 before 2020-2022, and keep="last" below
    # keeps the later file's row on a (cct, anio) collision — i.e. the more
    # recent vintage wins. Flip INIFED_FILES order (or keep="first") if that's
    # not the right call for a given overlap.
    print(f"  NOTE: {dup} (cct, anio) duplicates across the two files — keeping the more recent vintage")
raw = raw.drop_duplicates(subset=["cct", "anio"], keep="last")

# ── Build resources fields ────────────────────────────────────────────────
print("\nMapping fields...")
out = pd.DataFrame()
out["source_id"] = raw["cct"]
out["year"] = pd.to_numeric(raw["anio"], errors="coerce").astype("Int64")

out["water_basic"] = map_categorical(raw["alimentacion_agua"], WATER_SOURCE_MAP, "alimentacion_agua")
out["water_improved"] = pd.NA  # source doesn't distinguish service levels beyond basic/none

# out["handwashing_basic"] = parse_con_sin(raw["bebederos"], "bebederos")  # PROVISIONAL — see docstring
out["handwashing_basic"] = pd.NA

wc_alumnos = pd.to_numeric(raw["wc_alumnos"], errors="coerce")
wc_alumnas = pd.to_numeric(raw["wc_alumnas"], errors="coerce")
wc_docentes = pd.to_numeric(raw["wc_docentes"], errors="coerce")
wc_total = wc_alumnos.fillna(0) + wc_alumnas.fillna(0) + wc_docentes.fillna(0)
condition_ok = raw["condicion_fis_wc"].str.strip().str.upper().isin(USABLE_WC_CONDITIONS)
out["sanitation_basic"] = np.where(
    raw["condicion_fis_wc"].isna(), pd.NA,
    ((wc_total > 0) & condition_ok).astype("Int64")
)
out["sanitation_sex_separated"] = ((wc_alumnos > 0) & (wc_alumnas > 0)).astype("Int64")

out["electricity"] = parse_con_sin(raw["con_luz"], "con_luz")
out["internet"] = parse_con_sin(raw["internet"], "internet")
out["internet_type"] = pd.NA  # binary presence only in this source

computadora = pd.to_numeric(raw["computadora"], errors="coerce").fillna(0)
laptop = pd.to_numeric(raw["laptop"], errors="coerce").fillna(0)
out["computers"] = ((computadora + laptop) > 0).astype("Int64")

out["library"] = pd.NA  # not collected in this source

# ── Join to geo table (enforces public/active/ISCED 1-3 scope) ───────────
print(f"\nJoining to {GEO_FILE} on source_id...")
if not os.path.exists(GEO_FILE):
    raise FileNotFoundError(f"{GEO_FILE} not found — run mex_geo.py first, resources depends on it")

geo = pd.read_csv(GEO_FILE, dtype=str, usecols=["geo_id", "source_id"])
before = len(out)
out = out.merge(geo, on="source_id", how="inner")
print(f"  {before} rows -> {len(out)} matched to a geo_id ({before - len(out)} dropped, no match in geo table)")

# ── Assemble in schema column order ───────────────────────────────────────
RESOURCES_COLS = [
    "geo_id", "year",
    "water_basic", "water_improved",
    "sanitation_basic", "sanitation_sex_separated", "handwashing_basic",
    "electricity", "internet", "internet_type",
    "computers", "library",
]
resources = out[RESOURCES_COLS].copy()

# ── QA ──────────────────────────────────────────────────────────────────
print("\n=== MEX_resources QA ===")
print(f"Total rows: {len(resources)}")
print(f"Distinct schools: {resources['geo_id'].nunique()}")
print(f"Years covered: {sorted(resources['year'].dropna().unique().tolist())}")
print()

never_null = ["geo_id", "year"]
for col in never_null:
    n = resources[col].isna().sum()
    print(("  WARNING: " if n else "  OK: ") + f"{col} — {n} nulls")

print()
for col in ["water_basic", "sanitation_basic", "sanitation_sex_separated",
            "handwashing_basic", "electricity", "internet", "computers"]:
    print(f"{col} value counts (incl. NA):")
    print(resources[col].value_counts(dropna=False).to_string())
    print()

dup_geo_year = resources.duplicated(subset=["geo_id", "year"]).sum()
print(f"Duplicate (geo_id, year) pairs: {dup_geo_year}")

# ── Save ────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
resources.to_csv(OUT_FILE, index=False)
print(f"\nSaved: {OUT_FILE}")