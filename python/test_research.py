from __future__ import annotations

# ruff: noqa: UP022,ARG005
# pyright: reportUnusedCallResult=false, reportUnknownArgumentType=false

import concurrent.futures
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
    assert research.run_research_planner(raw=raw, output=out) == ("success", 0)
    assert out.read_text(encoding="utf-8") == "What changed?\nWhy now?\n"
    raw.write_text("What || breaks?\nWhy?\n", encoding="utf-8")
    assert research.run_research_planner(raw=raw, output=out) == ("delimiter_collision", 1)
    raw.write_text("Only one?\n", encoding="utf-8")
    assert research.run_research_planner(raw=raw, output=out) == ("count_below_minimum", 1)
    raw.write_text("A?\nB?\nC?\nD?\nE?\n", encoding="utf-8")
    assert research.run_research_planner(raw=raw, output=out) == ("count_above_maximum", 1)
    assert research.run_research_planner(raw=tmp_path / "missing", output=out) == ("empty_input", 1)
    assert research.run_research_planner(raw=raw, output=tmp_path / "missing" / "out") == ("bad_path", 2)


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
    for args in (
        ("research", "run-planner", "--output", str(out)),
        ("research", "run-planner", "--raw", str(raw)),
        ("research", "run-planner"),
    ):
        missing = run_cli(*args)
        assert missing.returncode == 2
        assert missing.stdout.strip() == "REASON=missing_arg"


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
    count, absent = research.render_findings_batch(report=report, output=out, research_question_file=question, branch="br", commit="abc", timestamp="2026-01-01T00:00:00Z")
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
    report_dir = tmp_path / "report_dir"
    report_dir.mkdir()
    dir_case = run_cli("research", "render-findings-batch", "--report", str(report_dir), "--output", str(out), "--research-question-file", str(q), "--branch", "b", "--commit", "c")
    assert dir_case.returncode == 2
    assert f"ERROR: report file not found: {report_dir}" in dir_case.stderr
    report = tmp_path / "report.md"
    report.write_text("### Findings Summary\n\n### Risk Assessment\nLow\n", encoding="utf-8")
    empty = run_cli("research", "render-findings-batch", "--report", str(report), "--output", str(out), "--research-question-file", str(q), "--branch", "b", "--commit", "c")
    assert empty.returncode == 3
    assert empty.stdout.strip() == "COUNT=0"
    assert out.read_text(encoding="utf-8") == ""


def test_validate_citations_no_claims_prose_sidecar(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text(
        "### Findings Summary\n\n1. Pure prose synthesis with no URLs, DOIs, or file-line claims.\n",
        encoding="utf-8",
    )
    assert research.validate_citations(report=report, output=out, tmpdir=tmp_path, git_root=ROOT) == (0, 0, 0, 0)
    text = out.read_text(encoding="utf-8")
    assert "_No citable provenance (URLs, DOIs, file:line) found in the synthesis." in text
    assert "**Claims extracted**: 0" in text
    cp = run_cli("research", "validate-citations", "--report", str(report), "--output", str(out), "--tmpdir", str(tmp_path))
    assert cp.returncode == 0
    assert cp.stdout.strip() == "SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0"


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

    counts = research.validate_citations(report=report, output=out, tmpdir=tmp_path, max_claims=10, fetcher=fake_fetch, git_root=ROOT)
    assert counts[0] >= 2
    text = out.read_text(encoding="utf-8")
    assert "**Validator**: validate-citations.sh v1" in text
    assert "| `https://example.com/doc` | url | PASS |" in text
    assert "| `10.1000/xyz` | doi | PASS |" in text
    assert "README.md:1" in text
    assert "<details><summary>Domain credibility (advisory only)</summary>" in text
    assert "| example.com | unknown |" in text
    assert "| doi.org | allow |" in text


def test_fetch_url_rejects_malformed_port() -> None:
    assert research.fetch_url("https://example.com:bad/").token() == "FAIL(invalid-url)"


def test_validate_citations_malformed_url_port_with_valid_url(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text(
        "See https://example.com:bad/ and https://example.com/valid.\n",
        encoding="utf-8",
    )

    def fake_fetch(url: str) -> research.FetchResult:
        if url == "https://example.com/valid":
            return research.FetchResult("PASS")
        return research.FetchResult("FAIL", "invalid-url")

    counts = research.validate_citations(report=report, output=out, tmpdir=tmp_path, fetcher=fake_fetch)
    assert counts == (1, 1, 0, 2)
    text = out.read_text(encoding="utf-8")
    assert "| `https://example.com:bad/` | url | FAIL | invalid-url |" in text
    assert "| `https://example.com/valid` | url | PASS |" in text
    assert "validation interrupted: unexpected error" not in text


def test_fetch_url_uses_non_default_https_port() -> None:
    seen: dict[str, str] = {}

    def connector(_url: str, pinned_ip: str | None, _timeout: int) -> int:
        seen["pinned_ip"] = pinned_ip or ""
        return 200

    assert (
        research.fetch_url(
            "https://example.com:8443/doc",
            resolver=lambda host: ["93.184.216.34"],
            connector=connector,
        ).token()
        == "PASS"
    )
    assert seen["pinned_ip"] == "93.184.216.34"


def test_fetch_url_host_header_omits_userinfo(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_headers: dict[str, str] = {}

    class FakeConn:
        def __init__(self, host: str, port: int, pinned_ip: str | None, timeout: float) -> None:
            _ = (host, port, pinned_ip, timeout)

        def request(self, method: str, path: str, headers: dict[str, str] | None = None) -> None:
            _ = (method, path)
            seen_headers.update(headers or {})

        def getresponse(self) -> object:
            class Resp:
                status = 200

            return Resp()

        def close(self) -> None:
            return None

    monkeypatch.setattr(research, "_PinnedHTTPSConnection", FakeConn)
    assert research.fetch_url("https://user:pass@example.com/a", resolver=lambda host: ["93.184.216.34"]).token() == "PASS"
    assert seen_headers["Host"] == "example.com"


def test_fetch_url_ignores_proxy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.setenv(key, "http://127.0.0.1:9")

    def connector(_url: str, pinned_ip: str | None, _timeout: int) -> int:
        seen["pinned_ip"] = pinned_ip or ""
        return 200

    assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=connector).token() == "PASS"
    assert seen["pinned_ip"] == "93.184.216.34"


def test_credibility_tier_allow_list() -> None:
    assert research._credibility_tier("en.wikipedia.org") == "allow"  # pyright: ignore[reportPrivateUsage]
    assert research._credibility_tier("arxiv.org") == "allow"  # pyright: ignore[reportPrivateUsage]
    assert research._credibility_tier("api.github.com") == "allow"  # pyright: ignore[reportPrivateUsage]
    assert research._credibility_tier("example.com") == "unknown"  # pyright: ignore[reportPrivateUsage]


def test_parallel_fetch_enforces_per_fetch_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
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
    results = research._parallel_fetch_results(  # pyright: ignore[reportPrivateUsage]
        {"u1": "https://hang.example/a"},
        budget_seconds=300,
        per_fetch_timeout=1,
        fetcher=None,
        sleeper=time.sleep,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 5
    assert results["u1"].token() == "UNKNOWN(timeout)"
    time.sleep(0.2)
    assert spawned
    assert all(proc.poll() is not None for proc in spawned)


def test_fetch_url_reason_matrix_and_ssrf() -> None:
    assert research.fetch_url("http://example.com").token() == "FAIL(non-https)"
    assert research.fetch_url("https://127.0.0.1/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://100.64.0.1/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://[::1]/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://[fd00::1]/").token() == "FAIL(ssrf-private-host)"
    assert research.fetch_url("https://example.com/", resolver=lambda host: ["10.0.0.1"]).token() == "FAIL(ssrf-private-resolved)"
    assert research.fetch_url("https://example.com/", resolver=lambda host: []).token() == "UNKNOWN(network-error)"
    assert research.fetch_url("https://example.com/", resolver=lambda host: [], connector=lambda _u, _p, _t: 200).token() == "UNKNOWN(network-error)"

    def connector(_url: str, pinned_ip: str | None, _timeout: int) -> int:
        assert pinned_ip == "93.184.216.34"
        return 404

    assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=connector).token() == "FAIL(head-not-found)"
    assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=lambda _u, _p, _t: 410).token() == "FAIL(head-not-found)"
    for code, token in ((403, "UNKNOWN(head-not-supported)"), (405, "UNKNOWN(head-not-supported)"), (501, "UNKNOWN(head-not-supported)"), (302, "UNKNOWN(redirect-not-followed)")):
        assert research.fetch_url("https://example.com/", resolver=lambda host: ["93.184.216.34"], connector=lambda _u, _p, _t, status=code: status).token() == token


def test_resolve_public_ips_maps_dns_failure_to_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise socket.gaierror(8, "dns")

    monkeypatch.setattr(research.socket, "getaddrinfo", boom)
    ips, reason = research._resolve_public_ips("example.com", timeout=1)  # pyright: ignore[reportPrivateUsage]
    assert ips == []
    assert reason == "network-error"


def test_resolve_public_ips_times_out_slow_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    class TimeoutFuture:
        def result(self, timeout: float | None = None) -> list[object]:
            _ = timeout
            raise concurrent.futures.TimeoutError

    class SyncPool:
        def submit(self, *_args: object, **_kwargs: object) -> TimeoutFuture:
            return TimeoutFuture()

        def shutdown(self, *, wait: bool = False, cancel_futures: bool = False) -> None:
            _ = (wait, cancel_futures)

    monkeypatch.setattr(research.concurrent.futures, "ThreadPoolExecutor", lambda max_workers=1: SyncPool())
    ips, reason = research._resolve_public_ips("example.com", timeout=0.2)  # pyright: ignore[reportPrivateUsage]
    assert ips == []
    assert reason == "timeout"


def test_banner_template_matches_research_phase_literal() -> None:
    phase = (ROOT / "skills/research/references/research-phase.md").read_text(encoding="utf-8")
    match = re.search(r"```\n(\*\*⚠ Reduced lane diversity:[^\n]+)\n```", phase)
    assert match is not None
    assert match.group(1).strip() == research.BANNER_TEMPLATE


def _research_sidecar_ingestion_snippet() -> str:
    phase = (ROOT / "skills/research/references/research-phase.md").read_text(encoding="utf-8")
    match = re.search(
        r"For each selected output path, set `SIDECAR=.*?```bash\n(?P<body>.*?)\n```",
        phase,
        re.DOTALL,
    )
    assert match is not None
    return match.group("body")


def _run_research_sidecar_ingestion_snippet(
    tmp_path: Path,
    *,
    fail_verb: str,
    fail_code: int,
) -> subprocess.CompletedProcess[str]:
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    python_stub = stub_dir / "python3"
    python_stub.write_text(
        """#!/usr/bin/env bash
if [[ "$*" == *"token append-record"* ]]; then
  if [[ "${FAIL_VERB:-}" == "append-record" ]]; then
    printf 'append diagnostic\\n' >&2
    exit "${FAIL_CODE:-37}"
  fi
  exit 0
fi
if [[ "$*" == *"token record-vendor-sidecar"* ]]; then
  if [[ "${FAIL_VERB:-}" == "record-vendor-sidecar" ]]; then
    printf 'active diagnostic\\n' >&2
    exit "${FAIL_CODE:-43}"
  fi
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    python_stub.chmod(0o755)
    sidecar = tmp_path / "codex-output.txt.token-record"
    sidecar.write_text("TOOL=codex\nTOTAL=1\n", encoding="utf-8")
    snippet = tmp_path / "snippet.sh"
    snippet.write_text(_research_sidecar_ingestion_snippet(), encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "PATH": f"{stub_dir}{os.pathsep}{env['PATH']}",
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "RESEARCH_TMPDIR": str(tmp_path),
        "SIDECAR": str(sidecar),
        "FAIL_VERB": fail_verb,
        "FAIL_CODE": str(fail_code),
    })
    return subprocess.run(
        ["bash", "-euo", "pipefail", str(snippet)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def test_research_sidecar_append_warning_reports_real_exit_code(tmp_path: Path) -> None:
    result = _run_research_sidecar_ingestion_snippet(tmp_path, fail_verb="append-record", fail_code=37)

    assert result.returncode == 0
    assert "WARNING: token append-record failed with exit 37: append diagnostic" in result.stderr
    assert "exit 0" not in result.stderr


def test_research_sidecar_active_warning_reports_real_exit_code(tmp_path: Path) -> None:
    result = _run_research_sidecar_ingestion_snippet(
        tmp_path,
        fail_verb="record-vendor-sidecar",
        fail_code=43,
    )

    assert result.returncode == 0
    assert "WARNING: token record-vendor-sidecar failed with exit 43: active diagnostic" in result.stderr
    assert "exit 0" not in result.stderr


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


def test_fileline_git_root_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_rev_parse(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git", "rev-parse", "--show-toplevel"], 1, "", "")

    monkeypatch.setattr(research.subprocess, "run", fail_rev_parse)
    assert research.check_fileline("README.md:1").token() == "UNKNOWN(git-root-unavailable)"


def test_fileline_out_of_tree_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    (repo / "escape").symlink_to(outside)
    assert research.check_fileline("escape:1", git_root=repo).token() == "UNKNOWN(out-of-tree-path-after-realpath)"


def test_fileline_unreadable_returns_unknown(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = repo / "secret.md"
    path.write_text("one\n", encoding="utf-8")
    path.chmod(0o000)
    try:
        assert research.check_fileline("secret.md:1", git_root=repo).token() == "UNKNOWN(file-unreadable)"
    finally:
        path.chmod(0o644)
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
    results = research._parallel_fetch_results(  # pyright: ignore[reportPrivateUsage]
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


def test_validate_citations_max_claims_truncation(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    lines: list[str] = []
    for i in range(1, 6):
        lines.append(f"URL {i}: https://example.com/page-{i}")
    for i in range(1, 6):
        lines.append(f"DOI {i}: 10.1234/foo-{i}")
    for i in range(1, 6):
        lines.append(f"File {i}: README.md:{i}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "sidecar.md"

    def fake_fetch(_url: str) -> research.FetchResult:
        return research.FetchResult("PASS")

    research.validate_citations(report=report, output=out, tmpdir=tmp_path, max_claims=6, fetcher=fake_fetch, git_root=ROOT)
    text = out.read_text(encoding="utf-8")
    assert text.count("| `") == 6
    assert "claim count exceeded `--max-claims=6`" in text


def test_validate_citations_budget_writes_timeout_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text("See https://hang.example/a and https://hang.example/b\n", encoding="utf-8")

    def fake_start(_url: str, *, timeout: int) -> subprocess.Popen[bytes]:
        _ = timeout
        return subprocess.Popen(["sleep", "30"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    monkeypatch.setattr(research, "_start_fetch_process", fake_start)
    research.validate_citations(report=report, output=out, tmpdir=tmp_path, budget_seconds=1, sleeper=time.sleep)
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
    count, _ = research.render_findings_batch(report=report, output=batch, research_question_file=question, branch="br", commit="abc", timestamp="2026-01-01T00:00:00Z")
    assert count == 1
    assert issue_create.parse_input_main(["--input-file", str(batch), "--output-dir", str(out_dir)]) == 0
    assert any(out_dir.glob("item-*-body.txt"))


def _run_quiet_cli(*cli_args: str, tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path | None]:
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    got = subprocess.run(
        [sys.executable, str(CLI), *cli_args],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    quiet_logs = list(tmp_path.glob("larch-quiet-*.log"))
    return got, quiet_logs[0] if quiet_logs else None


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
    resolved: list[str] = []
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
    got, quiet_log = _run_quiet_cli(*resolved, tmp_path=tmp_path)
    assert got.returncode in {0, 3}
    assert expect in got.stdout
    assert quiet_log is not None
    assert expect not in quiet_log.read_text(encoding="utf-8")
    assert expect not in got.stderr


def test_validate_citations_fail_soft_on_mid_run_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = tmp_path / "report.md"
    out = tmp_path / "sidecar.md"
    report.write_text("See https://example.com/a\n", encoding="utf-8")

    def boom(*_args: object, **_kwargs: object) -> dict[str, research.FetchResult]:
        raise OSError("disk full")

    captured: list[str] = []

    def capture_emit(text: str) -> None:
        captured.append(text)

    monkeypatch.setattr(research, "_parallel_fetch_results", boom)
    monkeypatch.setattr(research.logging_util, "emit", capture_emit)
    research.validate_citations(report=report, output=out, tmpdir=tmp_path)
    assert out.is_file()
    assert "filesystem error" in out.read_text(encoding="utf-8")
    assert captured[-1].startswith("SUMMARY=")


def test_validate_citations_cli_unreadable_and_invalid_flags(tmp_path: Path) -> None:
    out = tmp_path / "sidecar.md"
    cp = run_cli("research", "validate-citations", "--report", str(tmp_path / "missing"), "--output", str(out), "--tmpdir", str(tmp_path))
    assert cp.returncode == 0
    assert cp.stdout.strip() == "SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0"
    assert "input report not readable" in out.read_text(encoding="utf-8")
    bad = run_cli("research", "validate-citations", "--report", str(tmp_path / "missing"), "--output", str(out), "--tmpdir", str(tmp_path), "--max-claims", "nope")
    assert bad.returncode == 2
    assert "SUMMARY=PASS=0 FAIL=0 UNKNOWN=0 TOTAL=0" in bad.stdout


_RENDER_FOOTER = (
    "### Risk Assessment\nLow\n\n### Difficulty Estimate\nS\n\n"
    "### Feasibility Verdict\nYes\n\n### Key Files and Areas\n- f.md\n\n### Open Questions\n"
)


def _assert_render_round_trip(batch: Path, expected_count: int, out_dir: Path) -> None:
    cp = run_cli("issue", "parse-input", "--input-file", str(batch), "--output-dir", str(out_dir))
    assert cp.returncode == 0
    items_total = next(line.split("=", 1)[1] for line in cp.stdout.splitlines() if line.startswith("ITEMS_TOTAL="))
    assert items_total == str(expected_count)
    assert "MALFORMED=true" not in cp.stdout


@pytest.mark.parametrize(
    ("name", "findings_body", "expected_count", "body_contains"),
    [
        (
            "numbered list",
            "1. First finding here. With detail.\n2. Second finding text.\n3. Third finding mentioning `code`.\n",
            3,
            None,
        ),
        (
            "bulleted list",
            "- First bullet finding.\n- Second bullet finding with more text.\n",
            2,
            None,
        ),
        (
            "paragraph-per-item",
            "First finding paragraph. With multiple sentences. And more.\n\nSecond finding paragraph here.\n",
            2,
            None,
        ),
        (
            "planner-mode nested subquestions",
            "#### Subquestion 1: How does X work?\n\n1. Finding A about X.\n2. Finding B about X.\n\n"
            "#### Subquestion 2: How does Y work?\n\n1. Finding C about Y.\n",
            3,
            None,
        ),
        (
            "fenced code with ### inside",
            "1. First finding. Has fenced code:\n\n   ```\n   ### NotAHeading\n   ## NorThis\n   ```\n"
            "2. Second finding.\n",
            2,
            None,
        ),
        (
            "body-line ### escape",
            "- First finding. The body has a literal heading-shaped line below.\n### Bad Header Line\n"
            "This line follows the heading-shaped one inside the first finding's body.\n- Second finding.\n",
            2,
            "\\### Bad Header Line",
        ),
        (
            "empty-title fallback",
            "- !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!?\n- Normal second finding.\n",
            2,
            "### Finding 1",
        ),
        (
            "special characters in body",
            "1. First finding with `code` and $variable and **bold**.\n2. Second finding has \"quotes\" and 'apostrophes'.\n",
            2,
            None,
        ),
        (
            "tab-after-### body escape",
            "- First finding here. Body has tab-after-###:\n###\tTabbed\n- Second finding.\n",
            2,
            "\\###\tTabbed",
        ),
        (
            "indented fence with ### inside",
            "- First finding. Has indented fenced code:\n\n   ```\n   ### NotAHeading\n   ```\n- Second finding.\n",
            2,
            None,
        ),
        (
            "multi-line bulleted continuation",
            "- First finding. With multiple sentences across the item.\n  Continuation line for first finding.\n- Second finding here.\n",
            2,
            None,
        ),
        (
            "nested-numbered sublist",
            "1. First finding with a nested enumeration in its body:\n   1. nested step one\n   2. nested step two\n",
            1,
            None,
        ),
        (
            "nested then top-level sibling",
            "1. First finding with a nested enumeration in its body:\n   1. nested step one\n   2. nested step two\n"
            "2. Second top-level finding.\n",
            2,
            None,
        ),
        (
            "non-planner #### preserved",
            "1. First finding with a subsection heading in its body.\n\n#### Notes on the data\n"
            "The notes section contains additional context that should not be lost.\n",
            1,
            "#### Notes on the data",
        ),
    ],
)
def test_render_findings_batch_retired_harness_fixtures(
    tmp_path: Path, name: str, findings_body: str, expected_count: int, body_contains: str | None
) -> None:
    assert name
    report = tmp_path / "report.md"
    question = tmp_path / "question.txt"
    batch = tmp_path / "batch.md"
    out_dir = tmp_path / "parsed"
    question.write_text("Test research question\n", encoding="utf-8")
    report.write_text(f"## Research Report\n\n### Findings Summary\n\n{findings_body}\n{_RENDER_FOOTER}", encoding="utf-8")
    count, absent = research.render_findings_batch(report=report, output=batch, research_question_file=question, branch="test-branch", commit="deadbee", timestamp="2026-01-01T00:00:00Z")
    assert absent is False
    assert count == expected_count
    body = batch.read_text(encoding="utf-8")
    if body_contains is not None:
        assert body_contains in body
    _assert_render_round_trip(batch, expected_count, out_dir)


def test_render_findings_batch_empty_and_missing_sections(tmp_path: Path) -> None:
    question = tmp_path / "question.txt"
    batch = tmp_path / "batch.md"
    question.write_text("Test research question\n", encoding="utf-8")
    empty_report = tmp_path / "empty.md"
    empty_report.write_text(f"## Research Report\n\n### Findings Summary\n\n{_RENDER_FOOTER}", encoding="utf-8")
    count, absent = research.render_findings_batch(report=empty_report, output=batch, research_question_file=question, branch="b", commit="c", timestamp="2026-01-01T00:00:00Z")
    assert (count, absent) == (0, False)
    assert batch.read_text(encoding="utf-8") == ""
    missing_report = tmp_path / "missing-section.md"
    missing_report.write_text("## Research Report\n\n### Risk Assessment\nN/A\n", encoding="utf-8")
    count, absent = research.render_findings_batch(report=missing_report, output=batch, research_question_file=question, branch="b", commit="c", timestamp="2026-01-01T00:00:00Z")
    assert (count, absent) == (0, True)


def test_validate_citations_url_dedup_and_idempotent_rerun(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text(
        "See https://example.com/dup-page.\nAnd again: https://example.com/dup-page.\nAnd once more: https://example.com/dup-page.\n",
        encoding="utf-8",
    )
    out1 = tmp_path / "cv1.md"
    out2 = tmp_path / "cv2.md"

    def fake_fetch(_url: str) -> research.FetchResult:
        return research.FetchResult("PASS")

    research.validate_citations(report=report, output=out1, tmpdir=tmp_path, fetcher=fake_fetch)
    text = out1.read_text(encoding="utf-8")
    assert text.count("https://example.com/dup-page") == 1
    research.validate_citations(report=report, output=out2, tmpdir=tmp_path, fetcher=fake_fetch)
    assert out1.read_bytes() == out2.read_bytes()
