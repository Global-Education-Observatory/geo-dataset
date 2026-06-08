"""
dom_personnel.py
----------------
Builds DOM_personnel.csv from the MINERD centros educativos dataset
(Periodo Escolar 2022-2023 / 2023-2024).

PERSONNEL Dataset canonical schema v1.0

Source:
    Same source file as dom_geo.py — contains both 2022-2023 and
    2023-2024 academic years in a single sheet.

Coverage:
    - enrollment_total only — Matricula column
    - All other personnel fields (teachers, PTR, classrooms) are NA;
      not collected at the school level in this source
    - Two years: 2022 (Año == 20222023) and 2023 (Año == 20232024)

Scope:
    Restricted to geo_ids present in DOM_geo.csv. Schools dropped from
    geo due to coordinate issues or Nivel exclusions are excluded here.

Year convention:
    Beginning-year convention: 2022-2023 → year = 2022,
                               2023-2024 → year = 2023

Author: HB
"""

import os
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/DOM/X3I-8sq-centros-educativos-de-republica-dominicana-periodo-escolar-2023-2024xlsx.xlsx"
GEO_FILE    = "/Users/heatherbaier/Documents/research/geo/db/geo/dom_geo.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/personnel/dom_personnel.csv"

ISO3 = "DOM"

# ── Nivel values to exclude (must match dom_geo.py) ───────────────────────
ADULT_NIVELES = {
    "ADULTOS",
    "BASICA DE ADULTOS",
    "PREPARA REGULAR",
    "PREPARA ACELERA",
    "PREPARA REGULAR - PREPARA ACELERA",
    "BASICA DE ADULTOS - PREPARA REGULAR",
}
PREPRIMARY_ONLY_NIVELES = {"INICIAL"}
EXCLUDE_NIVELES = ADULT_NIVELES | PREPRIMARY_ONLY_NIVELES

# ── Year map: Año value → beginning year integer ──────────────────────────
YEAR_MAP = {
    20222023: 2022,
    20232024: 2023,
}

# ── Load geo file to get valid geo_ids and source_id→geo_id mapping ───────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype=str)
print(f"  Schools in geo: {len(geo)}")
source_to_geo = dict(zip(geo["source_id"], geo["geo_id"]))

# ── Load source data ───────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_excel(SOURCE_FILE)
print(f"  Total rows: {len(df)}")

# ── Filter sector and Nivel (mirror geo filters) ──────────────────────────
df = df[df["Sector"].isin(["PÚBLICO", "PUBLICO"])].copy()
df = df[~df["Nivel"].isin(EXCLUDE_NIVELES)].copy()
print(f"  After sector + Nivel filter: {len(df)} rows")

# ── Parse centro_code ─────────────────────────────────────────────────────
df["centro_code"] = df["Centros"].str.split(" - ", n=1).str[0].str.strip()

# ── Map to geo_id ─────────────────────────────────────────────────────────
df["geo_id"] = df["centro_code"].map(source_to_geo)

# Schools not in geo (dropped due to coordinate issues) → exclude
before = len(df)
df = df[df["geo_id"].notna()].copy()
n_dropped = before - len(df)
print(f"  Dropped {n_dropped} rows not in geo (coordinate/Nivel exclusions)")

# ── Map year ──────────────────────────────────────────────────────────────
df["year"] = df["Año"].map(YEAR_MAP)
unmapped_years = df["year"].isna().sum()
if unmapped_years > 0:
    print(f"  WARNING: {unmapped_years} rows with unmapped Año value")
    print(df[df["year"].isna()]["Año"].value_counts())

# ── Parse enrollment ──────────────────────────────────────────────────────
df["enrollment_total"] = pd.to_numeric(df["Matricula"], errors="coerce").astype("Int64")

# ── Assemble output ───────────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]             = df["geo_id"]
out["year"]               = df["year"].astype(int)
out["enrollment_total"]   = df["enrollment_total"]
out["enrollment_male"]    = pd.NA
out["enrollment_female"]  = pd.NA
out["teachers_total"]     = pd.NA
out["teachers_male"]      = pd.NA
out["teachers_female"]    = pd.NA
out["teachers_qualified"] = pd.NA
out["pupil_teacher_ratio"]= pd.NA
out["classrooms_total"]   = pd.NA

out = out.sort_values(["geo_id", "year"]).reset_index(drop=True)

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== DOM_personnel QA ===")
print(f"Total rows: {len(out)}")
print(f"Unique geo_ids: {out['geo_id'].nunique()}")

print(f"\nRows by year:")
print(out["year"].value_counts().sort_index().to_string())

print(f"\nDuplicate geo_id × year: {out.duplicated(['geo_id','year']).sum()}")

print(f"\nenrollment_total nulls: {out['enrollment_total'].isna().sum()}")
print(f"enrollment_total zeros: {(out['enrollment_total'] == 0).sum()}")
print(f"enrollment_total describe:")
print(out["enrollment_total"].describe().to_string())

# Schools in geo missing from personnel
geo_ids_in_geo = set(geo["geo_id"])
geo_ids_in_personnel = set(out["geo_id"])
missing_from_personnel = geo_ids_in_geo - geo_ids_in_personnel
print(f"\nSchools in geo with no personnel row (either year): {len(missing_from_personnel)}")

# Schools with only one year
both_years = out.groupby("geo_id")["year"].nunique()
print(f"Schools with both years: {(both_years == 2).sum()}")
print(f"Schools with one year only: {(both_years == 1).sum()}")

# ── Save ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved: {OUTPUT_FILE}")
