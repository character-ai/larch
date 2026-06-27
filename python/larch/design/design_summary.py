"""Python CLI entrypoint for /design final summary rendering."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import exec_issue_detail
import review_phase_detail
from design_publish import review_provenance
from larch.report.report_tokens_cost import CODEX_MINI_MODEL


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
    return Path(__file__).resolve().parents[3]


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
    # Split codex by model so the cost line prices gpt-5.4-mini at mini rates.
    # gpt-5.4-mini routes to D_MINI_*; every other model (gpt-5.5, unknown, legacy)
    # folds into D_* (gpt-5.5 rates). Reads `cached_input` (the BUCKETS_codex key).
    by_model = data.get("BUCKETS_codex_by_model")
    if isinstance(by_model, dict):
        bm: dict[str, object] = by_model  # type: ignore[assignment]
        main = {"in": 0, "cr": 0, "out": 0}
        mini = {"in": 0, "cr": 0, "out": 0}
        for model, raw_mb in bm.items():
            if not isinstance(raw_mb, dict):
                continue
            mb: dict[str, object] = raw_mb  # type: ignore[assignment]
            target = mini if model == CODEX_MINI_MODEL else main
            target["in"] += int(mb.get("input", 0) or 0)  # type: ignore[arg-type]
            target["cr"] += int(mb.get("cached_input", 0) or 0)  # type: ignore[arg-type]
            target["out"] += int(mb.get("output", 0) or 0)  # type: ignore[arg-type]
        buckets["D_IN"], buckets["D_CR"], buckets["D_OUT"] = main["in"], main["cr"], main["out"]
        buckets["D_MINI_IN"], buckets["D_MINI_CR"], buckets["D_MINI_OUT"] = mini["in"], mini["cr"], mini["out"]
    return buckets


def _build_cost_args(buckets: dict[str, int]) -> list[str]:
    sum_b = sum(v for k, v in buckets.items() if not k.endswith("_T"))
    if sum_b == 0:
        return ["--cost-unavailable"]
    args: list[str] = []
    mapping: list[tuple[str, str]] = [
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
        ("D_MINI_IN", "--codex-mini-input-tokens"),
        ("D_MINI_CR", "--codex-mini-cached-input-tokens"),
        ("D_MINI_OUT", "--codex-mini-output-tokens"),
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
    result = exec_issue_detail.load_issue_detail_groups(design_tmpdir, run_dir=None)
    return exec_issue_detail.count_load_result(result)


def _plan_review_line(design_tmpdir: Path) -> str:
    """Render plan-review provenance like 'complete (5 rounds)', or 'N/A' when absent."""
    status, rounds, _ = review_provenance(design_tmpdir)
    if not status:
        return "N/A"
    if rounds > 0:
        unit = "round" if rounds == 1 else "rounds"
        return f"{status} ({rounds} {unit})"
    return status


def _dynamic_archetypes_line(design_tmpdir: Path) -> str:
    status_file = design_tmpdir / "step2b-drafter-status.txt"
    if not status_file.is_file():
        return "static-only, drafter absent"
    text = status_file.read_text(encoding="utf-8", errors="replace")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if values.get("SCOUT_WRITTEN") != "true":
        return f"static-only, drafter {values.get('SCOUT_FAIL_REASON') or 'absent'}"
    try:
        data: object = json.loads((design_tmpdir / "scout-plan-manifest.json").read_text(encoding="utf-8"))
        archetypes = cast("dict[str, object]", data).get("archetypes") if isinstance(data, dict) else None
        count = len(cast("list[object]", archetypes)) if isinstance(archetypes, list) else 0
    except (OSError, json.JSONDecodeError):
        return "static-only, drafter filter_failed"
    return f"ok ({count})" if count else "static-only, drafter empty"


def _append_issue_detail(*, body: str, load_result: exec_issue_detail.LoadResult) -> str:
    detail_block = exec_issue_detail.build_issue_detail_section(load_result)
    if not detail_block:
        return body
    return body.rstrip("\n") + "\n\n" + detail_block.strip("\n") + "\n"


def _write_enriched_post_publish_summary(
    *, design_tmpdir: Path,
    out_file: Path,
    load_result: exec_issue_detail.LoadResult,
) -> int:
    try:
        body = out_file.read_text(encoding="utf-8")
        body = _append_issue_detail(body=body, load_result=load_result)
        try:
            detail = review_phase_detail.render_design_review_detail(design_tmpdir)
        except Exception:
            detail = ""
        body = review_phase_detail.append_review_phase_detail(body=body, detail=detail)
        _ = out_file.write_text(body, encoding="utf-8")
        sys.stdout.write(body)  # pyright: ignore[reportUnusedCallResult]
        if not body.endswith("\n"):
            sys.stdout.write("\n")  # pyright: ignore[reportUnusedCallResult]
        return 0
    except OSError as exc:
        msg = f"design render-final-summary: failed to write enriched summary: {exc}"
        print(msg, file=sys.stderr)
        ex_log = design_tmpdir / "execution-issues.md"
        try:
            with ex_log.open("a", encoding="utf-8") as fh:
                _ = fh.write(f"\n### Warnings\n- **design-summary**: {msg}\n")
        except OSError:
            pass
        try:
            reloaded = exec_issue_detail.load_issue_detail_groups(design_tmpdir, run_dir=None)
            if out_file.is_file():
                degraded_body = out_file.read_text(encoding="utf-8")
                detail_block = exec_issue_detail.build_issue_detail_section(reloaded)
                if detail_block:
                    degraded_body = _append_issue_detail(body=degraded_body, load_result=reloaded)
                else:
                    degraded_body = (
                        degraded_body.rstrip("\n")
                        + "\n\n**⚠ Enrich degraded — exec issue detail unavailable.**\n"
                    )
                _ = out_file.write_text(degraded_body, encoding="utf-8")
        except OSError:
            pass
        return 1


# Calls `python/cli.py render run-summary` with --claude-input-tokens for per-bucket cost detail.
def invoke_render(
    *, design_tmpdir: Path,
    outcome: str,
    mode_str: str,
    run_id: str,
    duration: str,
    issue: str,
    issue_url: str,
    oos_count: int,
    oos_urls: str,
    exec_issues: int,
    warnings: int,
    plan_review_line: str,
    dynamic_archetypes_line: str,
    run_logs_path: str,
    cost_args: list[str],
) -> int:
    out_file = design_tmpdir / "final-summary.md"
    manifest_candidates = (
        design_tmpdir / "manifest.json",
        design_tmpdir / "larch-logs" / "design" / run_id / "manifest.json",
    )
    manifest_path = next((str(p) for p in manifest_candidates if p.is_file()), str(manifest_candidates[0]))
    rr_args: list[str] = [
        "render", "run-summary",
        "--skill", "design",
        "--outcome", outcome,
        "--mode", mode_str,
        "--run-id", run_id,
        "--duration", duration,
        "--issue-number", issue or "0",
        "--issue-url", issue_url,
        "--pr-number", "0",
        "--pr-url", "N/A",
        "--plan-review-line", plan_review_line,
        "--dynamic-archetypes-line", dynamic_archetypes_line,
        "--code-review-line", "N/A",
        "--oos-count", str(oos_count),
        "--oos-urls", oos_urls,
        "--exec-issues", str(exec_issues),
        "--warnings", str(warnings),
        "--run-logs-path", run_logs_path,
        "--manifest-path", manifest_path,
        "--output-file", str(out_file),
        *cost_args,
    ]
    result = _run_cli(*rr_args)
    return result.returncode


def _run_design_failure_report_gate(
    *, design_tmpdir: Path,
    phase: str,
    outcome: str,
    repo: str,
    issue: str,
    run_id: str,
) -> None:
    if phase != "post":
        return
    from larch.design.design_lifecycle import capture_contract_stream_to_paths, failure_report_core  # noqa: PLC0415

    ex_log = design_tmpdir / "execution-issues.md"
    ex_before = ex_log.stat().st_size if ex_log.is_file() else 0
    out_file = design_tmpdir / "design-failure-report.stdout.log"
    err_file = design_tmpdir / "design-failure-report.stderr.log"
    cmd: list[str] = [
        "--design-tmpdir", str(design_tmpdir),
        "--outcome", outcome,
    ]
    if repo:
        cmd += ["--repo", repo]
    if issue:
        cmd += ["--issue", issue]
    if run_id:
        cmd += ["--run-id", run_id]

    gate_rc = capture_contract_stream_to_paths(failure_report_core, out_file, err_file, cmd)
    if gate_rc != 0:
        _run_cli(  # pyright: ignore[reportUnusedCallResult]
            "run-log", "append-failure",
            "--log", str(ex_log),
            "--site", "design failure report gate",
            "--tool", "design-failure-report.sh",
            "--exit-code", str(gate_rc),
            "--category", "Warnings",
            "--redact",
            "--output-file", str(err_file),
        )
    ex_after = ex_log.stat().st_size if ex_log.is_file() else 0
    if gate_rc != 0 or ex_after != ex_before:
        return


def _emit_report_gate_sidecars_file(design_tmpdir: Path) -> None:
    handoff = design_tmpdir / "design-report-gate-sidecars.md"
    sidecars: list[Path] = [
        design_tmpdir / "design-failure-chat-print.md",
        design_tmpdir / "design-failure-operator-action-chat.md",
    ]
    chunks: list[str] = [s.read_text(encoding="utf-8") for s in sidecars if s.is_file() and s.stat().st_size > 0]
    if not chunks:
        return
    body = "\n".join(chunks)
    if not body.endswith("\n"):
        body += "\n"
    _ = handoff.write_text(body, encoding="utf-8")
    print(f"REPORT_GATE_SIDECARS_FILE={handoff}")


def _refresh_final_reports(design_tmpdir: Path) -> None:
    _run_cli("token", "report", "--full", "--format", "json",  # pyright: ignore[reportUnusedCallResult]
             "--output", str(design_tmpdir / "token-report-final.json"))
    _run_cli("timing", "report", "--full", "--format", "json",  # pyright: ignore[reportUnusedCallResult]
             "--output", str(design_tmpdir / "timing-report-final.json"))


def render_final_summary_main(argv: Sequence[str]) -> int:
    argv = list(argv)
    outcome = ""
    mode_str = "N/A"
    repo = ""
    design_tmpdir_arg = ""
    issue_number_arg = ""
    session_id_arg = ""
    issue_number_set = False
    session_id_set = False
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
        elif a == "--design-tmpdir" and i + 1 < len(argv):
            design_tmpdir_arg = argv[i + 1]
            i += 2
        elif a == "--issue-number" and i + 1 < len(argv):
            issue_number_arg = argv[i + 1]
            issue_number_set = True
            i += 2
        elif a == "--session-id" and i + 1 < len(argv):
            session_id_arg = argv[i + 1]
            session_id_set = True
            i += 2
        elif a == "--pre-publish-only":
            phase = "pre"
            i += 1
        elif a == "--post-publish-only":
            phase = "post"
            i += 1
        else:
            i += 1

    design_tmpdir_str = design_tmpdir_arg or os.environ.get("DESIGN_TMPDIR", "")
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

    run_id = (session_id_arg if session_id_set else os.environ.get("SESSION_ID", "")) or "unknown"
    issue = issue_number_arg if issue_number_set else (os.environ.get("ISSUE_NUMBER", "") or "")

    issue_url = "N/A"
    if issue and issue != "0" and repo and "/" in repo:
        issue_url = f"https://github.com/{repo}/issues/{issue}"

    _refresh_final_reports(design_tmpdir)
    buckets = _read_token_report(design_tmpdir)
    cost_args = _build_cost_args(buckets)
    duration = _duration(design_tmpdir)
    oos_count, oos_urls = _oos_info(design_tmpdir)
    run_logs_path = f"larch-logs/design/{run_id}/" if run_id and run_id != "unknown" else "N/A"
    out_file = design_tmpdir / "final-summary.md"
    _run_design_failure_report_gate(design_tmpdir=design_tmpdir, phase=phase, outcome=outcome, repo=repo, issue=issue, run_id=run_id)
    load_result = exec_issue_detail.load_issue_detail_groups(design_tmpdir, run_dir=None)
    exec_issues, warnings = exec_issue_detail.count_load_result(load_result)
    plan_review_line = _plan_review_line(design_tmpdir)
    dynamic_archetypes_line = _dynamic_archetypes_line(design_tmpdir)

    rc = invoke_render(
        design_tmpdir=design_tmpdir, outcome=outcome, mode_str=mode_str, run_id=run_id, duration=duration, issue=issue, issue_url=issue_url,
        oos_count=oos_count, oos_urls=oos_urls, exec_issues=exec_issues, warnings=warnings, plan_review_line=plan_review_line, dynamic_archetypes_line=dynamic_archetypes_line, run_logs_path=run_logs_path, cost_args=cost_args,
    )

    if rc != 0 or not out_file.is_file() or out_file.stat().st_size == 0:
        with out_file.open("w", encoding="utf-8") as fh:
            fh.write(f"## /design run {run_id} — {outcome}\n\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write("**⚠ Degraded fallback — full renderer failed.**\n\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Outcome**: {outcome}\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Duration**: {duration}\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write("- **Cost**: N/A\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Exec issues**: {exec_issues}\n")  # pyright: ignore[reportUnusedCallResult]
            fh.write(f"- **Warnings**: {warnings}\n")  # pyright: ignore[reportUnusedCallResult]

    if phase == "pre":
        return 0

    exit_rc = _write_enriched_post_publish_summary(design_tmpdir=design_tmpdir, out_file=out_file, load_result=load_result)
    write_ok = exit_rc == 0

    if issue and issue != "0" and write_ok and out_file.is_file() and out_file.stat().st_size > 0:
        marker = f"<!-- larch:final-summary v1 runid={run_id} -->"
        ups_args: list[str] = [
            "tracking-issue", "upsert-summary",
            "--issue", issue,
            "--marker", marker,
            "--content-file", str(out_file),
        ]
        if repo:
            ups_args += ["--repo", repo]
        _run_cli(*ups_args)  # pyright: ignore[reportUnusedCallResult]
    _emit_report_gate_sidecars_file(design_tmpdir)

    return exit_rc
