# Codename: Michelle
"""Session persistence for wikiSpyder's human-readable tally archive."""

import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any


class TallyStore:
    """Keep complete session snapshots in a CSV file with legacy import support."""

    FIELDS = (
        "session_id",
        "started_at",
        "kind",
        "subject",
        "url",
        "term",
        "count",
        "value",
    )

    def __init__(self, path: str) -> None:
        self.path = path
        self.sessions: dict[str, dict[str, Any]] = {}
        self.load_error = ""
        self._load()

    def latest(self) -> tuple[str, dict[str, Any]] | None:
        if not self.sessions:
            return None
        session_id = max(
            self.sessions,
            key=lambda item: self.sessions[item].get("started_at", ""),
        )
        return session_id, self.sessions[session_id]

    def save(self, session_id: str, snapshot: dict[str, Any]) -> None:
        if self.load_error:
            raise OSError(f"existing tally file could not be read: {self.load_error}")
        self.sessions[session_id] = snapshot
        directory = os.path.dirname(os.path.abspath(self.path))
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=directory,
                prefix=".tally-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = temp_file.name
                writer = csv.DictWriter(temp_file, fieldnames=self.FIELDS)
                writer.writeheader()
                for saved_id, saved in self.sessions.items():
                    self._write_session(writer, saved_id, saved)
            os.replace(temp_path, self.path)
        except OSError:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise

    def export_session(self, session_id: str, path: str) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown session: {session_id}")

        directory = os.path.dirname(os.path.abspath(path))
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="",
                dir=directory,
                prefix=".session-export-",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = temp_file.name
                writer = csv.DictWriter(temp_file, fieldnames=self.FIELDS)
                writer.writeheader()
                self._write_session(writer, session_id, session)
            os.replace(temp_path, path)
        except OSError:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            raise

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            return

        try:
            with open(self.path, "r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                for row in reader:
                    session_id = row.get("session_id") or "legacy"
                    session = self.sessions.setdefault(session_id, self._empty_session())
                    session["started_at"] = row.get("started_at") or session["started_at"]
                    kind = row.get("kind", "")
                    url = row.get("url", "") or ""
                    term = row.get("term", "") or ""
                    value = row.get("value", "") or ""

                    if kind == "session":
                        session["subject"] = row.get("subject", "") or ""
                        if value:
                            try:
                                parsed_terms = json.loads(value)
                            except (TypeError, json.JSONDecodeError):
                                parsed_terms = []
                            if isinstance(parsed_terms, list):
                                session["search_terms"] = [
                                    str(item) for item in parsed_terms
                                ]
                    elif kind == "event":
                        event = value or term
                        if event:
                            session["events"].append(event)
                    elif kind in {"found_link", "probed_link", "matched_link", "image_url"}:
                        target = {
                            "found_link": "found_links",
                            "probed_link": "fixed_links",
                            "matched_link": "matched_links",
                            "image_url": "image_urls",
                        }[kind]
                        if url and url not in session[target]:
                            session[target].append(url)
                    elif kind == "term_count" and url and term:
                        try:
                            count = int(row.get("count", "0") or 0)
                        except ValueError:
                            count = 0
                        session["link_term_counts"].setdefault(url, {})[term] = count
                    elif kind == "output_links":
                        session["links_output"] = value
                    elif kind == "output_tally":
                        session["tally_output"] = value
                    elif kind == "metadata":
                        session["legacy_metadata"] = value or term
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            self.sessions.clear()
            self.load_error = str(exc)
            return

        legacy = self.sessions.get("legacy")
        if legacy and not legacy["search_terms"]:
            legacy["search_terms"] = list(
                dict.fromkeys(
                    term
                    for counts in legacy["link_term_counts"].values()
                    for term in counts
                )
            )

    @staticmethod
    def _empty_session() -> dict[str, Any]:
        return {
            "started_at": "",
            "subject": "",
            "search_terms": [],
            "found_links": [],
            "fixed_links": [],
            "matched_links": [],
            "image_urls": [],
            "link_term_counts": {},
            "events": [],
            "links_output": "",
            "tally_output": "",
        }

    @staticmethod
    def _write_session(
        writer: csv.DictWriter, session_id: str, session: dict[str, Any]
    ) -> None:
        base = {
            "session_id": session_id,
            "started_at": session.get("started_at", "")
            or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

        def write(kind: str, **values: Any) -> None:
            writer.writerow({**base, "kind": kind, **values})

        write(
            "session",
            subject=session.get("subject", ""),
            value=json.dumps(session.get("search_terms", []), ensure_ascii=False),
        )
        if session.get("legacy_metadata"):
            write("metadata", value=session["legacy_metadata"])
        for event in session.get("events", []):
            write("event", value=event)
        for kind, key in (
            ("found_link", "found_links"),
            ("probed_link", "fixed_links"),
            ("matched_link", "matched_links"),
            ("image_url", "image_urls"),
        ):
            for url in session.get(key, []):
                write(kind, url=url)
        for url, terms in session.get("link_term_counts", {}).items():
            for term, count in terms.items():
                write("term_count", url=url, term=term, count=count)
        if session.get("links_output"):
            write("output_links", value=session["links_output"])
        if session.get("tally_output"):
            write("output_tally", value=session["tally_output"])
