"""The committed recon evidence must not contain session tokens."""

import base64
import re
from pathlib import Path

import pytest

RECON = Path(__file__).resolve().parents[2] / "docs" / "recon"
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
JWT = re.compile(r"eyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]*")

EVIDENCE = sorted(
    path for path in RECON.rglob("*") if path.is_file() and path.suffix not in BINARY_SUFFIXES
)


def count_jwts(path: Path) -> int:
    return len(JWT.findall(path.read_text(encoding="utf-8", errors="ignore")))


def encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_recon_evidence_is_found() -> None:
    assert any(path.suffix == ".html" for path in EVIDENCE)


@pytest.mark.parametrize("signature", ["c2lnbmF0dXJl", ""], ids=["signed", "unsigned"])
def test_scanner_finds_a_synthetic_jwt(tmp_path, signature) -> None:
    token = f"{encode('{"alg":"HS256"}')}.{encode('{"sub":"example"}')}.{signature}"
    capture = tmp_path / "capture.har"
    capture.write_text(f'{{"jwt":"{token}"}}', encoding="utf-8")
    assert count_jwts(capture) == 1


@pytest.mark.parametrize("path", EVIDENCE, ids=lambda path: str(path.relative_to(RECON)))
def test_recon_file_has_no_jwt(path) -> None:
    count = count_jwts(path)
    assert count == 0, f"{path} contains {count} JWT(s); replace each one with REDACTED"
