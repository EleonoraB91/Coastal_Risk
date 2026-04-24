# -*- coding: utf-8 -*-
"""
core/risk_calculator.py
Calcolo del Coastal Vulnerability Index (CVI).
Fase 2: implementazione completa con calcolo singolo, batch e statistiche.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


@dataclass
class CVIParameters:
    """
    Parametri di input per il calcolo del CVI.
    Ogni variabile è classificata su scala 1–5 (1=basso rischio, 5=alto rischio).
    
    Tabella di classificazione:
    
    Geomorfologia:
        1 = Costa rocciosa alta (falesie)
        2 = Costa rocciosa bassa
        3 = Costa sabbiosa
        4 = Costa con dune basse
        5 = Costa bassa e fangosa / paludosa
    
    Pendenza (% media tratto):
        1 = > 20%
        2 = 10–20%
        3 = 5–10%
        4 = 1–5%
        5 = < 1%
    
    Uso del suolo:
        1 = Vegetazione naturale densa / area protetta
        2 = Macchia mediterranea / pascolo
        3 = Agricolo
        4 = Residenziale sparso
        5 = Urbanizzato / impermeabilizzato
    
    Esposizione al vento / fetch:
        1 = Costa riparata (< 10 km fetch)
        2 = Parzialmente riparata
        3 = Moderatamente esposta
        4 = Esposta
        5 = Molto esposta (> 200 km fetch)
    """
    geomorfologia: float
    pendenza: float
    uso_suolo: float
    esposizione: float
    feature_id: Optional[int] = None   # ID feature QGIS di riferimento

    def validate(self) -> Tuple[bool, str]:
        """
        Verifica che tutti i parametri siano nel range 1–5.
        :return: (True, "") se valido, (False, messaggio_errore) altrimenti
        """
        fields = {
            "geomorfologia": self.geomorfologia,
            "pendenza": self.pendenza,
            "uso_suolo": self.uso_suolo,
            "esposizione": self.esposizione,
        }
        for name, val in fields.items():
            if val is None:
                return False, f"Parametro '{name}' mancante."
            if not (1.0 <= float(val) <= 5.0):
                return False, f"Parametro '{name}' fuori range 1–5 (valore: {val})."
        return True, ""


@dataclass
class CVIResult:
    """Risultato del calcolo CVI per un singolo tratto costiero."""
    cvi_value: float
    risk_class: str        # "Molto Basso" | "Basso" | "Medio" | "Alto" | "Molto Alto"
    risk_color: str        # Colore HEX per la simbologia
    feature_id: Optional[int] = None
    params: Optional[CVIParameters] = None


@dataclass
class CVIStats:
    """Statistiche aggregate sui risultati CVI di un layer / isola."""
    count: int = 0
    mean_cvi: float = 0.0
    min_cvi: float = 0.0
    max_cvi: float = 0.0
    std_cvi: float = 0.0
    distribution: Dict[str, int] = field(default_factory=dict)     # classe → n. feature
    distribution_pct: Dict[str, float] = field(default_factory=dict)  # classe → %


class RiskCalculator:
    """
    Calcola il Coastal Vulnerability Index (CVI) secondo la formula:

        CVI = sqrt( (G * P * U * E) / 4 )

    Range risultante: 1.0 (minimo) → 5.0 (massimo)

    Esempio:
        calc = RiskCalculator()
        params = CVIParameters(geomorfologia=3, pendenza=2, uso_suolo=4, esposizione=3)
        result = calc.calculate(params)
        print(result.cvi_value, result.risk_class)
    """

    # Soglie di classificazione (upper bound incluso)
    THRESHOLDS: List[Tuple[float, str, str]] = [
        (1.5,         "Molto Basso", "#2ecc71"),
        (2.5,         "Basso",       "#a8d08d"),
        (3.5,         "Medio",       "#f1c40f"),
        (4.5,         "Alto",        "#e67e22"),
        (float("inf"), "Molto Alto", "#e74c3c"),
    ]

    RISK_CLASSES = ["Molto Basso", "Basso", "Medio", "Alto", "Molto Alto"]

    # ------------------------------------------------------------------
    # Calcolo singolo
    # ------------------------------------------------------------------

    def calculate(self, params: CVIParameters) -> CVIResult:
        """
        Calcola il CVI per un singolo tratto costiero.

        :param params: CVIParameters con i 4 valori classificati 1–5
        :return: CVIResult con valore, classe e colore
        :raises ValueError: se i parametri non sono nel range 1–5
        """
        valid, msg = params.validate()
        if not valid:
            raise ValueError(f"Parametri CVI non validi: {msg}")

        cvi = math.sqrt(
            (params.geomorfologia * params.pendenza *
             params.uso_suolo * params.esposizione) / 4.0
        )

        risk_class, color = self._classify(cvi)

        return CVIResult(
            cvi_value=round(cvi, 3),
            risk_class=risk_class,
            risk_color=color,
            feature_id=params.feature_id,
            params=params,
        )

    # ------------------------------------------------------------------
    # Calcolo batch
    # ------------------------------------------------------------------

    def calculate_batch(self, params_list: List[CVIParameters]) -> List[CVIResult]:
        """
        Calcola il CVI per una lista di tratti costieri.
        I tratti con parametri non validi vengono saltati (log di avviso).

        :param params_list: lista di CVIParameters
        :return: lista di CVIResult (stesso ordine dell'input)
        """
        results = []
        for params in params_list:
            try:
                results.append(self.calculate(params))
            except ValueError as e:
                # Feature non calcolabile: inserisce None come segnaposto
                results.append(None)
        return results

    # ------------------------------------------------------------------
    # Statistiche
    # ------------------------------------------------------------------

    def compute_stats(self, results: List[CVIResult]) -> CVIStats:
        """
        Calcola statistiche aggregate su una lista di CVIResult.

        :param results: lista di CVIResult (None viene ignorato)
        :return: CVIStats con media, min, max, deviazione standard e distribuzione
        """
        valid = [r for r in results if r is not None]
        if not valid:
            return CVIStats()

        values = [r.cvi_value for r in valid]
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n

        # Distribuzione per classe
        distribution = {cls: 0 for cls in self.RISK_CLASSES}
        for r in valid:
            distribution[r.risk_class] += 1

        distribution_pct = {
            cls: round(cnt / n * 100, 1)
            for cls, cnt in distribution.items()
        }

        return CVIStats(
            count=n,
            mean_cvi=round(mean, 3),
            min_cvi=round(min(values), 3),
            max_cvi=round(max(values), 3),
            std_cvi=round(math.sqrt(variance), 3),
            distribution=distribution,
            distribution_pct=distribution_pct,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify(self, cvi: float) -> Tuple[str, str]:
        """Restituisce (classe_rischio, colore_hex) per un valore CVI."""
        for threshold, risk_class, color in self.THRESHOLDS:
            if cvi <= threshold:
                return risk_class, color
        return "Molto Alto", "#e74c3c"

    @staticmethod
    def classify_geomorfologia(tipo: str) -> float:
        """Converte una descrizione testuale in valore 1–5."""
        mapping = {
            "falesia": 1.0, "roccia alta": 1.0,
            "roccia bassa": 2.0,
            "sabbia": 3.0, "ghiaia": 2.5,
            "dune basse": 4.0,
            "fango": 5.0, "palude": 5.0, "laguna": 4.5,
        }
        return mapping.get(tipo.lower().strip(), 3.0)

    @staticmethod
    def classify_pendenza(pendenza_pct: float) -> float:
        """Converte la pendenza in % nel valore classificato 1–5."""
        if pendenza_pct > 20:   return 1.0
        if pendenza_pct > 10:   return 2.0
        if pendenza_pct > 5:    return 3.0
        if pendenza_pct > 1:    return 4.0
        return 5.0
