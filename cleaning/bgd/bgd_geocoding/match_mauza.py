from rapidfuzz import process, fuzz
import geopandas as gpd
import pandas as pd


# Load schools
df = pd.read_excel("/Users/heatherbaier/Documents/research/geo/sources/BGD/Institutional Information.xlsx", header=1)#.sample(100)


print(df['MANAGEMENT_TYPE'].value_counts())

# Step 1: management type
df = df[
    (df['MANAGEMENT_TYPE'].isin(['GOVERNMENT', 'GOVERNMENT PRIMARY', 'LOCAL GOVERNMENT'])) |
    (df['MPO_STATUS'] == 'YES')
]

keep_levels = [
    'Junior Secondary',
    'Secondary',
    'Higher Secondary',
    'Dakhil',
    'Alim',
    'TECHNICAL SCHOOL AND COLLEGE',
    'H.S.C (B.M Independent)'
]

df = df[df['EDUCATION_LEVEL'].isin(keep_levels)]

# Load each gB shapefile

mauza = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/mauza.gpkg")

# Extract name lists from each shapefile
mauza_names = mauza["MAUZA_NAME"].dropna().unique().tolist()

def fuzzy_match(value, choices, threshold=67):
    if pd.isna(value) or str(value).strip() == "":
        return None, None
    result = process.extractOne(
        str(value).strip().lower(),
        [c.lower() for c in choices],
        scorer=fuzz.token_sort_ratio
    )
    if result and result[1] >= threshold:
        # Return the ORIGINAL (not lowercased) gB name
        original = choices[[c.lower() for c in choices].index(result[0])]
        return original, result[1]
    return None, result[1] if result else None

# Apply fuzzy match for each adm level
print("Matching ADM1 (Division)...")
df[["mauza_census", "mauza_score"]] = df["MAUZA_NAME"].apply(
    lambda x: pd.Series(fuzzy_match(x, mauza_names))
)

# # Save
df.to_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/schools_mauza.csv", index=False)

# Quick QA
# for level in ["adm1", "adm2", "adm3", "adm4"]:
n_failed = df[f"mauza_census"].isna().sum()
low_conf = (df[f"mauza_score"] < 90).sum()
print(f"{'MAUZA'}: {n_failed} unmatched, {low_conf} below 90 score")