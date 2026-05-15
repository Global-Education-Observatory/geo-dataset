"""
hnd_outcomes.py
---------------
Cleans Honduras EMIS flow data to produce hnd_outcomes.csv conforming to the
GEO Dataset canonical schema v1.0, using within-year flow rates.

Method: within_year_flow (not UIS reconstructed cohort)
    promotion_rate  = Aprobados / Final
    repetition_rate = Reprobados / Final
    dropout_rate    = Desertores / implied_initial
                      where implied_initial = Final + Desertores + Traslados
                      (2009 uses Consolidada directly as initial enrollment;
                       2010/2011 use implied initial as Consolidada is absent)

Sources:
    2009: 9_MatriculaFinalPorGrados_2009 (1).csv
        Grade-level final flow stats. Has Consolidada (true initial enrollment).
    2010: Estadistica_final_2010_2011.csv (Año == 2010)
        Grade-level final flow stats. No Consolidada column — dropout uses
        implied initial (Final + Desertores + Traslados).
    2011: Estadistica_final_2010_2011.csv (Año == 2011)
        Same structure as 2010.
    2013: No outcome columns available → year excluded.

Scope:
    Rates computed only for schools offering graded education (ISCED 1/2/3).
    Pure pre-basic schools (Pre-Básica-Jardines, Pre-Básica-CCPREB) are
    excluded — pass/fail grading does not apply at ISCED 0.

Internal consistency check:
    Per schema checklist: rows where |Aprobados + Reprobados − Final| > 2% of
    Final have promotion_rate and repetition_rate set to NA. dropout_rate is
    set to NA for the same rows for consistency. Schools with Final == 0 also
    set to NA.

outcome_reference_grade: all_grades
    Rates are aggregated across all grades to the school level. Grade-level
    disaggregation is available in supplementary files.

Author: HB
"""

import os
import sys
import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GEO_FILE = os.path.join(BASE_DIR, "db", "geo", "hnd_geo.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "db", "outcomes", "hnd_outcomes.csv")
DATA_DIR = os.path.join(BASE_DIR, "sources", "HND")


DISC_THRESHOLD = 0.02   # 2% internal consistency tolerance

# Pure pre-basic nivel values — excluded from outcome computation
PURE_PREBAS = {
    "Pre-Básica-Jardines",
    "Pre-Básica-CCPREB",
    "Pre-Básica-CCPREB / Pre-Básica-Jardines",
    "Pre-Básica-Jardines / Pre-Básica-CCPREB",
}


# ── Load geo ──────────────────────────────────────────────────────────────────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str, "geo_id": str})
geo["id_norm"] = geo["source_id"].str.lstrip("0")
id_to_geo  = dict(zip(geo["id_norm"], geo["geo_id"]))
id_to_nivel = dict(zip(geo["id_norm"], geo["school_type"]))  # school_type = raw Nivel
print(f"  Geo schools: {len(geo)}")


# ── Helper: clean numeric columns ─────────────────────────────────────────────
def clean_num(series):
    return pd.to_numeric(
        series.astype(str)
              .str.replace(",", "", regex=False)
              .str.replace("-", "0", regex=False)
              .str.strip()
              .replace("", np.nan),
        errors="coerce"
    ).fillna(0)


# ── Helper: compute rates from aggregated school-level counts ─────────────────
def compute_rates(df_agg, final_col, apro_col, repro_col, desert_col, initial_col):
    """
    Returns df_agg with promotion_rate, repetition_rate, dropout_rate columns.
    Sets all three to NA where internal consistency check fails or Final == 0.
    """
    final   = df_agg[final_col]
    apro    = df_agg[apro_col]
    repro   = df_agg[repro_col]
    desert  = df_agg[desert_col]
    initial = df_agg[initial_col]

    disc_pct = (apro + repro - final).abs() / final.replace(0, np.nan)
    bad = (disc_pct > DISC_THRESHOLD) | (final == 0)

    df_agg["promotion_rate"]  = (apro  / final.replace(0, np.nan)).where(~bad)
    df_agg["repetition_rate"] = (repro / final.replace(0, np.nan)).where(~bad)
    df_agg["dropout_rate"]    = (desert / initial.replace(0, np.nan)).where(~bad)
    df_agg["_bad"] = bad
    return df_agg


# ── 2009 ──────────────────────────────────────────────────────────────────────
print("\nProcessing 2009...")
df09 = pd.read_csv(
    os.path.join(DATA_DIR, "9_MatriculaFinalPorGrados_2009 (1).csv"),
    encoding="latin1",
    low_memory=False,
)
df09 = df09[df09["AdministraciÃ³n"] != "Privada"].copy()
df09["id_norm"] = df09["Codigo"].dropna().astype(int).astype(str)

# Exclude pure pre-basic schools
df09["nivel"] = df09["id_norm"].map(id_to_nivel)
df09 = df09[~df09["nivel"].isin(PURE_PREBAS)].copy()

for c in ["Consolidada T", "Final T", "Desertores T", "Aprobados T", "Reprobados T"]:
    df09[c] = clean_num(df09[c])

agg09 = df09.groupby("id_norm")[
    ["Consolidada T", "Final T", "Desertores T", "Aprobados T", "Reprobados T"]
].sum().reset_index()

agg09 = compute_rates(
    agg09,
    final_col="Final T", apro_col="Aprobados T", repro_col="Reprobados T",
    desert_col="Desertores T", initial_col="Consolidada T",
)
agg09["year"] = 2009
print(f"  Schools: {len(agg09)} | Passing consistency check: {(~agg09['_bad']).sum()}")


# ── 2010 & 2011 ───────────────────────────────────────────────────────────────
df_final = pd.read_csv(
    os.path.join(DATA_DIR, "Estadistica_final_2010_2011.csv"),
    encoding="latin1",
    low_memory=False,
)
year_col = df_final.columns[0]  # BOM-prefixed Año

def process_final_year(df_all, year):
    print(f"\nProcessing {year}...")
    df = df_all[
        (df_all[year_col] == year) &
        (df_all["Tipo Administracion"] == "Publico")
    ].copy()
    df["id_norm"] = df["Codigo Centro"].dropna().astype(int).astype(str)
    df["nivel"]   = df["id_norm"].map(id_to_nivel)
    df = df[~df["nivel"].isin(PURE_PREBAS)].copy()

    for col in ["MATRICULA FINAL femenino", "MATRICULA FINAL masculino",
                "DESERTORES femenino", "DESERTORES masculino",
                "TRASLADOS femenino", "TRASLADOS masculino",
                "APROBADOS femenino", "APROBADOS masculino",
                "REPROBADOS femenino", "REPROBADOS masculino"]:
        df[col] = clean_num(df[col])

    df["final_t"]   = df["MATRICULA FINAL femenino"]  + df["MATRICULA FINAL masculino"]
    df["desert_t"]  = df["DESERTORES femenino"]        + df["DESERTORES masculino"]
    df["trasl_t"]   = df["TRASLADOS femenino"]         + df["TRASLADOS masculino"]
    df["apro_t"]    = df["APROBADOS femenino"]         + df["APROBADOS masculino"]
    df["repro_t"]   = df["REPROBADOS femenino"]        + df["REPROBADOS masculino"]

    agg = df.groupby("id_norm")[
        ["final_t", "desert_t", "trasl_t", "apro_t", "repro_t"]
    ].sum().reset_index()

    # Implied initial = Final + Desertores + Traslados (no Consolidada in this file)
    agg["implied_initial"] = agg["final_t"] + agg["desert_t"] + agg["trasl_t"]

    agg = compute_rates(
        agg,
        final_col="final_t", apro_col="apro_t", repro_col="repro_t",
        desert_col="desert_t", initial_col="implied_initial",
    )
    agg["year"] = year
    print(f"  Schools: {len(agg)} | Passing consistency check: {(~agg['_bad']).sum()}")
    return agg

agg10 = process_final_year(df_final, 2010)
agg11 = process_final_year(df_final, 2011)


# ── Stack all years ───────────────────────────────────────────────────────────
combined = pd.concat(
    [agg09[["id_norm","year","promotion_rate","repetition_rate","dropout_rate"]],
     agg10[["id_norm","year","promotion_rate","repetition_rate","dropout_rate"]],
     agg11[["id_norm","year","promotion_rate","repetition_rate","dropout_rate"]]],
    ignore_index=True,
)


# ── Filter to geo schools ─────────────────────────────────────────────────────
before = len(combined)
combined = combined[combined["id_norm"].isin(id_to_geo)].copy()
print(f"\nAfter geo filter: {len(combined)} rows ({before - len(combined)} dropped)")


# ── Build output ──────────────────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]               = combined["id_norm"].map(id_to_geo)
out["year"]                 = combined["year"].astype(int)
out["outcome_method"]       = "within_year_flow"
out["promotion_rate"]       = combined["promotion_rate"].round(4)
out["repetition_rate"]      = combined["repetition_rate"].round(4)
out["dropout_rate"]         = combined["dropout_rate"].round(4)
out["completion_rate"]      = pd.NA   # Not available
out["gross_intake_ratio"]   = pd.NA   # Not available
out["outcome_reference_grade"] = "all_grades"


# ── Validation ────────────────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].notna().all(),         "ERROR: Null geo_ids"
assert out["year"].notna().all(),           "ERROR: Null years"
assert out["outcome_method"].eq("within_year_flow").all(), "ERROR: outcome_method mismatch"
assert out.duplicated(subset=["geo_id","year"]).sum() == 0, "ERROR: Duplicate geo_id × year"

for col in ["promotion_rate","repetition_rate","dropout_rate"]:
    vals = out[col].dropna()
    assert (vals >= 0).all() and (vals <= 1).all(), f"ERROR: {col} out of [0,1]"

print(f"\n  Total rows          : {len(out)}")
print(f"  Rows per year:\n{out['year'].value_counts().sort_index()}")
for col in ["promotion_rate","repetition_rate","dropout_rate"]:
    n_valid = out[col].notna().sum()
    n_na    = out[col].isna().sum()
    print(f"  {col:20s}: valid={n_valid:6d}  NA={n_na:6d}")


# ── Save ──────────────────────────────────────────────────────────────────────
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")
