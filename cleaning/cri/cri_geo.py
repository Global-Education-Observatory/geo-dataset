"""
cri_geo.py
----------
Builds cri_geo.csv from MEP enrollment files (2014–2025), a GPS coordinates
shapefile (June 2024), and a poblados centroid shapefile for fallback matching.

Conforms to GEO Dataset canonical schema v1.0.

Sources:
    Enrollment (primary, I y II Ciclos, 2014-2022):
        matriculainicialescuelasdiurnas-2014-2022-aniocursadosexo.xlsx
    Enrollment (secondary, III Ciclo + Educacion Diversificada, 2014-2022):
        MATRICULA_INICIAL_COLEGIOS_2014-2022_POR_ANIO_CURSADO_Y_SEXO.xlsx
    Enrollment (primary + secondary, 2023-2025, pre-cleaned):
        nominacentroseducativos-2023_edited.xlsx
        NominaCentrosEducativos2024_edited.xlsx
        NominaCentrosEducativos2025_edited.xlsx
        Note: these are matricula inicial files. The *_edited versions have been
        pre-cleaned to normalise column names and remove formatting rows. Column
        names are consistent across all three years. Enrollment is a single total
        per school (no grade or sex disaggregation available for 2023-2025).
    Coordinates:
        CE_PUBLICOS_SABER_JUN24_wsg4326.shp  (SABER system, June 2024)
    Poblados centroids (fallback):
        Poblados_de_Costa_Rica-shp/ae0d8a49-cfed-4f2e-92d9-b3b9909a9cde202042-1-b3h1at.ycopb.shp

Scope:
    Public schools only:
        2014-2022: SECTOR in {1, 3}  (1=Publico, 3=Subvencionado)
        2023-2025: DEPENDENCIA in {'PUB', 'SUB'}
    Primary (escuelas diurnas): ISCED 1, grades 1-6
    Secondary (colegios): ISCED 2|3, grades 7-12
        2014-2022: RAMA in {11, 21}
        2023-2025: RAMA-HORARIO in {'ACADEMICA DIURNA', 'TECNICA DIURNA'} (incl. accented)
        Nocturno (RAMA 12/22) and Artistico (RAMA 31) excluded
    CODIGO = 0 or null excluded

ISCED mapping:
    Escuelas (I y II Ciclos, grades 1-6)  -> 1
    Colegios (III Ciclo + Diversificada, grades 7-12) -> 2|3
        Note: no within-secondary disaggregation available; one administrative
        unit per CODIGO covers both ISCED 2 (grades 7-9) and ISCED 3 (10-12).

Coordinate assignment (three-tier):
    Tier 1 -- SABER GPS file (CODPRES join):
        coordinate_source    = 'official_emis'
        coordinate_precision = 'exact'
    Tier 2 -- Poblados centroid (PROVINCIA + CANTON + poblado join, ~42 schools):
        coordinate_source    = 'admin_centroid'
        coordinate_precision = 'approximate'
        Note: ~18 of these are urban (ZONA=1); urban centroid matches carry
        higher positional error than rural ones. Documented in harmonization note.
    Tier 3 -- No match: school dropped from geo entirely (schema rule).

Admin hierarchy:
    adm1-adm3 via spatial join to GeoBoundaries using shared pipeline utility.

Urban/rural:
    ZONA: 1/URB/URBANA -> 'urban', 2/RUR/RURAL -> 'rural'
    No peri_urban in source; GHSL provides cross-country classification.

sector column:
    All in-scope schools -> 'public'
    Subvencionadas are church-managed but fully MEP-funded and EMIS-managed.
    Treated as public per schema definition and Costa Rican convention.

Author: HB
Date: 2026-05-19
"""

import os
import sys
import pandas as pd
import geopandas as gpd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# -- Paths --------------------------------------------------------------------
BASE = "/Users/heatherbaier/Documents/research/geo"

ENROLL_L1    = os.path.join(BASE, "sources/CRI/new/matriculainicialescuelasdiurnas-2014-2022-aniocursadosexo.xlsx")
ENROLL_L2    = os.path.join(BASE, "sources/CRI/new/MATRICULA_INICIAL_COLEGIOS_2014-2022_POR_ANIO_CURSADO_Y_SEXO.xlsx")
NOMINA_2023  = os.path.join(BASE, "sources/CRI/new/nominacentroseducativos-2023_edited.xlsx")
NOMINA_2024  = os.path.join(BASE, "sources/CRI/new/NominaCentrosEducativos2024_edited.xlsx")
NOMINA_2025  = os.path.join(BASE, "sources/CRI/new/NominaCentrosEducativos2025_edited.xlsx")
COORDS_SHP   = os.path.join(BASE, "sources/CRI/cri_schools/CE_PUBLICOS_SABER_JUN24_wsg4326.shp")
POBLADOS_SHP = os.path.join(BASE, "sources/CRI/Poblados_de_Costa_Rica-shp/ae0d8a49-cfed-4f2e-92d9-b3b9909a9cde202042-1-b3h1at.ycopb.shp")
OUTPUT_FILE  = os.path.join(BASE, "db/geo/cri_geo.csv")

ISO3 = "CRI"

# Lookup maps used by both geo and nomina loading
ZONA_MAP     = {"URB": 1, "RUR": 2, "URBANA": 1, "RURAL": 2, "1": 1, "2": 2}
PUBLIC_DEP   = {"PUB", "SUB", "PUBLICA", "SUBVENCIONADA"}
DAYTIME_RAMA = {"ACADEMICA DIURNA", "ACADEMICA DIURNA", "TECNICA DIURNA", "TECNICA DIURNA",
                "11", "21"}

# -- 1. Load and filter 2014-2022 enrollment files -> unique school universe ---
print("Loading 2014-2022 enrollment files...")

# Primary: I y II Ciclos
l1 = pd.read_excel(ENROLL_L1, skiprows=2)
l1 = l1[l1["SECTOR"].isin([1, 3])]
l1 = l1[l1["CODIGO"].notna() & (l1["CODIGO"] != 0)]
l1 = l1[["CODIGO", "NOMBRE", "PROVINCIA", "CANTON", "DISTRITO", "POBLADO", "ZONA"]].copy()
l1["isced_level"] = "1"
l1.columns = ["source_id", "school_name", "PROVINCIA", "CANTON", "DISTRITO", "poblado", "zona", "isced_level"]

# Secondary: Colegios
l2 = pd.read_excel(ENROLL_L2, skiprows=2)
l2 = l2[l2["SECTOR"].isin([1, 3])]
l2 = l2[l2["RAMA"].isin([11, 21])]
l2 = l2[l2["CODIGO"].notna() & (l2["CODIGO"] != 0)]
l2 = l2[["CODIGO", "NOMBRE", "PROVINCIA", "CANTON", "DISTRITO", "POBLADO", "ZONA"]].copy()
l2["isced_level"] = "2|3"
l2.columns = ["source_id", "school_name", "PROVINCIA", "CANTON", "DISTRITO", "poblado", "zona", "isced_level"]

all_schools = pd.concat([l1, l2], ignore_index=True)
all_schools["source_id"] = pd.to_numeric(all_schools["source_id"], errors="coerce").astype("Int64")
all_schools = all_schools.dropna(subset=["source_id"])
all_schools = all_schools.drop_duplicates(subset="source_id").reset_index(drop=True)

print(f"  Unique schools in 2014-2022: {len(all_schools)}")
print(f"    ISCED 1:   {(all_schools['isced_level'] == '1').sum()}")
print(f"    ISCED 2|3: {(all_schools['isced_level'] == '2|3').sum()}")

# -- 1b. Extend school universe from 2023-2025 edited enrollment files ---------
# All three years share the same post-edit column structure:
#   CODIGO, NOMBRE DE LA INSTITUCION, PROVINCIA, CANTON, DISTRITO ADMINISTRATIVO,
#   POBLADO, DEPENDENCIA (PUB/SUB/PRI), ZONA (URB/RUR)
#   Colegios additionally: RAMA-HORARIO (text)
print("\nExtending school universe from 2023-2025 enrollment files...")


def _load_nomina_sheet(path, sheet, isced_level):
    """Load one sheet from a 2023-2025 edited nomina file."""
    df = pd.read_excel(path, sheet_name=sheet, header=0)
    df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]

    if "CODIGO" not in df.columns:
        raise KeyError(f"CODIGO not found. Columns: {list(df.columns)}")

    df["CODIGO"] = pd.to_numeric(df["CODIGO"], errors="coerce")
    df = df[df["CODIGO"].notna() & (df["CODIGO"] != 0)].copy()
    df["CODIGO"] = df["CODIGO"].astype("Int64")

    # DEPENDENCIA filter
    if "DEPENDENCIA" in df.columns:
        df = df[df["DEPENDENCIA"].str.strip().str.upper().isin(PUBLIC_DEP)].copy()

    # RAMA-HORARIO filter for colegios
    if isced_level == "2|3":
        rama_col = next((c for c in df.columns if "RAMA" in c.upper()), None)
        if rama_col:
            rama_vals = df[rama_col].astype(str).str.strip().str.upper()
            # Normalise accented characters for matching
            rama_vals = rama_vals.str.replace("ACADEMICA", "ACADEMICA").str.replace("TECNICA", "TECNICA")
            df = df[rama_vals.isin(DAYTIME_RAMA)].copy()

    # ZONA normalisation
    zona = pd.NA
    if "ZONA" in df.columns:
        zona = df["ZONA"].astype(str).str.strip().str.upper().map(ZONA_MAP)

    name_col = next(
        (c for c in ["NOMBRE DE LA INSTITUCION", "NOMBRE DE LA INSTITUCION", "NOMBRE"] if c in df.columns),
        None
    )
    dist_col = next((c for c in ["DISTRITO ADMINISTRATIVO", "DISTRITO"] if c in df.columns), None)

    return pd.DataFrame({
        "source_id":   df["CODIGO"],
        "school_name": df[name_col].str.strip() if name_col else pd.NA,
        "PROVINCIA":   df["PROVINCIA"] if "PROVINCIA" in df.columns else pd.NA,
        "CANTON":      df["CANTON"] if "CANTON" in df.columns else pd.NA,
        "DISTRITO":    df[dist_col] if dist_col else pd.NA,
        "poblado":     df["POBLADO"] if "POBLADO" in df.columns else pd.NA,
        "zona":        zona,
        "isced_level": isced_level,
    })


nomina_frames = []
for path, label in [(NOMINA_2023, "2023"), (NOMINA_2024, "2024"), (NOMINA_2025, "2025")]:
    for sheet, isced in [("I y II Ciclos", "1"), ("Colegios", "2|3")]:
        try:
            frame = _load_nomina_sheet(path, sheet, isced)
            nomina_frames.append(frame)
            print(f"  {label} {sheet}: {len(frame)} schools loaded")
        except Exception as e:
            print(f"  WARNING: could not load {label} / {sheet}: {e}")

if nomina_frames:
    nomina_all = pd.concat(nomina_frames, ignore_index=True)
    nomina_all = nomina_all.drop_duplicates(subset="source_id")
    new_ids = set(nomina_all["source_id"]) - set(all_schools["source_id"])
    new_schools = nomina_all[nomina_all["source_id"].isin(new_ids)].copy()
    print(f"  New schools added from 2023-2025: {len(new_schools)}")
    all_schools = pd.concat([all_schools, new_schools], ignore_index=True)
    all_schools = all_schools.drop_duplicates(subset="source_id").reset_index(drop=True)

print(f"  Total unique schools (all years): {len(all_schools)}")

# -- 2. Load GPS coordinates file ---------------------------------------------
print("\nLoading coordinates shapefile...")
coords = gpd.read_file(COORDS_SHP)
coords = coords[["CODSABER", "CODPRES", "CENTRO_EDU", "LATITUD", "LONGITUD", "geometry"]].copy()
coords["CODPRES"] = pd.to_numeric(coords["CODPRES"], errors="coerce").astype("Int64")
coords = coords[coords["CODPRES"].isin(all_schools["source_id"])].copy()
coords = coords.rename(columns={"CODPRES": "source_id"})

# Keep main campus (-00) where multiple entries share a CODPRES
coords["is_main"] = coords["CODSABER"].str.endswith("-00")
coords = coords.sort_values(["source_id", "is_main"], ascending=[True, False])
coords = coords.drop_duplicates(subset="source_id", keep="first").drop(columns="is_main")
print(f"  Schools with GPS coordinates: {len(coords)}")

# -- 3. Tier-1 merge: GPS join ------------------------------------------------
print("\nMerging school universe with GPS coordinates...")
merged = all_schools.merge(coords[["source_id", "LATITUD", "LONGITUD"]], on="source_id", how="inner")
merged["coordinate_source"]    = "official_emis"
merged["coordinate_precision"] = "exact"
print(f"  Matched on GPS: {len(merged)}")

# -- 4. Tier-2 merge: poblados centroid fallback -------------------------------
print("\nAttempting poblados centroid fallback for unmatched schools...")
not_matched = all_schools[~all_schools["source_id"].isin(merged["source_id"])].copy()
print(f"  Schools without GPS: {len(not_matched)}")

poblados = gpd.read_file(POBLADOS_SHP)
poblados = poblados.rename(columns={"PUEBLO": "poblado"})
poblados_wgs = poblados.to_crs("EPSG:4326")
poblados_wgs["pob_lat"] = poblados_wgs.geometry.y
poblados_wgs["pob_lon"] = poblados_wgs.geometry.x
poblados_wgs = poblados_wgs[["PROVINCIA", "CANTON", "poblado", "pob_lat", "pob_lon"]].copy()

centroid_matched = not_matched.merge(
    poblados_wgs, on=["PROVINCIA", "CANTON", "poblado"], how="inner"
)
centroid_matched = centroid_matched.drop_duplicates(subset="source_id")
centroid_matched = centroid_matched.rename(columns={"pob_lat": "LATITUD", "pob_lon": "LONGITUD"})
centroid_matched["coordinate_source"]    = "admin_centroid"
centroid_matched["coordinate_precision"] = "approximate"
print(f"  Matched on poblado centroid: {len(centroid_matched)}")
print(f"    ZONA breakdown: {centroid_matched['zona'].value_counts().to_dict()}")

dropped = not_matched[~not_matched["source_id"].isin(centroid_matched["source_id"])]
print(f"  Dropped (no coordinate match): {len(dropped)}")

# -- 5. Combine tiers ---------------------------------------------------------
geo_working = pd.concat([merged, centroid_matched], ignore_index=True)
print(f"\n  Total schools with coordinates: {len(geo_working)}")

# -- 6. Spatial join to GeoBoundaries for adm1-adm3 ---------------------------
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = gpd.GeoDataFrame(
    geo_working,
    geometry=gpd.points_from_xy(geo_working["LONGITUD"], geo_working["LATITUD"]),
    crs="EPSG:4326"
)
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])
# gdf = gdf[~gdf["adm1"].isna()]

# -- 7. Assign geo_id ---------------------------------------------------------
gdf = gdf.sort_values("source_id").reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in range(len(gdf))]

# -- 8. Map remaining schema columns ------------------------------------------
gdf["urban_rural"] = gdf["zona"].map({1: "urban", 2: "rural"})

# -- 9. Assemble output in schema column order ---------------------------------
out = pd.DataFrame()
out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["source_id"].astype(str)
out["country"]               = ISO3
out["school_name"]           = gdf["school_name"].str.strip()
out["school_name_romanized"] = pd.NA
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = pd.NA
out["sector"]                = "public"
out["adm0"]                  = "Costa Rica"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = gdf["urban_rural"]
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["LATITUD"]
out["longitude"]             = gdf["LONGITUD"]
out["coordinate_source"]     = gdf["coordinate_source"]
out["coordinate_precision"]  = gdf["coordinate_precision"]
out["status"]                = "unknown"

# -- 10. QA checks ------------------------------------------------------------
print("\n=== CRI_geo QA ===")
print(f"Total rows: {len(out)}")
print()

never_null = ["geo_id", "source_id", "country", "school_name",
              "isced_level", "sector", "adm0", "coordinate_source",
              "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    print(f"  {'WARNING' if n > 0 else 'OK'}: {col} -- {n} nulls")

print()
print("isced_level distribution:")
print(out["isced_level"].value_counts().to_string())
print()
print("coordinate_source distribution:")
print(out["coordinate_source"].value_counts().to_string())
print()
print("coordinate_precision distribution:")
print(out["coordinate_precision"].value_counts().to_string())
print()
print("urban_rural distribution:")
print(out["urban_rural"].value_counts(dropna=False).to_string())
print()
print(f"adm1 nulls: {out['adm1'].isna().sum()}")
print(f"adm2 nulls: {out['adm2'].isna().sum()}")
print(f"adm3 nulls: {out['adm3'].isna().sum()}")
print()
print(f"Duplicate geo_ids:    {out['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids: {out['source_id'].duplicated().sum()}")

# -- 11. Save -----------------------------------------------------------------
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved to {OUTPUT_FILE}")
print(f"  Rows: {len(out)}  |  Columns: {len(out.columns)}")
