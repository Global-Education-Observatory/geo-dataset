"""
bra_personnel.py
----------------
Builds BRA_personnel.csv from INEP Censo Escolar da Educação Básica
microdata files (2007–2025), conforming to the PERSONNEL table
canonical schema v1.0.

Sources:
    INEP Microdados do Censo Escolar da Educação Básica
    Years 2007–2024: single school-level CSV per year
    Year 2025:       split into three separate tables
                     (Tabela_Matricula, Tabela_Docente, Tabela_Escola)

Coverage:
    Restricted to schools present in bra_geo.csv (public, in-scope only).
    Personnel/resources/outcomes schema rule: no rows inserted for schools
    absent from geo in a given year.

Enrollment computation:
    enrollment_total = QT_MAT_FUND + QT_MAT_MED
    — QT_MAT_BAS excluded: includes pre-primary and EJA
    — NaN treated as 0 for summation where at least one field is present;
      both NaN → enrollment_total = NA

    2025 note: QT_MAT_MED in 2025 covers Ensino Médio Regular only
    (excludes IFTP track introduced by Novo Ensino Médio reform).
    QT_MAT_MED_IFTP_CT added to maintain comparability with prior years.

Teachers computation:
    teachers_total = QT_DOC_FUND + QT_DOC_MED
    — Same logic as enrollment_total
    — QT_DOC_* affected by row-shift error in releases prior to Nov 2022
      (2007–2021); corrected files re-downloaded May 2026.

Sex disaggregation:
    enrollment_female / enrollment_male set to NA for all years.
    Only sex-disaggregated field available is QT_MAT_BAS_FEM/MASC, which
    covers all basic education stages including Educação Infantil. In ~62%
    of schools this exceeds enrollment_total (Fundamental+Médio only),
    violating the schema requirement that sex subtotals are subsets of
    enrollment_total.

    teachers_male / teachers_female / teachers_qualified: not available
    at school level in Censo Escolar microdata.

PTR:
    pupil_teacher_ratio = enrollment_total / teachers_total
    Set to NA where teachers_total is 0 or NA (avoids inf/NaN).

Year convention:
    year = calendar year of the Censo Escolar reference date (last
    Wednesday of May). Consistent with UIS beginning-year convention.

Early years:
    Pre-2007 files use legacy school identifier (MASCARA/CODESC) that
    does not reliably join to CO_ENTIDADE and are excluded.

Author: HB
"""

import pandas as pd
import numpy as np
import os

# ── Paths ──────────────────────────────────────────────────────────────────
GEO_FILE   = "/Users/heatherbaier/Documents/research/geo/db/geo/bra_geo.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/personnel/bra_personnel.csv"

# Single-file years (2007–2024)
SOURCE_FILES = {
    2024: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2024/dados/microdados_ed_basica_2024.csv",
    2023: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2023/dados/microdados_ed_basica_2023.csv",
    2022: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/Microdados do Censo Escolar da Educa‡Æo B sica 2022/dados/microdados_ed_basica_2022.csv",
    2021: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2021/dados/microdados_ed_basica_2021.csv",
    2020: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2020/dados/microdados_ed_basica_2020.CSV",
    2019: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2019/dados/microdados_ed_basica_2019.csv",
    2018: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2018/dados/microdados_ed_basica_2018.csv",
    2017: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2017/dados/microdados_ed_basica_2017.csv",
    2016: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2016/dados/microdados_ed_basica_2016.csv",
    2015: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2015/dados/microdados_ed_basica_2015.csv",
    2014: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2014/dados/microdados_ed_basica_2014.csv",
    2013: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2013/dados/microdados_ed_basica_2013.csv",
    2012: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2012/dados/microdados_ed_basica_2012.csv",
    2011: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2011/dados/microdados_ed_basica_2011.csv",
    2010: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2010/dados/microdados_ed_basica_2010.csv",
    2009: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2009/dados/microdados_ed_basica_2009.csv",
    2008: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2008/dados/microdados_ed_basica_2008.csv",
    2007: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2007/dados/microdados_ed_basica_2007.csv",
}

# 2025 split files
SOURCE_2025 = {
    "matricula":  "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2025/dados/Tabela_Matricula_2025.csv",
    "docente":    "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2025/dados/Tabela_Docente_2025.csv",
    "escola":     "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2025/dados/Tabela_Escola_2025.csv",
}

# Schema column order
PERSONNEL_COLS = [
    "geo_id",
    "year",
    "enrollment_total",
    "enrollment_male",
    "enrollment_female",
    "teachers_total",
    "teachers_male",
    "teachers_female",
    "teachers_qualified",
    "pupil_teacher_ratio",
    "classrooms_total",
]


# ── Helpers ────────────────────────────────────────────────────────────────

def safe_sum(df, cols):
    """
    Sum columns, treating NaN as 0 only where at least one value is present.
    Returns NA where ALL input columns are NA.
    """
    present = df[cols].notna().any(axis=1)
    total = df[cols].fillna(0).sum(axis=1)
    total[~present] = pd.NA
    return total


def safe_ptr(enrollment, teachers):
    """
    Compute PTR. Returns NA where teachers is 0 or NA.
    """
    ptr = enrollment / teachers.replace(0, pd.NA)
    return ptr


def apply_id_map(df, id_map):
    """Map CO_ENTIDADE (as string) to geo_id."""
    df["CO_ENTIDADE"] = df["CO_ENTIDADE"].astype(str).str.strip()
    df["geo_id"] = df["CO_ENTIDADE"].map(id_map)
    return df


# ── Load geo ───────────────────────────────────────────────────────────────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str})
id_map = dict(zip(geo["source_id"], geo["geo_id"]))
geo_ids = set(geo["source_id"])
print(f"  {len(geo)} schools in geo")


# ── Process 2007–2024 ──────────────────────────────────────────────────────

def process_year(path, year, id_map, geo_ids):
    """
    Process a single-file Censo Escolar year into a personnel DataFrame.
    """
    print(f"  {year}: loading...", end=" ")
    df = pd.read_csv(path, encoding="latin-1", sep=";", dtype={"CO_ENTIDADE": str}, low_memory=False)

    # Restrict to geo schools
    df = df[df["CO_ENTIDADE"].str.strip().isin(geo_ids)].copy()
    df = apply_id_map(df, id_map)
    print(f"{len(df)} schools matched", end=" ")

    # Enrollment: FUND + MED
    fund_col = "QT_MAT_FUND" if "QT_MAT_FUND" in df.columns else None
    med_col  = "QT_MAT_MED"  if "QT_MAT_MED"  in df.columns else None

    if fund_col and med_col:
        df["enrollment_total"] = safe_sum(df, [fund_col, med_col])
    elif fund_col:
        df["enrollment_total"] = pd.to_numeric(df[fund_col], errors="coerce")
    elif med_col:
        df["enrollment_total"] = pd.to_numeric(df[med_col], errors="coerce")
    else:
        df["enrollment_total"] = pd.NA
        print(f"  WARNING {year}: no enrollment columns found")

    # Teachers: FUND + MED
    doc_fund = "QT_DOC_FUND" if "QT_DOC_FUND" in df.columns else None
    doc_med  = "QT_DOC_MED"  if "QT_DOC_MED"  in df.columns else None

    if doc_fund and doc_med:
        df["teachers_total"] = safe_sum(df, [doc_fund, doc_med])
    elif doc_fund:
        df["teachers_total"] = pd.to_numeric(df[doc_fund], errors="coerce")
    elif doc_med:
        df["teachers_total"] = pd.to_numeric(df[doc_med], errors="coerce")
    else:
        df["teachers_total"] = pd.NA
        print(f"  WARNING {year}: no teacher columns found")

    # Classrooms
    if "QT_SALAS_UTILIZADAS" in df.columns:
        df["classrooms_total"] = pd.to_numeric(df["QT_SALAS_UTILIZADAS"], errors="coerce")
    else:
        df["classrooms_total"] = pd.NA
        print(f"  WARNING {year}: QT_SALAS_UTILIZADAS not found")

    # PTR
    df["pupil_teacher_ratio"] = safe_ptr(df["enrollment_total"], df["teachers_total"])

    # NA columns
    df["year"]               = year
    df["enrollment_male"]    = pd.NA
    df["enrollment_female"]  = pd.NA
    df["teachers_male"]      = pd.NA
    df["teachers_female"]    = pd.NA
    df["teachers_qualified"] = pd.NA

    print(f"→ enrollment NA: {df['enrollment_total'].isna().sum()}, teacher NA: {df['teachers_total'].isna().sum()}")
    return df[PERSONNEL_COLS].copy()


# ── Process 2025 (split files) ─────────────────────────────────────────────

def process_2025(paths, id_map, geo_ids):
    """
    Process 2025 Censo Escolar from three separate tables.
    Enrollment: QT_MAT_FUND + QT_MAT_MED + QT_MAT_MED_IFTP_CT
    (QT_MAT_MED_IFTP_CT added to maintain comparability with prior years
    where integrated technical Ensino Médio was included in QT_MAT_MED.)
    """
    print("  2025: loading split files...", end=" ")

    # Matricula
    mat = pd.read_csv(paths["matricula"], encoding="latin-1", sep=";", dtype={"CO_ENTIDADE": str}, low_memory=False)
    mat = mat[mat["CO_ENTIDADE"].str.strip().isin(geo_ids)].copy()
    mat = apply_id_map(mat, id_map)

    enroll_cols = ["QT_MAT_FUND"]
    if "QT_MAT_MED" in mat.columns:
        enroll_cols.append("QT_MAT_MED")
    if "QT_MAT_MED_IFTP_CT" in mat.columns:
        enroll_cols.append("QT_MAT_MED_IFTP_CT")
    mat["enrollment_total"] = safe_sum(mat, enroll_cols)
    mat = mat[["geo_id", "enrollment_total"]]

    # Docente
    doc = pd.read_csv(paths["docente"], encoding="latin-1", sep=";", dtype={"CO_ENTIDADE": str}, low_memory=False)
    doc = doc[doc["CO_ENTIDADE"].str.strip().isin(geo_ids)].copy()
    doc = apply_id_map(doc, id_map)
    doc_cols = [c for c in ["QT_DOC_FUND", "QT_DOC_MED"] if c in doc.columns]
    doc["teachers_total"] = safe_sum(doc, doc_cols) if doc_cols else pd.NA
    doc = doc[["geo_id", "teachers_total"]]

    # Escola (classrooms)
    esc = pd.read_csv(paths["escola"], encoding="latin-1", sep=";", dtype={"CO_ENTIDADE": str}, low_memory=False)
    esc = esc[esc["CO_ENTIDADE"].str.strip().isin(geo_ids)].copy()
    esc = apply_id_map(esc, id_map)
    esc["classrooms_total"] = pd.to_numeric(esc["QT_SALAS_UTILIZADAS"], errors="coerce") if "QT_SALAS_UTILIZADAS" in esc.columns else pd.NA
    esc = esc[["geo_id", "classrooms_total"]]

    # Merge — left on mat to keep all matched enrollment schools
    out = mat.merge(doc, on="geo_id", how="left")
    out = out.merge(esc, on="geo_id", how="left")

    print(f"{len(out)} schools matched")
    print(f"    enrollment NA: {out['enrollment_total'].isna().sum()}, teacher NA: {out['teachers_total'].isna().sum()}")

    out["pupil_teacher_ratio"] = safe_ptr(out["enrollment_total"], out["teachers_total"])
    out["year"]               = 2025
    out["enrollment_male"]    = pd.NA
    out["enrollment_female"]  = pd.NA
    out["teachers_male"]      = pd.NA
    out["teachers_female"]    = pd.NA
    out["teachers_qualified"] = pd.NA

    return out[PERSONNEL_COLS].copy()


# ── Run all years ──────────────────────────────────────────────────────────
print("\nProcessing 2007–2024...")
processed = []
for year in sorted(SOURCE_FILES.keys()):
    processed.append(process_year(SOURCE_FILES[year], year, id_map, geo_ids))

print("\nProcessing 2025...")
processed.append(process_2025(SOURCE_2025, id_map, geo_ids))

# ── Concatenate ────────────────────────────────────────────────────────────
print("\nConcatenating...")
personnel = pd.concat(processed, ignore_index=True)

# ── QA ─────────────────────────────────────────────────────────────────────
print("\n=== BRA_personnel QA ===")
print(f"Total rows:        {len(personnel)}")
print(f"Unique geo_ids:    {personnel['geo_id'].nunique()}")
print(f"Years covered:     {sorted(personnel['year'].unique())}")
print()

never_null = ["geo_id", "year"]
for col in never_null:
    n = personnel[col].isna().sum()
    status = "OK" if n == 0 else f"WARNING: {n} nulls — schema violation"
    print(f"  {status}: {col}")

print()
print("Rows per year:")
print(personnel["year"].value_counts().sort_index().to_string())
print()
print("enrollment_total NA by year:")
print(personnel.groupby("year")["enrollment_total"].apply(lambda x: x.isna().sum()).to_string())
print()
print("teachers_total NA by year:")
print(personnel.groupby("year")["teachers_total"].apply(lambda x: x.isna().sum()).to_string())
print()

# Check no school appears more than once per year
dupes = personnel.duplicated(subset=["geo_id", "year"]).sum()
print(f"Duplicate geo_id × year rows: {dupes}")

# PTR sanity check
ptr_extreme = (personnel["pupil_teacher_ratio"] > 200).sum()
if ptr_extreme > 0:
    print(f"  WARNING: {ptr_extreme} rows with PTR > 200 — review")

# ── Save ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
personnel.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")