from __future__ import annotations

# ruff: noqa: UP022,ARG005
# pyright: reportUnusedCallResult=false, reportUnknownArgumentType=false

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

import issue_create
import rendering
import research

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "cli.py"


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=merged, check=False)


def test_planner_sanitizes_and_rejects_count_and_delimiter(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    out = tmp_path / "subquestions.txt"
    raw.write_text("Here are some questions\n- What changed?\n* Why now?\n\x01noise\n", encoding="utf-8")
    assert research.run_research_planner(raw, out) == ("success", 0)
    assert out.read_text(encoding="utf-8") == "What changed?\nWhy now?\n"
    raw.write_text("What || breaks?\nWhy?\n", encoding="utf-8")
    assert research.run_research_planner(raw, out) == ("delimiter_collision", 1)
    raw.write_text("Only one?\n", encoding="utf-8")
    assert research.run_research_planner(raw, out) == ("count_below_minimum", 1)
    raw.write_text("A?\nB?\nC?\nD?\nE?\n", encoding="utf-8")
    assert research.run_research_planner(raw, out) == ("count_above_maximum", 1)
    assert research.run_research_planner(tmp_path / "missing", out) == ("empty_input", 1)
    assert research.run_research_planner(raw, tmp_path / "missing" / "out") == ("bad_path", 2)


def test_planner_cli_exit_codes(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    out = tmp_path / "out.txt"
    raw.write_text("A?\nB?\n", encoding="utf-8")
    ok = run_cli("research", "run-planner", "--raw", str(raw), "--output", str(out))
    assert ok.returncode == 0
    assert ok.stdout.splitlines() == ["COUNT=2", f"OUTPUT={out}"]
    bad = run_cli("research", "run-planner", "--raw", str(raw), "--output", str(tmp_path / "x" / "out"))
    assert bad.returncode == 2
    assert bad.stdout.strip() == "REASON=bad_path"


def test_banner_matches_only_research_status(tmp_path: Path) -> None:
    lane = tmp_path / "lane-status.txt"
    lane.write_text(
        "VALIDATION_CODE_STATUS=fallback_claude\n"
        "RESEARCH_ARCH_REASON=mentions fallback_claude\n"
        "RESEARCH_ARCH_STATUS=fallback_claude\n"
        "RESEARCH_SEC_STATUS=ok\n",
        encoding="utf-8",
    )
    assert research.compute_research_banner(lane) == research.BANNER_TEMPLATE.replace("<N_FALLBACK>", "1")
    lane.write_text("RESEARCH_ARCH_REASON=fallback_claude\n", encoding="utf-8")
    assert research.compute_research_banner(lane) == ""


def test_findings_rendering_reuses_rendering_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = False
    real = rendering.render_findings_issue_batch

    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal called
        called = True
        return real(*args, **kwargs)

    monkeypatch.setattr(rendering, "render_findings_issue_batch", wrapper)
    report = tmp_path / "report.md"
    question = tmp_path / "question.txt"
    out = tmp_path / "batch.md"
    question.write_text("How safe is this?\n", encoding="utf-8")
    report.write_text(
        "### Findings Summary\n\n"
        "1. First finding. Details cite `x`.\n"
        "### Body heading must be escaped\n\n"
        "2. Second finding! More text.\n\n"
        "### Risk Assessment\nHigh\n"
        "### Difficulty Estimate\nMedium\n"
        "### Feasibility Verdict\nFeasible\n"
        "### Key Files and Areas\n- python/research.py\n- skills/research/SKILL.md\n"
        "### Open Questions\n- Who owns rollout?\n",
        encoding="utf-8",
    )
    count, absent = research.render_findings_batch(report, out, question, "br", "abc", timestamp="2026-01-01T00:00:00Z")
    assert called
    assert (count, absent) == (2, False)
    body = out.read_text(encoding="utf-8")
    assert "### First finding" in body
    assert "\\### Body heading must be escaped" in body
    assert "**Files touched**: python/research.py, skills/research/SKILL.md" in body


def test_findings_cli_missing_and_empty(tmp_path: Path) -> None:
    q = tmp_path / "q.txt"
    q.write_text("Question\n", encoding="utf-8")
    out = tmp_path / "out.md"
    missing = run_cli("research", "render-findings-batch", "--report", str(tmp_path / "missing"), "--output", str(out), "--research-question-file", str(q), "--branch", "b", "--commit", "c")
    assert missing.returncode == 2
    assert f"ERROR: report file not found: {tmp_path / 'missing'}" in missing.stderr
    report = tmp_path / "report.md"
    report.write_text("### Findings Summary\n\n### Risk Assessment\nLow\n", encoding="utf-8")
    empty = run_cli("research", "render-findings-batch", "--report", str(report), "--output", str(out), "--research-question-file", str(q), "--branch", "b", "--commit", "c")
    assert empty.returncode == 3
    assert empty.stdout.strip() == "COUNT=0"
    assert out.read_text(encoding="utf-8") == ""


def test_citation_extraction_and_fileline_sidecar(tmp_path: Path) -> None:
    repo_file = ROOT / "README.md"
    report = tmp_path / "report.md"
    out = tmp_path / "citation.md"
    report.write_text(
        f"See https://example.com/doc and DOI 10.1000/xyz plus README.md:1 and {repo_file.name}:999999.\n",
        encoding="utf-8",
    )

    def fake_fetch(url: str) -> research.FetchResult:
        if url.startswith("https://doi.org/"):
            return research.FetchResult("UNKNOWN", "redirect-not-followed")
        return research.FetchResult("PASS")

    counts = research.validate_citations(report, out, tmp_path, max_claims=10, fetcher=fake_fetch, git_root=ROOT)
    assert counts[0] >= 2
    text = out.read_text(encoding="utf-8")
    assert "**Validator**: validate-citations.sh v1" in text
    assert "| `https://example.com/doc` | url | PASS |" in text
    assert "| `10.1000/xyz` | doi | PASS |" in text
    assert "README.md:1" in text


def test_fetch_url_reason_matrix_and_ssrf() -> None:
    assert research.fetch_url("http://example.com").token() == "FAIL(non-https)"
    assert research.fetch_url("https://127.0.0.1/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://100.64.0.1/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://example.com/", resolver=lambda host: ["10.0.0.1"]).token() == "FAIL(ssrf-private-resolved)"

    def connector(_url: str, pinned_ip: str | None, _timeout: int) -> int:
        assert pinned_ip == "93.184.216.34"
        return 404

    assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=connector).token() == "FAIL(head-not-found)"
    for code, token in ((403, "UNKNOWN(head-not-supported)"), (405, "UNKNOWN(head-not-supported)"), (501, "UNKNOWN(head-not-supported)"), (302, "UNKNOWN(redirect-not-followed)")):
        assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=lambda _u, _p, _t, status=code: status).token() == token


def test_resolve_public_ips_maps_dns_failure_to_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise socket.gaierror(8, "dns")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    ips, reason = research._resolve_public_ips("example.com", timeout=1)
    assert ips == []
    assert reason == "network-error"


def test_banner_template_matches_research_phase_literal() -> None:
    phase = (ROOT / "skills/research/references/research-phase.md").read_text(encoding="utf-8")
    match = re.search(r"```\n(\*\*⚠ Reduced lane diversity:[^\n]+)\n```", phase)
    assert match is not None
    assert match.group(1).strip() == research.BANNER_TEMPLATE


def test_fileline_failure_modes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("one\n", encoding="utf-8")
    (repo / "dir").mkdir()
    assert research.check_fileline("README.md:1", git_root=repo).token() == "PASS"
    assert research.check_fileline("README.md:9", git_root=repo).token() == "FAIL(line-out-of-range)"
    assert research.check_fileline("README.md:3-1", git_root=repo).token() == "FAIL(line-range-empty)"
    assert research.check_fileline("missing.md", git_root=repo).token() == "FAIL(file-not-found)"
    assert research.check_fileline("dir", git_root=repo).token() == "FAIL(path-is-directory)"




def test_parallel_fetch_budget_backfill_and_subprocess_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    spawned: list[subprocess.Popen[bytes]] = []

    def fake_start(_url: str, *, timeout: int) -> subprocess.Popen[bytes]:
        _ = timeout
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            ["sleep", "30"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        spawned.append(proc)
        return proc

    monkeypatch.setattr(research, "_start_fetch_process", fake_start)
    start = time.monotonic()
    results = research._parallel_fetch_results(
        {"u1": "https://hang.example/a", "u2": "https://hang.example/b"},
        budget_seconds=1,
        per_fetch_timeout=10,
        fetcher=None,
        sleeper=time.sleep,
    )
    elapsed = time.monotonic() - start
    assert elapsed >= 0.9
    assert all(result.token() == "UNKNOWN(timeout)" for result in results.values())
    time.sleep(0.2)
    assert spawned
    assert all(proc.poll() is not None for proc in spawned)


def test_validate_citations_budget_writes_timeout_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text("See https://hang.example/a and https://hang.example/b\n", encoding="utf-8")

    def fake_start(_url: str, *, timeout: int) -> subprocess.Popen[bytes]:
        _ = timeout
        return subprocess.Popen(["sleep", "30"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    monkeypatch.setattr(research, "_start_fetch_process", fake_start)
    research.validate_citations(report, out, tmp_path, budget_seconds=1, sleeper=time.sleep)
    assert "timeout" in out.read_text(encoding="utf-8")


def test_validate_citations_summary_is_last_stdout_line(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text(f"See {ROOT / 'README.md'}:1\n", encoding="utf-8")
    cp = run_cli("research", "validate-citations", "--report", str(report), "--output", str(out), "--tmpdir", str(tmp_path))
    assert cp.returncode == 0
    lines = [line for line in cp.stdout.splitlines() if line.strip()]
    assert lines[-1].startswith("SUMMARY=")


def test_findings_batch_round_trip_parse_input(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    question = tmp_path / "question.txt"
    batch = tmp_path / "batch.md"
    out_dir = tmp_path / "issues"
    question.write_text("How safe is this?\n", encoding="utf-8")
    report.write_text(
        "### Findings Summary\n\n"
        "1. First finding cites `python/research.py`.\n"
        "### Risk Assessment\nLow\n"
        "### Difficulty Estimate\nLow\n"
        "### Feasibility Verdict\nFeasible\n"
        "### Key Files and Areas\n- python/research.py\n"
        "### Open Questions\n- none\n",
        encoding="utf-8",
    )
    count, _ = research.render_findings_batch(report, batch, question, "br", "abc", timestamp="2026-01-01T00:00:00Z")
    assert count == 1
    assert issue_create.parse_input_main(["--input-file", str(batch), "--output-dir", str(out_dir)]) == 0
    assert any(out_dir.glob("item-*-body.txt"))


def _quiet_fd3_cli(*cli_args: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    py = (
        "import os, subprocess, sys; "
        "fd=os.open(sys.argv[1], os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600); os.dup2(fd,3); os.close(fd); "
        f"raise SystemExit(subprocess.call([{sys.executable!r}, {str(CLI)!r}, *sys.argv[2:]]))"
    )
    fd3 = tmp_path / "fd3.txt"
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    return subprocess.run([sys.executable, "-c", py, str(fd3), *cli_args], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


@pytest.mark.parametrize(
    ("args", "expect"),
    [
        (("research", "run-planner", "--raw", "RAW", "--output", "OUT"), "COUNT="),
        (("research", "banner", "LANE"), "Reduced lane diversity"),
        (("research", "render-findings-batch", "--report", "REPORT", "--output", "OUT", "--research-question-file", "Q", "--branch", "b", "--commit", "c"), "COUNT="),
        (("research", "validate-citations", "--report", "REPORT", "--output", "OUT", "--tmpdir", "TMP"), "SUMMARY="),
    ],
)
def test_quiet_fd3_contract_for_all_research_verbs(tmp_path: Path, args: tuple[str, ...], expect: str) -> None:
    raw = tmp_path / "raw.txt"
    out = tmp_path / "out.txt"
    lane = tmp_path / "lane.txt"
    report = tmp_path / "report.md"
    question = tmp_path / "q.txt"
    raw.write_text("A?\nB?\n", encoding="utf-8")
    lane.write_text("RESEARCH_ARCH_STATUS=fallback_claude\n", encoding="utf-8")
    report.write_text("### Findings Summary\n\n1. One finding.\n### Risk Assessment\nLow\n### Difficulty Estimate\nLow\n### Feasibility Verdict\nFeasible\n### Key Files and Areas\n- python/research.py\n### Open Questions\n- none\n", encoding="utf-8")
    question.write_text("Question?\n", encoding="utf-8")
    resolved = []
    for part in args:
        resolved.append(
            {
                "RAW": str(raw),
                "OUT": str(out),
                "LANE": str(lane),
                "REPORT": str(report),
                "Q": str(question),
                "TMP": str(tmp_path),
            }.get(part, part)
        )
    got = _quiet_fd3_cli(*resolved, tmp_path=tmp_path)
    assert got.returncode in {0, 3}
    fd3 = (tmp_path / "fd3.txt").read_text(encoding="utf-8")
    assert expect in fd3 or expect in got.stdout


def test_validate_citations_cli_unreadable_and_invalid_flags(tmp_path: Path) -> None:
    out = tmp_path / "sidecar.md"
    cp = run_cli("research", "validate-citations", "--report", str(tmp_path / "missing"), "--output", str(out), "--tmpdir", str(tmp_path))
    assert cp.returncode == 0
    assert cp.stdout.strip() == "SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0"
    assert "input report not readable" in out.read_text(encoding="utf-8")
    bad = run_cli("research", "validate-citations", "--report", str(tmp_path / "missing"), "--output", str(out), "--tmpdir", str(tmp_path), "--max-claims", "nope")
    assert bad.returncode == 2
    assert "SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0" in bad.stdout


def test_quiet_contract_stream_for_research_verbs(tmp_path: Path) -> None:
    raw = tmp_path / "raw.txt"
    out = tmp_path / "out.txt"
    raw.write_text("A?\nB?\n", encoding="utf-8")
    py = (
        "import os, subprocess, sys; "
        "fd=os.open(sys.argv[1], os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600); os.dup2(fd,3); os.close(fd); "
        f"raise SystemExit(subprocess.call([{sys.executable!r}, {str(CLI)!r}, 'research', 'run-planner', '--raw', {str(raw)!r}, '--output', {str(out)!r}]))"
    )
    fd3 = tmp_path / "fd3.txt"
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    got = subprocess.run([sys.executable, "-c", py, str(fd3)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    assert got.returncode == 0
    assert "COUNT=2" in got.stdout
