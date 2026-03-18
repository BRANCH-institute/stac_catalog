#!/usr/bin/env bash
set -euo pipefail

BUCKET="gs://johan_public/test_stac"
CATALOG_URL="https://storage.googleapis.com/johan_public/test_stac/stac/catalog.json"
GH_PAGES_URL="https://branch-institute.github.io/stac_catalog/"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ── 1. Build STAC catalog ──────────────────────────────────────────────────
echo "==> Building STAC catalog..."
python3 build_stac.py

# ── 2. Upload catalog to GCS ───────────────────────────────────────────────
echo "==> Uploading catalog to GCS..."
gcloud storage cp -r stac/* "$BUCKET/stac/" \
  --cache-control='no-cache, no-store, must-revalidate'

# ── 3. Upload COGs (if present locally) ───────────────────────────────────
if [ -d cogs ] && [ -n "$(ls -A cogs 2>/dev/null)" ]; then
  echo "==> Uploading COGs to GCS..."
  gcloud storage cp -r cogs/* "$BUCKET/cogs/"
fi

# ── 4. Build STAC Browser ─────────────────────────────────────────────────
echo "==> Building STAC Browser..."
cd "$REPO_ROOT/stac-browser"
npm run build
cd "$REPO_ROOT"

# ── 5. Deploy to GitHub Pages ─────────────────────────────────────────────
echo "==> Deploying to GitHub Pages..."
WORKTREE_DIR="$(mktemp -d)"
cleanup() { git worktree remove --force "$WORKTREE_DIR" 2>/dev/null || true; rm -rf "$WORKTREE_DIR"; }
trap cleanup EXIT

if git ls-remote --exit-code origin gh-pages &>/dev/null; then
  git fetch origin gh-pages
  git worktree add "$WORKTREE_DIR" gh-pages
else
  echo "  (first deploy: creating gh-pages branch)"
  git worktree add --orphan -b gh-pages "$WORKTREE_DIR"
fi

rsync -a --exclude='.git' "$REPO_ROOT/stac-browser/dist/" "$WORKTREE_DIR/"
cd "$WORKTREE_DIR"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Deploy STAC Browser"
  git push origin gh-pages
else
  echo "  (no browser changes to deploy)"
fi
cd "$REPO_ROOT"

# ── 6. Commit and push code to main ───────────────────────────────────────
echo "==> Pushing code to GitHub..."

# Ensure .gitignore excludes large/generated files
for pattern in "cogs/" "*.DS_Store" "sampled_points.gpkg" "working_plan_stac_gcs.md"; do
  grep -qxF "$pattern" .gitignore 2>/dev/null || echo "$pattern" >> .gitignore
done

git rm -r --cached cogs/ 2>/dev/null || true

git add .gitignore build_stac.py layers.yaml stac/ sample_points.py deploy.sh
if ! git diff --cached --quiet; then
  git commit -m "Update STAC catalog and layers"
fi
git push origin main

# ── Done ──────────────────────────────────────────────────────────────────
echo ""
echo "Done!"
echo ""
echo "  Catalog:      $CATALOG_URL"
echo "  STAC Browser: $GH_PAGES_URL"
