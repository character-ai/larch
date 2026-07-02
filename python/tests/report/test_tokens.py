"""Tests for tokens.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence
from types import SimpleNamespace

import pytest

from larch.core import config
from larch.report import report_tokens_scan
from larch.report import tokens
from larch.report.report_tokens_models import RunRecord, VendorTotals


def test_atomic_text_uses_nofollow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    def fake_atomic_write(_path: Path, _text: str, **kwargs: object) -> None:
        calls.update(kwargs)

    monkeypatch.setattr(tokens.larch_io, "atomic_write", fake_atomic_write)
    tokens._atomic_text(path=tmp_path / "tokens.tsv", text="body\n")  # pyright: ignore[reportPrivateUsage]
    assert calls["prefix"] == ".tokens.tsv."
    assert calls["nofollow"] is True
    assert calls["newline"] == "\n"


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
    assert out.get("STATUS") == "unavailable"


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
    assert out.get("STATUS") == "unavailable"


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
    assert out["TRANSCRIPT_PATH"] == str(transcript.resolve())
    assert out["SESSION_DIR"] == str(session_dir)
    assert out["SESSION_UUID"] == "session-uuid"


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
    assert under["status"] == "under_cap"
    assert over["status"] == "cap_hit"
    assert over["total"] == 50


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
                # Model-less legacy row defaults to gpt-5.5.
                {"type": "vendor", "vendor": "codex", "input": 5, "cache_read": 6, "output": 7, "total": 18, "ts": "2026-06-25T00:00:03Z"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    report = tokens.build_report_from_ledgers([ledger])
    by_model = report["BUCKETS_codex_by_model"]
    assert by_model["gpt-5.4-mini"] == {"input": 1000, "cached_input": 2000, "output": 300, "total": 3300}
    # The gpt-5.5 row and the model-less row fold together under gpt-5.5.
    assert by_model["gpt-5.5"] == {"input": 105, "cached_input": 206, "output": 37, "total": 348}
    # BUCKETS_codex stays the model-summed total for back-compat.
    assert report["BUCKETS_codex"] == {"input": 1105, "cached_input": 2206, "output": 337, "total": 3648}



def test_full_json_splits_claude_sub_buckets_by_model_and_raw_fallback(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    rows = [
        {"type": "mark", "step": "Step 5 - review", "ts": "2026-06-25T00:00:00Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1, "cache_read": 2, "cache_create": 3, "output": 4, "total": 10, "model": "claude-haiku-4-5", "ts": "2026-06-25T00:00:01Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 10, "output": 20, "total": 30, "raw": "claude_review", "ts": "2026-06-25T00:00:02Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 100, "output": 200, "total": 300, "raw": "claude_ci_fix", "ts": "2026-06-25T00:00:03Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 1000, "output": 2000, "total": 3000, "raw": "claude_lint_fix", "ts": "2026-06-25T00:00:04Z"},
        {"type": "vendor", "vendor": "claude_sub", "input": 10000, "output": 20000, "total": 30000, "raw": "unknown", "ts": "2026-06-25T00:00:05Z"},
    ]
    _ = ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = tokens.build_report_from_ledgers([ledger])
    by_model = report["BUCKETS_claude_sub_by_model"]
    assert by_model["claude-haiku-4-5"]["cache_create_5m"] == 3
    assert by_model["claude-sonnet-4-6"]["input"] == 10
    assert by_model["claude-opus-4-8"]["input"] == 11100
    assert report["BUCKETS_claude_sub"]["input"] == 11111


def test_claude_sub_default_raw_keys_match_agents_outputs() -> None:
    assert set(config.CLAUDE_SUB_DEFAULT_MODEL_BY_RAW) == {
        "claude_review",
        "claude_vote",
        "claude_scout",
        "claude_draft",
        "claude_ci_fix",
        "claude_lint_fix",
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
    tokens.TokenLedger(ledger).mark("Step 1 - fixture")
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
    def fake_check_output(cmd: list[str], **_: object) -> str:
        assert "pulls/42/files" in " ".join(cmd)
        return "scripts/foo.sh\t10\t2\nlarch-logs/implement/run-x/summary.md\t5\t1\nassets/binary.png\t0\t0\n"

    monkeypatch.setattr(tokens.subprocess, "check_output", fake_check_output)
    result = tokens.compute_pr_line_counts(pr_number=42, repo="owner/repo")
    assert result["LINES_STATUS"] == "ok"
    assert result["CODE_ADDED"] == 10
    assert result["CODE_DELETED"] == 2
    assert result["LOGS_ADDED"] == 5
    assert result["LOGS_DELETED"] == 1


def test_classify_md_tier_and_claude_imports() -> None:
    repo = tokens._repo_root()  # pyright: ignore[reportPrivateUsage]
    imports = tokens._claude_root_imports(repo)  # pyright: ignore[reportPrivateUsage]
    assert "AGENTS.md" in imports
    assert tokens._classify_md_tier(rel="CLAUDE.md", tier1_imports=imports) == "tier-1a-claude-root"  # pyright: ignore[reportPrivateUsage]
    assert tokens._classify_md_tier(rel="AGENTS.md", tier1_imports=imports) == "tier-1a-claude-import"  # pyright: ignore[reportPrivateUsage]
    assert tokens._classify_md_tier(rel="skills/implement/SKILL.md", tier1_imports=imports) == "tier-1b-runtime-skill"  # pyright: ignore[reportPrivateUsage]


def test_normalize_read_path_handles_absolute_and_cache(tmp_path: Path) -> None:
    repo = tmp_path
    rel = tokens._normalize_read_path(raw=f"{repo}/docs/foo.md", repo=repo)  # pyright: ignore[reportPrivateUsage]
    assert rel == "docs/foo.md"
    cached = tokens._normalize_read_path(  # pyright: ignore[reportPrivateUsage]
        raw="/Users/me/.claude/plugins/cache/larch-local/larch/1.2.3/skills/shared/foo.md",
        repo=repo,
    )
    assert cached == "skills/shared/foo.md"
    assert tokens._normalize_read_path(  # pyright: ignore[reportPrivateUsage]
        raw="/Users/me/.cache/larch/sessions/run-1/docs/foo.md",
        repo=repo,
    ) is None
    assert tokens._normalize_read_path(  # pyright: ignore[reportPrivateUsage]
        raw="/tmp/larch/foo/skills/design/references/approval-gates.md",
        repo=repo,
    ) is None
    assert tokens._normalize_read_path(raw="/etc/passwd", repo=repo) is None  # pyright: ignore[reportPrivateUsage]


def test_ngram_source_files_include_claude_imports() -> None:
    files = tokens._ngram_source_files(tokens._repo_root())  # pyright: ignore[reportPrivateUsage]
    assert "CLAUDE.md" in files
    assert "AGENTS.md" in files


def test_token_report_main_terse_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledger, transcript = _token_report_fixtures(tmp_path)
    rc = tokens.token_report_main(
        ["--terse", "--ledger", str(ledger), "--transcript", str(transcript)],
    )
    assert rc == 0
    out = capsys.readouterr()
    assert "Step 2 - implement: claude=100 tokens" in out.out


def test_token_cli_rejects_invalid_ledger(capsys: pytest.CaptureFixture[str]) -> None:
    rc = tokens.token_dump_main(["--ledger", "/etc/passwd"])
    assert rc == 1
    assert "token dump:" in capsys.readouterr().err


def test_validate_under_tmp_empty_tmpdir_uses_system_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMPDIR", "")
    monkeypatch.chdir(tmp_path)
    resolved = tokens._validate_under_tmp("ledger.jsonl")  # pyright: ignore[reportPrivateUsage]
    assert tmp_path not in resolved.parents
    assert resolved == Path("/tmp/ledger.jsonl") or resolved == Path("/private/tmp/ledger.jsonl")


def test_tiktoken_count_texts_uses_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout=json.dumps([3, 5]).encode(), stderr=b"")

    monkeypatch.setattr(tokens.subprocess, "run", fake_run)
    assert tokens._tiktoken_count_texts(["a", "bb"]) == [3, 5]  # pyright: ignore[reportPrivateUsage]
    assert calls
    assert calls[0][0] == "python3"


def test_tiktoken_absent_exits_with_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"No module named 'tiktoken'")

    monkeypatch.setattr(tokens.subprocess, "run", fake_run)
    with pytest.raises(SystemExit, match="tiktoken required"):
        _ = tokens._tiktoken_count_texts(["x"])  # pyright: ignore[reportPrivateUsage]


def test_measure_md_cost_writes_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    _ = (repo / "docs").mkdir()
    _ = (repo / "docs" / "sample.md").write_text("# Title\n\nBody\n", encoding="utf-8")
    _ = (repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    _ = (repo / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "_repo_root", lambda: repo)
    monkeypatch.setattr(tokens, "_measure_stamp", lambda: "fixture-day")
    monkeypatch.setattr(
        tokens.subprocess,
        "check_output",
        lambda cmd, **_kw: b"docs/sample.md\x00" if "ls-files" in cmd else b"",  # type: ignore[arg-type]
    )
    monkeypatch.setattr(tokens, "_tiktoken_count_texts", lambda texts: [len(t) for t in texts])  # type: ignore[arg-type]
    out = tokens.measure_md_cost()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("path\ttier\tbytes\ttokens\tlines\th2_count\n")
    row = text.strip().splitlines()[1].split("\t")
    assert row[0] == "docs/sample.md"
    assert row[1] == "tier-3-doc"
    assert int(row[3]) > 0


def test_measure_realized_cost_writes_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path
    skill_dir = repo / "skills" / "review"
    skill_dir.mkdir(parents=True)
    _ = (skill_dir / "SKILL.md").write_text("review skill body\n", encoding="utf-8")
    run_dir = repo / "larch-logs" / "review" / "RUN1"
    run_dir.mkdir(parents=True)
    _ = (run_dir / "manifest.json").write_text('{"issue_number": 42, "skill": "review"}', encoding="utf-8")
    _ = (run_dir / "timing-report.md").write_text(
        "| Skill | Step | Duration |\n| review | Step 1 | 00:00:01 |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(tokens, "_repo_root", lambda: repo)
    monkeypatch.setattr(tokens, "_measure_stamp", lambda: "fixture-day")
    monkeypatch.setattr(tokens, "_tiktoken_count_texts", lambda texts: [11 for _ in texts])  # type: ignore[arg-type]
    out = tokens.measure_realized_cost()
    text = out.read_text(encoding="utf-8")
    assert text.startswith(
        "skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\t"
        "skill_md_tokens\treference_tokens_per_invocation\treference_reads_observed\t"
        "reference_capture_status\n"
    )
    row = text.strip().splitlines()[1].split("\t")
    assert row[0] == "review"
    assert row[1] == "1"
    assert row[2] == "1"
    assert row[3] == "11.00"
    assert row[4] == "11"
    assert row[5] == "11"
    assert row[6] == "0.00"
    assert row[7] == "0"
    # No session-transcript.jsonl was ever committed for this run, so the zero
    # reference-read count above is an unmeasured blind spot, not a confirmed zero.
    assert row[8] == "not-yet-measured"


def test_measure_md_cost_main_prints_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "larch-logs" / "measure-md-cost" / "fixture-day.tsv"
    out.parent.mkdir(parents=True)
    _ = out.write_text("path\ttier\tbytes\ttokens\tlines\th2_count\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "measure_md_cost", lambda: out)
    monkeypatch.setattr(tokens, "_repo_root", lambda: tmp_path)
    rc = tokens.measure_md_cost_main([])
    assert rc == 0


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

    def fake_source(**_: object) -> dict[str, str]:
        return {"TRANSCRIPT_PATH": str(transcript)}

    monkeypatch.setattr(tokens, "token_claude_source", fake_source)
    assert tokens.read_main_model() == "claude-opus-4-8"


def test_read_main_model_blank_when_no_assistant_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}), encoding="utf-8")

    def fake_source(**_: object) -> dict[str, str]:
        return {"TRANSCRIPT_PATH": str(transcript)}

    monkeypatch.setattr(tokens, "token_claude_source", fake_source)
    assert tokens.read_main_model() == ""


def test_read_main_model_blank_when_transcript_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_source(**_: object) -> dict[str, str]:
        return {"STATUS": "unavailable"}

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


def _setup_reference_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for rel, text in {
        "skills/design/SKILL.md": "design skill tokens",
        "skills/implement/SKILL.md": "implement skill tokens",
        "skills/design/references/approval-gates.md": "approval gates reference",
        "skills/design/references/plan-review.md": "plan review reference",
        "skills/design/references/finalize-step5.md": "finalize step five reference",
        "skills/shared/topology.md": "shared topology reference words",
        "docs/ignored.md": "ignored docs",
    }.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(tokens, "_repo_root", lambda: tmp_path)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(tokens, "_tiktoken_count_texts", _count_words)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setenv("LARCH_MEASURE_DATE", "2026-06-30")


def _count_words(texts: list[str]) -> list[int]:
    return [len(text.split()) for text in texts]


def _write_valid_run(tmp_path: Path, *, skill: str, run_id: str, issue: int = 1) -> Path:
    run_dir = tmp_path / "larch-logs" / skill / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _ = (run_dir / "manifest.json").write_text(json.dumps({"issue_number": issue, "skill": skill}), encoding="utf-8")
    return run_dir


def _write_transcript(run_dir: Path, rows: Sequence[Mapping[str, object]]) -> None:
    _ = (run_dir / "session-transcript.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _tsv_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=False)) for line in lines[1:]]


def _tsv_section_rows(path: Path, section: str) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"# {section}") + 1
    header = lines[start].split("\t")
    rows: list[dict[str, str]] = []
    for line in lines[start + 1 :]:
        if line.startswith("# "):
            break
        if not line:
            continue
        rows.append(dict(zip(header, line.split("\t"), strict=False)))
    return rows


def _cache_record(
    *,
    number: int,
    title: str = "Fixture",
    started_at: str = "2026-06-01T00:00:00Z",
    claude: VendorTotals | None = None,
    claude_sub: VendorTotals | None = None,
    raw_report: Mapping[str, object] | None = None,
) -> RunRecord:
    return RunRecord(
        number=number,
        title=title,
        url="",
        started_at=started_at,
        closed_at=started_at,
        workflow="",
        claude=VendorTotals() if claude is None else claude,
        codex=VendorTotals(),
        cursor=VendorTotals(),
        claude_sub=VendorTotals() if claude_sub is None else claude_sub,
        phase_rows=(),
        raw_report={} if raw_report is None else raw_report,
    )


def test_measure_cache_efficiency_writes_ranked_sections(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "consumer"
    repo.mkdir()
    monkeypatch.setenv("LARCH_MEASURE_DATE", "fixture-day")
    design_record = _cache_record(
        number=1,
        title="Finite",
        claude=VendorTotals(cache_create_5m=4, cache_read=2),
        raw_report={"claude": {"per_step": [{"step": "3", "totals": {"cache_create_5m": 4, "cache_read": 2}}]}},
    )
    legacy_record = _cache_record(
        number=2,
        title="Legacy zero read",
        claude_sub=VendorTotals(cache_create=9, cache_read=0),
        raw_report={"claude_sub": {"per_step": [{"step": "5", "totals": {"cache_create": 9, "cache_read": 0}}]}},
    )
    zero_record = _cache_record(number=3, title="All zero")

    def fake_scan(_runner: object, *, skill: str, resolve_repo: bool, **_kwargs: object) -> report_tokens_scan.ScanResult:
        assert resolve_repo is False
        records = (design_record, zero_record) if skill == "design" else (legacy_record,)
        return report_tokens_scan.ScanResult(repo_root=repo, repo_slug=None, records=records)

    monkeypatch.setattr(report_tokens_scan, "scan", fake_scan)

    out = tokens.measure_cache_efficiency()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# per_run\n")
    assert "\n# per_step\n" in text
    per_run = _tsv_section_rows(out, "per_run")
    assert per_run[0]["lane"] == "claude_sub"
    assert per_run[0]["ratio"] == "inf"
    assert per_run[0]["title"] == "Legacy zero read"
    assert all(row["title"] != "All zero" for row in per_run)


def test_cache_create_effective_uses_legacy_when_split_zero() -> None:
    assert tokens._cache_create_effective(cache_create=7, cache_create_5m=0, cache_create_1h=0) == 7  # pyright: ignore[reportPrivateUsage]
    assert tokens._cache_create_effective(cache_create=7, cache_create_5m=2, cache_create_1h=3) == 5  # pyright: ignore[reportPrivateUsage]


def test_measure_cache_efficiency_aggregates_steps_by_skill_step_and_lane(tmp_path: Path) -> None:
    first = _cache_record(
        number=1,
        raw_report={"claude": {"per_step": [{"step": "3", "totals": {"cache_create_5m": 3, "cache_create_1h": 2, "cache_read": 5}}]}},
    )
    second = _cache_record(
        number=2,
        raw_report={"claude": {"per_step": [{"step": "3", "totals": {"cache_create": 7, "cache_read": 5}}]}},
    )
    per_run, per_step = tokens._measure_cache_efficiency_records(tagged_records=(("design", first), ("design", second)))  # pyright: ignore[reportPrivateUsage]
    out = tmp_path / "cache.tsv"
    _ = out.write_text(tokens._render_cache_efficiency_tsv(per_run=per_run, per_step=per_step), encoding="utf-8")  # pyright: ignore[reportPrivateUsage]

    rows = _tsv_section_rows(out, "per_step")
    row = next(item for item in rows if item["skill"] == "design" and item["step"] == "3" and item["lane"] == "claude")
    assert row["runs"] == "2"
    assert row["cache_create"] == "7"
    assert row["cache_create_5m"] == "3"
    assert row["cache_create_1h"] == "2"
    assert row["cache_read"] == "10"
    assert row["ratio"] == "1.200000"


def test_measure_cache_efficiency_separates_homonymous_steps_across_skills(tmp_path: Path) -> None:
    design = _cache_record(
        number=1,
        raw_report={"claude": {"per_step": [{"step": "3", "totals": {"cache_create_5m": 4, "cache_read": 2}}]}},
    )
    implement = _cache_record(
        number=2,
        raw_report={"claude": {"per_step": [{"step": "3", "totals": {"cache_create_5m": 10, "cache_read": 5}}]}},
    )
    per_run, per_step = tokens._measure_cache_efficiency_records(tagged_records=(("design", design), ("implement", implement)))  # pyright: ignore[reportPrivateUsage]
    out = tmp_path / "cache.tsv"
    _ = out.write_text(tokens._render_cache_efficiency_tsv(per_run=per_run, per_step=per_step), encoding="utf-8")  # pyright: ignore[reportPrivateUsage]

    keys = {(row["skill"], row["step"], row["lane"]) for row in _tsv_section_rows(out, "per_step")}
    assert ("design", "3", "claude") in keys
    assert ("implement", "3", "claude") in keys


def test_measure_cache_efficiency_main_prints_relative_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "consumer"
    out = repo / "larch-logs" / "measure-cache-efficiency" / "fixture-day.tsv"
    out.parent.mkdir(parents=True)
    _ = out.write_text("# per_run\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "measure_cache_efficiency", lambda: out)
    monkeypatch.setattr(tokens, "_repo_root", lambda: pytest.fail("_repo_root must not be used"))  # pyright: ignore[reportPrivateUsage]

    rc = tokens.measure_cache_efficiency_main([])

    assert rc == 0
    assert capsys.readouterr().out == "WROTE\tlarch-logs/measure-cache-efficiency/fixture-day.tsv\n"


def test_measure_references_heatmap_counts_raw_v3_future_and_normalized_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_reference_repo(tmp_path, monkeypatch)
    run = _write_valid_run(tmp_path, skill="design", run_id="run1")
    transcript_rows = [
        {
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/design/references/approval-gates.md"}},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": f"{tmp_path}/skills/design/references/plan-review.md"}},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": f"{config.REDACTED_OPERATOR_REPO}/skills/design/references/finalize-step5.md"}},
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "docs/ignored.md"}},
                ]
            }
        },
        {
            "blocks": [
                {"type": "tool_call", "name": "Read", "input": {"file_path": "/Users/me/.claude/plugins/cache/larch-local/larch/abc/skills/shared/topology.md"}},
                {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/design/references/approval-gates.md"}},
            ]
        },
    ]
    _write_transcript(run, transcript_rows)
    _ = _write_valid_run(tmp_path, skill="design", run_id="run2", issue=2)
    manifestless = tmp_path / "larch-logs" / "design" / "not-a-run"
    manifestless.mkdir()
    bad_manifest = tmp_path / "larch-logs" / "design" / "bad-run"
    bad_manifest.mkdir()
    _ = (bad_manifest / "manifest.json").write_text("{}", encoding="utf-8")

    out = tokens.measure_references_heatmap()

    rows = {(row["skill"], row["reference_path"]): row for row in _tsv_rows(out)}
    assert rows[("design", "skills/design/references/approval-gates.md")]["reads_observed"] == "2"
    assert rows[("design", "skills/design/references/approval-gates.md")]["runs_observed"] == "2"
    assert rows[("design", "skills/design/references/approval-gates.md")]["loads_per_run"] == "1.000000"
    assert rows[("design", "skills/design/references/plan-review.md")]["reads_observed"] == "1"
    assert rows[("design", "skills/design/references/finalize-step5.md")]["reads_observed"] == "1"
    assert rows[("design", "skills/shared/topology.md")]["reads_observed"] == "1"
    assert all("docs/ignored.md" not in row["reference_path"] for row in rows.values())


def test_measure_references_heatmap_skips_symlinked_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_reference_repo(tmp_path, monkeypatch)
    run = _write_valid_run(tmp_path, skill="design", run_id="run1")
    outside = tmp_path / "outside.jsonl"
    _ = outside.write_text(json.dumps({"blocks": [{"type": "tool_use", "name": "Read", "input": {"file_path": "skills/shared/topology.md"}}]}) + "\n", encoding="utf-8")
    (run / "session-transcript.jsonl").symlink_to(outside)

    out = tokens.measure_references_heatmap()

    assert _tsv_rows(out) == []


def test_measure_realized_cost_averages_reference_reads_across_missing_transcripts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _setup_reference_repo(tmp_path, monkeypatch)
    run1 = _write_valid_run(tmp_path, skill="design", run_id="run1")
    _ = _write_valid_run(tmp_path, skill="design", run_id="run2", issue=2)
    _write_transcript(
        run1,
        [
            {
                "blocks": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/shared/topology.md"}},
                ]
            }
        ],
    )
    bad = tmp_path / "larch-logs" / "design" / "issue-less"
    bad.mkdir()
    _ = (bad / "manifest.json").write_text(json.dumps({"title": "bad"}), encoding="utf-8")

    out = tokens.measure_realized_cost()

    rows = {row["skill"]: row for row in _tsv_rows(out)}
    design = rows["design"]
    assert design["invocations"] == "2"
    assert design["skill_md_tokens"] == "3"
    assert design["reference_reads_observed"] == "1"
    assert design["reference_tokens_per_invocation"] == "2.00"
    assert design["realized_tokens"] == "10"
    assert design["tokens_per_invocation"] == "5.00"
    # run1's transcript is present (even though run2's is missing), so this
    # reference-read count is a confirmed measurement, not a blind spot.
    assert design["reference_capture_status"] == "measured"
