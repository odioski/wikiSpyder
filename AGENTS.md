# wikiSpyder Agent Instructions

> **Codename: Michelle**

wikiSpyder is a **Python 3.12 + PyQt6 desktop application** for scraping a Wikipedia page's references, filtering links by search terms, and probing the resulting pages for images.

## Project shape

- `main.py` is the real application entry point and contains the runtime behavior.
- `__main__.py` is only a thin launcher that calls `main.main()`.
- `newwindow.py` is generated from `main-view.ui` by `pyuic6`. Prefer editing `main-view.ui` and regenerating `newwindow.py` instead of hand-editing the generated file.

## Repo-specific conventions

- Keep **UI orchestration** in `MainWindow` methods and keep **normalization/parsing helpers** as small helper methods or standalone helpers instead of burying them inside signal handlers.
- Preserve the current split between:
  - reference scraping from the Wikipedia page,
  - link filtering/tallying,
  - image discovery and download,
  - image viewer/save flows.
- Shared runtime data currently lives in the `GlobalState` dataclass instance. If you add new cross-feature state, extend `GlobalState` intentionally rather than introducing more module-level globals.
- The app writes temporary downloaded images under `saved_images/` relative to the repository. Keep cleanup behavior aligned with `cleanup_images()` and `closeEvent()`.
- User-visible results are rendered in `label_4` and `label_5` using HTML strings. Preserve clickable-link behavior in formatted output.
- Networking currently uses:
  - `requests` for the initial Wikipedia/reference fetch
  - `aiohttp` for asynchronous page and image probing
  Keep that split unless there is a clear reason to consolidate it.

## Change rules

- When adding dependencies, update both `requirements.txt` and `setup.py`.
- When changing the UI surface, update both the `.ui` source and any runtime wiring in `main.py`.
- Do not silently broaden crawl scope or image saving behavior; new crawl/probe options should be explicit in the UI and reflected in runtime logic.
- Prefer behavior-preserving refactors. This app has minimal automation today, so avoid speculative rewrites.

## Validation

The repository does not currently define a full automated test suite. The existing lightweight checks are:

- `python -m py_compile __main__.py main.py newwindow.py setup.py`
- `python -c "import main, newwindow"`

For GUI-affecting changes, also launch the app locally and exercise the edited flow.
