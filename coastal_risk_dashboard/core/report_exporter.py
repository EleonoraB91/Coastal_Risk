# -*- coding: utf-8 -*-
"""
core/report_exporter.py
Esportazione dei risultati del rischio costiero in PNG, CSV e report testuale.
Fase 4.
"""

import os
import csv
import datetime
from typing import Optional, List, Dict

from qgis.core import (
    QgsVectorLayer,
    QgsProject,
    QgsMapSettings,
    QgsMapRendererParallelJob,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    Qgis,
)
from qgis.PyQt.QtCore import QSize, Qt, QEventLoop
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QFont, QFontMetrics
from qgis.PyQt.QtWidgets import QApplication

from .risk_calculator import CVIStats
from .shoreline_loader import CVI_FIELD_NAME, RISK_FIELD_NAME


class ReportExporter:
    """
    Esporta i risultati del calcolo CVI in formati condivisibili.

    Output supportati:
    - PNG  → mappa del canvas corrente con legenda e titolo
    - CSV  → tabella feature-per-feature con CVI e classe di rischio
    - TXT  → report testuale con statistiche aggregate

    Uso tipico:
        exp = ReportExporter(iface)
        exp.export_map_png("/path/output.png", title="Rischio costiero — Lipari")
        exp.export_stats_csv("/path/stats.csv", layer, stats)
        exp.export_report_txt("/path/report.txt", layer, stats)
    """

    LOG_TAG = "CoastalRiskDashboard"

    # Palette colori rischio (per legenda PNG)
    RISK_PALETTE = [
        ("#2ecc71", "Molto Basso  (CVI 1.0–1.5)"),
        ("#a8d08d", "Basso        (CVI 1.5–2.5)"),
        ("#f1c40f", "Medio        (CVI 2.5–3.5)"),
        ("#e67e22", "Alto         (CVI 3.5–4.5)"),
        ("#e74c3c", "Molto Alto   (CVI 4.5–5.0)"),
    ]

    def __init__(self, iface):
        self.iface = iface

    # ------------------------------------------------------------------
    # Export PNG — mappa canvas con legenda
    # ------------------------------------------------------------------

    def export_map_png(
        self,
        output_path: str,
        title: str = "Coastal Risk Dashboard",
        width_px: int = 1920,
        height_px: int = 1080,
        dpi: int = 150,
    ) -> bool:
        """
        Esporta la vista corrente del canvas QGIS come PNG ad alta risoluzione,
        con legenda dei colori di rischio, titolo e metadati in sovrimpressione.

        :param output_path: percorso completo del file PNG di output
        :param title:       titolo da stampare sull'immagine
        :param width_px:    larghezza in pixel
        :param height_px:   altezza in pixel
        :param dpi:         risoluzione
        :return: True se esportato con successo
        """
        canvas = self.iface.mapCanvas()

        # 1. Configura il renderer della mappa
        settings = QgsMapSettings()
        settings.setLayers(canvas.layers())
        settings.setExtent(canvas.extent())
        settings.setOutputSize(QSize(width_px, height_px))
        settings.setOutputDpi(dpi)
        settings.setBackgroundColor(QColor("#f0f4f8"))
        settings.setFlag(QgsMapSettings.Antialiasing, True)

        # 2. Rendering asincrono (non blocca la UI)
        render_job = QgsMapRendererParallelJob(settings)
        render_job.start()

        # Attende il completamento con event loop locale
        loop = QEventLoop()
        render_job.finished.connect(loop.quit)
        loop.exec_()

        img = render_job.renderedImage()
        if img.isNull():
            self._log("Rendering mappa fallito: immagine vuota.", Qgis.Critical)
            return False

        # 3. Sovrimpressione legenda e testo
        img = self._draw_overlay(img, title)

        # 4. Salvataggio
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        ok = img.save(output_path, "PNG")
        if ok:
            self._log(f"Mappa PNG esportata: {output_path}")
        else:
            self._log(f"Salvataggio PNG fallito: {output_path}", Qgis.Critical)
        return ok

    def _draw_overlay(self, img: QImage, title: str) -> QImage:
        """Disegna titolo, legenda e timestamp sull'immagine della mappa."""
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = img.width(), img.height()

        # ── Sfondo header ──────────────────────────────────────────────
        header_h = 52
        painter.fillRect(0, 0, w, header_h, QColor(26, 58, 92, 230))

        # Titolo
        painter.setPen(QColor("white"))
        font_title = QFont("Arial", 18, QFont.Bold)
        painter.setFont(font_title)
        painter.drawText(16, header_h - 14, title)

        # Timestamp
        ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        font_ts = QFont("Arial", 9)
        painter.setFont(font_ts)
        fm = QFontMetrics(font_ts)
        ts_w = fm.horizontalAdvance(ts)
        painter.drawText(w - ts_w - 14, header_h - 14, ts)

        # ── Legenda (in basso a sinistra) ──────────────────────────────
        leg_x, leg_y = 16, h - (len(self.RISK_PALETTE) * 26 + 42)
        leg_w = 260
        leg_h = len(self.RISK_PALETTE) * 26 + 36

        # Sfondo legenda
        painter.fillRect(leg_x - 4, leg_y - 4, leg_w, leg_h, QColor(255, 255, 255, 210))
        painter.setPen(QColor(180, 180, 180))
        painter.drawRect(leg_x - 4, leg_y - 4, leg_w, leg_h)

        # Titolo legenda
        painter.setPen(QColor(30, 30, 30))
        font_leg_title = QFont("Arial", 10, QFont.Bold)
        painter.setFont(font_leg_title)
        painter.drawText(leg_x, leg_y + 16, "Indice di Rischio Costiero (CVI)")

        # Voci legenda
        font_leg = QFont("Arial", 9)
        painter.setFont(font_leg)
        for i, (hex_color, label) in enumerate(self.RISK_PALETTE):
            cy = leg_y + 32 + i * 26
            # Quadratino colore
            painter.fillRect(leg_x, cy, 18, 18, QColor(hex_color))
            painter.setPen(QColor(100, 100, 100))
            painter.drawRect(leg_x, cy, 18, 18)
            # Testo
            painter.setPen(QColor(30, 30, 30))
            painter.drawText(leg_x + 26, cy + 14, label)

        # ── Watermark ──────────────────────────────────────────────────
        painter.setPen(QColor(120, 120, 120, 160))
        font_wm = QFont("Arial", 8)
        painter.setFont(font_wm)
        painter.drawText(w - 260, h - 8, "Coastal Risk Dashboard — QGIS Plugin v1.0")

        painter.end()
        return img

    # ------------------------------------------------------------------
    # Export CSV — feature per feature
    # ------------------------------------------------------------------

    def export_stats_csv(
        self,
        output_path: str,
        layer: QgsVectorLayer,
        stats: Optional[CVIStats] = None,
        extra_fields: Optional[List[str]] = None,
    ) -> bool:
        """
        Esporta una riga per ogni feature del layer con i valori CVI,
        classe di rischio e campi aggiuntivi opzionali.
        In coda aggiunge un blocco di statistiche aggregate.

        :param output_path:   percorso del file CSV di output
        :param layer:         layer vettoriale con campo CVI calcolato
        :param stats:         CVIStats per aggiungere sezione riepilogo
        :param extra_fields:  lista di campi aggiuntivi da includere (es. ["NOME", "COMUNE"])
        :return: True se esportato con successo
        """
        if layer is None or not layer.isValid():
            self._log("Layer non valido per export CSV.", Qgis.Warning)
            return False

        layer_fields = [f.name() for f in layer.fields()]
        cvi_present   = CVI_FIELD_NAME in layer_fields
        risk_present  = RISK_FIELD_NAME in layer_fields

        if not cvi_present:
            self._log(
                f"Campo '{CVI_FIELD_NAME}' assente nel layer. "
                "Esegui prima il calcolo CVI.",
                Qgis.Warning,
            )
            return False

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")

                # Intestazione
                header = ["ID_FEATURE", CVI_FIELD_NAME]
                if risk_present:
                    header.append(RISK_FIELD_NAME)
                if extra_fields:
                    header += [ef for ef in extra_fields if ef in layer_fields]
                writer.writerow(header)

                # Righe feature
                count = 0
                for feat in layer.getFeatures():
                    row = [feat.id(), feat[CVI_FIELD_NAME]]
                    if risk_present:
                        row.append(feat[RISK_FIELD_NAME])
                    if extra_fields:
                        row += [
                            feat[ef] for ef in extra_fields
                            if ef in layer_fields
                        ]
                    writer.writerow(row)
                    count += 1

                # Sezione statistiche aggregate (separata da riga vuota)
                if stats and stats.count > 0:
                    writer.writerow([])
                    writer.writerow(["=== STATISTICHE AGGREGATE ==="])
                    writer.writerow(["N. tratti analizzati", stats.count])
                    writer.writerow(["CVI medio",  stats.mean_cvi])
                    writer.writerow(["CVI minimo", stats.min_cvi])
                    writer.writerow(["CVI massimo", stats.max_cvi])
                    writer.writerow(["Deviazione standard", stats.std_cvi])
                    writer.writerow([])
                    writer.writerow(["=== DISTRIBUZIONE PER CLASSE ==="])
                    writer.writerow(["Classe", "N. tratti", "Percentuale (%)"])
                    for cls, cnt in stats.distribution.items():
                        pct = stats.distribution_pct.get(cls, 0.0)
                        writer.writerow([cls, cnt, f"{pct:.1f}"])

                    writer.writerow([])
                    writer.writerow(["Generato il", datetime.datetime.now().strftime("%d/%m/%Y %H:%M")])
                    writer.writerow(["Layer sorgente", layer.name()])

        except OSError as e:
            self._log(f"Errore scrittura CSV: {e}", Qgis.Critical)
            return False

        self._log(f"CSV esportato ({count} feature): {output_path}")
        return True

    # ------------------------------------------------------------------
    # Export report testuale TXT
    # ------------------------------------------------------------------

    def export_report_txt(
        self,
        output_path: str,
        layer: QgsVectorLayer,
        stats: CVIStats,
        island_name: str = "",
        field_map: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Genera un report testuale strutturato con:
        - intestazione progetto
        - descrizione metodologia CVI
        - statistiche aggregate
        - distribuzione classi di rischio
        - note operative

        :param output_path: percorso del file TXT
        :param layer:       layer vettoriale analizzato
        :param stats:       CVIStats calcolate
        :param island_name: nome dell'isola (per il titolo)
        :param field_map:   mappatura campi utilizzata nel calcolo
        :return: True se esportato con successo
        """
        now = datetime.datetime.now().strftime("%d/%m/%Y alle %H:%M")
        sep = "=" * 64
        sep2 = "-" * 64

        lines = [
            sep,
            "  COASTAL RISK DASHBOARD — REPORT RISCHIO EROSIONE COSTIERA",
            sep,
            "",
            f"  Isola / Area:    {island_name or 'N/D'}",
            f"  Layer analizzato: {layer.name() if layer else 'N/D'}",
            f"  Data analisi:    {now}",
            f"  Tratti costieri: {stats.count}",
            "",
            sep2,
            "  METODOLOGIA",
            sep2,
            "",
            "  Il Coastal Vulnerability Index (CVI) è calcolato secondo la formula:",
            "",
            "      CVI = √( (G × P × U × E) / 4 )",
            "",
            "  dove:",
            "    G = Geomorfologia  (1=falesia rocciosa → 5=costa fangosa)",
            "    P = Pendenza       (1=>20% → 5=<1%)",
            "    U = Uso del suolo  (1=naturale → 5=urbanizzato)",
            "    E = Esposizione    (1=riparata → 5=molto esposta)",
            "",
            "  Range CVI: 1.0 (rischio minimo) → 5.0 (rischio massimo)",
            "",
        ]

        if field_map:
            lines += [
                sep2,
                "  CAMPI UTILIZZATI",
                sep2,
                "",
            ]
            for param, campo in field_map.items():
                lines.append(f"    {param:<20} → {campo}")
            lines.append("")

        lines += [
            sep2,
            "  STATISTICHE AGGREGATE",
            sep2,
            "",
            f"  CVI medio:            {stats.mean_cvi:.4f}",
            f"  CVI minimo:           {stats.min_cvi:.4f}",
            f"  CVI massimo:          {stats.max_cvi:.4f}",
            f"  Deviazione standard:  {stats.std_cvi:.4f}",
            "",
            sep2,
            "  DISTRIBUZIONE PER CLASSE DI RISCHIO",
            sep2,
            "",
            f"  {'Classe':<20} {'N. tratti':>10} {'Percentuale':>13}",
            f"  {'-'*20} {'-'*10} {'-'*13}",
        ]

        for cls in ["Molto Basso", "Basso", "Medio", "Alto", "Molto Alto"]:
            cnt = stats.distribution.get(cls, 0)
            pct = stats.distribution_pct.get(cls, 0.0)
            lines.append(f"  {cls:<20} {cnt:>10}     {pct:>8.1f} %")

        # Valutazione sintetica
        mean = stats.mean_cvi
        if mean <= 1.5:
            valutazione = "MOLTO BASSA — costa generalmente stabile."
        elif mean <= 2.5:
            valutazione = "BASSA — vulnerabilità limitata a tratti specifici."
        elif mean <= 3.5:
            valutazione = "MEDIA — monitoraggio periodico raccomandato."
        elif mean <= 4.5:
            valutazione = "ALTA — interventi di protezione consigliati."
        else:
            valutazione = "MOLTO ALTA — interventi urgenti necessari."

        lines += [
            "",
            sep2,
            "  VALUTAZIONE SINTETICA",
            sep2,
            "",
            f"  Vulnerabilità complessiva: {valutazione}",
            "",
            sep2,
            "  NOTE",
            sep2,
            "",
            "  Questo report è generato automaticamente dal plugin",
            "  Coastal Risk Dashboard per QGIS.",
            "  I risultati devono essere validati da esperti di ingegneria",
            "  costiera prima di qualsiasi applicazione gestionale.",
            "",
            sep,
        ]

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as e:
            self._log(f"Errore scrittura report TXT: {e}", Qgis.Critical)
            return False

        self._log(f"Report TXT esportato: {output_path}")
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str, level=Qgis.Info):
        QgsMessageLog.logMessage(msg, self.LOG_TAG, level=level)
