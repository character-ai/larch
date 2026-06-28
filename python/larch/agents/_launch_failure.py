# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalMemberAccess=false, reportPrivateUsage=false
"""Launch failure classification and model argument resolution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from larch.core import config
from larch.core.ctx import Ctx
from larch.core import logging_util
from larch.core import proc

from larch.agents._types import (
    _PARSE_RE,
    _REFUSAL_RE,
    _QUOTA_RE,
    _CTRL_RE,
    _PY_CLI,
    LaunchFailure,
    TierAttempt,
    ModelArgResult,
    _err,
    _emit,
    _emit_kv,
    _read_text,
)

def is_transient_infra_failure(
    *, tool: str,
    exit_code: int,
    output_file: str | Path | None,
) -> bool:
    """Port of external_is_transient_infra_failure in lib-external-launcher-common.sh."""
    if tool == "codex":
        if exit_code not in {5, 7}:
            return False
    elif tool == "cursor":
        if exit_code not in {4, 8}:
            return False
    elif tool == "claude":
        if exit_code not in {4, 5, 7, 8}:
            return False
    else:
        return False
    if output_file is None:
        return True
    path = Path(output_file)
    if not path.is_file():
        return True
    return path.stat().st_size == 0


def is_quota_failure(*, tool: str, sidecar: str | Path | None) -> bool:
    """Port of external_is_quota_failure in lib-external-launcher-common.sh."""
    if tool not in ("codex", "cursor", "claude"):
        return False
    if not sidecar:
        return False
    path = Path(sidecar)
    if not path.is_file():
        return False
    return bool(_QUOTA_RE.search(path.read_text(encoding="utf-8", errors="replace")))


def _fallback_launcher_exit(process_rc: int) -> int:
    return max(process_rc, 1) if process_rc != 0 else 0


def _parse_launcher_exit_value(text: str) -> int | None:
    for line in text.splitlines():
        if line.startswith("LAUNCHER_EXIT="):
            raw = line.split("=", 1)[1].strip().strip("\r")
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def parse_launcher_exit_text(*, text: str, process_rc: int = 0) -> int:
    """Read LAUNCHER_EXIT= from launcher stdout capture; failed wrappers fail closed."""
    parsed = _parse_launcher_exit_value(text)
    return parsed if parsed is not None else _fallback_launcher_exit(process_rc)


def _read_launcher_done(output_file: str | Path) -> int | None:
    done = Path(output_file).with_suffix(Path(output_file).suffix + ".done")
    if not done.is_file():
        return None
    text = done.read_text(encoding="utf-8", errors="replace").strip()
    try:
        return int(text)
    except ValueError:
        return None


def resolve_launcher_exit(
    *, captured_text: str,
    output_file: str | Path | None = None,
    process_rc: int = 0,
) -> int:
    """Resolve launcher exit from sidecar, captured fd 3 text, output file, then wrapper rc."""
    if output_file is not None:
        done_exit = _read_launcher_done(output_file)
        if done_exit is not None:
            return done_exit
    parsed = _parse_launcher_exit_value(captured_text)
    if parsed is not None:
        return parsed
    if output_file is not None:
        path = Path(output_file)
        if path.is_file():
            parsed = _parse_launcher_exit_value(path.read_text(encoding="utf-8", errors="replace"))
            if parsed is not None:
                return parsed
    return _fallback_launcher_exit(process_rc)


def read_launcher_exit(*, output_file: str | Path, process_rc: int = 0) -> int:
    """Read launcher exit from sidecar or capture file; failed wrappers fail closed."""
    path = Path(output_file)
    return resolve_launcher_exit(captured_text="", output_file=path, process_rc=process_rc)


def _launcher_failure_class_from_text(text: str) -> str | None:
    last = ""
    for line in text.splitlines():
        if line.startswith("LAUNCHER_FAILURE_CLASS="):
            last = line.split("=", 1)[1].strip().strip("\r")
    if last in ("none", "health", "other"):
        return last
    return None


def parse_launcher_failure_class(log_file: str | Path | None) -> str:
    """Last LAUNCHER_FAILURE_CLASS= from launcher capture; unknown/missing → health."""
    if log_file is None:
        return "health"
    path = Path(log_file)
    if not path.is_file():
        return "health"
    parsed = _launcher_failure_class_from_text(
        path.read_text(encoding="utf-8", errors="replace"),
    )
    return parsed if parsed is not None else "health"


def effective_failure_class(attempt: TierAttempt) -> str:
    """Failure class from launcher capture when present, else ``attempt.failure``."""
    if attempt.failure_log is not None:
        return parse_launcher_failure_class(attempt.failure_log)
    return attempt.failure.failure_class


def classify_launch_failure(
    *,
    launcher_exit: int,
    sidecar: str | Path | None = None,
    auth_verdict: str = "unclassified",
    binary_present: bool = True,
    tool: str = "cursor",
    output_file: str | Path | None = None,
) -> LaunchFailure:
    """Port of external_classify_launch_failure."""
    if launcher_exit == 0:
        return LaunchFailure(failure_class="none", reason="")
    if not binary_present:
        return LaunchFailure(failure_class="health", reason="binary-missing")
    if auth_verdict == "auth":
        return LaunchFailure(failure_class="health", reason="auth")
    if (sidecar and is_quota_failure(tool=tool, sidecar=sidecar)) or (
        output_file and is_quota_failure(tool=tool, sidecar=output_file)
    ):
        return LaunchFailure(failure_class="health", reason="quota")
    if output_file and is_transient_infra_failure(tool=tool, exit_code=launcher_exit, output_file=output_file):
        return LaunchFailure(failure_class="health", reason="health-probe")
    if launcher_exit == config.EXIT_TIMEOUT:
        return LaunchFailure(failure_class="other", reason="timeout")
    if sidecar:
        text = _read_text(sidecar)
        if _PARSE_RE.search(text):
            return LaunchFailure(failure_class="other", reason="parse")
        if _REFUSAL_RE.search(text):
            return LaunchFailure(failure_class="other", reason="refusal")
    if output_file:
        text = _read_text(output_file)
        if _PARSE_RE.search(text):
            return LaunchFailure(failure_class="other", reason="parse")
    return LaunchFailure(failure_class="other", reason="unknown")


def resolve_model_args(
    tool: str,
    *,
    with_effort: bool = False,
    default_model: str = "",
    codex_role: Literal["default", "review", "vote", "fix"] = "default",
    ctx: Ctx | None = None,
) -> ModelArgResult:
    if tool not in {"cursor", "codex"}:
        raise ValueError(f"--tool must be 'cursor' or 'codex' (got: {tool})")
    if codex_role not in {"default", "review", "vote", "fix"}:
        raise ValueError(f"--codex-role must be default|review|vote|fix (got: {codex_role})")

    def reject_bad_arg(*, value: str, context: str) -> None:
        if _CTRL_RE.search(value):
            raise ValueError(f"{context} must not contain POSIX [[:cntrl:]] characters")

    def reject_blank(*, value: str, context: str) -> str:
        reject_bad_arg(value=value, context=context)
        if not value.strip():
            raise ValueError(f"{context} must not be blank or whitespace-only")
        return value

    def resolve(*, env_name: str, plugin_name: str, default_value: str) -> str:
        if ctx is not None:
            if ctx.contains(env_name):
                return reject_blank(value=ctx.str_value(key=env_name), context=env_name)
            if ctx.contains(plugin_name):
                return reject_blank(value=ctx.str_value(key=plugin_name), context=plugin_name)
            return reject_blank(value=default_value, context="default model")
        if env_name in os.environ:
            return reject_blank(value=os.environ[env_name], context=env_name)
        if plugin_name in os.environ:
            return reject_blank(value=os.environ[plugin_name], context=plugin_name)
        return reject_blank(value=default_value, context="default model")

    if tool == "cursor":
        model = resolve(env_name=config.ENV_LARCH_CURSOR_MODEL, plugin_name=config.ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL, default_value=config.CURSOR_DEFAULT_MODEL)
        return ModelArgResult(("--model", model))

    role_defaults = {
        "review": (config.ENV_LARCH_CODEX_REVIEW_MODEL, config.CODEX_REVIEW_MODEL_DEFAULT),
        "vote": (config.ENV_LARCH_CODEX_VOTE_MODEL, config.CODEX_VOTE_MODEL_DEFAULT),
        "fix": (config.ENV_LARCH_CODEX_FIX_MODEL, config.CODEX_FIX_MODEL_DEFAULT),
    }
    if codex_role == "default":
        model = resolve(env_name=config.ENV_LARCH_CODEX_MODEL, plugin_name=config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL, default_value=default_model or config.CODEX_DEFAULT_MODEL)
    else:
        env_name, default_value = role_defaults[codex_role]
        if ctx is not None:
            model = reject_blank(value=ctx.str_value(key=env_name), context=env_name) if ctx.contains(env_name) else reject_blank(value=default_value, context="default model")
        else:
            model = reject_blank(value=os.environ[env_name], context=env_name) if env_name in os.environ else reject_blank(value=default_value, context="default model")
    argv = ["-m", model]
    warning = ""
    if with_effort:
        if ctx is not None:
            effort = (
                ctx.str_value(key=config.ENV_LARCH_CODEX_EFFORT)
                if ctx.contains(config.ENV_LARCH_CODEX_EFFORT)
                else ctx.str_value(key=config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_EFFORT, default="high")
            )
        else:
            effort = os.environ.get(config.ENV_LARCH_CODEX_EFFORT, os.environ.get(config.ENV_CLAUDE_PLUGIN_OPTION_CODEX_EFFORT, "high"))
        if effort not in {"minimal", "low", "medium", "high"}:
            warning = f"WARN invalid codex effort '{effort}' (must be minimal|low|medium|high); falling back to 'high'"
            effort = "high"
        argv.extend(["-c", f'model_reasoning_effort="{effort}"'])
    return ModelArgResult(tuple(argv), warning)


def model_args_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py agent model-args")
    parser.add_argument("--tool", required=True)
    parser.add_argument("--with-effort", action="store_true")
    parser.add_argument("--default-model", default="")
    parser.add_argument("--codex-role", choices=("default", "review", "vote", "fix"), default="default")
    args = parser.parse_args(argv)
    ctx = Ctx.from_mapping(os.environ)
    try:
        result = resolve_model_args(args.tool, with_effort=args.with_effort, default_model=args.default_model, codex_role=args.codex_role, ctx=ctx)
    except ValueError as exc:
        _err(f"agent model-args: {exc}")
        return 1
    if result.warning:
        _err(f"agent model-args: {result.warning}")
    for token in result.argv:
        if not token:
            continue
        if _CTRL_RE.search(token):
            _err("agent model-args: emitted argv token must not contain POSIX [[:cntrl:]] characters")
            return 1
        _emit(token)
    return 0


def read_claude_model() -> str:
    source = proc.run([sys.executable, str(_PY_CLI), "token", "claude-source"])
    transcript = ""
    for line in source.stdout.splitlines():
        if line.startswith("TRANSCRIPT_PATH="):
            transcript = line.split("=", 1)[1]
            break
    if not transcript:
        return "unknown"
    path = Path(transcript)
    if not path.is_file():
        return "unknown"
    try:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            obj = json.loads(raw)
            model = obj.get("message", {}).get("model", "") if obj.get("type") == "assistant" else ""
            if isinstance(model, str) and model:
                return model
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return "unknown"


def read_claude_model_main(argv: list[str] | None = None) -> int:
    _ = argv
    logging_util.quiet_init(argv0="cli.py")
    _emit_kv(key="CLAUDE_MODEL", value=read_claude_model())
    return 0
