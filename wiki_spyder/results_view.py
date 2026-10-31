# Codename: Michelle
"""Formatting and counting helpers for links, tallies, and probe output."""

import html
import re
from collections.abc import Mapping, Sequence


def format_links(links: Sequence[str]) -> str:
    if not links:
        return "No links found."

    rows = []
    for index, link in enumerate(links, start=1):
        safe_url = html.escape(link, quote=True)
        rows.append(
            f'{index}. <a href="{safe_url}">{html.escape(link)}</a>'
            if link.startswith(("http://", "https://"))
            else f"{index}. {html.escape(link)}"
        )
    return "<h2>Links Found</h2><h4>Click a link to visit it.</h4><br/>" + "<br/>".join(rows)


def count_search_terms(page_text: str, search_terms: Sequence[str]) -> dict[str, int]:
    return {
        term: len(re.findall(re.escape(term), page_text, flags=re.IGNORECASE))
        for term in search_terms
    }


def matched_links_count(
    link_term_counts: Mapping[str, Mapping[str, int]], matched_links: Sequence[str]
) -> int:
    matched_by_content = [
        url for url, counts in link_term_counts.items() if sum(counts.values())
    ]
    return len(matched_by_content) if matched_by_content else len(matched_links)


def search_term_hits_count(term_totals: Mapping[str, int]) -> int:
    return sum(term_totals.values())


def format_tally_events(events: Sequence[str]) -> str:
    if not events:
        return ""
    rows = "".join(f"<li>{html.escape(event)}</li>" for event in events[-5:])
    return "<h3>Actions</h3><ul>" + rows + "</ul>"


def format_term_totals(
    search_terms: Sequence[str], term_totals: Mapping[str, int]
) -> str:
    if not search_terms:
        return "<p>Search terms = none</p>"
    rows = "".join(
        f"<li>{html.escape(term)} = {term_totals.get(term, 0)}</li>"
        for term in search_terms
    )
    return "<h3>Terms</h3><ul>" + rows + "</ul>"


def format_link_term_counts(
    search_terms: Sequence[str],
    link_term_counts: Mapping[str, Mapping[str, int]],
) -> str:
    if not search_terms or not link_term_counts:
        return ""

    rows = []
    for url, counts in link_term_counts.items():
        if not sum(counts.values()):
            continue
        terms = ", ".join(
            f"{html.escape(term)}: {count}"
            for term, count in counts.items()
            if count
        )
        safe_url = html.escape(url, quote=True)
        rows.append(
            f'<li><a href="{safe_url}">{html.escape(url)}</a><br/>{terms}</li>'
        )

    if not rows:
        return "<h3>Links</h3><p>No search terms found on probed pages.</p>"
    return "<h3>Links</h3><ol>" + "".join(rows) + "</ol>"


def format_download_output(messages: Sequence[str]) -> str:
    if not messages:
        return ""
    rows = "".join(f"<li>{html.escape(message)}</li>" for message in messages)
    return "<h2>Probe &amp; Image Operations</h2><ul>" + rows + "</ul>"


def format_tally(
    *,
    session_id: str,
    saved_session_count: int,
    found_link_count: int,
    matched_count: int,
    search_term_hits: int,
    tally_filename: str,
    tally_events: str,
    term_totals: str,
    link_term_counts: str,
    image_url_count: int,
    saved_image_count: int,
) -> str:
    return (
        "<h2>Links Found Tally</h2>"
        f"<p>Research Session = {html.escape(session_id[:8])}</p>"
        f"<p>Saved Sessions = {saved_session_count}</p>"
        f"<p>Found Links = {found_link_count}</p>"
        f"<p>Matched Links = {matched_count}</p>"
        f"<p>Search Term Hits = {search_term_hits}</p>"
        f"<p>Tally File = {html.escape(tally_filename)}</p>"
        f"{tally_events}{term_totals}{link_term_counts}"
        f"<p>Images Found = {image_url_count}</p>"
        f"<p>Images Saved = {saved_image_count}</p>"
    )
