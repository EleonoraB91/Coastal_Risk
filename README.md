# Coastal Risk Dashboard — QGIS Plugin v1.5

A QGIS plugin for monitoring and assessing coastal erosion risk in the **minor Italian islands**, based on the Coastal Vulnerability Index (CVI).

---

## Overview

The Coastal Risk Dashboard allows GIS analysts, researchers, and environmental managers to:

- Load and validate coastline vector layers
- Calculate the CVI from four geomorphological and environmental parameters
- Classify coastal segments into 5 risk classes with automatic color symbology
- Navigate and zoom to any of the 28 supported Italian minor islands
- Export results as high-resolution maps (PNG), data tables (CSV), and summary reports (TXT)

> ⚠️ **Experimental plugin** — designed and tested specifically for the minor Italian islands. Input data must follow the field mapping described below.

---

## Requirements

- QGIS 3.16 or later
- A polyline or polygon vector layer representing the coastline
- Attribute fields encoding the four CVI parameters (see [CVI Parameters](#cvi-parameters))

No external Python libraries are required beyond those included with QGIS.

---

## Installation

### From the QGIS Plugin Repository (recommended)

1. Open QGIS → **Plugins → Manage and Install Plugins**
2. Search for **Coastal Risk Dashboard**
3. Click **Install**

### Manual Installation

1. Download the `.zip` file from the [releases page](https://github.com/EleonoraB91/Coastal_Risk/releases)
2. Copy the `coastal_risk_dashboard/` folder to your QGIS plugins directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS / Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Open QGIS → **Plugins → Manage and Install Plugins**
4. Go to the **Installed** tab and enable **Coastal Risk Dashboard**
5. The plugin icon will appear in the toolbar and under the **Plugins** menu

---

## Usage

The plugin is organized into four tabs:

### 1. Data Tab
- Select the coastline vector layer
- Map the four CVI parameter fields from your attribute table
- Use the **Quick Test** button to verify field values before calculating

### 2. CVI Calculation Tab
- Click **Calculate** to run the CVI formula across all features
- A real-time progress bar tracks the computation
- On completion, three new fields are added to the layer: `CVI`, `RISK`, `CVI_COLOR`
- A green-to-red graduated symbology is applied automatically

### 3. Dashboard Tab
- Select an island from the list and click **Zoom** to navigate the map canvas
- View the risk class percentage distribution and average CVI value
- Toggle and inspect layer symbology using the dedicated buttons

### 4. Export Tab
- Set an output folder and report title
- Choose one or more export formats: **PNG**, **CSV**, **TXT**
- Click **Export**

---

## CVI Parameters

The CVI is calculated from four coastal parameters, each scored on a scale of 1 (lowest vulnerability) to 5 (highest vulnerability):

| Parameter | Description | Score 1 | Score 5 |
|-----------|-------------|---------|---------|
| Geomorphology | Coastal type | Rocky cliff | Mud / marsh |
| Slope | Average coastal slope (%) | > 20% | < 1% |
| Land use | Degree of anthropization | Natural / protected | Urbanized |
| Exposure | Fetch / dominant wind exposure | Sheltered | Highly exposed |

**Formula:** `CVI = √( (G × S × L × E) / 4 )` — range: 1.0 → 5.0

### Risk Classes

| Class | CVI Range | Color |
|-------|-----------|-------|
| Very Low | 1.0 – 1.5 | 🟢 Green |
| Low | 1.5 – 2.5 | 🟩 Light green |
| Medium | 2.5 – 3.5 | 🟡 Yellow |
| High | 3.5 – 4.5 | 🟠 Orange |
| Very High | 4.5 – 5.0 | 🔴 Red |

---

## Output Files

| File | Content |
|------|---------|
| `*.png` | High-resolution map (1920×1080 px) with legend and title |
| `*.csv` | Feature-by-feature attribute table with aggregate statistics |
| `*_report.txt` | Text report including methodology summary and risk assessment |

---

## Supported Islands (auto-zoom)

The plugin includes a built-in database with geographic extents for **28 Italian minor islands**, grouped by archipelago:

- Aeolian Islands (Eolie)
- Pontine Islands (Ponziane)
- Phlegraean Islands (Flegree)
- Egadi Islands
- Pelagie Islands
- Tuscan Archipelago (Arcipelago Toscano)
- La Maddalena Archipelago
- Sulcis Islands (Isole Sulcitane)

---

## Repository Structure

```
coastal_risk_dashboard/
├── core/
│   ├── risk_calculator.py    # CVI formula, batch processing, statistics
│   ├── shoreline_loader.py   # Layer loading and validation
│   ├── cvi_engine.py         # Pipeline orchestrator
│   ├── style_manager.py      # QGIS graduated symbology
│   ├── island_locator.py     # Island database and canvas zoom
│   └── report_exporter.py    # PNG, CSV, TXT export
├── ui/
│   └── main_dialog.py        # 4-tab main dialog
├── resources/
│   └── icons/
│       └── icon.png
├── metadata.txt
├── __init__.py
├── plugin_main.py            # QGIS entry point
└── LICENSE
```

---

## Known Limitations

- The island zoom database is currently limited to the 28 minor Italian islands listed above
- The plugin has been tested primarily on Italian coastal datasets; field naming conventions may differ for other regions
- Cross-platform testing (Windows, macOS, Linux) is ongoing — please report any issues

---

## Bug Reports and Contributions

- **Bug tracker:** [GitHub Issues](https://github.com/EleonoraB91/Coastal_Risk/issues)
- **Source code:** [GitHub Repository](https://github.com/EleonoraB91/Coastal_Risk)

Contributions, suggestions, and pull requests are welcome.

---

## License

This plugin is released under the **GNU General Public License v2** (GPL v2).  
See the [LICENSE](LICENSE) file for details.
