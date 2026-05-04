"""
geo_boundaries.py
-----------------
Utility for fetching and spatially joining GeoBoundaries administrative
boundary data to a GeoDataFrame of school points.

Loops through ADM levels (1–4 by default), checks availability via the
GeoBoundaries API, downloads and joins each available level, and silently
skips levels that are not available.

Usage:
    from pipeline.geo_boundaries import join_admin_boundaries

    gdf = join_admin_boundaries(gdf, iso3="BHR")
    # Adds columns: adm1, adm2, adm3, adm4 (NA where not available)

    # Or specify which levels to attempt:
    gdf = join_admin_boundaries(gdf, iso3="PHL", levels=[1, 2, 3])
"""

from typing import Optional
import geopandas as gpd
import pandas as pd
import requests


GB_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{level}/"


def _fetch_boundary(iso3: str, level: int, timeout: int = 15) -> Optional[gpd.GeoDataFrame]:
    """
    Fetch a single ADM level from GeoBoundaries for a given ISO3 country code.
    Returns a GeoDataFrame in EPSG:4326, or None if not available.
    """
    url = GB_API.format(iso3=iso3.upper(), level=level)
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200 or not r.text.strip():
            return None
        data = r.json()
        geojson_url = data.get("gjDownloadURL")
        if not geojson_url:
            return None
        gdf = gpd.read_file(geojson_url).to_crs("EPSG:4326")
        return gdf
    except Exception:
        return None


def join_admin_boundaries(
    gdf: gpd.GeoDataFrame,
    iso3: str,
    levels: list[int] = [1, 2, 3, 4],
    name_col: str = "shapeName",
    timeout: int = 15,
) -> gpd.GeoDataFrame:
    """
    Spatially join GeoBoundaries admin boundaries to a school point GeoDataFrame.

    For each requested ADM level:
      - Attempts to fetch the boundary from GeoBoundaries
      - If available, performs a left spatial join (within) to assign the
        admin unit name to each school point
      - If not available, adds the column with NA values
      - Prints a status line for each level

    Parameters
    ----------
    gdf : GeoDataFrame
        School points in EPSG:4326. Must have a geometry column.
    iso3 : str
        ISO 3166-1 alpha-3 country code (e.g., 'BHR', 'PHL').
    levels : list of int
        ADM levels to attempt. Default [1, 2, 3, 4].
    name_col : str
        Column name in GeoBoundaries data containing the admin unit name.
        GeoBoundaries uses 'shapeName' by default.
    timeout : int
        Request timeout in seconds.

    Returns
    -------
    GeoDataFrame with added columns adm1, adm2, adm3, adm4 (for each
    requested level). NA where not available or no spatial match found.
    """
    gdf = gdf.copy()

    for level in levels:
        col = f"adm{level}"
        print(f"  ADM{level}: fetching from GeoBoundaries...", end=" ")

        boundary = _fetch_boundary(iso3, level, timeout=timeout)

        if boundary is None:
            print(f"not available — {col} set to NA")
            gdf[col] = pd.NA
            continue

        # Find the name column — fall back to first non-geometry column
        if name_col in boundary.columns:
            use_col = name_col
        else:
            candidates = [c for c in boundary.columns if "name" in c.lower()]
            use_col = candidates[0] if candidates else boundary.columns[0]

        n_features = len(boundary)

        # Spatial join
        joined = gpd.sjoin(
            gdf,
            boundary[[use_col, "geometry"]].rename(columns={use_col: col}),
            how="left",
            predicate="within",
        )

        # Drop the right index from sjoin
        if "index_right" in joined.columns:
            joined = joined.drop(columns=["index_right"])

        # Handle duplicate rows from sjoin (school on boundary between two units)
        # Keep first match per original index
        joined = joined[~joined.index.duplicated(keep="first")]

        n_matched = joined[col].notna().sum()
        n_missed  = joined[col].isna().sum()

        print(f"{n_features} features → {n_matched} matched", end="")
        if n_missed > 0:
            print(f", {n_missed} unmatched (NA)", end="")
        print()

        gdf = joined

    return gdf


def get_available_levels(iso3: str, levels: list[int] = [1, 2, 3, 4], timeout: int = 15) -> list[int]:
    """
    Check which ADM levels are available in GeoBoundaries for a country
    without downloading the full boundary data.

    Returns a list of available level integers.
    """
    available = []
    for level in levels:
        url = GB_API.format(iso3=iso3.upper(), level=level)
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                data = r.json()
                if data.get("gjDownloadURL"):
                    available.append(level)
        except Exception:
            pass
    return available
