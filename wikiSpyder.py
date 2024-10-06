import requests
import os

import re
# for the haircut

from bs4 import BeautifulSoup
# parse wikipedia page Reference sections (or any web page...)

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor, QBrush
from PyQt6.QtWidgets import (QApplication, QCheckBox, QLabel, QLineEdit,
                             QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QScrollArea, QScrollBar,
                             QBoxLayout, QWidget, QAbstractSlider)

#pyQt

global newData

basedir = os.path.dirname(__file__)
# so it can find its home dir

app = QApplication([])

class MainWindow(QMainWindow):

    # discos's

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
        search_terms = []

        if search_terms == "":
            output.setText("Please add some search terms")
        else:
            search_terms = text

    def __init__(self):
        super().__init__()

        # first layer methods
    
        logo = QLabel("wikisSpyder 0.1.9")
        logo.setPixmap(QPixmap(os.path.join(basedir, "logo.png")))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subject_label = QLabel("Subject")
        subject_url = QLineEdit()
        subject_url.setPlaceholderText("wikipedia.org/wiki/YourFavoriteStar")
        subject_url.textChanged.connect(self.disco_subject)

        search_term_label = QLabel("Search terms")
        search_term_inputs = QLineEdit()
        # set the size of theis box

        search_term_inputs.setPlaceholderText("TYPE or DROP your search terms here; use csv or txt file if it's a long list")
        # if we get an upload box for input
        
        search_term_inputs.textChanged.connect(self.disco_terms)

        launchButton = QPushButton("Launch")
        launchButton.setFixedWidth(200)
        launchButton.setFixedHeight(50)
        launchButton.clicked.connect(spyder_1st_run)

        deep_probe_button = QPushButton("Deep Probe")
        deep_probe_button.setFixedWidth(200)
        deep_probe_button.setFixedHeight(50)
        launchButton.clicked.connect(spyder_infinite)
                
        view_images_button = QPushButton("View Images")
        view_images_button.setFixedWidth(200)
        view_images_button.setFixedHeight(50)
        view_images_button.clicked.connect(cycle_module_button)


        found_matches = QLabel("Links found...")
        found_matches.setAlignment(Qt.AlignmentFlag.AlignCenter)

        global output        

        output = QLabel("output will be displayed here...")
        output.setObjectName("nfo")
        output.setMinimumHeight(250)
        #output.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #output.setWordWrap(True)        
  
        scroll_area = QScrollArea()
        scroll_area.setWidget(output)
        
        # first layer display...


        title_panel = QVBoxLayout()

        title_panel.addWidget(logo)

        input_panel = QVBoxLayout()

        input_panel.addWidget(subject_label)
        input_panel.addWidget(subject_url)
        input_panel.addWidget(search_term_label)
        input_panel.addWidget(search_term_inputs)

        control_panel = QHBoxLayout()

        control_panel.addWidget(launchButton)
        control_panel.addWidget(deep_probe_button)
        control_panel.addWidget(view_images_button)

        layout_z_0 = QVBoxLayout()

        layout_z_0.addLayout(title_panel)
        layout_z_0.addLayout(input_panel)
        layout_z_0.addWidget(found_matches)
        layout_z_0.addWidget(output)
        layout_z_0.addLayout(control_panel)

        app_container = QWidget()
        app_container.setLayout(layout_z_0)

        self.setCentralWidget(app_container)
        self.setFixedSize(1200, 600)

        # image display

        # display of counts

        # map (Spyder's path) display

        # Actually, would like to see if Copiot or Chat-GPT can port this to .NET OR MAUI...

   
def capture_links(wikipedia_url):
 
    response = requests.get(wikipedia_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    global external_links
    external_links = []

    for ref in soup.find_all('span', class_='reference-text'):
        for link in ref.find_all('a', class_='external text', href=True):
            external_links.append(link['href'] + "<br/>")
            
    newData = str(external_links)
    output.setText(newData)
    return external_links

def capture_images(external_links):
    try:
        response = requests.get(external_links)
        soup = BeautifulSoup(response.content, 'html.parser')

            
        global image_link
        image_link = []
            
        for img in soup.find_all('img', src=True):
            image_link.append(img['src'])

            output.setText(image_link)    
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {external_links} : {e}")
        return []
    

def get_images():

    for img in image_link:
        img_link = re.compile(img)
        img_link = re.match(r'[\b.webp]+[\b.gif]+[b\.jpeg]+[b\.jpg]+[\b.png]', img)
        # regex to match and pick relevant images.

        output.setText(img_link) 


def spyder_1st_run(self):

    capture_links(wikipedia_url)
    capture_images

def spyder_infinite():

    pass
    #   infinite or let the user decide?


def cycle_module_button():

    pass
    #   Three modes:
    #   sums (hits per search term per external link), Spyder's path, and view images


window = MainWindow()

app.setStyleSheet(Path(os.path.join(basedir, 'wikiSpyder.qss')).read_text())

window.show()
app.exec()
