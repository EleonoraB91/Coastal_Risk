# -*- coding: utf-8 -*-
"""
core/online_data_connector.py
Connettore a endpoint WFS/WMS/WCS pubblici rilevanti per il rischio costiero
delle isole minori italiane.

Fornisce:
  - Catalogo di endpoint preconfigurati (ISPRA, IGM, EMODnet, Copernicus, ecc.)
  - Caricamento diretto dei layer in QGIS senza uscire dal plugin
  - Gestione degli errori di connettività con messaggi chiari
  - Anteprima metadati prima del caricamento
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsProject,
    QgsMessageLog,
    Qgis,
)


# ---------------------------------------------------------------------------
# Struttura dati endpoint
# ---------------------------------------------------------------------------

@dataclass
class OnlineEndpoint:
    """Descrizione completa di un endpoint WFS/WMS/WMTS preconfigurato."""

    id: str                        # identificatore univoco
    name: str                      # nome visualizzato
    category: str                  # categoria tematica
    provider: str                  # ente erogatore
    service_type: str              # "WFS" | "WMS" | "WMTS" | "ArcGIS"
    url: str                       # URL base del servizio
    layer_name: str                # nome del layer (typename WFS / layer WMS)
    description: str               # descrizione breve
    crs: str = "EPSG:4326"         # CRS predefinito
    extra_params: Dict = field(default_factory=dict)  # parametri aggiuntivi
    tags: List[str] = field(default_factory=list)     # tag di ricerca
    note: str = ""                 # note operative / limitazioni note


# ---------------------------------------------------------------------------
# Catalogo endpoint
# ---------------------------------------------------------------------------

ENDPOINTS: List[OnlineEndpoint] = [

    # ── ISPRA ──────────────────────────────────────────────────────────────

    OnlineEndpoint(
        id="ispra_erosione_costiera",
        name="Erosione costiera — tratti a rischio",
        category="Erosione costiera",
        provider="ISPRA",
        service_type="WFS",
        url="https://geoservices.ispra.it/geoserver/ows",
        layer_name="reteMonitoraggio:erosione_costiera",
        description=(
            "Tratti costieri classificati per tipo di tendenza evolutiva "
            "(erosione, stabilità, accrezione). Copertura nazionale. "
            "Fonte: Rapporto ISPRA sull'erosione costiera."
        ),
        tags=["erosione", "costa", "tendenza", "ISPRA"],
        note="Aggiornamento periodico — verificare la disponibilità del servizio.",
    ),

    OnlineEndpoint(
        id="ispra_uso_suolo_corine",
        name="Uso del suolo — CORINE Land Cover (livello 3)",
        category="Uso del suolo",
        provider="ISPRA",
        service_type="WFS",
        url="https://geoservices.ispra.it/geoserver/ows",
        layer_name="corine:clc_2018_it",
        description=(
            "Classificazione CORINE Land Cover 2018, livello 3 (44 classi). "
            "Utilizzabile direttamente come parametro 'Uso del suolo' nel CVI."
        ),
        tags=["uso suolo", "CORINE", "land cover", "ISPRA"],
    ),

    OnlineEndpoint(
        id="ispra_geomorfologia",
        name="Carta geomorfologica costiera",
        category="Geomorfologia",
        provider="ISPRA",
        service_type="WFS",
        url="https://geoservices.ispra.it/geoserver/ows",
        layer_name="geomorfologia:costa_geomorfologia",
        description=(
            "Tipo di costa (falesia, spiaggia sabbiosa, ghiaiosa, fangosa…). "
            "Parametro diretto per la variabile Geomorfologia del CVI."
        ),
        tags=["geomorfologia", "costa", "falesia", "spiaggia", "ISPRA"],
    ),

    # ── Geoportale Nazionale (IGM / PCN) ───────────────────────────────────

    OnlineEndpoint(
        id="pcn_ortofoto",
        name="Ortofoto Italia (PCN)",
        category="Immagini di sfondo",
        provider="Geoportale Nazionale — IGM",
        service_type="WMS",
        url="https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php",
        layer_name="ortofoto",
        description=(
            "Ortofoto ad alta risoluzione del territorio italiano. "
            "Utile come sfondo per la visualizzazione dei tratti costieri."
        ),
        tags=["ortofoto", "immagini", "sfondo", "PCN", "IGM"],
    ),

    OnlineEndpoint(
        id="pcn_dtm",
        name="Modello digitale del terreno — DTM 20m (PCN)",
        category="Topografia / Pendenza",
        provider="Geoportale Nazionale — IGM",
        service_type="WMS",
        url="https://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/Vettoriali/DTM.map",
        layer_name="DTM20",
        description=(
            "DTM a 20m di risoluzione per l'intero territorio italiano. "
            "Base per il calcolo della pendenza costiera (parametro CVI)."
        ),
        tags=["DTM", "DEM", "pendenza", "quota", "topografia"],
    ),

    OnlineEndpoint(
        id="pcn_limiti_amministrativi",
        name="Limiti amministrativi comunali (PCN)",
        category="Amministrativo",
        provider="Geoportale Nazionale — IGM",
        service_type="WFS",
        url="https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/ows01.php",
        layer_name="CP.CadastralParcel",
        description=(
            "Confini comunali ufficiali — utile per filtrare i dati "
            "per isola/comune."
        ),
        tags=["confini", "comuni", "amministrativo", "PCN"],
    ),

    # ── EMODnet (European Marine Observation and Data Network) ─────────────

    OnlineEndpoint(
        id="emodnet_bathymetry",
        name="Batimetria costiera — EMODnet",
        category="Batimetria",
        provider="EMODnet",
        service_type="WMS",
        url="https://ows.emodnet-bathymetry.eu/wms",
        layer_name="emodnet:mean_atlas_land",
        description=(
            "Batimetria ad alta risoluzione per i mari europei. "
            "Essenziale per la caratterizzazione del fetch e dell'energia ondosa "
            "(parametro Esposizione del CVI)."
        ),
        tags=["batimetria", "mare", "profondità", "EMODnet"],
    ),

    OnlineEndpoint(
        id="emodnet_geology_seabed",
        name="Geologia del fondale marino — EMODnet",
        category="Geomorfologia",
        provider="EMODnet",
        service_type="WMS",
        url="https://drive.emodnet-geology.eu/geoserver/bgr/wms",
        layer_name="GS:seabed_substrate_250k",
        description=(
            "Substrato del fondale (roccia, sabbia, ghiaia, fango…). "
            "Complementa la carta geomorfologica costiera per il parametro CVI."
        ),
        tags=["geologia", "fondale", "substrato", "EMODnet"],
    ),

    OnlineEndpoint(
        id="emodnet_human_activities",
        name="Attività antropiche marine — EMODnet",
        category="Uso del suolo",
        provider="EMODnet",
        service_type="WMS",
        url="https://ows.emodnet-humanactivities.eu/wms",
        layer_name="emodnet:AquacultureSites",
        description=(
            "Localizzazione di impianti di acquacoltura, porti, ancoraggi "
            "e aree marine protette — utile per il parametro uso del suolo "
            "nella zona costiera."
        ),
        tags=["acquacoltura", "porti", "attività umane", "EMODnet"],
    ),

    # ── Copernicus / EEA ───────────────────────────────────────────────────

    OnlineEndpoint(
        id="copernicus_clms_coastal",
        name="Coastal Zones — Copernicus Land (CLMS)",
        category="Uso del suolo",
        provider="Copernicus / EEA",
        service_type="WMS",
        url="https://image.discomap.eea.europa.eu/arcgis/services/Corine/CLC2018_WM/MapServer/WMSServer",
        layer_name="12",
        description=(
            "Copertura del suolo nelle zone costiere europee — "
            "derivata da CORINE Land Cover 2018 ad alta risoluzione (10m). "
            "Parametro diretto per Uso del suolo nel CVI."
        ),
        tags=["Copernicus", "uso suolo", "costa", "CLC", "EEA"],
    ),

    OnlineEndpoint(
        id="copernicus_global_surface_water",
        name="Global Surface Water — Copernicus/JRC",
        category="Idrologia",
        provider="Copernicus / JRC",
        service_type="WMS",
        url="https://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_10E_40Nv1_4_2021.tif",
        layer_name="occurrence",
        description=(
            "Frequenza di presenza d'acqua superficiale (1984–2021). "
            "Utile per identificare zone costiere basse con allagamento periodico."
        ),
        tags=["acqua", "alluvione", "superficie", "JRC", "Copernicus"],
    ),

    # ── OpenStreetMap / INSPIRE ────────────────────────────────────────────

    OnlineEndpoint(
        id="osm_coastline",
        name="Linea di costa — OpenStreetMap (QGIS XYZ)",
        category="Linea di riva",
        provider="OpenStreetMap",
        service_type="WMS",
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        layer_name="osm_standard",
        description=(
            "Mappa di sfondo OpenStreetMap — utile per localizzare "
            "visivamente i tratti costieri. Non è un layer vettoriale analitico."
        ),
        tags=["OSM", "sfondo", "mappa base"],
        note="Layer raster XYZ — non utilizzabile come input CVI.",
    ),

    OnlineEndpoint(
        id="inspire_protected_areas",
        name="Aree protette INSPIRE (Natura 2000)",
        category="Aree protette",
        provider="EEA / INSPIRE",
        service_type="WFS",
        url="https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/EIONET_Nature_WFS/MapServer/WFSServer",
        layer_name="PS.ProtectedSite",
        description=(
            "Siti Natura 2000, ZSC, ZPS e aree marine protette. "
            "Informazione contestuale per la valutazione dell'uso del suolo "
            "e della sensibilità ecologica dei tratti costieri."
        ),
        tags=["Natura 2000", "aree protette", "ZSC", "ZPS", "INSPIRE"],
    ),

    # ── Regioni / ARPA ─────────────────────────────────────────────────────

    OnlineEndpoint(
        id="sicilia_ctr",
        name="Carta Tecnica Regionale — Sicilia",
        category="Cartografia di base",
        provider="Regione Siciliana",
        service_type="WMS",
        url="https://www.sitr.regione.sicilia.it/geoserver/ows",
        layer_name="SITR:CTR",
        description=(
            "Carta Tecnica Regionale della Sicilia in scala 1:10.000. "
            "Copertura delle Isole Eolie, Egadi, Pelagie, Pantelleria."
        ),
        tags=["CTR", "Sicilia", "cartografia", "Eolie", "Egadi"],
    ),

    OnlineEndpoint(
        id="sardegna_geoportale",
        name="Ortofoto e layer costieri — Sardegna",
        category="Cartografia di base",
        provider="Regione Sardegna",
        service_type="WMS",
        url="https://www.sardegnageoportale.it/geoserver/wms",
        layer_name="ortofoto2019",
        description=(
            "Ortofoto 2019 della Sardegna. "
            "Copertura dell'Arcipelago della Maddalena e isole sulcitane."
        ),
        tags=["Sardegna", "ortofoto", "Maddalena", "cartografia"],
    ),
]


# ---------------------------------------------------------------------------
# Classe connettore
# ---------------------------------------------------------------------------

class OnlineDataConnector:
    """
    Gestisce il catalogo degli endpoint online e il caricamento dei layer in QGIS.

    Uso tipico:
        connector = OnlineDataConnector(iface)
        endpoints = connector.get_by_category("Erosione costiera")
        ok, msg, layer = connector.load("ispra_erosione_costiera")
    """

    LOG_TAG = "CoastalRiskDashboard"

    def __init__(self, iface):
        self.iface = iface
        self._endpoints: Dict[str, OnlineEndpoint] = {
            ep.id: ep for ep in ENDPOINTS
        }

    # ------------------------------------------------------------------
    # Interrogazione catalogo
    # ------------------------------------------------------------------

    def all_endpoints(self) -> List[OnlineEndpoint]:
        return list(self._endpoints.values())

    def categories(self) -> List[str]:
        """Restituisce le categorie tematiche disponibili, ordinate."""
        return sorted(set(ep.category for ep in self._endpoints.values()))

    def get_by_category(self, category: str) -> List[OnlineEndpoint]:
        return [ep for ep in self._endpoints.values() if ep.category == category]

    def get(self, endpoint_id: str) -> Optional[OnlineEndpoint]:
        return self._endpoints.get(endpoint_id)

    def search(self, query: str) -> List[OnlineEndpoint]:
        """Ricerca testuale su nome, descrizione e tag."""
        q = query.lower().strip()
        if not q:
            return self.all_endpoints()
        results = []
        for ep in self._endpoints.values():
            haystack = (
                ep.name.lower() + " " +
                ep.description.lower() + " " +
                " ".join(ep.tags).lower() + " " +
                ep.provider.lower()
            )
            if q in haystack:
                results.append(ep)
        return results

    # ------------------------------------------------------------------
    # Caricamento layer
    # ------------------------------------------------------------------

    def load(
        self,
        endpoint_id: str,
        layer_name_override: Optional[str] = None,
    ):
        """
        Carica un endpoint come layer QGIS e lo aggiunge al progetto.

        :param endpoint_id:        ID dell'endpoint nel catalogo
        :param layer_name_override: nome da assegnare al layer (default: ep.name)
        :return: (successo: bool, messaggio: str, layer: QgsVectorLayer|QgsRasterLayer|None)
        """
        ep = self._endpoints.get(endpoint_id)
        if ep is None:
            return False, f"Endpoint '{endpoint_id}' non trovato nel catalogo.", None

        display_name = layer_name_override or ep.name

        try:
            if ep.service_type == "WFS":
                return self._load_wfs(ep, display_name)
            elif ep.service_type in ("WMS", "WMTS"):
                return self._load_wms(ep, display_name)
            else:
                return False, f"Tipo servizio '{ep.service_type}' non supportato.", None

        except Exception as exc:
            msg = f"Errore caricamento '{ep.name}': {exc}"
            self._log(msg, Qgis.Critical)
            return False, msg, None

    def load_custom_wfs(self, url: str, layer_name: str, typename: str, display_name: str):
        """
        Carica un WFS custom (URL e typename inseriti manualmente dall'utente).

        :return: (successo, messaggio, layer)
        """
        ep = OnlineEndpoint(
            id="custom",
            name=display_name,
            category="Custom",
            provider="Personalizzato",
            service_type="WFS",
            url=url,
            layer_name=typename,
            description="Endpoint WFS personalizzato.",
        )
        return self._load_wfs(ep, display_name)

    def load_custom_wms(self, url: str, layer_name: str, display_name: str):
        """
        Carica un WMS custom (URL e layer inseriti manualmente dall'utente).

        :return: (successo, messaggio, layer)
        """
        ep = OnlineEndpoint(
            id="custom",
            name=display_name,
            category="Custom",
            provider="Personalizzato",
            service_type="WMS",
            url=url,
            layer_name=layer_name,
            description="Endpoint WMS personalizzato.",
        )
        return self._load_wms(ep, display_name)

    # ------------------------------------------------------------------
    # Loader interni
    # ------------------------------------------------------------------

    def _load_wfs(self, ep: OnlineEndpoint, display_name: str):
        """Costruisce la stringa di connessione WFS e carica il layer."""
        uri = (
            f"pagingEnabled='true' "
            f"preferCoordinatesForWfsT11='false' "
            f"restrictToRequestBBOX='1' "
            f"srsname='{ep.crs}' "
            f"typename='{ep.layer_name}' "
            f"url='{ep.url}' "
            f"version='auto'"
        )
        layer = QgsVectorLayer(uri, display_name, "WFS")

        if not layer.isValid():
            msg = (
                f"Impossibile connettersi al WFS:\n{ep.url}\n"
                f"Typename: {ep.layer_name}\n\n"
                "Possibili cause: servizio offline, URL non raggiungibile, "
                "typename errato o accesso negato dalla rete."
            )
            self._log(msg, Qgis.Warning)
            return False, msg, None

        QgsProject.instance().addMapLayer(layer)
        msg = f"Layer WFS caricato: '{display_name}' ({layer.featureCount()} feature)."
        self._log(msg)
        return True, msg, layer

    def _load_wms(self, ep: OnlineEndpoint, display_name: str):
        """Costruisce la stringa di connessione WMS/WMTS e carica il layer raster."""
        uri = (
            f"crs={ep.crs}"
            f"&format=image/png"
            f"&layers={ep.layer_name}"
            f"&styles="
            f"&url={ep.url}"
        )
        layer = QgsRasterLayer(uri, display_name, "wms")

        if not layer.isValid():
            msg = (
                f"Impossibile connettersi al WMS:\n{ep.url}\n"
                f"Layer: {ep.layer_name}\n\n"
                "Possibili cause: servizio offline, URL non raggiungibile, "
                "nome layer errato o restrizioni di accesso."
            )
            self._log(msg, Qgis.Warning)
            return False, msg, None

        QgsProject.instance().addMapLayer(layer)
        msg = f"Layer WMS caricato: '{display_name}'."
        self._log(msg)
        return True, msg, layer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)
