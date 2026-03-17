# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project builds a geospatial data platform for CHELSA bioclimatic data:
- Convert raster data to Cloud-Optimized GeoTIFFs (COGs)
- Build a static STAC (SpatioTemporal Asset Catalog) hosted on Google Cloud Storage
- Deploy a web-based STAC Browser for catalog navigation
- Python scripts for point sampling of COG layers via rasterio

## Key Commands

### COG Validation & Conversion
```bash
rio cogeo validate file.tif
gdal_translate -of COG -co COMPRESS=DEFLATE input.tif output.tif
```

### Python Dependencies
```bash
pip install pystac rasterio geopandas shapely stac-validator
```

### STAC Catalog Validation
```bash
stac-validator stac/catalog.json
```

### GCS Upload
```bash
gsutil cors set cors.json gs://your-bucket/          # Must be set before browser access
gsutil -m cp *.tif gs://your-bucket/cogs/
gsutil -m cp -r stac/ gs://your-bucket/stac/
```

### STAC Browser Build & Deploy
```bash
git clone https://github.com/radiantearth/stac-browser
cd stac-browser && npm install
SB_catalogUrl="https://storage.googleapis.com/your-bucket/stac/catalog.json" npm run build -- --historyMode=hash
gsutil -m cp -r dist/* gs://your-bucket/browser/
```

## Architecture

### Pipeline Phases
1. **COG Preparation** — Export from GEE or convert local TIFFs to COG format; upload to `gs://your-bucket/cogs/`
2. **STAC Catalog Build** — Python script using `pystac` + `rasterio` generates JSON hierarchy; upload to `gs://your-bucket/stac/`
3. **STAC Browser** — Build `radiantearth/stac-browser` with `catalogUrl` pointing to GCS; deploy to `gs://your-bucket/browser/` or GitHub Pages
4. **Point Sampling** — Python script loads STAC catalog, reads COGs via HTTP range requests using `rasterio.sample()`, joins values to a GeoDataFrame

### GCS Bucket Layout
```
gs://your-bucket/
├── cogs/              # Cloud-Optimized GeoTIFFs
├── stac/
│   ├── catalog.json
│   └── global-layers/
│       ├── collection.json
│       └── {layer-id}/{layer-id}.json   # One STAC Item per COG
└── browser/           # STAC Browser static site
```

### STAC Catalog Hierarchy
- `pystac.Catalog` (root) → `pystac.Collection` (`global-layers`) → `pystac.Item` (one per COG)
- Each Item has a single `"data"` asset pointing to the GCS COG URL
- Catalog saved as `ABSOLUTE_PUBLISHED` type with `normalize_hrefs()` before saving

### Point Sampling Notes
- `rasterio.open(https_url)` reads COGs directly over HTTP using range requests — no local download needed
- For >100k points, `src.sample(coords)` is still efficient as it uses COG internal tiling
- Sampling from Google Colab or GCE avoids GCS egress charges
- Output: GeoPackage or Parquet with one column per sampled layer

### CORS Requirement
The GCS bucket requires CORS configured (`cors.json`) before the STAC Browser can read catalog JSON files. The COG files themselves also need public read access.
