# Bago Yoma FireWatch — ပဲခူးရိုးမ မီးဘေးစောင့်ကြည့်ရေး

A working English/Myanmar map and research application for NASA Space Apps 2026, **Harmonization of MODIS and VIIRS Hot Spots**. This release uses authentic NASA records, not synthetic observations.

The hosted dashboard contains the real processed archive and outputs from actually fitted models. The reproducible Python pipeline and FastAPI backend run locally. Python training is **not hosted by the static website**. Browser CSV uploads are stored on that device and do not retrain the published model.

## What works

- Six bilingual views: overview, map, calendar, future planning, model quality, methodology; persistent language and light/dark selection.
- Interactive satellite/terrain/simple basemaps with attribution. MapLibre is the primary renderer; Leaflet is an automatic fallback when WebGL is unavailable.
- MODIS circles, VIIRS diamonds at detailed zoom, grouped detections at broad zoom, AOI boundaries and 5 km cells; popups/table, sensor/year/month/quality filters.
- User polygon drawing and single-feature Polygon/MultiPolygon GeoJSON uploads; analysis clipped to the chosen polygon. Custom AOIs disable the original model and regional calibration until reset.
- Real 2015–2025 NASA FIRMS archive, monthly and daily calendars, linked map selection, seasonal reference comparisons, raw versus experimentally adjusted activity.
- CSV/GeoJSON exports, model evaluation JSON and browser print report.
- Local FastAPI import, paginated queries, spatial/temporal candidate matching, background training job and saved-model inference.
- Seasonal baseline, logistic regression and 100-tree Random Forest training; chronological and spatial tests, rolling origins, calibration diagnostics and authentic metrics.
- 36/48-month planning view, repeated seasonal susceptibility, explicit scenarios and bootstrap spread. It does not claim calibrated actual-fire probabilities.

## Quick start — Windows CMD

Install Python 3.12 and Node.js 22 LTS, extract the source ZIP, then open CMD in that directory. If `py` is unavailable but `python --version` works, replace `py -3.12` with `python`.

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.lock.txt
npm ci
npm run dev
```

Open the localhost URL printed by Vite (normally `http://localhost:5173`). The bundled processed data work immediately. No NASA/GEE credentials are needed for this snapshot. A GPU is not needed.

macOS/Linux use `python3 -m venv .venv` and `source .venv/bin/activate`, then the same remaining commands.

To run the full local application and API from one origin:

```bat
npm run build
set FIREWATCH_API_KEY=choose-a-long-random-local-secret
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the app and `http://127.0.0.1:8000/docs` for the interactive API. The key authorizes mutations through the `X-API-Key` header. It is never embedded in the frontend. `.env.example` documents variables; it is a template, not an automatically loaded secret file.

## Reproduce the observations and training

```bat
python scripts/acquire_sources.py --start-year 2015 --end-year 2025
python -m backend.train
python -m unittest discover -s tests -v
npm test
npm run build
```

Acquisition downloads approximately 333 MB of country CSVs, validates their headers and hashes, and preserves them in `data/raw`. It also fetches NASA POWER context and the licensed Bago administrative polygon. Processing clips to the approximate study AOI. No source country CSVs are bundled in the ZIP; URLs, checksums, the AOI subset and a re-download script are included.

The pipeline saves `data/runtime/model.joblib`, `public/data/model-report.json`, manifests, monthly outputs, annual point files and the seasonal grid outlook. `data/processed/<fingerprint>` keeps a separately versioned snapshot; the fingerprint includes source code and raw-data hashes. The first year is a burn-in for supervised historical features. Model selection and thresholds use validation years, never the final test years.

To import another historical collection, put complete annual MODIS and VIIRS CSVs in a separate folder and run `python -m backend.train --raw-dir PATH`. At least seven overlapping years are required. Sparse/partial date coverage is not inferred from hotspot files; inspect the source manifests before treating a year as complete. Do not promote arbitrary browser/API uploads automatically into a training dataset.

## Optional NASA API and GEE

For an area API request (availability depends on the chosen product/date):

```bat
set FIRMS_MAP_KEY=your-key
python scripts/firms_api.py --source VIIRS_SNPP_SP --date 2025-03-01 --days 1
```

API raw files and processed manifests are kept separately. Near-real-time processing is explicitly marked. These requests do not silently update training or the published snapshot.

No Google Earth Engine project/credentials were supplied, so **GEE exports were not run and no GEE predictors were used in the delivered model**. The optional exporter is included:

```bat
python -m pip install -r requirements-gee.txt
earthengine authenticate
python scripts/export_gee.py --project YOUR_REGISTERED_PROJECT --year 2024
```

This creates Drive export tasks for NASA/USGS SRTM terrain, MODIS land cover, NDVI and MODIS observation masks. Review task success, band quality, dates and missingness. These exports are a preparation workflow, **not an automatically validated environmental-model upgrade**. MODIS Terra coverage cannot establish VIIRS S-NPP no-fire observations. See `docs/DATA_SOURCES.md`.

## API examples

Read `GET /api/health`, `/api/model`, or `/api/hotspots?year=2025&month=3&sensor=VIIRS&limit=500&offset=0`.

```json
POST /api/predict
{"months":48,"scenario":"baseline","cell_ids":["31_397"]}
```

Use actual `cell_id` values from `public/data/grid.geojson`, or omit `cell_ids` for all cells. Scenarios are `baseline`, `dry`, `wet`. A missing model returns HTTP 503. No random/synthetic prediction fallback exists.

`POST /api/import` accepts a multipart `file` up to 25 MB. `POST /api/match` accepts its SHA-256 and configurable `meters`/`minutes`. `POST /api/train` queues a job on the annual archive; poll `GET /api/jobs/{job_id}`. All mutation endpoints require `X-API-Key`. Jobs are local and in-memory; a process restart does not resume a job. Keep this service bound to loopback unless you add deployment authentication, quotas and a persistent job queue.

## Architecture and limits

React/TypeScript/Vite → yearly JSON point subsets and shared grid → Python pandas/Shapely/pyproj → scikit-learn → joblib/JSON. FastAPI serves the built UI and local API. A file-backed local store is used; PostgreSQL/PostGIS and a distributed queue are not configured. Cached year loads, viewport grouping and table pagination keep this AOI usable. Country/global interactive workloads would require spatial tiles/database indexing.

The source ZIP contains the fitted model, source, lock files, processed data, tests and documentation. The Dockerfile packages the full local service; Docker execution was not verified in this workspace. Bind a local container to loopback with `-p 127.0.0.1:8000:8000`.

Read `docs/MODEL_CARD.md`, `docs/METHODOLOGY.md`, `docs/DATA_SOURCES.md`, `docs/ACCEPTANCE.md` and `docs/DEMO_GUIDE.md` before presenting results. Thermal anomalies include agricultural and other heat sources. **Long-term planning projection — not an operational fire warning.**

## GitHub Pages deployment

The Pages workflow tests and builds the static dashboard on pushes to main.
Enable Settings > Pages > Build and deployment > Source: GitHub Actions.
Expected URL after successful deployment: https://waiyanchoutycc-blip.github.io/fireWatch/

`npm run build:pages` builds for `/fireWatch/`; `npm run build` retains root-path hosting for the local API or other hosts. Data and source-download URLs follow the Vite base path. The workflow creates the downloadable source ZIP before building, including the saved model. The saved model is explicitly tracked; imports and other runtime output remain ignored.

GitHub Pages serves the bundled observations and model outputs. It does not host Python training or FastAPI. Browser imports remain on the visitor's device.

The imported model snapshot's reported training-source hash differs from the supplied training code. Deployment preserves that report without claiming a fresh training run. Reconcile the training revision or rerun training before claiming exact reproducibility. The archive calendar remains qualifying-only even when the map's quality toggle is off; compare like-for-like filters.
