# -*- coding: utf-8 -*-
"""
core/cvi_engine.py
Motore principale del calcolo CVI: orchestra ShorelineLoader e RiskCalculator
in un unico flusso di lavoro con callback di progresso.
Fase 2.
"""

from typing import Callable, Dict, Optional, Tuple
from qgis.core import QgsVectorLayer

from .shoreline_loader import ShorelineLoader
from .risk_calculator import RiskCalculator, CVIParameters, CVIResult, CVIStats
from .style_manager import StyleManager


class CVIEngine:
    """
    Motore principale del calcolo CVI.

    Esegue l'intero pipeline:
        1. Valida il layer e i campi
        2. Legge i parametri da ogni feature
        3. Calcola il CVI per ogni feature
        4. Scrive i risultati sul layer
        5. Calcola le statistiche aggregate

    Uso tipico:
        engine = CVIEngine(iface)
        ok, msg, stats = engine.run(
            layer=layer,
            field_map={
                "geomorfologia": "GEOM",
                "pendenza":      "SLOPE",
                "uso_suolo":     "LAND_USE",
                "esposizione":   "EXPOSURE",
            },
            progress_callback=lambda p, m: print(f"{p}% — {m}")
        )
    """

    def __init__(self, iface):
        self.iface = iface
        self.loader = ShorelineLoader(iface)
        self.calculator = RiskCalculator()
        self.styler = StyleManager()

        # Risultati dell'ultima esecuzione (accessibili dopo run())
        self.last_results: Dict[int, CVIResult] = {}
        self.last_stats: Optional[CVIStats] = None

    # ------------------------------------------------------------------
    # Pipeline principale
    # ------------------------------------------------------------------

    def run(
        self,
        layer: QgsVectorLayer,
        field_map: Dict[str, str],
        progress_callback: Optional[Callable[[int, str], None]] = None,
        method_engine=None,
        const_values: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str, Optional[CVIStats]]:
        """
        Esegue il calcolo CVI completo sul layer.

        :param layer:             layer vettoriale con i parametri CVI negli attributi
        :param field_map:         {parametro: nome_campo_layer} (o __const_key_val__ per costanti)
        :param progress_callback: funzione(pct, msg) per aggiornare l'UI
        :param method_engine:     CVIMethodEngine opzionale per metodi multipli
        :param const_values:      {chiave_param: valore_float} per parametri costanti
        :return: (successo, messaggio, CVIStats)
        """
        const_values = const_values or {}
        self._progress(progress_callback, 0, "Avvio calcolo CVI...")

        # 1. Validazione layer
        ok, msg = self.loader.validate(layer)
        if not ok:
            return False, msg, None
        self._progress(progress_callback, 10, "Layer validato ✓")

        # 2. Verifica campi parametri — salta i parametri coperti da costante
        real_field_map = {
            k: v for k, v in field_map.items()
            if v and not v.startswith("__const_")
        }
        ok, msg = self.loader.check_param_fields(layer, real_field_map)
        if not ok:
            return False, msg, None
        self._progress(progress_callback, 20, "Campi parametri verificati ✓")

        # 3. Aggiunge campi output (CVI, RISCHIO, CVI_COLOR) se assenti
        ok = self.loader.ensure_cvi_fields(layer)
        if not ok:
            return False, (
                "Impossibile aggiungere i campi CVI al layer.\n"
                "Assicurati che il layer sia in un formato modificabile "
                "(GeoPackage o Shapefile)."
            ), None
        self._progress(progress_callback, 30, "Campi output pronti ✓")

        # 4. Lettura parametri da ogni feature
        params_list = self.loader.read_params(layer, real_field_map)
        total = len(params_list)
        if total == 0:
            return False, "Il layer non contiene feature da elaborare.", None
        self._progress(progress_callback, 40, f"Letti parametri per {total} tratti ✓")

        # 5. Calcolo CVI batch
        if method_engine is not None:
            results_list = []
            for feat in layer.getFeatures():
                # Legge parametri dal layer
                param_dict = method_engine.read_params_from_feature(feat, real_field_map)
                # Sovrascrive con valori costanti per i parametri non nel layer
                for k, v in const_values.items():
                    if k not in param_dict or not real_field_map.get(k):
                        param_dict[k] = v
                result = method_engine.calculate(param_dict, feature_id=feat.id())
                if result is not None:
                    from .risk_calculator import CVIResult
                    compat = CVIResult(
                        cvi_value=result.cvi_value,
                        risk_class=result.risk_class,
                        risk_color=result.risk_color,
                        feature_id=result.feature_id,
                    )
                    results_list.append(compat)
                else:
                    results_list.append(None)
        else:
            results_list = self.calculator.calculate_batch(params_list)
        self._progress(progress_callback, 70, f"CVI calcolato per {total} tratti ✓")

        # 6. Costruisce dizionario feature_id → CVIResult
        results_dict: Dict[int, CVIResult] = {}
        for result in results_list:
            if result is not None:
                results_dict[result.feature_id] = result

        # 7. Scrittura risultati sul layer
        written = self.loader.write_cvi_results(layer, results_dict)
        self._progress(progress_callback, 85, f"Risultati scritti su {written}/{total} feature ✓")

        # 8. Statistiche aggregate
        stats = self.calculator.compute_stats(results_list)
        self._progress(progress_callback, 95, "Statistiche calcolate ✓")

        # 9. Applica simbologia automatica CVI (verde → rosso)
        self.styler.apply_cvi_style(layer)
        self._progress(progress_callback, 98, "Simbologia applicata ✓")

        # Salva per uso esterno
        self.last_results = results_dict
        self.last_stats = stats

        self._progress(progress_callback, 100, "✅ Calcolo completato!")

        summary = (
            f"Calcolo completato su {written} tratti costieri.\n"
            f"CVI medio: {stats.mean_cvi:.3f}  |  "
            f"Min: {stats.min_cvi:.3f}  |  Max: {stats.max_cvi:.3f}\n"
            f"Classe predominante: {self._dominant_class(stats)}"
        )
        return True, summary, stats

    # ------------------------------------------------------------------
    # Calcolo manuale da valori numerici (per test / input da UI)
    # ------------------------------------------------------------------

    def calculate_manual(
        self,
        geomorfologia: float,
        pendenza: float,
        uso_suolo: float,
        esposizione: float,
    ) -> Tuple[bool, str, Optional[CVIResult]]:
        """
        Calcola il CVI da valori inseriti manualmente (non da layer).
        Utile per preview / test nella UI.

        :return: (successo, messaggio, CVIResult)
        """
        try:
            params = CVIParameters(
                geomorfologia=geomorfologia,
                pendenza=pendenza,
                uso_suolo=uso_suolo,
                esposizione=esposizione,
            )
            result = self.calculator.calculate(params)
            msg = (
                f"CVI = {result.cvi_value}  →  Classe: {result.risk_class}"
            )
            return True, msg, result
        except ValueError as e:
            return False, str(e), None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _progress(
        callback: Optional[Callable[[int, str], None]],
        pct: int,
        msg: str,
    ):
        if callback:
            callback(pct, msg)

    @staticmethod
    def _dominant_class(stats: CVIStats) -> str:
        if not stats.distribution:
            return "N/D"
        return max(stats.distribution, key=stats.distribution.get)
