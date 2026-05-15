"""
bgd_personnel.py
Builds BGD_personnel.csv from Students_by_age__1_.xls and BGD_geo.csv
GEO Dataset canonical schema v1.0

Source file: NUMBER OF STUDENT BY AGE AND CLASS, 2016
Structure: one row per school, columns = 5 classes × 7 age bands (AGE_UNDER11
           through AGE_UPER15) — no sex disaggregation, no teacher counts.

Harmonization notes:
  - enrollment_total: sum of all age-band columns across Classes 6–10.
    Headcount on EMIS reference date (academic year 2016).
  - enrollment_male / enrollment_female: NA — source does not disaggregate by sex.
  - teachers_total / teachers_male / teachers_female: NA — not in source file.
  - teachers_qualified: NA — not collected.
  - pupil_teacher_ratio: NA — teachers_total unavailable.
  - classrooms_total: NA — not collected in this source.
  - year: 2016 (beginning-year convention; Bangladesh academic year is Jan–Dec
    for secondary schools, so 2016 = 2016).
  - Schools in source not present in BGD_geo.csv (i.e. filtered out during
    management-type / education-level cleaning) are dropped.
"""

import pandas as pd
import numpy as np

# ── Load source ───────────────────────────────────────────────────────────────
raw = pd.read_excel(
    "/Users/heatherbaier/Documents/research/geo/sources/BGD/Students by age.xls",
    engine="xlrd",
    header=None,
    skiprows=2        # skip merged title row + class header row
)

# Row 2 (index 0 after skiprows=2) is the age-band sub-header — drop it
raw = raw.iloc[1:].reset_index(drop=True)

# Assign column names
AGE_BANDS = ["AGE_UNDER11", "AGE11", "AGE12", "AGE13", "AGE14", "AGE15", "AGE_UPER15"]
CLASSES   = ["CLASS_SIX", "CLASS_SEVEN", "CLASS_EIGHT", "CLASS_NINE", "CLASS_TEN"]

col_names = ["year", "district", "thana", "EIIN", "institute_name"]
for cls in CLASSES:
    for age in AGE_BANDS:
        col_names.append(f"{cls}__{age}")

raw.columns = col_names

# Drop any fully empty rows
raw = raw.dropna(subset=["EIIN"]).copy()
raw["EIIN"] = raw["EIIN"].astype(int).astype(str)

# ── Compute enrollment_total ──────────────────────────────────────────────────
# Sum all 35 age-band columns (5 classes × 7 age bands), ignoring NA
age_cols = [c for c in raw.columns if "__AGE" in c]
raw["enrollment_total"] = raw[age_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
# min_count=1 means: if ALL values are NA, result is NA rather than 0

# Convert to integer where not NA
raw["enrollment_total"] = raw["enrollment_total"].where(
    raw["enrollment_total"].isna(),
    raw["enrollment_total"].round(0).astype("Int64")
)

# ── Load geo table to get geo_id mapping ─────────────────────────────────────
geo = pd.read_csv("/Users/heatherbaier/Documents/research/geo/db/geo/bgd_geo.csv", dtype={"source_id": str})[["geo_id", "source_id"]]

# ── Merge — only keep schools present in geo table ───────────────────────────
df = raw.merge(geo, left_on="EIIN", right_on="source_id", how="inner")

n_source   = len(raw)
n_matched  = len(df)
n_dropped  = n_source - n_matched
print(f"Source rows:  {n_source}")
print(f"Matched to geo: {n_matched}")
print(f"Dropped (not in geo): {n_dropped}  — filtered during management/education-level cleaning")

# ── Assemble personnel table ──────────────────────────────────────────────────
personnel = pd.DataFrame({
    "geo_id":             df["geo_id"],
    "year":               2016,
    "enrollment_total":   df["enrollment_total"],
    "enrollment_male":    pd.NA,   # not disaggregated in source
    "enrollment_female":  pd.NA,   # not disaggregated in source
    "teachers_total":     pd.NA,   # not in source file
    "teachers_male":      pd.NA,
    "teachers_female":    pd.NA,
    "teachers_qualified": pd.NA,   # not collected
    "pupil_teacher_ratio": pd.NA,  # cannot compute without teachers_total
    "classrooms_total":   pd.NA,   # not collected
})

# Cast types per schema
personnel["year"]             = personnel["year"].astype(int)
personnel["enrollment_total"] = pd.array(personnel["enrollment_total"], dtype="Int64")

# ── QA ────────────────────────────────────────────────────────────────────────
print()
print("=== BGD_personnel QA ===")
print(f"Total rows: {len(personnel)}")

# Never-null check
for col in ["geo_id", "year"]:
    n = personnel[col].isna().sum()
    status = "OK" if n == 0 else f"WARNING: {n} nulls — schema violation"
    print(f"  {col}: {status}")

print(f"  enrollment_total: {personnel['enrollment_total'].isna().sum()} NA "
      f"({personnel['enrollment_total'].notna().sum()} populated)")
print(f"  enrollment_total range: "
      f"{personnel['enrollment_total'].min()} – {personnel['enrollment_total'].max()}")

# Sanity: any suspiciously large enrollment
big = (personnel["enrollment_total"] > 5000).sum()
if big:
    print(f"  WARNING: {big} schools with enrollment > 5000 — check for row-sum errors")

# Duplicate geo_id (should be unique per schema — one row per school × year)
dupes = personnel.duplicated(subset=["geo_id", "year"]).sum()
print(f"  Duplicate geo_id × year: {dupes}")

# ── Save ─────────────────────────────────────────────────────────────────────
PERSONNEL_COLS = [
    "geo_id", "year",
    "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female",
    "teachers_qualified", "pupil_teacher_ratio", "classrooms_total"
]
personnel[PERSONNEL_COLS].to_csv("/Users/heatherbaier/Documents/research/geo/db/personnel/bgd_personnel.csv", index=False)
print()
print("Saved: BGD_personnel.csv")