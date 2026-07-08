"""Phase driver result-env helpers, terminal state, failure report, and final summary."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false
# ruff: noqa: S607

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Callable, Iterable, Sequence

from larch.core import config, logging_util
from larch.core.ctx import Ctx
from larch.state import stall_recovery

from larch.design.design_core import (
    DESIGN_BGJOB_STEP_FINAL_SUMMARY,
    _CoreUsageError,
    _append_execution_issue,
    design_write_merge_env,
    _core_diagnostic,
    _core_print_exc,
    _emit_core_kvs,
    _read_env_value,
    _read_env_value_last,
    _read_env_values,
    _validate_design_tmpdir_arg,
    _append_failure,
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

def phase_driver_read_result_env(*, path: str | Path, allow_keys: Iterable[str]) -> list[tuple[str, str]]:
    """Read allowlisted KEY=VALUE records from a result-env file.

    Blank and malformed lines are skipped. Values containing CR or LF are
    refused, matching the shell phase-driver trust boundary.
    """
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise OSError(f"result env is not a regular file: {source}")
    allow = set(allow_keys)
    pairs: list[tuple[str, str]] = []
    for raw in source.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key not in allow:
            continue
        if "\n" in value or "\r" in value:
            continue
        pairs.append((key, value))
    return pairs


def phase_driver_write_result_env(*, path: str | Path, kvs: Iterable[tuple[str, str] | str]) -> None:
    """Atomically write allowlisted KEY=VALUE records to a result-env file.

    The trust boundary mirrors the shell phase driver: symlink targets are
    refused, keys must be allowlisted shell variable names, and values may not
    contain CR/LF bytes.
    """
    dest = Path(path)
    if dest.is_symlink():
        raise OSError(f"refusing to write symlink result env: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str]] = []
    for item in kvs:
        if isinstance(item, str):
            if "=" not in item:
                raise ValueError(f"result env row is missing '=': {item}")
            key, value = item.split("=", 1)
        else:
            key, value = item
        if key not in PHASE_RESULT_ENV_ALLOW_KEYS or not _valid_var_name(key):
            raise ValueError(f"result env key is not allowlisted: {key}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"result env value contains newline: {key}")
        rows.append((key, value))

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
    fd = -1
    try:
        if tmp.exists() or tmp.is_symlink():
            tmp.unlink()
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            for key, value in rows:
                handle.write(f"{key}={value}\n")  # pyright: ignore[reportUnusedCallResult]
        if dest.is_symlink():
            raise OSError(f"refusing to replace symlink result env: {dest}")
        tmp.replace(dest)  # pyright: ignore[reportUnusedCallResult]
    finally:
        if fd >= 0:
            os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            tmp.unlink()


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
    if dest.parent.is_symlink() or not dest.parent.is_dir():
        raise OSError(f"result env parent is not a regular directory: {dest.parent}")
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
    for raw in path.read_bytes().decode("utf-8", errors="replace").split("\n"):
        if raw == "":
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in {"WARN", "ERROR"}:
            print(f"{key}={value}")


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
        ".design-step-final-summary-result.env": DESIGN_BGJOB_STEP_FINAL_SUMMARY,
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


def _run_stall_main(*, callable_obj: Callable[..., int], argv: Sequence[str], stdout_path: Path | None = None, stderr_path: Path | None = None) -> int:
    try:
        with contextlib.ExitStack() as stack:
            if stdout_path is not None:
                out = stack.enter_context(stdout_path.open("w", encoding="utf-8"))
                stack.enter_context(contextlib.redirect_stdout(out))
            else:
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            if stderr_path is not None:
                err = stack.enter_context(stderr_path.open("w", encoding="utf-8"))
                stack.enter_context(contextlib.redirect_stderr(err))
            try:
                return int(callable_obj(list(argv)))
            except SystemExit as exc:
                return int(exc.code) if isinstance(exc.code, int) else 1
    except OSError:
        return 1


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
            rc = _run_stall_main(
                callable_obj=stall_recovery.validate_token_main,
                argv=[
                    *_stall_args(design_tmpdir),
                    "--token-kind",
                    kind,
                    "--value",
                    value,
                ],
            )
            if rc != 0:
                raise _CoreUsageError(f"{kind} is not a valid token")
        for kind, value in (("root-cause", ns.root_cause_hint), ("outcome", ns.summary_outcome)):
            if not value:
                continue
            rc = _run_stall_main(
                callable_obj=stall_recovery.validate_token_main,
                argv=[
                    *_stall_args(design_tmpdir),
                    "--token-kind",
                    kind,
                    "--value",
                    value,
                ],
            )
            if rc != 0:
                raise _CoreUsageError(f"{kind} is not a valid token")
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
        lines.append(f"OCCURRED_AT={datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if ns.evidence_ref:
            lines.append(f"EVIDENCE_REF={ns.evidence_ref}")
        candidate.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = _run_stall_main(
            callable_obj=stall_recovery.validate_terminal_state_main,
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
    proc_out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
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
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        rc = stall_recovery.is_larch_dev_clone_main([*_stall_args(design_tmpdir), "--working-tree-root", root])
    return rc == 0 and "LARCH_DEV_CLONE=true" in buf.getvalue().splitlines()


def _copy_if_file(*, source: Path, dest: Path) -> None:
    if source.is_file() and not source.is_symlink():
        shutil.copyfile(source, dest)


def _ledger_row_has_escalation_evidence(row: str) -> bool:
    values: dict[str, str] = {}
    for field in row.split("\t"):
        if "=" not in field:
            continue
        key, value = field.split("=", 1)
        values[key] = value
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
            "### [Bug] /design report fallback required\n\n"
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
        return _run_stall_main(
            callable_obj=stall_recovery.populate_sensitive_corpus_main,
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
                gh_out = subprocess.run(  # lint-subprocess-via-runner: ok current-repo gh lookup is a blocking stdout capture mirroring the tier-a filing helpers
                    ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                repo = gh_out.stdout.strip() if gh_out.returncode == 0 else ""
            fallback_reason = ""
            if not repo:
                fallback_reason = "tier-a-current-repo-unresolved"
            else:
                first = body_file.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
                title = (
                    first[0].removeprefix("### ").removeprefix("[Bug] ")
                    if first
                    else "/design terminal failure"
                )
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
                                    title or "/design terminal failure",
                                    "--publication-tier",
                                    "tier-a",
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
                            _run_stall_main(
                                callable_obj=stall_recovery.normalize_file_failure_report_env_main,
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

        dedup_env = design_tmpdir / "design-failure-tier-a-dedup.env"
        fallback_reason = ""
        if _run_stall_main(
            callable_obj=stall_recovery.dedup_tier_a_report_main,
            argv=[*helper_common(), "--body-file", str(body_file)],
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
        if _run_stall_main(
            callable_obj=stall_recovery.validate_terminal_state_main,
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
        _run_stall_main(callable_obj=stall_recovery.init_attempts_main, argv=[*helper_common(), "--attempts-file", str(attempts_file)])
        classify_out = design_tmpdir / "design-failure-classify.env"
        _run_stall_main(callable_obj=stall_recovery.classify_main, argv=[*helper_common(), *state_overrides()], stdout_path=classify_out)
        with contextlib.suppress(OSError):
            shutil.copyfile(classify_out, class_file)
        surface = report_surface()
        output = report_output_file(surface)
        if not populate_sensitive(class_path=class_file, attempts_path=attempts_file):
            append_run_log_audit("populate-sensitive-corpus-failed")
            write_fallback_chat("populate-sensitive-corpus-failed")
            return 0, []
        rc = _run_stall_main(
            callable_obj=stall_recovery.compose_report_main,
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
    _run_stall_main(callable_obj=stall_recovery.init_attempts_main, argv=[*helper_common(), "--attempts-file", str(attempts_file)])
    surface = report_surface()
    output = report_output_file(surface)
    if not populate_sensitive(class_path=None, attempts_path=attempts_file):
        append_run_log_audit("populate-sensitive-corpus-failed")
        write_fallback_chat("populate-sensitive-corpus-failed")
        return 0, []
    rc = _run_stall_main(
        callable_obj=stall_recovery.compose_report_main,
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


def _emit_report_gate_sidecars_from_disk(design_tmpdir: Path) -> Path | None:
    handoff = design_tmpdir / "design-report-gate-sidecars.md"
    sidecars = (design_tmpdir / "design-failure-chat-print.md", design_tmpdir / "design-failure-operator-action-chat.md")
    chunks = [sidecar.read_text(encoding="utf-8", errors="replace") for sidecar in sidecars if sidecar.is_file() and sidecar.stat().st_size > 0]
    handoff.write_text(("\n".join(chunks).rstrip("\n") + "\n") if chunks else "", encoding="utf-8")
    if handoff.stat().st_size > 0:
        logging_util.emit_kv(key="REPORT_GATE_SIDECARS_FILE", value=str(handoff))
        return handoff
    return None


def _is_terminal_publish_outcome(outcome: str) -> bool:
    return outcome.startswith("cancelled-") and outcome != "cancelled-clarify"


def _parse_contract_value(text: str, key: str) -> str:
    value = ""
    for line in text.splitlines():
        if line.startswith(f"{key}="):
            value = line.split("=", 1)[1]
    return value


def _has_nonempty_final_summary(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and path.stat().st_size > 0


def _touch_final_summary_complete(design_tmpdir: Path) -> None:
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-final-summary").touch()


def _final_summary_merge_env_arg(argv: Sequence[str]) -> str:
    args = list(argv)
    for idx, token in enumerate(args[:-1]):
        if token == "--merge-result-env":
            return args[idx + 1]
    return ""


def _write_final_summary_merge_env(
    *,
    design_tmpdir: Path,
    merge_result_env: str,
    final_summary_path: Path,
    report_gate_sidecars_path: Path | None,
) -> None:
    if not merge_result_env:
        return
    rows: list[tuple[str, object]] = []
    if _has_nonempty_final_summary(final_summary_path):
        rows.append((config.ENV_FINAL_SUMMARY_PATH, str(final_summary_path)))
    if report_gate_sidecars_path is not None:
        rows.append(("REPORT_GATE_SIDECARS_FILE", str(report_gate_sidecars_path)))
    design_write_merge_env(path=Path(merge_result_env), design_tmpdir=design_tmpdir, rows=rows)


def _finish_final_summary_success(
    *,
    design_tmpdir: Path,
    merge_result_env: str,
    final_summary_path: Path,
) -> None:
    _emit_final_summary_marked_from_disk(design_tmpdir=design_tmpdir, final_summary_path=str(final_summary_path))
    report_sidecars = _emit_report_gate_sidecars_from_disk(design_tmpdir)
    _write_final_summary_merge_env(
        design_tmpdir=design_tmpdir,
        merge_result_env=merge_result_env,
        final_summary_path=final_summary_path,
        report_gate_sidecars_path=report_sidecars,
    )
    sys.stdout.flush()
    with contextlib.suppress(OSError):
        _final_summary_stream().flush()
    _touch_final_summary_complete(design_tmpdir)


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
        merge_result_env = _final_summary_merge_env_arg(argv)
        with contextlib.suppress(OSError):
            (design_tmpdir / ".completed" / "step-final-summary").unlink(missing_ok=True)
        if ctx.summary_outcome in {"cancelled-clarify", "failed-clarify"} and _has_nonempty_final_summary(disk_final_summary):
            _finish_final_summary_success(
                design_tmpdir=design_tmpdir,
                merge_result_env=merge_result_env,
                final_summary_path=disk_final_summary,
            )
            return 0, []
        if _is_terminal_publish_outcome(ctx.summary_outcome):
            if not ctx.session_id:
                _append_execution_issue(
                    design_tmpdir=design_tmpdir,
                    message="Warning: design log publish skipped for terminal summary because SESSION_ID is missing",
                )
                return 1, []
            publish_rc, publish_ok = _publish_terminal_final_summary(
                design_tmpdir=design_tmpdir,
                run_id=ctx.session_id,
                issue=ctx.issue_number,
                outcome=ctx.summary_outcome,
                repo=ctx.repo,
            )
            if not publish_ok:
                _append_execution_issue(
                    design_tmpdir=design_tmpdir,
                    message=f"Warning: design log publish failed for terminal summary (exit {publish_rc})",
                )
                return 1, []
            from larch.design.design_summary import upsert_final_summary_from_disk  # noqa: PLC0415

            repo_args = ["--repo", ctx.repo] if ctx.repo else []
            if not upsert_final_summary_from_disk(
                design_tmpdir=design_tmpdir,
                issue=ctx.issue_number,
                session_id=ctx.session_id,
                repo_args=repo_args,
                final_summary_path=disk_final_summary,
            ):
                _append_execution_issue(
                    design_tmpdir=design_tmpdir,
                    message="Warning: tracking-issue upsert-summary failed for terminal final summary",
                )
                return 1, []
            _finish_final_summary_success(
                design_tmpdir=design_tmpdir,
                merge_result_env=merge_result_env,
                final_summary_path=disk_final_summary,
            )
            return 0, []
        # Local import is deliberate to avoid a design_summary <-> design_lifecycle
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
        render_rc = 0
        try:
            with render_stdout.open("w", encoding="utf-8") as out, contextlib.redirect_stdout(out):
                render_rc = render_final_summary_main(render_args)
        except BaseException as exc:
            render_rc = 1
            _core_print_exc()
            _append_execution_issue(design_tmpdir=design_tmpdir, message=f"Warning: render_final_summary_main failed: {exc}")
        if render_rc == 0:
            _finish_final_summary_success(
                design_tmpdir=design_tmpdir,
                merge_result_env=merge_result_env,
                final_summary_path=Path(final_summary_path),
            )
        else:
            sys.stdout.flush()
            with contextlib.suppress(OSError):
                _final_summary_stream().flush()
        return int(render_rc), []
    except (OSError, ValueError) as exc:
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
    if (design_tmpdir / ".completed" / "step-final-summary").is_file():
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
