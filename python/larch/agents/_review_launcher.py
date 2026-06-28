# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false
"""Review launcher for codex and cursor external reviewers."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from larch.state import dirty_tree
from larch.review import findings_ledger
from larch.git import git
from larch.core import logging_util
from larch.core import proc
from larch.core import redact

from larch.agents._types import (
    _CTRL_RE,
    _CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR,
    _CURSOR_DEGRADED_RESULT_BYTES_CEILING,
    _CURSOR_NO_WORK_INPUT_TOKEN_FLOOR,
    _PY_CLI,
    CURSOR_PREREAD_FAIL_RC,
    CURSOR_PREREAD_FAIL_MSG,
    LauncherPaths,
    RunExternalAgentResult,
    _err,
    _emit_kv,
    _write,
    _append,
    _is_positive_int,
    _validate_meta_path,
)
from larch.agents._launch_failure import (
    resolve_model_args,
    classify_launch_failure,
    is_quota_failure,
    is_transient_infra_failure,
)
from larch.agents._failure_diag import (
    _compose_failure_diag,
    resolve_failure_diagnostic_source,
    _review_failure_auth_paths,
    _num,
)
from larch.agents._run_external import (
    external_auth_verdict,
    external_startup_lock_acquire,
    external_startup_lock_release_after,
    _codex_auth_args,
    _trust_config_arg,
    _prepare_codex_home,
    _resolve_review_codex_workdir,
    _temporary_env,
    _record_launch_timing,
    _record_usage_from_events,
    _append_vendor_failure_diagnostics,
    _resolve_execution_issues_log,
    run_external_agent,
    _record_cursor_usage_from_output,
    _auth_retry_limit,
    _mirror_codex_quota_from_events,
    _is_unclassified_empty_startup_failure,
    _under,
    _promote_inner_done,
    _CODEX_REVIEW_STRICT_PREAMBLE,
    _CURSOR_REVIEW_STRICT_PREAMBLE,
    _REVIEW_MAX_TRANSIENT_RETRIES,
    _COLLECTOR_NS_STRONG_HEADER,
)
from larch.agents._auth import (
    cursor_auth_preflight,
    cursor_preread_service_token,
    cursor_auth_export_env,
    _probe_tmpdir,
)

def _review_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py agent launch-review")
    parser.add_argument("--tool", required=True, choices=("codex", "cursor"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", required=True)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    prompt_group.add_argument("--agent-file")
    parser.add_argument("--mode", default="")
    parser.add_argument("--description-text", default="")
    parser.add_argument("--scope-files", default="")
    parser.add_argument("--competition-notice", action="store_true")
    parser.add_argument("--competition-notice-file", default="")
    parser.add_argument("--diff-file", default="")
    parser.add_argument("--commit-count", default="")
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--feature-file", default="")
    parser.add_argument("--session-env-path", default="")
    parser.add_argument("--timing-task-kind", default=os.environ.get("LARCH_TIMING_TASK_KIND", ""))
    parser.add_argument("--token-budget-cap", default="")
    parser.add_argument("--risk", default="")
    parser.add_argument("--stderr-sink", default="")
    parser.add_argument("--site", default="review Step 2")
    parser.add_argument("--model-role", choices=("default", "review", "vote", "fix"), default="default")
    return parser


def _review_coerce_risk(risk: str) -> str:
    return "low" if risk == "low" else "high"


def _review_validate_args(args: argparse.Namespace) -> int:
    if not _validate_meta_path(label="--output", value=args.output):
        return 1
    if args.stderr_sink and not _validate_meta_path(label="--stderr-sink", value=args.stderr_sink):
        return 1
    if args.risk and _CTRL_RE.search(args.risk):
        _err("agent launch-review: --risk must not contain control characters")
        return 2
    if args.timing_task_kind and _CTRL_RE.search(args.timing_task_kind):
        _err("agent launch-review: --timing-task-kind must not contain control characters")
        return 2
    if not _is_positive_int(args.timeout):
        if args.tool == "codex":
            _err(f"agent launch-review: --timeout must be a positive integer (seconds), got '{args.timeout}'")
        elif args.timeout.isdigit():
            _err("agent launch-review: --timeout must be >= 1")
        else:
            _err("agent launch-review: --timeout must be a positive integer")
        return 2
    if args.timing_task_kind and (not args.timing_task_kind.strip() or args.timing_task_kind.startswith("--")):
        _err("agent launch-review: --timing-task-kind requires a non-empty, non-flag-like value")
        return 2
    if args.token_budget_cap and not _is_positive_int(args.token_budget_cap):
        _err("agent launch-review: --token-budget-cap requires a positive integer")
        return 2
    if not args.site.strip() or args.site.startswith("--"):
        _err("agent launch-review: --site requires a non-empty, non-flag-like value")
        return 2
    if _CTRL_RE.search(args.site):
        _err("agent launch-review: --site must not contain control characters")
        return 2
    return 0


def _review_session_env_path(args: argparse.Namespace) -> str:
    return getattr(args, "session_env_path", "") or os.environ.get("SESSION_ENV_PATH", "")


def _review_specialist_render_args(args: argparse.Namespace, *, sentinel: dict[str, str] | None = None) -> list[str]:
    if sentinel is not None:
        render_args = ["--agent-file", sentinel.get("AGENT_FILE", ""), "--mode", sentinel.get("MODE", "")]
        mapping = (
            ("SCOPE_FILES", "--scope-files"),
            ("COMPETITION_NOTICE_FILE", "--competition-notice-file"),
            ("DIFF_FILE", "--diff-file"),
            ("COMMIT_COUNT", "--commit-count"),
            ("PLAN_FILE", "--plan-file"),
            ("FEATURE_FILE", "--feature-file"),
            ("FINDINGS_LEDGER_FILE", "--findings-ledger-file"),
            ("SESSION_ENV_PATH", "--session-env-path"),
        )
        for key, flag in mapping:
            if sentinel.get(key):
                render_args.extend([flag, sentinel[key]])
        if sentinel.get("COMPETITION_NOTICE") == "true":
            render_args.append("--competition-notice")
        return render_args
    render_args = ["--agent-file", args.agent_file, "--mode", args.mode]
    for attr, flag in (
        ("description_text", "--description-text"),
        ("scope_files", "--scope-files"),
        ("competition_notice_file", "--competition-notice-file"),
        ("diff_file", "--diff-file"),
        ("commit_count", "--commit-count"),
        ("plan_file", "--plan-file"),
        ("feature_file", "--feature-file"),
    ):
        value = getattr(args, attr)
        if value:
            render_args.extend([flag, value])
        if args.competition_notice:
            render_args.append("--competition-notice")
    session_env_path = _review_session_env_path(args)
    if getattr(args, "output", ""):
        ledger_file = findings_ledger.ledger_path(
            findings_ledger.ledger_root(Path(args.output).parent, session_env_path=session_env_path)
        )
        render_args.extend(["--findings-ledger-file", str(ledger_file)])
    if session_env_path:
        render_args.extend(["--session-env-path", session_env_path])
    return render_args


def _review_render_specialist_prompt(args: argparse.Namespace) -> tuple[int, str]:
    result = proc.run(
        [sys.executable, str(_PY_CLI), "render", "specialist", *_review_specialist_render_args(args)],
        check=False,
    )
    if result.returncode != 0:
        _err(result.stderr or result.stdout or "agent launch-review: render specialist failed")
        return result.returncode if result.returncode != 0 else 1, ""
    return 0, result.stdout


def _review_read_prompt_file(path: str) -> tuple[int, str]:
    try:
        return 0, Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        _err(f"agent launch-review: failed to read --prompt-file {path}")
        return 1, ""


def _review_codex_compact_sentinel_offset(text: str) -> int | None:
    if text.startswith("LARCH_PROMPT_SENTINEL=1\n"):
        return 0
    header = _COLLECTOR_NS_STRONG_HEADER
    if text.startswith(header) and text[len(header) :].startswith("LARCH_PROMPT_SENTINEL=1\n"):
        return len(header)
    return None


def _review_read_codex_prompt_sentinel(path: str) -> tuple[int, str] | None:
    prompt_path = Path(path)
    try:
        text = prompt_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    sentinel_idx = _review_codex_compact_sentinel_offset(text)
    if sentinel_idx is None:
        return None
    prefix = text[:sentinel_idx]
    lines = text[sentinel_idx:].splitlines()
    if not lines or lines[0] != "LARCH_PROMPT_SENTINEL=1":
        return None
    values: dict[str, str] = {}
    for line in lines[1:]:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    if values.get("KIND") != "specialist" or not values.get("AGENT_FILE") or not values.get("MODE") or not values.get("HASH"):
        _err(f"agent launch-review: malformed prompt sentinel in {path} (missing or empty KIND/AGENT_FILE/MODE/HASH)")
        return 1, ""
    fake_args = argparse.Namespace()
    result = proc.run(
        [sys.executable, str(_PY_CLI), "render", "specialist", *_review_specialist_render_args(fake_args, sentinel=values)],
        check=False,
    )
    if result.returncode != 0:
        _err(result.stderr or result.stdout or "agent launch-review: render specialist failed")
        return 1, ""
    prompt = result.stdout
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    if digest != values["HASH"]:
        _err(f"agent launch-review: prompt reconstruction hash mismatch (sentinel={values['HASH']} reconstructed={digest})")
        return 1, ""
    if prefix:
        prompt = f"{prefix}{prompt}"
    return 0, prompt


def _review_resolve_prompt(args: argparse.Namespace) -> tuple[int, str]:
    if args.prompt is not None:
        return 0, args.prompt
    if args.prompt_file:
        if args.tool == "codex":
            sentinel = _review_read_codex_prompt_sentinel(args.prompt_file)
            if sentinel is not None:
                return sentinel
        return _review_read_prompt_file(args.prompt_file)
    if args.agent_file:
        return _review_render_specialist_prompt(args)
    return 2, ""


def _review_write_codex_prompt_sidecar(*, output: Path, prompt: str, args: argparse.Namespace) -> Path:
    sidecar = LauncherPaths.from_output(output).prompt
    if args.agent_file and not args.description_text:
        digest = hashlib.sha256(prompt.encode()).hexdigest()
        lines = [
            "LARCH_PROMPT_SENTINEL=1",
            "KIND=specialist",
            f"HASH={digest}",
            f"AGENT_FILE={args.agent_file}",
            f"MODE={args.mode}",
        ]
        if args.scope_files:
            lines.append(f"SCOPE_FILES={args.scope_files}")
        if args.competition_notice:
            lines.append("COMPETITION_NOTICE=true")
        if args.competition_notice_file and "\n" not in args.competition_notice_file:
            lines.append(f"COMPETITION_NOTICE_FILE={args.competition_notice_file}")
        if args.diff_file:
            lines.append(f"DIFF_FILE={args.diff_file}")
        if re.fullmatch(r"[0-9]+", args.commit_count or ""):
            lines.append(f"COMMIT_COUNT={args.commit_count}")
        if args.plan_file and "\n" not in args.plan_file:
            lines.append(f"PLAN_FILE={args.plan_file}")
        if args.feature_file and "\n" not in args.feature_file:
            lines.append(f"FEATURE_FILE={args.feature_file}")
        session_env_path = _review_session_env_path(args)
        ledger_file = findings_ledger.ledger_path(
            findings_ledger.ledger_root(output.parent, session_env_path=session_env_path)
        )
        if "\n" not in str(ledger_file):
            lines.append(f"FINDINGS_LEDGER_FILE={ledger_file}")
        if session_env_path and "\n" not in session_env_path:
            lines.append(f"SESSION_ENV_PATH={session_env_path}")
        _write(path=sidecar, text="\n".join(lines) + "\n")
    else:
        _write(path=sidecar, text=prompt)
    return sidecar


def _review_write_cursor_prompt_sidecar(*, output: Path, original_prompt: str) -> Path:
    sidecar = LauncherPaths.from_output(output).prompt
    _write(path=sidecar, text=original_prompt)
    return sidecar


def _review_apply_session_token_env() -> None:
    for env_name in ("IMPLEMENT_TMPDIR", "DESIGN_TMPDIR"):
        root = os.environ.get(env_name, "")
        if not root:
            continue
        session = Path(root) / "session-id"
        if not session.is_file() or session.stat().st_size == 0:
            continue
        text = session.read_text(encoding="utf-8", errors="replace").replace("\r", "").replace("\n", "")
        if text:
            os.environ["LARCH_TOKEN_SESSION_ID"] = text
            return


def _review_apply_claude_source_env() -> None:
    root = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not root:
        return
    source = Path(root) / "claude-source.env"
    if source.is_file() and source.stat().st_size > 0:
        os.environ["LARCH_CLAUDE_SOURCE_FILE"] = str(source)


def _review_effective_token_cap(args: argparse.Namespace) -> int | None:
    if args.token_budget_cap:
        return int(args.token_budget_cap)
    raw = os.environ.get("LARCH_TOKEN_BUDGET_CAP_REVIEW", "")
    if _is_positive_int(raw):
        return int(raw)
    return None


def _review_check_budget_or_write_cap_hit(*, output: Path, cap: int | None, timing_kind: str) -> bool:
    if cap is None:
        return False
    result = proc.run(
        [sys.executable, str(_PY_CLI), "token", "check-budget", "--cap", str(cap), "--step", timing_kind],
        check=False,
    )
    status = ""
    total = ""
    for token in result.stdout.split():
        if token.startswith("STATUS="):
            status = token.split("=", 1)[1]
        elif token.startswith("TOTAL="):
            total = token.split("=", 1)[1]
    if status != "cap_hit":
        return False
    _err(f"⚠ agent launch-review: step token budget cap of {cap} tokens exceeded ({total} combined vendor tokens); external reviewer fan-out skipped")
    _write(path=output, text="STATUS=cap_hit\n")
    _write(path=output.with_suffix(output.suffix + ".cap-hit"), text=f"STATUS=cap_hit\n{result.stdout.rstrip()}\n")
    if os.environ.get("IMPLEMENT_TMPDIR"):
        with contextlib.suppress(OSError):
            _write(path=Path(os.environ["IMPLEMENT_TMPDIR"]) / "step-budget-cap-hit.env", text=f"STATUS=cap_hit\n{result.stdout.rstrip()}\n")
    _write(path=output.with_suffix(output.suffix + ".done"), text="0\n")
    return True


def _review_record_timing(*, vendor: str, task_kind: str, start_s: float, output: Path, exit_code: int) -> None:
    _record_launch_timing(tool=vendor, task_kind=task_kind, start_s=start_s, output=output, exit_code=exit_code)


def _review_append_outer_meta(
    meta: Path,
    *,
    prompt_sidecar: Path,
    risk: str,
    stderr_sink: str,
    timing_task_kind: str = "",
    site: str = "review Step 2",
    model_role: str = "default",
) -> None:
    lines = [
        "OUTER_LAUNCHER=agent launch-review",
        f"OUTER_LAUNCHER_PROMPT_FILE={prompt_sidecar}",
        f"OUTER_LAUNCHER_WORKDIR={Path.cwd()}",
        f"OUTER_LAUNCHER_SITE={site}",
        f"OUTER_LAUNCHER_MODEL_ROLE={model_role or 'default'}",
    ]
    if risk:
        lines.append(f"OUTER_LAUNCHER_RISK={_review_coerce_risk(risk)}")
    if timing_task_kind:
        lines.append(f"OUTER_LAUNCHER_TIMING_KIND={timing_task_kind}")
    if stderr_sink:
        lines.append(f"STDERR_SINK={stderr_sink}")
    _append(path=meta, text="\n".join(lines) + "\n")


def _review_write_clean_readonly_dirty_tree(output: Path) -> None:
    _write(path=output.with_suffix(output.suffix + ".dirty-tree"), text="STATUS=clean\nMODE=baseline\nREASON=codex-sandbox-read-only\n")


def _review_write_unknown_dirty_tree(*, output: Path, reason: str) -> None:
    baseline = output.with_suffix(output.suffix + ".untracked-baseline")
    state = "present" if baseline.is_file() else "missing"
    _write(path=output.with_suffix(output.suffix + ".dirty-tree"), text=f"STATUS=unknown\nMODE=baseline\nUNTRACKED_BASELINE={state}\nREASON={reason}\n")


def _review_capture_cursor_dirty_baseline(output: Path) -> Path:
    baseline = output.with_suffix(output.suffix + ".untracked-baseline")
    for stale in (
        baseline,
        output.with_suffix(output.suffix + ".dirty-tree"),
        output.with_suffix(output.suffix + ".dirty-tree.tracked-paths"),
        output.with_suffix(output.suffix + ".dirty-tree.new-untracked-paths"),
    ):
        with contextlib.suppress(FileNotFoundError):
            stale.unlink()
    workdir = _resolve_review_codex_workdir(str(Path.cwd()))
    git.snapshot_untracked(proc, str(baseline), nul=True, cwd=workdir)
    return baseline


def _review_write_cursor_dirty_tree_from_baseline(*, output: Path, baseline: Path) -> None:
    workdir = _resolve_review_codex_workdir(str(Path.cwd()))
    lines = dirty_tree.baseline(baseline_path=str(baseline), sidecar=str(output.with_suffix(output.suffix + ".dirty-tree")), cwd=workdir)
    _write(path=output.with_suffix(output.suffix + ".dirty-tree"), text="\n".join(lines) + "\n")


def _review_failure_source(output: Path, *, sink: str = "") -> Path:
    return resolve_failure_diagnostic_source(output, sink=sink) or output.with_suffix(output.suffix + ".diag")


def _review_brainstorm_failure_uses_sink(*, timing_kind: str, stderr_sink: str) -> bool:
    return bool(stderr_sink) and timing_kind in ("codex-brainstorm", "cursor-brainstorm")


def _review_write_failure_sink(*, output: Path, stderr_sink: str, launcher_exit: int) -> None:
    diag = output.with_suffix(output.suffix + ".diag")
    content = diag.read_text(encoding="utf-8", errors="replace") if diag.is_file() else f"STATUS=FAILED\nLAUNCHER_EXIT={launcher_exit}\n"
    if "LAUNCHER_EXIT=" not in content:
        content += f"LAUNCHER_EXIT={launcher_exit}\n"
    _write(path=Path(stderr_sink), text=content)


def _review_append_launch_failure(
    *,
    output: Path,
    tool: str,
    exit_code: int,
    stderr_sink: str = "",
    auth_attempt: int = 1,
    transient_attempt: int = 1,
    site: str = "review Step 2",
) -> None:
    if exit_code == 0:
        return
    _compose_failure_diag(output, sink=stderr_sink)
    source = _review_failure_source(output, sink=stderr_sink)
    failure = classify_launch_failure(
        launcher_exit=exit_code,
        sidecar=source,
        auth_verdict=external_auth_verdict(tool, *_review_failure_auth_paths(output=output, source=source, stderr_sink=stderr_sink)),
        tool=tool,
        output_file=output,
    )
    log = _resolve_execution_issues_log()
    if log is not None:
        proc.run(
            [
                sys.executable,
                str(_PY_CLI),
                "run-log",
                "append-failure",
                "--log",
                str(log),
                "--site",
                site,
                "--tool",
                f"{tool}-review",
                "--exit-code",
                str(exit_code),
                "--category",
                "External Reviewer Issues",
                "--output-file",
                str(source),
                "--verdict",
                failure.reason or failure.failure_class,
                "--retry-count",
                str(auth_attempt),
                "--transient-retry-count",
                str(transient_attempt),
                "--redact",
            ],
            check=False,
        )
    _append_vendor_failure_diagnostics(source, site=f"{site} {tool}-review", exit_code=exit_code)


def _review_run_test_trap_after_inner_done_if_enabled() -> None:
    if os.environ.get("LARCH_ALLOW_TEST_HOOKS") != "1":
        return
    raw = os.environ.get("LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE", "")
    if not raw:
        return
    path = Path(raw)
    if path.is_file() and not path.is_symlink():
        subprocess.run([shutil.which("bash") or "/bin/bash", str(path)], check=False)


def _review_retry_delay(attempt: int) -> None:
    raw = os.environ.get("LARCH_TRANSIENT_RETRY_DELAY", "")
    if raw.isdigit():
        delay = int(raw)
        if delay > 0:
            time.sleep(delay)
        return
    delay = max(1 << attempt, 10) + random.randint(0, 1)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        delay = 0
    time.sleep(delay)


def _review_stream_reset(*, path: Path, history: Path, label: str) -> None:
    if path.is_file() and path.stat().st_size > 0:
        _append(path=history, text=f"===== {label} =====\n{path.read_text(encoding='utf-8', errors='replace')}\n")
    with contextlib.suppress(OSError):
        path.unlink()


def _review_reset_retry_artifacts(output: Path, *, tool: str, label: str) -> None:
    history = output.with_suffix(output.suffix + ".sidecar.history")
    _review_stream_reset(path=output.with_suffix(output.suffix + ".sidecar"), history=history, label=label)
    _review_stream_reset(path=output.with_suffix(output.suffix + ".diag"), history=history, label=f"{label} diag")
    if tool == "codex":
        _review_stream_reset(path=output.with_suffix(output.suffix + ".events.jsonl"), history=history, label=f"{label} events.jsonl")


def _review_run_wrapper_attempt(
    *,
    tool: str,
    output: Path,
    timeout_seconds: int,
    cmd: Sequence[str],
    capture_stdout_only: bool = False,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    stderr_sink: str = "",
) -> RunExternalAgentResult:
    old_suffix = os.environ.get("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX")
    os.environ["RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX"] = ".inner.done"
    state = external_startup_lock_acquire(tool=tool)
    external_startup_lock_release_after(state=state)
    try:
        return run_external_agent(
            tool=tool,
            output=str(output),
            timeout_seconds=timeout_seconds,
            cmd=cmd,
            capture_stdout_only=capture_stdout_only,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stderr_sink=stderr_sink,
        )
    finally:
        if old_suffix is None:
            os.environ.pop("RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX", None)
        else:
            os.environ["RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX"] = old_suffix


def _review_is_cursor_empty_result(output: Path) -> bool:
    if os.environ.get("LARCH_CURSOR_RETRY_EMPTY_RESULT", "1") == "0":
        return False
    if not output.is_file() or output.stat().st_size == 0:
        return False
    try:
        obj = json.loads(output.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and not (obj.get("result") or "")


def _review_run_with_retries(
    *,
    tool: str,
    output: Path,
    timeout_seconds: int,
    cmd: Sequence[str],
    capture_stdout_only: bool = False,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    stderr_sink: str = "",
) -> tuple[RunExternalAgentResult, int, int]:
    max_auth = _auth_retry_limit()
    auth_attempt = 1
    transient_attempt = 1
    result = RunExternalAgentResult(99, output)
    unclassified_empty_retried = False
    while True:
        result = _review_run_wrapper_attempt(
            tool=tool,
            output=output,
            timeout_seconds=timeout_seconds,
            cmd=cmd,
            capture_stdout_only=capture_stdout_only,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            stderr_sink=stderr_sink,
        )
        if tool == "codex" and result.exit_code != 0 and stdout_path is not None and stderr_path is not None:
            _mirror_codex_quota_from_events(events=stdout_path, sidecar=stderr_path)
        if tool == "codex":
            auth_sidecars = [stderr_path or output.with_suffix(output.suffix + ".sidecar")]
            quota_sidecars = [
                *auth_sidecars,
                output.with_suffix(output.suffix + ".diag"),
                stdout_path or output,
                output,
            ]
        else:
            auth_sidecars = [
                stderr_path or output.with_suffix(output.suffix + ".sidecar"),
                output.with_suffix(output.suffix + ".diag"),
                stdout_path or output,
                output,
            ]
            quota_sidecars = auth_sidecars
        verdict = external_auth_verdict(tool, *auth_sidecars)
        auth_failure = verdict == "auth"
        quota_failure = any(is_quota_failure(tool=tool, sidecar=p) for p in quota_sidecars)
        transient_failure = is_transient_infra_failure(tool=tool, exit_code=result.exit_code, output_file=output)
        empty_cursor = tool == "cursor" and result.exit_code == 0 and _review_is_cursor_empty_result(output)
        retryable_response = (result.exit_code != 0 and transient_failure) or empty_cursor
        retry_budget_remaining = transient_attempt <= _REVIEW_MAX_TRANSIENT_RETRIES
        if retryable_response and retry_budget_remaining and not auth_failure and not quota_failure:
            transient_attempt += 1
            _review_retry_delay(transient_attempt)
            _review_reset_retry_artifacts(output, tool=tool, label="attempt")
            continue
        if (
            result.exit_code != 0
            and not unclassified_empty_retried
            and _is_unclassified_empty_startup_failure(exit_code=result.exit_code, verdict=verdict)
            and not auth_failure
            and not quota_failure
        ):
            unclassified_empty_retried = True
            _review_reset_retry_artifacts(
                output,
                tool=tool,
                label="cursor auth attempt" if tool == "cursor" else "attempt",
            )
            continue
        if result.exit_code != 0 and auth_failure and auth_attempt < max_auth:
            auth_attempt += 1
            _review_reset_retry_artifacts(
                output,
                tool=tool,
                label="cursor auth attempt" if tool == "cursor" else "attempt",
            )
            continue
        return result, auth_attempt, transient_attempt


def _review_emit_launcher_result(*, output: Path, tool: str, launcher_exit: int, stderr_sink: str = "") -> None:
    if launcher_exit != 0:
        _compose_failure_diag(output, sink=stderr_sink)
    sidecar = _review_failure_source(output, sink=stderr_sink)
    failure = classify_launch_failure(
        launcher_exit=launcher_exit,
        sidecar=sidecar,
        auth_verdict=external_auth_verdict(tool, *_review_failure_auth_paths(output=output, source=sidecar, stderr_sink=stderr_sink)),
        tool=tool,
        output_file=output,
    )
    _emit_kv(key="LAUNCHER_EXIT", value=launcher_exit)
    _emit_kv(key="LAUNCHER_FAILURE_CLASS", value=failure.failure_class)
    _emit_kv(key="LAUNCHER_FAILURE_REASON", value=failure.reason)
    _emit_kv(key="OUTPUT", value=str(output))


def _review_write_preflight_bundle(
    *,
    output: Path,
    args: argparse.Namespace,
    failure_reason: str,
    tool: str,
    capture_stdout_only: bool = False,
    prompt_sidecar: Path | None = None,
) -> None:
    _write(path=output, text="")
    _write(path=output.with_suffix(output.suffix + ".diag"), text=f"STATUS=FAILED\nFAILURE_REASON={failure_reason}\n")
    meta = output.with_suffix(output.suffix + ".meta")
    _write(
        path=meta,
        text=f"TOOL={tool}\nTIMEOUT={args.timeout}\nCAPTURE_STDOUT=false\n"
        f"CAPTURE_STDOUT_ONLY={str(capture_stdout_only).lower()}\nOUTPUT_FILE={output}\nCMD_JSON=[]\n"
    )
    if prompt_sidecar is not None:
        _review_append_outer_meta(
            meta,
            prompt_sidecar=prompt_sidecar,
            risk=args.risk,
            stderr_sink=args.stderr_sink,
            timing_task_kind=args.timing_task_kind or f"{tool}-review",
            site=getattr(args, "site", "review Step 2"),
            model_role=getattr(args, "model_role", "default"),
        )


def _review_write_preflight_done(*, output: Path, launcher_exit: int) -> None:
    _write(path=output.with_suffix(output.suffix + ".done"), text=f"{launcher_exit}\n")


def _review_atomic_write_text(*, path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".atomic.tmp")
    _write(path=tmp, text=text)
    tmp.replace(path)


def _review_launch_codex(*, args: argparse.Namespace, prompt: str) -> int:
    output = Path(args.output)
    paths = LauncherPaths.from_output(output)
    timing_kind = args.timing_task_kind or "codex-review"
    site = getattr(args, "site", "review Step 2")
    if "'''" in _CODEX_REVIEW_STRICT_PREAMBLE:
        _err("agent launch-review: hardening preamble contains TOML triple-single-quote delimiter")
        return 2
    try:
        sandbox_dir = output.parent.resolve(strict=True)
    except FileNotFoundError:
        _err(f"agent launch-review: output parent directory does not exist: {output.parent}")
        return 2
    start = time.time()
    prompt_sidecar = _review_write_codex_prompt_sidecar(output=output, prompt=prompt, args=args)
    with tempfile.TemporaryDirectory(prefix="larch-codex-review-home-", dir=str(_probe_tmpdir())) as home:
        home_path = Path(home).resolve()
        try:
            output_parent = output.parent.resolve(strict=True)
            if _under(path=home_path, root=output_parent):
                _err(f"agent launch-review: CODEX_HOME inside output tree: {home_path}")
                return 2
        except FileNotFoundError:
            pass
        instr_path = Path(home) / "trusted-instructions.txt"
        instr_path.write_text(_CODEX_REVIEW_STRICT_PREAMBLE, encoding="utf-8")
        auth_rc, auth_msg = _prepare_codex_home(Path(home), trusted_instructions_file=str(instr_path))
        if auth_rc != 0:
            reason = auth_msg or f"codex auth setup failed (exit {auth_rc})"
            _review_write_preflight_bundle(output=output, args=args, failure_reason=reason, tool="codex", prompt_sidecar=prompt_sidecar)
            _review_write_clean_readonly_dirty_tree(output)
            _review_write_preflight_done(output=output, launcher_exit=auth_rc)
            if _review_brainstorm_failure_uses_sink(timing_kind=timing_kind, stderr_sink=args.stderr_sink):
                _review_write_failure_sink(output=output, stderr_sink=args.stderr_sink, launcher_exit=auth_rc)
            _review_emit_launcher_result(output=output, tool="codex", launcher_exit=auth_rc, stderr_sink=args.stderr_sink)
            return 0
        try:
            try:
                model_args = list(resolve_model_args("codex", with_effort=True, codex_role=getattr(args, "model_role", "default")).argv)
            except TypeError:
                model_args = list(resolve_model_args("codex", with_effort=True).argv)
        except ValueError as exc:
            _review_record_timing(vendor="codex", task_kind=timing_kind, start_s=start, output=output, exit_code=1)
            _review_write_preflight_bundle(output=output, args=args, failure_reason=f"agent model-args failed (exit 1): {exc}", tool="codex", prompt_sidecar=prompt_sidecar)
            _review_write_unknown_dirty_tree(output=output, reason="model-args-preflight-no-agent-ran")
            _review_write_preflight_done(output=output, launcher_exit=1)
            _review_emit_launcher_result(output=output, tool="codex", launcher_exit=1, stderr_sink=args.stderr_sink)
            return 1
        workdir = _resolve_review_codex_workdir(str(Path.cwd()))
        cmd = [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "-C",
            workdir,
            "--add-dir",
            str(sandbox_dir),
            *model_args,
            "-c",
            _trust_config_arg(workdir),
            *_codex_auth_args(),
            "--output-last-message",
            str(output),
            "--json",
            "--",
            prompt,
        ]
        with _temporary_env(name="CODEX_HOME", value=home):
            result, auth_attempt, transient_attempt = _review_run_with_retries(
                tool="codex",
                output=output,
                timeout_seconds=int(args.timeout),
                cmd=cmd,
                stdout_path=paths.events,
                stderr_path=paths.sidecar,
                stderr_sink=args.stderr_sink,
            )
    events = paths.events
    if not events.is_file() or events.stat().st_size == 0:
        _write(path=events, text="{}\n")
    sidecar = paths.sidecar
    if result.exit_code != 0:
        _mirror_codex_quota_from_events(events=events, sidecar=sidecar)
        _review_append_launch_failure(output=output, tool="codex", exit_code=result.exit_code, stderr_sink=args.stderr_sink, auth_attempt=auth_attempt, transient_attempt=transient_attempt, site=site)
    elif sidecar.is_file():
        _append(path=sidecar, text="codex-status: ok (no stderr emitted during agent run)\n")
    _review_append_outer_meta(
        paths.meta,
        prompt_sidecar=prompt_sidecar,
        risk=args.risk,
        stderr_sink=args.stderr_sink,
        timing_task_kind=timing_kind,
        site=site,
        model_role=getattr(args, "model_role", "default"),
    )
    _review_record_timing(vendor="codex", task_kind=timing_kind, start_s=start, output=output, exit_code=result.exit_code)
    model = ""
    for i, value in enumerate(model_args):
        if value == "-m" and i + 1 < len(model_args):
            model = model_args[i + 1]
            break
    token_record_path = paths.token_record
    _record_usage_from_events(events=events, sidecar=sidecar, label="codex_review", token_record=token_record_path, model=model)
    if token_record_path.is_file():
        proc.run(
            [sys.executable, str(_PY_CLI), "token", "record-vendor-sidecar", "--input", str(token_record_path)],
            check=False,
        )
    _review_write_clean_readonly_dirty_tree(output)
    _promote_inner_done(output)
    _review_emit_launcher_result(output=output, tool="codex", launcher_exit=result.exit_code, stderr_sink=args.stderr_sink)
    return result.exit_code


def _review_setup_cursor_config_dir() -> tuple[Path, str | None]:
    cfg_tmp = Path(tempfile.mkdtemp(prefix="larch-cursor-cfg-"))
    old_cfg = os.environ.get("CURSOR_CONFIG_DIR")
    os.environ["CURSOR_CONFIG_DIR"] = str(cfg_tmp)
    user_cfg = Path.home() / ".cursor" / "cli-config.json"
    if user_cfg.is_file():
        with contextlib.suppress(OSError):
            shutil.copyfile(user_cfg, cfg_tmp / "cli-config.json")
    return cfg_tmp, old_cfg


def _review_cleanup_cursor_config_dir(*, cfg_tmp: Path, old_cfg: str | None) -> None:
    shutil.rmtree(cfg_tmp, ignore_errors=True)
    if old_cfg is None:
        os.environ.pop("CURSOR_CONFIG_DIR", None)
    else:
        os.environ["CURSOR_CONFIG_DIR"] = old_cfg


def _review_cursor_jitter() -> None:
    raw = os.environ.get("LARCH_CURSOR_LAUNCH_JITTER_MS", "250")
    max_ms = int(raw) if raw.isdigit() else 250
    if max_ms <= 0:
        return
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    time.sleep(random.randint(0, max_ms) / 1000.0)


def _review_cursor_line_no_issues(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("{"):
        return False
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and obj.get("no_issues_found") is True


def _review_cursor_has_structured_findings(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        # A valid structured finding record always carries schema_version, so a
        # schema_version key (even on an invalid/partial finding) blocks collapse.
        if isinstance(obj, dict) and "schema_version" in obj:
            return True
    return False


def _review_cursor_normalize_no_issues(text: str) -> str:
    if not text.strip():
        return text
    if _review_cursor_has_structured_findings(text):
        return text
    first = ""
    for line in text.splitlines():
        if line.strip():
            first = line.strip()
            break
    if re.search(r"^\s*schema_version", text, re.MULTILINE):
        return text
    if first and not first.startswith("{"):
        match = re.search(r'\{[^{}]*"no_issues_found"[^{}]*\}', first)
        if match:
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict) and obj.get("no_issues_found") is True:
                return '{"no_issues_found": true}\n'
    sentinel_count = sum(1 for line in text.splitlines() if line.strip() == "NO_ISSUES_FOUND" or _review_cursor_line_no_issues(line))
    if sentinel_count == 1:
        return '{"no_issues_found": true}\n'
    return text


def _cursor_input_work_tokens(obj: object) -> int:
    """Total input-work tokens (inputTokens + cacheReadTokens) from a Cursor JSON envelope.

    A Cursor review that ingests the plan and reads files reports thousands of input
    tokens; a slot that never ran inference (issue #5518) reports ~0. Missing or
    non-numeric usage fields count as zero work.
    """
    usage = obj.get("usage") if isinstance(obj, dict) else None
    if not isinstance(usage, dict):
        return 0
    total = 0
    for key in ("inputTokens", "cacheReadTokens"):
        try:
            total += _num(usage.get(key))
        except ValueError:
            continue
    return total


def _cursor_output_tokens(obj: object) -> int:
    """Cursor envelope output-token count; missing or non-numeric values count as 0."""
    usage = obj.get("usage") if isinstance(obj, dict) else None
    if not isinstance(usage, dict):
        return 0
    try:
        return _num(usage.get("outputTokens"))
    except ValueError:
        return 0


def _review_cursor_result_is_no_issues(text: str) -> bool:
    """True when a normalized Cursor result is exactly the no-issues sentinel (no findings)."""
    if _review_cursor_has_structured_findings(text):
        return False
    non_empty = [line.strip() for line in text.splitlines() if line.strip()]
    if len(non_empty) != 1:
        return False
    return non_empty[0] == "NO_ISSUES_FOUND" or _review_cursor_line_no_issues(non_empty[0])


def _review_write_cursor_degraded_diag(*, output: Path, obj: object, reason: str) -> None:
    usage = obj.get("usage") if isinstance(obj, dict) and isinstance(obj.get("usage"), dict) else {}
    if isinstance(usage, dict):
        for key in ("inputTokens", "cacheReadTokens", "outputTokens"):
            if key in usage:
                reason += f" usage.{key}={usage[key]}"
    diag_text = redact.redact_secrets_only(redact.redact_tmpdir_paths(f"TOOL=cursor\nFAILURE_REASON={reason}\n"))
    _write(path=output.with_suffix(output.suffix + ".diag"), text=diag_text)


def _review_write_cursor_no_work_diag(*, output: Path, obj: object) -> None:
    _review_write_cursor_degraded_diag(
        output=output,
        obj=obj,
        reason=(
            "cursor-no-work-no-issues: exit 0, bare no_issues_found sentinel with input work "
            f"<= {_CURSOR_NO_WORK_INPUT_TOKEN_FLOOR} tokens (slot did not ingest the review; "
            "likely in-process auth/backend failure)"
        ),
    )


def _review_cursor_write_result(*, output: Path, result: str, obj: object) -> None:
    """Persist a Cursor review result, downgrading canned / degraded responses.

    A bare no-issues sentinel from a slot that ingested ~nothing (input work at/below the
    floor) is a canned response (#5518). A high-output/low-byte result that fails research validation is a
    degraded backend response. All are written as ``CURSOR_DEGRADED_RESPONSE`` so the
    collector does not score them as clean.
    """
    result_bytes = len(result.encode())
    if _review_cursor_result_is_no_issues(result) and _cursor_input_work_tokens(obj) <= _CURSOR_NO_WORK_INPUT_TOKEN_FLOOR:
        _review_atomic_write_text(path=output, text="CURSOR_DEGRADED_RESPONSE\n")
        _review_write_cursor_no_work_diag(output=output, obj=obj)
        return
    if _cursor_output_tokens(obj) > _CURSOR_DEGRADED_OUTPUT_TOKEN_FLOOR and result_bytes < _CURSOR_DEGRADED_RESULT_BYTES_CEILING:
        tmp = output.with_suffix(output.suffix + ".extract.tmp")
        _write(path=tmp, text=result)
        ok = proc.run([sys.executable, str(_PY_CLI), "eval", "validate-research-output", "--validation-mode", str(tmp)], check=False).returncode == 0
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()
        _review_atomic_write_text(path=output, text=result if ok else "CURSOR_DEGRADED_RESPONSE\n")
        return
    _review_atomic_write_text(path=output, text=result)


def _review_cursor_postprocess(*, output: Path, transient_attempt: int) -> None:
    if not output.is_file() or output.stat().st_size == 0:
        return
    raw = output.read_bytes()
    json_sidecar = output.with_suffix(output.suffix + ".json")
    with contextlib.suppress(FileNotFoundError):
        json_sidecar.unlink()
    json_sidecar.write_bytes(raw)
    try:
        obj = json.loads(raw.decode("utf-8", "replace"))
    except json.JSONDecodeError:
        return
    if not isinstance(obj, dict):
        return
    result = obj.get("result") or ""
    if isinstance(result, str) and result:
        result = _review_cursor_normalize_no_issues(result)
        _review_cursor_write_result(output=output, result=result, obj=obj)
    _record_cursor_usage_from_output(output=json_sidecar, label="cursor_review")
    token_record = json_sidecar.with_suffix(json_sidecar.suffix + ".token-record")
    if token_record.is_file():
        token_record.replace(output.with_suffix(output.suffix + ".token-record"))
    if not result:
        _review_atomic_write_text(path=output, text="CURSOR_EMPTY_RESPONSE\n")
        usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
        fields = [
            "TOOL=cursor",
            f"FAILURE_REASON=cursor-empty-result: exit 0, .result empty/null after {max(transient_attempt - 1, 0)} transient retries (shared exit-code and empty-result budget)",
        ]
        for key in ("type", "subtype", "is_error", "duration", "request_id", "requestId"):
            if key in obj:
                fields[-1] += f" {key}={str(obj[key]).replace(chr(10), ' ')[:200]}"
        if isinstance(usage, dict):
            for key in ("inputTokens", "outputTokens"):
                if key in usage:
                    fields[-1] += f" usage.{key}={usage[key]}"
        diag_text = redact.redact_secrets_only(redact.redact_tmpdir_paths("\n".join(fields) + "\n"))
        _write(path=output.with_suffix(output.suffix + ".diag"), text=diag_text)


def _review_launch_cursor(*, args: argparse.Namespace, original_prompt: str) -> int:
    paths = LauncherPaths.from_output(output := Path(args.output))
    timing_kind = args.timing_task_kind or "cursor-review"
    site = getattr(args, "site", "review Step 2")
    start = time.time()
    prompt_sidecar = _review_write_cursor_prompt_sidecar(output=output, original_prompt=original_prompt)
    try:
        model_args = list(resolve_model_args("cursor", with_effort=True).argv)
    except ValueError as exc:
        _review_record_timing(vendor="cursor", task_kind=timing_kind, start_s=start, output=output, exit_code=1)
        _review_write_preflight_bundle(
            output=output,
            args=args,
            failure_reason=f"cursor_launcher_load_model_args failed (exit 1): {exc}",
            tool="cursor",
            capture_stdout_only=True,
            prompt_sidecar=prompt_sidecar,
        )
        _review_write_unknown_dirty_tree(output=output, reason="model-args-preflight-no-agent-ran")
        _review_write_preflight_done(output=output, launcher_exit=1)
        _review_emit_launcher_result(output=output, tool="cursor", launcher_exit=1, stderr_sink=args.stderr_sink)
        return 1
    baseline = _review_capture_cursor_dirty_baseline(output)
    verdict = cursor_auth_preflight(caller="agent launch-review")
    if not verdict.ok:
        _err(verdict.message)
        _review_write_preflight_bundle(
            output=output,
            args=args,
            failure_reason="cursor-auth-preflight: CURSOR_API_KEY unset/empty and cursor-user keychain entry missing on Darwin; see docs/installation-and-setup.md (Cursor section)",
            tool="cursor",
            capture_stdout_only=True,
            prompt_sidecar=prompt_sidecar,
        )
        _review_write_unknown_dirty_tree(output=output, reason="preflight-short-circuit-no-agent-ran")
        _review_write_preflight_done(output=output, launcher_exit=verdict.rc)
        _review_emit_launcher_result(output=output, tool="cursor", launcher_exit=verdict.rc, stderr_sink=args.stderr_sink)
        return verdict.rc
    if not cursor_preread_service_token():
        _err(CURSOR_PREREAD_FAIL_MSG)
        _review_write_preflight_bundle(
            output=output,
            args=args,
            failure_reason="cursor-preread-service-token: keychain -w read returned no token on Darwin; see docs/installation-and-setup.md (Cursor section)",
            tool="cursor",
            capture_stdout_only=True,
            prompt_sidecar=prompt_sidecar,
        )
        _review_write_unknown_dirty_tree(output=output, reason="preflight-short-circuit-no-agent-ran")
        _review_write_preflight_done(output=output, launcher_exit=CURSOR_PREREAD_FAIL_RC)
        _review_emit_launcher_result(output=output, tool="cursor", launcher_exit=CURSOR_PREREAD_FAIL_RC, stderr_sink=args.stderr_sink)
        return CURSOR_PREREAD_FAIL_RC
    cursor_auth_export_env()
    prompt = f"{_CURSOR_REVIEW_STRICT_PREAMBLE}\n\n{original_prompt}"
    wrapped = f" /max-mode on. Prompt: {prompt}"
    cfg_tmp, old_cfg = _review_setup_cursor_config_dir()
    _review_cursor_jitter()
    sidecar_path = paths.sidecar
    _write(path=sidecar_path, text="")
    try:
        workdir = _resolve_review_codex_workdir(str(Path.cwd()))
        cmd = [
            "cursor",
            "agent",
            "-p",
            "--trust",
            "--mode",
            "ask",
            "--output-format",
            "json",
            *model_args,
            "--workspace",
            workdir,
            wrapped,
        ]
        result, auth_attempt, transient_attempt = _review_run_with_retries(
            tool="cursor",
            output=output,
            timeout_seconds=int(args.timeout),
            cmd=cmd,
            capture_stdout_only=True,
            stderr_sink=args.stderr_sink,
        )
    finally:
        _review_cleanup_cursor_config_dir(cfg_tmp=cfg_tmp, old_cfg=old_cfg)
    if result.exit_code != 0:
        if _review_brainstorm_failure_uses_sink(timing_kind=timing_kind, stderr_sink=args.stderr_sink):
            _review_write_failure_sink(output=output, stderr_sink=args.stderr_sink, launcher_exit=result.exit_code)
        else:
            _review_append_launch_failure(output=output, tool="cursor", exit_code=result.exit_code, stderr_sink=args.stderr_sink, auth_attempt=auth_attempt, transient_attempt=transient_attempt, site=site)
    else:
        _append(path=sidecar_path, text="cursor-status: ok (no stderr emitted during agent run)\n")
    _review_append_outer_meta(
        paths.meta,
        prompt_sidecar=prompt_sidecar,
        risk=args.risk,
        stderr_sink=args.stderr_sink,
        timing_task_kind=timing_kind,
        site=site,
        model_role=getattr(args, "model_role", "default"),
    )
    _review_run_test_trap_after_inner_done_if_enabled()
    if result.exit_code == 0:
        _review_cursor_postprocess(output=output, transient_attempt=transient_attempt)
    _review_write_cursor_dirty_tree_from_baseline(output=output, baseline=baseline)
    _review_record_timing(vendor="cursor", task_kind=timing_kind, start_s=start, output=output, exit_code=result.exit_code)
    _promote_inner_done(output)
    _review_emit_launcher_result(output=output, tool="cursor", launcher_exit=result.exit_code, stderr_sink=args.stderr_sink)
    return result.exit_code


def launch_review_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = _review_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    validation_rc = _review_validate_args(args)
    if validation_rc != 0:
        return validation_rc
    if not args.timing_task_kind or args.timing_task_kind.startswith("--"):
        args.timing_task_kind = f"{args.tool}-review"
    _review_apply_session_token_env()
    _review_apply_claude_source_env()
    output = Path(args.output)
    if _review_check_budget_or_write_cap_hit(output=output, cap=_review_effective_token_cap(args), timing_kind=args.timing_task_kind):
        return 0
    prompt_rc, prompt = _review_resolve_prompt(args)
    if prompt_rc != 0:
        return prompt_rc
    if args.tool == "codex":
        return _review_launch_codex(args=args, prompt=prompt)
    return _review_launch_cursor(args=args, original_prompt=prompt)
