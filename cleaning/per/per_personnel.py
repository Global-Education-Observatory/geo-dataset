"""
per_personnel.py
----------------
Builds per_personnel.csv (GEO Dataset canonical schema v1.0) from the Peru
Censo Educativo 2024, Modulo I.

STAGE 1 (this file, done)   enrollment_total / male / female from Matricula_01.dbf
STAGE 2 (this file, done)   teachers_* from Docentes_01.dbf (cuadros C301 to C305)
STAGE 3 (TODO)              classrooms_total, if any source is found

Source:
    Ministerio de Educacion del Peru, Unidad de Estadistica (ESCALE)
    Censo Educativo 2024, Modulo I, Matricula_01.dbf

Which rows are used:
    NROCED in {3AP, 3AS}  (EBR primaria, EBR secundaria)
    CUADRO == C201        (201. Matricula total por grado de estudio, segun turno)

Layout (from the data dictionary, cedulas 3AP and 3AS):
    Dxx are grade x sex counts, odd = hombre, even = mujer
    3AP  D01..D12  grades 1 to 6
    3AS  D01..D10  grades 1 to 5
    TIPDATO is the turno (01 manana, 02 tarde, 03 discontinuo, 04 continuo,
    04 only exists in 3AS). Each turno is a separate row of different
    students, so enrollment is the SUM across turnos (and across BLOQUE if
    that column is present).

Year:
    year = 2024. Peru's school year starts in March, so the beginning-year
    convention gives 2024. The dictionary also has retrospective questions
    about 2023, those are not enrollment. CONFIRM the census reference date.

Join:
    source_id = COD_MOD (7) + ANEXO (1), same as per_geo.py, mapped to geo_id
    through per_geo.csv. Services with no row in the geo table get no
    personnel row (general rule, no null rows).

Teachers (Docentes_01, cedulas 3AP and 3AS):
    C303 genero (TIPDATO 01 hombre, 02 mujer)  -> teachers_male / female / total
    C305 maximo nivel educativo, TIPDATO 02    -> teachers_qualified
         (estudios pedagogicos concluidos con titulo). TIPDATO 01 and 05 are
         SUBTOTALS and are never summed with the detail codes.
    C301, C302, C304 are partitions of the same staff and are used only as a
    consistency check (all should give the same teaching total as C303).
    Which cargo columns count as teaching staff is set in TEACH_COLS below
    (UIS definition, excludes auxiliares and administrators without a class).

OPEN ITEMS
    - Confirm the cargo rule in TEACH_COLS against the Padron TDOCENTE check
    - IMPUTADO exists in this table too but is NOT in the dictionary. Decide
      what it means before using enrollment for analysis, see QA printout.
    - Whether to drop zero-enrollment services (DROP_ZERO_ENROLLMENT).

Author: HB
Date: 2026-10-01
"""

import os

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
MATRICULA_FILE = "../../sources/PER/Matricula_01.dbf"  # TODO confirm
GEO_FILE       = "../../db/geo/per_geo.csv"
DOCENTES_FILE  = "../../sources/PER/Docentes_01.dbf"  # TODO confirm
PADRON_FILE    = "../../sources/PER/Padron.csv"   # optional, for validation
OUTPUT_FILE    = "../../db/personnel/per_personnel.csv"
ISO3 = "PER"
YEAR = 2024

# ── Config ────────────────────────────────────────────────────────────────
DROP_ZERO_ENROLLMENT = False   # services whose total enrollment is 0

# Number of grades in each cedula (D columns are grade x sex pairs)
GRADES = {"3AP": 6, "3AS": 5}
VALID_TURNOS = {"01", "02", "03", "04"}

# ── Teacher cargo rule ────────────────────────────────────────────────────
# Docentes_01 columns are cargos, not people types. Teaching staff = anyone
# with a class load. "con seccion" (3AP) and "con horas" (3AS) mean the person
# has teaching assigned, "sin" means administrative only. Auxiliares excluded.
TEACH_COLS = {
    # 3AP: D01/D03/D05/D07 director, subdirector, coordinador "con seccion";
    #      D09 docente de aula; D10-D13 docentes especiales; D14 docente de aula
    #      con cargo directivo; D15 otro docente. D16 auxiliar excluded.
    "3AP": ["D01", "D03", "D05", "D07", "D09", "D10", "D11", "D12", "D13", "D14", "D15"],
    # 3AS: D01/D03/D05/D07 director general, director, subdirector, coordinador
    #      "con horas"; D09-D13 docentes; D14 director academico con horas;
    #      D16 director de bienestar con horas; D22-D26 COAR, tutor,
    #      acompanante, coordinador de monografia, monitor.
    #      D18 (coord. psicopedagogico con horas) and D20 (asistente de direccion
    #      con horas) are AMBIGUOUS and excluded, add them here if you decide
    #      they count. D27 auxiliar excluded.
    "3AS": ["D01", "D03", "D05", "D07", "D09", "D10", "D11", "D12", "D13",
            "D14", "D16", "D22", "D23", "D24", "D25", "D26"],
}
N_CARGOS = {"3AP": 16, "3AS": 27}
AUX_COLS = {"3AP": ["D16"], "3AS": ["D27"]}

CUADRO_TIPDATO = {
    "C301": {"01", "02", "03", "04", "05", "06"},   # fuente de financiamiento
    "C302": {"01", "02", "03", "04", "05", "06"},   # jornada laboral
    "C303": {"01", "02"},                            # genero
    "C304": {"01", "02"},                            # condicion laboral
    "C305": {f"{i:02d}" for i in range(1, 11)},      # maximo nivel educativo
}
C305_PARTITION = ["02", "03", "04", "06", "07", "08", "09", "10"]  # 01 and 05 are subtotals

PERSONNEL_COLS = [
    "geo_id", "year",
    "enrollment_total", "enrollment_male", "enrollment_female",
    "teachers_total", "teachers_male", "teachers_female", "teachers_qualified",
    "pupil_teacher_ratio", "classrooms_total",
]


def load_dbf(path):
    from dbfread import DBF
    return pd.DataFrame(iter(DBF(path, encoding="latin-1", ignore_missing_memofile=True)))


def d_cols(df):
    return sorted(c for c in df.columns if len(c) == 3 and c[0] == "D" and c[1:].isdigit())


def enrollment_by_service(mat):
    """
    Returns one row per (COD_MOD, ANEXO) with enrollment_total / male / female
    summed over turnos (and bloques).
    """
    mat = mat.copy()
    for c in ["COD_MOD", "ANEXO", "NROCED", "CUADRO", "TIPDATO"]:
        mat[c] = mat[c].astype(str).str.strip()
    print(f"Matricula_01 rows: {len(mat)}")
    print("NROCED x CUADRO in the full file:")
    print(mat.groupby(["NROCED", "CUADRO"]).size())

    mat = mat[(mat["CUADRO"] == "C201") & (mat["NROCED"].isin(GRADES))].copy()
    print(f"\nRows after NROCED in {list(GRADES)} and CUADRO == C201: {len(mat)}")

    # TIPDATO must be a turno code. A stray total row would double count.
    bad = set(mat["TIPDATO"].unique()) - VALID_TURNOS
    if bad:
        raise ValueError(f"Unexpected TIPDATO values {bad}, review before summing")
    print("TIPDATO (turno) counts:")
    print(mat.groupby(["NROCED", "TIPDATO"]).size())

    # Exact duplicate keys would double count
    key = ["COD_MOD", "ANEXO", "NROCED", "TIPDATO"] + (["BLOQUE"] if "BLOQUE" in mat.columns else [])
    dups = mat.duplicated(key, keep=False).sum()
    if dups:
        raise ValueError(f"{dups} rows share {key}, summing would double count")

    # One cedula per service
    n_ced = mat.groupby(["COD_MOD", "ANEXO"])["NROCED"].nunique()
    if (n_ced > 1).any():
        raise ValueError(f"{(n_ced > 1).sum()} services appear under both 3AP and 3AS")

    dcols = d_cols(mat)
    for c in dcols:
        mat[c] = pd.to_numeric(mat[c], errors="coerce")

    parts = []
    for ced, n_grades in GRADES.items():
        sub = mat[mat["NROCED"] == ced].copy()
        male_cols = [f"D{2 * g - 1:02d}" for g in range(1, n_grades + 1)]
        female_cols = [f"D{2 * g:02d}" for g in range(1, n_grades + 1)]
        used = set(male_cols + female_cols)

        # Columns beyond the cedula's layout should be empty, otherwise the
        # layout assumption is wrong
        extra = [c for c in dcols if c not in used]
        extra_sum = sub[extra].fillna(0).abs().sum().sum() if extra else 0
        if extra_sum:
            raise ValueError(f"{ced} has nonzero values outside {sorted(used)}, check layout")

        sub["m"] = sub[male_cols].sum(axis=1, min_count=1)
        sub["f"] = sub[female_cols].sum(axis=1, min_count=1)
        parts.append(sub[["COD_MOD", "ANEXO", "NROCED", "m", "f"]])

    sub = pd.concat(parts, ignore_index=True)
    out = (sub.groupby(["COD_MOD", "ANEXO", "NROCED"], as_index=False)
              .agg(enrollment_male=("m", lambda s: s.sum(min_count=1)),
                   enrollment_female=("f", lambda s: s.sum(min_count=1))))
    # total = male + female, so the subtotals are subsets of the total by construction
    out["enrollment_total"] = out[["enrollment_male", "enrollment_female"]].sum(axis=1, min_count=1)
    out["source_id"] = out["COD_MOD"] + out["ANEXO"]
    print(f"\nServices with enrollment: {len(out)}")

    # IMPUTADO is not in the dictionary, show it so the meaning can be settled
    if "IMPUTADO" in mat.columns:
        print("\nIMPUTADO in the Matricula rows used (undefined in the dictionary):")
        print(mat.groupby(["NROCED", "IMPUTADO"], dropna=False).size())
        flag = (mat.groupby(["COD_MOD", "ANEXO"])["IMPUTADO"]
                   .agg(lambda s: ",".join(sorted(set(s.astype(str))))).rename("IMPUTADO").reset_index())
        flag["source_id"] = flag["COD_MOD"] + flag["ANEXO"]
        out = out.merge(flag[["source_id", "IMPUTADO"]], on="source_id", how="left")
    return out


def teachers_by_service(doc):
    """
    One row per (COD_MOD, ANEXO) with teachers_total / male / female /
    qualified plus diagnostic columns (cand_all, cand_noaux, check flags).
    """
    doc = doc.copy()
    for c in ["COD_MOD", "ANEXO", "NROCED", "CUADRO", "TIPDATO"]:
        doc[c] = doc[c].astype(str).str.strip()
    print(f"\nDocentes_01 rows: {len(doc)}")
    print("NROCED x CUADRO in the file:")
    print(doc.groupby(["NROCED", "CUADRO"]).size())

    doc = doc[doc["NROCED"].isin(TEACH_COLS) & doc["CUADRO"].isin(CUADRO_TIPDATO)].copy()
    print(f"Rows after NROCED in {list(TEACH_COLS)} and CUADRO in C301-C305: {len(doc)}")

    for cuadro, valid in CUADRO_TIPDATO.items():
        bad = set(doc.loc[doc["CUADRO"] == cuadro, "TIPDATO"].unique()) - valid
        if bad:
            raise ValueError(f"{cuadro} has unexpected TIPDATO values {bad}")

    key = ["COD_MOD", "ANEXO", "NROCED", "CUADRO", "TIPDATO"]
    dups = doc.duplicated(key, keep=False).sum()
    if dups:
        raise ValueError(f"{dups} Docentes rows share {key}, summing would double count")

    dcols = d_cols(doc)
    for c in dcols:
        doc[c] = pd.to_numeric(doc[c], errors="coerce")

    parts = []
    for ced in TEACH_COLS:
        sub = doc[doc["NROCED"] == ced].copy()
        cargo = [f"D{i:02d}" for i in range(1, N_CARGOS[ced] + 1)]
        extra = [c for c in dcols if c not in cargo]
        if extra and sub[extra].fillna(0).abs().sum().sum():
            raise ValueError(f"{ced} has nonzero values outside D01-D{N_CARGOS[ced]:02d}, check layout")
        sub["teach"] = sub[TEACH_COLS[ced]].sum(axis=1, min_count=1)
        sub["all_"] = sub[cargo].sum(axis=1, min_count=1)
        sub["noaux"] = sub[[c for c in cargo if c not in AUX_COLS[ced]]].sum(axis=1, min_count=1)
        parts.append(sub[key + ["teach", "all_", "noaux"]])
    long = pd.concat(parts, ignore_index=True)

    k3 = ["COD_MOD", "ANEXO", "NROCED"]

    def tot(cuadro, col="teach", tipdatos=None):
        d = long[long["CUADRO"] == cuadro]
        if tipdatos is not None:
            d = d[d["TIPDATO"].isin(tipdatos)]
        return d.groupby(k3)[col].sum(min_count=1)

    c303 = long[long["CUADRO"] == "C303"]
    male = c303[c303["TIPDATO"] == "01"].groupby(k3)["teach"].sum(min_count=1).rename("teachers_male")
    female = c303[c303["TIPDATO"] == "02"].groupby(k3)["teach"].sum(min_count=1).rename("teachers_female")

    c305 = long[long["CUADRO"] == "C305"]
    p305 = c305.pivot_table(index=k3, columns="TIPDATO", values="teach", aggfunc="sum")
    p305 = p305.reindex(columns=sorted(CUADRO_TIPDATO["C305"]))
    qualified = p305["02"].rename("teachers_qualified")

    out = pd.concat([male, female, qualified], axis=1)
    out["teachers_total"] = out[["teachers_male", "teachers_female"]].sum(axis=1, min_count=1)
    out["t301"] = tot("C301")
    out["t302"] = tot("C302")
    out["t304"] = tot("C304")
    out["t305"] = tot("C305", tipdatos=C305_PARTITION)
    out["cand_all"] = tot("C303", "all_")
    out["cand_noaux"] = tot("C303", "noaux")
    out = out.reset_index()
    out["source_id"] = out["COD_MOD"] + out["ANEXO"]

    # ── Consistency checks ───────────────────────────────────────────────
    print(f"\nServices with teacher data: {len(out)}")
    print("Teaching total by other cuadros vs C303 (exact agreement share):")
    for c in ["t301", "t302", "t304", "t305"]:
        both = out[c].notna() & out["teachers_total"].notna()
        print(f"  {c}: {(out.loc[both, c] == out.loc[both, 'teachers_total']).mean():.3f} (n={both.sum()})")

    for sub_code, parts_ in [("01", ["02", "03", "04"]), ("05", ["06", "07", "08"])]:
        has = p305[sub_code].notna()
        ok = (p305.loc[has, sub_code] == p305.loc[has, parts_].sum(axis=1)).mean() if has.any() else float("nan")
        print(f"C305 subtotal {sub_code} == {'+'.join(parts_)}: {ok:.3f} (n={has.sum()})")

    bad_q = (out["teachers_qualified"] > out["teachers_total"]).sum()
    if bad_q:
        print(f"  WARNING: {bad_q} services have teachers_qualified > teachers_total, "
              "teachers_qualified set to NA for those")
        out.loc[out["teachers_qualified"] > out["teachers_total"], "teachers_qualified"] = np.nan

    print("\nIMPUTADO in Docentes_01 rows used (if present):")
    if "IMPUTADO" in doc.columns:
        print(doc.groupby(["NROCED", "IMPUTADO"], dropna=False).size())
    return out


def validate_teachers_against_padron(tch, padron_path):
    """Compare candidate teacher totals with the Padron's TDOCENTE."""
    if not os.path.exists(padron_path):
        print(f"\n(Padron not found at {padron_path}, skipping teacher cross-check)")
        return
    p = pd.read_csv(padron_path, dtype=str)
    p["source_id"] = p["COD_MOD"].str.strip() + p["ANEXO"].str.strip()
    p["TDOCENTE"] = pd.to_numeric(p["TDOCENTE"], errors="coerce")
    m = tch.merge(p[["source_id", "TDOCENTE"]], on="source_id", how="inner")
    print(f"\n=== Teacher cross-check vs Padron TDOCENTE (n={len(m)}) ===")
    for label, col in [("proposed cargo rule", "teachers_total"),
                       ("all cargos incl. auxiliar", "cand_all"),
                       ("all cargos excl. auxiliar", "cand_noaux")]:
        d = m[col] - m["TDOCENTE"]
        print(f"{label:28s} exact match {(d == 0).mean():.3f}, "
              f"median abs diff {d.abs().median():.1f}, mean diff {d.mean():+.2f}")


def validate_against_padron(enr, padron_path):
    """Compare derived totals with the Padron's TALUMNO / TALUM_HOM / TALUM_MUJ."""
    if not os.path.exists(padron_path):
        print(f"\n(Padron not found at {padron_path}, skipping cross-check)")
        return
    p = pd.read_csv(padron_path, dtype=str)
    p["source_id"] = p["COD_MOD"].str.strip() + p["ANEXO"].str.strip()
    for c in ["TALUMNO", "TALUM_HOM", "TALUM_MUJ"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    m = enr.merge(p[["source_id", "TALUMNO", "TALUM_HOM", "TALUM_MUJ"]], on="source_id", how="inner")
    print(f"\n=== Cross-check vs Padron totals (n={len(m)}) ===")
    for mine, theirs in [("enrollment_total", "TALUMNO"),
                         ("enrollment_male", "TALUM_HOM"),
                         ("enrollment_female", "TALUM_MUJ")]:
        d = (m[mine] - m[theirs])
        print(f"{mine} vs {theirs}: exact match {(d == 0).mean():.3f}, "
              f"median abs diff {d.abs().median():.1f}, max abs diff {d.abs().max():.0f}")


def main():
    mat = load_dbf(MATRICULA_FILE)
    enr = enrollment_by_service(mat)
    validate_against_padron(enr, PADRON_FILE)

    doc = load_dbf(DOCENTES_FILE)
    tch = teachers_by_service(doc)
    validate_teachers_against_padron(tch, PADRON_FILE)

    # Outer join so a school with only one source still gets a row,
    # the missing columns stay NA. Schools with neither get no row.
    tcols = ["source_id", "teachers_total", "teachers_male", "teachers_female", "teachers_qualified"]
    both_sources = enr.merge(tch[tcols], on="source_id", how="outer")
    enr = both_sources

    # ── Join to geo ──────────────────────────────────────────────────────
    geo = pd.read_csv(GEO_FILE, dtype=str, usecols=["geo_id", "source_id"])
    n_geo = len(geo)
    merged = enr.merge(geo, on="source_id", how="inner")
    print(f"\nServices with enrollment or teacher data: {len(enr)}")
    print(f"Matched to geo table: {len(merged)} of {n_geo} geo schools "
          f"({len(merged) / n_geo:.1%} of geo has enrollment)")
    print(f"Services with no geo row (not public, level out of scope, or dropped): "
          f"{len(enr) - len(merged)}")
    if merged["geo_id"].duplicated().any():
        print(f"  WARNING: {merged['geo_id'].duplicated().sum()} duplicate geo_ids after join "
              "(duplicate source_id in geo table)")

    zero = (merged["enrollment_total"] == 0).sum()
    print(f"Services with zero total enrollment: {zero}")
    if DROP_ZERO_ENROLLMENT:
        merged = merged[merged["enrollment_total"] != 0].copy()

    p = merged.copy()
    p["year"] = YEAR

    # ── STAGE 3 TODO ─────────────────────────────────────────────────────
    p["classrooms_total"] = pd.NA

    # Computed, NA if either input is NA
    p["pupil_teacher_ratio"] = pd.to_numeric(p["enrollment_total"], errors="coerce") / \
        pd.to_numeric(p["teachers_total"], errors="coerce").replace(0, np.nan)

    for c in ["enrollment_total", "enrollment_male", "enrollment_female",
              "teachers_total", "teachers_male", "teachers_female", "teachers_qualified"]:
        p[c] = p[c].astype("Int64")

    out = p[PERSONNEL_COLS].sort_values("geo_id").reset_index(drop=True)

    print("\n=== PER_personnel QA ===")
    print(f"Rows: {len(out)}  year: {out['year'].unique().tolist()}")
    print(out[["enrollment_total", "enrollment_male", "enrollment_female",
               "teachers_total", "teachers_male", "teachers_female",
               "teachers_qualified", "pupil_teacher_ratio"]].describe())
    print(f"services with enrollment but no teachers: {(out['enrollment_total'].notna() & out['teachers_total'].isna()).sum()}")
    print(f"services with teachers but no enrollment: {(out['teachers_total'].notna() & out['enrollment_total'].isna()).sum()}")
    print(f"geo_id nulls: {out['geo_id'].isna().sum()}  "
          f"enrollment_total nulls: {out['enrollment_total'].isna().sum()}")

    if len(out) == 0:
        raise RuntimeError("Zero rows, not writing output")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()