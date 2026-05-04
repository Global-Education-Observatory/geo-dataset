# pipeline/package_country.py
"""
Creates a country zip file ready for uploading to the GitHub v1.0 release.

Usage:
    python pipeline/package_country.py BHR

Output:
    releases/BHR.zip  containing all available dimension CSVs + metadata
"""

import os
import sys
import zipfile

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR    = os.path.join(BASE_DIR, "db")
META_DIR  = os.path.join(BASE_DIR, "metadata")
OUT_DIR   = os.path.join(BASE_DIR, "releases")
DIMS      = ["geo", "personnel", "resources", "outcomes"]

def package_country(iso3):
    iso = iso3.lower()
    os.makedirs(OUT_DIR, exist_ok=True)
    zip_path = os.path.join(OUT_DIR, f"{iso3}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add available dimension CSVs
        for dim in DIMS:
            csv_path = os.path.join(DB_DIR, dim, f"{iso}_{dim}.csv")
            if os.path.exists(csv_path):
                zf.write(csv_path, f"{iso}_{dim}.csv")
                print(f"  ✓ Added {iso}_{dim}.csv")
            else:
                print(f"  — {iso}_{dim}.csv not found, skipping")

        # Add metadata file
        meta_path = os.path.join(META_DIR, f"{iso}_metadata.md")
        if os.path.exists(meta_path):
            zf.write(meta_path, f"{iso}_metadata.md")
            print(f"  ✓ Added {iso}_metadata.md")
        else:
            print(f"  — {iso}_metadata.md not found, skipping")

    print(f"\n✓ Created {zip_path}")
        
    # Upload to GitHub release v1.0
    import subprocess
    print(f"Uploading to GitHub release v1.0...")
    result = subprocess.run(
        [
            "gh", "release", "upload", "v1.0",
            zip_path,
            "--repo", "global-education-observatory/geo-dataset",
            "--clobber"  # overwrite if already exists
        ],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"✓ Uploaded to GitHub release v1.0")
        print(f"  Download URL: https://github.com/global-education-observatory/geo-dataset/releases/download/v1.0/{iso3}.zip")
    else:
        print(f"✗ GitHub upload failed: {result.stderr}")
        print(f"  Upload manually: gh release upload v1.0 {zip_path} --repo global-education-observatory/geo-dataset")


if __name__ == "__main__":
    iso3 = sys.argv[1].upper() if len(sys.argv) > 1 else input("ISO3 code: ").strip().upper()
    package_country(iso3)