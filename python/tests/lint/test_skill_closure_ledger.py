from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint import skill_closure_ledger as ledger

if TYPE_CHECKING:
    import pytest


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _ = _run_git(repo, "init", "-b", "main")
    _ = _run_git(repo, "config", "user.email", "test@example.com")
    _ = _run_git(repo, "config", "user.name", "Test")


def _commit_all(repo: Path, subject: str) -> str:
    _ = _run_git(repo, "add", ".")
    _ = _run_git(repo, "commit", "-m", subject)
    return _run_git(repo, "rev-parse", "HEAD")


def _commit_baseline(repo: Path, subject: str, rows: list[dict[str, object]]) -> str:
    baseline = repo / "python" / "skill-closure-baseline.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return _commit_all(repo, subject)


def _row(skill: str, tokens: int, *, extra: bool = False) -> dict[str, object]:
    row: dict[str, object] = {"skill": skill, "closure_estimated_tokens": tokens}
    if extra:
        row.update(
            {
                "skill_md_lines": 1,
                "skill_md_estimated_tokens": 2,
                "skill_md_content_estimated_tokens": 2,
                "closure_lines": 3,
                "closure_content_estimated_tokens": tokens - 1,
                "files": ["skills/example/SKILL.md"],
                "conditional_lines": 0,
                "conditional_estimated_tokens": 0,
                "conditional_content_estimated_tokens": 0,
                "conditional_files": [],
            },
        )
    return row


def _fixture_history(repo: Path) -> dict[str, str]:
    _init_repo(repo)
    commits: dict[str, str] = {}
    commits["initial"] = _commit_baseline(
        repo,
        "Initial closure baseline",
        [_row("panel-tier", 66043), _row("design", 10000)],
    )
    commits["panel_pre"] = _commit_baseline(
        repo,
        "Shrink panel tier prelude",
        [_row("panel-tier", 57617, extra=True), _row("design", 10000, extra=True)],
    )
    commits["pr5978"] = _commit_baseline(
        repo,
        "Shrink panel tier (#5978)",
        [_row("panel-tier", 50057, extra=True), _row("design", 10000, extra=True)],
    )
    _ = (repo / "NOTE.md").write_text("tag point\n", encoding="utf-8")
    commits["tag_point"] = _commit_all(repo, "Prepare release tag")
    _ = _run_git(repo, "tag", "v-ledger-test")
    commits["pr6029"] = _commit_baseline(
        repo,
        "Classifier honesty raises design (#6029)",
        [_row("panel-tier", 50711, extra=True), _row("design", 12763, extra=True)],
    )
    commits["pr5980"] = _commit_baseline(
        repo,
        "Final panel-tier shrink (#5980)",
        [_row("panel-tier", 44124, extra=True), _row("design", 12600, extra=True)],
    )
    return commits


def _tsv_rows(text: str) -> list[dict[str, str]]:
    lines = text.strip().splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=True)) for line in lines[1:]]


def test_detailed_ledger_marks_real_deltas_and_first_seen_rows(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    commits = _fixture_history(repo)

    rc = ledger.ledger_main(["--root", str(repo)])

    captured = capsys.readouterr()
    assert rc == 0
    rows = _tsv_rows(captured.out)
    initial_panel = next(row for row in rows if row["commit"] == commits["initial"] and row["target"] == "panel-tier")
    assert initial_panel["previous"] == ""
    assert initial_panel["delta"] == ""
    assert initial_panel["raise"] == "false"
    pr5978 = next(row for row in rows if row["pr"] == "#5978" and row["target"] == "panel-tier")
    assert pr5978["previous"] == "57617"
    assert pr5978["current"] == "50057"
    assert pr5978["delta"] == "-7560"
    assert pr5978["raise"] == "false"
    design_raise = next(row for row in rows if row["pr"] == "#6029" and row["target"] == "design")
    assert design_raise["previous"] == "10000"
    assert design_raise["current"] == "12763"
    assert design_raise["delta"] == "2763"
    assert design_raise["raise"] == "true"
    pr5980 = next(row for row in rows if row["pr"] == "#5980" and row["target"] == "panel-tier")
    assert pr5980["previous"] == "50711"
    assert pr5980["current"] == "44124"
    assert pr5980["delta"] == "-6587"


def test_window_uses_predecessor_outside_selected_range(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    commits = _fixture_history(repo)

    rc = ledger.ledger_main(["--root", str(repo), "--window", "2"])

    captured = capsys.readouterr()
    assert rc == 0
    rows = _tsv_rows(captured.out)
    assert {row["commit"] for row in rows} == {commits["pr6029"], commits["pr5980"]}
    first_panel = next(row for row in rows if row["commit"] == commits["pr6029"] and row["target"] == "panel-tier")
    assert first_panel["previous"] == "50057"
    assert first_panel["current"] == "50711"
    assert first_panel["delta"] == "654"
    first_design = next(row for row in rows if row["commit"] == commits["pr6029"] and row["target"] == "design")
    assert first_design["previous"] == "10000"
    assert first_design["delta"] == "2763"


def test_since_tag_summary_aggregates_after_tag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    commits = _fixture_history(repo)

    rc = ledger.ledger_main(["--root", str(repo), "--since-tag", "v-ledger-test", "--summary"])

    captured = capsys.readouterr()
    assert rc == 0
    rows = {row["target"]: row for row in _tsv_rows(captured.out)}
    assert rows["panel-tier"] == {
        "target": "panel-tier",
        "start": "50057",
        "end": "44124",
        "delta": "-5933",
        "raises": "1",
        "largest_raise_commit": commits["pr6029"],
        "largest_raise_delta": "654",
    }
    assert rows["design"] == {
        "target": "design",
        "start": "10000",
        "end": "12600",
        "delta": "2600",
        "raises": "1",
        "largest_raise_commit": commits["pr6029"],
        "largest_raise_delta": "2763",
    }


def test_malformed_historical_json_exits_2(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    baseline = repo / "python" / "skill-closure-baseline.json"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("not json\n", encoding="utf-8")
    _ = _commit_all(repo, "Bad baseline")

    rc = ledger.ledger_main(["--root", str(repo)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid JSON" in captured.err


def test_missing_baseline_history_exits_2(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "README.md").write_text("readme\n", encoding="utf-8")
    _ = _commit_all(repo, "Initial commit")

    rc = ledger.ledger_main(["--root", str(repo)])

    captured = capsys.readouterr()
    assert rc == 2
    assert "no git history found for python/skill-closure-baseline.json" in captured.err
