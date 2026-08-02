# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false, reportUnusedFunction=false
"""Offline tests for learn_from_bugs.py."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from larch.core import config
from larch.core import architectural_guidelines as ag
from larch.core.proc import CommandResult
from larch.issue import learn_from_bugs
from larch.issue.title_match import BUG_PREFIX
from larch.report import storage_config
from test_support import RecordingRunner, RunCall


@pytest.fixture(autouse=True)
def _isolated_analysis_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    storage = storage_config.ToolRepositoryStorage(
        storage_config.StorageBase("s3", "test-bucket"), "repository"
    )

    def load_storage(**_kwargs: object) -> storage_config.ToolRepositoryStorage:
        return storage

    monkeypatch.setattr(
        storage_config,
        "load_tool_repository_storage",
        load_storage,
    )


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

STRUCTURED_H4_BODY = """#### Summary

An h4-sectioned widget broke.

#### Root cause

The digester matched only h2/h3, so h4 bodies fell to freeform truncation.

#### Suggested fix(es)

Widen heading recognition to h2 through h4.

<!-- larch:plan:start -->
## Plan
## Approach
Do the thing.
"""

FENCED_HEADING_BACKTICK_BODY = """## Summary

Real summary before a fenced phantom.

```markdown
## Root cause

This fenced heading must not become a section.
```

Still summary after the fence.

## Suggested fix(es)

Ignore headings inside fences.

<!-- larch:plan:start -->
## Plan
## Approach
Do the thing.
"""

FENCED_HEADING_TILDE_BODY = """## Summary

Real summary with a tilde fence.

~~~~markdown
## Root cause

Longer tilde opener; a shorter closer must not end the fence.
~~~
Still inside the fence.
~~~~

Summary continues after the matched closer.

## Suggested fix(es)

Require closing length >= opener length.

<!-- larch:plan:start -->
## Plan
## Approach
Do the thing.
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


def test_diagnostic_prefix_uses_shared_marker_recognizer() -> None:
    body = (
        "## Summary\n\nKeep this.\n\n"
        "  <!--   larch:plan:start   -->  \n"
        "## Plan\nDrop this.\n"
    )
    prefix = learn_from_bugs.diagnostic_prefix(body)
    assert prefix == "## Summary\n\nKeep this.\n\n"
    assert "Drop this." not in prefix

    crlf_body = (
        "## Summary\r\n\r\nKeep this.\r\n\r\n"
        "  <!--   larch:plan:start   -->  \r\n"
        "## Plan\r\nDrop this.\r\n"
    )
    assert learn_from_bugs.diagnostic_prefix(crlf_body) == "## Summary\r\n\r\nKeep this.\r\n\r\n"

    # Case/partial/split forms must not act as marker boundaries; omit heading
    # fallbacks from these bodies so only the shared recognizer is under test.
    case_variant = "## Summary\n\nKeep.\n\n<!-- LARCH:PLAN:START -->\nDrop if matched.\n"
    assert learn_from_bugs.diagnostic_prefix(case_variant) == case_variant

    partial_prose = "## Summary\n\nSee <!-- larch:plan:start in prose\n"
    assert learn_from_bugs.diagnostic_prefix(partial_prose) == partial_prose

    split_line = "## Summary\n\nKeep.\n\n<!-- larch:plan:\nstart -->\nDrop if matched.\n"
    assert learn_from_bugs.diagnostic_prefix(split_line) == split_line

    heading_fallback = "## Summary\n\nKeep.\n\n## Plan\nDrop.\n"
    assert learn_from_bugs.diagnostic_prefix(heading_fallback) == "## Summary\n\nKeep.\n\n"


def test_build_digest_structured_keeps_signal_sections() -> None:
    digest = learn_from_bugs.build_digest(_issue(10, "[DONE] [BUG] widget", STRUCTURED_BODY))
    assert digest.structured is True
    assert digest.number == 10
    assert digest.title == "[BUG] widget"  # [DONE] stripped
    assert set(digest.sections) == {"summary", "root cause analysis", "suggested fix(es)"}
    assert digest.sections["summary"] == "A widget broke."
    assert digest.sections["root cause analysis"] == (
        "The reader parsed `https://` but the writer emits `OOS_FILE_MAP\\t`."
    )
    assert digest.sections["suggested fix(es)"] == "Match the writer prefix."
    assert "OOS_FILE_MAP" in digest.sections["root cause analysis"]
    assert "_freeform" not in digest.sections


def test_build_digest_h4_canonical_sections_are_structured() -> None:
    digest = learn_from_bugs.build_digest(_issue(13, "[BUG] h4 body", STRUCTURED_H4_BODY))
    assert digest.structured is True
    assert set(digest.sections) == {"summary", "root cause", "suggested fix(es)"}
    assert "freeform truncation" in digest.sections["root cause"]
    assert "h2 through h4" in digest.sections["suggested fix(es)"]
    assert "_freeform" not in digest.sections


def test_build_digest_ignores_headings_inside_backtick_fence() -> None:
    digest = learn_from_bugs.build_digest(
        _issue(14, "[BUG] fenced backtick", FENCED_HEADING_BACKTICK_BODY)
    )
    assert digest.structured is True
    assert "root cause" not in digest.sections
    assert "root cause analysis" not in digest.sections
    assert "Real summary before a fenced phantom." in digest.sections["summary"]
    assert "Still summary after the fence." in digest.sections["summary"]
    assert "## Root cause" in digest.sections["summary"]
    assert digest.sections["suggested fix(es)"] == "Ignore headings inside fences."


def test_build_digest_ignores_headings_inside_tilde_fence_with_short_closer() -> None:
    digest = learn_from_bugs.build_digest(
        _issue(15, "[BUG] fenced tilde", FENCED_HEADING_TILDE_BODY)
    )
    assert digest.structured is True
    assert "root cause" not in digest.sections
    assert "Still inside the fence." in digest.sections["summary"]
    assert "Summary continues after the matched closer." in digest.sections["summary"]
    assert digest.sections["suggested fix(es)"] == "Require closing length >= opener length."


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
    assert runner.calls == [[  # lint-gh-argv-literal: ok fixture assertion
        "gh", "issue", "list", "--repo", "o/r", "--state", "closed", "--json",
        "number,title,body,closedAt,url,state", "--search", "[BUG] in:title", "--limit", "5",
    ]]


def test_list_issues_raises_on_gh_failure() -> None:
    runner = RecordingRunner(responses=[_result(rc=1, stderr="boom")], strict=True)
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="gh issue list failed"):
        learn_from_bugs.list_issues(runner, search="x", state="closed", limit=1, repo="o/r")


def test_list_issues_filters_non_dict_rows() -> None:
    rows: list[object] = [_issue(1, "[BUG] a", "b1"), "skip", 3, None]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out = learn_from_bugs.list_issues(runner, search="[BUG] in:title", state="closed", limit=5, repo="o/r")
    assert [row["number"] for row in out] == [1]


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
        (match.group(1), match.group(2)) for match in ag.GUIDELINE_HEADING_RE.finditer(guidelines_text)  # pylint: disable=no-member
    )
    expected_invariants: tuple[tuple[str, str], ...] = tuple(
        (match.group(1), match.group(2)) for match in ag.INVARIANT_HEADING_RE.finditer(invariants_text)  # pylint: disable=no-member
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
    assert payload["schema_version"] == 2
    assert payload["proposals"] == []
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
    marker = learn_from_bugs.state_path(tmp_path)
    assert marker.is_file()
    assert out["STATE_RELPATH"] == config.LEARN_FROM_BUGS_STATE_RELPATH
    assert out["RUN_DATE"] == "2026-07-09T12:00:00Z"
    assert out["SCAN_STARTED_AT"] == "2026-07-09T11:00:00Z"
    assert out["HIGHEST_CLOSED_ISSUE_NUMBER_SCANNED"] == "0"


def test_write_state_cli_rejects_invalid_existing_marker(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('{"schema_version": 99}\n', encoding="utf-8")

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="invalid or unsupported"):
        learn_from_bugs.write_state_main([
            "--root", str(tmp_path), "--repo", "o/r", "--search", "x", "--state", "closed",
            "--selected-count", "0", "--highest-closed-issue-number-scanned", "0",
            "--run-date", "2026-07-09T12:00:00Z", "--scan-started-at", "2026-07-09T11:00:00Z",
        ])


def test_write_state_cli_requires_proposals_file_for_existing_history(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    learn_from_bugs.write_state(marker, learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z", repo="o/r", search="x", state="closed",
        selected_count=1, highest_closed_issue_number_scanned=3, proposals=(_proposal(status="pending"),),
    ))

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="--proposals-file"):
        learn_from_bugs.write_state_main([
            "--root", str(tmp_path), "--repo", "o/r", "--search", "x", "--state", "closed",
            "--selected-count", "0", "--highest-closed-issue-number-scanned", "0",
            "--run-date", "2026-07-10T12:00:00Z", "--scan-started-at", "2026-07-10T11:00:00Z",
        ])


def test_write_state_cli_preserves_newer_existing_proposals(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    remote_proposal = _proposal(status="adopted")
    remote_only = _proposal(
        "remote-only", target="registration:remote-only", status="pending"
    )
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(remote_proposal, remote_only),
        ),
    )
    proposals_file = tmp_path / "reconciled-proposals.jsonl"
    local_stale = _proposal(status="pending")
    proposals_file.write_text(
        json.dumps(local_stale.to_json()) + "\n", encoding="utf-8"
    )

    assert learn_from_bugs.write_state_main([
        "--root", str(tmp_path), "--repo", "o/r", "--search", "x", "--state", "closed",
        "--selected-count", "2", "--highest-closed-issue-number-scanned", "4",
        "--run-date", "2026-07-10T12:00:00Z", "--scan-started-at", "2026-07-10T11:00:00Z",
        "--proposals-file", str(proposals_file),
    ]) == 0

    written = learn_from_bugs.read_state(marker)
    assert written is not None
    assert written.proposals == (remote_proposal, remote_only)


def test_write_state_cli_applies_refresh_when_base_matches_published(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    # Fetched default branch still shows the pre-refresh pending status.
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(_proposal(status="pending"),),
        ),
    )
    base_file = tmp_path / "base-proposals.jsonl"
    base_file.write_text(
        json.dumps(_proposal(status="pending").to_json()) + "\n", encoding="utf-8"
    )
    proposals_file = tmp_path / "reconciled-proposals.jsonl"
    proposals_file.write_text(
        json.dumps(_proposal(status="adopted").to_json()) + "\n", encoding="utf-8"
    )

    assert learn_from_bugs.write_state_main([
        "--root", str(tmp_path), "--repo", "o/r", "--search", "x", "--state", "closed",
        "--selected-count", "1", "--highest-closed-issue-number-scanned", "4",
        "--run-date", "2026-07-10T12:00:00Z", "--scan-started-at", "2026-07-10T11:00:00Z",
        "--proposals-file", str(proposals_file),
        "--base-proposals-file", str(base_file),
    ]) == 0

    written = learn_from_bugs.read_state(marker)
    assert written is not None
    assert written.proposals[0].status == "adopted"


def test_write_state_cli_keeps_concurrent_publication_over_stale_refresh(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    # A concurrent run already published adopted on the default branch.
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(_proposal(status="adopted"),),
        ),
    )
    # Scan start saw pending; this run's local refresh is a stale pending.
    base_file = tmp_path / "base-proposals.jsonl"
    base_file.write_text(
        json.dumps(_proposal(status="pending").to_json()) + "\n", encoding="utf-8"
    )
    proposals_file = tmp_path / "reconciled-proposals.jsonl"
    proposals_file.write_text(
        json.dumps(_proposal(status="pending").to_json()) + "\n", encoding="utf-8"
    )

    assert learn_from_bugs.write_state_main([
        "--root", str(tmp_path), "--repo", "o/r", "--search", "x", "--state", "closed",
        "--selected-count", "1", "--highest-closed-issue-number-scanned", "4",
        "--run-date", "2026-07-10T12:00:00Z", "--scan-started-at", "2026-07-10T11:00:00Z",
        "--proposals-file", str(proposals_file),
        "--base-proposals-file", str(base_file),
    ]) == 0

    written = learn_from_bugs.read_state(marker)
    assert written is not None
    assert written.proposals[0].status == "adopted"


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

    def record_gh_call(_call: RunCall) -> None:
        events.append("gh")

    monkeypatch.setattr(learn_from_bugs, "_utc_now_iso", fake_now)
    runner = RecordingRunner(responses=[_result("[]")], strict=True, on_call=record_gh_call)

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


def _proposal(
    proposal_id: str = "add-audit-lint",
    proposal_type: learn_from_bugs.ProposalType = "lint",
    target: str = "registration:audit-lint",
    status: learn_from_bugs.ProposalStatus = "proposed",
    filed_issue: int | None = None,
    run_date: str = "2026-07-01T00:00:00Z",
    adoption_evidence: learn_from_bugs.AdoptionEvidence | None = None,
) -> learn_from_bugs.Proposal:
    return learn_from_bugs.Proposal(
        id=proposal_id,
        type=proposal_type,
        target=target,
        run_date=run_date,
        status=status,
        filed_issue=filed_issue,
        adoption_evidence=adoption_evidence,
    )


def test_state_v1_reads_as_v2_with_empty_proposals(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    marker.parent.mkdir(parents=True)
    marker.write_text(
        json.dumps({"schema_version": 1, "run_date": "2026-07-01", "repo": "o/r"}),
        encoding="utf-8",
    )

    state = learn_from_bugs.read_state(marker)

    assert state is not None
    assert state.schema_version == 2
    assert not state.proposals


def test_state_v2_round_trip_preserves_check_target(tmp_path: Path) -> None:
    marker = tmp_path / config.LEARN_FROM_BUGS_STATE_RELPATH
    proposal = _proposal(
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
        status="pending",
        filed_issue=123,
    )
    state = learn_from_bugs.LearnFromBugsState(
        run_date="2026-07-09T12:00:00Z",
        repo="o/r",
        search="x",
        state="closed",
        selected_count=1,
        highest_closed_issue_number_scanned=3,
        proposals=(proposal,),
    )

    learn_from_bugs.write_state(marker, state)

    assert learn_from_bugs.read_state(marker) == state


@pytest.mark.parametrize(
    ("proposal_type", "target"),
    [
        ("fix", "issue:1"),
        ("test", "../test_x.py"),
        ("lint", "module:/tmp/x.py"),
        ("guideline", "README.md"),
        ("lint", "check:crates/larch-lint/src/checks.rs"),
        ("test", "check:crates/larch-lint/src/checks.rs#not-a-symbol"),
    ],
)
def test_invalid_canonical_targets_are_rejected(
    tmp_path: Path, proposal_type: str, target: str
) -> None:
    path = tmp_path / "proposals.jsonl"
    path.write_text(
        json.dumps(
            {
                "id": "bad-target",
                "type": proposal_type,
                "target": target,
                "run_date": "2026-07-01",
                "status": "pending",
                "filed_issue": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_load_proposals_preserves_historical_issue_linkage(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    first = _proposal(status="pending", filed_issue=42).to_json()
    second = _proposal(status="proposed").to_json()
    path.write_text(
        json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8"
    )

    proposals = learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)

    assert proposals == (_proposal(status="pending", filed_issue=42),)


def test_load_proposals_rejects_checked_history_with_changed_run_date(
    tmp_path: Path,
) -> None:
    path = tmp_path / "proposals.jsonl"
    first = _proposal(status="orphaned").to_json()
    second = _proposal(status="proposed").to_json()
    second["run_date"] = "2026-07-09T00:00:00Z"
    path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="conflicting stable"):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_load_proposals_rejects_duplicate_with_changed_run_date(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    path.write_text(
        json.dumps(_proposal().to_json())
        + "\n"
        + json.dumps(_proposal(run_date="2026-07-09T00:00:00Z").to_json())
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="conflicting stable"):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_hook_target_matches_plugin_root_command(tmp_path: Path) -> None:
    hooks_path = tmp_path / "hooks" / "hooks.json"
    hooks_path.parent.mkdir()
    hooks_path.write_text(json.dumps({"hooks": [{"command": "${CLAUDE_PLUGIN_ROOT}/hooks/check.py"}]}), encoding="utf-8")
    proposal = _proposal(proposal_type="hook", target="hook:hooks/check.py")

    assert learn_from_bugs.check_proposals(RecordingRunner(strict=True), (proposal,), tmp_path, "o/r")[0].status == "adopted"


@pytest.mark.parametrize(
    "command",
    [
        "bash ${CLAUDE_PLUGIN_ROOT}/hooks/check.py --strict",
        "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/check.py --strict",
    ],
)
def test_hook_target_matches_wrapped_or_argument_bearing_command(
    tmp_path: Path, command: str
) -> None:
    hooks_path = tmp_path / "hooks" / "hooks.json"
    hooks_path.parent.mkdir()
    hooks_path.write_text(
        json.dumps({"hooks": [{"command": command}]}), encoding="utf-8"
    )
    proposal = _proposal(proposal_type="hook", target="hook:hooks/check.py")

    checked = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )

    assert checked[0].status == "adopted"


def test_lint_registration_matches_two_element_cli_key(tmp_path: Path) -> None:
    cli_path = tmp_path / "python" / "larch" / "cli.py"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text(
        '_REGISTRY = {("lint", "audit-lint"): ("module", "main")}\n',
        encoding="utf-8",
    )
    proposal = _proposal(target="registration:audit-lint")

    assert learn_from_bugs.check_proposals(RecordingRunner(strict=True), (proposal,), tmp_path, "o/r")[0].status == "adopted"


@pytest.mark.parametrize(
    "source",
    [
        '# ("lint", "audit-lint"): ("module", "main"),\n_REGISTRY = {}\n',
        '_REGISTRY = {"note": \'("lint", "audit-lint")\'}\n',
    ],
)
def test_lint_registration_ignores_comments_and_strings(
    tmp_path: Path, source: str
) -> None:
    cli_path = tmp_path / "python" / "larch" / "cli.py"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text(source, encoding="utf-8")
    proposal = _proposal(target="registration:audit-lint")

    checked = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )

    assert checked[0].status == "pending"


@pytest.mark.parametrize("proposal_type", ["lint", "test"])
def test_check_target_adopts_existing_symbol(
    tmp_path: Path, proposal_type: learn_from_bugs.ProposalType
) -> None:
    check_path = tmp_path / "crates" / "larch-lint" / "src" / "checks.rs"
    check_path.parent.mkdir(parents=True)
    check_path.write_text("pub fn hosted_check() {}\n", encoding="utf-8")
    proposal = _proposal(
        proposal_type=proposal_type,
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
    )

    checked = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )

    assert checked[0].status == "adopted"
    assert checked[0].adoption_evidence == "target-verified"


def test_check_target_is_pending_when_symbol_is_absent(tmp_path: Path) -> None:
    check_path = tmp_path / "crates" / "larch-lint" / "src" / "checks.rs"
    check_path.parent.mkdir(parents=True)
    check_path.write_text("pub fn hosted_check_extra() {}\n", encoding="utf-8")
    proposal = _proposal(
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
    )

    checked = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )

    assert checked[0].status == "pending"
    assert checked[0].adoption_evidence is None


def test_check_proposals_main_writes_ephemeral_adoption_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_path = tmp_path / "crates" / "larch-lint" / "src" / "checks.rs"
    check_path.parent.mkdir(parents=True)
    check_path.write_text("pub fn hosted_check() {}\n", encoding="utf-8")
    proposal = _proposal(
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
    )
    learn_from_bugs.write_state(
        learn_from_bugs.state_path(tmp_path),
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(proposal,),
        ),
    )
    proposals_out = tmp_path / "checked-proposals.jsonl"
    adoption_out = tmp_path / "adoption-summary.md"
    monkeypatch.setattr(
        learn_from_bugs, "_runner", lambda: RecordingRunner(strict=True)
    )

    assert (
        learn_from_bugs.check_proposals_main(
            [
                "--root",
                str(tmp_path),
                "--repo",
                "o/r",
                "--proposals-out",
                str(proposals_out),
                "--adoption-out",
                str(adoption_out),
            ]
        )
        == 0
    )

    row = json.loads(proposals_out.read_text(encoding="utf-8"))
    assert row["adoption_evidence"] == "target-verified"
    summary = adoption_out.read_text(encoding="utf-8")
    assert "- Adopted: 1 (1 target-verified)" in summary
    assert "- `add-audit-lint`: `target-verified`" in summary
    assert learn_from_bugs.load_proposals_jsonl(proposals_out, root=tmp_path) == (
        _proposal(
            target="check:crates/larch-lint/src/checks.rs#hosted_check",
            status="adopted",
        ),
    )


def test_repository_orphaned_status_remains_orphaned(tmp_path: Path) -> None:
    proposal = _proposal(status="orphaned")

    assert learn_from_bugs.check_proposals(RecordingRunner(strict=True), (proposal,), tmp_path, "o/r")[0].status == "orphaned"


def test_repository_checks_ignore_fenced_architectural_heading(tmp_path: Path) -> None:
    (tmp_path / "ARCHITECTURAL_GUIDELINES.md").write_text(
        "```md\n### G-X-1: Fake\n```\n", encoding="utf-8"
    )
    proposal = _proposal(
        proposal_type="guideline", target="ARCHITECTURAL_GUIDELINES.md#G-X-1"
    )

    checked = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )

    assert checked[0].status == "pending"


def test_filed_issue_status_precedes_repository_target(tmp_path: Path) -> None:
    (tmp_path / "python" / "larch").mkdir(parents=True)
    (tmp_path / "python" / "larch" / "cli.py").write_text(
        '_REGISTRY = {("lint", "audit-lint"): ("module", "main")}\n',
        encoding="utf-8",
    )
    proposal = _proposal(filed_issue=9)
    runner = RecordingRunner(
        responses=[
            _result(
                json.dumps(
                    {"number": 9, "state": "CLOSED", "stateReason": "NOT_PLANNED"}
                )
            )
        ],
        strict=True,
    )

    checked = learn_from_bugs.check_proposals(runner, (proposal,), tmp_path, "o/r")

    assert checked[0].status == "orphaned"
    assert checked[0].adoption_evidence is None


def test_filed_issue_closed_without_target_records_issue_closed_only_evidence(
    tmp_path: Path,
) -> None:
    proposal = _proposal(
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
        filed_issue=9,
    )
    runner = RecordingRunner(
        responses=[
            _result(
                json.dumps(
                    {"number": 9, "state": "CLOSED", "stateReason": "COMPLETED"}
                )
            )
        ],
        strict=True,
    )

    checked = learn_from_bugs.check_proposals(runner, (proposal,), tmp_path, "o/r")

    assert checked[0].status == "adopted"
    assert checked[0].adoption_evidence == "issue-closed-only"


def test_filed_issue_closed_with_target_records_both_evidence(tmp_path: Path) -> None:
    check_path = tmp_path / "crates" / "larch-lint" / "src" / "checks.rs"
    check_path.parent.mkdir(parents=True)
    check_path.write_text("pub fn hosted_check() {}\n", encoding="utf-8")
    proposal = _proposal(
        target="check:crates/larch-lint/src/checks.rs#hosted_check",
        filed_issue=9,
    )
    runner = RecordingRunner(
        responses=[
            _result(
                json.dumps(
                    {"number": 9, "state": "CLOSED", "stateReason": "COMPLETED"}
                )
            )
        ],
        strict=True,
    )

    checked = learn_from_bugs.check_proposals(runner, (proposal,), tmp_path, "o/r")

    assert checked[0].status == "adopted"
    assert checked[0].adoption_evidence == "both"


def test_adoption_summary_orders_pending_and_clamps_future_age() -> None:
    proposals = (
        _proposal("z-last", target="registration:z-last", status="pending"),
        learn_from_bugs.Proposal(
            "a-first", "fix", "fix:a-first", "2026-08-01", "pending"
        ),
        _proposal(
            "adopted-one",
            target="registration:adopted-one",
            status="adopted",
            adoption_evidence="target-verified",
        ),
    )

    summary = learn_from_bugs.render_adoption_summary(
        proposals, today=learn_from_bugs.date(2026, 7, 11)
    )

    assert "Adoption rate: 33.3%" in summary
    assert summary.index("z-last") < summary.index("a-first")
    assert "`a-first`: 0 days" in summary


def test_adoption_summary_renders_evidence_per_row_and_rollup() -> None:
    proposals = (
        _proposal(
            "target-only",
            status="adopted",
            adoption_evidence="target-verified",
        ),
        _proposal(
            "issue-only",
            status="adopted",
            adoption_evidence="issue-closed-only",
        ),
        _proposal("both", status="adopted", adoption_evidence="both"),
    )

    summary = learn_from_bugs.render_adoption_summary(proposals)

    assert "- Adopted: 3 (1 target-verified, 1 issue-closed-only, 1 both)" in summary
    assert "- `target-only`: `target-verified`" in summary
    assert "- `issue-only`: `issue-closed-only`" in summary
    assert "- `both`: `both`" in summary


def test_adoption_summary_marks_adopted_proposal_without_evidence_unavailable() -> None:
    summary = learn_from_bugs.render_adoption_summary((_proposal(status="adopted"),))

    assert "- Adopted: 1 (1 unavailable)" in summary
    assert "- `add-audit-lint`: `unavailable`" in summary


def test_reconcile_keeps_stable_fix_target_and_filed_issue() -> None:
    historical = _proposal("fix-one", "fix", "fix:stable-problem", "pending", 77)
    residual = _proposal("fix-one", "fix", "fix:stable-problem", "proposed")

    assert learn_from_bugs.reconcile_proposals((historical,), (residual,)) == (
        historical,
    )


def test_reconcile_rejects_same_id_with_changed_run_date() -> None:
    historical = _proposal("fix-one", "fix", "fix:stable-problem", "pending")
    residual = _proposal(
        "fix-one",
        "fix",
        "fix:stable-problem",
        "proposed",
        run_date="2026-07-09T00:00:00Z",
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="conflicting stable"):
        learn_from_bugs.reconcile_proposals((historical,), (residual,))


def test_reconcile_applies_same_run_refresh_when_published_matches_base() -> None:
    # Scan start saw pending; this run refreshed it to adopted; the fetched
    # default branch still shows pending (no concurrent publication), so the
    # refresh must survive publication.
    base = _proposal(status="pending")
    remote = _proposal(status="pending")
    local = _proposal(status="adopted")

    (merged,) = learn_from_bugs.reconcile_proposals((remote,), (local,), (base,))

    assert merged.status == "adopted"


def test_reconcile_keeps_concurrent_publication_that_diverged_from_base() -> None:
    # Scan start saw pending; a concurrent run published adopted; this run's
    # residual is a stale pending. The concurrent adopted must win.
    base = _proposal(status="pending")
    remote = _proposal(status="adopted")
    local = _proposal(status="pending")

    (merged,) = learn_from_bugs.reconcile_proposals((remote,), (local,), (base,))

    assert merged.status == "adopted"


def test_reconcile_without_base_keeps_published_status() -> None:
    # No base (empty) preserves the prior keep-published behavior.
    remote = _proposal(status="adopted")
    local = _proposal(status="pending")

    (merged,) = learn_from_bugs.reconcile_proposals((remote,), (local,))

    assert merged.status == "adopted"


def test_reconcile_three_way_preserves_filed_issue_when_keeping_concurrent() -> None:
    # A concurrent publication advanced pending -> adopted and recorded the
    # filed issue; the stale local refresh must revert neither.
    base = _proposal("fix-one", "fix", "fix:x", "pending", 55)
    remote = _proposal("fix-one", "fix", "fix:x", "adopted", 55)
    local = _proposal("fix-one", "fix", "fix:x", "pending", None)

    (merged,) = learn_from_bugs.reconcile_proposals((remote,), (local,), (base,))

    assert merged.status == "adopted"
    assert merged.filed_issue == 55


@pytest.mark.parametrize(
    "patch",
    [
        {"type": "unknown"},
        {"status": "done"},
        {"id": "Not-Kebab"},
        {"filed_issue": 0},
        {"run_date": "not-a-date"},
    ],
)
def test_load_proposals_rejects_malformed_fields(
    tmp_path: Path, patch: dict[str, object]
) -> None:
    path = tmp_path / "proposals.jsonl"
    payload = _proposal().to_json()
    payload.update(patch)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(learn_from_bugs.LearnFromBugsError):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_load_proposals_rejects_missing_field(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    payload = _proposal().to_json()
    del payload["target"]
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(learn_from_bugs.LearnFromBugsError):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_load_proposals_rejects_conflicting_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    first = _proposal().to_json()
    second = _proposal(target="registration:other-lint").to_json()
    path.write_text(
        json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8"
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="conflicting stable"):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_load_proposals_rejects_conflicting_issue_numbers(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    first = _proposal(filed_issue=41).to_json()
    second = _proposal(filed_issue=42).to_json()
    path.write_text(
        json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8"
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="conflicting filed"):
        learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)


def test_safe_target_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-proposal.py"
    outside.write_text("pass\n", encoding="utf-8")
    link = tmp_path / "linked.py"
    try:
        link.symlink_to(outside)
        path = tmp_path / "proposals.jsonl"
        path.write_text(
            json.dumps(_proposal(target="module:linked.py").to_json()) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(
            learn_from_bugs.LearnFromBugsError, match="escapes analysis root"
        ):
            learn_from_bugs.load_proposals_jsonl(path, root=tmp_path)
    finally:
        outside.unlink(missing_ok=True)


def test_pending_proposal_lookup_only_returns_unresolved() -> None:
    pending = _proposal(status="pending")
    adopted = _proposal("adopted", target="registration:adopted", status="adopted")

    assert (
        learn_from_bugs.pending_proposal_by_id((pending, adopted), pending.id)
        == pending
    )
    assert (
        learn_from_bugs.pending_proposal_by_id((pending, adopted), adopted.id) is None
    )


def test_check_proposals_main_does_not_write_outputs_after_failed_issue_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(_proposal(filed_issue=9),),
        ),
    )
    proposals_out = tmp_path / "checked.jsonl"
    adoption_out = tmp_path / "adoption.md"
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(responses=[_result(rc=1, stderr="boom")], strict=True),
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="boom"):
        learn_from_bugs.check_proposals_main(
            [
                "--root",
                str(tmp_path),
                "--repo",
                "o/r",
                "--proposals-out",
                str(proposals_out),
                "--adoption-out",
                str(adoption_out),
            ]
        )

    assert not proposals_out.exists()
    assert not adoption_out.exists()


def test_check_proposals_main_rejects_repository_mismatch(tmp_path: Path) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/durable",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(_proposal(filed_issue=9),),
        ),
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="does not match"):
        learn_from_bugs.check_proposals_main(
            [
                "--root",
                str(tmp_path),
                "--repo",
                "o/caller",
                "--proposals-out",
                str(tmp_path / "checked.jsonl"),
                "--adoption-out",
                str(tmp_path / "adoption.md"),
            ]
        )


def test_check_proposals_main_writes_pre_refresh_base_proposals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = learn_from_bugs.state_path(tmp_path)
    learn_from_bugs.write_state(
        marker,
        learn_from_bugs.LearnFromBugsState(
            run_date="2026-07-09T12:00:00Z",
            repo="o/r",
            search="x",
            state="closed",
            selected_count=1,
            highest_closed_issue_number_scanned=3,
            proposals=(_proposal(status="pending", filed_issue=9),),
        ),
    )
    # The filed issue is closed-completed, so the refresh advances pending ->
    # adopted; the base artifact must still record the pre-refresh pending.
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(
            responses=[
                _result(
                    stdout=json.dumps(
                        {"number": 9, "state": "CLOSED", "stateReason": "COMPLETED"}
                    )
                )
            ],
            strict=True,
        ),
    )
    base_out = tmp_path / "base.jsonl"
    checked_out = tmp_path / "checked.jsonl"

    rc = learn_from_bugs.check_proposals_main(
        [
            "--root", str(tmp_path), "--repo", "o/r",
            "--proposals-out", str(checked_out),
            "--adoption-out", str(tmp_path / "adoption.md"),
            "--base-proposals-out", str(base_out),
        ]
    )
    assert rc == 0

    base_rows = [
        json.loads(line) for line in base_out.read_text().splitlines() if line.strip()
    ]
    checked_rows = [
        json.loads(line) for line in checked_out.read_text().splitlines() if line.strip()
    ]
    assert base_rows[0]["status"] == "pending"
    assert base_rows[0]["filed_issue"] == 9
    assert checked_rows[0]["status"] == "adopted"

    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert "BASE_PROPOSALS_PATH" in out
    assert Path(out["BASE_PROPOSALS_PATH"]).exists()


def test_verify_origin_main_accepts_matching_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(
            responses=[_result(stdout="git@github.com:o/r.git\n")], strict=True
        ),
    )
    assert learn_from_bugs.verify_origin_main(["--root", str(tmp_path), "--repo", "o/r"]) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out["ORIGIN_MATCHES_REPO"] == "true"
    assert out["ORIGIN_REPO"] == "o/r"


def test_verify_origin_main_accepts_case_insensitive_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(
            responses=[_result(stdout="https://github.com/Owner/Repo\n")], strict=True
        ),
    )
    assert (
        learn_from_bugs.verify_origin_main(["--root", str(tmp_path), "--repo", "owner/repo"])
        == 0
    )


def test_verify_origin_main_rejects_mismatched_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(
            responses=[_result(stdout="git@github.com:other/elsewhere.git\n")], strict=True
        ),
    )
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="does not identify"):
        learn_from_bugs.verify_origin_main(["--root", str(tmp_path), "--repo", "o/r"])


def test_verify_origin_main_rejects_unresolvable_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        learn_from_bugs,
        "_runner",
        lambda: RecordingRunner(
            responses=[_result(rc=1, stderr="no such remote")], strict=True
        ),
    )
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="OWNER/REPO slug"):
        learn_from_bugs.verify_origin_main(["--root", str(tmp_path), "--repo", "o/r"])


# --- Out-path canonicalization (macOS default TMPDIR symlink) ---------------


def test_check_proposals_main_accepts_symlinked_ancestor_out_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A symlinked out-path ancestor (like the /var -> /private/var Mac spelling)
    is canonicalized instead of refused; artifacts land in the real directory.
    """
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    proposals_out = alias / "checked-proposals.jsonl"
    adoption_out = alias / "adoption-summary.md"
    monkeypatch.setattr(
        learn_from_bugs, "_runner", lambda: RecordingRunner(responses=[], strict=True)
    )

    rc = learn_from_bugs.check_proposals_main(
        [
            "--root",
            str(tmp_path),
            "--repo",
            "o/r",
            "--proposals-out",
            str(proposals_out),
            "--adoption-out",
            str(adoption_out),
        ]
    )

    assert rc == 0
    assert (real / "checked-proposals.jsonl").is_file()
    assert (real / "adoption-summary.md").is_file()
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines() if "=" in line)
    assert Path(out["CHECKED_PROPOSALS_PATH"]) == real.resolve() / "checked-proposals.jsonl"
    assert Path(out["ADOPTION_SUMMARY_PATH"]) == real.resolve() / "adoption-summary.md"


def test_prepare_main_accepts_symlinked_ancestor_out_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The sibling prepare verb also canonicalizes a symlinked --out ancestor."""
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    rows = [_issue(1, "[BUG] a", STRUCTURED_BODY)]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    monkeypatch.setattr(learn_from_bugs, "_runner", lambda: runner)

    rc = learn_from_bugs.prepare_main(
        [
            "--search",
            learn_from_bugs.DEFAULT_SEARCH,
            "--repo",
            "o/r",
            "--out",
            str(alias / "run"),
            "--root",
            str(tmp_path),
        ]
    )

    assert rc == 0
    assert (real / "run" / "digest.jsonl").is_file()
    assert (real / "run" / "coverage-index.json").is_file()
    assert (real / "run" / "origin-headline.md").is_file()
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines() if "=" in line)
    assert Path(out["DIGEST_PATH"]) == real.resolve() / "run" / "digest.jsonl"


def test_check_proposals_main_refuses_symlinked_destination_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G-Sec-4: a pre-created symlink at the destination leaf is still refused."""
    real = tmp_path / "real"
    real.mkdir()
    elsewhere = tmp_path / "elsewhere.jsonl"
    proposals_out = real / "checked-proposals.jsonl"
    proposals_out.symlink_to(elsewhere)
    adoption_out = real / "adoption-summary.md"
    monkeypatch.setattr(
        learn_from_bugs, "_runner", lambda: RecordingRunner(responses=[], strict=True)
    )

    with pytest.raises(OSError, match="symlink"):
        learn_from_bugs.check_proposals_main(
            [
                "--root",
                str(tmp_path),
                "--repo",
                "o/r",
                "--proposals-out",
                str(proposals_out),
                "--adoption-out",
                str(adoption_out),
            ]
        )

    assert not elsewhere.exists()
    assert not adoption_out.exists()


def test_checked_adoption_becomes_orphaned_after_target_is_removed(
    tmp_path: Path,
) -> None:
    cli_path = tmp_path / "python" / "larch" / "cli.py"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text(
        '_REGISTRY = {("lint", "audit-lint"): ("module", "main")}\n',
        encoding="utf-8",
    )
    proposal = _proposal(status="pending")

    adopted = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), (proposal,), tmp_path, "o/r"
    )
    cli_path.write_text("_REGISTRY = {}\n", encoding="utf-8")
    orphaned = learn_from_bugs.check_proposals(
        RecordingRunner(strict=True), adopted, tmp_path, "o/r"
    )

    assert adopted[0].status == "adopted"
    assert orphaned[0].status == "orphaned"


def test_filed_issue_rejects_unknown_closed_reason() -> None:
    proposal = _proposal(filed_issue=9)
    runner = RecordingRunner(
        responses=[
            _result(
                json.dumps(
                    {"number": 9, "state": "CLOSED", "stateReason": "UNKNOWN"}
                )
            )
        ],
        strict=True,
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="closed issue reason"):
        learn_from_bugs.check_proposals(runner, (proposal,), Path.cwd(), "o/r")


@pytest.mark.parametrize("stdout", ["not JSON", "[]"])
def test_filed_issue_rejects_malformed_json_response(stdout: str) -> None:
    proposal = _proposal(filed_issue=9)
    runner = RecordingRunner(responses=[_result(stdout)], strict=True)

    with pytest.raises(learn_from_bugs.LearnFromBugsError):
        learn_from_bugs.check_proposals(runner, (proposal,), Path.cwd(), "o/r")


# --- Origin classification ---------------------------------------------------


@pytest.mark.parametrize(
    ("text", "ref"),
    [
        ("introduced by #42", 42),
        ("INTRODUCED BY #7", 7),
        ("introduced by PR #99", 99),
        ("introduced by PR#88", 88),
        ("introduced by pr #12", 12),
        ("introduced in #77", 77),
        ("Introduced in #12", 12),
        ("incomplete fix of #55", 55),
        ("Incomplete Fix Of #55", 55),
        ("persists after #100", 100),
        ("residual of #3", 3),
    ],
)
def test_origin_referenced_marker_families(text: str, ref: int) -> None:
    body = f"## Root cause\n\n{text}\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="regression", ref=ref)


def test_origin_bare_regression_has_null_ref() -> None:
    body = "## Root cause\n\nThis is a regression in the flush path.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="regression", ref=None)


def test_origin_no_marker_is_unknown() -> None:
    body = "## Root cause\n\nA plain logic error with no residual language.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="unknown", ref=None)


def test_origin_introduced_in_requires_adjacency() -> None:
    body = "## Root cause analysis\n\nThe defect was introduced early in #12 of the port.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="unknown", ref=None)


@pytest.mark.parametrize(
    "phrase",
    ["never designed", "was never told", "no handling for"],
)
def test_origin_spec_gap_phrases(phrase: str) -> None:
    body = f"## Root cause\n\nThe feature {phrase} this case.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="spec-gap", ref=None)


@pytest.mark.parametrize(
    "phrase",
    ["first time this path ran", "newly added"],
)
def test_origin_new_code_phrases(phrase: str) -> None:
    body = f"## Root cause\n\nThe {phrase} code path failed.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="new-code", ref=None)


def test_origin_referenced_marker_beats_heuristic_phrase() -> None:
    body = "## Root cause\n\npersists after #9 and was never designed for this.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="regression", ref=9)


def test_origin_title_marker_classifies() -> None:
    origin = learn_from_bugs.classify_origin(
        title="[BUG] residual of #44 in ship",
        body="## Root cause\n\nNo body marker.\n",
    )
    assert origin == learn_from_bugs.Origin(kind="regression", ref=44)


def test_origin_scans_past_root_cause_cap() -> None:
    body = "## Root cause\n\n" + ("A" * (learn_from_bugs.ROOT_CAUSE_CAP + 40)) + "\npersists after #77\n"
    digest = learn_from_bugs.build_digest(_issue(2, "[BUG] late", body))
    assert digest.origin == learn_from_bugs.Origin(kind="regression", ref=77)
    assert "persists after" not in digest.sections["root cause"]


def test_origin_scans_past_freeform_cap() -> None:
    body = ("B" * (learn_from_bugs.FREEFORM_CAP + 40)) + "\npersists after #66\n"
    digest = learn_from_bugs.build_digest(_issue(3, "[BUG] late freeform", body))
    assert digest.origin == learn_from_bugs.Origin(kind="regression", ref=66)
    assert digest.structured is False


def test_origin_repeated_root_cause_first_marker_wins() -> None:
    body = (
        "## Root cause\n\npersists after #11\n\n"
        "## Root cause\n\npersists after #22\n"
    )
    origin = learn_from_bugs.classify_origin(title="[BUG] dup", body=body)
    assert origin == learn_from_bugs.Origin(kind="regression", ref=11)


def test_origin_ignores_marker_in_summary_only() -> None:
    body = (
        "## Summary\n\npersists after #5\n\n"
        "## Root cause\n\nNo residual language here.\n\n"
        "## Suggested fix(es)\n\nFix it.\n"
    )
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="unknown", ref=None)


def test_origin_ignores_marker_in_suggested_fix_only() -> None:
    body = (
        "## Summary\n\nBroke.\n\n"
        "## Root cause\n\nOrdinary failure.\n\n"
        "## Suggested fix(es)\n\nThis was introduced by #9.\n"
    )
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="unknown", ref=None)


def test_origin_title_only_ignores_plan_body_markers() -> None:
    body = (
        "<!-- larch:plan:start -->\n"
        "## Plan\n"
        "## Approach\n"
        "persists after #123\n"
        "never designed\n"
    )
    digest = learn_from_bugs.build_digest(_issue(12, "[BUG] plan-only", body))
    assert digest.sections == {"_title_only": ""}
    assert digest.origin == learn_from_bugs.Origin(kind="unknown", ref=None)


def test_origin_freeform_referenced_marker() -> None:
    body = "Something broke; persists after #81 in the flush path.\n"
    origin = learn_from_bugs.classify_origin(title="[BUG] freeform", body=body)
    assert origin == learn_from_bugs.Origin(kind="regression", ref=81)


def test_origin_ignores_marker_after_plan_boundary() -> None:
    body = (
        "## Root cause\n\nOrdinary failure.\n\n"
        "<!-- larch:plan:start -->\n"
        "## Plan\n"
        "## Approach\n"
        "persists after #999\n"
    )
    origin = learn_from_bugs.classify_origin(title="[BUG] x", body=body)
    assert origin == learn_from_bugs.Origin(kind="unknown", ref=None)


def test_build_digest_json_includes_origin() -> None:
    digest = learn_from_bugs.build_digest(
        _issue(10, "[DONE] [BUG] widget", STRUCTURED_BODY)
    )
    payload = digest.to_json()
    assert payload["origin"] == {"kind": "unknown", "ref": None}
    assert digest.title == "[BUG] widget"


# --- Zones ------------------------------------------------------------------


def test_resolve_zones_design_implement_or_group() -> None:
    assert learn_from_bugs.resolve_zone_search("design,implement") == (
        "[BUG] (design OR implement) in:title,body"
    )


def test_resolve_zones_trims_whitespace() -> None:
    assert learn_from_bugs.resolve_zone_search("  design , implement  ") == (
        "[BUG] (design OR implement) in:title,body"
    )


def test_resolve_zones_rejects_empty() -> None:
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="non-empty"):
        learn_from_bugs.resolve_zone_search("   ")


def test_resolve_zones_rejects_empty_element() -> None:
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="empty zone"):
        learn_from_bugs.resolve_zone_search("design,,implement")


def test_resolve_zones_rejects_explicit_search_conflict() -> None:
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="--search"):
        learn_from_bugs.resolve_zone_search("design", has_explicit_search=True)


def test_resolve_zones_rejects_verbal_search_conflict() -> None:
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="verbal"):
        learn_from_bugs.resolve_zone_search("design", has_verbal_search=True)


def test_resolve_zones_preserves_shell_metacharacters() -> None:
    query = learn_from_bugs.resolve_zone_search("design$(boom),impl;rm")
    assert query == "[BUG] (design$(boom) OR impl;rm) in:title,body"


def test_resolve_zones_main_emits_resolved_search(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = learn_from_bugs.resolve_zones_main(["--zones", "design,implement"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip() == "RESOLVED_SEARCH=[BUG] (design OR implement) in:title,body"


# --- Origin headline + report contract --------------------------------------


def _digest_with_origin(
    number: int,
    *,
    kind: learn_from_bugs.OriginKind,
    ref: int | None = None,
    title: str = "[BUG] x",
) -> learn_from_bugs.BugDigest:
    return learn_from_bugs.BugDigest(
        number=number,
        title=title,
        closed_at="2026-07-01",
        url=f"https://github.com/o/r/issues/{number}",
        state="CLOSED",
        structured=True,
        prefix_chars=10,
        sections={"summary": "x"},
        origin=learn_from_bugs.Origin(kind=kind, ref=ref),
    )


def test_render_origin_headline_counts_chains_ratio_and_self_chain() -> None:
    digests = [
        _digest_with_origin(200, kind="regression", ref=100),
        _digest_with_origin(50, kind="regression", ref=None),  # bare: ratio only
        _digest_with_origin(42, kind="regression", ref=42),  # self
        _digest_with_origin(3, kind="new-code"),
        _digest_with_origin(4, kind="spec-gap"),
        _digest_with_origin(5, kind="unknown"),
        _digest_with_origin(6, kind="unknown"),
        _digest_with_origin(7, kind="unknown"),
    ]
    headline = learn_from_bugs.render_origin_headline(digests)
    assert "selected=8" in headline
    assert "- regression: 3 (37.5%)" in headline
    assert "- new-code: 1 (12.5%)" in headline
    assert "- spec-gap: 1 (12.5%)" in headline
    assert "- unknown: 3 (37.5%)" in headline
    assert "#100 -> #200" in headline
    assert "#42 -> #42 (suspect: self-reference)" in headline
    assert "#50 ->" not in headline  # bare omitted from chains
    assert "3/8 (37.5%)" in headline


def test_render_origin_headline_zero_selected() -> None:
    headline = learn_from_bugs.render_origin_headline([])
    assert "selected=0" in headline
    assert "- regression: 0 (0.0%)" in headline
    assert "(none)" in headline
    assert "n/a (0/0)" in headline


def test_validate_report_contract_accepts_valid_report() -> None:
    digests = [_digest_with_origin(200, kind="regression", ref=100)]
    headline = learn_from_bugs.render_origin_headline(digests)
    report = (
        "## 1. Scope and cost\n\ncost\n\n"
        "## 2. Root-cause clusters\n\n"
        f"{headline}\n"
        "### Cluster: parsers\n"
        "Mechanism: duplicated contracts; single-sourcing is the class fix.\n\n"
        "## 3. Already covered (dedup)\n\nnone\n\n"
        "## 6. Proposed guideline entries\n\n"
        f"Marker: {learn_from_bugs.PROSE_ONLY_MARKER}. "
        "Cites #6746 and #6747. Nearest mechanical alternative: lint agent-tool-contract.\n"
    )
    learn_from_bugs.validate_report_contract(report=report, expected_headline=headline)


def test_validate_report_contract_rejects_headline_after_clusters() -> None:
    digests = [_digest_with_origin(200, kind="regression", ref=100)]
    headline = learn_from_bugs.render_origin_headline(digests)
    report = (
        "## 2. Root-cause clusters\n\n"
        "### Cluster: first\n"
        "rows before headline\n\n"
        f"{headline}\n"
    )
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="before cluster"):
        learn_from_bugs.validate_report_contract(report=report, expected_headline=headline)


def test_validate_report_contract_rejects_reversed_chain() -> None:
    digests = [_digest_with_origin(200, kind="regression", ref=100)]
    headline = learn_from_bugs.render_origin_headline(digests)
    altered = headline.replace("#100 -> #200", "#200 -> #100")
    report = f"## 2. Root-cause clusters\n\n{altered}\n"
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="verbatim"):
        learn_from_bugs.validate_report_contract(report=report, expected_headline=headline)


def test_validate_report_contract_rejects_prose_only_missing_citation() -> None:
    digests = [_digest_with_origin(1, kind="unknown")]
    headline = learn_from_bugs.render_origin_headline(digests)
    report = (
        f"## 2. Root-cause clusters\n\n{headline}\n"
        f"## 6. Proposed guideline entries\n\n{learn_from_bugs.PROSE_ONLY_MARKER} "
        "cites #6746 only. Nearest lint: lint-foo.\n"
    )
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="#6747"):
        learn_from_bugs.validate_report_contract(report=report, expected_headline=headline)


def test_validate_report_contract_rejects_prose_only_missing_mechanical_alt() -> None:
    digests = [_digest_with_origin(1, kind="unknown")]
    headline = learn_from_bugs.render_origin_headline(digests)
    report = (
        f"## 2. Root-cause clusters\n\n{headline}\n"
        f"## 6. Proposed guideline entries\n\n{learn_from_bugs.PROSE_ONLY_MARKER} "
        "cites #6746 and #6747 without naming any alternative.\n"
    )
    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="mechanical"):
        learn_from_bugs.validate_report_contract(report=report, expected_headline=headline)


def _filing_dependency_files(
    tmp_path: Path,
    *,
    batch: str,
    proposal_map: str,
    proposal_deps: str,
) -> tuple[Path, Path, Path]:
    batch_path = tmp_path / "batch-issues.md"
    map_path = tmp_path / "proposal-batch-map.tsv"
    deps_path = tmp_path / "proposal-deps.tsv"
    _ = batch_path.write_text(batch, encoding="utf-8")
    _ = map_path.write_text(proposal_map, encoding="utf-8")
    _ = deps_path.write_text(proposal_deps, encoding="utf-8")
    return batch_path, map_path, deps_path


def test_filing_dependencies_maps_invariant_to_named_backing_test(tmp_path: Path) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch=(
            "### Add the invariant\n"
            "Update ARCHITECTURAL_INVARIANTS.md.\n\n"
            "### Add its mechanical backing\n"
            "Add python/tests/core/test_architectural_invariants.py.\n"
        ),
        proposal_map="invariant-owner\t1\nbacking-test\t2\n",
        proposal_deps="backing-test\tinvariant-owner\n",
    )

    edges = learn_from_bugs.filing_dependencies(
        input_file=batch,
        proposal_map_file=proposal_map,
        proposal_deps_file=proposal_deps,
    )

    assert edges == ((2, 1),)


def test_filing_dependencies_serializes_shared_implementation_file(tmp_path: Path) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch=(
            "### First change\n"
            "Update python/larch/issue/learn_from_bugs.py.\n\n"
            "### Second change\n"
            "Also update python/larch/issue/learn_from_bugs.py.\n"
        ),
        proposal_map="first-change\t1\nsecond-change\t2\n",
        proposal_deps="",
    )

    edges = learn_from_bugs.filing_dependencies(
        input_file=batch,
        proposal_map_file=proposal_map,
        proposal_deps_file=proposal_deps,
    )

    assert edges == ((1, 2),)


def test_filing_dependencies_declared_direction_beats_shared_file_order(tmp_path: Path) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch=(
            "### Lint change\n"
            "Update python/larch/lint/lint_example.py.\n\n"
            "### Live violation fix\n"
            "Update python/larch/lint/lint_example.py.\n"
        ),
        proposal_map="lint-change\t1\nlive-fix\t2\n",
        proposal_deps="live-fix\tlint-change\n",
    )

    edges = learn_from_bugs.filing_dependencies(
        input_file=batch,
        proposal_map_file=proposal_map,
        proposal_deps_file=proposal_deps,
    )

    assert edges == ((2, 1),)


def test_filing_dependencies_declared_chain_beats_transitive_shared_cycle(
    tmp_path: Path,
) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch=(
            "### First change\n"
            "Update python/larch/shared.py.\n\n"
            "### Second change\n"
            "Update python/larch/shared.py.\n\n"
            "### Third change\n"
            "Update python/larch/shared.py.\n"
        ),
        proposal_map="first\t1\nsecond\t2\nthird\t3\n",
        proposal_deps="third\tsecond\nsecond\tfirst\n",
    )

    edges = learn_from_bugs.filing_dependencies(
        input_file=batch,
        proposal_map_file=proposal_map,
        proposal_deps_file=proposal_deps,
    )

    assert edges == ((2, 1), (3, 2))


def test_filing_deps_main_writes_empty_tsv_for_disjoint_residuals(tmp_path: Path) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch=(
            "### First change\n"
            "Update python/larch/first.py.\n\n"
            "### Second change\n"
            "Update python/larch/second.py.\n"
        ),
        proposal_map="first-change\t1\nsecond-change\t2\n",
        proposal_deps="",
    )
    output = tmp_path / "intra-batch-deps.tsv"

    rc = learn_from_bugs.filing_deps_main(
        [
            "--input-file",
            str(batch),
            "--proposal-map-file",
            str(proposal_map),
            "--proposal-deps-file",
            str(proposal_deps),
            "--output",
            str(output),
        ]
    )

    assert rc == 0
    assert output.read_text(encoding="utf-8") == ""


def test_filing_dependencies_rejects_unmapped_batch_item(tmp_path: Path) -> None:
    batch, proposal_map, proposal_deps = _filing_dependency_files(
        tmp_path,
        batch="### First\nBody one.\n\n### Second\nBody two.\n",
        proposal_map="first\t1\n",
        proposal_deps="",
    )

    with pytest.raises(learn_from_bugs.LearnFromBugsError, match="does not cover batch item"):
        learn_from_bugs.filing_dependencies(
            input_file=batch,
            proposal_map_file=proposal_map,
            proposal_deps_file=proposal_deps,
        )


def test_run_prepare_writes_origin_headline_and_digest_origin(tmp_path: Path) -> None:
    body = (
        "## Summary\n\nBroke.\n\n"
        "## Root cause analysis\n\npersists after #100\n\n"
        "## Suggested fix(es)\n\nFix.\n"
    )
    rows = [_issue(200, "[BUG] residual", body)]
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
    assert "ORIGIN_HEADLINE_PATH" in stats
    headline = Path(str(stats["ORIGIN_HEADLINE_PATH"])).read_text(encoding="utf-8")
    assert "#100 -> #200" in headline
    assert "1/1 (100.0%)" in headline
    first = json.loads((out_dir / "digest.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert first["origin"] == {"kind": "regression", "ref": 100}
    # DIGEST_CHARS measures full serialized digest including origin.
    assert int(str(stats["DIGEST_CHARS"])) == len(json.dumps(first))


# --- state-publish ----------------------------------------------------------

def _state_publish_args(tmp_path: Path) -> list[str]:
    run_dir = tmp_path / "run"
    run_dir.mkdir(exist_ok=True)
    return [
        "--root", str(tmp_path), "--repo", "o/r", "--run-dir", str(run_dir),
        "--search", "[BUG] in:title", "--state", "closed", "--selected-count", "3",
        "--highest-closed-issue-number-scanned", "10", "--run-date", "2026-07-14T12:00:00Z",
        "--scan-started-at", "2026-07-14T11:00:00Z", "--proposals-file", str(run_dir / "reconciled.jsonl"),
        "--base-proposals-file", str(run_dir / "base.jsonl"),
    ]

def test_state_publish_writes_local_state_without_git(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    state_path = tmp_path / "state/learn-from-bugs/state.json"
    runner = RecordingRunner.strict_queue(_result(f"STATE_PATH={state_path}\n"))
    monkeypatch.setattr(learn_from_bugs, "_runner", lambda: runner)
    assert learn_from_bugs.state_publish_main(_state_publish_args(tmp_path)) == 0
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    assert out == {"STATE_PUBLISH_STATUS": "saved", "STATE_PATH": str(state_path)}
    assert len(runner.calls) == 1
    assert runner.calls[0][2:4] == ["learn-from-bugs", "write-state"]
    assert all(token not in runner.calls[0] for token in ("git", "gh", "pr"))

def test_state_publish_write_failure_has_no_recovery_branch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr(learn_from_bugs, "_runner", lambda: RecordingRunner.strict_queue(_result(rc=1)))
    assert learn_from_bugs.state_publish_main(_state_publish_args(tmp_path)) == 2
    out = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines() if "=" in line)
    assert out == {"STATE_PUBLISH_STATUS": learn_from_bugs.STATE_PUBLISH_WRITE_STATE_FAILED}
