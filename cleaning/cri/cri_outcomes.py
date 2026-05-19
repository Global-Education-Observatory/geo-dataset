"""
cri_outcomes.py
---------------
Builds cri_outcomes.csv from Costa Rica MEP source files.
GEO Dataset canonical schema v1.0.

Sources:
    Promotion / repetition / completion:
        rendimientodefinitivoescuelas-2014-2021.xlsx  (primary schools)
        rendimientodefinitivocolegios-2014-2021.xlsx  (secondary schools)

    Dropout (intra-annual exclusion):
        exclusionintraanualescuelasdiurnas-2014-2022.xlsx  (primary schools)
        exclusionintraanualcolegios-2014-2022.xlsx         (secondary schools)

    Enrollment / geo bridge:
        cri_personnel.csv   (enrollment_total, enrollment_male, enrollment_female)
        cri_geo.csv         (geo_id ↔ source_id mapping)

Rate definitions (within-year flow rates):
    promotion_rate        = APROBT / MFT
    promotion_rate_male   = APROBH / MFH
    promotion_rate_female = APROBM / MFM

    repetition_rate        = REPROT / MFT
    repetition_rate_male   = REPROH / MFT   (denominator is MFT, not MFH)
    repetition_rate_female = REPROM / MFT   (denominator is MFT, not MFM)

    completion_rate        = APROBT6 / MF6T  (grade 6 approved / grade 6 matricula final)
    completion_rate_male   = APROBH6 / MF6H
    completion_rate_female = APROBM6 / MF6M

    dropout_rate        = EXC INTRAT / enrollment_total
    dropout_rate_male   = EXC INTRAH / enrollment_total
    dropout_rate_female = EXC INTRAM / enrollment_total
    → rates > 1 or where enrollment_total == 0 are set to NA

Intra-annual exclusion cleaning:
    Grade-level male and female counts are clipped to 0 before grade-level
    totals and yearly totals are recomputed from the clipped values.

Output column order (schema v1.0):
    geo_id, year,
    promotion_rate, promotion_rate_male, promotion_rate_female,
    repetition_rate, repetition_rate_male, repetition_rate_female,
    dropout_rate, dropout_rate_male, dropout_rate_female,
    completion_rate, completion_rate_male, completion_rate_female

Author: HB
"""

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────
BASE = "/Users/heatherbaier/Documents/research/geo"

OUTCOMES_ESCUELAS = f"{BASE}/sources/CRI/outcomes/rendimientodefinitivoescuelas-2014-2021.xlsx"
OUTCOMES_COLEGIOS = f"{BASE}/sources/CRI/outcomes/rendimientodefinitivocolegios-2014-2021.xlsx"
DROPOUT_ESCUELAS  = f"{BASE}/sources/CRI/outcomes/exclusionintraanualescuelasdiurnas-2014-2022.xlsx"
DROPOUT_COLEGIOS  = f"{BASE}/sources/CRI/outcomes/exclusionintraanualcolegios-2014-2022.xlsx"
PERSONNEL_FILE    = f"{BASE}/db/personnel/cri_personnel.csv"
GEO_FILE          = f"{BASE}/db/geo/cri_geo.csv"
OUTPUT_FILE       = f"{BASE}/db/outcomes/cri_outcomes.csv"

# ── Columns to keep from promotion/repetition/completion files ────────────
AP_COLS = [
    "CURSO LECTIVO", "CODIGO",
    "MFT", "MFH", "MFM",
    "APROBT", "APROBH", "APROBM",
    "REPROT", "REPROH", "REPROM",
    "MF6T", "MF6H", "MF6M",
    "APROBT6", "APROBH6", "APROBM6",
]

# ── Schema output columns (in order) ─────────────────────────────────────
OUTPUT_COLS = [
    "geo_id",
    "year",
    "promotion_rate",
    "promotion_rate_male",
    "promotion_rate_female",
    "repetition_rate",
    "repetition_rate_male",
    "repetition_rate_female",
    "dropout_rate",
    "dropout_rate_male",
    "dropout_rate_female",
    "completion_rate",
    "completion_rate_male",
    "completion_rate_female",
]

# ── 1. Promotion, repetition & completion rates ───────────────────────────
print("Loading promotion / repetition / completion data...")

apl1 = pd.read_excel(OUTCOMES_ESCUELAS, skiprows=2)
apl1 = apl1[AP_COLS]

apl2 = pd.read_excel(OUTCOMES_COLEGIOS, skiprows=2)
apl2 = apl2[AP_COLS]

ap = pd.concat([apl1, apl2])
ap = ap[ap["CODIGO"] != 0]

ap["promotion_rate"]        = ap["APROBT"] / ap["MFT"]
ap["promotion_rate_male"]   = ap["APROBH"] / ap["MFH"]
ap["promotion_rate_female"] = ap["APROBM"] / ap["MFM"]

ap["repetition_rate"]        = ap["REPROT"] / ap["MFT"]
ap["repetition_rate_male"]   = ap["REPROH"] / ap["MFT"]
ap["repetition_rate_female"] = ap["REPROM"] / ap["MFT"]

ap["completion_rate"]        = ap["APROBT6"] / ap["MF6T"]
ap["completion_rate_male"]   = ap["APROBH6"] / ap["MF6H"]
ap["completion_rate_female"] = ap["APROBM6"] / ap["MF6M"]

print(f"  Promotion/repetition/completion rows: {len(ap)}")

# ── 2. Dropout (intra-annual exclusion) ───────────────────────────────────
print("Loading dropout / exclusion data...")

def load_dropout(path: str, year_col: str) -> pd.DataFrame:
    """
    Load an intra-annual exclusion file, clip negative grade-level counts,
    recompute grade and yearly totals from clipped values, and return the
    tidy summary columns only.

    Parameters
    ----------
    path     : Path to the Excel file.
    year_col : Raw column name for the academic year (varies between files).
    """
    df = pd.read_excel(path, skiprows=2).rename(
        columns={"CODIGO": "source_id", year_col: "year"}
    )

    # Step 1: clip grade-level male and female counts to 0
    for i in range(1, 7):
        df[f"EXC INTRAH{i}"] = df[f"EXC INTRAH{i}"].clip(lower=0)
        df[f"EXC INTRAM{i}"] = df[f"EXC INTRAM{i}"].clip(lower=0)

    # Step 2: recompute grade-level totals from clipped H + M
    for i in range(1, 7):
        df[f"EXC INTRAT{i}"] = df[f"EXC INTRAH{i}"] + df[f"EXC INTRAM{i}"]

    # Step 3: recompute yearly totals from recalculated grade totals
    df["EXC INTRAT"] = sum(df[f"EXC INTRAT{i}"] for i in range(1, 7))
    df["EXC INTRAH"] = sum(df[f"EXC INTRAH{i}"] for i in range(1, 7))
    df["EXC INTRAM"] = sum(df[f"EXC INTRAM{i}"] for i in range(1, 7))

    return df[["year", "source_id", "EXC INTRAT", "EXC INTRAH", "EXC INTRAM"]]


drl1 = load_dropout(DROPOUT_ESCUELAS, year_col="CURSO LECTIVO ")  # trailing space in escuelas file
drl2 = load_dropout(DROPOUT_COLEGIOS, year_col="CURSO LECTIVO")

dr = pd.concat([drl1, drl2])
dr = dr[~dr["year"].isna()]
dr["year"] = dr["year"].astype(int)

print(f"  Dropout rows: {len(dr)}")
print(f"  Unique source_ids in dropout data: {dr['source_id'].nunique()}")

# ── 3. Load enrollment and geo bridge ─────────────────────────────────────
print("Loading personnel and geo files...")

enr = pd.read_csv(PERSONNEL_FILE)
geo = pd.read_csv(GEO_FILE)

# Build geo_id → source_id map and attach to enrollment
geo_map = dict(zip(geo["geo_id"], geo["source_id"]))
enr["source_id"] = enr["geo_id"].map(geo_map)

# ── 4. Merge promotion/repetition/completion with dropout ─────────────────
print("Merging and computing dropout rates...")

# Rename ap columns for merge
ap = ap.rename(columns={"CURSO LECTIVO": "year", "CODIGO": "source_id"})
ap["year"] = ap["year"].astype(int)

# Merge enrollment → dropout (source_id + year)
outcomes = pd.merge(
    enr[["geo_id", "year", "enrollment_total", "enrollment_male", "enrollment_female", "source_id"]],
    dr,
    on=["year", "source_id"],
)

# Merge in promotion/repetition/completion rates
outcomes = pd.merge(
    outcomes,
    ap[["year", "source_id",
        "promotion_rate", "promotion_rate_male", "promotion_rate_female",
        "repetition_rate", "repetition_rate_male", "repetition_rate_female",
        "completion_rate", "completion_rate_male", "completion_rate_female"]],
    on=["year", "source_id"],
    how="left",
)

# ── 5. Compute dropout rates with NA rules ────────────────────────────────
outcomes["dropout_rate"]        = outcomes["EXC INTRAT"] / outcomes["enrollment_total"]
outcomes["dropout_rate_male"]   = outcomes["EXC INTRAH"] / outcomes["enrollment_total"]
outcomes["dropout_rate_female"] = outcomes["EXC INTRAM"] / outcomes["enrollment_total"]

for col in ["dropout_rate", "dropout_rate_male", "dropout_rate_female"]:
    outcomes[col] = outcomes[col].where(
        (outcomes[col] <= 1) & (outcomes["enrollment_total"] > 0),
        other=pd.NA,
    )

print(f"  Merged outcomes rows: {len(outcomes)}")

# ── 6. QA ─────────────────────────────────────────────────────────────────
print("\n=== CRI outcomes QA ===")
print(f"Total rows: {len(outcomes)}")
print()
for rate_col in ["promotion_rate", "repetition_rate", "dropout_rate", "completion_rate"]:
    print(f"{rate_col}:")
    print(outcomes[rate_col].describe())
    print()
n_cap = (outcomes["dropout_rate"] == 1).sum()
if n_cap > 0:
    print(f"  NOTE: {n_cap} rows with dropout_rate == 1.0 (check source data)")

# ── 7. Assemble output in schema column order and save ────────────────────
outcomes[OUTPUT_COLS].to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved: {OUTPUT_FILE}")



