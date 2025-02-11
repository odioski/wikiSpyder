import re
import os
import shutil
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageQt
from io import BytesIO
from PIL import ImageQt
from PyQt6.QtCore import Qt, QMetaObject, QUrl, QThreadPool, QRunnable, pyqtSlot,  Q_ARG
from PyQt6.QtGui import QPixmap, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QDialog,
)
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

basedir = os.path.dirname(__file__)
img_dir = "saved_images"
os.makedirs(img_dir, exist_ok=True)


class GlobalState:
    def __init__(self):
        self.found_links = []
        self.search_terms = []
        self.wikipedia_url = ""
        self.matched_links = []
        self.images = []
        self.image_urls = []
        self.messages = []


global_state = GlobalState()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_deep_probing = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("wikiSpyder 0.2.1")

        logo = self.create_logo()
        subject_label, subject_url = self.create_subject_input()
        search_term_label, search_term_inputs = self.create_search_term_input()
        launch_button, deep_probe_button, view_images_button = (
            self.create_control_buttons()
        )
        output_scroll_area, deep_probe_output = self.create_output_areas()
        tally_scroll_area = self.create_tally_area()

        layout = QVBoxLayout()
        layout.addWidget(logo)
        layout.addWidget(subject_label)
        layout.addWidget(subject_url)
        layout.addWidget(search_term_label)
        layout.addWidget(search_term_inputs)
        layout.addSpacing(20)
        layout.addWidget(
            QLabel("wikiSpyder 0.2.1", alignment=Qt.AlignmentFlag.AlignCenter)
        )
        layout.addSpacing(20)
        layout.addLayout(
            self.create_output_layout(output_scroll_area, deep_probe_output)
        )
        layout.addSpacing(20)
        layout.addLayout(
            self.create_control_panel(
                launch_button, deep_probe_button, view_images_button
            )
        )
        layout.addSpacing(20)
        layout.addWidget(tally_scroll_area)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setFixedSize(1200, 600)

    def create_logo(self):
        logo = QLabel()
        logo.setPixmap(QPixmap(os.path.join(basedir, "logo.png")))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return logo

    def create_subject_input(self):
        subject_label = QLabel("Subject")
        subject_url = QLineEdit()
        subject_url.setPlaceholderText("wikipedia.org/wiki/YourFavoriteStar")
        subject_url.textChanged.connect(self.disco_subject)
        return subject_label, subject_url

    def create_search_term_input(self):
        search_term_label = QLabel("Search Terms")
        search_term_inputs = QLineEdit()
        search_term_inputs.setPlaceholderText(
            "TYPE or DROP your search terms here; use csv or txt file if it's a long list"
        )
        search_term_inputs.textChanged.connect(self.disco_terms)
        return search_term_label, search_term_inputs

    def create_control_buttons(self):
        launch_button = QPushButton("Launch")
        launch_button.setFixedSize(200, 50)
        launch_button.clicked.connect(self.spyder_1st_run)

        self.deep_probe_button = QPushButton("Deep Probe")
        self.deep_probe_button.setFixedSize(200, 50)

        view_images_button = QPushButton("View Images")
        view_images_button.setFixedSize(200, 50)
        view_images_button.clicked.connect(self.view_images_button)

        return launch_button, self.deep_probe_button, view_images_button

    def create_output_areas(self):
        global output
        output = QLabel("output will be displayed here...")
        output.setObjectName("nfo")
        output.setFixedWidth(1200)
        output.setWordWrap(True)
        output.setOpenExternalLinks(True)

        output_scroll_area = QScrollArea()
        output_scroll_area.setWidget(output)
        output_scroll_area.setWidgetResizable(True)
        output_scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        global deep_probe_output
        deep_probe_output = QLabel()
        deep_probe_output.setObjectName("deep_probe_output")
        deep_probe_output.setFixedWidth(output.width() // 3)
        deep_probe_output.setStyleSheet("border: 1px solid white;")
        deep_probe_output.setWordWrap(True)
        deep_probe_output.setOpenExternalLinks(True)

        return output_scroll_area, deep_probe_output

    def create_tally_area(self):
        global tally_output
        tally_output = QLabel()
        tally_output.setObjectName("tally_output")
        tally_output.setFixedWidth(1000)
        tally_output.setWordWrap(True)
        tally_output.setOpenExternalLinks(True)
        tally_output.setText("TALLY: 0")

        tally_scroll_area = QScrollArea()
        tally_scroll_area.setWidget(tally_output)
        tally_scroll_area.setWidgetResizable(True)
        tally_scroll_area.setMinimumHeight(50)
        tally_scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return tally_scroll_area

    def create_output_layout(self, output_scroll_area, deep_probe_output):
        output_layout = QHBoxLayout()
        output_layout.addWidget(output_scroll_area)
        output_layout.addWidget(deep_probe_output)
        return output_layout

    def create_control_panel(
        self, launch_button, deep_probe_button, view_images_button
    ):
        control_panel = QHBoxLayout()
        control_panel.addSpacing(20)
        control_panel.addWidget(launch_button)
        control_panel.addWidget(deep_probe_button)
        control_panel.addWidget(view_images_button)
        return control_panel

    def disco_subject(self, text):
        global_state.wikipedia_url = (
            f"https://en.wikipedia.org/wiki/{text}" if text else ""
        )
        if not text:
            output.setText("Please fill in the form...")

    def disco_terms(self, text):
        global_state.search_terms = text.split(" ") if text else []

    def cleanup_images(self):
        try:
            shutil.rmtree(img_dir)
        except Exception as e:
            print(f"Error removing image {img_dir}: {e}")
        global_state.images.clear()

    def spyder_1st_run(self):
        output.setText("Launching spider...")
        if global_state.wikipedia_url:
            global_state.wikipedia_url = global_state.wikipedia_url.replace(" ", "%20")
            result = self.scrape_wikipedia_references(
                global_state.wikipedia_url, global_state.search_terms
            )
            output.setText(self.format_links(result))
            tally_output.setText(self.tally_links(global_state.matched_links))
        else:
            output.setText("No subject URL found...")

    def scrape_wikipedia_references(self, url, search_terms):
        global fixed_links
        try:
            response = requests.get(global_state.wikipedia_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            references_section = soup.find("ol", class_="references") or soup.find(
                "div", class_="reflist reflist-columns references-column-width"
            )
            if not references_section:
                return ["No references section found."]

            all_links = [
                link["href"] for link in references_section.find_all("a", href=True)
            ]
            fixed_links = [
                link if link.startswith("http") else f"https://en.wikipedia.org{link}"
                for link in all_links
            ]

            if not search_terms:
                return fixed_links

            matched_links = [
                link
                for link in fixed_links
                if any(term in link for term in search_terms)
            ]
            global_state.matched_links = matched_links
            return (
                matched_links
                if matched_links
                else ["No matching links found in references."]
            )
        except requests.RequestException as e:
            return [f"An error occurred with the request: {str(e)}"]
        except Exception as e:
            return [f"An error occurred: {str(e)}"]

    async def download_image(self, session, url, semaphore):
        async with semaphore:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    image_tags = soup.find_all("img", src=True)
                    for img_tag in image_tags:
                        src = img_tag["src"]
                        link = re.search(r"(https?://[^\s]+\.(jpg|jpeg|png|gif|webp))", src)
                        if link is None:
                            global_state.messages.append(
                                f"Skipping non-image link: {src}"
                            )
                        else:
                            img_url = link.group(1)
                            if img_url in global_state.image_urls:
                                continue
                            QMetaObject.invokeMethod(
                                deep_probe_output,
                                "setText",
                                Q_ARG(str, f"Probing for images from: {img_url}"),
                            )
                            global_state.image_urls.append(img_url)

                    formatted_image_links = [
                        f'<a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>'
                        for link in global_state.image_urls
                    ]
                    QMetaObject.invokeMethod(
                        deep_probe_output,
                        "setText",
                        Q_ARG(
                            str,
                            f'<h5>Found {len(global_state.image_urls)} images from:</h5>{url}<br/>{"<br/>".join(formatted_image_links)}<h6>Ready to view...</h6>',
                        ),
                    )

                    if global_state.image_urls:
                        for img_url in global_state.image_urls:
                            global_state.messages.append(img_url)
                            async with session.get(img_url) as img_response:
                                img_data = await img_response.read()
                                img = Image.open(BytesIO(img_data))
                                try:
                                    img.verify()
                                    image_name = os.path.basename(img_url)
                                    output_path = os.path.join(img_dir, image_name)
                                    if os.path.exists(output_path):
                                        continue
                                    img = Image.open(BytesIO(img_data))
                                    img.save(output_path)
                                    if (
                                        output_path,
                                        img_url,
                                    ) not in global_state.images:
                                        global_state.images.append(
                                            (output_path, img_url)
                                        )
                                except (IOError, SyntaxError) as e:
                                    print(f"Skipping invalid image: {img_url} - {e}")
                        QMetaObject.invokeMethod(
                            output,
                            "setText",
                            Q_ARG(str, "\n".join(global_state.messages)),
                        )
                    else:
                        QMetaObject.invokeMethod(
                            deep_probe_output,
                            "setText",
                            Q_ARG(str, f"{global_state.messages}\n\n"),
                        )
                    global_state.image_urls.clear()
            except aiohttp.ClientResponseError as e:
                if e.status == 403:
                    QMetaObject.invokeMethod(
                        output,
                        "setText",
                        Q_ARG(str, f"Access denied (403) for URL: {url}"),
                    )
                elif e.status == 443:
                    QMetaObject.invokeMethod(
                        output,
                        "setText",
                        Q_ARG(str, f"Connection refused (443) for URL: {url}"),
                    )
                else:
                    QMetaObject.invokeMethod(
                        output, "setText", Q_ARG(str, f"An error occurred: {str(e)}")
                    )
            except aiohttp.ClientError as e:
                QMetaObject.invokeMethod(
                    output, "setText", Q_ARG(str, f"An error occurred: {str(e)}")
                )

    async def find_images_async(self, urls):
        timeout = ClientTimeout(total=60)
        connector = TCPConnector(limit_per_host=10)
        semaphore = asyncio.Semaphore(10)
        async with ClientSession(timeout=timeout, connector=connector) as session:
            tasks = [self.download_image(session, url, semaphore) for url in urls]
            await asyncio.gather(*tasks)

    def find_images(self, urls):
        print(f"{urls}\n\n")
        try:
            asyncio.run(self.find_images_async(urls))
            return global_state.image_urls
        except Exception as e:
            QMetaObject.invokeMethod(
                output, "setText", Q_ARG(str, f"An error occurred: {str(e)}")
            )
            print(f"An error occurred: {str(e)}")
        return []

    class ImageDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.parent = parent

    def closeEvent(self, event):
        self.parent.cleanup_images(event)
        event.accept()

    def view_images_button(self):
        output.setText("Launching image viewer...")
        self.find_images(global_state.matched_links)

        if not global_state.images:
            output.setText("No images found to display.")
            return

        image_dialog = self.ImageDialog()
        image_dialog.setWindowTitle("Image Viewer")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dialog_widget = QWidget()
        dialog_layout = QHBoxLayout(dialog_widget)
        row_layout = QVBoxLayout()
        row = QHBoxLayout()
        count = 0

        def create_mouse_press_event(url):
            def mouse_press_event(event):
                QDesktopServices.openUrl(QUrl(url))

            return mouse_press_event

        for img_path, img_url in global_state.images:
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setFixedSize(200, 200)
            img_label.setStyleSheet("border: 1px solid white;")
            pixmap = QPixmap(img_path)
            img_label.setPixmap(
                pixmap.scaled(
                    img_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            img_label.mousePressEvent = create_mouse_press_event(img_url)
            row.addWidget(img_label)
            count += 1
            if count % 5 == 0:
                row_layout.addLayout(row)
                row = QHBoxLayout()

        if count % 5 != 0:
            row_layout.addLayout(row)
        dialog_layout.addLayout(row_layout)
        dialog_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll_area.setWidget(dialog_widget)
        image_dialog_layout = QVBoxLayout(image_dialog)
        image_dialog_layout.addWidget(scroll_area)
        image_dialog.setLayout(image_dialog_layout)

        image_dialog.setFixedWidth(5 * 200 + 40)
        image_dialog.exec()

    def closeEvent(self, event):
        self.cleanup_images()
        event.accept()

    def format_links(self, text):
        links = text if isinstance(text, list) else text.split("\n")
        formatted_links = [
            f'{index + 1}. <a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>'
            for index, link in enumerate(links)
        ]
        self.tally_links(global_state.matched_links)
        return f'<h2>LINKS FOUND:</h2><h4>Click to visit or add/remove search terms</h4><br/>{"<br/>".join(formatted_links)}'

    def tally_links(self, text):
        formatted_matched_links = [
            f'<a href="{link}" style="color: pink; text-decoration: underline;">{link}</a>'
            for link in global_state.matched_links
        ]
        return f'<h2>TALLY: Found Links = {len(fixed_links)} Matched Links = {len(global_state.matched_links)}</h2><br/>{"<br/>".join(formatted_matched_links)}'


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
