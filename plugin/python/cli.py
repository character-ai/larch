"""Entry-point shim; canonical dispatcher is larch.cli.

Direct-call convention: consumers invoke
    python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]
No .sh shim files, ever. See docs/python-migration.md for the migration playbook.
"""

from __future__ import annotations

import sys

import larch.cli as _cli

# When imported as a module (`import cli`), redirect to the canonical location
# so tests that access cli._REGISTRY, cli._MACHINE_STDOUT_KEYS, etc. work.
if __name__ != "__main__":
    sys.modules[__name__] = _cli

if __name__ == "__main__":
    raise SystemExit(_cli.main())
