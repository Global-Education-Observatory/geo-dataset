import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


# Load files
geo = pd.read_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/geocoded_schools_all.csv")
schools_mauza = pd.read_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/schools_mauza.csv")

# Load gB shapefiles for spatial validation of geocoded points
adm1 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM1-all/geoBoundaries-BGD-ADM1.shp")[["shapeName", "geometry"]].rename(columns={"shapeName": "adm1_spatial"})
adm2 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM2-all/geoBoundaries-BGD-ADM2.shp")[["shapeName", "geometry"]].rename(columns={"shapeName": "adm2_spatial"})
adm3 = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/geoBoundaries-BGD-ADM3-all/geoBoundaries-BGD-ADM3.shp")[["shapeName", "geometry"]].rename(columns={"shapeName": "adm3_spatial"})

# Load Mauza shapefile and compute centroids
mauza_shp = gpd.read_file("/Users/heatherbaier/Documents/research/geo/sources/BGD/mauza.gpkg")  # adjust to your mauza shapefile
mauza_shp.head()

# Join mauza centroids onto schools file
mauza_geom = dict(zip(mauza_shp["MAUZA_NAME"], mauza_shp["geometry"]))
schools_mauza["mazua_geom"] = schools_mauza["mauza_census"].map(mauza_geom)
schools_mauza = gpd.GeoDataFrame(schools_mauza, geometry = "mazua_geom")
schools_mauza["centroid"] = schools_mauza["mazua_geom"].centroid
schools_mauza.head()

# Merge geocoded results onto mauza (left join — mauza is the base, geocoded is partial)
# Keep only one geocoded row per EIIN (prefer found_educational, then ambiguous)
match_priority = {"found_educational": 0, "ambiguous_no_edu_type": 1, "not_found": 2, "error": 3}
geo["match_rank"] = geo["match"].map(lambda x: match_priority.get(x, 99))
geo_best = geo.sort_values("match_rank").groupby("EIIN").first().reset_index()
print(geo_best.shape)
geo_best.head()

schools_mauza["EIIN"] = schools_mauza["EIIN"].astype(str)
geo_best["EIIN"] = geo_best["EIIN"].astype(str)

df = schools_mauza.merge(geo_best[["EIIN", "lat", "lon", "match", "adm1", "adm2", "adm3"]], 
                 on="EIIN", how="left")

for_df = df[(df["lat"].notna()) & (df["match"] == "found_educational")]

gdf = gpd.GeoDataFrame(
    for_df.copy(),
    geometry=[Point(lon, lat) for lat, lon in zip(for_df["lat"], for_df["lon"])],
    crs="EPSG:4326"
)

gdf = gpd.sjoin(gdf, adm1, how="left", predicate="within").drop(columns="index_right")
gdf = gpd.sjoin(gdf, adm2, how="left", predicate="within").drop(columns="index_right")
gdf = gpd.sjoin(gdf, adm3, how="left", predicate="within").drop(columns="index_right")

gdf["adm1_ok"] = gdf["adm1"].str.strip().str.lower() == gdf["adm1_spatial"].str.strip().str.lower()
gdf["adm2_ok"] = gdf["adm2"].str.strip().str.lower() == gdf["adm2_spatial"].str.strip().str.lower()
gdf["adm3_ok"] = gdf["adm3"].str.strip().str.lower() == gdf["adm3_spatial"].str.strip().str.lower()
gdf["geocode_valid"] = gdf["adm1_ok"] & gdf["adm2_ok"] & gdf["adm3_ok"]

# Merge validation results back
df = df.merge(
    pd.DataFrame(gdf[["EIIN", "geocode_valid"]]),
    on="EIIN", how="left"
)

# Apply coordinate selection logic
def assign_coords(row):
    if row.get("geocode_valid") == True:
        return pd.Series({
            "final_lat": row["lat"],
            "final_lon": row["lon"],
            "coordinate_source": "address_geocoded",
            "coordinate_precision": "approximate"
        })
    else:
        return pd.Series({
            "final_lat": row["mauza_lat"],
            "final_lon": row["mauza_lon"],
            "coordinate_source": "admin_centroid",
            "coordinate_precision": "approximate"
        })
    
df["mauza_lon"] = df.mazua_geom.centroid.x
df["mauza_lat"] = df.mazua_geom.centroid.y

df[["final_lat", "final_lon", "coordinate_source", "coordinate_precision"]] = df.apply(assign_coords, axis=1)

df.to_csv("/Users/heatherbaier/Documents/research/geo/sources/BGD/geocoding/schools_final_coords.csv", index=False)

# QA summary
n_geocoded = (df["coordinate_source"] == "address_geocoded").sum()
n_centroid = (df["coordinate_source"] == "admin_centroid").sum()
n_none     = df["final_lat"].isna().sum()
print(f"Geocoded (validated):  {n_geocoded} ({n_geocoded/len(df)*100:.1f}%)")
print(f"Mauza centroid:        {n_centroid} ({n_centroid/len(df)*100:.1f}%)")
print(f"No coordinate at all:  {n_none}")