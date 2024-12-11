import re
import os
import shutil
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
global img_dir
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
        self.matched_links = []


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
        layout.addWidget(QLabel("wikiSpyder 0.2.1", alignment=Qt.AlignmentFlag.AlignCenter))
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
        search_term_label = QLabel("Search Terms")
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
        # self.deep_probe_button.clicked.connect(self.spyder_infinite)

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

    def create_control_panel(self, launch_button, deep_probe_button, view_images_button):
        control_panel = QHBoxLayout()
        control_panel.addSpacing(20)
        control_panel.addWidget(launch_button)
        control_panel.addWidget(deep_probe_button)
        control_panel.addWidget(view_images_button)
        return control_panel

    def disco_subject(self, text):
        if text:
            global_state.wikipedia_url = f'https://en.wikipedia.org/wiki/{text}'
        else:
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
            result = self.scrape_wikipedia_references(global_state.wikipedia_url, global_state.search_terms)
            # global_state.found_links = result.split("\n") if result else []
            output.setText(self.format_links(result))
            tally_output.setText(self.tally_links(global_state.matched_links))    
        else:
            output.setText("No subject URL found...")

    # def spyder_infinite(self):
    #     self.is_deep_probing = not self.is_deep_probing
    #     if self.is_deep_probing:
    #         output.setText("Deep probe launched")
    #         self.deep_probe_button.setText("Pause Deep Probe")
    #         result = self.deep_scrape_wikipedia(global_state.found_links, global_state.search_terms)
    #         deep_probe_output.setText(self.format_links(result))
    #         time.sleep(2)
    #         deep_probe_output.setText("")
    #     else:
    #         output.setText("Deep probe paused.")
    #         self.deep_probe_button.setText("Resume Deep Probe")
    def scrape_wikipedia_references(self, url, search_terms):
        try:
            response = requests.get(global_state.wikipedia_url)  # Fetch the Wikipedia page
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Print the prettified HTML content
            print(soup.prettify())
            print(global_state.wikipedia_url)


            # Find the references section
            if not references_section:
                references_section = soup.find('div', class_='reflist reflist-columns references-column-width')
            elif not references_section:
                    references_section = soup.find('div', class_='reflist')
            elif not references_section:
                    references_section = soup.find('ol', class_='references')
            else:
                print("No references section found.")
                return ["No references section found."]

            # Print the references section for debugging
            print(references_section.prettify())
            print(len(references_section))

            # Extract all links from the references section
            all_links = [link['href'] for link in references_section.find_all('a', href=True)]
            fixed_links = [link if link.startswith("http") else f"https://en.wikipedia.org{link}" for link in all_links]

            # Print the extracted links for debugging
            print("Extracted links:", fixed_links)

            if not search_terms:
                return fixed_links

            # Filter links based on search terms
            matched_links = [link for link in fixed_links if any(term in link for term in search_terms)]
            global_state.matched_links = matched_links
            return matched_links if matched_links else ["No matching links found in references."]
        except requests.RequestException as e:
            return [f"An error occurred with the request: {str(e)}"]
        except Exception as e:
            return [f"An error occurred: {str(e)}"]

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
            for url in urls:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                image_tags = soup.find_all('img', src=True)
                print(f'{image_tags}\n\n')
                for img_tag in image_tags:
                    src = img_tag['src']
                    link = re.search(r'(https?://[^\s]+\.(jpg|jpeg|png|gif))', src)
                    if link is None:
                        global_state.messages.append(f"Skipping non-image link: {src}")
                        print(f"Skipping non-image link: {src} ***********\n\n\n")
                    else:
                        print(f'link = {link.group(1)}')
                        print(f'adding image url to image_urls list: {link.group(1)}')
                        deep_probe_output.setText(f"Probing for images from: {link.group(1)}")
                        global_state.image_urls.append(link.group(1))
                        print("Next..**************\n")

                formatted_image_links = [f'<a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>' for link in global_state.image_urls]
                deep_probe_output.setText(f'<h5>Found {len(global_state.image_urls)} images from:</h5>{url}<br/>{"<br/>".join(formatted_image_links)}<h6>Ready to view...</h6>')
                time.sleep(5)

                if global_state.image_urls:
                    print(f'Found {len(global_state.image_urls)} images\n**************')
                    print(f'{global_state.image_urls}\n\n')
                    for img_url in global_state.image_urls:
                        global_state.messages.append(img_url)
                        img_response = requests.get(img_url)
                        img = Image.open(BytesIO(img_response.content))
                        try:
                            img.verify()
                            image_name = os.path.basename(img_url)
                            output_path = os.path.join(img_dir, image_name)
                            img = Image.open(BytesIO(img_response.content))  # Reopen the image
                            img.save(output_path)
                            global_state.images.append(output_path)
                        except (IOError, SyntaxError) as e:
                            print(f"Skipping invalid image: {img_url} - {e}")
                    output.setText("\n".join(global_state.messages))
                else:
                    deep_probe_output.setText(f'{global_state.messages}\n\n')
                global_state.image_urls.clear()  # Clear image URLs after processing each URL
            return global_state.image_urls
        except Exception as e:
            output.setText(f"An error occurred: {str(e)}")
            print(f"An error occurred: {str(e)}")
        return []
    
    class ImageDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.parent = parent

    def closeEvent(self, event):
        self.parent.cleanup_images(event)
        event.accept()  # Accept the close event to proceed with closing

    def view_images_button(self):
        output.setText("Launching image viewer...")
        self.find_images(global_state.matched_links)

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

        for img_path in global_state.images:
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setFixedSize(200, 200)
            img_label.setStyleSheet("border: 1px solid white;")
            pixmap = QPixmap(img_path)
            img_label.setPixmap(pixmap.scaled(img_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
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

        image_dialog.setFixedWidth(5 * 200 + 40)  # Set width to fit at least 5 labels
        global_state.images.clear()
        global_state.image_urls = []
        image_dialog.exec()


    def closeEvent(self, event):
        # Purge images when the app exits
        self.cleanup_images()
        event.accept()

    def format_links(self, text):
        links = text if isinstance(text, list) else text.split("\n")
        formatted_links = [f'<a href="{link}" style="color: yellow; text-decoration: underline;">{link}</a>' for link in links]
        self.tally_links(global_state.matched_links)
        return f'<h2>LINKS FOUND:</h2><h4>Click to visit or add/remove search terms</h4><br/>{"<br/>".join(formatted_links)}'
    
    def tally_links(self, text):
        formatted_matched_links = [f'<a href="{link}" style="color: pink; text-decoration: underline;">{link}</a>' for link in global_state.matched_links]
        return f'<h2>TALLY: Matched Links = {len(global_state.matched_links)}</h2><br/>{"<br/>".join(formatted_matched_links)}'

if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    app.exec()

    