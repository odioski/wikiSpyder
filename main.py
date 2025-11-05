
# Standard library imports

import os
import sys


import re
import shutil
from io import BytesIO

# Third-party library imports


import requests

from bs4 import BeautifulSoup

from PIL import Image

import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

# PyQt6 imports


from PyQt6.QtCore import Qt, QMetaObject, QUrl, Q_ARG
from PyQt6.QtGui import QPixmap, QDesktopServices, QIcon, QPalette, QColor
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
    QMenuBar,
    QStatusBar,
    QMessageBox,
    QFileDialog,
    QCheckBox,
)


from PyQt6 import uic 

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
        self.fixed_links = []
        self.scrollArea = []
        self.scrollArea_2 = []
        self.tally_scrollArea = []
        self.Ui_Dialog = []
        self.wikiSpyderMethods = []
        self.wikiSpyderTools = []



global_state = GlobalState()



from PyQt6 import QtCore, QtGui, QtWidgets



# UI class for the main dialog window
class Ui_Dialog(object):
    def setupUi(self, Dialog):
        
        # Set up the UI elements for the dialog window.

        Dialog.setObjectName("Dialog")
        Dialog.resize(915, 579)

        self.buttonBox = QtWidgets.QDialogButtonBox(parent=Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(150, 530, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Ok
        )
        self.buttonBox.setObjectName("buttonBox")

        self.pushButton = QtWidgets.QPushButton(parent=Dialog)
        self.pushButton.setGeometry(QtCore.QRect(110, 440, 161, 61))
        self.pushButton.setObjectName("pushButton")

        self.pushButton_2 = QtWidgets.QPushButton(parent=Dialog)
        self.pushButton_2.setGeometry(QtCore.QRect(380, 440, 161, 61))
        self.pushButton_2.setObjectName("pushButton_2")

        self.pushButton_3 = QtWidgets.QPushButton(parent=Dialog)
        self.pushButton_3.setGeometry(QtCore.QRect(660, 440, 161, 61))
        self.pushButton_3.setObjectName("pushButton_3")

        self.subject_url = QtWidgets.QLineEdit(parent=Dialog)
        self.subject_url.setGeometry(QtCore.QRect(30, 40, 271, 31))
        self.subject_url.setObjectName("subject_url")

        self.lineEdit_2 = QtWidgets.QLineEdit(parent=Dialog)
        self.lineEdit_2.setGeometry(QtCore.QRect(30, 130, 641, 31))
        self.lineEdit_2.setObjectName("lineEdit_2")

        self.label = QtWidgets.QLabel(parent=Dialog)
        self.label.setGeometry(QtCore.QRect(40, 10, 161, 18))
        self.label.setObjectName("label")

        self.label_2 = QtWidgets.QLabel(parent=Dialog)
        self.label_2.setGeometry(QtCore.QRect(40, 80, 201, 31))
        self.label_2.setObjectName("label_2")

        self.label_3 = QtWidgets.QLabel(parent=Dialog)
        self.label_3.setGeometry(QtCore.QRect(390, 170, 201, 31))
        self.label_3.setObjectName("label_3")

        self.label_4 = QtWidgets.QLabel(parent=Dialog)
        self.label_4.setGeometry(QtCore.QRect(90, 210, 421, 211))
        self.label_4.setObjectName("label_4")

        self.label_5 = QtWidgets.QLabel(parent=Dialog)
        self.label_5.setGeometry(QtCore.QRect(540, 210, 341, 211))
        self.label_5.setObjectName("label_5")

        self.verticalScrollBar_3 = QtWidgets.QScrollBar(parent=Dialog)
        self.verticalScrollBar_3.setGeometry(QtCore.QRect(470, 230, 16, 160))
        self.verticalScrollBar_3.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.verticalScrollBar_3.setObjectName("verticalScrollBar_3")

        self.verticalScrollBar = QtWidgets.QScrollBar(parent=Dialog)
        self.verticalScrollBar.setGeometry(QtCore.QRect(840, 230, 16, 160))
        self.verticalScrollBar.setOrientation(QtCore.Qt.Orientation.Vertical)
        self.verticalScrollBar.setObjectName("verticalScrollBar")

        # self.retranslateUi(Dialog)
        # self.buttonBox.accepted.connect(Dialog.accept)  # type: ignore
        # self.buttonBox.rejected.connect(Dialog.reject)  # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        
        # Set text and placeholders for widgets.
       
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.pushButton.setText(_translate("Dialog", "Launch"))
        self.pushButton_2.setText(_translate("Dialog", "Deep Probe"))
        self.pushButton_3.setText(_translate("Dialog", "View Images"))
        self.subject_url.setPlaceholderText(
            _translate("Dialog", "wikipedia.org/wiki/YourFavoriteStar")
        )
        self.lineEdit_2.setPlaceholderText(
            _translate(
                "Dialog",
                "TYPE or DROP your search terms here; use csv or txt file if it's a long list."
            )
        )
        self.label.setText(_translate("Dialog", "Subject"))
        self.label_2.setText(_translate("Dialog", "Search Terms"))
        self.label_3.setText(_translate("Dialog", "wikiSpyder 0.3.1"))
        self.label_4.setText(_translate("Dialog", "TextLabel"))
        self.label_5.setText(_translate("Dialog", "TextLabel"))


class wikiSpyderMethods(object):


    def disco_terms(self, text):
            
        global_state.search_terms = text.split(" ") if text else []
        

    # File management and app handlers


    def new_file(self):
            
            # Implement new file functionality

            print("New file created")


    def open_file(self):

        # Implement open file functionality

        print("File opened")


    def save_found_links(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Found Links", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w') as file:
                file.write("Found Links:\n")
                for link in file:
                    file.write(f"{link}\n")
                print(f"Found links saved to {file_path}")


    def save_matched_links(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Matched Links", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w') as file:
                file.write("Matched Links:\n")
                for link in global_state.matched_links:
                    file.write(f"{link}\n")
                print(f"Matched links saved to {file_path}")


    def save_images(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Save Images")
        if folder_path:
                try:
                    for filename in os.listdir(img_dir):
                        full_file_name = os.path.join(img_dir, filename)
                        if os.path.isfile(full_file_name):
                            shutil.copy(full_file_name, folder_path)
                            if not os.path.isfile(os.path.join(folder_path, filename)):
                                raise Exception(f"Failed to copy {filename}")
                    QMessageBox.information(self, "Success", f"Images saved to {folder_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save images: {str(e)}")


    def save_selected_images(self, selected_images):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Save Images")
        if folder_path:
                try:
                    for img_path in selected_images:
                        if os.path.isfile(img_path):
                            filename, _ = QFileDialog.getSaveFileName(self, "Save Image As", os.path.join(folder_path, os.path.basename(img_path)), "Images (*.png *.xpm *.jpg)")
                            if filename:
                                shutil.copy(img_path, filename)
                                if not os.path.isfile(filename):
                                    raise Exception(f"Failed to copy {filename}")
                    QMessageBox.information(self, "Success", f"Selected images saved to {folder_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save images: {str(e)}")


    def exit_app(self):

        # Implement exit application functionality

        self.close()


# Main application execution


    def spyder_1st_run(self):
        # scrollArea.setText("Launching spider...")
        if global_state.wikipedia_url:
            global_state.wikipedia_url = global_state.wikipedia_url.replace(" ", "%20")
            result = self.scrape_wikipedia_references(
                global_state.wikipedia_url, global_state.search_terms
            )
            global_state.scrollArea.setText(self.format_links(result))
            global_state.tally_scrollArea.setText(self.tally_links(global_state.matched_links))
        else:
            global_state.scrollArea.setText("No subject URL found...")


    # Application methods.


    def scrape_wikipedia_references(self, url, search_terms):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0"
                }
                response = requests.get(global_state.wikipedia_url, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                references_section = soup.find("ol", class_="references") or soup.find(
                    "div", class_="reflist reflist-columns references-column-width"
                )
                if not references_section:
                    return ["No references section found."]
                all_links = [link["href"] for link in references_section.find_all("a", href=True)]
                fixed_links = [
                    link if link.startswith("http") else f"https://en.wikipedia.org{link}"
                    for link in all_links
                ]
                global_state.fixed_links = fixed_links
                if not search_terms:
                    return fixed_links
                matched_links = [
                    link for link in fixed_links if any(term in link for term in search_terms)
                ]
                global_state.matched_links = matched_links
                return matched_links if matched_links else ["No matching links found in references."]
            except Exception as e:
                return [f"Error: {str(e)}"]

            async def download_image(self, session, url, semaphore):
                async with semaphore:
                    try:
                        headers = {"User-Agent": "Mozilla/5.0"}
                        async with session.get(url, headers=headers) as response:
                            response.raise_for_status()
                            soup = BeautifulSoup(await response.text(), "html.parser")
                            image_tags = soup.find_all("img", src=True)
                        for img_tag in image_tags:
                            src = img_tag["src"]
                            match = re.search(r"(https?://[^\s]+\.(jpg|jpeg|png|gif|webp))", src)
                            if match:
                                img_url = match.group(1)
                                if img_url not in global_state.image_urls:
                                    global_state.image_urls.append(img_url)
                        for img_url in global_state.image_urls:
                            async with session.get(img_url) as img_response:
                                img_data = await img_response.read()
                                try:
                                    img = Image.open(BytesIO(img_data))
                                    img.verify()
                                    image_name = os.path.basename(img_url)
                                    output_path = os.path.join(img_dir, image_name)
                                    if not os.path.exists(output_path):
                                        img = Image.open(BytesIO(img_data))
                                        img.save(output_path)
                                        global_state.images.append((output_path, img_url))
                                except Exception:
                                    continue
                        global_state.image_urls.clear()
                    except Exception as e:
                        QMetaObject.invokeMethod(
                    output, "setText", Q_ARG(str, f"Image download error: {str(e)}")
                    )

            async def find_images_async(self, urls):
                timeout = ClientTimeout(total=60)
                connector = TCPConnector(limit_per_host=10)
                semaphore = asyncio.Semaphore(10)
                async with ClientSession(timeout=timeout, connector=connector) as session:
                    tasks = [self.download_image(session, url, semaphore) for url in urls]
                    await asyncio.gather(*tasks)


class wikiSpyderTools(object):

    def __init__(self):
        super().__init__()


    def find_images(self, urls):
    # output.setText("Finding images...")
        try:
            asyncio.run(self.find_images_async(urls))
        # output.setText("Images found." if global_state.images else "No images found.")
        except Exception as e:
            QMetaObject.invokeMethod(
           # output, "setText", Q_ARG(str, f"An error occurred: {str(e)}")
            )
        return global_state.image_urls

    def launch_image_viewer(self):
        image_dialog = QDialog(self)
        image_dialog.setWindowTitle("Image Viewer")
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dialog_widget = QWidget()
        dialog_layout = QVBoxLayout(dialog_widget)
        row_layout = QVBoxLayout()
        row = QHBoxLayout()
        count = 0

        selected_images = []
        checkboxes = []

        def open_url(url):
            QDesktopServices.openUrl(QUrl(url))

        def checkbox_event(img_path):
            def handler(state):
                if state == Qt.CheckState.Checked:
                    if img_path not in selected_images:
                        selected_images.append(img_path)
                else:
                    if img_path in selected_images:
                        selected_images.remove(img_path)
            return handler

        def select_all_images(state):
            for checkbox in checkboxes:
                checkbox.setChecked(state == Qt.CheckState.Checked)

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
            img_label.mousePressEvent = lambda event, url=img_url: open_url(url)
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(checkbox_event(img_path))
            checkboxes.append(checkbox)
            img_layout = QVBoxLayout()
            img_layout.addWidget(img_label)
            img_layout.addWidget(checkbox)
            row.addLayout(img_layout)
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

        select_all_checkbox = QCheckBox("Select All")
        select_all_checkbox.stateChanged.connect(select_all_images)
        image_dialog_layout.addWidget(select_all_checkbox)

        save_button = QPushButton("Save Selected Images")
        save_button.clicked.connect(lambda: self.save_selected_images(selected_images))
        image_dialog_layout.addWidget(save_button)

        image_dialog.setLayout(image_dialog_layout)
        image_dialog.setFixedWidth(5 * 200 + 40)
        image_dialog.exec()



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.retranslateUi(self)

        self.wikiSpyder = wikiSpyderMethods()

        self.ui.pushButton.clicked.connect(self.wikiSpyder.spyder_1st_run)
        # self.ui.pushButton_2.clicked.connect(self.wikiSpyder.deep_probe)

        self.ws_tools = wikiSpyderTools()
        self.ui.pushButton_3.clicked.connect(self.ws_tools.launch_image_viewer)
        # self.ui.subject_url.textChanged.connect(self.ws_tools.update_subject_url)
        # self.ui.lineEdit_2.textChanged.connect(self.ws_tools.update_disco_terms)


app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()



