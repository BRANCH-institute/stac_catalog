import pystac
import rasterio
from datetime import datetime
from shapely.geometry import box, mapping

BUCKET = "https://storage.googleapis.com/johan_public/test_stac"

# --- Catalog ---
catalog = pystac.Catalog(
    id="my-raster-stack",
    title="Global Environmental Layers",
    description="Global environmental raster data products"
)

# --- Collection definitions ---
# Keys match collection_id used in LAYERS below
COLLECTION_DEFS = {
    "climate": {
        "title": "Climate",
        "description": "Climatic variables including bioclimatic indices, temperature, and precipitation.",
        "license": "CC-BY-4.0",
        "keywords": ["climate", "bioclim", "temperature", "precipitation"],
        "providers": [
            pystac.Provider(
                name="CHELSA",
                description="Climatologies at High resolution for the Earth's Land Surface Areas",
                roles=["producer", "processor"],
                url="https://chelsa-climate.org"
            ),
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "vegetation": {
        "title": "Vegetation",
        "description": "Vegetation structure and productivity variables.",
        "license": "CC-BY-4.0",
        "keywords": ["vegetation", "ndvi", "evi", "lai"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "remote_sensing": {
        "title": "Remote Sensing",
        "description": "Satellite-derived spectral and structural variables.",
        "license": "CC-BY-4.0",
        "keywords": ["remote sensing", "satellite", "spectral"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "soil_physiochemical": {
        "title": "Soil Physiochemical",
        "description": "Soil physical and chemical properties.",
        "license": "CC-BY-4.0",
        "keywords": ["soil", "physiochemical", "texture", "pH"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "anthropogenic": {
        "title": "Anthropogenic",
        "description": "Human influence and anthropogenic pressure variables.",
        "license": "CC-BY-4.0",
        "keywords": ["anthropogenic", "human influence", "population"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "land_use_land_cover": {
        "title": "Land Use Land Cover",
        "description": "Land use and land cover classification variables.",
        "license": "CC-BY-4.0",
        "keywords": ["land use", "land cover", "lulc"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
    "topography": {
        "title": "Topography",
        "description": "Topographic and terrain variables.",
        "license": "CC-BY-4.0",
        "keywords": ["topography", "elevation", "dem", "terrain"],
        "providers": [
            pystac.Provider(
                name="BRANCH Institute",
                roles=["host"],
                url="https://branch-institute.org"
            ),
        ],
    },
}

COLLECTIONS = {}
for cid, meta in COLLECTION_DEFS.items():
    collection = pystac.Collection(
        id=cid,
        title=meta["title"],
        description=meta["description"],
        license=meta["license"],
        keywords=meta["keywords"],
        providers=meta["providers"],
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent(bboxes=[[-180, -90, 180, 90]]),
            temporal=pystac.TemporalExtent(intervals=[[None, None]])
        )
    )
    catalog.add_child(collection)
    COLLECTIONS[cid] = collection

# --- Layer definitions ---
# filepath: path under cogs/ on GCS
# collection_id: must match a key in COLLECTION_DEFS
# title: human-readable name shown in STAC Browser
# description: what the layer represents
# datetime: representative date for the layer
# doi: optional DOI URL
# thumbnail: optional filename under thumbnails/ on GCS (None if not available)
LAYERS = [
    {
        "filepath": "CHELSA_bioclim/CHELSA_bio01_1981-2010_V.2.1.tif",
        "collection_id": "climate",
        "title": "CHELSA Bio01 — Annual Mean Temperature (1981–2010)",
        "description": "Annual mean temperature [°C × 10] at 1 km resolution, 1981–2010 climatology.",
        "datetime": datetime(1981, 1, 1),
        "doi": "https://doi.org/10.1038/s41597-022-01834-9",
        "thumbnail": None,
    },
    {
        "filepath": "CHELSA_bioclim/CHELSA_bio02_1981-2010_V.2.1.tif",
        "collection_id": "climate",
        "title": "CHELSA Bio02 — Mean Diurnal Range (1981–2010)",
        "description": "Mean of monthly (max temp − min temp) [°C × 10] at 1 km resolution, 1981–2010 climatology.",
        "datetime": datetime(1981, 1, 1),
        "doi": "https://doi.org/10.1038/s41597-022-01834-9",
        "thumbnail": None,
    },
    {
        "filepath": "CHELSA_bioclim/CHELSA_bio03_1981-2010_V.2.1.tif",
        "collection_id": "climate",
        "title": "CHELSA Bio03 — Isothermality (1981–2010)",
        "description": "Isothermality (Bio02/Bio07 × 100) at 1 km resolution, 1981–2010 climatology.",
        "datetime": datetime(1981, 1, 1),
        "doi": "https://doi.org/10.1038/s41597-022-01834-9",
        "thumbnail": None,
    },
    {
        "filepath": "CHELSA_bioclim/CHELSA_bio04_1981-2010_V.2.1.tif",
        "collection_id": "climate",
        "title": "CHELSA Bio04 — Temperature Seasonality (1981–2010)",
        "description": "Temperature seasonality (standard deviation × 100) at 1 km resolution, 1981–2010 climatology.",
        "datetime": datetime(1981, 1, 1),
        "doi": "https://doi.org/10.1038/s41597-022-01834-9",
        "thumbnail": None,
    },
]

for layer in LAYERS:
    filepath = layer["filepath"]
    filename = filepath.split("/")[-1]
    name = filename.removesuffix(".tif")
    href = f"{BUCKET}/cogs/{filepath}"

    with rasterio.open(href) as src:
        bounds = src.bounds
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        geom = mapping(box(*bbox))

    extra_fields = {"description": layer["description"]}
    if layer.get("doi"):
        extra_fields["sci:doi"] = layer["doi"]

    item = pystac.Item(
        id=name,
        geometry=geom,
        bbox=bbox,
        datetime=layer["datetime"],
        properties={"title": layer["title"], **extra_fields}
    )
    item.add_asset(
        "data",
        pystac.Asset(
            href=href,
            title=layer["title"],
            media_type=pystac.MediaType.COG,
            roles=["data"]
        )
    )
    if layer.get("thumbnail"):
        item.add_asset(
            "thumbnail",
            pystac.Asset(
                href=f"{BUCKET}/thumbnails/{layer['thumbnail']}",
                media_type="image/png",
                roles=["thumbnail"]
            )
        )

    COLLECTIONS[layer["collection_id"]].add_item(item)

# --- Save ---
catalog.normalize_hrefs(f"{BUCKET}/stac")
catalog.save(catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED, dest_href="./stac")
