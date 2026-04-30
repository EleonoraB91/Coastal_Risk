# -*- coding: utf-8 -*-
"""
core/demo_data_generator.py
Generatore di dataset sintetici per il test del plugin Italian Minor Islands Coastal Risk.

Crea layer vettoriali in-memory con tratti costieri realistici attorno alle
isole minori italiane, completi dei 4 campi parametro CVI già valorizzati.
Permette di testare l'intero workflow senza disporre di dati reali.
"""

import math
import random
from typing import List, Dict, Tuple, Optional

from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtCore import QVariant

from .shoreline_loader import CVI_FIELD_NAME, RISK_FIELD_NAME, COLOR_FIELD_NAME


# ---------------------------------------------------------------------------
# Profili costieri realistici per isola
# Ogni tratto ha: (geomorfologia, pendenza, uso_suolo, esposizione, descrizione)
# I valori rispecchiano caratteristiche geomorfologiche reali delle isole.
# ---------------------------------------------------------------------------

ISLAND_PROFILES: Dict[str, List[Dict]] = {
    "Lipari": [
        # Costa nord: falesie laviche alte, molto ripide, esposte al Tirreno
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 4.0,
         "descr": "Falesia lavica N — Punta del Legno"},
        {"geom": 1.0, "pend": 1.5, "uso": 1.0, "espos": 4.5,
         "descr": "Falesia lavica NE — Acquacalda"},
        # Costa est: roccia bassa con calette, moderata antropizzazione
        {"geom": 2.0, "pend": 2.0, "uso": 2.5, "espos": 3.0,
         "descr": "Costa rocciosa E — Canneto"},
        {"geom": 2.0, "pend": 2.5, "uso": 3.0, "espos": 2.5,
         "descr": "Spiaggia ghiaiosa E — Marina Lunga"},
        # Centro est: spiaggia sabbiosa, urbanizzata (porto)
        {"geom": 3.0, "pend": 4.0, "uso": 4.5, "espos": 2.0,
         "descr": "Porto e lungomare — centro urbano"},
        # Costa sud: pomice, spiagge bianche, estrattiva
        {"geom": 3.5, "pend": 3.5, "uso": 3.5, "espos": 3.0,
         "descr": "Costa pomice S — Porticello"},
        {"geom": 4.0, "pend": 4.0, "uso": 4.0, "espos": 3.5,
         "descr": "Spiaggia pomice SE — area estrattiva"},
        # Costa ovest: falesie alte, inaccessibile, naturale
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Falesia O — Quattrocchi (inaccessibile)"},
        {"geom": 1.5, "pend": 1.0, "uso": 1.0, "espos": 4.5,
         "descr": "Falesia NO — Punta Castagna"},
        # Insenature protette
        {"geom": 2.5, "pend": 3.0, "uso": 2.0, "espos": 1.5,
         "descr": "Caletta riparata — Valle Muria"},
    ],
    "Vulcano": [
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Falesia vulcanica N — Gran Cratere"},
        {"geom": 4.5, "pend": 4.5, "uso": 1.0, "espos": 4.0,
         "descr": "Costa bassa lavica NE — campo fumarolico"},
        {"geom": 3.0, "pend": 3.5, "uso": 3.0, "espos": 3.0,
         "descr": "Spiaggia nera — Sabbie Nere"},
        {"geom": 3.5, "pend": 4.0, "uso": 4.0, "espos": 2.5,
         "descr": "Porto e Vulcano Piano — zona residenziale"},
        {"geom": 2.0, "pend": 2.0, "uso": 2.0, "espos": 4.5,
         "descr": "Costa S — Vulcanello"},
        {"geom": 4.0, "pend": 4.5, "uso": 1.5, "espos": 3.5,
         "descr": "Costa O — depositi piroclastici"},
    ],
    "Pantelleria": [
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Falesia basaltica N — Punta Spadillo"},
        {"geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 4.5,
         "descr": "Costa lavica NE — Balata dei Turchi"},
        {"geom": 2.0, "pend": 2.0, "uso": 2.0, "espos": 4.0,
         "descr": "Costa E — calette basaltiche"},
        {"geom": 3.0, "pend": 3.5, "uso": 3.5, "espos": 3.0,
         "descr": "Porto Pantelleria — zona urbana"},
        {"geom": 2.5, "pend": 2.5, "uso": 2.0, "espos": 3.5,
         "descr": "Costa S — Cuddia Attalora"},
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Costa O — Punta Fram (molto esposta)"},
        {"geom": 3.5, "pend": 3.0, "uso": 2.5, "espos": 4.0,
         "descr": "Lago Specchio di Venere — area umida"},
    ],
    "Lampedusa": [
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Falesia calcarea N — Punta Tabaccara"},
        {"geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 5.0,
         "descr": "Costa NE — Isola dei Conigli (Area Marina Protetta)"},
        {"geom": 3.0, "pend": 4.0, "uso": 4.5, "espos": 2.0,
         "descr": "Porto e centro — massima antropizzazione"},
        {"geom": 3.5, "pend": 4.0, "uso": 3.5, "espos": 2.5,
         "descr": "Spiaggia dei Conigli — turistica"},
        {"geom": 2.0, "pend": 2.0, "uso": 1.5, "espos": 4.5,
         "descr": "Costa S — falesie calcaree"},
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Costa O — Punta Parrino (molto esposta)"},
    ],
    "Ischia": [
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 4.0,
         "descr": "Falesia tufacea N — Monte Epomeo versante"},
        {"geom": 2.0, "pend": 2.5, "uso": 3.0, "espos": 3.0,
         "descr": "Costa NE — Lacco Ameno"},
        {"geom": 3.0, "pend": 3.5, "uso": 4.5, "espos": 2.0,
         "descr": "Ischia Porto — massima urbanizzazione"},
        {"geom": 3.5, "pend": 4.0, "uso": 4.5, "espos": 2.5,
         "descr": "Spiaggia dei Maronti — turistica"},
        {"geom": 2.5, "pend": 3.0, "uso": 3.5, "espos": 3.5,
         "descr": "Costa S — Forio"},
        {"geom": 4.0, "pend": 4.5, "uso": 2.0, "espos": 4.0,
         "descr": "Costa O bassa — area alluvionale (rischio frana)"},
        {"geom": 1.5, "pend": 1.5, "uso": 1.5, "espos": 4.5,
         "descr": "Costa NO — Punta Imperatore"},
        {"geom": 3.0, "pend": 3.0, "uso": 3.0, "espos": 3.0,
         "descr": "Casamicciola — zona post-sisma 2022"},
    ],
    "Ponza": [
        {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
         "descr": "Falesia trachitica N — Punta della Guardia"},
        {"geom": 2.0, "pend": 2.0, "uso": 1.5, "espos": 4.0,
         "descr": "Costa E — calette trachitiche"},
        {"geom": 3.0, "pend": 3.5, "uso": 4.0, "espos": 2.0,
         "descr": "Porto Ponza — zona urbana"},
        {"geom": 3.5, "pend": 4.0, "uso": 3.5, "espos": 3.0,
         "descr": "Spiaggia Santa Maria — sabbia/ghiaia"},
        {"geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 5.0,
         "descr": "Costa O — falesie molto esposte"},
        {"geom": 2.5, "pend": 3.0, "uso": 2.0, "espos": 3.5,
         "descr": "Costa S — Cala Inferno"},
    ],
}

# Fallback generico per isole non profilate
DEFAULT_PROFILE = [
    {"geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 4.0,
     "descr": "Costa rocciosa esposta"},
    {"geom": 2.5, "pend": 2.5, "uso": 2.0, "espos": 3.0,
     "descr": "Costa rocciosa moderata"},
    {"geom": 3.0, "pend": 3.5, "uso": 3.0, "espos": 3.0,
     "descr": "Costa sabbiosa"},
    {"geom": 3.5, "pend": 4.0, "uso": 4.0, "espos": 2.5,
     "descr": "Area portuale / urbana"},
    {"geom": 4.0, "pend": 4.5, "uso": 2.0, "espos": 4.5,
     "descr": "Costa bassa esposta"},
    {"geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
     "descr": "Falesia inaccessibile"},
]


class DemoDataGenerator:
    """
    Genera layer vettoriali sintetici in-memory per il test del plugin.

    Il layer prodotto contiene:
    - Geometrie lineari (tratti costieri) distribuite attorno all'isola scelta
    - Campi: GEOMORF, PENDENZA, USO_SUOLO, ESPOSIZ (parametri CVI, scala 1–5)
    - Campo TRATTO con descrizione testuale del tratto
    - Campo ISOLA con nome dell'isola
    - Campi CVI, RISCHIO, CVI_COLOR già popolati (pre-calcolati)

    Uso tipico:
        gen = DemoDataGenerator()
        layer = gen.generate("Lipari")
        QgsProject.instance().addMapLayer(layer)
    """

    LOG_TAG = "CoastalRiskDashboard"

    # Nomi dei campi parametro nel layer demo
    FIELD_GEOMORF  = "GEOMORF"
    FIELD_PENDENZA = "PENDENZA"
    FIELD_USO      = "USO_SUOLO"
    FIELD_ESPOS    = "ESPOSIZ"
    FIELD_TRATTO   = "TRATTO"
    FIELD_ISOLA    = "ISOLA"

    def __init__(self):
        random.seed(42)   # seed fisso: risultati riproducibili

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def generate(
        self,
        island_name: str,
        bbox: Tuple[float, float, float, float],
        add_noise: bool = True,
    ) -> QgsVectorLayer:
        """
        Genera un layer di test per l'isola specificata.

        :param island_name: nome dell'isola (usato per il titolo del layer)
        :param bbox:        bounding box WGS84 (lon_min, lat_min, lon_max, lat_max)
        :param add_noise:   se True, aggiunge una piccola variazione casuale
                            ai valori parametro per rendere i dati più realistici
        :return: QgsVectorLayer in-memory già pronto per il calcolo CVI
        """
        profile = ISLAND_PROFILES.get(island_name, DEFAULT_PROFILE)
        layer_name = f"[DEMO] {island_name} — Tratti costieri"

        # Crea layer in-memory (LineString, WGS84)
        layer = QgsVectorLayer("LineString?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()

        # Aggiunge i campi
        provider.addAttributes(self._fields())
        layer.updateFields()

        # Genera le feature
        features = self._build_features(
            island_name, profile, bbox, add_noise
        )
        provider.addFeatures(features)
        layer.updateExtents()

        self._log(
            f"Layer demo generato: '{layer_name}' "
            f"({len(features)} tratti, bbox {bbox})"
        )
        return layer

    def available_islands(self) -> List[str]:
        """Restituisce la lista delle isole con profilo costiero dettagliato."""
        return sorted(ISLAND_PROFILES.keys())

    # ------------------------------------------------------------------
    # Costruzione features
    # ------------------------------------------------------------------

    def _build_features(
        self,
        island_name: str,
        profile: List[Dict],
        bbox: Tuple[float, float, float, float],
        add_noise: bool,
    ) -> List[QgsFeature]:
        """
        Genera le feature distribuendo i tratti costieri lungo il perimetro
        approssimativo dell'isola (ellisse semplificata).
        """
        lon_min, lat_min, lon_max, lat_max = bbox
        cx = (lon_min + lon_max) / 2
        cy = (lat_min + lat_max) / 2
        rx = (lon_max - lon_min) / 2 * 0.85   # raggio X (longitudine)
        ry = (lat_max - lat_min) / 2 * 0.85   # raggio Y (latitudine)

        n = len(profile)
        features = []

        for i, seg in enumerate(profile):
            # Angolo iniziale e finale del tratto (distribuzione uniforme)
            angle_start = 2 * math.pi * i / n
            angle_end   = 2 * math.pi * (i + 1) / n

            # Genera 5 punti per tratto (linea con piccole irregolarità)
            points = []
            steps = 5
            for s in range(steps + 1):
                t = angle_start + (angle_end - angle_start) * s / steps
                # Punto sull'ellisse + rumore per realismo
                noise_r = 1.0 + (random.uniform(-0.08, 0.08) if add_noise else 0)
                lon = cx + rx * noise_r * math.cos(t)
                lat = cy + ry * noise_r * math.sin(t)
                points.append(QgsPointXY(lon, lat))

            geom = QgsGeometry.fromPolylineXY(points)

            # Valori con eventuale rumore ±0.3
            def noisy(v):
                if not add_noise:
                    return round(v, 2)
                return round(max(1.0, min(5.0, v + random.uniform(-0.3, 0.3))), 2)

            g = noisy(seg["geom"])
            p = noisy(seg["pend"])
            u = noisy(seg["uso"])
            e = noisy(seg["espos"])

            # Pre-calcola CVI e classe (coerente con RiskCalculator)
            cvi = round(math.sqrt((g * p * u * e) / 4.0), 3)
            risk_class, color = self._classify_cvi(cvi)

            feat = QgsFeature()
            feat.setGeometry(geom)
            feat.setAttributes([
                g, p, u, e,
                seg["descr"],
                island_name,
                cvi,
                risk_class,
                color,
            ])
            features.append(feat)

        return features

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fields(self) -> List[QgsField]:
        """Restituisce la lista di QgsField per il layer demo."""
        return [
            QgsField(self.FIELD_GEOMORF,  QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_PENDENZA, QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_USO,      QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_ESPOS,    QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_TRATTO,   QVariant.String, "string", 80),
            QgsField(self.FIELD_ISOLA,    QVariant.String, "string", 40),
            # Campi CVI pre-calcolati (pronti per visualizzazione immediata)
            QgsField(CVI_FIELD_NAME,      QVariant.Double, "double", 8, 4),
            QgsField(RISK_FIELD_NAME,     QVariant.String, "string", 20),
            QgsField(COLOR_FIELD_NAME,    QVariant.String, "string", 10),
        ]

    @staticmethod
    def _classify_cvi(cvi: float) -> Tuple[str, str]:
        """Classifica il CVI in classe e colore (coerente con RiskCalculator)."""
        thresholds = [
            (1.5, "Molto Basso", "#2ecc71"),
            (2.5, "Basso",       "#a8d08d"),
            (3.5, "Medio",       "#f1c40f"),
            (4.5, "Alto",        "#e67e22"),
        ]
        for upper, label, color in thresholds:
            if cvi <= upper:
                return label, color
        return "Molto Alto", "#e74c3c"

    @staticmethod
    def _log(msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, "CoastalRiskDashboard", level=level)
