# pyright: reportUnusedCallResult=false
"""Code-review voter dispatcher."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence

import agent_waterfall
import external_defaults
import findings_ledger
import logging_util
import proc

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DISPATCH_LABEL = "agent dispatch-voters"
MODE = "description"
VOTER_PANEL_ROLE = "scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted"

@dataclass(frozen=True)
class VoterSlotPolicy:
    slot_num: str
    slot_name: str
    primary_tool: str
    default_label: str
    archetype: str
    prompt_label: str
    output_name: str
    semantic_labels: Mapping[str, str]


VOTER_SLOT_POLICIES = tuple(
    VoterSlotPolicy(
        policy.slot_num,
        policy.slot_name,
        policy.primary_tool,
        policy.default_label,
        policy.archetype,
        policy.prompt_label,
        policy.output_name,
        dict(policy.semantic_labels),
    )
    for policy in external_defaults.voter_policies("review.voters")
)


@dataclass(frozen=True)
class Options:
    ballot_file: str
    review_tmpdir: str
    codex_available: str
    cursor_available: str
    session_env_path: str = ""
    diff_file: str = ""
    plan_file: str = ""
    round_num: int = 1
    site: str = "review Step 2"


# Mutable: per-voter status / parse-rate fields are updated in place as voters resolve.
@dataclass
class DispatchState:
    voter_1_path: str
    voter_2_path: str = ""
    voter_3_path: str = ""
    voter_1_tool: str = "cursor-validity"
    voter_2_tool: str = "codex-plan-fidelity"
    voter_3_tool: str = "codex-pragmatism"
    voter_1_status: str = "launched"
    voter_2_status: str = "launched"
    voter_3_status: str = "launched"
    voter_1_parse_rate_status: str = "SKIPPED"
    voter_2_parse_rate_status: str = "SKIPPED"
    voter_3_parse_rate_status: str = "SKIPPED"


class ValidationError(RuntimeError):
    pass


def _bounded_prefix_text(*, path: Path, limit: int) -> str:
    try:
        with path.open("rb") as handle:
            return handle.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _plugin_root() -> Path:
    return Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(_PLUGIN_ROOT))).resolve()


def _cli_path() -> Path:
    return _plugin_root() / "python" / "cli.py"


def _cli_argv(*subcommand: str) -> list[str]:
    return [sys.executable, str(_cli_path()), *subcommand]


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _validate_bool(*, raw: str, flag: str) -> None:
    if raw not in {"true", "false"}:
        raise ValidationError(f"agent dispatch-voters: {flag} must be true or false")


def _validate_options(opts: Options) -> None:
    if not opts.ballot_file or not Path(opts.ballot_file).is_file():
        raise ValidationError("agent dispatch-voters: --ballot-file must name a file")
    if not opts.review_tmpdir:
        raise ValidationError("agent dispatch-voters: --review-tmpdir is required")
    _validate_bool(raw=opts.codex_available, flag="--codex-available")
    _validate_bool(raw=opts.cursor_available, flag="--cursor-available")
    if opts.round_num <= 0:
        raise ValidationError("agent dispatch-voters: --round-num must be a positive integer")


def _make_bounded_context_copy(*, review_tmpdir: Path, label: str, src: str, max_bytes: int) -> str:
    if not src or not Path(src).is_file():
        return ""
    dest = review_tmpdir / f"{label}-context.txt"
    with Path(src).open("rb") as handle:
        dest.write_bytes(handle.read(max_bytes))
    return str(dest)


def _context_args(*, review_tmpdir: Path, diff_file: str, plan_file: str) -> tuple[list[str], str, str]:
    bounded_diff = _make_bounded_context_copy(review_tmpdir=review_tmpdir, label="diff", src=diff_file, max_bytes=200000)
    bounded_plan = _make_bounded_context_copy(review_tmpdir=review_tmpdir, label="plan", src=plan_file, max_bytes=60000)
    ctx_args: list[str] = []
    if bounded_diff:
        ctx_args.extend(["--diff-file", bounded_diff])
    if bounded_plan:
        ctx_args.extend(["--plan-file", bounded_plan])
    return ctx_args, bounded_diff, bounded_plan


def _parse_rate_ctx_args(*, bounded_diff: str, bounded_plan: str) -> list[str]:
    args: list[str] = []
    if bounded_diff:
        args.extend(["--ctx=--diff-file", "--ctx", bounded_diff])
    if bounded_plan:
        args.extend(["--ctx=--plan-file", "--ctx", bounded_plan])
    return args


def _make_voter_prompt_file(*, opts: Options, review_tmpdir: Path, label: str, archetype: str = "") -> str:
    prompt_file = review_tmpdir / f"{label}-vote-prompt.txt"
    argv = [
        *_cli_argv("render", "voter"),
        "--ballot-file",
        opts.ballot_file,
        "--panel-role",
        VOTER_PANEL_ROLE,
        "--id-grammar",
        "finding-oos",
        "--verification-context",
        "code",
        "--findings-ledger-file",
        str(findings_ledger.ledger_path(findings_ledger.ledger_root(review_tmpdir, session_env_path=opts.session_env_path))),
    ]
    if archetype:
        argv.extend(["--archetype", archetype])
    result = proc.run(argv)
    with prompt_file.open("w", encoding="utf-8") as handle:
        _ = handle.write(result.stdout)
    if result.returncode != 0:
        _err(f"agent dispatch-voters: python/cli.py render voter failed for {label} voter; aborting")
        raise SystemExit(2)
    if "Read the ballot from this path" not in result.stdout:
        _err(f"agent dispatch-voters: python/cli.py render voter output for {label} voter is missing ballot pointer; aborting")
        raise SystemExit(2)
    return str(prompt_file)


def _launch_claude_voter(*, voter_1_path: str, prompt_file: str, ctx_args: Sequence[str]) -> subprocess.Popen[bytes]:
    stderr_path = f"{voter_1_path}.launcher-stderr"
    with Path(stderr_path).open("wb") as stderr_handle:
        return subprocess.Popen(
            [
                *_cli_argv("agent", "launch-claude-review"),
                "--output",
                voter_1_path,
                "--prompt-file",
                prompt_file,
                "--mode",
                MODE,
                "--role",
                "voter",
                "--timeout",
                "1200",
                "--timing-task-kind",
                "claude-code-voter",
                *ctx_args,
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr_handle,
        )


def _write_voter23_waterfall_manifest(*, review_tmpdir: Path, prompt_files: dict[str, str]) -> str:
    manifest = review_tmpdir / "code-voter-slots.ndjson"
    with manifest.open("w", encoding="utf-8") as handle:
        for policy in VOTER_SLOT_POLICIES[1:]:
            row = {"slot": policy.slot_name, "tool": policy.primary_tool, "output": str(review_tmpdir / policy.output_name), "prompt_file": prompt_files[policy.prompt_label]}
            _ = handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return str(manifest)


def _launch_voter1_cursor_only(*, opts: Options, voter_1_path: str, prompt_file: str, ctx_args: Sequence[str]) -> int:
    stderr_path = f"{voter_1_path}.launcher-stderr"
    with Path(stderr_path).open("wb") as stderr_handle:
        result = proc.run(
            [
                *_cli_argv("agent", "launch-review"),
                "--tool",
                "cursor",
                "--output",
                voter_1_path,
                "--prompt-file",
                prompt_file,
                "--mode",
                MODE,
                "--timeout",
                "1200",
                "--timing-task-kind",
                "cursor-code-voter-validity",
                "--site",
                opts.site,
                *ctx_args,
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr_handle.fileno(),
        )
    return result.returncode


def _dispatch_waterfall(*, opts: Options, manifest: str, ctx_args: Sequence[str]) -> str:
    result = proc.run(
        [
            *_cli_argv("agent", "dispatch-waterfall"),
            "--slots-file",
            manifest,
            "--codex-present",
            opts.codex_available,
            "--cursor-present",
            opts.cursor_available,
            "--mode",
            MODE,
            "--timeout",
            "1200",
            "--model-role",
            "vote",
            "--site",
            opts.site,
            *ctx_args,
        ]
    )
    if result.returncode != 0:
        _err(f"agent dispatch-voters: agent dispatch-waterfall exited {result.returncode} — proceeding with partial or empty result")
    return result.stdout


def _append_voter1_failure(*, opts: Options, review_tmpdir: Path, voter_1_path: str, voter1_rc: int) -> None:
    diag = review_tmpdir / "voter1-diag.txt"
    output_path = Path(voter_1_path)
    output_bytes = 0
    try:
        output_bytes = output_path.stat().st_size
    except OSError:
        output_bytes = 0
    lines = [f"voter1_rc={voter1_rc}", f"output_bytes={output_bytes}"]
    if voter1_rc != 0 and output_path.is_file() and output_path.stat().st_size > 0:
        lines.extend(["--- first 200 bytes of voter output ---", _bounded_prefix_text(path=output_path, limit=200)])
    diag_path = Path(f"{voter_1_path}.diag")
    if diag_path.is_file() and diag_path.stat().st_size > 0:
        lines.extend(["--- first 200 bytes of .diag ---", _bounded_prefix_text(path=diag_path, limit=200)])
    stderr_path = Path(f"{voter_1_path}.launcher-stderr")
    if stderr_path.is_file() and stderr_path.stat().st_size > 0:
        lines.extend(["--- launcher stderr (first 500 bytes) ---", _bounded_prefix_text(path=stderr_path, limit=500)])
    with diag.open("w", encoding="utf-8") as handle:
        _ = handle.write("\n".join(lines) + "\n")

    issues_log = os.environ.get("LARCH_EXECUTION_ISSUES_LOG", "")
    if not issues_log and opts.session_env_path:
        issues_log = str(Path(opts.session_env_path).parent / "execution-issues.md")
    if not issues_log and os.environ.get("IMPLEMENT_TMPDIR"):
        issues_log = str(Path(os.environ["IMPLEMENT_TMPDIR"]) / "execution-issues.md")
    if not issues_log:
        issues_log = str(review_tmpdir / "execution-issues.md")
    status_label = "warning" if voter1_rc == 0 else "failed"
    proc.run(
        [
            *_cli_argv("run-log", "append-failure"),
            "--log",
            issues_log,
            "--site",
            "agent dispatch-voters voter1",
            "--tool",
            "agent launch-claude-review (claude voter)",
            "--exit-code",
            str(voter1_rc),
            "--status-label",
            status_label,
            "--category",
            "Warnings",
            "--output-file",
            str(diag),
            "--redact",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _parse_waterfall_output(output: str) -> tuple[list[str], list[str], str]:
    all_outputs = ""
    all_tools = ""
    dispatch_ok = "true"
    for line in output.splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        if key == "ALL_OUTPUT_FILES":
            all_outputs = value
        elif key == "ALL_OUTPUT_TOOLS":
            all_tools = value
        elif key == "DISPATCH_OK":
            dispatch_ok = value
        elif key == "WARN":
            logging_util.emit_kv("WARN", value)
    return all_outputs.split(), all_tools.split(), dispatch_ok


def _read_done_exit_code(path: str) -> str:
    if not path or not Path(path).is_file():
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return ""


def _wait_sentinels(*, review_tmpdir: Path, sentinels: Sequence[str]) -> tuple[bool, int]:
    voter1_timed_out = False
    wait_rc = 0
    if not sentinels:
        return voter1_timed_out, wait_rc
    timeout = os.environ.get("LARCH_VOTER_WAIT_TIMEOUT", "60")
    fd, wait_out = tempfile.mkstemp(prefix="voter-wait.", dir=str(review_tmpdir))
    os.close(fd)
    wait_path = Path(wait_out)
    try:
        with wait_path.open("wb") as handle:
            result = proc.run(
                [*_cli_argv("agent", "wait-reviewers"), "--timeout", timeout, *sentinels],
                stdout=handle.fileno(),
                stderr=handle.fileno(),
            )
        wait_rc = result.returncode
        lines = wait_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines:
            if line.startswith("TIMEOUT "):
                _err(f"agent dispatch-voters: voter sentinel {line}")
                if line.startswith("TIMEOUT 1 "):
                    voter1_timed_out = True
        if wait_rc != 0:
            _err(f"agent dispatch-voters: wait-reviewers exited {wait_rc} (usage/config error) - proceeding with whatever state exists")
    finally:
        with suppress(FileNotFoundError):
            wait_path.unlink()
    return voter1_timed_out, wait_rc


def _run_parse_rate_retry(vpr_args: Sequence[str], *, slot: str, voter_file: str, voter_tool: str) -> str:
    result = proc.run(
        [
            *_cli_argv("voting", "parse-rate-retry"),
            *vpr_args,
            "--slot",
            slot,
            "--voter-file",
            voter_file,
            "--voter-tool",
            voter_tool,
        ]
    )
    if result.returncode != 0:
        return "NOT_SUBSTANTIVE"
    lines = [line for line in result.stdout.splitlines() if line]
    if not lines:
        return "NOT_SUBSTANTIVE"
    status = lines[-1]
    if status not in {"OK", "NOT_SUBSTANTIVE"}:
        return "NOT_SUBSTANTIVE"
    return status


def _file_nonempty(path: str) -> bool:
    return bool(path) and Path(path).is_file() and Path(path).stat().st_size > 0


def _effective_judges(state: DispatchState) -> int:
    count = 0
    for status, path, parse_rate_status in (
        (state.voter_1_status, state.voter_1_path, state.voter_1_parse_rate_status),
        (state.voter_2_status, state.voter_2_path, state.voter_2_parse_rate_status),
        (state.voter_3_status, state.voter_3_path, state.voter_3_parse_rate_status),
    ):
        if status not in {"failed", "skipped"} and parse_rate_status != "NOT_SUBSTANTIVE" and _file_nonempty(path):
            count += 1
    return count


def _write_voter_paths_file(*, review_tmpdir: Path, state: DispatchState) -> str:
    paths_file = review_tmpdir / "code-voter-paths.txt"
    fd, tmp = tempfile.mkstemp(prefix=".code-voter-paths.", dir=str(review_tmpdir))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        if state.voter_1_path:
            _ = handle.write(state.voter_1_path + "\n")
        if state.voter_2_status != "skipped" and state.voter_2_path:
            _ = handle.write(state.voter_2_path + "\n")
        if state.voter_3_status != "skipped" and state.voter_3_path:
            _ = handle.write(state.voter_3_path + "\n")
    Path(tmp).replace(paths_file)
    return str(paths_file)


def _emit_final_kvs(*, state: DispatchState, voter_paths_file: str, dispatch_ok: str) -> None:
    logging_util.emit_kv("VOTER_1_PATH", state.voter_1_path)
    logging_util.emit_kv("VOTER_1_TOOL", state.voter_1_tool)
    logging_util.emit_kv("VOTER_1_STATUS", state.voter_1_status)
    logging_util.emit_kv("VOTER_1_PARSE_RATE_STATUS", state.voter_1_parse_rate_status)
    logging_util.emit_kv("VOTER_2_PATH", state.voter_2_path)
    logging_util.emit_kv("VOTER_2_TOOL", state.voter_2_tool)
    logging_util.emit_kv("VOTER_2_STATUS", state.voter_2_status)
    logging_util.emit_kv("VOTER_2_PARSE_RATE_STATUS", state.voter_2_parse_rate_status)
    logging_util.emit_kv("VOTER_3_PATH", state.voter_3_path)
    logging_util.emit_kv("VOTER_3_TOOL", state.voter_3_tool)
    logging_util.emit_kv("VOTER_3_STATUS", state.voter_3_status)
    logging_util.emit_kv("VOTER_3_PARSE_RATE_STATUS", state.voter_3_parse_rate_status)
    logging_util.emit_kv("VOTER_PATHS_FILE", voter_paths_file)
    logging_util.emit_kv("DISPATCH_OK", dispatch_ok)


def _semantic_label(*, policy: VoterSlotPolicy, tool: str) -> str:
    return policy.semantic_labels.get(tool, policy.default_label)


def _state_from_voter23_bindings(*, review_tmpdir: Path, bindings: Mapping[str, agent_waterfall.SlotOutputBinding]) -> tuple[str, str, str, str]:
    del review_tmpdir
    policy2 = VOTER_SLOT_POLICIES[1]
    policy3 = VOTER_SLOT_POLICIES[2]
    binding2 = bindings.get(policy2.slot_name, agent_waterfall.SlotOutputBinding())
    binding3 = bindings.get(policy3.slot_name, agent_waterfall.SlotOutputBinding())
    if binding2.dropped or not binding2.path:
        path2, tool2 = "", ""
    else:
        path2 = binding2.path
        tool2 = _semantic_label(policy=policy2, tool=binding2.tool or policy2.primary_tool)
    if binding3.dropped or not binding3.path:
        path3, tool3 = "", ""
    else:
        path3 = binding3.path
        tool3 = _semantic_label(policy=policy3, tool=binding3.tool or policy3.primary_tool)
    return path2, path3, tool2, tool3


def dispatch_voters(opts: Options) -> int:
    _validate_options(opts)
    if not _cli_path().is_file():
        _err(f"agent dispatch-voters: missing python/cli.py at {_cli_path()}")
        return 2
    review_tmpdir = Path(opts.review_tmpdir)
    review_tmpdir.mkdir(parents=True, exist_ok=True)
    ctx_args, bounded_diff, bounded_plan = _context_args(review_tmpdir=review_tmpdir, diff_file=opts.diff_file, plan_file=opts.plan_file)

    cursor_present = opts.cursor_available == "true"
    codex_present = opts.codex_available == "true"
    external_voter23 = cursor_present or codex_present
    prompt_files: dict[str, str] = {}
    for policy in VOTER_SLOT_POLICIES:
        if policy.slot_num == "1" or external_voter23:
            prompt_files[policy.prompt_label] = _make_voter_prompt_file(opts=opts, review_tmpdir=review_tmpdir, label=policy.prompt_label, archetype=policy.archetype)

    if cursor_present:
        voter_1_path = str(review_tmpdir / VOTER_SLOT_POLICIES[0].output_name)
        voter1_rc = _launch_voter1_cursor_only(opts=opts, voter_1_path=voter_1_path, prompt_file=prompt_files["validity"], ctx_args=ctx_args)
        voter1_process = None
        voter_1_tool = "cursor-validity"
    else:
        voter_1_path = str(review_tmpdir / "claude-vote-output.txt")
        voter1_process = _launch_claude_voter(voter_1_path=voter_1_path, prompt_file=prompt_files["validity"], ctx_args=ctx_args)
        voter1_rc = -1
        voter_1_tool = "claude"

    voter_2_path = str(review_tmpdir / VOTER_SLOT_POLICIES[1].output_name) if external_voter23 else ""
    voter_3_path = str(review_tmpdir / VOTER_SLOT_POLICIES[2].output_name) if external_voter23 else ""
    voter_2_tool = "codex-plan-fidelity"
    voter_3_tool = "codex-pragmatism"
    voter_2_status = "launched" if external_voter23 else "skipped"
    voter_3_status = "launched" if external_voter23 else "skipped"
    sentinels: list[str] = []
    dispatch_ok = "true"

    if external_voter23:
        manifest = _write_voter23_waterfall_manifest(review_tmpdir=review_tmpdir, prompt_files=prompt_files)
        waterfall_output = _dispatch_waterfall(opts=opts, manifest=manifest, ctx_args=ctx_args)
        _outputs, _tools, raw_dispatch_ok = _parse_waterfall_output(waterfall_output)
        dispatch_ok = raw_dispatch_ok
        bindings = agent_waterfall.bind_manifest_slot_outputs(manifest_path=manifest, wf_kv=_kv_from_waterfall(waterfall_output))
        voter_2_path, voter_3_path, voter_2_tool, voter_3_tool = _state_from_voter23_bindings(review_tmpdir=review_tmpdir, bindings=bindings)
        if voter_2_path:
            sentinels.append(f"{voter_2_path}.done")
        else:
            voter_2_status = "failed"
        if voter_3_path:
            sentinels.append(f"{voter_3_path}.done")
        else:
            voter_3_status = "failed"

    if voter1_process is not None:
        voter1_rc = voter1_process.wait()
    if voter1_rc != 0 or not _file_nonempty(voter_1_path):
        _append_voter1_failure(opts=opts, review_tmpdir=review_tmpdir, voter_1_path=voter_1_path, voter1_rc=voter1_rc)
    if cursor_present and not Path(f"{voter_1_path}.done").is_file() and voter1_rc == 0 and _file_nonempty(voter_1_path):
        Path(f"{voter_1_path}.done").write_text("0\n", encoding="utf-8")
    sentinels.insert(0, f"{voter_1_path}.done")
    voter1_timed_out, wait_rc = _wait_sentinels(review_tmpdir=review_tmpdir, sentinels=sentinels)
    if (
        not Path(f"{voter_1_path}.done").is_file()
        and voter1_rc == 0
        and _file_nonempty(voter_1_path)
        and not voter1_timed_out
        and wait_rc == 0
    ):
        Path(f"{voter_1_path}.done").write_text("0\n", encoding="utf-8")

    state = DispatchState(
        voter_1_path=voter_1_path,
        voter_2_path=voter_2_path,
        voter_3_path=voter_3_path,
        voter_1_tool=voter_1_tool,
        voter_2_tool=voter_2_tool,
        voter_3_tool=voter_3_tool,
        voter_2_status=voter_2_status,
        voter_3_status=voter_3_status,
    )

    voter1_done_rc = _read_done_exit_code(f"{state.voter_1_path}.done")
    voter2_done_rc = _read_done_exit_code(f"{state.voter_2_path}.done")
    voter3_done_rc = _read_done_exit_code(f"{state.voter_3_path}.done")
    if not (_file_nonempty(state.voter_1_path) and voter1_done_rc == "0"):
        state.voter_1_status = "failed"
    if not (state.voter_2_status == "skipped" or (_file_nonempty(state.voter_2_path) and voter2_done_rc == "0")):
        state.voter_2_status = "failed"
    if not (state.voter_3_status == "skipped" or (_file_nonempty(state.voter_3_path) and voter3_done_rc == "0")):
        state.voter_3_status = "failed"

    vpr_args = [
        "--ballot-file",
        opts.ballot_file,
        "--id-grammar",
        "finding-oos",
        "--review-tmpdir",
        opts.review_tmpdir,
        "--plugin-root",
        str(_plugin_root()),
        "--dispatch-label",
        DISPATCH_LABEL,
        *_parse_rate_ctx_args(bounded_diff=bounded_diff, bounded_plan=bounded_plan),
    ]
    if state.voter_1_status != "failed":
        state.voter_1_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="1", voter_file=state.voter_1_path, voter_tool=state.voter_1_tool)
    if state.voter_2_status not in {"failed", "skipped"}:
        state.voter_2_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="2", voter_file=state.voter_2_path, voter_tool=state.voter_2_tool)
    if state.voter_3_status not in {"failed", "skipped"}:
        state.voter_3_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="3", voter_file=state.voter_3_path, voter_tool=state.voter_3_tool)

    expected_judges = 3 if external_voter23 else 1
    effective_judges = _effective_judges(state)
    if effective_judges < expected_judges:
        warn_msg = f"**⚠ Degraded code-review panel: {effective_judges}/{expected_judges} effective judges produced output.**"
        _err(warn_msg)
        logging_util.emit_kv("DEGRADED_PANEL_WARNING", warn_msg)

    voter_paths_file = _write_voter_paths_file(review_tmpdir=review_tmpdir, state=state)
    dispatch_ok = "true" if effective_judges > 0 and state.voter_1_status != "failed" and dispatch_ok != "false" else "false"
    _emit_final_kvs(state=state, voter_paths_file=voter_paths_file, dispatch_ok=dispatch_ok)
    return 0


def _kv_from_waterfall(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            data[key] = value
    return data

def _parse_args(argv: Sequence[str]) -> Options | int:
    parser = argparse.ArgumentParser(prog="agent dispatch-voters")
    parser.add_argument("--ballot-file", required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--codex-available", required=True)
    parser.add_argument("--cursor-available", required=True)
    parser.add_argument("--session-env-path", default=os.environ.get("SESSION_ENV_PATH", ""))
    parser.add_argument("--diff-file", default="")
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--round-num", default="1")
    parser.add_argument("--site", default="review Step 2")
    args = parser.parse_args(argv)
    if not str(args.round_num).isdigit() or int(str(args.round_num), 10) <= 0:
        raise ValidationError("agent dispatch-voters: --round-num must be a positive integer")
    site = str(args.site)
    if not site.strip() or site.startswith("--"):
        raise ValidationError("agent dispatch-voters: --site requires a non-empty, non-flag-like value")
    if re.search(r"[\x00-\x1f\x7f]", site):
        raise ValidationError("agent dispatch-voters: --site must not contain control characters")
    return Options(
        ballot_file=str(args.ballot_file),
        review_tmpdir=str(args.review_tmpdir),
        codex_available=str(args.codex_available),
        cursor_available=str(args.cursor_available),
        session_env_path=str(args.session_env_path),
        diff_file=str(args.diff_file),
        plan_file=str(args.plan_file),
        round_num=int(str(args.round_num), 10),
        site=site,
    )


def dispatch_voters_main(argv: list[str]) -> int:
    logging_util.quiet_init(argv0="agent dispatch-voters")
    try:
        parsed = _parse_args(argv=argv)
        if isinstance(parsed, int):
            return parsed
        return dispatch_voters(parsed)
    except ValidationError as exc:
        _err(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(dispatch_voters_main(sys.argv[1:]))
