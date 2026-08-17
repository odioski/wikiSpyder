# Codename: Michelle
import os
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ClickableImageLabel(QLabel):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url


def save_selected_images(parent: QWidget, selected_images: list[str]) -> None:
    folder_path = QFileDialog.getExistingDirectory(
        parent, "Select Folder to Save Images"
    )
    if not folder_path:
        return

    try:
        for image_path in selected_images:
            if not os.path.isfile(image_path):
                continue

            default_name = os.path.join(folder_path, os.path.basename(image_path))
            filename, _ = QFileDialog.getSaveFileName(
                parent,
                "Save Image As",
                default_name,
                "Images (*.png *.xpm *.jpg *.jpeg *.gif *.webp)",
            )
            if filename:
                shutil.copy(image_path, filename)
        QMessageBox.information(
            parent, "Success", f"Selected images saved to {folder_path}"
        )
    except OSError as exc:
        QMessageBox.critical(parent, "Error", f"Failed to save images: {exc}")


def launch_image_viewer(parent: QWidget, images: list[tuple[str, str]]) -> None:
    if not images:
        QMessageBox.information(parent, "Images", "No images found to display.")
        return

    image_dialog = QDialog(parent)
    image_dialog.setWindowTitle("Image Viewer")

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

    dialog_widget = QWidget()
    dialog_layout = QVBoxLayout(dialog_widget)
    row_layout = QVBoxLayout()
    row = QHBoxLayout()

    selected_images: list[str] = []
    checkboxes: list[QCheckBox] = []

    for index, (image_path, image_url) in enumerate(images, start=1):
        image_label = ClickableImageLabel(image_url)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedSize(200, 200)
        image_label.setStyleSheet("border: 1px solid white;")

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            image_label.setPixmap(
                pixmap.scaled(
                    image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        checkbox = QCheckBox()

        def on_state_changed(state: int, image_path: str = image_path) -> None:
            is_checked = Qt.CheckState(state) == Qt.CheckState.Checked
            if is_checked:
                if image_path not in selected_images:
                    selected_images.append(image_path)
            elif image_path in selected_images:
                selected_images.remove(image_path)

        checkbox.stateChanged.connect(on_state_changed)
        checkboxes.append(checkbox)

        image_layout = QVBoxLayout()
        image_layout.addWidget(image_label)
        image_layout.addWidget(checkbox)
        row.addLayout(image_layout)

        if index % 5 == 0:
            row_layout.addLayout(row)
            row = QHBoxLayout()

    if images and len(images) % 5 != 0:
        row_layout.addLayout(row)

    dialog_layout.addLayout(row_layout)
    dialog_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    scroll_area.setWidget(dialog_widget)

    image_dialog_layout = QVBoxLayout(image_dialog)
    image_dialog_layout.addWidget(scroll_area)

    select_all_checkbox = QCheckBox("Select All")

    def select_all_images(state: int) -> None:
        is_checked = Qt.CheckState(state) == Qt.CheckState.Checked
        for checkbox in checkboxes:
            checkbox.setChecked(is_checked)

    select_all_checkbox.stateChanged.connect(select_all_images)
    image_dialog_layout.addWidget(select_all_checkbox)

    save_button = QPushButton("Save Selected Images")
    save_button.clicked.connect(
        lambda: save_selected_images(parent, selected_images)
    )
    image_dialog_layout.addWidget(save_button)

    image_dialog.setLayout(image_dialog_layout)
    image_dialog.setFixedWidth(5 * 200 + 40)
    image_dialog.exec()
