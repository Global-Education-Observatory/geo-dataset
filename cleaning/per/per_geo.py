"""
per_geo.py
----------
Cleans the Peru Padron de Instituciones Educativas (Marco Censal 2024) to
produce per_geo.csv conforming to the GEO Dataset canonical schema v1.0.

Source:
    Ministerio de Educacion del Peru, Unidad de Estadistica (ESCALE)
    Padron.dbf / marco censal, Censo Educativo 2024
    https://escale.minedu.gob.pe  (Bases de datos > A. Censo Educativo > 2024)

Unit of observation:
    One row per servicio educativo (COD_MOD + ANEXO). A single building
    (CODLOCAL) or institution (CODINST) can host several services, so primary
    and secondary in the same campus are separate rows. CODINST is carried as
    source_id_institution (same pattern as Colombia).

Scope:
    Public EBR primary and secondary only.
      - GESTION starts with "Publica" (includes Publica de gestion privada,
        i.e. Convenio schools, treated as public, same precedent as
        Bangladesh MPO and Belize Government Aided)
      - NIV_MOD in LEVEL_MAP below
    Excluded: private, inicial (ISCED 0), EBA, EBE, superior, CETPRO.

ISCED mapping:
    Primaria   -> 1
    Secundaria -> 2|3  (5 grades spanning ISCED 2 and 3, no within-secondary
                        disaggregation, same convention as BLZ)

Coordinates:
    NLAT_IE / NLONG_IE already WGS84 decimal degrees.
    TIPOCOORD == 1 (519 rows in the full file) is a centro poblado centroid,
    verified by one distinct point per CODCP_MED, so it maps to admin_centroid.
    TIPOCOORD == 2 is a school point, provenance from FTE_LOCAL.

OPEN ITEMS (need the Padron dictionary value lists)
    - FTE_LOCAL MED_RIE / MED_REG mapped as official_emis / approximate
      (not centroids, collection method undocumented)
    - IMPUTADO (values 1, 2, 3) is not used in any mapping yet
    - NIV_MOD codes below should be confirmed against D_NIV_MOD labels
    - urban_rural codes confirmed from DAREACENSO labels, see QA print
    - status has no source field, set to 'unknown'

Author: HB
Date: 2026-10-01
"""

import os
import sys
import unicodedata

import numpy as np
import pandas as pd
from dbfread import DBF


# ── Paths ─────────────────────────────────────────────────────────────────
SOURCE_FILE = "../../sources/PER/Padron.dbf"  # TODO confirm
OUTPUT_FILE = "../../db/geo/per_geo.csv"
ISO3 = "PER"

# ── Config ────────────────────────────────────────────────────────────────
# Set STRICT = False to let unresolved FTE_LOCAL values (MED_RIE, MED_REG)
# fall through to a provisional official_emis / approximate mapping.
STRICT = True

PUBLIC_GESTION = ["1", "2"]

# NIV_MOD -> (ISCED, label). CONFIRM against D_NIV_MOD before trusting.
LEVEL_MAP = {
    "B0": "1",     # Primaria
    "F0": "2|3",   # Secundaria
}

# FTE_LOCAL -> (coordinate_source, coordinate_precision)
FTE_MAP = {
    "MED_GPS":           ("gps_field", "exact"),
    "UGEL_GPS":          ("gps_field", "exact"),
    "UGELCENSO_GPS":     ("gps_field", "exact"),
    "GPS_OTRAS_FUENTES": ("gps_field", "exact"),
    "UBICACION_WEB":     ("official_emis", "approximate"),
    "UBICACION_WEB_MED": ("official_emis", "approximate"),
    # Ministry-sourced points, collection method undocumented. Not centroids
    # (up to 6 distinct points per CODCP_MED, 41-45% shared-point rate, same as
    # ordinary school points), so mapped conservatively as approximate.
    "MED_RIE":           ("official_emis", "approximate"),
    "MED_REG":           ("official_emis", "approximate"),
}
FTE_UNRESOLVED = set()  # add any FTE_LOCAL value here to make the script stop on it
FTE_PROVISIONAL = ("official_emis", "approximate")

GEO_COLS = [
    "geo_id", "source_id", "country", "school_name", "school_name_romanized",
    "isced_level", "school_type", "sector",
    "adm0", "adm1", "adm2", "adm3",
    "urban_rural", "ghsl_smod_code", "ghsl_urban_rural",
    "latitude", "longitude", "coordinate_source", "coordinate_precision",
    "status",
]
# Not in schema.md v1.0 but used in the project (Colombia). Appended last.
EXTRA_COLS = ["source_id_institution"]


def _norm(s):
    """Uppercase, strip accents and whitespace. NaN stays NaN."""
    if pd.isna(s):
        return s
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().upper()


# cp850 bytes for a, e, i, o, u, n-tilde etc. as they appear when read as latin-1
MOJIBAKE_MARKERS = "\u00a3\u00a2\u00a4\u00a5\u00a1\u00a0\u0082\u0090\u00b5"


def fix_mojibake(s):
    """
    The Padron is a DOS-era dbf (code page 850). If it was read as latin-1 /
    cp1252 the accents come out as e.g. 'P£blica de gesti¢n'. Re-encode and
    decode to repair. Only strings containing the tell-tale characters are
    touched, so text that is already correct is returned unchanged.
    """
    if pd.isna(s):
        return s
    if not any(ch in s for ch in MOJIBAKE_MARKERS):
        return s
    try:
        return s.encode("latin-1").decode("cp850")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


TEXT_COLS = ["CEN_EDU", "D_NIV_MOD", "D_GESTION", "DAREACENSO", "DIST", "DPTO", "PROV"]


def load_source(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path, dtype=str)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    if ext == ".dbf":
        import geopandas as gpd
        return pd.DataFrame(iter(DBF(SOURCE_FILE, encoding="latin-1", ignore_missing_memofile=True))).replace("None", np.nan)
    raise ValueError(f"Unsupported source format: {ext}")


def build_geo(df):
    """Everything up to (not including) the admin boundary join and geo_id."""
    df = df.copy()
    print(f"Source rows: {len(df)}")
    for c in TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].map(fix_mojibake)

    # ── Public filter ────────────────────────────────────────────────────
    # Filter on the code, not the label (labels carry encoding noise).
    # 1 = Publica de gestion directa, 2 = Publica de gestion privada (Convenio),
    # 3 = Privada, confirmed from the value counts of the 2024 file.
    print("\nGESTION value counts (check the public filter):")
    print(df.groupby(["GESTION", "D_GESTION"], dropna=False).size())
    unexpected = set(df["GESTION"].dropna().unique()) - set(PUBLIC_GESTION) - {"3"}
    if unexpected:
        raise ValueError(f"Unexpected GESTION codes {unexpected}, review the public filter")
    df = df[df["GESTION"].isin(PUBLIC_GESTION)].copy()
    print(f"After public filter: {len(df)}")

    # ── Level filter ─────────────────────────────────────────────────────
    print("\nNIV_MOD value counts among public services:")
    print(df.groupby(["NIV_MOD", "D_NIV_MOD"], dropna=False).size())
    df = df[df["NIV_MOD"].isin(LEVEL_MAP)].copy()
    print(f"After level filter ({list(LEVEL_MAP)}): {len(df)}")

    # ── Identifiers ──────────────────────────────────────────────────────
    # COD_MOD (7) + ANEXO (1), kept as strings so leading zeros survive
    df["source_id"] = df["COD_MOD"].str.strip() + df["ANEXO"].str.strip()
    df["source_id_institution"] = df["CODINST"].str.strip().replace("", np.nan)
    dup = df["source_id"].duplicated().sum()
    print(f"Duplicate source_id (retained verbatim): {dup}")

    # ── Names, level, type, sector ───────────────────────────────────────
    df["country"] = ISO3
    df["school_name"] = df["CEN_EDU"].str.strip()
    df["school_name_romanized"] = pd.NA
    df["isced_level"] = df["NIV_MOD"].map(LEVEL_MAP)
    df["school_type"] = df["D_NIV_MOD"].str.strip()
    df["sector"] = "public"
    df["adm0"] = "Peru"

    # ── Urban / rural (country-reported, not reclassified) ──────────────
    ar = df["DAREACENSO"].map(_norm)
    print("\nDAREACENSO value counts (confirm mapping):")
    print(df.groupby(["AREA_CENSO", "DAREACENSO"], dropna=False).size())
    ur_map = {"URBANA": "urban", "URBANO": "urban", "RURAL": "rural"}
    df["urban_rural"] = ar.map(ur_map)
    unmapped_ar = ar[ar.notna() & ~ar.isin(ur_map)].unique()
    if len(unmapped_ar):
        print(f"  WARNING: unmapped DAREACENSO values set to NA: {unmapped_ar}")

    # ── Coordinates ──────────────────────────────────────────────────────
    df["latitude"] = pd.to_numeric(df["NLAT_IE"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["NLONG_IE"], errors="coerce")

    n0 = len(df)
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    print(f"\nDropped {n0 - len(df)} rows with missing coordinates")

    tipo = df["TIPOCOORD"].str.strip()
    fte = df["FTE_LOCAL"].str.strip().replace("", np.nan)

    # Blank FTE_LOCAL should coincide with centroid rows (TIPOCOORD == 1)
    blank_not_centroid = (fte.isna() & (tipo != "1")).sum()
    if blank_not_centroid:
        raise ValueError(f"{blank_not_centroid} rows have blank FTE_LOCAL but TIPOCOORD != 1")

    unknown = set(fte.dropna().unique()) - set(FTE_MAP) - FTE_UNRESOLVED
    if unknown:
        raise ValueError(f"Unmapped FTE_LOCAL values, add to FTE_MAP: {unknown}")

    unresolved_hit = (fte.isin(FTE_UNRESOLVED) & (tipo != "1")).sum()
    if unresolved_hit and STRICT:
        raise ValueError(
            f"{unresolved_hit} rows use unresolved FTE_LOCAL values {FTE_UNRESOLVED}. "
            "Define them from the Padron dictionary, or set STRICT = False to map "
            "them provisionally to official_emis / approximate."
        )
    if unresolved_hit:
        print(f"  WARNING: {unresolved_hit} rows mapped PROVISIONALLY (MED_RIE / MED_REG)")

    def _coord(t, f):
        if t == "1":
            return ("admin_centroid", "admin_centroid")
        if f in FTE_MAP:
            return FTE_MAP[f]
        return FTE_PROVISIONAL  # unresolved, only reached when STRICT is False

    pairs = [_coord(t, f) for t, f in zip(tipo, fte)]
    df["coordinate_source"] = [p[0] for p in pairs]
    df["coordinate_precision"] = [p[1] for p in pairs]

    # ── Status ───────────────────────────────────────────────────────────
    # No status field in the Padron extract
    df["status"] = "unknown"

    # ── QA extras (IMPUTADO is not mapped yet) ───────────────────────────
    print("\nFTE_LOCAL x IMPUTADO (to interpret IMPUTADO):")
    print(pd.crosstab(fte.fillna("BLANK"), df["IMPUTADO"]))

    return df


def main():
    print("Loading source data...")
    raw = load_source(SOURCE_FILE)
    df = build_geo(raw)

    # ── Admin boundaries from GeoBoundaries (standing project rule) ──────
    import geopandas as gpd
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pipeline"))
    from geo_boundaries import join_admin_boundaries

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326"
    )
    print("\nJoining admin boundaries from GeoBoundaries...")
    gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])

    # Schools outside ADM1 are dropped, not nulled (Colombia precedent)
    n0 = len(gdf)
    gdf = gdf[gdf["adm1"].notna()].copy()
    print(f"Dropped {n0 - len(gdf)} rows outside ADM1 boundaries")

    # Report disagreement with the ministry's own district labels (validation stat)
    if "DIST" in gdf.columns and gdf["adm3"].notna().any():
        a = gdf["adm3"].map(_norm)
        b = gdf["DIST"].map(_norm)
        both = a.notna() & b.notna()
        print(f"ADM3 vs ministry DIST name agreement: {(a[both] == b[both]).mean():.3f} "
              f"(n={both.sum()}, exact string match, expect accent/naming noise)")

    # ── geo_id assigned last, sorted by school name (tiebreak source_id) ─
    gdf = gdf.sort_values(["school_name", "source_id"]).reset_index(drop=True)
    gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]

    gdf["ghsl_smod_code"] = pd.NA
    gdf["ghsl_urban_rural"] = pd.NA

    geo = pd.DataFrame(gdf)[GEO_COLS + EXTRA_COLS].copy()

    # ── QA ───────────────────────────────────────────────────────────────
    print("\n=== PER_geo QA ===")
    print(f"Total rows: {len(geo)}")
    never_null = ["geo_id", "source_id", "country", "school_name", "isced_level",
                  "sector", "adm0", "coordinate_source", "coordinate_precision", "status"]
    for col in never_null:
        n = geo[col].isna().sum()
        print(f"  {'WARNING' if n else 'OK'}: {col} nulls = {n}")
    assert geo["geo_id"].is_unique, "Duplicate geo_ids"
    assert geo["sector"].eq("public").all()
    print("\nisced_level:\n", geo["isced_level"].value_counts())
    print("\ncoordinate_source:\n", geo["coordinate_source"].value_counts())
    print("\ncoordinate_precision:\n", geo["coordinate_precision"].value_counts())
    print("\nurban_rural:\n", geo["urban_rural"].value_counts(dropna=False))
    print("\nadm1:\n", geo["adm1"].value_counts().head(30))
    print(f"\nsource_id_institution missing: {geo['source_id_institution'].isna().sum()}")

    if len(geo) == 0:
        raise RuntimeError("Zero rows after cleaning, not writing output")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    geo.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()