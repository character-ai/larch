from __future__ import annotations

# pylint: disable=unused-argument

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

import config
from errors import ShipError
from proc import CommandResult
from report_tokens_issue import assemble_issue_body, post_issue
from report_tokens_models import ReportSection, SectionPriority


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
    body = assemble_issue_body(sections)
    assert "/tmp/larch-report-tokens" not in body
    assert "Raw per-issue data" not in body


def test_post_issue_uses_repo_option_and_surfaces_failure() -> None:
    runner = Runner(CommandResult(("gh",), 1, "", "body is too long", 0.01))
    with pytest.raises(ShipError):
        post_issue(runner, repo="o/r", title="t", sections=[ReportSection("s", "body", SectionPriority.SUMMARY)])
    assert "--repo" in runner.calls[0]


def test_trim_notice_uses_reader_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "GITHUB_ISSUE_BODY_MAX_BYTES", 245)
    body = assemble_issue_body([
        ReportSection("summary", "## Report Tokens Analysis\n\nok", SectionPriority.SUMMARY),
        ReportSection("trends", "## Per-day cost trends\n\n" + ("x" * 200), SectionPriority.TRENDS),
    ])
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
        )
    assert not runner.calls
