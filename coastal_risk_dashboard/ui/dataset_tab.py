# -*- coding: utf-8 -*-
"""
ui/dataset_tab.py
Tab "📦 Dataset" — raccoglie in un unico pannello:
  1. Wizard di digitalizzazione guidata (5 step)
  2. Dataset reali georeferenziati (Ischia, Lipari, Lampedusa)
  3. Dataset sintetici di test (tutte le isole minori)
"""

import os
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QStackedWidget, QFrame, QCheckBox,
    QGridLayout, QTextEdit, QScrollArea, QSizePolicy,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont, QColor
from qgis.core import QgsProject, QgsVectorLayer, QgsApplication


class DatasetTab(QWidget):
    """
    Tab Dataset completo.

    Segnali:
        layer_loaded(QgsVectorLayer)  — emesso ogni volta che un layer viene caricato
    """

    layer_loaded = pyqtSignal(object)   # QgsVectorLayer

    # Indici step wizard
    WIZARD_STEPS = [
        ("1", "Scegli isola",       "Seleziona l'isola su cui lavorare e carica una mappa di sfondo."),
        ("2", "Crea il layer",      "Crea un nuovo layer vettoriale LineString in QGIS."),
        ("3", "Disegna i tratti",   "Digitalizza i tratti costieri sopra la mappa di sfondo."),
        ("4", "Compila parametri",  "Aggiungi i campi CVI e valorizza ogni tratto."),
        ("5", "Verifica e carica",  "Verifica la geometria e carica il layer nel plugin."),
    ]

    def __init__(self, iface, locator, detailed, demo_gen, styler, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.locator = locator
        self.detailed = detailed
        self.demo_gen = demo_gen
        self.styler = styler

        self._current_wizard_step = 0
        self._build_ui()

    # ------------------------------------------------------------------
    # Costruzione UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # Tre pannelli orizzontali scorribili
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)

        layout.addWidget(self._build_wizard_panel())
        layout.addWidget(self._build_real_data_panel())
        layout.addWidget(self._build_demo_panel())
        layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Pannello 1: Wizard
    # ------------------------------------------------------------------

    def _build_wizard_panel(self) -> QGroupBox:
        group = QGroupBox("🧭 Wizard — Digitalizzazione guidata dei tratti costieri")
        group.setStyleSheet(
            "QGroupBox { border: 2px solid #7b4fa6; border-radius: 6px; "
            "margin-top: 8px; font-weight: bold; color: #4a2a6a; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; }"
        )
        layout = QVBoxLayout(group)

        # Intestazione
        intro = QLabel(
            "Segui questi 5 passaggi per creare il tuo layer di tratti costieri "
            "direttamente in QGIS, con la precisione di un'ortofoto come sfondo."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #4a2a6a; font-size: 10px; padding-bottom: 6px;")
        layout.addWidget(intro)

        # Barra step (numeretti colorati)
        step_bar = QHBoxLayout()
        self._step_buttons = []
        for i, (num, title, _) in enumerate(self.WIZARD_STEPS):
            btn = QPushButton(f" {num} ")
            btn.setFixedSize(32, 32)
            btn.setToolTip(title)
            btn.clicked.connect(lambda checked, idx=i: self._go_to_step(idx))
            self._step_buttons.append(btn)
            step_bar.addWidget(btn)
            if i < len(self.WIZARD_STEPS) - 1:
                arrow = QLabel("→")
                arrow.setAlignment(Qt.AlignCenter)
                arrow.setStyleSheet("color: #9e9e9e; font-size: 14px;")
                step_bar.addWidget(arrow)
        step_bar.addStretch()
        layout.addLayout(step_bar)

        # Contenuto step (QStackedWidget)
        self._wizard_stack = QStackedWidget()
        self._wizard_stack.addWidget(self._wizard_step_0())
        self._wizard_stack.addWidget(self._wizard_step_1())
        self._wizard_stack.addWidget(self._wizard_step_2())
        self._wizard_stack.addWidget(self._wizard_step_3())
        self._wizard_stack.addWidget(self._wizard_step_4())
        layout.addWidget(self._wizard_stack)

        # Navigazione
        nav_row = QHBoxLayout()
        self.btn_wizard_prev = QPushButton("◀  Indietro")
        self.btn_wizard_prev.setEnabled(False)
        self.btn_wizard_prev.clicked.connect(self._wizard_prev)
        self.btn_wizard_next = QPushButton("Avanti  ▶")
        self.btn_wizard_next.setStyleSheet(
            "QPushButton { background: #7b4fa6; color: white; border-radius: 4px; "
            "font-weight: bold; padding: 4px 12px; }"
            "QPushButton:hover { background: #5a3a8a; }"
        )
        self.btn_wizard_next.clicked.connect(self._wizard_next)
        nav_row.addWidget(self.btn_wizard_prev)
        nav_row.addStretch()
        self.wizard_step_label = QLabel("Passo 1 di 5")
        self.wizard_step_label.setStyleSheet("color: #666; font-size: 10px;")
        nav_row.addWidget(self.wizard_step_label)
        nav_row.addStretch()
        nav_row.addWidget(self.btn_wizard_next)
        layout.addLayout(nav_row)

        self._update_wizard_step_ui()
        return group

    # ------------------------------------------------------------------
    # Step 0 — Scegli isola e sfondo
    # ------------------------------------------------------------------

    def _wizard_step_0(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._step_header(
            "Passo 1 — Scegli l'isola e carica la mappa di sfondo",
            "Seleziona l'isola su cui vuoi lavorare. "
            "Il plugin zoomera automaticamente sull'area corretta."
        ))

        row = QHBoxLayout()
        row.addWidget(QLabel("Isola:"))
        self.wizard_island_combo = QComboBox()
        for name in self.locator.island_names():
            info = self.locator.get_info(name)
            reg = info.get("regione", "") if info else ""
            self.wizard_island_combo.addItem(f"{name}  ({reg})", name)
        row.addWidget(self.wizard_island_combo, 1)
        lay.addLayout(row)

        btn_zoom = QPushButton("🔍  Zoom sull'isola selezionata")
        btn_zoom.clicked.connect(self._wizard_zoom)
        lay.addWidget(btn_zoom)

        lay.addWidget(self._tip_box(
            "💡 Sfondo consigliato",
            "In QGIS vai su:\n"
            "  Browser → XYZ Tiles → OpenStreetMap (trascina nella mappa)\n"
            "  oppure\n"
            "  Browser → XYZ Tiles → Google Satellite\n\n"
            "Se non vedi XYZ Tiles nel Browser:\n"
            "  Browser (tasto destro) → Nuovo → Connessione XYZ\n"
            "  URL: https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}\n"
            "  Nome: Google Satellite"
        ))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Step 1 — Crea il layer
    # ------------------------------------------------------------------

    def _wizard_step_1(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._step_header(
            "Passo 2 — Crea un nuovo layer vettoriale",
            "Crea in QGIS il layer su cui disegnerai i tratti costieri."
        ))

        btn_create = QPushButton("⚙️  Crea layer 'Tratti_Costieri' automaticamente")
        btn_create.setMinimumHeight(36)
        btn_create.setStyleSheet(
            "QPushButton { background: #1a3a5c; color: white; border-radius: 4px; "
            "font-weight: bold; }"
            "QPushButton:hover { background: #2a5a8c; }"
        )
        btn_create.clicked.connect(self._wizard_create_layer)
        lay.addWidget(btn_create)

        self.wizard_create_result = QLabel("")
        self.wizard_create_result.setWordWrap(True)
        self.wizard_create_result.setStyleSheet("font-size: 10px; color: #1a7a3a;")
        lay.addWidget(self.wizard_create_result)

        lay.addWidget(self._tip_box(
            "💡 In alternativa — manualmente",
            "Layer → Crea layer → Nuovo Shapefile Layer\n"
            "  • Tipo di geometria: LineString\n"
            "  • CRS: EPSG:4326 (WGS 84)\n"
            "  • Nome file: Tratti_Costieri.shp\n\n"
            "Aggiungi questi campi:\n"
            "  GEOMORF   (Numero decimale)\n"
            "  PENDENZA  (Numero decimale)\n"
            "  USO_SUOLO (Numero decimale)\n"
            "  ESPOSIZ   (Numero decimale)\n"
            "  TRATTO    (Testo, lunghezza 100)"
        ))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Step 2 — Digitalizza
    # ------------------------------------------------------------------

    def _wizard_step_2(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._step_header(
            "Passo 3 — Disegna i tratti costieri",
            "Attiva la modalità di editing e digitalizza ogni tratto costiero."
        ))

        btn_edit = QPushButton("✏️  Attiva editing sul layer Tratti_Costieri")
        btn_edit.clicked.connect(self._wizard_start_editing)
        lay.addWidget(btn_edit)

        lay.addWidget(self._tip_box(
            "💡 Come digitalizzare bene",
            "1. Seleziona il layer Tratti_Costieri nel pannello Layer\n"
            "2. Clicca il pulsante matita (✏️) nella toolbar, oppure usa il pulsante sopra\n"
            "3. Nella toolbar di editing → 'Aggiungi elemento linea' (icona linea spezzata)\n"
            "4. Clicca sulla mappa per aggiungere i vertici del tratto\n"
            "5. Tasto destro per terminare ogni tratto\n\n"
            "📌 Suggerimento: dividi la costa in tratti omogenei\n"
            "   (es. un tratto per ogni tipo di costa: porto, spiaggia, falesia…)\n"
            "   Tratti di 200–500m sono una buona granularità."
        ))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Step 3 — Compila parametri
    # ------------------------------------------------------------------

    def _wizard_step_3(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._step_header(
            "Passo 4 — Compila i parametri CVI per ogni tratto",
            "Apri la tabella attributi e valorizza i 4 campi parametro "
            "per ogni tratto che hai disegnato."
        ))

        btn_table = QPushButton("📋  Apri tabella attributi del layer")
        btn_table.clicked.connect(self._wizard_open_table)
        lay.addWidget(btn_table)

        lay.addWidget(self._tip_box(
            "💡 Guida ai valori",
            "GEOMORF — tipo di costa:\n"
            "  1 = Falesia rocciosa alta (>10m)\n"
            "  2 = Costa rocciosa bassa / scogliera\n"
            "  3 = Spiaggia sabbiosa o ghiaiosa\n"
            "  4 = Dune basse / cordone sabbioso\n"
            "  5 = Costa bassa fangosa / paludosa / lagunare\n\n"
            "PENDENZA — pendenza media del tratto costiero:\n"
            "  1 = > 20%  |  2 = 10–20%  |  3 = 5–10%  |  4 = 1–5%  |  5 = < 1%\n\n"
            "USO_SUOLO — grado di antropizzazione:\n"
            "  1 = Naturale / area protetta  |  3 = Agricolo  |  5 = Urbano denso\n\n"
            "ESPOSIZ — esposizione al vento / fetch:\n"
            "  1 = Costa riparata  |  3 = Moderatamente esposta  |  5 = Molto esposta"
        ))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Step 4 — Verifica e carica
    # ------------------------------------------------------------------

    def _wizard_step_4(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        lay.addWidget(self._step_header(
            "Passo 5 — Verifica e carica nel plugin",
            "Salva il layer, verifica che i campi siano corretti e caricalo."
        ))

        btn_save = QPushButton("💾  Salva modifiche al layer")
        btn_save.clicked.connect(self._wizard_save_layer)
        lay.addWidget(btn_save)

        btn_validate = QPushButton("✅  Verifica layer (geometria + campi)")
        btn_validate.clicked.connect(self._wizard_validate_layer)
        lay.addWidget(btn_validate)

        self.wizard_validate_result = QTextEdit()
        self.wizard_validate_result.setReadOnly(True)
        self.wizard_validate_result.setMaximumHeight(80)
        self.wizard_validate_result.setStyleSheet(
            "background: #f8f9fa; border: 1px solid #dee2e6; "
            "border-radius: 4px; font-family: monospace; font-size: 9px;"
        )
        lay.addWidget(self.wizard_validate_result)

        btn_load = QPushButton("🚀  Carica nel plugin e vai al tab Dati")
        btn_load.setMinimumHeight(38)
        btn_load.setStyleSheet(
            "QPushButton { background: #1a7a3a; color: white; border-radius: 4px; "
            "font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: #145c2c; }"
        )
        btn_load.clicked.connect(self._wizard_load_to_plugin)
        lay.addWidget(btn_load)

        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Pannello 2: Dati reali
    # ------------------------------------------------------------------

    def _build_real_data_panel(self) -> QGroupBox:
        group = QGroupBox("📍 Dataset reali — Ischia, Lipari, Lampedusa")
        group.setStyleSheet(
            "QGroupBox { border: 2px solid #1a7a3a; border-radius: 6px; "
            "margin-top: 8px; font-weight: bold; color: #1a4a2a; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; }"
        )
        layout = QVBoxLayout(group)

        desc = QLabel(
            "Tratti costieri con parametri CVI derivati da ISPRA, CNR-IRPI, "
            "CoastSat e CTR regionali. Utili come riferimento metodologico. "
            "⚠️ Le geometrie sono approssimative — per analisi precise usa il wizard."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #2d4a2d; font-size: 10px; padding-bottom: 4px;")
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.addWidget(QLabel("Isola:"))
        self.real_island_combo = QComboBox()
        for name in self.detailed.available_islands():
            self.real_island_combo.addItem(name, name)
        self.real_island_combo.currentIndexChanged.connect(self._update_real_preview)
        row.addWidget(self.real_island_combo, 1)

        btn_load = QPushButton("📍 Carica")
        btn_load.setFixedWidth(80)
        btn_load.setStyleSheet(
            "QPushButton { background: #1a7a3a; color: white; border-radius: 4px; "
            "font-weight: bold; }"
            "QPushButton:hover { background: #145c2c; }"
        )
        btn_load.clicked.connect(self._load_real_dataset)
        row.addWidget(btn_load)

        btn_clear = QPushButton("🗑️")
        btn_clear.setFixedWidth(36)
        btn_clear.setToolTip("Rimuovi layer [REALE]")
        btn_clear.clicked.connect(self._clear_real_layers)
        row.addWidget(btn_clear)
        layout.addLayout(row)

        self.real_preview_label = QLabel("")
        self.real_preview_label.setWordWrap(True)
        self.real_preview_label.setStyleSheet(
            "color: #1a4a2a; font-size: 9px; font-style: italic;"
        )
        layout.addWidget(self.real_preview_label)
        self._update_real_preview()

        self.real_result_label = QLabel("")
        self.real_result_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.real_result_label)

        return group

    # ------------------------------------------------------------------
    # Pannello 3: Demo
    # ------------------------------------------------------------------

    def _build_demo_panel(self) -> QGroupBox:
        group = QGroupBox("🧪 Dataset sintetico — Test rapido")
        group.setStyleSheet(
            "QGroupBox { border: 2px dashed #2a7abf; border-radius: 6px; "
            "margin-top: 8px; font-weight: bold; color: #1a3a5c; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; }"
        )
        layout = QVBoxLayout(group)

        desc = QLabel(
            "Genera un layer sintetico (ellisse approssimativa) per esplorare "
            "il plugin senza dati reali. Non adatto ad analisi tecniche."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #444; font-size: 10px; padding-bottom: 4px;")
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.addWidget(QLabel("Isola:"))
        self.demo_island_combo = QComboBox()
        detailed = self.demo_gen.available_islands()
        for name in detailed:
            info = self.locator.get_info(name)
            reg = info.get("regione", "") if info else ""
            self.demo_island_combo.addItem(f"⭐ {name}  ({reg})", name)
        self.demo_island_combo.insertSeparator(len(detailed))
        for name in self.locator.island_names():
            if name not in detailed:
                info = self.locator.get_info(name)
                reg = info.get("regione", "") if info else ""
                self.demo_island_combo.addItem(f"{name}  ({reg})", name)
        self.demo_island_combo.currentIndexChanged.connect(self._update_demo_preview)
        row.addWidget(self.demo_island_combo, 1)

        self.demo_noise_chk = QCheckBox("Variazione")
        self.demo_noise_chk.setChecked(True)
        self.demo_noise_chk.setToolTip("Aggiunge variazione casuale ai parametri")
        row.addWidget(self.demo_noise_chk)

        btn_gen = QPushButton("⚡ Genera")
        btn_gen.setFixedWidth(80)
        btn_gen.setStyleSheet(
            "QPushButton { background: #2a7abf; color: white; border-radius: 4px; "
            "font-weight: bold; }"
            "QPushButton:hover { background: #1a5a9f; }"
        )
        btn_gen.clicked.connect(self._generate_demo_layer)
        row.addWidget(btn_gen)

        btn_clear = QPushButton("🗑️")
        btn_clear.setFixedWidth(36)
        btn_clear.setToolTip("Rimuovi layer [DEMO]")
        btn_clear.clicked.connect(self._clear_demo_layers)
        row.addWidget(btn_clear)
        layout.addLayout(row)

        self.demo_preview_label = QLabel("")
        self.demo_preview_label.setStyleSheet(
            "color: #1a3a5c; font-size: 9px; font-style: italic;"
        )
        layout.addWidget(self.demo_preview_label)
        self._update_demo_preview()

        self.demo_result_label = QLabel("")
        self.demo_result_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.demo_result_label)

        return group

    # ------------------------------------------------------------------
    # Helper widget
    # ------------------------------------------------------------------

    def _step_header(self, title: str, subtitle: str) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            "background: #f3eeff; border-radius: 5px; padding: 4px;"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(8, 6, 8, 6)
        t = QLabel(f"<b>{title}</b>")
        t.setWordWrap(True)
        t.setStyleSheet("color: #4a2a6a; font-size: 11px;")
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setStyleSheet("color: #6a4a8a; font-size: 10px;")
        lay.addWidget(t)
        lay.addWidget(s)
        return frame

    def _tip_box(self, title: str, body: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #fffde7; border: 1px solid #f9a825; "
            "border-radius: 5px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(8, 6, 8, 6)
        t = QLabel(f"<b>{title}</b>")
        t.setStyleSheet("color: #e65100; font-size: 10px;")
        b = QLabel(body)
        b.setWordWrap(True)
        b.setStyleSheet("color: #4e342e; font-size: 9px; font-family: monospace;")
        lay.addWidget(t)
        lay.addWidget(b)
        return frame

    # ------------------------------------------------------------------
    # Wizard logic
    # ------------------------------------------------------------------

    def _go_to_step(self, idx: int):
        self._current_wizard_step = idx
        self._wizard_stack.setCurrentIndex(idx)
        self._update_wizard_step_ui()

    def _wizard_prev(self):
        if self._current_wizard_step > 0:
            self._go_to_step(self._current_wizard_step - 1)

    def _wizard_next(self):
        n = len(self.WIZARD_STEPS)
        if self._current_wizard_step < n - 1:
            self._go_to_step(self._current_wizard_step + 1)

    def _update_wizard_step_ui(self):
        n = len(self.WIZARD_STEPS)
        step = self._current_wizard_step
        self.btn_wizard_prev.setEnabled(step > 0)
        self.btn_wizard_next.setEnabled(step < n - 1)
        self.btn_wizard_next.setText("Fine ✅" if step == n - 1 else "Avanti  ▶")
        self.wizard_step_label.setText(f"Passo {step + 1} di {n}")

        # Colora i numeretti step
        for i, btn in enumerate(self._step_buttons):
            if i < step:
                btn.setStyleSheet(
                    "QPushButton { background: #2ecc71; color: white; border-radius: 14px; "
                    "font-weight: bold; border: none; }"
                )
            elif i == step:
                btn.setStyleSheet(
                    "QPushButton { background: #7b4fa6; color: white; border-radius: 14px; "
                    "font-weight: bold; border: none; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #e0e0e0; color: #888; border-radius: 14px; "
                    "border: none; }"
                )

    def _wizard_zoom(self):
        name = self.wizard_island_combo.currentData()
        if name:
            self.locator.zoom_to(name)

    def _wizard_create_layer(self):
        """Crea un layer LineString in-memory con i campi CVI preconfigurati."""
        from qgis.core import QgsVectorLayer, QgsField, QgsProject
        from qgis.PyQt.QtCore import QVariant

        layer = QgsVectorLayer(
            "LineString?crs=EPSG:4326&field=GEOMORF:double&field=PENDENZA:double"
            "&field=USO_SUOLO:double&field=ESPOSIZ:double&field=TRATTO:string(100)",
            "Tratti_Costieri",
            "memory"
        )
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            self.wizard_create_result.setText(
                "✅ Layer 'Tratti_Costieri' creato e aggiunto al progetto.\n"
                "Vai al passo 3 per iniziare a disegnare."
            )
            self.layer_loaded.emit(layer)
        else:
            self.wizard_create_result.setText("❌ Creazione layer fallita.")

    def _wizard_start_editing(self):
        """Attiva editing sul layer Tratti_Costieri."""
        layer = self._find_tratti_layer()
        if layer:
            layer.startEditing()
            self.iface.setActiveLayer(layer)
            # Attiva lo strumento linea
            self.iface.actionAddFeature().trigger()
        else:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Layer non trovato",
                "Non trovo il layer 'Tratti_Costieri'. "
                "Torna al passo 2 e crea il layer prima."
            )

    def _wizard_open_table(self):
        """Apre la tabella attributi del layer Tratti_Costieri."""
        layer = self._find_tratti_layer()
        if layer:
            self.iface.showAttributeTable(layer)

    def _wizard_save_layer(self):
        """Salva le modifiche al layer."""
        layer = self._find_tratti_layer()
        if layer and layer.isEditable():
            layer.commitChanges()

    def _wizard_validate_layer(self):
        """Verifica geometria e campi del layer."""
        self.wizard_validate_result.clear()

        layer = self._find_tratti_layer()
        if layer is None:
            self.wizard_validate_result.append("❌ Layer 'Tratti_Costieri' non trovato.")
            return

        msgs = []
        n = layer.featureCount()
        msgs.append(f"✅ Layer trovato: {n} tratti")

        required = ["GEOMORF", "PENDENZA", "USO_SUOLO", "ESPOSIZ"]
        field_names = [f.name() for f in layer.fields()]
        for f in required:
            if f in field_names:
                msgs.append(f"✅ Campo {f} presente")
            else:
                msgs.append(f"❌ Campo {f} MANCANTE")

        # Controlla valori fuori range
        out_range = 0
        for feat in layer.getFeatures():
            for f in required:
                if f in field_names:
                    try:
                        v = float(feat[f] or 0)
                        if not (1.0 <= v <= 5.0):
                            out_range += 1
                    except (TypeError, ValueError):
                        out_range += 1
        if out_range == 0:
            msgs.append("✅ Tutti i valori parametro nel range 1–5")
        else:
            msgs.append(f"⚠️ {out_range} valori fuori range 1–5 (verranno sostituiti con 3.0)")

        for m in msgs:
            self.wizard_validate_result.append(m)

    def _wizard_load_to_plugin(self):
        """Emette il segnale con il layer pronto."""
        layer = self._find_tratti_layer()
        if layer:
            self.layer_loaded.emit(layer)
        else:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Nessun layer",
                "Non trovo il layer 'Tratti_Costieri'.\n"
                "Crea e compila il layer seguendo i passi del wizard."
            )

    def _find_tratti_layer(self):
        """Cerca il layer 'Tratti_Costieri' nel progetto."""
        for layer in QgsProject.instance().mapLayers().values():
            if "Tratti_Costieri" in layer.name():
                return layer
        return None

    # ------------------------------------------------------------------
    # Slot dati reali
    # ------------------------------------------------------------------

    def _update_real_preview(self, index=None):
        from ..core.detailed_island_data import DETAILED_ISLANDS
        name = self.real_island_combo.currentData()
        info = DETAILED_ISLANDS.get(name) if name else None
        if not info:
            return
        n = len(info["tratti"])
        fonti = ", ".join(info["fonti"])
        self.real_preview_label.setText(
            f"{n} tratti  |  {info['anno_riferimento']}  |  {fonti}"
        )

    def _load_real_dataset(self):
        name = self.real_island_combo.currentData()
        if not name:
            return
        layer = self.detailed.generate(name)
        if layer:
            QgsProject.instance().addMapLayer(layer)
            self.styler.apply_cvi_style(layer)
            base_name = name.replace(" (dati reali)", "")
            self.locator.zoom_to(base_name)
            self.real_result_label.setText(
                f"✅ {layer.featureCount()} tratti caricati."
            )
            self.real_result_label.setStyleSheet("color: #1a7a3a; font-size: 10px;")
            self.layer_loaded.emit(layer)

    def _clear_real_layers(self):
        to_remove = [
            lid for lid, lyr in QgsProject.instance().mapLayers().items()
            if lyr.name().startswith("[REALE]")
        ]
        QgsProject.instance().removeMapLayers(to_remove)
        self.real_result_label.setText("")

    # ------------------------------------------------------------------
    # Slot demo
    # ------------------------------------------------------------------

    def _update_demo_preview(self, index=None):
        from ..core.demo_data_generator import ISLAND_PROFILES, DEFAULT_PROFILE
        name = self.demo_island_combo.currentData()
        if not name:
            return
        profile = ISLAND_PROFILES.get(name, DEFAULT_PROFILE)
        from ..core.demo_data_generator import ISLAND_PROFILES as IP
        badge = "⭐ dettagliato" if name in IP else "generico"
        self.demo_preview_label.setText(
            f"{len(profile)} tratti  ({badge})"
        )

    def _generate_demo_layer(self):
        name = self.demo_island_combo.currentData()
        if not name:
            return
        bbox = self.locator.get_bbox(name)
        if not bbox:
            return
        add_noise = self.demo_noise_chk.isChecked()
        try:
            layer = self.demo_gen.generate(name, bbox, add_noise=add_noise)
            QgsProject.instance().addMapLayer(layer)
            self.styler.apply_cvi_style(layer)
            self.locator.zoom_to(name)
            self.demo_result_label.setText(
                f"✅ {layer.featureCount()} tratti generati."
            )
            self.demo_result_label.setStyleSheet("color: #2a7abf; font-size: 10px;")
            self.layer_loaded.emit(layer)
        except Exception as e:
            self.demo_result_label.setText(f"❌ {e}")

    def _clear_demo_layers(self):
        to_remove = [
            lid for lid, lyr in QgsProject.instance().mapLayers().items()
            if lyr.name().startswith("[DEMO]")
        ]
        QgsProject.instance().removeMapLayers(to_remove)
        self.demo_result_label.setText("")
