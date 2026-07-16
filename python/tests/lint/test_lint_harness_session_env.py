from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from larch.lint.lint_harness_session_env import SESSION_ENV_PREAMBLE, main


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def harness(body: str) -> str:
    return f"#!/usr/bin/env bash\n{body.strip()}\n"


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def test_compliant_preamble_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "scripts/test-clean.sh",
        harness(f"{SESSION_ENV_PREAMBLE}\nset -euo pipefail\necho clean"),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_missing_preamble_reports_file_specific_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "skills/example/scripts/test-missing.sh",
        harness("set -euo pipefail\necho missing"),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "skills/example/scripts/test-missing.sh" in err
    assert "session-neutralization preamble before the first command" in err


def test_preamble_after_the_first_command_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "scripts/test-late.sh",
        harness(f"set -euo pipefail\n{SESSION_ENV_PREAMBLE}\necho late"),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "scripts/test-late.sh" in err


def test_harness_can_set_fixture_values_after_preamble(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(
        tmp_path,
        "scripts/test-fixture-values.sh",
        harness(f"{SESSION_ENV_PREAMBLE}\nIMPLEMENT_TMPDIR=/tmp/fixture\nDESIGN_TMPDIR=/tmp/design\necho fixture"),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_reason_bearing_suppression_on_first_session_use_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path,
        "scripts/test-suppressed.sh",
        harness(
            "set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\" "
            "# lint-harness-session-env: ok verifies inherited state"
        ),
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


@pytest.mark.parametrize(
    "body",
    [
        "set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\" # lint-harness-session-env: ok",
        "# lint-harness-session-env: ok standalone comments are not trailing suppressions\n"
        "set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\"",
    ],
)
def test_invalid_or_reasonless_suppression_fails(
    body: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "scripts/test-invalid-suppression.sh", harness(body))

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "scripts/test-invalid-suppression.sh" in err


def test_scope_excludes_hooks_and_runtime_scripts(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path, "hooks/test-hook.sh", harness("set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\""))
    write(tmp_path, "scripts/runtime.sh", harness("set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\""))
    write(tmp_path, "skills/example/scripts/runtime.sh", harness("set -euo pipefail\necho \"$IMPLEMENT_TMPDIR\""))

    rc, err = run(tmp_path, capsys)

    assert rc == 0, err


def test_git_discovery_includes_only_committed_harness_patterns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if shutil.which("git") is None:
        pytest.skip("git is required for worktree enumeration")
    _ = subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    write(tmp_path, "scripts/test-root.sh", harness("echo root"))
    write(tmp_path, "skills/example/scripts/test-skill.sh", harness("echo skill"))
    write(tmp_path, "scripts/runtime.sh", harness("echo runtime"))
    _ = subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    rc, err = run(tmp_path, capsys)

    assert rc == 1
    assert "scripts/test-root.sh" in err
    assert "skills/example/scripts/test-skill.sh" in err
    assert "scripts/runtime.sh" not in err
