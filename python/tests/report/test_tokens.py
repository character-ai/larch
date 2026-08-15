"""Tests for tokens.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest

from larch.core import config
from larch.report import tokens


def test_normalize_sidecar_codex() -> None:
    record = tokens.normalize_sidecar(
        {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_tokens": 1,
            "cache_create_tokens": 0,
        },
        tool="codex",
    )
    assert record is not None
    assert record.total_tokens == 16
    assert record.tool == "codex"


def test_normalize_sidecar_cursor() -> None:
    record = tokens.normalize_sidecar(
        {
            "total_tokens": 17,
            "input_tokens": 11,
            "output_tokens": 6,
        },
        tool="cursor",
    )
    assert record is not None
    assert record.total_tokens == 17
    assert record.tool == "cursor"


def test_scrape_run_empty_is_noop(tmp_path: Path) -> None:
    out = tmp_path / "tokens.ndjson"
    records = tokens.scrape_run(sidecar_paths=(), output_path=out)
    assert not records
    assert not out.exists()


def test_append_token_record(tmp_path: Path) -> None:
    path = tmp_path / "out.ndjson"
    record = tokens.TokenRecord("cursor", 3, 1, 2, 0, 0)
    tokens.append_token_record(path=path, record=record)
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["tool"] == "cursor"


def test_scrape_run_timing_sidecar(tmp_path: Path) -> None:
    timing = tmp_path / "cursor-timing.json"
    _ = timing.write_text('{"duration_ms": 1200}', encoding="utf-8")
    out = tmp_path / "timing.ndjson"
    _ = tokens.scrape_run(
        timing_sidecar_paths=(("cursor", timing),),
        timing_output_path=out,
    )
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["duration_ms"] == 1200


def test_scrape_run_token_sidecar_path(tmp_path: Path) -> None:
    sidecar = tmp_path / "cursor-tokens.json"
    _ = sidecar.write_text('{"input_tokens": 2, "output_tokens": 3}', encoding="utf-8")
    out = tmp_path / "tokens.ndjson"
    records = tokens.scrape_run(
        sidecar_paths=(("cursor", sidecar),),
        output_path=out,
    )
    assert records[0].tool == "cursor"
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["total_tokens"] == 5


def test_claude_rows_dedupe_splits_cache_buckets_without_ids() -> None:
    rows = [
        {
            "type": "assistant",
            "timestamp": "2025-01-01T00:00:00Z",
            "usage": {
                "input_tokens": 1,
                "cache_read_input_tokens": 2,
                "output_tokens": 3,
                "cache_creation": {"ephemeral_5m_input_tokens": 4, "ephemeral_1h_input_tokens": 0},
            },
        },
        {
            "type": "assistant",
            "timestamp": "2025-01-01T00:00:01Z",
            "usage": {
                "input_tokens": 1,
                "cache_read_input_tokens": 2,
                "output_tokens": 3,
                "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 4},
            },
        },
    ]
    out = tokens._claude_rows(transcript_rows=rows, marks=[{"ts": 0.0, "step": "Step 0"}])  # pyright: ignore[reportPrivateUsage]
    assert len(out) == 2


def test_token_claude_source_requires_complete_snapshot(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    snap = tmp_path / "source.env"
    _ = snap.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    out = tokens.token_claude_source(claude_source_file=snap, env={"HOME": str(tmp_path)})
    assert not out.available
    assert out.reason


def test_token_cost_helpers_exported_from_tokens_module() -> None:
    assert tokens.token_cost_from_args(["--claude-input-tokens", "1"])
    assert tokens.render_cost_line_from_args(["--claude-input-tokens", "1"])
    assert tokens.CostBreakdown is not None


def test_token_claude_source_rejects_transcript_outside_session_dir(tmp_path: Path) -> None:
    transcript = tmp_path / "outside.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    session_dir = tmp_path / "session-uuid"
    session_dir.mkdir()
    snap = tmp_path / "source.env"
    _ = snap.write_text(
        f"TRANSCRIPT_PATH={transcript}\nSESSION_DIR={session_dir}\nSESSION_UUID=session-uuid\n",
        encoding="utf-8",
    )
    out = tokens.token_claude_source(claude_source_file=snap, env={"HOME": str(tmp_path)})
    assert not out.available
    assert out.reason


def test_token_claude_source_accepts_complete_snapshot(tmp_path: Path) -> None:
    session_dir = tmp_path / "session-uuid"
    session_dir.mkdir()
    transcript = session_dir / "session.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    snap = tmp_path / "source.env"
    _ = snap.write_text(
        f"TRANSCRIPT_PATH={transcript}\nSESSION_DIR={session_dir}\nSESSION_UUID=session-uuid\n",
        encoding="utf-8",
    )
    out = tokens.token_claude_source(claude_source_file=snap)
    assert out.available
    assert out.transcript_path == transcript.resolve()
    assert out.session_dir == session_dir
    assert out.session_uuid == "session-uuid"
    with pytest.raises(FrozenInstanceError):
        out.reason = "changed"  # type: ignore[misc]


def test_find_latest_claude_transcript_uses_ambient_claude_sid(tmp_path: Path) -> None:
    sid = "claude-session-1"
    transcript = tmp_path / f"{sid}.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")

    latest, requested_sid = tokens._find_latest_claude_transcript(  # pyright: ignore[reportPrivateUsage]
        project_dir=tmp_path,
        env_map={"CLAUDE_CODE_SESSION_ID": sid},
    )

    assert latest == transcript
    assert requested_sid == sid


def test_find_latest_claude_transcript_sid_miss_fails_closed(tmp_path: Path) -> None:
    _ = (tmp_path / "newer.jsonl").write_text('{"type":"user"}\n', encoding="utf-8")

    latest, requested_sid = tokens._find_latest_claude_transcript(  # pyright: ignore[reportPrivateUsage]
        project_dir=tmp_path,
        env_map={"CLAUDE_CODE_SESSION_ID": "missing-sid"},
    )

    assert latest is None
    assert requested_sid == "missing-sid"


def test_find_latest_claude_transcript_without_sid_uses_newest(tmp_path: Path) -> None:
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    _ = old.write_text('{"type":"user"}\n', encoding="utf-8")
    _ = new.write_text('{"type":"user"}\n', encoding="utf-8")
    os.utime(old, (1, 1))
    os.utime(new, (2, 2))

    latest, requested_sid = tokens._find_latest_claude_transcript(  # pyright: ignore[reportPrivateUsage]
        project_dir=tmp_path,
        env_map={},
    )

    assert latest == new
    assert requested_sid == ""


def test_find_latest_claude_transcript_ignores_legacy_token_session_id(tmp_path: Path) -> None:
    newest = tmp_path / "real-claude-session.jsonl"
    _ = newest.write_text('{"type":"user"}\n', encoding="utf-8")

    latest, requested_sid = tokens._find_latest_claude_transcript(  # pyright: ignore[reportPrivateUsage]
        project_dir=tmp_path,
        env_map={"LARCH_TOKEN_SESSION_ID": "larch-run-id"},
    )

    assert latest == newest
    assert requested_sid == ""


def test_replace_block_ignores_prose_marker_mentions(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    _ = target.write_text(
        "Mention <!-- token-report-begin --> in prose\n\n"
        "<!-- token-report-begin -->\nold\n<!-- token-report-end -->\n",
        encoding="utf-8",
    )
    tokens._replace_block(target=target, block="BLOCK\n", begin="token-report-begin", end="token-report-end")  # pyright: ignore[reportPrivateUsage]
    text = target.read_text(encoding="utf-8")
    assert "Mention <!-- token-report-begin --> in prose" in text
    assert "BLOCK" in text
    assert "old" not in text


def test_check_step_token_budget_resets_at_mark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "token-ledger.jsonl"
    rows = [
        {"type": "vendor", "vendor": "codex", "total": 100, "ts": "1"},
        {"type": "mark", "step": "Step 1", "ts": "2"},
        {"type": "vendor", "vendor": "cursor", "total": 50, "ts": "3"},
    ]
    _ = ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_TOKEN_LEDGER", str(ledger))
    under = tokens.check_step_token_budget(cap=100, step="Step 1")
    over = tokens.check_step_token_budget(cap=40, step="Step 1")
    assert under.status == "under_cap"
    assert over.status == "cap_hit"
    assert over.total == 50
    with pytest.raises(FrozenInstanceError):
        over.total = 0  # type: ignore[misc]


def _token_report_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    ledger = tmp_path / "ledger.jsonl"
    transcript = tmp_path / "transcript.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 1 - design", "ts": "2026-05-06T00:00:00Z"},
                {"type": "vendor", "vendor": "codex", "total": 100, "ts": "2026-05-06T00:00:05Z"},
                {"type": "mark", "step": "Step 2 - implement", "ts": "2026-05-06T00:01:00Z"},
                {
                    "type": "vendor",
                    "vendor": "cursor",
                    "input": 1,
                    "output": 2,
                    "cache_read": 3,
                    "cache_create": 4,
                    "total": 10,
                    "ts": "2026-05-06T00:01:03Z",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _ = transcript.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "type": "assistant",
                    "timestamp": "2026-05-06T00:00:03.100Z",
                    "attributionSkill": "larch:design",
                    "message": {
                        "usage": {
                            "input_tokens": 1,
                            "cache_read_input_tokens": 2,
                            "cache_creation_input_tokens": 3,
                            "output_tokens": 4,
                        }
                    },
                },
                {
                    "type": "assistant",
                    "timestamp": "2026-05-06T00:01:03.100Z",
                    "attributionSkill": "larch:implement",
                    "message": {
                        "usage": {
                            "input_tokens": 10,
                            "cache_read_input_tokens": 20,
                            "cache_creation_input_tokens": 30,
                            "output_tokens": 40,
                        }
                    },
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return ledger, transcript


def test_token_report_full_json_markdown_and_terse(tmp_path: Path) -> None:
    ledger, transcript = _token_report_fixtures(tmp_path)
    terse = tokens.token_report(
        ledger_path=ledger,
        transcript_path=transcript,
        mode="terse",
        since_last_mark=True,
    )
    assert "Step 2 - implement: claude=100 tokens" in terse
    assert "vendor=10" in terse
    markdown = tokens.token_report(ledger_path=ledger, transcript_path=transcript, mode="full", fmt="markdown")
    assert "### Claude" in markdown
    assert "### Codex" in markdown
    assert "### Cursor" in markdown
    payload = tokens.token_report(ledger_path=ledger, transcript_path=transcript, mode="full", fmt="json")
    assert isinstance(payload, dict)
    assert payload["BUCKETS_codex"]["total"] == 100
    assert payload["BUCKETS_cursor"]["total"] == 10


def test_full_json_splits_codex_buckets_by_model(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 5 - review", "ts": "2026-06-25T00:00:00Z"},
                # A single review round mixing a default-role gpt-5.5 reviewer and
                # gpt-5.4-mini Codex rows.
                {"type": "vendor", "vendor": "codex", "input": 100, "cache_read": 200, "output": 30, "total": 330, "model": "gpt-5.5", "ts": "2026-06-25T00:00:01Z"},
                {"type": "vendor", "vendor": "codex", "input": 1000, "cache_read": 2000, "output": 300, "total": 3300, "model": "gpt-5.4-mini", "ts": "2026-06-25T00:00:02Z"},
                # Model-less legacy row defaults to the current Codex default.
                {"type": "vendor", "vendor": "codex", "input": 5, "cache_read": 6, "output": 7, "total": 18, "ts": "2026-06-25T00:00:03Z"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    report = tokens.build_report_from_ledgers([ledger])
    by_model = report["BUCKETS_codex_by_model"]
    assert by_model["gpt-5.4-mini"] == {"input": 1000, "cached_input": 2000, "output": 300, "total": 3300}
    assert by_model["gpt-5.5"] == {"input": 100, "cached_input": 200, "output": 30, "total": 330}
    assert by_model["gpt-5.6-sol"] == {"input": 5, "cached_input": 6, "output": 7, "total": 18}
    # BUCKETS_codex stays the model-summed total for back-compat.
    assert report["BUCKETS_codex"] == {"input": 1105, "cached_input": 2206, "output": 337, "total": 3648}


def test_ci_fixer_mark_surfaces_as_distinct_step(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 8 - ship", "ts": "2026-06-25T00:00:00Z"},
                {"type": "vendor", "vendor": "claude_sub", "input": 1, "output": 2, "total": 3, "raw": "claude_ci_fix", "ts": "2026-06-25T00:00:10Z"},
                {"type": "mark", "step": "Step 8 - CI fixer", "ts": "2026-06-25T00:01:00Z"},
                {"type": "vendor", "vendor": "claude_sub", "input": 10, "output": 20, "total": 30, "raw": "claude_ci_fix", "ts": "2026-06-25T00:01:10Z"},
                {"type": "mark", "step": "Step 8 - ship resume", "ts": "2026-06-25T00:02:00Z"},
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report = tokens.build_report_from_ledgers([ledger])

    claude_sub_steps = report["claude_sub"]["per_step"]
    ci_fixer = next(row for row in claude_sub_steps if row["step"] == "Step 8 - CI fixer")
    assert ci_fixer["totals"]["total"] == 30


def test_full_json_splits_claude_sub_buckets_by_model_and_raw_fallback(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    rows = [
        {"type": "mark", "step": "Step 5 - review", "ts": "2026-06-25T00:00:00Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1, "cache_read": 2, "cache_create": 3, "output": 4, "total": 10, "model": "claude-haiku-4-5", "ts": "2026-06-25T00:00:01Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 10, "output": 20, "total": 30, "raw": "claude_review", "ts": "2026-06-25T00:00:02Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 7, "output": 8, "total": 15, "model": "claude-sonnet-4-6[1m]", "ts": "2026-06-25T00:00:02Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 100, "output": 200, "total": 300, "raw": "claude_ci_fix", "ts": "2026-06-25T00:00:03Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1000, "output": 2000, "total": 3000, "raw": "claude_lint_fix", "ts": "2026-06-25T00:00:04Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 10000, "output": 20000, "total": 30000, "raw": "unknown", "ts": "2026-06-25T00:00:05Z"},
    ]
    _ = ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = tokens.build_report_from_ledgers([ledger])
    by_model = report["BUCKETS_claude_sub_by_model"]
    assert by_model["claude-haiku-4-5"]["cache_create_5m"] == 3
    assert by_model["claude-sonnet-4-6"]["input"] == 117
    assert by_model["claude-opus-4-8"]["input"] == 11000
    assert report["BUCKETS_claude_sub"]["input"] == 11118


def test_claude_sub_default_raw_keys_match_agents_outputs() -> None:
    assert set(config.CLAUDE_SUB_DEFAULT_MODEL_BY_RAW) == {
        "claude_review",
        "claude_vote",
        "claude_scout",
        "claude_draft",
        "claude_ci_fix",
        "claude_lint_fix",
        "claude_review_fix",
    }
    assert all(key.startswith("claude_") for key in config.CLAUDE_SUB_DEFAULT_MODEL_BY_RAW)


def test_enrich_claude_sub_by_model_from_committed_ledger(tmp_path: Path) -> None:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    ledger = run_dir / "larch-tokens-abc.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 5", "ts": "2026-06-25T00:00:00Z"},
                {"type": "vendor", "vendor": "claude_sub", "input": 10, "output": 5, "total": 15, "model": "claude-fable-5", "ts": "2026-06-25T00:00:01Z"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    report = tokens.enrich_claude_sub_by_model({"BUCKETS_claude_sub": {"input": 10, "output": 5}}, run_dir=run_dir)
    assert report["BUCKETS_claude_sub_by_model"] == {"claude-fable-5": {"input": 10, "cache_read": 0, "cache_create_5m": 0, "cache_create_1h": 0, "output": 5, "total": 15}}


def test_token_report_unknown_format_raises(tmp_path: Path) -> None:
    ledger, transcript = _token_report_fixtures(tmp_path)
    with pytest.raises(ValueError, match="unknown format"):
        _ = tokens.token_report(ledger_path=ledger, transcript_path=transcript, mode="full", fmt="yaml")


def test_token_report_append_json_writes_json_not_repr(tmp_path: Path) -> None:
    ledger, transcript = _token_report_fixtures(tmp_path)
    target = tmp_path / "body.md"
    _ = target.write_text("<!-- token-report-begin -->\nold\n<!-- token-report-end -->\n", encoding="utf-8")
    _ = tokens.token_report(
        ledger_path=ledger,
        transcript_path=transcript,
        mode="full",
        fmt="json",
        append_token_report=target,
    )
    text = target.read_text(encoding="utf-8")
    assert '"BUCKETS_codex"' in text
    assert "'BUCKETS_codex'" not in text


def test_token_ledger_mark_record_dump(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    _ = tokens.TokenLedger(ledger).mark("Step 1 - fixture")
    tokens.TokenLedger(ledger).record_vendor("codex", total=123, raw="codex_implement", model="gpt-5.5")
    dump = tokens.TokenLedger(ledger).dump()
    assert '"type":"mark"' in dump
    assert '"vendor":"codex"' in dump
    assert '"total":123' in dump
    assert '"model":"gpt-5.5"' in dump
    assert oct(ledger.stat().st_mode & 0o777) == oct(0o600)


def test_token_ledger_rejects_claude_vendor(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError, match="claude"):
        tokens.TokenLedger(ledger).record_vendor("claude", total=1)


def test_append_token_record_from_sidecar_preserves_model(tmp_path: Path) -> None:
    sidecar = tmp_path / "codex.token-record"
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=10\nOUTPUT=2\nCACHE_READ=30\nTOTAL=42\nRAW=codex_plan_draft\nMODEL=gpt-5.5\n",
        encoding="utf-8",
    )
    tokens.append_token_record_from_sidecar(input_path=sidecar, tmpdir=tmp_path)
    row = json.loads((tmp_path / "token-report.ndjson").read_text(encoding="utf-8"))
    assert row["tool"] == "codex"
    assert row["raw"] == "codex_plan_draft"
    assert row["model"] == "gpt-5.5"




def test_append_token_record_from_sidecar_normalizes_claude_1m_model(tmp_path: Path) -> None:
    sidecar = tmp_path / "claude.token-record"
    _ = sidecar.write_text(
        "TOOL=claude\nINPUT=10\nOUTPUT=2\nCACHE_READ=30\nTOTAL=42\nRAW=claude_ci_fix\nMODEL=claude-sonnet-4-6[1m]\n",
        encoding="utf-8",
    )
    tokens.append_token_record_from_sidecar(input_path=sidecar, tmpdir=tmp_path)
    row = json.loads((tmp_path / "token-report.ndjson").read_text(encoding="utf-8"))
    assert row["tool"] == "claude"
    assert row["model"] == "claude-sonnet-4-6"


def test_append_token_record_from_sidecar_accepts_historical_without_model(tmp_path: Path) -> None:
    sidecar = tmp_path / "cursor.token-record"
    _ = sidecar.write_text("TOOL=cursor\nINPUT=1\nOUTPUT=2\nTOTAL=3\nRAW=cursor_ci_fix\n", encoding="utf-8")
    tokens.append_token_record_from_sidecar(input_path=sidecar, tmpdir=tmp_path)
    row = json.loads((tmp_path / "token-report.ndjson").read_text(encoding="utf-8"))
    assert row["tool"] == "cursor"
    assert "model" not in row


def test_record_vendor_from_sidecar_noops_for_absent_empty_malformed_and_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.delenv("LARCH_TOKEN_LEDGER", raising=False)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "sidecar-noop")
    for name, body in {
        "empty": "",
        "malformed": "not kv\n",
        "zero": "TOOL=codex\nINPUT=0\nOUTPUT=0\nTOTAL=0\n",
    }.items():
        sidecar = tmp_path / f"{name}.token-record"
        _ = sidecar.write_text(body, encoding="utf-8")
        tokens.record_vendor_from_sidecar(input_path=sidecar)
    tokens.record_vendor_from_sidecar(input_path=tmp_path / "absent.token-record")
    ledger = tokens.resolve_token_ledger_path()
    assert ledger is not None
    assert not ledger.exists()


def test_record_vendor_from_sidecar_warns_for_unsupported_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.delenv("RESEARCH_TMPDIR", raising=False)
    monkeypatch.delenv("LARCH_TOKEN_LEDGER", raising=False)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "unsupported-tool")
    sidecar = tmp_path / "gemini.token-record"
    _ = sidecar.write_text("TOOL=gemini\nINPUT=10\nOUTPUT=2\nTOTAL=12\nRAW=gemini_lane\n", encoding="utf-8")

    tokens.record_vendor_from_sidecar(input_path=sidecar)

    ledger = tokens.resolve_token_ledger_path()
    assert ledger is not None
    assert not ledger.exists()
    err = capsys.readouterr().err
    assert "unsupported TOOL=unknown" in err
    assert "raw TOOL=gemini" in err
    assert str(sidecar) in err


def test_record_vendor_from_sidecar_uses_research_tmpdir_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.delenv("DESIGN_TMPDIR", raising=False)
    monkeypatch.delenv("LARCH_TOKEN_LEDGER", raising=False)
    monkeypatch.delenv("LARCH_TOKEN_SESSION_ID", raising=False)
    research_tmpdir = tmp_path / "research"
    research_tmpdir.mkdir()
    _ = (research_tmpdir / "session-id").write_text("research-session", encoding="utf-8")
    monkeypatch.setenv("RESEARCH_TMPDIR", str(research_tmpdir))
    sidecar = tmp_path / "codex.token-record"
    _ = sidecar.write_text("TOOL=codex\nINPUT=10\nOUTPUT=2\nTOTAL=12\nRAW=codex_research\n", encoding="utf-8")

    tokens.record_vendor_from_sidecar(input_path=sidecar)

    ledger = tokens.resolve_token_ledger_path()
    assert ledger is not None
    assert ledger.parent == research_tmpdir
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["vendor"] == "codex"
    assert rows[0]["raw"] == "codex_research"


def test_record_vendor_from_sidecar_writes_active_ledger_with_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPLEMENT_TMPDIR", raising=False)
    monkeypatch.delenv("LARCH_TOKEN_LEDGER", raising=False)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("LARCH_TOKEN_SESSION_ID", "sidecar-model")
    sidecar = tmp_path / "codex.token-record"
    _ = sidecar.write_text(
        "TOOL=codex\nINPUT=10\nOUTPUT=2\nCACHE_READ=30\nTOTAL=42\nRAW=codex_plan_draft\nMODEL=gpt-5.5\n",
        encoding="utf-8",
    )
    tokens.record_vendor_from_sidecar(input_path=sidecar)
    ledger = tokens.resolve_token_ledger_path()
    assert ledger is not None
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["vendor"] == "codex"
    assert rows[0]["raw"] == "codex_plan_draft"
    assert rows[0]["model"] == "gpt-5.5"


def test_token_report_json_includes_custom_vendor_sibling(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    transcript = tmp_path / "transcript.jsonl"
    _ = ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"type": "mark", "step": "Step 1 - design", "ts": "2026-05-06T00:00:00Z"},
                {"type": "vendor", "vendor": "gemini", "total": 42, "ts": "2026-05-06T00:00:05Z"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _ = transcript.write_text(
        json.dumps(
            {
                "type": "assistant",
                "timestamp": "2026-05-06T00:00:03.100Z",
                "message": {"usage": {"input_tokens": 1, "output_tokens": 1}},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = tokens.token_report(ledger_path=ledger, transcript_path=transcript, mode="full", fmt="json")
    assert isinstance(payload, dict)
    assert "gemini" in payload["vendors"]
    gemini = payload["gemini"]
    assert isinstance(gemini, dict)
    assert gemini["totals"]["total"] == 42


def test_token_lane_tally_write_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    research_dir = Path("/tmp") / f"larch-research-tally-{tmp_path.name}"
    research_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TMPDIR", "/tmp")
    tally = tokens.ResearchLaneTally(research_dir)
    tally.write(phase="research", lane="arch", tool="claude", total_tokens="1200")
    tally.write(phase="validation", lane="review", tool="claude", total_tokens="unknown")
    report = tally.report()
    assert "total=1200" in report
    assert "unmeasurable" in report


def test_token_append_record_from_sidecar(tmp_path: Path) -> None:
    sidecar = tmp_path / "sidecar.env"
    _ = sidecar.write_text("TOOL=codex\nINPUT=1\nOUTPUT=2\nCACHE_READ=3\nCACHE_CREATE=4\nTOTAL=10\nRAW=codex_ci_fix\n", encoding="utf-8")
    tokens.append_token_record_from_sidecar(input_path=sidecar, tmpdir=tmp_path)
    row = json.loads((tmp_path / "token-report.ndjson").read_text(encoding="utf-8").strip())
    assert row["tool"] == "codex"
    assert row["total"] == 10


def test_compute_pr_line_counts_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **_: object) -> SimpleNamespace:
        assert "pulls/42/files" in " ".join(cmd)
        return SimpleNamespace(
            returncode=0,
            stdout="scripts/foo.sh\t10\t2\nlarch-logs/implement/run-x/summary.md\t5\t1\nassets/binary.png\t0\t0\n",
            stderr="",
        )

    monkeypatch.setattr(tokens.proc, "run", fake_run)
    result = tokens.compute_pr_line_counts(pr_number=42, repo="owner/repo")
    assert result.status == "ok"
    assert result.code_added == 10
    assert result.code_deleted == 2
    assert result.logs_added == 5
    assert result.logs_deleted == 1
    assert result.kv_items() == (
        ("LINES_STATUS", "ok"),
        ("CODE_ADDED", "10"),
        ("CODE_DELETED", "2"),
        ("LOGS_ADDED", "5"),
        ("LOGS_DELETED", "1"),
    )


def test_token_mark_returns_typed_recorded_and_skipped_results(tmp_path: Path) -> None:
    recorded = tokens.token_mark(step="Step 1", env={"IMPLEMENT_TMPDIR": str(tmp_path)})
    skipped = tokens.token_mark(step="Step 1", env={})

    assert recorded.marked
    assert recorded.ledger_path is not None
    assert not skipped.marked
    assert skipped.ledger_path is None
    with pytest.raises(FrozenInstanceError):
        recorded.marked = False  # type: ignore[misc]



def test_token_cli_rejects_invalid_ledger(capsys: pytest.CaptureFixture[str]) -> None:
    pytest.skip("token dump CLI cut over to Rust (#8506); covered by crates/larch-cli/tests/token_commands.rs")
    _ = capsys


def test_validate_under_tmp_empty_tmpdir_uses_system_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMPDIR", "")
    monkeypatch.chdir(tmp_path)
    resolved = tokens._validate_under_tmp("ledger.jsonl")  # pyright: ignore[reportPrivateUsage]
    assert tmp_path not in resolved.parents
    assert resolved == Path("/tmp/ledger.jsonl") or resolved == Path("/private/tmp/ledger.jsonl")



def test_tokens_imports_without_tiktoken() -> None:
    code = "import importlib; importlib.import_module('larch.report.tokens')"
    proc = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


def test_read_main_model_returns_first_assistant_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "message": {"content": "hi"}}),
                json.dumps({"type": "assistant", "message": {"model": "claude-opus-4-8", "content": []}}),
                json.dumps({"type": "assistant", "message": {"model": "claude-sonnet-4-6", "content": []}}),
            ]
        ),
        encoding="utf-8",
    )

    def fake_source(**_: object) -> tokens.ClaudeSourceResult:
        return tokens.ClaudeSourceResult(transcript_path=transcript, session_dir=None, session_uuid="")

    monkeypatch.setattr(tokens, "token_claude_source", fake_source)
    assert tokens.read_main_model() == "claude-opus-4-8"


def test_read_main_model_blank_when_no_assistant_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}), encoding="utf-8")

    def fake_source(**_: object) -> tokens.ClaudeSourceResult:
        return tokens.ClaudeSourceResult(transcript_path=transcript, session_dir=None, session_uuid="")

    monkeypatch.setattr(tokens, "token_claude_source", fake_source)
    assert tokens.read_main_model() == ""


def test_read_main_model_blank_when_transcript_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_source(**_: object) -> tokens.ClaudeSourceResult:
        return tokens.ClaudeSourceResult(transcript_path=None, session_dir=None, session_uuid="", reason="unavailable")

    monkeypatch.setattr(tokens, "token_claude_source", fake_source)
    assert tokens.read_main_model() == ""


def _ledger(path: Path, rows: tuple[dict[str, object], ...]) -> Path:
    _ = path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def test_build_report_from_ledgers_recovers_vendor_lanes(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path / "larch-tokens-abc.jsonl",
        (
            {"type": "mark", "step": "design Step 0", "ts": "2026-06-15T00:00:00Z"},
            {"type": "vendor", "vendor": "codex", "input": 100, "output": 20, "cache_read": 50, "total": 170, "ts": "2026-06-15T00:00:05Z"},
            {"type": "vendor", "vendor": "cursor", "input": 10, "output": 2, "cache_read": 3, "total": 15, "ts": "2026-06-15T00:00:06Z"},
        ),
    )
    report = tokens.build_report_from_ledgers([ledger])
    assert report["codex"]["totals"]["total"] == 170
    assert report["cursor"]["totals"]["total"] == 15
    assert report["BUCKETS_codex"]["input"] == 100
    # The main-agent claude lane lives in the uncommitted transcript; recovered as zero.
    assert report["claude"]["totals"]["total"] == 0


def test_build_report_from_ledgers_reroutes_implementer_raw_rows_to_step2(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path / "larch-tokens-abc.jsonl",
        (
            {"type": "mark", "step": "Step 0 — preflight", "ts": "2026-06-15T00:00:00Z"},
            {
                "type": "vendor",
                "vendor": "codex",
                "input": 100,
                "output": 20,
                "total": 120,
                "raw": config.CODEX_IMPLEMENT_RAW_LABEL,
                "ts": "2026-06-15T00:00:05Z",
            },
            {
                "type": "vendor",
                "vendor": "codex",
                "total": 10,
                "raw": "codex_review",
                "ts": "2026-06-15T00:00:06Z",
            },
            {
                "type": "vendor",
                "vendor": "cursor",
                "input": 7,
                "output": 8,
                "total": 15,
                "raw": config.CURSOR_IMPLEMENT_RAW_LABEL,
                "ts": "2026-06-15T00:00:07Z",
            },
        ),
    )

    report = tokens.build_report_from_ledgers([ledger])
    codex_steps = {row["step"]: row["totals"] for row in report["codex"]["per_step"]}
    cursor_steps = {row["step"]: row["totals"] for row in report["cursor"]["per_step"]}

    assert codex_steps["Step 0 — preflight"]["total"] == 10
    assert codex_steps[config.IMPLEMENT_STEP2_LABEL]["total"] == 120
    assert report["codex"]["totals"]["total"] == 130
    assert cursor_steps["Step 0 — preflight"]["total"] == 0
    assert cursor_steps[config.IMPLEMENT_STEP2_LABEL]["total"] == 15
    assert report["cursor"]["totals"]["total"] == 15


def test_build_report_from_ledgers_merges_multiple(tmp_path: Path) -> None:
    led1 = _ledger(
        tmp_path / "larch-tokens-1.jsonl",
        (
            {"type": "mark", "step": "s0", "ts": "2026-06-15T00:00:00Z"},
            {"type": "vendor", "vendor": "codex", "total": 100, "ts": "2026-06-15T00:00:05Z"},
        ),
    )
    led2 = _ledger(
        tmp_path / "larch-tokens-2.jsonl",
        (
            {"type": "mark", "step": "s1", "ts": "2026-06-15T00:01:00Z"},
            {"type": "vendor", "vendor": "codex", "total": 50, "ts": "2026-06-15T00:01:05Z"},
        ),
    )
    report = tokens.build_report_from_ledgers([led1, led2])
    assert report["codex"]["totals"]["total"] == 150


def test_build_report_from_ledgers_no_marks_raises(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path / "larch-tokens-x.jsonl",
        ({"type": "vendor", "vendor": "codex", "total": 5, "ts": "2026-06-15T00:00:00Z"},),
    )
    with pytest.raises(ValueError, match="no step marks"):
        _ = tokens.build_report_from_ledgers([ledger])


def test_build_report_vendor_totals_cache_read_is_integer(tmp_path: Path) -> None:
    # Regression test for issue #5852: external-vendor totals.cache_read must be
    # a non-null integer, never absent. Covers the live build + re-render path via
    # build_report_from_ledgers (which uses _full_json → _per_step_json → _totals).
    ledger = _ledger(
        tmp_path / "larch-tokens-abc.jsonl",
        (
            {"type": "mark", "step": "s0", "ts": "2026-06-15T00:00:00Z"},
            {"type": "vendor", "vendor": "cursor", "input": 10, "output": 2, "cache_read": 80, "total": 92, "ts": "2026-06-15T00:00:01Z"},
            {"type": "vendor", "vendor": "codex", "input": 100, "output": 20, "cache_read": 50, "total": 170, "ts": "2026-06-15T00:00:02Z"},
            {"type": "vendor", "vendor": "claude_sub", "input": 5, "output": 1, "cache_read": 40, "total": 46, "ts": "2026-06-15T00:00:03Z"},
        ),
    )
    report = tokens.build_report_from_ledgers([ledger])
    for vendor in ("cursor", "codex", "claude_sub"):
        totals = report[vendor]["totals"]  # type: ignore[index]
        assert "cache_read" in totals, f"{vendor}.totals must contain cache_read"
        assert isinstance(totals["cache_read"], int), f"{vendor}.totals.cache_read must be int"
    assert report["cursor"]["totals"]["cache_read"] == 80  # type: ignore[index]
    assert report["codex"]["totals"]["cache_read"] == 50  # type: ignore[index]
    assert report["claude_sub"]["totals"]["cache_read"] == 40  # type: ignore[index]



def _tsv_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=False)) for line in lines[1:]]



def test_panel_prompt_size_helper_writes_counts_without_prompt_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "panel-prompt-sizes.tsv"
    monkeypatch.setenv("LARCH_PANEL_SLOT", "correctness")
    monkeypatch.setenv("LARCH_PANEL_SITE", "review Step 2")

    tokens.append_panel_prompt_size(
        artifact_path=out,
        output=tmp_path / "cursor-specialist-correctness-output.txt",
        tool="cursor",
        prompt="secret rendered prompt text",
    )

    text = out.read_text(encoding="utf-8")
    assert "secret rendered prompt text" not in text
    rows = _tsv_rows(out)
    assert rows[0]["slot_kind"] == "specialist"
    assert rows[0]["prompt_bytes"] == str(len(b"secret rendered prompt text"))
    assert rows[0]["prompt_tokens"] == str((len(b"secret rendered prompt text") + 3) // 4)
    assert rows[0]["scaffold_bytes"] == rows[0]["prompt_bytes"]
    assert rows[0]["payload_bytes"] == "0"




def test_panel_prompt_size_records_explicit_and_env_payload_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "panel-prompt-sizes.tsv"
    monkeypatch.setenv("LARCH_PANEL_SLOT", "aggregator")
    monkeypatch.setenv("LARCH_PANEL_PAYLOAD_BYTES", "4")

    tokens.append_panel_prompt_size(artifact_path=out, prompt="abcdefghij", payload_bytes=6)
    tokens.append_panel_prompt_size(artifact_path=out, prompt="abcdefghij")

    rows = _tsv_rows(out)
    assert rows[0]["payload_bytes"] == "6"
    assert rows[0]["scaffold_bytes"] == "4"
    assert rows[1]["payload_bytes"] == "4"
    assert rows[1]["scaffold_bytes"] == "6"


def test_panel_prompt_size_malformed_payload_falls_back_to_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "panel-prompt-sizes.tsv"
    monkeypatch.setenv("LARCH_PANEL_SLOT", "voter-1")
    monkeypatch.setenv("LARCH_PANEL_PAYLOAD_BYTES", "not-an-int")

    tokens.append_panel_prompt_size(artifact_path=out, prompt="abc", payload_bytes="-1")

    row = _tsv_rows(out)[0]
    assert row["payload_bytes"] == "0"
    assert row["scaffold_bytes"] == "3"


def test_panel_prompt_size_explicit_malformed_does_not_fall_back_to_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "panel-prompt-sizes.tsv"
    monkeypatch.setenv("LARCH_PANEL_SLOT", "voter-1")
    monkeypatch.setenv("LARCH_PANEL_PAYLOAD_BYTES", "4")

    tokens.append_panel_prompt_size(artifact_path=out, prompt="abc", payload_bytes="not-an-int")

    row = _tsv_rows(out)[0]
    assert row["payload_bytes"] == "0"
    assert row["scaffold_bytes"] == "3"


def test_panel_prompt_size_migrates_legacy_header_on_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "panel-prompt-sizes.tsv"
    _ = out.write_text(
        "site\tphase\tround_num\tslot\tslot_kind\ttool\toutput\tprompt_bytes\tprompt_tokens\tagent_file\tagent_bytes\tagent_tokens\n"
        "review\t\t1\tcorrectness\tspecialist\tcursor\told.txt\t12\t3\tagents/reviewer-testing.md\t8\t2\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LARCH_PANEL_SLOT", "voter-1")

    tokens.append_panel_prompt_size(artifact_path=out, prompt="xyz", payload_bytes=1)

    rows = _tsv_rows(out)
    assert rows[0]["scaffold_bytes"] == "12"
    assert rows[0]["payload_bytes"] == "0"
    assert rows[0]["agent_file"] == "agents/reviewer-testing.md"
    assert rows[1]["scaffold_bytes"] == "2"
    assert rows[1]["payload_bytes"] == "1"
    assert rows[1]["agent_file"] == ""

def test_panel_prompt_size_skips_without_panel_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_PANEL_SLOT", raising=False)
    out = tmp_path / "panel-prompt-sizes.tsv"

    tokens.append_panel_prompt_size(artifact_path=out, prompt="body", output=tmp_path / "out.txt")

    assert not out.exists()


def test_panel_prompt_size_missing_agent_file_is_best_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_PANEL_SLOT", "voter-1")
    out = tmp_path / "panel-prompt-sizes.tsv"

    tokens.append_panel_prompt_size(
        artifact_path=out,
        output=tmp_path / "vote.txt",
        tool="claude",
        prompt="vote prompt",
        agent_file=tmp_path / "missing-agent.md",
    )

    row = _tsv_rows(out)[0]
    assert row["slot_kind"] == "voter"
    assert row["agent_file"] == ""
    assert row["agent_bytes"] == "0"


def test_repo_relative_agent_path_rejects_symlink_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tokens, "_repo_root", lambda: tmp_path)  # pyright: ignore[reportPrivateUsage]
    agent = tmp_path / "agents" / "reviewer.md"
    agent.parent.mkdir()
    _ = agent.write_text("agent body\n", encoding="utf-8")
    symlink = tmp_path / "agent-link.md"
    try:
        symlink.symlink_to(agent)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    rel, byte_count, token_count = tokens._repo_relative_agent_path(symlink)  # pyright: ignore[reportPrivateUsage]

    assert (rel, byte_count, token_count) == ("", 0, 0)


def test_panel_prompt_artifact_prefers_env_artifact_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact_dir = tmp_path / "artifact"
    monkeypatch.setenv("LARCH_PANEL_ARTIFACT_DIR", str(artifact_dir))

    path = tokens.panel_prompt_size_artifact_for_output(output=tmp_path / "other" / "out.txt")

    assert path == artifact_dir / "panel-prompt-sizes.tsv"


def test_panel_prompt_artifact_routes_design_round_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_PANEL_ARTIFACT_DIR", raising=False)
    output = tmp_path / "design" / "plan-review" / "round-2" / "cursor-plan-arch-output.txt"

    path = tokens.panel_prompt_size_artifact_for_output(output=output, site="design Step 3")

    assert path == output.parent / "panel-prompt-sizes.tsv"


def test_panel_slot_kind_classifies_dyn_slots_before_plan_substring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_PANEL_SLOT", "dyn-migration-plan")
    assert tokens._panel_slot_kind_from_env() == "specialist"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setenv("LARCH_PANEL_SLOT", "dyn-cursor-plan-arch")
    monkeypatch.setenv("LARCH_PANEL_PHASE", "plan-review")
    monkeypatch.setenv("LARCH_PANEL_SITE", "design Step 3")
    assert tokens._panel_slot_kind_from_env() == "plan-review"  # pyright: ignore[reportPrivateUsage]

    monkeypatch.delenv("LARCH_PANEL_PHASE", raising=False)
    monkeypatch.delenv("LARCH_PANEL_SITE", raising=False)
    monkeypatch.setenv("LARCH_PANEL_SLOT", "cursor-plan-arch")
    assert tokens._panel_slot_kind_from_env() == "plan-review"  # pyright: ignore[reportPrivateUsage]


def test_panel_slot_kind_classifies_architectural_compliance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_PANEL_SLOT", "architectural-compliance")

    assert tokens._panel_slot_kind_from_env() == "specialist"  # pyright: ignore[reportPrivateUsage]


def test_build_panel_dispatch_env_sets_panel_keys_without_mutating_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LARCH_PANEL_SLOT", raising=False)
    artifact_dir = tmp_path / "round-3"

    env = tokens.build_panel_dispatch_env(
        artifact_dir=artifact_dir,
        site="review Step 2",
        round_dir=artifact_dir,
        slot="correctness",
        phase="phase1",
        primary_tool="cursor",
        source_agent_file="agents/reviewer-testing.md",
    )

    assert os.environ.get("LARCH_PANEL_SLOT") is None
    assert env["LARCH_PANEL_ARTIFACT_DIR"] == str(artifact_dir)
    assert env["LARCH_PANEL_ROUND_NUM"] == "3"
    assert env["LARCH_PANEL_SLOT"] == "correctness"
    assert env["LARCH_PANEL_PRIMARY_TOOL"] == "cursor"
    assert "LARCH_PANEL_PAYLOAD_BYTES" not in env


def test_build_panel_dispatch_env_clears_inherited_payload_without_explicit_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_PANEL_PAYLOAD_BYTES", "123")

    env = tokens.build_panel_dispatch_env(artifact_dir=tmp_path, site="review Step 2")

    assert "LARCH_PANEL_PAYLOAD_BYTES" not in env


def test_build_panel_dispatch_env_sets_explicit_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LARCH_PANEL_PAYLOAD_BYTES", "123")

    env = tokens.build_panel_dispatch_env(artifact_dir=tmp_path, site="review Step 2", payload_bytes=7)

    assert env["LARCH_PANEL_PAYLOAD_BYTES"] == "7"
