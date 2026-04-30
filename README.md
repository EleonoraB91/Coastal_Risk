[README.md](https://github.com/user-attachments/files/27259828/README.md)
# Italian Minor Islands Coastal Risk — QGIS Plugin v1.6

A QGIS plugin for **coastal erosion vulnerability assessment** on Italian minor islands, based on the Coastal Vulnerability Index (CVI) methodology.

---

## Overview

The plugin allows GIS technicians, coastal engineers and researchers to:

- Calculate the CVI on shoreline segment layers using four scientifically validated methods
- Receive per-island method recommendations based on peer-reviewed literature
- Visualise risk classes with an automatic green-to-red graduated symbology
- Explore results through an interactive bar chart dashboard
- Export maps (PNG), attribute tables (CSV) and summary reports (TXT)

**Spatial coverage:** Italian minor islands (Aeolian, Pontine, Pelagie, Tuscan Archipelago, Sardinian islands and more).

---

## Installation

1. Copy the `coastal_risk_dashboard/` folder to your QGIS plugins directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS/Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
2. Open QGIS → **Plugins → Manage and Install Plugins**
3. Go to **Installed** and enable **Italian Minor Islands Coastal Risk**
4. The plugin icon appears in the toolbar and the menu under Plugins

No external Python libraries are required beyond those bundled with the standard QGIS installation.

---

## Workflow

```
1. Tab DATASET
   → Use the 5-step digitisation wizard to create a shoreline layer over a
     background map (OSM or Google Satellite)
   → Or load a pre-built reference dataset (Ischia, Lipari, Lampedusa)
   → Or generate a synthetic test dataset for any of the 28 supported islands

2. Tab DATA
   → Select the shoreline layer from the QGIS project
   → Map the layer fields to CVI parameters

3. Tab CALCULATE CVI
   → Select an island to get a literature-based method recommendation
   → Choose the calculation method
   → Set constant values for parameters not in the layer (sea level rise, wave height, etc.)
   → Click Calculate

4. Tab DASHBOARD
   → View risk class distribution (bar chart with hover tooltips)
   → Read mean CVI, min/max and standard deviation
   → Click a bar to highlight the corresponding features on the map
   → Apply/toggle/reset the graduated symbology

5. Tab ONLINE DATA
   → Browse the verified data catalogue (ISPRA, Copernicus, EMODnet, TINITALY, OSM)
   → Open download pages directly in the browser
   → Or load WMS/XYZ/WFS layers directly into QGIS

6. Tab EXPORT
   → Set output folder and map title
   → Select PNG / CSV / TXT outputs
   → Click Export
```

---

## CVI Calculation Methods

| Method | Formula | Parameters | Notes |
|--------|---------|-----------|-------|
| **Gornitz (1991)** | √(G×P×U×E / 4) | 4 | Classic baseline, suitable as default |
| **USGS Thieler & Hammar-Klose (1999)** | √(G×P×SLR×Waves×Tides×ΔShoreline / 6) | 6 | Best for islands with available oceanographic data |
| **Pantusa et al. (2018)** | Weighted mean | 5 | Calibrated for the Mediterranean, recommended for volcanic islands |
| **Linear Mean** | (G+P+U+E) / N | 4 | Simple and transparent, useful for comparison |

All parameters are classified on a **1–5 scale** (1 = low risk, 5 = high risk).

### Risk Classes

| Class | CVI Range | Colour |
|-------|-----------|--------|
| Very Low | 1.0 – 1.5 | 🟢 Green |
| Low | 1.5 – 2.5 | 🟩 Light green |
| Medium | 2.5 – 3.5 | 🟡 Yellow |
| High | 3.5 – 4.5 | 🟠 Orange |
| Very High | 4.5 – 5.0 | 🔴 Red |

---

## Per-Island Method Recommendations

The plugin includes literature-based method recommendations for 12 islands:

| Island | Recommended Method | Key Reference |
|--------|-------------------|---------------|
| Lipari, Vulcano, Stromboli, Pantelleria | Pantusa (2018) | Anfuso et al. (2011) |
| Ischia | Pantusa (2018) | CNR-IRPI (2023), Fiorillo et al. (2023) |
| Lampedusa, Favignana | USGS (1999) | AMP Isole Pelagie (2022) |
| Procida, Capri | Gornitz (1991) | Budillon et al. (2018) |
| Elba | USGS (1999) | Cipriani et al. (2001) |
| Giglio, La Maddalena | Pantusa (2018) | Pranzini et al. (2015) |

---

## Output Files

| File | Contents |
|------|----------|
| `*.png` | High-resolution map (1920×1080 px) with legend, title and timestamp |
| `*.csv` | Per-feature table with CVI values, risk classes and aggregate statistics |
| `*_report.txt` | Structured text report with methodology, statistics and synthetic assessment |

---

## Data Sources

The **Online Data** tab provides links to:

- **Copernicus Data Space** — Sentinel-2 imagery for shoreline extraction (NDWI)
- **ISPRA** — Coastal erosion shapefiles, geomorphological map
- **TINITALY (INGV)** — 10m DEM for slope calculation
- **EMODnet** — Bathymetry and seabed substrate
- **Geofabrik/OSM** — Vector coastline (also via QuickOSM plugin)
- **Rete Ondametrica Nazionale (RON/ISPRA)** — Wave height data
- **Natura 2000 (MASE)** — Protected areas

---

## Plugin Structure

```
coastal_risk_dashboard/
├── core/
│   ├── cvi_engine.py            # Pipeline orchestrator
│   ├── cvi_methods.py           # Four CVI methods (Gornitz, USGS, Pantusa, Linear)
│   ├── island_method_advisor.py # Literature-based per-island recommendations
│   ├── risk_calculator.py       # CVI formula, batch processing, statistics
│   ├── shoreline_loader.py      # Layer loading, validation, attribute writing
│   ├── style_manager.py         # QGIS graduated renderer
│   ├── island_locator.py        # 28-island coordinate database and zoom
│   ├── demo_data_generator.py   # Synthetic test layer generator
│   ├── detailed_island_data.py  # Reference datasets (Ischia, Lipari, Lampedusa)
│   ├── online_data_sources.py   # Verified online data catalogue
│   └── report_exporter.py       # PNG, CSV, TXT export
├── ui/
│   ├── main_dialog.py           # Main 6-tab dialog
│   ├── dataset_tab.py           # Dataset tab with digitisation wizard
│   └── cvi_chart_widget.py      # Interactive bar chart (pure QPainter)
└── plugin_main.py               # QGIS entry point
```

---

## Known Limitations

- The reference geometries for Ischia, Lipari and Lampedusa are approximate. For technical analyses, always digitise shoreline segments directly on a high-resolution background image using the built-in wizard.
- Some WFS endpoints of Italian regional/national geoportals are unstable. The Online Data tab therefore prioritises direct download links over live WFS connections.
- The plugin is currently marked as **Experimental** while the coordinate accuracy of the reference datasets is being improved.

---

## License

GNU General Public License v2.0 or later — see [LICENSE](../LICENSE)

## Citation

If you use this plugin in academic work, please cite:

> Battaglia E. (2025). *Italian Minor Islands Coastal Risk* (v1.6). QGIS Plugin Repository. https://github.com/EleonoraB91/Coastal_Risk
