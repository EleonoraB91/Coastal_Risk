# -*- coding: utf-8 -*-
"""
core/online_data_sources.py
Fonti dati online affidabili per il rischio costiero delle isole minori italiane.

Approccio rivisto rispetto alla versione precedente (WFS instabili):
  - Sezione A: link diretti a pagine di download (shapefile/GeoTIFF scaricabili)
  - Sezione B: servizi WMS/WMTS affidabili (solo visualizzazione sfondo)
  - Sezione C: servizi WFS verificati e stabili (pochi, ma funzionanti)

Ogni fonte è classificata per:
  - affidabilità (HIGH / MEDIUM)
  - tipo di accesso (DOWNLOAD / WMS / WFS)
  - parametro CVI cui contribuisce
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject, QgsMessageLog, Qgis


@dataclass
class DataSource:
    """Descrizione di una fonte dati online."""
    id: str
    name: str
    provider: str
    category: str
    access_type: str          # "DOWNLOAD" | "WMS" | "WFS" | "XYZ"
    url: str                  # URL pagina download o servizio
    description: str
    cvi_param: str            # parametro CVI: "geomorfologia"|"pendenza"|"uso_suolo"|"esposizione"|"sfondo"|"linea_riva"
    reliability: str          # "HIGH" | "MEDIUM"
    format_note: str          # es. "Shapefile .zip" o "WMS - solo visualizzazione"
    layer_name: str = ""      # per WMS/WFS: nome layer
    tags: List[str] = field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------------------
# Catalogo fonti
# ---------------------------------------------------------------------------

SOURCES: List[DataSource] = [

    # ── DOWNLOAD DIRETTI — alta affidabilità ───────────────────────────

    DataSource(
        id="copernicus_clc_download",
        name="CORINE Land Cover 2018 — Italia",
        provider="Copernicus Land Monitoring Service",
        category="Uso del suolo",
        access_type="DOWNLOAD",
        url="https://land.copernicus.eu/en/products/corine-land-cover/clc2018",
        description=(
            "Mappa uso del suolo a 100m per l'intera Italia. "
            "Direttamente utilizzabile come parametro 'Uso del suolo' nel CVI. "
            "Gratuito, richiede registrazione."
        ),
        cvi_param="uso_suolo",
        reliability="HIGH",
        format_note="GeoTIFF / Shapefile — download gratuito con registrazione",
        tags=["uso suolo", "CORINE", "land cover", "Copernicus"],
    ),

    DataSource(
        id="copernicus_data_space",
        name="Sentinel-2 — Immagini satellitari",
        provider="Copernicus Data Space (ESA)",
        category="Immagini satellitari",
        access_type="DOWNLOAD",
        url="https://dataspace.copernicus.eu",
        description=(
            "Immagini Sentinel-2 aggiornate ogni 5 giorni, risoluzione 10m. "
            "Usare NDWI per estrarre la linea di riva. "
            "Gratuito, plugin QGIS dedicato disponibile."
        ),
        cvi_param="linea_riva",
        reliability="HIGH",
        format_note="GeoTIFF — gratuito, plugin QGIS 'Copernicus Data Space'",
        tags=["Sentinel-2", "satellite", "NDWI", "linea di riva", "ESA"],
        note="Installa il plugin 'Copernicus Data Space Browser' direttamente in QGIS.",
    ),

    DataSource(
        id="ispra_erosione_download",
        name="Erosione costiera — Report e shapefile ISPRA",
        provider="ISPRA",
        category="Erosione costiera",
        access_type="DOWNLOAD",
        url="https://www.isprambiente.gov.it/it/banche-dati/dati-e-informazioni-ambientali/suolo-e-territorio/erosione-costiera",
        description=(
            "Shapefile dei tratti costieri classificati per tendenza evolutiva "
            "(erosione / stabilità / accrezione) per l'intera costa italiana. "
            "Parametro diretto per la variazione della linea di riva."
        ),
        cvi_param="linea_riva",
        reliability="HIGH",
        format_note="Shapefile .zip — download diretto, gratuito",
        tags=["erosione", "linea di riva", "ISPRA", "costa"],
    ),

    DataSource(
        id="ispra_geomorfologia_download",
        name="Carta geomorfologica costiera — ISPRA",
        provider="ISPRA",
        category="Geomorfologia",
        access_type="DOWNLOAD",
        url="https://www.isprambiente.gov.it/it/banche-dati/dati-e-informazioni-ambientali/suolo-e-territorio/carta-geomorfologica",
        description=(
            "Carta della geomorfologia costiera italiana. "
            "Classifica il tipo di costa: falesia, spiaggia, costa bassa, ecc. "
            "Parametro diretto 'Geomorfologia' nel CVI."
        ),
        cvi_param="geomorfologia",
        reliability="HIGH",
        format_note="Shapefile — download gratuito",
        tags=["geomorfologia", "falesia", "spiaggia", "ISPRA"],
    ),

    DataSource(
        id="tinitaly_dem",
        name="DEM Italia — TINITALY (10m)",
        provider="INGV",
        category="Topografia / Pendenza",
        access_type="DOWNLOAD",
        url="https://tinitaly.pi.ingv.it",
        description=(
            "Modello digitale del terreno dell'Italia a 10m di risoluzione. "
            "Il migliore DEM disponibile per l'Italia. "
            "Usare QGIS → Raster → Analisi → Pendenza per ricavare il parametro CVI."
        ),
        cvi_param="pendenza",
        reliability="HIGH",
        format_note="GeoTIFF — download gratuito con registrazione",
        tags=["DEM", "pendenza", "quota", "TINITALY", "INGV"],
    ),

    DataSource(
        id="emodnet_bathymetry_download",
        name="Batimetria costiera — EMODnet",
        provider="EMODnet Bathymetry",
        category="Batimetria / Esposizione",
        access_type="DOWNLOAD",
        url="https://emodnet.ec.europa.eu/geoviewer/",
        description=(
            "Batimetria ad alta risoluzione per i mari europei incluso il Mediterraneo. "
            "Usare per caratterizzare il fetch e l'energia ondosa "
            "(parametro 'Esposizione' nel CVI)."
        ),
        cvi_param="esposizione",
        reliability="HIGH",
        format_note="GeoTIFF / NetCDF — download gratuito dal GeoViewer",
        tags=["batimetria", "mare", "profondità", "EMODnet", "esposizione"],
    ),

    DataSource(
        id="natura2000_download",
        name="Aree Natura 2000 — Italia",
        provider="ISPRA / Ministero Ambiente",
        category="Aree protette",
        access_type="DOWNLOAD",
        url="https://www.mase.gov.it/pagina/rete-natura-2000",
        description=(
            "Perimetri ZSC, ZPS e SIC in Italia. Utile per contestualizzare "
            "l'uso del suolo nelle aree marine protette (AMP) delle isole minori."
        ),
        cvi_param="uso_suolo",
        reliability="HIGH",
        format_note="Shapefile — download diretto, gratuito",
        tags=["Natura 2000", "ZSC", "ZPS", "aree protette", "AMP"],
    ),

    DataSource(
        id="osm_coastline",
        name="Linea di costa — OpenStreetMap",
        provider="OpenStreetMap / Geofabrik",
        category="Linea di riva",
        access_type="DOWNLOAD",
        url="https://download.geofabrik.de/europe/italy.html",
        description=(
            "Linea di costa vettoriale precisa da OpenStreetMap per l'Italia. "
            "Scaricare il file Italia (.shp.zip), cercare il layer 'coastline'. "
            "In alternativa usare il plugin QuickOSM direttamente in QGIS."
        ),
        cvi_param="linea_riva",
        reliability="HIGH",
        format_note="Shapefile — download gratuito (Geofabrik) o plugin QuickOSM",
        tags=["OSM", "linea di costa", "vettoriale", "QuickOSM"],
        note="Con QuickOSM in QGIS: Key='natural', Value='coastline', area='nome isola'.",
    ),

    DataSource(
        id="arpacal_meteo_marino",
        name="Dati ondametrici — Rete Ondametrica Nazionale (RON)",
        provider="ISPRA — Rete Ondametrica Nazionale",
        category="Dati ondametrici",
        access_type="DOWNLOAD",
        url="https://www.isprambiente.gov.it/it/progetti/progetto-rete-ondametrica-nazionale-ron",
        description=(
            "Dati storici di altezza d'onda dalle boe della rete italiana. "
            "Fondamentale per il parametro 'Esposizione / altezza onde' nei metodi "
            "USGS e Pantusa. Boe rilevanti: Ponza, Mazara del Vallo, Alghero."
        ),
        cvi_param="esposizione",
        reliability="HIGH",
        format_note="CSV / Excel — download previa richiesta via form",
        tags=["onde", "ondametria", "RON", "ISPRA", "esposizione"],
    ),

    # ── SERVIZI WMS AFFIDABILI — solo visualizzazione ──────────────────

    DataSource(
        id="emodnet_wms",
        name="EMODnet Bathymetry — WMS sfondo",
        provider="EMODnet",
        category="Sfondo / Batimetria",
        access_type="WMS",
        url="https://ows.emodnet-bathymetry.eu/wms",
        layer_name="emodnet:mean_atlas_land",
        description=(
            "Mappa batimetrica colorata come sfondo. Utile per visualizzare "
            "la profondità del mare attorno alle isole minori. "
            "Non analiticamente utilizzabile come input CVI."
        ),
        cvi_param="sfondo",
        reliability="HIGH",
        format_note="WMS — solo visualizzazione",
        tags=["batimetria", "sfondo", "EMODnet", "WMS"],
    ),

    DataSource(
        id="osm_xyz",
        name="OpenStreetMap — Mappa base (XYZ)",
        provider="OpenStreetMap",
        category="Sfondo / Mappa base",
        access_type="XYZ",
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        description=(
            "Mappa di sfondo OpenStreetMap. Aggiungibile come tile XYZ in QGIS "
            "dal pannello Browser → XYZ Tiles."
        ),
        cvi_param="sfondo",
        reliability="HIGH",
        format_note="XYZ Tiles — aggiungere dal Browser QGIS",
        tags=["OSM", "sfondo", "mappa base", "XYZ"],
    ),

    DataSource(
        id="google_satellite_xyz",
        name="Google Satellite — Ortofoto (XYZ)",
        provider="Google",
        category="Sfondo / Ortofoto",
        access_type="XYZ",
        url="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        description=(
            "Ortofoto satellite Google come sfondo per la digitalizzazione. "
            "Aggiungere come XYZ Tile in QGIS: Browser → XYZ Tiles (tasto destro) "
            "→ Nuova connessione."
        ),
        cvi_param="sfondo",
        reliability="HIGH",
        format_note="XYZ Tiles — aggiungere manualmente dal Browser QGIS",
        tags=["Google", "satellite", "ortofoto", "sfondo", "XYZ"],
        note="Verifica i termini d'uso Google Maps prima dell'uso in pubblicazioni.",
    ),

    # ── SERVIZI WFS VERIFICATI ─────────────────────────────────────────

    DataSource(
        id="emodnet_geology_wfs",
        name="Geologia fondale marino — EMODnet WFS",
        provider="EMODnet Geology",
        category="Geomorfologia",
        access_type="WFS",
        url="https://drive.emodnet-geology.eu/geoserver/bgr/wfs",
        layer_name="bgr:GS_seabed_substrate_250k",
        description=(
            "Substrato del fondale (roccia, sabbia, ghiaia, fango). "
            "Servizio WFS EMODnet — tra i più stabili disponibili. "
            "Complementa la geomorfologia costiera per il parametro CVI."
        ),
        cvi_param="geomorfologia",
        reliability="MEDIUM",
        format_note="WFS — caricamento diretto in QGIS",
        tags=["geologia", "fondale", "substrato", "EMODnet", "WFS"],
    ),
]

# Categorie disponibili
CATEGORIES = sorted(set(s.category for s in SOURCES))
ACCESS_TYPES = ["DOWNLOAD", "WMS", "WFS", "XYZ"]
CVI_PARAMS = sorted(set(s.cvi_param for s in SOURCES))


# ---------------------------------------------------------------------------
# Classe connettore semplificata
# ---------------------------------------------------------------------------

class OnlineDataSources:
    """
    Gestisce il catalogo delle fonti dati e il caricamento dei servizi live.

    Per le fonti DOWNLOAD apre il browser alla pagina corretta.
    Per WMS/XYZ/WFS carica direttamente in QGIS.
    """

    LOG_TAG = "CoastalRiskDashboard"

    def __init__(self, iface):
        self.iface = iface
        self._by_id: Dict[str, DataSource] = {s.id: s for s in SOURCES}

    def all_sources(self) -> List[DataSource]:
        return list(self._by_id.values())

    def get(self, source_id: str) -> Optional[DataSource]:
        return self._by_id.get(source_id)

    def filter(
        self,
        query: str = "",
        category: str = "",
        access_type: str = "",
        cvi_param: str = "",
    ) -> List[DataSource]:
        results = list(self._by_id.values())
        if query:
            q = query.lower()
            results = [
                s for s in results
                if q in s.name.lower() or q in s.description.lower()
                or any(q in t.lower() for t in s.tags)
                or q in s.provider.lower()
            ]
        if category:
            results = [s for s in results if s.category == category]
        if access_type:
            results = [s for s in results if s.access_type == access_type]
        if cvi_param:
            results = [s for s in results if s.cvi_param == cvi_param]
        return results

    def open_download_page(self, source_id: str) -> bool:
        """Apre la pagina di download nel browser di sistema."""
        import webbrowser
        source = self._by_id.get(source_id)
        if source is None:
            return False
        webbrowser.open(source.url)
        self._log(f"Browser aperto: {source.url}")
        return True

    def load_wms(self, source_id: str) -> tuple:
        """Carica un layer WMS in QGIS."""
        source = self._by_id.get(source_id)
        if source is None:
            return False, "Fonte non trovata.", None
        if source.access_type not in ("WMS", "WMTS"):
            return False, f"Fonte '{source.name}' non è un WMS.", None

        uri = (
            f"crs=EPSG:4326&format=image/png"
            f"&layers={source.layer_name}&styles=&url={source.url}"
        )
        layer = QgsRasterLayer(uri, source.name, "wms")
        if not layer.isValid():
            msg = (
                f"Impossibile caricare il WMS:\n{source.url}\n"
                f"Layer: {source.layer_name}"
            )
            self._log(msg, Qgis.Warning)
            return False, msg, None

        QgsProject.instance().addMapLayer(layer)
        self._log(f"WMS caricato: {source.name}")
        return True, f"Layer WMS caricato: {source.name}", layer

    def load_xyz(self, source_id: str) -> tuple:
        """Aggiunge un tile XYZ come layer raster in QGIS."""
        source = self._by_id.get(source_id)
        if source is None:
            return False, "Fonte non trovata.", None

        uri = (
            f"type=xyz&url={source.url}"
            f"&zmax=19&zmin=0&crs=EPSG:3857"
        )
        layer = QgsRasterLayer(uri, source.name, "wms")
        if not layer.isValid():
            return False, f"Impossibile caricare XYZ: {source.url}", None

        QgsProject.instance().addMapLayer(layer)
        self._log(f"XYZ caricato: {source.name}")
        return True, f"Layer XYZ caricato: {source.name}", layer

    def load_wfs(self, source_id: str) -> tuple:
        """Carica un layer WFS in QGIS."""
        source = self._by_id.get(source_id)
        if source is None:
            return False, "Fonte non trovata.", None

        uri = (
            f"pagingEnabled='true' restrictToRequestBBOX='1' "
            f"srsname='EPSG:4326' typename='{source.layer_name}' "
            f"url='{source.url}' version='auto'"
        )
        layer = QgsVectorLayer(uri, source.name, "WFS")
        if not layer.isValid():
            msg = (
                f"Impossibile caricare il WFS:\n{source.url}\n"
                f"Typename: {source.layer_name}"
            )
            self._log(msg, Qgis.Warning)
            return False, msg, None

        QgsProject.instance().addMapLayer(layer)
        self._log(f"WFS caricato: {source.name}")
        return True, f"Layer WFS caricato: {source.name} ({layer.featureCount()} feature)", layer

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)
