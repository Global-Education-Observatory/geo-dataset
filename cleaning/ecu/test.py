import pandas as pd
import requests
import time

API_KEY = ""
URL = "https://places.googleapis.com/v1/places:searchText"

headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types"
}

# df = pd.read_excel("/Users/heatherbaier/Documents/research/geo/sources/BGD/Institutional Information.xlsx", header=1)#.sample(100)
df = pd.read_csv("/Users/heatherbaier/Documents/research/geo/sources/ECU/registro-administrativo-historico_2009-2024-fin.csv", sep = ";")

# print(df['MANAGEMENT_TYPE'].value_counts())

# # Step 1: management type
# df = df[
#     (df['MANAGEMENT_TYPE'].isin(['GOVERNMENT', 'GOVERNMENT PRIMARY', 'LOCAL GOVERNMENT'])) |
#     (df['MPO_STATUS'] == 'YES')
# ]

# keep_levels = [
#     'Junior Secondary',
#     'Secondary',
#     'Higher Secondary',
#     'Dakhil',
#     'Alim',
#     'TECHNICAL SCHOOL AND COLLEGE',
#     'H.S.C (B.M Independent)'
# ]

# df = df[df['EDUCATION_LEVEL'].isin(keep_levels)]

# print(df.shape)

EDUCATION_TYPES = {
    "school", "secondary_school", "primary_school", "university",
    "educational_institution", "library"
}

results = []
OUTPUT_FILE = "/Users/heatherbaier/Documents/research/geo/sources/ECU/geocoded_schools_samp.csv"

c = 0
for _, row in df[0:10].iterrows():

    query = f"{row['Nombre_Institucion']}, {row['Provincia']}, {row['Canton']}, {row['Parroquia']}, Ecuador"
    body = {"textQuery": query}

    # try:
    response = requests.post(URL, headers=headers, json=body)
    data = response.json()

    if "places" not in data or len(data["places"]) == 0:
        rows_to_write = [{
            "AMIE": row["AMIE"],
            "Nombre_Institucion": row["Nombre_Institucion"],
            "query": query,
            "lat": None, "lon": None,
            "formatted_address": "",
            "place_name": "",
            "adm1": row['Provincia'],
            "adm2": row['Canton'],
            "adm3": row['Parroquia'],
            # "adm4": row['adm4_gb'],
            "types": "",
            "match": "not_found",
            "result_index": None
        }]

    else:
        places = data["places"]
        edu_match = None
        for place in places:
            if set(place.get("types", [])) & EDUCATION_TYPES:
                edu_match = place
                break

        if edu_match:
            rows_to_write = [{
                "AMIE": row["AMIE"],
                "Nombre_Institucion": row["Nombre_Institucion"],
                "query": query,
                "lat": edu_match["location"]["latitude"],
                "lon": edu_match["location"]["longitude"],
                "formatted_address": edu_match.get("formattedAddress", ""),
                "place_name": edu_match["displayName"]["text"],
                "adm1": row['Provincia'],
                "adm2": row['Canton'],
                "adm3": row['Parroquia'],
                "types": ", ".join(edu_match.get("types", [])),
                "match": "found_educational",
                "result_index": places.index(edu_match)
            }]
        else:
            rows_to_write = [{
                "AMIE": row["AMIE"],
                "Nombre_Institucion": row["Nombre_Institucion"],
                "query": query,
                "lat": place["location"]["latitude"],
                "lon": place["location"]["longitude"],
                "formatted_address": place.get("formattedAddress", ""),
                "place_name": place["displayName"]["text"],
                "adm1": row['Provincia'],
                "adm2": row['Canton'],
                "adm3": row['Parroquia'],
                "types": ", ".join(place.get("types", [])),
                "match": "ambiguous_no_edu_type",
                "result_index": i
            } for i, place in enumerate(places)]

    # except Exception as e:
    #     rows_to_write = [{
    #         "AMIE": row["AMIE"],
    #         "Nombre_Institucion": row["Nombre_Institucion"],
    #         "query": query,
    #         "lat": None, "lon": None,
    #         "formatted_address": "",
    #         "place_name": "",
    #         "adm1": row['Provincia'],
    #         "adm2": row['Canton'],
    #         "adm3": row['Parroquia'],
    #         "match": f"error: {e}",
    #         "types": "",
    #         "result_index": None
    #     }]

    # Write rows to CSV iteratively
    pd.DataFrame(rows_to_write).to_csv(
        OUTPUT_FILE,
        mode='a',
        header=c == 0,  # write header only on first iteration
        index=False
    )

    time.sleep(0.05)
    print(c, end="\r")
    c += 1
