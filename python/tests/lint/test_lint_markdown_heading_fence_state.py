from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.lint import lint_markdown_heading_fence_state as lint


def _record(
    *,
    file: str = "larch/mod.py",
    qualified_symbol: str = "parse",
    pattern_name: str = "HEADING_RE",
    occurrence: int = 1,
    reason: str = "grandfathered",
) -> dict[str, object]:
    return {
        "file": file,
        "qualified_symbol": qualified_symbol,
        "pattern_name": pattern_name,
        "occurrence": occurrence,
        "reason": reason,
    }


def _write_project(root: Path, *, files: dict[str, str], baseline: object | None) -> None:
    python_dir = root / "python"
    for relpath, source in files.items():
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")
    if baseline is not None:
        _ = (python_dir / lint.BASELINE_FILENAME).write_text(json.dumps(baseline), encoding="utf-8")


VIOLATING = """\
import re

HEADING_RE = re.compile(r"^#{1,6}\\s+")

def parse(text: str) -> None:
    for line in text.splitlines():
        if HEADING_RE.match(line):
            pass
"""

COMPLIANT = """\
import re

HEADING_RE = re.compile(r"^#{1,6}\\s+")

def _balanced_fence_line_indices(lines: list[str]) -> set[int]:
    return set()

def parse(text: str) -> None:
    lines = text.splitlines()
    fenced = _balanced_fence_line_indices(lines)
    for index, line in enumerate(lines):
        in_fence = index in fenced
        if not in_fence and HEADING_RE.match(line):
            pass
"""

UNRELATED = """\
import re

TOKEN_RE = re.compile(r"^[A-Z_]+$")

def parse(text: str) -> None:
    for line in text.splitlines():
        if TOKEN_RE.match(line):
            pass
"""


def test_direct_re_compile_without_fence_is_detected(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(VIOLATING, encoding="utf-8")

    findings = lint.scan_file(path, python_dir=python_dir)
    assert [(f.pattern_name, f.qualified_symbol) for f in findings] == [("HEADING_RE", "parse")]


def test_fence_helper_gating_is_compliant(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(COMPLIANT, encoding="utf-8")

    assert lint.scan_file(path, python_dir=python_dir) == []


def test_inline_fence_helper_and_continue_skip_are_compliant(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\\\s+')\n"
        "def fence_indices(lines: list[str]) -> set[int]:\n"
        "    return set()\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    for index, line in enumerate(lines):\n"
        "        if index in fence_indices(lines):\n"
        "            continue\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n",
        encoding="utf-8",
    )
    assert lint.scan_file(path, python_dir=python_dir) == []


def test_unrelated_boolean_does_not_count_as_fence_guard(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\\\s+')\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        in_fence = False\n"
        "        if not in_fence and HEADING_RE.match(line):\n"
        "            pass\n",
        encoding="utf-8",
    )
    assert [finding.pattern_name for finding in lint.scan_file(path, python_dir=python_dir)] == [
        "HEADING_RE"
    ]


def test_unrelated_regex_ignored(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(UNRELATED, encoding="utf-8")

    assert lint.scan_file(path, python_dir=python_dir) == []


def test_search_over_split_lines_detected(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\\\s')\n"
        "def parse(text: str) -> None:\n"
        "    lines = text.splitlines()\n"
        "    for line in lines:\n"
        "        if HEADING_RE.search(line):\n"
        "            pass\n",
        encoding="utf-8",
    )

    assert [f.pattern_name for f in lint.scan_file(path, python_dir=python_dir)] == ["HEADING_RE"]


def test_scope_excludes_tests_and_vendor(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    for relpath in [
        "larch/test_mod.py",
        "larch/conftest.py",
        "larch/.venv/vendor.py",
        "larch/prod.py",
    ]:
        path = python_dir / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text("import re\n", encoding="utf-8")

    assert [p.relative_to(python_dir).as_posix() for p in lint.iter_source_files(python_dir)] == [
        "larch/prod.py"
    ]


def test_symlink_excluded(tmp_path: Path) -> None:
    python_dir = tmp_path / "python" / "larch"
    python_dir.mkdir(parents=True)
    real = python_dir / "real.py"
    _ = real.write_text(VIOLATING, encoding="utf-8")
    link = python_dir / "link.py"
    link.symlink_to(real)
    assert [p.name for p in lint.iter_source_files(tmp_path / "python")] == ["real.py"]


def test_malformed_source_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": "def broken(\n"}, baseline=[])
    assert lint.main(["--root", str(tmp_path)]) == 2


def test_valid_suppression_on_regex_declaration(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\\\s+')  # lint-markdown-heading-fence-state: ok intentional\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n",
        encoding="utf-8",
    )
    assert lint.scan_file(path, python_dir=python_dir) == []


def test_empty_suppression_reason_fails(tmp_path: Path) -> None:
    python_dir = tmp_path / "python"
    path = python_dir / "larch" / "mod.py"
    path.parent.mkdir(parents=True)
    _ = path.write_text(
        "import re\n"
        "HEADING_RE = re.compile(r'^#{1,6}\\\\s+')  # lint-markdown-heading-fence-state: ok\n"
        "def parse(text: str) -> None:\n"
        "    for line in text.splitlines():\n"
        "        if HEADING_RE.match(line):\n"
        "            pass\n",
        encoding="utf-8",
    )
    with pytest.raises(lint.ScanError, match="empty"):
        _ = lint.scan_file(path, python_dir=python_dir)


def test_baseline_suppresses_and_new_finding_exits_1(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        files={"larch/mod.py": VIOLATING},
        baseline=[_record()],
    )
    assert lint.main(["--root", str(tmp_path)]) == 0

    _write_project(
        tmp_path,
        files={"larch/mod.py": VIOLATING, "larch/other.py": VIOLATING.replace("HEADING_RE", "OTHER_RE")},
        baseline=[_record()],
    )
    assert lint.main(["--root", str(tmp_path)]) == 1


def test_issue_create_passes_with_fence_helper() -> None:
    root = Path(__file__).resolve().parents[3]
    python_dir = root / "python"
    path = python_dir / "larch" / "issue" / "issue_create.py"
    findings = [
        f
        for f in lint.scan_file(path, python_dir=python_dir)
        if "issue_create" in f.file
    ]
    assert findings == []


def test_cli_write_and_check(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": VIOLATING}, baseline=None)
    assert (
        lint.main(
            [
                "--root",
                str(tmp_path),
                "--write",
                "--initial-reason",
                "bootstrap",
            ]
        )
        == 0
    )
    assert lint.main(["--root", str(tmp_path)]) == 0


def test_baseline_stale_duplicate_and_shrink_fail_closed(tmp_path: Path) -> None:
    _write_project(tmp_path, files={"larch/mod.py": VIOLATING}, baseline=[_record(), _record()])
    assert lint.main(["--root", str(tmp_path)]) == 2

    _write_project(tmp_path, files={"larch/mod.py": "def parse() -> None:\n    pass\n"}, baseline=[_record()])
    assert lint.main(["--root", str(tmp_path)]) == 2

    _write_project(tmp_path, files={"larch/mod.py": VIOLATING}, baseline=[])
    assert lint.main(["--root", str(tmp_path)]) == 1
