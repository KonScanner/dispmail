"""Contract fixtures: a saved snapshot and the locators expected in it."""

from dataclasses import dataclass
from pathlib import Path

from dispmail.browser import Locator


@dataclass(frozen=True, slots=True)
class Contract:
    """One recon snapshot plus the locators that must resolve inside it."""

    name: str
    snapshot: Path
    locators: tuple[Locator, ...]
