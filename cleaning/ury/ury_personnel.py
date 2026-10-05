"""
02_ury_personnel.py
-------------------
Builds ury_personnel.csv conforming to the GEO Dataset canonical schema v1.0.

Source:
    ANEP - SIGANEP Oferta educativa, DGEIP.xlsx (initial + primary)
    https://catalogodatos.gub.uy/dataset/anep-http-sig-anep-edu-uy-siganep-formatos

Coverage:
    DGEIP (primary) only. DGES (secondary) has no data in matricula or
    cant_aulas (0% non-null, verified), so DGES schools receive no personnel
    rows (they remain in the geo table only).

Fields populated:
    enrollment_total  <- matricula
    classrooms_total  <- cant_aulas, NA where cant_aulas == 0 and matricula > 0
                         (students but no classrooms = not recorded)

Fields NA for all rows:
    enrollment_male, enrollment_female  - not disaggregated by sex in source
    teachers_total/male/female/qualified - total_docentes is entirely empty
    pupil_teacher_ratio                 - cannot compute without teachers_total

Known limitation:
    matricula appears to include nivel inicial (ISCED 0) children in some
    primary schools (pnofrece2 = '3 AÑOS' / '4 AÑOS'). Not separable in source.

Join:
    geo_id is assigned in ury_geo.py after cleaning, so it is joined here from
    ury_geo.csv on source_id. Schools dropped from the geo table (jardines,
    no coordinates, outside ADM1) drop out of personnel automatically.

Year:
    PROVISIONAL. Inferred from file modified date (2023-08-30), reference year
    unconfirmed with ANEP. Uruguay's school year starts in March, so this is
    treated as the 2023/24 beginning-year convention = 2023.

Author: HB
Date: 2026-10-02
"""

import os
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
BASE        = "/Users/heatherbaier/Documents/research/geo/geo-dataset"
DGEIP_FILE  = os.path.join(BASE, "sources/URY/centros_anep/DGEIP.xlsx")
GEO_FILE    = os.path.join(BASE, "db/geo/ury_geo.csv")
OUTPUT_FILE = os.path.join(BASE, "db/personnel/ury_personnel.csv")

YEAR = 2023   # PROVISIONAL, see docstring

PERSONNEL_COLS = [
    "geo_id", "year",
    "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female", "teachers_qualified",
    "pupil_teacher_ratio", "classrooms_total",
]

# ── Load ──────────────────────────────────────────────────────────────────
print("Loading sources...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str})
src = pd.read_excel(DGEIP_FILE)
src.columns = src.columns.str.lower()
print(f"  geo rows: {len(geo)}   DGEIP rows: {len(src)}")

# Same source_id construction as ury_geo.py
src["source_id"] = pd.to_numeric(src["ruee"]).astype("Int64").astype(str)

# geo_id lookup must be one-to-one
assert geo["source_id"].is_unique, "ERROR: source_id not unique in ury_geo.csv"
assert src["source_id"].is_unique, "ERROR: source_id not unique in DGEIP"

# Inner join keeps only schools that survived geo cleaning
df = src.merge(geo[["geo_id", "source_id"]], on="source_id", how="inner")
print(f"  DGEIP schools matched to geo: {len(df)} "
      f"({len(src) - len(df)} DGEIP rows not in geo: jardines, no coords, outside ADM1, etc.)")

# ── Build personnel table ─────────────────────────────────────────────────
mat = pd.to_numeric(df["matricula"], errors="coerce")
aul = pd.to_numeric(df["cant_aulas"], errors="coerce")

# Students but zero classrooms = not recorded -> NA
aul = aul.where(~((aul == 0) & (mat > 0)))

out = pd.DataFrame({
    "geo_id":              df["geo_id"],
    "year":                YEAR,
    "enrollment_total":    mat.astype("Int64"),
    "enrollment_male":     pd.array([pd.NA] * len(df), dtype="Int64"),
    "enrollment_female":   pd.array([pd.NA] * len(df), dtype="Int64"),
    "teachers_total":      pd.array([pd.NA] * len(df), dtype="Int64"),
    "teachers_male":       pd.array([pd.NA] * len(df), dtype="Int64"),
    "teachers_female":     pd.array([pd.NA] * len(df), dtype="Int64"),
    "teachers_qualified":  pd.array([pd.NA] * len(df), dtype="Int64"),
    "pupil_teacher_ratio": np.nan,
    "classrooms_total":    aul.astype("Int64"),
})

# Schools with no table data are excluded rather than given null rows
no_data = out["enrollment_total"].isna() & out["classrooms_total"].isna()
print(f"  Dropped {no_data.sum()} schools with no personnel data")
out = out[~no_data]

out = out[PERSONNEL_COLS].sort_values("geo_id").reset_index(drop=True)

# ── Validation checks ─────────────────────────────────────────────────────
print("\nRunning validation checks...")

assert out["geo_id"].notna().all(), "ERROR: Null geo_ids"
assert out["year"].notna().all(), "ERROR: Null year"
assert not out.duplicated(["geo_id", "year"]).any(), "ERROR: Duplicate geo_id x year"
assert out["geo_id"].isin(geo["geo_id"]).all(), "ERROR: geo_id not in geo table"
assert (out["enrollment_total"].dropna() >= 0).all(), "ERROR: Negative enrollment"

print(f"\n  Total personnel rows: {len(out)}")
print(f"  Schools in geo table: {len(geo)} (DGES schools have no personnel rows)")
print(f"  enrollment_total non-null: {out['enrollment_total'].notna().sum()}")
print(f"  enrollment_total == 0:     {(out['enrollment_total'] == 0).sum()}")
print(f"  classrooms_total non-null: {out['classrooms_total'].notna().sum()}")
print(f"  classrooms_total == 0:     {(out['classrooms_total'] == 0).sum()}")
print(f"  enrollment_total summary:\n{out['enrollment_total'].astype(float).describe()}")

# ── Save output ───────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")