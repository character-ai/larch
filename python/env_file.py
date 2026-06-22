"""Shared shell-style ``KEY=value`` env-file parser.

Single source of truth for the lenient env-file reader used by ``cleanup_skill``
and ``progress_report``; keeping one copy avoids re-introducing a duplicate-code
run (pylint R0801) across those modules.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

_ENV_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a shell-style env file into a ``dict``.

    Skips blank/comment lines, strips a leading ``export ``, validates each key
    against ``^[A-Z_][A-Z0-9_]*$``, and shell-splits the value (a single token is
    unquoted; a multi-token RHS is preserved verbatim). An unreadable file yields
    an empty dict.
    """
    data: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return data
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not _ENV_KEY_RE.match(key):
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = [value]
        data[key] = parsed[0] if len(parsed) == 1 else value
    return data
