.PHONY: check format lint types test read read-all read-tuta read-interia read-recovery read-email read-json read-secrets

check: format lint types test

format:
	uv run ruff format --check .

lint:
	uv run ruff check .

types:
	uv run ty check

test:
	uv run pytest

# Read the account database (data/sqlite.db). Pass ARGS for extra flags.
read: read-all

read-all:
	uv run dispmail read $(ARGS)

read-tuta:
	uv run dispmail read --platform tuta $(ARGS)

read-interia:
	uv run dispmail read --platform interia $(ARGS)

read-recovery:
	uv run dispmail read --recovery yes $(ARGS)

read-email:
	@test -n "$(RE)" || (echo "usage: make read-email RE='<regex>'"; exit 2)
	uv run dispmail read --email-regex "$(RE)" $(ARGS)

read-json:
	uv run dispmail read --json $(ARGS)

read-secrets:
	uv run dispmail read --show-passwords $(ARGS)
