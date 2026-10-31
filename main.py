# Codename: Michelle
import asyncio
import csv
import html
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from threading import Event, RLock
from typing import Any, Callable
from uuid import uuid4

import requests
from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QMenu,
    QSpinBox,
    QDoubleSpinBox,
)

from wiki_spyder.app_state import (
    APP_DISPLAY_NAME,
    IMG_DIR,
    ICON_FILE,
    TALLY_FILE,
    USER_AGENT,
    global_state,
    normalize_subject_url,
)
from wiki_spyder.image_probe import ImageProbe
from wiki_spyder.newwindow import Ui_Dialog
from wiki_spyder.scraping import deep_probe_links, scrape_wikipedia_references
from wiki_spyder.results_view import (
    count_search_terms,
    format_download_output,
    format_link_term_counts,
    format_links,
    format_tally,
    format_tally_events,
    format_term_totals,
    matched_links_count,
    search_term_hits_count,
)
from wiki_spyder.session_store import TallyStore
from wiki_spyder.window_layout import MainWindowLayoutMixin
from wiki_spyder.worker import OperationWorker


class MainWindow(MainWindowLayoutMixin, QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._initialize_layout_state()
        self._stop_requested = False
        self._stop_event = Event()
        self._state_lock = RLock()
        self._operation_active = False
        self._kill_event: asyncio.Event | None = None
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._worker: OperationWorker | None = None
        self._download_output: list[str] = []
        self._links_output = ""
        self._tally_output = ""
        self._progress_value = 0
        self._progress_direction = 1
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(18)
        self._progress_timer.timeout.connect(self._animate_progress_bar)
        self._network_executor = ThreadPoolExecutor(max_workers=12)
        self._session_store = TallyStore(TALLY_FILE)
        self._settings = QSettings("Omar Daniels", "wikiSpyder")
        self._restore_latest_on_start = self._settings.value(
            "restore_latest_session", True, type=bool
        )
        self._deep_probe_page_limit = self._settings.value(
            "deep_probe_page_limit", 100, type=int
        )
        self._deep_probe_request_delay = self._settings.value(
            "deep_probe_request_delay", 1.0, type=float
        )
        self._session_id = uuid4().hex
        self._session_started_at = datetime.now(timezone.utc).isoformat(
            timespec="microseconds"
        )
        self._configure_ui()
        self._build_menu_bar()
        self._load_tally_file()
        self._connect_signals()

    def _build_menu_bar(self) -> None:
        self.menu_bar = self.ui.menuBar
        self.menu_bar.setNativeMenuBar(False)
        self.file_menu = self.menu_bar.addMenu("&File")
        self._add_menu_action(
            self.file_menu, "New Session", self.start_new_session, "Ctrl+N"
        )
        self._add_menu_action(
            self.file_menu, "Save Session Now", self.save_session_now, "Ctrl+S"
        )
        self._add_menu_action(
            self.file_menu, "Export Current Session…", self.export_current_session
        )
        self.file_menu.addSeparator()
        self._add_menu_action(self.file_menu, "Exit", self.close, "Ctrl+Q")

        self.sessions_menu = self.menu_bar.addMenu("&Sessions")
        self._add_menu_action(
            self.sessions_menu, "Open Latest Session", self.open_latest_session
        )
        self.open_session_menu = self.sessions_menu.addMenu("Open Saved Session")
        self.open_session_menu.aboutToShow.connect(self._populate_saved_sessions_menu)

        self.options_menu = self.menu_bar.addMenu("&Options")
        self._add_menu_action(
            self.options_menu,
            "Deep Probe Settings…",
            self._show_deep_probe_settings,
        )
        self.options_menu.addSeparator()
        self.restore_session_action = QAction(
            "Restore Latest Session on Startup", self
        )
        self.restore_session_action.setCheckable(True)
        self.restore_session_action.setChecked(self._restore_latest_on_start)
        self.restore_session_action.toggled.connect(self._set_restore_latest_on_start)
        self.options_menu.addAction(self.restore_session_action)

        help_menu = self.menu_bar.addMenu("&Help")
        self._add_menu_action(help_menu, "About wikiSpyder", self.show_about)
        self.menu_bar.setGeometry(0, 0, self.width(), 28)

    def _add_menu_action(
        self,
        menu: QMenu,
        text: str,
        callback: Callable[..., Any],
        shortcut: str | None = None,
    ) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _connect_signals(self) -> None:
        self.ui.subject_url.textChanged.connect(self.disco_subject)
        self.ui.subject_url.returnPressed.connect(self.spyder_1st_run)
        self.ui.lineEdit_2.textChanged.connect(self.disco_terms)
        self.ui.lineEdit_2.returnPressed.connect(self.spyder_1st_run)
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
        self._set_tally_output(html.escape(status))

        worker = OperationWorker(operation, self)
        self._worker = worker
        worker.links_changed.connect(self._set_links_output)
        worker.tally_changed.connect(self._set_tally_output)
        worker.output_changed.connect(self._set_tally_output)
        worker.failed.connect(self._worker_failed)
        worker.operation_finished.connect(self._worker_finished)
        worker.operation_finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.start()

    def _worker_failed(self, message: str) -> None:
        self._set_tally_output(f"An error occurred: {html.escape(message)}")
        self._worker = None
        self._set_operation_active(False)
        self._save_tally_file()

    def _worker_finished(self, stopped: bool, show_viewer: bool) -> None:
        self._worker = None
        self._set_operation_active(False)
        self._save_tally_file()
        if show_viewer and not stopped:
            self.show_image_gallery(global_state.images)

    def _set_links_output(self, content: str) -> None:
        self._links_output = content
        self.ui.label_4.setText(content)
        self._save_tally_file()

    def _set_tally_output(self, content: str) -> None:
        self._tally_output = content
        self.ui.label_5.setText(content)
        self._save_tally_file()

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
        self._save_tally_file()

    def _record_tally_event(self, event: str) -> None:
        with self._state_lock:
            global_state.tally_events.append(event)
            self._save_tally_file()

    def _save_tally_file(self) -> bool:
        with self._state_lock:
            snapshot = {
                "started_at": self._session_started_at,
                "subject": global_state.tally_wikipedia_url,
                "search_terms": list(global_state.tally_search_terms),
                "found_links": list(global_state.found_links),
                "fixed_links": list(global_state.fixed_links),
                "matched_links": list(global_state.matched_links),
                "image_urls": list(global_state.image_urls),
                "link_term_counts": {
                    url: dict(counts)
                    for url, counts in global_state.link_term_counts.items()
                },
                "events": list(global_state.tally_events),
                "links_output": self._links_output,
                "tally_output": self._tally_output,
            }

            try:
                self._session_store.save(self._session_id, snapshot)
            except (OSError, csv.Error) as exc:
                global_state.messages.append(f"Could not save tally file: {exc}")
                return False
        return True

    def _load_tally_file(self) -> None:
        if not self._restore_latest_on_start:
            return
        latest = self._session_store.latest()
        if latest is None:
            return

        session_id, _session = latest
        self.open_saved_session(session_id, warn_if_busy=False)

    def _restore_saved_session(self, session_id: str) -> None:
        session = self._session_store.sessions.get(session_id)
        if session is None:
            return
        self._session_id = session_id
        self.show_results()
        self._session_started_at = session.get("started_at") or self._session_started_at
        global_state.tally_wikipedia_url = session.get("subject", "")
        global_state.wikipedia_url = global_state.tally_wikipedia_url
        global_state.tally_search_terms = list(session.get("search_terms", []))
        global_state.search_terms = list(global_state.tally_search_terms)
        global_state.found_links = list(session.get("found_links", []))
        global_state.fixed_links = list(session.get("fixed_links", []))
        global_state.matched_links = list(session.get("matched_links", []))
        global_state.image_urls = list(session.get("image_urls", []))
        global_state.images.clear()
        global_state.messages.clear()
        self._download_output.clear()
        global_state.link_term_counts = {
            url: dict(counts)
            for url, counts in session.get("link_term_counts", {}).items()
        }
        global_state.tally_events = list(session.get("events", []))
        self._rebuild_term_totals()
        self.ui.subject_url.setText(global_state.wikipedia_url)
        self.ui.lineEdit_2.setText(", ".join(global_state.search_terms))
        self._links_output = session.get("links_output", "") or self.format_links(
            global_state.fixed_links or global_state.found_links
        )
        self._tally_output = session.get("tally_output", "") or self.tally_links()
        self.ui.label_4.setText(self._links_output)
        self.ui.label_5.setText(self._tally_output)

    def _populate_saved_sessions_menu(self) -> None:
        self.open_session_menu.clear()
        sessions = sorted(
            self._session_store.sessions.items(),
            key=lambda item: item[1].get("started_at", ""),
            reverse=True,
        )
        for session_id, session in sessions:
            timestamp = session.get("started_at", "")
            timestamp_label = timestamp.replace("T", " ")[:19] or "Unknown date"
            subject = session.get("subject") or "Untitled session"
            if len(subject) > 48:
                subject = subject[:45] + "…"
            label = f"{timestamp_label} · {subject} · {session_id[:8]}"
            self._add_menu_action(
                self.open_session_menu,
                label,
                lambda checked=False, saved_id=session_id: self.open_saved_session(
                    saved_id
                ),
            )
        if not sessions:
            action = QAction("No saved sessions", self)
            action.setEnabled(False)
            self.open_session_menu.addAction(action)

    def open_latest_session(self) -> None:
        latest = self._session_store.latest()
        if latest is None:
            QMessageBox.information(self, "Saved Sessions", "No saved sessions yet.")
            return
        self.open_saved_session(latest[0])

    def open_saved_session(
        self, session_id: str, warn_if_busy: bool = True
    ) -> None:
        if self._operation_active:
            if warn_if_busy:
                QMessageBox.information(
                    self,
                    "Operation in Progress",
                    "Stop the current operation before opening another session.",
                )
            return
        if session_id not in self._session_store.sessions:
            return
        if self._session_id in self._session_store.sessions:
            global_state.tally_wikipedia_url = global_state.wikipedia_url
            global_state.tally_search_terms = list(global_state.search_terms)
            self._save_tally_file()
        if session_id != self._session_id:
            self.cleanup_images()
        self._restore_saved_session(session_id)

    def start_new_session(self) -> None:
        if self._operation_active:
            return
        self.show_results()
        self._clear_download_output()
        self.cleanup_images()
        self._begin_new_session("New Session")

    def _begin_new_session(self, event: str) -> None:
        self._session_id = uuid4().hex
        self._session_started_at = datetime.now(timezone.utc).isoformat(
            timespec="microseconds"
        )
        self._links_output = ""
        self._tally_output = ""
        self._download_output.clear()
        self._clear_runtime_state(reset_tally=True)
        self._set_tally_query(global_state.wikipedia_url, global_state.search_terms)
        self._links_output = "Search results will appear here."
        self._tally_output = "Session ready. Choose Launch to find references."
        self.ui.label_4.setText(self._links_output)
        self.ui.label_5.setText(self._tally_output)
        self._record_tally_event(event)

    def save_session_now(self) -> None:
        global_state.tally_wikipedia_url = global_state.wikipedia_url
        global_state.tally_search_terms = list(global_state.search_terms)
        if self._save_tally_file():
            QMessageBox.information(self, "Session Saved", "Saved to tally.csv.")
        else:
            QMessageBox.warning(self, "Save Failed", "The session could not be saved.")

    def export_current_session(self) -> None:
        global_state.tally_wikipedia_url = global_state.wikipedia_url
        global_state.tally_search_terms = list(global_state.search_terms)
        if not self._save_tally_file():
            QMessageBox.warning(self, "Save Failed", "The session could not be saved.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Current Session",
            "wikiSpyder-session.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return
        if os.path.abspath(file_path) == os.path.abspath(TALLY_FILE):
            QMessageBox.warning(
                self,
                "Choose Another File",
                "Choose a separate file so the full session archive is preserved.",
            )
            return
        try:
            self._session_store.export_session(self._session_id, file_path)
        except (OSError, KeyError, csv.Error) as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return
        QMessageBox.information(self, "Session Exported", f"Saved to {file_path}")

    def _set_restore_latest_on_start(self, enabled: bool) -> None:
        self._restore_latest_on_start = enabled
        self._settings.setValue("restore_latest_session", enabled)
        if enabled:
            self.open_latest_session()

    def _show_deep_probe_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Deep Probe Settings")
        form = QFormLayout(dialog)

        page_limit = QSpinBox(dialog)
        page_limit.setRange(1, 1000)
        page_limit.setSuffix(" pages per website")
        page_limit.setValue(self._deep_probe_page_limit)
        page_limit.setToolTip(
            "Maximum number of same-site pages Deep Probe will request from each host."
        )

        request_delay = QDoubleSpinBox(dialog)
        request_delay.setRange(0.5, 30.0)
        request_delay.setSingleStep(0.5)
        request_delay.setDecimals(1)
        request_delay.setSuffix(" seconds between requests")
        request_delay.setValue(self._deep_probe_request_delay)
        request_delay.setToolTip(
            "Minimum time between requests to the same website, including robots.txt."
        )

        form.addRow("Page limit", page_limit)
        form.addRow("Request spacing", request_delay)
        scope_note = QLabel(
            "Crawls same-site links from the currently selected reference links. "
            "Pages disallowed by that host’s robots.txt are skipped.",
            dialog,
        )
        scope_note.setWordWrap(True)
        form.addRow("Scope", scope_note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._deep_probe_page_limit = page_limit.value()
        self._deep_probe_request_delay = request_delay.value()
        self._settings.setValue("deep_probe_page_limit", self._deep_probe_page_limit)
        self._settings.setValue(
            "deep_probe_request_delay", self._deep_probe_request_delay
        )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About wikiSpyder",
            f"<h3>{html.escape(APP_DISPLAY_NAME)}</h3>"
            "Research Wikipedia references, search linked pages, and discover images.",
        )

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
        self._set_tally_output("Reloading wikiSpyder from the current codebase...")
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
        self._set_tally_output("Killing current operation...")
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
            self._set_links_output("Please fill in the form...")

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

    def spyder_1st_run(self) -> None:
        if self._operation_active:
            return

        self._begin_new_session("Launch")

        if not global_state.wikipedia_url:
            self._set_links_output("No subject URL found...")
            return

        self._set_links_output("Launching spider...")
        self._start_worker(
            lambda: self._run_reference_operation(
                global_state.wikipedia_url,
                global_state.search_terms,
                cancelled_links_text="Spider stopped by user.",
            ),
            "Finding reference links...",
        )

    def _run_reference_operation(
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
                "Operation cancelled.",
                False,
            )

        return self.format_links(result), self.tally_links(), False

    def update_tally_view(self) -> None:
        self._set_tally_output(self.tally_links())

    def _find_images_core(self, urls: list[str]) -> list[tuple[str, str]]:
        self._kill_event = None
        global_state.messages.clear()
        global_state.image_urls.clear()

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

        self.show_results()
        self._clear_download_output()
        self.cleanup_images()
        if not urls:
            self._set_tally_output("No links available for image probing.")
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
        return format_download_output(self._download_output)

    def view_images(self) -> None:
        if self._operation_active:
            return

        self.show_results()
        self._record_tally_event("View Images")
        self._clear_download_output()
        links = self._focused_probe_links()
        self.cleanup_images()
        if not links:
            self._set_tally_output("No links available for image probing.")
            return

        self._start_worker(
            lambda: self._run_image_operation(links, show_viewer=True),
            "Finding images in selected links...",
        )

    def deep_probe_view(self) -> None:
        if self._operation_active:
            return

        self._record_tally_event("Deep Probe")
        self._clear_download_output()
        base_links = self._focused_probe_links()
        self.cleanup_images()
        self._start_worker(
            lambda: self._run_deep_probe_operation(base_links),
            "Deep probing selected links...",
        )

    @staticmethod
    def _focused_probe_links() -> list[str]:
        if global_state.matched_links:
            return list(global_state.matched_links)
        return list(global_state.found_links or global_state.fixed_links)

    def _clear_download_output(self) -> None:
        with self._state_lock:
            self._download_output.clear()

    def _run_deep_probe_operation(
        self, base_links: list[str]
    ) -> tuple[str | None, str | None, bool]:
        deep_links = deep_probe_links(
            base_links,
            self._get_with_responsive_stop,
            lambda: self._stop_requested or self._stop_event.is_set(),
            progress_callback=self._append_download_output,
            max_pages_per_site=self._deep_probe_page_limit,
            request_delay=self._deep_probe_request_delay,
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
        return format_links(links)

    def tally_links(self) -> str:
        return format_tally(
            session_id=self._session_id,
            saved_session_count=len(self._session_store.sessions),
            found_link_count=len(global_state.fixed_links),
            matched_count=matched_links_count(
                global_state.link_term_counts, global_state.matched_links
            ),
            search_term_hits=search_term_hits_count(global_state.term_totals),
            tally_filename=os.path.basename(TALLY_FILE),
            tally_events=format_tally_events(global_state.tally_events),
            term_totals=format_term_totals(
                global_state.search_terms, global_state.term_totals
            ),
            link_term_counts=format_link_term_counts(
                global_state.search_terms, global_state.link_term_counts
            ),
            image_url_count=len(global_state.image_urls),
            saved_image_count=len(global_state.images),
        )

    def _record_link_term_counts(self, url: str, page_text: str) -> None:
        if not global_state.search_terms:
            return

        with self._state_lock:
            counts = count_search_terms(page_text, global_state.search_terms)
            global_state.link_term_counts[url] = counts
            self._rebuild_term_totals()
            self._save_tally_file()

            if sum(counts.values()) and url not in global_state.matched_links:
                global_state.matched_links.append(url)


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
        global_state.tally_wikipedia_url = global_state.wikipedia_url
        global_state.tally_search_terms = list(global_state.search_terms)
        has_session_data = (
            self._session_id in self._session_store.sessions
            or bool(global_state.wikipedia_url)
            or bool(global_state.tally_events)
        )
        if has_session_data:
            self._save_tally_file()
        self._network_executor.shutdown(wait=False, cancel_futures=True)
        self.cleanup_images()
        event.accept()

def main() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    if os.path.isfile(ICON_FILE):
        app.setWindowIcon(QIcon(ICON_FILE))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
