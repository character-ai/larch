"""Step 5b OOS-filing prepare and annotate entry points."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from collections.abc import Mapping, Sequence

from larch.design import design_oos

from larch.design.design_core import _append_failure
from larch.design.design_router import _parse_stdout_kv
from larch.design.design_session import (
    _call_pause_save,
    _capture_stdout_stderr,
    _design_require_plugin_root,
    _maybe_timing_mark,
    _parse_common_wrapper_args,
    _print_text,
    _rehydrate_wrapper_env,
    _write_text,
)
from larch.design.design_step0 import _require_design_tmpdir_nonempty
from larch.design.design_step5c import _step5b_mark_complete

def _step5b_issue_args(env: Mapping[str, str]) -> list[str]:
    issue_number = env.get("ISSUE_NUMBER", "")
    args = ["--issue-number", issue_number] if issue_number else []
    repo = env.get("REPO", "")
    if repo:
        args.extend(["--repo", repo])
    return args


def _path_nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def _step5b_append_failure_if_stderr(*, plugin_root: Path, design_tmpdir: Path, tool: str, exit_code: int, stderr_path: Path) -> None:
    if _path_nonempty(stderr_path):
        _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 5b", tool=tool, exit_code=exit_code, category="Tool Failures", output_file=stderr_path)


def _step5b_issues_failed(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(re.match(r"^ISSUES_FAILED=[1-9][0-9]*$", line) for line in text.splitlines())


def _step5b_annotate_sequencing_error(oos_issue_stdout: Path) -> bool:
    try:
        if not oos_issue_stdout.is_file():
            return True
        return not oos_issue_stdout.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return True


_STEP5B_SKIP_BREADCRUMBS = {
    "skip-sentinel": "⏩ 5b: oos filing; sentinel recovery (skip pipeline)",
    "skip-already-filed-sentinel": "⏩ 5b: oos filing; oos-issue-sentinel present (already filed); skip pipeline",
    "skip-no-items": "⏩ 5b: oos filing; no accepted-OOS items",
    "skip-all-security": "⏩ 5b: oos filing; no non-security OOS items",
    "label-only-retry": "⏩ 5b: oos filing; label-only retry (pending priority labels)",
}


def _step5b_next_action(status: str) -> str:
    if status == "ready":
        return "file-issues"
    if status == "label-only-retry":
        return "label-only"
    if status in _STEP5B_SKIP_BREADCRUMBS:
        return "skip-pipeline"
    return "unknown-oos-status"


def _step5b_write_prepare_env(*, path: Path, stdout_text: str, wrapper_rows: Sequence[str]) -> None:
    separator = "" if not stdout_text or stdout_text.endswith("\n") else "\n"
    wrapper_text = "\n".join(wrapper_rows) + "\n"
    _write_text(path=path, text=stdout_text + separator + wrapper_text)


def _step5b_emit_prepare_success(*, design_tmpdir: Path, prepare_env_path: Path, stdout_text: str, oos_issue_stdout: Path) -> str:
    kv = _parse_stdout_kv(stdout_text)
    for line in stdout_text.splitlines():
        if line.startswith(("FILE_DESIGN_OOS_", "WARN=")):
            print(line)
    status = kv.get("FILE_DESIGN_OOS_STATUS", [""])[-1]
    combined = kv.get("FILE_DESIGN_OOS_COMBINED", [""])[-1]
    deps_tsv = kv.get("FILE_DESIGN_OOS_DEPS_TSV", [""])[-1]
    deps_available = kv.get("FILE_DESIGN_OOS_DEPS_AVAILABLE", [""])[-1]
    upstream_next_action = kv.get("NEXT_ACTION", [""])[-1]
    next_action = _step5b_next_action(status)
    if upstream_next_action and upstream_next_action != next_action:
        next_action = "unknown-oos-status"
    is_unknown = next_action == "unknown-oos-status"
    emit_status = "unknown-oos-status" if is_unknown else status
    breadcrumb = _STEP5B_SKIP_BREADCRUMBS.get(status, "")
    needs_annotate = not is_unknown and (
        status in {"ready", "label-only-retry"}
        or (status == "skip-already-filed-sentinel" and not _step5b_annotate_sequencing_error(oos_issue_stdout))
    )

    wrapper_rows = [f"STEP5B_STATUS={emit_status}", "OOS_PREP_RC=0", f"OOS_ISSUE_STDOUT_PATH={oos_issue_stdout}"]
    wrapper_rows.append(f"NEXT_ACTION={next_action}")
    if breadcrumb:
        wrapper_rows.append(f"OOS_SKIP_BREADCRUMB={breadcrumb}")
    if needs_annotate:
        wrapper_rows.append("STEP5B_NEEDS_ANNOTATE=true")

    print("\n".join(wrapper_rows))
    if combined:
        print(f"FILE_DESIGN_OOS_COMBINED={combined}")
    if deps_tsv:
        print(f"FILE_DESIGN_OOS_DEPS_TSV={deps_tsv}")
    if deps_available:
        print(f"FILE_DESIGN_OOS_DEPS_AVAILABLE={deps_available}")
    if not is_unknown and status in _STEP5B_SKIP_BREADCRUMBS and status != "label-only-retry" and not needs_annotate:
        _step5b_mark_complete(design_tmpdir)
    _step5b_write_prepare_env(path=prepare_env_path, stdout_text=stdout_text, wrapper_rows=wrapper_rows)
    return next_action


def step5b_prepare_main(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step5b-prepare.sh: {exc}", file=sys.stderr)
        return 2
    env = _rehydrate_wrapper_env(parsed)
    req = _design_require_plugin_root()
    if req != 0:
        return req
    plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    design_tmpdir = _require_design_tmpdir_nonempty(env=env, site="prepare")
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-4b").touch()
    if (design_tmpdir / ".pause-requested").is_file():
        return _call_pause_save(design_tmpdir=design_tmpdir)
    _maybe_timing_mark(label="design Step 5 — finalize")

    stderr_path = design_tmpdir / "oos-filing-prepare.stderr.log"
    prep_args = ["--design-tmpdir", str(design_tmpdir), *_step5b_issue_args(env)]
    prep_rc, stdout_text = _capture_stdout_stderr(callable_obj=design_oos.file_oos_prepare_main, argv=prep_args, stderr_path=stderr_path)
    prepare_env_path = design_tmpdir / "oos-filing-prepare.env"
    _write_text(path=prepare_env_path, text=stdout_text)
    oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"

    if prep_rc != 0:
        _step5b_append_failure_if_stderr(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            tool="file-design-oos.sh prepare",
            exit_code=prep_rc,
            stderr_path=stderr_path,
        )
        print("**⚠ /design: OOS filing prepare failed; skipping /larch:issue; continuing to Step 5b.5**")
        wrapper_text = (
            "STEP5B_STATUS=prepare-failed-continue\n"
            f"OOS_PREP_RC={prep_rc}\n"
            f"OOS_ISSUE_STDOUT_PATH={oos_issue_stdout}\n"
            "NEXT_ACTION=skip-pipeline\n"
        )
        _step5b_write_prepare_env(path=prepare_env_path, stdout_text=stdout_text, wrapper_rows=wrapper_text.splitlines())
        print(wrapper_text, end="")
        _step5b_mark_complete(design_tmpdir)
        return 0

    next_action = _step5b_emit_prepare_success(
        design_tmpdir=design_tmpdir,
        prepare_env_path=prepare_env_path,
        stdout_text=stdout_text,
        oos_issue_stdout=oos_issue_stdout,
    )
    if next_action == "unknown-oos-status":
        print("**⚠ /design: unrecognized OOS prepare status; stop for repair before Step 5b.5**")
        return 2
    return 0


def _step5b_handle_empty_stdout_retry(*, plugin_root: Path, design_tmpdir: Path, stderr_path: Path, exit_code: int, verb: str) -> int:
    retry_sentinel = design_tmpdir / ".oos-issue-retry-used"
    if retry_sentinel.is_file():
        _append_failure(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            site="design Step 5b annotate-skip",
            tool="file-design-oos.sh annotate",
            exit_code=exit_code,
            category="Tool Failures",
            output_file=stderr_path,
        )
        print(f"**⚠ /design: annotate {verb} (empty issue stdout) after retry sentinel; stop before Step 5b.5**")
        return 1
    _ = retry_sentinel.write_text("used\n", encoding="utf-8")
    _append_failure(
        plugin_root=plugin_root,
        design_tmpdir=design_tmpdir,
        site="design Step 5b annotate-skip",
        tool="file-design-oos.sh annotate",
        exit_code=exit_code,
        category="Warnings",
        output_file=stderr_path,
    )
    print(f"**⚠ /design: annotate {verb} (empty issue stdout); status unclear; see execution-issues**")
    return 1


def step5b_annotate_main(argv: Sequence[str]) -> int:
    try:
        parsed = _parse_common_wrapper_args(argv)
    except ValueError as exc:
        print(f"design-step5b-annotate.sh: {exc}", file=sys.stderr)
        return 2
    env = _rehydrate_wrapper_env(parsed)
    req = _design_require_plugin_root()
    if req != 0:
        return req
    plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
    design_tmpdir = _require_design_tmpdir_nonempty(env=env, site="annotate")
    oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"
    if (design_tmpdir / ".pause-requested").is_file():
        return _call_pause_save(design_tmpdir=design_tmpdir)

    stderr_path = design_tmpdir / "oos-filing-annotate.stderr.log"
    prepare_env = _parse_stdout_kv((design_tmpdir / "oos-filing-prepare.env").read_text(encoding="utf-8", errors="replace") if (design_tmpdir / "oos-filing-prepare.env").is_file() else "")
    prepare_status = prepare_env.get("FILE_DESIGN_OOS_STATUS", [""])[-1]
    prepare_next_action = prepare_env.get("NEXT_ACTION", [""])[-1]
    label_only = prepare_status == "label-only-retry" or prepare_next_action == "label-only"
    ann_args = [
        "--design-tmpdir",
        str(design_tmpdir),
        "--issue-stdout-file",
        str(oos_issue_stdout),
        *_step5b_issue_args(env),
    ]
    if label_only:
        ann_args.append("--label-only")
    ann_rc, stdout_text = _capture_stdout_stderr(callable_obj=design_oos.file_oos_annotate_main, argv=ann_args, stderr_path=stderr_path)
    _write_text(path=design_tmpdir / "oos-filing-annotate.stdout.txt", text=stdout_text)
    _print_text(stdout_text)
    print(f"OOS_ANN_RC={ann_rc}")

    kv = _parse_stdout_kv(stdout_text)
    status = kv.get("FILE_DESIGN_OOS_STATUS", [""])[-1]
    warn = kv.get("WARN", [""])[-1]

    if ann_rc != 0:
        _step5b_append_failure_if_stderr(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            tool="file-design-oos.sh annotate",
            exit_code=ann_rc,
            stderr_path=stderr_path,
        )
        if _step5b_issues_failed(oos_issue_stdout):
            print("**⚠ /design: OOS filing completed with ISSUES_FAILED>0; see execution-issues and oos-issue.stdout.txt**")
        if status == "annotate-failed-empty-stdout" and warn:
            return _step5b_handle_empty_stdout_retry(
                plugin_root=plugin_root,
                design_tmpdir=design_tmpdir,
                stderr_path=stderr_path,
                exit_code=ann_rc,
                verb="failed",
            )
        label_failed = status == "annotate-label-failed" or (design_tmpdir / ".oos-priority-label-pending").is_file()
        if label_failed:
            if not _path_nonempty(stderr_path):
                stderr_path.write_text("design Step 5b: priority label application failed\n", encoding="utf-8")
                _step5b_append_failure_if_stderr(
                    plugin_root=plugin_root,
                    design_tmpdir=design_tmpdir,
                    tool="file-design-oos.sh annotate",
                    exit_code=ann_rc,
                    stderr_path=stderr_path,
                )
            print("STEP5B_STATUS=annotate-label-failed")
            return ann_rc
        print("STEP5B_STATUS=annotate-failed")
        if not label_only and not _step5b_annotate_sequencing_error(oos_issue_stdout):
            _step5b_mark_complete(design_tmpdir)
        return ann_rc

    if (design_tmpdir / ".oos-priority-label-pending").is_file():
        print("STEP5B_STATUS=annotate-label-failed")
        return 1

    _step5b_mark_complete(design_tmpdir)
    final_status = "annotate-label-complete" if status == "annotate-label-complete" else "annotate-complete"
    print(f"STEP5B_STATUS={final_status}")
    return 0
