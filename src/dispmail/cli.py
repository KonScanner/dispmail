"""Command line entry point: list, doctor and the two provider paths."""

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, replace
from pathlib import Path
from random import Random

from dispmail.accounts import AccountRepository
from dispmail.browser import HttpEgressProbe, open_browser
from dispmail.doctor import exit_code_for, run_checks
from dispmail.flows import FlowResult, FlowRunner, ProviderSpec, TerminalConfirmation
from dispmail.ledger import Ledger
from dispmail.providers import BUILDERS
from dispmail.providers.tuta import DOMAINS
from dispmail.settings import ExitCode, Settings, persona_for

logger = logging.getLogger(__name__)

PROVIDER_NAMES = tuple(BUILDERS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dispmail",
        description="Create a disposable mailbox without giving away personal data.",
    )
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show providers, plans and domains")

    doctor = sub.add_parser("doctor", help="check the environment and egress configuration")
    doctor.add_argument("--json", action="store_true", dest="as_json")

    read = sub.add_parser("read", help="query data/sqlite.db")
    read.add_argument("--platform", choices=PROVIDER_NAMES)
    read.add_argument("--email", help="exact address")
    read.add_argument("--email-regex", help="regular expression over the address")
    read.add_argument("--recovery", choices=("any", "yes", "no"))
    read.add_argument("--since", help="ISO timestamp lower bound")
    read.add_argument("--limit", type=_positive_int)
    read.add_argument("--data-dir", type=Path)
    read.add_argument("--json", action="store_true", dest="as_json")
    read.add_argument(
        "--show-passwords",
        action="store_true",
        help="print the real passwords (default: masked)",
    )

    for name in PROVIDER_NAMES:
        provider = sub.add_parser(name, help=f"run the {name} signup path")
        _add_run_arguments(provider, name)

    return parser


def _add_run_arguments(parser: argparse.ArgumentParser, name: str) -> None:
    parser.add_argument(
        "--submit", action="store_true", default=None, help="really create the account"
    )
    parser.add_argument(
        "--headed", action="store_true", default=None, help="show the browser window"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        default=None,
        help="ask before recording the account",
    )
    parser.add_argument(
        "--assisted",
        action="store_true",
        default=None,
        help="wait for a human to clear captcha/verification in the window (needs --headed)",
    )
    parser.add_argument(
        "--accept-attestation",
        action="store_true",
        default=None,
        help="confirm you own no other free account on this provider (required for live)",
    )
    parser.add_argument(
        "--replace-account",
        action="store_true",
        default=None,
        help="ignore the weekly limit (use when an old account is gone)",
    )
    parser.add_argument(
        "--show-passwords",
        action="store_true",
        default=None,
        help="include the real password/recovery in --json output",
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--assist-timeout", type=float)
    parser.add_argument("--weekly-limit", type=_positive_int)
    parser.add_argument("--username-timeout", type=float)
    parser.add_argument(
        "--ignore-cooldown",
        action="store_true",
        default=None,
        help="start the run even if this egress is cooling down",
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--artifacts-dir", type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--egress-name")
    parser.add_argument("--egress-country")
    parser.add_argument("--egress-asn", type=int)
    parser.add_argument("--home-ip")
    parser.add_argument("--proxy-server")
    parser.add_argument("--proxy-username")
    parser.add_argument("--proxy-password", help="prefer DISPMAIL_PROXY_PASSWORD")
    parser.add_argument("--json", action="store_true", dest="as_json")
    if name == "tuta":
        parser.add_argument("--domain", choices=DOMAINS, default="tutamail.com")
    if name == "interia":
        parser.add_argument("--consents", choices=("required", "all"), default="required")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if args.command == "list":
        _print_providers()
        return int(ExitCode.OK)
    settings = _settings_from_args(args)
    if args.command == "doctor":
        return _doctor(settings, as_json=args.as_json)
    if args.command == "read":
        return _read(args, settings)
    if args.command not in BUILDERS:
        parser.error(f"unknown provider {args.command!r}")
    return _run(args, settings)


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        msg = f"{raw!r} must be at least 1"
        raise argparse.ArgumentTypeError(msg)
    return value


def _settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    overrides: dict[str, object] = {}
    seed = getattr(args, "seed", None)
    if seed is not None:
        overrides["seed"] = seed
    headed = getattr(args, "headed", None)
    if headed is not None:
        overrides["headless"] = not headed
    for flag, field_name in (
        ("submit", "submit"),
        ("manual", "manual"),
        ("assisted", "assisted"),
        ("accept_attestation", "accept_attestation"),
        ("replace_account", "replace_account"),
        ("ignore_cooldown", "ignore_cooldown"),
    ):
        value = getattr(args, flag, None)
        if value is not None:
            overrides[field_name] = value
    argument_to_field = {
        "timeout": "timeout",
        "assist_timeout": "assist_timeout",
        "weekly_limit": "weekly_limit",
        "username_timeout": "username_timeout",
        "data_dir": "data_dir",
        "artifacts_dir": "artifacts_dir",
        "state_dir": "state_dir",
    }
    for argument, field_name in argument_to_field.items():
        value = getattr(args, argument, None)
        if value is not None:
            overrides[field_name] = value
    egress = replace(
        settings.egress,
        name=getattr(args, "egress_name", None) or settings.egress.name,
        expect_country=getattr(args, "egress_country", None) or settings.egress.expect_country,
        expect_asn=getattr(args, "egress_asn", None)
        if getattr(args, "egress_asn", None) is not None
        else settings.egress.expect_asn,
        proxy_server=getattr(args, "proxy_server", None) or settings.egress.proxy_server,
        proxy_username=getattr(args, "proxy_username", None) or settings.egress.proxy_username,
        proxy_password=getattr(args, "proxy_password", None) or settings.egress.proxy_password,
    )
    overrides["egress"] = egress
    if getattr(args, "home_ip", None):
        overrides["home_ip"] = args.home_ip
    return replace(settings, **overrides)


def _build_spec(args: argparse.Namespace, settings: Settings) -> ProviderSpec:
    if args.command == "tuta":
        return BUILDERS["tuta"](
            domain=args.domain,
            username_timeout=settings.username_timeout,
        )
    return BUILDERS["interia"](consents=args.consents)


def _run(args: argparse.Namespace, settings: Settings) -> int:
    spec = _build_spec(args, settings)
    if settings.submit and spec.needs_attestation and not settings.accept_attestation:
        _emit("error: this provider needs --accept-attestation for a live run", as_json=False)
        return int(ExitCode.USAGE)
    if settings.assisted and settings.headless:
        _emit("error: --assisted needs --headed", as_json=False)
        return int(ExitCode.USAGE)
    if settings.submit and spec.name == "interia" and not settings.assisted:
        _emit(
            "error: Interia live signup ends in a captcha/SMS step; add --assisted --headed",
            as_json=False,
        )
        return int(ExitCode.USAGE)

    rng = Random(settings.seed) if settings.seed is not None else Random()
    persona = persona_for(settings.egress.expect_country, rng)
    browser = open_browser(settings, persona, locale=spec.locale)
    store = AccountRepository(settings.data_dir)
    runner = FlowRunner(
        browser,
        settings,
        HttpEgressProbe(),
        store,
        Ledger(settings.state_dir),
        TerminalConfirmation() if settings.manual else None,
        persona_label=f"{persona.locale}/{persona.timezone}",
    )
    try:
        result = runner.run(spec, rng=rng)
    finally:
        browser.close()
    _emit_result(
        result,
        as_json=args.as_json,
        settings=settings,
        show_passwords=bool(args.show_passwords),
    )
    return int(result.exit_code)


MASK = "********"


def _read(args: argparse.Namespace, settings: Settings) -> int:
    repository = AccountRepository(settings.data_dir)
    try:
        rows = repository.find(
            platform=args.platform,
            email=args.email,
            email_regex=args.email_regex,
            recovery=args.recovery,
            since=args.since,
            limit=args.limit,
        )
    except re.error as exc:
        _emit(f"invalid --email-regex: {exc}", as_json=args.as_json)
        return int(ExitCode.USAGE)
    except ValueError as exc:
        _emit(f"invalid filter: {exc}", as_json=args.as_json)
        return int(ExitCode.USAGE)
    if args.as_json:
        payload = []
        for row in rows:
            recovery_path = row.recovery_path(settings.data_dir)
            payload.append(
                {
                    "id": row.id,
                    "email": row.email,
                    "password": row.password if args.show_passwords else MASK,
                    "recovery": (
                        row.recovery if args.show_passwords else (MASK if row.recovery else None)
                    ),
                    "recovery_file": str(recovery_path) if recovery_path else None,
                    "platform": row.platform,
                    "created_at": row.created_at,
                    "egress": row.egress,
                }
            )
        print(json.dumps(payload, indent=2))
        return int(ExitCode.OK)
    if not rows:
        print("no accounts")
        return int(ExitCode.OK)
    print(f"{'platform':8} {'email':40} {'password':12} {'recovery':8} {'created':20}")
    for row in rows:
        password = row.password if args.show_passwords else MASK
        recovery = "yes" if row.recovery else "-"
        print(f"{row.platform:8} {row.email:40} {password:12} {recovery:8} {row.created_at:20}")
    return int(ExitCode.OK)


def _doctor(settings: Settings, *, as_json: bool) -> int:
    checks = run_checks(settings)
    if as_json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        for check in checks:
            marker = "ok" if check.ok else "FAIL"
            print(f"[{marker:4}] {check.name:12} {check.detail}")
    return int(exit_code_for(checks))


def _print_providers() -> None:
    for name, builder in BUILDERS.items():
        spec = builder()
        domains = ", ".join(spec.domains) if spec.domains else spec.email_domain
        print(f"{name:8} {spec.url}")
        print(f"         plans={','.join(spec.plans)} domains={domains}")
        print(f"         live requires attestation: {spec.needs_attestation}")
        if name == "interia":
            print("         live is assisted: captcha + SMS/mail verification need a human")


def _emit_result(
    result: FlowResult,
    *,
    as_json: bool,
    settings: Settings,
    show_passwords: bool = False,
) -> None:
    if as_json:
        payload = asdict(result)
        payload["exit_code"] = int(result.exit_code)
        payload["artifacts"] = str(result.artifacts) if result.artifacts else None
        account_payload = asdict(result.account) if result.account else None
        if account_payload and not show_passwords:
            account_payload["password"] = MASK
            account_payload["recovery"] = MASK if account_payload["recovery"] else None
        payload["account"] = account_payload
        print(json.dumps(payload, indent=2))
        return
    status = "ok" if result.ok else "failed"
    print(f"{status}: {result.provider} {result.outcome} ({result.exit_code.name})")
    if result.detail:
        print(f"  {result.detail}")
    if result.account:
        print(f"  account: {result.account.email}")
        if result.account.recovery:
            print(f"  recovery: saved under {settings.data_dir}")
    if result.egress:
        print(f"  egress: {result.egress.ip} {result.egress.country} {result.egress.org}")
    if result.artifacts:
        print(f"  artifacts: {result.artifacts}")


def _emit(message: str, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
