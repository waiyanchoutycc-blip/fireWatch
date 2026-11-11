# Five-minute hackathon demonstration

1. Open **Overview**. Explain Bago Region versus the approximate Bago Yoma study envelope. Identify real NASA data, dates and unknown observation coverage.
2. Select March 2024. Zoom in so MODIS orange circles and VIIRS magenta diamonds are visible. Open a table row: original sensor confidence, UTC/Yangon time, FRP and provenance remain available.
3. Open **Burning calendar**. Compare 2015–2025 and switch between raw and adjusted activity. Click a month to update the map. Explain that a thermal detection is not one wildfire.
4. Enable **Adjusted historical grid**. Explain the training-era monthly MODIS-to-VIIRS adjustment and its limits; download grid/monthly CSV and the AOI.
5. Open **Model & data**. Show actual held-out 2024–2025 scores. Random Forest F1 is about 0.755; the seasonal baseline is displayed for planning because validation Brier error was better. Explain the missing observation denominator.
6. Open **Future risk**. Select 36 or 48 months; move across the same season in different years. The repeated pattern is intentional. Compare sensitivity scenarios and bootstrap spread. Read the non-operational-warning label.
7. Switch to **မြန်မာ** and dark mode. Show an import or draw a new AOI: the original fitted model/calibration becomes unavailable rather than making unsupported new-AOI predictions.
8. Finish with **Methodology** and the source download. State that NASA data were used; authenticated GEE covariates/coverage masks are the next scientific step, not completed work.

Do not say “92% accurate wildfire prediction,” “one marker equals one fire,” “NASA-validated model,” or “exact fires three years ahead.” A defensible phrase is: “On withheld 2024–2025 cell-months, the model identified patterns of recorded satellite activity; planning maps show exploratory relative seasonal susceptibility.”
