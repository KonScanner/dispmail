"""Offline DOM contracts: every locator must resolve in the saved snapshots."""

from pathlib import Path

import pytest
from patchright.sync_api import sync_playwright

from dispmail.providers import CONTRACTS

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def page():
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True, channel="chrome")
    except Exception as exc:  # noqa: BLE001 - any launch failure means skip
        pytest.skip(f"Chrome not available: {exc}")
    context = browser.new_context(java_script_enabled=False)
    context.route("**/*", lambda route: route.abort())
    page = context.new_page()
    yield page
    browser.close()
    playwright.stop()


@pytest.mark.browser
@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda contract: contract.name)
def test_locators_resolve_in_snapshot(page, contract) -> None:
    snapshot = REPO_ROOT / contract.snapshot
    if not snapshot.exists():  # pragma: no cover - recon output is committed
        pytest.skip(f"missing recon snapshot {snapshot}")
    page.set_content(snapshot.read_text(encoding="utf-8"), wait_until="domcontentloaded")
    for locator in contract.locators:
        count = page.locator(locator.selector).count()
        assert count == 1, f"{locator} resolved {count} times in {snapshot}"
