"""
phl_resources.py
----------------
Builds phl_resources.csv conforming to the GEO Dataset canonical schema v1.0,
resources table.

Source
    DepEd school-level WASH / electricity / internet file, one row per school_id.
    Level-specific columns for elementary (es), junior high (jhs) and senior
    high (shs). Only school year 2023-2024 (year = 2023) at the moment.

How level-specific columns become one school-level binary
    1. Build a 0/1/NA indicator for each level the school offers
       (offers_es / offers_jhs / offers_shs).
    2. Combine across offered levels with an AND. A school gets 1 only if every
       offered level has it, 0 if any offered level lacks it, NA if nothing is 0
       and at least one offered level has no data.
    To treat utilities as campus-wide instead (any level), swap all_levels()
    for any_level() at the bottom of the indicator section.

Blank counts
    In the count sections (handwashing, sanitation) a blank for an offered
    level is read as 0 when the school reported anything else in that section
    for that level. If the whole section is blank for an offered level, the
    indicator is NA.

Indicator definitions
    water_basic              {level}_has_water_supply. Source does not say whether the
                             source is improved or working today, so this is a
                             proxy for JMP basic water.
    water_improved           NA. Source does not distinguish service levels.
    sanitation_basic         at least one functional toilet (male + female + pwd +
                             shared, attached + standalone). Toilet type is not
                             in the source so improved status is not verified.
                             toilet_nonfunc is assumed to be counted separately.
    sanitation_sex_separated at least one functional male AND one functional female
                             toilet.
    handwashing_basic        at least one functional handwashing facility with soap
                             (group + individual).
    electricity              grid OR off-grid.
    internet                 {level}_has_internet.
    internet_type            NA. Source has purpose (instructional/admin), not type.
    computers                ICT equipment file. At least one desktop, laptop, all-in-one,
                             tablet or tablet PC for ACADEMIC use, summed across funding
                             sources. Admin-use devices are ignored. Virtual terminals
                             (thin clients) are not counted. Edit COMPUTER_DEVICES to change.
    library                  NA. Not in any file so far.

Author: HB
"""

import os
import pandas as pd
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────
ISO3 = "PHL"
RESOURCE_FILES = {
    2023: "../../sources/PHL/WASH and Utilities Data in SY 2023-2024/sanitation_utilities_2023-24.csv",   # TODO confirm
}
ICT_FILES = {
    2023: "../../sources/PHL/ICT Data in SY 2023-2024/ict_2023-24.csv",   # TODO confirm
}
GEO_FILE    = "../../db/geo/phl_geo.csv"
OUTPUT_FILE = "../../db/resources/phl_resources.csv"

LEVELS = ["es", "jhs", "shs"]

# Devices that count as a computer for instructional use (column stem after the level)
COMPUTER_DEVICES = ["desktop", "laptop", "all_in_one", "tablet", "tablet_pc"]


# ── Helpers ───────────────────────────────────────────────────────────────
def to_bool(s: pd.Series) -> pd.Series:
    """'True'/'False' strings (any case) to 1.0/0.0, everything else NaN."""
    return s.astype(str).str.strip().str.lower().map({"true": 1.0, "false": 0.0})


def count_block(df: pd.DataFrame, cols: list):
    """Numeric block with blanks read as 0, plus a flag for 'section reported'."""
    block = df[cols].apply(pd.to_numeric, errors="coerce")
    reported = block.notna().any(axis=1)
    return block.fillna(0), reported


def flag(cond: pd.Series, reported: pd.Series) -> pd.Series:
    """0/1 from a condition, NaN where the section was not reported."""
    return cond.astype(float).where(reported)


def all_levels(ind: pd.DataFrame, offered: pd.DataFrame) -> pd.Series:
    """AND across offered levels. 0 if any is 0, 1 if all are 1, else NA."""
    vals      = ind.where(offered)
    any_zero  = (vals == 0).any(axis=1)
    any_na    = (vals.isna() & offered).any(axis=1)
    any_off   = offered.any(axis=1)
    out = pd.Series(np.nan, index=ind.index)
    out[any_off & ~any_zero & ~any_na] = 1.0
    out[any_zero] = 0.0
    return out


def any_level(ind: pd.DataFrame, offered: pd.DataFrame) -> pd.Series:
    """OR across offered levels. Not used by default."""
    vals     = ind.where(offered)
    any_one  = (vals == 1).any(axis=1)
    any_na   = (vals.isna() & offered).any(axis=1)
    any_off  = offered.any(axis=1)
    out = pd.Series(np.nan, index=ind.index)
    out[any_off & ~any_one & ~any_na] = 0.0
    out[any_one] = 1.0
    return out


# ── Indicators for one year's file ────────────────────────────────────────
def build_indicators(d: pd.DataFrame) -> pd.DataFrame:
    offered = pd.DataFrame({L: to_bool(d[f"offers_{L}"]) == 1 for L in LEVELS})

    water, sanb, sansex, hand, elec, inet = ({} for _ in range(6))

    for L in LEVELS:
        # water
        water[L] = to_bool(d[f"{L}_has_water_supply"])

        # electricity
        grid = to_bool(d[f"{L}_has_electricity_grid"])
        off  = to_bool(d[f"{L}_has_electricity_offgrid"])
        any1 = (grid == 1) | (off == 1)
        rep  = grid.notna() | off.notna()
        elec[L] = flag(any1, rep)

        # internet
        inet[L] = to_bool(d[f"{L}_has_internet"])

        # handwashing
        wcols = [c for c in d.columns if c.startswith(f"wash_{L}_")]
        wb, wrep = count_block(d, wcols)
        soap = wb[f"wash_{L}_group_func_with_soap"] + wb[f"wash_{L}_indiv_func_with_soap"]
        hand[L] = flag(soap > 0, wrep)

        # sanitation (attached + standalone)
        scols = [c for c in d.columns
                 if c.startswith(f"san_attached_{L}_") or c.startswith(f"san_standalone_{L}_")]
        sb, srep = count_block(d, scols)
        def tot(kind):
            return sb[f"san_attached_{L}_toilet_{kind}"] + sb[f"san_standalone_{L}_toilet_{kind}"]
        male, female, pwd, shared = tot("male"), tot("female"), tot("pwd"), tot("shared")
        sanb[L]   = flag((male + female + pwd + shared) > 0, srep)
        sansex[L] = flag((male > 0) & (female > 0), srep)

    def combine(ind):
        return all_levels(pd.DataFrame(ind), offered)

    return pd.DataFrame({
        "source_id":                d["school_id"].str.strip(),
        "water_basic":              combine(water),
        "sanitation_basic":         combine(sanb),
        "sanitation_sex_separated": combine(sansex),
        "handwashing_basic":        combine(hand),
        "electricity":              combine(elec),
        "internet":                 combine(inet),
    })


# ── Computers (ICT equipment file) ────────────────────────────────────────
def build_computers(d: pd.DataFrame) -> pd.DataFrame:
    offered = pd.DataFrame({L: to_bool(d[f"offers_{L}"]) == 1 for L in LEVELS})
    comp = {}
    for L in LEVELS:
        cols = [c for c in d.columns
                if any(c.startswith(f"{L}_{dev}_academic_") for dev in COMPUTER_DEVICES)]
        block, rep = count_block(d, cols)
        comp[L] = flag(block.sum(axis=1) > 0, rep)
    return pd.DataFrame({
        "source_id": d["school_id"].str.strip(),
        "computers": all_levels(pd.DataFrame(comp), offered),
    })


# ── Load ──────────────────────────────────────────────────────────────────
geo = pd.read_csv(GEO_FILE, dtype=str, usecols=["geo_id", "source_id"])
print(f"Geo schools: {len(geo)}")

frames = []
for year, path in RESOURCE_FILES.items():
    d = pd.read_csv(path, dtype=str)
    print(f"  year={year}  rows={len(d)}  {os.path.basename(path)}")
    ind = build_indicators(d)
    ind["year"] = year
    frames.append(ind)

res = pd.concat(frames, ignore_index=True)

dupes = res.duplicated(["source_id", "year"]).sum()
if dupes:
    print(f"  WARNING: {dupes} duplicate school_id x year rows. Keeping first.")
    res = res.drop_duplicates(["source_id", "year"], keep="first")

# ── Merge computers ───────────────────────────────────────────────────────
iframes = []
for year, path in ICT_FILES.items():
    d = pd.read_csv(path, dtype=str)
    print(f"  ICT year={year}  rows={len(d)}  {os.path.basename(path)}")
    c = build_computers(d)
    c["year"] = year
    iframes.append(c)

if iframes:
    ict = pd.concat(iframes, ignore_index=True)
    idupes = ict.duplicated(["source_id", "year"]).sum()
    if idupes:
        print(f"  WARNING: {idupes} duplicate ICT rows. Keeping first.")
        ict = ict.drop_duplicates(["source_id", "year"], keep="first")
    res = res.merge(ict, on=["source_id", "year"], how="outer")
else:
    res["computers"] = np.nan

# ── Join to geo_id ────────────────────────────────────────────────────────
n_before = len(res)
res = res.merge(geo, on="source_id", how="inner")
print(f"\nResource rows: {n_before}  matched to geo: {len(res)}  not in geo (dropped): {n_before - len(res)}")

# ── Output in schema order ────────────────────────────────────────────────
out = pd.DataFrame()
out["geo_id"]                   = res["geo_id"]
out["year"]                     = res["year"].astype("Int64")
out["water_basic"]              = res["water_basic"].astype("Int64")
out["water_improved"]           = pd.NA
out["sanitation_basic"]         = res["sanitation_basic"].astype("Int64")
out["sanitation_sex_separated"] = res["sanitation_sex_separated"].astype("Int64")
out["handwashing_basic"]        = res["handwashing_basic"].astype("Int64")
out["electricity"]              = res["electricity"].astype("Int64")
out["internet"]                 = res["internet"].astype("Int64")
out["internet_type"]            = pd.NA
out["computers"]                = res["computers"].astype("Int64")
out["library"]                  = pd.NA

out = out.sort_values(["geo_id", "year"]).reset_index(drop=True)

# ── QA ────────────────────────────────────────────────────────────────────
print("\n=== PHL_resources QA ===")
print(f"Total rows: {len(out)}")
print(f"Duplicate geo_id x year: {out.duplicated(['geo_id', 'year']).sum()}")
for col in ["water_basic", "sanitation_basic", "sanitation_sex_separated",
            "handwashing_basic", "electricity", "internet", "computers"]:
    vc = out[col].value_counts(dropna=False).sort_index()
    print(f"\n{col}")
    print(vc.to_string())

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
out.to_csv(OUTPUT_FILE, index=False)
print(f"\nSaved: {OUTPUT_FILE}")