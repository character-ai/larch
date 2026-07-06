from __future__ import annotations

from pathlib import Path

from larch.lint import timing_task_kind_allowlist as allowlist


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_scans_add_argument_defaults_and_or_fallbacks(tmp_path: Path) -> None:
    rel = "python/larch/agents/_drafter.py"
    write(
        tmp_path / rel,
        """
from __future__ import annotations

import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--timing-task-kind", default="new-kind")
parser.add_argument(
    "--timing-task-kind",
    default=os.environ.get("LARCH_TIMING_TASK_KIND", "") or "or-kind",
)
""".strip()
        + "\n",
    )

    found = allowlist.scan_files(tmp_path, [rel])

    assert found["new-kind"] == {rel}
    assert found["or-kind"] == {rel}


def test_missing_allowlist_entries_reports_default_only_literal(tmp_path: Path) -> None:
    rel = "python/larch/agents/_drafter.py"
    write(
        tmp_path / rel,
        """
from __future__ import annotations

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--timing-task-kind", default="new-kind")
""".strip()
        + "\n",
    )

    missing = allowlist.missing_allowlist_entries(tmp_path, [rel], allowed=set())

    assert missing == {"new-kind": [rel]}

