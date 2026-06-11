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
    tokens.TokenLedger(ledger).record_vendor("codex", total=123, raw="codex_implement")
    dump = tokens.TokenLedger(ledger).dump()
    assert '"type":"mark"' in dump
    assert '"vendor":"codex"' in dump
    assert '"total":123' in dump
    assert oct(ledger.stat().st_mode & 0o777) == oct(0o600)


def test_token_ledger_rejects_claude_vendor(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError, match="claude"):
        tokens.TokenLedger(ledger).record_vendor("claude", total=1)


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
    assert tokens._classify_md_tier("CLAUDE.md", imports) == "tier-1a-claude-root"  # pyright: ignore[reportPrivateUsage]
    assert tokens._classify_md_tier("AGENTS.md", imports) == "tier-1a-claude-import"  # pyright: ignore[reportPrivateUsage]
    assert tokens._classify_md_tier("skills/implement/SKILL.md", imports) == "tier-1b-runtime-skill"  # pyright: ignore[reportPrivateUsage]


def test_normalize_read_path_handles_absolute_and_cache(tmp_path: Path) -> None:
    repo = tmp_path
    rel = tokens._normalize_read_path(f"{repo}/docs/foo.md", repo)  # pyright: ignore[reportPrivateUsage]
    assert rel == "docs/foo.md"
    cached = tokens._normalize_read_path("/Users/me/.cache/larch/sessions/run-1/docs/foo.md", repo)  # pyright: ignore[reportPrivateUsage]
    assert cached == "run-1/docs/foo.md"
    assert tokens._normalize_read_path("/etc/passwd", repo) is None  # pyright: ignore[reportPrivateUsage]


def test_ngram_source_files_include_claude_imports() -> None:
    files = tokens._ngram_source_files(tokens._repo_root())  # pyright: ignore[reportPrivateUsage]
    assert "CLAUDE.md" in files
    assert "AGENTS.md" in files
