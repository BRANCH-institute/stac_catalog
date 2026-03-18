import yaml
import pystac
import rasterio
from datetime import datetime, timezone
from shapely.geometry import box, mapping

BUCKET = "https://storage.googleapis.com/johan_public/test_stac"
LAYERS_FILE = "layers.yaml"

# --- Load layer definitions ---
with open(LAYERS_FILE) as f:
    config = yaml.safe_load(f)

# --- Catalog ---
catalog = pystac.Catalog(
    id="my-raster-stack",
    title="Global Environmental Layers",
    description="Global environmental raster data products"
)

# --- Build collections and items ---
for cid, meta in config["collections"].items():
    providers = [
        pystac.Provider(
            name=p["name"],
            description=p.get("description"),
            roles=p["roles"],
            url=p.get("url")
        )
        for p in meta.get("providers", [])
    ]

    collection = pystac.Collection(
        id=cid,
        title=meta["title"],
        description=meta["description"],
        license=meta["license"],
        keywords=meta.get("keywords", []),
        providers=providers,
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent(bboxes=[[-180, -90, 180, 90]]),
            temporal=pystac.TemporalExtent(intervals=[[None, None]])
        )
    )
    catalog.add_child(collection)

    for layer in meta.get("layers", []):
        href = layer.get("href") or f"{BUCKET}/cogs/{layer['filepath']}"

        if layer.get("bbox"):
            bbox = layer["bbox"]
            geom = mapping(box(*bbox))
        else:
            with rasterio.open(href) as src:
                bounds = src.bounds
                bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
                geom = mapping(box(*bbox))

        item_datetime = datetime.fromisoformat(layer["datetime"]).replace(tzinfo=timezone.utc)

        extra_fields = {"description": layer["description"]}
        if layer.get("doi"):
            extra_fields["sci:doi"] = layer["doi"]
        for field in ("unit", "scale", "offset", "datatype"):
            if layer.get(field) is not None:
                extra_fields[field] = layer[field]

        item = pystac.Item(
            id=layer["id"],
            geometry=geom,
            bbox=bbox,
            datetime=item_datetime,
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
            thumb = layer["thumbnail"]
            thumb_href = thumb if thumb.startswith("http") else f"{BUCKET}/thumbnails/{thumb}"
            item.add_asset(
                "thumbnail",
                pystac.Asset(
                    href=thumb_href,
                    media_type="image/png",
                    roles=["thumbnail"]
                )
            )
        collection.add_item(item)

    # --- External indexed sub-collections (e.g. tiled datasets with a GeoParquet index) ---
    for ext in meta.get("external_collections", []):
        ext_providers = [
            pystac.Provider(
                name=p["name"],
                description=p.get("description"),
                roles=p["roles"],
                url=p.get("url")
            )
            for p in ext.get("providers", [])
        ]

        start = datetime.fromisoformat(ext["temporal_extent"][0]).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(ext["temporal_extent"][1]).replace(tzinfo=timezone.utc)

        # Collect any aef: prefixed extra fields
        extra_fields = {}
        for key, val in ext.items():
            if key.startswith("aef:"):
                extra_fields[key] = val
        if ext.get("attribution"):
            extra_fields["attribution"] = ext["attribution"]

        ext_collection = pystac.Collection(
            id=ext["id"],
            title=ext["title"],
            description=ext["description"],
            license=ext["license"],
            keywords=ext.get("keywords", []),
            providers=ext_providers,
            extent=pystac.Extent(
                spatial=pystac.SpatialExtent(bboxes=[ext["spatial_extent"]]),
                temporal=pystac.TemporalExtent(intervals=[[start, end]])
            ),
            extra_fields=extra_fields
        )

        # Link to STAC GeoParquet (standard way to reference a tiled item index)
        ext_collection.add_link(pystac.Link(
            rel="items",
            target=ext["stac_geoparquet_href"],
            media_type="application/vnd.apache.parquet",
            extra_fields={"title": "STAC GeoParquet index"}
        ))

        # Assets: spatial indices and base tile location
        ext_collection.add_asset("index_parquet", pystac.Asset(
            href=ext["index_parquet_href"],
            title="Spatial index (GeoParquet)",
            media_type="application/vnd.apache.parquet",
            roles=["metadata"]
        ))
        ext_collection.add_asset("index_gpkg", pystac.Asset(
            href=ext["index_gpkg_href"],
            title="Spatial index (GeoPackage)",
            media_type="application/geopackage+sqlite3",
            roles=["metadata"]
        ))

        catalog.add_child(ext_collection)

# --- Save ---
catalog.normalize_hrefs(f"{BUCKET}/stac")
catalog.save(catalog_type=pystac.CatalogType.ABSOLUTE_PUBLISHED, dest_href="./stac")

print("STAC catalog written to ./stac/")
print("\nNext steps:")
print("  1. Upload COGs:    gcloud storage cp -r cogs/* gs://johan_public/test_stac/cogs/")
print("  2. Upload catalog: gcloud storage cp -r stac/* gs://johan_public/test_stac/stac/ --cache-control='no-cache, no-store, must-revalidate'")
