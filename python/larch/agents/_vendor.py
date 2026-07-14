"""Inactive vendor descriptors, argv builders, and shared launch lifecycle.

Pieces 1-2 of the vendor foundation (#7204/#7205 / #7029). Declares the frozen
data model, exact argv builders, and ``run_vendor_launch`` lifecycle that later
pieces plug production callers into. Production launchers must not import this
module yet.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Generator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from larch.core import proc

from larch.agents._run_external import (
    _codex_auth_args,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist argv helper
    _trust_config_arg,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist argv helper
)
from larch.agents._types import (
    _PY_CLI,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist cli path
    _is_positive_int,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist cap gate
)

# Capabilities every vendor descriptor must declare. Hook behavior is wired in
# the lifecycle piece; this piece only freezes the surface.
REQUIRED_CAPABILITIES: frozenset[str] = frozenset(
    {
        "argv",
        "model_extraction",
        "execution",
        "retry",
        "timing",
        "quota_mirroring",
        "usage_recording",
        "postprocessing",
        "cap_hit_artifact",
        "completion_promotion",
    }
)

CodexSandbox = Literal["read-only", "workspace-write"]
CursorProfile = Literal["review-ask", "ci-write", "implement-write", "negotiation-write"]
ClaudeProfile = Literal[
    "review-subprocess",
    "review-subprocess-base",
    "drafter-read",
    "workspace-write",
]


@dataclass(frozen=True)
class VendorLaunchRequest:
    """Inputs for argv construction and (later) the shared launch lifecycle."""

    workdir: str
    output: str
    prompt: str
    timing_task_kind: str = ""
    model_args: tuple[str, ...] = ()
    model: str = ""
    add_dirs: tuple[str, ...] = ()
    prompt_via_stdin: bool = False
    read_tools_add_dir: str = ""
    token_cap: str = ""


@dataclass(frozen=True)
class VendorProcessResult:
    """Terminal result of a vendor process invocation."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class VendorParsedResult:
    """Typed post-parse outcome for family postprocessing (Claude envelopes)."""

    status: str
    text: str = ""
    raw: str = ""
    is_error: bool = False


@dataclass(frozen=True)
class VendorFamilyHooks:
    """Injectable lifecycle hooks. Behavior is wired in the lifecycle piece."""

    execute: Callable[..., Any] | None = None
    retry: Callable[..., Any] | None = None
    record_timing: Callable[..., Any] | None = None
    mirror_quota: Callable[..., Any] | None = None
    record_usage: Callable[..., Any] | None = None
    postprocess: Callable[..., Any] | None = None
    emit_cap_hit_artifact: Callable[..., Any] | None = None
    promote_completion: Callable[..., Any] | None = None
    preflight: Callable[..., Any] | None = None


@dataclass(frozen=True)
class VendorDescriptor:
    """Immutable vendor identity, capabilities, profiles, and argv builder."""

    key: str
    capabilities: frozenset[str]
    argv_profiles: frozenset[str]
    build_argv: Callable[[str, VendorLaunchRequest], list[str]]
    extract_model: Callable[[Sequence[str]], str]
    hooks: VendorFamilyHooks = field(default_factory=VendorFamilyHooks)


def extract_model_from_argv(argv: Sequence[str]) -> str:
    """Extract a model from Codex ``-m``, Cursor ``--model``, or Claude ``--model``.

    Missing or dangling flags return an empty string without raising.
    Prefers ``--model`` over ``-m`` when both appear.
    """
    for flag in ("--model", "-m"):
        try:
            idx = list(argv).index(flag)
        except ValueError:
            continue
        if idx + 1 < len(argv):
            return str(argv[idx + 1])
    return ""


def build_codex_argv(profile: str, request: VendorLaunchRequest) -> list[str]:
    """Build Codex ``codex exec`` argv for ``read-only`` or ``workspace-write``."""
    if profile not in {"read-only", "workspace-write"}:
        raise ValueError(f"unknown Codex argv profile: {profile}")
    sandbox: CodexSandbox = "read-only" if profile == "read-only" else "workspace-write"
    add_dir_args = [value for directory in request.add_dirs for value in ("--add-dir", directory)]
    prompt_token = "-" if request.prompt_via_stdin else request.prompt
    return [
        "codex",
        "exec",
        "--sandbox",
        sandbox,
        "-C",
        request.workdir,
        *add_dir_args,
        *request.model_args,
        "-c",
        _trust_config_arg(request.workdir),
        *_codex_auth_args(),
        "--output-last-message",
        request.output,
        "--json",
        "--",
        prompt_token,
    ]


def build_cursor_argv(profile: str, request: VendorLaunchRequest) -> list[str]:
    """Build Cursor ``cursor agent -p`` argv for a named profile."""
    if profile == "review-ask":
        return [
            "cursor",
            "agent",
            "-p",
            "--trust",
            "--mode",
            "ask",
            "--output-format",
            "json",
            *request.model_args,
            "--workspace",
            request.workdir,
            request.prompt,
        ]
    if profile == "ci-write":
        return [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            *request.model_args,
            "--output-format",
            "json",
            "--workspace",
            request.workdir,
            request.prompt,
        ]
    if profile == "implement-write":
        return [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            "--output-format",
            "json",
            *request.model_args,
            "--workspace",
            request.workdir,
            request.prompt,
        ]
    if profile == "negotiation-write":
        return [
            "cursor",
            "agent",
            "-p",
            "--force",
            "--trust",
            *request.model_args,
            "--workspace",
            request.workdir,
            request.prompt,
        ]
    raise ValueError(f"unknown Cursor argv profile: {profile}")


def build_claude_argv(profile: str, request: VendorLaunchRequest) -> list[str]:
    """Build Claude argv for a named profile. Prompt is stdin-transported."""
    model = request.model
    if profile == "review-subprocess":
        if not request.read_tools_add_dir:
            raise ValueError("Claude review-subprocess requires read_tools_add_dir")
        return [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--model",
            model,
            "--add-dir",
            request.read_tools_add_dir,
            "--allowedTools",
            "Read",
            "--permission-mode",
            "plan",
        ]
    if profile == "review-subprocess-base":
        # Base no-read-tools shape: review --print JSON + model only.
        return [
            "claude",
            "--print",
            "--output-format",
            "json",
            "--model",
            model,
        ]
    if profile == "drafter-read":
        return [
            "claude",
            "--model",
            model,
            "--print",
            "--output-format",
            "json",
            "--add-dir",
            request.workdir,
            "--allowedTools",
            "Read,Glob,Grep,LS",
            "--permission-mode",
            "plan",
        ]
    if profile == "workspace-write":
        return [
            "claude",
            "-p",
            "--output-format",
            "json",
            "--model",
            model,
            "--add-dir",
            request.workdir,
            "--allowedTools",
            "Read,Edit,Write",
        ]
    raise ValueError(f"unknown Claude argv profile: {profile}")


def _validate_descriptor(descriptor: VendorDescriptor) -> VendorDescriptor:
    if not descriptor.key:
        raise ValueError("vendor descriptor key must be non-empty")
    missing = REQUIRED_CAPABILITIES - descriptor.capabilities
    if missing:
        raise ValueError(
            f"vendor {descriptor.key!r} missing capabilities: {sorted(missing)}"
        )
    if not descriptor.argv_profiles:
        raise ValueError(f"vendor {descriptor.key!r} has no argv profiles")
    return descriptor


def build_vendor_registry(
    descriptors: Sequence[VendorDescriptor],
) -> dict[str, VendorDescriptor]:
    """Register descriptors; fail loudly on duplicate keys or missing capabilities."""
    registry: dict[str, VendorDescriptor] = {}
    for descriptor in descriptors:
        validated = _validate_descriptor(descriptor)
        if validated.key in registry:
            raise ValueError(f"duplicate vendor key: {validated.key!r}")
        registry[validated.key] = validated
    return registry


_CODEX_PROFILES: frozenset[str] = frozenset({"read-only", "workspace-write"})
_CURSOR_PROFILES: frozenset[str] = frozenset(
    {"review-ask", "ci-write", "implement-write", "negotiation-write"}
)
_CLAUDE_PROFILES: frozenset[str] = frozenset(
    {
        "review-subprocess",
        "review-subprocess-base",
        "drafter-read",
        "workspace-write",
    }
)


CODEX_DESCRIPTOR: VendorDescriptor = _validate_descriptor(
    VendorDescriptor(
        key="codex",
        capabilities=REQUIRED_CAPABILITIES,
        argv_profiles=_CODEX_PROFILES,
        build_argv=build_codex_argv,
        extract_model=extract_model_from_argv,
        hooks=VendorFamilyHooks(),
    )
)

CURSOR_DESCRIPTOR: VendorDescriptor = _validate_descriptor(
    VendorDescriptor(
        key="cursor",
        capabilities=REQUIRED_CAPABILITIES,
        argv_profiles=_CURSOR_PROFILES,
        build_argv=build_cursor_argv,
        extract_model=extract_model_from_argv,
        hooks=VendorFamilyHooks(),
    )
)

CLAUDE_DESCRIPTOR: VendorDescriptor = _validate_descriptor(
    VendorDescriptor(
        key="claude",
        capabilities=REQUIRED_CAPABILITIES,
        argv_profiles=_CLAUDE_PROFILES,
        build_argv=build_claude_argv,
        extract_model=extract_model_from_argv,
        hooks=VendorFamilyHooks(),
    )
)

VENDOR_DESCRIPTORS: Mapping[str, VendorDescriptor] = build_vendor_registry(
    (CODEX_DESCRIPTOR, CURSOR_DESCRIPTOR, CLAUDE_DESCRIPTOR)
)

# ---------------------------------------------------------------------------
# Lifecycle (piece 2 / #7205): caps, config context, envelopes, retries, launch
# ---------------------------------------------------------------------------

CAP_HIT_PAYLOAD = "STATUS=cap_hit\n"

CLAUDE_ENVELOPE_OK = "ok"
CLAUDE_ENVELOPE_MALFORMED_JSON = "malformed_json"
CLAUDE_ENVELOPE_NON_OBJECT = "non_object"
CLAUDE_ENVELOPE_IS_ERROR = "is_error"
CLAUDE_ENVELOPE_MISSING_RESULT = "missing_result"
CLAUDE_ENVELOPE_NON_STRING_RESULT = "non_string_result"
CLAUDE_ENVELOPE_EMPTY_RESULT = "empty_result"

VendorLaunchStatus = Literal["completed", "cap_hit", "preflight_refused"]


@dataclass(frozen=True)
class VendorCapCheckResult:
    """Outcome of an optional token-budget cap check."""

    hit: bool
    argv: tuple[str, ...] = ()
    stdout: str = ""
    payload: str = ""


@dataclass(frozen=True)
class VendorLaunchOutcome:
    """Terminal outcome of ``run_vendor_launch``."""

    status: VendorLaunchStatus
    process_result: VendorProcessResult | None = None
    model: str = ""
    argv: tuple[str, ...] = ()
    cap_check: VendorCapCheckResult | None = None


@dataclass(frozen=True)
class VendorRetryPolicy:
    """Family-specific retry classification and limits around an injected executor.

    Limits count *retries after the first attempt* (max_auth_retries=1 allows
    the initial try plus one auth retry). Classifiers that are ``None`` never
    match. ``sleep`` defaults to a no-op so offline tests need not patch time.
    """

    is_auth_failure: Callable[[VendorProcessResult], bool] | None = None
    is_transient_failure: Callable[[VendorProcessResult], bool] | None = None
    is_empty_response: Callable[[VendorProcessResult], bool] | None = None
    max_auth_retries: int = 0
    max_transient_retries: int = 0
    max_empty_retries: int = 0
    sleep: Callable[[float], None] | None = None
    delay_seconds: float = 0.0


def build_check_budget_argv(*, cap: str, step: str) -> list[str]:
    """Exact ``cli.py token check-budget`` argv for a positive cap."""
    return [
        sys.executable,
        str(_PY_CLI),
        "token",
        "check-budget",
        "--cap",
        cap,
        "--step",
        step,
    ]


def check_token_budget_cap(
    *,
    cap: str,
    step: str,
    runner: Callable[[Sequence[str]], Any] | None = None,
) -> VendorCapCheckResult:
    """Return whether ``cap`` is hit. Non-positive / nonnumeric caps skip the command."""
    if not _is_positive_int(cap):
        return VendorCapCheckResult(hit=False)
    argv = tuple(build_check_budget_argv(cap=cap, step=step))

    def _default_runner(cmd: Sequence[str]) -> Any:
        return proc.run(list(cmd), check=False)

    run = runner if runner is not None else _default_runner
    result = run(argv)
    stdout = str(getattr(result, "stdout", "") or "")
    status = ""
    for token in stdout.split():
        if token.startswith("STATUS="):
            status = token.split("=", 1)[1]
            break
    if status != "cap_hit":
        return VendorCapCheckResult(hit=False, argv=argv, stdout=stdout)
    return VendorCapCheckResult(hit=True, argv=argv, stdout=stdout, payload=CAP_HIT_PAYLOAD)


@contextlib.contextmanager
def cursor_config_context() -> Generator[Path]:
    """Isolate Cursor config under a temp dir; restore ``CURSOR_CONFIG_DIR`` on exit."""
    cfg_tmp = Path(tempfile.mkdtemp(prefix="larch-cursor-cfg-", dir=tempfile.gettempdir()))
    old_cfg = os.environ.get("CURSOR_CONFIG_DIR")
    os.environ["CURSOR_CONFIG_DIR"] = str(cfg_tmp)
    user_cfg = Path.home() / ".cursor" / "cli-config.json"
    if user_cfg.is_file():
        with contextlib.suppress(OSError):
            _ = shutil.copyfile(user_cfg, cfg_tmp / "cli-config.json")
    try:
        yield cfg_tmp
    finally:
        shutil.rmtree(cfg_tmp, ignore_errors=True)
        if old_cfg is None:
            _ = os.environ.pop("CURSOR_CONFIG_DIR", None)
        else:
            os.environ["CURSOR_CONFIG_DIR"] = old_cfg


def parse_claude_envelope(raw: str) -> VendorParsedResult:  # noqa: PLR0911 - seven envelope statuses are distinct outcomes
    """Parse a Claude JSON envelope into a typed postprocess outcome."""
    try:
        obj: object = json.loads(raw)
    except json.JSONDecodeError:
        return VendorParsedResult(status=CLAUDE_ENVELOPE_MALFORMED_JSON, raw=raw)
    if not isinstance(obj, dict):
        return VendorParsedResult(status=CLAUDE_ENVELOPE_NON_OBJECT, raw=raw)
    payload = cast("dict[str, object]", obj)
    if payload.get("is_error"):
        return VendorParsedResult(status=CLAUDE_ENVELOPE_IS_ERROR, raw=raw, is_error=True)
    if "result" not in payload:
        return VendorParsedResult(status=CLAUDE_ENVELOPE_MISSING_RESULT, raw=raw)
    value = payload.get("result")
    if not isinstance(value, str):
        return VendorParsedResult(status=CLAUDE_ENVELOPE_NON_STRING_RESULT, raw=raw)
    if not value:
        return VendorParsedResult(status=CLAUDE_ENVELOPE_EMPTY_RESULT, raw=raw)
    return VendorParsedResult(status=CLAUDE_ENVELOPE_OK, text=value, raw=raw)


def run_with_vendor_retries(
    execute: Callable[[], VendorProcessResult],
    *,
    policy: VendorRetryPolicy,
) -> VendorProcessResult:
    """Retry ``execute`` for auth, transient, and empty-response classifiers.

    Auth retries take precedence over transient/empty when both match. Exhaustion
    returns the final process result without raising.
    """
    auth_retries = 0
    transient_retries = 0
    empty_retries = 0
    result = execute()
    while True:
        if result.exit_code == 0 and not (
            policy.is_empty_response is not None and policy.is_empty_response(result)
        ):
            return result
        is_auth = policy.is_auth_failure is not None and policy.is_auth_failure(result)
        is_transient = (
            policy.is_transient_failure is not None and policy.is_transient_failure(result)
        )
        is_empty = policy.is_empty_response is not None and policy.is_empty_response(result)

        def _noop_sleep(_seconds: float) -> None:
            return None

        sleeper: Callable[[float], None] = policy.sleep if policy.sleep is not None else _noop_sleep
        if is_auth and auth_retries < policy.max_auth_retries:
            auth_retries += 1
            if policy.delay_seconds > 0:
                sleeper(policy.delay_seconds)
            result = execute()
            continue
        if not is_auth and is_transient and transient_retries < policy.max_transient_retries:
            transient_retries += 1
            if policy.delay_seconds > 0:
                sleeper(policy.delay_seconds)
            result = execute()
            continue
        if not is_auth and is_empty and empty_retries < policy.max_empty_retries:
            empty_retries += 1
            if policy.delay_seconds > 0:
                sleeper(policy.delay_seconds)
            result = execute()
            continue
        return result


def _invoke_execute(
    *,
    family: VendorFamilyHooks,
    argv: list[str],
    request: VendorLaunchRequest,
    descriptor: VendorDescriptor,
    model: str,
) -> VendorProcessResult:
    if family.execute is None:
        raise RuntimeError("run_vendor_launch requires hooks.execute")
    outcome = family.execute(
        argv=argv,
        request=request,
        descriptor=descriptor,
        model=model,
    )
    if isinstance(outcome, VendorProcessResult):
        return outcome
    if isinstance(outcome, int):
        return VendorProcessResult(exit_code=outcome)
    raise TypeError("hooks.execute must return VendorProcessResult or int")


def _execute_with_retries(  # noqa: PLR0913 - launch context fields stay explicit for callers
    *,
    family: VendorFamilyHooks,
    argv: list[str],
    request: VendorLaunchRequest,
    descriptor: VendorDescriptor,
    model: str,
    retry_policy: VendorRetryPolicy | None,
) -> VendorProcessResult:
    def _execute_once() -> VendorProcessResult:
        return _invoke_execute(
            family=family,
            argv=argv,
            request=request,
            descriptor=descriptor,
            model=model,
        )

    if family.retry is not None:
        process_result = family.retry(
            _execute_once,
            argv=argv,
            request=request,
            descriptor=descriptor,
            model=model,
        )
        if not isinstance(process_result, VendorProcessResult):
            raise TypeError("hooks.retry must return VendorProcessResult")
        return process_result
    if retry_policy is not None:
        return run_with_vendor_retries(_execute_once, policy=retry_policy)
    return _execute_once()


def _run_post_execution_hooks(  # noqa: PLR0913 - lifecycle hook kwargs stay explicit
    *,
    family: VendorFamilyHooks,
    process_result: VendorProcessResult,
    request: VendorLaunchRequest,
    descriptor: VendorDescriptor,
    argv: list[str],
    model: str,
) -> None:
    hook_kwargs = {
        "result": process_result,
        "request": request,
        "descriptor": descriptor,
        "argv": argv,
        "model": model,
    }
    if family.mirror_quota is not None:
        family.mirror_quota(**hook_kwargs)
    if family.record_timing is not None:
        family.record_timing(**hook_kwargs)
    if family.postprocess is not None:
        family.postprocess(**hook_kwargs)
    if family.record_usage is not None:
        family.record_usage(**hook_kwargs)
    if family.promote_completion is not None:
        family.promote_completion(**hook_kwargs)


def run_vendor_launch(  # noqa: PLR0913 - injectable seams are independent lifecycle parameters
    descriptor: VendorDescriptor,
    profile: str,
    request: VendorLaunchRequest,
    *,
    hooks: VendorFamilyHooks | None = None,
    resolve_model: Callable[[VendorLaunchRequest], VendorLaunchRequest] | None = None,
    use_config_context: bool | None = None,
    budget_runner: Callable[[Sequence[str]], Any] | None = None,
    retry_policy: VendorRetryPolicy | None = None,
) -> VendorLaunchOutcome:
    """Shared vendor launch lifecycle (inactive; callers inject executors/hooks).

    Order: positive-cap check → preflight → model resolution → configuration
    context → argv construction → retrying execution → quota mirroring →
    timing → family postprocessing → usage recording → completion promotion.
    """
    family = hooks if hooks is not None else descriptor.hooks

    cap_check = check_token_budget_cap(
        cap=request.token_cap,
        step=request.timing_task_kind,
        runner=budget_runner,
    )
    if cap_check.hit:
        if family.emit_cap_hit_artifact is not None:
            family.emit_cap_hit_artifact(
                payload=cap_check.payload,
                stdout=cap_check.stdout,
                request=request,
                descriptor=descriptor,
            )
        return VendorLaunchOutcome(status="cap_hit", cap_check=cap_check)

    if family.preflight is not None:
        allowed = family.preflight(request=request, descriptor=descriptor)
        if allowed is False:
            return VendorLaunchOutcome(status="preflight_refused", cap_check=cap_check)

    working = resolve_model(request) if resolve_model is not None else request
    enter_config = (
        use_config_context if use_config_context is not None else descriptor.key == "cursor"
    )
    config_cm: contextlib.AbstractContextManager[object] = (
        cursor_config_context() if enter_config else contextlib.nullcontext()
    )

    with config_cm:
        argv = descriptor.build_argv(profile, working)
        model = descriptor.extract_model(argv) or working.model
        process_result = _execute_with_retries(
            family=family,
            argv=argv,
            request=working,
            descriptor=descriptor,
            model=model,
            retry_policy=retry_policy,
        )
        _run_post_execution_hooks(
            family=family,
            process_result=process_result,
            request=working,
            descriptor=descriptor,
            argv=argv,
            model=model,
        )

    return VendorLaunchOutcome(
        status="completed",
        process_result=process_result,
        model=model,
        argv=tuple(argv),
        cap_check=cap_check,
    )
