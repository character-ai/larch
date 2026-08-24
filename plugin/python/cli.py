"""Temporary entry-point shim for the empty ``larch.cli`` dispatcher."""

from __future__ import annotations

import sys

import larch.cli as _cli

# When imported as a module (`import cli`), redirect to the canonical location
# so tests that access cli._REGISTRY, cli._MACHINE_STDOUT_KEYS, etc. work.
if __name__ != "__main__":
    sys.modules[__name__] = _cli

if __name__ == "__main__":
    raise SystemExit(_cli.main())
