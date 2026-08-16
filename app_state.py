import os
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

APP_NAME = "wikiSpyder"
APP_VERSION = "0.9.2"
APP_CODENAME = "Michelle"
APP_DISPLAY_NAME = f"{APP_NAME} {APP_VERSION} - Codename {APP_CODENAME}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "saved_images")
TALLY_FILE = os.path.join(BASE_DIR, "tally.csv")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
IMAGE_PATTERN = re.compile(r"\.(?:jpg|jpeg|png|gif|webp)(?:$|[?#])", re.IGNORECASE)

os.makedirs(IMG_DIR, exist_ok=True)


@dataclass
class GlobalState:
    found_links: list[str] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    wikipedia_url: str = ""
    tally_wikipedia_url: str = ""
    tally_search_terms: list[str] = field(default_factory=list)
    matched_links: list[str] = field(default_factory=list)
    images: list[tuple[str, str]] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    fixed_links: list[str] = field(default_factory=list)
    link_term_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    term_totals: dict[str, int] = field(default_factory=dict)
    tally_events: list[str] = field(default_factory=list)


global_state = GlobalState()


def normalize_subject_url(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    if cleaned.startswith(("wikipedia.org/", "en.wikipedia.org/")):
        return f"https://{cleaned}"
    if cleaned.startswith("/wiki/"):
        return f"https://en.wikipedia.org{cleaned}"
    return f"https://en.wikipedia.org/wiki/{cleaned.replace(' ', '_')}"


def normalize_image_url(src: str, page_url: str) -> str | None:
    if not src:
        return None
    if src.startswith("//"):
        candidate = f"https:{src}"
    else:
        candidate = urljoin(page_url, src)
    if not IMAGE_PATTERN.search(candidate):
        return None
    return candidate


def build_image_path(image_url: str, image_count: int) -> str:
    filename = os.path.basename(image_url.split("?", 1)[0].split("#", 1)[0])
    if not filename:
        filename = f"image_{image_count + 1}.png"

    name, extension = os.path.splitext(filename)
    extension = extension or ".png"
    candidate = os.path.join(IMG_DIR, f"{name}{extension}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(IMG_DIR, f"{name}_{counter}{extension}")
        counter += 1
    return candidate
