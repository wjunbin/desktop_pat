from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .hotspots import HotspotManager, HotspotOverlay
from .pet import PetController, PetDefinition, PetSprite, default_pet_definitions


class DesktopPetWindow(QtWidgets.QWidget):
    """Frameless, transparent window that renders a single pet."""

    def __init__(self, definition: PetDefinition, manager: HotspotManager, overlay: HotspotOverlay, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.definition = definition
        self.hotspot_manager = manager
        self.overlay = overlay
        self.setWindowTitle(definition.name)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
            | QtCore.Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.sprite = PetSprite(definition, self)
        self.sprite.move(0, 0)
        self.setFixedSize(self.sprite.size())

        self.controller = PetController(self)
        self.controller.positionChanged.connect(self._handle_position_changed)
        self.controller.start()

        self._drag_offset: Optional[QtCore.QPoint] = None
        self._interaction_timer = QtCore.QTimer(self)
        self._interaction_timer.setInterval(1000)
        self._interaction_timer.timeout.connect(self._encourage_hotspot_visit)
        self._interaction_timer.start()

    def showEvent(self, event: QtGui.QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        screen = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        center = QtCore.QPoint(screen.center().x() - self.width() // 2, screen.bottom() - self.height() - 80)
        self.move(center)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self.controller.set_playful(True)
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.controller.set_playful(False)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._drag_offset:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            self.controller.move_to(new_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.controller.set_playful(False)
            self.controller.choose_new_target()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.overlay.isVisible():
                self.overlay.hide()
            else:
                self.overlay.showFullScreen()
                self.overlay.raise_()
        super().mouseDoubleClickEvent(event)

    def _handle_position_changed(self, position: QtCore.QPoint) -> None:
        center = QtCore.QPoint(position.x() + self.width() // 2, position.y() + self.height() // 2)
        hotspot = self.hotspot_manager.nearest_hotspot(center)
        if hotspot:
            target = QtCore.QPoint(hotspot.geometry.center().x() - self.width() // 2, hotspot.geometry.top() - self.height())
            self.controller.move_to(target)
            self.controller.set_playful(True)
        else:
            self.controller.set_playful(False)

    def _encourage_hotspot_visit(self) -> None:
        if not self.hotspot_manager.hotspots:
            return
        target_hotspot = self.hotspot_manager.hotspots[0]
        target = QtCore.QPoint(
            target_hotspot.geometry.center().x() - self.width() // 2,
            target_hotspot.geometry.bottom() - self.height(),
        )
        self.controller.move_to(target)


class PetSelectionDialog(QtWidgets.QDialog):
    """Dialog for selecting one of the default pets or importing a custom sprite."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose your desktop companion")
        self.setModal(True)
        self.resize(420, 320)
        self._selected_definition: Optional[PetDefinition] = None

        layout = QtWidgets.QVBoxLayout(self)
        intro = QtWidgets.QLabel(
            "选择一个默认宠物或者导入自定义形象。双击桌面宠物可以打开热点编辑器，在你的桌面上绘制可互动区域。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.list_widget = QtWidgets.QListWidget()
        for definition in default_pet_definitions():
            item = QtWidgets.QListWidgetItem(definition.name)
            sprite = PetSprite(definition)
            pixmap = sprite.pixmap()
            if pixmap:
                item.setIcon(QtGui.QIcon(pixmap))
            sprite.deleteLater()
            item.setData(QtCore.Qt.ItemDataRole.UserRole, definition)
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        button_layout = QtWidgets.QHBoxLayout()
        self.import_button = QtWidgets.QPushButton("导入自定义宠物…")
        self.import_button.clicked.connect(self._import_custom_pet)
        self.confirm_button = QtWidgets.QPushButton("确认")
        self.confirm_button.clicked.connect(self._accept_selection)
        button_layout.addWidget(self.import_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.confirm_button)
        layout.addLayout(button_layout)

    def _import_custom_pet(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择宠物图像",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.gif *.apng);;All Files (*)",
        )
        if not file_path:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "宠物名称", "为你的宠物起一个名字：")
        if not ok or not name:
            return
        definition = PetDefinition(name, QtGui.QColor("white"), QtGui.QColor("#CCCCCC"), image_path=file_path)
        self._selected_definition = definition
        self.accept()

    def _accept_selection(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            QtWidgets.QMessageBox.information(self, "提示", "请选择一个宠物或者导入自定义宠物。")
            return
        self._selected_definition = item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    def selected_definition(self) -> Optional[PetDefinition]:
        return self._selected_definition


class MainController(QtCore.QObject):
    """Application controller that wires together selection, pet window, and hotspots."""

    def __init__(self) -> None:
        super().__init__()
        self.hotspot_manager = HotspotManager()
        self.hotspot_overlay = HotspotOverlay(self.hotspot_manager)
        self.pet_window: Optional[DesktopPetWindow] = None

    def run(self) -> int:
        dialog = PetSelectionDialog()
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return 0
        definition = dialog.selected_definition()
        if not definition:
            return 0
        self.pet_window = DesktopPetWindow(definition, self.hotspot_manager, self.hotspot_overlay)
        self.pet_window.show()
        return 0

def run() -> None:
    app = QtWidgets.QApplication(sys.argv)
    controller = MainController()
    exit_code = controller.run()
    sys.exit(app.exec() if controller.pet_window else exit_code)
