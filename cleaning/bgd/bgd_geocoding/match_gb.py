import pandas as pd
from rapidfuzz import process, fuzz

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
import geopandas as gpd
adm1 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM1-all/geoBoundaries-BGD-ADM1.shp")  # adjust filenames to yours
adm2 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM2-all/geoBoundaries-BGD-ADM2.shp")
adm3 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM3-all/geoBoundaries-BGD-ADM3.shp")
adm4 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM4-all/geoBoundaries-BGD-ADM4.shp")

# Extract name lists from each shapefile
adm1_names = adm1["shapeName"].dropna().unique().tolist()
print(adm1_names)
print(df["DIVISION"].unique())
adm2_names = adm2["shapeName"].dropna().unique().tolist()
adm3_names = adm3["shapeName"].dropna().unique().tolist()
adm4_names = adm4["shapeName"].dropna().unique().tolist()

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
df[["adm1_gb", "adm1_score"]] = df["DIVISION"].apply(
    lambda x: pd.Series(fuzzy_match(x, adm1_names))
)

print("Matching ADM2 (District)...")
df[["adm2_gb", "adm2_score"]] = df["DISTRICT"].apply(
    lambda x: pd.Series(fuzzy_match(x, adm2_names))
)

print("Matching ADM3 (Thana)...")
df[["adm3_gb", "adm3_score"]] = df["THANA"].apply(
    lambda x: pd.Series(fuzzy_match(x, adm3_names))
)

print("Matching ADM4 (Union)...")
df[["adm4_gb", "adm4_score"]] = df["UNION_NAME"].apply(
    lambda x: pd.Series(fuzzy_match(x, adm4_names))
)

# Save
df.to_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/schools_with_gb_names.csv", index=False)

# Quick QA
for level in ["adm1", "adm2", "adm3", "adm4"]:
    n_failed = df[f"{level}_gb"].isna().sum()
    low_conf = (df[f"{level}_score"] < 90).sum()
    print(f"{level}: {n_failed} unmatched, {low_conf} below 90 score")