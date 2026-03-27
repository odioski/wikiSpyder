from setuptools import setup, find_packages

setup(
    name="wikiSpyder",
    version="0.2.1",
    packages=find_packages(),
    install_requires=[
        "aiohttp==3.13.3",
        "beautifulsoup4==4.14.3",
        "Pillow==12.1.1",
        "PyQt6==6.5.0",
        "requests==2.33.0",
    ],
    entry_points={
        "console_scripts": [
            "wikiSpyder=main:main",
        ],
    },
    package_data={
        "": ["logo.png"],
    },
    include_package_data=True,
    author="Omar Daniels",
    author_email="link92@bookmotives.com",
    description="A web scraping tool to find and display images from Wikipedia references.",
    url="https://github.com/odioski",
)
