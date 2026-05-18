"""
col_personnel.py
----------------
Builds col_personnel.csv from the MEN SIMAT full enrollment extract.
Conforms to GEO Dataset canonical schema v1.0 — personnel table.

Enrollment scope (documented in harmonisation note):
  - ISCED 1–3 only (Primero–Once); ISCED 0 excluded for cross-country consistency
  - OFICIAL sector only
  - Jornadas excluded: Fin de Semana, Nocturna (adult education delivery slots)
  - Grades excluded: all Ciclo Adultos, PFC programs, Aceleración, Normal superior,
    INTR-Semestre, Prejardín, Jardín, Transición (ISCED 0)

Teachers, classrooms: not available in this source — NA for all rows.
PTR: NA because teachers_total is NA.

Author: HB
"""

import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────
GEO_FILE  = "/Users/heatherbaier/Documents/research/geo/db/geo/col_geo.csv"
ENROLL_FILE = "/Users/heatherbaier/Documents/research/geo/sources/COL/new/MEN_MATRICULA_EN_EDUCACION_EN_PREESCOLAR,_BÁSICA_Y_MEDIA_20260518_full.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/personnel/col_personnel.csv"

# ── Grades in scope (ISCED 1–3 only) ──────────────────────────────────────
GRADES_IN_SCOPE = {
    'Primero', 'Segundo', 'Tercero', 'Cuarto', 'Quinto',   # ISCED 1
    'Sexto', 'Septimo', 'Octavo', 'Noveno',                 # ISCED 2
    'Decimo', 'Once',                                        # ISCED 3
}

# ── Load geo file — source of truth for which sedes are in scope ───────────
print("Loading geo file...")
ids = pd.read_csv(GEO_FILE, dtype={"source_id": str})
print(f"  {len(ids):,} sedes in col_geo")

# ── Load and filter enrollment ─────────────────────────────────────────────
print("\nLoading enrollment file...")
full = pd.read_csv(ENROLL_FILE, dtype={"CODIGO_DANE_SEDE": str})
print(f"  Loaded {len(full):,} rows")

# Drop adult education jornadas
full = full[~full["TIPO_JORNADA"].isin(["Fin de Semana", "Nocturna"])]
print(f"  After jornada filter: {len(full):,} rows")

# Keep only ISCED 1–3 grades
full = full[full["GRADO"].isin(GRADES_IN_SCOPE)]
print(f"  After grade filter: {len(full):,} rows")

# Public sector only
full = full[full["SECTOR"] == "OFICIAL"]
print(f"  After sector filter: {len(full):,} rows")

full["TOTAL_MATRICULA"] = full["TOTAL_MATRICULA"].astype(int).fillna(0)

# ── Pivot to get enrollment_female / enrollment_male per sede × year ───────
print("\nPivoting enrollment by gender...")
enrollment = (
    full.groupby(["ANNO_INF", "CODIGO_DANE_SEDE", "GENERO"])["TOTAL_MATRICULA"]
    .sum()
    .unstack("GENERO")
    .rename(columns={"Femenino": "enrollment_female", "Masculino": "enrollment_male"})
    .reset_index()
    .rename(columns={"CODIGO_DANE_SEDE": "source_id"})
)
enrollment["enrollment_total"] = enrollment["enrollment_female"].fillna(0) + enrollment["enrollment_male"].fillna(0)
print(f"  {len(enrollment):,} sede × year rows")
print(f"  Years covered: {sorted(enrollment['ANNO_INF'].unique())}")

# ── Merge to geo — inner join keeps only sedes present in col_geo ──────────
# Left join would introduce sedes that were filtered out of geo (no coords,
# outside ADM1 boundary, etc.) — use inner to stay consistent with geo scope.
print("\nMerging to geo...")
merged = pd.merge(
    ids[["geo_id", "source_id"]],
    enrollment,
    how="inner",
    on="source_id",
)
print(f"  {len(merged):,} rows after merge")

# Check for sedes in geo with no enrollment data
no_enroll = ids[~ids["source_id"].isin(enrollment["source_id"])]
if len(no_enroll):
    print(f"  NOTE: {len(no_enroll):,} geo sedes have no enrollment data in source — excluded per schema (no null rows)")

# ── Assemble output in schema column order ─────────────────────────────────
print("\nAssembling output...")
final = pd.DataFrame()
final["geo_id"]             = merged["geo_id"]
final["year"]               = merged["ANNO_INF"].astype(int)
final["enrollment_total"]   = merged["enrollment_total"].astype("Int64")   # Int64 handles NA safely
final["enrollment_male"]    = merged["enrollment_male"].astype("Int64")
final["enrollment_female"]  = merged["enrollment_female"].astype("Int64")
final["teachers_total"]     = pd.NA
final["teachers_male"]      = pd.NA
final["teachers_female"]    = pd.NA
final["teachers_qualified"] = pd.NA
final["pupil_teacher_ratio"]= pd.NA
final["classrooms_total"]   = pd.NA

# ── QA ─────────────────────────────────────────────────────────────────────
print("\nRunning QA checks...")
assert final["geo_id"].notna().all(),           "ERROR: Null geo_ids"
assert final["year"].notna().all(),             "ERROR: Null years"
assert final["enrollment_total"].notna().all(), "ERROR: Null enrollment_total"
assert (final["enrollment_total"] >= 0).all(),  "ERROR: Negative enrollment values"

# Disaggregated counts should sum to total
mismatch = (final["enrollment_male"] + final["enrollment_female"]) != final["enrollment_total"]
if mismatch.any():
    print(f"  WARNING: {mismatch.sum()} rows where male + female != total")

print(f"\n  Total rows:        {len(final):,}")
print(f"  Unique sedes:      {final['geo_id'].nunique():,}")
print(f"  Years:             {sorted(final['year'].unique())}")
print(f"  Enrollment range:  {final['enrollment_total'].min()} – {final['enrollment_total'].max()}")

# ── Save ───────────────────────────────────────────────────────────────────
final.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")