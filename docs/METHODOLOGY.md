# Methodology

## AOI and coordinates

Bago Region is an administrative unit. Bago Yoma is a geographical hill/forest region; they are not interchangeable. No authoritative Bago Yoma polygon was obtained. The release uses an analyst-drawn envelope intersected with geoBoundaries Bago 2019, prominently labelled **Approximate study boundary**. It is not a verified forest-only mask. The exact polygon, metadata and projected area are in `public/data/aoi.geojson`. Web geometry is WGS84 EPSG:4326; Python distances, grid and area use WGS84/UTM zone 47N EPSG:32647. Browser custom polygon area is a spherical estimate and is labelled in its metadata; reprocess with Python for projected measurements.

The 5 km grid is a provisional planning scale: both 1 km MODIS and nominal 375 m VIIRS records fit within it, while monthly aggregation reduces sparsity. This is not proof of optimal resolution. Edge cells are clipped; slivers below 0.1 km² are excluded. 589 cells cover the release AOI. Experiments at other scales need independent frequency/coverage and validation checks before claiming improved precision.

## Ingestion and quality

Raw downloads are retained, SHA-256 hashed and never modified by normalization. Coordinates, UTC acquisition time, source, ingestion time, satellite, original confidence, FRP (MW), scan/track (km), day/night and version are retained. Invalid coordinates/timestamps are rejected. Exact duplicate rows are removed. Standard records take precedence over NRT records with the same sensor/satellite/position/time; original raw records remain. This exact-pixel rule cannot guarantee matching shifted geolocation between processing versions.

MODIS confidence 30–100 and VIIRS nominal/high qualify. These are sensor-specific rules, not interchangeable confidence scales. VIIRS categories are never converted to MODIS percentages. Files with unspecified processing quality are marked `standard_or_unspecified`; inspect product versions before assuming standard status. No-record counts are **not confirmed absence** because overpass/cloud/valid-observation coverage was not acquired.

## Harmonization

The implemented method has separate components:

1. Common UTC schema, original provenance, quality filtering and exact duplicate handling.
2. Configurable potential cross-sensor pairs (default 1 km, 90 minutes), greedy nearest one-to-one matching across UTC midnight. These are candidate observations, not confirmed fire incidents. Pairing does not establish burned area or add/subtract incidents.
3. Shared 5 km cells and monthly bins.
4. Experimental monthly regional calibration, fit only on 2015–2021 paired monthly totals. Let global training ratio be `g=(sum(V)+1)/(sum(M)+1)`. For calendar month m, `r_m=(sum(V_m)+20*g)/(sum(M_m)+20)`. Adjusted MODIS activity is `r_m*M`; the combined activity index is `(r_m*M+V)/2`. The shrinkage value 20 is an explicitly fixed engineering choice, not a universal scientific constant.
5. Held-out 2024–2025 regional monthly MAE against VIIRS is compared before/after adjustment. 100 resampled training-year sets give a 10th–90th ratio spread. This does not capture all observation/detection biases.

The adjusted grid applies the same regional coefficient to each cell. **Cell-level calibration is not independently validated.** Combined values are VIIRS-equivalent activity indices, never counts of distinct fires. The equal-weight mean avoids simply adding redundant sensor records. Neither this mean nor common-grid aggregation fully corrects sensor sensitivity, cloud coverage, overpass frequency or pixel-footprint differences. The model target uses one stable VIIRS platform instead of pretending adjusted counts are verified incident labels.

## Calendar

Raw views expose either sensor or their detection-record total. Adjusted activity uses both qualifying sensors regardless of the point-display sensor toggle. A 2015–2021 reference monthly mean supports anomalies expressed as differences in recorded activity. A missing file raises an error; it is not substituted by zeros. Cells with zero records are hatched/labelled coverage unknown. Day detail exists only from timestamped raw observations; no daily adjusted series is fabricated.

## Modelling and outlook

The target is presence of at least one qualifying recorded VIIRS S-NPP detection in a cell/month. Apparent negatives can be unobserved or missed fires. See the model card for splits and metrics. History-derived training features use only strictly earlier years. Later validation/test and rolling-origin predictions use only the training history. Seasonal inputs are climatological historical patterns, not future observed NDVI or weather. Modelled outputs are relative ranks; actual-fire probabilities cannot be established from this archive alone.

November 2026 is the released planning origin. The latest observation is 31 December 2025. January–October 2026 is an unobserved pre-origin gap. 36/48-month horizons repeat the learned seasonal pattern because no defensible year-specific climate projection was available.

Dry/hot and wet/cool sensitivities multiply the recorded-detection proxy odds by 1.25 and 0.8. These user scenarios have no assigned likelihood and are not estimated climate responses. Ranking uses a fixed baseline cell/month reference distribution. Display categories default to five relative percentile bands and can be changed in the UI. They are not universal damage or safety thresholds. No population/infrastructure impact score is implemented.

Bootstrap-year spread (40 resamples, seed 42, 10th–90th percentiles) measures historical sampling variability for the selected seasonal baseline. It is not a calibrated future prediction interval. Scenario changes are conceptually separate from this baseline uncertainty.

## Export semantics

CSV files use stable machine-readable keys, original provenance, units, source AOI/version and observation/model status; user-facing report headings follow the selected language. Export the AOI GeoJSON alongside CSVs to retain the exact polygon. Adjusted monthly exports contain the whole reference archive; grid exports use selected year/month and both qualifying sensors. Projection export is the selected target month/scenario; the local API can produce all 36/48 months. Original confidence, future susceptibility and potential damage remain separate concepts.
