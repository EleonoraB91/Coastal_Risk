# -*- coding: utf-8 -*-
"""
ui/main_dialog.py
Main dialog — Italian Minor Islands Coastal Risk.
Fase 1: struttura base con pannelli placeholder pronti per le fasi successive.
"""

import os
import re
import datetime
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QComboBox,
    QGroupBox, QGridLayout, QSizePolicy, QSpacerItem,
    QProgressBar, QFrame, QMessageBox, QDoubleSpinBox,
    QTextEdit, QFileDialog, QLineEdit, QCheckBox
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QFont, QColor, QPalette
from qgis.core import QgsProject, QgsMapLayer

from ..core.cvi_engine import CVIEngine
from ..core.risk_calculator import CVIStats
from ..core.style_manager import StyleManager
from ..core.island_locator import IslandLocator
from ..core.report_exporter import ReportExporter
from ..core.demo_data_generator import DemoDataGenerator
from ..core.online_data_connector import OnlineDataConnector
from ..core.detailed_island_data import DetailedIslandDataset
from ..core.cvi_methods import CVIMethodEngine, ALL_METHODS
from ..core.island_method_advisor import IslandMethodAdvisor
from .cvi_chart_widget import CVIChartWidget
from .dataset_tab import DatasetTab


class MainDialog(QDialog):
    """Finestra principale del plugin."""

    # Palette colori rischio
    RISK_COLORS = {
        "Molto Basso":  "#2ecc71",
        "Basso":        "#a8d08d",
        "Medio":        "#f1c40f",
        "Alto":         "#e67e22",
        "Molto Alto":   "#e74c3c",
    }

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.engine = CVIEngine(iface)
        self.styler = StyleManager()
        self.locator = IslandLocator(iface)
        self.exporter = ReportExporter(iface)
        self.demo_gen = DemoDataGenerator()
        self.connector = OnlineDataConnector(iface)
        self.detailed = DetailedIslandDataset()
        self.method_engine = CVIMethodEngine("gornitz_1991")
        self.advisor = IslandMethodAdvisor()
        self.field_map = {
            "geomorfologia": "",
            "pendenza":      "",
            "uso_suolo":     "",
            "esposizione":   "",
        }
        self.setWindowTitle("🌊 Italian Minor Islands Coastal Risk — CVI Dashboard")
        self.setMinimumSize(720, 580)
        self.resize(860, 700)
        self._build_ui()

    # ------------------------------------------------------------------
    # Costruzione UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Assembla il layout principale."""
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # Header
        root.addWidget(self._make_header())

        # Tab widget principale
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_dashboard(),     "📊 Dashboard")
        self.tabs.addTab(self._tab_data(),          "📂 Dati")
        self.tabs.addTab(self._tab_cvi(),           "🧮 Calcolo CVI")
        self.tabs.addTab(self._tab_dataset(),       "📦 Dataset")
        self.tabs.addTab(self._tab_online_data(),   "🌐 Dati online")
        self.tabs.addTab(self._tab_export(),        "💾 Export")
        root.addWidget(self.tabs)

        # Barra di stato
        root.addWidget(self._make_statusbar())

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _make_header(self):
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #1a3a5c; border-radius: 6px; padding: 4px;"
        )
        layout = QHBoxLayout(frame)

        title = QLabel("🌊 Italian Minor Islands Coastal Risk")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: white;")

        subtitle = QLabel("Monitoraggio erosione costiera — Isole Minori Italiane")
        subtitle.setStyleSheet("color: #a8c8e8; font-size: 10px;")
        subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(subtitle)
        return frame

    # ------------------------------------------------------------------
    # Tab: Dashboard
    # ------------------------------------------------------------------

    def _tab_dashboard(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        # ── Navigazione isola ─────────────────────────────────────────
        sel_group = QGroupBox("Navigazione isola")
        sel_layout = QGridLayout(sel_group)
        self.island_combo = QComboBox()
        self.island_combo.addItem("-- Seleziona un'isola --")
        for name in self.locator.island_names():
            info = self.locator.get_info(name)
            display = f"{name}  ({info.get('regione', '?')})"
            self.island_combo.addItem(display, name)
        self.island_combo.currentIndexChanged.connect(self._on_island_changed)
        sel_layout.addWidget(QLabel("Isola:"), 0, 0)
        sel_layout.addWidget(self.island_combo, 0, 1)

        btn_zoom = QPushButton("🔍 Zoom")
        btn_zoom.setToolTip("Zoom all'isola selezionata")
        btn_zoom.clicked.connect(self._zoom_to_island)
        sel_layout.addWidget(btn_zoom, 0, 2)

        btn_overview = QPushButton("🗺️ Vista globale")
        btn_overview.setToolTip("Mostra tutte le isole minori italiane")
        btn_overview.clicked.connect(self._zoom_overview)
        sel_layout.addWidget(btn_overview, 0, 3)

        self.island_info_label = QLabel("")
        self.island_info_label.setStyleSheet("color: #555; font-style: italic; font-size: 10px;")
        sel_layout.addWidget(self.island_info_label, 1, 0, 1, 4)
        layout.addWidget(sel_group)

        # ── Layout a due colonne: box + grafico ───────────────────────
        mid_row = QHBoxLayout()
        mid_row.setSpacing(8)

        # Colonna sinistra: box statistiche + barra CVI
        left_col = QVBoxLayout()
        left_col.setSpacing(6)

        # Box colorati 5 classi
        stats_group = QGroupBox("Tratti per classe")
        stats_grid = QGridLayout(stats_group)
        stats_grid.setSpacing(4)
        self.risk_labels = {}
        self.risk_count_labels = {}
        for i, (label, color) in enumerate(self.RISK_COLORS.items()):
            box = self._make_risk_box(label, color, "—")
            self.risk_labels[label] = box["value"]
            stats_grid.addWidget(box["frame"], 0, i)
        left_col.addWidget(stats_group)

        # Barra CVI medio
        cvi_group = QGroupBox("Indice CVI medio del layer")
        cvi_layout = QVBoxLayout(cvi_group)
        self.cvi_bar = QProgressBar()
        self.cvi_bar.setRange(0, 100)
        self.cvi_bar.setValue(0)
        self.cvi_bar.setFormat("CVI: non calcolato")
        self.cvi_bar.setStyleSheet(
            "QProgressBar { height: 28px; border-radius: 4px; font-weight: bold; }"
            "QProgressBar::chunk { background-color: #e67e22; border-radius: 4px; }"
        )
        cvi_layout.addWidget(self.cvi_bar)

        # Dettaglio statistiche sotto la barra
        self.cvi_detail_label = QLabel("")
        self.cvi_detail_label.setStyleSheet(
            "color: #546e7a; font-size: 9px; padding: 2px 4px;"
        )
        self.cvi_detail_label.setAlignment(Qt.AlignCenter)
        cvi_layout.addWidget(self.cvi_detail_label)
        left_col.addWidget(cvi_group)

        # Simbologia
        style_group = QGroupBox("Simbologia layer")
        style_layout = QHBoxLayout(style_group)
        btn_apply_style   = QPushButton("🎨 Stile CVI")
        btn_toggle_labels = QPushButton("🏷️ Etichette")
        btn_reset_style   = QPushButton("↺ Reset")
        btn_apply_style.clicked.connect(self._apply_style)
        btn_toggle_labels.clicked.connect(self._toggle_labels)
        btn_reset_style.clicked.connect(self._reset_style)
        for btn in [btn_apply_style, btn_toggle_labels, btn_reset_style]:
            btn.setMinimumHeight(30)
            style_layout.addWidget(btn)
        left_col.addWidget(style_group)

        mid_row.addLayout(left_col, 55)

        # Colonna destra: grafico a barre
        chart_group = QGroupBox("📊 Distribuzione classi di rischio")
        chart_group.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #1a3a5c; "
            "border: 1px solid #c8d8e8; border-radius: 6px; margin-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; }"
        )
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.setContentsMargins(4, 8, 4, 4)

        self.cvi_chart = CVIChartWidget()
        self.cvi_chart.setMinimumHeight(190)
        self.cvi_chart.bar_clicked.connect(self._on_chart_bar_clicked)
        chart_layout.addWidget(self.cvi_chart)

        # Info click sulla barra
        self.chart_detail_label = QLabel("Clicca una barra per filtrare le feature nel layer")
        self.chart_detail_label.setStyleSheet(
            "color: #78909c; font-size: 9px; font-style: italic; padding: 2px;"
        )
        self.chart_detail_label.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(self.chart_detail_label)

        mid_row.addWidget(chart_group, 45)
        layout.addLayout(mid_row)

        layout.addStretch()
        return widget

    def _make_risk_box(self, label, color, value_text):
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {color}22; border: 2px solid {color}; "
            f"border-radius: 6px; padding: 6px;"
        )
        vbox = QVBoxLayout(frame)
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        val = QLabel(value_text)
        val.setAlignment(Qt.AlignCenter)
        val.setFont(QFont("Segoe UI", 16, QFont.Bold))
        val.setStyleSheet(f"color: {color};")
        vbox.addWidget(lbl)
        vbox.addWidget(val)
        return {"frame": frame, "value": val}

    # ------------------------------------------------------------------
    # Tab: Dati
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Tab: Dati
    # ------------------------------------------------------------------

    def _tab_data(self):
        from qgis.PyQt.QtWidgets import QFormLayout
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        # ── Layer selezionato ─────────────────────────────────────────
        shore_group = QGroupBox("📌 Layer linea di riva")
        shore_layout = QGridLayout(shore_group)

        shore_layout.addWidget(QLabel("Layer:"), 0, 0)
        self.shore_combo = QComboBox()
        self._populate_layer_combo(self.shore_combo)
        shore_layout.addWidget(self.shore_combo, 0, 1)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setFixedWidth(36)
        btn_refresh.setToolTip("Aggiorna lista layer dal progetto QGIS")
        btn_refresh.clicked.connect(self._refresh_all_combos)
        shore_layout.addWidget(btn_refresh, 0, 2)

        self.feat_count_label = QLabel("— feature")
        self.feat_count_label.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        shore_layout.addWidget(self.feat_count_label, 1, 1)
        self.shore_combo.currentIndexChanged.connect(self._on_shore_layer_changed)
        layout.addWidget(shore_group)

        # ── Mappatura campi → parametri ───────────────────────────────
        params_group = QGroupBox("🔗 Mappatura campi → parametri CVI")
        params_outer = QVBoxLayout(params_group)

        method_note = QLabel(
            "ℹ️  I parametri variano in base al metodo scelto nel tab 🧮 Calcolo CVI. "
            "Per i parametri senza campo nel layer, usa i valori costanti nel tab Calcolo CVI."
        )
        method_note.setWordWrap(True)
        method_note.setStyleSheet(
            "background: #fffde7; border: 1px solid #f9a825; border-radius: 4px; "
            "padding: 6px; color: #4e342e; font-size: 9px;"
        )
        params_outer.addWidget(method_note)

        self._params_form_widget = QWidget()
        self._params_layout = QFormLayout(self._params_form_widget)
        self._params_layout.setSpacing(5)
        self._params_layout.setLabelAlignment(Qt.AlignRight)
        self._params_layout.addRow(
            QLabel("<b>Parametro</b>"),
            QLabel("<b>Campo nel layer  ·  Scala di riferimento</b>"),
        )

        # Popola con il metodo default (Gornitz)
        self._param_field_combos = {}
        self.field_map = {
            "geomorfologia": "", "pendenza": "",
            "uso_suolo": "",    "esposizione": "",
        }
        from ..core.cvi_methods import METHOD_GORNITZ
        for param in METHOD_GORNITZ.params:
            cb = QComboBox()
            cb.addItem("-- non assegnato --", "")
            self._populate_field_combo(cb, None)
            cb.currentIndexChanged.connect(
                lambda idx, k=param.key, c=cb: self._on_field_mapped(k, c)
            )
            self._param_field_combos[param.key] = cb
            scale_lbl = QLabel(param.scale_desc)
            scale_lbl.setStyleSheet("color: #777; font-size: 9px;")
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.addWidget(cb, 1)
            row_l.addWidget(scale_lbl)
            self._params_layout.addRow(f"{param.label}:", row_w)

        params_outer.addWidget(self._params_form_widget)
        layout.addWidget(params_group)

        # ── Test rapido manuale ───────────────────────────────────────
        manual_group = QGroupBox("⚡ Test rapido — Calcolo CVI da valori manuali")
        manual_layout = QGridLayout(manual_group)
        self._manual_spins = {}
        for col, (key, label) in enumerate([
            ("geomorfologia", "Geomorf."), ("pendenza", "Pendenza"),
            ("uso_suolo", "Uso suolo"),    ("esposizione", "Esposiz."),
        ]):
            manual_layout.addWidget(QLabel(f"<b>{label}</b>"), 0, col)
            spin = QDoubleSpinBox()
            spin.setRange(1.0, 5.0)
            spin.setSingleStep(0.5)
            spin.setValue(3.0)
            self._manual_spins[key] = spin
            manual_layout.addWidget(spin, 1, col)

        btn_manual = QPushButton("⚡  Calcola CVI sui valori sopra")
        btn_manual.clicked.connect(self._run_manual_cvi)
        manual_layout.addWidget(btn_manual, 2, 0, 1, 4)
        self.manual_result_label = QLabel("Risultato: —")
        self.manual_result_label.setAlignment(Qt.AlignCenter)
        self.manual_result_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 6px;")
        manual_layout.addWidget(self.manual_result_label, 3, 0, 1, 4)
        layout.addWidget(manual_group)

        # ── Suggerimento ──────────────────────────────────────────────
        hint = QLabel(
            "💡 Non hai ancora un layer?  →  tab <b>📦 Dataset</b> per crearlo con il wizard "
            "o caricare un dataset di esempio\n"
            "💡 Vuoi scaricare dati aggiornati?  →  tab <b>🌐 Dati online</b>"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "background: #e8f4fd; border: 1px solid #a8d0f0; border-radius: 4px; "
            "padding: 8px; color: #1a3a5c; font-size: 10px;"
        )
        layout.addWidget(hint)

        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Tab: Calcolo CVI
    # ------------------------------------------------------------------

    def _tab_cvi(self):
        from qgis.PyQt.QtWidgets import QScrollArea, QFormLayout
        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(8)

        # ── Raccomandazione per isola ─────────────────────────────────
        adv_group = QGroupBox("🎯 Raccomandazione metodo per isola")
        adv_group.setStyleSheet(
            "QGroupBox { border: 2px solid #e67e22; border-radius: 6px; "
            "margin-top: 8px; font-weight: bold; color: #7a3a00; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; }"
        )
        adv_layout = QVBoxLayout(adv_group)

        adv_row = QHBoxLayout()
        adv_row.addWidget(QLabel("Isola:"))
        self.adv_island_combo = QComboBox()
        self.adv_island_combo.addItem("-- Seleziona isola --", "")
        for name in self.locator.island_names():
            badge = "⭐ " if self.advisor.has_profile(name) else ""
            self.adv_island_combo.addItem(f"{badge}{name}", name)
        self.adv_island_combo.currentIndexChanged.connect(self._on_advisor_island_changed)
        adv_row.addWidget(self.adv_island_combo, 1)

        btn_apply_rec = QPushButton("✅  Applica metodo raccomandato")
        btn_apply_rec.setStyleSheet(
            "QPushButton { background: #e67e22; color: white; border-radius: 4px; "
            "font-weight: bold; padding: 4px 10px; }"
            "QPushButton:hover { background: #ca6f1e; }"
        )
        btn_apply_rec.clicked.connect(self._apply_recommended_method)
        adv_row.addWidget(btn_apply_rec)
        adv_layout.addLayout(adv_row)

        # Box raccomandazione
        self.adv_box = QTextEdit()
        self.adv_box.setReadOnly(True)
        self.adv_box.setMaximumHeight(100)
        self.adv_box.setStyleSheet(
            "background: #fff8f0; border: 1px solid #f0a060; border-radius: 4px; "
            "font-size: 10px; padding: 4px;"
        )
        self.adv_box.setPlaceholderText(
            "Seleziona un'isola per vedere la raccomandazione metodologica…\n"
            "Le isole con ⭐ hanno una raccomandazione specifica da letteratura."
        )
        adv_layout.addWidget(self.adv_box)
        layout.addWidget(adv_group)

        # ── Selezione metodo ──────────────────────────────────────────
        method_group = QGroupBox("📐 Metodo di calcolo CVI")
        method_layout = QVBoxLayout(method_group)

        method_row = QHBoxLayout()
        method_row.addWidget(QLabel("Metodo:"))
        self.method_combo = QComboBox()
        for mid, meth in ALL_METHODS.items():
            self.method_combo.addItem(meth.name, mid)
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_row.addWidget(self.method_combo, 1)
        method_layout.addLayout(method_row)

        self.method_info_label = QLabel("")
        self.method_info_label.setWordWrap(True)
        self.method_info_label.setStyleSheet(
            "background: #f0f4ff; border: 1px solid #c8d0f0; border-radius: 4px; "
            "padding: 6px; font-size: 10px; color: #2a2a6a;"
        )
        method_layout.addWidget(self.method_info_label)

        self.method_formula_label = QLabel("")
        self.method_formula_label.setAlignment(Qt.AlignCenter)
        self.method_formula_label.setStyleSheet(
            "font-family: monospace; font-size: 12px; font-weight: bold; "
            "color: #1a3a5c; padding: 4px;"
        )
        method_layout.addWidget(self.method_formula_label)

        self.method_params_label = QLabel("")
        self.method_params_label.setWordWrap(True)
        self.method_params_label.setStyleSheet(
            "color: #555; font-size: 9px; font-style: italic; padding: 2px;"
        )
        method_layout.addWidget(self.method_params_label)
        layout.addWidget(method_group)

        # ── Valori costanti per parametri senza campo layer ───────────
        const_group = QGroupBox("🔢 Valori costanti — parametri senza campo nel layer")
        const_group.setStyleSheet(
            "QGroupBox { border: 1px solid #a8c8e8; border-radius: 6px; "
            "margin-top: 8px; color: #1a3a5c; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; background: white; font-weight: bold; }"
        )
        const_outer = QVBoxLayout(const_group)

        const_note = QLabel(
            "Per i parametri non presenti come campo nel layer (es. SLR, altezza onde), "
            "inserisci un valore costante valido per l'intera isola. "
            "I valori precompilati provengono dalla letteratura specifica per l'isola selezionata."
        )
        const_note.setWordWrap(True)
        const_note.setStyleSheet("color: #555; font-size: 9px; padding-bottom: 4px;")
        const_outer.addWidget(const_note)

        self._const_form_widget = QWidget()
        self._const_form_layout = QFormLayout(self._const_form_widget)
        self._const_form_layout.setSpacing(4)
        self._const_spins: Dict[str, "QDoubleSpinBox"] = {}
        self._const_source_labels: Dict[str, QLabel] = {}
        const_outer.addWidget(self._const_form_widget)
        layout.addWidget(const_group)

        # ── Calcola ───────────────────────────────────────────────────
        btn_calc = QPushButton("🧮  Calcola CVI sul layer selezionato")
        btn_calc.setMinimumHeight(40)
        btn_calc.setStyleSheet(
            "QPushButton { background-color: #1a3a5c; color: white; "
            "border-radius: 5px; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #2a5a8c; }"
        )
        btn_calc.clicked.connect(self._run_cvi)
        layout.addWidget(btn_calc)

        self.calc_progress = QProgressBar()
        self.calc_progress.setRange(0, 100)
        self.calc_progress.setValue(0)
        self.calc_progress.setFormat("In attesa...")
        self.calc_progress.setStyleSheet(
            "QProgressBar { height: 22px; border-radius: 4px; }"
            "QProgressBar::chunk { background-color: #1a3a5c; border-radius: 4px; }"
        )
        layout.addWidget(self.calc_progress)

        self.calc_log = QTextEdit()
        self.calc_log.setReadOnly(True)
        self.calc_log.setMaximumHeight(150)
        self.calc_log.setStyleSheet(
            "background: #f4f4f4; border: 1px solid #ddd; border-radius: 4px; "
            "padding: 4px; font-family: monospace; font-size: 10px;"
        )
        self.calc_log.setPlaceholderText("Il log del calcolo apparirà qui...")
        layout.addWidget(self.calc_log)

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

        # Popola default
        self._on_method_changed(0)
        return widget

    # ------------------------------------------------------------------
    # Tab: Dataset (wizard + dati reali + demo)
    # ------------------------------------------------------------------

    def _tab_dataset(self) -> QWidget:
        self._dataset_tab = DatasetTab(
            iface=self.iface,
            locator=self.locator,
            detailed=self.detailed,
            demo_gen=self.demo_gen,
            styler=self.styler,
        )
        # Quando il wizard o i pannelli caricano un layer, aggiorna il tab Dati
        self._dataset_tab.layer_loaded.connect(self._on_dataset_layer_loaded)
        return self._dataset_tab

    def _on_dataset_layer_loaded(self, layer):
        """Callback: layer caricato dal tab Dataset → aggiorna tab Dati."""
        self._refresh_all_combos(select_layer=layer)
        self._auto_map_fields_for_layer(layer)
        self._flash_data_tab()

    def _auto_map_fields_for_layer(self, layer):
        """Prova a mappare automaticamente i campi noti (wizard, reale, demo)."""
        from ..core.demo_data_generator import DemoDataGenerator as DDG
        from ..core.detailed_island_data import DetailedIslandDataset as DID

        # Mappa comune a wizard, reale e demo
        candidate_maps = [
            {"geomorfologia": DID.FIELD_GEOMORF, "pendenza": DID.FIELD_PENDENZA,
             "uso_suolo": DID.FIELD_USO,          "esposizione": DID.FIELD_ESPOS},
            {"geomorfologia": DDG.FIELD_GEOMORF,  "pendenza": DDG.FIELD_PENDENZA,
             "uso_suolo": DDG.FIELD_USO,           "esposizione": DDG.FIELD_ESPOS},
        ]
        # I campi del wizard usano gli stessi nomi del dataset reale
        field_names = [f.name() for f in layer.fields()]
        for mapping in candidate_maps:
            if all(v in field_names for v in mapping.values()):
                for key, field_name in mapping.items():
                    cb = self._param_field_combos.get(key)
                    if cb:
                        self._populate_field_combo(cb, layer)
                        idx = cb.findData(field_name)
                        if idx >= 0:
                            cb.setCurrentIndex(idx)
                            self.field_map[key] = field_name
                return

    # ------------------------------------------------------------------
    # Tab: Dati online
    # ------------------------------------------------------------------

    def _tab_online_data(self):
        from qgis.PyQt.QtWidgets import QScrollArea
        from ..core.online_data_sources import OnlineDataSources, CATEGORIES, CVI_PARAMS

        self._ods = OnlineDataSources(self.iface)
        self._selected_source_id = None

        widget = QWidget()
        root = QVBoxLayout(widget)
        root.setSpacing(6)

        # ── Header ───────────────────────────────────────────────────
        info = QLabel(
            "Fonti dati verificate e aggiornate per il rischio costiero delle isole minori italiane.\n"
            "📥 DOWNLOAD — apre il browser alla pagina ufficiale per scaricare il file\n"
            "🖼️ WMS / XYZ — carica direttamente in QGIS come layer di sfondo\n"
            "🔗 WFS — carica layer vettoriale direttamente in QGIS"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "background: #e8f4fd; border: 1px solid #a8d0f0; border-radius: 5px; "
            "padding: 8px; color: #1a3a5c; font-size: 10px;"
        )
        root.addWidget(info)

        # ── Filtri ───────────────────────────────────────────────────
        filter_row = QHBoxLayout()

        self.ods_search = QLineEdit()
        self.ods_search.setPlaceholderText("🔍  Cerca per nome, provider o tag…")
        self.ods_search.textChanged.connect(self._filter_sources)
        filter_row.addWidget(self.ods_search, 2)

        self.ods_cat_combo = QComboBox()
        self.ods_cat_combo.addItem("Tutte le categorie", "")
        for cat in CATEGORIES:
            self.ods_cat_combo.addItem(cat, cat)
        self.ods_cat_combo.currentIndexChanged.connect(self._filter_sources)
        filter_row.addWidget(self.ods_cat_combo, 1)

        self.ods_param_combo = QComboBox()
        self.ods_param_combo.addItem("Tutti i parametri", "")
        param_labels = {
            "geomorfologia": "🏔 Geomorfologia",
            "pendenza":      "📐 Pendenza",
            "uso_suolo":     "🌿 Uso del suolo",
            "esposizione":   "🌊 Esposizione",
            "linea_riva":    "📍 Linea di riva",
            "sfondo":        "🗺️ Sfondo",
        }
        for p in CVI_PARAMS:
            self.ods_param_combo.addItem(param_labels.get(p, p), p)
        self.ods_param_combo.currentIndexChanged.connect(self._filter_sources)
        filter_row.addWidget(self.ods_param_combo, 1)
        root.addLayout(filter_row)

        # ── Lista fonti ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self._ods_list_widget = QWidget()
        self._ods_list_layout = QVBoxLayout(self._ods_list_widget)
        self._ods_list_layout.setSpacing(3)
        self._ods_list_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self._ods_list_widget)
        scroll.setMinimumHeight(240)
        root.addWidget(scroll, 1)

        # ── Dettaglio + azione ────────────────────────────────────────
        detail_group = QGroupBox("Fonte selezionata")
        detail_lay = QVBoxLayout(detail_group)

        self.ods_detail = QTextEdit()
        self.ods_detail.setReadOnly(True)
        self.ods_detail.setMaximumHeight(85)
        self.ods_detail.setStyleSheet(
            "background: #f8f9fa; border: 1px solid #dee2e6; "
            "border-radius: 4px; font-size: 10px; padding: 4px;"
        )
        self.ods_detail.setPlaceholderText("Clicca una fonte per vedere i dettagli…")
        detail_lay.addWidget(self.ods_detail)

        action_row = QHBoxLayout()
        self.ods_action_btn = QPushButton("Seleziona una fonte")
        self.ods_action_btn.setMinimumHeight(36)
        self.ods_action_btn.setEnabled(False)
        self.ods_action_btn.setStyleSheet(
            "QPushButton { background: #1a3a5c; color: white; border-radius: 5px; "
            "font-weight: bold; font-size: 11px; }"
            "QPushButton:hover { background: #2a5a8c; }"
            "QPushButton:disabled { background: #b0bec5; }"
        )
        self.ods_action_btn.clicked.connect(self._execute_source_action)
        action_row.addWidget(self.ods_action_btn, 1)
        detail_lay.addLayout(action_row)
        root.addWidget(detail_group)

        # ── Log ───────────────────────────────────────────────────────
        self.ods_log = QTextEdit()
        self.ods_log.setReadOnly(True)
        self.ods_log.setMaximumHeight(55)
        self.ods_log.setStyleSheet(
            "background: #f4f4f4; border: 1px solid #ddd; border-radius: 4px; "
            "padding: 4px; font-family: monospace; font-size: 9px;"
        )
        root.addWidget(self.ods_log)

        # Popola lista
        self._populate_sources(self._ods.all_sources())
        return widget

    # ------------------------------------------------------------------
    # Slot — Dati online
    # ------------------------------------------------------------------

    def _populate_sources(self, sources):
        """Ricostruisce la lista delle fonti dati."""
        # Pulisce
        while self._ods_list_layout.count():
            item = self._ods_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        access_icons = {
            "DOWNLOAD": ("📥", "#1a7a3a", "#e8f8ee"),
            "WMS":      ("🖼️", "#1a3a8a", "#e8eef8"),
            "XYZ":      ("🗺️", "#5a1a8a", "#f0e8f8"),
            "WFS":      ("🔗", "#7a4a00", "#fff3e0"),
        }
        param_icons = {
            "geomorfologia": "🏔", "pendenza": "📐",
            "uso_suolo": "🌿",     "esposizione": "🌊",
            "linea_riva": "📍",    "sfondo": "🗺️",
        }

        for i, src in enumerate(sources):
            frame = QFrame()
            bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
            frame.setStyleSheet(
                f"QFrame {{ background: {bg}; border-radius: 4px; "
                f"border: 1px solid #e9ecef; }}"
                f"QFrame:hover {{ background: #e3f2fd; border: 1px solid #90caf9; }}"
            )
            frame.setCursor(Qt.PointingHandCursor)
            row = QHBoxLayout(frame)
            row.setContentsMargins(6, 4, 6, 4)
            row.setSpacing(6)

            # Badge tipo accesso
            icon, tc, tbg = access_icons.get(src.access_type, ("?", "#333", "#eee"))
            badge = QLabel(f"{icon} {src.access_type}")
            badge.setStyleSheet(
                f"font-size: 8px; font-weight: bold; color: {tc}; "
                f"background: {tbg}; border-radius: 3px; padding: 2px 5px;"
            )
            badge.setFixedWidth(72)
            badge.setAlignment(Qt.AlignCenter)
            row.addWidget(badge)

            # Nome + provider
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            name_lbl = QLabel(f"<b>{src.name}</b>")
            name_lbl.setStyleSheet("font-size: 10px; color: #212529;")
            prov_lbl = QLabel(f"{src.provider}")
            prov_lbl.setStyleSheet("font-size: 9px; color: #6c757d;")
            text_col.addWidget(name_lbl)
            text_col.addWidget(prov_lbl)
            row.addLayout(text_col, 1)

            # Parametro CVI
            p_icon = param_icons.get(src.cvi_param, "")
            param_lbl = QLabel(f"{p_icon}")
            param_lbl.setToolTip(f"Parametro: {src.cvi_param}")
            param_lbl.setStyleSheet("font-size: 13px;")
            param_lbl.setFixedWidth(22)
            row.addWidget(param_lbl)

            # Affidabilità
            rel_color = "#1a7a3a" if src.reliability == "HIGH" else "#e67e22"
            rel_lbl = QLabel("●")
            rel_lbl.setToolTip(f"Affidabilità: {src.reliability}")
            rel_lbl.setStyleSheet(f"color: {rel_color}; font-size: 14px;")
            rel_lbl.setFixedWidth(18)
            row.addWidget(rel_lbl)

            frame.mousePressEvent = lambda e, sid=src.id: self._select_source(sid)
            self._ods_list_layout.addWidget(frame)

        if not sources:
            empty = QLabel("Nessuna fonte corrisponde ai filtri selezionati.")
            empty.setStyleSheet("color: #999; font-style: italic; padding: 12px;")
            empty.setAlignment(Qt.AlignCenter)
            self._ods_list_layout.addWidget(empty)

        self._ods_list_layout.addStretch()

    def _filter_sources(self):
        query     = self.ods_search.text().strip()
        category  = self.ods_cat_combo.currentData()
        cvi_param = self.ods_param_combo.currentData()
        results   = self._ods.filter(query=query, category=category, cvi_param=cvi_param)
        self._populate_sources(results)

    def _select_source(self, source_id: str):
        from ..core.online_data_sources import SOURCES
        src = self._ods.get(source_id)
        if src is None:
            return
        self._selected_source_id = source_id

        # Testo dettaglio
        note_html = f"<br><span style='color:#e67e22;'>⚠️ {src.note}</span>" if src.note else ""
        html = (
            f"<b>{src.name}</b><br>"
            f"<span style='color:#546e7a;'>Provider:</span> {src.provider} &nbsp;·&nbsp; "
            f"<span style='color:#546e7a;'>Formato:</span> {src.format_note}<br>"
            f"{src.description}{note_html}"
        )
        self.ods_detail.setHtml(html)

        # Aggiorna pulsante azione in base al tipo
        action_labels = {
            "DOWNLOAD": "📥  Apri pagina download nel browser",
            "WMS":      "🖼️  Carica layer WMS in QGIS",
            "XYZ":      "🗺️  Carica layer XYZ in QGIS",
            "WFS":      "🔗  Carica layer WFS in QGIS",
        }
        self.ods_action_btn.setText(action_labels.get(src.access_type, "Apri"))
        self.ods_action_btn.setEnabled(True)
        self._set_status(f"Selezionato: {src.name}")

    def _execute_source_action(self):
        """Esegue l'azione per la fonte selezionata."""
        if not self._selected_source_id:
            return
        src = self._ods.get(self._selected_source_id)
        if src is None:
            return

        self.ods_log.append(f"▶ {src.name}  [{src.access_type}]")

        if src.access_type == "DOWNLOAD":
            ok = self._ods.open_download_page(self._selected_source_id)
            if ok:
                self.ods_log.append(f"   ✅ Browser aperto: {src.url}")
                self._set_status(f"🌐 Pagina download aperta: {src.name}")
            else:
                self.ods_log.append("   ❌ Impossibile aprire il browser.")

        elif src.access_type == "WMS":
            self.ods_action_btn.setEnabled(False)
            self.ods_action_btn.setText("⏳ Caricamento…")
            ok, msg, layer = self._ods.load_wms(self._selected_source_id)
            self._handle_live_result(ok, msg, layer, src.name)

        elif src.access_type == "XYZ":
            self.ods_action_btn.setEnabled(False)
            self.ods_action_btn.setText("⏳ Caricamento…")
            ok, msg, layer = self._ods.load_xyz(self._selected_source_id)
            self._handle_live_result(ok, msg, layer, src.name)

        elif src.access_type == "WFS":
            self.ods_action_btn.setEnabled(False)
            self.ods_action_btn.setText("⏳ Caricamento WFS…")
            ok, msg, layer = self._ods.load_wfs(self._selected_source_id)
            self._handle_live_result(ok, msg, layer, src.name)

        # Ripristina pulsante
        from ..core.online_data_sources import ACCESS_TYPES
        action_labels = {
            "DOWNLOAD": "📥  Apri pagina download nel browser",
            "WMS":      "🖼️  Carica layer WMS in QGIS",
            "XYZ":      "🗺️  Carica layer XYZ in QGIS",
            "WFS":      "🔗  Carica layer WFS in QGIS",
        }
        self.ods_action_btn.setText(action_labels.get(src.access_type, "Apri"))
        self.ods_action_btn.setEnabled(True)

    def _handle_live_result(self, ok: bool, msg: str, layer, name: str):
        if ok:
            self.ods_log.append(f"   ✅ {msg}")
            self._set_status(f"✅ {name} caricato in QGIS")
            if layer and hasattr(layer, "id"):
                self._refresh_all_combos(select_layer=layer if hasattr(layer, "fields") else None)
            self._flash_data_tab()
        else:
            self.ods_log.append(f"   ❌ {msg.splitlines()[0]}")
            self._set_status(f"❌ Caricamento fallito: {name}")

    def _flash_data_tab(self):
        """
        Evidenzia il tab 📂 Dati per 3 secondi con testo e colore modificati,
        segnalando all'utente che il layer è disponibile lì.
        """
        from qgis.PyQt.QtCore import QTimer
        DATA_TAB_INDEX = 1   # "📂 Dati" è il secondo tab (indice 1)
        original_text  = self.tabs.tabText(DATA_TAB_INDEX)

        self.tabs.setTabText(DATA_TAB_INDEX, "📂 Dati  ✅")
        self.tabs.tabBar().setTabTextColor(DATA_TAB_INDEX, QColor("#1a7a3a"))

        def restore():
            self.tabs.setTabText(DATA_TAB_INDEX, original_text)
            self.tabs.tabBar().setTabTextColor(DATA_TAB_INDEX, QColor())

        QTimer.singleShot(3000, restore)

    def _tab_export(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)

        # ── Cartella di output ─────────────────────────────────────────
        folder_group = QGroupBox("Cartella di output")
        folder_layout = QHBoxLayout(folder_group)
        self.export_dir_edit = QLineEdit()
        self.export_dir_edit.setPlaceholderText(
            "Seleziona la cartella dove salvare i file..."
        )
        folder_layout.addWidget(self.export_dir_edit, 1)
        btn_browse = QPushButton("📁 Sfoglia")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self._browse_export_dir)
        folder_layout.addWidget(btn_browse)
        layout.addWidget(folder_group)

        # ── Titolo mappa ───────────────────────────────────────────────
        title_group = QGroupBox("Titolo mappa (per PNG e report)")
        title_layout = QHBoxLayout(title_group)
        self.export_title_edit = QLineEdit()
        self.export_title_edit.setPlaceholderText(
            "es.  Rischio Costiero — Lipari (Isole Eolie)"
        )
        title_layout.addWidget(self.export_title_edit)
        layout.addWidget(title_group)

        # ── Opzioni export ─────────────────────────────────────────────
        opts_group = QGroupBox("Output da generare")
        opts_layout = QVBoxLayout(opts_group)
        self.chk_png = QCheckBox("🖼️  Mappa PNG  (vista corrente del canvas, alta risoluzione)")
        self.chk_csv = QCheckBox("📄  Tabella CSV  (feature per feature con CVI e classe di rischio)")
        self.chk_txt = QCheckBox("📋  Report TXT  (statistiche aggregate e valutazione sintetica)")
        for chk in [self.chk_png, self.chk_csv, self.chk_txt]:
            chk.setChecked(True)
            chk.setStyleSheet("font-size: 11px; padding: 2px;")
            opts_layout.addWidget(chk)
        layout.addWidget(opts_group)

        # ── Pulsante esporta ───────────────────────────────────────────
        btn_export = QPushButton("💾  Esporta selezionati")
        btn_export.setMinimumHeight(42)
        btn_export.setStyleSheet(
            "QPushButton { background-color: #1a3a5c; color: white; "
            "border-radius: 5px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #2a5a8c; }"
        )
        btn_export.clicked.connect(self._run_export)
        layout.addWidget(btn_export)

        # ── Log export ─────────────────────────────────────────────────
        self.export_log = QTextEdit()
        self.export_log.setReadOnly(True)
        self.export_log.setMaximumHeight(140)
        self.export_log.setStyleSheet(
            "background: #f4f4f4; border: 1px solid #ddd; "
            "border-radius: 4px; padding: 4px; font-family: monospace; font-size: 10px;"
        )
        self.export_log.setPlaceholderText("Il log dell'esportazione apparirà qui...")
        layout.addWidget(self.export_log)

        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Barra di stato
    # ------------------------------------------------------------------

    def _make_statusbar(self):
        frame = QFrame()
        frame.setStyleSheet("background: #ecf0f1; border-radius: 4px; padding: 2px 8px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        self.status_label = QLabel("✅ Plugin pronto.")
        self.status_label.setStyleSheet("color: #2c3e50; font-size: 10px;")
        layout.addWidget(self.status_label)
        layout.addStretch()
        version_lbl = QLabel("v1.6 — Dati & Online")
        version_lbl.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(version_lbl)
        return frame

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _populate_layer_combo(self, combo):
        """Popola un QComboBox con i layer vettoriali presenti nel progetto."""
        combo.clear()
        combo.addItem("-- nessun layer --", "")
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                combo.addItem(layer.name(), layer.id())

    def _populate_field_combo(self, combo, layer):
        """Popola un QComboBox con i campi del layer selezionato."""
        current = combo.currentData()
        combo.clear()
        combo.addItem("-- non assegnato --", "")
        if layer is not None:
            for field in layer.fields():
                combo.addItem(field.name(), field.name())
        # Ripristina selezione precedente
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _refresh_all_combos(self, select_layer=None):
        """
        Aggiorna tutti i combo dei layer e dei campi parametro.

        :param select_layer: se fornito, seleziona questo layer nel shore_combo
                             dopo l'aggiornamento (evita il problema di ordine).
        """
        self._populate_layer_combo(self.shore_combo)

        # Seleziona il layer desiderato PRIMA di aggiornare i field combo
        if select_layer is not None:
            idx = self.shore_combo.findData(select_layer.id())
            if idx >= 0:
                # Blocca il segnale per evitare doppio trigger di _on_shore_layer_changed
                self.shore_combo.blockSignals(True)
                self.shore_combo.setCurrentIndex(idx)
                self.shore_combo.blockSignals(False)

        # Ora legge il layer corretto (quello appena selezionato)
        layer = self._get_selected_layer()
        for cb in self._param_field_combos.values():
            self._populate_field_combo(cb, layer)
        if layer:
            self.feat_count_label.setText(f"{layer.featureCount()} feature")
        self._set_status("🔄 Lista layer aggiornata.")

    def _get_selected_layer(self):
        """Restituisce il layer vettoriale selezionato nel shore_combo, o None."""
        lid = self.shore_combo.currentData()
        if not lid:
            return None
        return QgsProject.instance().mapLayer(lid)

    def _set_status(self, msg):
        self.status_label.setText(msg)

    def _log(self, msg: str):
        """Aggiunge una riga al log del tab CVI."""
        self.calc_log.append(msg)

    # ------------------------------------------------------------------
    # Slot — Dataset reali
    # ------------------------------------------------------------------

    def _update_real_preview(self, index=None):
        """Aggiorna la descrizione del dataset reale selezionato."""
        name = self.real_island_combo.currentData()
        info = self.detailed.get_info(name) if name else None
        if not info:
            return
        n = len(info["tratti"])
        fonti = ", ".join(info["fonti"])
        self.real_preview_label.setText(
            f"{n} tratti costieri  |  Anno riferimento: {info['anno_riferimento']}\n"
            f"Fonti: {fonti}\n"
            f"{info['descrizione']}"
        )

    def _load_real_dataset(self):
        """Carica il layer georeferenziato reale in QGIS."""
        name = self.real_island_combo.currentData()
        if not name:
            return

        self.btn_load_real.setEnabled(False)
        self.btn_load_real.setText("⏳  Caricamento…")

        try:
            layer = self.detailed.generate(name)
            if layer is None:
                self.real_result_label.setText("❌ Generazione layer fallita.")
                return

            QgsProject.instance().addMapLayer(layer)
            self.styler.apply_cvi_style(layer)

            # Zoom sull'isola (usa il nome base senza il suffisso)
            base_name = name.replace(" (dati reali)", "")
            self.locator.zoom_to(base_name)

            # Aggiorna combo e seleziona layer + auto-mappa campi
            self._refresh_all_combos(select_layer=layer)
            self._auto_map_real_fields()

            n = layer.featureCount()
            self.real_result_label.setText(
                f"✅ {n} tratti caricati con coordinate reali.\n"
                f"   Campi mappati automaticamente → vai al tab Calcolo CVI!"
            )
            self.real_result_label.setStyleSheet(
                "color: #1a7a3a; font-size: 10px; padding: 2px 0;"
            )
            self._set_status(f"✅ Dataset reale caricato: {name}")

        except Exception as e:
            self.real_result_label.setText(f"❌ Errore: {e}")
            self.real_result_label.setStyleSheet("color: #c0392b; font-size: 10px;")
        finally:
            self.btn_load_real.setEnabled(True)
            self.btn_load_real.setText("📍  Carica dataset reale in QGIS")

    def _auto_map_real_fields(self):
        """Mappa automaticamente i campi del layer reale ai parametri CVI."""
        from ..core.detailed_island_data import DetailedIslandDataset as DID
        field_mapping = {
            "geomorfologia": DID.FIELD_GEOMORF,
            "pendenza":      DID.FIELD_PENDENZA,
            "uso_suolo":     DID.FIELD_USO,
            "esposizione":   DID.FIELD_ESPOS,
        }
        layer = self._get_selected_layer()
        if layer is None:
            return
        for key, field_name in field_mapping.items():
            cb = self._param_field_combos.get(key)
            if cb is None:
                continue
            self._populate_field_combo(cb, layer)
            idx = cb.findData(field_name)
            if idx >= 0:
                cb.setCurrentIndex(idx)
                self.field_map[key] = field_name

    def _clear_real_layers(self):
        """Rimuove tutti i layer [REALE] dal progetto."""
        to_remove = [
            lid for lid, lyr in QgsProject.instance().mapLayers().items()
            if lyr.name().startswith("[REALE]")
        ]
        if not to_remove:
            self._set_status("ℹ️ Nessun layer reale presente.")
            return
        QgsProject.instance().removeMapLayers(to_remove)
        self._populate_layer_combo(self.shore_combo)
        self._set_status(f"🗑️ Rimossi {len(to_remove)} layer reali.")
        self.real_result_label.setText("")

    # ------------------------------------------------------------------
    # Slot — Dataset demo
    # ------------------------------------------------------------------

    def _update_demo_preview(self):
        """Aggiorna l'anteprima dei tratti che verranno generati."""
        from ..core.demo_data_generator import ISLAND_PROFILES, DEFAULT_PROFILE
        name = self.demo_island_combo.currentData()
        if not name:
            return
        profile = ISLAND_PROFILES.get(name, DEFAULT_PROFILE)
        n = len(profile)
        has_detail = name in ISLAND_PROFILES
        badge = "⭐ profilo dettagliato" if has_detail else "profilo generico"
        self.demo_preview_label.setText(
            f"Verranno generati {n} tratti costieri  ({badge})"
        )

    def _generate_demo_layer(self):
        """Genera il layer demo e lo carica nel progetto QGIS."""
        from ..core.demo_data_generator import DemoDataGenerator

        name = self.demo_island_combo.currentData()
        if not name:
            self.demo_result_label.setText("⚠️ Seleziona un'isola.")
            return

        bbox = self.locator.get_bbox(name)
        if bbox is None:
            self.demo_result_label.setText(
                f"⚠️ Bounding box non disponibile per '{name}'."
            )
            return

        add_noise = self.demo_noise_chk.isChecked()
        self.btn_generate_demo.setEnabled(False)
        self.btn_generate_demo.setText("⏳  Generazione in corso...")
        self.demo_result_label.setText("")

        try:
            layer = self.demo_gen.generate(name, bbox, add_noise=add_noise)
            QgsProject.instance().addMapLayer(layer)

            # Applica subito simbologia CVI
            self.styler.apply_cvi_style(layer)

            # Aggiorna il combo layer e seleziona quello appena generato
            self._populate_layer_combo(self.shore_combo)
            idx = self.shore_combo.findText(layer.name())
            if idx >= 0:
                self.shore_combo.setCurrentIndex(idx)

            # Auto-mappa i campi demo nei parametri CVI
            self._auto_map_demo_fields()

            # Zoom sull'isola
            self.locator.zoom_to(name)

            n = layer.featureCount()
            self.demo_result_label.setText(
                f"✅ Layer demo caricato: {n} tratti costieri.\n"
                f"   Campi parametro mappati automaticamente. "
                f"Vai nel tab Calcolo CVI e premi Calcola!"
            )
            self.demo_result_label.setStyleSheet(
                "color: #1a7a3a; font-size: 10px; padding: 2px 0;"
            )
            self._set_status(f"✅ Layer demo '{name}' caricato — pronto per il calcolo CVI.")

        except Exception as e:
            self.demo_result_label.setText(f"❌ Errore: {e}")
            self.demo_result_label.setStyleSheet(
                "color: #c0392b; font-size: 10px; padding: 2px 0;"
            )
        finally:
            self.btn_generate_demo.setEnabled(True)
            self.btn_generate_demo.setText("⚡  Genera layer demo e carica in QGIS")

    def _auto_map_demo_fields(self):
        """
        Mappa automaticamente i campi del layer demo ai parametri CVI.
        Funziona perché i nomi dei campi demo sono noti e fissi.
        """
        from ..core.demo_data_generator import DemoDataGenerator as DDG
        field_mapping = {
            "geomorfologia": DDG.FIELD_GEOMORF,
            "pendenza":      DDG.FIELD_PENDENZA,
            "uso_suolo":     DDG.FIELD_USO,
            "esposizione":   DDG.FIELD_ESPOS,
        }
        layer = self._get_selected_layer()
        if layer is None:
            return

        for key, field_name in field_mapping.items():
            cb = self._param_field_combos.get(key)
            if cb is None:
                continue
            self._populate_field_combo(cb, layer)
            idx = cb.findData(field_name)
            if idx >= 0:
                cb.setCurrentIndex(idx)
                self.field_map[key] = field_name

    def _clear_demo_layers(self):
        """Rimuove tutti i layer [DEMO] dal progetto corrente."""
        to_remove = [
            lid for lid, lyr in QgsProject.instance().mapLayers().items()
            if lyr.name().startswith("[DEMO]")
        ]
        if not to_remove:
            self._set_status("ℹ️ Nessun layer demo presente nel progetto.")
            return
        QgsProject.instance().removeMapLayers(to_remove)
        self._populate_layer_combo(self.shore_combo)
        self._set_status(f"🗑️ Rimossi {len(to_remove)} layer demo.")
        self.demo_result_label.setText("")

    # ------------------------------------------------------------------
    # Slot — Selezione layer / campi
    # ------------------------------------------------------------------

    def _on_shore_layer_changed(self, index):
        """Aggiorna contatore feature e combo dei campi quando cambia il layer."""
        layer = self._get_selected_layer()
        if layer is None:
            self.feat_count_label.setText("— feature")
            for cb in self._param_field_combos.values():
                self._populate_field_combo(cb, None)
            return

        self.feat_count_label.setText(f"{layer.featureCount()} feature")
        for cb in self._param_field_combos.values():
            self._populate_field_combo(cb, layer)
        self._set_status(f"Layer selezionato: {layer.name()}")

    def _on_field_mapped(self, key: str, combo: "QComboBox"):
        """Aggiorna il field_map quando l'utente seleziona un campo."""
        self.field_map[key] = combo.currentData() or ""

    def _on_island_changed(self, index):
        if index > 0:
            name = self.island_combo.currentData()
            info = self.locator.get_info(name) if name else None
            if info:
                arc = info.get("arcipelago") or "—"
                reg = info.get("regione", "?")
                self.island_info_label.setText(
                    f"Arcipelago: {arc}   |   Regione: {reg}"
                )
            self._set_status(f"Isola selezionata: {name}")

    def _zoom_to_island(self):
        name = self.island_combo.currentData()
        if not name:
            self._set_status("⚠️ Seleziona un'isola dal menu.")
            return
        ok = self.locator.zoom_to(name)
        if ok:
            self._set_status(f"🔍 Zoom su: {name}")
        else:
            self._set_status(f"⚠️ Isola '{name}' non trovata nel database.")

    def _zoom_overview(self):
        self.locator.zoom_to_all_islands()
        self._set_status("🗺️ Vista d'insieme: tutte le isole minori italiane.")

    def _apply_style(self):
        layer = self._get_selected_layer()
        if layer is None:
            self._set_status("⚠️ Nessun layer selezionato nel tab Dati.")
            return
        ok = self.styler.apply_cvi_style(layer)
        if ok:
            self._set_status(f"🎨 Stile CVI applicato a: {layer.name()}")
        else:
            self._set_status("❌ Impossibile applicare lo stile.")

    def _toggle_labels(self):
        layer = self._get_selected_layer()
        if layer is None:
            self._set_status("⚠️ Nessun layer selezionato.")
            return
        if layer.labelsEnabled():
            self.styler.disable_labels(layer)
            self._set_status("🏷️ Etichette disattivate.")
        else:
            self.styler.apply_labels(layer)
            self._set_status("🏷️ Etichette CVI attivate.")

    def _reset_style(self):
        layer = self._get_selected_layer()
        if layer is None:
            self._set_status("⚠️ Nessun layer selezionato.")
            return
        self.styler.reset_style(layer)
        self._set_status(f"↺ Stile ripristinato su: {layer.name()}")

    # ------------------------------------------------------------------
    # Slot — Advisor isola
    # ------------------------------------------------------------------

    def _on_advisor_island_changed(self, index: int):
        """Mostra la raccomandazione metodologica per l'isola selezionata."""
        name = self.adv_island_combo.currentData()
        if not name:
            self.adv_box.clear()
            return

        profile = self.advisor.get_profile(name)
        from ..core.cvi_methods import ALL_METHODS
        rec_method = ALL_METHODS.get(profile.recommended_method)
        alts = [ALL_METHODS[m].short_name for m in profile.alternative_methods if m in ALL_METHODS]

        has_specific = self.advisor.has_profile(name)
        badge = "⭐ Raccomandazione specifica da letteratura" if has_specific else "ℹ️ Profilo generico"

        html = (
            f"<b>{badge}</b><br><br>"
            f"<b>Metodo raccomandato:</b> {rec_method.name if rec_method else profile.recommended_method}<br>"
            f"<b>Alternative accettabili:</b> {', '.join(alts) if alts else '—'}<br><br>"
            f"<b>Motivazione:</b> {profile.reason}<br><br>"
            f"<i>Riferimento: {profile.reference}</i>"
        )
        if profile.notes:
            html += f"<br><br><span style='color:#e67e22;'>⚠️ {profile.notes}</span>"
        self.adv_box.setHtml(html)

        # Aggiorna anche i valori costanti con i dati dell'isola
        self._rebuild_constants_panel(name)

    def _apply_recommended_method(self):
        """Seleziona nel combo il metodo raccomandato per l'isola corrente."""
        name = self.adv_island_combo.currentData()
        if not name:
            return
        mid = self.advisor.get_recommended_method(name)
        idx = self.method_combo.findData(mid)
        if idx >= 0:
            self.method_combo.setCurrentIndex(idx)
        self._set_status(f"✅ Metodo impostato: {ALL_METHODS.get(mid, {}).name if mid in ALL_METHODS else mid}")

    def _rebuild_constants_panel(self, island_name: str = ""):
        """Ricostruisce il pannello valori costanti per i parametri del metodo corrente."""
        from qgis.PyQt.QtWidgets import QDoubleSpinBox as DSB

        # Rimuove righe esistenti
        while self._const_form_layout.rowCount() > 0:
            self._const_form_layout.removeRow(0)
        self._const_spins.clear()
        self._const_source_labels.clear()

        method = self.method_engine.method
        layer = self._get_selected_layer()
        layer_fields = [f.name() for f in layer.fields()] if layer else []

        # Mostra solo i parametri NON presenti come campo nel layer
        constants_from_island = self.advisor.get_constants(island_name) if island_name else {}
        any_shown = False

        for param in method.params:
            mapped_field = self.field_map.get(param.key, "")
            if mapped_field and mapped_field in layer_fields:
                continue   # già coperto da campo layer → non mostrare

            any_shown = True
            # SpinBox valore 1–5
            spin = DSB()
            spin.setRange(1.0, 5.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)

            # Pre-compila con valore da advisor se disponibile
            const = constants_from_island.get(param.key)
            if const:
                spin.setValue(const.value)
                source_txt = f"📚 {const.raw_value}  |  {const.source}"
            else:
                spin.setValue(3.0)
                source_txt = "Inserisci valore manualmente (scala 1–5)"

            self._const_spins[param.key] = spin

            # Label fonte
            source_lbl = QLabel(source_txt)
            source_lbl.setWordWrap(True)
            source_lbl.setStyleSheet("color: #666; font-size: 9px;")
            self._const_source_labels[param.key] = source_lbl

            # Riga: SpinBox + fonte
            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.addWidget(spin)
            row_lay.addWidget(source_lbl, 1)
            self._const_form_layout.addRow(f"{param.label}:", row_widget)

        if not any_shown:
            lbl = QLabel("✅ Tutti i parametri sono coperti dai campi del layer selezionato.")
            lbl.setStyleSheet("color: #1a7a3a; font-size: 10px; padding: 4px;")
            self._const_form_layout.addRow(lbl)

    # ------------------------------------------------------------------
    # Slot — Selezione metodo CVI
    # ------------------------------------------------------------------

    def _on_method_changed(self, index: int):
        """Aggiorna le info del metodo selezionato e ricrea i pannelli dipendenti."""
        mid = self.method_combo.currentData() if hasattr(self, "method_combo") else "gornitz_1991"
        if not mid:
            return

        method = ALL_METHODS.get(mid)
        if not method:
            return

        self.method_engine = CVIMethodEngine(mid)

        self.method_info_label.setText(
            f"<b>{method.short_name}</b> — {method.description}"
        )
        self.method_formula_label.setText(method.formula_display)

        param_list = "  |  ".join(f"{p.label}" for p in method.params)
        self.method_params_label.setText(f"Parametri: {param_list}")

        # Ricostruisce combo campi nel tab Dati
        self._rebuild_param_field_combos(method)

        # Ricostruisce pannello costanti
        island_name = self.adv_island_combo.currentData() if hasattr(self, "adv_island_combo") else ""
        self._rebuild_constants_panel(island_name or "")

    def _rebuild_param_field_combos(self, method):
        """
        Ricostruisce i combo di mappatura campi nel tab Dati
        in base ai parametri richiesti dal metodo selezionato.
        """
        if not hasattr(self, "_params_layout"):
            return   # il tab Dati non è ancora stato costruito

        # Pulisce i combo esistenti
        while self._params_layout.rowCount() > 1:
            self._params_layout.removeRow(1)

        self._param_field_combos = {}
        layer = self._get_selected_layer()

        for param in method.params:
            cb = QComboBox()
            cb.addItem("-- non assegnato --", "")
            self._populate_field_combo(cb, layer)
            # Prova a ripristinare la mappatura esistente
            if param.key in self.field_map:
                idx = cb.findData(self.field_map[param.key])
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            cb.currentIndexChanged.connect(
                lambda idx, k=param.key, c=cb: self._on_field_mapped(k, c)
            )
            self._param_field_combos[param.key] = cb
            scale_lbl = QLabel(param.scale_desc)
            scale_lbl.setStyleSheet("color: #666; font-size: 9px;")
            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.addWidget(cb, 1)
            row_lay.addWidget(scale_lbl)
            self._params_layout.addRow(f"{param.label}:", row_widget)

    # ------------------------------------------------------------------
    # Slot — Calcolo CVI su layer
    # ------------------------------------------------------------------

    def _run_cvi(self):
        """Avvia il calcolo CVI sul layer selezionato con il metodo scelto."""
        layer = self._get_selected_layer()
        if layer is None:
            QMessageBox.warning(
                self, "Layer mancante",
                "Seleziona un layer vettoriale nel tab Dati prima di avviare il calcolo."
            )
            return

        method = self.method_engine.method

        # Costruisce il field_map completo:
        # - parametri da campo layer (self.field_map)
        # - parametri da valori costanti (_const_spins) per i parametri non mappati
        effective_field_map = dict(self.field_map)
        const_values_used = {}

        for param in method.params:
            key = param.key
            if effective_field_map.get(key):
                continue   # già coperto da campo layer
            if key in self._const_spins:
                # Inietta il valore costante come valore fisso
                const_val = self._const_spins[key].value()
                effective_field_map[key] = f"__const_{key}_{const_val}__"
                const_values_used[key] = const_val

        # Verifica che tutti i parametri richiesti siano coperti
        missing = [
            p.key for p in method.params
            if not effective_field_map.get(p.key)
        ]
        if missing:
            QMessageBox.warning(
                self, "Parametri mancanti",
                f"Parametri non coperti da campo layer né da valore costante:\n"
                f"{', '.join(missing)}\n\n"
                f"Mappa i campi nel tab 📂 Dati o inserisci valori costanti "
                f"nel pannello qui sopra."
            )
            return

        self.calc_log.clear()
        self.calc_progress.setValue(0)
        self._log(f"▶ Metodo: {method.name}")
        self._log(f"   Layer: {layer.name()}")
        if const_values_used:
            self._log(f"   Valori costanti: {const_values_used}")
        self._set_status(f"⚙️ Calcolo CVI ({method.short_name}) in corso...")

        def on_progress(pct: int, msg: str):
            self.calc_progress.setValue(pct)
            self.calc_progress.setFormat(f"{pct}% — {msg}")
            self._log(f"   [{pct:3d}%] {msg}")

        ok, message, stats = self.engine.run(
            layer=layer,
            field_map=effective_field_map,
            progress_callback=on_progress,
            method_engine=self.method_engine,
            const_values=const_values_used,
        )

        if ok:
            self._log(f"\n✅ {message}")
            self._set_status(f"✅ CVI calcolato ({method.short_name}) — {layer.name()}")
            self._update_dashboard(stats)
            layer.triggerRepaint()
        else:
            self._log(f"\n❌ {message}")
            self._set_status("❌ Calcolo fallito.")
            QMessageBox.critical(self, "Errore calcolo CVI", message)

    # ------------------------------------------------------------------
    # Slot — Calcolo manuale
    # ------------------------------------------------------------------

    def _run_manual_cvi(self):
        """Calcola il CVI dai valori inseriti manualmente (test rapido)."""
        values = {k: spin.value() for k, spin in self._manual_spins.items()}
        ok, msg, result = self.engine.calculate_manual(**values)
        if ok and result:
            self.manual_result_label.setText(
                f"CVI = {result.cvi_value}   →   {result.risk_class}"
            )
            self.manual_result_label.setStyleSheet(
                f"font-size: 13px; font-weight: bold; padding: 6px; "
                f"color: {result.risk_color};"
            )
        else:
            self.manual_result_label.setText(f"Errore: {msg}")
            self.manual_result_label.setStyleSheet("color: red; font-size: 11px;")

    # ------------------------------------------------------------------
    # Aggiornamento Dashboard
    # ------------------------------------------------------------------

    def _update_dashboard(self, stats: CVIStats):
        """Aggiorna tutti i widget della dashboard con le statistiche CVI."""
        if stats is None or stats.count == 0:
            return

        # Box percentuali
        for risk_class, label_widget in self.risk_labels.items():
            pct = stats.distribution_pct.get(risk_class, 0.0)
            cnt = stats.distribution.get(risk_class, 0)
            label_widget.setText(f"{pct:.0f}%\n({cnt})")

        # Barra CVI medio (normalizzata 1–5 → 0–100)
        cvi_norm = int((stats.mean_cvi - 1.0) / 4.0 * 100)
        self.cvi_bar.setValue(max(0, min(100, cvi_norm)))
        self.cvi_bar.setFormat(f"CVI medio: {stats.mean_cvi:.3f}")

        # Dettaglio statistiche
        self.cvi_detail_label.setText(
            f"Min: {stats.min_cvi:.3f}   |   "
            f"Max: {stats.max_cvi:.3f}   |   "
            f"σ = {stats.std_cvi:.3f}   |   "
            f"N = {stats.count} tratti"
        )

        # Colore barra CVI in base al rischio medio
        if stats.mean_cvi <= 1.5:    bar_color = "#2ecc71"
        elif stats.mean_cvi <= 2.5:  bar_color = "#a8d08d"
        elif stats.mean_cvi <= 3.5:  bar_color = "#f1c40f"
        elif stats.mean_cvi <= 4.5:  bar_color = "#e67e22"
        else:                         bar_color = "#e74c3c"
        self.cvi_bar.setStyleSheet(
            f"QProgressBar {{ height: 28px; border-radius: 4px; font-weight: bold; }}"
            f"QProgressBar::chunk {{ background-color: {bar_color}; border-radius: 4px; }}"
        )

        # ── Aggiorna grafico a barre ──────────────────────────────────
        self.cvi_chart.update_data(
            stats.distribution,
            stats.distribution_pct,
            stats.count,
        )

    def _on_chart_bar_clicked(self, risk_class: str):
        """
        Quando l'utente clicca una barra del grafico, seleziona nel layer
        le feature corrispondenti a quella classe di rischio.
        """
        layer = self._get_selected_layer()
        if layer is None:
            self.chart_detail_label.setText(
                "⚠️ Nessun layer selezionato."
            )
            return

        from ..core.shoreline_loader import RISK_FIELD_NAME
        risk_idx = layer.fields().indexOf(RISK_FIELD_NAME)
        if risk_idx < 0:
            self.chart_detail_label.setText(
                "⚠️ Campo RISCHIO non presente — esegui prima il calcolo CVI."
            )
            return

        # Seleziona le feature con quella classe
        matching_ids = [
            f.id() for f in layer.getFeatures()
            if f[RISK_FIELD_NAME] == risk_class
        ]
        self.styler.apply_highlight(layer, matching_ids)
        cnt = len(matching_ids)

        color_map = {
            "Molto Basso": "#2ecc71", "Basso": "#a8d08d",
            "Medio": "#f1c40f", "Alto": "#e67e22", "Molto Alto": "#e74c3c",
        }
        color = color_map.get(risk_class, "#555")
        self.chart_detail_label.setText(
            f"<span style='color:{color}; font-weight:bold;'>{risk_class}</span>"
            f" — {cnt} tratti selezionati nel layer"
        )
        self._set_status(
            f"🔎 Selezionati {cnt} tratti con rischio '{risk_class}'."
        )

    # ------------------------------------------------------------------
    # Slot — Export
    # ------------------------------------------------------------------

    def _browse_export_dir(self):
        """Apre il dialogo di selezione cartella."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleziona cartella di output",
            os.path.expanduser("~"),
        )
        if directory:
            self.export_dir_edit.setText(directory)

    def _run_export(self):
        """Esegue tutti gli export selezionati dall'utente."""
        self.export_log.clear()

        # Validazioni preliminari
        export_dir = self.export_dir_edit.text().strip()
        if not export_dir:
            QMessageBox.warning(
                self, "Cartella mancante",
                "Seleziona una cartella di output prima di esportare."
            )
            return

        if not os.path.isdir(export_dir):
            QMessageBox.warning(
                self, "Cartella non valida",
                f"La cartella selezionata non esiste:\n{export_dir}"
            )
            return

        do_png = self.chk_png.isChecked()
        do_csv = self.chk_csv.isChecked()
        do_txt = self.chk_txt.isChecked()

        if not any([do_png, do_csv, do_txt]):
            QMessageBox.information(
                self, "Nessun output selezionato",
                "Seleziona almeno un formato di output."
            )
            return

        layer  = self._get_selected_layer()
        stats  = self.engine.last_stats
        title  = self.export_title_edit.text().strip() or "Italian Minor Islands Coastal Risk"

        # Nome base file (da titolo o timestamp)
        safe_title = re.sub(r"[^\w\-_]", "_", title)[:40]
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        base = f"coastal_risk_{safe_title}_{ts}"

        success_count = 0
        self._elog("▶ Avvio esportazione...")
        self._elog(f"   Cartella: {export_dir}")
        self._elog(f"   Titolo:   {title}")
        self._elog("")

        # ── PNG ────────────────────────────────────────────────────────
        if do_png:
            png_path = os.path.join(export_dir, f"{base}.png")
            self._elog("🖼️  Esportazione PNG...")
            ok = self.exporter.export_map_png(png_path, title=title)
            if ok:
                self._elog(f"   ✅ Salvato: {os.path.basename(png_path)}")
                success_count += 1
            else:
                self._elog("   ❌ Esportazione PNG fallita.")

        # ── CSV ────────────────────────────────────────────────────────
        if do_csv:
            if layer is None:
                self._elog("📄  CSV: ⚠️ nessun layer selezionato — saltato.")
            else:
                csv_path = os.path.join(export_dir, f"{base}.csv")
                self._elog("📄  Esportazione CSV...")
                ok = self.exporter.export_stats_csv(csv_path, layer, stats)
                if ok:
                    self._elog(f"   ✅ Salvato: {os.path.basename(csv_path)}")
                    success_count += 1
                else:
                    self._elog("   ❌ Esportazione CSV fallita (CVI non calcolato?).")

        # ── TXT ────────────────────────────────────────────────────────
        if do_txt:
            if stats is None or stats.count == 0:
                self._elog("📋  Report TXT: ⚠️ nessuna statistica disponibile — saltato.")
            else:
                txt_path = os.path.join(export_dir, f"{base}_report.txt")
                island_name = self.island_combo.currentData() or ""
                self._elog("📋  Esportazione report TXT...")
                ok = self.exporter.export_report_txt(
                    txt_path,
                    layer=layer,
                    stats=stats,
                    island_name=island_name,
                    field_map=self.field_map,
                )
                if ok:
                    self._elog(f"   ✅ Salvato: {os.path.basename(txt_path)}")
                    success_count += 1
                else:
                    self._elog("   ❌ Esportazione report fallita.")

        # ── Riepilogo ──────────────────────────────────────────────────
        self._elog("")
        if success_count > 0:
            self._elog(f"✅ Completato: {success_count} file esportati in:")
            self._elog(f"   {export_dir}")
            self._set_status(f"✅ Export completato: {success_count} file salvati.")
        else:
            self._elog("❌ Nessun file esportato.")
            self._set_status("❌ Export fallito.")

    def _elog(self, msg: str):
        """Aggiunge una riga al log del tab Export."""
        self.export_log.append(msg)
