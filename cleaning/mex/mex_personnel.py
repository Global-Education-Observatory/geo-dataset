"""
mex_personnel.py
-----------------
Cleans the SEP Formato 911 school-statistics files (basica + media superior)
to produce mex_personnel.csv conforming to the GEO Dataset canonical schema v1.0.

Sources:
    - BASICA_{YYYY}-{YYYY}.csv     (preescolar/primaria/secundaria; one file per
      cycle, e.g. BASICA_2019-2020.csv). Key column: clavecct — this IS the CCT
      and matches source_id in MEX_geo.csv directly.
    - media_superior_{YYYY}-{YYYY}.csv (bachillerato). Key columns: plantel
      (the MMS-prefixed CCT, matches geo's source_id) and escuela (a FINER
      sub-code, one per turno/track within the plantel — NOT the geo join key).
      Rows are grouped up to plantel level before use.

Both file families are read with glob patterns rather than hardcoded years, so
this picks up whatever cycles exist in SRC_DIR without editing the script.

Join to geo:
    Same approach as mex_resources.py — no re-filtering by control/status here.
    Inner-joining source_id against MEX_geo.csv (already restricted to public,
    active, ISCED 1-3) does the scope filtering for free: private schools and
    ISCED 0 (preescolar/inicial) rows have no match and are dropped, with a
    count printed.

Year convention:
    BASICA: year comes from the `periodo` column (e.g. 'I2019' -> 2019),
    which is the UIS beginning-year convention already. Cross-checked against
    the year parsed from the filename; mismatches are printed, not silently
    resolved.
    media_superior: this file has NO year/periodo column at all — year is
    parsed from the filename only (first YYYY in media_superior_YYYY-YYYY.csv).

Field mapping — see chat discussion for the full reasoning:
    BASICA            -> enrollment_total = insc_t, _male = hom_t, _female = muj_t
                          teachers_total   = tot_doc   (classroom teachers only —
                             see TEACHERS_TOTAL_COL_BASICA below for the
                             tot_doc_p alternative, which additionally folds in
                             directors-with-group, subdirectors, specialists,
                             and tutors)
                          classrooms_total = aula_aexi (UNVERIFIED — best guess
                             at "aulas existentes"; aula_u_t/aula_a_t looked
                             narrower, "in use" / "under construction")
    media_superior    -> enrollment_total = alumnos, _male = hombres, _female = mujeres
                          teachers_total   = docentes (only one teacher role in
                             this file, no ambiguity)
                          classrooms_total = NA (no classroom column exists)

    teachers_qualified is NA for both — not collected in either source.
    pupil_teacher_ratio is computed per schema rule, never sourced directly.

Author: HB
Date: 2026-09-21
"""

import os
import re
import glob
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
SRC_DIR  = "/Users/heatherbaier/Documents/research/geo/sources/MEX"
GEO_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/mex_geo.csv"
OUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/personnel/mex_personnel.csv"

ISO3 = "MEX"

# ── Field-selection decisions (flip these if you decide differently) ──────
# tot_doc = classroom teachers only. tot_doc_p is broader (also director-with-
# group, subdirector, specialists, tutors) — closer to "everyone who teaches"
# but not the strict UIS definition. Confirm against SEP's glosario.
TEACHERS_TOTAL_COL_BASICA = "tot_doc"
CLASSROOMS_TOTAL_COL_BASICA = "aula_aexi"  # UNVERIFIED, see docstring

# ── Column sets actually used ──────────────────────────────────────────────
BASICA_COLS = [
    "clavecct", "periodo", "control",
    "insc_t", "hom_t", "muj_t",
    "tot_doc_p", "tot_doc", "docente_h", "docente_m",
    "aula_aexi", "aula_u_t", "aula_a_t",
]

MS_COLS = [
    "plantel", "escuela", "control",
    "alumnos", "hombres", "mujeres",
    "docentes", "docentes_h", "docentes_m",
]


# ── Mojibake fix (Mac Roman misread as UTF-8) — verify this is still needed
# once run against the real files; the xlsx samples this was built from had
# the corruption baked into the cell values themselves, not just the CSV read.
def fix_mojibake(series: pd.Series) -> pd.Series:
    def _fix(x):
        if not isinstance(x, str) or "√" not in x:
            return x
        try:
            return x.encode("mac_roman").decode("utf-8")
        except Exception:
            return x
    return series.map(_fix)


def year_from_filename(path: str) -> int:
    m = re.search(r"(\d{4})-\d{4}", os.path.basename(path))
    if not m:
        raise ValueError(f"Could not parse a YYYY-YYYY cycle out of filename: {path}")
    return int(m.group(1))


# ── BASICA ───────────────────────────────────────────────────────────────
def process_basica_file(path: str) -> pd.DataFrame:
    name = os.path.basename(path)
    try:
        df = pd.read_csv(path, dtype=str, usecols=BASICA_COLS, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, usecols=BASICA_COLS, encoding="latin-1")
        print(f"  NOTE: {name} is not UTF-8 — read as latin-1")

    df["control"] = fix_mojibake(df["control"].str.strip())

    # Year: prefer periodo (e.g. 'I2019' -> 2019), cross-check filename
    file_year = year_from_filename(path)
    periodo_year = pd.to_numeric(df["periodo"].str.extract(r"(\d{4})")[0], errors="coerce")
    mismatches = (periodo_year.notna() & (periodo_year != file_year)).sum()
    if mismatches > 0:
        print(f"  WARNING: {name} — {mismatches} row(s) where periodo year != filename year")
    year = periodo_year.fillna(file_year).astype(int)

    out = pd.DataFrame()
    out["source_id"] = df["clavecct"]
    out["year"] = year
    out["enrollment_total"]  = pd.to_numeric(df["insc_t"], errors="coerce")
    out["enrollment_male"]   = pd.to_numeric(df["hom_t"], errors="coerce")
    out["enrollment_female"] = pd.to_numeric(df["muj_t"], errors="coerce")
    out["teachers_total"]  = pd.to_numeric(df[TEACHERS_TOTAL_COL_BASICA], errors="coerce")
    out["teachers_male"]   = pd.to_numeric(df["docente_h"], errors="coerce")
    out["teachers_female"] = pd.to_numeric(df["docente_m"], errors="coerce")
    out["classrooms_total"] = pd.to_numeric(df[CLASSROOMS_TOTAL_COL_BASICA], errors="coerce")

    print(f"  {name}: {len(out)} rows, year(s) {sorted(year.unique().tolist())}")
    return out


# ── MEDIA SUPERIOR ─────────────────────────────────────────────────────────
def process_media_superior_file(path: str) -> pd.DataFrame:
    name = os.path.basename(path)
    try:
        df = pd.read_csv(path, dtype=str, usecols=MS_COLS, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, usecols=MS_COLS, encoding="latin-1")
        print(f"  NOTE: {name} is not UTF-8 — read as latin-1")

    df["control"] = fix_mojibake(df["control"].str.strip())

    for c in ["alumnos", "hombres", "mujeres", "docentes", "docentes_h", "docentes_m"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    n_escuela = len(df)
    n_plantel = df["plantel"].nunique()
    print(f"  {name}: {n_escuela} escuela rows -> {n_plantel} distinct plantel(es); "
          f"summing escuela rows up to plantel level")

    # `escuela` splits (turno/track) within one `plantel` are summed — the geo
    # table has one row per plantel (MMS CCT), not per escuela.
    grouped = df.groupby("plantel", as_index=False)[
        ["alumnos", "hombres", "mujeres", "docentes", "docentes_h", "docentes_m"]
    ].sum()

    file_year = year_from_filename(path)  # no periodo column in this source

    out = pd.DataFrame()
    out["source_id"] = grouped["plantel"]
    out["year"] = file_year
    out["enrollment_total"]  = grouped["alumnos"]
    out["enrollment_male"]   = grouped["hombres"]
    out["enrollment_female"] = grouped["mujeres"]
    out["teachers_total"]  = grouped["docentes"]
    out["teachers_male"]   = grouped["docentes_h"]
    out["teachers_female"] = grouped["docentes_m"]
    out["classrooms_total"] = pd.NA  # not collected in this source

    return out


# ══════════════════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════════════════

basica_files = sorted(glob.glob(os.path.join(SRC_DIR, "BASICA_*.csv")))
ms_files     = sorted(glob.glob(os.path.join(SRC_DIR, "media_superior_*.csv")))

print(f"Found {len(basica_files)} BASICA file(s), {len(ms_files)} media_superior file(s)")

frames = []

print("\nProcessing BASICA files...")
for f in basica_files:
    frames.append(process_basica_file(f))

print("\nProcessing media_superior files...")
for f in ms_files:
    frames.append(process_media_superior_file(f))

if not frames:
    raise FileNotFoundError(f"No BASICA_*.csv or media_superior_*.csv files found in {SRC_DIR}")

personnel = pd.concat(frames, ignore_index=True)
print(f"\nCombined rows before geo join: {len(personnel)}")

# ── Join to geo table (enforces public/active/ISCED 1-3 scope) ───────────
print(f"\nJoining to {GEO_FILE} on source_id...")
if not os.path.exists(GEO_FILE):
    raise FileNotFoundError(f"{GEO_FILE} not found — run mex_geo.py first, personnel depends on it")

geo = pd.read_csv(GEO_FILE, dtype=str, usecols=["geo_id", "source_id"])
before = len(personnel)
personnel = personnel.merge(geo, on="source_id", how="inner")
print(f"  {before} rows -> {len(personnel)} matched to a geo_id ({before - len(personnel)} dropped, no match in geo table)")

# ── pupil_teacher_ratio — computed, never sourced directly (schema rule) ──
personnel["pupil_teacher_ratio"] = np.where(
    (personnel["teachers_total"].notna()) & (personnel["teachers_total"] != 0),
    personnel["enrollment_total"] / personnel["teachers_total"],
    np.nan,
)

# teachers_qualified not collected in either source
personnel["teachers_qualified"] = pd.NA

# ── Assemble in schema column order ───────────────────────────────────────
PERSONNEL_COLS = [
    "geo_id", "year",
    "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female",
    "teachers_qualified", "pupil_teacher_ratio", "classrooms_total",
]
personnel = personnel[PERSONNEL_COLS].copy()

# ── QA ──────────────────────────────────────────────────────────────────
print("\n=== MEX_personnel QA ===")
print(f"Total rows: {len(personnel)}")
print(f"Distinct schools: {personnel['geo_id'].nunique()}")
print(f"Years covered: {sorted(personnel['year'].dropna().unique().tolist())}")
print()

never_null = ["geo_id", "year", "enrollment_total", "teachers_total"]
for col in never_null:
    n = personnel[col].isna().sum()
    print(("  WARNING: " if n else "  OK: ") + f"{col} — {n} nulls")

print()
sex_mismatch = (
    (personnel["enrollment_male"] + personnel["enrollment_female"]) != personnel["enrollment_total"]
).sum()
print(f"enrollment_male + enrollment_female != enrollment_total: {sex_mismatch} rows "
      f"(if >0 and not just rounding, check whether sex disaggregation should be nulled per project rule)")

print(f"\npupil_teacher_ratio: min {personnel['pupil_teacher_ratio'].min():.1f}, "
      f"max {personnel['pupil_teacher_ratio'].max():.1f}, "
      f"NA count {personnel['pupil_teacher_ratio'].isna().sum()}")

dup_geo_year = personnel.duplicated(subset=["geo_id", "year"]).sum()
print(f"\nDuplicate (geo_id, year) pairs: {dup_geo_year}")
if dup_geo_year > 0:
    print(personnel[personnel.duplicated(subset=['geo_id', 'year'], keep=False)]
          .sort_values(['geo_id', 'year']).head(10).to_string())

# ── Save ────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
personnel.to_csv(OUT_FILE, index=False)
print(f"\nSaved: {OUT_FILE}")