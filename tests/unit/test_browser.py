"""Egress probe parsing and the fail-closed verdict."""

import pytest

from dispmail.browser import EgressFacts, EgressMismatchError, HttpEgressProbe, verify_egress
from dispmail.settings import EgressSpec

CF = "fl=1\nh=cloudflare\nip=203.0.113.7\nts=1\nloc=PL\n"
IPINFO = '{"ip": "203.0.113.7", "country": "PL", "org": "AS20473 Example Hosting"}'
EMPTY = ""


class ProbeBrowser:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.url = ""

    def goto(self, url: str) -> None:
        self.url = url

    def content(self) -> str:
        return self.pages.get(self.url, EMPTY)


def _browser(cloudflare: str, ipinfo: str) -> ProbeBrowser:
    return ProbeBrowser(
        {
            "https://www.cloudflare.com/cdn-cgi/trace": cloudflare,
            "https://ipinfo.io/json": ipinfo,
        }
    )


def test_probe_merges_asn_from_the_second_endpoint() -> None:
    facts = HttpEgressProbe().check(_browser(CF, IPINFO))
    assert facts.ip == "203.0.113.7"
    assert facts.country == "PL"
    assert facts.asn == 20473
    assert facts.org == "Example Hosting"
    assert facts.source == "cloudflare+ipinfo"


def test_probe_falls_back_to_ipinfo_alone() -> None:
    facts = HttpEgressProbe().check(_browser(EMPTY, IPINFO))
    assert facts.asn == 20473
    assert facts.country == "PL"
    assert facts.source == "ipinfo"


def test_probe_keeps_country_when_asn_is_unavailable() -> None:
    facts = HttpEgressProbe().check(_browser(CF, EMPTY))
    assert facts.asn is None
    verify_egress(EgressSpec(expect_country="PL"), facts)


def test_probe_refuses_divergent_endpoints() -> None:
    ipinfo = '{"ip": "198.51.100.9", "country": "GR", "org": "AS64500 Other"}'
    with pytest.raises(EgressMismatchError, match="disagree"):
        HttpEgressProbe().check(_browser(CF, ipinfo))


def test_probe_fails_closed_when_no_endpoint_answers() -> None:
    with pytest.raises(EgressMismatchError, match="could not determine"):
        HttpEgressProbe().check(_browser(EMPTY, EMPTY))


def test_verdict_country_mismatch() -> None:
    facts = EgressFacts(ip="203.0.113.7", country="PL", asn=20473, org="x", source="fake")
    with pytest.raises(EgressMismatchError, match="country"):
        verify_egress(EgressSpec(expect_country="GR"), facts)


def test_verdict_asn_mismatch() -> None:
    facts = EgressFacts(ip="203.0.113.7", country="PL", asn=20473, org="x", source="fake")
    with pytest.raises(EgressMismatchError, match="AS"):
        verify_egress(EgressSpec(expect_country="PL", expect_asn=64500), facts)


def test_verdict_home_ip_is_refused() -> None:
    facts = EgressFacts(ip="5.55.140.210", country="GR", asn=None, org="", source="fake")
    with pytest.raises(EgressMismatchError, match="home IP"):
        verify_egress(EgressSpec(expect_country="GR"), facts, home_ip="5.55.140.210")


def test_verdict_accepts_a_matching_exit() -> None:
    facts = EgressFacts(ip="203.0.113.7", country="PL", asn=20473, org="x", source="fake")
    verify_egress(EgressSpec(expect_country="PL", expect_asn=20473), facts)
