import asyncio
import os
from collections.abc import Callable
from io import BytesIO
from threading import Event, RLock

import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

from app_state import (
    USER_AGENT,
    build_image_path,
    global_state,
    normalize_image_url,
)


class ImageProbe:
    def __init__(
        self,
        state_lock: RLock,
        stop_event: Event,
        stop_requested: Callable[[], bool],
        set_stop_requested: Callable[[bool], None],
        set_kill_event: Callable[[asyncio.Event | None], None],
        record_link_term_counts: Callable[[str, str], None],
        append_output: Callable[[str], None],
    ) -> None:
        self._state_lock = state_lock
        self._stop_event = stop_event
        self._stop_requested = stop_requested
        self._set_stop_requested = set_stop_requested
        self._set_kill_event = set_kill_event
        self._record_link_term_counts = record_link_term_counts
        self._append_output = append_output

    async def download_image(
        self,
        session: requests.Session,
        url: str,
        semaphore: asyncio.Semaphore,
        kill_event: asyncio.Event,
    ) -> None:
        async with semaphore:
            if self._should_stop(kill_event):
                return

            self._append_output(f"Probing page: {url}")
            try:
                response = await asyncio.to_thread(
                    session.get,
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=60,
                )
                response.raise_for_status()
                page_html = response.text
            except requests.RequestException as exc:
                global_state.messages.append(f"Skipping {url}: {exc}")
                self._append_output(f"Skipped page: {url} ({exc})")
                return

            if self._should_stop(kill_event):
                return

            soup = BeautifulSoup(page_html, "html.parser")
            self._record_link_term_counts(url, soup.get_text(" "))

            discovered_urls = self._discover_image_urls(soup, url, kill_event)
            self._append_output(
                f"Found {len(discovered_urls)} image link(s): {url}"
            )

            for image_url in discovered_urls:
                if self._should_stop(kill_event):
                    return
                try:
                    img_response = await asyncio.to_thread(
                        session.get,
                        image_url,
                        headers={"User-Agent": USER_AGENT},
                        timeout=60,
                    )
                    img_response.raise_for_status()
                    img_data = img_response.content
                except requests.RequestException as exc:
                    self._append_output(f"Skipped image: {image_url} ({exc})")
                    continue

                if self._should_stop(kill_event):
                    return

                output_path = build_image_path(image_url, len(global_state.images))
                try:
                    with Image.open(BytesIO(img_data)) as image:
                        image.verify()
                    with Image.open(BytesIO(img_data)) as image:
                        image.save(output_path)
                except (UnidentifiedImageError, OSError):
                    self._append_output(f"Skipped invalid image: {image_url}")
                    continue

                with self._state_lock:
                    global_state.images.append((output_path, image_url))
                self._append_output(
                    f"Saved {os.path.basename(output_path)} from {image_url}"
                )

    async def find_images_async(self, urls: list[str]) -> None:
        if not urls:
            return

        semaphore = asyncio.Semaphore(10)
        urls = list(dict.fromkeys(urls))
        kill_event = asyncio.Event()
        self._set_kill_event(kill_event)
        try:
            with requests.Session() as session:
                tasks = [
                    asyncio.create_task(
                        self.download_image(session, url, semaphore, kill_event)
                    )
                    for url in urls
                ]
                probe_task = asyncio.ensure_future(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
                kill_task = asyncio.create_task(kill_event.wait())
                done, _ = await asyncio.wait(
                    [probe_task, kill_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if kill_task in done:
                    self._set_stop_requested(True)
                    for task in tasks:
                        task.cancel()
                    probe_task.cancel()
                    await asyncio.gather(probe_task, return_exceptions=True)
                    return

                kill_task.cancel()
                await asyncio.gather(kill_task, return_exceptions=True)
        finally:
            self._set_kill_event(None)

    def _discover_image_urls(
        self,
        soup: BeautifulSoup,
        page_url: str,
        kill_event: asyncio.Event,
    ) -> list[str]:
        discovered_urls: list[str] = []
        for tag in soup.find_all("img", src=True):
            if self._should_stop(kill_event):
                return discovered_urls
            src = str(tag.get("src", "")).strip()
            image_url = normalize_image_url(src, page_url)
            if not image_url:
                continue
            with self._state_lock:
                if image_url in global_state.image_urls:
                    continue
                global_state.image_urls.append(image_url)
            discovered_urls.append(image_url)
        return discovered_urls

    def _should_stop(self, kill_event: asyncio.Event) -> bool:
        return kill_event.is_set() or self._stop_requested() or self._stop_event.is_set()
