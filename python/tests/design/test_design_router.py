"""Tests for /design router KV parsing helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from larch import io as larch_io
from larch.design import design_router
from larch.issue.issue_wire import compose_named_block


def test_router_stdout_codec_preserves_ordered_duplicates() -> None:
    parsed = design_router._parse_stdout_kv(  # pyright: ignore[reportPrivateUsage]
        "WARN=first\nSTEP=old\nWARN=second\nSTEP=latest\n"
    )
    assert parsed == {"WARN": ["first", "second"], "STEP": ["old", "latest"]}


def test_router_rename_stdout_uses_last_match() -> None:
    text = "RENAMED=false\nRENAMED=true\nOTHER=x\n"
    assert larch_io.kv_value(text=text, key="RENAMED", duplicate_policy="last") == "true"


def test_parse_stdout_kv_collects_repeated_keys_in_order() -> None:
    result = design_router._parse_stdout_kv("WARN=first\nWARN=second\nROUTE=ok\n")  # pyright: ignore[reportPrivateUsage]
    assert result["WARN"] == ["first", "second"]
    assert result["ROUTE"] == ["ok"]


def test_parse_stdout_kv_preserves_first_occurrence_order() -> None:
    result = design_router._parse_stdout_kv("B=1\nA=2\nB=3\nA=4\n")  # pyright: ignore[reportPrivateUsage]
    assert list(result.keys()) == ["B", "A"]
    assert result["B"] == ["1", "3"]
    assert result["A"] == ["2", "4"]


def test_parse_stdout_kv_skips_lines_without_equals() -> None:
    result = design_router._parse_stdout_kv("NOEQUALS\nKEY=val\n\n")  # pyright: ignore[reportPrivateUsage]
    assert result == {"KEY": ["val"]}


def test_parse_stdout_kv_handles_embedded_equals() -> None:
    result = design_router._parse_stdout_kv("URL=https://example.com/?a=1\n")  # pyright: ignore[reportPrivateUsage]
    assert result["URL"] == ["https://example.com/?a=1"]


def test_designed_issue_with_plan_routes_to_already_planned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    issue_body = design_tmpdir / "issue.md"
    _ = issue_body.write_text(
        compose_named_block(marker="plan", inner="Plan\n"), encoding="utf-8"
    )

    def title_eligibility(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            0,
            "LIFECYCLE_REJECT=true\nLIFECYCLE_MARKER=[DESIGNED]\n",
            "",
        )

    monkeypatch.setattr(design_router.subprocess, "run", title_eligibility)
    assert design_router.route_main(
        [
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            "7",
            "--issue-title",
            "[DESIGNED] Work",
            "--issue-body-file",
            str(issue_body),
            "--has-clarify-label",
            "false",
            "--claude-pid",
            "1",
            "--session-id",
            "session",
        ]
    ) == 0
    assert "ROUTE=already-planned\n" in capsys.readouterr().out


@pytest.mark.parametrize(
    "marker",
    [("[IMPLEMENTING]",), ("[DONE]",), ("[DEBATING]",)],
)
def test_non_designed_lifecycle_markers_remain_rejected(
    marker: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    issue_body = design_tmpdir / "issue.md"
    _ = issue_body.write_text(
        compose_named_block(marker="plan", inner="Plan\n"), encoding="utf-8"
    )

    def title_eligibility(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv,
            0,
            f"LIFECYCLE_REJECT=true\nLIFECYCLE_MARKER={marker}\n",
            "",
        )

    monkeypatch.setattr(design_router.subprocess, "run", title_eligibility)
    assert design_router.route_main(
        [
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            "7",
            "--issue-title",
            f"{marker} Work",
            "--issue-body-file",
            str(issue_body),
            "--has-clarify-label",
            "false",
            "--claude-pid",
            "1",
            "--session-id",
            "session",
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "ROUTE=cancel-title-filter\n" in output
    assert "TITLE_FILTER_REASON=lifecycle\n" in output
    assert f"TITLE_FILTER_MARKER={marker}\n" in output
