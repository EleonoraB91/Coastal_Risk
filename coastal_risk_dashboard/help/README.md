# Coastal Risk Dashboard — Plugin QGIS v1.0

Monitoraggio del rischio da erosione costiera per le **isole minori italiane**.

---

## Installazione

1. Copia la cartella `coastal_risk_dashboard/` in:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS/Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
2. Apri QGIS → **Plugin → Gestisci e installa plugin**
3. Vai su **Installati** e attiva **Coastal Risk Dashboard**
4. L'icona compare nella toolbar e la voce nel menu Plugin

---

## Workflow completo

```
1. Tab DATI
   → Seleziona il layer vettoriale della linea di riva
   → Mappa i 4 campi dei parametri CVI
   → Usa il Test rapido per verificare i valori

2. Tab CALCOLO CVI
   → Avvia il calcolo → barra di progresso in tempo reale
   → Il layer viene aggiornato con i campi CVI, RISCHIO, CVI_COLOR
   → La simbologia verde→rosso viene applicata automaticamente

3. Tab DASHBOARD
   → Seleziona l'isola e clicca Zoom per navigare
   → Leggi distribuzione % e CVI medio
   → Controlla la simbologia con i pulsanti dedicati

4. Tab EXPORT
   → Imposta cartella e titolo
   → Seleziona PNG / CSV / TXT
   → Clicca Esporta
```

---

## Parametri CVI

| Parametro | Descrizione | Scala |
|-----------|-------------|-------|
| Geomorfologia | Tipo di costa | 1 (falesia) → 5 (fango/palude) |
| Pendenza | Pendenza media % | 1 (>20%) → 5 (<1%) |
| Uso del suolo | Antropizzazione | 1 (naturale) → 5 (urbanizzato) |
| Esposizione | Fetch / vento dominante | 1 (riparata) → 5 (molto esposta) |

**Formula:** `CVI = √( (G × P × U × E) / 4 )`  — range 1.0 → 5.0

### Classi di rischio

| Classe | Range CVI | Colore |
|--------|-----------|--------|
| Molto Basso | 1.0 – 1.5 | 🟢 Verde |
| Basso | 1.5 – 2.5 | 🟩 Verde chiaro |
| Medio | 2.5 – 3.5 | 🟡 Giallo |
| Alto | 3.5 – 4.5 | 🟠 Arancione |
| Molto Alto | 4.5 – 5.0 | 🔴 Rosso |

---

## Output prodotti

| File | Contenuto |
|------|-----------|
| `*.png` | Mappa alta risoluzione (1920×1080) con legenda e titolo |
| `*.csv` | Tabella feature-per-feature + statistiche aggregate |
| `*_report.txt` | Report testuale con metodologia e valutazione sintetica |

---

## Isole supportate (zoom automatico)

Eolie, Ponziane, Flegree, Egadi, Pelagie, Arcipelago Toscano,
Arcipelago della Maddalena, Isole Sulcitane — **28 isole in totale**.

---

## Struttura moduli

```
coastal_risk_dashboard/
├── core/
│   ├── risk_calculator.py   CVI formula, batch, statistiche
│   ├── shoreline_loader.py  Caricamento e validazione layer
│   ├── cvi_engine.py        Pipeline orchestrator
│   ├── style_manager.py     Simbologia QGIS graduata
│   ├── island_locator.py    Database isole e zoom canvas
│   └── report_exporter.py   Export PNG, CSV, TXT
├── ui/
│   └── main_dialog.py       Dashboard 4 tab
└── plugin_main.py           Entry point QGIS
```

---

## Licenza
MIT License — progetto open source
