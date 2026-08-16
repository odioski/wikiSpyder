from setuptools import setup

setup(
    name="wikiSpyder",
    version="0.9.2",
    py_modules=[
        "app_state",
        "image_probe",
        "image_viewer",
        "main",
        "newwindow",
        "scraping",
        "worker",
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
    description="wikiSpyder 0.9.2, Codename Michelle: a web scraping tool that finds and displays images from Wikipedia reference pages.",
    url="https://github.com/odioski",
)
