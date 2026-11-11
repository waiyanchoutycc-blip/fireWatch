# Data sources and acquisition status

Retrieved 10 November 2026; processed/trained again 11 November 2026. No synthetic observations or invented evaluation metrics are included.

| Dataset | Actually used | Coverage and native scale | Role / limitations |
|---|---|---|---|
| NASA FIRMS MODIS, Terra/Aqua, annual Myanmar CSVs | Yes, 589,787 country records | 2015–2025; nominal 1 km | Historical observations and training-period sensor comparison. CSV confidence/scan/track/version retained. |
| NASA FIRMS VIIRS S-NPP, annual Myanmar CSVs | Yes, 3,670,341 country records | 2015–2025; nominal 375 m | Recorded-occurrence labels and comparison reference. No NOAA-20/21 mixing in this model. |
| NASA POWER T2M / PRECTOTCORR | Yes, 132 monthly values per variable | 2015–2025, point 95.9° E, 18.5° N; meteorological grid about 0.625° longitude × 0.5° latitude | Regional climate context only. Temperature °C; precipitation mm/day. Coarse grid was not claimed to contain 5 km information. Annual YYYY13 summaries excluded. |
| geoBoundaries gbOpen / Myanmar Analytics Project | Yes | Bago ADM1, year 2019; boundary ID MMR-ADM1-20573499 | Administrative clipping/context; not an official Bago Yoma forest polygon. CC BY 4.0. Source build December 2023. |
| Analyst study envelope | Yes | Version 1.0, intersected with Bago ADM1; approximately 13,177 km² | Approximate and editable; WGS84 display, UTM 47N measurement. |
| SRTMGL1_003 via GEE | No, exporter provided | NASA/USGS elevation, 30 m | Planned mean elevation, slope and aspect. No downloaded raster or feature used in fitting. |
| MODIS/061/MCD12Q1 via GEE | No, exporter provided | Annual land cover, 500 m | Planned forest fraction from IGBP classes 1–5. Historical classification is not a current forest boundary. |
| MODIS/061/MOD13Q1 via GEE | No, exporter provided | Vegetation indices, 250 m, 16-day | Planned monthly QA-filtered NDVI. No future observed NDVI may enter an outlook/backtest. |
| MODIS/061/MOD14A1 via GEE | No, exporter provided | Terra daily FireMask, 1 km | Planned counts of valid pixel-days; not proof of VIIRS observation coverage. |

Combined country input: **4,260,128 records in 22 archives** (~333 MB CSV). After clipping, resolving identical detections and retaining both sensors: **109,544 AOI records**; **91,051 qualifying records**. Original per-file counts, invalid/outside/duplicate counts and SHA-256 values are in `public/data/summary.json` and `acquisition-manifest.json`. Four exact duplicate rows were found in country VIIRS inputs; they were outside the retained AOI. Cell/month model labels use the quality-filtered VIIRS subset, not the combined raw count.

## Source links

- [Official challenge](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/)
- [NASA FIRMS country archive](https://firms.modaps.eosdis.nasa.gov/country/)
- [NASA FIRMS area API](https://firms.modaps.eosdis.nasa.gov/api/area/)
- [NASA POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/)
- [geoBoundaries metadata](https://www.geoboundaries.org/api/current/gbOpen/MMR/ADM1/)
- [Earth Engine authentication/project setup](https://developers.google.com/earth-engine/guides/auth)
- [SRTM](https://developers.google.com/earth-engine/datasets/catalog/USGS_SRTMGL1_003)
- [MODIS land cover](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD12Q1)
- [MODIS vegetation](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1)
- [MODIS daily fire masks](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD14A1)

NASA observations are openly available scientific data; retain NASA/LANCE/FIRMS and product attribution and consult provider terms. POWER attribution and parameter definitions are retained in its manifest. geoBoundaries geometry is redistributed under CC BY 4.0, credited to geoBoundaries and Myanmar Analytics Project. These data licenses do not imply NASA endorsement of this app.

Basemaps are network services: Esri World Imagery (Esri/Maxar/Earthstar Geographics attribution), OpenTopoMap (OpenStreetMap/SRTM and CC BY-SA cartography), and OpenStreetMap. The app displays attribution and does not bulk download tiles. Provider service policies apply; an institutional production deployment may require a contracted/keyed map provider. A failed basemap does not silently change the analysis dataset.

## GEE status and missingness

The environment had no authenticated registered Earth Engine project. The GEE script was syntax-checked, but authenticated exports were not executed. No GEE result is represented as downloaded or used. It exports native-scale summaries to the same 5 km grid instead of upsampling coarse data and claiming extra information. Inspect temporal coverage and land/water semantics before using a returned table. A complete future environmental model, covariate validation and observed/clear-sky denominator construction remain future work.

Hotspot CSVs are positive detections, not complete observation logs. Even for a complete annual file, zero recorded detections can represent no fire, missed detection or missing observations. The app always distinguishes file availability from satellite observation coverage.
