"""
gtm_geo.py
----------
Builds GTM_geo.csv from the pooled Guatemala EMIS establecimientos files,
conforming to the GEO Dataset canonical schema v1.0.

Sources:
    Guatemala Ministry of Education — Establecimientos Educativos
    Files: establecimientos_2013-2014.csv, establecimientos_2015-2016.xlsx,
           establecimientos_2017-2018.xlsx, establecimientos_2019-2020.xlsx,
           establecimientos_2021-2022.xlsx
    Provider: Ministerio de Educación de Guatemala (MINEDUC)

Scope:
    Public schools only:
      - Sector IN ['OFICIAL', 'MUNICIPAL', 'COOPERATIVA']
      - Nivel IN ['PRIMARIA', 'BASICO', 'DIVERSIFICADO']
    Excluded:
      - PRIVADO sector
      - PREPRIMARIA level (ISCED 0, out of scope)
      - PRIMARIA DE ADULTOS (non-formal, out of scope)

    Note: 'COOPERATIVA' schools (Institutos por Cooperativa) are
    community-run secondary institutions that receive government subsidies
    and are registered in the national MINEDUC EMIS. They are treated as
    public schools per the GEO schema provision for government-subsidised
    institutions.

ISCED mapping:
    PRIMARIA      → 1  (grades 1–6, ages 7–12)
    BASICO        → 2  (grades 7–9, lower secondary)
    DIVERSIFICADO → 3  (grades 10–12, upper secondary; includes vocational
                        tracks such as magisterio and bachillerato — standard
                        mapping is ISCED 3 per UNESCO ISCED 2011)

Coordinate strategy:
    Stage 1 — Source coordinates:
        Coordinates taken directly from source Latitud/Longitud columns
        where non-null. coordinate_source = 'official_emis',
        coordinate_precision = 'exact'.

    Stage 2 — Municipio centroid fallback:
        For schools with no source coordinate across any year, the centroid
        of the matched GeoBoundaries ADM2 (municipio) polygon is assigned.
        Source Municipio name fuzzy-matched to GeoBoundaries shapeName using
        rapidfuzz token_sort_ratio (threshold = 80, lowercase normalised).
        coordinate_source = 'admin_centroid',
        coordinate_precision = 'approximate'.

Admin boundaries:
    adm1 (departamento) and adm2 (municipio) assigned via spatial join to
    GeoBoundaries ADM1 and ADM2 polygons for schools with source coordinates.
    For centroid-fallback schools, adm1/adm2 come from the fuzzy-matched
    GeoBoundaries shapeName.

Author: HB
Date: 2026-06-08
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point
from rapidfuzz import process, fuzz

# Allow importing shared pipeline utilities
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ─────────────────────────────────────────────────────────────────────
SOURCE_DIR  = "/Users/heatherbaier/Documents/research/geo/sources/GTM/"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/gtm_geo.csv"
ISO3        = "GTM"

# ── Constants ─────────────────────────────────────────────────────────────────
IN_SCOPE_NIVEL  = ["PRIMARIA", "BASICO", "DIVERSIFICADO"]
PUBLIC_SECTORS  = ["OFICIAL", "MUNICIPAL", "COOPERATIVA"]
FUZZY_THRESHOLD = 80  # rapidfuzz token_sort_ratio threshold for municipio matching

ISCED_MAP = {
    "PRIMARIA":      "1",
    "BASICO":        "2",
    "DIVERSIFICADO": "3",
}

URBAN_RURAL_MAP = {
    "URBANO": "urban",
    "RURAL":  "rural",
}

GB_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{level}/"


# ── Step 1: Load and pool all source files ────────────────────────────────────
print("=" * 60)
print("STEP 1: Loading source files")
print("=" * 60)

# Build file list: prefer XLSX over CSV when both exist for the same stem
# (e.g. establecimientos_2013-2014.csv and .xlsx are identical — load only once)
_all = (
    glob.glob(os.path.join(SOURCE_DIR, "establecimientos_*.csv")) +
    glob.glob(os.path.join(SOURCE_DIR, "establecimientos_*.xlsx"))
)
seen_stems = set()
all_files = []
for fpath in sorted(_all, key=lambda p: (os.path.splitext(p)[0], p)):
    stem = os.path.splitext(fpath)[0]
    if stem not in seen_stems:
        seen_stems.add(stem)
        all_files.append(fpath)
all_files = sorted(all_files)

if not all_files:
    raise FileNotFoundError(f"No establecimientos_* files found in {SOURCE_DIR}")

print(f"Found {len(all_files)} file(s):")
frames = []
for fpath in all_files:
    ext = os.path.splitext(fpath)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(fpath, encoding="utf-8", on_bad_lines="skip", dtype=str)
    else:
        df = pd.read_excel(fpath, dtype=str)
    df.columns = df.columns.str.strip()
    frames.append(df)
    print(f"  {os.path.basename(fpath)}: {len(df)} rows")

raw = pd.concat(frames, ignore_index=True)
print(f"\nTotal rows across all files: {len(raw)}")


# ── Step 2: Filter to public in-scope schools ─────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Filtering to public in-scope schools")
print("=" * 60)

raw["Sector"] = raw["Sector"].str.strip().str.upper()
raw["Nivel"]  = raw["Nivel"].str.strip().str.upper()
raw["Area"]   = raw["Area"].str.strip().str.upper()
raw["Latitud"]  = pd.to_numeric(raw["Latitud"],  errors="coerce")
raw["Longitud"] = pd.to_numeric(raw["Longitud"], errors="coerce")
raw["Año"]      = pd.to_numeric(raw["Año"],      errors="coerce")

filtered = raw[
    raw["Sector"].isin(PUBLIC_SECTORS) &
    raw["Nivel"].isin(IN_SCOPE_NIVEL)
].copy()

print(f"Rows after filter: {len(filtered)}")
print(f"Unique CodigoEst:  {filtered['CodigoEst'].nunique()}")
print(f"\nNivel:  \n{filtered['Nivel'].value_counts()}")
print(f"\nSector: \n{filtered['Sector'].value_counts()}")


# ── Step 3: Build canonical school register (one row per school) ──────────────
print("\n" + "=" * 60)
print("STEP 3: Building canonical school register")
print("=" * 60)

# Latest year wins for canonical attributes
filtered_sorted = filtered.sort_values("Año", ascending=False)

canonical_cols = [
    "NombreEstablecimiento", "Sector", "Nivel",
    "CodDepartamento", "Departamento", "CodMuni", "Municipio",
    "Modalidad", "Area",
]
canonical = (
    filtered_sorted
    .groupby("CodigoEst")[canonical_cols]
    .first()
    .reset_index()
)
print(f"Unique schools in canonical register: {len(canonical)}")


# ── Step 4: Resolve coordinates across years ──────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Resolving coordinates across years")
print("=" * 60)

# Earliest year with a coord is preferred (most likely to have been
# manually entered at school registration time)
coord_df = filtered.sort_values("Año", ascending=True)

def first_non_null_coord(group):
    valid = group.dropna(subset=["Latitud", "Longitud"])
    if len(valid) == 0:
        return pd.Series({"Latitud": np.nan, "Longitud": np.nan, "coord_year": np.nan})
    row = valid.iloc[0]
    return pd.Series({
        "Latitud":    row["Latitud"],
        "Longitud":   row["Longitud"],
        "coord_year": row["Año"],
    })

coord_resolved = (
    coord_df
    .groupby("CodigoEst")
    .apply(first_non_null_coord, include_groups=False)
    .reset_index()
)
# Safety dedup — should be one row per CodigoEst after groupby
coord_resolved = coord_resolved.drop_duplicates(subset="CodigoEst", keep="first")

schools = canonical.merge(coord_resolved, on="CodigoEst", how="left")

n_has_coord = schools["Latitud"].notna().sum()
n_no_coord  = schools["Latitud"].isna().sum()
print(f"Schools with source coords:    {n_has_coord} ({n_has_coord/len(schools)*100:.1f}%)")
print(f"Schools without source coords: {n_no_coord} ({n_no_coord/len(schools)*100:.1f}%)")


# ── Step 5: Fetch GeoBoundaries ADM2 for centroid fallback ────────────────────
print("\n" + "=" * 60)
print("STEP 5: Fetching GeoBoundaries ADM2 for centroid fallback")
print("=" * 60)

def fetch_boundary(iso3: str, level: int, timeout: int = 30):
    url = GB_API.format(iso3=iso3.upper(), level=level)
    r = requests.get(url, timeout=timeout)
    if r.status_code != 200 or not r.text.strip():
        return None
    data = r.json()
    geojson_url = data.get("gjDownloadURL")
    if not geojson_url:
        return None
    return gpd.read_file(geojson_url).to_crs("EPSG:4326")

adm2_gdf = fetch_boundary(ISO3, 2)
if adm2_gdf is None:
    raise RuntimeError("Could not fetch GeoBoundaries ADM2 for GTM")

print(f"ADM2 features: {len(adm2_gdf)}")
print(f"ADM2 shapeName sample: {adm2_gdf['shapeName'].head(10).tolist()}")


# ── Step 6: Fuzzy match Municipio → GeoBoundaries ADM2 shapeName ──────────────
print("\n" + "=" * 60)
print("STEP 6: Fuzzy matching Municipio → GeoBoundaries ADM2")
print("=" * 60)

gb_adm2_names = adm2_gdf["shapeName"].tolist()
gb_adm2_names_lower = [n.lower() for n in gb_adm2_names]

def fuzzy_match_municipio(municipio_raw: str) -> tuple[str | None, float]:
    """Return (matched shapeName, score) or (None, 0) if below threshold."""
    if pd.isna(municipio_raw) or str(municipio_raw).strip() == "":
        return None, 0.0
    query = str(municipio_raw).strip().lower()
    result = process.extractOne(
        query,
        gb_adm2_names_lower,
        scorer=fuzz.token_sort_ratio,
    )
    if result is None or result[1] < FUZZY_THRESHOLD:
        return None, result[1] if result else 0.0
    matched_idx = result[2]
    return gb_adm2_names[matched_idx], result[1]

# Apply fuzzy match to all schools (used for centroid fallback schools;
# also used as cross-check for spatially joined schools)
print("Running fuzzy match on Municipio names...")
match_results = schools["Municipio"].apply(fuzzy_match_municipio)
schools["gb_adm2_matched"]      = match_results.apply(lambda x: x[0])
schools["gb_adm2_match_score"]  = match_results.apply(lambda x: x[1])

n_matched   = schools["gb_adm2_matched"].notna().sum()
n_unmatched = schools["gb_adm2_matched"].isna().sum()
print(f"Fuzzy match results (threshold={FUZZY_THRESHOLD}):")
print(f"  Matched:   {n_matched}")
print(f"  Unmatched: {n_unmatched}")

# Score distribution for matched
scores = schools.loc[schools["gb_adm2_matched"].notna(), "gb_adm2_match_score"]
print(f"  Score distribution: min={scores.min():.0f}, median={scores.median():.0f}, max={scores.max():.0f}")
low_confidence = (scores < 90).sum()
print(f"  Low-confidence matches (score 80–89): {low_confidence}")

# Merge ADM2 polygon to get centroid for fallback schools
adm2_centroids = adm2_gdf.copy()
adm2_centroids["centroid_lat"] = adm2_centroids.geometry.centroid.y
adm2_centroids["centroid_lon"] = adm2_centroids.geometry.centroid.x
adm2_centroids = adm2_centroids[["shapeName", "centroid_lat", "centroid_lon"]].rename(
    columns={"shapeName": "gb_adm2_matched"}
)

schools = schools.merge(adm2_centroids, on="gb_adm2_matched", how="left")

# Apply centroid coords to schools missing source coords
no_coord_mask = schools["Latitud"].isna()
centroid_available = no_coord_mask & schools["centroid_lat"].notna()

schools.loc[centroid_available, "Latitud"]  = schools.loc[centroid_available, "centroid_lat"]
schools.loc[centroid_available, "Longitud"] = schools.loc[centroid_available, "centroid_lon"]

n_centroid_filled = centroid_available.sum()
n_still_missing   = schools["Latitud"].isna().sum()
print(f"\nAfter centroid fallback:")
print(f"  Schools filled via centroid: {n_centroid_filled}")
print(f"  Still missing coords:        {n_still_missing}")


# ── Step 7: Assign coordinate_source and coordinate_precision ─────────────────
print("\n" + "=" * 60)
print("STEP 7: Assigning coordinate metadata")
print("=" * 60)

schools["coordinate_source"]    = pd.NA
schools["coordinate_precision"] = pd.NA

# Original source coords
had_source_coord = coord_resolved["Latitud"].notna()
source_coord_ids = set(coord_resolved.loc[had_source_coord, "CodigoEst"])
source_mask = schools["CodigoEst"].isin(source_coord_ids)

schools.loc[source_mask, "coordinate_source"]    = "official_emis"
schools.loc[source_mask, "coordinate_precision"] = "exact"

# Centroid fallback
schools.loc[centroid_available, "coordinate_source"]    = "admin_centroid"
schools.loc[centroid_available, "coordinate_precision"] = "approximate"

# Remaining (no source coord AND fuzzy match failed)
still_missing = schools["Latitud"].isna()
schools.loc[still_missing, "coordinate_source"]    = "admin_centroid"
schools.loc[still_missing, "coordinate_precision"] = "approximate"

print("coordinate_source distribution:")
print(schools["coordinate_source"].value_counts())


# ── Step 8: Spatial join admin boundaries for schools with source coords ───────
print("\n" + "=" * 60)
print("STEP 8: Spatial join admin boundaries (source-coord schools)")
print("=" * 60)

# Build GeoDataFrame for schools with coords
has_coord_mask = schools["Latitud"].notna() & schools["Longitud"].notna()
gdf_coords = gpd.GeoDataFrame(
    schools[has_coord_mask].copy(),
    geometry=[
        Point(lon, lat)
        for lat, lon in zip(
            schools.loc[has_coord_mask, "Latitud"],
            schools.loc[has_coord_mask, "Longitud"],
        )
    ],
    crs="EPSG:4326",
)

# Spatial join for ADM1 and ADM2
gdf_joined = join_admin_boundaries(gdf_coords, iso3=ISO3, levels=[1, 2])

# Merge back into main schools df
adm_cols = [c for c in ["adm1", "adm2"] if c in gdf_joined.columns]
schools = schools.merge(
    gdf_joined[["CodigoEst"] + adm_cols],
    on="CodigoEst",
    how="left",
)

print(f"\nADM1 null after spatial join: {schools['adm1'].isna().sum()}")
print(f"ADM2 null after spatial join: {schools['adm2'].isna().sum()}")


# ── Step 9: Fill adm1/adm2 for centroid-fallback schools ─────────────────────
print("\n" + "=" * 60)
print("STEP 9: Filling adm1/adm2 for centroid-fallback schools")
print("=" * 60)

# For schools that got centroid coords, adm2 = matched GB shapeName
# adm1 = look up departamento shapeName via ADM1 spatial join on the centroid point
# For simplicity: fetch ADM1 boundary and do a name lookup via ADM2→ADM1 containment
# (GeoBoundaries ADM2 features contain shapeName which we can cross-reference with ADM1)

adm1_gdf = fetch_boundary(ISO3, 1)
if adm1_gdf is not None:
    print(f"ADM1 features: {len(adm1_gdf)}")

    # Build centroid GDF for fallback schools
    centroid_mask = schools["coordinate_source"] == "admin_centroid"
    centroid_schools = schools[centroid_mask & schools["Latitud"].notna()].copy()

    if len(centroid_schools) > 0:
        gdf_centroids = gpd.GeoDataFrame(
            centroid_schools,
            geometry=[
                Point(lon, lat)
                for lat, lon in zip(
                    centroid_schools["Longitud"],
                    centroid_schools["Latitud"],
                )
            ],
            crs="EPSG:4326",
        )
        # Spatial join centroid points to ADM1
        centroid_joined = gpd.sjoin(
            gdf_centroids[["CodigoEst", "geometry"]],
            adm1_gdf[["shapeName", "geometry"]].rename(columns={"shapeName": "adm1_centroid"}),
            how="left",
            predicate="within",
        )
        if "index_right" in centroid_joined.columns:
            centroid_joined = centroid_joined.drop(columns=["index_right"])
        # Deduplicate by CodigoEst (schools on ADM1 boundaries may match two polygons)
        centroid_joined = centroid_joined.drop_duplicates(subset="CodigoEst", keep="first")

        adm1_lookup = centroid_joined.set_index("CodigoEst")["adm1_centroid"]

        # Fill adm1 where missing
        adm1_missing = schools["adm1"].isna() & schools["CodigoEst"].isin(adm1_lookup.index)
        schools.loc[adm1_missing, "adm1"] = schools.loc[adm1_missing, "CodigoEst"].map(adm1_lookup)

        # Fill adm2 where missing using fuzzy matched GB name
        adm2_missing = schools["adm2"].isna() & schools["gb_adm2_matched"].notna()
        schools.loc[adm2_missing, "adm2"] = schools.loc[adm2_missing, "gb_adm2_matched"]

        print(f"ADM1 null after centroid fill: {schools['adm1'].isna().sum()}")
        print(f"ADM2 null after centroid fill: {schools['adm2'].isna().sum()}")
else:
    print("WARNING: Could not fetch ADM1 — adm1 will be NA for centroid-fallback schools")


# ── Step 10: Assign geo_id ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 10: Assigning geo_id")
print("=" * 60)

# Sort by CodigoEst for reproducible ID assignment
schools = schools.sort_values("CodigoEst").reset_index(drop=True)
schools["geo_id"] = [f"{ISO3}_{str(i+1).zfill(6)}" for i in range(len(schools))]
print(f"geo_id range: {schools['geo_id'].iloc[0]} to {schools['geo_id'].iloc[-1]}")


# ── Step 11: Assemble output ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 11: Assembling output")
print("=" * 60)

out = pd.DataFrame()

out["geo_id"]                = schools["geo_id"]
out["source_id"]             = schools["CodigoEst"].str.strip()
out["country"]               = ISO3
out["school_name"]           = schools["NombreEstablecimiento"].str.strip()
out["school_name_romanized"] = pd.NA  # names already in Latin script (Spanish)
out["isced_level"]           = schools["Nivel"].map(ISCED_MAP)
out["school_type"]           = schools["Nivel"].str.title()  # retain source level label
out["sector"]                = "public"
out["adm0"]                  = "Guatemala"
out["adm1"]                  = schools["adm1"]
out["adm2"]                  = schools["adm2"]
out["adm3"]                  = pd.NA  # GeoBoundaries does not provide ADM3 for GTM
out["urban_rural"]           = schools["Area"].map(URBAN_RURAL_MAP)
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = schools["Latitud"].round(6)
out["longitude"]             = schools["Longitud"].round(6)
out["coordinate_source"]     = schools["coordinate_source"]
out["coordinate_precision"]  = schools["coordinate_precision"]
out["status"]                = "open"

# ── Step 12: QA checks ────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 12: QA checks")
print("=" * 60)

print(f"Total rows: {len(out)}")
print()

never_null = [
    "geo_id", "source_id", "country", "school_name",
    "isced_level", "sector", "adm0",
    "coordinate_source", "coordinate_precision", "status",
]
for col in never_null:
    n = out[col].isna().sum()
    status = "OK" if n == 0 else f"WARNING — {n} nulls"
    print(f"  {status}: {col}")

print()
print("isced_level distribution:")
print(out["isced_level"].value_counts())
print()
print("coordinate_source distribution:")
print(out["coordinate_source"].value_counts())
print()
print("coordinate_precision distribution:")
print(out["coordinate_precision"].value_counts())
print()
print("urban_rural distribution:")
print(out["urban_rural"].value_counts(dropna=False))
print()
print(f"Missing latitude:  {out['latitude'].isna().sum()}")
print(f"Missing longitude: {out['longitude'].isna().sum()}")
print()
print(f"ADM1 null: {out['adm1'].isna().sum()}")
print(f"ADM2 null: {out['adm2'].isna().sum()}")
print()
dupes = out["geo_id"].duplicated().sum()
print(f"Duplicate geo_ids: {dupes}")
dupes_src = out["source_id"].duplicated().sum()
print(f"Duplicate source_ids: {dupes_src}")

# Coord bounding box check (Guatemala: lat 13.7–17.8, lon -92.3–-88.2)
bad_lat = out["latitude"].notna() & ((out["latitude"] < 13.5) | (out["latitude"] > 18.0))
bad_lon = out["longitude"].notna() & ((out["longitude"] < -92.5) | (out["longitude"] > -88.0))
print(f"\nCoords outside Guatemala bounding box:")
print(f"  Bad latitude:  {bad_lat.sum()}")
print(f"  Bad longitude: {bad_lon.sum()}")

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved: {OUTPUT_FILE}")
print(f"  {len(out)} schools")