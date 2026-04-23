# -*- coding: utf-8 -*-
"""
plugin_main.py
Classe principale del plugin Coastal Risk Dashboard.
Gestisce inizializzazione, toolbar, menu e ciclo di vita del plugin.
"""

import os
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.core import QgsProject

from .ui.main_dialog import MainDialog


class CoastalRiskDashboard:
    """Classe principale del plugin QGIS."""

    def __init__(self, iface):
        """
        Costruttore.
        :param iface: QgisInterface — interfaccia QGIS fornita al plugin
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr("&Coastal Risk Dashboard")
        self.toolbar = self.iface.addToolBar("CoastalRiskDashboard")
        self.toolbar.setObjectName("CoastalRiskDashboard")
        self.dialog = None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def tr(self, message):
        """Traduzione Qt (lasciato per futura localizzazione)."""
        return QCoreApplication.translate("CoastalRiskDashboard", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Helper per aggiungere azioni a menu e toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    # ------------------------------------------------------------------
    # Ciclo di vita QGIS
    # ------------------------------------------------------------------

    def initGui(self):
        """Chiamata da QGIS all'attivazione del plugin — crea UI."""
        icon_path = os.path.join(self.plugin_dir, "resources", "icons", "icon.png")

        self.add_action(
            icon_path=icon_path,
            text=self.tr("Coastal Risk Dashboard"),
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip=self.tr("Apri la dashboard del rischio costiero"),
            whats_this=self.tr(
                "Calcola e visualizza il Coastal Vulnerability Index "
                "per le isole minori italiane."
            ),
        )

    def unload(self):
        """Chiamata da QGIS alla disattivazione del plugin — rimuove UI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    # ------------------------------------------------------------------
    # Logica principale
    # ------------------------------------------------------------------

    def run(self):
        """Apre la finestra principale del plugin."""
        if self.dialog is None:
            self.dialog = MainDialog(self.iface)

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
