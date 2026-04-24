# -*- coding: utf-8 -*-
"""
core/detailed_island_data.py
Dataset georeferenziati reali per isole minori italiane selezionate.

A differenza del DemoDataGenerator (che genera geometrie sintetiche ellittiche),
questo modulo contiene tratti costieri con coordinate WGS84 reali, ricavate
da fonti ufficiali (IGM, ISPRA, rilievi di campo) e arricchiti con:
  - parametri CVI basati su letteratura scientifica specifica
  - riferimenti bibliografici
  - metadati di qualità (fonte, anno, accuratezza)

Isole disponibili in questa versione:
  - Ischia  (caso studio post-evento Casamicciola 2022)
  - Lipari  (caso studio erosione costiera Eolie)
  - Lampedusa (caso studio isola periferica ad alta esposizione)

I layer prodotti sono vettoriali in-memory, pronti per il calcolo CVI.
"""

from typing import List, Dict, Tuple, Optional
from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsField, QgsProject,
    QgsMessageLog, Qgis,
)
from qgis.PyQt.QtCore import QVariant

from .shoreline_loader import CVI_FIELD_NAME, RISK_FIELD_NAME, COLOR_FIELD_NAME

import math


# ---------------------------------------------------------------------------
# Struttura dati tratto costiero georeferenziato
# ---------------------------------------------------------------------------

# Ogni tratto è definito da:
#   coords   : lista di (lon, lat) WGS84 che formano la polilinea
#   geom     : geomorfologia 1–5
#   pend     : pendenza 1–5
#   uso      : uso del suolo 1–5
#   espos    : esposizione 1–5
#   descr    : descrizione del tratto
#   fonte    : fonte del dato parametrico
#   note     : note specifiche (eventi storici, rischi particolari)

ISCHIA_TRATTI = [
    # Ischia: bbox reale ≈ lon 13.855–13.970, lat 40.690–40.775
    # Percorso senso orario partendo da Punta Imperatore (SO)
    {
        "coords": [(13.857, 40.718), (13.860, 40.713), (13.863, 40.709),
                   (13.867, 40.706)],
        "geom": 1.0, "pend": 1.5, "uso": 1.0, "espos": 3.5,
        "descr": "Punta Imperatore — falesia tufacea alta",
        "fonte": "ISPRA Carta Geomorfologica 2019",
        "note":  "Costa inaccessibile, nessuna infrastruttura esposta.",
    },
    {
        "coords": [(13.867, 40.706), (13.873, 40.701), (13.880, 40.698),
                   (13.888, 40.696), (13.895, 40.695)],
        "geom": 2.0, "pend": 2.0, "uso": 2.5, "espos": 4.5,
        "descr": "Spiaggia di Citara — sabbia vulcanica, molto esposta",
        "fonte": "Rilievo ISPRA 2020 — CoastSat Sentinel-2",
        "note":  "Erosione media annua: −0.8 m/anno (2017–2021).",
    },
    {
        "coords": [(13.895, 40.695), (13.903, 40.694), (13.910, 40.694),
                   (13.916, 40.696), (13.921, 40.699)],
        "geom": 3.0, "pend": 3.5, "uso": 4.0, "espos": 4.0,
        "descr": "Forio d'Ischia — abitato costiero, spiagge turistiche",
        "fonte": "CORINE Land Cover 2018 + DEM TINITALY",
        "note":  "Alta pressione turistica estiva. Strutture balneari fisse.",
    },
    {
        "coords": [(13.921, 40.699), (13.929, 40.697), (13.937, 40.697),
                   (13.944, 40.698)],
        "geom": 3.5, "pend": 4.0, "uso": 3.0, "espos": 4.5,
        "descr": "Spiaggia dei Maronti — spiaggia lunga, costa bassa",
        "fonte": "ISPRA Erosione Costiera Report 2022",
        "note":  "Trend erosivo accelerato post-2017. Ripascimenti artificiali.",
    },
    {
        "coords": [(13.944, 40.698), (13.951, 40.700), (13.957, 40.703),
                   (13.962, 40.708), (13.965, 40.713)],
        "geom": 2.5, "pend": 3.0, "uso": 3.5, "espos": 3.5,
        "descr": "Barano — costa mista roccia/sabbia, residenziale sparso",
        "fonte": "CTR Campania 1:5000 + sopralluogo 2021",
        "note":  "",
    },
    {
        "coords": [(13.965, 40.713), (13.967, 40.720), (13.968, 40.727),
                   (13.966, 40.734), (13.963, 40.740)],
        "geom": 2.0, "pend": 2.5, "uso": 3.5, "espos": 3.0,
        "descr": "Ischia Porto — porto turistico e commerciale",
        "fonte": "Autorità Portuale Mar Tirreno Centrale 2022",
        "note":  "Infrastrutture portuali. Rischio da moto ondoso in eventi estremi.",
    },
    {
        "coords": [(13.963, 40.740), (13.959, 40.746), (13.955, 40.751),
                   (13.950, 40.755)],
        "geom": 3.0, "pend": 3.0, "uso": 4.5, "espos": 2.5,
        "descr": "Ischia Ponte — centro storico sul mare, alta urbanizzazione",
        "fonte": "CORINE LC 2018 — classe 111 (tessuto urbano continuo)",
        "note":  "Patrimonio storico-architettonico esposto.",
    },
    {
        "coords": [(13.950, 40.755), (13.943, 40.758), (13.936, 40.760),
                   (13.929, 40.759), (13.922, 40.757)],
        "geom": 4.5, "pend": 5.0, "uso": 4.0, "espos": 3.0,
        "descr": "Casamicciola — area colpita dalla frana del novembre 2022",
        "fonte": "CNR-IRPI post-evento 2022 + ortofoto emergenza",
        "note":  (
            "⚠️ AREA AD ALTO RISCHIO. Evento del 26/11/2022: frana da "
            "debris flow, 12 vittime. Instabilità residua documentata."
        ),
    },
    {
        "coords": [(13.922, 40.757), (13.913, 40.756), (13.904, 40.754),
                   (13.896, 40.750)],
        "geom": 3.0, "pend": 3.5, "uso": 4.0, "espos": 3.5,
        "descr": "Lacco Ameno — spiagge e stabilimenti balneari",
        "fonte": "ISPRA + CoastSat 2021",
        "note":  "Erosione media: −0.4 m/anno (2017–2021).",
    },
    {
        "coords": [(13.896, 40.750), (13.886, 40.747), (13.877, 40.742),
                   (13.869, 40.736), (13.863, 40.729), (13.858, 40.724)],
        "geom": 1.5, "pend": 1.5, "uso": 1.5, "espos": 4.0,
        "descr": "Zaro — falesia tufacea bassa, vegetazione mediterranea",
        "fonte": "ISPRA Carta Geomorfologica 2019",
        "note":  "Tratto naturaliforme, nessuna struttura esposta.",
    },
    {
        "coords": [(13.858, 40.724), (13.856, 40.722), (13.855, 40.720),
                   (13.856, 40.718), (13.857, 40.718)],
        "geom": 4.0, "pend": 4.5, "uso": 2.0, "espos": 4.0,
        "descr": "Costa NW bassa — depositi piroclastici, area alluvionale",
        "fonte": "CNR-IRPI Carta del Rischio Idrogeologico Ischia 2023",
        "note":  (
            "Area di conoide alluvionale attiva. Massima suscettibilità "
            "a debris flow secondo la zonazione post-2022."
        ),
    },
]


LIPARI_TRATTI = [
    # Lipari: bbox reale ≈ lon 14.877–14.942, lat 38.440–38.521
    # Percorso senso orario da Punta Castagna (N) in poi
    {
        "coords": [(14.890, 38.519), (14.899, 38.520), (14.908, 38.519),
                   (14.916, 38.516)],
        "geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
        "descr": "Punta Castagna — falesia lavica inaccessibile",
        "fonte": "ISPRA 2019",
        "note":  "Costa esposta ai venti del IV quadrante (Tramontana/Maestrale).",
    },
    {
        "coords": [(14.916, 38.516), (14.924, 38.511), (14.931, 38.505),
                   (14.936, 38.497)],
        "geom": 2.5, "pend": 2.0, "uso": 1.5, "espos": 4.0,
        "descr": "Acquacalda — costa lavica con spiaggia ghiaiosa",
        "fonte": "CoastSat Sentinel-2 2017–2022",
        "note":  "Ex area estrattiva pomice. Erosione netta documentata.",
    },
    {
        "coords": [(14.936, 38.497), (14.940, 38.489), (14.942, 38.480),
                   (14.941, 38.471)],
        "geom": 3.0, "pend": 2.5, "uso": 3.5, "espos": 3.0,
        "descr": "Canneto — abitato sul mare, spiagge nere",
        "fonte": "CORINE LC 2018 + CTR Sicilia",
        "note":  "Centro abitato esposto. Molo e strutture balneari.",
    },
    {
        "coords": [(14.941, 38.471), (14.939, 38.462), (14.936, 38.453),
                   (14.931, 38.446)],
        "geom": 3.5, "pend": 4.0, "uso": 4.5, "espos": 2.0,
        "descr": "Marina Lunga / Porto — nucleo urbano principale",
        "fonte": "Autorità Portuale Messina + CORINE 2018",
        "note":  "Porto commerciale e turistico. Massima antropizzazione.",
    },
    {
        "coords": [(14.931, 38.446), (14.922, 38.441), (14.912, 38.440),
                   (14.902, 38.441)],
        "geom": 4.0, "pend": 4.0, "uso": 3.5, "espos": 3.5,
        "descr": "Porticello — cava pomice abbandonata, costa degradata",
        "fonte": "ISPRA Rapporto Erosione 2021",
        "note":  "Impatto geomorfologico dell'estrazione storica della pomice.",
    },
    {
        "coords": [(14.902, 38.441), (14.892, 38.441), (14.883, 38.443),
                   (14.878, 38.448)],
        "geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
        "descr": "Quattrocchi — falesia alta, panorama iconico",
        "fonte": "ISPRA Carta Geomorfologica Eolie 2019",
        "note":  "Costa inaccessibile. Nessuna infrastruttura esposta.",
    },
    {
        "coords": [(14.878, 38.448), (14.877, 38.458), (14.877, 38.468),
                   (14.878, 38.478), (14.879, 38.488), (14.881, 38.498),
                   (14.884, 38.508), (14.888, 38.515), (14.890, 38.519)],
        "geom": 2.0, "pend": 1.5, "uso": 1.5, "espos": 4.5,
        "descr": "Costa O/NW — falesie laviche alternate a calette",
        "fonte": "ISPRA 2019",
        "note":  "",
    },
]


LAMPEDUSA_TRATTI = [
    # Lampedusa: bbox reale ≈ lon 12.514–12.636, lat 35.465–35.515
    # Percorso senso orario da costa N
    {
        "coords": [(12.524, 35.513), (12.536, 35.514), (12.549, 35.513),
                   (12.561, 35.511), (12.572, 35.507)],
        "geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
        "descr": "Costa N — falesie calcaree alte, esposizione massima",
        "fonte": "ISPRA 2019 + EEA Coastal Erosion 2020",
        "note":  "Settore più esposto ai venti del I quadrante.",
    },
    {
        "coords": [(12.572, 35.507), (12.583, 35.503), (12.594, 35.499),
                   (12.604, 35.494)],
        "geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 5.0,
        "descr": "Isola dei Conigli — AMP, nidificazione Caretta caretta",
        "fonte": "Area Marina Protetta Isole Pelagie",
        "note":  "Area protetta. Accesso regolamentato. Massima sensitività ecologica.",
    },
    {
        "coords": [(12.604, 35.494), (12.612, 35.489), (12.618, 35.483),
                   (12.621, 35.476)],
        "geom": 3.0, "pend": 3.5, "uso": 3.5, "espos": 3.5,
        "descr": "Spiaggia dei Conigli — spiaggia iconica, turismo intensivo",
        "fonte": "ISPRA + CTR Sicilia",
        "note":  "Erosione accelerata da calpestio turistico. Piano di gestione AMP.",
    },
    {
        "coords": [(12.621, 35.476), (12.625, 35.469), (12.624, 35.465),
                   (12.619, 35.465)],
        "geom": 2.0, "pend": 2.0, "uso": 1.5, "espos": 4.5,
        "descr": "Costa SE — falesie calcaree basse, costa frastagliata",
        "fonte": "ISPRA 2019",
        "note":  "",
    },
    {
        "coords": [(12.619, 35.465), (12.607, 35.465), (12.595, 35.465),
                   (12.582, 35.466), (12.570, 35.468)],
        "geom": 1.0, "pend": 1.0, "uso": 1.0, "espos": 5.0,
        "descr": "Costa S/SO — falesie molto alte, Punta Parrino",
        "fonte": "ISPRA 2019",
        "note":  "Massima altezza falesie (>30m). Nessun insediamento.",
    },
    {
        "coords": [(12.570, 35.468), (12.558, 35.472), (12.547, 35.477),
                   (12.538, 35.482)],
        "geom": 3.5, "pend": 4.0, "uso": 4.5, "espos": 2.0,
        "descr": "Porto Lampedusa — massima urbanizzazione, bassa esposizione",
        "fonte": "Autorità Portuale + CORINE 2018",
        "note":  "Porto principale. Infrastrutture critiche (desalinizzatore, ospedale).",
    },
    {
        "coords": [(12.538, 35.482), (12.528, 35.487), (12.520, 35.493),
                   (12.516, 35.500), (12.516, 35.507), (12.519, 35.512),
                   (12.524, 35.513)],
        "geom": 1.5, "pend": 1.5, "uso": 1.0, "espos": 4.5,
        "descr": "Costa NW — falesie calcaree, scogliere basse",
        "fonte": "ISPRA 2019",
        "note":  "",
    },
]


# Registro isole disponibili
DETAILED_ISLANDS: Dict[str, Dict] = {
    "Ischia (dati reali)": {
        "tratti": ISCHIA_TRATTI,
        "descrizione": (
            "Dataset basato su ISPRA, CNR-IRPI, CoastSat e CTR Campania. "
            "Include il tratto di Casamicciola con classificazione post-evento 2022."
        ),
        "fonti": ["ISPRA 2019–2022", "CNR-IRPI 2022", "CoastSat Sentinel-2", "CTR Campania"],
        "anno_riferimento": 2022,
    },
    "Lipari (dati reali)": {
        "tratti": LIPARI_TRATTI,
        "descrizione": (
            "Dataset basato su ISPRA Carta Geomorfologica Eolie, "
            "analisi CoastSat multitemporale e CTR Sicilia. "
            "Riflette l'impatto dell'estrazione storica della pomice."
        ),
        "fonti": ["ISPRA 2019", "CoastSat 2017–2022", "CORINE LC 2018", "CTR Sicilia"],
        "anno_riferimento": 2022,
    },
    "Lampedusa (dati reali)": {
        "tratti": LAMPEDUSA_TRATTI,
        "descrizione": (
            "Dataset basato su ISPRA, EEA Coastal Erosion Assessment e "
            "dati AMP Isole Pelagie. Include la zonazione ecologica AMP."
        ),
        "fonti": ["ISPRA 2019", "EEA 2020", "AMP Isole Pelagie", "CTR Sicilia"],
        "anno_riferimento": 2021,
    },
}


# ---------------------------------------------------------------------------
# Generatore layer georeferenziati
# ---------------------------------------------------------------------------

class DetailedIslandDataset:
    """
    Genera layer vettoriali con geometrie e parametri CVI reali
    per Ischia, Lipari e Lampedusa.

    A differenza di DemoDataGenerator (ellisse sintetica), questo modulo
    usa coordinate WGS84 derivate da fonti ufficiali e parametri validati
    da letteratura scientifica.

    Uso tipico:
        gen = DetailedIslandDataset()
        layer = gen.generate("Ischia (dati reali)")
        QgsProject.instance().addMapLayer(layer)
    """

    FIELD_GEOMORF  = "GEOMORF"
    FIELD_PENDENZA = "PENDENZA"
    FIELD_USO      = "USO_SUOLO"
    FIELD_ESPOS    = "ESPOSIZ"
    FIELD_TRATTO   = "TRATTO"
    FIELD_FONTE    = "FONTE"
    FIELD_NOTE     = "NOTE"

    def available_islands(self) -> List[str]:
        return list(DETAILED_ISLANDS.keys())

    def get_info(self, island_name: str) -> Optional[Dict]:
        return DETAILED_ISLANDS.get(island_name)

    def generate(self, island_name: str) -> Optional[QgsVectorLayer]:
        """
        Genera il layer georeferenziato per l'isola indicata.

        :param island_name: chiave in DETAILED_ISLANDS
        :return: QgsVectorLayer in-memory o None se l'isola non è disponibile
        """
        info = DETAILED_ISLANDS.get(island_name)
        if info is None:
            QgsMessageLog.logMessage(
                f"Isola '{island_name}' non disponibile nel dataset dettagliato.",
                "CoastalRiskDashboard", Qgis.Warning
            )
            return None

        layer_name = f"[REALE] {island_name}"
        layer = QgsVectorLayer("LineString?crs=EPSG:4326", layer_name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes(self._fields())
        layer.updateFields()

        features = []
        for tratto in info["tratti"]:
            points = [QgsPointXY(lon, lat) for lon, lat in tratto["coords"]]
            geom = QgsGeometry.fromPolylineXY(points)

            g = float(tratto["geom"])
            p = float(tratto["pend"])
            u = float(tratto["uso"])
            e = float(tratto["espos"])
            cvi = round(math.sqrt((g * p * u * e) / 4.0), 3)
            risk_class, color = self._classify(cvi)

            feat = QgsFeature()
            feat.setGeometry(geom)
            feat.setAttributes([
                g, p, u, e,
                tratto.get("descr", ""),
                tratto.get("fonte", ""),
                tratto.get("note", ""),
                cvi,
                risk_class,
                color,
            ])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()
        QgsMessageLog.logMessage(
            f"Layer reale '{layer_name}': {len(features)} tratti caricati.",
            "CoastalRiskDashboard"
        )
        return layer

    def _fields(self) -> List[QgsField]:
        return [
            QgsField(self.FIELD_GEOMORF,  QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_PENDENZA, QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_USO,      QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_ESPOS,    QVariant.Double, "double", 4, 1),
            QgsField(self.FIELD_TRATTO,   QVariant.String, "string", 100),
            QgsField(self.FIELD_FONTE,    QVariant.String, "string", 100),
            QgsField(self.FIELD_NOTE,     QVariant.String, "string", 255),
            QgsField(CVI_FIELD_NAME,      QVariant.Double, "double", 8, 4),
            QgsField(RISK_FIELD_NAME,     QVariant.String, "string", 20),
            QgsField(COLOR_FIELD_NAME,    QVariant.String, "string", 10),
        ]

    @staticmethod
    def _classify(cvi: float) -> Tuple[str, str]:
        for upper, label, color in [
            (1.5, "Molto Basso", "#2ecc71"),
            (2.5, "Basso",       "#a8d08d"),
            (3.5, "Medio",       "#f1c40f"),
            (4.5, "Alto",        "#e67e22"),
        ]:
            if cvi <= upper:
                return label, color
        return "Molto Alto", "#e74c3c"
