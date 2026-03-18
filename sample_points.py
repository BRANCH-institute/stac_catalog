import geopandas as gpd
import rasterio
import pystac
import numpy as np
from shapely.geometry import Point

CATALOG_URL = "https://storage.googleapis.com/johan_public/test_stac/stac/catalog.json"

# --- Test points (lon, lat) ---
test_points = gpd.GeoDataFrame(
    {"id": ["point_A", "point_B", "point_C"]},
    geometry=[Point(8.5, 47.3), Point(2.3, 48.8), Point(-3.7, 40.4)],
    crs="EPSG:4326"
)

coords = list(zip(test_points.geometry.x, test_points.geometry.y))

# --- Load STAC catalog ---
catalog = pystac.Catalog.from_file(CATALOG_URL)

# --- Sample each layer ---
for collection in catalog.get_children():
    for item in collection.get_items():
        href = item.assets["data"].href
        print(f"Sampling {item.id}...")
        with rasterio.open(href) as src:
            values = [val[0] for val in src.sample(coords)]
        test_points[item.id] = values

# create geopandas GeoDataFrame with sampled values
gdf = gpd.GeoDataFrame(test_points, geometry="geometry", crs="EPSG:4326")
# write to parquet file
gdf.to_file("sampled_points.gpkg", driver="GPKG")
print("\nSaved to sampled_points.gpkg")
print("\nNext steps:")
print("  - Inspect results: open sampled_points.gpkg in QGIS or load with geopandas")
print("  - Add more layers: edit layers.yaml, run build_stac.py, re-run this script")

