"""Challenge signatures and detection."""

import logging
from dataclasses import dataclass
from typing import Literal

from dispmail.browser import Browser, css

logger = logging.getLogger(__name__)

SignatureKind = Literal["url", "title", "text", "css"]


@dataclass(frozen=True, slots=True)
class ChallengeSignature:
    """One observable that only appears when a provider is gating the run."""

    kind: SignatureKind
    value: str
    description: str = ""
    frame: str | None = None


GENERIC_CHALLENGES: tuple[ChallengeSignature, ...] = (
    ChallengeSignature("title", "just a moment", "Cloudflare interstitial"),
    ChallengeSignature("css", "#challenge-form", "Cloudflare challenge form"),
    ChallengeSignature("css", "iframe[src*='challenges.cloudflare.com']", "Turnstile widget"),
    ChallengeSignature("text", "verify you are human", "human verification prompt"),
    ChallengeSignature("text", "checking your browser", "browser check prompt"),
)

INTERIA_CHALLENGES: tuple[ChallengeSignature, ...] = (
    ChallengeSignature("css", ".captcha__image", "Interia image captcha"),
    ChallengeSignature("css", ".captcha__input", "Interia captcha input"),
    ChallengeSignature("css", ".captcha__command", "Interia captcha instruction"),
    ChallengeSignature(
        "css",
        "#rc-imageselect",
        "reCAPTCHA image grid",
        frame="iframe[src*='recaptcha'][src*='bframe']",
    ),
    ChallengeSignature(
        "css",
        ".rc-imageselect-desc",
        "reCAPTCHA image instruction",
        frame="iframe[src*='recaptcha'][src*='bframe']",
    ),
    ChallengeSignature("text", "kod jest wymagany", "Interia captcha prompt"),
    ChallengeSignature("text", "kod jest nieprawid", "Interia captcha rejection"),
)

TUTA_CHALLENGES: tuple[ChallengeSignature, ...] = ()


def detect(
    browser: Browser,
    signatures: tuple[ChallengeSignature, ...],
) -> ChallengeSignature | None:
    """Return the first matching signature, or ``None`` for a clean page."""
    for signature in signatures:
        try:
            if signature.kind == "url" and signature.value.lower() in browser.url().lower():
                logger.debug("challenge detected: %s", signature.description)
                return signature
            if signature.kind == "title" and signature.value.lower() in browser.title().lower():
                logger.debug("challenge detected: %s", signature.description)
                return signature
            if signature.kind == "text" and signature.value.lower() in browser.content().lower():
                logger.debug("challenge detected: %s", signature.description)
                return signature
            if signature.kind == "css":
                if signature.frame is not None:
                    found = browser.has_in_frame(signature.frame, signature.value, timeout=0.3)
                else:
                    found = browser.has(css(signature.value), timeout=0.2)
                if found:
                    logger.debug("challenge detected: %s", signature.description)
                    return signature
        except Exception:  # noqa: BLE001 - detection must never crash the flow
            logger.debug("challenge signature %s could not be evaluated", signature)
    return None
