"""
bgd_geo.py
Builds BGD_geo.csv from schools_final_coords.csv
GEO Dataset canonical schema v1.0
"""

import pandas as pd
import numpy as np

# ── Input ────────────────────────────────────────────────────────────────────
df = pd.read_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/schools_final_coords.csv")

# ── geo_id ───────────────────────────────────────────────────────────────────
# Assign BGD_{zero-padded integer} in order of EIIN (stable, reproducible)
df = df.sort_values("EIIN").reset_index(drop=True)
df["geo_id"] = ["BGD_" + str(i + 1).zfill(6) for i in df.index]

# ── source_id ────────────────────────────────────────────────────────────────
# EIIN is the national MoE identifier — retain verbatim as string
df["source_id"] = df["EIIN"].astype(str)

# ── country ──────────────────────────────────────────────────────────────────
df["country"] = "BGD"

# ── school_name ──────────────────────────────────────────────────────────────
# Names are already in Latin script (romanized Bengali) in the EMIS
df["school_name"] = df["INSTITUTE NAME"].str.strip()

# ── school_name_romanized ────────────────────────────────────────────────────
# Source is already Latin script — field is NA per schema rule
df["school_name_romanized"] = pd.NA

# ── isced_level ──────────────────────────────────────────────────────────────
# Harmonization note: Bangladesh madrasha levels mapped as follows:
#   Dakhil       → ISCED 2 (equivalent to Secondary/JSC-SSC level)
#   Alim         → ISCED 3 (equivalent to Higher Secondary/HSC level)
#   Junior Secondary → ISCED 2
#   TECHNICAL SCHOOL AND COLLEGE → ISCED 3
#   H.S.C (B.M Independent)     → ISCED 3
ISCED_MAP = {
    "Dakhil":                        "2",
    "Alim":                          "3",
    "Junior Secondary":              "2",
    "TECHNICAL SCHOOL AND COLLEGE":  "3",
    "H.S.C (B.M Independent)":       "3",
}
df["isced_level"] = df["EDUCATION_LEVEL"].map(ISCED_MAP)

# ── school_type ───────────────────────────────────────────────────────────────
# Retain national EMIS classification verbatim
df["school_type"] = df["INSTITUTE_TYPE"].str.strip()

# ── sector ───────────────────────────────────────────────────────────────────
# Harmonization note: Bangladesh uses an MPO (Monthly Pay Order) system where
# the majority of schools are classified as NON-GOVERNMENT in the EMIS but
# receive government salary funding. All schools in this dataset are either
# fully government-managed or MPO-subsidised and appear in the national EMIS
# as managed institutions. Sector = 'public' for all rows.
df["sector"] = "public"

# ── adm0 ─────────────────────────────────────────────────────────────────────
df["adm0"] = "Bangladesh"

# ── adm1–adm3 ────────────────────────────────────────────────────────────────
# Using gB-matched names from fuzzy matching step (adm1, adm2, adm3 columns)
df["adm1"] = df["adm1"].str.strip()
df["adm2"] = df["adm2"].str.strip()
df["adm3"] = df["adm3"].str.strip()

# ── urban_rural ───────────────────────────────────────────────────────────────
# Map from AREA_STATUS using country-reported classification
# Harmonization note: 'UPZILA SADAR MUNICIPALITY', 'DISTRICT SADAR MUNICIPALITY',
# 'METROPOLITAN', 'OTHER MUNICIPALITY AREA', 'CityCorp' → urban
# 'UPZILA SADAR BUT NOT MUNICIPALITY' → peri_urban
# ' RURAL' → rural
URBAN_RURAL_MAP = {
    " RURAL":                          "rural",
    "UPZILA SADAR MUNICIPALITY":       "urban",
    "UPZILA SADAR BUT NOT MUNICIPALITY": "peri_urban",
    "METROPOLITAN":                    "urban",
    "DISTRICT SADAR MUNICIPALITY":     "urban",
    "OTHER MUNICIPALITY AREA":         "urban",
    "CityCorp":                        "urban",
}
df["urban_rural"] = df["AREA_STATUS"].map(URBAN_RURAL_MAP)

# ── GHSL columns (not yet applied) ───────────────────────────────────────────
df["ghsl_smod_code"]  = pd.NA
df["ghsl_urban_rural"] = pd.NA

# ── coordinates ──────────────────────────────────────────────────────────────
df["latitude"]  = pd.to_numeric(df["final_lat"], errors="coerce")
df["longitude"] = pd.to_numeric(df["final_lon"], errors="coerce")


df = df[~df["latitude"].isna()]
df = df[~df["longitude"].isna()]


# ── coordinate_source & coordinate_precision ─────────────────────────────────
# Already assigned in schools_final_coords.csv — carry through directly
df["coordinate_source"]    = df["coordinate_source"]
df["coordinate_precision"] = df["coordinate_precision"]


# ── status ───────────────────────────────────────────────────────────────────
# Harmonization note: no operational status field in the Bangladesh EMIS source.
# All schools in the EMIS register are assumed open at time of data collection.
# Status set to 'open' for all rows.
df["status"] = "open"

# ── Assemble output in schema column order ────────────────────────────────────
GEO_COLS = [
    "geo_id",
    "source_id",
    "country",
    "school_name",
    "school_name_romanized",
    "isced_level",
    "school_type",
    "sector",
    "adm0",
    "adm1",
    "adm2",
    "adm3",
    "urban_rural",
    "ghsl_smod_code",
    "ghsl_urban_rural",
    "latitude",
    "longitude",
    "coordinate_source",
    "coordinate_precision",
    "status",
]

geo = df[GEO_COLS].copy()

# ── QA checks ────────────────────────────────────────────────────────────────
print("=== BGD_geo QA ===")
print(f"Total rows: {len(geo)}")
print()

# Never-null columns
never_null = ["geo_id", "source_id", "country", "school_name",
              "isced_level", "sector", "adm0", "coordinate_source",
              "coordinate_precision", "status"]
for col in never_null:
    n = geo[col].isna().sum()
    if n > 0:
        print(f"  WARNING: {col} has {n} null values — schema violation")
    else:
        print(f"  OK: {col} — no nulls")

print()
print("isced_level distribution:")
print(geo["isced_level"].value_counts())
print()
print("coordinate_source distribution:")
print(geo["coordinate_source"].value_counts())
print()
print("coordinate_precision distribution:")
print(geo["coordinate_precision"].value_counts())
print()
print("urban_rural distribution:")
print(geo["urban_rural"].value_counts())
print()
print(f"Missing latitude:  {geo['latitude'].isna().sum()}")
print(f"Missing longitude: {geo['longitude'].isna().sum()}")
print()

# geo_id uniqueness
dupes = geo["geo_id"].duplicated().sum()
print(f"Duplicate geo_ids: {dupes}")

# ── Save ─────────────────────────────────────────────────────────────────────
geo.to_csv("/Users/heatherbaier/Documents/research/geo/db/geo/bgd_geo.csv", index=False)
print()
print("Saved: BGD_geo.csv")
