# -*- coding: utf-8 -*-
"""
core/cvi_methods.py
Metodi di calcolo del Coastal Vulnerability Index (CVI).

Implementa quattro metodi scientificamente validati, selezionabili dall'utente:
  1. Gornitz 1991          — formula classica a 4 variabili (default)
  2. USGS Thieler 1999     — formula a 6 variabili, standard americano
  3. Pantusa et al. 2018   — media ponderata, calibrata per il Mediterraneo
  4. Indice lineare        — media aritmetica semplice, per confronto rapido
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from qgis.core import QgsMessageLog, Qgis


# ---------------------------------------------------------------------------
# Definizione parametri per metodo
# ---------------------------------------------------------------------------

@dataclass
class MethodParam:
    """Descrizione di un singolo parametro di input per un metodo CVI."""
    key: str            # chiave interna (usata nel field_map)
    label: str          # etichetta UI
    description: str    # descrizione per l'utente
    scale_desc: str     # descrizione scala 1–5
    weight: float = 1.0 # peso per metodi ponderati


@dataclass
class CVIMethod:
    """Definizione completa di un metodo di calcolo CVI."""
    id: str
    name: str
    short_name: str
    reference: str
    description: str
    formula_display: str   # formula leggibile per l'utente
    params: List[MethodParam]
    range_min: float = 1.0
    range_max: float = 5.0
    thresholds: List[Tuple[float, str, str]] = field(default_factory=list)

    def __post_init__(self):
        if not self.thresholds:
            # Soglie proporzionali al range del metodo
            span = self.range_max - self.range_min
            self.thresholds = [
                (self.range_min + span * 0.20, "Molto Basso", "#2ecc71"),
                (self.range_min + span * 0.40, "Basso",       "#a8d08d"),
                (self.range_min + span * 0.60, "Medio",       "#f1c40f"),
                (self.range_min + span * 0.80, "Alto",        "#e67e22"),
                (float("inf"),                  "Molto Alto",  "#e74c3c"),
            ]


# ---------------------------------------------------------------------------
# Catalogo metodi
# ---------------------------------------------------------------------------

METHOD_GORNITZ = CVIMethod(
    id="gornitz_1991",
    name="Gornitz (1991) — 4 variabili",
    short_name="Gornitz",
    reference="Gornitz V. (1991) — Global coastal hazards from future sea level rise. Palaeogeography, Palaeoclimatology, Palaeoecology.",
    description=(
        "Il metodo più citato in letteratura. Combina 4 variabili geomorfologiche "
        "e antropiche con media geometrica. Adatto per analisi regionali rapide."
    ),
    formula_display="CVI = √( (G × P × U × E) / 4 )",
    params=[
        MethodParam("geomorfologia", "Geomorfologia",   "Tipo di costa",           "1=falesia rocciosa → 5=costa fangosa"),
        MethodParam("pendenza",      "Pendenza",         "Pendenza media %",         "1=>20% → 5=<1%"),
        MethodParam("uso_suolo",     "Uso del suolo",    "Grado di antropizzazione", "1=naturale → 5=urbanizzato"),
        MethodParam("esposizione",   "Esposizione",      "Fetch / vento dominante",  "1=riparata → 5=molto esposta"),
    ],
    range_min=1.0,
    range_max=5.0,
)

METHOD_USGS = CVIMethod(
    id="usgs_thieler_1999",
    name="USGS Thieler & Hammar-Klose (1999) — 6 variabili",
    short_name="USGS",
    reference="Thieler E.R. & Hammar-Klose E.S. (1999) — National Assessment of Coastal Vulnerability to Future Sea-Level Rise. USGS Open-File Report 99-593.",
    description=(
        "Standard americano a 6 variabili. Aggiunge tasso di variazione della linea "
        "di riva e range delle maree rispetto a Gornitz. Più preciso per analisi "
        "multitemporali e contesti con forte variabilità delle maree."
    ),
    formula_display="CVI = √( (G × P × SLR × Onde × Maree × ΔLinea) / 6 )",
    params=[
        MethodParam("geomorfologia", "Geomorfologia",        "Tipo di costa",                "1=falesia → 5=fango"),
        MethodParam("pendenza",      "Pendenza",              "Pendenza media %",              "1=>20% → 5=<1%"),
        MethodParam("slr",           "Innalz. livello mare",  "Sea Level Rise (mm/anno)",      "1=<1.8 → 5=>3.6 mm/a"),
        MethodParam("altezza_onde",  "Altezza onde",          "Altezza d'onda significativa",  "1=<0.55m → 5=>2.0m"),
        MethodParam("range_maree",   "Range maree",           "Escursione di marea (m)",       "1=>6.0m → 5=<1.0m"),
        MethodParam("delta_linea",   "Variaz. linea riva",    "Tasso erosione (m/anno)",       "1=+2.0 → 5=<-2.0 m/a"),
    ],
    range_min=1.0,
    range_max=5.0,
)

METHOD_PANTUSA = CVIMethod(
    id="pantusa_2018",
    name="Pantusa et al. (2018) — Mediterraneo ponderato",
    short_name="Pantusa",
    reference="Pantusa D. et al. (2018) — New Indicators and a Quasi-Dynamic Approach to Coastal Vulnerability Assessment. Water, 10(11), 1536.",
    description=(
        "Metodo sviluppato specificamente per il contesto mediterraneo. "
        "Usa una media ponderata invece della radice quadrata, attribuendo "
        "pesi diversi alle variabili in base alla loro rilevanza nel Mar Mediterraneo "
        "(es. maggiore peso alla geomorfologia, minore alle maree quasi-assenti)."
    ),
    formula_display="CVI = (w₁·G + w₂·P + w₃·U + w₄·E + w₅·SLR) / Σwᵢ",
    params=[
        MethodParam("geomorfologia", "Geomorfologia",       "Tipo di costa",           "1=falesia → 5=fango",    weight=0.30),
        MethodParam("pendenza",      "Pendenza",             "Pendenza media %",         "1=>20% → 5=<1%",         weight=0.20),
        MethodParam("uso_suolo",     "Uso del suolo",        "Grado di antropizzazione", "1=naturale → 5=urbano",  weight=0.20),
        MethodParam("esposizione",   "Esposizione",          "Fetch / vento dominante",  "1=riparata → 5=esposta", weight=0.20),
        MethodParam("slr",           "Innalz. livello mare", "SLR (mm/anno)",            "1=<1.8 → 5=>3.6 mm/a",  weight=0.10),
    ],
    range_min=1.0,
    range_max=5.0,
)

METHOD_LINEAR = CVIMethod(
    id="linear_mean",
    name="Indice lineare — Media aritmetica",
    short_name="Lineare",
    reference="McLaughlin S. & Cooper J.A.G. (2010) — A multi-scale coastal vulnerability index: A tool for coastal managers? Environmental Hazards, 9(3), 233-248.",
    description=(
        "Media aritmetica semplice dei parametri. Più intuitivo e trasparente "
        "della radice geometrica: ogni variabile contribuisce linearmente al risultato. "
        "Utile per confronto con altri metodi e per comunicazione con non esperti."
    ),
    formula_display="CVI = (G + P + U + E) / N",
    params=[
        MethodParam("geomorfologia", "Geomorfologia",   "Tipo di costa",           "1=falesia → 5=fango"),
        MethodParam("pendenza",      "Pendenza",         "Pendenza media %",         "1=>20% → 5=<1%"),
        MethodParam("uso_suolo",     "Uso del suolo",    "Grado di antropizzazione", "1=naturale → 5=urbano"),
        MethodParam("esposizione",   "Esposizione",      "Fetch / vento dominante",  "1=riparata → 5=esposta"),
    ],
    range_min=1.0,
    range_max=5.0,
)

# Registro completo
ALL_METHODS: Dict[str, CVIMethod] = {
    m.id: m for m in [METHOD_GORNITZ, METHOD_USGS, METHOD_PANTUSA, METHOD_LINEAR]
}


# ---------------------------------------------------------------------------
# Dataclass risultati (estende risk_calculator per compatibilità)
# ---------------------------------------------------------------------------

@dataclass
class CVIResultEx:
    """Risultato CVI esteso con informazioni sul metodo usato."""
    cvi_value: float
    cvi_normalized: float   # valore normalizzato 0–1 per confronto tra metodi
    risk_class: str
    risk_color: str
    method_id: str
    feature_id: Optional[int] = None


@dataclass
class CVIStatsEx:
    """Statistiche aggregate con informazioni sul metodo."""
    count: int = 0
    mean_cvi: float = 0.0
    min_cvi: float = 0.0
    max_cvi: float = 0.0
    std_cvi: float = 0.0
    distribution: Dict[str, int] = field(default_factory=dict)
    distribution_pct: Dict[str, float] = field(default_factory=dict)
    method_id: str = ""
    method_name: str = ""


# ---------------------------------------------------------------------------
# Motore di calcolo multi-metodo
# ---------------------------------------------------------------------------

class CVIMethodEngine:
    """
    Calcola il CVI usando uno dei metodi disponibili.

    Uso tipico:
        engine = CVIMethodEngine("gornitz_1991")
        result = engine.calculate({"geomorfologia": 3, "pendenza": 2, ...})
        stats  = engine.compute_stats(results_list)
    """

    RISK_CLASSES = ["Molto Basso", "Basso", "Medio", "Alto", "Molto Alto"]

    def __init__(self, method_id: str = "gornitz_1991"):
        self.method = ALL_METHODS.get(method_id)
        if self.method is None:
            QgsMessageLog.logMessage(
                f"Metodo '{method_id}' non trovato, uso Gornitz di default.",
                "CoastalRiskDashboard", Qgis.Warning
            )
            self.method = METHOD_GORNITZ

    # ------------------------------------------------------------------
    # Calcolo singolo
    # ------------------------------------------------------------------

    def calculate(
        self,
        params: Dict[str, float],
        feature_id: Optional[int] = None,
    ) -> Optional[CVIResultEx]:
        """
        Calcola il CVI per una singola feature.

        :param params:     dizionario {chiave_parametro: valore 1–5}
        :param feature_id: ID feature QGIS opzionale
        :return: CVIResultEx o None se parametri insufficienti
        """
        try:
            cvi = self._compute(params)
        except (KeyError, ValueError, ZeroDivisionError) as e:
            QgsMessageLog.logMessage(
                f"Calcolo CVI fallito (feature {feature_id}): {e}",
                "CoastalRiskDashboard", Qgis.Warning
            )
            return None

        risk_class, color = self._classify(cvi)
        norm = (cvi - self.method.range_min) / (self.method.range_max - self.method.range_min)

        return CVIResultEx(
            cvi_value=round(cvi, 4),
            cvi_normalized=round(max(0.0, min(1.0, norm)), 4),
            risk_class=risk_class,
            risk_color=color,
            method_id=self.method.id,
            feature_id=feature_id,
        )

    def calculate_batch(
        self,
        params_list: List[Dict],
        feature_ids: Optional[List[int]] = None,
    ) -> List[Optional[CVIResultEx]]:
        """Calcola CVI per una lista di dizionari parametro."""
        ids = feature_ids or [None] * len(params_list)
        return [self.calculate(p, fid) for p, fid in zip(params_list, ids)]

    # ------------------------------------------------------------------
    # Statistiche
    # ------------------------------------------------------------------

    def compute_stats(self, results: List[Optional[CVIResultEx]]) -> CVIStatsEx:
        valid = [r for r in results if r is not None]
        if not valid:
            return CVIStatsEx(method_id=self.method.id, method_name=self.method.name)

        values = [r.cvi_value for r in valid]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n

        distribution = {cls: 0 for cls in self.RISK_CLASSES}
        for r in valid:
            distribution[r.risk_class] += 1

        distribution_pct = {
            cls: round(cnt / n * 100, 1)
            for cls, cnt in distribution.items()
        }

        return CVIStatsEx(
            count=n,
            mean_cvi=round(mean, 4),
            min_cvi=round(min(values), 4),
            max_cvi=round(max(values), 4),
            std_cvi=round(math.sqrt(variance), 4),
            distribution=distribution,
            distribution_pct=distribution_pct,
            method_id=self.method.id,
            method_name=self.method.name,
        )

    # ------------------------------------------------------------------
    # Lettura parametri da feature QGIS
    # ------------------------------------------------------------------

    def read_params_from_feature(
        self,
        feature,
        field_map: Dict[str, str],
    ) -> Dict[str, float]:
        """
        Estrae i parametri richiesti dal metodo corrente dalla feature QGIS.

        :param feature:   QgsFeature
        :param field_map: {chiave_param: nome_campo_layer}
        :return: dizionario {chiave_param: valore_float}
        """
        params = {}
        for param in self.method.params:
            field_name = field_map.get(param.key, "")
            if not field_name:
                params[param.key] = 3.0   # default medio se non mappato
                continue
            try:
                val = float(feature[field_name] or 3.0)
                params[param.key] = max(1.0, min(5.0, val))
            except (TypeError, ValueError):
                params[param.key] = 3.0
        return params

    # ------------------------------------------------------------------
    # Formule per metodo
    # ------------------------------------------------------------------

    def _compute(self, params: Dict[str, float]) -> float:
        mid = self.method.id

        if mid == "gornitz_1991":
            g = params["geomorfologia"]
            p = params["pendenza"]
            u = params["uso_suolo"]
            e = params["esposizione"]
            return math.sqrt((g * p * u * e) / 4.0)

        elif mid == "usgs_thieler_1999":
            g   = params["geomorfologia"]
            p   = params["pendenza"]
            slr = params["slr"]
            ond = params["altezza_onde"]
            mar = params["range_maree"]
            dl  = params["delta_linea"]
            return math.sqrt((g * p * slr * ond * mar * dl) / 6.0)

        elif mid == "pantusa_2018":
            total_weight = sum(param.weight for param in self.method.params)
            weighted_sum = sum(
                params.get(param.key, 3.0) * param.weight
                for param in self.method.params
            )
            return weighted_sum / total_weight

        elif mid == "linear_mean":
            vals = [params[p.key] for p in self.method.params]
            return sum(vals) / len(vals)

        else:
            raise ValueError(f"Formula non implementata per metodo '{mid}'.")

    def _classify(self, cvi: float) -> Tuple[str, str]:
        for threshold, label, color in self.method.thresholds:
            if cvi <= threshold:
                return label, color
        return "Molto Alto", "#e74c3c"
