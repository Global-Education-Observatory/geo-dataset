"""
chl_personnel.py
----------------
Builds chl_personnel.csv (GEO Dataset canonical schema v1.0, personnel table)
from MINEDUC student-level enrolment (matrícula) and teacher-position
(cargos docentes) files.

Sources (MINEDUC Centro de Estudios, public files with MRUN, SIGE):
    Matrícula por estudiante  — reference date 30 April each year
    Cargos docentes           — reference date 30 June each year

Universe:
    Schools in chl_geo.csv (join on source_id = RBD). One row per school-year
    where the school appears in either source. Schools absent from a source in
    a given year get NA (not 0) for that source's fields.

Year convention:
    AGNO in both sources is the calendar year the (March-start) school year
    begins, which matches the schema's beginning-year convention. No shift.

One definition for all years:
    Everything follows the 2015+ definition below. If a year's file lacks a
    column that definition needs, that source's fields for the year are left
    blank (NA), not approximated. In practice teacher fields are blank before
    2013 (no HORAS_AULA) and 2011 (no COD_ENS / TIT_ID_2); enrolment is
    available from 2004.

Filters (both sources):
    ESTADO_ESTAB == 1 (school operating) where the column exists (2015+).
    Earlier files have no ESTADO_ESTAB, but the codebooks report their counts
    only for operating schools, so no filter is applied (assumption taken from
    the codebooks, not verified on the data).

Enrolment (enrollment_total / _male / _female):
    Headcount of students in regular child/youth programmes only —
    COD_ENSE in 110 (básica), 310 (media HC), 410–910 (media TP/artística).
    Excluded: parvularia (10), adult (x60/x61/x62/x63), special education
    (2xx). This matches the ISCED 1–3 scope of chl_geo.csv and keeps the
    pupil–teacher ratio internally consistent.
    Sex from GEN_ALU (1 = male, 2 = female). GEN_ALU = 0 (no information) is
    counted in the total only, so male + female can be below the total.

Teachers (teachers_total / _male / _female / _qualified):
    Unit is a person, counted once at their principal school. Filters:
      PERSONAS == 1                       principal position of the person
      ID_IFP == 1 (docente de aula) OR HORAS_AULA > 0
                                          instructional staff; excludes
                                          non-teaching directors, UTP heads,
                                          inspectors, and staff working for the
                                          sostenedor (UIS 'teaching staff')
      COD_ENS_1 or COD_ENS_2 in youth codes (TEACHERS_YOUTH_ONLY = True)
                                          teaches in a programme counted in
                                          the enrolment above
    Because PERSONAS assigns each teacher to ONE school, teachers working at
    several schools are counted at their principal school only (headcount, not
    FTE, per schema). Headcount is as of 30 June.
    Sex from DOC_GENERO (1 = male, 2 = female). Code 3 (non-binary) is counted
    in the total only, so male + female can be below the total.
    Qualified = TIT_ID_1 == 1 or TIT_ID_2 == 1 (holds a teaching degree,
    'Titulado en Educación'). This is the national qualification standard used
    here; document in the harmonization note.

Computed:
    pupil_teacher_ratio = enrollment_total / teachers_total (NA if either is
    NA or teachers_total = 0).

Not available in these sources:
    classrooms_total = NA.

Author: HB
Date: 2026-09-24
"""

import os
import unicodedata

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
BASE = "/Users/heatherbaier/Documents/research/geo"
GEO_FILE       = f"{BASE}/db/geo/chl_geo.csv"
MATRICULA_DIR  = f"{BASE}/sources/CHL/matricula"          # holds Matricula-por-estudiante-{year}/ folders
MATRICULA_FOLDER_TPL = "Matricula-por-estudiante-{year}"
MATRICULA_MARKER = "publ"                                 # tiebreaker only, used if a folder holds several .csv files
DOCENTES_DIR   = f"{BASE}/sources/CHL/docentes"            # holds Directorio-Docentes-{year}/ folders
DOCENTES_FOLDER_TPL = "Directorio-Docentes-{year}"
DOCENTES_MARKER = "publica"                               # tiebreaker only, used if a folder holds several .csv files
OUTPUT_FILE    = f"{BASE}/db/personnel/chl_personnel.csv"

ISO3 = "CHL"
YEARS = list(range(2004, 2026))   # ESTADO_ESTAB exists in both sources from 2015

# ── Settings ──────────────────────────────────────────────────────────────
YOUTH_ENSE = {"110", "310", "410", "510", "610", "710", "810", "910"}
TEACHERS_YOUTH_ONLY = True

# One definition for every year: the 2015+ definition. A year whose file lacks
# a column the definition needs gets NA for that source's fields (no fallbacks).
MAT_REQUIRED = {"AGNO", "RBD", "COD_ENSE", "GEN_ALU"}
MAT_OPTIONAL = {"ESTADO_ESTAB"}          # 2015+; earlier files already hold operating schools only
DOC_REQUIRED = {"AGNO", "RBD", "MRUN", "PERSONAS", "DOC_GENERO", "TIT_ID_1", "TIT_ID_2",
                "ID_IFP", "HORAS_AULA", "COD_ENS_1", "COD_ENS_2"}
DOC_OPTIONAL = {"ESTADO_ESTAB"}          # 2015+; earlier files already hold operating schools only
# Columns that are absent in early years per the codebook. If ONLY these are
# missing, the year is blanked; any other missing column is treated as an error.
DOC_EXPECTED_EARLY_GAPS = {"HORAS_AULA", "COD_ENS_1", "COD_ENS_2", "TIT_ID_2"}

PERSONNEL_COLS = [
    "geo_id", "year", "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female", "teachers_qualified",
    "pupil_teacher_ratio", "classrooms_total",
]


# ── Helpers ───────────────────────────────────────────────────────────────
def clean_col(c: str) -> str:
    """Normalise a header name: drop BOM (also the Latin-1 form 'ï»¿'), quotes, whitespace; uppercase."""
    c = c.replace("\ufeff", "").replace("ï»¿", "").replace("\x00", "")
    return c.strip().strip("\"'").strip().upper()


def _sniff(path: str):
    """Return (encoding, separator, raw_first_line) from the file's header line."""
    with open(path, "rb") as f:
        raw = f.readline()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        enc = "utf-16"
    else:
        enc = "latin-1"          # never fails; the columns we use are numeric codes
    text = raw.decode(enc, errors="replace")
    seps = [";", ",", "\t", "|"]
    sep = max(seps, key=text.count)
    return enc, sep, raw


class MissingColumns(RuntimeError):
    def __init__(self, msg, missing):
        super().__init__(msg)
        self.missing = set(missing)


def read_source(path: str, required: set, optional: set = frozenset()) -> pd.DataFrame:
    """
    Read only the needed columns, everything as stripped strings.
    Encoding and delimiter are sniffed from the header line. Missing REQUIRED
    columns raise an error showing the raw header; missing OPTIONAL columns are
    simply absent from the result (callers check `in df.columns`).
    """
    wanted = set(required) | set(optional)
    enc, sep, raw = _sniff(path)
    df = pd.read_csv(
        path, sep=sep, encoding=enc, dtype=str,
        usecols=lambda c: clean_col(c) in wanted,
    )
    df.columns = [clean_col(c) for c in df.columns]
    missing = set(required) - set(df.columns)
    if missing:
        raise MissingColumns(
            f"{os.path.basename(path)}: missing columns {sorted(missing)}\n"
            f"  detected encoding={enc!r}, separator={sep!r}\n"
            f"  raw first line: {raw[:400]!r}",
            missing,
        )
    return df.apply(lambda c: c.str.strip())


def num(s: pd.Series) -> pd.Series:
    """Numeric parse tolerant of comma decimals and whitespace."""
    return pd.to_numeric(s.astype(str).str.strip().str.replace(",", ".", regex=False),
                         errors="coerce")


def _norm(name: str) -> str:
    """Lowercase and strip accents so PÚBLICA / publica / PUBLICA all match."""
    return "".join(c for c in unicodedata.normalize("NFKD", name.lower())
                   if not unicodedata.combining(c))


def find_source(base_dir: str, folder_tpl: str, marker, year: int):
    """
    Locate a year's data file inside its folder. PDFs (codebooks) and .rar
    archives are ignored; only .csv files are candidates.
      - exactly one .csv in the folder → use it (name does not matter)
      - several .csv files → use the one whose name contains `marker`
        (case/accent-insensitive), if that narrows it to exactly one
      - otherwise raise, listing the candidates
    Returns None if the folder is missing or holds no .csv.
    """
    folder = os.path.join(base_dir, folder_tpl.format(year=year))
    if not os.path.isdir(folder):
        return None
    csvs = []
    for root, _, files in os.walk(folder):
        for f in files:
            if _norm(f).endswith(".csv"):
                csvs.append(os.path.join(root, f))
    if len(csvs) <= 1:
        return csvs[0] if csvs else None
    if marker:
        preferred = [c for c in csvs if marker in _norm(os.path.basename(c))]
        if len(preferred) == 1:
            return preferred[0]
    raise RuntimeError(f"{year}: {len(csvs)} csv files in {folder} and '{marker}' does not "
                       f"single one out — resolve manually:\n  " + "\n  ".join(csvs))


def find_matricula(year: int):
    return find_source(MATRICULA_DIR, MATRICULA_FOLDER_TPL, MATRICULA_MARKER, year)


def find_docentes(year: int):
    return find_source(DOCENTES_DIR, DOCENTES_FOLDER_TPL, DOCENTES_MARKER, year)


def check_year(seen: set, year: int, label: str):
    """Fail loudly if the AGNO values in a file do not match the year it was loaded as."""
    if seen and seen != {str(year)}:
        raise RuntimeError(f"{label} {year}: AGNO values in file are {sorted(seen)} — wrong file for this year")


# ── Enrolment for one year ────────────────────────────────────────────────
def enrollment_for_year(path: str, rbds: set, year: int) -> pd.DataFrame:
    m = read_source(path, MAT_REQUIRED, MAT_OPTIONAL)
    check_year(set(m["AGNO"].dropna().unique()), year, "matrícula")
    if "ESTADO_ESTAB" in m.columns:
        m = m[m["ESTADO_ESTAB"] == "1"]
    m = m[m["RBD"].isin(rbds) & m["COD_ENSE"].isin(YOUTH_ENSE)]
    if m.empty:
        return pd.DataFrame(columns=["RBD", "enrollment_total",
                                     "enrollment_male", "enrollment_female"])
    g = m.groupby(["RBD", "GEN_ALU"]).size().rename("n").reset_index()
    wide = g.pivot(index="RBD", columns="GEN_ALU", values="n").fillna(0)
    out = pd.DataFrame(index=wide.index)
    out["enrollment_total"] = wide.sum(axis=1)
    out["enrollment_male"]   = wide["1"] if "1" in wide.columns else 0
    out["enrollment_female"] = wide["2"] if "2" in wide.columns else 0
    return out.astype(int).reset_index()


# ── Teachers for one year ─────────────────────────────────────────────────
def teachers_for_year(path: str, rbds: set, year: int) -> pd.DataFrame:
    try:
        t = read_source(path, DOC_REQUIRED, DOC_OPTIONAL)
    except MissingColumns as e:
        if e.missing <= DOC_EXPECTED_EARLY_GAPS:
            print(f"    note ({year}): file lacks {sorted(e.missing)} needed for the 2015+ "
                  f"teacher definition → teacher fields left blank")
            return pd.DataFrame(columns=["RBD"])
        raise
    check_year(set(t["AGNO"].dropna().unique()), year, "docentes")
    if "ESTADO_ESTAB" in t.columns:
        t = t[t["ESTADO_ESTAB"] == "1"]
    t = t[(t["PERSONAS"] == "1") & t["RBD"].isin(rbds)]
    cols = ["RBD", "teachers_total", "teachers_male", "teachers_female",
            "teachers_qualified"]
    if t.empty:
        return pd.DataFrame(columns=cols)

    # instructional staff: docente de aula, or anyone with classroom hours
    t = t[(num(t["ID_IFP"]) == 1) | (num(t["HORAS_AULA"]) > 0)].copy()

    # teaches in a programme counted in enrolment
    if TEACHERS_YOUTH_ONLY:
        t = t[t["COD_ENS_1"].isin(YOUTH_ENSE) | t["COD_ENS_2"].isin(YOUTH_ENSE)].copy()

    # one row per person per school (guard against residual duplicates)
    t = t.drop_duplicates(["RBD", "MRUN"])

    t["male"]      = (t["DOC_GENERO"] == "1").astype(int)
    t["female"]    = (t["DOC_GENERO"] == "2").astype(int)
    t["qualified"] = ((t["TIT_ID_1"] == "1") | (t["TIT_ID_2"] == "1")).astype(int)

    g = t.groupby("RBD").agg(
        teachers_total=("MRUN", "size"),
        teachers_male=("male", "sum"),
        teachers_female=("female", "sum"),
        teachers_qualified=("qualified", "sum"),
    ).reset_index()
    return g


# ── Load geo register ─────────────────────────────────────────────────────
print("Loading geo register...")
geo = pd.read_csv(GEO_FILE, dtype=str)[["geo_id", "source_id"]]
rbd_to_geo = dict(zip(geo["source_id"].str.strip(), geo["geo_id"]))
rbds = set(rbd_to_geo)
print(f"  Schools in geo table: {len(rbds)}")

# ── Build panel ───────────────────────────────────────────────────────────
frames = []
for year in YEARS:
    mpath = find_matricula(year)
    dpath = find_docentes(year)
    have_m, have_d = mpath is not None, dpath is not None
    if have_m:
        print(f"  {year}: matrícula file → {os.path.basename(mpath)}")
    if have_d:
        print(f"  {year}: docentes file  → {os.path.basename(dpath)}")
    if not (have_m or have_d):
        print(f"  {year}: no source files found — skipping")
        continue

    enr = enrollment_for_year(mpath, rbds, year) if have_m else pd.DataFrame(columns=["RBD"])
    tea = teachers_for_year(dpath, rbds, year) if have_d else pd.DataFrame(columns=["RBD"])
    if not have_m:
        print(f"  {year}: WARNING no matrícula file — enrolment NA")
    if not have_d:
        print(f"  {year}: WARNING no docentes file — teachers NA")

    p = pd.merge(enr, tea, on="RBD", how="outer")
    p["year"] = year
    frames.append(p)
    print(f"  {year}: {len(p)} schools "
          f"(enrolment {p['enrollment_total'].notna().sum() if 'enrollment_total' in p else 0}, "
          f"teachers {p['teachers_total'].notna().sum() if 'teachers_total' in p else 0})")

if not frames:
    raise SystemExit("ERROR: no source files found for any year — check the path templates")

panel = pd.concat(frames, ignore_index=True)
panel["geo_id"] = panel["RBD"].map(rbd_to_geo)

# ── Schema columns ────────────────────────────────────────────────────────
for c in ["enrollment_total", "enrollment_male", "enrollment_female",
          "teachers_total", "teachers_male", "teachers_female", "teachers_qualified"]:
    if c not in panel.columns:
        panel[c] = np.nan

panel["pupil_teacher_ratio"] = np.where(
    panel["enrollment_total"].notna() & panel["teachers_total"].notna()
    & (panel["teachers_total"] > 0),
    panel["enrollment_total"] / panel["teachers_total"],
    np.nan,
)
panel["classrooms_total"] = np.nan   # not collected in these sources

out = panel[PERSONNEL_COLS].copy()
out = out.sort_values(["geo_id", "year"]).reset_index(drop=True)
for c in ["enrollment_total", "enrollment_male", "enrollment_female",
          "teachers_total", "teachers_male", "teachers_female",
          "teachers_qualified", "classrooms_total"]:
    out[c] = out[c].astype("Int64")

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].notna().all(), "ERROR: unmatched geo_id"
assert not out.duplicated(["geo_id", "year"]).any(), "ERROR: duplicate geo_id × year"
assert out["year"].notna().all(), "ERROR: null year"

# male + female vs total (schema: flag gap > 1%)
for label, tot, m, f in [
    ("enrolment", "enrollment_total", "enrollment_male", "enrollment_female"),
    ("teachers",  "teachers_total",   "teachers_male",   "teachers_female"),
]:
    d = out.dropna(subset=[tot, m, f])
    d = d[d[tot] > 0]
    if len(d) == 0:
        print(f"  {label}: no rows with total, male, and female all present — skipping check")
        continue
    gap = (d[tot] - d[m] - d[f]) / d[tot]
    print(f"  {label}: male+female exceeds total in {(gap < 0).sum()} rows; "
          f"gap > 1% in {(gap > 0.01).sum()} of {len(d)} rows "
          f"(overall gap {(d[tot].sum() - d[m].sum() - d[f].sum()) / d[tot].sum():.3%})")

q = out.dropna(subset=["teachers_total", "teachers_qualified"])
print(f"  qualified > total: {(q['teachers_qualified'] > q['teachers_total']).sum()} rows")

ptr = out["pupil_teacher_ratio"].dropna()
print(f"  PTR: median {ptr.median():.1f}, p1 {ptr.quantile(.01):.1f}, "
      f"p99 {ptr.quantile(.99):.1f}; >100 in {(ptr > 100).sum()} rows, <1 in {(ptr < 1).sum()} rows")

print(f"\n  Rows: {len(out)}   Schools: {out['geo_id'].nunique()}   Years: {out['year'].min()}–{out['year'].max()}")
print(f"  Schools in geo with no personnel row: {len(rbds) - out['geo_id'].nunique()}")
print(f"  Null counts:\n{out.isna().sum()}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")