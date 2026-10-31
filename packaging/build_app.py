"""Build a platform-native, bundled wikiSpyder application with PyInstaller."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image
from PyInstaller.__main__ import run


ROOT = Path(__file__).resolve().parents[1]
DATA_SEPARATOR = os.pathsep


def macos_icon() -> Path:
    """Convert the source ICO to the iconset required by macOS bundles."""
    iconset = ROOT / "build" / "wikiSpyder.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    source = Image.open(ROOT / "assets" / "wikiSpyder.ico").convert("RGBA")
    for size in (16, 32, 64, 128, 256, 512):
        for scale in (1, 2):
            pixel_size = size * scale
            if pixel_size > 1024:
                continue
            filename = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
            source.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS).save(
                iconset / filename
            )
    output = ROOT / "build" / "wikiSpyder.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(output)],
        check=True,
    )
    return output


def main() -> None:
    icon = ROOT / "assets" / "wikiSpyder.ico"
    if sys.platform == "darwin":
        icon = macos_icon()
    elif sys.platform != "win32":
        icon = None

    arguments = [
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name=wikiSpyder",
    ]
    if icon is not None:
        arguments.append(f"--icon={icon}")
    arguments.extend(
        [
            f"--add-data={ROOT / 'assets' / 'wikiSpyder.ico'}{DATA_SEPARATOR}assets",
            f"--add-data={ROOT / 'wikiSpyder.qss'}{DATA_SEPARATOR}.",
            f"--specpath={ROOT / 'build' / 'pyinstaller'}",
            f"--distpath={ROOT / 'dist'}",
            f"--workpath={ROOT / 'build' / 'pyinstaller'}",
            str(ROOT / "__main__.py"),
        ]
    )
    run(
        arguments
    )


if __name__ == "__main__":
    main()
