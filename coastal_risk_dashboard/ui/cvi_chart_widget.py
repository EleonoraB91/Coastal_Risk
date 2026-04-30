# -*- coding: utf-8 -*-
"""
ui/cvi_chart_widget.py
Widget grafico a barre per la distribuzione delle classi di rischio CVI.

Disegnato interamente con QPainter nativo — zero dipendenze esterne.
Funziona in qualsiasi installazione QGIS senza matplotlib o altri pacchetti.

Caratteristiche:
  - 5 barre colorate (verde → rosso) per le classi di rischio
  - Animazione di ingresso (barre che crescono)
  - Tooltip interattivo al passaggio del mouse con n. tratti e %
  - Asse Y con griglia tratteggiata
  - Ridimensionamento responsivo
  - Modalità "vuoto" con messaggio placeholder
"""

from typing import Dict, Optional, List, Tuple
from qgis.PyQt.QtWidgets import QWidget, QToolTip, QSizePolicy
from qgis.PyQt.QtCore import (
    Qt, QRect, QRectF, QPointF, QTimer, pyqtSignal,
)
from qgis.PyQt.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QPen,
    QLinearGradient, QPainterPath, QBrush,
)


# Palette rischio — (hex_fill, hex_border, label_corto, label_esteso)
RISK_BARS: List[Tuple[str, str, str, str]] = [
    ("#2ecc71", "#27ae60", "Molto\nBasso", "Molto Basso  (1.0–1.5)"),
    ("#a8d08d", "#7dba5a", "Basso",        "Basso        (1.5–2.5)"),
    ("#f1c40f", "#d4ac0d", "Medio",        "Medio        (2.5–3.5)"),
    ("#e67e22", "#ca6f1e", "Alto",          "Alto         (3.5–4.5)"),
    ("#e74c3c", "#cb4335", "Molto\nAlto",  "Molto Alto   (4.5–5.0)"),
]

RISK_CLASSES = ["Molto Basso", "Basso", "Medio", "Alto", "Molto Alto"]


class CVIChartWidget(QWidget):
    """
    Grafico a barre interattivo per la distribuzione delle classi di rischio CVI.

    Segnali:
        bar_clicked(risk_class: str)  — emesso al click su una barra

    Uso tipico:
        chart = CVIChartWidget(parent)
        chart.update_data(stats.distribution, stats.distribution_pct, stats.count)
    """

    bar_clicked = pyqtSignal(str)

    # Costanti layout
    MARGIN_LEFT   = 52   # spazio asse Y
    MARGIN_RIGHT  = 16
    MARGIN_TOP    = 20
    MARGIN_BOTTOM = 52   # spazio etichette X
    BAR_GAP       = 0.18 # gap tra barre (frazione della larghezza barra)
    CORNER_RADIUS = 5
    ANIMATION_MS  = 600  # durata animazione ingresso (ms)
    ANIMATION_FPS = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        # Dati
        self._counts: Dict[str, int] = {}
        self._pcts:   Dict[str, float] = {}
        self._total:  int = 0
        self._max_count: int = 1

        # Stato animazione
        self._anim_progress: float = 0.0   # 0.0 → 1.0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_step)

        # Stato hover
        self._hovered_bar: Optional[int] = None

        # Cache geometrie barre (aggiornata in paintEvent)
        self._bar_rects: List[QRect] = []

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def update_data(
        self,
        distribution: Dict[str, int],
        distribution_pct: Dict[str, float],
        total: int,
    ):
        """
        Aggiorna i dati del grafico e avvia l'animazione di ingresso.

        :param distribution:     {classe: n_tratti}
        :param distribution_pct: {classe: percentuale}
        :param total:            numero totale di tratti
        """
        self._counts = {cls: distribution.get(cls, 0) for cls in RISK_CLASSES}
        self._pcts   = {cls: distribution_pct.get(cls, 0.0) for cls in RISK_CLASSES}
        self._total  = total
        self._max_count = max(max(self._counts.values(), default=1), 1)

        # Avvia animazione
        self._anim_progress = 0.0
        self._anim_timer.start(1000 // self.ANIMATION_FPS)

    def clear(self):
        """Azzera il grafico mostrando il placeholder."""
        self._counts = {}
        self._pcts   = {}
        self._total  = 0
        self._max_count = 1
        self._anim_progress = 0.0
        self._anim_timer.stop()
        self.update()

    # ------------------------------------------------------------------
    # Animazione
    # ------------------------------------------------------------------

    def _anim_step(self):
        step = 1.0 / (self.ANIMATION_MS / (1000 / self.ANIMATION_FPS))
        self._anim_progress = min(1.0, self._anim_progress + step)
        self.update()
        if self._anim_progress >= 1.0:
            self._anim_timer.stop()

    @staticmethod
    def _ease_out(t: float) -> float:
        """Easing cubico in uscita per animazione fluida."""
        return 1 - (1 - t) ** 3

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        h = self.height()

        # Sfondo
        painter.fillRect(0, 0, w, h, QColor("#fafbfc"))

        if not self._counts or self._total == 0:
            self._draw_placeholder(painter, w, h)
            painter.end()
            return

        # Aree del grafico
        plot_x = self.MARGIN_LEFT
        plot_y = self.MARGIN_TOP
        plot_w = w - self.MARGIN_LEFT - self.MARGIN_RIGHT
        plot_h = h - self.MARGIN_TOP - self.MARGIN_BOTTOM

        self._draw_grid(painter, plot_x, plot_y, plot_w, plot_h)
        self._draw_bars(painter, plot_x, plot_y, plot_w, plot_h)
        self._draw_axes(painter, plot_x, plot_y, plot_w, plot_h)
        self._draw_title_row(painter, w, h)

        painter.end()

    def _draw_placeholder(self, painter: QPainter, w: int, h: int):
        """Messaggio centrato quando non ci sono dati."""
        painter.setPen(QColor("#b0bec5"))
        font = QFont("Arial", 11)
        font.setItalic(True)
        painter.setFont(font)
        painter.drawText(
            QRect(0, 0, w, h),
            Qt.AlignCenter,
            "Esegui il calcolo CVI\nper visualizzare la distribuzione del rischio",
        )

    def _draw_grid(self, painter, px, py, pw, ph):
        """Linee orizzontali di griglia con valori asse Y."""
        n_lines = 4
        pen = QPen(QColor("#e0e6ea"), 1, Qt.DashLine)
        painter.setPen(pen)
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.setPen(QColor("#90a4ae"))

        for i in range(n_lines + 1):
            y = py + ph - int(ph * i / n_lines)
            # Linea griglia
            grid_pen = QPen(QColor("#e0e6ea"), 1, Qt.DashLine)
            painter.setPen(grid_pen)
            painter.drawLine(px, y, px + pw, y)
            # Label asse Y
            val = int(self._max_count * i / n_lines)
            painter.setPen(QColor("#78909c"))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(
                QRect(0, y - 10, px - 4, 20),
                Qt.AlignRight | Qt.AlignVCenter,
                str(val),
            )

    def _draw_bars(self, painter, px, py, pw, ph):
        """Barre colorate con gradiente e arrotondamento."""
        n = len(RISK_BARS)
        slot_w = pw / n
        bar_w  = slot_w * (1 - self.BAR_GAP)
        ease   = self._ease_out(self._anim_progress)

        self._bar_rects = []

        for i, (fill_hex, border_hex, _, _) in enumerate(RISK_BARS):
            cls   = RISK_CLASSES[i]
            count = self._counts.get(cls, 0)
            pct   = self._pcts.get(cls, 0.0)

            # Altezza barra con animazione
            bar_h_full = int(ph * count / self._max_count) if self._max_count > 0 else 0
            bar_h = int(bar_h_full * ease)

            bx = int(px + slot_w * i + slot_w * self.BAR_GAP / 2)
            by = py + ph - bar_h
            bw = int(bar_w)

            # Salva rect per hover/click
            full_rect = QRect(bx, py + ph - bar_h_full, bw, bar_h_full)
            self._bar_rects.append(full_rect)

            if bar_h == 0:
                continue

            rect = QRect(bx, by, bw, bar_h)
            is_hovered = (self._hovered_bar == i)

            # Gradiente verticale: colore pieno → leggermente più chiaro
            grad = QLinearGradient(bx, by, bx, by + bar_h)
            base  = QColor(fill_hex)
            light = base.lighter(120)
            grad.setColorAt(0.0, light if is_hovered else base.lighter(110))
            grad.setColorAt(1.0, base)
            painter.setBrush(QBrush(grad))

            # Bordo
            border_color = QColor(border_hex)
            if is_hovered:
                border_color = border_color.darker(130)
                painter.setPen(QPen(border_color, 2))
            else:
                painter.setPen(QPen(border_color, 1))

            # Disegna barra con angoli arrotondati (solo in cima)
            path = QPainterPath()
            r = float(min(self.CORNER_RADIUS, bw // 2, bar_h // 2))
            path.moveTo(bx, by + bar_h)
            path.lineTo(bx, by + r)
            path.arcTo(QRectF(bx, by, 2 * r, 2 * r), 180, -90)
            path.lineTo(bx + bw - r, by)
            path.arcTo(QRectF(bx + bw - 2 * r, by, 2 * r, 2 * r), 90, -90)
            path.lineTo(bx + bw, by + bar_h)
            path.closeSubpath()
            painter.drawPath(path)

            # Etichetta valore sopra la barra (solo se c'è spazio)
            if bar_h > 22 and self._anim_progress >= 0.85:
                painter.setPen(QColor("#1a1a1a"))
                painter.setFont(QFont("Arial", 8, QFont.Bold))
                painter.drawText(
                    QRect(bx, by - 18, bw, 18),
                    Qt.AlignCenter,
                    f"{pct:.0f}%",
                )

            # Etichetta classe sotto la barra
            painter.setPen(QColor("#37474f"))
            painter.setFont(QFont("Arial", 8))
            label_rect = QRect(
                bx - 4,
                py + ph + 4,
                bw + 8,
                self.MARGIN_BOTTOM - 8,
            )
            painter.drawText(label_rect, Qt.AlignCenter | Qt.TextWordWrap, RISK_BARS[i][2])

    def _draw_axes(self, painter, px, py, pw, ph):
        """Asse X e Y."""
        ax_pen = QPen(QColor("#90a4ae"), 1)
        painter.setPen(ax_pen)
        # Asse Y
        painter.drawLine(px, py, px, py + ph)
        # Asse X
        painter.drawLine(px, py + ph, px + pw, py + ph)

    def _draw_title_row(self, painter, w, h):
        """Titolo asse Y."""
        painter.save()
        painter.translate(12, h // 2)
        painter.rotate(-90)
        painter.setPen(QColor("#546e7a"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRect(-60, -8, 120, 16), Qt.AlignCenter, "N. tratti")
        painter.restore()

    # ------------------------------------------------------------------
    # Interattività
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event):
        hovered = self._bar_index_at(event.pos())
        if hovered != self._hovered_bar:
            self._hovered_bar = hovered
            self.update()

        if hovered is not None:
            cls   = RISK_CLASSES[hovered]
            count = self._counts.get(cls, 0)
            pct   = self._pcts.get(cls, 0.0)
            tip   = (
                f"<b>{RISK_BARS[hovered][3]}</b><br>"
                f"Tratti: <b>{count}</b> su {self._total}<br>"
                f"Percentuale: <b>{pct:.1f}%</b>"
            )
            QToolTip.showText(event.globalPos(), tip, self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self._bar_index_at(event.pos())
            if idx is not None:
                self.bar_clicked.emit(RISK_CLASSES[idx])

    def leaveEvent(self, event):
        self._hovered_bar = None
        self.update()

    def _bar_index_at(self, pos) -> Optional[int]:
        """Restituisce l'indice della barra sotto il cursore, o None."""
        for i, rect in enumerate(self._bar_rects):
            # Allarga la zona cliccabile fino all'asse X per comodità
            extended = QRect(
                rect.x(), self.MARGIN_TOP,
                rect.width(), self.height() - self.MARGIN_TOP - self.MARGIN_BOTTOM,
            )
            if extended.contains(pos):
                return i
        return None

    def resizeEvent(self, event):
        self.update()
