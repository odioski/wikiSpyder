# Codename: Michelle
import os
import shutil

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _available_destination(folder: str, image_path: str) -> str:
    name = os.path.basename(image_path)
    stem, extension = os.path.splitext(name)
    destination = os.path.join(folder, name)
    suffix = 1
    while os.path.exists(destination):
        destination = os.path.join(folder, f"{stem} ({suffix}){extension}")
        suffix += 1
    return destination


def save_selected_images(parent: QWidget, selected_images: list[str]) -> int:
    valid_images = [path for path in selected_images if os.path.isfile(path)]
    if not valid_images:
        QMessageBox.information(parent, "Save Images", "Select at least one available image.")
        return 0

    folder_path = QFileDialog.getExistingDirectory(
        parent, "Choose a Folder for Selected Images"
    )
    if not folder_path:
        return 0

    saved = 0
    failures: list[str] = []
    for image_path in valid_images:
        try:
            destination = _available_destination(folder_path, image_path)
            shutil.copy2(image_path, destination)
            saved += 1
        except OSError as exc:
            failures.append(f"{os.path.basename(image_path)}: {exc}")

    if failures:
        detail = "\n".join(failures[:5])
        if len(failures) > 5:
            detail += f"\n…and {len(failures) - 5} more"
        QMessageBox.warning(
            parent,
            "Images Saved with Errors",
            f"Saved {saved} of {len(valid_images)} selected images to {folder_path}.\n\n{detail}",
        )
    else:
        QMessageBox.information(
            parent,
            "Images Saved",
            f"Saved {saved} selected image(s) to {folder_path}.",
        )
    return saved


class ImageGallery(QWidget):
    """Selectable image gallery embedded in the main application window."""

    backRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._images: list[tuple[str, str]] = []
        self._checkboxes: list[QCheckBox] = []
        self._cards: list[QFrame] = []

        self.setObjectName("image_gallery")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.count_label = QLabel("No images loaded")
        self.select_all_checkbox = QCheckBox("Select All")
        self.save_button = QPushButton("Save Selected Images")
        self.back_button = QPushButton("Back to Results")
        toolbar.addWidget(self.count_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self.select_all_checkbox)
        toolbar.addWidget(self.save_button)
        toolbar.addWidget(self.back_button)
        layout.addLayout(toolbar)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("gallery_scroll_area")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.content = QWidget()
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(10, 10, 10, 10)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("gallery_status")
        layout.addWidget(self.status_label)

        self.select_all_checkbox.stateChanged.connect(self._select_all)
        self.save_button.clicked.connect(self._save_selected)
        self.back_button.clicked.connect(self.backRequested.emit)
        self.set_images([])

    def set_images(self, images: list[tuple[str, str]]) -> None:
        self._images = list(images)
        self._checkboxes.clear()
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        for index, (image_path, image_url) in enumerate(self._images):
            card = QFrame(self.content)
            card.setObjectName("image_card")
            card_layout = QVBoxLayout(card)
            preview = QLabel()
            preview.setObjectName("image_preview")
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setFixedSize(204, 154)
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                preview.setPixmap(
                    pixmap.scaled(
                        preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                preview.setText("Preview unavailable")

            source = QLabel(image_url)
            source.setObjectName("image_source")
            source.setToolTip(image_url)
            source.setWordWrap(True)
            source.setMaximumHeight(38)
            checkbox = QCheckBox(f"Image {index + 1}")
            checkbox.setChecked(False)
            self._checkboxes.append(checkbox)
            card_layout.addWidget(preview, 0, Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(source)
            card_layout.addWidget(checkbox)
            self._cards.append(card)

        self._reflow_cards()

        self.count_label.setText(
            f"{len(self._images)} image(s) found · select images to save"
            if self._images
            else "No images found"
        )
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(False)
        self.select_all_checkbox.blockSignals(False)
        self.select_all_checkbox.setEnabled(bool(self._images))
        self.save_button.setEnabled(bool(self._images))
        self.status_label.clear()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow_cards()

    def _reflow_cards(self) -> None:
        if not hasattr(self, "grid"):
            return
        while self.grid.count():
            self.grid.takeAt(0)
        columns = max(1, min(4, (self.width() - 40) // 236))
        for index, card in enumerate(self._cards):
            self.grid.addWidget(card, index // columns, index % columns)

    def selected_images(self) -> list[str]:
        return [
            image_path
            for (image_path, _image_url), checkbox in zip(
                self._images, self._checkboxes
            )
            if checkbox.isChecked()
        ]

    def _select_all(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        for checkbox in self._checkboxes:
            checkbox.setChecked(checked)

    def _save_selected(self) -> None:
        count = save_selected_images(self, self.selected_images())
        if count:
            self.status_label.setText(f"Saved {count} selected image(s).")
