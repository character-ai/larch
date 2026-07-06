# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
"""Offline tests for learn_from_bugs.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.issue import learn_from_bugs
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


def test_run_prepare_writes_artifacts_and_stats(tmp_path: Path) -> None:
    rows = [_issue(1, "[BUG] a", STRUCTURED_BODY), _issue(2, "[BUG] b", FREEFORM_BODY)]
    runner = RecordingRunner(responses=[_result(json.dumps(rows))], strict=True)
    out_dir = tmp_path / "run"
    request = learn_from_bugs.PrepareRequest(
        search="[BUG] in:title",
        state="closed",
        limit=10,
        repo_explicit="o/r",
        out_dir=out_dir,
        root=tmp_path,
    )
    stats = learn_from_bugs.run_prepare(runner, request)
    assert stats["ISSUES_SELECTED"] == 2
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
