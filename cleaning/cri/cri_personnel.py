"""
cri_personnel.py
----------------
Builds cri_personnel.csv from MEP matricula inicial enrollment files (2014-2025).
Conforms to GEO Dataset canonical schema v1.0.

Sources:
    2014-2022 (primary, I y II Ciclos):
        matriculainicialescuelasdiurnas-2014-2022-aniocursadosexo.xlsx
        Columns: CURSO LECTIVO, CODIGO, T (total), H (hombres), M (mujeres)
    2014-2022 (secondary, III Ciclo + Educacion Diversificada):
        MATRICULA_INICIAL_COLEGIOS_2014-2022_POR_ANIO_CURSADO_Y_SEXO.xlsx
        Columns: CURSO LECTIVO, CODIGO, TOTAL, HOMBRES, MUJERES
    2023-2025 (primary + secondary, pre-cleaned edited files):
        nominacentroseducativos-2023_edited.xlsx
        NominaCentrosEducativos2024_edited.xlsx
        NominaCentrosEducativos2025_edited.xlsx
        Columns: CODIGO, I Y II CICLOS (primary) / DE 7o A 12o ANO (secondary)
        Note: single enrollment total only -- no sex or grade disaggregation.
    Geo table (for geo_id join and school universe restriction):
        cri_geo.csv

Scope:
    Restricted to schools present in cri_geo.csv (schema rule).
    2014-2022: SECTOR in {1, 3}, RAMA in {11, 21} for colegios
    2023-2025: DEPENDENCIA in {'PUB', 'SUB'}, RAMA-HORARIO daytime only
    One row per school x year. No null rows for missing years.

Year convention:
    Costa Rica academic year = single calendar year (January-December).
    CURSO LECTIVO = calendar year = beginning year. No adjustment needed.

Enrollment columns:
    enrollment_total:  populated for all years (2014-2025)
    enrollment_male:   populated for 2014-2022 only; NA for 2023-2025
    enrollment_female: populated for 2014-2022 only; NA for 2023-2025

Teacher data:
    Not available in any MEP enrollment source file.
    teachers_total, teachers_male, teachers_female, teachers_qualified -> NA
    pupil_teacher_ratio -> NA (computed; NA if either input is NA)
    classrooms_total -> NA (not collected in source)

Author: HB
Date: 2026-05-19
"""

import os
import pandas as pd
import numpy as np

# -- Paths --------------------------------------------------------------------
BASE = "/Users/heatherbaier/Documents/research/geo"

ENROLL_L1   = os.path.join(BASE, "sources/CRI/new/matriculainicialescuelasdiurnas-2014-2022-aniocursadosexo.xlsx")
ENROLL_L2   = os.path.join(BASE, "sources/CRI/new/MATRICULA_INICIAL_COLEGIOS_2014-2022_POR_ANIO_CURSADO_Y_SEXO.xlsx")
NOMINA_2023 = os.path.join(BASE, "sources/CRI/new/nominacentroseducativos-2023_edited.xlsx")
NOMINA_2024 = os.path.join(BASE, "sources/CRI/new/NominaCentrosEducativos2024_edited.xlsx")
NOMINA_2025 = os.path.join(BASE, "sources/CRI/new/NominaCentrosEducativos2025_edited.xlsx")
GEO_FILE    = os.path.join(BASE, "db/geo/cri_geo.csv")
OUTPUT_FILE = os.path.join(BASE, "db/personnel/cri_personnel.csv")

PUBLIC_DEP   = {"PUB", "SUB", "PUBLICA", "SUBVENCIONADA"}
DAYTIME_RAMA = {"ACADEMICA DIURNA", "ACADEMICA DIURNA", "TECNICA DIURNA", "TECNICA DIURNA",
                "11", "21"}

# -- 1. Load geo table --------------------------------------------------------
print("Loading geo table...")
geo = pd.read_csv(GEO_FILE, dtype={"geo_id": str, "source_id": str})
geo["source_id_int"] = pd.to_numeric(geo["source_id"], errors="coerce").astype("Int64")
valid_ids  = set(geo["source_id_int"].dropna())
sid_to_gid = geo.set_index("source_id_int")["geo_id"].to_dict()
print(f"  Schools in geo table: {len(geo)}")

# -- 2. Load 2014-2022 primary enrollment -------------------------------------
print("\nLoading 2014-2022 primary enrollment (escuelas)...")
l1 = pd.read_excel(ENROLL_L1, skiprows=2)
l1 = l1[l1["SECTOR"].isin([1, 3])]
l1 = l1[l1["CODIGO"].notna() & (l1["CODIGO"] != 0)]
l1["CODIGO"] = pd.to_numeric(l1["CODIGO"], errors="coerce").astype("Int64")
l1 = l1[l1["CODIGO"].isin(valid_ids)].copy()
l1 = l1[["CURSO LECTIVO", "CODIGO", "T", "H", "M"]].copy()
l1.columns = ["year", "source_id", "enrollment_total", "enrollment_male", "enrollment_female"]
l1["isced_level"] = "1"
print(f"  Rows: {len(l1)}  |  Schools: {l1['source_id'].nunique()}  |  Years: {sorted(l1['year'].unique())}")

# -- 3. Load 2014-2022 secondary enrollment -----------------------------------
print("\nLoading 2014-2022 secondary enrollment (colegios)...")
l2 = pd.read_excel(ENROLL_L2, skiprows=2)
l2 = l2[l2["SECTOR"].isin([1, 3])]
l2 = l2[l2["RAMA"].isin([11, 21])]
l2 = l2[l2["CODIGO"].notna() & (l2["CODIGO"] != 0)]
l2["CODIGO"] = pd.to_numeric(l2["CODIGO"], errors="coerce").astype("Int64")
l2 = l2[l2["CODIGO"].isin(valid_ids)].copy()
l2 = l2[["CURSO LECTIVO", "CODIGO", "TOTAL", "HOMBRES", "MUJERES"]].copy()
l2.columns = ["year", "source_id", "enrollment_total", "enrollment_male", "enrollment_female"]
l2["isced_level"] = "2|3"
print(f"  Rows: {len(l2)}  |  Schools: {l2['source_id'].nunique()}  |  Years: {sorted(l2['year'].unique())}")

# -- 4. Load 2023-2025 enrollment (total only, no sex disaggregation) ---------
print("\nLoading 2023-2025 enrollment files...")


def _load_nomina_enrollment(path, year):
    """
    Load enrollment totals from one edited nomina file.
    Returns a dataframe with: year, source_id, enrollment_total, isced_level.
    enrollment_male and enrollment_female will be set to NA by the caller.
    """
    frames = []

    # Primary: I y II Ciclos
    df = pd.read_excel(path, sheet_name="I y II Ciclos", header=0)
    df.columns = [str(c).strip().replace("\n", " ") for c in df.columns]
    df["CODIGO"] = pd.to_numeric(df["CODIGO"], errors="coerce")
    df = df[df["CODIGO"].notna() & (df["CODIGO"] != 0)].copy()
    df["CODIGO"] = df["CODIGO"].astype("Int64")
    if "DEPENDENCIA" in df.columns:
        df = df[df["DEPENDENCIA"].str.strip().str.upper().isin(PUBLIC_DEP)].copy()
    df = df[df["CODIGO"].isin(valid_ids)].copy()

    # Enrollment column for primary
    enroll_col = next((c for c in df.columns if "I Y II" in c.upper()), None)
    if enroll_col:
        frames.append(pd.DataFrame({
            "year":             year,
            "source_id":        df["CODIGO"],
            "enrollment_total": pd.to_numeric(df[enroll_col], errors="coerce"),
            "isced_level":      "1",
        }))

    # Secondary: Colegios
    df2 = pd.read_excel(path, sheet_name="Colegios", header=0)
    df2.columns = [str(c).strip().replace("\n", " ") for c in df2.columns]
    df2["CODIGO"] = pd.to_numeric(df2["CODIGO"], errors="coerce")
    df2 = df2[df2["CODIGO"].notna() & (df2["CODIGO"] != 0)].copy()
    df2["CODIGO"] = df2["CODIGO"].astype("Int64")
    if "DEPENDENCIA" in df2.columns:
        df2 = df2[df2["DEPENDENCIA"].str.strip().str.upper().isin(PUBLIC_DEP)].copy()
    # RAMA-HORARIO filter
    rama_col = next((c for c in df2.columns if "RAMA" in c.upper()), None)
    if rama_col:
        rama_vals = df2[rama_col].astype(str).str.strip().str.upper()
        df2 = df2[rama_vals.isin(DAYTIME_RAMA)].copy()
    df2 = df2[df2["CODIGO"].isin(valid_ids)].copy()

    # Enrollment column for secondary
    enroll_col2 = next((c for c in df2.columns if "7" in c and "12" in c), None)
    if enroll_col2:
        frames.append(pd.DataFrame({
            "year":             year,
            "source_id":        df2["CODIGO"],
            "enrollment_total": pd.to_numeric(df2[enroll_col2], errors="coerce"),
            "isced_level":      "2|3",
        }))

    result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return result


nomina_rows = []
for path, year, label in [(NOMINA_2023, 2023, "2023"),
                           (NOMINA_2024, 2024, "2024"),
                           (NOMINA_2025, 2025, "2025")]:
    try:
        frame = _load_nomina_enrollment(path, year)
        nomina_rows.append(frame)
        print(f"  {label}: {len(frame)} school-year rows loaded")
    except Exception as e:
        print(f"  WARNING: could not load {label}: {e}")

# -- 5. Combine all years -----------------------------------------------------
print("\nCombining all years...")
panel_2014_2022 = pd.concat([l1, l2], ignore_index=True)
# enrollment_male/female already present for 2014-2022

if nomina_rows:
    panel_2023_2025 = pd.concat(nomina_rows, ignore_index=True)
    # No sex disaggregation available for 2023-2025
    panel_2023_2025["enrollment_male"]   = pd.NA
    panel_2023_2025["enrollment_female"] = pd.NA
    panel = pd.concat([panel_2014_2022, panel_2023_2025], ignore_index=True)
else:
    panel = panel_2014_2022

# -- 6. Add geo_id ------------------------------------------------------------
panel["geo_id"] = panel["source_id"].map(sid_to_gid)
null_gids = panel["geo_id"].isna().sum()
if null_gids > 0:
    print(f"  WARNING: {null_gids} rows could not be matched to a geo_id -- dropping")
    panel = panel[panel["geo_id"].notna()].copy()

# -- 7. Add teacher and classroom columns (all NA) ----------------------------
panel["teachers_total"]      = pd.NA
panel["teachers_male"]       = pd.NA
panel["teachers_female"]     = pd.NA
panel["teachers_qualified"]  = pd.NA
panel["pupil_teacher_ratio"] = pd.NA  # NA because teachers_total is NA
panel["classrooms_total"]    = pd.NA

# -- 8. Cast types ------------------------------------------------------------
for col in ["year", "enrollment_total", "enrollment_male", "enrollment_female"]:
    panel[col] = pd.to_numeric(panel[col], errors="coerce").astype("Int64")

# -- 9. QA checks -------------------------------------------------------------
print("\n=== CRI_personnel QA ===")
print(f"Total rows: {len(panel)}")
print(f"Unique schools: {panel['geo_id'].nunique()}")
print(f"Years covered: {sorted(panel['year'].dropna().unique())}")
print()

never_null = ["geo_id", "year", "enrollment_total"]
for col in never_null:
    n = panel[col].isna().sum()
    print(f"  {'WARNING' if n > 0 else 'OK'}: {col} -- {n} nulls")

# Sex sum check for 2014-2022 rows only
check = panel[
    panel["enrollment_male"].notna() &
    panel["enrollment_female"].notna() &
    panel["enrollment_total"].notna() &
    (panel["enrollment_total"] > 0)
].copy()
check["sum_sex"] = check["enrollment_male"] + check["enrollment_female"]
check["pct_diff"] = (
    abs(check["sum_sex"] - check["enrollment_total"]) / check["enrollment_total"]
)
discrepancies = check[check["pct_diff"] > 0.01]
print(f"\n  Enrollment sex sum discrepancies (>1%): {len(discrepancies)}")
if len(discrepancies) > 0:
    print(discrepancies[["geo_id", "year", "enrollment_total",
                           "enrollment_male", "enrollment_female"]].head(10).to_string())

print()
print("Rows per year:")
print(panel.groupby("year")["geo_id"].count().to_string())
print()
print("Sex disaggregation availability by year range:")
has_sex = panel[panel["enrollment_male"].notna()]["year"]
print(f"  Years with sex data:    {sorted(has_sex.unique())}")
no_sex = panel[panel["enrollment_male"].isna()]["year"]
print(f"  Years without sex data: {sorted(no_sex.unique())}")

# -- 10. Assemble output in schema column order -------------------------------
PERSONNEL_COLS = [
    "geo_id",
    "year",
    "enrollment_total",
    "enrollment_male",
    "enrollment_female",
    "teachers_total",
    "teachers_male",
    "teachers_female",
    "teachers_qualified",
    "pupil_teacher_ratio",
    "classrooms_total",
]
out = panel[PERSONNEL_COLS].copy()

# -- 11. Save -----------------------------------------------------------------
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved to {OUTPUT_FILE}")
print(f"  Rows: {len(out)}  |  Columns: {len(out.columns)}")
