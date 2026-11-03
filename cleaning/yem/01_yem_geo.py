"""
01_yem_geo.py
-------------
Cleans the Yemen education facilities register to produce yem_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    Yemen - Education (HDX)
    URL: https://data.humdata.org/dataset/yemen-education
    File: Ymn-Edu-Facility.csv (16,239 rows, 23 columns)
    Provider / data date / license: TODO confirm from the HDX page.
    Latest building-extension year in the file (YEAR_2) is 2009, so the
    register reflects roughly the 2009/10 school year.

Source columns used:
    ID_STL     9-digit facility code (GG DD xx sss). First 2 digits = ID_GOV,
               first 4 = ID_DIST. Unique across all rows -> source_id.
               NOTE: the "STL" label suggests a settlement code, but it is
               unique per row here, so it functions as the facility ID.
    type_edu   basic / Basic and Secondary Education / secondary / miis / unknown
    STATUS     operational status (identical to Sudents_B1 in every row)
    x, y       longitude, latitude (decimal degrees, assumed WGS84)

Source columns NOT used in the geo table:
    YEAR_B, YEAR_2       construction / extension year
    K_B_1..K_B_5         building material per block (candidate for resources)
    L_B_1..L_B_5         builder / funder per block (MOE, SFD, PWP, UNICEF ...)
    gender, sessions     boys/girls/co-ed and shift; no geo schema column
    ID_GOV, ID_DIST      used only for QA against GeoBoundaries joins

Scope / filters (applied in this order):
    1. Drop non-existent facilities. STATUS in
         {under construction, location in the plan, proposition location}
       are planned or unbuilt sites, not schools.
    2. Drop rows with no education level. type_edu in {miis, unknown}
       cannot be mapped to ISCED, and isced_level is never-null. Nearly all
       of these are non-working sites (new, temporarily closed, unknown
       status); see the QA crosstab printed below.
    3. Drop schools outside GeoBoundaries ADM1 (standing project rule).

Sector:
    The file has no management/sector field. It is treated as the MoE
    public school register and every row is set to sector = 'public'.
    L_B_* records who BUILT each block, not who runs the school, so it is
    not used as a sector filter.  -> flag in metadata.

ISCED mapping (Yemen: basic = grades 1-9, secondary = grades 10-12):
    basic                          -> 1|2   (grades 1-6 = ISCED 1, 7-9 = ISCED 2)
    Basic and Secondary Education  -> 1|2|3
    secondary                      -> 3
    This is the nominal cycle. Small rural basic schools may only offer
    the lower grades; no grade-range field exists to check this.

school_name:
    NO school name column exists in the source. school_name is left NA
    (schema violation, flagged in QA). geo_id is therefore assigned by
    sorting on source_id instead of school name (BGD/EIIN precedent).

Status mapping:
    working          -> open
    temporary closed -> closed_temporary
    closed           -> closed_permanent
    unknown          -> unknown

Coordinates:
    x -> longitude, y -> latitude. coordinate_source = 'official_emis',
    coordinate_precision = 'exact'. Collection method is undocumented.
    ~400 rows share an exact coordinate pair with another row (multiple
    schools / shifts on one site). They are kept and reported in QA.

Admin hierarchy:
    adm1-adm3 from GeoBoundaries spatial join (never from source codes).
    ID_GOV / ID_DIST are used only as a consistency check on the join.

Author: HB
Date: 2026-11-02
"""

import os
import sys

import geopandas as gpd
import pandas as pd

# Allow importing from pipeline/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(os.path.join(BASE_DIR, "pipeline"))
from geo_boundaries import join_admin_boundaries  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = os.path.join(BASE_DIR, "sources", "YEM", "ymn-edu-facility", "Ymn-Edu-Facility.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "db", "geo", "yem_geo.csv")

ISO3 = "YEM"

# ── Mappings ──────────────────────────────────────────────────────────────
NOT_YET_SCHOOLS = ["under construction", "location in the plan", "proposition location"]

ISCED_MAP = {
    "basic":                         "1|2",
    "Basic and Secondary Education": "1|2|3",
    "secondary":                     "3",
}

STATUS_MAP = {
    "working":          "open",
    "temporary closed": "closed_temporary",
    "closed":           "closed_permanent",
    "unknown":          "unknown",
}

GEO_COLS = [
    "geo_id", "source_id", "country", "school_name", "school_name_romanized",
    "isced_level", "school_type", "sector", "adm0", "adm1", "adm2", "adm3",
    "urban_rural", "ghsl_smod_code", "ghsl_urban_rural", "latitude", "longitude",
    "coordinate_source", "coordinate_precision", "status",
]

# ── Load ──────────────────────────────────────────────────────────────────
print("Loading source data...")
ID_COLS = ["ID_GOV", "ID_DIST", "ID_STL"]
df = pd.read_csv(SOURCE_FILE, dtype={c: str for c in ID_COLS})
for c in ["type_edu", "STATUS"]:
    df[c] = df[c].astype("string").str.strip()
n_raw = len(df)
print(f"  Raw rows: {n_raw}")

# IDs are read as text. ~3,000 ID_STL values carry float32 precision
# artifacts from the source GIS export (e.g. '240121000.99999997020' is
# 240121001). Round every ID to the nearest integer and report how many
# changed. Off-by-more-than-0.01 values would indicate a real problem.
for c in ID_COLS:
    raw = df[c].str.strip()
    num = pd.to_numeric(raw, errors="coerce")
    assert num.notna().all(), f"ERROR: non-numeric {c}: {raw[num.isna()].unique()[:10]}"
    off = (num - num.round()).abs()
    assert (off < 0.01).all(), f"ERROR: {c} values not near an integer: {raw[off >= 0.01].unique()[:10]}"
    n_fixed = (~raw.str.fullmatch(r"\d+(\.0+)?")).sum()
    if n_fixed:
        print(f"  {c}: rounded {n_fixed} float-artifact values to integers")
    df[c] = num.round().astype("int64").astype(str)

assert df["ID_STL"].notna().all(), "ERROR: null ID_STL in source"
assert not df["ID_STL"].duplicated().any(), "ERROR: duplicate ID_STL in source"

print("\n  STATUS x type_edu (raw):")
print(pd.crosstab(df["STATUS"], df["type_edu"], margins=True).to_string())

# ── Filter 1: planned / unbuilt sites ─────────────────────────────────────
mask_unbuilt = df["STATUS"].isin(NOT_YET_SCHOOLS)
print(f"\n  Dropping {mask_unbuilt.sum()} planned/unbuilt sites "
      f"({', '.join(NOT_YET_SCHOOLS)})")
df = df[~mask_unbuilt].copy()

# ── Filter 2: no mappable education level ─────────────────────────────────
df["isced_level"] = df["type_edu"].map(ISCED_MAP)
mask_nolevel = df["isced_level"].isna()
print(f"  Dropping {mask_nolevel.sum()} rows with no mappable type_edu:")
print(df.loc[mask_nolevel, ["type_edu", "STATUS"]].value_counts().to_string())
df = df[~mask_nolevel].copy()

# ── Status ────────────────────────────────────────────────────────────────
df["status"] = df["STATUS"].map(STATUS_MAP)
unmapped = df.loc[df["status"].isna(), "STATUS"].unique()
assert len(unmapped) == 0, f"ERROR: unmapped STATUS values: {unmapped}"

# ── Coordinates → GeoDataFrame ────────────────────────────────────────────
df["longitude"] = pd.to_numeric(df["x"], errors="coerce")
df["latitude"]  = pd.to_numeric(df["y"], errors="coerce")
n_nocoord = (df["latitude"].isna() | df["longitude"].isna()).sum()
if n_nocoord:
    print(f"  Dropping {n_nocoord} rows with missing coordinates")
df = df.dropna(subset=["latitude", "longitude"]).copy()

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326",
)
print(f"\n  Rows before admin join: {len(gdf)}")

# ── GeoBoundaries admin join ──────────────────────────────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])

# ── Filter 3: outside ADM1 ────────────────────────────────────────────────
mask_out = gdf["adm1"].isna()
if mask_out.sum():
    print(f"\n  Dropping {mask_out.sum()} schools outside GeoBoundaries ADM1:")
    print(gdf.loc[mask_out, ["ID_STL", "ID_GOV", "longitude", "latitude"]].to_string())
gdf = gdf[~mask_out].copy()

# ── geo_id (no names in source → sort by source_id) ──────────────────────
gdf = gdf.sort_values("ID_STL").reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]

# ── Build output ──────────────────────────────────────────────────────────
out = pd.DataFrame(index=gdf.index)
out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["ID_STL"]
out["country"]               = ISO3
out["school_name"]           = pd.NA   # not in source
out["school_name_romanized"] = pd.NA
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["type_edu"]
out["sector"]                = "public"
out["adm0"]                  = "Yemen"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = pd.NA   # no source classification
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["latitude"]
out["longitude"]             = gdf["longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "exact"
out["status"]                = gdf["status"]
out = out[GEO_COLS]

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== YEM_geo QA ===")
print(f"Raw rows:    {n_raw}")
print(f"Output rows: {len(out)}  ({n_raw - len(out)} dropped)")

assert out["geo_id"].is_unique, "ERROR: duplicate geo_id"
assert out["source_id"].is_unique, "ERROR: duplicate source_id"

never_null = ["geo_id", "source_id", "country", "school_name", "isced_level",
              "sector", "adm0", "coordinate_source", "coordinate_precision", "status"]
print("\nNever-null columns:")
for col in never_null:
    n = out[col].isna().sum()
    print(f"  {'WARNING' if n else 'OK':7s} {col}: {n} nulls")

for col in ["isced_level", "school_type", "status", "adm1"]:
    print(f"\n{col}:")
    print(out[col].value_counts(dropna=False).to_string())

for lvl in ["adm2", "adm3"]:
    print(f"\n{lvl}: {out[lvl].nunique()} units, {out[lvl].isna().sum()} NA")

# Consistency of GeoBoundaries join vs source codes (QA only, names never used)
def code_consistency(code_col, adm_col):
    """Share of schools whose gB unit equals the modal gB unit for their source code."""
    tmp = pd.DataFrame({"code": gdf[code_col], "adm": gdf[adm_col]}).dropna()
    modal = tmp.groupby("code")["adm"].agg(lambda s: s.mode().iat[0])
    agree = tmp["adm"].eq(tmp["code"].map(modal))
    return agree.mean(), tmp.loc[~agree, "code"].value_counts()

print("\nSource code vs GeoBoundaries agreement (modal match):")
for code_col, adm_col in [("ID_GOV", "adm1"), ("ID_DIST", "adm2")]:
    share, off = code_consistency(code_col, adm_col)
    print(f"  {code_col} vs {adm_col}: {share:.1%} agree; "
          f"{off.sum()} schools disagree across {len(off)} codes")
    if len(off):
        print("    top codes with disagreement:", off.head(10).to_dict())

shared = out.duplicated(["latitude", "longitude"], keep=False)
print(f"\nSchools sharing an exact coordinate with another school: {shared.sum()} "
      f"({out[shared].groupby(['latitude', 'longitude']).ngroups} sites)")

# ── Save ──────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved {len(out)} rows to {OUTPUT_FILE}")