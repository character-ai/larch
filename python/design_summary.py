"""Python CLI entrypoint for /design final summary rendering."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


_VALID_OUTCOMES = frozenset({
    "approved", "approved-partition",
    "cancelled-clarify", "cancelled-already-planned", "cancelled-reentry-guard",
    "cancelled-title-filter", "cancelled-sprawl", "cancelled-plan-size",
    "cancelled-decompose", "cancelled-outline",
    "failed-plan-write", "failed-publish", "failed-postplan",
    "failed-clarify", "failed-judge-panel", "failed-publish-tail",
    "publish-skipped",
})


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    root = _plugin_root()
    return subprocess.run(
        [sys.executable, str(root / "python" / "cli.py"), *args],
        capture_output=True, text=True, check=False,
    )


def _read_token_report(design_tmpdir: Path) -> dict[str, int]:
    tok_json = design_tmpdir / "token-report-final.json"
    if not tok_json.is_file():
        return {}
    try:
        data: dict[str, object] = json.loads(tok_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    buckets: dict[str, int] = {}
    for vendor, prefix in (("claude", "C"), ("codex", "D"), ("cursor", "U"), ("claude_sub", "CS")):
        bkey = f"BUCKETS_{vendor}"
        if bkey in data and isinstance(data[bkey], dict):
            b: dict[str, object] = data[bkey]  # type: ignore[assignment]
            buckets[f"{prefix}_IN"] = int(b.get("input", 0) or 0)  # type: ignore[arg-type]
            buckets[f"{prefix}_CR"] = int(b.get("cache_read", 0) or 0)  # type: ignore[arg-type]
            if vendor in ("claude", "claude_sub"):
                buckets[f"{prefix}_CW5"] = int(b.get("cache_create_5m", 0) or 0)  # type: ignore[arg-type]
                buckets[f"{prefix}_CW1"] = int(b.get("cache_create_1h", 0) or 0)  # type: ignore[arg-type]
            buckets[f"{prefix}_OUT"] = int(b.get("output", 0) or 0)  # type: ignore[arg-type]
        if vendor in data and isinstance(data[vendor], dict):
            t: dict[str, object] = data[vendor].get("totals", {})  # type: ignore[union-attr]
            buckets[f"{vendor.upper()}_T"] = int(t.get("total", 0) or 0)  # type: ignore[arg-type]
    return buckets


def _build_cost_args(buckets: dict[str, int]) -> list[str]:
    sum_b = sum(v for k, v in buckets.items() if not k.endswith("_T"))
    if sum_b == 0:
        return ["--cost-unavailable"]
    args: list[str] = []
    mapping = [
        ("CLAUDE_T", "--claude-tokens"),
        ("CODEX_T", "--codex-tokens"),
        ("CURSOR_T", "--cursor-tokens"),
        ("CLAUDE_SUB_T", "--claude-sub-tokens"),
        ("C_IN", "--claude-input-tokens"),
        ("C_CR", "--claude-cache-read-tokens"),
        ("C_CW5", "--claude-cache-write-5m-tokens"),
        ("C_CW1", "--claude-cache-write-1h-tokens"),
        ("C_OUT", "--claude-output-tokens"),
        ("D_IN", "--codex-input-tokens"),
        ("D_CR", "--codex-cached-input-tokens"),
        ("D_OUT", "--codex-output-tokens"),
        ("U_IN", "--cursor-input-tokens"),
        ("U_CR", "--cursor-cache-read-tokens"),
        ("U_OUT", "--cursor-output-tokens"),
        ("CS_IN", "--claude-sub-input-tokens"),
        ("CS_CR", "--claude-sub-cache-read-tokens"),
        ("CS_CW5", "--claude-sub-cache-write-5m-tokens"),
        ("CS_CW1", "--claude-sub-cache-write-1h-tokens"),
        ("CS_OUT", "--claude-sub-output-tokens"),
    ]
    for key, flag in mapping:
        if key in buckets:
            args += [flag, str(buckets[key])]
    return args


def _duration(design_tmpdir: Path) -> str:
    tj = design_tmpdir / "timing-report-final.json"
    if not tj.is_file():
        return "N/A"
    try:
        data: dict[str, object] = json.loads(tj.read_text(encoding="utf-8"))
        val = data.get("total_hms") or data.get("total_seconds")
        return str(val) if val else "N/A"
    except (OSError, json.JSONDecodeError):
        return "N/A"


def _oos_info(design_tmpdir: Path) -> tuple[int, str]:
    sentinel = design_tmpdir / "oos-issues-created.md"
    if not sentinel.is_file():
        return 0, ""
    urls: list[str] = []
    for raw_line in sentinel.read_text(encoding="utf-8").splitlines():
        sline = raw_line.strip()
        if sline.startswith("https://"):
            urls.append(sline)
    return len(urls), "\n".join(urls)


def _issue_counts(design_tmpdir: Path) -> tuple[int, int]:
    ei = design_tmpdir / "execution-issues.md"
    if not ei.is_file():
        return 0, 0
    exec_count = warn_count = 0
    in_exec = in_warn = False
    for raw in ei.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s.startswith("## "):
            h = s.lstrip("#").strip().lower()
            in_exec = "execution" in h and "issues" in h
            in_warn = "warning" in h
        elif s.startswith("- "):
            if in_exec:
                exec_count += 1
            elif in_warn:
                warn_count += 1
    return exec_count, warn_count


# Calls `python/cli.py render run-summary` with --claude-input-tokens for per-bucket cost detail.
def invoke_render(
    design_tmpdir: Path,
    outcome: str,
    run_id: str,
    duration: str,
    issue: str,
    issue_url: str,
    oos_count: int,
    oos_urls: str,
    exec_issues: int,
    warnings: int,
    run_logs_path: str,
    cost_args: list[str],
) -> int:
    out_file = design_tmpdir / "final-summary.md"
    rr_args = [
        "render", "run-summary",
        "--skill", "design",
        "--outcome", outcome,
        "--run-id", run_id,
        "--duration", duration,
        "--issue-number", issue or "0",
        "--issue-url", issue_url,
        "--pr-number", "0",
        "--pr-url", "N/A",
        "--plan-review-line", "N/A",
        "--code-review-line", "N/A",
        "--oos-count", str(oos_count),
        "--oos-urls", oos_urls,
        "--exec-issues", str(exec_issues),
        "--warnings", str(warnings),
        "--run-logs-path", run_logs_path,
        "--output-file", str(out_file),
        *cost_args,
    ]
    result = _run_cli(*rr_args)
    return result.returncode


def render_final_summary_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    outcome = ""
    mode_str = "N/A"
    repo = ""
    phase = "post"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--outcome" and i + 1 < len(argv):
            outcome = argv[i + 1]
            i += 2
        elif a == "--mode" and i + 1 < len(argv):
            mode_str = argv[i + 1]
            i += 2
        elif a == "--repo" and i + 1 < len(argv):
            repo = argv[i + 1]
            i += 2
        elif a == "--pre-publish-only":
            phase = "pre"
            i += 1
        elif a == "--post-publish-only":
            phase = "post"
            i += 1
        else:
            i += 1

    _ = mode_str  # consumed for future use

    design_tmpdir_str = os.environ.get("DESIGN_TMPDIR", "")
    if not design_tmpdir_str:
        print("design render-final-summary: DESIGN_TMPDIR unset", file=sys.stderr)
        return 2
    design_tmpdir = Path(design_tmpdir_str)
    if not design_tmpdir.is_dir():
        print("design render-final-summary: DESIGN_TMPDIR not a directory", file=sys.stderr)
        return 2
    if not outcome:
        print("design render-final-summary: --outcome is required", file=sys.stderr)
        return 2
    if outcome not in _VALID_OUTCOMES:
        print(f"design render-final-summary: outcome not in enumeration: {outcome}", file=sys.stderr)
        return 2

    run_id = os.environ.get("SESSION_ID", "") or "unknown"
    issue = os.environ.get("ISSUE_NUMBER", "") or ""

    issue_url = "N/A"
    if issue and issue != "0" and repo and "/" in repo:
        issue_url = f"https://github.com/{repo}/issues/{issue}"

    # Refresh token/timing reports
    _run_cli("token", "report", "--full", "--format", "json",  # pyright: ignore[reportUnusedCallResult]
             "--output", str(design_tmpdir / "token-report-final.json"))
    _run_cli("timing", "report", "--full", "--format", "json",  # pyright: ignore[reportUnusedCallResult]
             "--output", str(design_tmpdir / "timing-report-final.json"))

    buckets = _read_token_report(design_tmpdir)
    cost_args = _build_cost_args(buckets)
    duration = _duration(design_tmpdir)
    oos_count, oos_urls = _oos_info(design_tmpdir)
    exec_issues, warnings = _issue_counts(design_tmpdir)
    run_logs_path = f"larch-logs/design/{run_id}/" if run_id != "unknown" else "N/A"
    out_file = design_tmpdir / "final-summary.md"

    rc = invoke_render(
        design_tmpdir, outcome, run_id, duration, issue, issue_url,
        oos_count, oos_urls, exec_issues, warnings, run_logs_path, cost_args,
    )

    if rc != 0 or not out_file.is_file() or out_file.stat().st_size == 0:
        with out_file.open("w", encoding="utf-8") as fh:
            fh.write(f"## /design run {run_id} — {outcome}\n\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write("**⚠ Degraded fallback — full renderer failed.**\n\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Outcome**: {outcome}\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Duration**: {duration}\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write("- **Cost**: N/A\n")  # pyright: ignore[reportUnusedCallResult]

    if phase == "pre":
        return 0

    try:
        body = out_file.read_text(encoding="utf-8")
        sys.stdout.write(body)  # pyright: ignore[reportUnusedCallResult]
        if not body.endswith("\n"):
            sys.stdout.write("\n")  # pyright: ignore[reportUnusedCallResult]
    except OSError:
        pass

    if issue and issue != "0" and out_file.is_file() and out_file.stat().st_size > 0:
        marker = f"<!-- larch:final-summary v1 runid={run_id} -->"
        ups_args = [
            "tracking-issue", "upsert-summary",
            "--issue", issue,
            "--marker", marker,
            "--content-file", str(out_file),
        ]
        if repo:
            ups_args += ["--repo", repo]
        _run_cli(*ups_args)  # pyright: ignore[reportUnusedCallResult]

    return 0
