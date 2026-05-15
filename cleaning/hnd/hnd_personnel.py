"""
hnd_personnel.py
----------------
Cleans Honduras EMIS enrollment and teacher data to produce hnd_personnel.csv
conforming to the GEO Dataset canonical schema v1.0.

Sources and year coverage:
    2009: 9_MatriculaFinalPorGrados_2009.xlsx
        Final (end-of-year) enrollment by grade, sex-disaggregated.
        Outcome flow columns also present — used in hnd_outcomes.py.
        No teacher data.
    2010: Estadistica_final_2010_2011.csv (Año == 2010)
        Final enrollment by grade, sex-disaggregated.
    2010: 12_Estadistica_inicial_2010_porNivelSubNivel.csv
        Initial enrollment + teacher counts (male/female) at school level.
        Used for teachers_total/male/female only — enrollment from final
        stats file is preferred.
    2011: Estadistica_final_2010_2011.csv (Año == 2011)
        Final enrollment by grade, sex-disaggregated. No teacher data.
        Note: 30_Estadistica_inicial_2011 has a Docentes column but it is a
        binary 0/1 subnivel-level indicator, not a teacher count. Excluded.
    2013: 90_201311_USINIEH_Matricula_Inicial_2013_SEE_por_Grado.xlsx
        Initial (beginning-of-year) enrollment by grade, sex-disaggregated.
        Inconsistent with 2009–2011 (which use final enrollment). Flagged.
        No teacher data.

Excluded sources:
    79_201308_USINIEH_Matricula_Inicial_2013 — superseded by 90_2013 which
        provides sex disaggregation. 79_2013 is total-only.
    30_Estadistica_inicial_2011 / 49_Estadistica_inicial_2012 — Docentes
        column is a binary 0/1 indicator per subnivel row, not a teacher
        headcount. Every school sums to exactly 1. Unusable.
    43_Matricula_Media_x_Grado — secondary only, uses internal survey ID
        (id_centro) with no crosswalk to EMIS CodigoCentro.
    49_Estadistica_inicial_2012 — only covers pre-basic (subnivel 4) rows.
        No full school enrollment available for 2012.

Year coverage:
    2009, 2010, 2011: final enrollment + 2010 teachers
    2013: initial enrollment only (no teachers)
    2012: no usable data available

Enrollment convention:
    2009–2011 use final (end-of-year) enrollment per UIS convention.
    2013 uses initial (beginning-of-year) enrollment — the only available
    source for that year. Documented in harmonization note.

Null row decision:
    Schools in geo with no enrollment record for a given year are excluded.
    No null rows inserted.

ID normalisation:
    geo source_id has leading zero (e.g. '010100001').
    Enrollment files store the same ID without leading zero ('10100001').
    Normalised by stripping leading zeros before matching.

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
OUTPUT_FILE = os.path.join(BASE_DIR, "db", "personnel", "hnd_personnel.csv")
DATA_DIR = os.path.join(BASE_DIR, "sources", "HND")


# ── Load geo ID lookup ────────────────────────────────────────────────────────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str, "geo_id": str})
geo["id_norm"] = geo["source_id"].str.lstrip("0")
id_to_geo = dict(zip(geo["id_norm"], geo["geo_id"]))
print(f"  Geo schools: {len(geo)}")


# ── Helper: clean numeric to nullable Int64 ───────────────────────────────────
def to_int(series):
    return (
        pd.to_numeric(
            series.astype(str)
                  .str.replace(",", "", regex=False)
                  .str.replace("-", "0", regex=False)
                  .str.strip()
                  .replace("", np.nan),
            errors="coerce"
        ).astype("Int64")
    )


# ── 2009: final enrollment ────────────────────────────────────────────────────
print("\nLoading 2009...")
df09 = pd.read_csv(
    os.path.join(DATA_DIR, "9_MatriculaFinalPorGrados_2009 (1).csv"),
    dtype={"Codigo": str},
)
df09 = df09[df09["Administración"] != "Privada"].copy()
df09["id_norm"] = df09["Codigo"].dropna().str.strip().str.lstrip("0")
df09["enr_f"] = to_int(df09["Final F"])
df09["enr_m"] = to_int(df09["Final M"])
agg09 = df09.groupby("id_norm")[["enr_f", "enr_m"]].sum().reset_index()
agg09["enrollment_female"] = agg09["enr_f"].astype("Int64")
agg09["enrollment_male"]   = agg09["enr_m"].astype("Int64")
agg09["enrollment_total"]  = (agg09["enr_f"] + agg09["enr_m"]).astype("Int64")
agg09["year"] = 2009
agg09 = agg09[agg09["id_norm"].isin(id_to_geo)]
print(f"  Schools: {len(agg09)}")


# ── 2010: final enrollment ────────────────────────────────────────────────────
print("\nLoading 2010 enrollment...")
df_final = pd.read_csv(
    os.path.join(DATA_DIR, "Estadistica_final_2010_2011.csv"),
    encoding="latin1",
    low_memory=False,
)
year_col = df_final.columns[0]  # BOM-prefixed Año

df10 = df_final[
    (df_final[year_col] == 2010) & (df_final["Tipo Administracion"] == "Publico")
].copy()
df10["id_norm"] = df10["Codigo Centro"].dropna().astype(int).astype(str)
df10["enr_f"] = to_int(df10["MATRICULA FINAL femenino"])
df10["enr_m"] = to_int(df10["MATRICULA FINAL masculino"])
agg10 = df10.groupby("id_norm")[["enr_f", "enr_m"]].sum().reset_index()
agg10["enrollment_female"] = agg10["enr_f"].astype("Int64")
agg10["enrollment_male"]   = agg10["enr_m"].astype("Int64")
agg10["enrollment_total"]  = (agg10["enr_f"] + agg10["enr_m"]).astype("Int64")
agg10["year"] = 2010
agg10 = agg10[agg10["id_norm"].isin(id_to_geo)]
print(f"  Schools: {len(agg10)}")


# ── 2010: teachers from initial stats file ────────────────────────────────────
print("\nLoading 2010 teachers...")
df12 = pd.read_csv(
    os.path.join(DATA_DIR, "12_Estadistica_inicial_2010_porNivelSubNivel.csv"),
    encoding="latin1",
    low_memory=False,
)
df12 = df12[df12["AdministraciÃ³n"].isin(
    ["Oficial", "Comunitaria", "Municipal", "Semioficial"]
)].copy()
df12["id_norm"] = df12["deped_id"].dropna().astype(int).astype(str)
df12["teachers_female"] = to_int(df12["total_teacher_female"])
df12["teachers_male"]   = to_int(df12["total_teacher_male"])
df12["teachers_total"]  = (
    df12["teachers_female"].fillna(0) + df12["teachers_male"].fillna(0)
).astype("Int64")
# Already one row per school — no aggregation needed
df12 = df12[df12["id_norm"].isin(id_to_geo)][
    ["id_norm", "teachers_female", "teachers_male", "teachers_total"]
]
print(f"  Schools with teacher data: {len(df12)}")

# Merge teachers onto 2010 enrollment (left join — keep all enrollment rows)
agg10 = agg10.merge(df12, on="id_norm", how="left")
print(f"  2010 schools with both enrollment and teachers: {agg10['teachers_total'].notna().sum()}")


# ── 2011: final enrollment ────────────────────────────────────────────────────
print("\nLoading 2011...")
df11 = df_final[
    (df_final[year_col] == 2011) & (df_final["Tipo Administracion"] == "Publico")
].copy()
df11["id_norm"] = df11["Codigo Centro"].dropna().astype(int).astype(str)
df11["enr_f"] = to_int(df11["MATRICULA FINAL femenino"])
df11["enr_m"] = to_int(df11["MATRICULA FINAL masculino"])
agg11 = df11.groupby("id_norm")[["enr_f", "enr_m"]].sum().reset_index()
agg11["enrollment_female"] = agg11["enr_f"].astype("Int64")
agg11["enrollment_male"]   = agg11["enr_m"].astype("Int64")
agg11["enrollment_total"]  = (agg11["enr_f"] + agg11["enr_m"]).astype("Int64")
agg11["year"] = 2011
agg11["teachers_female"] = pd.NA
agg11["teachers_male"]   = pd.NA
agg11["teachers_total"]  = pd.NA
agg11 = agg11[agg11["id_norm"].isin(id_to_geo)]
print(f"  Schools: {len(agg11)}")


# ── 2013: initial enrollment (sex-disaggregated) ──────────────────────────────
# Source: 90_201311_USINIEH — wide format with F/M cols per grade.
# Rows 0–1 are merged headers; data starts at row 2.
# School code = col 3, Administración = col 5.
# Female grade cols: indices 15,17,19,...,59 (even from 15 to 60)
# Male grade cols:   indices 16,18,20,...,60 (odd from 16 to 61)
print("\nLoading 2013...")
df90 = pd.read_excel(
    os.path.join(DATA_DIR, "90_201311_USINIEH_Matricula_Inicial_2013_SEE_por_Grado.xlsx"),
    header=None,
    skiprows=2,
)
fem_cols = list(range(15, 61, 2))
mal_cols = list(range(16, 61, 2))

df90["id_norm"] = (
    df90.iloc[:, 3]
    .astype(str).str.strip()
    .str.replace(".0", "", regex=False)
    .str.lstrip("0")
)
df90["administracion"] = df90.iloc[:, 5]
df90 = df90[
    df90["administracion"].isin(["Oficial", "Comunitaria", "Municipal", "Semioficial"])
].copy()

for c in fem_cols + mal_cols:
    df90[c] = pd.to_numeric(df90[c], errors="coerce").fillna(0)

df90["enr_f"] = df90.iloc[:, fem_cols].sum(axis=1)
df90["enr_m"] = df90.iloc[:, mal_cols].sum(axis=1)

agg13 = df90.groupby("id_norm")[["enr_f", "enr_m"]].sum().reset_index()
agg13["enrollment_female"] = agg13["enr_f"].astype("Int64")
agg13["enrollment_male"]   = agg13["enr_m"].astype("Int64")
agg13["enrollment_total"]  = (agg13["enr_f"] + agg13["enr_m"]).astype("Int64")
agg13["year"] = 2013
agg13["teachers_female"] = pd.NA
agg13["teachers_male"]   = pd.NA
agg13["teachers_total"]  = pd.NA
agg13 = agg13[agg13["id_norm"].isin(id_to_geo)]
print(f"  Schools: {len(agg13)}")


# ── Stack all years ───────────────────────────────────────────────────────────
keep_cols = [
    "id_norm", "year",
    "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female",
]

print(agg09.columns)

combined = pd.concat(
    [agg09[keep_cols], agg10[keep_cols], agg11[keep_cols], agg13[keep_cols]],
    ignore_index=True,
)


# ── Build output ──────────────────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]              = combined["id_norm"].map(id_to_geo)
out["year"]                = combined["year"].astype(int)
out["enrollment_total"]    = combined["enrollment_total"]
out["enrollment_male"]     = combined["enrollment_male"]
out["enrollment_female"]   = combined["enrollment_female"]
out["teachers_total"]      = combined["teachers_total"]
out["teachers_male"]       = combined["teachers_male"]
out["teachers_female"]     = combined["teachers_female"]
out["teachers_qualified"]  = pd.NA
out["pupil_teacher_ratio"] = (
    out["enrollment_total"] / out["teachers_total"]
).where(out["teachers_total"].notna() & out["teachers_total"] > 0).round(2)
out["classrooms_total"]    = pd.NA


# ── Validation ────────────────────────────────────────────────────────────────
print("\nRunning validation checks...")
assert out["geo_id"].notna().all(),   "ERROR: Null geo_ids"
assert out["year"].notna().all(),     "ERROR: Null years"
assert out.duplicated(subset=["geo_id", "year"]).sum() == 0, "ERROR: Duplicate geo_id × year"
assert (out["enrollment_total"].dropna() >= 0).all(), "ERROR: Negative enrollment"

# Sex disaggregation check: male + female should equal total (within 1%)
mask = out["enrollment_male"].notna() & out["enrollment_female"].notna()
computed = out.loc[mask, "enrollment_male"] + out.loc[mask, "enrollment_female"]
diff = (computed - out.loc[mask, "enrollment_total"]).abs()
bad = (diff > out.loc[mask, "enrollment_total"] * 0.01).sum()
if bad > 0:
    print(f"  WARNING: {bad} rows where male+female disagrees with total by >1%")

print(f"\n  Total rows: {len(out)}")
print(f"  Rows per year:\n{out['year'].value_counts().sort_index()}")
print(f"  Schools with teacher data (2010 only): {out['teachers_total'].notna().sum()}")
print(f"  Geo schools with no data (any year): {len(geo) - out['geo_id'].nunique()}")


# ── Save ──────────────────────────────────────────────────────────────────────
out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")
