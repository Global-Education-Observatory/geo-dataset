"""
bra_resources.py
----------------
Builds BRA_resources.csv from INEP Censo Escolar da Educação Básica
microdata files (2007–2025), conforming to the RESOURCES table
canonical schema v1.0.

Sources:
    INEP Microdados do Censo Escolar da Educação Básica
    Years 2007–2024: single school-level CSV per year
    Year 2025:       Tabela_Escola_2025.csv

Coverage:
    Restricted to schools present in bra_geo.csv.

Variable mappings:

    water_basic
        2013+: IN_AGUA_POTAVEL (provides potable water for human consumption)
        2007–2012: IN_AGUA_FILTRADA (water consumed by students is filtered)
        Note: IN_AGUA_FILTRADA is a slightly narrower concept than JMP 'basic'
        (filtered ≠ potable; source could be unimproved). Used as best available
        proxy for pre-2013 years; document in metadata.

    water_improved
        1 if any of IN_AGUA_REDE_PUBLICA (public network) or
        IN_AGUA_POCO_ARTESIANO (artesian well) = 1.
        Both qualify as improved sources under JMP 2018 definitions.
        IN_AGUA_CACIMBA (cistern/hand-dug well) and IN_AGUA_FONTE_RIO
        (surface water) are unimproved and excluded.

    sanitation_basic
        2013+: IN_BANHEIRO (any bathroom on premises)
        2007–2012: OR of IN_BANHEIRO_DENTRO_PREDIO and IN_BANHEIRO_FORA_PREDIO
        (bathroom inside OR outside building). Mapped to 1 if either = 1.

    sanitation_sex_separated
        Not available in Censo Escolar — NA all years.

    handwashing_basic
        Not available in Censo Escolar — NA all years.

    electricity
        1 if any of IN_ENERGIA_REDE_PUBLICA, IN_ENERGIA_GERADOR_FOSSIL,
        IN_ENERGIA_RENOVAVEL = 1 (any electricity source).
        0 if IN_ENERGIA_INEXISTENTE = 1.
        Note: pre-2013 uses IN_ENERGIA_GERADOR instead of the split
        IN_ENERGIA_GERADOR_FOSSIL / IN_ENERGIA_RENOVAVEL fields.

    internet
        IN_INTERNET (direct binary, all years).

    internet_type
        Not available at school level — NA all years.

    computers
        2013+: 1 if any of IN_DESKTOP_ALUNO, IN_COMP_PORTATIL_ALUNO,
        IN_TABLET_ALUNO = 1; 0 if all = 0.
        2007–2012: derived from QT_COMP_ALUNO (count of student computers);
        1 if QT_COMP_ALUNO > 0, else 0.

    library
        IN_BIBLIOTECA_SALA_LEITURA (all years).
        Note: pre-2009 uses IN_BIBLIO (existence of library) — same concept,
        different field name.

Author: HB
"""

import pandas as pd
import numpy as np
import os

# ── Paths ──────────────────────────────────────────────────────────────────
GEO_FILE    = "/Users/heatherbaier/Documents/research/geo/db/geo/bra_geo.csv"
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/db/resources/bra_resources.csv"

SOURCE_FILES = {
    2024: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2024/dados/microdados_ed_basica_2024.csv",
    2023: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2023/dados/microdados_ed_basica_2023.csv",
    2022: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/Microdados do Censo Escolar da Educa‡Æo B sica 2022/dados/microdados_ed_basica_2022.csv",
    2021: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2021/dados/microdados_ed_basica_2021.csv",
    2020: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2020/dados/microdados_ed_basica_2020.CSV",
    2019: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2019/dados/microdados_ed_basica_2019.csv",
    2018: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2018/dados/microdados_ed_basica_2018.csv",
    2017: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2017/dados/microdados_ed_basica_2017.csv",
    2016: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2016/dados/microdados_ed_basica_2016.csv",
    2015: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2015/dados/microdados_ed_basica_2015.csv",
    2014: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2014/dados/microdados_ed_basica_2014.csv",
    2013: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2013/dados/microdados_ed_basica_2013.csv",
    2012: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2012/dados/microdados_ed_basica_2012.csv",
    2011: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2011/dados/microdados_ed_basica_2011.csv",
    2010: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2010/dados/microdados_ed_basica_2010.csv",
    2009: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2009/dados/microdados_ed_basica_2009.csv",
    2008: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2008/dados/microdados_ed_basica_2008.csv",
    2007: "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_ed_basica_2007/dados/microdados_ed_basica_2007.csv",
}

SOURCE_2025_ESCOLA = "/Users/heatherbaier/Documents/research/geo/sources/BRA/microdados/microdados_censo_escolar_2025/dados/Tabela_Escola_2025.csv"

RESOURCES_COLS = [
    "geo_id",
    "year",
    "water_basic",
    "water_improved",
    "sanitation_basic",
    "sanitation_sex_separated",
    "handwashing_basic",
    "electricity",
    "internet",
    "internet_type",
    "computers",
    "library",
]


# ── Helpers ────────────────────────────────────────────────────────────────

def any_binary(df, cols):
    """
    Return 1 if any available column = 1, 0 if all available = 0, NA if
    none of the columns exist or all present values are NA.
    """
    available = [c for c in cols if c in df.columns]
    if not available:
        return pd.array([pd.NA] * len(df))
    sub = df[available].apply(pd.to_numeric, errors="coerce")
    has_one  = (sub == 1).any(axis=1)
    has_data = sub.notna().any(axis=1)
    result = pd.array([pd.NA] * len(df), dtype="Int64")
    result[has_data & has_one]  = 1
    result[has_data & ~has_one] = 0
    return result


def col_binary(df, col):
    """Return a binary Int64 series from a single column, or NA series if absent."""
    if col not in df.columns:
        return pd.array([pd.NA] * len(df), dtype="Int64")
    s = pd.to_numeric(df[col], errors="coerce")
    result = pd.array([pd.NA] * len(df), dtype="Int64")
    result[s == 1] = 1
    result[s == 0] = 0
    return result


def map_electricity(df):
    """
    Electricity from any source = 1; no electricity = 0.
    Handles pre/post 2013 field name changes.
    """
    source_cols = [c for c in [
        "IN_ENERGIA_REDE_PUBLICA",
        "IN_ENERGIA_GERADOR_FOSSIL",   # 2013+
        "IN_ENERGIA_RENOVAVEL",         # 2013+
        "IN_ENERGIA_GERADOR",           # pre-2013
    ] if c in df.columns]

    no_elec_col = "IN_ENERGIA_INEXISTENTE"

    result = pd.array([pd.NA] * len(df), dtype="Int64")

    if source_cols:
        sub = df[source_cols].apply(pd.to_numeric, errors="coerce")
        has_any = (sub == 1).any(axis=1)
        has_data = sub.notna().any(axis=1)
        result[has_data & has_any]  = 1
        result[has_data & ~has_any] = 0

    # Override: explicitly no electricity
    if no_elec_col in df.columns:
        no_elec = pd.to_numeric(df[no_elec_col], errors="coerce") == 1
        result[no_elec] = 0

    return result


def map_computers(df, year):
    """
    2013+: any of IN_DESKTOP_ALUNO, IN_COMP_PORTATIL_ALUNO, IN_TABLET_ALUNO = 1
    2007–2012: QT_COMP_ALUNO > 0
    """
    if year >= 2013:
        return any_binary(df, ["IN_DESKTOP_ALUNO", "IN_COMP_PORTATIL_ALUNO", "IN_TABLET_ALUNO"])
    else:
        if "QT_COMP_ALUNO" not in df.columns:
            return pd.array([pd.NA] * len(df), dtype="Int64")
        qty = pd.to_numeric(df["QT_COMP_ALUNO"], errors="coerce")
        result = pd.array([pd.NA] * len(df), dtype="Int64")
        result[qty > 0]  = 1
        result[qty == 0] = 0
        return result


def map_water_basic(df, year):
    """
    2013+: IN_AGUA_POTAVEL
    2007–2012: IN_AGUA_FILTRADA (proxy; noted in metadata)
    """
    col = "IN_AGUA_POTAVEL" if year >= 2013 else "IN_AGUA_FILTRADA"
    return col_binary(df, col)


def map_sanitation(df, year):
    """
    2013+: IN_BANHEIRO
    2007–2012: OR of IN_BANHEIRO_DENTRO_PREDIO, IN_BANHEIRO_FORA_PREDIO
    """
    if year >= 2013:
        return col_binary(df, "IN_BANHEIRO")
    else:
        return any_binary(df, ["IN_BANHEIRO_DENTRO_PREDIO", "IN_BANHEIRO_FORA_PREDIO"])


def map_library(df):
    """
    IN_BIBLIOTECA_SALA_LEITURA (2009+); IN_BIBLIO fallback for 2007–2008.
    """
    if "IN_BIBLIOTECA_SALA_LEITURA" in df.columns:
        return col_binary(df, "IN_BIBLIOTECA_SALA_LEITURA")
    return col_binary(df, "IN_BIBLIO")


# ── Core processing function ───────────────────────────────────────────────

def process_resources(df, year, id_map, geo_ids):
    """Apply all resource mappings to a loaded DataFrame."""

    df["CO_ENTIDADE"] = df["CO_ENTIDADE"].astype(str).str.strip()
    df = df[df["CO_ENTIDADE"].isin(geo_ids)].copy()
    df["geo_id"] = df["CO_ENTIDADE"].map(id_map)

    out = pd.DataFrame()
    out["geo_id"]                  = df["geo_id"].values
    out["year"]                    = year
    out["water_basic"]             = map_water_basic(df, year)
    out["water_improved"]          = any_binary(df, ["IN_AGUA_REDE_PUBLICA", "IN_AGUA_POCO_ARTESIANO"])
    out["sanitation_basic"]        = map_sanitation(df, year)
    out["sanitation_sex_separated"] = pd.NA
    out["handwashing_basic"]       = pd.NA
    out["electricity"]             = map_electricity(df)
    out["internet"]                = col_binary(df, "IN_INTERNET")
    out["internet_type"]           = pd.NA
    out["computers"]               = map_computers(df, year)
    out["library"]                 = map_library(df)

    return out[RESOURCES_COLS].copy()


# ── Load geo ───────────────────────────────────────────────────────────────
print("Loading geo file...")
geo = pd.read_csv(GEO_FILE, dtype={"source_id": str})
id_map   = dict(zip(geo["source_id"], geo["geo_id"]))
geo_ids  = set(geo["source_id"])
print(f"  {len(geo)} schools in geo")

# ── Process 2007–2024 ──────────────────────────────────────────────────────
print("\nProcessing 2007–2024...")
processed = []

for year in sorted(SOURCE_FILES.keys()):
    print(f"  {year}: loading...", end=" ")
    df = pd.read_csv(
        SOURCE_FILES[year],
        encoding="latin-1",
        sep=";",
        dtype={"CO_ENTIDADE": str},
        low_memory=False,
    )
    out = process_resources(df, year, id_map, geo_ids)
    print(f"{len(out)} schools → electricity NA: {out['electricity'].isna().sum()}, internet NA: {out['internet'].isna().sum()}")
    processed.append(out)

# ── Process 2025 ───────────────────────────────────────────────────────────
print("\nProcessing 2025...")
df_2025 = pd.read_csv(
    SOURCE_2025_ESCOLA,
    encoding="latin-1",
    sep=";",
    dtype={"CO_ENTIDADE": str},
    low_memory=False,
)
out_2025 = process_resources(df_2025, 2025, id_map, geo_ids)
print(f"  {len(out_2025)} schools → electricity NA: {out_2025['electricity'].isna().sum()}, internet NA: {out_2025['internet'].isna().sum()}")
processed.append(out_2025)

# ── Concatenate ────────────────────────────────────────────────────────────
print("\nConcatenating...")
resources = pd.concat(processed, ignore_index=True)

# ── QA ─────────────────────────────────────────────────────────────────────
print("\n=== BRA_resources QA ===")
print(f"Total rows:     {len(resources)}")
print(f"Unique geo_ids: {resources['geo_id'].nunique()}")
print(f"Years covered:  {sorted(resources['year'].unique())}")
print()

never_null = ["geo_id", "year"]
for col in never_null:
    n = resources[col].isna().sum()
    print(f"  {'OK' if n == 0 else f'WARNING: {n} nulls'}: {col}")

print()
print("Binary value distributions (sample year 2024):")
y2024 = resources[resources["year"] == 2024]
for col in ["water_basic", "water_improved", "sanitation_basic",
            "electricity", "internet", "computers", "library"]:
    vc = y2024[col].value_counts(dropna=False).to_dict()
    print(f"  {col}: {vc}")

print()
dupes = resources.duplicated(subset=["geo_id", "year"]).sum()
print(f"Duplicate geo_id × year rows: {dupes}")

# ── Save ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
resources.to_csv(OUTPUT_FILE, index=False)
print(f"\n✓ Saved to {OUTPUT_FILE}")