"""Shared test fixtures: a throwaway workspace with the example prototype in it."""

import shutil
from pathlib import Path

import pytest

from protoreel.workspace import Workspace

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture
def workspace(tmp_path) -> Workspace:
    shutil.copy(EXAMPLES / "like-button.html", tmp_path / "like-button.html")
    return Workspace.open(tmp_path)


@pytest.fixture
def quick_script() -> dict:
    """A short script so renders in tests stay fast."""
    return {"start": ["80%", "85%"], "actions": [{"click": "#like", "dur": 150}, {"wait": 100}]}
