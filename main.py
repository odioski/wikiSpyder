import re
import os
import time
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageQt
from io import BytesIO
from PIL import ImageQt
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (QApplication, QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QDialog)

basedir = os.path.dirname(__file__)
img_dir = "./saved_images"
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
        self.setWindowTitle("wikiSpyder 0.1.9")

        logo = self.create_logo()
        subject_label, subject_url = self.create_subject_input()
        search_term_label, search_term_inputs = self.create_search_term_input()
        launch_button, deep_probe_button, view_images_button = self.create_control_buttons()
        output_scroll_area, deep_probe_output = self.create_output_areas()
        tally_scroll_area = self.create_tally_area()

        layout = QVBoxLayout()
        layout.addWidget(logo)
        layout.addWidget(subject_label)
        layout.addWidget(subject_url)
        layout.addWidget(search_term_label)
        layout.addWidget(search_term_inputs)
        layout.addSpacing(20)
        layout.addWidget(QLabel("wikiSpyder 0.1.9", alignment=Qt.AlignmentFlag.AlignCenter))
        layout.addSpacing(20)
        layout.addLayout(self.create_output_layout(output_scroll_area, deep_probe_output))
        layout.addSpacing(20)
        layout.addLayout(self.create_control_panel(launch_button, deep_probe_button, view_images_button))
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
        search_term_label = QLabel("Search terms")
        search_term_inputs = QLineEdit()
        search_term_inputs.setPlaceholderText("TYPE or DROP your search terms here; use csv or txt file if it's a long list")
        search_term_inputs.textChanged.connect(self.disco_terms)
        return search_term_label, search_term_inputs

    def create_control_buttons(self):
        launch_button = QPushButton("Launch")
        launch_button.setFixedSize(200, 50)
        launch_button.clicked.connect(self.spyder_1st_run)

        self.deep_probe_button = QPushButton("Deep Probe")
        self.deep_probe_button.setFixedSize(200, 50)
        self.deep_probe_button.clicked.connect(self.spyder_infinite)

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
        output.setOpenExternalLinks(True)  # Enable clickable links

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

        # deep_probe_output_scroll_area = QScrollArea()
        # deep_probe_output_scroll_area.setWidget(deep_probe_output)
        # deep_probe_output.setFixedWidth(output.width() // 3)
        # deep_probe_output_scroll_area.setWidgetResizable(True)
        # deep_probe_output_scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)    


        return output_scroll_area, deep_probe_output

    def create_tally_area(self):
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

    def create_control_panel(self, launch_button, deep_probe_button, view_images_button):
        control_panel = QHBoxLayout()
        control_panel.addSpacing(20)
        control_panel.addWidget(launch_button)
        control_panel.addWidget(deep_probe_button)
        control_panel.addWidget(view_images_button)
        return control_panel

    def disco_subject(self, text):
        if text:
            global_state.wikipedia_url = f'https://wikipedia.org/wiki/{text}'
        else:
            output.setText("Please fill in the form...")

    def disco_terms(self, text):
        global_state.search_terms = text.split(" ") if text else []

    def spyder_1st_run(self):
        output.setText("Launching spider...")
        if global_state.wikipedia_url:
            result = self.scrape_wikipedia_references(global_state.wikipedia_url, global_state.search_terms)
            global_state.found_links = result.split("\n") if result else []
            output.setText(self.format_links(result))
        else:
            output.setText("No subject URL found...")

    def spyder_infinite(self):
        self.is_deep_probing = not self.is_deep_probing
        if self.is_deep_probing:
            output.setText("Deep probe launched")
            self.deep_probe_button.setText("Pause Deep Probe")
            result = self.deep_scrape_wikipedia(global_state.found_links, global_state.search_terms)
            deep_probe_output.setText(self.format_links(result))
            time.sleep(2)
            deep_probe_output.setText("")
        else:
            output.setText("Deep probe paused.")
            self.deep_probe_button.setText("Resume Deep Probe")

    def scrape_wikipedia_references(self, url, search_terms):
        try:
            base_url = "https://en.wikipedia.org"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            references_section = soup.find('ol', class_='references')
            if not references_section:
                return "No references section found."

            all_links = references_section.find_all('a', href=True)
            fixed_links = [f"{base_url}{link['href']}" if link['href'].startswith("/") else link['href'] for link in all_links]

            if not search_terms or search_terms == "NIL":
                return "\n".join(fixed_links)

            global_state.matched_links = [link for link in fixed_links if any(term in link for term in search_terms)]
            return "\n".join(global_state.matched_links) if global_state.matched_links else "No matching links found in references."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    # def deep_scrape_wikipedia(self, found_links, search_terms):
    #     try:
    #         base_url = "https://en.wikipedia.org"
    #         matched_links = []
    #         for sub_url in found_links:
    #             if sub_url.startswith("#"):
    #                 continue
    #             if sub_url.startswith("/"):
    #                 sub_url = f"{base_url}{sub_url}"
    #             response = requests.get(sub_url)
    #             sub_soup = BeautifulSoup(response.text, 'html.parser')
    #             sub_links = sub_soup.find_all('a', href=True)
    #             for sub_link in sub_links:
    #                 href = sub_link['href']
    #                 if href.startswith("#"):
    #                     deep_probe_output.setText(f"Skipping internal link: {href}, temp. void.")
    #                     continue
    #                 if href.startswith("/"):
    #                     href = f"{base_url}{href}"
    #                 if any(term in sub_link.get_text() for term in search_terms):
    #                     deep_probe_output.setText(f"Found matching link: {href}")
    #                     matched_links.append(href)
    #         deep_probe_output.setText("\n".join(matched_links) if matched_links else "No matching links found in deep probe.")
    #     except Exception as e:
    #         deep_probe_output.setText(f"An error occurred: {str(e)}")
    #         return f"An error occurred: {str(e)}"


    def find_images(self, urls):
        print(f'{urls}\n\n')
        try:
            #base_url = "https://en.wikipedia.org"
            for url in urls:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                image_tags = soup.find_all('img', src=True) 
                print(f'{image_tags}\n\n')
                for src in image_tags:
                    src = src['src']
                    link = re.search(r'(https?://[^\s]+\.(jpg|jpeg|png|gif))', src)
                    if link == "None" or link is None:
                        global_state.messages.append(f"Skipping non-image link: {src} = {link}")
                        #deep_probe_output.setText(f'Skipping non-image link: {src} = {link}')
                        print(f"Skipping non-image link: {src} = {link} ***********\n\n\n")
                    else:
                        #new_link = (f'{base_url}{new_src}')
                        print(f'link = {link.group(1)}')
                        print(f'adding image url to image_urls list: {link.group(1)}')
                        deep_probe_output.setText(f"Probing for images from: {link.group(1)}") 
                        global_state.image_urls.append(link.group(1))
                        print("Next..**************\n")

                deep_probe_output.setText(f"Found {len(global_state.image_urls)} images from: {url}\n{global_state.image_urls}\nReady to view...")
                time.sleep(5)

                if global_state.image_urls:
                    print(f'{global_state.image_urls}\n\n')
                    for img_url in global_state.image_urls:
                        global_state.messages.append(img_url)
                        img_response = requests.get(img_url)
                        img = Image.open(BytesIO(img_response.content))
                        try:
                            img.verify()
                            global_state.images.append(img)
                            image_name = os.path.basename(img_url)
                            output_path = os.path.join(img_dir, image_name)
                            img.save(output_path)
                        except (IOError, SyntaxError) as e:
                            print(f"Skipping invalid image: {img_url} - {e}")
                    output.setText("\n".join(global_state.messages))
                else:
                    deep_probe_output.setText(f'{global_state.messages}\n\n')
                return global_state.image_urls
        except Exception as e:
            output.setText(f"An error occurred: {str(e)}")
            print(f"An error occurred: {str(e)}")
        return []

    def view_images_button(self):
        output.setText("Launching image viewer...")
        self.find_images(global_state.matched_links)
        image_dialog = QDialog(self)
        image_dialog.setWindowTitle("Image Viewer")

        dialog_layout = QVBoxLayout()

        if global_state.image_urls:
            for img in global_state.images:
                img_label = QLabel()
                qimage = ImageQt.ImageQt(img)
                pixmap = QPixmap.fromImage(qimage)
                img_label.setPixmap(pixmap)
                dialog_layout.addWidget(img_label)
                image_dialog.setLayout(dialog_layout)
                image_dialog.exec()
        else:
            output.setText("No images found...")

    def format_links(self, text):
        links = text.split("\n")
        formatted_links = [f'<a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>' for link in links]
        return f'<h2>LINKS FOUND:</h2><h4>Click to visit or add/remove keywords</h4><br/>{"<br/>".join(formatted_links)}'

if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()

