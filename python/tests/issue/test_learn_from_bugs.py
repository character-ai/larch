# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
"""Offline tests for learn_from_bugs.py."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from larch.core import config
from larch.core import architectural_guidelines as ag
from larch.core.proc import CommandResult
from larch.issue import learn_from_bugs
from larch.issue.title_match import BUG_PREFIX
from test_support import RecordingRunner


def _result(stdout: str = "", rc: int = 0, stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


STRUCTURED_BODY = """## Summary

A widget broke.

## Root cause analysis

The reader parsed `https://` but the writer emits `OOS_FILE_MAP\\t`.

## Suggested fix(es)

Match the writer prefix.

<!-- larch:plan:start -->
## Plan
## Approach
Do the thing.
### UPDATED: python/larch/foo.py
lots of plan bytes that must be dropped
"""

FREEFORM_BODY = """**Summary.** Something went wrong in the flush path and nobody noticed.

More detail about the failure that is not under a recognized heading.
"""

TITLE_ONLY_BODY = "<!-- larch:plan:start -->\n## Plan\n## Approach\nonly a plan here\n"


def _issue(number: int, title: str, body: str, *, state: str = "CLOSED") -> dict[str, object]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "url": f"https://github.com/o/r/issues/{number}",
        "closedAt": "2026-07-01T00:00:00Z",
        "state": state,
    }


def _digest_numbers(path: Path) -> list[int]:
    return [int(json.loads(line)["number"]) for line in path.read_text(encoding="utf-8").splitlines()]


def test_diagnostic_prefix_cuts_at_plan_marker() -> None:
    prefix = learn_from_bugs.diagnostic_prefix(STRUCTURED_BODY)
    assert "larch:plan:start" not in prefix
    assert "must be dropped" not in prefix
    assert "Root cause analysis" in prefix


def test_build_digest_structured_keeps_signal_sections() -> None:
    digest = learn_from_bugs.build_digest(_issue(10, "[DONE] [BUG] widget", STRUCTURED_BODY))
    assert digest.structured is True
    assert digest.number == 10
    assert digest.title == "[BUG] widget"  # [DONE] stripped
    assert set(digest.sections) == {"summary", "root cause analysis", "suggested fix(es)"}
    assert "OOS_FILE_MAP" in digest.sections["root cause analysis"]


def test_build_digest_freeform_fallback() -> None:
    digest = learn_from_bugs.build_digest(_issue(11, "[BUG] flush", FREEFORM_BODY))
    assert digest.structured is False
    assert "_freeform" in digest.sections
    assert "flush path" in digest.sections["_freeform"]


def test_build_digest_title_only_when_body_is_plan_only() -> None:
    digest = learn_from_bugs.build_digest(_issue(12, "[BUG] plan-only", TITLE_ONLY_BODY))
    assert digest.structured is False
    assert digest.sections == {"_title_only": ""}


def test_build_digest_truncates_long_section() -> None:
    body = "## Summary\n\n" + ("A" * 800) + "\n\n<!-- larch:plan:start -->\n## Plan\n"
    digest = learn_from_bugs.build_digest(_issue(20, "[BUG] long", body))
    summary = digest.sections["summary"]
    assert summary.endswith("…")
    assert len(summary) == learn_from_bugs.SUMMARY_CAP + 1  # cap chars + ellipsis


def test_list_issues_parses_json_array() -> None:
    rows = [_issue(1, "[BUG] a", "b1"), _issue(2, "[BUG] b", "b2")]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out = learn_from_bugs.list_issues(runner, search="[BUG] in:title", state="closed", limit=5, repo="o/r")
    assert [row["number"] for row in out] == [1, 2]
    assert runner.calls[0][:3] == ["gh", "issue", "list"]
    assert "--search" in runner.calls[0]


def test_list_issues_raises_on_gh_failure() -> None:
    runner = RecordingRunner(responses=[_result(rc=1, stderr="boom")], strict=True)
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="boom"):
        learn_from_bugs.list_issues(runner, search="x", state="closed", limit=1, repo="o/r")


def test_coverage_index_scans_repo_surface(tmp_path: Path) -> None:
    (tmp_path / "ARCHITECTURAL_GUIDELINES.md").write_text(
        "### G-Py-1: Do a thing\n\ntext\n### G-Wire-1: Another\n", encoding="utf-8")
    lintdir = tmp_path / "python" / "larch" / "lint"
    lintdir.mkdir(parents=True)
    (lintdir / "lint_foo.py").write_text("x = 1\n", encoding="utf-8")
    (lintdir / "helper.py").write_text("x = 1\n", encoding="utf-8")  # not lint_-prefixed
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "lint-bar.sh").write_text("echo\n", encoding="utf-8")

    cov = learn_from_bugs.coverage_index(tmp_path)
    assert cov.guidelines == (("G-Py-1", "Do a thing"), ("G-Wire-1", "Another"))
    assert not cov.invariants  # file absent yet, must not error
    assert cov.python_lints == ("lint_foo",)
    assert cov.script_lints == ("lint-bar",)


def test_coverage_index_absent_files_yield_empty(tmp_path: Path) -> None:
    cov = learn_from_bugs.coverage_index(tmp_path)
    assert cov.to_json() == {
        "guidelines": [],
        "invariants": [],
        "python_lints": [],
        "script_lints": [],
    }


def test_coverage_index_does_not_emit_retired_rule_field(tmp_path: Path) -> None:
    retired_dir = tmp_path / ".claude" / "rules"
    retired_dir.mkdir(parents=True)
    (retired_dir / "some-rule.md").write_text("# Some Rule\n\nbody\n", encoding="utf-8")

    payload = learn_from_bugs.coverage_index(tmp_path).to_json()

    assert "rules" not in payload
    assert set(payload) == {"guidelines", "invariants", "python_lints", "script_lints"}


ARCHITECTURAL_FIXTURE = """# G-Depth-1: Rejected guideline depth 1
- Why: Example rationale.

## G-Depth-2: Rejected guideline depth 2
- Why: Example rationale.

### G-Run-Log-3: Accepted hyphenated guideline
- Why: Example rationale.
- Deviate when: Example carve-out.

#### G-Depth-4: Rejected guideline depth 4
- Why: Example rationale.

##### G-Depth-5: Rejected guideline depth 5
- Why: Example rationale.

###### G-Depth-6: Rejected guideline depth 6
- Why: Example rationale.

# I-Depth-1: Accepted invariant depth 1
- Why: Example rationale.

## I-Depth-2: Accepted invariant depth 2
- Why: Example rationale.

### I-Depth-3: Accepted invariant depth 3
- Why: Example rationale.

#### I-Depth-4: Accepted invariant depth 4
- Why: Example rationale.

##### I-Depth-5: Accepted invariant depth 5
- Why: Example rationale.

###### I-Depth-6: Accepted invariant depth 6
- Why: Example rationale.

### INV-Depth-1: Rejected invariant spelling
- Why: Example rationale.

Prose reference G-Xx-1: stays prose.
"""


def _reader_population(normalized: str, pattern: re.Pattern[str]) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for block in normalized.split("\n\n"):
        first_line: str = block.splitlines()[0] if block.splitlines() else ""
        match: re.Match[str] | None = pattern.match(first_line)
        if match is not None:
            entries.append((match.group(1), match.group(2)))
    return tuple(entries)


def _assert_reader_indexer_parity(root: Path, *, guidelines_text: str, invariants_text: str) -> None:
    expected_guidelines: tuple[tuple[str, str], ...] = tuple(
        (match.group(1), match.group(2)) for match in ag.GUIDELINE_HEADING_RE.finditer(guidelines_text)
    )
    expected_invariants: tuple[tuple[str, str], ...] = tuple(
        (match.group(1), match.group(2)) for match in ag.INVARIANT_HEADING_RE.finditer(invariants_text)
    )
    reader_guidelines: tuple[tuple[str, str], ...] = _reader_population(
        ag.parse_guideline_entries(guidelines_text), ag.GUIDELINE_HEADING_RE
    )
    reader_invariants: tuple[tuple[str, str], ...] = _reader_population(
        ag.parse_invariant_entries(invariants_text), ag.INVARIANT_HEADING_RE
    )
    indexed = learn_from_bugs.coverage_index(root)

    assert indexed.guidelines == expected_guidelines
    assert indexed.invariants == expected_invariants
    assert reader_guidelines == expected_guidelines
    assert reader_invariants == expected_invariants


def test_coverage_index_architectural_grammar_matches_reader(tmp_path: Path) -> None:
    (tmp_path / ag.GUIDELINES_FILENAME).write_text(ARCHITECTURAL_FIXTURE, encoding="utf-8")
    (tmp_path / ag.INVARIANTS_FILENAME).write_text(ARCHITECTURAL_FIXTURE, encoding="utf-8")

    _assert_reader_indexer_parity(
        tmp_path, guidelines_text=ARCHITECTURAL_FIXTURE, invariants_text=ARCHITECTURAL_FIXTURE
    )
    indexed = learn_from_bugs.coverage_index(tmp_path)
    all_rows = indexed.guidelines + indexed.invariants
    assert ("G-Run-Log-3", "Accepted hyphenated guideline") in indexed.guidelines
    assert ("G-Depth-2", "Rejected guideline depth 2") not in all_rows
    assert ("G-Depth-4", "Rejected guideline depth 4") not in all_rows
    assert all(identifier != "INV-Depth-1" for identifier, _title in all_rows)
    assert all(identifier != "G-Xx-1" for identifier, _title in all_rows)


def test_committed_architectural_files_match_reader_and_indexer() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    guidelines_text = (repo_root / ag.GUIDELINES_FILENAME).read_text(encoding="utf-8")
    invariants_text = (repo_root / ag.INVARIANTS_FILENAME).read_text(encoding="utf-8")

    _assert_reader_indexer_parity(
        repo_root, guidelines_text=guidelines_text, invariants_text=invariants_text
    )


def test_default_search_uses_shared_bug_prefix() -> None:
    assert f"{BUG_PREFIX} in:title" == learn_from_bugs.DEFAULT_SEARCH


def test_state_write_and_read_schema_version_one(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    state = learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z",
        scan_started_at="2026-07-09T11:00:00Z",
        highest_closed_issue_number_scanned=123,
        repo="o/r",
        search="[BUG] in:title",
        state="closed",
        selected_count=7,
    )

    learn_from_bugs.write_state(marker, state)

    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["scan_started_at"] == "2026-07-09T11:00:00Z"
    assert learn_from_bugs.read_state(marker) == state


def test_state_missing_and_malformed_markers_are_unusable(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    assert learn_from_bugs.read_state(marker) is None

    marker.parent.mkdir(parents=True)
    marker.write_text("{not-json\n", encoding="utf-8")
    assert learn_from_bugs.read_state(marker) is None

    marker.write_text(json.dumps({"schema_version": 1, "repo": "o/r"}), encoding="utf-8")
    assert learn_from_bugs.read_state(marker) is None

    marker.write_bytes(b'{"schema_version":1,"run_date":"2026-07-09T12:00:00Z","repo":"o/r","search":"x","state":"closed","selected_count":1,"highest_closed_issue_number_scanned":0}\xff')
    assert learn_from_bugs.read_state(marker) is None


def test_state_prior_shape_without_scan_started_at_reads_run_date(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    marker.parent.mkdir(parents=True)
    marker.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_date": "2026-07-09T12:00:00Z",
                "repo": "o/r",
                "extra": "ignored",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    state = learn_from_bugs.read_state(marker)

    assert state is not None
    assert state.run_date == "2026-07-09T12:00:00Z"
    assert state.scan_started_at is None
    assert state.repo == "o/r"


def test_write_state_cli_creates_parent_and_prints_kv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert learn_from_bugs.write_state_main(
        [
            "--root",
            str(tmp_path),
            "--repo",
            "o/r",
            "--search",
            "[BUG] in:title",
            "--state",
            "closed",
            "--selected-count",
            "0",
            "--highest-closed-issue-number-scanned",
            "0",
            "--run-date",
            "2026-07-09T12:00:00Z",
            "--scan-started-at",
            "2026-07-09T11:00:00Z",
        ]
    ) == 0

    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    assert marker.is_file()
    assert out["STATE_RELPATH"] == config.LEARN_FROM_BUGS_STATE_RELPATH
    assert out["RUN_DATE"] == "2026-07-09T12:00:00Z"
    assert out["SCAN_STARTED_AT"] == "2026-07-09T11:00:00Z"
    assert out["HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED"] == "0"


def test_read_state_cli_reports_missing_without_crashing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert learn_from_bugs.read_state_main(["--root", str(tmp_path)]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["LEARN_FROM_BUGS_STATE_FOUND"] == "false"


def test_run_prepare_captures_scan_started_at_before_issue_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []

    def fake_now() -> str:
        events.append("clock")
        return "2026-07-09T11:00:00Z"

    class EventRunner(RecordingRunner):
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> CommandResult:
            events.append("gh")
            return super().run(
                argv, timeout=timeout, cwd=cwd, env=env, check=check, stdout=stdout, stderr=stderr
            )

    monkeypatch.setattr(learn_from_bugs, "_utc_now_iso", fake_now)
    runner = EventRunner(responses=[_result("[]")], strict=True)

    stats = learn_from_bugs.run_prepare(
        runner,
        learn_from_bugs.PrepareRequest(
            search="[BUG] in:title",
            search_explicit=False,
            state="closed",
            limit=50,
            repo_explicit="o/r",
            out_dir=tmp_path / "out",
            root=tmp_path,
        ),
    )

    assert events == ["clock", "gh"]
    assert stats["SCAN_STARTED_AT"] == "2026-07-09T11:00:00Z"
    assert stats["HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED"] == 0
    assert stats["ISSUES_SELECTED"] == 0


def test_run_prepare_highest_issue_number_uses_unfiltered_rows(tmp_path: Path) -> None:
    rows = [
        _issue(40, "not a bug", FREEFORM_BODY),
        _issue(12, "[BUG] included", STRUCTURED_BODY),
    ]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)

    stats = learn_from_bugs.run_prepare(
        runner,
        learn_from_bugs.PrepareRequest(
            search="[BUG] in:title",
            search_explicit=False,
            state="closed",
            limit=50,
            repo_explicit="o/r",
            out_dir=tmp_path / "out",
            root=tmp_path,
        ),
    )

    assert stats["HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED"] == 40
    assert stats["ISSUES_FILTERED_NON_BUG"] == 1
    assert _digest_numbers(Path(str(stats["DIGEST_PATH"]))) == [12]


def test_run_prepare_explicit_search_still_filters_non_bug_rows(tmp_path: Path) -> None:
    rows = [
        _issue(1, "plain issue", FREEFORM_BODY),
        _issue(2, "[IMPLEMENTING] [BUG] lifecycle bug", STRUCTURED_BODY),
    ]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)

    stats = learn_from_bugs.run_prepare(
        runner,
        learn_from_bugs.PrepareRequest(
            search="operator search",
            search_explicit=True,
            state="closed",
            limit=50,
            repo_explicit="o/r",
            out_dir=tmp_path / "out",
            root=tmp_path,
        ),
    )

    assert stats["ISSUES_FILTERED_NON_BUG"] == 1
    assert stats["ISSUES_SELECTED"] == 1
    assert _digest_numbers(Path(str(stats["DIGEST_PATH"]))) == [2]


def test_state_symlink_marker_rejected_on_read_and_write(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    marker.parent.mkdir(parents=True)
    marker.symlink_to(target)
    state = learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z",
        scan_started_at="2026-07-09T11:00:00Z",
        highest_closed_issue_number_scanned=1,
        repo="o/r",
        search="[BUG] in:title",
        state="closed",
        selected_count=1,
    )

    assert learn_from_bugs.read_state(marker) is None
    with pytest.raises(OSError, match="symlink"):
        learn_from_bugs.write_state(marker, state)


def test_state_write_ignores_fixed_temp_symlink(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    marker.parent.mkdir(parents=True)
    temp = marker.with_name(marker.name + ".tmp")
    temp.symlink_to(tmp_path / "target.json")
    state = learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z",
        scan_started_at="2026-07-09T11:00:00Z",
        highest_closed_issue_number_scanned=1,
        repo="o/r",
        search="[BUG] in:title",
        state="closed",
        selected_count=1,
    )

    learn_from_bugs.write_state(marker, state)

    assert learn_from_bugs.read_state(marker) == state


def test_state_symlink_ancestor_rejected_on_read_and_write(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    link_parent = tmp_path / "link-parent"
    link_parent.symlink_to(real_parent, target_is_directory=True)
    marker = link_parent / "learn-from-bugs-state.json"
    state = learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z",
        scan_started_at="2026-07-09T11:00:00Z",
        highest_closed_issue_number_scanned=1,
        repo="o/r",
        search="[BUG] in:title",
        state="closed",
        selected_count=1,
    )

    assert learn_from_bugs.read_state(marker) is None
    with pytest.raises(OSError, match="symlink"):
        learn_from_bugs.write_state(marker, state)


def test_run_prepare_writes_artifacts_and_stats(tmp_path: Path) -> None:
    rows = [_issue(1, "[BUG] a", STRUCTURED_BODY), _issue(2, "[BUG] b", FREEFORM_BODY)]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out_dir = tmp_path / "run"
    request = learn_from_bugs.PrepareRequest(
        search="[BUG] in:title",
        search_explicit=False,
        state="closed",
        limit=10,
        repo_explicit="o/r",
        out_dir=out_dir,
        root=tmp_path,
    )
    stats = learn_from_bugs.run_prepare(runner, request)
    assert stats["ISSUES_SELECTED"] == 2
    assert stats["ISSUES_FILTERED_NON_BUG"] == 0
    assert stats["STRUCTURED"] == 1
    assert stats["REPO"] == "o/r"
    digest_lines = (out_dir / "digest.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(digest_lines) == 2
    first = json.loads(digest_lines[0])
    assert first["number"] == 1
    assert first["structured"] is True
    coverage = json.loads((out_dir / "coverage-index.json").read_text(encoding="utf-8"))
    assert set(coverage) == {"guidelines", "invariants", "python_lints", "script_lints"}
    assert "RULES_INDEXED" not in stats


def test_run_prepare_filters_implicit_default_search_to_bug_titles(tmp_path: Path) -> None:
    rows = [
        _issue(1, "[DONE] [BUG] fixed", STRUCTURED_BODY),
        _issue(2, "[Bug] mixed case", FREEFORM_BODY),
        _issue(3, "[FEATURE] discusses bugs", FREEFORM_BODY),
    ]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out_dir = tmp_path / "run"
    request = learn_from_bugs.PrepareRequest(
        search=learn_from_bugs.DEFAULT_SEARCH,
        search_explicit=False,
        state="closed",
        limit=10,
        repo_explicit="o/r",
        out_dir=out_dir,
        root=tmp_path,
    )

    stats = learn_from_bugs.run_prepare(runner, request)

    assert stats["ISSUES_SELECTED"] == 2
    assert stats["ISSUES_FILTERED_NON_BUG"] == 1
    assert _digest_numbers(out_dir / "digest.jsonl") == [1, 2]


def test_run_prepare_filters_explicit_default_search_to_bug_titles(tmp_path: Path) -> None:
    rows = [
        _issue(1, "[DONE] [BUG] fixed", STRUCTURED_BODY),
        _issue(2, "[Bug] mixed case", FREEFORM_BODY),
        _issue(3, "[FEATURE] discusses bugs", FREEFORM_BODY),
    ]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out_dir = tmp_path / "run"
    request = learn_from_bugs.PrepareRequest(
        search=learn_from_bugs.DEFAULT_SEARCH,
        search_explicit=True,
        state="closed",
        limit=10,
        repo_explicit="o/r",
        out_dir=out_dir,
        root=tmp_path,
    )

    stats = learn_from_bugs.run_prepare(runner, request)

    assert stats["ISSUES_SELECTED"] == 2
    assert stats["ISSUES_FILTERED_NON_BUG"] == 1
    assert _digest_numbers(out_dir / "digest.jsonl") == [1, 2]


def test_prepare_main_filters_explicit_search_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rows = [_issue(3, "[FEATURE] discusses bugs", FREEFORM_BODY)]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out_dir = tmp_path / "run"
    monkeypatch.setattr(learn_from_bugs, "_runner", lambda: runner)

    rc = learn_from_bugs.prepare_main(
        [
            "--search",
            learn_from_bugs.DEFAULT_SEARCH,
            "--repo",
            "o/r",
            "--out",
            str(out_dir),
            "--root",
            str(tmp_path),
        ]
    )

    stdout = capsys.readouterr().out
    stats = dict(line.split("=", 1) for line in stdout.splitlines() if "=" in line)
    assert rc == 0
    assert stats["ISSUES_SELECTED"] == "0"
    assert stats["ISSUES_FILTERED_NON_BUG"] == "1"
    assert _digest_numbers(out_dir / "digest.jsonl") == []


def test_prepare_main_rejects_abbreviated_search_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(responses=[], strict=True)
    monkeypatch.setattr(learn_from_bugs, "_runner", lambda: runner)

    with pytest.raises(SystemExit):
        learn_from_bugs.prepare_main(
            [
                "--sear",
                learn_from_bugs.DEFAULT_SEARCH,
                "--repo",
                "o/r",
                "--out",
                str(tmp_path / "run"),
                "--root",
                str(tmp_path),
            ]
        )
