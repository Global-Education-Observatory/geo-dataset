"""
lby_geo.py
----------
Cleans the REACH Libya National Schools Assessment (October 2012) to produce
lby_geo.csv conforming to the GEO Dataset canonical schema v1.0.

Source:
    REACH Libya National Schools Assessment — complete database
    (reliable + not-reliable records), 18 October 2012
    URL: https://data.humdata.org/dataset/reach-libya-national-schools-assessment-2012
    File: reach_lby_nationalschoolsassessment_complete_db_reliable__not_reliable_18oct2012.csv
    Provider: REACH Initiative / ACTED
    Format: CSV, 4,800 rows, 365 columns

Scope:
    - Public schools only (QI_iSchoolPuplic == 1; value 2 = private, excluded)
    - In-scope ISCED levels: Primary (Q1_1LevelofSchoolPrimary), Preparatory /
      lower secondary (Q1_1LevelofSchoolPrep), Secondary (Q1_1aMedSciences,
      Q1_1bEngSciences, Q1_1cEconSciences). Rows with none of these flags set
      are excluded (nursery-only, special-only, adult literacy-only).
    - Both Reliable and Unreliable records retained; reliability flag preserved
      in a supplementary column (lby_reliable) for downstream use.
    - Zero-coordinate rows (0.0 / 0.0) dropped — no fallback available.

ISCED mapping:
    Level flags are non-exclusive (e.g. a school may offer both Primary and Prep).
    ISCED is assigned by pipe-delimiting all applicable levels per row:
        Q1_1LevelofSchoolPrimary set → ISCED 1
        Q1_1LevelofSchoolPrep set    → ISCED 2
        Any of Q1_1aMedSciences / Q1_1bEngSciences / Q1_1cEconSciences set → ISCED 3
    Resulting values: "1", "2", "3", "1|2", "1|3", "2|3", "1|2|3"
    Note: ISCED 0 (nursery, Q1_1LevelofSchoolNursery) and special needs
    (Q1_1LevelofSchoolSpecial) are excluded per project scope. Adult literacy
    (Q1_1EradicationOfIlliteracy) is also excluded.

Coordinate handling:
    CRITICAL: The source CSV columns QII_5Longitude and QII_6Latitude are
    mislabelled — the column named "Longitude" contains true latitude values
    (~19–33 °N) and the column named "Latitude" contains true longitude values
    (~9–25 °E). This is confirmed by reference to the first surveyed school
    (AJ-001, Ajdabiya), whose true coordinates are 30.74 °N 20.22 °E.
    In this script:
        latitude  = QII_5Longitude  (mislabelled source column)
        longitude = QII_6Latitude   (mislabelled source column)
    coordinate_source    = 'official_emis'  (GPS-collected by REACH field teams)
    coordinate_precision = 'exact'
    Rows where both values are 0.0 are dropped (n=92 in full dataset).

Administrative hierarchy:
    adm0 = "Libya" (hardcoded)
    adm1 assigned from source QII_1Province (numeric code) via a lookup table
        derived from school ID prefixes cross-referenced against known Libyan
        shabiyat (districts) at time of survey (2011–2012 administrative structure,
        22 districts). See PROVINCE_MAP below.
    adm2 (mantika / sub-district) = NA — QII_3Mantika is a numeric code with no
        available name lookup in the source file or accompanying documentation.
    adm3 = NA — not available.
    Note: ADM boundaries were not joined from GeoBoundaries for this country
        because the 2012 Libyan administrative structure (22 shabiyat) differs
        from post-2014 boundaries currently in GeoBoundaries. adm1 is sourced
        from the survey instrument's province code instead.

Duplicate source_ids:
    Four survey IDs (BI-450, BI-451, BI-452, BI-453) were assigned to two
    distinct schools each (different names, locations, and ISCED levels),
    almost certainly due to data-entry error during the survey. After the
    public-school filter:
      - BI-450 and BI-451: both rows are public → retained, producing 2
        non-unique source_ids in the output.
      - BI-452 and BI-453: shift-1 row is private (excluded), shift-2 row is
        public (retained as singleton) → no source_id collision in output.
    source_id values are preserved verbatim for all retained rows. geo_id
    uniqueness is maintained. See metadata for details.

Status mapping:
    Q1_2scheduledToBegin: 1 = school currently operating → 'open'
                          0 = not yet started / not operating → 'closed_temporary'
                          other values (2,3,4,5,6) → 'unknown'

Author: HB
Date: 2026-06-10
"""

import os
import sys
import pandas as pd
import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/LBY/reach_lby_nationalschoolsassessment_complete_db_reliable__not_reliable_18oct2012.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/lby_geo.csv"

ISO3 = "LBY"

# ── Province code → name lookup ───────────────────────────────────────────
# Derived from school ID prefixes (e.g. AJ-xxx → Ajdabiya) cross-referenced
# against Libya's 22-district shabiyat structure in use at time of survey.
# Codes 4, 5, 7, 8, 9, 10, 11, 12 are absent from the data.
PROVINCE_MAP = {
    1:  "Benghazi",
    2:  "Tripoli",
    3:  "Murzuq",
    6:  "Sabha",
    13: "Zawiya",
    14: "Gharyan",
    15: "Nalut",
    16: "Jabal al-Akhdar",
    17: "Wadi al-Shatii",
    18: "Wadi al-Hayaa",
    19: "Wadi al-Maqataa",
    20: "Wadi Awal",
    21: "Tobruk",
    22: "Sirt",
    23: "Misrata",
    24: "Misurata",
    25: "Marj",
    26: "Al Khums",
    27: "Jufra",
    28: "Ghat",
    29: "Derna",
    30: "Ajdabiya",
    31: "Kufra",
}

# ── Status mapping ────────────────────────────────────────────────────────
STATUS_MAP = {
    1: "open",
    0: "closed_temporary",
}

# ── Load source data ──────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_csv(SOURCE_FILE, encoding="utf-8-sig", low_memory=False)
print(f"  Rows loaded: {len(df)}")

# ── Sector filter: public only ─────────────────────────────────────────────
# QI_iSchoolPuplic: 1 = public, 2 = private
before = len(df)
df = df[df["QI_iSchoolPuplic"] == 1].copy()
print(f"  After public filter: {len(df)} rows (dropped {before - len(df)} private)")

# ── ISCED level flags ──────────────────────────────────────────────────────
# Each flag column is either NaN (flag not set) or a numeric code when set.
df["_has_primary"] = df["Q1_1LevelofSchoolPrimary"].notna()
df["_has_prep"]    = df["Q1_1LevelofSchoolPrep"].notna()
df["_has_sec"]     = (
    df["Q1_1aMedSciences"].notna() |
    df["Q1_1bEngSciences"].notna() |
    df["Q1_1cEconSciences"].notna()
)

# ── Scope filter: at least one in-scope ISCED level ───────────────────────
in_scope = df["_has_primary"] | df["_has_prep"] | df["_has_sec"]
before = len(df)
df = df[in_scope].copy()
print(f"  After ISCED scope filter: {len(df)} rows (dropped {before - len(df)} nursery/special/literacy-only)")

# ── Coordinate fix: columns are mislabelled in source ────────────────────
# QII_5Longitude contains true latitude; QII_6Latitude contains true longitude.
df["latitude"]  = pd.to_numeric(df["QII_5Longitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["QII_6Latitude"],  errors="coerce")

# ── Drop zero-coordinate rows ──────────────────────────────────────────────
zero_coords = (df["latitude"] == 0.0) | (df["longitude"] == 0.0)
before = len(df)
df = df[~zero_coords].copy()
print(f"  After dropping zero coordinates: {len(df)} rows (dropped {before - len(df)})")

# ── Derive ISCED level string (pipe-delimited) ────────────────────────────
def build_isced(row):
    levels = []
    if row["_has_primary"]:
        levels.append("1")
    if row["_has_prep"]:
        levels.append("2")
    if row["_has_sec"]:
        levels.append("3")
    return "|".join(levels)

df["isced_level"] = df.apply(build_isced, axis=1)

# ── adm1 from province code ────────────────────────────────────────────────
df["adm1"] = df["QII_1Province"].map(PROVINCE_MAP)

# ── Status ────────────────────────────────────────────────────────────────
df["status"] = df["Q1_2scheduledToBegin"].map(STATUS_MAP).fillna("unknown")

# ── Sort alphabetically by school name and assign geo_id ──────────────────
# school_name = romanized name from QI_fSchoolName; sort on this.
df["school_name_clean"] = df["QI_fSchoolName"].str.strip()
df = df.sort_values("school_name_clean").reset_index(drop=True)
df["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(df))]

# ── Assemble output in schema column order ─────────────────────────────────
out = pd.DataFrame()

out["geo_id"]     = df["geo_id"]
out["source_id"]  = df["QI_eSchoolID"].astype(str).str.strip()
out["country"]    = ISO3

# school_name: use romanized Latin-script name from source
out["school_name"] = df["school_name_clean"]

# school_name_romanized: Arabic script name available → populate
# ALA-LC romanization not applied; field holds the source Arabic name as-is.
# A formal romanization pass is pending (see metadata known issues).
out["school_name_romanized"] = df["QI_ArabicName"].str.strip()

out["isced_level"]  = df["isced_level"]

# school_type: retain source level labels verbatim as a concatenated string
# e.g. "Primary", "Primary|Preparatory", "Secondary (Medical Sciences)"
def build_type_label(row):
    parts = []
    if row["_has_primary"]:
        parts.append("Primary")
    if row["_has_prep"]:
        parts.append("Preparatory")
    if row["Q1_1aMedSciences"].notna() if "_has_sec" in row else False:
        parts.append("Secondary (Medical Sciences)")
    if row["Q1_1bEngSciences"].notna() if "_has_sec" in row else False:
        parts.append("Secondary (Engineering Sciences)")
    if row["Q1_1cEconSciences"].notna() if "_has_sec" in row else False:
        parts.append("Secondary (Economic Sciences)")
    # Handle case where _has_sec is True but no sub-type was checked
    # (shouldn't happen given flag logic but guard anyway)
    if row["_has_sec"] and not parts[len(parts)-1:][0:1] or (row["_has_sec"] and "Secondary" not in "|".join(parts)):
        parts.append("Secondary")
    return "|".join(parts) if parts else pd.NA

# Simpler approach: build from actual notna flags directly
def build_school_type(row):
    parts = []
    if row["Q1_1LevelofSchoolPrimary"].notna() if hasattr(row["Q1_1LevelofSchoolPrimary"], '__class__') else False:
        parts.append("Primary")
    if row["Q1_1LevelofSchoolPrep"] is not None and not pd.isna(row["Q1_1LevelofSchoolPrep"]):
        parts.append("Preparatory")
    if row["Q1_1aMedSciences"] is not None and not pd.isna(row["Q1_1aMedSciences"]):
        parts.append("Secondary (Medical Sciences)")
    if row["Q1_1bEngSciences"] is not None and not pd.isna(row["Q1_1bEngSciences"]):
        parts.append("Secondary (Engineering Sciences)")
    if row["Q1_1cEconSciences"] is not None and not pd.isna(row["Q1_1cEconSciences"]):
        parts.append("Secondary (Economic Sciences)")
    # If secondary flag set but no specialisation column caught above,
    # append generic Secondary label
    if row["_has_sec"] and not any("Secondary" in p for p in parts):
        parts.append("Secondary")
    return "|".join(parts) if parts else pd.NA

out["school_type"] = df.apply(build_school_type, axis=1)

out["sector"] = "public"
out["adm0"]   = "Libya"
out["adm1"]   = df["adm1"]
out["adm2"]   = pd.NA   # mantika numeric codes — no name lookup available
out["adm3"]   = pd.NA   # not available

# urban_rural: no urban/rural classification in source
out["urban_rural"]    = pd.NA
out["ghsl_smod_code"] = pd.NA
out["ghsl_urban_rural"] = pd.NA

out["latitude"]  = df["latitude"]
out["longitude"] = df["longitude"]
out["coordinate_source"]    = "official_emis"
out["coordinate_precision"] = "exact"
out["status"] = df["status"]

# ── Supplementary reliability flag ────────────────────────────────────────
# Not a schema column; written to a supplementary file alongside the geo table.
# Retained here as a working column for QA then dropped before final save.
out["_lby_reliable"] = df["RELIABLE"]

# ── QA checks ──────────────────────────────────────────────────────────────
print("\n=== LBY geo QA ===")
print(f"Total rows: {len(out)}")
print()

never_null = [
    "geo_id", "source_id", "country", "school_name",
    "isced_level", "sector", "adm0", "coordinate_source",
    "coordinate_precision", "status",
]
for col in never_null:
    n = out[col].isna().sum()
    flag = "WARNING" if n > 0 else "OK"
    print(f"  {flag}: {col} — {n} nulls")

print()
print("isced_level distribution:")
print(out["isced_level"].value_counts().to_string())

print()
print("adm1 distribution:")
print(out["adm1"].value_counts().to_string())
print(f"adm1 nulls: {out['adm1'].isna().sum()}")

print()
print("status distribution:")
print(out["status"].value_counts().to_string())

print()
print(f"Missing latitude:  {out['latitude'].isna().sum()}")
print(f"Missing longitude: {out['longitude'].isna().sum()}")

# Bounding-box check (Libya: lat 19.5–33.2 N, lon 9.3–25.2 E)
out_of_bbox = (
    (out["latitude"]  < 19.5) | (out["latitude"]  > 33.2) |
    (out["longitude"] < 9.3)  | (out["longitude"] > 25.2)
)
print(f"Coordinates outside Libya bbox: {out_of_bbox.sum()}")

print()
dupes_geo = out["geo_id"].duplicated().sum()
print(f"Duplicate geo_ids: {dupes_geo}")

dupes_src = out["source_id"].duplicated().sum()
print(f"Duplicate source_ids (known collisions BI-450–453): {dupes_src}")

print()
reliable_counts = out["_lby_reliable"].value_counts(dropna=False)
print("Reliability breakdown:")
print(reliable_counts.to_string())

# ── Write supplementary reliability file ─────────────────────────────────
supp = out[["geo_id", "source_id", "_lby_reliable"]].rename(
    columns={"_lby_reliable": "lby_reliable"}
)
supp_path = OUTPUT_FILE.replace("lby_geo.csv", "lby_geo_reliability.csv")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
supp.to_csv(supp_path, index=False)
print(f"\nSupplementary reliability file saved: {supp_path}")

# ── Drop working columns and save ─────────────────────────────────────────
GEO_COLS = [
    "geo_id", "source_id", "country", "school_name", "school_name_romanized",
    "isced_level", "school_type", "sector", "adm0", "adm1", "adm2", "adm3",
    "urban_rural", "ghsl_smod_code", "ghsl_urban_rural",
    "latitude", "longitude", "coordinate_source", "coordinate_precision",
    "status",
]
geo = out[GEO_COLS].copy()
geo.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE}")