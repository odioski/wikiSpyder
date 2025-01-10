from setuptools import setup, find_packages

setup(
    name="wikiSpyder",
    version="0.2.1",
    packages=find_packages(),
    install_requires=[
        "requests",
        "beautifulsoup4",
        "Pillow",
        "PyQt6",
        "aiohttp",
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
