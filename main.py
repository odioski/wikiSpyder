
import asyncio
import csv
import html
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Event, RLock
from typing import Callable

import requests
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStyle,
)

from app_state import (
    APP_DISPLAY_NAME,
    IMG_DIR,
    TALLY_FILE,
    USER_AGENT,
    global_state,
    normalize_subject_url,
)
from image_probe import ImageProbe
from image_viewer import launch_image_viewer
from newwindow import Ui_Dialog
from scraping import deep_probe_links, scrape_wikipedia_references
from worker import OperationWorker


class MainWindow(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._stop_requested = False
        self._stop_event = Event()
        self._state_lock = RLock()
        self._operation_active = False
        self._kill_event: asyncio.Event | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._worker: OperationWorker | None = None
        self._download_output: list[str] = []
        self._progress_value = 0
        self._progress_direction = 1
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(18)
        self._progress_timer.timeout.connect(self._animate_progress_bar)
        self._network_executor = ThreadPoolExecutor(max_workers=12)
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
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.ui.label_3.setText(APP_DISPLAY_NAME)

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
        self.refresh_button.setToolTip("Reload wikiSpyder from the current codebase.")
        self.refresh_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
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
        self.ui.pushButton_2.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        )
        self.ui.pushButton_3.setGeometry(680, 440, 150, 61)
        self.ui.pushButton_3.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )

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
        self.refresh_button.clicked.connect(self.refresh_codebase)
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

    def _start_worker(
        self,
        operation: Callable[[], tuple[str | None, str | None, bool]],
        status: str,
    ) -> None:
        if self._operation_active:
            return

        self._stop_requested = False
        self._stop_event.clear()
        self._set_operation_active(True)
        self.ui.label_5.setText(status)

        worker = OperationWorker(operation, self)
        self._worker = worker
        worker.links_changed.connect(self.ui.label_4.setText)
        worker.tally_changed.connect(self.ui.label_5.setText)
        worker.output_changed.connect(self.ui.label_5.setText)
        worker.failed.connect(self._worker_failed)
        worker.operation_finished.connect(self._worker_finished)
        worker.operation_finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.start()

    def _worker_failed(self, message: str) -> None:
        self.ui.label_5.setText(f"An error occurred: {message}")
        self._worker = None
        self._set_operation_active(False)

    def _worker_finished(self, stopped: bool, show_viewer: bool) -> None:
        self._worker = None
        self._set_operation_active(False)
        if show_viewer and not stopped:
            launch_image_viewer(self, global_state.images)

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
        with self._state_lock:
            global_state.tally_events.append(event)
            self._save_tally_file()

    def _save_tally_file(self) -> None:
        with self._state_lock:
            events = list(global_state.tally_events)
            link_term_counts = {
                url: dict(counts)
                for url, counts in global_state.link_term_counts.items()
            }

        try:
            with open(TALLY_FILE, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["kind", "url", "term", "count"])
                for event in events:
                    writer.writerow(["event", "", event, ""])
                for url, counts in link_term_counts.items():
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
        with self._state_lock:
            global_state.term_totals.clear()
            for counts in global_state.link_term_counts.values():
                for term, count in counts.items():
                    global_state.term_totals[term] = (
                        global_state.term_totals.get(term, 0) + count
                    )

    def refresh_codebase(self) -> None:
        if self._operation_active:
            return

        self.cleanup_images()
        self.ui.label_5.setText("Reloading wikiSpyder from the current codebase...")
        QApplication.processEvents()
        os.execv(sys.executable, [sys.executable, *sys.argv])

    def stop_current_operation(self) -> None:
        self.kill_current_operation()

    def kill_current_operation(self, record_event: bool = True) -> None:
        self._stop_requested = True
        self._stop_event.set()
        if self._kill_event is not None:
            if self._async_loop is not None:
                self._async_loop.call_soon_threadsafe(self._kill_event.set)
            else:
                self._kill_event.set()
        self.stop_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        if record_event:
            self._record_tally_event("Stop")
        self.ui.label_5.setText("Killing current operation...")
        QApplication.processEvents()

    def _set_stop_requested(self, requested: bool) -> None:
        self._stop_requested = requested

    def _set_kill_event(self, kill_event: asyncio.Event | None) -> None:
        self._kill_event = kill_event

    def _get_with_responsive_stop(
        self, url: str, timeout: int | tuple[int, int]
    ) -> requests.Response | None:
        future = self._network_executor.submit(
            requests.get,
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        while True:
            try:
                return future.result(timeout=0.05)
            except FutureTimeoutError:
                if self._stop_requested or self._stop_event.is_set():
                    future.cancel()
                    return None

    def _run_async_with_responsive_stop(self, coro) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._async_loop = loop
        task = loop.create_task(coro)
        try:
            while not task.done():
                loop.run_until_complete(asyncio.sleep(0.05))
                if (
                    (self._stop_requested or self._stop_event.is_set())
                    and self._kill_event is not None
                ):
                    self._kill_event.set()
            loop.run_until_complete(task)
        finally:
            pending = [
                pending_task
                for pending_task in asyncio.all_tasks(loop)
                if not pending_task.done()
            ]
            for pending_task in pending:
                pending_task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.run_until_complete(loop.shutdown_asyncgens())
            if self._async_loop is loop:
                self._async_loop = None
            asyncio.set_event_loop(None)
            loop.close()

    def disco_subject(self, text: str) -> None:
        global_state.wikipedia_url = normalize_subject_url(text)
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

    def spyder_1st_run(self) -> None:
        if self._operation_active:
            return

        self._clear_runtime_state(reset_tally=True)
        self._set_tally_query(
            global_state.wikipedia_url,
            global_state.search_terms,
        )
        self._record_tally_event("Launch")

        if not global_state.wikipedia_url:
            self.ui.label_4.setText("No subject URL found...")
            return

        self.ui.label_4.setText("Launching spider...")
        self._start_worker(
            lambda: self._run_reference_and_image_operation(
                global_state.wikipedia_url,
                global_state.search_terms,
                cancelled_links_text="Spider stopped by user.",
            ),
            "Finding images...",
        )

    def _run_reference_and_image_operation(
        self,
        subject_url: str,
        search_terms: list[str],
        cancelled_links_text: str,
    ) -> tuple[str | None, str | None, bool]:
        result = scrape_wikipedia_references(
            subject_url,
            search_terms,
            self._get_with_responsive_stop,
        )
        if self._stop_requested or self._stop_event.is_set():
            return (
                cancelled_links_text,
                self._format_download_output() + "Operation cancelled.",
                False,
            )

        probe_links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        if probe_links:
            self._find_images_core(probe_links)

        if self._stop_requested or self._stop_event.is_set():
            return (
                self.format_links(result),
                self._format_download_output() + "Operation cancelled.",
                False,
            )

        return self.format_links(result), self._format_download_output() + self.tally_links(), False

    def update_tally_view(self) -> None:
        self.ui.label_5.setText(self.tally_links())

    def _find_images_core(self, urls: list[str]) -> list[tuple[str, str]]:
        self._kill_event = None
        global_state.messages.clear()
        global_state.image_urls.clear()
        with self._state_lock:
            self._download_output.clear()

        if not urls:
            return []

        probe = ImageProbe(
            self._state_lock,
            self._stop_event,
            lambda: self._stop_requested,
            self._set_stop_requested,
            self._set_kill_event,
            self._record_link_term_counts,
            self._append_download_output,
        )
        self._run_async_with_responsive_stop(probe.find_images_async(urls))
        return global_state.images

    def find_images(self, urls: list[str]) -> list[tuple[str, str]]:
        if self._operation_active:
            return []

        self.cleanup_images()
        if not urls:
            self.ui.label_5.setText("No links available for image probing.")
            return []

        self._start_worker(
            lambda: self._run_image_operation(urls, show_viewer=False),
            "Finding images...",
        )
        return []

    def _run_image_operation(
        self, urls: list[str], show_viewer: bool
    ) -> tuple[str | None, str | None, bool]:
        self._find_images_core(urls)
        if self._stop_requested or self._stop_event.is_set():
            return (
                None,
                self._format_download_output() + "Image search stopped by user.",
                False,
            )
        return None, self._format_download_output() + self.tally_links(), show_viewer

    def _append_download_output(self, message: str) -> None:
        with self._state_lock:
            self._download_output.append(message)
            self._download_output = self._download_output[-24:]
            output_html = self._format_download_output_locked()

        worker = self._worker
        if worker is not None:
            worker.output_changed.emit(output_html)

    def _format_download_output(self) -> str:
        with self._state_lock:
            return self._format_download_output_locked()

    def _format_download_output_locked(self) -> str:
        if not self._download_output:
            return ""

        rows = "".join(
            f"<li>{html.escape(message)}</li>"
            for message in self._download_output
        )
        return "<h2>Image Download Output</h2><ul>" + rows + "</ul>"

    def view_images(self) -> None:
        if self._operation_active:
            return

        self._record_tally_event("View Images")
        links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.cleanup_images()
        if not links:
            self.ui.label_5.setText("No links available for image probing.")
            return

        self._start_worker(
            lambda: self._run_image_operation(links, show_viewer=True),
            "Finding images in matched links...",
        )

    def deep_probe_view(self) -> None:
        if self._operation_active:
            return

        self._record_tally_event("Deep Probe")
        base_links = (
            global_state.matched_links
            if global_state.matched_links
            else global_state.fixed_links
        )
        self.cleanup_images()
        self._start_worker(
            lambda: self._run_deep_probe_operation(base_links),
            "Deep probing reference pages...",
        )

    def _run_deep_probe_operation(
        self, base_links: list[str]
    ) -> tuple[str | None, str | None, bool]:
        deep_links = deep_probe_links(
            base_links,
            self._get_with_responsive_stop,
            lambda: self._stop_requested or self._stop_event.is_set(),
            max_depth=2,
        )
        if self._stop_requested or self._stop_event.is_set():
            return None, self._format_download_output() + "Operation cancelled.", False

        global_state.fixed_links = deep_links
        if deep_links:
            self._find_images_core(deep_links)
        if self._stop_requested or self._stop_event.is_set():
            return (
                self.format_links(deep_links),
                self._format_download_output() + "Operation cancelled.",
                False,
            )
        return self.format_links(deep_links), self._format_download_output() + self.tally_links(), True

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

        with self._state_lock:
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
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(1500)
        self._network_executor.shutdown(wait=False, cancel_futures=True)
        self.cleanup_images()
        event.accept()

def main() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
