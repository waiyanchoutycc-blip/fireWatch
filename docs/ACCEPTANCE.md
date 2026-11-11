# Release verification and scope

## Verified on 11 November 2026

| Area | Evidence |
|---|---|
| Real acquisition | 22 NASA country archives; 4,260,128 source rows; SHA-256 manifests; POWER and geoBoundaries retrieved. |
| Actual model training | Three estimators/baselines evaluated from authentic records; joblib artifact saved and loaded for API inference. No synthetic training data. |
| AOI and CRS | Automated tests check original AOI membership, every clipped grid cell, 589-cell grid and WGS84↔UTM round trip. |
| Data semantics | Automated tests cover exact duplicates, invalid coordinates/dates/missing time, original confidence scales, standard-over-NRT replacement and cross-midnight sensor pairs. |
| Leakage and splits | Tests verify past-only feature construction and chronological train/validation/test separation; real rolling-origin and spatial results saved. |
| Coverage and inference | No-record versus unknown-coverage contract; missing-model HTTP 503, bad filters HTTP 422, mutation authentication, 36-month saved-model inference tested. |
| API import | Temporary test imports preserve original bytes and produce valid candidate matching results. Built app, data, model and API docs endpoints returned HTTP 200. |
| Frontend contracts | CSV schema/time validation, NRT replacement, AOI clipping/invalid geometry, bilingual dictionary completeness, bounded scenario ranking and formula-safe CSV exports. |
| Browser QA | English/Myanmar switching; actual satellite basemap with WebGL fallback; monthly calendar selection loads the corresponding year/month on the map; import of 12 authentic NASA records succeeded (11 qualify); original calibration/model disabled for custom import, then NASA dataset restored. |
| Exports | A real 2025 filtered CSV was downloaded and inspected: 6,855 rows; source, sensor, original confidence, units, AOI/version, mode and coverage fields present. |
| Layout | Desktop, 390 px mobile iframe and 820 px tablet iframe reviewed; Myanmar wraps without horizontal page overflow in reviewed views. Light/dark modes reviewed; warning contrast corrected. These are browser layout checks, not physical-device certification. |
| Build | TypeScript compilation and Vite production build complete; JS and Python dependency versions pinned. |

Automated suites: **10 Python tests and 7 TypeScript tests**. The model quality report contains measured statistical evaluations; unit tests do not certify predictive validity. Library deprecation warnings and MapLibre's large bundle warning remain non-blocking.

## Explicit limits / not completed

- The public-facing hosted artifact is a static interactive dashboard with a genuine trained snapshot. The FastAPI service and training queue run locally; there is no hosted Python training service, PostGIS server, persistent distributed job queue or scheduled data refresh.
- GEE export code is prepared and syntax-checked, but no authenticated export was executed. No DEM, land-cover, vegetation, drought, roads/settlements or satellite observation-denominator features were fitted. No forest-only or land-cover overlay is fabricated; terrain is a basemap.
- Bago Yoma uses an approximate analyst envelope, not an official forest boundary. Custom browser AOI area is an explicitly labelled spherical estimate; original AOI/grid calculations use projected UTM. Custom polygons can clip the delivered study subset but cannot recover observations outside it; import a broader CSV for that purpose.
- The operational pipeline uses a fixed 5 km grid. Other resolutions need coordinated normalization, feature, interface and evaluation changes. The `grid` utility accepts a cell size but this release does not expose a resolution selector.
- Sensor calibration is regional and experimental; it does not make the sensor of origin irrelevant. Cell-level adjustment is extrapolated from the regional coefficient. No verified incident clusters are generated. Display clusters are only map grouping.
- True no-fire labels and calibrated actual-fire probabilities are unavailable. Relative seasonal susceptibility is used. Climate scenarios are sensitivity assumptions; no exact future ignition locations/dates or year-specific climate forecasts are claimed.
- Risk category thresholds are configurable. Impact/damage scoring is not implemented. Data scarcity and observation coverage remain explicit caveats rather than a fabricated quantified risk adjustment.
- Daily raw calendars are available; daily calibrated/harmonized activity is not. Monthly calendar clicks synchronize the map. A separate day-level map filter and a predefined named subregion picker are not provided; use the polygon tools for subregions.
- Browser exports use stable machine-readable CSV keys; printable headings are translated. The concise print layout is implemented but physical printing/PDF output was not verified. The Dockerfile is supplied but not executed here.
- API ingestion code is provided but live keyed requests were not run (no FIRMS API key). Browser uploads are local and deliberately do not train or change the shared published snapshot. Invalid services never trigger a synthetic fallback.
- Specialist Myanmar terminology remains subject to human review. Keyboard-accessible tables and upload controls supplement canvas interaction; a formal accessibility audit has not been completed.

These limits are part of the release, not hidden claims of completed scientific work. Prioritize authenticated observation coverage and environmental-data evaluation before promoting this prototype to operational use.
