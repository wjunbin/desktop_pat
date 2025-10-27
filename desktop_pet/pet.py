from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass
class PetDefinition:
    """Configuration describing the appearance and behavior of a pet."""

    name: str
    color: QtGui.QColor
    accent_color: QtGui.QColor
    size: QtCore.QSize = QtCore.QSize(128, 128)
    image_path: Optional[str] = None


class PetSprite(QtWidgets.QLabel):
    """A label that renders a simple, programmatic pet sprite.

    If ``image_path`` is provided, the sprite will display that file. For GIFs
    or APNGs we rely on :class:`~PySide6.QtGui.QMovie` to animate frames.
    """

    BLINK_INTERVAL = (4000, 9000)
    PLAYFUL_INTERVAL = (8000, 14000)

    def __init__(self, definition: PetDefinition, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.definition = definition
        self.setFixedSize(definition.size)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setScaledContents(True)
        self._movie: Optional[QtGui.QMovie] = None

        if definition.image_path:
            self._movie = QtGui.QMovie(definition.image_path)
            if self._movie.isValid():
                self.setMovie(self._movie)
                self._movie.start()
            else:
                self._movie = None
                pixmap = QtGui.QPixmap(definition.image_path)
                self.setPixmap(pixmap.scaled(definition.size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        else:
            self._idle_pixmap = self._generate_pixmap(False)
            self._blink_pixmap = self._generate_pixmap(True)
            self.setPixmap(self._idle_pixmap)

        self._blink_timer = QtCore.QTimer(self)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._playful_timer = QtCore.QTimer(self)
        self._playful_timer.timeout.connect(self._playful_pose)
        self._schedule_blink()
        self._schedule_playful()

    def _schedule_blink(self) -> None:
        low, high = self.BLINK_INTERVAL
        self._blink_timer.start(random.randint(low, high))

    def _schedule_playful(self) -> None:
        low, high = self.PLAYFUL_INTERVAL
        self._playful_timer.start(random.randint(low, high))

    def _toggle_blink(self) -> None:
        if self._movie:
            return
        current = self.pixmap()
        if current and current.cacheKey() == self._blink_pixmap.cacheKey():
            self.setPixmap(self._idle_pixmap)
        else:
            self.setPixmap(self._blink_pixmap)
        self._schedule_blink()

    def _playful_pose(self) -> None:
        if self._movie:
            return
        animation = QtCore.QPropertyAnimation(self, b"pos")
        animation.setDuration(800)
        start = self.pos()
        animation.setKeyValueAt(0.25, start + QtCore.QPoint(8, -6))
        animation.setKeyValueAt(0.5, start + QtCore.QPoint(-8, -6))
        animation.setKeyValueAt(0.75, start + QtCore.QPoint(8, -2))
        animation.setEndValue(start)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._schedule_playful()

    def _generate_pixmap(self, blink: bool) -> QtGui.QPixmap:
        size = self.definition.size
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        body_rect = QtCore.QRect(8, 16, size.width() - 16, size.height() - 24)
        ear_left = QtGui.QPolygonF([
            QtCore.QPointF(size.width() * 0.25, 8),
            QtCore.QPointF(size.width() * 0.35, 32),
            QtCore.QPointF(size.width() * 0.15, 32),
        ])
        ear_right = QtGui.QPolygonF([
            QtCore.QPointF(size.width() * 0.75, 8),
            QtCore.QPointF(size.width() * 0.65, 32),
            QtCore.QPointF(size.width() * 0.85, 32),
        ])

        painter.setBrush(self.definition.color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawPolygon(ear_left)
        painter.drawPolygon(ear_right)
        painter.drawRoundedRect(body_rect, 40, 40)

        eye_color = QtGui.QColor("white")
        pupil_color = QtGui.QColor("black")
        accent = self.definition.accent_color

        painter.setBrush(eye_color)
        painter.drawEllipse(QtCore.QRectF(size.width() * 0.28, size.height() * 0.4, 24, 18))
        painter.drawEllipse(QtCore.QRectF(size.width() * 0.52, size.height() * 0.4, 24, 18))

        painter.setBrush(pupil_color)
        if blink:
            painter.drawRect(QtCore.QRectF(size.width() * 0.28, size.height() * 0.48, 24, 4))
            painter.drawRect(QtCore.QRectF(size.width() * 0.52, size.height() * 0.48, 24, 4))
        else:
            painter.drawEllipse(QtCore.QRectF(size.width() * 0.32, size.height() * 0.44, 12, 12))
            painter.drawEllipse(QtCore.QRectF(size.width() * 0.56, size.height() * 0.44, 12, 12))

        painter.setBrush(accent)
        painter.drawEllipse(QtCore.QRectF(size.width() * 0.45, size.height() * 0.58, 20, 12))
        painter.end()
        return pixmap

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.animate_bounce()
        super().mousePressEvent(event)

    def animate_bounce(self) -> None:
        animation = QtCore.QPropertyAnimation(self, b"pos")
        animation.setDuration(400)
        start_pos = self.pos()
        peak = QtCore.QPoint(start_pos.x(), start_pos.y() - 20)
        animation.setKeyValueAt(0.5, peak)
        animation.setEndValue(start_pos)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.OutQuad)
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)


class PetController(QtCore.QObject):
    """Coordinates the position of a pet and responds to user interaction."""

    positionChanged = QtCore.Signal(QtCore.QPoint)

    def __init__(self, widget: QtWidgets.QWidget, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.widget = widget
        self._movement_timer = QtCore.QTimer(self)
        self._movement_timer.timeout.connect(self._on_tick)
        self._current_target: Optional[QtCore.QPoint] = None
        self._base_speed = 6
        self._playful = False

    def start(self) -> None:
        self._movement_timer.start(30)
        self._choose_new_target()

    def set_playful(self, playful: bool) -> None:
        self._playful = playful

    def move_to(self, point: QtCore.QPoint) -> None:
        self._current_target = point

    def choose_new_target(self) -> None:
        self._choose_new_target()

    def _choose_new_target(self) -> None:
        window = self.widget.window() if hasattr(self.widget, "window") else None
        screen = window.screen() if window else None
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                return
            geometry = screen.availableGeometry()
        else:
            geometry = screen.availableGeometry()
        margin = 60
        x_min = geometry.left() + margin
        x_max = geometry.right() - margin - self.widget.width()
        y_min = geometry.top() + margin
        y_max = geometry.bottom() - margin - self.widget.height()
        if x_min > x_max:
            x_min, x_max = geometry.left(), geometry.right() - self.widget.width()
            if x_min > x_max:
                x_min = x_max = geometry.left()
        if y_min > y_max:
            y_min, y_max = geometry.top(), geometry.bottom() - self.widget.height()
            if y_min > y_max:
                y_min = y_max = geometry.top()
        x = random.randint(x_min, x_max)
        y = random.randint(y_min, y_max)
        self._current_target = QtCore.QPoint(x, y)

    def _on_tick(self) -> None:
        window = self.widget.window() if hasattr(self.widget, "window") else None
        if not window:
            return

        if not self._current_target:
            self._choose_new_target()
            return

        current_pos = self.widget.pos()
        target = self._current_target
        delta = target - current_pos
        distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5

        speed = self._base_speed * (0.6 if self._playful else 1.0)
        if distance < speed:
            self.widget.move(target)
            self.positionChanged.emit(self.widget.pos())
            self._choose_new_target()
            return

        if distance == 0:
            self._choose_new_target()
            return

        direction = QtCore.QPointF(delta.x() / distance, delta.y() / distance)
        step = QtCore.QPoint(int(direction.x() * speed), int(direction.y() * speed))
        if step == QtCore.QPoint(0, 0):
            step = QtCore.QPoint(1 if delta.x() > 0 else -1, 1 if delta.y() > 0 else -1)
        self.widget.move(current_pos + step)
        self.positionChanged.emit(self.widget.pos())


def default_pet_definitions() -> List[PetDefinition]:
    return [
        PetDefinition("Astral Cat", QtGui.QColor("#5D5FEF"), QtGui.QColor("#FDB827")),
        PetDefinition("Verdant Fox", QtGui.QColor("#27AE60"), QtGui.QColor("#2ECC71")),
        PetDefinition("Sunset Bun", QtGui.QColor("#EB5757"), QtGui.QColor("#F2994A")),
        PetDefinition("Aurora Pup", QtGui.QColor("#9B51E0"), QtGui.QColor("#BB6BD9")),
        PetDefinition("Nimbus Owl", QtGui.QColor("#2D9CDB"), QtGui.QColor("#56CCF2")),
    ]
