from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from larch.lint import lint_guideline_no_exception as lgne


def _record(
    *,
    guideline_id: str = "G-New-1",
    reason: str = "kept as guideline",
    **extra: object,
) -> dict[str, object]:
    record: dict[str, object] = {"guideline_id": guideline_id, "reason": reason}
    record.update(extra)
    return record


def _guideline(
    guideline_id: str = "G-New-1",
    *,
    title: str = "New guidance",
    deviate: str = "never; this has no exception",
) -> str:
    return (
        f"### {guideline_id}: {title}\n"
        "- Why: fixture reason.\n"
        f"- Deviate when: {deviate}\n"
    )


def _write_project(
    root: Path,
    *,
    guidelines: str | None = None,
    baseline: object | None = None,
) -> None:
    if guidelines is not None:
        _ = (root / "ARCHITECTURAL_GUIDELINES.md").write_text(guidelines, encoding="utf-8")
    if baseline is not None:
        baseline_path: Path = root / "python" / lgne.BASELINE_FILENAME
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        _ = baseline_path.write_text(json.dumps(baseline), encoding="utf-8")


def test_unbaselined_never_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 1
    assert "G-New-1 has a no-exception deviate clause" in capsys.readouterr().err


def test_unbaselined_na_exits_1(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline(deviate="n/a for this fixture"), baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 1


def test_baselined_live_finding_exits_0_and_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=[_record(reason="intentional")])

    assert lgne.main(["--root", str(tmp_path)]) == 0
    assert "baselined" in capsys.readouterr().err


def test_stale_baseline_row_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(
        tmp_path,
        guidelines=_guideline(deviate="with explicit exception"),
        baseline=[_record()],
    )

    assert lgne.main(["--root", str(tmp_path)]) == 1
    assert "stale baseline row: G-New-1" in capsys.readouterr().err


def test_blank_baseline_reason_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=[_record(reason=" ")])

    assert lgne.main(["--root", str(tmp_path)]) == 2


def test_duplicate_baseline_id_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=[_record(), _record()])

    assert lgne.main(["--root", str(tmp_path)]) == 2


@pytest.mark.parametrize(
    "baseline",
    [
        [{"guideline_id": "G-New-1"}],
        [{"reason": "missing id"}],
        [_record(extra="bad")],
        [_record(guideline_id="not-a-guideline")],
        ["not an object"],
    ],
)
def test_missing_extra_or_invalid_baseline_keys_exit_2(
    tmp_path: Path, baseline: object
) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=baseline)

    assert lgne.main(["--root", str(tmp_path)]) == 2


def test_malformed_json_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline())
    baseline_path: Path = tmp_path / "python" / lgne.BASELINE_FILENAME
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline_path.write_text("[", encoding="utf-8")

    assert lgne.main(["--root", str(tmp_path)]) == 2


def test_missing_guidelines_file_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 2


def test_non_utf8_guidelines_file_exits_2(tmp_path: Path) -> None:
    _write_project(tmp_path, baseline=[])
    _ = (tmp_path / "ARCHITECTURAL_GUIDELINES.md").write_bytes(b"\xff")

    assert lgne.main(["--root", str(tmp_path)]) == 2


def test_non_matching_deviate_text_passes_without_baseline_row(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        guidelines=_guideline(deviate="when a fixture needs an exception"),
        baseline=[],
    )

    assert lgne.main(["--root", str(tmp_path)]) == 0


def test_matching_is_anchored_to_clause_start(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        guidelines=_guideline(deviate="when never is acceptable for a fixture"),
        baseline=[],
    )

    assert lgne.main(["--root", str(tmp_path)]) == 0


def test_multiple_entries_report_baselined_and_unbaselined_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    guidelines: str = _guideline("G-Kept-1") + "\n" + _guideline("G-New-1")
    _write_project(tmp_path, guidelines=guidelines, baseline=[_record(guideline_id="G-Kept-1")])

    assert lgne.main(["--root", str(tmp_path)]) == 1
    stderr: str = capsys.readouterr().err
    assert "G-Kept-1 line" in stderr
    assert "G-New-1 has a no-exception deviate clause" in stderr


def test_cli_root_points_at_fixture_root(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline(), baseline=[])
    repo_root: Path = Path(__file__).resolve().parents[3]

    result: subprocess.CompletedProcess[str] = subprocess.run(
        [
            sys.executable,
            "python/cli.py",
            "lint",
            "guideline-no-exception",
            "--root",
            str(tmp_path),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "G-New-1 has a no-exception deviate clause" in result.stderr


def test_new_no_exception_guideline_without_baseline_fails(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline("G-New-1"), baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 1


def test_non_entry_heading_closes_current_guideline_entry(tmp_path: Path) -> None:
    guidelines: str = (
        _guideline("G-First-1", deviate="with a real exception")
        + "\n### Not a guideline entry\n"
        + "- Deviate when: n/a for non-entry prose\n\n"
        + _guideline("G-Second-1", deviate="with another real exception")
    )
    _write_project(tmp_path, guidelines=guidelines, baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 0


def test_never_before_punctuation_matches(tmp_path: Path) -> None:
    _write_project(tmp_path, guidelines=_guideline(deviate="never; punctuation follows"), baseline=[])

    assert lgne.main(["--root", str(tmp_path)]) == 1
