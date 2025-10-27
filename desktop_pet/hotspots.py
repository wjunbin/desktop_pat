from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class Hotspot:
    """Represents an interactive zone where the pet can perform special actions."""

    name: str
    geometry: QtCore.QRect
    behavior: str = "idle"


@dataclass
class HotspotManager:
    """Stores hotspots and notifies listeners when they change."""

    hotspots: List[Hotspot] = field(default_factory=list)

    def add_hotspot(self, hotspot: Hotspot) -> None:
        self.hotspots.append(hotspot)

    def remove_hotspot(self, hotspot: Hotspot) -> None:
        self.hotspots.remove(hotspot)

    def nearest_hotspot(self, point: QtCore.QPoint) -> Optional[Hotspot]:
        for hotspot in self.hotspots:
            if hotspot.geometry.contains(point):
                return hotspot
        return None


class HotspotOverlay(QtWidgets.QWidget):
    """Semi-transparent overlay used to visualize hotspot placement."""

    def __init__(self, manager: HotspotManager, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Hotspot Overlay")
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._drag_origin: Optional[QtCore.QPoint] = None
        self._current_rect: Optional[QtCore.QRect] = None
        self.hide()

    def toggle(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showFullScreen()
            self.raise_()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(20, 20, 20, 40))

        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 160))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtGui.QColor(93, 95, 239, 80))
        for hotspot in self.manager.hotspots:
            painter.drawRoundedRect(hotspot.geometry, 8, 8)

        if self._current_rect:
            painter.setBrush(QtGui.QColor(235, 87, 87, 80))
            painter.drawRoundedRect(self._current_rect, 8, 8)
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_origin = event.position().toPoint()
            self._current_rect = QtCore.QRect(self._drag_origin, QtCore.QSize())
            self.update()
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            hotspot = self._hotspot_at(event.position().toPoint())
            if hotspot:
                self.manager.remove_hotspot(hotspot)
                self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._drag_origin:
            rect = QtCore.QRect(self._drag_origin, event.position().toPoint()).normalized()
            self._current_rect = rect
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._drag_origin and self._current_rect:
            rect = QtCore.QRect(self._drag_origin, event.position().toPoint()).normalized()
            if rect.width() > 10 and rect.height() > 10:
                name = f"Hotspot {len(self.manager.hotspots) + 1}"
                self.manager.add_hotspot(Hotspot(name, rect))
            self._drag_origin = None
            self._current_rect = None
            self.update()
        super().mouseReleaseEvent(event)

    def _hotspot_at(self, point: QtCore.QPoint) -> Optional[Hotspot]:
        for hotspot in reversed(self.manager.hotspots):
            if hotspot.geometry.contains(point):
                return hotspot
        return None
