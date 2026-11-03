"""
00_yem_reverse_names.py
-----------------------
Looks up candidate school names for Yemen schools from their coordinates
using the Google Places API (New) Nearby Search.

Why Nearby Search and not the Geocoding API reverse endpoint:
    Reverse geocoding returns street addresses / localities, not POI names.
    Nearby Search restricted to school place types returns named schools
    near the point, which is what we want.

    Endpoint: POST https://places.googleapis.com/v1/places:searchNearby

Input:
    db/geo/yem_geo.csv  (output of 01_yem_geo.py; only in-scope schools
                         are queried)

Output:
    sources/YEM/geocoding/yem_reverse_names.csv
        One row per school (source_id), with the best candidate and flags.
    sources/YEM/geocoding/yem_reverse_cache.jsonl
        Raw API responses, one line per unique coordinate. Used to resume
        and to avoid paying twice. Delete it to force a re-query.

Matching logic:
    - Query each UNIQUE coordinate once (several schools share a point).
    - includedTypes = school, primary_school, secondary_school
    - rankPreference = DISTANCE, radius = SEARCH_RADIUS_M
    - Best candidate = nearest returned place.
    - match_confidence:
        high    nearest school <= HIGH_M and only one school at this coordinate
        medium  nearest school <= MEDIUM_M and only one school at this coordinate
        low     anything further, up to SEARCH_RADIUS_M
        shared  coordinate is used by >1 school in the register, so the
                returned name cannot be assigned to a specific school
        none    no school-type place found within SEARCH_RADIUS_M

Caveats (document in metadata if used):
    - A returned name is the nearest Google POI tagged as a school, not a
      confirmed match to the EMIS record. Google coverage of Yemen is
      uneven, especially in rural governorates.
    - Google Maps Platform terms restrict storing and redistributing Places
      content (names) beyond temporary caching; place_id is the exception.
      Check this before publishing these names in the CC BY release.

Usage:
    export GOOGLE_MAPS_API_KEY=...
    python cleaning/yem/00_yem_reverse_names.py            # full run
    python cleaning/yem/00_yem_reverse_names.py --limit 50 # pilot

Author: HB
Date: 2026-11-02
"""

import argparse
import json
import math
import os
import sys
import time

import pandas as pd
import requests

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GEO_FILE   = os.path.join(BASE_DIR, "db", "geo", "yem_geo.csv")
OUT_DIR    = os.path.join(BASE_DIR, "sources", "YEM", "geocoding")
CACHE_FILE = os.path.join(OUT_DIR, "yem_reverse_cache.jsonl")
OUT_FILE   = os.path.join(OUT_DIR, "yem_reverse_names.csv")

# ── Settings ──────────────────────────────────────────────────────────────
ENDPOINT        = "https://places.googleapis.com/v1/places:searchNearby"
SCHOOL_TYPES    = ["school", "primary_school", "secondary_school"]
SEARCH_RADIUS_M = 500.0
HIGH_M          = 100.0
MEDIUM_M        = 250.0
MAX_RESULTS     = 5
LANGUAGE        = "ar"      # original script; romanize separately later
REGION          = "YE"
FIELD_MASK      = ("places.id,places.displayName,places.location,"
                   "places.types,places.primaryType,places.formattedAddress")
SLEEP_S         = 0.05      # pause between calls
MAX_RETRIES     = 4
COORD_DECIMALS  = 6         # rounding used to define "same coordinate"


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def coord_key(lat, lon):
    return f"{round(lat, COORD_DECIMALS)},{round(lon, COORD_DECIMALS)}"


def load_cache(path):
    """Return {coord_key: response_dict} from a JSONL cache."""
    cache = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    cache[rec["key"]] = rec["response"]
    return cache


def search_nearby(session, api_key, lat, lon):
    """Call Places Nearby Search for school types around (lat, lon)."""
    body = {
        "includedTypes": SCHOOL_TYPES,
        "maxResultCount": MAX_RESULTS,
        "rankPreference": "DISTANCE",
        "languageCode": LANGUAGE,
        "regionCode": REGION,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": SEARCH_RADIUS_M,
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    for attempt in range(MAX_RETRIES):
        r = session.post(ENDPOINT, json=body, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 503):
            wait = 2 ** attempt
            print(f"    HTTP {r.status_code}, retrying in {wait}s")
            time.sleep(wait)
            continue
        # Non-retryable (bad key, quota off, bad request): stop the run
        sys.exit(f"ERROR: HTTP {r.status_code}: {r.text[:500]}")
    sys.exit("ERROR: exhausted retries")


def parse_candidates(response, lat, lon):
    """Return list of candidate dicts sorted by distance."""
    out = []
    for p in response.get("places", []):
        loc = p.get("location", {})
        if "latitude" not in loc:
            continue
        out.append({
            "place_id":   p.get("id"),
            "name":       (p.get("displayName") or {}).get("text"),
            "name_lang":  (p.get("displayName") or {}).get("languageCode"),
            "primary_type": p.get("primaryType"),
            "address":    p.get("formattedAddress"),
            "place_lat":  loc["latitude"],
            "place_lon":  loc["longitude"],
            "distance_m": haversine_m(lat, lon, loc["latitude"], loc["longitude"]),
        })
    return sorted(out, key=lambda c: c["distance_m"])


def confidence(dist, n_schools_here):
    if dist is None:
        return "none"
    if n_schools_here > 1:
        return "shared"
    if dist <= HIGH_M:
        return "high"
    if dist <= MEDIUM_M:
        return "medium"
    return "low"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="query at most N new coordinates (pilot run)")
    args = ap.parse_args()

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        sys.exit("ERROR: set GOOGLE_MAPS_API_KEY")

    os.makedirs(OUT_DIR, exist_ok=True)

    geo = pd.read_csv(GEO_FILE, dtype={"source_id": str})[0:25]
    geo["key"] = [coord_key(a, b) for a, b in zip(geo["latitude"], geo["longitude"])]
    n_at_key = geo["key"].value_counts()
    geo["n_schools_at_coord"] = geo["key"].map(n_at_key)

    sites = geo.drop_duplicates("key")[["key", "latitude", "longitude"]]
    cache = load_cache(CACHE_FILE)
    todo = sites[~sites["key"].isin(cache)]
    if args.limit:
        todo = todo.head(args.limit)

    print(f"Schools: {len(geo)} | unique coordinates: {len(sites)} | "
          f"cached: {len(cache)} | to query now: {len(todo)}")

    # ── Query (append to cache as we go so the run can resume) ───────────
    session = requests.Session()
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        for i, row in enumerate(todo.itertuples(index=False), 1):
            resp = search_nearby(session, api_key, row.latitude, row.longitude)
            cache[row.key] = resp
            f.write(json.dumps({"key": row.key, "response": resp},
                               ensure_ascii=False) + "\n")
            if i % 100 == 0:
                f.flush()
                print(f"  {i}/{len(todo)} queried")
            time.sleep(SLEEP_S)

    # ── Build per-school output from cache ────────────────────────────────
    rows = []
    for r in geo.itertuples(index=False):
        resp = cache.get(r.key)
        queried = resp is not None
        cands = parse_candidates(resp, r.latitude, r.longitude) if queried else []
        best = cands[0] if cands else {}
        dist = best.get("distance_m")
        rows.append({
            "geo_id":              r.geo_id,
            "source_id":           r.source_id,
            "latitude":            r.latitude,
            "longitude":           r.longitude,
            "n_schools_at_coord":  r.n_schools_at_coord,
            "queried":             queried,
            "n_candidates":        len(cands),
            "gm_place_id":         best.get("place_id"),
            "gm_name":             best.get("name"),
            "gm_name_lang":        best.get("name_lang"),
            "gm_primary_type":     best.get("primary_type"),
            "gm_address":          best.get("address"),
            "gm_distance_m":       round(dist, 1) if dist is not None else None,
            "gm_name_2":           cands[1]["name"] if len(cands) > 1 else None,
            "gm_distance_m_2":     round(cands[1]["distance_m"], 1) if len(cands) > 1 else None,
            "match_confidence":    confidence(dist, r.n_schools_at_coord) if queried else pd.NA,
        })
    out = pd.DataFrame(rows)

    # Same Google place matched to several different coordinates is suspect
    dup_place = out["gm_place_id"].notna() & out["gm_place_id"].duplicated(keep=False)
    out["gm_place_reused"] = dup_place

    out.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    # ── QA ────────────────────────────────────────────────────────────────
    q = out[out["queried"]]
    print("\n=== YEM reverse-name QA ===")
    print(f"Schools with a queried coordinate: {len(q)} / {len(out)}")
    print("\nmatch_confidence:")
    print(q["match_confidence"].value_counts(dropna=False).to_string())
    print(f"\nGoogle place matched to >1 school: {int(q['gm_place_reused'].sum())}")
    if q["gm_distance_m"].notna().any():
        print("\nDistance to nearest school POI (m):")
        print(q["gm_distance_m"].describe().round(1).to_string())
    print(f"\n✓ Saved {OUT_FILE}")


if __name__ == "__main__":
    main()
