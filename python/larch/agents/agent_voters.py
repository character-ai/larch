# pyright: reportUnusedCallResult=false
"""Code-review voter dispatcher."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence

from larch.agents import agent_waterfall
from larch.core import external_defaults
from larch.review import findings_ledger
from larch.review import voting
from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.report.tokens import build_panel_dispatch_env, resolve_panel_artifact_dir

_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
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
    voter_1_tool: str = "codex-validity"
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


def _panel_artifact_context(*, review_tmpdir: Path, round_num: int, site: str) -> tuple[Path, Path | None, dict[str, str]]:
    artifact_dir, round_dir = resolve_panel_artifact_dir(review_tmpdir=review_tmpdir, round_num=round_num)
    env = build_panel_dispatch_env(artifact_dir=artifact_dir, site=site, round_num=round_num, round_dir=round_dir)
    return artifact_dir, round_dir, env


def _feedback_enabled() -> bool:
    return os.environ.get(config.ENV_LARCH_VOTER_CALIBRATION_FEEDBACK, "").strip() != "0"


def _fresh_calibration_stats_file(*, review_tmpdir: Path) -> str | None:
    target = review_tmpdir / "voter-calibration-stats.tsv"
    with suppress(FileNotFoundError):
        target.unlink()
    if not _feedback_enabled():
        return None
    fd, tmp = tempfile.mkstemp(prefix=".voter-calibration-stats.", suffix=".tsv", dir=str(review_tmpdir))
    os.close(fd)
    tmp_path = Path(tmp)
    with suppress(FileNotFoundError):
        tmp_path.unlink()
    try:
        log_root = voting._resolve_voter_calibration_log_root(design_tmpdir=None, review_tmpdir=review_tmpdir)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
    except Exception:
        with suppress(FileNotFoundError):
            tmp_path.unlink()
        return None
    result = proc.run(
        [
            *_cli_argv("voter-calibration", "snapshot"),
            "--log-root",
            str(log_root),
            "--out",
            str(tmp_path),
        ]
    )
    if result.returncode != 0 or not tmp_path.is_file() or tmp_path.stat().st_size <= 0:
        with suppress(FileNotFoundError):
            tmp_path.unlink()
        return None
    tmp_path.replace(target)
    return str(target)


def _launchable_base_tools_for_slot(
    policy: VoterSlotPolicy,
    *,
    codex_present: bool,
    cursor_present: bool,
    no_fallback: bool,
) -> list[str]:
    present = {"codex": codex_present, "cursor": cursor_present, "claude": True}
    tools: list[str] = []
    primary = policy.primary_tool
    if present.get(primary, False):
        tools.append(primary)
    if not no_fallback and primary in {"codex", "cursor"}:
        alt = "cursor" if primary == "codex" else "codex"
        if present[alt]:
            tools.append(alt)
        tools.append("claude")
    if primary == "claude" and "claude" not in tools:
        tools.append("claude")
    semantic_tools = set(policy.semantic_labels)
    return [tool for tool in dict.fromkeys(tools) if tool in semantic_tools]


def _make_voter_prompt_file(  # noqa: PLR0913
    *,
    opts: Options,
    review_tmpdir: Path,
    label: str,
    archetype: str = "",
    calibration_stats_file: str | None = None,
    voter_tool: str | None = None,
    output_basename: str | None = None,
) -> str:
    basename = output_basename or (f"{label}-vote-prompt-{voter_tool}.txt" if voter_tool else f"{label}-vote-prompt.txt")
    prompt_file = review_tmpdir / basename
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
    if voter_tool:
        argv.extend(["--voter-tool", voter_tool])
        if calibration_stats_file:
            argv.extend(["--calibration-stats-file", calibration_stats_file])
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


def _build_voter_prompt_files(
    *,
    opts: Options,
    review_tmpdir: Path,
    policies: Sequence[VoterSlotPolicy],
    availability: tuple[bool, bool],
    calibration_stats_file: str | None,
) -> dict[str, dict[str, str]]:
    prompt_files: dict[str, dict[str, str]] = {}
    codex_present, cursor_present = availability
    for policy in policies:
        tools = _launchable_base_tools_for_slot(
            policy,
            codex_present=codex_present,
            cursor_present=cursor_present,
            no_fallback=False,
        )
        prompt_files[policy.prompt_label] = {
            tool: _make_voter_prompt_file(
                opts=opts,
                review_tmpdir=review_tmpdir,
                label=policy.prompt_label,
                archetype=policy.archetype,
                calibration_stats_file=calibration_stats_file,
                voter_tool=tool,
                output_basename=f"{policy.prompt_label}-vote-prompt-{tool}.txt",
            )
            for tool in tools
        }
    return prompt_files


def _write_voter_waterfall_manifest(*, review_tmpdir: Path, policies: Sequence[VoterSlotPolicy], prompt_files: dict[str, dict[str, str]]) -> str:
    manifest = review_tmpdir / "code-voter-slots.ndjson"
    with manifest.open("w", encoding="utf-8") as handle:
        for policy in policies:
            row = {
                "slot": policy.slot_name,
                "tool": policy.primary_tool,
                "output": str(review_tmpdir / policy.output_name),
                "prompt_files": prompt_files.get(policy.prompt_label, {}),
            }
            _ = handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return str(manifest)


def _dispatch_waterfall(*, opts: Options, manifest: str, ctx_args: Sequence[str], review_tmpdir: Path) -> str:
    artifact_dir, _round_dir, panel_env = _panel_artifact_context(review_tmpdir=review_tmpdir, round_num=opts.round_num, site=opts.site)
    result = proc.run(
        [
            *_cli_argv("agent", "dispatch-waterfall"),
            "--slots-file",
            manifest,
            "--panel-artifact-dir",
            str(artifact_dir),
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
            # Grant the terminal Claude voter tier read access to the round dir so it
            # can Read the ballot file without a permission prompt, mirroring the
            # design plan-voter path (issue #5837). Reviewers do not pass this flag.
            "--claude-read-tools-add-dir",
            str(review_tmpdir),
            *ctx_args,
        ],
        env=panel_env,
    )
    if result.returncode != 0:
        _err(f"agent dispatch-voters: agent dispatch-waterfall exited {result.returncode} — proceeding with partial or empty result")
    return result.stdout


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
            logging_util.emit_kv(key="WARN", value=value)
    return all_outputs.split(), all_tools.split(), dispatch_ok


def _read_done_exit_code(path: str) -> str:
    if not path or not Path(path).is_file():
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[0]
    except (OSError, IndexError):
        return ""


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
    logging_util.emit_kv(key="VOTER_1_PATH", value=state.voter_1_path)
    logging_util.emit_kv(key="VOTER_1_TOOL", value=state.voter_1_tool)
    logging_util.emit_kv(key="VOTER_1_STATUS", value=state.voter_1_status)
    logging_util.emit_kv(key="VOTER_1_PARSE_RATE_STATUS", value=state.voter_1_parse_rate_status)
    logging_util.emit_kv(key="VOTER_2_PATH", value=state.voter_2_path)
    logging_util.emit_kv(key="VOTER_2_TOOL", value=state.voter_2_tool)
    logging_util.emit_kv(key="VOTER_2_STATUS", value=state.voter_2_status)
    logging_util.emit_kv(key="VOTER_2_PARSE_RATE_STATUS", value=state.voter_2_parse_rate_status)
    logging_util.emit_kv(key="VOTER_3_PATH", value=state.voter_3_path)
    logging_util.emit_kv(key="VOTER_3_TOOL", value=state.voter_3_tool)
    logging_util.emit_kv(key="VOTER_3_STATUS", value=state.voter_3_status)
    logging_util.emit_kv(key="VOTER_3_PARSE_RATE_STATUS", value=state.voter_3_parse_rate_status)
    logging_util.emit_kv(key="VOTER_PATHS_FILE", value=voter_paths_file)
    logging_util.emit_kv(key="DISPATCH_OK", value=dispatch_ok)


def _semantic_label(*, policy: VoterSlotPolicy, tool: str) -> str:
    return policy.semantic_labels.get(tool, policy.default_label)


def _state_from_bindings(*, bindings: Mapping[str, agent_waterfall.SlotOutputBinding], launched_policies: Sequence[VoterSlotPolicy]) -> DispatchState:
    launched = {policy.slot_name for policy in launched_policies}

    def _resolve(policy: VoterSlotPolicy) -> tuple[str, str, str]:
        if policy.slot_name not in launched:
            return "", policy.default_label, "skipped"
        binding = bindings.get(policy.slot_name, agent_waterfall.SlotOutputBinding())
        if binding.dropped or not binding.path:
            return "", policy.default_label, "failed"
        return binding.path, _semantic_label(policy=policy, tool=binding.tool or policy.primary_tool), "launched"

    path1, tool1, status1 = _resolve(VOTER_SLOT_POLICIES[0])
    path2, tool2, status2 = _resolve(VOTER_SLOT_POLICIES[1])
    path3, tool3, status3 = _resolve(VOTER_SLOT_POLICIES[2])
    return DispatchState(
        voter_1_path=path1,
        voter_2_path=path2,
        voter_3_path=path3,
        voter_1_tool=tool1,
        voter_2_tool=tool2,
        voter_3_tool=tool3,
        voter_1_status=status1,
        voter_2_status=status2,
        voter_3_status=status3,
    )


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
    calibration_stats_file = _fresh_calibration_stats_file(review_tmpdir=review_tmpdir)

    # All voters flow through the shared waterfall so a runtime tool failure (nonzero
    # exit, empty output, or a billing-class block that passes the static probe)
    # re-dispatches to the next tier exactly like a statically-unavailable tool, and
    # the terminal Claude tier can read the ballot. Voter 1 always runs; voters 2/3
    # run only when at least one external tool is present, so a both-external-down
    # panel shrinks to the single Claude anchor rather than spawning redundant
    # same-model voters (issue #5837). All launched slots are dispatched together in
    # one manifest, preserving the parallelism of #5448.
    launched_policies = [VOTER_SLOT_POLICIES[0]]
    if external_voter23:
        launched_policies.extend(VOTER_SLOT_POLICIES[1:])

    prompt_files = _build_voter_prompt_files(
        opts=opts,
        review_tmpdir=review_tmpdir,
        policies=launched_policies,
        availability=(codex_present, cursor_present),
        calibration_stats_file=calibration_stats_file,
    )
    manifest = _write_voter_waterfall_manifest(review_tmpdir=review_tmpdir, policies=launched_policies, prompt_files=prompt_files)
    waterfall_output = _dispatch_waterfall(opts=opts, manifest=manifest, ctx_args=ctx_args, review_tmpdir=review_tmpdir)
    _outputs, _tools, dispatch_ok = _parse_waterfall_output(waterfall_output)
    bindings = agent_waterfall.bind_manifest_slot_outputs(manifest_path=manifest, wf_kv=_kv_from_waterfall(waterfall_output))

    state = _state_from_bindings(bindings=bindings, launched_policies=launched_policies)

    voter1_done_rc = _read_done_exit_code(f"{state.voter_1_path}.done")
    voter2_done_rc = _read_done_exit_code(f"{state.voter_2_path}.done")
    voter3_done_rc = _read_done_exit_code(f"{state.voter_3_path}.done")
    if state.voter_1_status != "skipped" and not (_file_nonempty(state.voter_1_path) and voter1_done_rc == "0"):
        state.voter_1_status = "failed"
    if state.voter_2_status != "skipped" and not (_file_nonempty(state.voter_2_path) and voter2_done_rc == "0"):
        state.voter_2_status = "failed"
    if state.voter_3_status != "skipped" and not (_file_nonempty(state.voter_3_path) and voter3_done_rc == "0"):
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
    if state.voter_1_status not in {"failed", "skipped"}:
        state.voter_1_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="1", voter_file=state.voter_1_path, voter_tool=state.voter_1_tool)
    if state.voter_2_status not in {"failed", "skipped"}:
        state.voter_2_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="2", voter_file=state.voter_2_path, voter_tool=state.voter_2_tool)
    if state.voter_3_status not in {"failed", "skipped"}:
        state.voter_3_parse_rate_status = _run_parse_rate_retry(vpr_args, slot="3", voter_file=state.voter_3_path, voter_tool=state.voter_3_tool)

    expected_judges = len(launched_policies)
    effective_judges = _effective_judges(state)
    if effective_judges < expected_judges:
        warn_msg = f"**⚠ Degraded code-review panel: {effective_judges}/{expected_judges} effective judges produced output.**"
        _err(warn_msg)
        logging_util.emit_kv(key="DEGRADED_PANEL_WARNING", value=warn_msg)

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
