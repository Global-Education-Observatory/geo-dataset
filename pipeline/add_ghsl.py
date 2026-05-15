"""
add_ghsl.py
-----------
Samples the GHS-SMOD R2023 epoch 2020 raster at school coordinates and
assigns ghsl_smod_code and ghsl_urban_rural to all {iso}_geo.csv files
in the db/geo/ directory.

Source raster:
    GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif
    GHS-SMOD R2023A, epoch 2020, 1km resolution, Mollweide projection
    https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/

SMOD class codes → ghsl_urban_rural mapping:
    30  Urban centre            → urban
    23  Dense urban cluster     → urban
    22  Semi-dense urban cluster→ urban
    21  Suburban/peri-urban     → peri_urban
    13  Rural cluster           → rural
    12  Low density rural       → rural
    11  Very low density rural  → rural
    10  Water bodies            → NA
     1  (outside land area)     → NA

Usage:
    # Process all countries in db/geo/
    python pipeline/add_ghsl.py

    # Process a single country
    python pipeline/add_ghsl.py BHR

Notes:
    - ghsl_smod_code and ghsl_urban_rural are OVERWRITTEN on each run
    - The raster is in Mollweide (EPSG:54009) — coordinates are reprojected
      from WGS84 before sampling
    - Schools that fall in water or outside the land mask get NA
    - Run this ONCE after all countries are cleaned, or re-run any time
      the raster is updated

Author: HB
Date: 2026-05-04
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
import rasterio
from rasterio.crs import CRS
from pyproj import Transformer

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO_DIR    = os.path.join(BASE_DIR, "db", "geo")
RASTER     = os.path.join(BASE_DIR, "data", "ghsl", "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0",
                          "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.tif")

# ── SMOD code → urban/rural label ─────────────────────────────────────────
SMOD_LABELS = {
    30: "urban",      # Urban centre
    23: "urban",      # Dense urban cluster
    22: "urban",      # Semi-dense urban cluster
    21: "peri_urban", # Suburban / peri-urban
    13: "rural",      # Rural cluster
    12: "rural",      # Low density rural
    11: "rural",      # Very low density rural
    10: None,         # Water bodies
     1: None,         # Outside land area / no data
     0: None,         # No data
}

def sample_ghsl(csv_path: str, transformer, src) -> pd.DataFrame:
    """
    Sample GHSL-SMOD raster for all schools in a geo CSV.
    Returns the updated DataFrame.
    """
    iso = os.path.basename(csv_path).replace("_geo.csv", "").upper()
    df  = pd.read_csv(csv_path, dtype=str)

    # Check required columns
    if "latitude" not in df.columns or "longitude" not in df.columns:
        print(f"  {iso}: missing latitude/longitude columns — skipping")
        return df

    # Parse coordinates
    lats = pd.to_numeric(df["latitude"],  errors="coerce")
    lons = pd.to_numeric(df["longitude"], errors="coerce")

    valid = lats.notna() & lons.notna()
    n_valid   = valid.sum()
    n_invalid = (~valid).sum()

    if n_valid == 0:
        print(f"  {iso}: no valid coordinates — skipping")
        return df

    # Reproject WGS84 → Mollweide (EPSG:54009)
    xs, ys = transformer.transform(
        lats[valid].values,
        lons[valid].values
    )

    # Sample raster
    coords    = list(zip(xs, ys))
    sampled   = list(src.sample(coords, indexes=1))
    codes     = np.array([s[0] for s in sampled], dtype=float)

    # Map nodata value to NaN
    nodata = src.nodata
    if nodata is not None:
        codes[codes == nodata] = np.nan

    # Assign back to full-length arrays
    smod_codes  = np.full(len(df), np.nan)
    smod_labels = np.full(len(df), None, dtype=object)

    smod_codes[valid.values]  = codes
    smod_labels[valid.values] = [
        SMOD_LABELS.get(int(c), None) if not np.isnan(c) else None
        for c in codes
    ]

    df["ghsl_smod_code"]  = [
        int(c) if not np.isnan(c) else pd.NA
        for c in smod_codes
    ]
    df["ghsl_urban_rural"] = [
        lbl if lbl is not None else pd.NA
        for lbl in smod_labels
    ]

    # Summary
    label_counts = pd.Series(smod_labels[valid.values]).value_counts(dropna=False)
    print(f"  {iso}: {n_valid} schools sampled", end="")
    if n_invalid > 0:
        print(f", {n_invalid} skipped (no coords)", end="")
    print()
    for label, count in label_counts.items():
        tag = label if label is not None else "NA (water/nodata)"
        print(f"    {tag}: {count}")

    return df


def main():
    # Check raster exists
    if not os.path.exists(RASTER):
        print(f"ERROR: GHSL raster not found at:\n  {RASTER}")
        print("Download from:")
        print("  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
              "GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000/"
              "V1-0/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0.zip")
        sys.exit(1)

    # Determine which countries to process
    if len(sys.argv) > 1:
        isos = [sys.argv[1].lower()]
        csv_paths = [os.path.join(GEO_DIR, f"{iso}_geo.csv") for iso in isos]
        missing = [p for p in csv_paths if not os.path.exists(p)]
        if missing:
            print(f"ERROR: file(s) not found: {missing}")
            sys.exit(1)
    else:
        csv_paths = sorted(glob.glob(os.path.join(GEO_DIR, "*_geo.csv")))
        if not csv_paths:
            print(f"No *_geo.csv files found in {GEO_DIR}")
            sys.exit(1)

    print(f"GHSL-SMOD R2023 epoch 2020 — sampling {len(csv_paths)} country file(s)")
    print(f"Raster: {RASTER}\n")

    # Set up reprojection transformer: WGS84 → Mollweide (EPSG:54009)
    # GHSL raster uses ESRI:54009 (World Mollweide)
    mollweide_wkt = (
        'PROJCS["World_Mollweide",'
        'GEOGCS["GCS_WGS_1984",'
        'DATUM["D_WGS_1984",'
        'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
        'PRIMEM["Greenwich",0.0],'
        'UNIT["Degree",0.0174532925199433]],'
        'PROJECTION["Mollweide"],'
        'PARAMETER["False_Easting",0.0],'
        'PARAMETER["False_Northing",0.0],'
        'PARAMETER["Central_Meridian",0.0],'
        'UNIT["Meter",1.0]]'
    )

    transformer = Transformer.from_crs(
        "EPSG:4326",          # WGS84 (lat, lon)
        mollweide_wkt,        # Mollweide
        always_xy=False       # input is (lat, lon) order
    )

    # Open raster once and process all countries
    with rasterio.open(RASTER) as src:
        print(f"Raster CRS:   {src.crs}")
        print(f"Raster shape: {src.height} x {src.width}")
        print(f"Nodata value: {src.nodata}\n")

        for csv_path in csv_paths:
            df = sample_ghsl(csv_path, transformer, src)
            df.to_csv(csv_path, index=False)

    print(f"\n✓ Done — ghsl_smod_code and ghsl_urban_rural updated in all geo files")
    print(f"  Source: GHS-SMOD R2023A, epoch 2020, 1km resolution")
    print(f"  Reference: Schiavina et al. (2023), doi:10.2905/4606D58A-DC08-463C-86A9-D49EF461C47F")


if __name__ == "__main__":
    main()
