"""Challenge signatures: every kind must be detectable and safe on a clean page."""

from dispmail.challenges import (
    GENERIC_CHALLENGES,
    INTERIA_CHALLENGES,
    ChallengeSignature,
    detect,
)
from tests.fakes import FakeBrowser


def test_url_signature() -> None:
    browser = FakeBrowser()
    browser.url_value = "https://provider.example/challenge"
    assert detect(browser, (ChallengeSignature("url", "/challenge"),)) is not None


def test_title_signature() -> None:
    browser = FakeBrowser()
    browser.title_value = "Just a moment..."
    assert detect(browser, GENERIC_CHALLENGES) is not None


def test_text_signature() -> None:
    browser = FakeBrowser()
    browser.content_value = "<p>Kod jest wymagany</p>"
    assert detect(browser, INTERIA_CHALLENGES) is not None


def test_css_signature() -> None:
    browser = FakeBrowser()
    browser.present.add(".captcha__image")
    assert detect(browser, INTERIA_CHALLENGES) is not None


def test_clean_page_has_no_challenge() -> None:
    browser = FakeBrowser()
    browser.content_value = "<html><body>signup form</body></html>"
    assert detect(browser, INTERIA_CHALLENGES + GENERIC_CHALLENGES) is None


def test_detection_never_raises() -> None:
    class Broken(FakeBrowser):
        def content(self) -> str:
            raise RuntimeError("navigation in progress")

    assert detect(Broken(), (ChallengeSignature("text", "verify"),)) is None
