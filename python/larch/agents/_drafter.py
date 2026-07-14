# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false
"""Drafter and negotiation round launchers."""

from __future__ import annotations

import argparse
import contextlib
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from larch.core import config
from larch.design import design_dialectic, plan_grammar
from larch.core import logging_util
from larch.design import plan_scout
from larch.core import proc

from larch.agents._types import (
    _CTRL_RE,
    _MAX_CLAUDE_TIMEOUT,
    _PY_CLI,
    LauncherPaths,
    DrafterParseResult,
    _err,
    _emit_kv,
    _write,
    _append,
    _is_positive_int,
    _validate_meta_path,
    _json_array,
    _plugin_root,
)
from larch.agents._launch_failure import (
    resolve_model_args,
    resolve_launcher_exit,
)
from larch.agents._run_external import (
    external_startup_lock_acquire,
    external_startup_lock_release_after,
    _prepare_codex_home,
    _mirror_codex_quota_from_events,
    _record_usage_from_events,
    _resolve_review_codex_workdir,
    _run_external_agent_with_auth_retries,
    _write_preflight_bundle,
    _promote_inner_done,
    _under,
)
from larch.agents._failure_diag import (
    write_failed_agent_stderr_tail,
    _compose_failure_diag,
)
from larch.agents._auth import (
    cursor_auth_preflight,
    cursor_auth_export_env,
    _probe_tmpdir,
)
from larch.agents._vendor import (
    CODEX_DESCRIPTOR,
    CURSOR_DESCRIPTOR,
    CLAUDE_DESCRIPTOR,
    VendorLaunchRequest,
    VendorProcessResult,
    VendorFamilyHooks,
    parse_claude_envelope,
    run_vendor_launch,
)
from larch.agents._claude_runner import (
    _record_claude_sub_usage,
)

def _negotiation_base(output: Path) -> Path:
    text = str(output)
    if text.endswith(".txt"):
        return Path(text[:-4])
    return output


# ---------------------------------------------------------------------------
# Vendor launch hook helpers (lifted from inlined closures so the enclosing
# launch functions shed the closure statements and recover prior complexity).
# Each helper threads the formerly captured state through explicit parameters;
# ``**_kwargs`` absorbs the extra lifecycle kwargs ``run_vendor_launch`` passes.
# ---------------------------------------------------------------------------


def _emit_response_file(*, output_path: Path, **_kwargs: object) -> None:
    _emit_kv(key="RESPONSE_FILE", value=str(output_path))


def _negotiation_codex_preflight(*, prep_rc: int, prep_msg: str, sidecar: Path, **_kwargs: object) -> bool:
    if prep_rc != 0:
        if prep_msg:
            _write(path=sidecar, text=prep_msg + "\n")
        return False
    return True


def _negotiation_codex_execute(
    *,
    argv: list[str],
    prompt: Path,
    events: Path,
    sidecar: Path,
    workdir: Path,
    env: dict[str, str],
    **_kwargs: object,
) -> VendorProcessResult:
    state = external_startup_lock_acquire(tool="codex")
    external_startup_lock_release_after(state=state)
    with prompt.open("r", encoding="utf-8", errors="replace") as input_handle:
        try:
            with events.open("w", encoding="utf-8") as out_handle, sidecar.open("w", encoding="utf-8") as err_handle:
                # lint-subprocess-via-runner: ok requires stdin, stdout, stderr file handles; proc.run only captures to pipes
                proc_obj = subprocess.run(
                    argv,
                    stdin=input_handle,
                    stdout=out_handle,
                    stderr=err_handle,
                    cwd=str(workdir),
                    env=env,
                    text=True,
                    check=False,
                )
            codex_rc = proc_obj.returncode
        except FileNotFoundError:
            codex_rc = 127
            _append(path=sidecar, text="Failed to launch child: codex\n")
    return VendorProcessResult(exit_code=codex_rc)


def _negotiation_codex_mirror_quota(*, result: VendorProcessResult, events: Path, sidecar: Path, **_kwargs: object) -> None:
    if result.exit_code != 0:
        _mirror_codex_quota_from_events(events=events, sidecar=sidecar)


def _negotiation_codex_record_usage(*, events: Path, sidecar: Path, **_kwargs: object) -> None:
    _record_usage_from_events(events=events, sidecar=sidecar, label="codex_negotiation")


def _negotiation_cursor_preflight(**_kwargs: object) -> bool:
    verdict = cursor_auth_preflight(caller="agent run-negotiation-round")
    if not verdict.ok:
        _err(verdict.message)
        return False
    cursor_auth_export_env()
    return True


def _negotiation_cursor_execute(*, argv: list[str], output_path: Path, workdir: Path, **_kwargs: object) -> VendorProcessResult:
    state = external_startup_lock_acquire(tool="cursor")
    external_startup_lock_release_after(state=state)
    try:
        with output_path.open("w", encoding="utf-8") as handle:
            # lint-subprocess-via-runner: ok requires stdout file handle; proc.run only captures to pipes
            result = subprocess.run(
                argv,
                stdout=handle,
                stderr=subprocess.STDOUT,
                cwd=str(workdir),
                env=dict(os.environ),
                text=True,
                check=False,
            )
        cursor_rc = result.returncode
    except FileNotFoundError:
        _write(path=output_path, text="Failed to launch child: cursor\n")
        cursor_rc = 127
    return VendorProcessResult(exit_code=cursor_rc)


def _codex_external_agent_execute(
    *,
    argv: list[str],
    output: Path,
    timeout: str,
    env: dict[str, str],
    cwd: str,
    stdout_path: Path,
    stderr_path: Path,
    start_holder: list[float],
    **_kwargs: object,
) -> VendorProcessResult:
    start_holder.append(time.time())
    result = _run_external_agent_with_auth_retries(
        tool="codex",
        output=output,
        timeout_seconds=int(timeout, 10),
        cmd=argv,
        env=env,
        cwd=cwd,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    return VendorProcessResult(exit_code=result.exit_code)


def _codex_events_mirror_quota(*, events: Path, sidecar: Path, **_kwargs: object) -> None:
    if not events.is_file() or events.stat().st_size == 0:
        _write(path=events, text="{}\n")
    _mirror_codex_quota_from_events(events=events, sidecar=sidecar)


def _codex_record_vendor_timing(*, result: VendorProcessResult, timing_task_kind: str, output: Path, start_holder: list[float], **_kwargs: object) -> None:
    end = time.time()
    start = start_holder[0] if start_holder else end
    proc.run(
        [
            sys.executable,
            str(_PY_CLI),
            "timing",
            "record-vendor-task",
            "--vendor",
            "codex",
            "--task-kind",
            timing_task_kind,
            "--start-s",
            str(int(start)),
            "--end-s",
            str(int(end)),
            "--output",
            str(output),
            "--exit-code",
            str(result.exit_code),
            "--status",
            "complete" if result.exit_code == 0 else "signal",
        ],
        check=False,
    )


def _codex_record_vendor_usage(*, model: str, events: Path, sidecar: Path, label: str, token_record: Path, **_kwargs: object) -> None:
    _record_usage_from_events(events=events, sidecar=sidecar, label=label, token_record=token_record, model=model)


def _codex_exec_promote(
    *,
    output: Path,
    prompt_sidecar: Path,
    workdir: Path,
    sandbox: str,
    with_effort: bool,
    model_role: str,
    usage_label: str,
    timing_task_kind: str,
    add_dirs: list[str],
    **_kwargs: object,
) -> None:
    _append(
        path=output.with_suffix(output.suffix + ".meta"),
        text="\n".join(
            [
                "OUTER_LAUNCHER=agent launch-codex-exec",
                f"OUTER_LAUNCHER_PROMPT_FILE={prompt_sidecar}",
                f"OUTER_LAUNCHER_WORKDIR={workdir}",
                "OUTER_LAUNCHER_KIND=codex-exec",
                f"OUTER_LAUNCHER_SANDBOX={sandbox}",
                f"OUTER_LAUNCHER_WITH_EFFORT={str(with_effort).lower()}",
                f"OUTER_LAUNCHER_MODEL_ROLE={model_role}",
                f"OUTER_LAUNCHER_USAGE_LABEL={usage_label}",
                f"OUTER_LAUNCHER_TIMING_KIND={timing_task_kind}",
                f"OUTER_LAUNCHER_ADD_DIRS_JSON={_json_array(add_dirs)}",
            ]
        )
        + "\n",
    )
    _promote_inner_done(output)


def _claude_drafter_execute(
    *,
    argv: list[str],
    timeout_bin: str | None,
    timeout: str,
    json_tmp: Path,
    stderr_path: Path,
    prompt_text: str,
    **_kwargs: object,
) -> VendorProcessResult:
    run_cmd = [timeout_bin, timeout, *argv] if timeout_bin else argv
    with json_tmp.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        try:
            # lint-subprocess-via-runner: ok requires input string and stdout/stderr file handles; proc.run only captures to pipes
            completed = subprocess.run(run_cmd, input=prompt_text, text=True, stdout=out, stderr=err, check=False)
            return VendorProcessResult(exit_code=completed.returncode)
        except FileNotFoundError:
            err.write("Failed to launch child: claude\n")
            return VendorProcessResult(exit_code=127)


def run_negotiation_round(*, tool: str, prompt_file: str | Path, output: str | Path, workspace: str | Path) -> int:
    if tool not in {"codex", "cursor"}:
        _err(f"agent run-negotiation-round: ERROR: --tool must be 'codex' or 'cursor' (got: {tool})")
        return 1
    prompt = Path(prompt_file)
    output_path = Path(output)
    workdir = Path(workspace)
    if not prompt.is_file():
        _err(f"agent run-negotiation-round: ERROR: prompt file not found: {prompt}")
        return 1

    with contextlib.suppress(FileNotFoundError):
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if tool == "codex":
        base = _negotiation_base(output_path)
        events = Path(str(base) + ".events.jsonl")
        sidecar = Path(str(base) + ".sidecar")
        with contextlib.suppress(FileNotFoundError):
            events.unlink()
        with contextlib.suppress(FileNotFoundError):
            sidecar.unlink()
        try:
            model_args = tuple(resolve_model_args("codex").argv)
        except ValueError as exc:
            _err(f"agent run-negotiation-round: model args failed: {exc}")
            return 1
        codex_home = Path(tempfile.mkdtemp(prefix="larch-codex-negotiation-home-", dir=str(_probe_tmpdir())))
        try:
            prep_rc, prep_msg = _prepare_codex_home(codex_home)
            env: dict[str, str] = dict(os.environ)
            env["CODEX_HOME"] = str(codex_home)

            request = VendorLaunchRequest(
                workdir=str(workdir),
                output=str(output_path),
                prompt="",
                model_args=model_args,
                prompt_via_stdin=True,
                timing_task_kind="codex_negotiation",
            )
            hooks = VendorFamilyHooks(
                preflight=functools.partial(_negotiation_codex_preflight, prep_rc=prep_rc, prep_msg=prep_msg, sidecar=sidecar),
                execute=functools.partial(_negotiation_codex_execute, prompt=prompt, events=events, sidecar=sidecar, workdir=workdir, env=env),
                mirror_quota=functools.partial(_negotiation_codex_mirror_quota, events=events, sidecar=sidecar),
                record_usage=functools.partial(_negotiation_codex_record_usage, events=events, sidecar=sidecar),
                promote_completion=functools.partial(_emit_response_file, output_path=output_path),
            )
            outcome = run_vendor_launch(
                CODEX_DESCRIPTOR,
                "workspace-write",
                request,
                hooks=hooks,
                use_config_context=False,
            )
            if outcome.status == "preflight_refused":
                _emit_kv(key="RESPONSE_FILE", value=str(output_path))
                return 2
            if outcome.process_result is not None and outcome.process_result.exit_code != 0:
                return 2
            return 0
        finally:
            shutil.rmtree(codex_home, ignore_errors=True)

    try:
        model_args = tuple(resolve_model_args("cursor").argv)
    except ValueError as exc:
        _err(f"agent run-negotiation-round: model args failed: {exc}")
        return 1
    wrapped = f" /max-mode on. Prompt: Read the negotiation prompt from {prompt} and respond to it."

    cursor_request = VendorLaunchRequest(
        workdir=str(workdir),
        output=str(output_path),
        prompt=wrapped,
        model_args=model_args,
        timing_task_kind="cursor_negotiation",
    )
    cursor_hooks = VendorFamilyHooks(
        preflight=_negotiation_cursor_preflight,
        execute=functools.partial(_negotiation_cursor_execute, output_path=output_path, workdir=workdir),
        promote_completion=functools.partial(_emit_response_file, output_path=output_path),
    )
    cursor_outcome = run_vendor_launch(
        CURSOR_DESCRIPTOR,
        "negotiation-write",
        cursor_request,
        hooks=cursor_hooks,
        use_config_context=False,
    )
    if cursor_outcome.status == "preflight_refused":
        _emit_kv(key="RESPONSE_FILE", value=str(output_path))
        return 3
    if cursor_outcome.process_result is not None and cursor_outcome.process_result.exit_code != 0:
        return 2
    return 0


def run_negotiation_round_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent run-negotiation-round")
    parser.add_argument("--tool", choices=("codex", "cursor"), required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    return run_negotiation_round(tool=args.tool, prompt_file=args.prompt_file, output=args.output, workspace=args.workspace)


def launch_codex_exec_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent launch-codex-exec")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", required=True)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--add-dir", action="append", default=[])
    parser.add_argument("--sandbox", choices=("workspace-write", "read-only"), default="workspace-write")
    parser.add_argument("--with-effort", action="store_true")
    parser.add_argument("--model-role", choices=("default", "fix"), default="default")
    parser.add_argument("--usage-label", default="codex_exec")
    parser.add_argument("--timing-task-kind", default="codex-exec")
    parser.add_argument("--trusted-instructions-file", default="")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if not _is_positive_int(args.timeout):
        _err("agent launch-codex-exec: --timeout must be a positive integer")
        return 2
    if not output.is_absolute() or not _validate_meta_path(label="--output", value=str(output)):
        return 2
    workdir_value = args.workdir if args.workdir is not None else _resolve_review_codex_workdir(str(Path.cwd()))
    workdir = Path(workdir_value)
    if not workdir.is_dir():
        _err(f"agent launch-codex-exec: --workdir is not a directory: {workdir}")
        return 2
    prompt = args.prompt if args.prompt is not None else Path(args.prompt_file).read_text(encoding="utf-8", errors="replace")
    prompt_sidecar = output.with_suffix(output.suffix + ".prompt")
    _write(path=prompt_sidecar, text=prompt)
    add_dirs = args.add_dir or [str(workdir)]
    with tempfile.TemporaryDirectory(prefix="larch-codex-exec-home-") as home:
        auth_rc, auth_msg = _prepare_codex_home(Path(home), trusted_instructions_file=args.trusted_instructions_file)
        if auth_rc != 0:
            reason = auth_msg or f"codex auth setup failed (exit {auth_rc})"
            _write_preflight_bundle(output=output, timeout=args.timeout, launcher_exit=auth_rc, failure_reason=reason)
            return 0
        try:
            model_args = tuple(resolve_model_args("codex", with_effort=args.with_effort, codex_role=getattr(args, "model_role", "default")).argv)
        except ValueError as exc:
            _write_preflight_bundle(output=output, timeout=args.timeout, launcher_exit=1, failure_reason=f"model args failed: {exc}")
            return 0
        events = output.with_suffix(output.suffix + ".events.jsonl")
        sidecar = output.with_suffix(output.suffix + ".sidecar")
        env: dict[str, str] = dict(os.environ)
        env["CODEX_HOME"] = home
        start_holder: list[float] = []
        exec_request = VendorLaunchRequest(
            workdir=str(workdir),
            output=str(output),
            prompt=prompt,
            model_args=model_args,
            add_dirs=tuple(add_dirs),
            timing_task_kind=args.timing_task_kind,
        )
        exec_hooks = VendorFamilyHooks(
            execute=functools.partial(_codex_external_agent_execute, output=output, timeout=args.timeout, env=env, cwd=str(workdir), stdout_path=events, stderr_path=sidecar, start_holder=start_holder),
            mirror_quota=functools.partial(_codex_events_mirror_quota, events=events, sidecar=sidecar),
            record_timing=functools.partial(_codex_record_vendor_timing, timing_task_kind=args.timing_task_kind, output=output, start_holder=start_holder),
            record_usage=functools.partial(_codex_record_vendor_usage, events=events, sidecar=sidecar, label=args.usage_label, token_record=output.with_suffix(output.suffix + ".token-record")),
            promote_completion=functools.partial(_codex_exec_promote, output=output, prompt_sidecar=prompt_sidecar, workdir=workdir, sandbox=args.sandbox, with_effort=args.with_effort, model_role=args.model_role, usage_label=args.usage_label, timing_task_kind=args.timing_task_kind, add_dirs=add_dirs),
        )
        outcome = run_vendor_launch(
            CODEX_DESCRIPTOR,
            args.sandbox,
            exec_request,
            hooks=exec_hooks,
            use_config_context=False,
        )
        launcher_exit = outcome.process_result.exit_code if outcome.process_result is not None else 0
    _emit_kv(key="LAUNCHER_EXIT", value=launcher_exit)
    _emit_kv(key="OUTPUT", value=str(output))
    return 0



RAW_PENDING = ".dialectic-raw-pending.json"


_CODEX_DRAFTER_TRUSTED_INSTRUCTIONS = """STRICT CONSTRAINTS — your role is read-only plan drafting for /design Step 2b. Do not create, edit, delete, or overwrite repository or tmpdir files. The launcher enforces this with --sandbox read-only.

OUTPUT CONTRACT — these requirements override any conflicting Codex user configuration or instructions:
- Emit exactly one whole-line LARCH_PLAN_BEGIN and one whole-line LARCH_PLAN_END with a non-empty plan body between them.
- Optionally emit zero or one balanced LARCH_SUMMARY_BEGIN/LARCH_SUMMARY_END pair before the plan envelope.
- The plan body must end with a whole-line diff_lines: <N> trailer.
- Optionally emit zero or one balanced LARCH_DIALECTIC_BEGIN/LARCH_DIALECTIC_END JSON block after LARCH_PLAN_END and before LARCH_SCOUT_BEGIN.
- Use dialectic JSON only for genuine bistable forks: at most two decisions, each with id, title, option_a, option_b, tradeoff, drafter_pick (option_a or option_b), and why_this_matters.
- Malformed dialectic output after the plan is ignored by the launcher and must not affect a valid plan; dialectic sentinels inside the summary or plan are fatal.
- Emit zero or one balanced LARCH_SCOUT_BEGIN/LARCH_SCOUT_END pair after LARCH_PLAN_END on a best-effort basis.
- Use {"archetypes":[]} when no dynamic plan-review specialists are useful.
- The scout block must contain only compact JSON with this shape: {"archetypes":[{"name":"slug","focus_area":"code-quality|risk-integration|correctness|architecture|security","weight":1,"rationale":"...","prompt_body":"..."}]}.
- Malformed scout output after the plan is ignored by the launcher and must not affect a valid plan.
- Scout sentinels before or inside the summary or plan are fatal format errors.
- Return only the sentinel-delimited response format; do not omit required sentinels.
"""


def _positions(*, lines: Sequence[str], marker: str) -> list[int]:
    return [idx for idx, line in enumerate(lines) if line == marker]


def _plan_contains_standalone_scout_manifest(plan_text: str) -> bool:
    decoder = json.JSONDecoder()
    in_fence = False
    unfenced_lines: list[str] = []
    for line in plan_text.splitlines():
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            unfenced_lines.append(line)
    unfenced_text = plan_text if in_fence else "\n".join(unfenced_lines)
    for match in re.finditer(r"(?m)^\s*\{", unfenced_text):
        try:
            parsed, end = decoder.raw_decode(unfenced_text, match.start())
        except json.JSONDecodeError:
            continue
        line_start = unfenced_text.rfind("\n", 0, match.start()) + 1
        line_end = unfenced_text.find("\n", end)
        if line_end == -1:
            line_end = len(unfenced_text)
        if unfenced_text[line_start:match.start()].strip() or unfenced_text[end:line_end].strip():
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("archetypes"), list):
            return True
    return False


def parse_drafter_output(*, raw_file: Path, plan_tmp: Path, summary_tmp: Path, scout_tmp: Path | None = None) -> DrafterParseResult:
    text = raw_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    pb = _positions(lines=lines, marker="LARCH_PLAN_BEGIN")
    pe = _positions(lines=lines, marker="LARCH_PLAN_END")
    sb = _positions(lines=lines, marker="LARCH_SUMMARY_BEGIN")
    se = _positions(lines=lines, marker="LARCH_SUMMARY_END")
    scb = _positions(lines=lines, marker="LARCH_SCOUT_BEGIN")
    sce = _positions(lines=lines, marker="LARCH_SCOUT_END")
    db = _positions(lines=lines, marker="LARCH_DIALECTIC_BEGIN")
    de = _positions(lines=lines, marker="LARCH_DIALECTIC_END")

    def fail(message: str) -> NoReturn:
        if scout_tmp is not None:
            with contextlib.suppress(FileNotFoundError):
                scout_tmp.unlink()
        raise ValueError(message)

    if len(pb) != 1 or len(pe) != 1:
        fail("invalid plan sentinels: require exactly one LARCH_PLAN_BEGIN and LARCH_PLAN_END")
    if pb[0] >= pe[0]:
        fail("invalid plan sentinels: reversed or empty plan envelope")
    if (len(sb) == 0) != (len(se) == 0) or len(sb) > 1 or len(se) > 1:
        fail("invalid summary sentinels: require zero or one balanced pair")
    if sb and sb[0] >= se[0]:
        fail("invalid summary sentinels: reversed or empty summary envelope")
    if sb and (pb[0] < sb[0] < pe[0] or pb[0] < se[0] < pe[0]):
        fail("invalid sentinels: nested summary inside plan envelope")
    if sb and sb[0] < pb[0] < pe[0] < se[0]:
        fail("invalid sentinels: nested plan inside summary envelope")
    if sb and se[0] >= pb[0]:
        fail("invalid summary sentinels: summary must appear before plan envelope")
    if any(i < pe[0] for i in scb + sce):
        fail("invalid scout sentinels: scout block may appear only after LARCH_PLAN_END")
    if any(pb[0] < i < pe[0] for i in db + de):
        fail("invalid dialectic sentinels: dialectic block may not appear inside plan envelope")
    if sb and any(sb[0] < i < se[0] for i in db + de):
        fail("invalid dialectic sentinels: dialectic block may not appear inside summary envelope")
    plan_lines = lines[pb[0] + 1:pe[0]]
    if not plan_lines or not "".join(plan_lines).strip():
        fail("empty extracted plan body")
    while plan_lines and plan_lines[-1] == "":
        plan_lines.pop()
    plan_body = "\n".join(plan_lines) + "\n"
    diff_lines = plan_grammar.terminal_diff_lines(plan_body)
    if diff_lines is None:
        fail("missing final diff_lines trailer")
    if _plan_contains_standalone_scout_manifest(plan_body):
        fail("invalid plan body: standalone scout manifest JSON is not allowed inside plan")
    _write(path=plan_tmp, text=plan_body)
    summary_written = False
    if sb:
        summary_lines = lines[sb[0] + 1:se[0]]
        if "".join(summary_lines).strip():
            _write(path=summary_tmp, text="\n".join(summary_lines).rstrip("\n") + "\n")
            summary_written = True
        else:
            fail("empty extracted summary body")

    dialectic_payload = ""
    dialectic_parsed = False
    dialectic_fail_reason = ""
    dialectic_sentinels_absent = not db and not de
    dialectic_sentinels_malformed = (len(db) != 1 or len(de) != 1)
    if db and de:
        dialectic_sentinels_malformed = dialectic_sentinels_malformed or db[0] >= de[0] or db[0] <= pe[0] or (scb and de[0] >= scb[0])
    if dialectic_sentinels_absent:
        dialectic_fail_reason = ""
    elif dialectic_sentinels_malformed:
        dialectic_fail_reason = "invalid_dialectic_sentinels"
    else:
        dialectic_text = "\n".join(lines[db[0] + 1:de[0]]).strip()
        if not dialectic_text:
            dialectic_fail_reason = "empty_dialectic_json"
        else:
            try:
                dialectic_payload = json.dumps(design_dialectic.validate_candidates_content(dialectic_text, require_fingerprint=False), separators=(",", ":")) + "\n"
                dialectic_parsed = True
                dialectic_fail_reason = ""
            except Exception:
                dialectic_payload = ""
                dialectic_fail_reason = "invalid_dialectic_json"

    scout_written = False
    scout_fail_reason = ""
    if scout_tmp is not None:
        with contextlib.suppress(FileNotFoundError):
            scout_tmp.unlink()
        if not scb and not sce:
            scout_fail_reason = "absent"
        elif len(scb) != 1 or len(sce) != 1 or scb[0] >= sce[0]:
            scout_fail_reason = "invalid_scout_sentinels"
        else:
            scout_text = "\n".join(lines[scb[0] + 1:sce[0]]).strip()
            if not scout_text:
                scout_fail_reason = "empty_scout_json"
            else:
                try:
                    scout_payload = json.loads(scout_text)
                except json.JSONDecodeError:
                    scout_fail_reason = "json_parse"
                else:
                    if isinstance(scout_payload, dict) and isinstance(scout_payload.get("archetypes"), list):
                        _write(path=scout_tmp, text=json.dumps(scout_payload, separators=(",", ":")) + "\n")
                        scout_written = True
                    else:
                        scout_fail_reason = "invalid_archetypes_shape"
    return DrafterParseResult(
        plan_lines=len(plan_lines),
        diff_lines=diff_lines,
        summary_written=summary_written,
        scout_candidate_written=scout_written,
        scout_fail_reason="" if scout_written else scout_fail_reason,
        dialectic_payload=dialectic_payload,
        dialectic_parsed=dialectic_parsed,
        dialectic_fail_reason=dialectic_fail_reason,
    )


def _validate_drafter_timeout(*, timeout: str, prog: str) -> bool:
    if not _is_positive_int(timeout):
        _err(f"{prog}: --timeout must be a positive integer")
        return False
    if int(timeout, 10) > _MAX_CLAUDE_TIMEOUT:
        _err(f"{prog}: --timeout must be <= 1800")
        return False
    return True


def _reject_control_or_dotdot(raw: str) -> bool:
    return bool(raw) and not _CTRL_RE.search(raw) and ".." not in raw


def _canonical_existing_file_for_drafter(raw: str, *, reject_dotdot: bool = False) -> Path | None:
    if reject_dotdot and not _reject_control_or_dotdot(raw):
        return None
    path = Path(raw)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        return path.parent.resolve(strict=True) / path.name
    except OSError:
        return None


def _canonical_existing_dir_for_drafter(raw: str, *, reject_dotdot: bool = False, reject_symlink: bool = True) -> Path | None:
    if reject_dotdot and not _reject_control_or_dotdot(raw):
        return None
    path = Path(raw)
    if not path.is_dir() or (reject_symlink and path.is_symlink()):
        return None
    try:
        return path.resolve(strict=True)
    except OSError:
        return None


def _canonical_output_for_drafter(raw: str, *, reject_dotdot: bool = False) -> Path | None:
    if reject_dotdot and not _reject_control_or_dotdot(raw):
        return None
    path = Path(raw)
    if path.exists() and path.is_symlink():
        return None
    try:
        return path.parent.resolve(strict=True) / path.name
    except OSError:
        return None


def _write_drafter_status_file(
    *,
    output: Path,
    status: str,
    plan_written: bool,
    plan_lines: int,
    diff_lines: int,
    summary_written: bool,
    scout_written: bool = False,
    scout_fail_reason: str = "",
    dialectic_parsed: bool = False,
    dialectic_raw_pending_written: bool = False,
    dialectic_fail_reason: str = "",
    launched: bool,
    reason: str = "",
) -> None:
    lines = [
        f"STATUS={status}",
        f"PLAN_WRITTEN={str(plan_written).lower()}",
        f"PLAN_LINES={plan_lines}",
        f"DIFF_LINES={diff_lines}",
        f"SUMMARY_WRITTEN={str(summary_written).lower()}",
        f"SCOUT_WRITTEN={str(scout_written).lower()}",
        f"DIALECTIC_CANDIDATES_PARSED={str(dialectic_parsed).lower()}",
        f"DIALECTIC_RAW_PENDING_WRITTEN={str(dialectic_raw_pending_written).lower()}",
    ]
    if scout_fail_reason:
        lines.append(f"SCOUT_FAIL_REASON={scout_fail_reason}")
    if dialectic_fail_reason:
        lines.append(f"DIALECTIC_CANDIDATES_FAIL_REASON={dialectic_fail_reason}")
    lines.append(f"DRAFTER_LAUNCHED={str(launched).lower()}")
    if reason:
        lines.append(f"REASON={reason}")
    tmp = output.with_name(output.name + f".tmp.{os.getpid()}")
    _write(path=tmp, text="\n".join(lines) + "\n")
    tmp.replace(output)


def _write_drafter_dirty_tree_sidecar(output: Path, *, repo_root: Path, baseline: Path | None, launched: bool, tool: str) -> None:
    status = "unknown"
    mode = "prelaunch"
    reason = "launcher-exited-before-drafter-launch"
    if launched:
        current = proc.run(["git", "-C", str(repo_root), "status", "--porcelain"], check=False)
        if baseline is not None and baseline.is_file():
            mode = "baseline-delta"
            if current.returncode == 0:
                base = baseline.read_text(encoding="utf-8", errors="replace")
                if current.stdout == base:
                    status = "clean"
                    reason = f"{tool}-drafter-no-new-mutations"
                else:
                    status = "dirty"
                    reason = f"{tool}-drafter-new-mutations"
            else:
                reason = "git-status-failed"
        elif current.returncode == 0 and current.stdout == "":
            status = "clean"
            mode = "absolute"
            reason = f"{tool}-drafter-clean-working-tree"
        elif current.returncode == 0:
            mode = "no-baseline"
            reason = f"{tool}-drafter-no-usable-baseline"
        else:
            mode = "no-baseline"
            reason = "git-status-failed"
    _write(path=output.with_suffix(output.suffix + ".dirty-tree"), text=f"STATUS={status}\nMODE={mode}\nREASON={reason}\n")


def _filter_drafter_scout(*, design_tmpdir: Path, candidate: Path, filtered: Path) -> tuple[bool, str]:
    if not candidate.is_file() or candidate.stat().st_size == 0:
        return False, "absent"
    status, _count = plan_scout.filter_plan_manifest(input_path=candidate, output_path=filtered, max_archetypes=1)
    if filtered.is_file() and filtered.stat().st_size > 0 and status != "parse-failed":
        try:
            data = json.loads(filtered.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(data, dict) and isinstance(data.get("archetypes"), list):
                filtered.replace(design_tmpdir / "scout-plan-manifest.json")
                return True, ""
    with contextlib.suppress(FileNotFoundError):
        filtered.unlink()
    with contextlib.suppress(FileNotFoundError):
        (design_tmpdir / "scout-plan-manifest.json").unlink()
    return False, "filter_failed"


def _write_dialectic_pending(*, path: Path, payload: str) -> bool:
    """Persist the raw dialectic payload, returning whether it was written."""
    if not payload:
        return False
    try:
        _write(path=path, text=payload)
    except OSError:
        return False
    return True


def _launch_codex_exec_inprocess(*, argv: list[str], stdout_path: Path, stderr_path: Path) -> int:  # type: ignore[reportUnusedFunction]  # intentionally retained as a thin compatibility delegate re-exported from agents.py
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            wrapper_rc = launch_codex_exec_main(argv)
    output_path: Path | None = None
    with contextlib.suppress(ValueError, IndexError):
        output_path = Path(argv[argv.index("--output") + 1])
    launcher_exit = resolve_launcher_exit(captured_text="", output_file=output_path, process_rc=wrapper_rc)
    with stdout_path.open("a", encoding="utf-8") as out:
        _ = out.write(f"LAUNCHER_EXIT={launcher_exit}\n")
        if output_path is not None:
            _ = out.write(f"OUTPUT={output_path}\n")
    return wrapper_rc


def _drafter_token_raw(kind: str) -> str:
    if "draft" in kind:
        return "claude_draft"
    if "scout" in kind:
        return "claude_scout"
    if "voter" in kind:
        return "claude_vote"
    return "claude_review"


def launch_codex_drafter(
    *,
    prompt_file: str,
    output_file: str,
    timeout: str,
    design_tmpdir: str,
    repo_root: str,
    timing_task_kind: str = "codex-plan-draft",
    baseline_porcelain: str = "",
) -> int:
    prog = "agent launch-codex-drafter"
    if not _validate_drafter_timeout(timeout=timeout, prog=prog):
        return 2
    if not timing_task_kind or timing_task_kind.startswith("--"):
        _err(f"{prog}: --timing-task-kind must be a non-empty, non-flag-like value")
        return 2
    prompt = _canonical_existing_file_for_drafter(prompt_file)
    if prompt is None:
        _err(f"{prog}: --prompt-file not found or is a symlink: {prompt_file}")
        return 2
    design = _canonical_existing_dir_for_drafter(design_tmpdir)
    if design is None:
        _err(f"{prog}: --design-tmpdir not found or is a symlink: {design_tmpdir}")
        return 2
    repo = _canonical_existing_dir_for_drafter(repo_root)
    if repo is None:
        _err(f"{prog}: --repo-root not found or is a symlink: {repo_root}")
        return 2
    output = _canonical_output_for_drafter(output_file)
    if output is None:
        _err(f"{prog}: invalid --output-file")
        return 2
    if not _under(path=output, root=design):
        _err(f"{prog}: --output-file outside design tmpdir")
        return 2
    baseline = None
    if baseline_porcelain:
        baseline = _canonical_existing_file_for_drafter(baseline_porcelain)
        if baseline is None or not _under(path=baseline, root=design):
            _err(f"{prog}: --baseline-porcelain outside design tmpdir or invalid")
            return 2
    paths = LauncherPaths.from_output(output)
    for stale in (paths.stderr_tail, paths.failure_diag, paths.token_record):
        with contextlib.suppress(FileNotFoundError):
            stale.unlink()
    _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=False, reason="prelaunch")
    launched = False
    try:
        if not (_under(path=prompt, root=design) or _under(path=prompt, root=repo)):
            _err(f"{prog}: --prompt-file outside allowed roots")
            return 2
        pid = os.getpid()
        raw = design / f"step2b-codex-raw.{pid}.txt"
        plan_tmp = design / f"plan.txt.tmp.{pid}"
        summary_tmp = design / f"plan-summary.md.tmp.{pid}"
        scout_candidate = design / f"scout-plan-manifest.json.candidate.{pid}"
        scout_filtered = design / f"scout-plan-manifest.json.filtered.{pid}"
        dialectic_pending = design / RAW_PENDING
        trusted = design / f"step2b-codex-trusted-instructions.{pid}.txt"
        for path in (raw, plan_tmp, summary_tmp, scout_candidate, scout_filtered, trusted):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        _write(path=trusted, text=_CODEX_DRAFTER_TRUSTED_INSTRUCTIONS)
        launched = True
        try:
            model_args = tuple(resolve_model_args("codex").argv)
        except ValueError as exc:
            _err(f"{prog}: model args failed: {exc}")
            return 1
        prompt_text = prompt.read_text(encoding="utf-8", errors="replace")
        launcher_exit = 1
        with tempfile.TemporaryDirectory(prefix="larch-codex-drafter-home-", dir=tempfile.gettempdir()) as home:
            prep_rc, prep_msg = _prepare_codex_home(Path(home), trusted_instructions_file=str(trusted))
            if prep_rc != 0:
                reason = prep_msg or f"codex auth setup failed (exit {prep_rc})"
                _write_preflight_bundle(output=raw, timeout=timeout, launcher_exit=prep_rc, failure_reason=reason)
            else:
                events = raw.with_suffix(raw.suffix + ".events.jsonl")
                sidecar = raw.with_suffix(raw.suffix + ".sidecar")
                env: dict[str, str] = dict(os.environ)
                env["CODEX_HOME"] = home
                start_holder: list[float] = []
                drafter_request = VendorLaunchRequest(
                    workdir=str(repo),
                    output=str(raw),
                    prompt=prompt_text,
                    model_args=model_args,
                    add_dirs=(str(repo),),
                    timing_task_kind=timing_task_kind,
                )
                drafter_hooks = VendorFamilyHooks(
                    execute=functools.partial(_codex_external_agent_execute, output=raw, timeout=timeout, env=env, cwd=str(repo), stdout_path=events, stderr_path=paths.stderr, start_holder=start_holder),
                    mirror_quota=functools.partial(_codex_events_mirror_quota, events=events, sidecar=sidecar),
                    record_timing=functools.partial(_codex_record_vendor_timing, timing_task_kind=timing_task_kind, output=raw, start_holder=start_holder),
                    record_usage=functools.partial(_codex_record_vendor_usage, events=events, sidecar=sidecar, label="codex_plan_draft", token_record=raw.with_suffix(raw.suffix + ".token-record")),
                )
                drafter_outcome = run_vendor_launch(
                    CODEX_DESCRIPTOR,
                    "read-only",
                    drafter_request,
                    hooks=drafter_hooks,
                    use_config_context=False,
                )
                launcher_exit = drafter_outcome.process_result.exit_code if drafter_outcome.process_result is not None else 1
        token_src = raw.with_suffix(raw.suffix + ".token-record")
        if token_src.is_file() and token_src.stat().st_size > 0:
            shutil.copyfile(token_src, paths.token_record)
        if launcher_exit != 0:
            _write(path=paths.failure_diag, text="CODEX_EXEC_FAILED\n")
            _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="CODEX_EXEC_FAILED")
            source = raw.with_suffix(raw.suffix + ".sidecar") if raw.with_suffix(raw.suffix + ".sidecar").is_file() and raw.with_suffix(raw.suffix + ".sidecar").stat().st_size > 0 else paths.stderr
            if source.is_file() and source.stat().st_size > 0:
                write_failed_agent_stderr_tail(source=source, output=output)
            _write(path=paths.done, text=f"{launcher_exit}\n")
            _emit_kv(key="STATUS", value="ERROR")
            _emit_kv(key="OUTPUT_FILE", value=str(output))
            _emit_kv(key="TOKEN_RECORD", value=str(paths.token_record) if paths.token_record.is_file() else "")
            return launcher_exit
        if not raw.is_file() or raw.stat().st_size == 0:
            _write(path=paths.failure_diag, text="CODEX_EMPTY_OUTPUT\n")
            _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="CODEX_EMPTY_OUTPUT")
            _write(path=paths.done, text="1\n")
            _emit_kv(key="STATUS", value="ERROR")
            _emit_kv(key="OUTPUT_FILE", value=str(output))
            return 1
        try:
            parsed = parse_drafter_output(raw_file=raw, plan_tmp=plan_tmp, summary_tmp=summary_tmp, scout_tmp=scout_candidate)
        except ValueError as exc:
            _write(path=paths.failure_diag, text=f"DELIMITER_EXTRACTION_INVALID\n{exc}\n")
            _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="DELIMITER_EXTRACTION_INVALID")
            _write(path=paths.done, text="99\n")
            _emit_kv(key="STATUS", value="ERROR")
            _emit_kv(key="OUTPUT_FILE", value=str(output))
            return 99
        scout_written = False
        scout_reason = parsed.scout_fail_reason
        if parsed.scout_candidate_written:
            scout_written, scout_reason = _filter_drafter_scout(design_tmpdir=design, candidate=scout_candidate, filtered=scout_filtered)
        dialectic_pending_written = _write_dialectic_pending(path=dialectic_pending, payload=parsed.dialectic_payload)
        plan_tmp.replace(design / "plan.txt")
        if parsed.summary_written:
            summary_tmp.replace(design / "plan-summary.md")
        else:
            with contextlib.suppress(FileNotFoundError):
                summary_tmp.unlink()
        for stale in (paths.stderr, paths.stderr_tail, paths.failure_diag):
            with contextlib.suppress(FileNotFoundError):
                stale.unlink()
        _write_drafter_status_file(output=output, status="OK", plan_written=True, plan_lines=parsed.plan_lines, diff_lines=parsed.diff_lines, summary_written=parsed.summary_written, scout_written=scout_written, scout_fail_reason=scout_reason if not scout_written else "", dialectic_parsed=parsed.dialectic_parsed, dialectic_raw_pending_written=dialectic_pending_written, dialectic_fail_reason=parsed.dialectic_fail_reason if not parsed.dialectic_parsed else "", launched=True)
        _write(path=paths.done, text="0\n")
        _emit_kv(key="STATUS", value="OK")
        _emit_kv(key="OUTPUT_FILE", value=str(output))
        if paths.token_record.is_file():
            _emit_kv(key="TOKEN_RECORD", value=str(paths.token_record))
        else:
            _emit_kv(key="TOKEN_RECORD_MISSING", value="true")
        _emit_kv(key="SCOUT_WRITTEN", value=str(scout_written).lower())
        _emit_kv(key="DIALECTIC_CANDIDATES_PARSED", value=str(parsed.dialectic_parsed).lower())
        _emit_kv(key="DIALECTIC_RAW_PENDING_WRITTEN", value=str(dialectic_pending_written).lower())
        if parsed.dialectic_fail_reason and not parsed.dialectic_parsed:
            _emit_kv(key="DIALECTIC_CANDIDATES_FAIL_REASON", value=parsed.dialectic_fail_reason)
        if scout_reason and not scout_written:
            _emit_kv(key="SCOUT_FAIL_REASON", value=scout_reason)
        return 0
    finally:
        _write_drafter_dirty_tree_sidecar(output, repo_root=repo, baseline=baseline, launched=launched, tool="codex")
        for pattern in ("step2b-codex-raw.*.txt", "plan.txt.tmp.*", "plan-summary.md.tmp.*", "scout-plan-manifest.json.candidate.*", "scout-plan-manifest.json.filtered.*", "step2b-codex-trusted-instructions.*.txt"):
            for path in design.glob(pattern):
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()


def launch_codex_drafter_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent launch-codex-drafter")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--timeout", required=True)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--timing-task-kind", default="codex-plan-draft")
    parser.add_argument("--baseline-porcelain", default="")
    args = parser.parse_args(argv)
    return launch_codex_drafter(**vars(args))


def launch_claude_drafter(
    *,
    model: str,
    prompt_file: str,
    output_file: str,
    timeout: str,
    design_tmpdir: str,
    repo_root: str,
    timing_task_kind: str = "claude-plan-draft",
    baseline_porcelain: str = "",
) -> int:
    prog = "agent launch-claude-drafter"
    path_values = (prompt_file, output_file, design_tmpdir, repo_root, baseline_porcelain)
    if _CTRL_RE.search(model) or not model or any(ch.isspace() for ch in model):
        _err(f"{prog}: --model must be a single non-empty token")
        return 2
    if any(value and not _reject_control_or_dotdot(value) for value in path_values):
        _err(f"{prog}: paths must not contain control characters or '..'")
        return 2
    if not _validate_drafter_timeout(timeout=timeout, prog=prog):
        return 2
    if not timing_task_kind or timing_task_kind.startswith("--"):
        _err(f"{prog}: --timing-task-kind requires a non-empty, non-flag-like value")
        return 2
    design = _canonical_existing_dir_for_drafter(design_tmpdir, reject_dotdot=True)
    repo = _canonical_existing_dir_for_drafter(repo_root, reject_dotdot=True)
    prompt = _canonical_existing_file_for_drafter(prompt_file, reject_dotdot=True)
    output = _canonical_output_for_drafter(output_file, reject_dotdot=True)
    if design is None:
        _err(f"{prog}: invalid --design-tmpdir")
        return 2
    if repo is None:
        _err(f"{prog}: invalid --repo-root")
        return 2
    if prompt is None:
        _err(f"{prog}: invalid --prompt-file")
        return 2
    if output is None:
        _err(f"{prog}: invalid --output-file")
        return 2
    if not _under(path=output, root=design):
        _err(f"{prog}: --output-file outside design tmpdir")
        return 2
    baseline = None
    if baseline_porcelain:
        baseline = _canonical_existing_file_for_drafter(baseline_porcelain, reject_dotdot=True)
        if baseline is None or not _under(path=baseline, root=design):
            _err(f"{prog}: invalid --baseline-porcelain")
            return 2
    paths = LauncherPaths.from_output(output)
    for stale in (paths.stderr_tail, paths.failure_diag, output.with_suffix(output.suffix + ".json"), output.with_suffix(output.suffix + ".result")):
        with contextlib.suppress(FileNotFoundError):
            stale.unlink()
    _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=False, reason="prelaunch")
    launched = False
    start = time.time()
    status = "ERROR"
    exit_code = 2
    try:
        if not (_under(path=prompt, root=design) or _under(path=prompt, root=_plugin_root())):
            _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=False, reason="--prompt-file outside allowed roots")
            _err(f"{prog}: --prompt-file outside allowed roots")
            return 2
        pid = os.getpid()
        json_tmp = output.with_suffix(output.suffix + f".json.{pid}")
        result_tmp = output.with_suffix(output.suffix + f".extract.{pid}")
        plan_tmp = design / f"plan.txt.tmp.{pid}"
        summary_tmp = design / f"plan-summary.md.tmp.{pid}"
        scout_candidate = design / f"scout-plan-manifest.json.candidate.{pid}"
        scout_filtered = design / f"scout-plan-manifest.json.filtered.{pid}"
        dialectic_pending = design / RAW_PENDING
        claude_request = VendorLaunchRequest(
            workdir=str(repo),
            output=str(output),
            prompt="",
            model=model,
            timing_task_kind=timing_task_kind,
        )
        cmd = CLAUDE_DESCRIPTOR.build_argv("drafter-read", claude_request)
        _write(path=paths.meta, text="OUTER_LAUNCHER=claude-drafter\nTIMEOUT=" + timeout + "\nTOOL=claude\nCMD_JSON=" + _json_array(cmd) + "\n")
        launched = True
        prompt_text = prompt.read_text(encoding="utf-8", errors="replace")
        timeout_bin = shutil.which("timeout")
        claude_outcome = run_vendor_launch(
            CLAUDE_DESCRIPTOR,
            "drafter-read",
            claude_request,
            hooks=VendorFamilyHooks(execute=functools.partial(_claude_drafter_execute, timeout_bin=timeout_bin, timeout=timeout, json_tmp=json_tmp, stderr_path=paths.stderr, prompt_text=prompt_text)),
            use_config_context=False,
        )
        exit_code = claude_outcome.process_result.exit_code if claude_outcome.process_result is not None else 127
        if timeout_bin and exit_code == config.EXIT_TIMEOUT:
            status = "TIMEOUT"
            _write_drafter_status_file(output=output, status="TIMEOUT", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="TIMEOUT")
        elif exit_code != 0:
            status = "ERROR"
            _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="CLAUDE_EXIT_NONZERO")
        else:
            try:
                envelope = parse_claude_envelope(json_tmp.read_text(encoding="utf-8"))
                if not envelope.text:
                    raise ValueError(f"claude JSON envelope parse failed: {envelope.status}")
                _write(path=result_tmp, text=envelope.text)
                _record_claude_sub_usage(obj=json.loads(envelope.raw), raw=_drafter_token_raw(timing_task_kind), model=model)
            except (json.JSONDecodeError, ValueError) as exc:
                _write(path=paths.failure_diag, text="CLAUDE_JSON_RESULT_INVALID\n")
                _append(path=paths.stderr, text=f"{exc}\n")
                _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="CLAUDE_JSON_RESULT_INVALID")
                exit_code = 99
                status = "ERROR"
        if exit_code == 0:
            try:
                parsed = parse_drafter_output(raw_file=result_tmp, plan_tmp=plan_tmp, summary_tmp=summary_tmp, scout_tmp=scout_candidate)
            except ValueError as exc:
                _write(path=paths.failure_diag, text=f"DELIMITER_EXTRACTION_INVALID\n{exc}\n")
                _write_drafter_status_file(output=output, status="ERROR", plan_written=False, plan_lines=0, diff_lines=0, summary_written=False, launched=True, reason="DELIMITER_EXTRACTION_INVALID")
                exit_code = 99
                status = "ERROR"
            else:
                scout_written = False
                scout_reason = parsed.scout_fail_reason
                if parsed.scout_candidate_written:
                    scout_written, scout_reason = _filter_drafter_scout(design_tmpdir=design, candidate=scout_candidate, filtered=scout_filtered)
                dialectic_pending_written = _write_dialectic_pending(path=dialectic_pending, payload=parsed.dialectic_payload)
                plan_tmp.replace(design / "plan.txt")
                if parsed.summary_written:
                    summary_tmp.replace(design / "plan-summary.md")
                else:
                    with contextlib.suppress(FileNotFoundError):
                        summary_tmp.unlink()
                _write_drafter_status_file(output=output, status="OK", plan_written=True, plan_lines=parsed.plan_lines, diff_lines=parsed.diff_lines, summary_written=parsed.summary_written, scout_written=scout_written, scout_fail_reason=scout_reason if not scout_written else "", dialectic_parsed=parsed.dialectic_parsed, dialectic_raw_pending_written=dialectic_pending_written, dialectic_fail_reason=parsed.dialectic_fail_reason if not parsed.dialectic_parsed else "", launched=True)
                status = "OK"
        if exit_code != 0:
            stderr_file = paths.stderr
            if stderr_file.is_file() and stderr_file.stat().st_size > 0:
                write_failed_agent_stderr_tail(source=stderr_file, output=output)
            if not paths.failure_diag.is_file() or paths.failure_diag.stat().st_size == 0:
                _compose_failure_diag(output, sink=str(stderr_file))
        else:
            for stale in (paths.stderr_tail, paths.failure_diag):
                with contextlib.suppress(FileNotFoundError):
                    stale.unlink()
        _write(path=paths.done, text=f"{exit_code}\n")
        return exit_code
    finally:
        end = time.time()
        _write_drafter_dirty_tree_sidecar(output, repo_root=repo, baseline=baseline, launched=launched, tool="claude")
        proc.run([sys.executable, str(_PY_CLI), "timing", "record-vendor-task", "--vendor", "claude", "--task-kind", timing_task_kind, "--start-s", str(int(start)), "--end-s", str(int(end)), "--output", str(output), "--exit-code", str(exit_code), "--status", status], check=False)
        _emit_kv(key="STATUS", value=status)
        _emit_kv(key="OUTPUT_FILE", value=str(output))
        _emit_kv(key="ELAPSED", value=int(end - start))
        status_text = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        scout_written = "SCOUT_WRITTEN=true" in status_text
        _emit_kv(key="SCOUT_WRITTEN", value=str(scout_written).lower())
        status_text_for_dialectic = output.read_text(encoding="utf-8", errors="replace") if output.is_file() else ""
        _emit_kv(key="DIALECTIC_CANDIDATES_PARSED", value=str("DIALECTIC_CANDIDATES_PARSED=true" in status_text_for_dialectic).lower())
        _emit_kv(key="DIALECTIC_RAW_PENDING_WRITTEN", value=str("DIALECTIC_RAW_PENDING_WRITTEN=true" in status_text_for_dialectic).lower())
        for pattern in (f"{output.name}.json.*", f"{output.name}.extract.*", "plan.txt.tmp.*", "plan-summary.md.tmp.*", "scout-plan-manifest.json.candidate.*", "scout-plan-manifest.json.filtered.*"):
            for path in (output.parent if pattern.startswith(output.name) else design).glob(pattern):
                with contextlib.suppress(FileNotFoundError):
                    path.unlink()


def launch_claude_drafter_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent launch-claude-drafter")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--timeout", required=True)
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--timing-task-kind", default="claude-plan-draft")
    parser.add_argument("--baseline-porcelain", default="")
    if argv and any(arg in {"--read-tools", "--read-tools-add-dir"} for arg in argv):
        _err("agent launch-claude-drafter: larch wrapper-only read-tool flags are not supported here")
        return 2
    args = parser.parse_args(argv)
    return launch_claude_drafter(**vars(args))
