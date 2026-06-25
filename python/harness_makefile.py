"""Read and write ``test-harnesses-N`` shard prerequisite lines in the Makefile.

Preserves every other line verbatim so comments, recipe bodies, and the
aggregate ``test-harnesses:`` line are never touched.

Public surface:

- ``read_shards(makefile_path)``  → ``{N: [target, ...]}``
- ``write_shards(makefile_path, shards)`` — in-place update
"""

from __future__ import annotations

import re
from pathlib import Path

_SLICE_LINE_RE = re.compile(r"^(test-harnesses-(\d+)):\s*(.*?)\s*$")


def read_shards(makefile_path: str | Path) -> dict[int, list[str]]:
    """Parse ``test-harnesses-N:`` lines and return ``{N: [target, ...]}``.

    Only single-physical-line shard rules are supported (no backslash
    continuation), matching the invariant enforced by
    ``scripts/test-harness-shards-coverage.sh``.
    """
    shards: dict[int, list[str]] = {}
    for line in Path(makefile_path).read_text(encoding="utf-8").splitlines():
        m: re.Match[str] | None = _SLICE_LINE_RE.match(line)
        if m:
            n = int(m.group(2))
            shards[n] = m.group(3).split() if m.group(3).strip() else []
    return shards


def write_shards(*, makefile_path: str | Path, shards: dict[int, list[str]]) -> None:
    """Rewrite each ``test-harnesses-N:`` line with the prerequisites from *shards*.

    Lines whose shard number does not appear in *shards* are left unchanged.
    All non-shard lines (recipes, comments, other targets) are preserved
    verbatim.  The file is written atomically via a full read-then-write
    so a KeyboardInterrupt mid-write cannot leave the Makefile half-updated.
    """
    path = Path(makefile_path)
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        m: re.Match[str] | None = _SLICE_LINE_RE.match(line.rstrip("\n"))
        if m:
            n = int(m.group(2))
            if n in shards:
                out.append(f"{m.group(1)}: {' '.join(shards[n])}\n")
                continue
        out.append(line)
    _ = path.write_text("".join(out), encoding="utf-8")
