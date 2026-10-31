# Changelog

## 1.0.0 - Codename Michelle

- Added one-click Windows, Linux, and macOS release packaging through tagged GitHub releases.
- Moved session archives and temporary images into per-user application data and cache locations, migrating an existing checkout `tally.csv` on first launch.
- Removed the GUI test plugin from normal app dependencies and added separate development and packaging dependency lists.
- Recreated `.gitignore` rules for local sessions, temporary images, build outputs, Python caches, and editor artifacts.

## 2026-10-31 — Codex session

- Refreshed the desktop UI with a dark slate theme, clearer input and result sections, and responsive layouts.
- Added vertical scrolling to both result panels and Enter-to-launch behavior for the Search Terms field.
- Added File, Sessions, Options, and Help menus, including saved-session browsing, session export, and a setting to restore the latest session at startup.
- Expanded `tally.csv` into a session-aware archive that saves and restores queries, links, term counts, events, and displayed output. Existing four-column tally files remain readable; writes use an atomic replacement.
- Added recursive same-site Deep Probe with `robots.txt` checks. Deep Probe and View Images now target matched links when available, otherwise the subject's found references.
- Embedded the selectable image gallery in the main window. Saving selected images now uses one destination folder and avoids overwriting existing filenames.
- Created an encyclopedia-style globe and spider app icon in ICO format, with an editable SVG source, and wired it into the window and application.
- Moved supporting Python modules into the `wiki_spyder/` package. Kept `main.py` as the entry point and moved window construction/layout and result formatting into dedicated modules.
- Updated packaging, generated UI references, README, agent instructions, and CI commands for the package layout.
- Removed the unused image-save method, temporary bytecode and image directories, and a duplicate CI workflow.
