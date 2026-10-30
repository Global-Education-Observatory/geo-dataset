"""
chl_outcomes.py
---------------
Builds chl_outcomes.csv (GEO Dataset canonical schema v1.0, outcomes table)
from MINEDUC student-level end-of-year performance files (Rendimiento escolar
por estudiante, public files with MRUN, SIGE).

Universe:
    Schools in chl_geo.csv (join on source_id = RBD). One row per school-year in
    which the school has at least one student with a final status.

Year convention:
    AGNO = calendar year the (March-start) school year begins. Matches the
    schema's beginning-year convention. No shift.

Filters:
    ESTADO_ESTAB == 1 where the column exists (2015+). Earlier files have no
    ESTADO_ESTAB; the codebooks report their counts only for operating schools,
    so no filter is applied (assumption from the codebooks, not verified).
    Regular child/youth programmes only — COD_ENSE in 110 (básica), 310 (media
    HC), 410–910 (media TP/artística). Adult, special-education, and
    pre-primary records are excluded, matching the enrolment and teacher
    definitions in chl_personnel.py.

Final status (SIT_FIN_R):
    P promoted, R repeated (reprobado), Y withdrawn (retirado), T transferred.
    SIT_FIN_R is used, not SIT_FIN. In SIT_FIN, transferred students are coded Y
    (about two thirds of all 'Y' records in 2016), which would triple-count
    withdrawals. SIT_FIN_R separates them as T.
    Students with status T or blank are excluded from all rates: a transferred
    student receives a final status at the school they moved to, and a blank
    status carries no outcome information.

Rates (proportions, 0–1), all grades of the retained programmes combined:
    denominator n = P + R + Y
    promotion_rate  = P / n
    repetition_rate = R / n
    dropout_rate    = Y / n
    (the three sum to 1 by construction)
    _male / _female use GEN_ALU 1 / 2 and only that sex's students in both
    numerator and denominator. Students with sex 0 (undefined) or 3 (non-binary)
    are included in the overall rates only.

    dropout_rate is computed from within-year formal and informal withdrawals
    (Y). It is NOT the UIS cohort-based dropout rate: a student who completes
    the year but does not re-enrol the following year does not appear as a
    dropout. Document in the harmonization note.

    completion_rate = P / n among students in the FINAL grade of their
    programme — 8º básico (COD_ENSE 110) or 4º medio (all media codes).
    Schools without students in a final grade get NA. This is promotion in the
    last grade of the level, a proxy for the schema's 'completes the final grade
    of the school's ISCED level'; it is not an age-cohort completion rate.

Notes:
    - 2020 and 2021 promotion rules were relaxed during the pandemic; expect
      atypical rates in those years (verify the exact policy before citing).
    - Year files hold students of the year's end-of-year status; counts are not
      the same population as the April 30 enrolment in the personnel table.

Author: HB
Date: 2026-09-24
"""

import os
import unicodedata

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
BASE = "/Users/heatherbaier/Documents/research/geo"
GEO_FILE        = f"{BASE}/db/geo/chl_geo.csv"
PERSONNEL_FILE  = f"{BASE}/db/personnel/chl_personnel.csv"      # optional, used for a consistency check
RENDIMIENTO_DIR = f"{BASE}/sources/CHL/rendimiento"             # holds one folder per year
RENDIMIENTO_FOLDER_TPL = "Rendimiento-{year}"    # GUESS — adjust to the real folder names
RENDIMIENTO_MARKER = "publ"                                     # tiebreaker only, used if a folder holds several .csv files
OUTPUT_FILE     = f"{BASE}/db/outcomes/chl_outcomes.csv"

ISO3 = "CHL"
YEARS = list(range(2003, 2026))

# ── Settings ──────────────────────────────────────────────────────────────
YOUTH_ENSE = {"110", "310", "410", "510", "610", "710", "810", "910"}
FINAL_GRADE = {"110": "8"}                       # 8º básico
FINAL_GRADE.update({e: "4" for e in YOUTH_ENSE - {"110"}})   # 4º medio (HC, TP, artística)

REQUIRED = {"AGNO", "RBD", "COD_ENSE", "COD_GRADO", "GEN_ALU", "SIT_FIN_R"}
OPTIONAL = {"ESTADO_ESTAB"}                      # 2015+

OUTCOME_COLS = [
    "geo_id", "year",
    "promotion_rate", "promotion_rate_male", "promotion_rate_female",
    "repetition_rate", "repetition_rate_male", "repetition_rate_female",
    "dropout_rate", "dropout_rate_male", "dropout_rate_female",
    "completion_rate", "completion_rate_male", "completion_rate_female",
]


# ── Helpers (same as chl_personnel.py) ────────────────────────────────────
def clean_col(c: str) -> str:
    """Normalise a header name: drop BOM (also the Latin-1 form 'ï»¿'), quotes, whitespace; uppercase."""
    c = c.replace("\ufeff", "").replace("ï»¿", "").replace("\x00", "")
    return c.strip().strip("\"'").strip().upper()


def _norm(name: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", name.lower())
                   if not unicodedata.combining(c))


def _sniff(path: str):
    """Return (encoding, separator, raw_first_line) from the file's header line."""
    with open(path, "rb") as f:
        raw = f.readline()
    enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "latin-1"
    text = raw.decode(enc, errors="replace")
    sep = max([";", ",", "\t", "|"], key=text.count)
    return enc, sep, raw


def read_source(path: str, required: set, optional: set = frozenset()) -> pd.DataFrame:
    """Read only the needed columns as stripped strings; raise with the raw header if required ones are missing."""
    wanted = set(required) | set(optional)
    enc, sep, raw = _sniff(path)
    df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str,
                     usecols=lambda c: clean_col(c) in wanted)
    df.columns = [clean_col(c) for c in df.columns]
    missing = set(required) - set(df.columns)
    if missing:
        raise RuntimeError(
            f"{os.path.basename(path)}: missing columns {sorted(missing)}\n"
            f"  detected encoding={enc!r}, separator={sep!r}\n"
            f"  raw first line: {raw[:400]!r}"
        )
    return df.apply(lambda c: c.str.strip())


def find_source(base_dir: str, folder_tpl: str, marker, year: int):
    """
    One .csv in the year's folder → use it. Several → the one whose name contains
    `marker` if that singles one out, otherwise raise. PDFs / .rar are ignored.
    Returns None if the folder is missing or holds no .csv.
    """
    folder = os.path.join(base_dir, folder_tpl.format(year=year))
    if not os.path.isdir(folder):
        return None
    csvs = [os.path.join(r, f) for r, _, fs in os.walk(folder)
            for f in fs if _norm(f).endswith(".csv")]
    if len(csvs) <= 1:
        return csvs[0] if csvs else None
    if marker:
        preferred = [c for c in csvs if marker in _norm(os.path.basename(c))]
        if len(preferred) == 1:
            return preferred[0]
    raise RuntimeError(f"{year}: {len(csvs)} csv files in {folder} and '{marker}' does not "
                       f"single one out — resolve manually:\n  " + "\n  ".join(csvs))


def check_year(seen: set, year: int, label: str):
    if seen and seen != {str(year)}:
        raise RuntimeError(f"{label} {year}: AGNO values in file are {sorted(seen)} — wrong file for this year")


# ── Rates for one year ────────────────────────────────────────────────────
def counts(sub: pd.DataFrame) -> pd.DataFrame:
    """Students per RBD by final status (columns P, R, Y)."""
    return (sub.groupby(["RBD", "SIT_FIN_R"]).size().unstack(fill_value=0)
               .reindex(columns=["P", "R", "Y"], fill_value=0))


def outcomes_for_year(path: str, rbds: set, year: int) -> pd.DataFrame:
    d = read_source(path, REQUIRED, OPTIONAL)
    check_year(set(d["AGNO"].dropna().unique()), year, "rendimiento")
    if "ESTADO_ESTAB" in d.columns:
        d = d[d["ESTADO_ESTAB"] == "1"]
    d = d[d["RBD"].isin(rbds) & d["COD_ENSE"].isin(YOUTH_ENSE)]
    d = d[d["SIT_FIN_R"].isin(["P", "R", "Y"])]          # drop T (transferred) and blank
    if d.empty:
        return pd.DataFrame(columns=["RBD"])

    final = d[d["COD_GRADO"] == d["COD_ENSE"].map(FINAL_GRADE)]   # last grade of the programme

    parts = []
    for suffix, sex in [("", None), ("_male", "1"), ("_female", "2")]:
        sub  = d     if sex is None else d[d["GEN_ALU"] == sex]
        subf = final if sex is None else final[final["GEN_ALU"] == sex]
        c, cf = counts(sub), counts(subf)
        n, nf = c.sum(axis=1), cf.sum(axis=1)
        r = pd.DataFrame({
            f"promotion_rate{suffix}":  c["P"] / n,
            f"repetition_rate{suffix}": c["R"] / n,
            f"dropout_rate{suffix}":    c["Y"] / n,
        })
        if sex is None:
            r["_n"] = n                                   # kept for the consistency check, not saved
        r[f"completion_rate{suffix}"] = cf["P"] / nf      # NaN where no final-grade students
        parts.append(r)

    return pd.concat(parts, axis=1).reset_index()


# ── Load geo register ─────────────────────────────────────────────────────
print("Loading geo register...")
geo = pd.read_csv(GEO_FILE, dtype=str)[["geo_id", "source_id"]]
rbd_to_geo = dict(zip(geo["source_id"].str.strip(), geo["geo_id"]))
rbds = set(rbd_to_geo)
print(f"  Schools in geo table: {len(rbds)}")

# ── Build panel ───────────────────────────────────────────────────────────
frames = []
for year in YEARS:
    path = find_source(RENDIMIENTO_DIR, RENDIMIENTO_FOLDER_TPL, RENDIMIENTO_MARKER, year)
    if path is None:
        print(f"  {year}: no rendimiento file found — skipping")
        continue
    print(f"  {year}: rendimiento file → {os.path.basename(path)}")
    o = outcomes_for_year(path, rbds, year)
    o["year"] = year
    frames.append(o)
    print(f"  {year}: {len(o)} schools")

if not frames:
    raise SystemExit("ERROR: no source files found for any year — check RENDIMIENTO_DIR / RENDIMIENTO_FOLDER_TPL")

panel = pd.concat(frames, ignore_index=True)
panel["geo_id"] = panel["RBD"].map(rbd_to_geo)
n_status = panel[["geo_id", "year", "_n"]].copy() if "_n" in panel.columns else None

for c in OUTCOME_COLS:
    if c not in panel.columns:
        panel[c] = np.nan
out = panel[OUTCOME_COLS].sort_values(["geo_id", "year"]).reset_index(drop=True)

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].notna().all(), "ERROR: unmatched geo_id"
assert not out.duplicated(["geo_id", "year"]).any(), "ERROR: duplicate geo_id × year"

rate_cols = [c for c in OUTCOME_COLS if c.endswith(("rate", "_male", "_female"))]
bad = ((out[rate_cols] < 0) | (out[rate_cols] > 1)).any(axis=1).sum()
print(f"  rows with any rate outside [0, 1]: {bad}")

s = out[["promotion_rate", "repetition_rate", "dropout_rate"]].dropna()
print(f"  promotion + repetition + dropout = 1 (±0.001): "
      f"{((s.sum(axis=1) - 1).abs() < 1e-3).mean():.1%} of {len(s)} rows")

print("\n  Median school-level rates by year:")
summ = out.groupby("year")[["promotion_rate", "repetition_rate", "dropout_rate", "completion_rate"]].median().round(3)
summ["n_schools"] = out.groupby("year").size()
summ["completion_NA"] = out.groupby("year")["completion_rate"].apply(lambda x: x.isna().mean()).round(2)
print(summ.to_string())

# consistency with personnel enrolment (April 30 headcount vs students with a final status)
if os.path.exists(PERSONNEL_FILE) and n_status is not None:
    per = pd.read_csv(PERSONNEL_FILE, usecols=["geo_id", "year", "enrollment_total"])
    m = n_status.merge(per, on=["geo_id", "year"]).dropna()
    m = m[m["enrollment_total"] > 0]
    if len(m):
        ratio = m["_n"] / m["enrollment_total"]
        print(f"\n  students with final status / personnel enrollment_total: "
              f"median {ratio.median():.3f}, p5 {ratio.quantile(.05):.3f}, p95 {ratio.quantile(.95):.3f} "
              f"(n={len(m)} school-years)")

print(f"\n  Rows: {len(out)}   Schools: {out['geo_id'].nunique()}   Years: {out['year'].min()}–{out['year'].max()}")
print(f"  Null counts:\n{out.isna().sum()}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")