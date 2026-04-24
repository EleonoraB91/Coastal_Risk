# -*- coding: utf-8 -*-
"""
Coastal Risk Dashboard
Plugin QGIS per il monitoraggio del rischio costiero nelle isole minori italiane.

Entry point richiesto da QGIS per caricare il plugin.
"""

def classFactory(iface):
    """
    Funzione obbligatoria chiamata da QGIS al caricamento del plugin.
    
    :param iface: istanza di QgisInterface fornita da QGIS
    :return: istanza della classe principale del plugin
    """
    from .plugin_main import CoastalRiskDashboard
    return CoastalRiskDashboard(iface)
