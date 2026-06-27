# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
"""Three-phase waterfall dispatcher for external review slots."""

from __future__ import annotations

import atexit
import contextlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping, Sequence

from larch.agents import agents
from larch.core import logging_util
from larch.core import proc

REPO_ROOT = Path(__file__).resolve().parents[3]
PY_CLI = REPO_ROOT / "python" / "cli.py"
TIMING_KIND_MAX = 64
MIN_STRAGGLER_PHASE_SLOTS = 2

_USAGE = (
    "Usage: dispatch-with-waterfall.sh --slots-file FILE --codex-present true|false "
    "--cursor-present true|false --mode diff|description [--paths-file FILE] [--skip-invalid-slots] [--site SITE] [context flags]. "
    "Default paths-file is SLOTS_FILE.output-files; its parent directory must already exist. "
    "--straggler-cutoff enables the adaptive reviewer straggler deadline for this dispatch. "
    "--model-role default|review|vote|fix forwards an explicit Codex model role to Codex launches. "
    "Stdout KVs include ALL_OUTPUT_FILES_PATH, ALL_OUTPUT_FILES, ALL_OUTPUT_TOOLS, DISPATCH_OK, WARN, …"
)
_POSIX_CLASS_REPLACEMENTS = {
    "[[:alnum:]]": r"[A-Za-z0-9]",
    "[[:alpha:]]": r"[A-Za-z]",
    "[[:blank:]]": r"[ \t]",
    "[[:cntrl:]]": r"[\x00-\x1f\x7f]",
    "[[:digit:]]": r"\d",
    "[[:graph:]]": r"[^\s]",
    "[[:lower:]]": r"[a-z]",
    "[[:print:]]": r"[^\x00-\x1f\x7f]",
    "[[:punct:]]": r"[^\w\s]",
    "[[:space:]]": r"\s",
    "[[:upper:]]": r"[A-Z]",
    "[[:xdigit:]]": r"[A-Fa-f0-9]",
    "[[:word:]]": r"\w",
}


@dataclass(frozen=True)
class Slot:
    name: str
    tool: str
    output: str
    agent: str
    prompt_file: str
    model_role: str = ""


@dataclass(frozen=True)
class InvalidSlotDrop:
    line: int
    slot: str
    snippet: str
    message: str


@dataclass(frozen=True)
class Options:
    slots_file: str
    codex_present: bool
    cursor_present: bool
    mode: str
    diff_file: str = ""
    commit_count: str = ""
    plan_file: str = ""
    feature_file: str = ""
    scope_files: str = ""
    description_text: str = ""
    timeout: str = "1800"
    fallback_counter_file: str = ""
    competition_notice: bool = False
    competition_notice_file: str = ""
    paths_file: str = ""
    require_result_pattern: str = ""
    require_first_line_pattern: str = ""
    no_fallback: bool = False
    straggler_cutoff: bool = False
    skip_invalid_slots: bool = False
    site: str = "review Step 2"
    session_env_path: str = ""
    model_role: str = ""


@dataclass(frozen=True)
class SlotOutputBinding:
    path: str = ""
    tool: str = ""
    dropped: bool = False


@dataclass(frozen=True)
class DropState:
    reason: str = ""
    detail: str = ""


@dataclass(frozen=True)
class PhaseLaunch:
    idx: int
    output: str
    tool: str
    process: subprocess.Popen[bytes]
    stderr_handle: object


class ValidationError(RuntimeError):
    pass


_ACTIVE_LAUNCHES: list[PhaseLaunch] = []
_DISPATCH_LAUNCHES: list[PhaseLaunch] = []

def posix_ere_to_python(pattern: str) -> str:
    """Translate the POSIX character classes used by shell callers."""
    translated = pattern
    for needle, replacement in _POSIX_CLASS_REPLACEMENTS.items():
        translated = translated.replace(needle, replacement)
    return translated


def _compile_pattern(*, raw: str, flag: str) -> re.Pattern[str] | None:
    if not raw:
        return None
    try:
        return re.compile(posix_ere_to_python(raw), re.MULTILINE)
    except re.error as exc:
        raise ValidationError(f"dispatch-with-waterfall.sh: {flag} is not a valid ERE: {raw}") from exc


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _usage() -> None:
    _err(_USAGE)


def _bool_raw(*, raw: str, flag: str) -> bool:
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ValidationError(f"dispatch-with-waterfall.sh: {flag} must be true or false")


def _parse_args(argv: Sequence[str]) -> Options | int:
    values: dict[str, str | bool] = {
        "slots_file": "",
        "codex_present": "",
        "cursor_present": "",
        "mode": "",
        "diff_file": "",
        "commit_count": "",
        "plan_file": "",
        "feature_file": "",
        "scope_files": "",
        "description_text": "",
        "timeout": "1800",
        "fallback_counter_file": "",
        "competition_notice": False,
        "competition_notice_file": "",
        "paths_file": "",
        "require_result_pattern": "",
        "require_first_line_pattern": "",
        "no_fallback": False,
        "straggler_cutoff": False,
        "skip_invalid_slots": False,
        "site": "review Step 2",
        "session_env_path": "",
        "model_role": "",
    }
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        key_map = {
            "--slots-file": "slots_file",
            "--mode": "mode",
            "--diff-file": "diff_file",
            "--commit-count": "commit_count",
            "--plan-file": "plan_file",
            "--feature-file": "feature_file",
            "--scope-files": "scope_files",
            "--description-text": "description_text",
            "--timeout": "timeout",
            "--fallback-counter-file": "fallback_counter_file",
            "--competition-notice-file": "competition_notice_file",
            "--paths-file": "paths_file",
            "--require-result-pattern": "require_result_pattern",
            "--require-first-line-pattern": "require_first_line_pattern",
            "--site": "site",
            "--session-env-path": "session_env_path",
            "--model-role": "model_role",
        }
        if arg in {"--codex-present", "--codex-available"}:
            if idx + 1 >= len(argv):
                raise ValidationError("dispatch-with-waterfall.sh: --codex-present requires a value")
            values["codex_present"] = argv[idx + 1]
            idx += 2
        elif arg in {"--cursor-present", "--cursor-available"}:
            if idx + 1 >= len(argv):
                raise ValidationError("dispatch-with-waterfall.sh: --cursor-present requires a value")
            values["cursor_present"] = argv[idx + 1]
            idx += 2
        elif arg in key_map:
            if idx + 1 >= len(argv):
                raise ValidationError(f"dispatch-with-waterfall.sh: {arg} requires a value")
            values[key_map[arg]] = argv[idx + 1]
            idx += 2
        elif arg == "--competition-notice":
            values["competition_notice"] = True
            idx += 1
        elif arg == "--no-fallback":
            values["no_fallback"] = True
            idx += 1
        elif arg == "--straggler-cutoff":
            values["straggler_cutoff"] = True
            idx += 1
        elif arg == "--skip-invalid-slots":
            values["skip_invalid_slots"] = True
            idx += 1
        elif arg == "--help":
            _usage()
            return 0
        else:
            _err(f"dispatch-with-waterfall.sh: unknown option: {arg}")
            _usage()
            return 2
    slots_file = str(values["slots_file"])
    if not slots_file or not Path(slots_file).is_file():
        raise ValidationError("dispatch-with-waterfall.sh: --slots-file must name a file")
    codex_present = _bool_raw(raw=str(values["codex_present"]), flag="--codex-present")
    cursor_present = _bool_raw(raw=str(values["cursor_present"]), flag="--cursor-present")
    mode = str(values["mode"])
    if mode not in {"diff", "description"}:
        raise ValidationError("dispatch-with-waterfall.sh: --mode must be diff or description")
    timeout = str(values["timeout"])
    if not timeout.isdigit() or int(timeout, 10) == 0:
        raise ValidationError("dispatch-with-waterfall.sh: --timeout must be a positive integer")
    site = str(values["site"])
    if not site.strip() or site.startswith("--"):
        raise ValidationError("dispatch-with-waterfall.sh: --site requires a non-empty, non-flag-like value")
    if re.search(r"[\x00-\x1f\x7f]", site):
        raise ValidationError("dispatch-with-waterfall.sh: --site must not contain control characters")
    model_role = str(values["model_role"])
    if model_role and model_role not in {"default", "review", "vote", "fix"}:
        raise ValidationError("dispatch-with-waterfall.sh: --model-role must be default, review, vote, or fix")
    return Options(
        slots_file=slots_file,
        codex_present=codex_present,
        cursor_present=cursor_present,
        mode=mode,
        diff_file=str(values["diff_file"]),
        commit_count=str(values["commit_count"]),
        plan_file=str(values["plan_file"]),
        feature_file=str(values["feature_file"]),
        scope_files=str(values["scope_files"]),
        description_text=str(values["description_text"]),
        timeout=timeout,
        fallback_counter_file=str(values["fallback_counter_file"]),
        competition_notice=bool(values["competition_notice"]),
        competition_notice_file=str(values["competition_notice_file"]),
        paths_file=str(values["paths_file"]),
        require_result_pattern=str(values["require_result_pattern"]),
        require_first_line_pattern=str(values["require_first_line_pattern"]),
        no_fallback=bool(values["no_fallback"]),
        straggler_cutoff=bool(values["straggler_cutoff"]),
        skip_invalid_slots=bool(values["skip_invalid_slots"]),
        site=site,
        session_env_path=str(values["session_env_path"]),
        model_role=model_role,
    )


def _invalid_drop_for_row(*, line_no: int, row: str, message: str) -> InvalidSlotDrop:
    slot = ""
    with contextlib.suppress(json.JSONDecodeError):
        parsed: object = json.loads(row)
        if isinstance(parsed, dict):
            slot_value: object | None = parsed.get("slot")
            if isinstance(slot_value, str) and slot_value:
                slot = slot_value
    snippet = _flatten_field(row)[:200]
    return InvalidSlotDrop(line=line_no, slot=slot, snippet=snippet, message=message)


def _validated_model_role(*, value: object | None, slot: str, row: str) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    if value and value not in {"default", "review", "vote", "fix"}:
        raise ValidationError(
            f"dispatch-with-waterfall.sh: slot '{slot}' model_role must be default, review, vote, or fix"
        )
    return value


def _parse_slot_row(row: str) -> Slot:
    try:
        data: object = json.loads(row)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    slot: object | None = data.get("slot")
    tool: object | None = data.get("tool")
    output: object | None = data.get("output")
    agent = data.get("agent", "")
    prompt_file = data.get("prompt_file", "")
    if not isinstance(slot, str) or not slot:
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    if not isinstance(tool, str) or tool not in {"codex", "cursor"}:
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    tool_value = tool
    if not isinstance(output, str) or not output:
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    if "\n" in output or "\r" in output:
        raise ValidationError(
            "dispatch-with-waterfall.sh: slot "
            f"'{slot}' output path contains a newline or carriage return (line-oriented paths-file contract)"
        )
    if agent is None:
        agent = ""
    if prompt_file is None:
        prompt_file = ""
    if not isinstance(agent, str) or not isinstance(prompt_file, str):
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid slot row: {row}")
    if agent and prompt_file:
        raise ValidationError(f"dispatch-with-waterfall.sh: slot '{slot}' must not set both agent and prompt_file")
    if not agent and not prompt_file:
        raise ValidationError(f"dispatch-with-waterfall.sh: slot '{slot}' must set either agent or prompt_file")
    model_role_value: object | None = data.get("model_role", "")
    model_role = _validated_model_role(value=model_role_value, slot=slot, row=row)  # type: ignore[reportUnknownArgumentType]
    return Slot(slot, tool_value, output, agent, prompt_file, model_role)


def _load_slots_with_invalid_drops(slots_file: str, *, skip_invalid: bool) -> tuple[list[Slot], list[InvalidSlotDrop]]:
    slots: list[Slot] = []
    invalid_drops: list[InvalidSlotDrop] = []
    for line_no, row in enumerate(Path(slots_file).read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not row:
            continue
        try:
            slots.append(_parse_slot_row(row))
        except ValidationError as exc:
            if not skip_invalid:
                raise
            invalid_drops.append(_invalid_drop_for_row(line_no=line_no, row=row, message=str(exc)))
    if not slots and (not skip_invalid or not invalid_drops):
        raise ValidationError("dispatch-with-waterfall.sh: slots file contains no slot rows")
    return slots, invalid_drops


def _load_slots(slots_file: str) -> list[Slot]:  # pyright: ignore[reportUnusedFunction]
    slots, _invalid_drops = _load_slots_with_invalid_drops(slots_file, skip_invalid=False)
    return slots


def _output_for_phase(*, base: str, phase: str) -> str:
    if phase == "phase1":
        return base
    if base.endswith(".txt"):
        return f"{base[:-4]}-{phase}.txt"
    return f"{base}-{phase}"


def _present_for_tool(*, tool: str, opts: Options) -> bool:
    if tool == "codex":
        return opts.codex_present
    if tool == "cursor":
        return opts.cursor_present
    return False


def _other_tool(tool: str) -> str:
    return "cursor" if tool == "codex" else "codex"


def _common_args(opts: Options) -> list[str]:
    args: list[str] = []
    pairs = [
        ("--diff-file", opts.diff_file),
        ("--commit-count", opts.commit_count),
        ("--plan-file", opts.plan_file),
        ("--feature-file", opts.feature_file),
        ("--scope-files", opts.scope_files),
        ("--description-text", opts.description_text),
    ]
    for flag, value in pairs:
        if value:
            args.extend([flag, value])
    if opts.session_env_path:
        args.extend(["--session-env-path", opts.session_env_path])
    return args


def _timing_kind(*, tool: str, phase: str, slot_name: str) -> str:
    timing = f"{tool}-{phase}-{slot_name}"
    if len(timing) > TIMING_KIND_MAX:
        timing = timing[:TIMING_KIND_MAX].removesuffix("-")
    return timing


def _launch_slot(*, idx: int, phase: str, tool: str, output: str, slots: Sequence[Slot], opts: Options) -> PhaseLaunch:
    slot = slots[idx]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if tool == "claude":
        argv = [
            sys.executable,
            str(PY_CLI),
            "agent",
            "launch-claude-review",
            "--output",
            output,
        ]
        argv.extend(["--prompt-file", slot.prompt_file] if slot.prompt_file else ["--agent-file", slot.agent])
    else:
        argv = [
            sys.executable,
            str(PY_CLI),
            "agent",
            "launch-review",
            "--tool",
            tool,
            "--output",
            output,
        ]
        argv.extend(["--prompt-file", slot.prompt_file] if slot.prompt_file else ["--agent-file", slot.agent])
    argv.extend(["--mode", opts.mode, "--timeout", opts.timeout, "--timing-task-kind", _timing_kind(tool=tool, phase=phase, slot_name=slot.name)])
    argv.extend(_common_args(opts))
    if tool != "claude":
        argv.extend(["--site", opts.site])
        if opts.competition_notice:
            argv.append("--competition-notice")
        if opts.competition_notice_file:
            argv.extend(["--competition-notice-file", opts.competition_notice_file])
        if tool == "codex":
            effective_role = slot.model_role or opts.model_role
            if effective_role:
                argv.extend(["--model-role", effective_role])
    stderr_handle = Path(f"{output}.launch-stderr").open("wb")  # noqa: SIM115  # pylint: disable=consider-using-with
    try:
        process = subprocess.Popen(  # pylint: disable=consider-using-with
            argv, stdout=subprocess.DEVNULL, stderr=stderr_handle, start_new_session=True
        )
    except Exception:
        stderr_handle.close()
        raise
    launch = PhaseLaunch(idx=idx, output=output, tool=tool, process=process, stderr_handle=stderr_handle)
    _ACTIVE_LAUNCHES.append(launch)
    _DISPATCH_LAUNCHES.append(launch)
    return launch


def _descendants(pid: int) -> list[int]:
    result = proc.run(["pgrep", "-P", str(pid)])
    children: list[int] = []
    if result.returncode != 0:
        return children
    for line in result.stdout.splitlines():
        if line.strip().isdigit():
            child = int(line.strip())
            children.extend(_descendants(child))
            children.append(child)
    return children


def _terminate_launch(launch: PhaseLaunch) -> None:
    pid = launch.process.pid
    with contextlib.suppress(OSError):
        os.killpg(pid, signal.SIGTERM)
    for child in _descendants(pid):
        with contextlib.suppress(OSError):
            os.kill(child, signal.SIGTERM)
    if launch.process.poll() is None:
        try:
            _ = launch.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                launch.process.kill()
            _ = launch.process.wait()
    with contextlib.suppress(OSError):
        launch.stderr_handle.close()  # type: ignore[attr-defined]


def _kill_active_launches() -> None:
    for launch in _DISPATCH_LAUNCHES[:]:
        _terminate_launch(launch)
    _ACTIVE_LAUNCHES.clear()
    _DISPATCH_LAUNCHES.clear()


def _sigterm_handler(_signum: int, _frame: object) -> None:  # lint-keyword-only: ok signal handler callback
    _kill_active_launches()
    raise SystemExit(143)


def _straggler_multiple() -> float:
    raw = os.environ.get("LARCH_REVIEWER_STRAGGLER_MULTIPLE", "2.5")
    try:
        return float(raw)
    except ValueError:
        return 2.5


def _straggler_floor() -> int:
    raw = os.environ.get("LARCH_REVIEWER_STRAGGLER_FLOOR_SECONDS", "300")
    try:
        return max(int(raw), 0)
    except ValueError:
        return 300


def _finish_launch(*, launch: PhaseLaunch, rc: int | None) -> None:
    with contextlib.suppress(OSError):
        launch.stderr_handle.close()  # type: ignore[attr-defined]
    if not Path(f"{launch.output}.done").is_file():
        _ = Path(f"{launch.output}.done").write_text(f"{rc if rc is not None else -signal.SIGTERM}\n", encoding="utf-8")
    if launch in _ACTIVE_LAUNCHES:
        _ACTIVE_LAUNCHES.remove(launch)
    if launch in _DISPATCH_LAUNCHES:
        _DISPATCH_LAUNCHES.remove(launch)


def _reap_phase(
    *, launches: Sequence[PhaseLaunch],
    opts: Options,
    result_pattern: re.Pattern[str] | None,
    first_line_pattern: re.Pattern[str] | None,
) -> set[int]:
    pending = list(launches)
    stragglers: set[int] = set()
    multiple = _straggler_multiple()
    cutoff_enabled = opts.straggler_cutoff and multiple > 0 and len(launches) >= MIN_STRAGGLER_PHASE_SLOTS
    floor = float(_straggler_floor())
    ceiling = float(int(opts.timeout))
    needed = (len(launches) + 1) // 2
    accepted = 0
    deadline: float | None = None
    start = time.monotonic()
    while pending:
        finished: list[PhaseLaunch] = []
        for launch in pending:
            rc = launch.process.poll()
            if rc is None:
                continue
            _finish_launch(launch=launch, rc=rc)
            finished.append(launch)
            if cutoff_enabled and deadline is None and _slot_collector_accepted(launch=launch, opts=opts, result_pattern=result_pattern, first_line_pattern=first_line_pattern):
                accepted += 1
                if accepted >= needed:
                    anchor = time.monotonic() - start
                    deadline = min(ceiling, max(multiple * anchor, floor))
        for launch in finished:
            pending.remove(launch)
        if deadline is not None and pending and time.monotonic() - start >= deadline:
            for launch in pending:
                _terminate_launch(launch)
                _finish_launch(launch=launch, rc=launch.process.poll())
                stragglers.add(launch.idx)
            pending.clear()
            break
        if pending:
            time.sleep(0.05)
    return stragglers


def _split_summary_blocks(stdout: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in stdout.splitlines():
        if not line:
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _parse_block(block: str) -> tuple[str, str]:
    status = ""
    reviewer_file = ""
    for line in block.splitlines():
        key, sep, value = line.partition("=")
        if not sep:
            continue
        if key == "STATUS":
            status = value
        elif key == "REVIEWER_FILE":
            reviewer_file = value
    return status, reviewer_file


def _snippet_from_file(path: str) -> str:
    try:
        with Path(path).open("rb") as handle:
            data = handle.read(2000)
    except OSError:
        return ""
    text = data.decode("utf-8", errors="replace")
    return text.replace("\n", " ").replace("\r", " ").replace("\t", " ")[:200]


def _first_nonblank_trimmed(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _salvage_first_line(*, check_file: str, pattern: re.Pattern[str]) -> bool:
    try:
        lines = Path(check_file).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return False
    for idx, line in enumerate(lines):
        if pattern.search(line.rstrip("\n")):
            if idx <= 0:
                return False
            fd, tmp = tempfile.mkstemp(prefix=f"{Path(check_file).name}.salvage.", dir=str(Path(check_file).parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.writelines(lines[idx:])
                _ = Path(tmp).replace(check_file)
                return True
            except OSError:
                with contextlib.suppress(OSError):
                    Path(tmp).unlink()
                return False
    return False


def _apply_collector_block(
    *, output: str,
    status: str,
    reviewer_file: str,
    result_pattern: re.Pattern[str] | None,
    first_line_pattern: re.Pattern[str] | None,
) -> tuple[bool, str, DropState]:
    if status not in {"OK", "cap_hit"}:
        stderr_snippet = _snippet_from_file(f"{output}.launch-stderr")
        detail = f"STATUS={status or 'unknown'}"
        if stderr_snippet:
            detail = f"{detail} {stderr_snippet}"
        return False, "", DropState("collector-failure", detail)
    if status == "OK" and result_pattern is not None:
        check_file = reviewer_file or output
        if not Path(check_file).is_file():
            _err(
                "dispatch-with-waterfall.sh: result file not readable for --require-result-pattern check: "
                f"{check_file}"
            )
            return False, "", DropState("result-unreadable", f"result file not readable: {check_file}")
        content = Path(check_file).read_text(encoding="utf-8", errors="replace")
        if not result_pattern.search(content):
            return False, "", DropState("result-gate-miss", _snippet_from_file(check_file))
    if status == "OK" and first_line_pattern is not None:
        check_file = reviewer_file or output
        if not Path(check_file).is_file():
            _err(
                "dispatch-with-waterfall.sh: result file not readable for --require-first-line-pattern check: "
                f"{check_file}"
            )
            return False, "", DropState("result-unreadable", f"result file not readable: {check_file}")
        content = Path(check_file).read_text(encoding="utf-8", errors="replace")
        first_nonblank = _first_nonblank_trimmed(content)
        if not first_line_pattern.search(first_nonblank):
            if not first_nonblank:
                return False, "", DropState("empty", "")
            if not _salvage_first_line(check_file=check_file, pattern=first_line_pattern):
                return False, "", DropState("format-gate-miss", _snippet_from_file(check_file))
    return True, reviewer_file or output, DropState()


def _slot_collector_accepted(
    *, launch: PhaseLaunch,
    opts: Options,
    result_pattern: re.Pattern[str] | None,
    first_line_pattern: re.Pattern[str] | None,
) -> bool:
    result = proc.run(
        [sys.executable, str(PY_CLI), "agent", "collect-results", "--timeout", opts.timeout, "--summary-only", launch.output]
    )
    if result.returncode != 0:
        return False
    blocks = _split_summary_blocks(result.stdout)
    status, reviewer_file = _parse_block(blocks[0] if blocks else "")
    accepted, _final_output, _drop = _apply_collector_block(
        output=launch.output, status=status, reviewer_file=reviewer_file, result_pattern=result_pattern, first_line_pattern=first_line_pattern
    )
    return accepted


def _collect_phase(
    *, launches: Sequence[PhaseLaunch],
    opts: Options,
    final_outputs: list[str],
    final_tools: list[str],
    drops: list[DropState],
    result_pattern: re.Pattern[str] | None,
    first_line_pattern: re.Pattern[str] | None,
) -> list[int]:
    if not launches:
        return []
    straggler_idxs = _reap_phase(launches=launches, opts=opts, result_pattern=result_pattern, first_line_pattern=first_line_pattern)
    outputs = [launch.output for launch in launches]
    result = proc.run(
        [sys.executable, str(PY_CLI), "agent", "collect-results", "--timeout", opts.timeout, "--summary-only", *outputs]
    )
    blocks = _split_summary_blocks(result.stdout if result.returncode == 0 else "")
    failed: list[int] = []
    for pos, launch in enumerate(launches):
        idx = launch.idx
        output = launch.output
        if idx in straggler_idxs:
            drops[idx] = DropState("straggler-dropped", "cut at adaptive straggler deadline")
            continue
        status, reviewer_file = _parse_block(blocks[pos] if pos < len(blocks) else "")
        accepted, final_output, drop = _apply_collector_block(output=output, status=status, reviewer_file=reviewer_file, result_pattern=result_pattern, first_line_pattern=first_line_pattern)
        if accepted:
            final_outputs[idx] = final_output
            final_tools[idx] = launch.tool
            drops[idx] = DropState()
        else:
            drops[idx] = drop
            failed.append(idx)
    return failed



def _read_resolved_paths_from_kv(wf_kv: Mapping[str, str]) -> list[str]:
    path_file = wf_kv.get("ALL_OUTPUT_FILES_PATH", "")
    if path_file:
        try:
            return [line for line in Path(path_file).read_text(encoding="utf-8", errors="replace").splitlines() if line]
        except OSError:
            pass
    return [part for part in wf_kv.get("ALL_OUTPUT_FILES", "").split() if part]


def _read_dropped_slots(wf_kv: Mapping[str, str]) -> set[str]:
    path = wf_kv.get("DROPPED_SLOTS_FILE", "")
    if not path:
        return set()
    try:
        return {line.split("\t", 1)[0] for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if line}
    except OSError:
        return set()


def _phase_candidate_paths(output: str) -> set[str]:
    return {output, _output_for_phase(base=output, phase="phase2"), _output_for_phase(base=output, phase="phase3")}


def _path_matches_manifest_output(*, candidate: str, manifest_output: str) -> bool:
    candidates = _phase_candidate_paths(manifest_output)
    if candidate in candidates:
        return True
    cand_name = Path(candidate).name
    return any(cand_name == Path(value).name for value in candidates)


def bind_manifest_slot_outputs(*, manifest_path: str | Path, wf_kv: Mapping[str, str]) -> dict[str, SlotOutputBinding]:
    """Bind waterfall outputs by manifest slot, not compressed stdout position."""
    resolved_paths = _read_resolved_paths_from_kv(wf_kv)
    tools = [part for part in wf_kv.get("ALL_OUTPUT_TOOLS", "").split() if part]
    dropped_slots = _read_dropped_slots(wf_kv)
    rows = _load_slots(str(manifest_path))
    bound_indexes: set[int] = set()
    bindings: dict[str, SlotOutputBinding] = {}
    for row in rows:
        match_index: int | None = None
        for idx, path in enumerate(resolved_paths):
            if idx in bound_indexes:
                continue
            if _path_matches_manifest_output(candidate=path, manifest_output=row.output):
                match_index = idx
                break
        if match_index is None:
            bindings[row.name] = SlotOutputBinding(dropped=row.name in dropped_slots)
            continue
        bound_indexes.add(match_index)
        tool = tools[match_index] if match_index < len(tools) else ""
        bindings[row.name] = SlotOutputBinding(path=resolved_paths[match_index], tool=tool, dropped=False)
    return bindings


def _write_counter(*, path: str, combined_fallback: int) -> None:
    if not path:
        return
    prior = 0
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="replace").strip()
        if raw.isdigit():
            prior = int(raw, 10)
    except OSError:
        pass
    fd, tmp = tempfile.mkstemp(prefix=f"{Path(path).name}.tmp.", dir=str(Path(path).parent))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        _ = handle.write(f"{prior + combined_fallback}\n")
    _ = Path(tmp).replace(path)


def _flatten_field(text: str) -> str:
    return text.replace("\t", " ").replace("\n", " ").replace("\r", " ")


def _dropped_diag_name(*, slot: Slot, reason: str) -> str:
    raw = f"dropped-{slot.name}-{slot.tool}-{reason or 'unknown'}"
    safe = re.sub(r"[\x00-\x1f\x7f/\t\r\n]+", "-", raw)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", safe).strip(".-")
    return f"{safe or 'dropped-slot'}.txt"


def _preserve_drop_diagnostic(*, slot: Slot, reason: str) -> None:
    destination = Path(slot.output).parent / _dropped_diag_name(slot=slot, reason=reason)
    candidates = [
        Path(_output_for_phase(base=slot.output, phase=phase))
        for phase in ("phase1", "phase2", "phase3")
    ]
    for output in candidates:
        with contextlib.suppress(Exception):
            agents._compose_failure_diag(output)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        round_dir = Path(slot.output).parent.resolve()
        for source in (Path(f"{output}.failure-diag"), Path(f"{output}.launch-stderr")):
            try:
                if source.is_symlink() or not source.is_file() or source.stat().st_size <= 0:
                    continue
                resolved = source.resolve()
                _ = resolved.relative_to(round_dir)
                if not resolved.is_file():
                    continue
                text = resolved.read_text(encoding="utf-8", errors="replace")
                _ = destination.write_text(text, encoding="utf-8")
                return
            except (OSError, ValueError):
                continue


def _write_drops(*, path: str, slots: Sequence[Slot], final_outputs: Sequence[str], drops: Sequence[DropState]) -> str:
    paths_dir = Path(path).parent
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix=".dispatch-waterfall-drops.", dir=str(paths_dir))
        drop_any = False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for idx, slot in enumerate(slots):
                if final_outputs[idx]:
                    continue
                drop_any = True
                _preserve_drop_diagnostic(slot=slot, reason=drops[idx].reason or "unknown")
                _ = handle.write(
                    f"{_flatten_field(slot.name)}\t{_flatten_field(slot.tool)}\t{drops[idx].reason or 'unknown'}\t{drops[idx].detail}\n"
                )
        if not drop_any:
            Path(tmp).unlink(missing_ok=True)
            return ""
        dropped_slots_file = f"{path}.dropped-slots"
        _ = Path(tmp).replace(dropped_slots_file)
        return dropped_slots_file
    except OSError as exc:
        if tmp:
            with contextlib.suppress(OSError):
                Path(tmp).unlink()
        raise ValidationError(f"dispatch-with-waterfall.sh: dropped-slots sidecar not writable: {path}") from exc


def _write_invalid_slot_drops(*, path: str, invalid_drops: Sequence[InvalidSlotDrop]) -> str:
    invalid_slots_file = f"{path}.invalid-slots"
    paths_dir = Path(path).parent
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix=".dispatch-waterfall-invalid-slots.", dir=str(paths_dir))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for drop in invalid_drops:
                record = {
                    "line": drop.line,
                    "slot": drop.slot,
                    "snippet": drop.snippet,
                    "message": drop.message,
                }
                _ = handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        _ = Path(tmp).replace(invalid_slots_file)
        return invalid_slots_file
    except OSError as exc:
        if tmp:
            with contextlib.suppress(OSError):
                Path(tmp).unlink()
        raise ValidationError(f"dispatch-with-waterfall.sh: invalid-slots sidecar not writable: {invalid_slots_file}") from exc


def _write_paths_file(*, path: str, final_outputs: Sequence[str]) -> None:
    paths_dir = Path(path).parent
    tmp = ""
    try:
        fd, tmp = tempfile.mkstemp(prefix=".dispatch-waterfall-paths.", dir=str(paths_dir))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for output in final_outputs:
                if not output:
                    continue
                _ = handle.write(f"{output}\n")
        _ = Path(tmp).replace(path)
    except OSError as exc:
        if tmp:
            with contextlib.suppress(OSError):
                Path(tmp).unlink()
        raise ValidationError(f"dispatch-with-waterfall.sh: paths-file not writable: {path}") from exc


def _emit_bool(key: str, *, value: bool) -> None:
    logging_util.emit_kv(key=key, value="true" if value else "false")


def dispatch_waterfall(opts: Options) -> int:
    _ACTIVE_LAUNCHES.clear()
    _DISPATCH_LAUNCHES.clear()
    result_pattern = _compile_pattern(raw=opts.require_result_pattern, flag="--require-result-pattern")
    first_line_pattern = _compile_pattern(raw=opts.require_first_line_pattern, flag="--require-first-line-pattern")
    slots, invalid_drops = _load_slots_with_invalid_drops(opts.slots_file, skip_invalid=opts.skip_invalid_slots)
    if opts.skip_invalid_slots and not slots:
        raise ValidationError("dispatch-with-waterfall.sh: slots file contains no valid slot rows")
    resolved_paths_file = opts.paths_file or f"{opts.slots_file}.output-files"
    paths_dir = Path(resolved_paths_file).parent
    if not paths_dir.is_dir():
        raise ValidationError(f"dispatch-with-waterfall.sh: paths-file parent directory does not exist: {paths_dir}")
    invalid_slots_file = ""
    if invalid_drops:
        invalid_slots_file = _write_invalid_slot_drops(path=resolved_paths_file, invalid_drops=invalid_drops)
    final_outputs: list[str] = [""] * len(slots)
    final_tools: list[str] = [""] * len(slots)
    drops: list[DropState] = [DropState() for _ in slots]

    phase1_outputs: list[str] = []
    phase2_outputs: list[str] = []
    phase3_outputs: list[str] = []
    phase1_queue: list[int] = []

    phase1_launches: list[PhaseLaunch] = []
    for idx, slot in enumerate(slots):
        if _present_for_tool(tool=slot.tool, opts=opts):
            out = _output_for_phase(base=slot.output, phase="phase1")
            phase1_outputs.append(out)
            phase1_launches.append(_launch_slot(idx=idx, phase="phase1", tool=slot.tool, output=out, slots=slots, opts=opts))
        else:
            phase1_queue.append(idx)
    phase1_failed = _collect_phase(
        launches=phase1_launches, opts=opts, final_outputs=final_outputs, final_tools=final_tools, drops=drops, result_pattern=result_pattern, first_line_pattern=first_line_pattern
    )

    fallback_count = 0
    combined_fallback = 0
    phase3_failed: list[int] = []
    dispatch_ok = True
    static_dispatch_ok = True
    dynamic_dispatch_ok = True

    if opts.no_fallback:
        for idx in phase1_queue:
            drops[idx] = DropState("tool-absent", f"primary tool {slots[idx].tool} not present")
        for idx in [*phase1_queue, *phase1_failed]:
            if slots[idx].name.startswith("dyn-"):
                dynamic_dispatch_ok = False
            else:
                static_dispatch_ok = False
    else:
        phase2_queue = [*phase1_queue, *phase1_failed]
        phase3_seed: list[int] = []
        phase2_launches: list[PhaseLaunch] = []
        for idx in phase2_queue:
            alt = _other_tool(slots[idx].tool)
            if _present_for_tool(tool=alt, opts=opts):
                out = _output_for_phase(base=slots[idx].output, phase="phase2")
                phase2_outputs.append(out)
                phase2_launches.append(_launch_slot(idx=idx, phase="phase2", tool=alt, output=out, slots=slots, opts=opts))
            else:
                phase3_seed.append(idx)
        phase2_failed = _collect_phase(
            launches=phase2_launches, opts=opts, final_outputs=final_outputs, final_tools=final_tools, drops=drops, result_pattern=result_pattern, first_line_pattern=first_line_pattern
        )
        phase3_queue = [*phase3_seed, *phase2_failed]
        phase3_launches: list[PhaseLaunch] = []
        for idx in phase3_queue:
            out = _output_for_phase(base=slots[idx].output, phase="phase3")
            phase3_outputs.append(out)
            fallback_count += 1
            phase3_launches.append(_launch_slot(idx=idx, phase="phase3", tool="claude", output=out, slots=slots, opts=opts))
        phase3_failed = _collect_phase(
            launches=phase3_launches, opts=opts, final_outputs=final_outputs, final_tools=final_tools, drops=drops, result_pattern=result_pattern, first_line_pattern=first_line_pattern
        )
        combined_fallback = fallback_count

    _write_counter(path=opts.fallback_counter_file, combined_fallback=combined_fallback)

    for idx in phase3_failed:
        final_outputs[idx] = _output_for_phase(base=slots[idx].output, phase="phase3")
        final_tools[idx] = "claude"
        dispatch_ok = False
        if slots[idx].name.startswith("dyn-"):
            dynamic_dispatch_ok = False
        else:
            static_dispatch_ok = False

    if phase3_failed:
        env: dict[str, str] = dict(os.environ)
        env["LARCH_QUIET_DISABLE"] = "1"
        _ = proc.run(
            [
                sys.executable,
                str(PY_CLI),
                "agent",
                "collect-results",
                "--timeout",
                opts.timeout,
                *[final_outputs[idx] for idx in phase3_failed],
            ],
            env=env,
            stdout=subprocess.DEVNULL,
        )

    threshold_raw = os.environ.get("LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD", "3")
    threshold = int(threshold_raw, 10) if threshold_raw.isdigit() else 3
    warn_tokens: list[str] = []
    if combined_fallback > threshold:
        warn_tokens.append("cost-fallback-exceeded-threshold")

    for idx, output in enumerate(final_outputs):
        if "\n" in output or "\r" in output:
            raise ValidationError(
                "dispatch-with-waterfall.sh: output path for slot "
                f"'{slots[idx].name}' contains a newline or carriage return (line-oriented paths-file contract)"
            )

    all_output_files: list[str] = []
    all_output_tools: list[str] = []
    for idx, output in enumerate(final_outputs):
        if not output:
            continue
        all_output_files.append(output)
        all_output_tools.append(final_tools[idx])

    dropped_slots_file = ""
    # Persist dropped slots whenever any slot ends with a drop reason, regardless of
    # fallback mode. Straggler drops in fallback-mode dispatch must still reach the
    # coverage gate so it can excuse the dropped archetype instead of producing a
    # spurious panel-failed stall (issue #5047).
    if any(drop.reason for drop in drops):
        dropped_slots_file = _write_drops(path=resolved_paths_file, slots=slots, final_outputs=final_outputs, drops=drops)
    _write_paths_file(path=resolved_paths_file, final_outputs=final_outputs)
    straggler_dropped_count = sum(1 for drop in drops if drop.reason == "straggler-dropped")

    logging_util.emit_kv(key="PHASE1_SLOTS", value=" ".join(phase1_outputs))
    logging_util.emit_kv(key="PHASE2_SLOTS", value=" ".join(phase2_outputs))
    logging_util.emit_kv(key="PHASE3_SLOTS", value=" ".join(phase3_outputs))
    logging_util.emit_kv(key="ALL_OUTPUT_FILES", value=" ".join(all_output_files))
    logging_util.emit_kv(key="ALL_OUTPUT_FILES_PATH", value=resolved_paths_file)
    logging_util.emit_kv(key="ALL_OUTPUT_TOOLS", value=" ".join(all_output_tools))
    logging_util.emit_kv(key="FALLBACK_COUNT", value=str(fallback_count))
    logging_util.emit_kv(key="COMBINED_FALLBACK_COUNT", value=str(combined_fallback))
    logging_util.emit_kv(key="STRAGGLER_DROPPED_COUNT", value=str(straggler_dropped_count))
    if straggler_dropped_count > 0:
        warn_tokens.append("reviewer-straggler-dropped")
    if invalid_drops:
        logging_util.emit_kv(key="INVALID_SLOT_DROP_COUNT", value=str(len(invalid_drops)))
        logging_util.emit_kv(key="INVALID_SLOT_DROPS_FILE", value=invalid_slots_file)
        warn_tokens.append("invalid-slots-dropped")
    if warn_tokens:
        logging_util.emit_kv(key="WARN", value=";".join(warn_tokens))
    _emit_bool("DISPATCH_OK", value=dispatch_ok)
    _emit_bool("STATIC_DISPATCH_OK", value=static_dispatch_ok)
    _emit_bool("DYNAMIC_DISPATCH_OK", value=dynamic_dispatch_ok)
    if opts.no_fallback and not all_output_files and slots:
        logging_util.emit_kv(key="ALL_SLOTS_DROPPED", value="true")
    if dropped_slots_file:
        logging_util.emit_kv(key="DROPPED_SLOTS_FILE", value=dropped_slots_file)
    _DISPATCH_LAUNCHES.clear()
    return 0


def dispatch_waterfall_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="dispatch-with-waterfall.sh")
    _ = signal.signal(signal.SIGTERM, _sigterm_handler)
    _ = atexit.register(_kill_active_launches)
    args = sys.argv[1:] if argv is None else argv
    try:
        parsed = _parse_args(argv=args)
        if isinstance(parsed, int):
            return parsed
        return dispatch_waterfall(parsed)
    except ValidationError as exc:
        _err(str(exc))
        return 2
    except SystemExit as exc:
        return int(exc.code or 0)


if __name__ == "__main__":
    raise SystemExit(dispatch_waterfall_main())
