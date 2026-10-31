# Codename: Michelle
from setuptools import setup

setup(
    name="wikiSpyder",
    version="1.0.0",
    packages=["wiki_spyder"],
    py_modules=["main"],
    data_files=[
        (
            "share/wikiSpyder",
            ["assets/wikiSpyder.ico", "assets/wikiSpyder.svg", "wikiSpyder.qss"],
        ),
    ],
    install_requires=[
        "aiohttp==3.13.3",
        "beautifulsoup4==4.14.3",
        "Pillow==12.1.1",
        "PyQt6==6.10.2",
        "pytest-qt==4.5.0",
        "requests==2.33.0",
    ],
    entry_points={
        "console_scripts": [
            "wikiSpyder=main:main",
        ],
    },
    author="Omar Daniels",
    author_email="link92@bookmotives.com",
    description="wikiSpyder 1.0.0, Codename Michelle: a web scraping tool that finds and displays images from Wikipedia reference pages.",
    url="https://github.com/odioski",
)
