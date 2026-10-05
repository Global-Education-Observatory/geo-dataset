"""
phl_personnel.py
----------------
Builds phl_personnel.csv (enrollment only for now) conforming to the GEO
Dataset canonical schema v1.0, personnel table.

Source
    DepEd enrollment CSVs, one file per school year, one row per school_id.
    Male/female counts by grade (kinder, g1-g12 by track, plus non-graded).

Year
    Parsed from the file name as the FIRST four-digit number (beginning year of
    the academic year per schema convention, e.g. 2023-2024 -> 2023).
    CONFIRM the file naming so this is right.

Enrollment scope
    Grades 1-12 only, to match the geo table scope (ISCED 1-3).
      ISCED 1  g1-g6 + esng (elementary non-graded)
      ISCED 2  g7-g10 + jhsng (junior high non-graded)
      ISCED 3  g11/g12 across all strands
    Kindergarten is EXCLUDED (ISCED 0, outside V1 scope).
    Male and female are summed separately, total = male + female.
    A school-year with no enrollment values at all is NA, not 0.

Join
    school_id -> geo table source_id -> geo_id. Only schools in phl_geo.csv are
    kept, which also takes care of the public-only scope (the sector column in
    the enrollment files is not used).

Classrooms
    classrooms_total = es + jhs + shs instructional classrooms, from the
    buildings / classrooms file (2023 only for now). NA if all three are blank.
    Non-instructional rooms are not counted, per schema.

Teachers
    teachers_total = headcount of teaching positions from the DepEd staffing
    file (2023 only for now), summed across the levels offered.
      Counted      master teacher, teacher I-III, SPED/SNED teacher, instructor,
                   special science teacher (ES, JHS, SHS), plus locally funded
                   teachers (SEF province, SEF municipality/city, LGU, other) for
                   ES, JHS and SHS. Set INCLUDE_LOCALLY_FUNDED = False to drop them.
      Not counted  principals, assistant principals, head teachers, guidance,
                   librarians, nurses, admin and support staff, locally funded
                   kinder teachers (UIS excludes school heads unless they teach).
    NA if every counted column is blank. Blanks are 0 when at least one counted
    column has a value.
    pupil_teacher_ratio = enrollment_total / teachers_total, NA if either is NA
    or teachers_total is 0.

Not available from this source (NA)
    teachers_male, teachers_female, teachers_qualified (file has position titles
    only, no sex and no qualification)

Author: HB
"""

import os
import re
import glob
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────
ISO3 = "PHL"
ENROLL_GLOB = "../../sources/PHL/enrollment/Enrollment in SY */*.csv"   # TODO confirm
CLASSROOM_FILES = {
    2023: "../../sources/PHL/School Facilities in SY 2023-2024/facilities_2023-24.csv",   # TODO confirm
}
TEACHER_FILES = {
    2023: "../../sources/PHL/School Personnel in SY 2023-2024/personnel_2023-24.csv",   # TODO confirm
}
INCLUDE_LOCALLY_FUNDED = True
GEO_FILE    = "../../db/geo/phl_geo.csv"
OUTPUT_FILE = "../../db/personnel/phl_personnel.csv"

# ── Enrollment columns ────────────────────────────────────────────────────
GRADE_STEMS = (
    [f"g{i}" for i in range(1, 7)] + ["esng"]              # ISCED 1
    + [f"g{i}" for i in range(7, 11)] + ["jhsng"]          # ISCED 2
    + [f"g{g}_{s}" for g in (11, 12)                       # ISCED 3
       for s in ("abm", "arts", "gas", "humss", "maritime",
                 "sports", "stem", "tvl", "unique")]
)
MALE_COLS   = [f"{s}_male"   for s in GRADE_STEMS]
FEMALE_COLS = [f"{s}_female" for s in GRADE_STEMS]

# ── Load geo register ─────────────────────────────────────────────────────
geo = pd.read_csv(GEO_FILE, dtype=str, usecols=["geo_id", "source_id"])
print(f"Geo schools: {len(geo)}")

# ── Load and stack enrollment files ───────────────────────────────────────
frames = []
for path in sorted(glob.glob(ENROLL_GLOB)):
    m = re.search(r"(\d{4})", os.path.basename(path))
    if not m:
        print(f"  WARNING: no year in file name, skipping {path}")
        continue
    year = int(m.group(1))

    d = pd.read_csv(path, dtype={"school_id": str})
    d["school_id"] = d["school_id"].str.strip()

    missing = [c for c in MALE_COLS + FEMALE_COLS if c not in d.columns]
    if missing:
        print(f"  WARNING: {os.path.basename(path)} missing columns {missing}; treated as absent")

    male   = d[[c for c in MALE_COLS   if c in d.columns]].apply(pd.to_numeric, errors="coerce")
    female = d[[c for c in FEMALE_COLS if c in d.columns]].apply(pd.to_numeric, errors="coerce")

    out = pd.DataFrame({
        "source_id":         d["school_id"],
        "year":              year,
        "enrollment_male":   male.sum(axis=1, min_count=1),
        "enrollment_female": female.sum(axis=1, min_count=1),
    })
    frames.append(out)
    print(f"  {os.path.basename(path)}  year={year}  rows={len(out)}")

enr = pd.concat(frames, ignore_index=True)

dupes = enr.duplicated(["source_id", "year"]).sum()
if dupes:
    print(f"  WARNING: {dupes} duplicate school_id x year rows. Keeping first.")
    enr = enr.drop_duplicates(["source_id", "year"], keep="first")

# ── Classrooms ────────────────────────────────────────────────────────────
CLASS_COLS = ["es_classrooms_instructional", "jhs_classrooms_instructional", "shs_classrooms_instructional"]
cframes = []
for year, path in CLASSROOM_FILES.items():
    c = pd.read_csv(path, dtype={"school_id": str})
    c["school_id"] = c["school_id"].str.strip()
    vals = c[CLASS_COLS].apply(pd.to_numeric, errors="coerce")
    cframes.append(pd.DataFrame({
        "source_id":        c["school_id"],
        "year":             year,
        "classrooms_total": vals.sum(axis=1, min_count=1),
    }))
    print(f"  classrooms year={year}  rows={len(c)}  {os.path.basename(path)}")

if cframes:
    cls = pd.concat(cframes, ignore_index=True)
    cd = cls.duplicated(["source_id", "year"]).sum()
    if cd:
        print(f"  WARNING: {cd} duplicate classroom rows. Keeping first.")
        cls = cls.drop_duplicates(["source_id", "year"], keep="first")
    enr = enr.merge(cls, on=["source_id", "year"], how="outer")
else:
    enr["classrooms_total"] = pd.NA

# ── Teachers ──────────────────────────────────────────────────────────────
RANKS_IV  = ["iv", "iii", "ii", "i"]
RANKS_V   = ["v", "iv", "iii", "ii", "i"]
TEACHER_COLS = (
    [f"es_master_teacher_{r}" for r in RANKS_IV]
    + [f"es_teacher_{r}" for r in ("iii", "ii", "i")]
    + [f"es_sped_sned_teacher_{r}" for r in RANKS_V]
    + [f"jhs_instructor_{r}" for r in ("iii", "ii", "i")]
    + [f"jhs_master_teacher_{r}" for r in RANKS_IV]
    + [f"jhs_teacher_{r}" for r in ("iii", "ii", "i")]
    + ["jhs_special_science_teacher_i"]
    + [f"jhs_sped_teacher_{r}" for r in RANKS_V]
    + [f"shs_master_teacher_{r}" for r in RANKS_IV]
    + [f"shs_teacher_{r}" for r in ("iii", "ii", "i")]
    + ["shs_special_science_teacher_i"]
)
if INCLUDE_LOCALLY_FUNDED:
    TEACHER_COLS += [f"{lv}_teachers_{f}" for lv in ("es", "jhs", "shs")
                     for f in ("sef_province", "sef_municipality_city", "lgu_funding", "other_funding")]

tframes = []
for year, path in TEACHER_FILES.items():
    t = pd.read_csv(path, dtype={"school_id": str})
    t["school_id"] = t["school_id"].str.strip()
    absent = [c for c in TEACHER_COLS if c not in t.columns]
    if absent:
        print(f"  WARNING: teacher file missing columns {absent}")
    vals = t[[c for c in TEACHER_COLS if c in t.columns]].apply(pd.to_numeric, errors="coerce")
    tframes.append(pd.DataFrame({
        "source_id":      t["school_id"],
        "year":           year,
        "teachers_total": vals.sum(axis=1, min_count=1),
    }))
    print(f"  teachers year={year}  rows={len(t)}  {os.path.basename(path)}")

if tframes:
    tch = pd.concat(tframes, ignore_index=True)
    td = tch.duplicated(["source_id", "year"]).sum()
    if td:
        print(f"  WARNING: {td} duplicate teacher rows. Keeping first.")
        tch = tch.drop_duplicates(["source_id", "year"], keep="first")
    enr = enr.merge(tch, on=["source_id", "year"], how="outer")
else:
    enr["teachers_total"] = pd.NA

# total = male + female, NA only if both are NA
enr["enrollment_total"] = enr[["enrollment_male", "enrollment_female"]].sum(axis=1, min_count=1)

# ── Join to geo_id ────────────────────────────────────────────────────────
n_before = len(enr)
enr = enr.merge(geo, on="source_id", how="inner")
print(f"\nEnrollment rows: {n_before}  matched to geo: {len(enr)}  "
      f"not in geo (dropped): {n_before - len(enr)}")
print(f"Geo schools with at least one enrollment row: {enr['geo_id'].nunique()} of {len(geo)}")

# ── Build output in schema order ──────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]              = enr["geo_id"]
out["year"]                = enr["year"].astype("Int64")
out["enrollment_total"]    = enr["enrollment_total"].astype("Int64")
out["enrollment_male"]     = enr["enrollment_male"].astype("Int64")
out["enrollment_female"]   = enr["enrollment_female"].astype("Int64")
out["teachers_total"]      = enr["teachers_total"].astype("Int64")
out["teachers_male"]       = pd.NA
out["teachers_female"]     = pd.NA
out["teachers_qualified"]  = pd.NA
out["pupil_teacher_ratio"] = (enr["enrollment_total"] / enr["teachers_total"].where(enr["teachers_total"] > 0)).astype("Float64")
out["classrooms_total"]    = enr["classrooms_total"].astype("Int64")

out = out.sort_values(["geo_id", "year"]).reset_index(drop=True)

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== PHL_personnel QA ===")
print(f"Total rows: {len(out)}")
print(f"Duplicate geo_id x year: {out.duplicated(['geo_id', 'year']).sum()}")
for col in ["geo_id", "year"]:
    print(f"  {'WARNING' if out[col].isna().any() else 'OK'}: {col} nulls = {out[col].isna().sum()}")
print(f"teachers_total NA: {out['teachers_total'].isna().sum()}  zero: {(out['teachers_total'] == 0).sum()}")
print(f"pupil_teacher_ratio summary:\n{out['pupil_teacher_ratio'].describe()}")
print(f"enrollment_total NA: {out['enrollment_total'].isna().sum()}  zero: {(out['enrollment_total'] == 0).sum()}")
print("\nRows per year:")
print(out["year"].value_counts().sort_index())
print("\nenrollment_total summary:")
print(out["enrollment_total"].describe())

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE}")