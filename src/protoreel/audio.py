"""Prototype sound.

Browsers will not let headless Chromium record its own audio output, so prototypes
that make sound can opt in by exposing one function:

    window.__recorderAudio(startMs, durationMs) -> base64 WAV (or a Promise of one)

It should render the sounds that played between `startMs` and `startMs + durationMs`
on the page's clock (for example by replaying a log of sound events into an
OfflineAudioContext). Protoreel calls it once after the last frame and lays the WAV
under the video. Pages without the function simply produce a silent video.
"""

from __future__ import annotations

import base64


async def page_soundtrack(page, start_ms: float, duration_ms: float) -> tuple[bytes | None, str]:
    """Ask the page for its soundtrack. Returns (wav bytes or None, status message)."""
    try:
        if not await page.evaluate("typeof window.__recorderAudio === 'function'"):
            return None, "none"
        encoded = await page.evaluate("([s, d]) => window.__recorderAudio(s, d)", [start_ms, duration_ms])
        if not encoded:
            return None, "empty"
        return base64.b64decode(encoded), "added"
    except Exception as error:
        return None, f"failed: {error}"
