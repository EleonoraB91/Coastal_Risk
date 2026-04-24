# -*- coding: utf-8 -*-
"""
core/shoreline_loader.py
Gestione, caricamento e validazione dei layer della linea di riva.
Fase 2: implementazione completa.
"""

from typing import Optional, Tuple, List, Dict
from qgis.core import (
    QgsVectorLayer, QgsProject, QgsMapLayer,
    QgsField, QgsFeature, QgsWkbTypes,
    QgsVectorDataProvider, QgsMessageLog, Qgis,
)
from qgis.PyQt.QtCore import QVariant

# Nome del campo CVI scritto sul layer
CVI_FIELD_NAME = "CVI"
RISK_FIELD_NAME = "RISCHIO"
COLOR_FIELD_NAME = "CVI_COLOR"

# Campi attesi per i parametri (devono esistere nel layer o essere mappabili)
REQUIRED_PARAM_FIELDS = ["geomorf", "pendenza", "uso_suolo", "esposiz"]


class ShorelineLoader:
    """
    Carica, valida e prepara layer vettoriali della linea di riva
    per il calcolo del CVI.

    Uso tipico:
        loader = ShorelineLoader(iface)
        layer = loader.load_from_project(layer_id)
        ok, msg = loader.validate(layer)
        if ok:
            loader.ensure_cvi_fields(layer)
    """

    LOG_TAG = "CoastalRiskDashboard"

    def __init__(self, iface):
        self.iface = iface

    # ------------------------------------------------------------------
    # Caricamento
    # ------------------------------------------------------------------

    def load_from_file(self, path: str, layer_name: str = "Linea di Riva") -> QgsVectorLayer:
        """
        Carica un layer vettoriale da file e lo aggiunge al progetto QGIS.

        :param path: percorso assoluto al file (.shp, .gpkg, .geojson…)
        :param layer_name: nome da assegnare al layer nel pannello layer
        :return: QgsVectorLayer caricato
        :raises IOError: se il file non è leggibile o il formato non è supportato
        """
        layer = QgsVectorLayer(path, layer_name, "ogr")
        if not layer.isValid():
            raise IOError(
                f"Impossibile caricare il file: {path}\n"
                "Verifica che il file esista e che il formato sia supportato "
                "(Shapefile, GeoPackage, GeoJSON, ecc.)."
            )
        QgsProject.instance().addMapLayer(layer)
        self._log(f"Layer caricato: {layer_name} ({layer.featureCount()} feature)")
        return layer

    def load_from_project(self, layer_id: str) -> QgsVectorLayer:
        """
        Recupera un layer vettoriale già presente nel progetto QGIS tramite ID.

        :param layer_id: ID univoco del layer (da QgsProject.instance().mapLayers())
        :return: QgsVectorLayer
        :raises KeyError: se il layer non esiste nel progetto
        :raises TypeError: se il layer non è di tipo vettoriale
        """
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer is None:
            raise KeyError(f"Layer con ID '{layer_id}' non trovato nel progetto.")
        if layer.type() != QgsMapLayer.VectorLayer:
            raise TypeError(
                f"Il layer '{layer.name()}' non è vettoriale "
                f"(tipo: {layer.type()})."
            )
        return layer

    def get_vector_layers(self) -> List[Tuple[str, str]]:
        """
        Restituisce tutti i layer vettoriali del progetto come lista di tuple (nome, id).

        :return: lista di (nome_layer, layer_id)
        """
        result = []
        for lid, layer in QgsProject.instance().mapLayers().items():
            if layer.type() == QgsMapLayer.VectorLayer:
                result.append((layer.name(), lid))
        return result

    # ------------------------------------------------------------------
    # Validazione
    # ------------------------------------------------------------------

    def validate(self, layer: QgsVectorLayer) -> Tuple[bool, str]:
        """
        Verifica che il layer sia adatto al calcolo CVI:
        - Deve essere vettoriale e valido
        - Deve avere geometria lineare o poligonale
        - Deve avere almeno una feature

        :return: (True, "") se valido, (False, messaggio) altrimenti
        """
        if layer is None:
            return False, "Nessun layer fornito."

        if not layer.isValid():
            return False, f"Il layer '{layer.name()}' non è valido."

        geom_type = layer.geometryType()
        if geom_type not in (QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry):
            return False, (
                f"Il layer '{layer.name()}' ha geometria non supportata "
                f"(attesa: Linea o Poligono, trovata: {QgsWkbTypes.displayString(layer.wkbType())})."
            )

        if layer.featureCount() == 0:
            return False, f"Il layer '{layer.name()}' non contiene feature."

        return True, ""

    def check_param_fields(self, layer: QgsVectorLayer, field_map: Dict[str, str]) -> Tuple[bool, str]:
        """
        Verifica che i campi dei parametri CVI esistano nel layer.

        :param layer: layer da controllare
        :param field_map: dizionario {parametro: nome_campo} es. {"geomorfologia": "GEOM"}
        :return: (True, "") se tutti i campi esistono, (False, lista_mancanti) altrimenti
        """
        field_names = [f.name() for f in layer.fields()]
        missing = [
            f"{param} → '{col}'"
            for param, col in field_map.items()
            if col and col not in field_names
        ]
        if missing:
            return False, "Campi mancanti nel layer:\n• " + "\n• ".join(missing)
        return True, ""

    # ------------------------------------------------------------------
    # Preparazione campi output
    # ------------------------------------------------------------------

    def ensure_cvi_fields(self, layer: QgsVectorLayer) -> bool:
        """
        Aggiunge i campi CVI, RISCHIO e CVI_COLOR al layer se non esistono già.
        Richiede che il layer sia modificabile (o lo mette temporaneamente in edit mode).

        :param layer: layer su cui aggiungere i campi
        :return: True se i campi sono stati aggiunti o già presenti
        """
        existing = [f.name() for f in layer.fields()]
        fields_to_add = []

        if CVI_FIELD_NAME not in existing:
            fields_to_add.append(QgsField(CVI_FIELD_NAME, QVariant.Double, "double", 10, 4))
        if RISK_FIELD_NAME not in existing:
            fields_to_add.append(QgsField(RISK_FIELD_NAME, QVariant.String, "string", 20))
        if COLOR_FIELD_NAME not in existing:
            fields_to_add.append(QgsField(COLOR_FIELD_NAME, QVariant.String, "string", 10))

        if not fields_to_add:
            return True  # già tutti presenti

        caps = layer.dataProvider().capabilities()
        if not (caps & QgsVectorDataProvider.AddAttributes):
            self._log(
                f"Il layer '{layer.name()}' non supporta l'aggiunta di campi. "
                "Prova a convertirlo in GeoPackage o Shapefile.",
                level=Qgis.Warning,
            )
            return False

        layer.startEditing()
        ok = layer.dataProvider().addAttributes(fields_to_add)
        layer.updateFields()
        layer.commitChanges()

        if ok:
            self._log(
                f"Aggiunti {len(fields_to_add)} campi al layer '{layer.name()}': "
                + ", ".join(f.name() for f in fields_to_add)
            )
        return ok

    def write_cvi_results(
        self,
        layer: QgsVectorLayer,
        results: Dict[int, "CVIResult"],  # feature_id → CVIResult
    ) -> int:
        """
        Scrive i valori CVI, classe di rischio e colore nelle feature del layer.

        :param layer: layer vettoriale target (deve avere i campi CVI/RISCHIO/CVI_COLOR)
        :param results: dizionario {feature_id: CVIResult}
        :return: numero di feature aggiornate con successo
        """
        cvi_idx   = layer.fields().indexOf(CVI_FIELD_NAME)
        risk_idx  = layer.fields().indexOf(RISK_FIELD_NAME)
        color_idx = layer.fields().indexOf(COLOR_FIELD_NAME)

        if -1 in (cvi_idx, risk_idx, color_idx):
            self._log(
                "Campi CVI mancanti nel layer. Esegui prima ensure_cvi_fields().",
                level=Qgis.Critical,
            )
            return 0

        layer.startEditing()
        updated = 0
        for fid, result in results.items():
            if result is None:
                continue
            ok = layer.changeAttributeValue(fid, cvi_idx,   result.cvi_value)
            ok &= layer.changeAttributeValue(fid, risk_idx,  result.risk_class)
            ok &= layer.changeAttributeValue(fid, color_idx, result.risk_color)
            if ok:
                updated += 1

        layer.commitChanges()
        self._log(f"Scritti risultati CVI su {updated}/{len(results)} feature.")
        return updated

    # ------------------------------------------------------------------
    # Lettura parametri dal layer
    # ------------------------------------------------------------------

    def read_params(
        self,
        layer: QgsVectorLayer,
        field_map: Dict[str, str],
    ) -> List["CVIParameters"]:
        """
        Legge i parametri CVI direttamente dagli attributi del layer.

        :param layer: layer vettoriale sorgente
        :param field_map: dizionario {parametro: nome_campo}
                          es. {"geomorfologia": "GEOM", "pendenza": "SLOPE", ...}
        :return: lista di CVIParameters, uno per feature
        """
        from .risk_calculator import CVIParameters

        params_list = []
        for feature in layer.getFeatures():
            try:
                params = CVIParameters(
                    geomorfologia=float(feature[field_map["geomorfologia"]] or 3),
                    pendenza=float(feature[field_map["pendenza"]] or 3),
                    uso_suolo=float(feature[field_map["uso_suolo"]] or 3),
                    esposizione=float(feature[field_map["esposizione"]] or 3),
                    feature_id=feature.id(),
                )
            except (KeyError, TypeError, ValueError) as e:
                self._log(
                    f"Feature {feature.id()}: parametri non leggibili ({e}). "
                    "Usati valori di default (3.0).",
                    level=Qgis.Warning,
                )
                params = CVIParameters(
                    geomorfologia=3.0, pendenza=3.0,
                    uso_suolo=3.0, esposizione=3.0,
                    feature_id=feature.id(),
                )
            params_list.append(params)
        return params_list

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)
