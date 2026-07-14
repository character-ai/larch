"""Inactive vendor descriptors, argv builders, and model extraction.

Piece 1 of the vendor foundation (#7204 / #7029.1). Declares the frozen data
model and exact argv builders that later pieces plug lifecycle hooks into.
Production launchers must not import this module yet.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from larch.agents._run_external import (
    _codex_auth_args,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist argv helper
    _trust_config_arg,  # pyright: ignore[reportPrivateUsage]  # lower-level allowlist argv helper
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
