"""
bra_geo.py
----------
Cleans the Brazil INEP Catálogo de Escolas to produce bra_geo.csv
conforming to the GEO Dataset canonical schema v1.0.

Source:
    INEP — Catálogo de Escolas (Censo Escolar da Educação Básica)
    URL: https://anonymousdata.inep.gov.br/analytics/ [Catálogo de Escolas portal]
    Format: CSV export from INEP Data portal
    Year: TODO — confirm which Censo Escolar year this export reflects

Scope:
    Public schools only:
      - Categoria Administrativa == 'Pública'
      - Dependência Administrativa IN ['Municipal', 'Estadual', 'Federal']
      - Conveniada Poder Público == 'Não'  (excludes charter/conveniada schools)
      - Must offer at least one of: Ensino Fundamental, Ensino Médio
    Excluded:
      - Private schools (Categoria Administrativa == 'Privada')
      - Conveniadas (private schools contracted by government as overflow capacity)
      - Schools offering only: Educação Infantil, Educação Profissional,
        Educação de Jovens Adultos (outside compulsory education scope)

    Note: Conveniadas are privately-owned schools (for-profit or non-profit)
    that partner with municipalities to absorb students who cannot find spots
    in the public system. They are treated as private-sector overflow, not
    public schools, and excluded from V1 scope.

ISCED mapping (from Etapas e Modalidade de Ensino Oferecidas):
    Contains 'Ensino Fundamental' only               → 1
    Contains 'Ensino Médio' only                     → 3
    Contains both 'Ensino Fundamental' and 'Ensino Médio' → 1|3
    (Ensino Fundamental spans ISCED 1 and lower ISCED 2 in Brazil's 9-year
     structure; no within-Fundamental disaggregation available in source.
     Ensino Médio = ISCED 3. Educação Infantil excluded from isced_level
     even where offered alongside in-scope levels.)

Admin hierarchy:
    adm1–adm3 assigned via spatial join to GeoBoundaries ADM1–ADM3 for BRA.
    Source UF and Município columns are NOT used for adm fields — GeoBoundaries
    spatial join is the authoritative source per pipeline standard.

Coordinates:
    Latitude/Longitude present in source. Decimal degrees, assumed WGS84.
    coordinate_source = 'official_emis'
    coordinate_precision = 'approximate'
    Schools with missing coordinates are dropped (not nulled) per pipeline rule.

school_type:
    Populated from Localidade Diferenciada where not null/empty, to capture
    indigenous land (terra indígena), quilombola, and settlement schools.
    Otherwise set to NA.

Author: HB
"""

import pandas as pd
import geopandas as gpd
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
from geo_boundaries import join_admin_boundaries

# ── Paths ──────────────────────────────────────────────────────────────────
SOURCE_FILE = "/Users/heatherbaier/Documents/research/geo/sources/BRA/Análise - Tabela da lista das escolas - Detalhado.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/geo/bra_geo.csv"

ISO3 = "BRA"

# ── Load ───────────────────────────────────────────────────────────────────
print("Loading source data...")
df = pd.read_csv(SOURCE_FILE, dtype=str)
print(f"  Total rows: {len(df)}")

# ── Filter: public, non-conveniada, in-scope levels ───────────────────────
print("\nFiltering to public in-scope schools...")

df = df[
    (df["Categoria Administrativa"] == "Pública") &
    (df["Dependência Administrativa"].isin(["Municipal", "Estadual", "Federal"])) &
    (df["Conveniada Poder Público"] == "Não")
].copy()
print(f"  After public/non-conveniada filter: {len(df)}")

IN_SCOPE_LEVELS = ["Ensino Fundamental", "Ensino Médio"]
df = df[
    df["Etapas e Modalidade de Ensino Oferecidas"].apply(
        lambda x: any(level in str(x) for level in IN_SCOPE_LEVELS)
    )
].copy()
print(f"  After in-scope level filter: {len(df)}")

# ── Drop missing coordinates ───────────────────────────────────────────────
df["Latitude"]  = pd.to_numeric(df["Latitude"],  errors="coerce")
df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

before = len(df)
df = df[df["Latitude"].notna() & df["Longitude"].notna()].copy()
dropped = before - len(df)
if dropped > 0:
    print(f"  Dropped {dropped} schools with missing coordinates")
print(f"  Schools with coordinates: {len(df)}")

# ── Build GeoDataFrame for spatial join ────────────────────────────────────
print("\nBuilding GeoDataFrame...")
gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
    crs="EPSG:4326"
)

# ── Assign geo_id ──────────────────────────────────────────────────────────
# Sort by Código INEP for stable, reproducible ID assignment
gdf = gdf.sort_values("Código INEP").reset_index(drop=True)
gdf["geo_id"] = [f"{ISO3}_{str(i + 1).zfill(6)}" for i in gdf.index]
print(f"  geo_id range: {gdf['geo_id'].iloc[0]} to {gdf['geo_id'].iloc[-1]}")

# ── ISCED level ────────────────────────────────────────────────────────────
def map_isced(etapas):
    s = str(etapas)
    has_fund = "Ensino Fundamental" in s
    has_med  = "Ensino Médio" in s
    if has_fund and has_med:
        return "1|3"
    elif has_fund:
        return "1"
    elif has_med:
        return "3"
    return pd.NA

gdf["isced_level"] = gdf["Etapas e Modalidade de Ensino Oferecidas"].apply(map_isced)

print("\nisced_level distribution:")
print(gdf["isced_level"].value_counts())

# ── Urban/rural ────────────────────────────────────────────────────────────
urban_rural_map = {
    "Urbana": "urban",
    "Rural":  "rural",
}
gdf["urban_rural"] = gdf["Localização"].map(urban_rural_map)

# ── school_type: capture localidade diferenciada ──────────────────────────
# Retain indigenous/quilombola/settlement designation where present
gdf["school_type"] = gdf["Localidade Diferenciada"].apply(
    lambda x: x.strip() if pd.notna(x) and str(x).strip() not in ["", "Área de Localização Diferenciada não se aplica"] else pd.NA
)

# ── Spatial join: admin boundaries from GeoBoundaries ─────────────────────
print("\nJoining admin boundaries from GeoBoundaries...")
gdf = join_admin_boundaries(gdf, iso3=ISO3, levels=[1, 2, 3])

# ── Assemble output ────────────────────────────────────────────────────────
print("\nAssembling output...")
out = pd.DataFrame()

out["geo_id"]                = gdf["geo_id"]
out["source_id"]             = gdf["Código INEP"].astype(str).str.strip()
out["country"]               = ISO3
out["school_name"]           = gdf["Escola"].str.strip()
out["school_name_romanized"] = pd.NA          # Portuguese is Latin script
out["isced_level"]           = gdf["isced_level"]
out["school_type"]           = gdf["school_type"]
out["sector"]                = "public"
out["adm0"]                  = "Brazil"
out["adm1"]                  = gdf["adm1"]
out["adm2"]                  = gdf["adm2"]
out["adm3"]                  = gdf["adm3"]
out["urban_rural"]           = gdf["urban_rural"]
out["ghsl_smod_code"]        = pd.NA
out["ghsl_urban_rural"]      = pd.NA
out["latitude"]              = gdf["Latitude"]
out["longitude"]             = gdf["Longitude"]
out["coordinate_source"]     = "official_emis"
out["coordinate_precision"]  = "approximate"
out["status"]                = "open"

# ── QA checks ──────────────────────────────────────────────────────────────
print("\n=== BRA_geo QA ===")
print(f"Total rows: {len(out)}")

never_null = ["geo_id", "source_id", "country", "school_name",
              "isced_level", "sector", "adm0",
              "coordinate_source", "coordinate_precision", "status"]
for col in never_null:
    n = out[col].isna().sum()
    status = "OK" if n == 0 else f"WARNING: {n} nulls — schema violation"
    print(f"  {status}: {col}")

print(f"\nDuplicate geo_ids:  {out['geo_id'].duplicated().sum()}")
print(f"Duplicate source_ids: {out['source_id'].duplicated().sum()}")
print(f"\nisced_level distribution:\n{out['isced_level'].value_counts()}")
print(f"\nDependência distribution (pre-filter check):\n{gdf['Dependência Administrativa'].value_counts()}")
print(f"\nurban_rural distribution:\n{out['urban_rural'].value_counts()}")
print(f"\nschool_type (localidade diferenciada) distribution:\n{out['school_type'].value_counts(dropna=False).head(10)}")
print(f"\nadm1 — top 10:\n{out['adm1'].value_counts().head(10)}")
print(f"\nMissing adm1: {out['adm1'].isna().sum()}")
print(f"Missing adm2: {out['adm2'].isna().sum()}")
print(f"Missing adm3: {out['adm3'].isna().sum()}")

# ── Save ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")