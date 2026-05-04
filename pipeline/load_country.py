import os
import sys
import requests
import zipfile
import tempfile
import geopandas as gpd
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

# ── Config ────────────────────────────────────────────────────────
DB_URL  = "postgresql://geomain:geoRocks2026@206.189.232.243:5432/geodb"
GS_URL  = "http://206.189.232.243:8080/geoserver"
GS_USER = "admin"
GS_PASS = "geoserver"
WS      = "geo"
DS      = "GEO_PostGIS"

# Local data folder structure
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR   = os.path.join(BASE_DIR, "db")
DIMS     = ["geo", "personnel", "resources", "outcomes"]

# ── Database engine ───────────────────────────────────────────────
engine = create_engine(DB_URL)

# ── Step 1: Load CSVs into PostgreSQL ────────────────────────────
def load_csvs(iso3):
    iso = iso3.lower()
    print(f"\n── Loading CSVs for {iso3} ──")

    for dim in DIMS:
        csv_path = os.path.join(DB_DIR, dim, f"{iso}_{dim}.csv")
        if not os.path.exists(csv_path):
            print(f"  ⚠ No {dim} file found, skipping")
            continue

        print(csv_path)
        df = pd.read_csv(csv_path)
        table = f"{iso}_{dim}"

        df.to_sql(
            table,
            engine,
            if_exists="replace",   # replace so re-cleaning is safe
            index=False
        )
        print(f"  ✓ Loaded {table} ({len(df):,} rows)")

# ── Step 2: Add PostGIS geometry to geo table ─────────────────────
def add_geometry(iso3):
    iso = iso3.lower()
    table = f"{iso}_geo"
    print(f"\n── Adding PostGIS geometry to {table} ──")

    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    # Check latitude/longitude columns exist
    cur.execute(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = '{table}'
        AND column_name IN ('latitude', 'longitude');
    """)
    cols = [r[0] for r in cur.fetchall()]

    if len(cols) < 2:
        print(f"  ⚠ No lat/lon columns found in {table}, skipping geometry")
        conn.close()
        return

    cur.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS geom;")
    cur.execute(f"""
        ALTER TABLE {table}
        ADD COLUMN geom geometry(Point, 4326);
    """)
    cur.execute(f"""
        UPDATE {table}
        SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE longitude IS NOT NULL AND latitude IS NOT NULL;
    """)
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table}_geom_idx
        ON {table} USING GIST(geom);
    """)

    conn.commit()
    conn.close()
    print(f"  ✓ Geometry column added and indexed")

# ── Step 3: Download + load ADM0 boundary from GeoBoundaries ──────
def load_adm0(iso3):
    iso = iso3.lower()
    table = f"{iso}_adm0"
    print(f"\n── Loading ADM0 boundary for {iso3} ──")

    # Fetch download URL from GeoBoundaries API
    try:
        r = requests.get(
            f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM0/",
            timeout=15
        )
        r.raise_for_status()
        geojson_url = r.json().get("gjDownloadURL")
        if not geojson_url:
            print(f"  ✗ No gjDownloadURL in GeoBoundaries response")
            return
    except Exception as e:
        print(f"  ✗ GeoBoundaries API failed: {e}")
        return

    # Read GeoJSON directly into geopandas — no zip, no temp dir needed
    print(f"  Downloading GeoJSON...")
    try:
        gdf = gpd.read_file(geojson_url)
        gdf = gdf.to_crs("EPSG:4326")
        gdf.to_postgis(table, engine, if_exists="replace", index=False)
        print(f"  ✓ Loaded {table} ({len(gdf)} features)")
    except Exception as e:
        print(f"  ✗ Failed to load boundary: {e}")

# ── Step 4: Publish layers in GeoServer ───────────────────────────
def publish_geoserver(iso3):
    iso = iso3.lower()
    print(f"\n── Publishing GeoServer layers for {iso3} ──")

    layers = [f"{iso}_adm0", f"{iso}_geo"]

    for layer in layers:
        ft_url  = f"{GS_URL}/rest/workspaces/{WS}/datastores/{DS}/featuretypes/{layer}"
        lyr_url = f"{GS_URL}/rest/layers/{WS}:{layer}"
        pub_url = f"{GS_URL}/rest/workspaces/{WS}/datastores/{DS}/featuretypes"

        # Always delete both the layer and featuretype first to ensure clean state
        requests.delete(lyr_url, auth=(GS_USER, GS_PASS))
        requests.delete(f"{ft_url}?recurse=true", auth=(GS_USER, GS_PASS))

        payload = {
            "featureType": {
                "name":       layer,
                "nativeName": layer,
                "title":      layer.upper().replace("_", " "),
                "srs":        "EPSG:4326",
                "enabled":    True,
                "nativeBoundingBox": {
                    "minx": -180, "maxx": 180,
                    "miny": -90,  "maxy": 90,
                    "crs":  "EPSG:4326"
                },
                "latLonBoundingBox": {
                    "minx": -180, "maxx": 180,
                    "miny": -90,  "maxy": 90,
                    "crs":  "EPSG:4326"
                }
            }
        }

        r = requests.post(
            pub_url,
            json=payload,
            auth=(GS_USER, GS_PASS),
            headers={"Content-Type": "application/json"}
        )

        if r.status_code == 201:
            print(f"  ✓ Published {layer}")
        else:
            print(f"  ✗ Failed {layer}: {r.status_code} {r.text}")

# ── Main ──────────────────────────────────────────────────────────
def main():
    iso3 = sys.argv[1].upper() if len(sys.argv) > 1 else input("ISO3 code: ").strip().upper()

    print(f"\n{'='*50}")
    print(f"  Loading {iso3} into GEO pipeline")
    print(f"{'='*50}")

    load_csvs(iso3)
    add_geometry(iso3)
    load_adm0(iso3)
    publish_geoserver(iso3)

    print(f"\n{'='*50}")
    print(f"  ✓ {iso3} complete — website will update automatically")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()