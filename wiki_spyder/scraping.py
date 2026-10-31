# Codename: Michelle
from collections import deque
from collections.abc import Callable
from time import monotonic, sleep
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .app_state import USER_AGENT, global_state

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
    max_depth: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
    max_pages_per_site: int = 100,
    request_delay: float = 1.0,
) -> list[str]:
    if not start_urls:
        return []

    queue: deque[tuple[str, str, int]] = deque()
    queued: set[str] = set()
    for url in start_urls:
        normalized = _normalize_probe_url(url)
        if not normalized or normalized in queued:
            continue
        queue.append((normalized, _site_key(normalized), 0))
        queued.add(normalized)

    visited: set[str] = set()
    discovered: list[str] = []
    robots_cache: dict[str, RobotFileParser | None] = {}
    robots_allowed: dict[str, bool] = {}
    pages_by_site: dict[str, int] = {}
    last_request_by_site: dict[str, float] = {}

    while queue:
        if should_stop():
            break

        current_url, root_site, depth = queue.popleft()
        if max_depth is not None and depth > max_depth:
            continue

        normalized = _normalize_probe_url(current_url)
        if not normalized or normalized in visited:
            continue
        if _site_key(normalized) != root_site:
            continue
        if pages_by_site.get(root_site, 0) >= max_pages_per_site:
            continue

        visited.add(normalized)
        if progress_callback and (
            len(visited) == 1 or len(visited) % 25 == 0
        ):
            progress_callback(
                f"Deep Probe: checking page {len(visited)} — {normalized}"
            )
        if not _can_probe_url(
            normalized,
            get_response,
            should_stop,
            robots_cache,
            robots_allowed,
            last_request_by_site,
            request_delay,
        ):
            continue

        discovered.append(normalized)
        pages_by_site[root_site] = pages_by_site.get(root_site, 0) + 1

        if not _wait_for_site_rate_limit(
            root_site, request_delay, last_request_by_site, should_stop
        ):
            break
        last_request_by_site[root_site] = monotonic()
        try:
            response = get_response(normalized, 20)
            if response is None:
                break
            response.raise_for_status()
        except requests.RequestException:
            continue

        content_type = response.headers.get("Content-Type", "")
        if content_type and "html" not in content_type.lower():
            continue

        try:
            soup = BeautifulSoup(response.content, "html.parser")
        except Exception:
            continue

        for tag in soup.find_all("a", href=True):
            next_url = _normalize_probe_url(str(tag.get("href", "")), normalized)
            if not next_url:
                continue
            if _site_key(next_url) != root_site or next_url in visited:
                continue
            if next_url in queued:
                continue
            queue.append((next_url, root_site, depth + 1))
            queued.add(next_url)

    if progress_callback:
        if should_stop():
            progress_callback(f"Deep Probe stopped after {len(visited)} pages.")
        else:
            progress_callback(
                "Deep Probe crawl complete: "
                f"{len(discovered)} pages found across "
                f"{len(pages_by_site)} sites (limit {max_pages_per_site} pages/site)."
            )
    return discovered


def _normalize_probe_url(href: str, base_url: str | None = None) -> str | None:
    candidate = href.strip()
    if not candidate or candidate.startswith("#"):
        return None
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    elif base_url is not None:
        candidate = urljoin(base_url, candidate)

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return parsed._replace(fragment="").geturl()


def _site_key(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def _can_probe_url(
    url: str,
    get_response: ResponseGetter,
    should_stop: Callable[[], bool],
    robots_cache: dict[str, RobotFileParser | None],
    robots_allowed: dict[str, bool],
    last_request_by_site: dict[str, float],
    request_delay: float,
) -> bool:
    parsed = urlparse(url)
    site = _site_key(url)
    if site in robots_cache:
        parser = robots_cache[site]
        return robots_allowed.get(site, False) and (
            parser is None or parser.can_fetch(USER_AGENT, url)
        )

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser: RobotFileParser | None = None
    allowed = False
    try:
        if not _wait_for_site_rate_limit(
            site, request_delay, last_request_by_site, should_stop
        ):
            robots_cache[site] = None
            robots_allowed[site] = False
            return False
        response = get_response(robots_url, (5, 10))
        if response is None:
            robots_cache[site] = None
            robots_allowed[site] = False
            return False
        last_request_by_site[site] = monotonic()
        if response.ok:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            allowed = True
        elif response.status_code == 404:
            # RFC 9309 treats a missing robots.txt as unavailable, so access is allowed.
            allowed = True
    except requests.RequestException:
        parser = None
        allowed = False

    robots_cache[site] = parser
    robots_allowed[site] = allowed
    if should_stop():
        return False
    return allowed and (parser is None or parser.can_fetch(USER_AGENT, url))


def _wait_for_site_rate_limit(
    site: str,
    request_delay: float,
    last_request_by_site: dict[str, float],
    should_stop: Callable[[], bool],
) -> bool:
    last_request = last_request_by_site.get(site)
    if last_request is None or request_delay <= 0:
        return not should_stop()

    remaining = request_delay - (monotonic() - last_request)
    while remaining > 0:
        if should_stop():
            return False
        sleep(min(remaining, 0.1))
        remaining = request_delay - (monotonic() - last_request)
    return not should_stop()
