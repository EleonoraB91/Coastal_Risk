# -*- coding: utf-8 -*-
"""
core/style_manager.py
Gestione della simbologia QGIS per i layer del rischio costiero.
Fase 3: implementazione completa con renderer graduato, etichette e legenda.
"""

from typing import List, Optional
from qgis.core import (
    QgsVectorLayer,
    QgsWkbTypes,
    QgsSymbol,
    QgsLineSymbol,
    QgsFillSymbol,
    QgsSimpleLineSymbolLayer,
    QgsSimpleFillSymbolLayer,
    QgsGraduatedSymbolRenderer,
    QgsRendererRange,
    QgsTextFormat,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt


class StyleManager:
    """
    Applica stili e simbologie QGIS ai layer del rischio costiero.

    Supporta geometrie Line e Polygon.
    Usa un renderer graduato in 5 classi (verde → rosso) sul campo CVI.

    Uso tipico:
        sm = StyleManager()
        sm.apply_cvi_style(layer)          # stile automatico
        sm.apply_labels(layer)             # etichette CVI
        sm.reset_style(layer)              # ripristina default
    """

    LOG_TAG = "CoastalRiskDashboard"

    # Palette rischio: (lower, upper, hex_color, label)
    RISK_PALETTE = [
        (1.0, 1.5, "#2ecc71", "Molto Basso  (1.0 – 1.5)"),
        (1.5, 2.5, "#a8d08d", "Basso        (1.5 – 2.5)"),
        (2.5, 3.5, "#f1c40f", "Medio        (2.5 – 3.5)"),
        (3.5, 4.5, "#e67e22", "Alto         (3.5 – 4.5)"),
        (4.5, 5.0, "#e74c3c", "Molto Alto   (4.5 – 5.0)"),
    ]

    # ------------------------------------------------------------------
    # Stile CVI graduato
    # ------------------------------------------------------------------

    def apply_cvi_style(
        self,
        layer: QgsVectorLayer,
        field: str = "CVI",
        line_width: float = 1.2,
        opacity: float = 1.0,
    ) -> bool:
        """
        Applica un renderer graduato in 5 classi al layer.
        Funziona sia per geometrie Line che Polygon.

        :param layer:      layer vettoriale con campo CVI calcolato
        :param field:      nome del campo CVI (default: "CVI")
        :param line_width: spessore linea per geometrie lineari (pt)
        :param opacity:    opacità del layer (0.0–1.0)
        :return: True se applicato con successo
        """
        if not self._check_layer(layer):
            return False

        geom_type = layer.geometryType()
        ranges = []

        for lower, upper, hex_color, label in self.RISK_PALETTE:
            color = QColor(hex_color)

            if geom_type == QgsWkbTypes.LineGeometry:
                symbol = self._make_line_symbol(color, line_width)
            elif geom_type == QgsWkbTypes.PolygonGeometry:
                symbol = self._make_fill_symbol(color)
            else:
                # Punto (fallback)
                symbol = QgsSymbol.defaultSymbol(geom_type)
                symbol.setColor(color)

            ranges.append(QgsRendererRange(lower, upper, symbol, label))

        renderer = QgsGraduatedSymbolRenderer(field, ranges)
        layer.setRenderer(renderer)
        layer.setOpacity(opacity)
        layer.triggerRepaint()

        self._log(f"Stile CVI graduato applicato a '{layer.name()}' sul campo '{field}'.")
        return True

    # ------------------------------------------------------------------
    # Etichette
    # ------------------------------------------------------------------

    def apply_labels(
        self,
        layer: QgsVectorLayer,
        field: str = "CVI",
        font_size: int = 8,
    ) -> bool:
        """
        Aggiunge etichette con il valore CVI su ogni feature.

        :param layer:     layer vettoriale target
        :param field:     campo da etichettare
        :param font_size: dimensione font in punti
        :return: True se applicato con successo
        """
        if not self._check_layer(layer):
            return False

        settings = QgsPalLayerSettings()
        settings.fieldName = field
        settings.enabled = True

        text_format = QgsTextFormat()
        text_format.setSize(font_size)
        text_format.setColor(QColor("#1a1a1a"))

        # Sfondo bianco semitrasparente per leggibilità
        from qgis.core import QgsTextBackgroundSettings
        bg = QgsTextBackgroundSettings()
        bg.setEnabled(True)
        bg.setFillColor(QColor(255, 255, 255, 180))
        bg.setType(QgsTextBackgroundSettings.ShapeRectangle)
        text_format.setBackground(bg)

        settings.setFormat(text_format)
        labeling = QgsVectorLayerSimpleLabeling(settings)
        layer.setLabelsEnabled(True)
        layer.setLabeling(labeling)
        layer.triggerRepaint()

        self._log(f"Etichette CVI abilitate su '{layer.name()}'.")
        return True

    def disable_labels(self, layer: QgsVectorLayer):
        """Rimuove le etichette dal layer."""
        if self._check_layer(layer):
            layer.setLabelsEnabled(False)
            layer.triggerRepaint()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_style(self, layer: QgsVectorLayer) -> bool:
        """
        Ripristina il renderer di default del layer e rimuove le etichette.

        :return: True se eseguito con successo
        """
        if not self._check_layer(layer):
            return False

        geom_type = layer.geometryType()
        default_symbol = QgsSymbol.defaultSymbol(geom_type)
        from qgis.core import QgsSingleSymbolRenderer
        layer.setRenderer(QgsSingleSymbolRenderer(default_symbol))
        layer.setLabelsEnabled(False)
        layer.setOpacity(1.0)
        layer.triggerRepaint()

        self._log(f"Stile ripristinato su '{layer.name()}'.")
        return True

    # ------------------------------------------------------------------
    # Stile feature evidenziata (selezione)
    # ------------------------------------------------------------------

    def apply_highlight(
        self,
        layer: QgsVectorLayer,
        feature_ids: List[int],
    ):
        """
        Seleziona e mette in evidenza le feature con gli ID indicati.
        QGIS colorerà automaticamente le feature selezionate in giallo.

        :param layer:       layer vettoriale
        :param feature_ids: lista di ID feature da evidenziare
        """
        if not self._check_layer(layer):
            return
        layer.selectByIds(feature_ids)
        self._log(f"Evidenziate {len(feature_ids)} feature su '{layer.name()}'.")

    def clear_highlight(self, layer: QgsVectorLayer):
        """Rimuove la selezione (e l'evidenziazione) dal layer."""
        if self._check_layer(layer):
            layer.removeSelection()

    # ------------------------------------------------------------------
    # Utility — costruzione simboli
    # ------------------------------------------------------------------

    @staticmethod
    def _make_line_symbol(color: QColor, width: float) -> QgsLineSymbol:
        """Costruisce un QgsLineSymbol con colore e spessore dati."""
        symbol = QgsLineSymbol.createSimple({
            "color": color.name(),
            "width": str(width),
            "capstyle": "round",
            "joinstyle": "round",
        })
        return symbol

    @staticmethod
    def _make_fill_symbol(color: QColor) -> QgsFillSymbol:
        """Costruisce un QgsFillSymbol con riempimento e bordo scuro."""
        border = color.darker(140)
        symbol = QgsFillSymbol.createSimple({
            "color": color.name(),
            "outline_color": border.name(),
            "outline_width": "0.4",
        })
        return symbol

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_layer(self, layer: QgsVectorLayer) -> bool:
        if layer is None or not layer.isValid():
            self._log("Layer non valido.", level=Qgis.Warning)
            return False
        return True

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)

