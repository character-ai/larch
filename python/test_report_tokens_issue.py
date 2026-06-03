from __future__ import annotations

# pylint: disable=unused-argument

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

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
