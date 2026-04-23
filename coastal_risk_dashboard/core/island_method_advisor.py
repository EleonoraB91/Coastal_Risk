# -*- coding: utf-8 -*-
"""
core/island_method_advisor.py
Raccomandazioni del metodo CVI per isola e valori costanti preconfigurati.

Per ogni isola minore italiana fornisce:
  - metodo CVI raccomandato dalla letteratura scientifica specifica
  - motivazione scientifica della scelta
  - riferimento bibliografico
  - valori costanti preconfigurati per i parametri che non derivano
    da attributi del layer (SLR, altezza onde, range maree, ecc.)

I valori costanti permettono di usare metodi a più variabili (es. USGS)
anche quando il layer contiene solo i 4 parametri base, inserendo
i valori aggiuntivi come costanti per l'intera isola.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List


# ---------------------------------------------------------------------------
# Strutture dati
# ---------------------------------------------------------------------------

@dataclass
class ConstantParam:
    """
    Valore costante per un parametro che non varia per tratto
    ma è uniforme sull'intera isola (es. SLR, range maree).
    """
    key: str           # chiave parametro (uguale a MethodParam.key)
    value: float       # valore classificato 1–5
    raw_value: str     # valore fisico originale (es. "2.3 mm/anno")
    source: str        # fonte bibliografica del dato


@dataclass
class IslandMethodProfile:
    """Profilo metodologico completo per un'isola."""
    island_name: str
    recommended_method: str          # ID metodo (es. "pantusa_2018")
    reason: str                      # motivazione scientifica
    reference: str                   # riferimento bibliografico
    alternative_methods: List[str]   # metodi alternativi accettabili
    constants: Dict[str, ConstantParam] = field(default_factory=dict)
    notes: str = ""


# ---------------------------------------------------------------------------
# Profili per isola
# ---------------------------------------------------------------------------

ISLAND_PROFILES: Dict[str, IslandMethodProfile] = {

    # ── Isole Eolie ────────────────────────────────────────────────────

    "Lipari": IslandMethodProfile(
        island_name="Lipari",
        recommended_method="pantusa_2018",
        reason=(
            "Isola vulcanica nel Mediterraneo con costa prevalentemente rocciosa "
            "e falesie laviche alte. Il metodo Pantusa è calibrato per questo contesto: "
            "attribuisce maggior peso alla geomorfologia (0.30) rispetto agli altri "
            "parametri, penalizzando le aree con depositi piroclastici friabili. "
            "Il range di marea trascurabile nel Tirreno rende l'USGS meno accurato."
        ),
        reference=(
            "Anfuso G. et al. (2011) — Coastal sensitivity/vulnerability "
            "characterization and ranking: a review. J. Coast. Res. 61, 33–54. "
            "Doukakis E. (2005) — Coastal vulnerability and risk parameters. "
            "Eur. Water 11/12, 3–7."
        ),
        alternative_methods=["gornitz_1991", "linear_mean"],
        constants={
            "slr": ConstantParam(
                key="slr", value=2.0,
                raw_value="~2.3 mm/anno (Mar Tirreno, stazione mareografica Palermo)",
                source="ISPRA — Annuario dei Dati Ambientali 2022",
            ),
            "altezza_onde": ConstantParam(
                key="altezza_onde", value=3.0,
                raw_value="Hs media ~0.8m; Hs estrema 98° percentile ~3.2m",
                source="Boccotti P. et al. — Meteo-marino Tirreno Meridionale",
            ),
            "range_maree": ConstantParam(
                key="range_maree", value=5.0,
                raw_value="~0.20m (marea quasi-assente, Mar Tirreno)",
                source="ISPRA — Rete Mareografica Nazionale, stazione Milazzo",
            ),
            "delta_linea": ConstantParam(
                key="delta_linea", value=3.0,
                raw_value="−0.3 / −0.8 m/anno (Canneto-Acquacalda, CoastSat 2017–2022)",
                source="Lirer L. et al. (2010) + analisi CoastSat Sentinel-2",
            ),
        },
        notes="Prestare particolare attenzione alle aree di cava pomice (Porticello, Acquacalda).",
    ),

    "Vulcano": IslandMethodProfile(
        island_name="Vulcano",
        recommended_method="pantusa_2018",
        reason=(
            "Costa vulcanica attiva con materiali piroclastici altamente erodibili "
            "nella zona nord (Gran Cratere). La geomorfologia è il parametro dominante. "
            "Pantusa et al. è preferibile per il Mediterraneo; l'attività idrotermale "
            "(fumarole costiere) introduce una variabile di instabilità non catturata "
            "dai metodi standard ma approssimabile con valori elevati di geomorfologia."
        ),
        reference=(
            "Anzidei M. et al. (2017) — Coastal structure, sea-level changes and "
            "vertical motion of the land in the Mediterranean. "
            "Geological Society Special Publication 388."
        ),
        alternative_methods=["gornitz_1991"],
        constants={
            "slr": ConstantParam(
                key="slr", value=2.0,
                raw_value="~2.3 mm/anno",
                source="ISPRA 2022 — stazione Milazzo",
            ),
            "altezza_onde": ConstantParam(
                key="altezza_onde", value=3.0,
                raw_value="Hs media ~0.9m",
                source="Boccotti et al.",
            ),
            "range_maree": ConstantParam(
                key="range_maree", value=5.0,
                raw_value="~0.20m",
                source="ISPRA RMN",
            ),
            "delta_linea": ConstantParam(
                key="delta_linea", value=3.0,
                raw_value="variabile, stima media",
                source="Analisi CoastSat",
            ),
        },
    ),

    "Stromboli": IslandMethodProfile(
        island_name="Stromboli",
        recommended_method="pantusa_2018",
        reason=(
            "Vulcano attivo con rischio tsunami da frana sottomarina documentato "
            "(evento 2002, 2019). La costa NW (Sciara del Fuoco) è soggetta a "
            "continuo apporto di materiale vulcanico e instabilità. "
            "Il metodo Pantusa con peso elevato sulla geomorfologia è il più adatto."
        ),
        reference=(
            "Tinti S. et al. (2006) — The 30 December 2002 Stromboli tsunami. "
            "Bull. Volcanol. 68, 462–479."
        ),
        alternative_methods=["gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.3 mm/anno", "ISPRA 2022"),
            "altezza_onde": ConstantParam("altezza_onde", 4.0, "Hs ~1.2m (esposizione elevata NW)", "Boccotti et al."),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.20m", "ISPRA RMN"),
            "delta_linea": ConstantParam("delta_linea", 4.0, "Sciara del Fuoco: tasso molto variabile", "Tinti et al."),
        },
        notes="La Sciara del Fuoco (costa NW) richiede valutazione separata per rischio vulcanico-costiero.",
    ),

    # ── Isole Campane ──────────────────────────────────────────────────

    "Ischia": IslandMethodProfile(
        island_name="Ischia",
        recommended_method="pantusa_2018",
        reason=(
            "Post-evento Casamicciola 2022 (debris flow), la letteratura CNR-IRPI "
            "indica un approccio ponderato simile a Pantusa come il più appropriato, "
            "con peso aumentato per geomorfologia (instabilità versanti-costa) e pendenza. "
            "L'USGS non cattura adeguatamente il rischio da frana costiera che è il "
            "processo dominante su questo vulcano quiescente."
        ),
        reference=(
            "Fiorillo F. et al. (2023) — The November 2022 Casamicciola landslide. "
            "Landslides 20, 1–12. "
            "Mazzoli S. et al. (2021) — Coastal vulnerability of Ischia Island. "
            "Marine Geology."
        ),
        alternative_methods=["gornitz_1991", "linear_mean"],
        constants={
            "slr": ConstantParam(
                key="slr", value=2.0,
                raw_value="~2.2 mm/anno (stazione mareografica Napoli)",
                source="ISPRA — RMN Napoli 2022",
            ),
            "altezza_onde": ConstantParam(
                key="altezza_onde", value=3.0,
                raw_value="Hs media 0.7m; Hs estrema ~3.0m (burrasche di Libeccio)",
                source="Rete Ondametrica Nazionale — Boa Ponza",
            ),
            "range_maree": ConstantParam(
                key="range_maree", value=5.0,
                raw_value="~0.25m (Golfo di Napoli)",
                source="ISPRA RMN — stazione Napoli",
            ),
            "delta_linea": ConstantParam(
                key="delta_linea", value=3.0,
                raw_value="−0.4 m/anno (Maronti); stabile per coste rocciose",
                source="CoastSat Sentinel-2 2017–2022",
            ),
        },
        notes=(
            "Per Casamicciola applicare valori elevati di geomorfologia (4.5–5.0) "
            "e pendenza (5.0) in quanto area classificata ad alto rischio frana "
            "da CNR-IRPI post-evento 2022."
        ),
    ),

    "Procida": IslandMethodProfile(
        island_name="Procida",
        recommended_method="gornitz_1991",
        reason=(
            "Isola tufacea piccola e quasi interamente urbanizzata. "
            "La semplicità del Gornitz è adeguata: la variabilità dei parametri "
            "tra i tratti è limitata e i dati ondametrici specifici non sono "
            "disponibili a questa scala. La costa è prevalentemente bassa e "
            "antropizzata, con rischio dominante da storm surge."
        ),
        reference=(
            "Budillon F. et al. (2018) — Coastal morphodynamics of the "
            "Campanian islands. Marine Geology."
        ),
        alternative_methods=["linear_mean"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.2 mm/anno", "ISPRA RMN Napoli"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.7m", "RON Boa Ponza"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.25m", "ISPRA RMN Napoli"),
            "delta_linea": ConstantParam("delta_linea", 3.0, "stima media", "CoastSat"),
        },
    ),

    "Capri": IslandMethodProfile(
        island_name="Capri",
        recommended_method="gornitz_1991",
        reason=(
            "Costa prevalentemente costituita da falesie calcaree alte e stabili. "
            "Il Gornitz con 4 variabili è sufficiente: la geomorfologia rocciosa "
            "domina il risultato e non giustifica la complessità aggiuntiva di "
            "metodi a 6 variabili. L'erosione è localmente significativa solo "
            "nelle calette sabbiose (Marina Piccola, Marina Grande)."
        ),
        reference=(
            "Budillon F. et al. (2018) — Coastal morphodynamics of the "
            "Campanian islands. Marine Geology."
        ),
        alternative_methods=["linear_mean"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.2 mm/anno", "ISPRA RMN Napoli"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.7m", "RON Boa Ponza"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.25m", "ISPRA RMN Napoli"),
            "delta_linea": ConstantParam("delta_linea", 2.0, "falesie stabili; calette −0.2 m/anno", "ISPRA 2021"),
        },
    ),

    # ── Isole Siciliane ────────────────────────────────────────────────

    "Lampedusa": IslandMethodProfile(
        island_name="Lampedusa",
        recommended_method="usgs_thieler_1999",
        reason=(
            "Isola calcarea piatta nel Canale di Sicilia con esposizione massima. "
            "La boa di Mazara del Vallo fornisce dati ondametrici affidabili e il "
            "tasso di SLR è ben documentato. L'USGS è il metodo più accurato perché "
            "l'altezza d'onda è il parametro dominante per questa isola, e il metodo "
            "lo valorizza esplicitamente. Unico caso italiano dove l'AMP ha adottato "
            "un approccio USGS-like nella gestione costiera."
        ),
        reference=(
            "Anfuso G. et al. (2011) — Coastal sensitivity/vulnerability "
            "characterization. J. Coast. Res. 61, 33–54. "
            "Piano di Gestione AMP Isole Pelagie (2022)."
        ),
        alternative_methods=["pantusa_2018", "gornitz_1991"],
        constants={
            "slr": ConstantParam(
                key="slr", value=2.0,
                raw_value="~2.4 mm/anno (Canale di Sicilia, staz. Porto Empedocle)",
                source="ISPRA — RMN 2022",
            ),
            "altezza_onde": ConstantParam(
                key="altezza_onde", value=4.0,
                raw_value="Hs media 1.1m; Hs 98° percentile ~4.5m (Boa Mazara del Vallo)",
                source="Rete Ondametrica Nazionale — Boa Mazara del Vallo 2004–2022",
            ),
            "range_maree": ConstantParam(
                key="range_maree", value=5.0,
                raw_value="~0.30m (Canale di Sicilia)",
                source="ISPRA RMN — stazione Porto Empedocle",
            ),
            "delta_linea": ConstantParam(
                key="delta_linea", value=3.0,
                raw_value="−0.3 m/anno (Spiaggia Conigli); stabile per falesie",
                source="EEA Coastal Erosion Assessment 2020",
            ),
        },
        notes="L'Isola dei Conigli (AMP) va trattata con classificazione ecologica separata.",
    ),

    "Pantelleria": IslandMethodProfile(
        island_name="Pantelleria",
        recommended_method="pantusa_2018",
        reason=(
            "Isola vulcanica nel Canale di Sicilia con costa interamente rocciosa. "
            "Anfuso et al. (2011) raccomanda esplicitamente la media ponderata "
            "per isole vulcaniche con costa rocciosa nel Mediterraneo. "
            "Il range di marea irrilevante e la predominanza assoluta di falesie "
            "basaltiche rendono l'USGS sovrastimato per questa isola."
        ),
        reference=(
            "Anfuso G. et al. (2011) — Coastal sensitivity/vulnerability "
            "characterization. J. Coast. Res. 61, 33–54."
        ),
        alternative_methods=["gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.4 mm/anno", "ISPRA RMN Porto Empedocle"),
            "altezza_onde": ConstantParam("altezza_onde", 4.0, "Hs media 1.0m; molto esposta a SO", "RON Boa Mazara"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.25m", "ISPRA RMN"),
            "delta_linea": ConstantParam("delta_linea", 2.0, "falesie stabili, erosione trascurabile", "ISPRA 2021"),
        },
    ),

    "Favignana": IslandMethodProfile(
        island_name="Favignana",
        recommended_method="usgs_thieler_1999",
        reason=(
            "Isola calcarea bassa nel Canale di Sicilia con spiagge sabbiose e "
            "costa bassa esposta. I dati ondametrici della boa di Mazara del Vallo "
            "sono rappresentativi. La presenza di spiagge in erosione documentata "
            "giustifica l'uso del metodo USGS che include il tasso di variazione "
            "della linea di riva."
        ),
        reference=(
            "Cipriani L.E. et al. (2013) — Coastal vulnerability assessment "
            "in the Sicilian channel. J. Coast. Res. Special Issue 65."
        ),
        alternative_methods=["pantusa_2018", "gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.4 mm/anno", "ISPRA RMN Porto Empedocle"),
            "altezza_onde": ConstantParam("altezza_onde", 4.0, "Hs media 1.1m", "RON Boa Mazara"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.30m", "ISPRA RMN"),
            "delta_linea": ConstantParam("delta_linea", 4.0, "−0.8/−1.2 m/anno (spiagge E e S)", "ISPRA Erosione 2022"),
        },
    ),

    # ── Isole Tirreniche ───────────────────────────────────────────────

    "Ponza": IslandMethodProfile(
        island_name="Ponza",
        recommended_method="gornitz_1991",
        reason=(
            "Costa tufacea e trachitica con alternanza di falesie e calette. "
            "Il Gornitz è adeguato: la geomorfologia varia molto da tratto a tratto "
            "e domina il risultato. I dati ondametrici della boa di Ponza (RON) "
            "sono disponibili ma la variabilità intra-isola è più importante "
            "della variabilità dei parametri oceanografici."
        ),
        reference=(
            "Pranzini E. & Williams A. (2013) — Coastal Erosion and Protection "
            "in Europe. Routledge, London."
        ),
        alternative_methods=["pantusa_2018"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~2.1 mm/anno (Mar Tirreno C)", "ISPRA RMN Civitavecchia"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.8m", "RON Boa Ponza"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.25m", "ISPRA RMN"),
            "delta_linea": ConstantParam("delta_linea", 3.0, "stima media, pochi studi specifici", "ISPRA 2021"),
        },
    ),

    # ── Arcipelago Toscano ─────────────────────────────────────────────

    "Elba": IslandMethodProfile(
        island_name="Elba",
        recommended_method="usgs_thieler_1999",
        reason=(
            "Isola più grande dell'Arcipelago Toscano con dati ondametrici "
            "disponibili dalla boa RON di La Spezia. La presenza di spiagge "
            "sabbiose in erosione documentata (Procchio, Marina di Campo) e "
            "la disponibilità di dati sul tasso di variazione della linea di riva "
            "da analisi multitemporale rendono l'USGS il metodo più accurato."
        ),
        reference=(
            "Cipriani L.E. et al. (2001) — Coastal erosion in Tuscany. "
            "Regione Toscana — Settore Difesa del Suolo."
        ),
        alternative_methods=["pantusa_2018", "gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~1.9 mm/anno (Mar Ligure/Tirreno N)", "ISPRA RMN Livorno"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.7m", "RON Boa La Spezia"),
            "range_maree": ConstantParam("range_maree", 4.0, "~0.40m (escursione maggiore rispetto al Tirreno S)", "ISPRA RMN Livorno"),
            "delta_linea": ConstantParam("delta_linea", 3.0, "−0.3/−0.5 m/anno (Procchio, Marina di Campo)", "Cipriani et al. 2001"),
        },
    ),

    "Giglio": IslandMethodProfile(
        island_name="Giglio",
        recommended_method="pantusa_2018",
        reason=(
            "Isola granitica con costa prevalentemente rocciosa. "
            "La geomorfologia domina nettamente: Pantusa con peso 0.30 "
            "sulla geomorfologia è il metodo più appropriato. "
            "La Costa Concordia (2012) ha localmente alterato la morfologia costiera "
            "nella zona SE — da considerare come fattore aggiuntivo."
        ),
        reference=(
            "Pranzini E. et al. (2015) — Coastal erosion in Tuscany. "
            "Ocean & Coastal Management."
        ),
        alternative_methods=["gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~1.9 mm/anno", "ISPRA RMN Livorno"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.7m", "RON La Spezia"),
            "range_maree": ConstantParam("range_maree", 4.0, "~0.40m", "ISPRA RMN Livorno"),
            "delta_linea": ConstantParam("delta_linea", 2.0, "costa granitica stabile", "ISPRA 2021"),
        },
    ),

    # ── Sardegna ───────────────────────────────────────────────────────

    "La Maddalena": IslandMethodProfile(
        island_name="La Maddalena",
        recommended_method="pantusa_2018",
        reason=(
            "Arcipelago granitico con costa molto frastagliata. "
            "Come per il Giglio, la geomorfologia granitica domina. "
            "La presenza di numerose calette sabbiose con erosione in atto "
            "rende il peso maggiore sulla geomorfologia (Pantusa) più appropriato "
            "rispetto alla media semplice di Gornitz."
        ),
        reference=(
            "Buosi C. et al. (2017) — Coastal erosion in Sardinia. "
            "J. Maps."
        ),
        alternative_methods=["gornitz_1991"],
        constants={
            "slr": ConstantParam("slr", 2.0, "~1.8 mm/anno (Mar di Sardegna)", "ISPRA RMN Cagliari"),
            "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media 0.9m", "RON Boa Alghero"),
            "range_maree": ConstantParam("range_maree", 5.0, "~0.20m (micro-marea)", "ISPRA RMN"),
            "delta_linea": ConstantParam("delta_linea", 3.0, "variabile per caletta", "Buosi et al. 2017"),
        },
    ),
}

# Profilo di default per isole senza raccomandazione specifica
DEFAULT_PROFILE = IslandMethodProfile(
    island_name="(generico)",
    recommended_method="gornitz_1991",
    reason=(
        "Nessuna raccomandazione specifica disponibile per questa isola. "
        "Il metodo Gornitz (1991) è il più robusto come approccio di default "
        "per isole del Mediterraneo in assenza di dati oceanografici specifici."
    ),
    reference="Gornitz V. (1991) — Global coastal hazards from future sea level rise.",
    alternative_methods=["pantusa_2018", "linear_mean"],
    constants={
        "slr":          ConstantParam("slr",          2.0, "~2.2 mm/anno (stima media Mediterraneo)", "ISPRA 2022"),
        "altezza_onde": ConstantParam("altezza_onde", 3.0, "Hs media ~0.8m (stima)",                  "RON media"),
        "range_maree":  ConstantParam("range_maree",  5.0, "~0.20–0.30m (Mediterraneo)",              "ISPRA RMN"),
        "delta_linea":  ConstantParam("delta_linea",  3.0, "stima media",                             "ISPRA 2021"),
    },
)


# ---------------------------------------------------------------------------
# Advisor
# ---------------------------------------------------------------------------

class IslandMethodAdvisor:
    """
    Fornisce raccomandazioni metodologiche e valori costanti per isola.

    Uso tipico:
        advisor = IslandMethodAdvisor()
        profile = advisor.get_profile("Lampedusa")
        print(profile.recommended_method)   # "usgs_thieler_1999"
        constants = advisor.get_constants("Lampedusa")
        print(constants["altezza_onde"].value)  # 4.0
    """

    def get_profile(self, island_name: str) -> IslandMethodProfile:
        """Restituisce il profilo metodologico per l'isola, o il default."""
        return ISLAND_PROFILES.get(island_name, DEFAULT_PROFILE)

    def get_recommended_method(self, island_name: str) -> str:
        """Restituisce l'ID del metodo raccomandato per l'isola."""
        return self.get_profile(island_name).recommended_method

    def get_constants(self, island_name: str) -> Dict[str, ConstantParam]:
        """Restituisce i valori costanti preconfigurati per l'isola."""
        return self.get_profile(island_name).constants

    def get_constant_value(self, island_name: str, param_key: str) -> Optional[float]:
        """Restituisce il valore classificato (1–5) di un parametro costante."""
        consts = self.get_constants(island_name)
        c = consts.get(param_key)
        return c.value if c else None

    def has_profile(self, island_name: str) -> bool:
        """Restituisce True se esiste un profilo specifico per l'isola."""
        return island_name in ISLAND_PROFILES

    def all_profiled_islands(self) -> List[str]:
        """Lista delle isole con profilo metodologico dedicato."""
        return list(ISLAND_PROFILES.keys())
