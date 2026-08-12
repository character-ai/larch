"""Phase driver result-env helpers, terminal state, failure report, and final summary."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence

from larch import io as larch_io
from larch.core import config, logging_util, proc, rust_runtime
from larch.core.repo_roots import larch_entrypoint, repo_root_probe
from larch.git import gh
from larch.core.ctx import Ctx
from larch.issue import title_match
from larch.state import session_env as _session_env_dt

from larch.design.design_core import (
    _CoreUsageError,
    _append_execution_issue,
    _core_diagnostic,
    _core_print_exc,
    _emit_core_kvs,
    _read_env_value,
    _read_env_value_last,
    _read_env_values,
    _validate_design_tmpdir_arg,
    _append_failure,
    design_write_merge_env,
)
from larch.design.design_router import _usage
from larch.design.design_session import (
    _call_pause_save,
    _parse_common_wrapper_args,
    _quote_single,
    _rehydrate_wrapper_env,
    _valid_var_name,
    PHASE_RESULT_ENV_ALLOW_KEYS,
)
from larch.report import progress_file as _progress_file

def phase_driver_read_result_env(*, path: str | Path, allow_keys: Iterable[str]) -> list[tuple[str, str]]:
    """Read allowlisted KEY=VALUE records from a result-env file.

    Blank and malformed lines are skipped. Values containing CR or LF are
    refused, matching the shell phase-driver trust boundary.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    allow = set(allow_keys)
    text = source.read_bytes().decode("utf-8", errors="replace")
    clean_lines = [line for line in text.split("\n") if "\r" not in line]
    text = "\n".join(clean_lines)
    rows = larch_io.parse_kv(
        text,
        duplicate_policy="all",
        allowed_keys=allow,
    )
    return [(key, value) for key, values in rows.items() for value in values]


def phase_driver_write_result_env(
    *,
    path: str | Path,
    kvs: Iterable[tuple[str, str] | str],
    allow_keys: Iterable[str] | None = None,
) -> None:
    """Atomically write allowlisted KEY=VALUE records to a result-env file.

    The trust boundary mirrors the shell phase driver: symlink targets are
    refused, keys must be allowlisted shell variable names, and values may not
    contain CR/LF bytes.
    """
    allowed = set(PHASE_RESULT_ENV_ALLOW_KEYS if allow_keys is None else allow_keys)
    dest = Path(path)
    if dest.is_symlink():
        raise OSError(f"refusing to write symlink result env: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str]] = []
    for item in kvs:
        if isinstance(item, str):
            if "=" not in item:
                raise ValueError(f"result env row is missing '=': {item}")
            key, _, value = item.partition("=")
        else:
            key, value = item
        if key not in allowed or not _valid_var_name(key):
            raise ValueError(f"result env key is not allowlisted: {key}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"result env value contains newline: {key}")
        rows.append((key, value))
    larch_io.atomic_write(
        path=dest,
        text=larch_io.format_kvs(rows),
        create_parent=True,
        nofollow=True,
        mode=0o600,
    )


def clarify_failure_stage_args(
    *, design_tmpdir: Path, exit_code: str, detail_log: Path
) -> list[str]:
    """Return the shared terminal-state argv for a failed clarify loop."""
    return [
        "--design-tmpdir", str(design_tmpdir),
        "--outcome", "failed-clarify",
        "--step", "clarify",
        "--phase", "clarify-loop",
        "--site", "clarify-loop",
        "--trigger", "failed",
        "--bail-reason", "clarify-hard-halt",
        "--exit-code", exit_code,
        "--source-script", "clarify-loop",
        "--summary-outcome", "failed-clarify",
        "--failure-detail-log", str(detail_log),
    ]


def phase_driver_recreate_result_env(*, path: str | Path, design_tmpdir: str | Path) -> None:
    """Recreate a result-env file under a validated design tmpdir.

    This is the safe replacement for shell truncation when a wrapper needs an
    empty merge-input env: the destination must stay under DESIGN_TMPDIR, must
    not be a symlink, and is recreated through the atomic nofollow writer.
    """
    dest = Path(path)
    root = Path(design_tmpdir)
    if root.is_symlink() or not root.is_dir():
        raise OSError(f"design tmpdir is not a regular directory: {root}")
    resolved_root = root.resolve()
    if dest.is_symlink():
        raise OSError(f"refusing to replace symlink result env: {dest}")
    try:
        resolved_dest = dest.resolve(strict=False)
    except OSError as exc:
        raise OSError(f"result env cannot be resolved: {dest}") from exc
    if resolved_dest != resolved_root and resolved_root not in resolved_dest.parents:
        raise OSError(f"result env escapes DESIGN_TMPDIR: {dest}")
    phase_driver_write_result_env(path=dest, kvs=[])


def json_get_bool(*, path: str | Path, key: str, default: bool = False) -> bool:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        return default
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    if not isinstance(data, dict):
        return default
    typed_data: dict[str, object] = data  # type: ignore[assignment]
    value = typed_data.get(key, default)
    return value if isinstance(value, bool) else default


def json_get_bool_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review json-get-bool")
    parser.add_argument("--path", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--key", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--default", choices=("true", "false"), default="false")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    value = json_get_bool(path=ns.path, key=ns.key, default=ns.default == "true")
    print("true" if value else "false")
    return 0


def _replay_warn_error(path: Path) -> None:
    rows = larch_io.parse_kv(
        path.read_bytes().decode("utf-8", errors="replace"),
        duplicate_policy="all",
        allowed_keys={"WARN", "ERROR"},
    )
    for key, values in rows.items():
        for value in values:
            logging_util.emit_kv(key=key, value=value)


def _classify_input(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "nonregular"
    return "regular"


def _preferred_bgjob_result_input(input_path: Path) -> Path | None:
    step_by_legacy_name = {
        ".design-step4-tail-result.env": "design-step4-tail",
        ".design-step5c-status.env": "design-step5c",
        ".design-step-final-summary-result.env": "design-step-final-summary",
    }
    step = step_by_legacy_name.get(input_path.name)
    if step is None:
        return None
    candidate = input_path.parent / config.BGJOB_TMP_SUBDIR / f"{step}{config.BGJOB_RESULT_ENV_SUFFIX}"
    if _classify_input(candidate) == "regular":
        return candidate
    return None


def _resolve_read_result_env_source(input_path: Path, fallback_path: Path | None) -> tuple[Path | None, str]:
    preferred_bgjob_input = _preferred_bgjob_result_input(input_path)
    if preferred_bgjob_input is not None:
        return preferred_bgjob_input, ""
    primary_kind = _classify_input(input_path)
    if primary_kind == "regular":
        return input_path, ""
    if fallback_path is None:
        return None, ""
    warning = ""
    if primary_kind == "symlink":
        if str(input_path).endswith(".design-init-runparams-result.env"):
            warning = "**⚠ Step 0b: design-init-runparams result env is a symlink; refusing to source**"
        else:
            warning = f"WARN=read-result-env input is a symlink; refusing primary path: {input_path}"
    if fallback_path.is_symlink() or not fallback_path.is_file():
        return None, warning
    return fallback_path, warning


def _stall_args(design_tmpdir: Path) -> list[str]:
    return ["--profile", "generic", "--artifact-prefix", "design-failure", "--implement-tmpdir", str(design_tmpdir)]


def extend_publish_failure_stage_args(stage_args: list[str], values: Mapping[str, str]) -> None:
    """Append optional publish state to a terminal-stage command."""
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
        value = values.get(key, "")
        if value:
            stage_args.extend((flag, value))


def _run_stall_rust(
    *,
    verb: str,
    argv: Sequence[str],
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
) -> int:
    try:
        result = proc.run(_stall_rust_argv(verb=verb, argv=argv))
    except OSError:
        return 1
    try:
        if stdout_path is not None:
            stdout_path.write_text(result.stdout, encoding="utf-8")
        if stderr_path is not None:
            stderr_path.write_text(result.stderr, encoding="utf-8")
    except OSError:
        return 1
    return result.returncode


def _run_stall_rust_capture(*, verb: str, argv: Sequence[str]) -> proc.CommandResult:
    return proc.run(_stall_rust_argv(verb=verb, argv=argv))


def _stall_rust_argv(*, verb: str, argv: Sequence[str]) -> list[str]:
    entrypoint = str(larch_entrypoint(Path(__file__).resolve().parents[3]))
    if verb == "classify":
        return [entrypoint, "stall-recovery", "classify", *argv]
    if verb == "init-attempts":
        return [entrypoint, "stall-recovery", "init-attempts", *argv]
    if verb == "is-larch-dev-clone":
        return [entrypoint, "stall-recovery", "is-larch-dev-clone", *argv]
    if verb == "normalize-file-failure-report-env":
        return [entrypoint, "stall-recovery", "normalize-file-failure-report-env", *argv]
    if verb == "validate-terminal-state":
        return [entrypoint, "stall-recovery", "validate-terminal-state", *argv]
    if verb == "validate-token":
        return [entrypoint, "stall-recovery", "validate-token", *argv]
    if verb == "compose-report":
        return [entrypoint, "stall-recovery", "compose-report", *argv]
    if verb == "dedup-tier-a-report":
        return [entrypoint, "stall-recovery", "dedup-tier-a-report", *argv]
    if verb == "chat-print":
        return [entrypoint, "stall-recovery", "chat-print", *argv]
    if verb == "populate-sensitive-corpus":
        return [entrypoint, "stall-recovery", "populate-sensitive-corpus", *argv]
    raise ValueError(f"unsupported Rust stall-recovery command: {verb}")


def _safe_failure_detail_log(*, raw: str, design_tmpdir: Path) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw)
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise _CoreUsageError("--failure-detail-log must be under --design-tmpdir") from exc
    if resolved != design_tmpdir and design_tmpdir not in resolved.parents:
        raise _CoreUsageError("--failure-detail-log must be under --design-tmpdir")
    if candidate.is_symlink():
        raise _CoreUsageError("--failure-detail-log must not be a symlink")
    if not candidate.is_file():
        raise _CoreUsageError("--failure-detail-log must be a regular file")
    if not os.access(candidate, os.R_OK):
        raise _CoreUsageError("--failure-detail-log must be readable")
    return candidate


def _safe_evidence_ref(raw: str) -> None:
    if not raw:
        return
    has_control = "\n" in raw or "\r" in raw
    has_unsafe_prefix = raw.startswith(("http://", "https://", "/"))
    has_unsafe_body = ".." in raw or " " in raw or "`" in raw
    if has_control or has_unsafe_prefix or has_unsafe_body:
        raise _CoreUsageError("--evidence-ref is not a safe token")


def stage_terminal_state_core(argv: Sequence[str]) -> tuple[int, list[str]]:
    parser = argparse.ArgumentParser(prog="design stage-terminal-state", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--trigger", required=True)
    parser.add_argument("--bail-reason", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--source-script", required=True)
    parser.add_argument("--failure-detail-log", default="")
    parser.add_argument("--root-cause-hint", default="")
    parser.add_argument("--summary-outcome", default="")
    parser.add_argument("--evidence-ref", default="")
    parser.add_argument("--publish-attempt-id", default="")
    parser.add_argument("--publish-rc-source", default="")
    parser.add_argument("--latest-phase", default="")
    parser.add_argument("--plan-write-ok", default="")
    parser.add_argument("--publish-ok", default="")
    parser.add_argument("--renamed", default="")
    parser.add_argument("--log-publish-attempted", default="")
    parser.add_argument("--log-publish-completed", default="")
    parser.add_argument("--designed-admission-ready", default="")
    parser.add_argument("--pr-url", default="")
    parser.add_argument("--recovery-branch", default="")
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return 2, []
    if extra:
        _core_diagnostic(f"design-stage-terminal-state.sh: unknown option: {extra[0]}")
        return 2, []
    try:
        design_tmpdir = _validate_design_tmpdir_arg(ns.design_tmpdir)
        required = {
            "outcome": ns.outcome,
            "step": ns.step,
            "phase": ns.phase,
            "site": ns.site,
            "trigger": ns.trigger,
            "bail": ns.bail_reason,
            "source-script": ns.source_script,
        }
        for kind, value in required.items():
            if not value:
                raise _CoreUsageError(f"{kind} is required")
            rc = _run_stall_rust(
                verb="validate-token",
                argv=[
                    *_stall_args(design_tmpdir),
                    "--token-kind",
                    kind,
                    "--value",
                    value,
                ],
            )
            if rc != 0:
                raise _CoreUsageError(f"{kind} is not a valid token: {value}")
        for kind, value in (("root-cause", ns.root_cause_hint), ("outcome", ns.summary_outcome)):
            if not value:
                continue
            rc = _run_stall_rust(
                verb="validate-token",
                argv=[
                    *_stall_args(design_tmpdir),
                    "--token-kind",
                    kind,
                    "--value",
                    value,
                ],
            )
            if rc != 0:
                raise _CoreUsageError(f"{kind} is not a valid token: {value}")
        if ns.exit_code != "unknown" and not ns.exit_code.isdigit():
            raise _CoreUsageError("--exit-code must be an integer or unknown")
        _safe_failure_detail_log(raw=ns.failure_detail_log, design_tmpdir=design_tmpdir)
        _safe_evidence_ref(ns.evidence_ref)
        state_file = design_tmpdir / "design-failure-terminal-state.env"
        if state_file.exists() or state_file.is_symlink():
            if state_file.is_symlink() or not state_file.is_file():
                raise _CoreUsageError("existing terminal state is unsafe")
            old = _read_env_values(path=state_file, defaults={"FAILURE_OUTCOME": "", "SITE": "", "TRIGGER": ""})
            if old["FAILURE_OUTCOME"] != ns.outcome or old["SITE"] != ns.site or old["TRIGGER"] != ns.trigger:
                rows = [("STAGED", "false"), ("PRESERVED", "true"), ("TERMINAL_STATE_FILE", str(state_file))]
                _emit_core_kvs(rows)
                return 0, [f"{k}={v}" for k, v in rows]
        candidate = design_tmpdir / f"design-failure-terminal-state.env.candidate.{os.getpid()}"
        lines = [
            "DESIGN_FAILURE_VERSION=1",
            "DESIGN_FAILURE_KIND=terminal",
            f"FAILURE_OUTCOME={ns.outcome}",
            f"STALL_STEP={ns.step}",
            f"PHASE={ns.phase}",
            f"SITE={ns.site}",
            f"TRIGGER={ns.trigger}",
            f"BAIL_REASON={ns.bail_reason}",
            f"EXIT_CODE={ns.exit_code}",
            f"FAILURE_DETAIL_LOG={ns.failure_detail_log}",
            f"SOURCE_SCRIPT={ns.source_script}",
        ]
        if ns.root_cause_hint:
            lines.append(f"ROOT_CAUSE_HINT={ns.root_cause_hint}")
        if ns.summary_outcome:
            lines.append(f"SUMMARY_OUTCOME={ns.summary_outcome}")
        extras = {
            "PUBLISH_ATTEMPT_ID": ns.publish_attempt_id,
            "PUBLISH_RC_SOURCE": ns.publish_rc_source,
            "LATEST_PHASE": ns.latest_phase,
            "PLAN_WRITE_OK": ns.plan_write_ok,
            "PUBLISH_OK": ns.publish_ok,
            "RENAMED": ns.renamed,
            "LOG_PUBLISH_ATTEMPTED": ns.log_publish_attempted,
            "LOG_PUBLISH_COMPLETED": ns.log_publish_completed,
            "DESIGNED_ADMISSION_READY": ns.designed_admission_ready,
            "PR_URL": ns.pr_url,
            "RECOVERY_BRANCH": ns.recovery_branch,
        }
        for key, value in extras.items():
            if value:
                lines.append(f"{key}={value}")
        lines.append(f"OCCURRED_AT={datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if ns.evidence_ref:
            lines.append(f"EVIDENCE_REF={ns.evidence_ref}")
        candidate.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = _run_stall_rust(
            verb="validate-terminal-state",
            argv=[
                *_stall_args(design_tmpdir),
                "--primary-state-file",
                str(candidate),
            ],
        )
        if rc != 0:
            with contextlib.suppress(FileNotFoundError):
                candidate.unlink()
            raise _CoreUsageError("candidate terminal state failed validation")
        candidate.replace(state_file)
        rows = [("STAGED", "true"), ("TERMINAL_STATE_FILE", str(state_file))]
        _emit_core_kvs(rows)
        return 0, [f"{k}={v}" for k, v in rows]
    except _CoreUsageError as exc:
        _core_diagnostic(f"design-stage-terminal-state.sh: {exc}")
        return 2, []


def _emit_skip(reason: str) -> None:
    logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_DECISION", value="skip")
    logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_REASON", value=reason)


def _resolve_working_tree_root(design_tmpdir: Path) -> str:
    for value in (os.environ.get("CLAUDE_PROJECT_DIR", ""), os.environ.get("REPO_ROOT", "")):
        if value:
            return value
    source_env = design_tmpdir / "source-env.sh"
    root = _read_env_value(path=source_env, key="REPO_ROOT", default="")
    if root:
        return root
    proc_out = repo_root_probe(run=lambda argv: subprocess.run(
        argv, capture_output=True, text=True, check=False
    ))
    return proc_out.stdout.strip() if proc_out.returncode == 0 else ""


def _tier_a_forked(design_tmpdir: Path) -> bool:
    for path in (design_tmpdir / "ship-pr-state.sh", design_tmpdir / "finalize-state.sh", design_tmpdir / "source-env.sh"):
        value = _read_env_value(path=path, key="FORKED_TARGET", default="")
        if value:
            return value in {"true", "1", "yes", "TRUE", "True"}
    return False


def _tier_a_eligible(design_tmpdir: Path) -> bool:
    if _tier_a_forked(design_tmpdir):
        return False
    root = _resolve_working_tree_root(design_tmpdir)
    if not root:
        return False
    result = _run_stall_rust_capture(
        verb="is-larch-dev-clone",
        argv=[*_stall_args(design_tmpdir), "--working-tree-root", root],
    )
    return result.returncode == 0 and "LARCH_DEV_CLONE=true" in result.stdout.splitlines()


def _copy_if_file(*, source: Path, dest: Path) -> None:
    if source.is_file() and not source.is_symlink():
        shutil.copyfile(source, dest)


def _ledger_row_has_escalation_evidence(row: str) -> bool:
    values = larch_io.parse_kv("\n".join(row.split("\t")))
    site = values.get("site", "")
    trigger = values.get("trigger", "")
    if not site or not trigger:
        return False
    if site != "step3-review":
        return True
    return trigger in config.STEP3_ESCALATION_FAILURE_STATUSES


def _ledger_file_has_escalation_evidence(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    return any(_ledger_row_has_escalation_evidence(row) for row in rows)


_RECONCILE_PUBLISH_TAIL_MARKER = "<!-- larch-reconcile:failed-publish-tail -->"


def _resolve_report_repo(*, url: str, fallback: str) -> str:
    match = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/", url or "")
    return match.group(1) if match else fallback


def _salvage_success_proven(design_tmpdir: Path) -> bool:
    """Return True only when local evidence proves the salvage completed.

    Gates reconciliation on the current publish result env recording that the
    plan wrote, the tracking issue was renamed to [DESIGNED], and the run log
    published. Missing, stale, or unproven state returns False so the prior
    report stays open for operator review instead of being mis-closed.
    """
    return _validated_salvage_publish_result(
        design_tmpdir=design_tmpdir,
        path=design_tmpdir / config.DESIGN_PUBLISH_RESULT_FILE,
    ) is not None


def _validated_publish_state(*, design_tmpdir: Path, path: Path) -> dict[str, str] | None:
    if path.is_symlink() or not path.is_file():
        return None
    try:
        resolved_root = design_tmpdir.resolve(strict=False)
        resolved_path = path.resolve(strict=False)
    except OSError:
        return None
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        if not raw_line or raw_line.startswith("#"):
            continue
        if "=" not in raw_line:
            return None
        key, _, value = raw_line.partition("=")
        if key in values:
            return None
        values[key] = value
    return values


def _validated_salvage_publish_result(*, design_tmpdir: Path, path: Path) -> dict[str, str] | None:
    values = _validated_publish_state(design_tmpdir=design_tmpdir, path=path)
    if values is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]{8,128}", values.get("PUBLISH_ATTEMPT_ID", "")):
        return None
    if values.get("PUBLISH_RC_SOURCE") not in {"returned", "exception"}:
        return None
    if not (
        values.get("PLAN_WRITE_OK") == "true"
        and values.get("RENAMED") == "true"
        and values.get("LOG_PUBLISH_COMPLETED") == "true"
    ):
        return None
    return values


def _reconcile_post_recovery_comment(*, design_tmpdir: Path, report_issue: str, repo: str) -> tuple[bool, str]:
    """Post a marker-keyed recovery comment and close the prior report issue.

    Returns (ok, detail). Kept as one seam so tests can fake the GitHub mutation
    without exercising ``gh``. The comment body uses only fixed safe tokens and
    is still run through the redaction filter before egress.
    """
    source_env = design_tmpdir / "source-env.sh"
    ctx = source_env if source_env.is_file() else None
    run_id = _read_env_value(path=source_env, key="LARCH_RUN_ID", default="")
    authorized, _ = _session_env_dt.check_live_mutation_auth(context_file=ctx, operator_mode=False, run_id=run_id, trusted_root=design_tmpdir)
    if not authorized:
        return False, "reconcile-unauthorized"
    plugin_root = Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, Path(__file__).resolve().parents[3]))
    body = design_tmpdir / "design-failure-reconcile-comment.body.md"
    redacted = design_tmpdir / "design-failure-reconcile-comment.redacted.md"
    body.write_text(
        f"{_RECONCILE_PUBLISH_TAIL_MARKER}\n\n"
        "The /design run that filed this terminal report later completed its "
        "remaining publish work: the plan was published, the tracking issue was "
        "renamed to [DESIGNED], and the run log was published. Closing this "
        "auto-filed report as recovered.\n",
        encoding="utf-8",
    )
    redact_cmd = ["python3", str(plugin_root / "python" / "cli.py"), "redact", "secrets"]
    try:
        with body.open("rb") as stdin, redacted.open("wb") as stdout:
            redact_rc = subprocess.run(redact_cmd, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, check=False).returncode  # lint-subprocess-via-runner: ok redact-cli pipes stdin/stdout to open file handles
    except OSError as exc:
        return False, f"redact-secrets failed: {exc}"
    if redact_rc != 0 or not redacted.is_file() or redacted.stat().st_size == 0:
        return False, "redact-secrets failed"
    comment_sent = design_tmpdir / "design-failure-reconcile-comment.sent"
    runner = proc.ProcRunner()
    if not comment_sent.is_file():
        body_text = redacted.read_text(encoding="utf-8", errors="replace")
        comment_result = gh.issue_comment(runner, report_issue, body_text, repo=repo)
        comment_rc = comment_result.returncode
        if comment_rc != 0:
            return False, "gh issue comment failed"
        comment_sent.touch()
    close_result = gh.issue_close(runner, report_issue, repo=repo or None)
    if close_result.returncode != 0:
        return False, "gh issue close failed"
    view = gh.issue_view_field_read(runner, report_issue, "state", repo=repo or None)
    if view.returncode != 0 or '"CLOSED"' not in (view.stdout or ""):
        return False, "gh issue close verification failed"
    comment_sent.unlink(missing_ok=True)
    return True, "reconciled"


def _reconcile_failed_publish_tail_report(
    *, design_tmpdir: Path, terminal_sentinel: Path, outcome: str, repo: str,
) -> bool:
    """Reconcile a prior failed-publish-tail terminal report after a salvage.

    Runs only on an approved outcome when a prior failed-publish-tail report was
    newly filed from the same DESIGN_TMPDIR and validated local evidence proves
    the salvage completed. Marker-keyed and idempotent via a durable sentinel.
    On any failure the report stays open and a bounded execution issue records
    the reason. Returns True when a reconciliation action was taken this call so
    the caller stops normal reporting; False to fall through to normal handling.
    """
    if outcome not in {"approved", "approved-partition"}:
        return False
    if not terminal_sentinel.is_file():
        return False
    reconcile_sentinel = design_tmpdir / "design-failure-reconcile-report.env"
    if _read_env_value(path=reconcile_sentinel, key="STATUS", default="") == "reconciled":
        return False
    if _read_env_value(path=terminal_sentinel, key="STALL_RECOVERY_REPORT_STATUS", default="") != "filed":
        return False
    report_issue = _read_env_value(path=terminal_sentinel, key="STALL_RECOVERY_REPORT_ISSUE_NUMBER", default="")
    if not (report_issue and report_issue.isdigit()):
        return False
    terminal_state = design_tmpdir / "design-failure-terminal-state.env"
    terminal_values = _validated_publish_state(design_tmpdir=design_tmpdir, path=terminal_state)
    if terminal_values is None or (
        terminal_values.get("TRIGGER") != "publish-tail-failed"
        and terminal_values.get("FAILURE_OUTCOME") != "failed-publish-tail"
    ):
        return False
    if not _salvage_success_proven(design_tmpdir):
        return False
    plugin_root = Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, Path(__file__).resolve().parents[3]))
    report_repo = _resolve_report_repo(
        url=_read_env_value(path=terminal_sentinel, key="STALL_RECOVERY_REPORT_ISSUE_URL", default=""),
        fallback=repo,
    )
    ok, detail = _reconcile_post_recovery_comment(design_tmpdir=design_tmpdir, report_issue=report_issue, repo=report_repo)
    status = "reconciled" if ok else "reconcile-failed"
    reconcile_sentinel.write_text(
        f"DESIGN_FAILURE_RECONCILE_REPORT=true\nSTATUS={status}\nREPORT_ISSUE={report_issue}\n{detail}\n",
        encoding="utf-8",
    )
    if ok:
        logging_util.emit_kv(key="DESIGN_FAILURE_RECONCILE_STATUS", value="reconciled")
        logging_util.emit_kv(key="DESIGN_FAILURE_RECONCILE_REPORT_ISSUE", value=report_issue)
        _core_diagnostic(f"**\N{INFORMATION SOURCE} /design: reconciled prior failed-publish-tail report #{report_issue} after salvage.**")
    else:
        audit = design_tmpdir / "design-failure-reconcile-audit.log"
        audit.write_text(detail + "\n", encoding="utf-8")
        _append_failure(
            plugin_root=plugin_root, design_tmpdir=design_tmpdir,
            site="design failure reconcile", tool="gh issue", exit_code=1,
            category="Warnings", output_file=audit,
        )
        _append_execution_issue(
            design_tmpdir=design_tmpdir,
            message=f"failed-publish-tail report #{report_issue} reconcile failed: {detail}; left open for operator review",
        )
        _core_diagnostic(f"**⚠ /design: failed-publish-tail report #{report_issue} reconcile failed ({detail}); left open.**")
    return True


def failure_report_core(argv: Sequence[str]) -> tuple[int, list[str]]:
    parser = argparse.ArgumentParser(prog="design failure-report", add_help=False)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--issue", default="")
    parser.add_argument("--run-id", default="")
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return 2, []
    if extra:
        _core_diagnostic(f"design-failure-report.sh: unknown option: {extra[0]}")
        return 2, []
    try:
        design_tmpdir = _validate_design_tmpdir_arg(ns.design_tmpdir)
    except _CoreUsageError as exc:
        _core_diagnostic(f"design-failure-report.sh: {exc}")
        return 2, []
    outcome = ns.outcome
    terminal_state = design_tmpdir / "design-failure-terminal-state.env"
    class_file = design_tmpdir / "design-failure-classification.env"
    attempts_file = design_tmpdir / "design-failure-attempts.env"
    ledger = design_tmpdir / "design-failure-escalation-ledger.tsv"
    fallback = design_tmpdir / "design-failure-escalation-fallback.tsv"
    marker = design_tmpdir / "design-failure-escalation-record-failure.env"
    root_file = design_tmpdir / "design-failure-root-cause.md"
    bounded_root_file = design_tmpdir / "design-failure-bounded-root-cause.md"
    sensitive_file = design_tmpdir / "design-failure-sensitive-corpus.env"
    issue_input = design_tmpdir / "design-failure-issue-input.md"
    chat_print = design_tmpdir / "design-failure-chat-print.md"
    operator_chat = design_tmpdir / "design-failure-operator-action-chat.md"
    terminal_sentinel = design_tmpdir / "design-failure-terminal-report.env"
    escalation_sentinel = design_tmpdir / "design-failure-escalation-success.env"
    operator_sentinel = design_tmpdir / "design-failure-operator-action.env"
    compose_env = design_tmpdir / "design-failure-compose.env"

    def compose_env_key(*, key: str, default: str = "") -> str:
        if key == "STALL_RECOVERY_REPORT_STATUS":
            return _read_env_value_last(path=compose_env, key=key, default=default)
        return _read_env_value(path=compose_env, key=key, default=default)

    def helper_common() -> list[str]:
        return _stall_args(design_tmpdir)

    def state_overrides() -> list[str]:
        out = ["--primary-state-file", str(terminal_state), "--session-env-file", str(design_tmpdir / "source-env.sh")]
        finalize = design_tmpdir / "finalize-state.sh"
        if finalize.is_file():
            out.extend(["--finalize-state-file", str(finalize)])
        return out

    def append_run_log_audit(reason: str) -> None:
        detail = design_tmpdir / "design-failure-audit.log"
        detail.write_text(f"design failure report audit: {reason}\n", encoding="utf-8")
        _append_failure(plugin_root=Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3])), design_tmpdir=design_tmpdir, site="design failure report", tool="design-failure-report.sh", exit_code=0, category="Warnings", output_file=detail)

    def write_operator_action_audit(reason: str) -> None:
        operator_sentinel.write_text(f"DESIGN_FAILURE_OPERATOR_ACTION=true\nREASON={reason}\nOUTCOME={outcome}\n", encoding="utf-8")
        operator_chat.write_text(
            f"**\N{INFORMATION SOURCE} /design auto-report skipped:** operator action or cancellation outcome `{outcome}`.\n\n"
            "No public larch bug was filed. The skip was recorded in the run log.\n",
            encoding="utf-8",
        )
        append_run_log_audit(f"operator-action:{reason}")

    def write_fallback_chat(reason: str) -> None:
        chat_print.write_text(
            f"### {title_match.BUG_PREFIX} /design report fallback required\n\n"
            "The /design failure reporter could not safely file an issue.\n\n"
            "| Field | Value |\n|---|---|\n"
            f"| Outcome | `{outcome}` |\n"
            f"| Reason | `{reason}` |\n\n"
            "Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.\n",
            encoding="utf-8",
        )
        logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_DECISION", value="fallback-print-required")
        logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_REASON", value=reason)
        logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_ARTIFACT", value=str(chat_print))

    def report_surface() -> str:
        return "issue-input" if _tier_a_eligible(design_tmpdir) else "chat-print"

    def report_output_file(surface: str) -> Path:
        return issue_input if surface == "issue-input" else chat_print

    def populate_sensitive(*, class_path: Path | None = class_file, attempts_path: Path = attempts_file) -> bool:
        actual_class = class_path or class_file
        if not actual_class.is_file():
            actual_class = design_tmpdir / "design-failure-classification.seed.env"
            actual_class.write_text("", encoding="utf-8")
        return _run_stall_rust(
            verb="populate-sensitive-corpus",
            argv=[
                *helper_common(),
                "--sensitive-corpus-file",
                str(sensitive_file),
                "--classification-file",
                str(actual_class),
                "--attempts-file",
                str(attempts_path),
                "--escalation-ledger-file",
                str(ledger),
                "--escalation-fallback-file",
                str(fallback),
                "--record-failure-marker",
                str(marker),
            ],
            stdout_path=design_tmpdir / "design-failure-populate-sensitive.stdout.log",
            stderr_path=design_tmpdir / "design-failure-populate-sensitive.stderr.log",
        ) == 0

    def panel_failure_evidence_present() -> bool:
        if terminal_state.is_file() and not terminal_state.is_symlink():
            text = terminal_state.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^(TRIGGER|BAIL_REASON)=(panel-failed|panel-init-failed)$", text, re.MULTILINE):
                return True
        for path in (ledger, fallback, marker, design_tmpdir / "execution-issues.md"):
            if path.is_file() and re.search(r"panel-failed|panel-init-failed", path.read_text(encoding="utf-8", errors="replace")):
                return True
        return False

    def escalation_evidence_present() -> bool:
        if _ledger_file_has_escalation_evidence(ledger):
            return True
        if _ledger_file_has_escalation_evidence(fallback):
            return True
        if marker.stat().st_size if marker.exists() else 0:
            return True
        ex = design_tmpdir / "execution-issues.md"
        return ex.is_file() and re.search(r"^#{2,3}\s+Tool Failure: record-escalation(\s|$)", ex.read_text(encoding="utf-8", errors="replace"), re.MULTILINE) is not None

    def safe_root_summary_from_state() -> str:
        values = _read_env_values(path=terminal_state, defaults={"SITE": "unknown", "TRIGGER": "unknown", "FAILURE_OUTCOME": outcome})
        return f"{values['FAILURE_OUTCOME']} at {values['SITE']} via {values['TRIGGER']}\n"

    def prepare_root_cause(kind: str) -> None:
        verdict = "larch-defect"
        if kind == "terminal":
            hint = _read_env_value(path=terminal_state, key="ROOT_CAUSE_HINT", default="")
            if hint in {"larch-defect", "environment", "operator-action"}:
                verdict = hint
            summary = safe_root_summary_from_state().rstrip("\n")
        else:
            summary = "design escalation reached main-agent recovery"
        root_file.write_text(
            f"verdict={verdict}\nconfidence=medium\nsummary={summary}\n\n"
            "The reporter used bounded /design state tokens and local ledger evidence only.\n",
            encoding="utf-8",
        )
        shutil.copyfile(root_file, bounded_root_file)
        populate_sensitive()

    def file_tier_a_after_compose(body_file: Path) -> None:
        if compose_env_key(key="STALL_RECOVERY_REPORT_STATUS", default=""):
            return

        def append_env_file(source: Path) -> None:
            with compose_env.open("a", encoding="utf-8") as dest:
                dest.write(source.read_text(encoding="utf-8", errors="replace"))

        def append_fallback(reason: str) -> None:
            with compose_env.open("a", encoding="utf-8") as dest:
                dest.write("STALL_RECOVERY_REPORT_STATUS=fallback-print-required\n")
                dest.write(f"STALL_RECOVERY_REPORT_FALLBACK_REASON={reason}\n")

        def reason_with_status(reason: str, status: str) -> str:
            clean = re.sub(r"[^A-Za-z0-9_.:/+-]+", "-", status).strip("-")[:80]
            return f"{reason}:{clean}" if clean else reason

        def file_issue_after_dedup() -> str:
            repo = ns.repo
            if not repo:
                repo = gh.resolve_repo(proc) or ""
            fallback_reason = ""
            if not repo:
                fallback_reason = "tier-a-current-repo-unresolved"
            else:
                helper = (
                    Path(os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, Path(__file__).resolve().parents[3]))
                    / "scripts"
                    / "file-failure-report-cross-repo.sh"
                )
                if not helper.is_file():
                    fallback_reason = "tier-a-file-helper-missing"
                else:
                    helper_out = design_tmpdir / "design-failure-tier-a-file.env"
                    try:
                        with (
                            helper_out.open("w", encoding="utf-8") as stdout_handle,
                            (
                                design_tmpdir / "design-failure-tier-a-file.stderr.log"
                            ).open("w", encoding="utf-8") as stderr_handle,
                        ):
                            run_rc = subprocess.run(  # lint-subprocess-via-runner: ok tier-a file helper streams stdout/stderr to open sidecar log handles instead of captured pipes
                                [
                                    str(helper),
                                    "--repo",
                                    repo,
                                    "--body-file",
                                    str(body_file),
                                    "--title",
                                    "/design terminal failure",
                                    "--publication-tier",
                                    "tier-a",
                                    "--mutation-context",
                                    str(_ctx or source_env),
                                    "--run-id",
                                    str(_run_id),
                                    "--trusted-root",
                                    str(design_tmpdir),
                                ],
                                stdout=stdout_handle,
                                stderr=stderr_handle,
                                check=False,
                            ).returncode
                    except OSError:
                        run_rc = 1
                    if run_rc != 0:
                        fallback_reason = "tier-a-file-helper-failed"
                    else:
                        file_norm = design_tmpdir / "design-failure-tier-a-file.normalized.env"
                        if (
                            _run_stall_rust(
                                verb="normalize-file-failure-report-env",
                                argv=[
                                    *helper_common(),
                                    "--file-failure-report-env",
                                    str(helper_out),
                                ],
                                stdout_path=file_norm,
                            )
                            == 0
                        ):
                            append_env_file(file_norm)
                        else:
                            fallback_reason = "tier-a-normalize-failed"
            return fallback_reason

        source_env = design_tmpdir / "source-env.sh"
        _ctx = source_env if source_env.is_file() else None
        _run_id = _read_env_value(path=source_env, key="LARCH_RUN_ID", default="")
        _authorized, _ = _session_env_dt.check_live_mutation_auth(context_file=_ctx, operator_mode=False, run_id=_run_id, trusted_root=design_tmpdir)
        if not _authorized:
            append_fallback(f"{config.LIVE_MUTATION_REFUSAL_REASON}:reporter-unauthorized")
            return
        dedup_argv = [*helper_common(), "--body-file", str(body_file)]
        if _ctx is not None:
            dedup_argv.extend(["--context-file", str(_ctx)])
        dedup_env = design_tmpdir / "design-failure-tier-a-dedup.env"
        fallback_reason = ""
        if _run_stall_rust(
            verb="dedup-tier-a-report",
            argv=dedup_argv,
            stdout_path=dedup_env,
            stderr_path=design_tmpdir / "design-failure-tier-a-dedup.stderr.log",
        ) != 0:
            fallback_reason = "tier-a-dedup-helper-failed"
        else:
            status = _read_env_value(path=dedup_env, key="STALL_RECOVERY_REPORT_STATUS", default="")
            if status in {"dedup-comment", "dry-run", "fallback-print-required", "filed", "printed"}:
                append_env_file(dedup_env)
                return
            if status in {"no-match", "lookup-failed-open"}:
                fallback_reason = file_issue_after_dedup()
            else:
                fallback_reason = reason_with_status("tier-a-dedup-status-unexpected", status)
        if fallback_reason:
            append_fallback(fallback_reason)
            return

    def handle_compose_outcome(
        *,
        kind: str,
        decision: str,
        sentinel: Path,
        artifact_key: str,
        last_surface: str,
        last_output: Path,
    ) -> None:
        status = compose_env_key(key="STALL_RECOVERY_REPORT_STATUS", default="")
        last_output_nonempty = last_output.is_file() and last_output.stat().st_size > 0
        retry_evidence_present = panel_failure_evidence_present() or (
            kind == "escalation-success" and escalation_evidence_present()
        )
        if not status and retry_evidence_present and last_output_nonempty:
            if last_surface == "issue-input":
                file_tier_a_after_compose(last_output)
                status = compose_env_key(key="STALL_RECOVERY_REPORT_STATUS", default="")
            if not status:
                write_fallback_chat("compose-status-missing")
                return
        if status == "skipped_operator_action":
            write_operator_action_audit(f"compose-{kind}")
            logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_DECISION", value="operator-action-skip")
            logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_ARTIFACT", value=str(operator_chat))
            return
        if status == "fallback-print-required":
            write_fallback_chat(compose_env_key(key="STALL_RECOVERY_REPORT_FALLBACK_REASON", default=f"compose-{kind}"))
            return
        if status in {"filed", "dry-run", "dedup-comment", "no-match", "lookup-failed-open", "printed"}:
            _copy_if_file(source=compose_env, dest=sentinel)
            logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_DECISION", value=decision)
            logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_ENV", value=str(sentinel))
            artifact = compose_env_key(key=artifact_key, default="")
            if artifact:
                logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_ARTIFACT", value=artifact)
            return
        write_fallback_chat("compose-status-missing" if not status else f"compose-status-{status}")

    if _reconcile_failed_publish_tail_report(design_tmpdir=design_tmpdir, terminal_sentinel=terminal_sentinel, outcome=outcome, repo=ns.repo):
        return 0, []
    if terminal_sentinel.exists():
        _emit_skip("terminal-sentinel-present")
        return 0, []
    if escalation_sentinel.exists():
        _emit_skip("escalation-sentinel-present")
        return 0, []
    if outcome.startswith("cancelled-"):
        write_operator_action_audit("cancelled-outcome")
        logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_DECISION", value="operator-action-skip")
        logging_util.emit_kv(key="DESIGN_FAILURE_REPORT_ARTIFACT", value=str(operator_chat))
        return 0, []
    if outcome in {"failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify", "failed-judge-panel", "failed-publish-tail"}:
        if not terminal_state.exists():
            write_fallback_chat("missing-terminal-state")
            return 0, []
        if _run_stall_rust(
            verb="validate-terminal-state",
            argv=[*helper_common(), "--primary-state-file", str(terminal_state)],
            stderr_path=design_tmpdir / "design-failure-validate-terminal-state.stderr.log",
        ) != 0:
            append_run_log_audit("invalid-terminal-state")
            write_fallback_chat("invalid-terminal-state")
            return 0, []
        state = _read_env_values(path=terminal_state, defaults={"FAILURE_OUTCOME": "", "SUMMARY_OUTCOME": ""})
        if state["FAILURE_OUTCOME"] and state["FAILURE_OUTCOME"] != outcome:
            append_run_log_audit("terminal-state-outcome-mismatch")
            write_fallback_chat("terminal-state-outcome-mismatch")
            return 0, []
        if state["SUMMARY_OUTCOME"] and state["SUMMARY_OUTCOME"] != outcome:
            append_run_log_audit("terminal-state-summary-mismatch")
            write_fallback_chat("terminal-state-summary-mismatch")
            return 0, []
        prepare_root_cause("terminal")
        _run_stall_rust(verb="init-attempts", argv=[*helper_common(), "--attempts-file", str(attempts_file)])
        classify_out = design_tmpdir / "design-failure-classify.env"
        _run_stall_rust(verb="classify", argv=[*helper_common(), *state_overrides()], stdout_path=classify_out)
        with contextlib.suppress(OSError):
            shutil.copyfile(classify_out, class_file)
        surface = report_surface()
        output = report_output_file(surface)
        if not populate_sensitive(class_path=class_file, attempts_path=attempts_file):
            append_run_log_audit("populate-sensitive-corpus-failed")
            write_fallback_chat("populate-sensitive-corpus-failed")
            return 0, []
        rc = _run_stall_rust(
            verb="compose-report",
            argv=[
                *helper_common(),
                *state_overrides(),
                "--report-kind",
                "terminal-failure",
                "--surface",
                surface,
                "--classification-file",
                str(class_file),
                "--attempts-file",
                str(attempts_file),
                "--root-cause-file",
                str(root_file),
                "--bounded-root-cause-file",
                str(bounded_root_file),
                "--sensitive-corpus-file",
                str(sensitive_file),
                "--output-file",
                str(output),
            ],
            stdout_path=compose_env,
            stderr_path=design_tmpdir / "design-failure-compose.stderr.log",
        )
        if rc != 0:
            append_run_log_audit("terminal-compose-failed")
            write_fallback_chat("terminal-compose-failed")
            return 0, []
        populate_sensitive(class_path=class_file, attempts_path=attempts_file)
        if surface == "issue-input":
            file_tier_a_after_compose(output)
        handle_compose_outcome(kind="terminal-failure", decision="terminal-failure", sentinel=terminal_sentinel, artifact_key="STALL_RECOVERY_REPORT_ARTIFACT", last_surface=surface, last_output=output)
        return 0, []
    if outcome not in {"approved", "approved-partition"}:
        _emit_skip("outcome-not-success-allowlist")
        return 0, []
    if operator_sentinel.exists():
        if not operator_chat.stat().st_size if operator_chat.exists() else True:
            write_operator_action_audit("operator-sentinel-present")
        _emit_skip("operator-action")
        return 0, []
    if not escalation_evidence_present():
        _emit_skip("no-escalation-evidence")
        return 0, []
    prepare_root_cause("escalation")
    _run_stall_rust(verb="init-attempts", argv=[*helper_common(), "--attempts-file", str(attempts_file)])
    surface = report_surface()
    output = report_output_file(surface)
    if not populate_sensitive(class_path=None, attempts_path=attempts_file):
        append_run_log_audit("populate-sensitive-corpus-failed")
        write_fallback_chat("populate-sensitive-corpus-failed")
        return 0, []
    rc = _run_stall_rust(
        verb="compose-report",
        argv=[
            *helper_common(),
            "--report-kind",
            "escalation-success",
            "--surface",
            surface,
            "--attempts-file",
            str(attempts_file),
            "--escalation-ledger-file",
            str(ledger),
            "--escalation-fallback-file",
            str(fallback),
            "--record-failure-marker",
            str(marker),
            "--root-cause-file",
            str(root_file),
            "--bounded-root-cause-file",
            str(bounded_root_file),
            "--sensitive-corpus-file",
            str(sensitive_file),
            "--output-file",
            str(output),
        ],
        stdout_path=compose_env,
        stderr_path=design_tmpdir / "design-failure-compose.stderr.log",
    )
    if rc != 0:
        append_run_log_audit("escalation-compose-failed")
        write_fallback_chat("escalation-compose-failed")
        return 0, []
    populate_sensitive(class_path=None, attempts_path=attempts_file)
    if surface == "issue-input":
        file_tier_a_after_compose(output)
    handle_compose_outcome(kind="escalation-success", decision="escalation-success", sentinel=escalation_sentinel, artifact_key="STALL_RECOVERY_REPORT_ARTIFACT", last_surface=surface, last_output=output)
    return 0, []


def _final_summary_stream():
    return logging_util.contract_stream()


def _emit_final_summary_marked_from_disk(*, design_tmpdir: Path, final_summary_path: str) -> None:
    del design_tmpdir
    summary_path = Path(final_summary_path)
    if not summary_path.is_file() or summary_path.stat().st_size == 0:
        return
    stream = _final_summary_stream()
    logging_util.emit_kv(key=config.ENV_FINAL_SUMMARY_PATH, value=str(summary_path))
    stream.write("LARCH_FINAL_SUMMARY_BEGIN\n")
    stream.write("LARCH_FINAL_SUMMARY_END\n")
    stream.flush()


def _emit_report_gate_sidecars_from_disk(design_tmpdir: Path) -> None:
    handoff = design_tmpdir / "design-report-gate-sidecars.md"
    sidecars = (design_tmpdir / "design-failure-chat-print.md", design_tmpdir / "design-failure-operator-action-chat.md")
    chunks = [sidecar.read_text(encoding="utf-8", errors="replace") for sidecar in sidecars if sidecar.is_file() and sidecar.stat().st_size > 0]
    handoff.write_text(("\n".join(chunks).rstrip("\n") + "\n") if chunks else "", encoding="utf-8")
    if handoff.stat().st_size > 0:
        logging_util.emit_kv(key="REPORT_GATE_SIDECARS_FILE", value=str(handoff))


def _is_terminal_publish_outcome(outcome: str) -> bool:
    return outcome.startswith("cancelled-") and outcome != "cancelled-clarify"


def _parse_contract_value(text: str, key: str) -> str:
    return larch_io.kv_value(text=text, key=key, duplicate_policy="last")


def _has_nonempty_final_summary(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and path.stat().st_size > 0


def _touch_final_summary_complete(design_tmpdir: Path) -> None:
    _ = design_tmpdir


def _write_final_summary_result_env(*, design_tmpdir: Path, final_summary_path: str) -> None:
    summary_path = Path(final_summary_path)
    if not _has_nonempty_final_summary(summary_path):
        return
    design_write_merge_env(
        path=design_tmpdir / ".design-step-final-summary-result.env",
        design_tmpdir=design_tmpdir,
        rows=[("FINAL_SUMMARY_PATH", str(summary_path))],
    )


def _complete_final_summary(*, design_tmpdir: Path, final_summary_path: str) -> None:
    _write_final_summary_result_env(design_tmpdir=design_tmpdir, final_summary_path=final_summary_path)
    _touch_final_summary_complete(design_tmpdir)


def _flush_final_summary_outputs() -> None:
    sys.stdout.flush()
    with contextlib.suppress(OSError):
        _final_summary_stream().flush()


def _emit_and_complete_final_summary(*, design_tmpdir: Path, final_summary_path: str) -> int:
    try:
        _emit_final_summary_marked_from_disk(design_tmpdir=design_tmpdir, final_summary_path=final_summary_path)
        _emit_report_gate_sidecars_from_disk(design_tmpdir)
    except OSError as exc:
        _append_execution_issue(design_tmpdir=design_tmpdir, message=f"Warning: final summary emit failed: {exc}")
        return 1
    _flush_final_summary_outputs()
    try:
        _complete_final_summary(design_tmpdir=design_tmpdir, final_summary_path=final_summary_path)
    except (OSError, ValueError) as exc:
        _append_execution_issue(design_tmpdir=design_tmpdir, message=f"Warning: final summary result env write failed: {exc}")
        return 1
    return 0


def _publish_terminal_final_summary(
    *,
    design_tmpdir: Path,
    run_id: str,
    issue: str,
    outcome: str,
    repo: str = "",
) -> tuple[int, bool]:
    from larch.design import design_log_publish_flow  # noqa: PLC0415

    args = [
        "--design-tmpdir",
        str(design_tmpdir),
        "--run-id",
        run_id,
        "--issue",
        issue,
        "--outcome",
        outcome,
    ]
    if repo:
        args.extend(["--repo", repo])
    stdout_log = design_tmpdir / "design-log-publish.terminal.stdout.log"
    stderr_log = design_tmpdir / "design-log-publish.terminal.stderr.log"
    rc = 1
    with stdout_log.open("w", encoding="utf-8") as out, stderr_log.open("w", encoding="utf-8") as err:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = int(design_log_publish_flow.log_publish_main(args))
    stdout_text = stdout_log.read_text(encoding="utf-8", errors="replace") if stdout_log.is_file() else ""
    publish_ok = _parse_contract_value(stdout_text, "PUBLISH_OK")
    recovery_branch = _parse_contract_value(stdout_text, "RECOVERY_BRANCH")
    return rc, rc == 0 and publish_ok == "true" and not recovery_branch


def _run_terminal_publish_final_summary(*, design_tmpdir: Path, ctx: Ctx, final_summary_path: Path) -> int:
    if not ctx.session_id:
        _append_execution_issue(
            design_tmpdir=design_tmpdir,
            message="Warning: design log publish skipped for terminal summary because SESSION_ID is missing",
        )
        return 1
    try:
        publish_rc, publish_ok = _publish_terminal_final_summary(
            design_tmpdir=design_tmpdir,
            run_id=ctx.session_id,
            issue=ctx.issue_number,
            outcome=ctx.summary_outcome,
            repo=ctx.repo,
        )
    except OSError as exc:
        _append_execution_issue(design_tmpdir=design_tmpdir, message=f"Warning: design log publish failed for terminal summary: {exc}")
        return 1
    if not publish_ok:
        _append_execution_issue(
            design_tmpdir=design_tmpdir,
            message=f"Warning: design log publish failed for terminal summary (exit {publish_rc})",
        )
        return 1
    from larch.design.design_summary import upsert_final_summary_from_disk  # noqa: PLC0415

    repo_args = ["--repo", ctx.repo] if ctx.repo else []
    if not upsert_final_summary_from_disk(
        design_tmpdir=design_tmpdir,
        issue=ctx.issue_number,
        session_id=ctx.session_id,
        repo_args=repo_args,
        final_summary_path=final_summary_path,
    ):
        _append_execution_issue(
            design_tmpdir=design_tmpdir,
            message="Warning: tracking-issue upsert-summary failed for terminal final summary",
        )
        return 1
    return _emit_and_complete_final_summary(design_tmpdir=design_tmpdir, final_summary_path=str(final_summary_path))


def _render_final_summary_post_publish(*, design_tmpdir: Path, ctx: Ctx) -> int:
    # Local import is deliberate to avoid a design_summary <-> design_terminal
    # top-level import cycle while preserving the in-process port.
    from larch.design.design_summary import render_final_summary_main  # noqa: PLC0415

    render_args = [
        "--outcome",
        ctx.summary_outcome,
        "--design-tmpdir",
        str(design_tmpdir),
        "--issue-number",
        ctx.issue_number,
    ]
    if ctx.session_id:
        render_args.extend(["--session-id", ctx.session_id])
    render_args.append("--post-publish-only")
    if ctx.repo:
        render_args.extend(["--repo", ctx.repo])
    render_stdout = design_tmpdir / "render-final-summary.stdout.log"
    try:
        with render_stdout.open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
            return int(render_final_summary_main(render_args))
    except BaseException as exc:
        _core_print_exc()
        _append_execution_issue(design_tmpdir=design_tmpdir, message=f"Warning: render_final_summary_main failed: {exc}")
        return 1


def _run_rendered_final_summary(*, design_tmpdir: Path, ctx: Ctx, final_summary_path: str) -> int:
    render_rc = _render_final_summary_post_publish(design_tmpdir=design_tmpdir, ctx=ctx)
    if render_rc != 0:
        _flush_final_summary_outputs()
        return render_rc
    return _emit_and_complete_final_summary(design_tmpdir=design_tmpdir, final_summary_path=final_summary_path)


def _try_deactivate_design_run(design_tmpdir: Path) -> None:
    with contextlib.suppress(Exception):
        run_id = _progress_file.resolve_owned_run_id(tmpdir=design_tmpdir)
        if run_id:
            _ = rust_runtime.progress_deactivate(
                proc,
                repo_root=str(Path.cwd()),
                run_id=run_id,
            )


def step_final_summary_core(argv: Sequence[str]) -> tuple[int, list[str]]:
    old_environ: dict[str, str] = os.environ.copy()
    try:
        parsed = _parse_common_wrapper_args(argv)
        env = _rehydrate_wrapper_env(parsed)
        raw_tmpdir = env.get("DESIGN_TMPDIR", "")
        if not raw_tmpdir:
            _core_diagnostic("design-step-final-summary.sh: DESIGN_TMPDIR required")
            return 1, []
        try:
            design_tmpdir = _validate_design_tmpdir_arg(raw_tmpdir)
        except _CoreUsageError as exc:
            _core_diagnostic(f"design-step-final-summary.sh: {exc}")
            return 1, []
        os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)
        normalized_overrides = {config.ENV_DESIGN_TMPDIR: str(design_tmpdir)}
        logging_util.quiet_init(argv0="design-step-final-summary.sh")
        ctx = Ctx.from_mapping({**os.environ, **env, **normalized_overrides})
        final_summary_path = ctx.final_summary_path or str(design_tmpdir / "final-summary.md")
        disk_final_summary = design_tmpdir / "final-summary.md"
        if (design_tmpdir / ".pause-requested").is_file():
            return _call_pause_save(design_tmpdir=design_tmpdir, ctx=ctx), []
        with contextlib.suppress(OSError):
            (design_tmpdir / ".design-step-final-summary-result.env").unlink(missing_ok=True)
        if ctx.summary_outcome in {"cancelled-clarify", "failed-clarify"} and _has_nonempty_final_summary(disk_final_summary):
            rc = _emit_and_complete_final_summary(design_tmpdir=design_tmpdir, final_summary_path=str(disk_final_summary))
            _try_deactivate_design_run(design_tmpdir)
            return rc, []
        if _is_terminal_publish_outcome(ctx.summary_outcome):
            rc = _run_terminal_publish_final_summary(design_tmpdir=design_tmpdir, ctx=ctx, final_summary_path=disk_final_summary)
            _try_deactivate_design_run(design_tmpdir)
            return rc, []
        rc = _run_rendered_final_summary(design_tmpdir=design_tmpdir, ctx=ctx, final_summary_path=final_summary_path)
        _try_deactivate_design_run(design_tmpdir)
        return rc, []
    except ValueError as exc:
        _core_diagnostic(f"design-step-final-summary.sh: {exc}")
        return 2, []
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


def stage_terminal_state_main(argv: Sequence[str]) -> int:
    design_tmpdir_arg = ""
    args = list(argv)
    for idx, token in enumerate(args[:-1]):
        if token == "--design-tmpdir":
            design_tmpdir_arg = args[idx + 1]
            break
    try:
        design_tmpdir = _validate_design_tmpdir_arg(design_tmpdir_arg)
    except _CoreUsageError as exc:
        print(f"design-stage-terminal-state.sh: {exc}", file=sys.stderr)
        return 2
    os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)
    logging_util.quiet_init(argv0="design-stage-terminal-state.sh")
    rc, _ = stage_terminal_state_core(args)
    return rc


def failure_report_main(argv: Sequence[str]) -> int:
    design_tmpdir_arg = ""
    args = list(argv)
    for idx, token in enumerate(args[:-1]):
        if token == "--design-tmpdir":
            design_tmpdir_arg = args[idx + 1]
            break
    try:
        design_tmpdir = _validate_design_tmpdir_arg(design_tmpdir_arg)
    except _CoreUsageError as exc:
        print(f"design-failure-report.sh: {exc}", file=sys.stderr)
        return 2
    os.environ["DESIGN_TMPDIR"] = str(design_tmpdir)
    logging_util.quiet_init(argv0="design-failure-report.sh")
    rc, _ = failure_report_core(args)
    return rc


def step_final_summary_main(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step-final-summary.sh: {exc}", file=sys.stderr)
        return 2
    old_environ: dict[str, str] = os.environ.copy()
    try:
        env = _rehydrate_wrapper_env(parsed)
        try:
            design_tmpdir = _validate_design_tmpdir_arg(env.get("DESIGN_TMPDIR", ""))
        except _CoreUsageError as exc:
            print(f"design-step-final-summary.sh: {exc}", file=sys.stderr)
            return 1
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
    rc, _ = step_final_summary_core(argv)
    if rc in {2, 3}:
        return rc
    result_env = design_tmpdir / ".design-step-final-summary-result.env"
    if result_env.is_file() and not result_env.is_symlink():
        return 0
    return rc


def read_result_env_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py design read-result-env",
        add_help=False,
    )
    parser.add_argument("--input", dest="input_path")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--fallback-input", dest="fallback_input", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--allow", dest="allow", action="append", default=[])  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--output", dest="output_path")  # pyright: ignore[reportUnusedCallResult]
    try:
        ns, extra = parser.parse_known_args(list(argv))
    except SystemExit:
        _usage()
        return 1
    if extra or not ns.input_path or not ns.output_path or any(not _valid_var_name(k) for k in ns.allow):
        _usage()
        return 1

    input_path = Path(ns.input_path)
    fallback_path = Path(ns.fallback_input) if ns.fallback_input else None
    source_path, warning = _resolve_read_result_env_source(input_path, fallback_path)
    if warning:
        print(warning)
    if source_path is None:
        return 1

    output_path = Path(ns.output_path)
    if not output_path.parent.is_dir():
        return 1

    def write_pairs(*, from_path: Path, tmp_path: Path) -> int:
        _replay_warn_error(from_path)
        try:
            pairs = phase_driver_read_result_env(path=from_path, allow_keys=ns.allow)
        except OSError:
            return 1
        with tmp_path.open("w", encoding="utf-8") as handle:
            for key, value in pairs:
                handle.write(f"{key}={_quote_single(value)}\n")  # pyright: ignore[reportUnusedCallResult]
        return 0

    fd = -1
    tmp_name = ""
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=str(output_path.parent))
        os.close(fd)
        fd = -1
        tmp_path = Path(tmp_name)
        if write_pairs(from_path=source_path, tmp_path=tmp_path) != 0:
            return 1
        tmp_path.replace(output_path)  # pyright: ignore[reportUnusedCallResult]
        tmp_name = ""
        return 0
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_name:
            with contextlib.suppress(FileNotFoundError):
                Path(tmp_name).unlink()
