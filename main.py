import requests
import os
import time
import re
from bs4 import BeautifulSoup
from pathlib import Path
from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (QApplication, QCheckBox, QLabel, QLineEdit,
                             QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QBoxLayout, QWidget, QAbstractSlider, QDialog, QVBoxLayout, QLabel)

global found_links, search_terms, wikipedia_url
search_terms = []
wikipedia_url = ""

basedir = os.path.dirname(__file__)

app = QApplication([])

class MainWindow(QMainWindow):

    def disco_subject(self, text):
        global wikipedia_url
        if text == "":
            output.setText("Please fill in the form...")
        else:
            subject = text
            wikipedia_url = (f'https://wikipedia.org/wiki/{subject}')
        return wikipedia_url

    def disco_terms(self, text):
        global search_terms
        search_terms = text.split(" ") if text else []

    def __init__(self):
        super().__init__()
        self.is_deep_probing = False  # Toggle flag

        logo = QLabel("wikisSpyder 0.1.9")
        logo.setPixmap(QPixmap(os.path.join(basedir, "logo.png")))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
############################# SLOTS ########################################/


        subject_label = QLabel("Subject")
        subject_url = QLineEdit()
        subject_url.setPlaceholderText("wikipedia.org/wiki/YourFavoriteStar")
        subject_url.textChanged.connect(self.disco_subject)

        search_term_label = QLabel("Search terms")
        search_term_inputs = QLineEdit()
        search_term_inputs.setAcceptDrops(True)
        search_term_inputs.dragEnterEvent = self.dragEnterEvent
        search_term_inputs.dropEvent = self.dropEvent
        search_term_inputs.setPlaceholderText("TYPE or DROP your search terms here; use csv or txt file if it's a long list")
        search_term_inputs.textChanged.connect(self.disco_terms)

        launchButton = QPushButton("Launch")
        launchButton.setFixedWidth(200)
        launchButton.setFixedHeight(50)
        launchButton.clicked.connect(self.spyder_1st_run)

        self.deep_probe_button = QPushButton("Deep Probe")
        self.deep_probe_button.setFixedWidth(200)
        self.deep_probe_button.setFixedHeight(50)
        self.deep_probe_button.clicked.connect(self.spyder_infinite)
                
        view_images_button = QPushButton("View Images")
        view_images_button.setFixedWidth(200)
        view_images_button.setFixedHeight(50)
        view_images_button.clicked.connect(self.cycle_module_button)

############################# OUTPUT PANELS ################################/


        # self.flash_stacked_widget = QStackedWidget()
        # self.flash_stacked_widget.setBackgroundRole(QPixmap(os.path.join(basedir, "flash.jpg")))
        # self.flash_stacked_widget.setCurrentIndex(1)

        wiki_spyder = QLabel("wikiSpyder 0.1.9")
        wiki_spyder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        global output        
        output = QLabel("output will be displayed here...")
        output.setObjectName("nfo")
        output.setFixedWidth(1000)
        output.setWordWrap(True)                
        output.setOpenExternalLinks(True)  # Enable clickable links

        output_scroll_area = QScrollArea()
        output_scroll_area.setWidget(output)
        output_scroll_area.setWidgetResizable(True)
        output_scroll_area.setMinimumHeight(300)
        output_scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create deep_probe_output and nest it inside output
        global deep_probe_output
        deep_probe_output = QLabel()
        deep_probe_output.setObjectName("deep_probe_output")
        deep_probe_output.setFixedWidth(output.width() // 3)
        deep_probe_output.setStyleSheet("border: 1px solid white;")
        deep_probe_output.setWordWrap(True)
        deep_probe_output.setOpenExternalLinks(True)

        deep_probe_output_scroll_area = QScrollArea()
        deep_probe_output_scroll_area.setWidget(deep_probe_output)
        deep_probe_output_scroll_area.setWidgetResizable(True)
        deep_probe_output_scroll_area.setMinimumHeight(output_scroll_area.height())
        deep_probe_output_scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_panel = QVBoxLayout()
        title_panel.addWidget(logo)

        input_panel = QVBoxLayout()
        input_panel.addWidget(subject_label)
        input_panel.addWidget(subject_url)
        input_panel.addWidget(search_term_label)
        input_panel.addWidget(search_term_inputs)

        control_panel = QHBoxLayout()
        control_panel.addSpacing(20)
        control_panel.addWidget(launchButton)
        control_panel.addWidget(self.deep_probe_button)
        control_panel.addWidget(view_images_button)

        output_banner_left = QLabel("LINKS FOUND:")
        output_banner_right = QLabel("MISC. OUTPUT:")
        #how to get these centered above their respective outputs?

        output_banner = QHBoxLayout()
        output_banner.addWidget(output_banner_left)
        output_banner.addStretch()
        output_banner.addWidget(output_banner_right)

        output_layout = QHBoxLayout()
        output_layout.addWidget(output_scroll_area)
        output_layout.addWidget(deep_probe_output)

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

        tally_layout = QVBoxLayout()
        tally_layout.addWidget(tally_scroll_area)
        

        layout_z_0 = QVBoxLayout()
        layout_z_0.addLayout(title_panel)
        layout_z_0.addLayout(input_panel)
        layout_z_0.addSpacing(20)
        layout_z_0.addWidget(wiki_spyder)
        layout_z_0.addSpacing(20)
        #layout_z_0.addLayout(output_banner)
        layout_z_0.addLayout(output_layout)
        layout_z_0.addSpacing(20)
        layout_z_0.addLayout(control_panel)
        layout_z_0.addSpacing(20)
        layout_z_0.addLayout(tally_layout)

        app_container = QWidget()
        app_container.setLayout(layout_z_0)
        self.setCentralWidget(app_container)
        self.setFixedSize(1200, 700)

############################# METHODS ########################################/

    def spyder_1st_run(self):
        if wikipedia_url:
            output.setText("Launching spider...")
            result = self.scrape_wikipedia_references(wikipedia_url, search_terms)
            global found_links
            found_links = result.split("\n") if result else []
            output.setText(self.format_links(result))  # Format links for display
        else:
            output.setText("No subject URL found...")

    def spyder_infinite(self):
        self.is_deep_probing = not self.is_deep_probing
        if self.is_deep_probing:
            output.setText("Deep probe launched")
            self.deep_probe_button.setText("Pause Deep Probe")
            result = self.deep_scrape_wikipedia(found_links, search_terms)
            deep_probe_output.setText(self.format_links(result))  # Format links for display
            time.sleep(2)  # Pause for 5 seconds
            deep_probe_output.setText("")  # Clear previous output
        else:
            output.setText("Deep probe paused.")
            self.deep_probe_button.setText("Resume Deep Probe")

    def cycle_module_button(self):
        output.setText("Launching image viewer...")
        result = self.view_images(wikipedia_url)
        image_dialog = QDialog(self)
        image_dialog.setWindowTitle("Image Viewer")

        dialog_layout = QVBoxLayout()
        for img_url in result:
            img_label = QLabel()
            img_label.setPixmap(QPixmap(img_url))
            dialog_layout.addWidget(img_label)

        image_dialog.setLayout(dialog_layout)
        image_dialog.exec()

    def scrape_wikipedia_references(self, url, search_terms):
        try:
            base_url = "https://en.wikipedia.org"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            references_section = soup.find('ol', class_='references')
            if not references_section:
                return "No references section found."

            all_links = references_section.find_all('a', href=True)
            fixed_links = []
            for link in all_links:
                href = link['href']
                if href.startswith("/"):
                    fixed_links.append(f"{base_url}{href}")
                else:
                    fixed_links.append(href)
            
            if not search_terms or search_terms == "NIL":
                return "\n".join(fixed_links)
            
            matched_links = []
            for link in fixed_links:
                if any(term in link for term in search_terms):
                    matched_links.append(link)
            return "\n".join(matched_links) if matched_links else "No matching links found in references."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def deep_scrape_wikipedia(self, found_links, search_terms):
        try:
            base_url = "https://en.wikipedia.org"
            matched_links = []
            for sub_url in found_links:
                if sub_url.startswith("#"):
                    # Skip internal page references
                    continue
                if sub_url.startswith("/"):
                    sub_url = f"{base_url}{sub_url}"
                response = requests.get(sub_url)
                sub_soup = BeautifulSoup(response.text, 'html.parser')
                sub_links = sub_soup.find_all('a', href=True)
                for sub_link in sub_links:
                    href = sub_link['href']
                    if href.startswith("#"):
                        deep_probe_output.setText(f"Skipping internal link: {href}, temp. void.")
                        # Skip internal page references
                        continue
                    if href.startswith("/"):
                        href = f"{base_url}{href}"
                    if any(term in sub_link.get_text() for term in search_terms):
                        deep_probe_output.setText(f"Found matching link: {href}")
                        matched_links.append(href)
            deep_probe_output.setText("\n".join(matched_links) if matched_links else "No matching links found in deep probe.")
        except Exception as e:
            deep_probe_output.setText(f"An error occurred: {str(e)}")
            return f"An error occurred: {str(e)}"

    def view_images(self, url):
        try:
            base_url = "https://en.wikipedia.org"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            image_tags = soup.find_all('img')
            image_urls = []
            for img in image_tags:
                src = img['src']
                if src.startswith("/"):
                    image_urls.append(f"{base_url}{src}")
                else:
                    image_urls.append(src)
            return image_urls
        except Exception as e:
            output.setText(f"An error occurred: {str(e)}")
            return []

    def format_links(self, text):
        links = text.split("\n")
        formatted_links = []
        for link in links:
            formatted_links.append(f'<a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>')
        return f'<h2>LINKS FOUND:</h2><h4>Click to visit or add/remove keywords</h4><br/>{"<br/>".join(formatted_links)}'

if __name__ == "__main__":
    window = MainWindow()
    window.show()
    app.exec()
