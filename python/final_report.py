"""Final report rendering and Step 18b helpers for /implement."""

# pyright: reportUnusedCallResult=false, reportUnusedFunction=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import architectural_guidelines
import closeout
import config
import exec_issue_detail
import larch_io
import pr_body
import repo_roots
import report_tokens_cost
import review_phase_detail
import stall_recovery
import tokens

_OOS_FILED_URL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s]+/issues/\d+)", re.MULTILINE)


_emit_kv = pr_body._emit_kv  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001


def _read_kv(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path, key, default=default, first_match=True, cr_strip="strip", on_error_default=False)


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _object_map(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, dict) else {}


def _json_archetype_count(path: Path) -> int | None:
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    archetypes = cast("Mapping[str, object]", data).get("archetypes")
    return len(cast("list[object]", archetypes)) if isinstance(archetypes, list) else None


def _first_round_scout_status(implement_tmpdir: Path) -> str:
    for status_file in sorted(implement_tmpdir.glob("round-*/scout-round*-status.env")):
        status = _read_kv(path=status_file, key="SCOUT_STATUS")
        if status:
            return status
    return ""


def _first_round_scout_manifest(implement_tmpdir: Path) -> Path | None:
    for manifest in sorted(implement_tmpdir.glob("round-*/scout-round*-manifest.json")):
        if manifest.is_file():
            return manifest
    return None


def _self_review_requested(implement_tmpdir: Path) -> bool:
    return _read_kv(path=implement_tmpdir / "run-flags.sh", key="SELF_REVIEW_REQUESTED") == "true"


def _dynamic_archetypes_line(implement_tmpdir: Path) -> str:
    round_status = _first_round_scout_status(implement_tmpdir)
    if round_status.startswith("skipped-"):
        return round_status
    if round_status in {"producer-missing", "producer-invalid"}:
        return "static-only, producer missing-or-invalid"
    if round_status == "pre-scouted-empty":
        return "static-only, pre-scouted-empty"
    if round_status == "pre-scouted":
        round_manifest = _first_round_scout_manifest(implement_tmpdir)
        count = _json_archetype_count(round_manifest) if round_manifest is not None else None
        if count is not None:
            return f"ok ({count})"
        return "unknown"
    if not round_status:
        if _self_review_requested(implement_tmpdir):
            return "N/A"
        status_file = implement_tmpdir / "step2-scout-coder-status.env"
        if not status_file.is_file():
            return "unknown"
        coder_status = _read_kv(path=status_file, key="SCOUT_CODER_STATUS")
        if not coder_status:
            return "unknown"
        if coder_status != "ok":
            return "static-only, producer missing-or-invalid"
        manifest = implement_tmpdir / "scout-coder-manifest.json"
        marker = implement_tmpdir / "step2-external-scout-eligible.txt"
        count = _json_archetype_count(manifest)
        if count is None or not marker.is_file():
            return "static-only, producer missing-or-invalid"
        if count == 0:
            return "static-only, producer empty"
        return f"ok ({count})"
    return "unknown"


def _current_head_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _session_env_value(*, session: Path, key: str) -> str:
    if not session.is_file() or session.is_symlink():
        return ""
    for line in session.read_text(encoding="utf-8", errors="replace").splitlines():
        field, sep, value = line.partition("=")
        if sep and field == key:
            return value.strip().strip("'\"")
    return ""


def _keepalive_clone_path(implement_tmpdir: Path) -> str:
    keepalive = implement_tmpdir / ".larch-keepalive"
    return _session_env_value(session=keepalive, key="CLONE_PATH")


def _implement_repo_root(implement_tmpdir: Path) -> Path | None:
    session = implement_tmpdir / "session-env.sh"
    for key in ("CLAUDE_PROJECT_DIR", "REPO_CWD"):
        cleaned = _session_env_value(session=session, key=key)
        if cleaned:
            root = repo_roots.consumer_repo_root(Path(cleaned))
            if root is not None:
                return root
            try:
                return Path(cleaned).resolve()
            except OSError:
                pass
    clone = _keepalive_clone_path(implement_tmpdir)
    if clone:
        root = repo_roots.consumer_repo_root(Path(clone))
        if root is not None:
            return root
    return repo_roots.consumer_repo_root()


def _architectural_guidelines_section(implement_tmpdir: Path) -> str:
    head_sha = _current_head_sha()
    if not head_sha or not architectural_guidelines.note_consumable(implement_tmpdir, head_sha):
        return ""
    meta = architectural_guidelines.durable_note_metadata(implement_tmpdir)
    note_base_ref = meta.get("BASE_REF", "")
    if architectural_guidelines.note_fingerprint_stale(
        implement_tmpdir,
        base_ref=note_base_ref,
        repo_root=_implement_repo_root(implement_tmpdir),
    ):
        architectural_guidelines.invalidate_implement_note(implement_tmpdir)
        return ""
    try:
        note = architectural_guidelines.durable_note_path(implement_tmpdir).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""
    redacted = pr_body.redact_pr_body(note)
    if not redacted.strip():
        return ""
    return "## Architectural guidelines\n\n" + redacted.strip() + "\n"


def _token_argv_from_report(data: Mapping[str, object]) -> list[str]:
    argv: list[str] = []
    vendor_buckets = (
        ("claude", "BUCKETS_claude", "claude"),
        ("codex", "BUCKETS_codex", "codex"),
        ("cursor", "BUCKETS_cursor", "cursor"),
        ("claude_sub", "BUCKETS_claude_sub", "claude-sub"),
    )
    for vendor, bucket_key, flag_prefix in vendor_buckets:
        bucket = _object_map(data.get(bucket_key))
        if bucket and any(_safe_int(value) for value in bucket.values()):
            if vendor in {"claude", "claude_sub"}:
                cache_create_5m = _safe_int(bucket.get("cache_create_5m"))
                if cache_create_5m == 0:
                    cache_create_5m = _safe_int(bucket.get("cache_create"))
                argv.extend([
                    f"--{flag_prefix}-input-tokens", str(_safe_int(bucket.get("input"))),
                    f"--{flag_prefix}-cache-read-tokens", str(_safe_int(bucket.get("cache_read"))),
                    f"--{flag_prefix}-cache-write-5m-tokens", str(cache_create_5m),
                    f"--{flag_prefix}-cache-write-1h-tokens", str(_safe_int(bucket.get("cache_create_1h"))),
                    f"--{flag_prefix}-output-tokens", str(_safe_int(bucket.get("output"))),
                ])
            elif vendor == "codex":
                argv.extend([
                    "--codex-input-tokens", str(_safe_int(bucket.get("input"))),
                    "--codex-cached-input-tokens", str(_safe_int(bucket.get("cached_input"))),
                    "--codex-output-tokens", str(_safe_int(bucket.get("output"))),
                ])
            else:
                argv.extend([
                    "--cursor-input-tokens", str(_safe_int(bucket.get("input"))),
                    "--cursor-cache-read-tokens", str(_safe_int(bucket.get("cache_read"))),
                    "--cursor-output-tokens", str(_safe_int(bucket.get("output"))),
                ])
            continue
        totals = _object_map(data.get(vendor))
        nested_totals = _object_map(totals.get("totals"))
        if nested_totals:
            total = _safe_int(nested_totals.get("total"))
            if total:
                argv.extend([f"--{flag_prefix}-tokens", str(total)])
    return argv


def _final_report_token_fields(*, implement_tmpdir: Path, run_id: str) -> dict[str, object]:
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    token_json: Path | None = None
    for cand in (run_dir / "token-report.json", implement_tmpdir / "token-report-rendered.json"):
        if cand.is_file() and not cand.is_symlink():
            token_json = cand
            break
    if token_json is None:
        tr_json = implement_tmpdir / "token-report-truth.json"
        env = {**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir)}
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "cli.py"),
                "token",
                "report",
                "--full",
                "--format",
                "json",
                "--output",
                str(tr_json),
            ],
            env=env,
            capture_output=True,
            check=False,
        )
        if completed.returncode == 0 and tr_json.is_file():
            token_json = tr_json
    if token_json is None:
        return {"cost_unavailable": True}
    try:
        data_obj = json.loads(token_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cost_unavailable": True}
    if not isinstance(data_obj, dict):
        return {"cost_unavailable": True}
    data = cast("dict[str, object]", data_obj)
    claude = _object_map(data.get("claude"))
    if not _object_map(claude.get("totals")):
        return {"cost_unavailable": True}
    token_argv = _token_argv_from_report(data)
    if not token_argv:
        return {"cost_unavailable": True}
    try:
        cost_kv = report_tokens_cost.token_cost_from_args(token_argv)
    except Exception:
        return {"cost_unavailable": True}

    total_cost = larch_io.kv_value(cost_kv, "TOTAL_COST", default="N/A")
    if total_cost == "N/A":
        return {"cost_unavailable": True}
    return {
        "cost_unavailable": False,
        "total_cost": total_cost,
        "claude_cost": larch_io.kv_value(cost_kv, "CLAUDE_COST", default="N/A"),
        "codex_cost": larch_io.kv_value(cost_kv, "CODEX_COST", default="N/A"),
        "cursor_cost": larch_io.kv_value(cost_kv, "CURSOR_COST", default="N/A"),
        "claude_sub_cost": larch_io.kv_value(cost_kv, "CLAUDE_SUB_COST", default="N/A"),
        "total_tokens": int(larch_io.kv_value(cost_kv, "TOTAL_TOKENS", default="N/A") or 0),
    }


def _final_report_duration(*, run_dir: Path, ship: Path) -> str:
    timing = run_dir / "timing-report.json"
    if timing.is_file():
        try:
            data_obj = json.loads(timing.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data_obj = None
        if isinstance(data_obj, dict):
            data = cast("dict[str, object]", data_obj)
            total_hms = data.get("total_hms")
            if total_hms:
                return str(total_hms)
            total_seconds = data.get("total_seconds")
            if total_seconds is not None:
                return f"{total_seconds}s"
    return _read_kv(path=ship, key="DURATION", default="N/A")


def _refresh_issue_counts(*, implement_tmpdir: Path, run_id: str) -> tuple[int, int]:
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    result = exec_issue_detail.load_issue_detail_groups(implement_tmpdir, run_dir=run_dir)
    return exec_issue_detail.count_load_result(result)


def _issue_load_result_for_run(
    *, implement_tmpdir: Path,
    run_id: str,
) -> tuple[Path, exec_issue_detail.LoadResult, int, int]:
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    load_result = exec_issue_detail.load_issue_detail_groups(implement_tmpdir, run_dir=run_dir)
    exec_count, warn_count = exec_issue_detail.count_load_result(load_result)
    return run_dir, load_result, exec_count, warn_count


def _merge_line_count_state(*, ship: Path, pr_number: str, lines: Mapping[str, object]) -> None:
    if not ship.is_file() or ship.is_symlink() or not os.access(ship, os.W_OK):
        return
    preserved: list[str] = []
    for line in ship.read_text(encoding="utf-8", errors="replace").splitlines():
        key = line.split("=", 1)[0] if "=" in line else ""
        if key and key not in {"LINES_PR_NUMBER", "LINES_STATUS", "CODE_ADDED", "CODE_DELETED", "LOGS_ADDED", "LOGS_DELETED"}:
            preserved.append(line)
    tmp = ship.with_suffix(ship.suffix + ".tmp")
    tmp.write_text(
        "".join(f"{line}\n" for line in preserved)
        + f"LINES_PR_NUMBER={pr_number or '0'}\n"
        + "".join(f"{key}={lines[key]}\n" for key in ("LINES_STATUS", "CODE_ADDED", "CODE_DELETED", "LOGS_ADDED", "LOGS_DELETED") if key in lines),
        encoding="utf-8",
    )
    tmp.replace(ship)


def _derive_pr_line_counts(*, repo: str, repo_unavailable: bool, pr_number: str, ship: Path) -> tuple[str, str, str, str]:
    if repo_unavailable or not pr_number or pr_number == "0":
        return "", "", "", ""
    cached_pr = _read_kv(path=ship, key="LINES_PR_NUMBER")
    if cached_pr == pr_number and _read_kv(path=ship, key="LINES_STATUS") == "ok":
        ca, cd, la, ld = (_read_kv(path=ship, key=key) for key in ("CODE_ADDED", "CODE_DELETED", "LOGS_ADDED", "LOGS_DELETED"))
        if all(value.isdigit() for value in (ca, cd, la, ld)):
            return ca, cd, la, ld
    result = tokens.compute_pr_line_counts(pr_number=int(pr_number), repo=repo or None)
    if result.get("LINES_STATUS") == "ok":
        with contextlib.suppress(OSError):
            _merge_line_count_state(ship=ship, pr_number=pr_number, lines=result)
        return (
            str(result.get("CODE_ADDED", "")),
            str(result.get("CODE_DELETED", "")),
            str(result.get("LOGS_ADDED", "")),
            str(result.get("LOGS_DELETED", "")),
        )
    return "", "", "", ""


def _derive_review_line(*, run_dir: Path, filename: str) -> str:
    tally = run_dir / filename
    if not tally.is_file():
        return "N/A"
    try:
        data_obj = json.loads(tally.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "N/A"
    if not isinstance(data_obj, dict):
        return "N/A"
    data = cast("dict[str, object]", data_obj)
    try:
        accepted = int(str(data.get("accepted_count") or 0))
        rejected = int(str(data.get("rejected_count") or 0))
    except (TypeError, ValueError):
        return "N/A"
    if accepted < 0 or rejected < 0:
        return "N/A"
    total = accepted + rejected
    if total > 0:
        return f"{accepted}/{total} accepted"
    # Zero-count tally: distinguish "review ran clean" from "no review ran", but
    # only for code-review tallies. plan-review (or any non-code-review phase)
    # zero totals stay N/A.
    is_code_review = filename == "code-review-tally.json" or data.get("phase") == "code-review"
    if not is_code_review:
        return "N/A"
    if data.get("mode") == "self-review":
        return "self-review: 0 findings"
    return "0 findings"


def _derive_oos_fields(run_dir: Path) -> tuple[str, str]:
    ndjson = run_dir / "oos-issues.ndjson"
    if not ndjson.is_file():
        return "0", ""
    text = ndjson.read_text(encoding="utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    urls: list[str] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        body = cast("Mapping[str, object]", record).get("body")
        if isinstance(body, str):
            urls.extend(_OOS_FILED_URL_LINE_RE.findall(body))
    return str(len(lines)), ",".join(sorted(set(urls)))


def _derive_final_report_fields(
    implement_tmpdir: Path,
    *,
    run_id: str,
    repo: str,
    repo_unavailable: bool,
    pr_number: str,
    ship: Path,
) -> dict[str, str]:
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    code_added, code_deleted, logs_added, logs_deleted = _derive_pr_line_counts(
        repo=repo,
        repo_unavailable=repo_unavailable,
        pr_number=pr_number,
        ship=ship,
    )
    plan_line = _read_kv(path=ship, key="PLAN_REVIEW_LINE") or _derive_review_line(run_dir=run_dir, filename="plan-review-tally.json")
    code_line = _read_kv(path=ship, key="CODE_REVIEW_LINE") or _derive_review_line(run_dir=run_dir, filename="code-review-tally.json")
    oos_count = _read_kv(path=ship, key="OOS_COUNT") or _derive_oos_fields(run_dir)[0]
    oos_urls = _read_kv(path=ship, key="OOS_URLS") or _derive_oos_fields(run_dir)[1]
    return {
        "plan_review_line": plan_line or "N/A",
        "code_review_line": code_line or "N/A",
        "code_added": code_added or _read_kv(path=ship, key="CODE_ADDED"),
        "code_deleted": code_deleted or _read_kv(path=ship, key="CODE_DELETED"),
        "logs_added": logs_added or _read_kv(path=ship, key="LOGS_ADDED"),
        "logs_deleted": logs_deleted or _read_kv(path=ship, key="LOGS_DELETED"),
        "oos_count": oos_count or "0",
        "oos_urls": oos_urls,
    }


def _append_issue_detail(*, body: str, load_result: exec_issue_detail.LoadResult) -> str:
    detail_block = exec_issue_detail.build_issue_detail_section(load_result)
    if not detail_block:
        return body
    return body.rstrip("\n") + "\n\n" + detail_block.strip("\n") + "\n"


def _reconcile_manifest_for_terminal_report(
    implement_tmpdir: Path,
    *,
    run_id: str,
    outcome: str,
) -> tuple[int, str]:
    if not run_id or run_id == "unknown":
        return 0, ""
    run_dir = implement_tmpdir / "larch-logs" / "implement" / run_id
    manifest = run_dir / "manifest.json"
    if not manifest.is_file():
        return 0, ""
    fields: list[str] = []
    if not (run_dir / "run-statistics.md").is_file():
        fields.append("steps_ran.step9a1=false")
    if (run_dir / "final-summary.md").is_file() or (run_dir / "version-bump-reasoning.md").is_file():
        fields.append("steps_ran.step8=true")
    else:
        fields.append("steps_ran.step8=false")
    if not any(
        (run_dir / name).is_file()
        for name in (
            "token-report.json",
            "timing-report.json",
            "execution-issues.ndjson",
            "session-transcript.jsonl",
        )
    ):
        fields.append("steps_ran.step7a=false")
    if outcome in {"pr-created", "pr-created-draft"}:
        fields.append(f"status={config.MANIFEST_STATUS_IN_PROGRESS}")
    pr_number = _read_kv(path=implement_tmpdir / "ship-pr-state.sh", key="PR_NUMBER") or _read_kv(
        path=implement_tmpdir / "finalize-state.sh",
        key="PR_NUMBER",
    )
    if pr_number.strip().isdigit() and int(pr_number.strip()) > 0:
        fields.append(f"pr_number={pr_number.strip()}")
    if not fields:
        return 0, ""
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "cli.py"),
        "run-log",
        "manifest",
        "--log-root",
        str(implement_tmpdir / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        run_id,
    ]
    for field in fields:
        cmd.extend(["--field", field])
    completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "manifest update failed").strip()
        return completed.returncode or 1, f"run-log manifest reconcile failed: {err[:300]}"
    return 0, ""


def write_final_report(
    implement_tmpdir: Path,
    *,
    comment_only: bool = False,
    print_stdout: bool = False,
    skip_tracking_upsert: bool = False,
) -> tuple[int, str, str]:
    parent = implement_tmpdir / "parent-issue.md"
    session = implement_tmpdir / "session-env.sh"
    ship = implement_tmpdir / "ship-pr-state.sh"
    final = implement_tmpdir / "finalize-state.sh"
    run_flags = implement_tmpdir / "run-flags.sh"
    issue = _read_kv(path=parent, key="ISSUE_NUMBER", default="0") or "0"
    run_id = _read_kv(path=parent, key="RUN_ID") or ((implement_tmpdir / "session-id").read_text(encoding="utf-8").strip() if (implement_tmpdir / "session-id").is_file() else "unknown")
    if "/" in run_id or ".." in run_id:
        return 1, "", "invalid RUN_ID (path-traversal characters rejected)"
    repo = _read_kv(path=session, key="REPO")
    pr_number = _read_kv(path=ship, key="PR_NUMBER") or _read_kv(path=final, key="PR_NUMBER")
    pr_url = _read_kv(path=ship, key="PR_URL", default="N/A") or _read_kv(path=final, key="PR_URL", default="N/A")
    issue_url = f"https://github.com/{repo}/issues/{issue}" if repo and issue and issue != "0" else ""
    run_dir, load_result, exec_count, warn_count = _issue_load_result_for_run(implement_tmpdir=implement_tmpdir, run_id=run_id)
    derived = _derive_final_report_fields(
        implement_tmpdir,
        run_id=run_id or "unknown",
        repo=repo,
        repo_unavailable=_read_kv(path=session, key="REPO_UNAVAILABLE", default="false") == "true",
        pr_number=pr_number,
        ship=ship,
    )
    cost_fields = _final_report_token_fields(implement_tmpdir=implement_tmpdir, run_id=run_id)
    outcome_values = stall_recovery.normalized_outcome_values(
        argparse.Namespace(implement_tmpdir=str(implement_tmpdir), in_memory_stall_tracking="")
    )
    outcome = outcome_values.get("IMPLEMENT_NORMALIZED_OUTCOME", "bailed")
    body = pr_body.render_run_summary(
        skill="implement",
        outcome=outcome,
        run_id=run_id or "unknown",
        mode=_read_kv(path=session, key="MODE", default="N/A"),
        workflow_path=_read_kv(path=session, key="WORKFLOW_PATH"),
        duration=_final_report_duration(run_dir=run_dir, ship=ship),
        issue_number=issue,
        issue_url=issue_url,
        pr_number=pr_number,
        pr_url=pr_url,
        plan_review_line=derived["plan_review_line"],
        dynamic_archetypes_line=_dynamic_archetypes_line(implement_tmpdir),
        code_review_line=derived["code_review_line"],
        code_added=derived["code_added"],
        code_deleted=derived["code_deleted"],
        logs_added=derived["logs_added"],
        logs_deleted=derived["logs_deleted"],
        oos_count=derived["oos_count"],
        oos_urls=derived["oos_urls"],
        exec_issues=exec_count,
        warnings=warn_count,
        run_logs_path=f"larch-logs/implement/{run_id}/" if run_id else "N/A",
        force_requested=_read_kv(path=run_flags, key="FORCE_REQUESTED", default="false"),
        merge_downgraded=outcome_values.get("IMPLEMENT_MERGE_DOWNGRADED", "false"),
        manifest_path=str(run_dir / "manifest.json"),
        **cost_fields,
    )
    body = _append_issue_detail(body=body, load_result=load_result)
    try:
        detail = review_phase_detail.render_implement_review_detail(implement_tmpdir=implement_tmpdir, run_id=run_id or "unknown")
    except Exception:
        detail = ""
    body = review_phase_detail.append_review_phase_detail(body=body, detail=detail)
    try:
        guidelines_section = _architectural_guidelines_section(implement_tmpdir)
    except Exception as exc:
        if print_stdout:
            sys.stdout.write(body)
        return 1, "", f"architectural-guidelines section failed: {exc}"
    if guidelines_section:
        body = body.rstrip("\n") + "\n\n" + guidelines_section
    summary = implement_tmpdir / "summary-final.md"
    try:
        summary.write_text(body, encoding="utf-8")
    except OSError as exc:
        if print_stdout:
            sys.stdout.write(body)
        return 1, "", f"summary-final write failed: {exc}"
    if not comment_only:
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "final-summary.md").write_text(body, encoding="utf-8")
        except OSError as exc:
            if print_stdout:
                sys.stdout.write(body)
            return 1, "", f"final-summary write failed: {exc}"
        if not skip_tracking_upsert:
            reconcile_rc, reconcile_err = _reconcile_manifest_for_terminal_report(
                implement_tmpdir,
                run_id=run_id or "unknown",
                outcome=outcome,
            )
            if reconcile_rc != 0:
                if print_stdout:
                    sys.stdout.write(body)
                return reconcile_rc, "", reconcile_err
        if skip_tracking_upsert:
            if print_stdout:
                sys.stdout.write(body)
            return 0, "", ""
    comment_url = ""
    repo_unav = _read_kv(path=session, key="REPO_UNAVAILABLE", default="false") == "true"
    if issue and issue != "0" and not repo_unav:
        marker = f"<!-- larch:final-summary v1 runid={run_id} -->"
        cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent / "cli.py"),
            "tracking-issue",
            "upsert-summary",
            "--issue",
            issue,
            "--marker",
            marker,
            "--content-file",
            str(summary),
        ]
        if repo:
            cmd += ["--repo", repo]
        completed = subprocess.run(cmd, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            err = (completed.stderr or completed.stdout or "tracking-issue upsert failed").strip()
            if print_stdout:
                sys.stdout.write(body)
            return 1, "", err[:500]
        m = re.search(r"^COMMENT_URL=(.*)$", completed.stdout, re.MULTILINE)
        comment_url = m.group(1) if m else ""
    if print_stdout:
        sys.stdout.write(body)
    return 0, comment_url, ""


def write_final_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py final-report write")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--comment-only", action="store_true")
    parser.add_argument("--print-stdout", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        _emit_kv(key="COMMENT_URL", value="")
        _emit_kv(key="STATUS", value="failed")
        _emit_kv(key="ERROR", value="usage")
        return 2
    rc, url, err = write_final_report(Path(args.implement_tmpdir), comment_only=args.comment_only, print_stdout=args.print_stdout)
    _emit_kv(key="COMMENT_URL", value=url)
    _emit_kv(key="STATUS", value="ok" if rc == 0 else "failed")
    if err:
        _emit_kv(key="ERROR", value=err)
    return rc


def step18b_final_report(implement_tmpdir: Path) -> tuple[bool, int, bool, str]:
    step17_present = (implement_tmpdir / ".step17-emitted").exists()
    if not (implement_tmpdir / ".step16-16a-done").exists():
        closeout.step_16_16a(["--implement-tmpdir", str(implement_tmpdir)])
    emit_body = not step17_present
    snapshot_ok = "absent"
    pre = implement_tmpdir / ".step18-prebody"
    summary = implement_tmpdir / "summary-final.md"
    if summary.exists():
        try:
            pre.write_bytes(summary.read_bytes())
            snapshot_ok = "true"
        except OSError:
            snapshot_ok = "false"
            with contextlib.suppress(OSError):
                pre.unlink()
    wfr_rc, _url, _err = write_final_report(implement_tmpdir)
    summary_present = summary.is_file() and summary.stat().st_size > 0
    snapshot_changed = pre.is_file() and pre.read_bytes() != summary.read_bytes()
    snapshot_unavailable = snapshot_ok in {"absent", "false"}
    should_emit_updated_body = (
        wfr_rc == 0
        and summary_present
        and not emit_body
        and (snapshot_unavailable or snapshot_changed)
    )
    if should_emit_updated_body:
        emit_body = True
    return (emit_body and wfr_rc == 0 and summary_present), wfr_rc, step17_present, snapshot_ok


def step18b_final_report_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py final-report step18b")
    parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    emit_body, wfr_rc, present, snapshot = step18b_final_report(Path(args.implement_tmpdir))
    _emit_kv(key="EMIT_BODY", value=str(emit_body).lower())
    _emit_kv(key="WFR_RC", value=wfr_rc)
    _emit_kv(key="STEP17_EMITTED_PRESENT", value=str(present).lower())
    _emit_kv(key="SNAPSHOT_OK", value=snapshot)
    return wfr_rc
