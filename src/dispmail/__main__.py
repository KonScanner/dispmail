"""Allow ``python -m dispmail``."""

from dispmail.cli import main

raise SystemExit(main())  # pragma: no cover
