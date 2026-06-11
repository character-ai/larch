"""Tests for tokens.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tokens


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
    tokens.append_token_record(path, record)
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
    out = tokens._claude_rows(rows, [{"ts": 0.0, "step": "Step 0"}])  # pyright: ignore[reportPrivateUsage]
    assert len(out) == 2


def test_token_claude_source_requires_complete_snapshot(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    snap = tmp_path / "source.env"
    _ = snap.write_text(f"TRANSCRIPT_PATH={transcript}\n", encoding="utf-8")
    out = tokens.token_claude_source(claude_source_file=snap, env={"HOME": str(tmp_path)})
    assert out.get("STATUS") == "unavailable"


def test_token_claude_source_accepts_complete_snapshot(tmp_path: Path) -> None:
    transcript = tmp_path / "session.jsonl"
    _ = transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    session_dir = tmp_path / "session-uuid"
    session_dir.mkdir()
    snap = tmp_path / "source.env"
    _ = snap.write_text(
        f"TRANSCRIPT_PATH={transcript}\nSESSION_DIR={session_dir}\nSESSION_UUID=session-uuid\n",
        encoding="utf-8",
    )
    out = tokens.token_claude_source(claude_source_file=snap)
    assert out["TRANSCRIPT_PATH"] == str(transcript)
    assert out["SESSION_DIR"] == str(session_dir)
    assert out["SESSION_UUID"] == "session-uuid"


def test_replace_block_ignores_prose_marker_mentions(tmp_path: Path) -> None:
    target = tmp_path / "body.md"
    _ = target.write_text(
        "Mention <!-- token-report-begin --> in prose\n\n"
        "<!-- token-report-begin -->\nold\n<!-- token-report-end -->\n",
        encoding="utf-8",
    )
    tokens._replace_block(target, "BLOCK\n", begin="token-report-begin", end="token-report-end")  # pyright: ignore[reportPrivateUsage]
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
