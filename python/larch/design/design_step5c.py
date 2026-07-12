"""Step 2b.5 plan-size check, Step 5c publish, and Step 5c status helpers."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false
# ruff: noqa: PLR2004

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence

from larch import io as larch_io
from larch.core import config, logging_util
from larch.core.ctx import Ctx

from larch.design.design_core import (
    _CoreUsageError,
    _capture_contract_stream_to_paths,
    _core_diagnostic,
    _core_print_exc,
    _emit_core_kvs,
    _read_env_value,
    _validate_design_tmpdir_arg,
    _append_failure,
    design_write_merge_env,
)
from larch.design.design_session import (
    _call_pause_save,
    _capture_stdout_stderr,
    _design_require_plugin_root,
    _design_tmpdir,
    _parse_common_wrapper_args,
    _print_text,
    _rehydrate_wrapper_env,
    _touch,
    step2b5_next_action_for,
)
from larch.design.design_step0 import _step2b5_self_log
from larch.design.design_step0_env import load_bash_quoted_env
from larch.design.design_terminal import (
    _emit_final_summary_marked_from_disk,
    _emit_report_gate_sidecars_from_disk,
    _publish_terminal_final_summary,
    read_result_env_main,
    stage_terminal_state_core,
)
from larch.design.design_summary import resolve_summary_mode
from larch.design import plan_grammar, plan_quality

def step2b5_main(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step2b5.sh: {exc}", file=sys.stderr)
        return 2
    _rehydrate_wrapper_env(parsed)
    req = _design_require_plugin_root()
    if req != 0:
        return req
    design_tmpdir = _design_tmpdir()
    if (design_tmpdir / ".pause-requested").is_file():
        return _call_pause_save(design_tmpdir=design_tmpdir)
    plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    stderr_tmp = design_tmpdir / f".check-plan-size.stderr.{os.getpid()}.tmp"
    with contextlib.suppress(FileNotFoundError):
        stderr_tmp.unlink()
    old_quiet = os.environ.get("LARCH_QUIET_DISABLE")
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    try:
        rc, out = _capture_stdout_stderr(callable_obj=plan_quality.check_plan_size_main, argv=["--design-tmpdir", str(design_tmpdir)], stderr_path=stderr_tmp)
    finally:
        if old_quiet is None:
            os.environ.pop("LARCH_QUIET_DISABLE", None)
        else:
            os.environ["LARCH_QUIET_DISABLE"] = old_quiet
    _print_text(out)
    stderr_text = ""
    if stderr_tmp.is_file():
        stderr_text = stderr_tmp.read_text(encoding="utf-8", errors="replace")
    check_size_kvs = larch_io.parse_kv((out or "") + "\n" + stderr_text)
    partition_requested = False
    run_params_path = design_tmpdir / "run-params.json"
    if run_params_path.is_file():
        try:
            data = json.loads(run_params_path.read_text(encoding="utf-8"))
            partition_requested = data.get("partition_requested") is True
        except (OSError, json.JSONDecodeError):
            partition_requested = False
    step2b5 = step2b5_next_action_for(check_size_rc=rc, check_size_kvs=check_size_kvs, partition_requested=partition_requested)
    print(f"STEP2B5_STATUS={step2b5.status}")
    print(f"STEP2B5_NEXT_ACTION={step2b5.action}")
    print(f"STEP2B5_EXIT_RC={step2b5.exit_rc}")
    try:
        _step2b5_self_log(plugin_root=plugin_root, design_tmpdir=design_tmpdir, rc=rc, stdout=out, stderr_tmp=stderr_tmp)
    finally:
        with contextlib.suppress(FileNotFoundError):
            stderr_tmp.unlink()
    return step2b5.exit_rc


def _step5b_mark_complete(design_tmpdir: Path) -> None:
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-5b").touch()


STEP5C_PUBLISH_RESULT_ALLOW_KEYS = (
    "PUBLISH_ATTEMPT_ID",
    "PUBLISH_RC_SOURCE",
    "LATEST_PHASE",
    "LOG_PUBLISH_ATTEMPTED",
    "LOG_PUBLISH_COMPLETED",
    "DESIGNED_ADMISSION_READY",
    "PLAN_WRITE_OK",
    "VALIDATE_STATUS",
    "VALIDATE_DEFECT_COUNT",
    "VALIDATE_SKIPPED_COUNT",
    "VALIDATE_UNSAFE_TOKEN_COUNT",
    "VALIDATE_MISSING_SCRIPT_COUNT",
    "VALIDATE_LOG_FILE",
    "PUBLISH_OK",
    "RENAMED",
    "UPSERT_STATUS",
    "ARCHITECTURE_SOURCE",
    "FINAL_SUMMARY_PATH",
    "PR_NUMBER",
    "PR_URL",
    "RECOVERY_BRANCH",
    "LOG_RECOVERY_BRANCH",
    "PUBLISH_REFUSE_REASON",
    "ARCH_INVARIANT_ASSESSMENT_REQUIRED",
    "ARCH_INVARIANT_ASSESSMENT_PRESENT",
    "ARCH_INVARIANT_ASSESSMENT_STATUS",
    "ARCH_INVARIANT_ASSESSMENT_ARTIFACT",
    "ARCH_GUIDE_ASSESSMENT_REQUIRED",
    "ARCH_GUIDE_ASSESSMENT_PRESENT",
    "ARCH_GUIDE_ASSESSMENT_STATUS",
    "ARCH_GUIDE_ASSESSMENT_ARTIFACT",
)


def _step5c_safe_publish_env(
    *, design_tmpdir: Path,
    publish_rc: int,
    publish_stdout_file: Path,
    attempt_id: str = "",
) -> tuple[int, dict[str, str], bool]:
    primary = design_tmpdir / ".design-publish-result.env"
    stdout_fallback = False
    if publish_rc in {1, 3, 4}:
        primary = design_tmpdir / f".design-publish-result.env.rc{publish_rc}-primary-missing.{os.getpid()}"
        with contextlib.suppress(FileNotFoundError):
            primary.unlink()
        stdout_fallback = True
    fd = -1
    safe_name = ""
    try:
        fd, safe_name = tempfile.mkstemp(prefix=".design-publish-safe.", dir=str(design_tmpdir))
        os.close(fd)
        fd = -1
        safe_path = Path(safe_name)
        argv = ["--input", str(primary), "--fallback-input", str(publish_stdout_file)]
        for key in STEP5C_PUBLISH_RESULT_ALLOW_KEYS:
            argv.extend(["--allow", key])
        argv.extend(["--output", str(safe_path)])
        rre_rc = read_result_env_main(argv)
        if rre_rc != 0:
            return int(rre_rc), {}, stdout_fallback
        values = load_bash_quoted_env(path=safe_path, allow_keys=STEP5C_PUBLISH_RESULT_ALLOW_KEYS)
        if attempt_id and values.get("PUBLISH_ATTEMPT_ID") != attempt_id:
            return 1, {}, stdout_fallback
        return 0, values, stdout_fallback
    finally:
        if fd >= 0:
            os.close(fd)
        if safe_name:
            with contextlib.suppress(FileNotFoundError):
                Path(safe_name).unlink()
        if stdout_fallback:
            with contextlib.suppress(FileNotFoundError):
                primary.unlink()


def _step5c_render_final_summary(
    *, design_tmpdir: Path,
    ctx: Ctx,
    outcome: str,
    final_summary_path: str,
    plan_write_ok: str = "",
) -> bool:
    del plan_write_ok
    from larch.design.design_summary import (  # noqa: PLC0415
        FinalSummaryRenderRequest,
        render_final_summary_for_request,
    )

    return render_final_summary_for_request(
        FinalSummaryRenderRequest(
            design_tmpdir=design_tmpdir,
            outcome=outcome,
            mode=resolve_summary_mode(design_tmpdir),
            issue_number=ctx.issue_number,
            session_id=ctx.session_id,
            repo=ctx.repo,
            upsert_summary_comment=True,
            stdout_log_path=design_tmpdir / f"render-final-summary.{outcome}.stdout.log",
            final_summary_path=Path(final_summary_path),
        )
    )


def _step5c_stage_failed_publish_tail(
    *, design_tmpdir: Path, plugin_root: Path, publish_rc: int, result_env: dict[str, str] | None = None
) -> None:
    detail_log = design_tmpdir / "design-publish-tail.failure.log"
    if not detail_log.is_file():
        detail_log.write_text(f"design-publish.sh failed (exit {publish_rc})\n", encoding="utf-8")
    stdout_log = design_tmpdir / "design-stage-terminal-state.stdout.log"
    stderr_log = design_tmpdir / "design-stage-terminal-state.stderr.log"
    result_env = result_env or {}
    stage_args = [
        "--design-tmpdir",
        str(design_tmpdir),
        "--outcome",
        "failed-publish-tail",
        "--step",
        "publish",
        "--phase",
        "publish",
        "--site",
        "design-publish",
        "--trigger",
        "publish-tail-failed",
        "--bail-reason",
        "publish-tail-failed",
        "--exit-code",
        str(publish_rc),
        "--source-script",
        "design-step5c",
        "--summary-outcome",
        "failed-publish-tail",
        "--failure-detail-log",
        str(detail_log),
    ]
    for flag, key in (
        ("--publish-attempt-id", "PUBLISH_ATTEMPT_ID"),
        ("--publish-rc-source", "PUBLISH_RC_SOURCE"),
        ("--latest-phase", "LATEST_PHASE"),
        ("--plan-write-ok", "PLAN_WRITE_OK"),
        ("--publish-ok", "PUBLISH_OK"),
        ("--renamed", "RENAMED"),
        ("--log-publish-attempted", "LOG_PUBLISH_ATTEMPTED"),
        ("--log-publish-completed", "LOG_PUBLISH_COMPLETED"),
        ("--designed-admission-ready", "DESIGNED_ADMISSION_READY"),
        ("--pr-url", "PR_URL"),
        ("--recovery-branch", "RECOVERY_BRANCH"),
    ):
        if result_env.get(key, ""):
            stage_args.extend([flag, result_env[key]])
    stage_rc = _capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout_log,
        stderr_log,
        stage_args,
    )
    if _read_env_value(path=stdout_log, key="STAGED", default="") == "false":
        _append_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            site="design Step 5c publish-tail staging",
            tool="design-stage-terminal-state.sh",
            exit_code=0,
            category="Warnings",
            output_file=stdout_log,
        )
    elif stage_rc != 0:
        _append_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            site="design Step 5c publish-tail staging",
            tool="design-stage-terminal-state.sh",
            exit_code=stage_rc,
            category="Warnings",
            output_file=stderr_log,
        )


def _step5c_publish_evidence_present(*, design_tmpdir: Path, publish_stdout_file: Path) -> bool:
    evidence_keys = ("PUBLISH_OK=", "PR_URL=", "RECOVERY_BRANCH=")
    texts = [
        source.read_text(encoding="utf-8", errors="replace")
        for source in (publish_stdout_file, design_tmpdir / ".design-publish-result.env")
        if source.is_file()
    ]
    return any(key in text for text in texts for key in evidence_keys)


def _step5c_try_central_failed_publish_tail(
    *,
    design_tmpdir: Path,
    ctx: Ctx,
    publish_stdout_file: Path,
) -> bool:
    if _step5c_publish_evidence_present(design_tmpdir=design_tmpdir, publish_stdout_file=publish_stdout_file):
        return False
    if not ctx.session_id:
        return False
    publish_rc, publish_ok = _publish_terminal_final_summary(
        design_tmpdir=design_tmpdir,
        run_id=ctx.session_id,
        issue=ctx.issue_number,
        outcome="failed-publish-tail",
        repo=ctx.repo,
    )
    if publish_rc != 0 or not publish_ok:
        return False
    from larch.design.design_summary import upsert_final_summary_from_disk  # noqa: PLC0415

    repo_args = ["--repo", ctx.repo] if ctx.repo else []
    return upsert_final_summary_from_disk(
        design_tmpdir=design_tmpdir,
        issue=ctx.issue_number,
        session_id=ctx.session_id,
        repo_args=repo_args,
        final_summary_path=design_tmpdir / "final-summary.md",
    )


def _step5c_write_status(
    *, design_tmpdir: Path,
    ctx: Ctx,
    publish_rc: int | str,
    publish_stdout_fallback: bool,
    plan_write_ok: str,
    publish_ok: str,
    cleanup_eligible: bool,
    result_env: dict[str, str] | None = None,
) -> None:
    result_env = result_env or {}
    rows: list[tuple[str, str]] = [
        ("PLAN_WRITE_OK", plan_write_ok),
        ("PUBLISH_OK", publish_ok),
        ("STANDALONE_HEAVY_FAILED", ctx.str_value(key="STANDALONE_HEAVY_FAILED", default="")),
        ("SESSION_ID", ctx.session_id),
        ("PUBLISH_RC", str(publish_rc)),
        ("PUBLISH_STDOUT_FALLBACK", "true" if publish_stdout_fallback else "false"),
        ("CLEANUP_ELIGIBLE", "true" if cleanup_eligible else "false"),
    ]
    rows.extend(
        (key, result_env.get(key, ""))
        for key in (
            "PUBLISH_ATTEMPT_ID", "PUBLISH_RC_SOURCE", "LATEST_PHASE",
            "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED", "RENAMED",
            "PR_URL", "RECOVERY_BRANCH",
        )
    )
    status_path = design_tmpdir / ".design-step5c-status.env"
    design_write_merge_env(
        path=status_path,
        design_tmpdir=design_tmpdir,
        rows=rows,
    )
    verified = load_bash_quoted_env(path=status_path, allow_keys=(key for key, _ in rows))
    if not verified or any(verified.get(key, "") != value for key, value in rows):
        raise OSError("step 5c status write verification failed")


def _step5c_invalidate_publish_result(*, design_tmpdir: Path) -> None:
    result_env = design_tmpdir / config.DESIGN_PUBLISH_RESULT_FILE
    if result_env.is_symlink() or (result_env.exists() and not result_env.is_file()):
        raise OSError("prior publish result is unsafe")
    if result_env.exists():
        tombstone = design_tmpdir / f"{config.DESIGN_PUBLISH_RESULT_FILE}.invalid.{os.getpid()}"
        result_env.replace(tombstone)
        tombstone.unlink()


def _step5c_copy_bounded_tail(*, source: Path, destination: Path) -> str:
    if source.is_symlink() or not source.is_file():
        return ""
    try:
        data = source.read_bytes()[-config.DESIGN_PUBLISH_TAIL_BYTE_CAP :]
        text = data.decode("utf-8", errors="replace")
        larch_io.atomic_write(path=destination, text=text, create_parent=False, nofollow=True, mode=0o600)
        return destination.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _step5c_render_publish_failure_detail(
    *, design_tmpdir: Path, publish_rc: int, rc_source: str, result_env: dict[str, str], stdout_tail: str, stderr_tail: str
) -> Path:
    lines = [
        f"exit_code={publish_rc}",
        f"rc_source={rc_source}",
        f"latest_phase={result_env.get('LATEST_PHASE', '')}",
    ]
    lines.extend(
        f"{key.lower()}={result_env.get(key, '')}"
        for key in ("PLAN_WRITE_OK", "PUBLISH_OK", "RENAMED", "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED")
    )
    traceback_line = next((line for line in stderr_tail.splitlines() if line.startswith("Traceback") or "Error:" in line), "")
    if traceback_line:
        lines.append(f"traceback={traceback_line[:512]}")
    for label, text in (("step5c_stderr", stderr_tail), ("rename_stderr", _read_phase_tail(design_tmpdir, config.DESIGN_PUBLISH_RENAME_STDERR_FILE)), ("log_publish_stderr", _read_phase_tail(design_tmpdir, config.DESIGN_PUBLISH_LOG_STDERR_FILE)), ("step5c_stdout", stdout_tail)):
        if text:
            lines.extend((f"[{label}]", text[-config.DESIGN_PUBLISH_TAIL_BYTE_CAP :]))
    detail = design_tmpdir / config.DESIGN_PUBLISH_FAILURE_DETAIL_FILE
    larch_io.atomic_write(path=detail, text="\n".join(lines) + "\n", create_parent=False, nofollow=True, mode=0o600)
    return detail


def _read_phase_tail(design_tmpdir: Path, filename: str) -> str:
    path = design_tmpdir / filename
    if path.is_symlink() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-config.DESIGN_PUBLISH_TAIL_BYTE_CAP :]


def _step5c_invoke_publish_core(publish_args: list[str]) -> int:
    from larch.design.design_publish import publish_core  # noqa: PLC0415

    try:
        return int(publish_core(publish_args))
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 5
    except BaseException:
        _core_print_exc()
        return 5


def _split_plan_body_and_trailers(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return body and final contiguous shared trailer block."""
    text = "".join(lines)
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    if not trailers.matches:
        return lines, []
    start = trailers.start_line - 1
    return lines[:start], lines[start:]


def _strip_leading_plan_header(body_lines: list[str]) -> list[str]:
    """Remove a leading ``## Plan`` heading and following blank lines from plan body."""
    idx = 0
    while idx < len(body_lines) and not body_lines[idx].strip():
        idx += 1
    if idx < len(body_lines) and re.match(r"^## Plan\s*$", body_lines[idx].rstrip("\n")):
        idx += 1
        while idx < len(body_lines) and not body_lines[idx].strip():
            idx += 1
    return body_lines[idx:]


def _read_diff_lines_sidecar(design_tmpdir: Path) -> str | None:
    path = design_tmpdir / "diff-lines.txt"
    if not path.is_file():
        return None
    try:
        token = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return token if re.fullmatch(r"\d+", token) else None


def _optional_trailer_lines_from_values_file(values_path: Path) -> list[str]:
    if not values_path.is_file():
        return []
    try:
        raw = values_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines: list[str] = []
    for raw_item in raw.splitlines():
        item = raw_item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "diff_added" and re.fullmatch(r"\d+", value):
            lines.append(f"diff_added: {value}\n")
        elif key == "diff_deleted" and re.fullmatch(r"\d+", value):
            lines.append(f"diff_deleted: {value}\n")
        elif key == "mechanical_churn" and value in {"true", "false"}:
            lines.append(f"mechanical_churn: {value}\n")
        elif key == "oversize_override" and value == config.OVERSIZE_OVERRIDE_OPERATOR:
            lines.append(f"oversize_override: {value}\n")
    return lines


def _peel_trailing_optional_trailers(body_lines: list[str]) -> tuple[list[str], list[str]]:
    idx = len(body_lines)
    peeled: list[str] = []
    while idx > 0:
        line = body_lines[idx - 1]
        stripped = line.rstrip("\n")
        if not stripped.strip():
            idx -= 1
            continue
        match = plan_grammar.match_trailer_line(stripped)
        if match is not None and match.key != "diff_lines":
            peeled.insert(0, line if line.endswith("\n") else f"{line}\n")
            idx -= 1
            continue
        break
    return body_lines[:idx], peeled


def _build_trailer_lines_from_sidecars(
    design_tmpdir: Path,
    *,
    body_lines: list[str],
) -> tuple[list[str], list[str]]:
    """Recover a canonical trailer block when plan.txt lacks a terminal diff_lines line."""
    diff_n = _read_diff_lines_sidecar(design_tmpdir)
    if diff_n is None:
        return body_lines, []
    optional = _optional_trailer_lines_from_values_file(
        design_tmpdir / ".gate-b-optional-trailer-keys.values"
    )
    trimmed_body = body_lines
    if not optional:
        trimmed_body, optional = _peel_trailing_optional_trailers(body_lines)
    return trimmed_body, [*optional, f"diff_lines: {diff_n}\n"]


def _build_acceptance_section(body_lines: list[str]) -> str:
    """Return a ## Acceptance section derived from ## Testing strategy, or a fallback."""
    testing_start = -1
    testing_level = 0
    for idx, line in enumerate(body_lines):
        m = re.match(r"(#+)\s+Testing strategy\s*$", line.rstrip("\n"), re.IGNORECASE)
        if m:
            testing_start = idx
            testing_level = len(m.group(1))
            break
    if testing_start < 0:
        return "## Acceptance\n\nSee Testing strategy in plan."
    content_lines: list[str] = []
    for line in body_lines[testing_start + 1 :]:
        heading_match = re.match(r"(#+)\s+", line.rstrip("\n"))
        if heading_match and len(heading_match.group(1)) <= testing_level:
            break
        content_lines.append(line)
    body = "".join(content_lines).strip()
    return f"## Acceptance\n\n{body}" if body else "## Acceptance\n\nSee Testing strategy in plan."


def _auto_compose_plan_md(design_tmpdir: Path) -> None:
    """Write composed-plan.md from plan.txt when the file is missing or empty.

    Removes the orchestrator ambiguity in Step 5c: the driver self-completes the
    prerequisite rather than failing closed with PUBLISH_RC=4.
    """
    composed_plan = design_tmpdir / "composed-plan.md"
    if composed_plan.is_file() and composed_plan.stat().st_size > 0:
        return
    plan_txt = design_tmpdir / "plan.txt"
    if not plan_txt.is_file() or plan_txt.stat().st_size == 0:
        _core_diagnostic(
            "**⚠ Step 5c auto-compose: plan.txt missing or empty: "
            "compose composed-plan.md manually before retrying**"
        )
        return
    try:
        raw = plan_txt.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _core_diagnostic(f"**⚠ Step 5c auto-compose: could not read plan.txt: {exc}**")
        return
    body_lines, trailer_lines = _split_plan_body_and_trailers(raw.splitlines(keepends=True))
    if not trailer_lines:
        body_lines, trailer_lines = _build_trailer_lines_from_sidecars(
            design_tmpdir, body_lines=body_lines
        )
    body_lines = _strip_leading_plan_header(body_lines)
    body_text = "".join(body_lines).rstrip()
    acceptance_section = _build_acceptance_section(body_lines)
    trailer_text = "".join(trailer_lines).rstrip("\n")
    composed = f"## Plan\n\n{body_text}\n\n{acceptance_section}\n"
    if trailer_text:
        composed += f"\n{trailer_text}\n"
    try:
        composed_plan.write_text(composed, encoding="utf-8")
    except OSError as exc:
        _core_diagnostic(f"**⚠ Step 5c auto-compose: failed to write composed-plan.md: {exc}**")
        return
    _core_diagnostic(
        "**⚠ Step 5c: composed-plan.md was absent; auto-composed from plan.txt**"
    )


def step5c_core(argv: Sequence[str]) -> tuple[int, list[str]]:
    old_environ = os.environ.copy()
    design_tmpdir: Path | None = None
    try:
        try:
            parsed = _parse_common_wrapper_args(argv)
        except ValueError as exc:
            _core_diagnostic(f"design-step5c.sh: {exc}")
            return 2, []
        env = _rehydrate_wrapper_env(parsed)
        raw_tmpdir = env.get("DESIGN_TMPDIR", "")
        if not raw_tmpdir:
            _core_diagnostic("/design Step 5c: DESIGN_TMPDIR required")
            return 1, []
        try:
            design_tmpdir = _validate_design_tmpdir_arg(raw_tmpdir)
        except _CoreUsageError as exc:
            _core_diagnostic(f"design-step5c.sh: {exc}")
            return 1, []
        os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)
        normalized_overrides = {
            config.ENV_DESIGN_TMPDIR: str(design_tmpdir),
            config.ENV_CLAUDE_PID: parsed.claude_pid or os.environ.get(config.ENV_CLAUDE_PID, ""),
        }
        logging_util.quiet_init(argv0="design-step5c.sh")
        req = _design_require_plugin_root()
        if req != 0:
            return req, []
        plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
        ctx = Ctx.from_mapping({**os.environ, **env, **normalized_overrides})
        if not (design_tmpdir / ".completed" / "step-5b").is_file():
            _core_diagnostic("**⚠ Step 5c: missing .completed/step-5b: OOS filing incomplete; repair Step 5b before publish**")
            return 1, []
        if (design_tmpdir / ".pause-requested").is_file():
            pause_rc = _call_pause_save(design_tmpdir=design_tmpdir, ctx=ctx)
            logging_util.emit_kv(key="STEP5C_STATUS", value="pause-save")
            return pause_rc, []

        _auto_compose_plan_md(design_tmpdir)

        publish_args = [
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            ctx.issue_number,
            "--session-id",
            ctx.session_id,
            "--claude-pid",
            ctx.claude_pid,
        ]
        if ctx.repo:
            publish_args.extend(["--repo", ctx.repo])
        if parsed.skip_validate:
            publish_args.append("--skip-validate")

        attempt_id = f"{os.getpid()}-{os.urandom(12).hex()}"
        try:
            _step5c_invalidate_publish_result(design_tmpdir=design_tmpdir)
        except OSError as exc:
            _core_diagnostic(f"**⚠ Step 5c: prior publish result invalidation failed: {exc}**")
            _step5c_write_status(
                design_tmpdir=design_tmpdir, ctx=ctx, publish_rc=5, publish_stdout_fallback=False,
                plan_write_ok="", publish_ok="", cleanup_eligible=False,
            )
            _step5c_stage_failed_publish_tail(design_tmpdir=design_tmpdir, plugin_root=plugin_root, publish_rc=5)
            return 1, []
        os.environ[config.ENV_LARCH_DESIGN_PUBLISH_ATTEMPT_ID] = attempt_id

        publish_fd, publish_stdout_name = tempfile.mkstemp(prefix="larch-publish-stdout.", dir=os.environ.get("TMPDIR") or None)
        os.close(publish_fd)
        publish_stdout_file = Path(publish_stdout_name)
        publish_stderr_fd, publish_stderr_name = tempfile.mkstemp(prefix="larch-publish-stderr.", dir=os.environ.get("TMPDIR") or None)
        os.close(publish_stderr_fd)
        publish_stderr_file = Path(publish_stderr_name)
        publish_rc = 5
        try:
            publish_rc = _capture_contract_stream_to_paths(
                _step5c_invoke_publish_core,
                publish_stdout_file,
                publish_stderr_file,
                publish_args,
            )

            if publish_rc == 2 or publish_rc not in {0, 1, 3, 4, 5}:
                _step5c_write_status(
                    design_tmpdir=design_tmpdir,
                    ctx=ctx,
                    publish_rc=publish_rc,
                    publish_stdout_fallback=False,
                    plan_write_ok="",
                    publish_ok="",
                    cleanup_eligible=False,
                )
                _step5c_stage_failed_publish_tail(design_tmpdir=design_tmpdir, plugin_root=plugin_root, publish_rc=publish_rc)
                failed_tail_summary_path = str(design_tmpdir / "final-summary.md")
                central_publish_ok = _step5c_try_central_failed_publish_tail(
                    design_tmpdir=design_tmpdir,
                    ctx=ctx,
                    publish_stdout_file=publish_stdout_file,
                )
                if central_publish_ok or _step5c_render_final_summary(design_tmpdir=design_tmpdir, ctx=ctx, outcome="failed-publish-tail", final_summary_path=failed_tail_summary_path):
                    _emit_final_summary_marked_from_disk(design_tmpdir=design_tmpdir, final_summary_path=failed_tail_summary_path)
                _emit_report_gate_sidecars_from_disk(design_tmpdir)
                if publish_rc == 2:
                    _core_diagnostic("**⚠ Step 5c: design-publish.sh configuration error (exit 2); aborting /design**")
                else:
                    _core_diagnostic(f"**⚠ Step 5c: design-publish.sh failed (exit {publish_rc}); aborting /design**")
                return 1, []
            if publish_rc == 5:
                stdout_tail = _step5c_copy_bounded_tail(
                    source=publish_stdout_file,
                    destination=design_tmpdir / config.DESIGN_PUBLISH_STDOUT_TAIL_FILE,
                )
                stderr_tail = _step5c_copy_bounded_tail(
                    source=publish_stderr_file,
                    destination=design_tmpdir / config.DESIGN_PUBLISH_STDERR_TAIL_FILE,
                )
                rre_rc, result_env, _stdout_fallback = _step5c_safe_publish_env(
                    design_tmpdir=design_tmpdir,
                    publish_rc=publish_rc,
                    publish_stdout_file=publish_stdout_file,
                    attempt_id=attempt_id,
                )
                if rre_rc != 0:
                    result_env = {}
                if result_env.get("PUBLISH_RC_SOURCE") not in {
                    config.DESIGN_PUBLISH_RC_SOURCE_RETURNED,
                    config.DESIGN_PUBLISH_RC_SOURCE_EXCEPTION,
                }:
                    result_env["PUBLISH_RC_SOURCE"] = (
                        config.DESIGN_PUBLISH_RC_SOURCE_EXCEPTION if "Traceback" in stderr_tail else config.DESIGN_PUBLISH_RC_SOURCE_RETURNED
                    )
                try:
                    _step5c_render_publish_failure_detail(
                        design_tmpdir=design_tmpdir, publish_rc=publish_rc,
                        rc_source=result_env["PUBLISH_RC_SOURCE"], result_env=result_env,
                        stdout_tail=stdout_tail, stderr_tail=stderr_tail,
                    )
                except OSError as exc:
                    _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design publish tail", tool="tail persistence", exit_code=1, category="Warnings", output_file=publish_stderr_file)
                    _core_diagnostic(f"**⚠ Step 5c: publish-tail diagnostic persistence failed: {exc}**")
                _step5c_write_status(
                    design_tmpdir=design_tmpdir, ctx=ctx, publish_rc=publish_rc, publish_stdout_fallback=False,
                    plan_write_ok=result_env.get("PLAN_WRITE_OK", ""), publish_ok=result_env.get("PUBLISH_OK", ""),
                    cleanup_eligible=False, result_env=result_env,
                )
                _step5c_stage_failed_publish_tail(
                    design_tmpdir=design_tmpdir, plugin_root=plugin_root, publish_rc=publish_rc, result_env=result_env
                )
                central_publish_ok = _step5c_try_central_failed_publish_tail(
                    design_tmpdir=design_tmpdir, ctx=ctx, publish_stdout_file=publish_stdout_file,
                )
                failed_tail_summary_path = str(design_tmpdir / "final-summary.md")
                if central_publish_ok or _step5c_render_final_summary(
                    design_tmpdir=design_tmpdir, ctx=ctx, outcome="failed-publish-tail",
                    final_summary_path=failed_tail_summary_path,
                ):
                    _emit_final_summary_marked_from_disk(
                        design_tmpdir=design_tmpdir, final_summary_path=failed_tail_summary_path
                    )
                _emit_report_gate_sidecars_from_disk(design_tmpdir)
                _core_diagnostic("**⚠ Step 5c: design-publish.sh failed (exit 5); aborting /design**")
                return 1, []
            if publish_rc == 3:
                _core_diagnostic("**⚠ Step 5c: design-publish.sh result-env write failed (exit 3); continuing with stdout parse**")

            rre_rc, result_env, stdout_fallback = _step5c_safe_publish_env(design_tmpdir=design_tmpdir, publish_rc=publish_rc, publish_stdout_file=publish_stdout_file)
            if rre_rc != 0:
                _core_diagnostic("**⚠ Step 5c: design-publish result env missing or unreadable; aborting /design**")
                return 1, []
            final_summary_path = result_env.get("FINAL_SUMMARY_PATH", "")
            summary_emit_path = final_summary_path or str(design_tmpdir / "final-summary.md")
            plan_write_ok = result_env.get("PLAN_WRITE_OK", "")
            publish_ok = result_env.get("PUBLISH_OK", "")
            publish_refuse_reason = result_env.get("PUBLISH_REFUSE_REASON", "")
            cleanup_eligible = (
                publish_rc != 4
                and plan_write_ok == "true"
                and ctx.str_value(key="STANDALONE_HEAVY_FAILED", default="false") != "true"
                and (not ctx.session_id or publish_ok == "true")
            )
            rows = [
                ("PUBLISH_RC", str(publish_rc)),
                ("PLAN_WRITE_OK", plan_write_ok),
                ("PUBLISH_OK", publish_ok),
                ("STANDALONE_HEAVY_FAILED", ctx.str_value(key="STANDALONE_HEAVY_FAILED", default="")),
                ("SESSION_ID", ctx.session_id),
                ("PUBLISH_STDOUT_FALLBACK", "true" if stdout_fallback else "false"),
                ("VALIDATE_STATUS", result_env.get("VALIDATE_STATUS", "")),
                ("VALIDATE_DEFECT_COUNT", result_env.get("VALIDATE_DEFECT_COUNT", "")),
                ("VALIDATE_SKIPPED_COUNT", result_env.get("VALIDATE_SKIPPED_COUNT", "")),
                ("VALIDATE_UNSAFE_TOKEN_COUNT", result_env.get("VALIDATE_UNSAFE_TOKEN_COUNT", "")),
                ("VALIDATE_MISSING_SCRIPT_COUNT", result_env.get("VALIDATE_MISSING_SCRIPT_COUNT", "")),
                ("VALIDATE_LOG_FILE", result_env.get("VALIDATE_LOG_FILE", "")),
                ("PUBLISH_REFUSE_REASON", publish_refuse_reason),
                ("ARCH_INVARIANT_ASSESSMENT_REQUIRED", result_env.get("ARCH_INVARIANT_ASSESSMENT_REQUIRED", "")),
                ("ARCH_INVARIANT_ASSESSMENT_PRESENT", result_env.get("ARCH_INVARIANT_ASSESSMENT_PRESENT", "")),
                ("ARCH_INVARIANT_ASSESSMENT_STATUS", result_env.get("ARCH_INVARIANT_ASSESSMENT_STATUS", "")),
                ("ARCH_INVARIANT_ASSESSMENT_ARTIFACT", result_env.get("ARCH_INVARIANT_ASSESSMENT_ARTIFACT", "")),
                ("ARCH_GUIDE_ASSESSMENT_REQUIRED", result_env.get("ARCH_GUIDE_ASSESSMENT_REQUIRED", "")),
                ("ARCH_GUIDE_ASSESSMENT_PRESENT", result_env.get("ARCH_GUIDE_ASSESSMENT_PRESENT", "")),
                ("ARCH_GUIDE_ASSESSMENT_STATUS", result_env.get("ARCH_GUIDE_ASSESSMENT_STATUS", "")),
                ("ARCH_GUIDE_ASSESSMENT_ARTIFACT", result_env.get("ARCH_GUIDE_ASSESSMENT_ARTIFACT", "")),
                ("FINAL_SUMMARY_PATH", final_summary_path),
                ("UPSERT_STATUS", result_env.get("UPSERT_STATUS", "")),
                ("ARCHITECTURE_SOURCE", result_env.get("ARCHITECTURE_SOURCE", "")),
                ("CLEANUP_ELIGIBLE", "true" if cleanup_eligible else "false"),
            ]
            design_write_merge_env(
                path=design_tmpdir / ".design-step5c-status.env",
                design_tmpdir=design_tmpdir,
                rows=rows,
            )
            _emit_core_kvs(rows)
            if publish_rc == 4:
                if publish_refuse_reason == "missing-invariant-assessment":
                    status_value = "missing-invariant-assessment"
                elif publish_refuse_reason == "missing-guideline-assessment":
                    status_value = "missing-guideline-assessment"
                else:
                    status_value = "validator-defects"
                logging_util.emit_kv(key="STEP5C_STATUS", value=status_value)
                _emit_report_gate_sidecars_from_disk(design_tmpdir)
                return 0, []
            if plan_write_ok == "true":
                _touch(design_tmpdir / ".completed" / "step-5c")
            outcome = "approved" if plan_write_ok == "true" else "failed-plan-write"
            if _step5c_render_final_summary(design_tmpdir=design_tmpdir, ctx=ctx, outcome=outcome, final_summary_path=summary_emit_path, plan_write_ok=plan_write_ok):
                _emit_final_summary_marked_from_disk(design_tmpdir=design_tmpdir, final_summary_path=summary_emit_path)
            _emit_report_gate_sidecars_from_disk(design_tmpdir)
            return 0, []
        finally:
            with contextlib.suppress(FileNotFoundError):
                publish_stdout_file.unlink()
            with contextlib.suppress(FileNotFoundError):
                publish_stderr_file.unlink()
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def step5c_main(argv: Sequence[str]) -> int:
    try:
        _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step5c.sh: {exc}", file=sys.stderr)
        return 2
    rc, _ = step5c_core(argv)
    return rc


STEP5C_STATUS_ALLOW_KEYS = {
    "PLAN_WRITE_OK",
    "PUBLISH_OK",
    "STANDALONE_HEAVY_FAILED",
    "SESSION_ID",
    "PUBLISH_RC",
    "PUBLISH_STDOUT_FALLBACK",
    "CLEANUP_ELIGIBLE",
    "ARCH_INVARIANT_ASSESSMENT_REQUIRED",
    "ARCH_INVARIANT_ASSESSMENT_PRESENT",
    "ARCH_INVARIANT_ASSESSMENT_STATUS",
    "ARCH_INVARIANT_ASSESSMENT_ARTIFACT",
    "ARCH_GUIDE_ASSESSMENT_REQUIRED",
    "ARCH_GUIDE_ASSESSMENT_PRESENT",
    "ARCH_GUIDE_ASSESSMENT_STATUS",
    "ARCH_GUIDE_ASSESSMENT_ARTIFACT",
}
STEP6_INFO_ICON = "\N{INFORMATION SOURCE}"
