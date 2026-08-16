
import asyncio
import csv
import html
import os
import re
import shutil
import sys
from collections import deque
from dataclasses import dataclass, field
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QPixmap, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from newwindow import Ui_Dialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "saved_images")
TALLY_FILE = os.path.join(BASE_DIR, "tally.csv")
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
    tally_wikipedia_url: str = ""
    tally_search_terms: list[str] = field(default_factory=list)
    matched_links: list[str] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    fixed_links: list[str] = field(default_factory=list)
    link_term_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    term_totals: dict[str, int] = field(default_factory=dict)
    tally_events: list[str] = field(default_factory=list)


global_state = GlobalState()


class ClickableImageLabel(QLabel):
    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = url


class MainWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._stop_requested = False
        self._operation_active = False
        self._kill_event: asyncio.Event | None = None
        self._progress_value = 0
        self._progress_direction = 1
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(18)
        self._progress_timer.timeout.connect(self._animate_progress_bar)
        self.stop_button = None
        self.progress_bar = None
        self.links_scroll_area = None
        self._results_top = 210
        self._results_height = 211
        self._results_left_margin = 90
        self._results_right_margin = 34
        self._results_gap = 29
        self._links_width_ratio = 421 / (421 + 341)
        self._bottom_button_y = 440
        self._bottom_button_width = 140
        self._bottom_button_height = 61
        self._bottom_button_gap = 30
        self._progress_width = 320
        self._progress_height = 16
        self._progress_y = 520
        self._configure_ui()
        self._connect_signals()

    def _configure_ui(self) -> None:
        self.setWindowTitle("wikiSpyder 0.3.1")

        self.ui.buttonBox.hide()
        self.ui.verticalScrollBar.hide()
        self.ui.verticalScrollBar_3.hide()

        self.links_scroll_area = QScrollArea(self)
        self.links_scroll_area.setObjectName("links_scroll_area")
        self.links_scroll_area.setGeometry(self.ui.label_4.geometry())
        self.links_scroll_area.setWidget(self.ui.label_4)
        self.links_scroll_area.setWidgetResizable(True)
        self.links_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.links_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.links_scroll_area.setStyleSheet(
            "QScrollArea { background-color: #2d2d2d; border: 1px solid #555555; border-radius: 5px; }"
            "QScrollBar:vertical { background-color: #3a3a3a; width: 12px; border-radius: 6px; }"
            "QScrollBar::handle:vertical { background-color: #666666; border-radius: 6px; min-height: 20px; }"
            "QScrollBar::handle:vertical:hover { background-color: #777777; }"
        )

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setGeometry(480, 440, 150, 61)
        self.stop_button.setVisible(True)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(
            "QPushButton { background-color: #0078d4; border: none; border-radius: 8px; color: #ffffff; font-weight: bold; font-size: 14px; padding: 12px 24px; }"
            "QPushButton:hover { background-color: #106ebe; }"
            "QPushButton:pressed { background-color: #005a9e; }"
            "QPushButton:disabled { background-color: #555555; color: #999999; }"
        )

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.setGeometry(0, self._bottom_button_y, 140, 61)
        self.refresh_button.setVisible(True)
        self.refresh_button.setEnabled(True)
        self.refresh_button.setStyleSheet(
            "QPushButton { background-color: #0078d4; border: none; border-radius: 8px; color: #ffffff; font-weight: bold; font-size: 12px; padding: 8px 12px; }"
            "QPushButton:hover { background-color: #106ebe; }"
            "QPushButton:pressed { background-color: #005a9e; }"
            "QPushButton:disabled { background-color: #555555; color: #999999; }"
        )

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self._progress_value)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #1a1a1a; border: 1px solid #555555; border-radius: 5px; }"
            "QProgressBar::chunk { background-color: #0078d4; border-radius: 4px; }"
        )

        self.ui.pushButton.setGeometry(70, 440, 150, 61)
        self.ui.pushButton_2.setGeometry(270, 440, 150, 61)
        self.ui.pushButton_3.setGeometry(680, 440, 150, 61)

        for label in (self.ui.label_4, self.ui.label_5):
            label.setWordWrap(True)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            label.setStyleSheet(
                "background-color: #1a1a1a; border: 1px solid #555555; border-radius: 5px; padding: 8px; color: #ffffff;"
            )

        self.ui.label_4.setText("Search results will appear here.")
        self.ui.label_5.setText("Link tally and image status will appear here.")
        self.setMinimumSize(915, 579)
        self._resize_result_views()
        self._center_bottom_buttons()
        self._center_progress_bar()

    def _connect_signals(self) -> None:
        self.ui.subject_url.textChanged.connect(self.disco_subject)
        self.ui.subject_url.returnPressed.connect(self.spyder_1st_run)
        self.ui.lineEdit_2.textChanged.connect(self.disco_terms)
        self.ui.pushButton.clicked.connect(self.spyder_1st_run)
        self.ui.pushButton_2.clicked.connect(self.deep_probe_view)
        self.ui.pushButton_3.clicked.connect(self.view_images)
        self.refresh_button.clicked.connect(self.refresh_current_view)
        self.stop_button.clicked.connect(self.stop_current_operation)

    def _set_operation_active(self, active: bool) -> None:
        self._operation_active = active
        self.stop_button.setEnabled(active)
        self.refresh_button.setEnabled(not active)
        self.progress_bar.setVisible(active)
        if active:
            self._start_progress_bar()
        else:
            self._stop_progress_bar()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_result_views()
        self._center_bottom_buttons()
        self._center_progress_bar()

    def _resize_result_views(self) -> None:
        if getattr(self, "links_scroll_area", None) is None:
            return

        available_width = (
            self.width()
            - self._results_left_margin
            - self._results_right_margin
            - self._results_gap
        )
        left_width = max(260, int(available_width * self._links_width_ratio))
        right_width = max(240, available_width - left_width)
        if left_width + right_width > available_width:
            overflow = left_width + right_width - available_width
            left_width = max(260, left_width - overflow)

        right_x = self._results_left_margin + left_width + self._results_gap
        self.links_scroll_area.setGeometry(
            self._results_left_margin,
            self._results_top,
            left_width,
            self._results_height,
        )
        self.ui.label_5.setGeometry(
            right_x,
            self._results_top,
            right_width,
            self._results_height,
        )

    def _center_bottom_buttons(self) -> None:
        if getattr(self, "stop_button", None) is None:
            return

        buttons = [
            self.ui.pushButton,
            self.ui.pushButton_2,
            self.stop_button,
            self.refresh_button,
            self.ui.pushButton_3,
        ]
        total_width = (
            len(buttons) * self._bottom_button_width
            + (len(buttons) - 1) * self._bottom_button_gap
        )
        x = max(0, (self.width() - total_width) // 2)
        for button in buttons:
            button.setGeometry(
                x,
                self._bottom_button_y,
                self._bottom_button_width,
                self._bottom_button_height,
            )
            x += self._bottom_button_width + self._bottom_button_gap

    def _center_progress_bar(self) -> None:
        if getattr(self, "progress_bar", None) is None:
            return

        self.progress_bar.setGeometry(
            max(0, (self.width() - self._progress_width) // 2),
            self._progress_y,
            self._progress_width,
            self._progress_height,
        )

    def _start_progress_bar(self) -> None:
        self._progress_value = 8
        self._progress_direction = 1
        self.progress_bar.setValue(self._progress_value)
        if not self._progress_timer.isActive():
            self._progress_timer.start()

    def _stop_progress_bar(self) -> None:
        self._progress_timer.stop()
        self._progress_value = 0
        self._progress_direction = 1
        self.progress_bar.setValue(self._progress_value)

    def _animate_progress_bar(self) -> None:
        self._progress_value += self._progress_direction * 2
        if self._progress_value >= 92:
            self._progress_value = 92
            self._progress_direction = -1
        elif self._progress_value <= 8:
            self._progress_value = 8
            self._progress_direction = 1
        self.progress_bar.setValue(self._progress_value)

    def _clear_runtime_state(self, reset_tally: bool = True) -> None:
        global_state.found_links.clear()
        global_state.fixed_links.clear()
        global_state.matched_links.clear()
        global_state.image_urls.clear()
        global_state.images.clear()
        global_state.messages.clear()
        if reset_tally:
            global_state.link_term_counts.clear()
            global_state.term_totals.clear()
            global_state.tally_events.clear()
            global_state.tally_wikipedia_url = ""
            global_state.tally_search_terms.clear()
            self._save_tally_file()

    def _set_tally_query(self, url: str, search_terms: list[str]) -> None:
        global_state.tally_wikipedia_url = url
        global_state.tally_search_terms = list(search_terms)

    def _record_tally_event(self, event: str) -> None:
        global_state.tally_events.append(event)
        self._save_tally_file()

    def _save_tally_file(self) -> None:
        try:
            with open(TALLY_FILE, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["kind", "url", "term", "count"])
                for event in global_state.tally_events:
                    writer.writerow(["event", "", event, ""])
                for url, counts in global_state.link_term_counts.items():
                    for term, count in counts.items():
                        writer.writerow(["term_count", url, term, count])
        except OSError as exc:
            global_state.messages.append(f"Could not save tally file: {exc}")

    def _load_tally_file(self) -> None:
        if not os.path.isfile(TALLY_FILE):
            return

        link_term_counts: dict[str, dict[str, int]] = {}
        tally_events: list[str] = []
        try:
            with open(TALLY_FILE, "r", encoding="utf-8", newline="") as file:
                for row in csv.DictReader(file):
                    kind = row.get("kind", "")
                    if kind == "event":
                        event = row.get("term", "")
                        if event:
                            tally_events.append(event)
                    elif kind == "term_count":
                        url = row.get("url", "")
                        term = row.get("term", "")
                        if not url or not term:
                            continue
                        try:
                            count = int(row.get("count", "0") or 0)
                        except ValueError:
                            count = 0
                        link_term_counts.setdefault(url, {})[term] = count
        except OSError as exc:
            global_state.messages.append(f"Could not load tally file: {exc}")
            return

        global_state.link_term_counts = link_term_counts
        global_state.tally_events = tally_events
        self._rebuild_term_totals()

    def _rebuild_term_totals(self) -> None:
        global_state.term_totals.clear()
        for counts in global_state.link_term_counts.values():
            for term, count in counts.items():
                global_state.term_totals[term] = (
                    global_state.term_totals.get(term, 0) + count
                )

    def refresh_current_view(self) -> None:
        if self._operation_active:
            return

        subject_url = self._normalize_subject_url(self.ui.subject_url.text())
        search_terms = [
            term
            for term in re.split(r"[\s,]+", self.ui.lineEdit_2.text().strip())
            if term
        ]

        if not subject_url:
            self.ui.label_4.setText("Please fill in the form...")
            return

        same_query = (
            global_state.tally_wikipedia_url == subject_url
            and global_state.tally_search_terms == search_terms
        )
        global_state.wikipedia_url = subject_url
        global_state.search_terms = search_terms

        self._stop_requested = False
        self._clear_runtime_state(reset_tally=not same_query)
        self._set_tally_query(subject_url, search_terms)
        if same_query:
            self._load_tally_file()
        self._record_tally_event("Refresh")
        self.cleanup_images()
        self._set_operation_active(True)

        result = self.scrape_wikipedia_references(subject_url, search_terms)
        self.ui.label_4.setText(self.format_links(result))
        QApplication.processEvents()

        probe_links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.ui.label_5.setText("Refreshing images...")
        QApplication.processEvents()

        self.find_images(probe_links)

        if self._stop_requested:
            self.ui.label_5.setText("Operation cancelled.")
            self._set_operation_active(False)
            return

        self.ui.label_5.setText(self.tally_links())
        self._set_operation_active(False)

    def stop_current_operation(self) -> None:
        self.kill_current_operation()

    def kill_current_operation(self, record_event: bool = True) -> None:
        self._stop_requested = True
        if self._kill_event is not None:
            self._kill_event.set()
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        if record_event:
            self._record_tally_event("Stop")
        self.ui.label_5.setText("Killing current operation...")
        QApplication.processEvents()

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
        if self._operation_active:
            return

        self._stop_requested = False
        self._set_operation_active(True)
        self._clear_runtime_state(reset_tally=True)
        self._set_tally_query(
            global_state.wikipedia_url,
            global_state.search_terms,
        )
        self._record_tally_event("Launch")

        if not global_state.wikipedia_url:
            self.ui.label_4.setText("No subject URL found...")
            self._set_operation_active(False)
            return

        self.ui.label_4.setText("Launching spider...")
        QApplication.processEvents()

        result = self.scrape_wikipedia_references(
            global_state.wikipedia_url,
            global_state.search_terms,
        )
        if self._stop_requested:
            self.ui.label_4.setText("Spider stopped by user.")
            self.ui.label_5.setText("Operation cancelled.")
            self._set_operation_active(False)
            return

        self.ui.label_4.setText(self.format_links(result))
        QApplication.processEvents()

        probe_links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        if not probe_links:
            self.ui.label_5.setText(self.tally_links())
            self._set_operation_active(False)
            return

        self.ui.label_5.setText("Finding images...")
        QApplication.processEvents()
        self.find_images(probe_links)

        if self._stop_requested:
            self.ui.label_5.setText("Operation cancelled.")
            self._set_operation_active(False)
            return

        self.ui.label_5.setText(self.tally_links())
        self._set_operation_active(False)

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
        session: requests.Session,
        url: str,
        semaphore: asyncio.Semaphore,
        kill_event: asyncio.Event,
    ) -> None:
        async with semaphore:
            if kill_event.is_set() or self._stop_requested:
                return

            try:
                response = await asyncio.to_thread(
                    session.get,
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=60,
                )
                response.raise_for_status()
                page_html = response.text
            except requests.RequestException as exc:
                global_state.messages.append(f"Skipping {url}: {exc}")
                return

            if kill_event.is_set() or self._stop_requested:
                return

            soup = BeautifulSoup(page_html, "html.parser")
            self._record_link_term_counts(url, soup.get_text(" "))
            self.update_tally_view()
            QApplication.processEvents()

            discovered_urls: list[str] = []
            for tag in soup.find_all("img", src=True):
                if kill_event.is_set() or self._stop_requested:
                    return
                src = str(tag.get("src", "")).strip()
                image_url = self._normalize_image_url(src, url)
                if not image_url or image_url in global_state.image_urls:
                    continue
                global_state.image_urls.append(image_url)
                discovered_urls.append(image_url)

            for image_url in discovered_urls:
                if kill_event.is_set() or self._stop_requested:
                    return
                try:
                    img_response = await asyncio.to_thread(
                        session.get,
                        image_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=60,
                    )
                    img_response.raise_for_status()
                    img_data = img_response.content
                except requests.RequestException:
                    continue

                if kill_event.is_set() or self._stop_requested:
                    return

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

        semaphore = asyncio.Semaphore(10)
        urls = list(dict.fromkeys(urls))
        kill_event = asyncio.Event()
        self._kill_event = kill_event
        try:
            with requests.Session() as session:
                tasks = [
                    asyncio.create_task(
                        self.download_image(session, url, semaphore, kill_event)
                    )
                    for url in urls
                ]
                probe_task = asyncio.ensure_future(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
                kill_task = asyncio.create_task(kill_event.wait())
                done, _ = await asyncio.wait(
                    [probe_task, kill_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if kill_task in done:
                    self._stop_requested = True
                    for task in tasks:
                        task.cancel()
                    probe_task.cancel()
                    await asyncio.gather(probe_task, return_exceptions=True)
                    return

                kill_task.cancel()
                await asyncio.gather(kill_task, return_exceptions=True)
        finally:
            if self._kill_event is kill_event:
                self._kill_event = None

    def update_tally_view(self) -> None:
        self.ui.label_5.setText(self.tally_links())

    def find_images(self, urls: list[str]) -> list[tuple[str, str]]:
        self._stop_requested = False
        self._kill_event = None
        self._set_operation_active(True)
        self.cleanup_images()
        global_state.messages.clear()
        global_state.image_urls.clear()

        if not urls:
            self.ui.label_5.setText("No links available for image probing.")
            self._set_operation_active(False)
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
            self._set_operation_active(False)
            return []

        if self._stop_requested:
            self.ui.label_5.setText("Image search stopped by user.")
            self._set_operation_active(False)
            return []

        self.update_tally_view()
        self._set_operation_active(False)
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
        if self._operation_active:
            return

        self._record_tally_event("View Images")
        links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.ui.label_5.setText("Finding images in matched links...")
        QApplication.processEvents()
        self.find_images(links)
        self.update_tally_view()
        self.launch_image_viewer()

    def _deep_probe_links(self, start_urls: list[str], max_depth: int = 2) -> list[str]:
        if not start_urls:
            return []

        queue: deque[tuple[str, int]] = deque((url, 0) for url in start_urls if url)
        visited: set[str] = set()
        discovered: list[str] = []

        while queue:
            if self._stop_requested:
                break

            current_url, depth = queue.popleft()
            normalized = current_url.split("#", 1)[0].strip()
            if not normalized or normalized in visited or depth > max_depth:
                continue

            visited.add(normalized)
            discovered.append(normalized)

            try:
                response = requests.get(
                    normalized,
                    headers={"User-Agent": USER_AGENT},
                    timeout=20,
                )
                response.raise_for_status()
            except requests.RequestException:
                continue

            try:
                soup = BeautifulSoup(response.content, "html.parser")
            except Exception:
                continue

            for tag in soup.find_all("a", href=True):
                href = str(tag.get("href", "")).strip()
                if not href or href.startswith("#"):
                    continue
                candidate = href
                if candidate.startswith("//"):
                    candidate = f"https:{candidate}"
                elif not candidate.startswith(("http://", "https://")):
                    candidate = urljoin(normalized, candidate)

                if not candidate.startswith(("http://", "https://")):
                    continue
                next_url = candidate.split("#", 1)[0].strip()
                if next_url not in visited:
                    queue.append((next_url, depth + 1))

        return discovered

    def deep_probe_view(self) -> None:
        if self._operation_active:
            return

        self._set_operation_active(True)
        self._record_tally_event("Deep Probe")
        base_links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.ui.label_5.setText("Deep probing reference pages...")
        QApplication.processEvents()

        deep_links = self._deep_probe_links(base_links, max_depth=2)
        if self._stop_requested:
            self.ui.label_5.setText("Operation cancelled.")
            self._set_operation_active(False)
            return

        global_state.fixed_links = deep_links
        self.ui.label_4.setText(self.format_links(deep_links))
        self.find_images(deep_links)
        self.update_tally_view()
        self._set_operation_active(False)
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
        matched_by_content = [
            link
            for link, counts in global_state.link_term_counts.items()
            if sum(counts.values())
        ]
        matched_count = (
            len(matched_by_content)
            if global_state.search_terms
            else len(global_state.matched_links)
        )
        total_term_hits = sum(global_state.term_totals.values())

        return (
            "<h2>Links Found Tally</h2>"
            f"<p>Found Links = {len(global_state.fixed_links)}</p>"
            f"<p>Matched Links = {matched_count}</p>"
            f"<p>Search Term Hits = {total_term_hits}</p>"
            f"<p>Tally File = {html.escape(os.path.basename(TALLY_FILE))}</p>"
            f"{self._format_tally_events()}"
            f"{self._format_term_totals()}"
            f"{self._format_link_term_counts()}"
            f"<p>Images Found = {len(global_state.image_urls)}</p>"
            f"<p>Images Saved = {len(global_state.images)}</p>"
        )

    def _record_link_term_counts(self, url: str, page_text: str) -> None:
        if not global_state.search_terms:
            return

        counts = self._count_search_terms(page_text, global_state.search_terms)
        global_state.link_term_counts[url] = counts
        self._rebuild_term_totals()
        self._save_tally_file()

        if sum(counts.values()) and url not in global_state.matched_links:
            global_state.matched_links.append(url)

    @staticmethod
    def _count_search_terms(page_text: str, search_terms: list[str]) -> dict[str, int]:
        return {
            term: len(re.findall(re.escape(term), page_text, flags=re.IGNORECASE))
            for term in search_terms
        }

    def _format_term_totals(self) -> str:
        if not global_state.search_terms:
            return "<p>Search terms = none</p>"

        rows = [
            f"<li>{html.escape(term)} = {global_state.term_totals.get(term, 0)}</li>"
            for term in global_state.search_terms
        ]
        return "<h3>Terms</h3><ul>" + "".join(rows) + "</ul>"

    def _format_tally_events(self) -> str:
        if not global_state.tally_events:
            return ""

        recent_events = global_state.tally_events[-5:]
        rows = [f"<li>{html.escape(event)}</li>" for event in recent_events]
        return "<h3>Actions</h3><ul>" + "".join(rows) + "</ul>"

    def _format_link_term_counts(self) -> str:
        if not global_state.search_terms or not global_state.link_term_counts:
            return ""

        rows: list[str] = []
        for url, counts in global_state.link_term_counts.items():
            hit_count = sum(counts.values())
            if not hit_count:
                continue

            term_counts = ", ".join(
                f"{html.escape(term)}: {count}"
                for term, count in counts.items()
                if count
            )
            rows.append(
                '<li><a href="{url}" style="color: yellow; text-decoration: underline;">'
                "{label}</a><br/>{term_counts}</li>".format(
                    url=html.escape(url, quote=True),
                    label=html.escape(url),
                    term_counts=term_counts,
                )
            )

        if not rows:
            return "<h3>Links</h3><p>No search terms found on probed pages.</p>"

        return "<h3>Links</h3><ol>" + "".join(rows) + "</ol>"

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
        self.kill_current_operation(record_event=False)
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
