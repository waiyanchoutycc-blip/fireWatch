# Model card

## Intended use and target

Exploratory research and seasonal planning within the approximate Bago Yoma study AOI. The event is at least one qualifying **recorded VIIRS S-NPP detection** per 5 km cell-month. Missing records do not establish a true no-fire state. No public-safety warning, exact ignition-location prediction or damage estimate is supported.

## Actual training

Run: 2026-11-11T02:41:43.581003+00:00. Seed: 42. 109,544 raw AOI records; 91,051 quality-filtered records across both sensors. 589 grid cells. Training years 2015–2021, validation 2022–2023, test 2024–2025 (14,136 cell-months).

Three approaches were actually fitted/evaluated:

- Seasonal baseline: smoothed empirical cell/month frequency, borrowing strength from regional month frequency.
- Logistic regression: scaled six-feature input, balanced class weights, up to 600 optimization iterations.
- Random Forest: 100 bootstrap trees, maximum depth 10, minimum 20 samples per leaf, balanced subsample class weights, two CPU workers. No pretrained/deep-learning model was used.

Features: latitude, longitude, sine/cosine month, strictly historical cell-season and cell activity. Each supervised training year uses only earlier years. The first year supplies history rather than training labels. GEE terrain, vegetation, cover, weather and roads are not model inputs. NASA POWER is contextual only.

## Held-out scores

| Model | Accuracy | Precision | Recall | F1 | PR-AUC | Brier | Decision threshold |
|---|---:|---:|---:|---:|---:|---:|---:|
| Seasonal baseline | 0.9194 | 0.7106 | 0.8125 | 0.7581 | 0.8126 | 0.0569 | 0.4500 |
| Logistic regression | 0.9207 | 0.7325 | 0.7715 | 0.7515 | 0.8066 | 0.0898 | 0.8000 |
| Random forest | 0.9163 | 0.6929 | 0.8289 | 0.7548 | 0.8387 | 0.0851 | 0.7500 |

Test positive rate: 0.1554. Predicting no detection everywhere therefore yields high accuracy; PR-AUC, recall, F1 and Brier provide more useful complementary evidence.

**Selected for the displayed outlook: Seasonal baseline.** Selection used lowest validation Brier score. Random Forest ranks recorded activity well (highest test PR-AUC) but its raw class-balanced probabilities have poorer Brier error. We do not publish these as calibrated actual-fire probabilities. Thresholds maximize validation F1 on 0.05–0.95 in steps of 0.05; the test set did not select them. Calibration plots are diagnostics, not a claim that the outputs were successfully calibrated.

After independent evaluation, all 2015–2025 years are used for the final planning refit. The fitted estimators, history, preprocessing, feature schema and report are included in `data/runtime/model.joblib`. The evaluation results belong to the separate chronological fits, not that final refit. Only load this trusted package; joblib is executable serialization.

## Spatial and temporal checks

Random Forest spatial holdout: easternmost 20% of cells excluded from fitting and evaluated in 2024–2025; F1 0.6643. This is one geographic split, not proof of transfer across all Myanmar.

| Origin (last observed year) | Lead years | RF F1 | Seasonal F1 | RF PR-AUC |
|---|---:|---:|---:|---:|
| 2019 | 1 | 0.7700 | 0.7237 | 0.8407 |
| 2019 | 2 | 0.6920 | 0.7288 | 0.7956 |
| 2019 | 3 | 0.6881 | 0.7533 | 0.8140 |
| 2019 | 4 | 0.7295 | 0.7312 | 0.8138 |
| 2021 | 1 | 0.7039 | 0.7523 | 0.8163 |
| 2021 | 2 | 0.7381 | 0.7464 | 0.8250 |
| 2021 | 3 | 0.7466 | 0.7828 | 0.8713 |
| 2021 | 4 | 0.6834 | 0.7199 | 0.8087 |

Rolling tests use the origin-year history for every lead year, without observed future weather/vegetation. Fixed 0.5 decision thresholds are used for these diagnostic backtests, so their F1 values are not directly equivalent to the validation-tuned final test threshold. This small number of origins does not establish reliable year-specific future skill.

Dry (November–April) and wet (May–October) metrics and calibration bins are in `public/data/model-report.json`. Full data hashes, feature types, configuration, seed and source hash are in that report.

## Scores, scenarios and uncertainty

UI scores are relative percentiles of the selected model across the full 589-cell × 12-month baseline reference distribution. They are not percent probability. The default bands are <20, <40, <60, <80, ≥80 and are user-configurable; equal scores/ties mean category sizes are not exactly 20% each.

The 36/48-month projection begins at 2026-11-01. Latest observed day: 2025-12-31. The archive has an unobserved January–October 2026 gap. All future years repeat the seasonal pattern. Dry/hot and wet/cool scenarios multiply proxy odds by 1.25/0.8 before reference ranking. They are arbitrary sensitivity assumptions, not estimated climate-model outputs.

10th–90th year-bootstrap spread (seasonal baseline), or tree disagreement (RF); not a calibrated prediction interval. The seasonal baseline uses 40 resamples of whole historical years, seed 42. Scenario differences are not folded into this sampling spread.

## Missing evidence

- No VIIRS coverage masks/verified true negatives, wildfire ground truth, or official forest boundary.
- No acquired GEE covariates, no environmental covariate model or climate projections.
- No calibrated actual-fire probabilities, incident inventory, damage score, emergency forecasting, or independent Myanmar field validation.
- Spatial/temporal data dependence, mixed land use and changing observation sensitivity limit generalization.
- Specialist Myanmar terminology needs local human review.
