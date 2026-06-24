"""Tests for tokens.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import tokens


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
    run_dir = repo / "larch-logs" / "implement" / "RUN1"
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
    assert text.startswith("skill\tinvocations\tissues_observed\ttokens_per_invocation\trealized_tokens\n")
    row = text.strip().splitlines()[1].split("\t")
    assert row[0] == "review"
    assert row[1] == "1"
    assert row[2] == "1"
    assert row[3] == "11"
    assert row[4] == "11"


def test_measure_md_cost_main_prints_relative_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "larch-logs" / "measure-md-cost" / "fixture-day.tsv"
    out.parent.mkdir(parents=True)
    _ = out.write_text("path\ttier\tbytes\ttokens\tlines\th2_count\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "measure_md_cost", lambda: out)
    monkeypatch.setattr(tokens, "_repo_root", lambda: tmp_path)
    rc = tokens.measure_md_cost_main([])
    assert rc == 0


def test_tokens_imports_without_tiktoken() -> None:
    code = "import importlib; importlib.import_module('tokens')"
    proc = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parent, capture_output=True, text=True, check=False)
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
