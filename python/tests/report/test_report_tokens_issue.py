from __future__ import annotations

# pylint: disable=unused-argument

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from larch.core import config
from larch.errors import ShipError
from larch.core.proc import CommandResult
from larch.report.report_tokens_issue import assemble_issue_body, post_issue
from larch.report.report_tokens_models import ReportSection, SectionPriority


def _calls() -> list[list[str]]:
    return []


@dataclass
class Runner:
    result: CommandResult
    calls: list[list[str]] = field(default_factory=_calls)

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
        self.calls.append(list(argv))
        return self.result


def test_tmpdir_scrub_and_raw_data_absent() -> None:
    sections = [ReportSection("summary", "/tmp/larch-report-tokens.abc/file\n", SectionPriority.SUMMARY)]
    body = assemble_issue_body(sections, skill="implement")
    assert "/tmp/larch-report-tokens" not in body
    assert "Raw per-issue data" not in body


def test_post_issue_uses_repo_option_and_surfaces_redacted_failure(capsys: pytest.CaptureFixture[str]) -> None:
    runner = Runner(CommandResult(("gh",), 1, "", "body is too long ghp_abcdefghijklmnopqrstuvwx", 0.01))
    with pytest.raises(ShipError):
        post_issue(runner, repo="o/r", title="t", sections=[ReportSection("s", "body", SectionPriority.SUMMARY)], skill="implement")
    assert "--repo" in runner.calls[0]
    err = capsys.readouterr().err
    assert "body is too long" in err
    assert "ghp_abcdefghijklmnopqrstuvwx" not in err


def test_trim_notice_uses_reader_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GITHUB_ISSUE_BODY_MAX_BYTES", 245)
    body = assemble_issue_body([
        ReportSection("summary", "## Report Tokens Analysis\n\nok", SectionPriority.SUMMARY),
        ReportSection("trends", "## Per-day cost trends\n\n" + ("x" * 200), SectionPriority.TRENDS),
    ], skill="implement")
    assert "Per-day cost trends" in body
    omitted = body.partition("Omitted sections: ")[2].split(".", 1)[0]
    assert omitted != "trends"
    assert "trends" not in omitted.split(", ")


def test_post_issue_fails_when_body_still_oversize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GITHUB_ISSUE_BODY_MAX_BYTES", 20)
    runner = Runner(CommandResult(("gh",), 0, "", "", 0.01))
    with pytest.raises(ShipError):
        post_issue(
            runner,
            repo="o/r",
            title="t",
            sections=[ReportSection("summary", "## Report Tokens Analysis\n\nrequired", SectionPriority.SUMMARY)],
            skill="implement",
        )
    assert not runner.calls


def test_post_issue_prints_created_url(capsys: pytest.CaptureFixture[str]) -> None:
    runner = Runner(CommandResult(("gh",), 0, "https://github.com/o/r/issues/9\n", "", 0.01))
    post_issue(runner, repo="o/r", title="t", sections=[ReportSection("summary", "body", SectionPriority.SUMMARY)], skill="implement")
    assert "https://github.com/o/r/issues/9" in capsys.readouterr().out


def test_trim_notice_aggregate_label_implement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GITHUB_ISSUE_BODY_MAX_BYTES", 245)
    body = assemble_issue_body([
        ReportSection("summary", "## Report Tokens Analysis\n\nok", SectionPriority.SUMMARY),
        ReportSection("aggregate", "## Aggregate cost\n\n" + ("x" * 200), SectionPriority.AGGREGATE),
    ], skill="implement")
    omitted = body.partition("Omitted sections: ")[2].split(".", 1)[0]
    assert "Aggregate cost" in omitted
    assert "Aggregate cost by workflow" not in omitted


def test_trim_notice_aggregate_label_design(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GITHUB_ISSUE_BODY_MAX_BYTES", 245)
    body = assemble_issue_body([
        ReportSection("summary", "## Report Tokens Analysis\n\nok", SectionPriority.SUMMARY),
        ReportSection("aggregate", "## Aggregate cost by workflow\n\n" + ("x" * 200), SectionPriority.AGGREGATE),
    ], skill="design")
    omitted = body.partition("Omitted sections: ")[2].split(".", 1)[0]
    assert "Aggregate cost by workflow" in omitted
