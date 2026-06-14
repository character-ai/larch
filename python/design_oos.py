"""Python CLI entrypoints for /design OOS filing helpers.

Ports skills/design/scripts/file-design-oos.sh prepare and annotate verbs.
The annotate step uses $DESIGN_TMPDIR/oos-issue.stdout.txt (stdout handoff from /issue).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


# Contract: the annotate step reads this file and writes oos-issues-created.md.
OOS_ISSUE_STDOUT_FILE = "oos-issue.stdout.txt"


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def _run_cli(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    root = _plugin_root()
    return subprocess.run(
        [sys.executable, str(root / "python" / "cli.py"), *args],
        capture_output=capture, text=True, check=False,
    )


def _emit_kv(key: str, value: str) -> None:
    print(f"{key}={value}")


def file_oos_prepare_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    design_tmpdir_str = os.environ.get("DESIGN_TMPDIR", "")
    for i, a in enumerate(argv):
        if a == "--design-tmpdir" and i + 1 < len(argv):
            design_tmpdir_str = argv[i + 1]
    if not design_tmpdir_str:
        print("design file-oos-prepare: DESIGN_TMPDIR unset", file=sys.stderr)
        return 2
    d = Path(design_tmpdir_str)
    if not d.is_dir():
        print("design file-oos-prepare: DESIGN_TMPDIR not a directory", file=sys.stderr)
        return 2

    sent = d / "oos-issues-created.md"
    acc = d / "oos-accepted-design.md"

    # Already filed (sentinel exists and is non-empty)
    if sent.is_file() and sent.stat().st_size > 0:
        _emit_kv("FILE_DESIGN_OOS_STATUS", "skip-sentinel")
        return 0

    # No accepted OOS items
    if not acc.is_file() or acc.stat().st_size == 0:
        _emit_kv("FILE_DESIGN_OOS_STATUS", "skip-no-items")
        return 0

    # Run OOS issue cap check
    cap_result = _run_cli("oos", "issue-cap",
                          "--design-tmpdir", str(d), capture=True)
    if cap_result.returncode != 0:
        _emit_kv("FILE_DESIGN_OOS_STATUS", "cap-error")
        print(cap_result.stderr or "", end="", file=sys.stderr)
        return 1

    # Emit the stdout path so the wrapper can pass it to /issue
    _emit_kv("OOS_ISSUE_STDOUT_PATH", str(d / OOS_ISSUE_STDOUT_FILE))
    _emit_kv("FILE_DESIGN_OOS_STATUS", "ok")
    return 0


def file_oos_annotate_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    design_tmpdir_str = os.environ.get("DESIGN_TMPDIR", "")
    issue_stdout_file = ""
    for i, a in enumerate(argv):
        if a == "--design-tmpdir" and i + 1 < len(argv):
            design_tmpdir_str = argv[i + 1]
        elif a == "--issue-stdout-file" and i + 1 < len(argv):
            issue_stdout_file = argv[i + 1]
    if not design_tmpdir_str:
        print("design file-oos-annotate: DESIGN_TMPDIR unset", file=sys.stderr)
        return 2
    d = Path(design_tmpdir_str)
    if not d.is_dir():
        print("design file-oos-annotate: DESIGN_TMPDIR not a directory", file=sys.stderr)
        return 2

    # Default stdout file path
    if not issue_stdout_file:
        issue_stdout_file = str(d / OOS_ISSUE_STDOUT_FILE)

    stdout_path = Path(issue_stdout_file)
    if not stdout_path.is_file() or stdout_path.stat().st_size == 0:
        _emit_kv("STEP5B_STATUS", "annotate-failed")
        print(f"design file-oos-annotate: issue-stdout-file empty or missing ({issue_stdout_file})",
              file=sys.stderr)
        return 1

    # Parse issue URLs from stdout
    issue_stdout = stdout_path.read_text(encoding="utf-8")
    urls: list[str] = []
    for line in issue_stdout.splitlines():
        m = re.search(r"https://github\.com/[^/]+/[^/]+/issues/\d+", line)
        if m:
            urls.append(m.group(0))

    # Write oos-issues-created.md sentinel
    sent = d / "oos-issues-created.md"
    with sent.open("w", encoding="utf-8") as fh:
        for url in urls:
            fh.write(url + "\n")  # pyright: ignore[reportUnusedCallResult]

    _emit_kv("STEP5B_STATUS", "ok")
    return 0
