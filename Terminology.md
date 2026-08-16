# wikiSpyder Terminology

A compact glossary of terms that came up while refining wikiSpyder's Tally, Stop, Refresh, layout, and progress behavior.

## Runtime And Control Flow

### active
Work is currently running.

Example: `_operation_active` prevents Refresh from starting a second run.

### idle
No operation is running.

Example: Refresh is enabled again after `_set_operation_active(False)`.

### operation state
Whether the app is idle or busy.

Example: `_set_operation_active(True)` disables Refresh, enables Stop, and shows progress.

### workflow
Sequence of user actions and app responses.

Example: Launch starts work, Stop kills it, Refresh reruns when idle.

### runtime
Behavior while the app is running.

Example: Stop affects running probes rather than only changing static code.

### blocking
Work that may not return immediately.

Example: an in-flight `requests.get()` call can block until it returns or times out.

### timeout
Maximum wait before a network request gives up.

Example: `requests.get(..., timeout=60)` can delay immediate Stop response during a socket wait.

### network socket
Low-level request connection that cannot always be killed instantly.

Example: Stop cannot instantly terminate a blocking requests socket.

## Stop And Cancellation

### Stop
Cancellation/kill action.

Example: Stop records `Stop` and triggers `kill_current_operation()`.

### kill command
The Stop action expressed as a stronger cancellation command.

Example: pressing Stop now sets the kill event for running async probe tasks.

### kill path
The dedicated Stop flow for cancelling active work.

Example: `stop_current_operation()` now delegates to `kill_current_operation()`.

### cancellation
Stopping queued or running operations.

Example: unfinished probe tasks are cancelled when the kill event wins the async race.

### cooperative stopping
Stopping when code reaches cancellation checks.

Example: `download_image()` returns early when `_stop_requested` or `kill_event` is set.

### signal
Shared cancellation trigger for async tasks.

Example: `_kill_event` is an `asyncio.Event` passed to probe tasks.

### cancel
Stop unfinished async tasks.

Example: `find_images_async()` cancels remaining tasks when `kill_event` fires.

### queued
Scheduled work not yet completed.

Example: URL probe tasks waiting behind the semaphore are cancelled after Stop.

### unfinished
Tasks still running or waiting.

Example: unfinished image probes are cancelled by the kill path.

### intercedes
A button/action interrupting or stepping into an active workflow.

Example: Stop intercedes while a probe is running and records that action in `tally.csv`.

## Tally And Persistence

### Tally
The count/status view and tracking feature.

Example: `label_5` now renders Links Found Tally with found links, matched links, term hits, and images.

### CSV-backed
Stored in `tally.csv`.

Example: link-term counts and button events are saved to `tally.csv` beside `main.py`.

### comma-delimited
CSV format.

Example: `tally.csv` rows use fields like `kind,url,term,count`.

### tracker
Persistent structure for events/counts.

Example: `_save_tally_file()` and `_load_tally_file()` act as the Tally tracker.

### event
Recorded button/action such as Launch, Stop, Refresh.

Example: `_record_tally_event("Stop")` writes the Stop event to `tally.csv`.

### preserve
Keep counts instead of losing them across actions.

Example: Refresh reloads `tally.csv` when the URL and search terms are unchanged.

### reset
Clear old state for a new query.

Example: changing the URL or search terms resets Tally state instead of reusing old counts.

### reload
Read existing tally data back from CSV.

Example: `_load_tally_file()` restores counts before Refresh continues the same query.

### no-double-count
Replacing counts for a URL rather than accumulating duplicates.

Example: `_record_link_term_counts()` rebuilds totals after replacing one URL's counts.

### query signature
URL/search-term identity used to decide whether counts still apply.

Example: `tally_wikipedia_url` and `tally_search_terms` decide whether Refresh preserves the Tally.

### term hits
Search term occurrence count.

Example: `"alpha beta alpha"` produces `alpha = 2` and `beta = 1`.

### per-link
Count grouped by URL.

Example: the Tally view lists each matched URL with that page's term counts.

### per-term
Count grouped by search term.

Example: the Terms section shows one total for each search term.

### visible page text
Text extracted from HTML for cleaner term counts.

Example: `soup.get_text(" ")` is counted instead of raw HTML markup.

## Probing And Output

### async
Asynchronous work used for probing pages/images.

Example: `find_images_async()` schedules page/image probe tasks.

### probe
Fetching/checking links for terms or images.

Example: each reference URL is probed for search-term hits and image candidates.

### image probing
Checking pages for image URLs.

Example: `download_image()` collects `img src` values after counting text.

### Deep Probe
Recursive link crawl mode.

Example: Deep Probe crawls deeper from the reference links before image probing.

### live update
Refreshing the Tally view as each link is processed.

Example: `download_image()` calls `update_tally_view()` after recording term counts.

### stream
Progressively showing results as they arrive.

Example: each probed link can appear in the Tally panel before the full probe run finishes.

### clickable
Links remain openable in the UI.

Example: `format_links()` and the Tally link list render URLs as clickable anchors.

### formatted output
HTML-rendered result text.

Example: `label_4` and `label_5` receive HTML strings with headings, lists, and anchors.

## UI And Layout

### progress
Visible busy feedback.

Example: the bottom-center progress bar appears while operations are active.

### indeterminate
Progress bar mode that shows activity without a percent.

Example: the first progress bar used an indeterminate busy state while Launch, Refresh, Deep Probe, or View Images was running.

### dynamic
Adjusts with app state or window changes.

Example: Refresh enables/disables dynamically based on whether work is running.

### flex
Layout behavior that adapts rather than staying fixed.

Example: result panels and button rows reposition when the main window expands.

### responsive
UI expands/repositions with the window.

Example: Links Found and Tally views grow horizontally on resize.

### horizontally
Width/left-right layout behavior.

Example: `_resize_result_views()` distributes extra horizontal space between the two result panels.

### centered
Aligned around the middle of the main view.

Example: `_center_bottom_buttons()` keeps the button row centered.

### geometry
Explicit widget position and size.

Example: `setGeometry()` is used to resize the result panels and button row.

### resize
Window size change handling.

Example: `resizeEvent()` recenters buttons, result views, and the progress bar.

## Buttons

### Launch
Initial scrape/probe action.

Example: pressing Launch records `Launch` in `tally.csv` and starts the first run.

### Refresh
Rerun current query/action context.

Example: Refresh preserves Tally counts when the same URL and terms are used.

## Engineering Terms

### refactor
Reorganizing code behavior without changing the user-facing goal.

Example: Stop was refactored from scattered flag setting into `kill_current_operation()`.

### helper
Small focused method.

Example: `_format_tally_events()` formats recent button actions for the Tally view.

### cleanup
Removing temporary images/state.

Example: `cleanup_images()` clears `saved_images` on close or before a fresh image probe.

### minimize
Reduce code clutter.

Example: dead commented click-handler code and unused imports were removed.

### main functions
Core app behavior methods.

Example: `refresh_current_view()`, `spyder_1st_run()`, `find_images()`, and `tally_links()` carry the main workflows.

### deterministic
Predictable behavior that does not vary by platform defaults or incidental runtime state.

Example: the Deep Probe tooltip uses a custom-drawn circular information icon so it stays circular instead of depending on the operating system's standard icon.

### validation
Checks proving the change works.

Example: `py_compile`, import checks, and offscreen Qt smoke tests were run after edits.

### smoke test
Small focused test for one behavior.

Example: the progress bar test checked visibility, timer state, and reset behavior.

### compile
Syntax/bytecode check via `py_compile`.

Example: `python -m py_compile __main__.py main.py newwindow.py setup.py`.

### import
Module loading check.

Example: `python -c "import main, newwindow"`.

## AI Retrieval Terms

### RAG
Retrieval-augmented generation: an AI pattern where the model first looks up relevant project text, then uses that retrieved context to answer or generate.

Example: a local wikiSpyder assistant could retrieve `Terminology.md`, `README.md`, and `tally.csv` context before explaining why a link matched.

### retrieval
The lookup step that finds relevant chunks of local knowledge before an AI responds.

Example: searching `Terminology.md` for "query signature" before modifying Refresh behavior.

### chunk
A small searchable piece of a larger document.

Example: the Tally section of `Terminology.md` could be split into chunks so a local model can retrieve only the relevant definitions.

### embedding
A numeric representation of text used to compare meaning, not just exact words.

Example: an embedding can help match "cancel a probe" with the Stop and kill path definitions.

### vector index
A searchable store of embeddings.

Example: wikiSpyder could keep embeddings for `README.md`, `Terminology.md`, and `Architecture.md` in a local vector index.

### context window
The amount of text an AI model can consider at once.

Example: retrieval keeps the prompt smaller by adding only the most relevant wikiSpyder notes.

### grounding
Anchoring an AI answer in retrieved source material.

Example: a grounded answer about Stop should cite `kill_current_operation()` concepts from `Terminology.md` instead of guessing.

### local AI context
Project-specific files supplied to a self-hosted model so it understands the app.

Example: `Terminology.md` can teach a local model what Tally, Refresh, and Deep Probe mean in wikiSpyder.
