from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from io import BytesIO
from urllib.parse import urljoin

import aiohttp
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
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

from newwindow import Ui_Dialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "saved_images")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
IMAGE_PATTERN = re.compile(r"\.(?:jpg|jpeg|png|gif|webp)(?:$|[?#])", re.IGNORECASE)

os.makedirs(IMG_DIR, exist_ok=True)


@dataclass
class GlobalState:
    found_links: list[str] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    wikipedia_url: str = ""
    matched_links: list[str] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    fixed_links: list[str] = field(default_factory=list)


global_state = GlobalState()


class ClickableImageLabel(QLabel):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url

    # def mousePressEvent(self, event: QMouseEvent | None) -> None:
    #     QDesktopServices.openUrl(QUrl(self._url))
    #     super().mousePressEvent(event)


class MainWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._configure_ui()
        self._connect_signals()

    def _configure_ui(self) -> None:
        self.setWindowTitle("wikiSpyder 0.3.1")

        self.ui.buttonBox.hide()
        self.ui.verticalScrollBar.hide()
        self.ui.verticalScrollBar_3.hide()

        for label in (self.ui.label_4, self.ui.label_5):
            label.setWordWrap(True)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.ui.label_4.setText("Search results will appear here.")
        self.ui.label_5.setText("Link tally and image status will appear here.")

    def _connect_signals(self) -> None:
        self.ui.subject_url.textChanged.connect(self.disco_subject)
        self.ui.lineEdit_2.textChanged.connect(self.disco_terms)
        self.ui.pushButton.clicked.connect(self.spyder_1st_run)
        self.ui.pushButton_2.clicked.connect(self.deep_probe_view)
        self.ui.pushButton_3.clicked.connect(self.view_images)

    def disco_subject(self, text: str) -> None:
        global_state.wikipedia_url = self._normalize_subject_url(text)
        if not global_state.wikipedia_url:
            self.ui.label_4.setText("Please fill in the form...")

    def disco_terms(self, text: str) -> None:
        global_state.search_terms = [
            term for term in re.split(r"[\s,]+", text.strip()) if term
        ]

    def save_found_links(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Found Links",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("Found Links:\n")
            for link in global_state.found_links:
                file.write(f"{link}\n")

    def save_matched_links(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Matched Links",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as file:
            file.write("Matched Links:\n")
            for link in global_state.matched_links:
                file.write(f"{link}\n")

    def save_images(self) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder to Save Images"
        )
        if not folder_path:
            return

        try:
            for filename in os.listdir(IMG_DIR):
                source_path = os.path.join(IMG_DIR, filename)
                if os.path.isfile(source_path):
                    shutil.copy(source_path, folder_path)
            QMessageBox.information(self, "Success", f"Images saved to {folder_path}")
        except OSError as exc:
            QMessageBox.critical(
                self, "Error", f"Failed to save images: {exc}"
            )

    def save_selected_images(self, selected_images: list[str]) -> None:
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder to Save Images"
        )
        if not folder_path:
            return

        try:
            for image_path in selected_images:
                if not os.path.isfile(image_path):
                    continue

                default_name = os.path.join(
                    folder_path, os.path.basename(image_path)
                )
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Image As",
                    default_name,
                    "Images (*.png *.xpm *.jpg *.jpeg *.gif *.webp)",
                )
                if filename:
                    shutil.copy(image_path, filename)
            QMessageBox.information(
                self, "Success", f"Selected images saved to {folder_path}"
            )
        except OSError as exc:
            QMessageBox.critical(
                self, "Error", f"Failed to save images: {exc}"
            )

    def spyder_1st_run(self) -> None:
        if not global_state.wikipedia_url:
            self.ui.label_4.setText("No subject URL found...")
            return

        self.ui.label_4.setText("Launching spider...")
        QApplication.processEvents()

        result = self.scrape_wikipedia_references(
            global_state.wikipedia_url,
            global_state.search_terms,
        )
        self.ui.label_4.setText(self.format_links(result))
        self.ui.label_5.setText(self.tally_links())

    def scrape_wikipedia_references(
        self, url: str, search_terms: list[str]
    ) -> list[str]:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return [f"Request error: {exc}"]

        try:
            soup = BeautifulSoup(response.content, "html.parser")
            references_section = soup.find("ol", class_="references") or soup.find(
                "div",
                class_="reflist reflist-columns references-column-width",
            )
            if references_section is None:
                global_state.found_links = []
                global_state.fixed_links = []
                global_state.matched_links = []
                return ["No references section found."]

            fixed_links: list[str] = []
            for tag in references_section.find_all("a", href=True):
                href = str(tag.get("href", "")).strip()
                if not href:
                    continue
                if href.startswith("http://") or href.startswith("https://"):
                    fixed_links.append(href)
                elif href.startswith("//"):
                    fixed_links.append(f"https:{href}")
                else:
                    fixed_links.append(urljoin("https://en.wikipedia.org", href))

            global_state.found_links = fixed_links
            global_state.fixed_links = fixed_links

            lowered_terms = [term.lower() for term in search_terms]
            if not lowered_terms:
                global_state.matched_links = []
                return fixed_links

            matched_links = [
                link
                for link in fixed_links
                if any(term in link.lower() for term in lowered_terms)
            ]
            global_state.matched_links = matched_links
            return (
                matched_links
                if matched_links
                else ["No matching links found in references."]
            )
        except Exception as exc:
            return [f"An error occurred: {exc}"]

    async def download_image(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore,
    ) -> None:
        async with semaphore:
            try:
                async with session.get(url, headers={"User-Agent": USER_AGENT}) as response:
                    response.raise_for_status()
                    html = await response.text()
            except aiohttp.ClientError as exc:
                global_state.messages.append(f"Skipping {url}: {exc}")
                return

            soup = BeautifulSoup(html, "html.parser")
            discovered_urls: list[str] = []
            for tag in soup.find_all("img", src=True):
                src = str(tag.get("src", "")).strip()
                image_url = self._normalize_image_url(src, url)
                if not image_url or image_url in global_state.image_urls:
                    continue
                global_state.image_urls.append(image_url)
                discovered_urls.append(image_url)

            if discovered_urls:
                self.ui.label_5.setText(
                    f"Found {len(discovered_urls)} image candidates on:\n{url}"
                )
                QApplication.processEvents()

            for image_url in discovered_urls:
                try:
                    async with session.get(
                        image_url, headers={"User-Agent": USER_AGENT}
                    ) as img_response:
                        img_response.raise_for_status()
                        img_data = await img_response.read()
                except aiohttp.ClientError:
                    continue

                output_path = self._build_image_path(image_url)
                try:
                    with Image.open(BytesIO(img_data)) as image:
                        image.verify()
                    with Image.open(BytesIO(img_data)) as image:
                        image.save(output_path)
                except (UnidentifiedImageError, OSError):
                    continue

                global_state.images.append((output_path, image_url))

    async def find_images_async(self, urls: list[str]) -> None:
        if not urls:
            return

        timeout = aiohttp.ClientTimeout(total=60)
        connector = aiohttp.TCPConnector(limit_per_host=10)
        semaphore = asyncio.Semaphore(10)
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
        ) as session:
            tasks = [self.download_image(session, url, semaphore) for url in urls]
            await asyncio.gather(*tasks)

    def find_images(self, urls: list[str]) -> list[tuple[str, str]]:
        self.cleanup_images()
        global_state.messages.clear()
        global_state.image_urls.clear()

        if not urls:
            self.ui.label_5.setText("No links available for image probing.")
            return []

        self.ui.label_5.setText("Finding images...")
        QApplication.processEvents()

        try:
            asyncio.run(self.find_images_async(urls))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.find_images_async(urls))
            finally:
                loop.close()
        except Exception as exc:
            self.ui.label_5.setText(f"An error occurred: {exc}")
            return []

        if global_state.images:
            self.ui.label_5.setText(
                f"Found {len(global_state.images)} images ready to view."
            )
        else:
            self.ui.label_5.setText("No images found.")
        return global_state.images

    def launch_image_viewer(self) -> None:
        if not global_state.images:
            QMessageBox.information(self, "Images", "No images found to display.")
            return

        image_dialog = QDialog(self)
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

        for index, (image_path, image_url) in enumerate(global_state.images, start=1):
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

        if global_state.images and len(global_state.images) % 5 != 0:
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
            lambda: self.save_selected_images(selected_images)
        )
        image_dialog_layout.addWidget(save_button)

        image_dialog.setLayout(image_dialog_layout)
        image_dialog.setFixedWidth(5 * 200 + 40)
        image_dialog.exec()

    def view_images(self) -> None:
        links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.find_images(links)
        self.launch_image_viewer()

    def deep_probe_view(self) -> None:
        self.find_images(global_state.fixed_links)
        self.launch_image_viewer()

    def format_links(self, links: list[str]) -> str:
        if not links:
            return "No links found."

        formatted_links: list[str] = []
        for index, link in enumerate(links, start=1):
            if link.startswith("http://") or link.startswith("https://"):
                formatted_links.append(
                    f'{index}. <a href="{link}" '
                    'style="color: yellow; text-decoration: underline;">'
                    f"{link}</a>"
                )
            else:
                formatted_links.append(f"{index}. {link}")

        return (
            "<h2>Links Found</h2>"
            "<h4>Click a link to visit it.</h4><br/>"
            + "<br/>".join(formatted_links)
        )

    def tally_links(self) -> str:
        return (
            "<h2>Tally</h2>"
            f"<p>Found Links = {len(global_state.fixed_links)}</p>"
            f"<p>Matched Links = {len(global_state.matched_links)}</p>"
            f"<p>Images Saved = {len(global_state.images)}</p>"
        )

    def cleanup_images(self) -> None:
        global_state.images.clear()
        for filename in os.listdir(IMG_DIR):
            file_path = os.path.join(IMG_DIR, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    continue

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cleanup_images()
        event.accept()

    @staticmethod
    def _normalize_subject_url(text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        if cleaned.startswith(("http://", "https://")):
            return cleaned
        if cleaned.startswith(("wikipedia.org/", "en.wikipedia.org/")):
            return f"https://{cleaned}"
        if cleaned.startswith("/wiki/"):
            return f"https://en.wikipedia.org{cleaned}"
        return f"https://en.wikipedia.org/wiki/{cleaned.replace(' ', '_')}"

    @staticmethod
    def _normalize_image_url(src: str, page_url: str) -> str | None:
        if not src:
            return None
        if src.startswith("//"):
            candidate = f"https:{src}"
        else:
            candidate = urljoin(page_url, src)
        if not IMAGE_PATTERN.search(candidate):
            return None
        return candidate

    def _build_image_path(self, image_url: str) -> str:
        filename = os.path.basename(image_url.split("?", 1)[0].split("#", 1)[0])
        if not filename:
            filename = f"image_{len(global_state.images) + 1}.png"

        name, extension = os.path.splitext(filename)
        extension = extension or ".png"
        candidate = os.path.join(IMG_DIR, f"{name}{extension}")
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(IMG_DIR, f"{name}_{counter}{extension}")
            counter += 1
        return candidate


def main() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
