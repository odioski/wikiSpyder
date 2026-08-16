from collections import deque
from collections.abc import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app_state import global_state

ResponseGetter = Callable[[str, int | tuple[int, int]], requests.Response | None]


def scrape_wikipedia_references(
    url: str,
    search_terms: list[str],
    get_response: ResponseGetter,
) -> list[str]:
    try:
        response = get_response(url, 30)
        if response is None:
            return ["Operation cancelled."]
        response.raise_for_status()
    except requests.RequestException as exc:
        return [f"Request error: {exc}"]

    try:
        soup = BeautifulSoup(response.content, "html.parser")
        references_section = soup.find("ol", class_="references") or soup.find(
            "div",
            class_="reflist reflist-columns references-column-width",
        )
        if references_section is None:
            global_state.found_links = []
            global_state.fixed_links = []
            global_state.matched_links = []
            return ["No references section found."]

        fixed_links: list[str] = []
        for tag in references_section.find_all("a", href=True):
            href = str(tag.get("href", "")).strip()
            if not href:
                continue
            if href.startswith("http://") or href.startswith("https://"):
                fixed_links.append(href)
            elif href.startswith("//"):
                fixed_links.append(f"https:{href}")
            else:
                fixed_links.append(urljoin("https://en.wikipedia.org", href))

        global_state.found_links = fixed_links
        global_state.fixed_links = fixed_links

        lowered_terms = [term.lower() for term in search_terms]
        if not lowered_terms:
            global_state.matched_links = []
            return fixed_links

        matched_links = [
            link
            for link in fixed_links
            if any(term in link.lower() for term in lowered_terms)
        ]
        global_state.matched_links = matched_links
        return matched_links if matched_links else ["No matching links found in references."]
    except Exception as exc:
        return [f"An error occurred: {exc}"]


def deep_probe_links(
    start_urls: list[str],
    get_response: ResponseGetter,
    should_stop: Callable[[], bool],
    max_depth: int = 2,
) -> list[str]:
    if not start_urls:
        return []

    queue: deque[tuple[str, int]] = deque((url, 0) for url in start_urls if url)
    visited: set[str] = set()
    discovered: list[str] = []

    while queue:
        if should_stop():
            break

        current_url, depth = queue.popleft()
        normalized = current_url.split("#", 1)[0].strip()
        if not normalized or normalized in visited or depth > max_depth:
            continue

        visited.add(normalized)
        discovered.append(normalized)

        try:
            response = get_response(normalized, 20)
            if response is None:
                break
            response.raise_for_status()
        except requests.RequestException:
            continue

        try:
            soup = BeautifulSoup(response.content, "html.parser")
        except Exception:
            continue

        for tag in soup.find_all("a", href=True):
            href = str(tag.get("href", "")).strip()
            if not href or href.startswith("#"):
                continue
            candidate = href
            if candidate.startswith("//"):
                candidate = f"https:{candidate}"
            elif not candidate.startswith(("http://", "https://")):
                candidate = urljoin(normalized, candidate)

            if not candidate.startswith(("http://", "https://")):
                continue
            next_url = candidate.split("#", 1)[0].strip()
            if next_url not in visited:
                queue.append((next_url, depth + 1))

    return discovered
