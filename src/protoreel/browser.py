"""Headless Chromium via Playwright, installing it on first use if needed."""

from __future__ import annotations

import os
import subprocess
import sys

INSTALL_HINT = "Run `protoreel setup` (or `python -m playwright install chromium`) and try again."


def install_chromium(quiet: bool = False) -> None:
    """Download Playwright's Chromium (about 150 MB, once per machine)."""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.STDOUT if quiet else None,
    )


async def launch(playwright):
    """Launch Chromium. If the browser has not been downloaded yet, download it once and retry.

    Set PROTOREEL_CHROMIUM to use a Chromium/Chrome binary you already have.
    """
    executable = os.environ.get("PROTOREEL_CHROMIUM") or None
    try:
        return await playwright.chromium.launch(executable_path=executable)
    except Exception as error:
        if executable or "Executable doesn't exist" not in str(error):
            raise
    try:
        install_chromium(quiet=True)
    except Exception as error:
        raise RuntimeError(f"Chromium is not installed and could not be downloaded. {INSTALL_HINT}") from error
    return await playwright.chromium.launch()
