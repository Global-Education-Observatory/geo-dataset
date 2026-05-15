"""
hnd_resources.py
----------------
Cleans Honduras EMIS infrastructure data to produce hnd_resources.csv
conforming to the GEO Dataset canonical schema v1.0.

Sources:
    2011: 31_MatriculaInicial2011_Infraestructura_porCentroEducativoCompleto.csv
        School-level infrastructure survey. One row per school × ISCED level;
        multi-level schools deduplicated by taking max() across level rows
        (see Duplicates note below).

Excluded sources:
    42_Infraestrcutura.xlsx (labelled 2010): id_centro is an internal survey ID,
        not the EMIS CodigoCentro. No reliable join to geo_id is possible.
        Excluded entirely. See harmonization note.

Coverage:
    Resources data available for 2011 only.

Variables mapped:
    water_basic     : Tipo Agua — Potable/Pozo → 1; Río/Otra Fuente/Ninguna → 0;
                      NA → NA. Pozo (unprotected well status unknown) mapped to 1
                      conservatively per project decision; flagged in harmonization note.
    water_improved  : Tipo Agua — Potable → 1; all others → 0; NA → NA.
                      Only Potable qualifies as improved (piped/treated) under JMP.
    electricity     : Suministro Electricidad — any non-Ninguno value → 1;
                      Ninguno → 0; NA → NA. Covers grid (ENEE), solar, generator, other.
    internet        : Tiene Internet — Si → 1; No → 0.
    computers       : Cant. PC Alumnos — ≥ 1 → 1; 0 → 0. Boolean indicator of
                      whether school has computers available for instructional use.
                      Source records count of student PCs, not a direct lab indicator.
    internet_type   : Not collected in source → NA throughout.
    classrooms_total: Not in 2011 source file. Available in 2010 xlsx but that file
                      cannot be joined to geo_id → NA throughout.
    sanitation_basic          : Not collected → NA throughout.
    sanitation_sex_separated  : Not collected → NA throughout.
    handwashing_basic         : Not collected → NA throughout.
    library                   : Not collected → NA throughout.
    permanent_building        : Dropped from schema entirely (all countries).

Duplicates:
    2011 file has one row per school × ISCED level. Multi-level schools appear
    multiple times under the same Codigo.1. Deduplicated by taking max() across
    all rows for a given school — if any level row indicates electricity/water/
    internet, the school is coded 1. For pc count, max() captures the highest
    count reported across levels.

Scope:
    Filtered to Administracion == 'Publico'. Schools joined to geo via
    source_id (stripping leading zeros). Schools in geo with no infrastructure
    record are excluded (no null rows inserted).

Author: HB
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEO_FILE = os.path.join(BASE_DIR, "db", "geo", "hnd_geo.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "db", "resources", "hnd_resources.csv")
DATA_DIR = os.path.join(BASE_DIR, "sources", "HND")


# ── Load geo ID lookup ────────────────────────────────────────────────────────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str, "geo_id": str})
geo["id_norm"] = geo["source_id"].str.lstrip("0")
id_to_geo = dict(zip(geo["id_norm"], geo["geo_id"]))
print(f"  Geo schools: {len(geo)}")


# ── Load 2011 infrastructure file ─────────────────────────────────────────────
print("\nLoading 2011 infrastructure file...")
df = pd.read_csv(
    os.path.join(DATA_DIR, "31_MatriculaInicial2011_Infraestructura_porCentroEducativoCompleto.csv"),
    encoding="latin1",
    low_memory=False,
)
df = df[df["Administracion"] == "Publico"].copy()
df["id_norm"] = df["Codigo.1"].dropna().astype(int).astype(str)
print(f"  Rows (public): {len(df)}")
print(f"  Unique school IDs: {df['id_norm'].nunique()}")


# ── Map variables ─────────────────────────────────────────────────────────────

# water_basic: Potable/Pozo → 1; Río/Otro/Ninguna → 0; NaN → NA
water_basic_map = {
    "Potable": 1,
    "Pozo":    1,   # unprotected status unknown; mapped 1, flagged in harmonization note
    "Río":     0,
    "Otro":    0,
    "Ninguna": 0,
}
df["water_basic"] = df["Tipo Agua"].map(water_basic_map)  # unmapped (NaN) stays NA

# water_improved: Potable → 1; all others → 0; NaN → NA
def map_water_improved(val):
    if pd.isna(val):
        return pd.NA
    return 1 if str(val).strip() == "Potable" else 0

df["water_improved"] = df["Tipo Agua"].apply(map_water_improved)

# electricity: anything except Ninguno → 1; Ninguno → 0; NaN → NA
def map_electricity(val):
    if pd.isna(val):
        return pd.NA
    return 0 if str(val).strip() == "Ninguno" else 1

df["electricity"] = df["Suministro Electricidad"].apply(map_electricity)

# internet: Si → 1; No → 0
df["internet"] = df["Tiene Internet"].map({"Si": 1, "No": 0})

# computers: pc_alumnos >= 1 → 1; 0 → 0
df["computers"] = (df["Cant. PC Alumnos"].fillna(0) >= 1).astype(int)


# ── Deduplicate multi-level schools ───────────────────────────────────────────
# Take max() per school — if any level row has the resource, school has it.
# For binary vars this means 1 wins over 0; for NA-containing columns,
# max() ignores NA (skipna=True default), so a single valid value is retained.
agg_cols = ["water_basic", "water_improved", "electricity", "internet", "computers"]
df_agg = df.groupby("id_norm")[agg_cols].max().reset_index()
print(f"\n  After dedup to school level: {len(df_agg)} schools")


# ── Filter to geo schools ─────────────────────────────────────────────────────
before = len(df_agg)
df_agg = df_agg[df_agg["id_norm"].isin(id_to_geo)].copy()
print(f"  After geo filter: {len(df_agg)} schools ({before - len(df_agg)} dropped)")


# ── Build output ──────────────────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]                  = df_agg["id_norm"].map(id_to_geo)
out["year"]                    = 2011
out["water_basic"]             = df_agg["water_basic"].astype("Int64")
out["water_improved"]          = df_agg["water_improved"].astype("Int64")
out["sanitation_basic"]        = pd.NA
out["sanitation_sex_separated"]= pd.NA
out["handwashing_basic"]       = pd.NA
out["electricity"]             = df_agg["electricity"].astype("Int64")
out["internet"]                = df_agg["internet"].astype("Int64")
out["internet_type"]           = pd.NA
out["computers"]               = df_agg["computers"].astype("Int64")
out["library"]                 = pd.NA
out["classrooms_total"]        = pd.NA


# ── Validation ────────────────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].notna().all(),  "ERROR: Null geo_ids"
assert out["year"].notna().all(),    "ERROR: Null years"
assert out.duplicated(subset=["geo_id", "year"]).sum() == 0, "ERROR: Duplicate geo_id × year"

for col in ["water_basic", "water_improved", "electricity", "internet", "computers"]:
    vals = out[col].dropna().unique()
    assert set(vals).issubset({0, 1}), f"ERROR: Non-binary values in {col}: {vals}"

print(f"\n  Total rows           : {len(out)}")
print(f"  Geo schools covered  : {out['geo_id'].nunique()} / {len(geo)}")
print(f"  Geo schools excluded : {len(geo) - out['geo_id'].nunique()}")
for col in agg_cols:
    n1 = (out[col] == 1).sum()
    n0 = (out[col] == 0).sum()
    nna = out[col].isna().sum()
    print(f"  {col:20s}: 1={n1:5d}  0={n0:5d}  NA={nna:4d}")


# ── Save ──────────────────────────────────────────────────────────────────────
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")
