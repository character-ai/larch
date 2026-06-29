"""Tests for shared exec issue detail parsing and rendering."""
# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from larch.core import config
from larch.core.proc import CommandResult
from larch.report import exec_issue_detail

if TYPE_CHECKING:
    import pytest


def test_parses_markdown_sections_fence_aware_and_ignores_other_sections() -> None:
    groups = exec_issue_detail.parse_markdown_execution_issues(
        "### Tool Failures\n"
        "- **lint**: drift\n"
        "```text\n- hidden\n```\n"
        "### Notes\n- ignored\n"
        "### Warnings\n- plain warning\n"
    )

    assert exec_issue_detail.count_issue_groups(groups) == (1, 1)
    assert groups.exec_issues[0].display_text == "lint: drift"
    assert groups.warnings[0].display_text == "plain warning"


def test_section_heading_inside_open_fence_is_boundary() -> None:
    result = exec_issue_detail.LoadResult(
        exec_issue_detail.parse_markdown_execution_issues(
            "### Tool Failures\n- exec1\n```\nlog line\n### Warnings\n- warn1\n"
        ),
        listing_degraded=False,
    )

    assert exec_issue_detail.count_load_result(result) == (1, 1)
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "1. exec1" in block
    assert "1. warn1" in block


def test_bold_suffix_duplicate_collapse_and_distinct_suffixes() -> None:
    result = exec_issue_detail.LoadResult(
        exec_issue_detail.parse_markdown_execution_issues(
            "### Warnings\n"
            "- **lint**: drift\n"
            "- **lint**: drift\n"
            "- **lint**: timeout\n"
        ),
        listing_degraded=False,
    )

    assert exec_issue_detail.count_load_result(result) == (0, 3)
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "Warnings (3):" in block
    assert "1. lint: drift \u00d72" in block
    assert "2. lint: timeout" in block


def test_render_excludes_fenced_diagnostic_body_and_truncates() -> None:
    long_text = "x" * (exec_issue_detail.MAX_DISPLAY_LEN + 30)
    result = exec_issue_detail.LoadResult(
        exec_issue_detail.parse_markdown_execution_issues(
            f"### Tool Failures\n- {long_text}\n```\n- fenced secret diagnostic\n```\n"
        ),
        listing_degraded=False,
    )

    display = result.groups.exec_issues[0].display_text
    assert len(display) <= exec_issue_detail.MAX_DISPLAY_LEN
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "fenced secret diagnostic" not in block


def test_load_structured_ndjson_rows_and_plain_fallback(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows = [
        {"category": "Tool Failures", "body": "- a\n- **step**: b\n"},
        {"category": "Warnings", "body": "plain warning row"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert not result.listing_degraded
    assert exec_issue_detail.count_load_result(result) == (2, 1)
    assert result.groups.warnings[0].display_text == "plain warning row"


def test_legacy_body_text_fallback_lists_rows(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows: list[object] = [
        "legacy",
        {"body": "### Tool Failures\n- a\n- b"},
        {"body": "### Warnings\n- c"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert not result.listing_degraded
    assert exec_issue_detail.count_load_result(result) == (2, 1)
    assert "1. a" in exec_issue_detail.render_issue_detail_block(result, assess=False)


def test_legacy_string_count_only_fallback_header_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    body = '{"category":"Tool Failures"}\n{"category":"External Reviewer Issues"}\n{"category":"Warnings"}'
    rows: list[object] = ["legacy", {"body": body}]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)
    block = exec_issue_detail.render_issue_detail_block(result, assess=True)

    assert result.listing_degraded
    assert result.degraded_totals == (2, 1)
    assert exec_issue_detail.count_load_result(result) == (2, 1)
    assert "Exec Issues (2):" in block
    assert "Warnings (1):" in block
    assert "  1." not in block


def test_assessment_uses_model_default_and_claude_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    prompt_texts: list[str] = []
    inner = json.dumps({"assessments": [{"id": "0", "assessment": "Operators should inspect this warning."}]})

    def fake_run(argv: list[str], **_kwargs: Any) -> CommandResult:
        calls.append(argv)
        prompt_texts.append(Path(argv[argv.index("--prompt-file") + 1]).read_text(encoding="utf-8"))
        _ = Path(argv[argv.index("--output-file") + 1]).write_text(inner, encoding="utf-8")
        return CommandResult(argv=tuple(argv), returncode=0, stdout="", stderr="", duration=0.0)

    monkeypatch.delenv(config.ENV_LARCH_EXEC_ISSUE_ASSESSMENT_MODEL, raising=False)
    monkeypatch.setattr("larch.core.proc.run", fake_run)  # type: ignore[arg-type]
    detail = exec_issue_detail.IssueDetail("lint", "drift", "lint: drift", 1)

    assessments = exec_issue_detail.assess_issue_details("Warnings", (detail,))

    assert assessments == {"0": "Operators should inspect this warning."}
    assert calls[0][calls[0].index("--model") + 1] == config.EXEC_ISSUE_ASSESSMENT_MODEL_DEFAULT
    assert '"id": "0"' in prompt_texts[0]


def test_assessment_model_override_and_prompt_redaction(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    prompt_texts: list[str] = []
    raw_secret = "sk-" + "a" * 32
    inner = json.dumps({"assessments": [{"id": "0", "assessment": "Secret-bearing row was redacted."}]})

    def fake_run(argv: list[str], **_kwargs: Any) -> CommandResult:
        calls.append(argv)
        prompt_texts.append(Path(argv[argv.index("--prompt-file") + 1]).read_text(encoding="utf-8"))
        _ = Path(argv[argv.index("--output-file") + 1]).write_text(inner, encoding="utf-8")
        return CommandResult(argv=tuple(argv), returncode=0, stdout="", stderr="", duration=0.0)

    monkeypatch.setenv(config.ENV_LARCH_EXEC_ISSUE_ASSESSMENT_MODEL, "test-haiku")
    monkeypatch.setattr("larch.core.proc.run", fake_run)  # type: ignore[arg-type]
    detail = exec_issue_detail.IssueDetail("", raw_secret, raw_secret, 1)

    _ = exec_issue_detail.assess_issue_details("Warnings", (detail,))

    assert calls[0][calls[0].index("--model") + 1] == "test-haiku"
    assert raw_secret not in prompt_texts[0]
    assert "<REDACTED-TOKEN>" in prompt_texts[0]


def test_render_attaches_assessments_and_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    groups = exec_issue_detail.IssueDetailGroups(
        (exec_issue_detail.IssueDetail("step", "failed", "step: failed", 1),),
        (),
    )
    result = exec_issue_detail.LoadResult(groups, listing_degraded=False)

    def fake_assess(_category: str, _details: tuple[exec_issue_detail.IssueDetail, ...]) -> dict[str, str]:
        return {"0": "This may block operators until the tool failure is resolved."}

    monkeypatch.setattr(exec_issue_detail, "assess_issue_details", fake_assess)
    assert "    This may block operators" in exec_issue_detail.render_issue_detail_block(result)

    def no_assess(_category: str, _details: tuple[exec_issue_detail.IssueDetail, ...]) -> dict[str, str]:
        return {}

    monkeypatch.setattr(exec_issue_detail, "assess_issue_details", no_assess)
    assert "This may block operators" not in exec_issue_detail.render_issue_detail_block(result)


def test_bad_claude_envelopes_and_inner_payloads_fail_closed() -> None:
    assert exec_issue_detail._unwrap_claude_json_result('{"is_error":true,"result":"{}"}') is None
    assert exec_issue_detail._unwrap_claude_json_result('{"is_error":false,"result":""}') is None
    assert not exec_issue_detail._parse_assessments_payload('{"assessments": "bad"}')
    assert exec_issue_detail._parse_assessments_payload('{"assessments":[{"id":"0","assessment":"ok"},{"id":"1","assessment":""}]}') == {"0": "ok"}


def test_render_redacts_outbound_secret() -> None:
    raw_secret = "sk-" + "b" * 32
    groups = exec_issue_detail.IssueDetailGroups(
        (),
        (exec_issue_detail.IssueDetail("", raw_secret, raw_secret, 1),),
    )
    block = exec_issue_detail.render_issue_detail_block(exec_issue_detail.LoadResult(groups, listing_degraded=False), assess=False)

    assert raw_secret not in block
    assert "<REDACTED-TOKEN>" in block


def test_display_text_redacts_before_truncation() -> None:
    prefix = "x" * (exec_issue_detail.MAX_DISPLAY_LEN - 8)
    raw_secret = "sk-" + "a" * 32
    raw = prefix + raw_secret
    groups = exec_issue_detail.parse_markdown_execution_issues(f"### Warnings\n- {raw}\n")

    display = groups.warnings[0].display_text
    assert len(display) <= exec_issue_detail.MAX_DISPLAY_LEN
    assert "sk-" not in display
    assert raw_secret not in display


def test_mixed_valid_and_malformed_ndjson_rows(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    ndjson = (
        '{"category":"Warnings","body":"- warn one"}\n'
        "not-json\n"
        '{"category":"Tool Failures","body":"- exec one"}\n'
    )
    _ = (run_dir / "execution-issues.ndjson").write_text(ndjson, encoding="utf-8")

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert not result.listing_degraded
    assert exec_issue_detail.count_load_result(result) == (1, 1)
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "Warnings (1):" in block
    assert "1. warn one" in block
    assert "1. exec one" in block


def test_fallback_dedupe_uses_full_body_not_first_line_only() -> None:
    body = "shared first line\nunique tail alpha\n"
    event_a = exec_issue_detail._fallback_event(body, "Warnings")  # pyright: ignore[reportPrivateUsage]
    event_b = exec_issue_detail._fallback_event("shared first line\nunique tail beta\n", "Warnings")  # pyright: ignore[reportPrivateUsage]
    assert event_a.display_text == event_b.display_text
    assert event_a.dedupe_key != event_b.dedupe_key


def test_assessment_subprocess_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **_kwargs: Any) -> CommandResult:
        return CommandResult(argv=tuple(argv), returncode=127, stdout="", stderr="timeout", duration=0.0)

    monkeypatch.setattr("larch.core.proc.run", fake_run)  # type: ignore[arg-type]
    detail = exec_issue_detail.IssueDetail("lint", "drift", "lint: drift", 1)
    assert not exec_issue_detail.assess_issue_details("Warnings", (detail,))
    result = exec_issue_detail.LoadResult(exec_issue_detail.IssueDetailGroups((), (detail,)), listing_degraded=False)
    block = exec_issue_detail.render_issue_detail_block(result, assess=True)
    assert "1. lint: drift" in block
    assert "Assessment" not in block


def test_empty_markdown_falls_back_to_ndjson(tmp_path: Path) -> None:
    _ = (tmp_path / "execution-issues.md").touch()
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows = [
        {"category": "Tool Failures", "body": "- exec one"},
        {"category": "Warnings", "body": "- warn one"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert not result.listing_degraded
    assert exec_issue_detail.count_load_result(result) == (1, 1)
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "1. exec one" in block
    assert "1. warn one" in block


def test_all_dict_ndjson_without_category_keys_uses_body_concat(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    rows = [
        {"body": "### Tool Failures\n- a"},
        {"body": "### Warnings\n- b"},
    ]
    _ = (run_dir / "execution-issues.ndjson").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert not result.listing_degraded
    assert exec_issue_detail.count_load_result(result) == (1, 1)
    block = exec_issue_detail.render_issue_detail_block(result, assess=False)
    assert "1. a" in block
    assert "1. b" in block


def test_assessment_subprocess_nonzero_exit_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **_kwargs: Any) -> CommandResult:
        return CommandResult(argv=tuple(argv), returncode=1, stdout="", stderr="failed", duration=0.0)

    monkeypatch.setattr("larch.core.proc.run", fake_run)  # type: ignore[arg-type]
    detail = exec_issue_detail.IssueDetail("lint", "drift", "lint: drift", 1)
    assert not exec_issue_detail.assess_issue_details("Warnings", (detail,))
    result = exec_issue_detail.LoadResult(exec_issue_detail.IssueDetailGroups((), (detail,)), listing_degraded=False)
    block = exec_issue_detail.render_issue_detail_block(result, assess=True)
    assert "1. lint: drift" in block
    assert "Assessment" not in block


def test_warn_count_includes_dynamic_drop_warning_from_execution_issues_md(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (tmp_path / "execution-issues.md").write_text(
        "### Warnings\n"
        "- **code-review panel (round 1)**: dynamic reviewer slot drop/failure detected "
        "(failed=0, dropped=1, stragglers=1); review continued with the remaining panel output.\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert exec_issue_detail.count_load_result(result) == (0, 1)


def test_warn_count_zero_for_static_only_straggler_execution_issues_md(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    _ = (tmp_path / "execution-issues.md").write_text("### Warnings\n", encoding="utf-8")

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert exec_issue_detail.count_load_result(result) == (0, 0)


def test_warn_count_persists_dynamic_drop_after_retry_execution_issues_ndjson(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    warning = (
        "- **code-review panel (round 1)**: dynamic reviewer slot drop/failure detected "
        "(failed=0, dropped=1, stragglers=0); review continued with the remaining panel output."
    )
    _ = (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": warning}) + "\n",
        encoding="utf-8",
    )

    result = exec_issue_detail.load_issue_detail_groups(tmp_path, run_dir=run_dir)

    assert exec_issue_detail.count_load_result(result) == (0, 1)
    assert "dynamic reviewer slot drop/failure" in result.groups.warnings[0].display_text
