"""Structural coverage for public lint Makefile contracts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE = REPO_ROOT / "Makefile"
LINTING_DOC = REPO_ROOT / "docs" / "linting.md"


def _descriptor_block(name: str) -> tuple[str, ...]:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(rf"^{name} := \\\n(?P<body>(?:\t.*\\\n)+\t[^\n]+)$", text, re.MULTILINE)
    assert match, f"missing {name} descriptor block"
    return tuple(
        line.strip().removesuffix("\\").strip()
        for line in match.group("body").splitlines()
    )


def _make_dry_run(target: str) -> str:
    result = subprocess.run(
        ["make", "--no-print-directory", "-n", target],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_common_lint_test_descriptors_generate_focused_pytest_targets() -> None:
    for descriptor in _descriptor_block("LINT_TEST_DESCRIPTORS"):
        target, module = descriptor.split("|")
        assert (REPO_ROOT / module).is_file()
        output = _make_dry_run(f"test-lint-{target}")
        assert "timing harness-mark" in output
        assert module in output


def test_generic_baseline_descriptors_generate_regeneration_targets() -> None:
    for descriptor in _descriptor_block("REGEN_BASELINE_DESCRIPTORS"):
        target, baseline, bootstrap_reason = descriptor.split("|")
        assert baseline.endswith("-baseline.json")
        assert bootstrap_reason
        output = _make_dry_run(f"regen-{target}-baseline")
        assert f"python/cli.py lint {target} --write" in output
        if (REPO_ROOT / "python" / baseline).is_file():
            assert "--initial-reason" not in output
        else:
            assert f"--initial-reason '{bootstrap_reason.replace('+', ' ')}'" in output


def test_documented_and_registered_lint_targets_resolve() -> None:
    documented = set(
        re.findall(r"`make ((?:lint|test-lint|regen)-[a-z0-9-]+(?:-baseline)?)`", LINTING_DOC.read_text(encoding="utf-8"))
    )
    makefile_text = MAKEFILE.read_text(encoding="utf-8")
    registered_match = re.search(r"for chk in (?P<names>[^;]+); do", makefile_text)
    assert registered_match, "missing py-lint-checks-fast command inventory"
    registered = {f"lint-{name}" for name in registered_match.group("names").split()}

    for target in sorted(documented | registered):
        _ = _make_dry_run(target)
