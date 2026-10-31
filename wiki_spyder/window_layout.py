# Codename: Michelle
"""Main-window construction and responsive layout."""

import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QMessageBox, QStyle

from .app_state import APP_DISPLAY_NAME, APP_VERSION_LABEL, ICON_FILE, QSS_FILE
from .image_viewer import ImageGallery

class MainWindowLayoutMixin:

    def _initialize_layout_state(self) -> None:
        self.stop_button = None
        self.progress_bar = None
        self.links_scroll_area = None
        self.tally_scroll_area = None
        self.image_gallery = None
        self.image_gallery_host = None
        self._results_top = 290
        self._results_height = 300
        self._results_left_margin = 32
        self._results_right_margin = 32
        self._results_gap = 20
        self._links_width_ratio = 421 / (421 + 341)
        self._bottom_button_y = 625
        self._bottom_button_width = 150
        self._bottom_button_height = 52
        self._progress_width = 320
        self._progress_height = 16

    def _configure_ui(self) -> None:
        self.resize(1080, 760)
        self.setMinimumSize(860, 640)
        self.setWindowTitle(APP_DISPLAY_NAME)
        if os.path.isfile(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))
        try:
            with open(QSS_FILE, encoding="utf-8") as stylesheet:
                self.setStyleSheet(stylesheet.read())
        except OSError:
            pass

        self.ui.label_3.setText(APP_VERSION_LABEL)
        self.ui.label_3.setObjectName("build_label")
        self._title_label = self.ui.appTitle
        self._subtitle_label = self.ui.appSubtitle
        self._subject_heading = self.ui.label
        self._terms_heading = self.ui.label_2
        self._links_heading = self.ui.linksHeading
        self._tally_heading = self.ui.tallyHeading

        self.links_scroll_area = self.ui.linksScrollArea
        self.links_scroll_area.setObjectName("links_scroll_area")
        self.links_scroll_area.setWidget(self.ui.label_4)
        self.links_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.links_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.tally_scroll_area = self.ui.tallyScrollArea
        self.tally_scroll_area.setObjectName("tally_scroll_area")
        self.tally_scroll_area.setWidget(self.ui.label_5)
        self.tally_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tally_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.stop_button = self.ui.stopButton
        self.stop_button.setObjectName("stop_button")

        self.refresh_button = self.ui.refreshButton
        self.refresh_button.setToolTip("Reload wikiSpyder from the current codebase.")
        self.refresh_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.refresh_button.setObjectName("refresh_button")

        self.progress_bar = self.ui.progressBar
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(self._progress_value)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        self.ui.pushButton.setObjectName("launch_button")
        self.ui.pushButton_2.setObjectName("deep_probe_button")
        self.ui.pushButton_3.setObjectName("view_images_button")
        self.ui.pushButton_2.setToolTip(
            "Follow same-site links from the currently selected reference links. "
            "Each host is limited to 100 pages with at least 1 second between "
            "requests. robots.txt rules are followed. Change the limits in "
            "Options > Deep Probe Settings."
        )
        self.ui.pushButton_2.setToolTipDuration(10000)
        self.ui.pushButton_2.setIcon(self._information_icon())
        self.ui.pushButton_2.setIconSize(QSize(18, 18))
        self.ui.pushButton_3.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )

        for label in (self.ui.label_4, self.ui.label_5):
            label.setWordWrap(True)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.ui.label_4.setObjectName("links_output")
        self.ui.label_5.setObjectName("tally_output")
        self.image_gallery_host = self.ui.imageGalleryHost
        self.image_gallery = ImageGallery(self.image_gallery_host)
        self.image_gallery.setGeometry(self.image_gallery_host.rect())
        self.image_gallery.backRequested.connect(self.show_results)
        self.image_gallery_host.hide()

        self._title_label.setObjectName("app_title")
        self._subtitle_label.setObjectName("app_subtitle")
        for heading in (
            self._subject_heading,
            self._terms_heading,
            self._links_heading,
            self._tally_heading,
        ):
            heading.setObjectName("section_label")
        self._resize_result_views()
        self._center_bottom_buttons()
        self._center_progress_bar()
        self._layout_surface()

    def _information_icon(self) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#0078d4"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 20, 20)

        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "i")
        painter.end()

        return QIcon(pixmap)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if not hasattr(self, "_title_label"):
            return
        self._resize_result_views()
        self._center_bottom_buttons()
        self._center_progress_bar()
        self._layout_surface()

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
        self._results_top = 320
        self._results_height = max(150, self.height() - 494)
        self.links_scroll_area.setGeometry(
            self._results_left_margin,
            self._results_top,
            left_width,
            self._results_height,
        )
        self.tally_scroll_area.setGeometry(
            right_x,
            self._results_top,
            right_width,
            self._results_height,
        )
        if self.image_gallery_host is not None:
            self.image_gallery_host.setGeometry(
                self._results_left_margin,
                292,
                self.width() - self._results_left_margin - self._results_right_margin,
                max(190, self.height() - 442),
            )
            self.image_gallery.setGeometry(self.image_gallery_host.rect())

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
        spacing = 16
        button_width = min(
            self._bottom_button_width,
            (self.width() - 64 - spacing * (len(buttons) - 1)) // len(buttons),
        )
        total_width = len(buttons) * button_width + (len(buttons) - 1) * spacing
        x = max(0, (self.width() - total_width) // 2)
        for button in buttons:
            button.setGeometry(
                x,
                self.height() - 112,
                button_width,
                self._bottom_button_height,
            )
            x += button_width + spacing

    def _center_progress_bar(self) -> None:
        if getattr(self, "progress_bar", None) is None:
            return

        self.progress_bar.setGeometry(
            max(0, (self.width() - self._progress_width) // 2),
            self.height() - 36,
            self._progress_width,
            self._progress_height,
        )

    def _layout_surface(self) -> None:
        margin = 32
        content_width = self.width() - margin * 2
        menu_bar = getattr(self, "menu_bar", None)
        if menu_bar is not None:
            menu_bar.setGeometry(0, 0, self.width(), 28)
        self._title_label.setGeometry(margin, 42, content_width - 250, 40)
        self._subtitle_label.setGeometry(margin + 2, 84, content_width - 4, 24)
        self.ui.label_3.setGeometry(self.width() - 260, 57, 228, 24)
        self._subject_heading.setGeometry(margin + 2, 128, content_width - 4, 20)
        self.ui.subject_url.setGeometry(margin, 150, content_width, 44)
        self._terms_heading.setGeometry(margin + 2, 203, content_width - 4, 20)
        self.ui.lineEdit_2.setGeometry(margin, 225, content_width, 44)
        left_heading_width = max(240, int(content_width * self._links_width_ratio))
        self._links_heading.setGeometry(margin + 2, 293, left_heading_width, 20)
        self._tally_heading.setGeometry(
            margin + left_heading_width + self._results_gap,
            293,
            max(220, content_width - left_heading_width - self._results_gap),
            20,
        )

    def show_image_gallery(self, images: list[tuple[str, str]]) -> None:
        if not images:
            self.show_results()
            QMessageBox.information(self, "Images", "No images found to display.")
            return
        self.image_gallery.set_images(images)
        self.links_scroll_area.hide()
        self.tally_scroll_area.hide()
        self._links_heading.hide()
        self._tally_heading.hide()
        self.image_gallery_host.show()
        self.image_gallery_host.raise_()
        self.image_gallery.show()

    def show_results(self) -> None:
        self.image_gallery.hide()
        self.image_gallery_host.hide()
        self.links_scroll_area.show()
        self.tally_scroll_area.show()
        self._links_heading.show()
        self._tally_heading.show()

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
