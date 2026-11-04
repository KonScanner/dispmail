"""Flow engine: dry-run gate, success detection, taxonomy and budget rules."""

import stat
from random import Random

import pytest

from dispmail.accounts import Account, AccountRepository
from dispmail.browser import EgressMismatchError, StepTimeoutError
from dispmail.credentials import generate
from dispmail.flows import FlowRunner
from dispmail.ledger import Ledger, attempt, run_lock
from dispmail.providers import interia, tuta
from dispmail.settings import ExitCode
from tests.fakes import FakeBrowser, FakeProbe, ScriptedConfirmation, make_settings


def _runner(settings, browser, probe=None, confirm=None):
    return FlowRunner(
        browser,
        settings,
        probe or FakeProbe(),
        AccountRepository(settings.data_dir),
        Ledger(settings.state_dir),
        confirm,
    )


def test_dry_run_stops_before_submit(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "dry-run"
    assert ("click", tuta.CREATE.selector) not in browser.actions
    assert AccountRepository(settings.data_dir).count() == 0


def test_live_tuta_creates_and_records_account(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True)
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    browser.texts["xpath=//body"] = (
        "fa54 7805 6b94 bfca 4d3c 56dd 14f7 6b84 a4b2 d777 c443 fdde 18d7 6017 5b70 0c74"
    )
    credentials = generate(rng=Random(7))
    result = _runner(settings, browser).run(tuta.build(username_timeout=0), credentials=credentials)
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "created"
    assert result.account is not None
    rows = AccountRepository(settings.data_dir).find()
    assert len(rows) == 1
    assert rows[0].email == f"{credentials.username}@tutamail.com"
    assert rows[0].password == credentials.password
    assert rows[0].recovery == (
        "fa54 7805 6b94 bfca 4d3c 56dd 14f7 6b84 a4b2 d777 c443 fdde 18d7 6017 5b70 0c74"
    )
    assert rows[0].platform == "tuta"
    recovery_path = rows[0].recovery_path(settings.data_dir)
    assert recovery_path is not None
    assert recovery_path.read_text(encoding="utf-8").strip().startswith("fa54 7805")


def test_live_requires_attestation(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True)
    browser = FakeBrowser()
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.USAGE
    assert result.outcome == "attestation-required"
    assert ("goto", tuta.SIGNUP_URL) not in browser.actions


def test_egress_mismatch_stops_before_the_provider(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    probe = FakeProbe(facts=None)
    probe.facts = probe.facts.__class__(
        ip="198.51.100.1", country="PL", asn=1, org="Other", source="fake"
    )
    result = _runner(settings, browser, probe=probe).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.EGRESS_MISMATCH
    assert ("goto", tuta.SIGNUP_URL) not in browser.actions


def test_probe_failure_is_an_egress_mismatch(tmp_path) -> None:
    settings = make_settings(tmp_path)
    result = _runner(
        settings,
        FakeBrowser(),
        probe=FakeProbe(error=EgressMismatchError("probe down")),
    ).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.EGRESS_MISMATCH


def test_timeout_is_provider_changed(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    browser.fail_on[tuta.CONTINUE.selector] = StepTimeoutError("selector gone")
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.PROVIDER_CHANGED
    assert result.artifacts is not None


def test_live_challenge_sets_cooldown_and_blocks_second_run(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True)
    browser = FakeBrowser()
    browser.content_value = "Kod jest wymagany"
    spec = interia.build()
    first = _runner(settings, browser).run(spec)
    assert first.exit_code is ExitCode.CHALLENGE
    second = _runner(settings, FakeBrowser()).run(spec)
    assert second.exit_code is ExitCode.BUDGET
    assert "cooling down" in second.detail


def test_dry_run_challenge_does_not_set_a_cooldown(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    browser.content_value = "Kod jest wymagany"
    spec = interia.build()
    first = _runner(settings, browser).run(spec)
    assert first.exit_code is ExitCode.CHALLENGE
    assert not any(entry.challenged for entry in Ledger(settings.state_dir).read())
    again = FakeBrowser()
    again.content_value = "Kod jest wymagany"
    second = _runner(settings, again).run(spec)
    assert second.exit_code is ExitCode.CHALLENGE


def test_cooldown_can_be_ignored(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, ignore_cooldown=True)
    browser = FakeBrowser()
    browser.content_value = "Kod jest wymagany"
    spec = interia.build()
    assert _runner(settings, browser).run(spec).exit_code is ExitCode.CHALLENGE
    again = FakeBrowser()
    again.content_value = "Kod jest wymagany"
    retry = _runner(settings, again).run(spec)
    assert retry.exit_code is ExitCode.CHALLENGE


def test_weekly_limit_is_enforced(tmp_path) -> None:
    settings = make_settings(tmp_path)
    ledger = Ledger(settings.state_dir)
    for _ in range(4):
        ledger.record(attempt("tuta", "test", "created", 0))
    result = FlowRunner(
        FakeBrowser(), settings, FakeProbe(), AccountRepository(settings.data_dir), ledger
    ).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.BUDGET
    assert "4 accounts" in result.detail


def test_replacement_allows_a_run_over_the_limit(tmp_path) -> None:
    settings = make_settings(tmp_path, replace_account=True)
    ledger = Ledger(settings.state_dir)
    for _ in range(4):
        ledger.record(attempt("tuta", "test", "created", 0))
    result = FlowRunner(
        FakeBrowser(), settings, FakeProbe(), AccountRepository(settings.data_dir), ledger
    ).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "dry-run"


def test_concurrent_run_is_refused(tmp_path) -> None:
    settings = make_settings(tmp_path)
    with run_lock(settings.state_dir):
        result = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.BUDGET
    assert "lock" in result.detail


def test_manual_rejection_does_not_record(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, manual=True)
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    confirmation = ScriptedConfirmation([False])
    result = _runner(settings, browser, confirm=confirmation).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.REJECTED
    assert result.outcome == "manual-rejected"
    assert AccountRepository(settings.data_dir).count() == 0


def test_existing_account_is_not_overwritten(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, replace_account=True)
    credentials = generate(rng=Random(9))
    repository = AccountRepository(settings.data_dir)
    repository.add(Account(f"{credentials.username}@tutamail.com", "old"), platform="tuta")
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    result = _runner(settings, browser).run(tuta.build(username_timeout=0), credentials=credentials)
    assert result.exit_code is ExitCode.EXISTS
    assert repository.find()[0].password == "old"


def test_interia_dry_run_reaches_the_submit_gate(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    result = _runner(settings, browser).run(interia.build(consents="required"))
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "dry-run"
    assert ("click", interia.SUBMIT.selector) not in browser.actions


@pytest.mark.parametrize("consents", ["required", "all"])
def test_interia_consent_strategies(tmp_path, consents: str) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    result = _runner(settings, browser).run(interia.build(consents=consents))
    assert result.exit_code is ExitCode.OK
    assert ("click", interia.SUBMIT.selector) not in browser.actions


def test_no_success_after_submit_is_rejected(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, submit_timeout=0.05)
    result = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.REJECTED
    assert result.outcome == "rejected"


def test_unexpected_exception_is_a_flow_error(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    browser.fail_on[tuta.CONTINUE.selector] = RuntimeError("boom")
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.FLOW_ERROR
    assert result.outcome == "flow-error"


def test_assisted_mode_waits_for_a_cleared_challenge(tmp_path) -> None:
    settings = make_settings(tmp_path, assisted=True, headless=False, assist_timeout=0.1)
    browser = FakeBrowser()
    browser.content_sequence = ["Kod jest wymagany", "clean"]
    result = _runner(settings, browser).run(interia.build())
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "dry-run"


def test_a_blocking_challenge_beats_a_selector_timeout(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    browser.fail_on[tuta.CONTINUE.selector] = StepTimeoutError("click blocked")
    browser.content_value = "Verify you are human"
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.CHALLENGE
    assert result.outcome == "challenge"


def test_database_inventory_blocks_a_run_over_the_limit(tmp_path) -> None:
    settings = make_settings(tmp_path, weekly_limit=1)
    repository = AccountRepository(settings.data_dir)
    repository.add(Account("existing@tutamail.com", "pw"), platform="tuta")
    result = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.BUDGET
    assert "last 7 days" in result.detail
    assert repository.find()[0].email == "existing@tutamail.com"


def test_one_recorded_account_still_allows_another_run(tmp_path) -> None:
    settings = make_settings(tmp_path)
    repository = AccountRepository(settings.data_dir)
    repository.add(Account("existing@tutamail.com", "pw"), platform="tuta")
    result = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "dry-run"


def test_recovery_failure_still_records_the_account(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True)
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    browser.fail_on["xpath=//body"] = RuntimeError("recovery page broken")
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.OK
    assert result.account is not None
    assert result.account.recovery is None
    assert AccountRepository(settings.data_dir).count() == 1


def test_submit_time_challenge_is_classified_as_challenge(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, submit_timeout=0.1)
    browser = FakeBrowser()
    browser.content_value = "Verify you are human"
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.CHALLENGE
    ledger = Ledger(settings.state_dir)
    assert any(entry.challenged for entry in ledger.read())


def test_timeout_artifact_directory_exists(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    browser.fail_on[tuta.CONTINUE.selector] = StepTimeoutError("selector gone")
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.artifacts is not None
    assert (result.artifacts / "fill-account-timeout.png").exists() or (
        result.artifacts / "select-free-plan-timeout.png"
    ).exists()


def test_pending_credentials_survive_a_failed_detection(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, submit_timeout=0.1)
    result = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.REJECTED
    pending = list((tmp_path / "data").glob("pending_*.txt"))
    assert len(pending) == 1
    assert ":" in pending[0].read_text(encoding="utf-8")
    assert stat.S_IMODE(pending[0].stat().st_mode) == 0o600
    assert AccountRepository(settings.data_dir).count() == 0


def test_pending_credentials_are_removed_after_success(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True)
    browser = FakeBrowser()
    browser.url_after_click[tuta.CREATE.selector] = "https://app.tuta.com/mail"
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.OK
    assert list((tmp_path / "data").glob("pending_*.txt")) == []


def test_dry_run_leaves_no_pending_credentials(tmp_path) -> None:
    settings = make_settings(tmp_path)
    _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert list((tmp_path / "data").glob("pending_*.txt")) == []


def test_provider_failure_text_is_classified_quickly(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, submit_timeout=30)
    browser = FakeBrowser()
    browser.content_value = "Could not reach server, looks like you are offline."
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.REJECTED
    assert result.outcome == "provider-error"
    assert "Could not reach server" in result.detail
    assert list((tmp_path / "data").glob("pending_*.txt"))


def test_tuta_recovery_pattern_normalises_the_code(tmp_path) -> None:
    browser = FakeBrowser()
    browser.texts["xpath=//body"] = (
        "Your unique 64-character recovery code:\n"
        "FA54 7805 6B94 BFCA\n4D3C 56DD 14F7 6B84\n"
        "A4B2 D777 C443 FDDE\n18D7 6017 5B70 0C74\n"
    )
    code = tuta._recovery(browser)
    assert code == (
        "fa54 7805 6b94 bfca 4d3c 56dd 14f7 6b84 a4b2 d777 c443 fdde 18d7 6017 5b70 0c74"
    )


def test_ip_block_is_classified_and_cools_the_egress(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True, accept_attestation=True, submit_timeout=0.1)
    browser = FakeBrowser()
    browser.content_value = (
        "Registration is temporarily blocked for your IP address to avoid abuse."
    )
    result = _runner(settings, browser).run(tuta.build(username_timeout=0))
    assert result.exit_code is ExitCode.BLOCKED
    assert result.outcome == "blocked"
    entries = Ledger(settings.state_dir).read()
    assert any(entry.blocked for entry in entries)
    second = _runner(settings, FakeBrowser()).run(tuta.build(username_timeout=0))
    assert second.exit_code is ExitCode.BUDGET
    assert "cooling down" in second.detail


def test_taken_username_falls_back_to_an_alternative(tmp_path) -> None:
    class TakenFirst(FakeBrowser):
        def __init__(self, taken: str) -> None:
            super().__init__()
            self.taken = taken
            self.last_value = ""

        def fill(self, locator, value, *, timeout=None) -> None:
            super().fill(locator, value, timeout=timeout)
            self.last_value = value

        def content(self) -> str:
            if self.last_value == self.taken:
                return "Email address is not available."
            return "Email address is available."

    credentials = generate(rng=Random(11))
    browser = TakenFirst(credentials.username)
    chosen = tuta._choose_username(browser, credentials, 0.3)
    assert chosen.username == credentials.alternatives[0]
    assert chosen.alternatives == ()


def test_interia_checks_every_required_consent(tmp_path) -> None:
    settings = make_settings(tmp_path)
    browser = FakeBrowser()
    _runner(settings, browser).run(interia.build(consents="required"))
    clicked = " ".join(selector for action, selector in browser.actions if action == "click")
    for name in interia.REQUIRED_CONSENTS:
        assert name in clicked


def test_interia_success_is_the_login_redirect(tmp_path) -> None:
    settings = make_settings(tmp_path, submit=True)
    browser = FakeBrowser()
    browser.url_after_click[interia.SUBMIT.selector] = "https://poczta.interia.pl/logowanie/"
    result = _runner(settings, browser).run(interia.build())
    assert result.exit_code is ExitCode.OK
    assert result.outcome == "created"
    rows = AccountRepository(settings.data_dir).find()
    assert len(rows) == 1
    assert rows[0].platform == "interia"
    assert list((settings.data_dir).glob("pending_*.txt")) == []
