# -*- coding: utf-8 -*-
"""
core/island_locator.py
Gestione del zoom e della navigazione per le isole minori italiane.
Fase 3.

Contiene le coordinate (bounding box WGS84) delle principali isole minori italiane
e fornisce metodi per zoomare il canvas QGIS sull'isola selezionata.
"""

from typing import Dict, Optional, Tuple
from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsMessageLog,
    Qgis,
)

# Tipo: (lon_min, lat_min, lon_max, lat_max) in WGS84
BBox = Tuple[float, float, float, float]


class IslandLocator:
    """
    Fornisce coordinate e funzioni di navigazione per le isole minori italiane.

    Uso tipico:
        locator = IslandLocator(iface)
        locator.zoom_to("Lipari")
        bbox = locator.get_bbox("Pantelleria")
    """

    LOG_TAG = "CoastalRiskDashboard"

    # Bounding box WGS84 (lon_min, lat_min, lon_max, lat_max) + centroide
    # Margine ~0.05° attorno all'isola per una vista confortevole
    ISLANDS: Dict[str, Dict] = {
        # ── Isole Eolie ────────────────────────────────────────────────
        "Lipari": {
            "bbox": (14.88, 38.42, 14.99, 38.52),
            "centro": (14.935, 38.465),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Vulcano": {
            "bbox": (14.96, 38.38, 15.02, 38.44),
            "centro": (14.978, 38.404),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Stromboli": {
            "bbox": (15.19, 38.77, 15.26, 38.83),
            "centro": (15.213, 38.789),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Panarea": {
            "bbox": (15.04, 38.62, 15.08, 38.66),
            "centro": (15.064, 38.638),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Salina": {
            "bbox": (14.82, 38.53, 14.90, 38.60),
            "centro": (14.869, 38.563),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Filicudi": {
            "bbox": (14.52, 38.53, 14.59, 38.60),
            "centro": (14.570, 38.570),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        "Alicudi": {
            "bbox": (14.32, 38.51, 14.38, 38.56),
            "centro": (14.350, 38.540),
            "arcipelago": "Eolie",
            "regione": "Sicilia",
        },
        # ── Isole Ponziane ─────────────────────────────────────────────
        "Ponza": {
            "bbox": (12.92, 40.86, 12.98, 40.93),
            "centro": (12.957, 40.899),
            "arcipelago": "Ponziane",
            "regione": "Lazio",
        },
        "Ventotene": {
            "bbox": (13.40, 40.78, 13.44, 40.81),
            "centro": (13.425, 40.797),
            "arcipelago": "Ponziane",
            "regione": "Lazio",
        },
        # ── Isole Flegree / Campane ────────────────────────────────────
        "Ischia": {
            "bbox": (13.85, 40.69, 13.97, 40.77),
            "centro": (13.904, 40.730),
            "arcipelago": "Flegree",
            "regione": "Campania",
        },
        "Procida": {
            "bbox": (14.01, 40.74, 14.05, 40.78),
            "centro": (14.027, 40.759),
            "arcipelago": "Flegree",
            "regione": "Campania",
        },
        "Capri": {
            "bbox": (14.19, 40.54, 14.27, 40.57),
            "centro": (14.242, 40.551),
            "arcipelago": "Flegree",
            "regione": "Campania",
        },
        # ── Isole Egadi ────────────────────────────────────────────────
        "Favignana": {
            "bbox": (12.27, 37.91, 12.36, 37.96),
            "centro": (12.328, 37.929),
            "arcipelago": "Egadi",
            "regione": "Sicilia",
        },
        "Levanzo": {
            "bbox": (12.31, 37.99, 12.36, 38.03),
            "centro": (12.337, 38.015),
            "arcipelago": "Egadi",
            "regione": "Sicilia",
        },
        "Marettimo": {
            "bbox": (12.05, 37.95, 12.09, 37.99),
            "centro": (12.068, 37.970),
            "arcipelago": "Egadi",
            "regione": "Sicilia",
        },
        # ── Isole Pelagie ──────────────────────────────────────────────
        "Lampedusa": {
            "bbox": (12.52, 35.47, 12.63, 35.52),
            "centro": (12.600, 35.506),
            "arcipelago": "Pelagie",
            "regione": "Sicilia",
        },
        "Linosa": {
            "bbox": (12.83, 35.84, 12.87, 35.87),
            "centro": (12.862, 35.861),
            "arcipelago": "Pelagie",
            "regione": "Sicilia",
        },
        # ── Isola singole ──────────────────────────────────────────────
        "Pantelleria": {
            "bbox": (11.96, 36.70, 12.06, 36.84),
            "centro": (12.002, 36.773),
            "arcipelago": None,
            "regione": "Sicilia",
        },
        "Ustica": {
            "bbox": (13.13, 38.68, 13.18, 38.72),
            "centro": (13.184, 38.706),
            "arcipelago": None,
            "regione": "Sicilia",
        },
        # ── Arcipelago della Maddalena ─────────────────────────────────
        "La Maddalena": {
            "bbox": (9.37, 41.19, 9.43, 41.24),
            "centro": (9.411, 41.212),
            "arcipelago": "Maddalena",
            "regione": "Sardegna",
        },
        "Caprera": {
            "bbox": (9.44, 41.18, 9.52, 41.23),
            "centro": (9.466, 41.200),
            "arcipelago": "Maddalena",
            "regione": "Sardegna",
        },
        # ── Isole Sulcitane ────────────────────────────────────────────
        "Carloforte (S. Pietro)": {
            "bbox": (8.17, 39.11, 8.26, 39.18),
            "centro": (8.315, 39.145),
            "arcipelago": "Sulcitane",
            "regione": "Sardegna",
        },
        "Sant'Antioco": {
            "bbox": (8.42, 38.99, 8.49, 39.07),
            "centro": (8.456, 39.026),
            "arcipelago": "Sulcitane",
            "regione": "Sardegna",
        },
        # ── Arcipelago Toscano ─────────────────────────────────────────
        "Elba": {
            "bbox": (10.13, 42.71, 10.46, 42.82),
            "centro": (10.267, 42.762),
            "arcipelago": "Toscano",
            "regione": "Toscana",
        },
        "Giglio": {
            "bbox": (10.85, 42.33, 10.91, 42.38),
            "centro": (10.899, 42.361),
            "arcipelago": "Toscano",
            "regione": "Toscana",
        },
        "Capraia": {
            "bbox": (9.82, 43.03, 9.87, 43.07),
            "centro": (9.838, 43.048),
            "arcipelago": "Toscano",
            "regione": "Toscana",
        },
        "Pianosa": {
            "bbox": (10.06, 42.57, 10.11, 42.60),
            "centro": (10.083, 42.584),
            "arcipelago": "Toscano",
            "regione": "Toscana",
        },
    }

    def __init__(self, iface):
        self.iface = iface

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def island_names(self) -> list:
        """Restituisce la lista ordinata dei nomi delle isole disponibili."""
        return sorted(self.ISLANDS.keys())

    def get_info(self, name: str) -> Optional[Dict]:
        """Restituisce il dizionario info dell'isola, o None se non trovata."""
        return self.ISLANDS.get(name)

    def get_bbox(self, name: str) -> Optional[BBox]:
        """Restituisce il bounding box WGS84 dell'isola."""
        info = self.ISLANDS.get(name)
        return info["bbox"] if info else None

    def zoom_to(self, name: str, margin_deg: float = 0.02) -> bool:
        """
        Zooma il canvas QGIS sull'isola indicata.
        Trasforma il bbox da WGS84 al CRS del progetto corrente.

        :param name:       nome dell'isola (deve essere in ISLANDS)
        :param margin_deg: margine aggiuntivo in gradi attorno al bbox
        :return: True se lo zoom è riuscito
        """
        info = self.ISLANDS.get(name)
        if info is None:
            self._log(f"Isola '{name}' non trovata nel database.", Qgis.Warning)
            return False

        lon_min, lat_min, lon_max, lat_max = info["bbox"]
        # Aggiunge margine
        lon_min -= margin_deg
        lat_min -= margin_deg
        lon_max += margin_deg
        lat_max += margin_deg

        # Bounding box in WGS84
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        rect_wgs84 = QgsRectangle(lon_min, lat_min, lon_max, lat_max)

        # Trasforma al CRS del progetto
        project_crs = QgsProject.instance().crs()
        if project_crs != wgs84 and project_crs.isValid():
            transform = QgsCoordinateTransform(wgs84, project_crs, QgsProject.instance())
            try:
                rect_proj = transform.transformBoundingBox(rect_wgs84)
            except Exception as e:
                self._log(f"Trasformazione CRS fallita: {e}", Qgis.Warning)
                rect_proj = rect_wgs84
        else:
            rect_proj = rect_wgs84

        canvas = self.iface.mapCanvas()
        canvas.setExtent(rect_proj)
        canvas.refresh()

        self._log(f"Zoom su {name} ({info.get('regione', '?')}).")
        return True

    def zoom_to_all_islands(self) -> bool:
        """
        Zooma sulla vista d'insieme di tutte le isole minori italiane
        (bbox approssimativo del Mar Mediterraneo centrale).
        """
        # Bbox che copre tutta l'Italia insulare: Tirreno + Sicilia + Sardegna
        overview_bbox = (8.0, 35.0, 16.5, 44.5)
        lon_min, lat_min, lon_max, lat_max = overview_bbox

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        rect_wgs84 = QgsRectangle(lon_min, lat_min, lon_max, lat_max)
        project_crs = QgsProject.instance().crs()

        if project_crs != wgs84 and project_crs.isValid():
            transform = QgsCoordinateTransform(wgs84, project_crs, QgsProject.instance())
            try:
                rect_proj = transform.transformBoundingBox(rect_wgs84)
            except Exception:
                rect_proj = rect_wgs84
        else:
            rect_proj = rect_wgs84

        canvas = self.iface.mapCanvas()
        canvas.setExtent(rect_proj)
        canvas.refresh()
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)
