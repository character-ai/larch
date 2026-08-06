"""Shared repository and installed-plugin root discovery helpers."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from larch.core import config, proc
from larch.core.proc import Runner

class RepoRootResult(Protocol):
    """The command-result fields callers need to interpret a root probe."""

    @property
    def returncode(self) -> int: ...

    @property
    def stdout(self) -> str: ...

    @property
    def stderr(self) -> str: ...


RepoRootRunner = Callable[[list[str]], RepoRootResult]


@dataclass(frozen=True)
class RepoRootProbeOptions:
    """Independent controls for a raw repository-root probe."""

    git_cwd: Path | str | None = None
    runner_cwd: Path | str | None = None
    git_bin: str = "git"
    timeout: float | None = None
    check: bool = False


_DEFAULT_PROBE_OPTIONS: Final = RepoRootProbeOptions()


def repo_root_probe(
    *,
    runner: Runner | None = None,
    run: RepoRootRunner | None = None,
    options: RepoRootProbeOptions = _DEFAULT_PROBE_OPTIONS,
) -> RepoRootResult:
    """Run the repository-top-level probe without discarding its diagnostics.

    ``git_cwd`` emits Git's ``-C`` argument while ``runner_cwd`` sets the
    injected runner's working directory. ``options`` keeps both controls
    independent, so callers
    preserve their existing command shape and inspect nonzero, empty-output,
    or stderr results before deciding their own failure policy.
    """
    argv: list[str] = [options.git_bin]
    if options.git_cwd is not None:
        argv.extend(["-C", str(options.git_cwd)])
    argv.extend(["rev-parse", "--show-toplevel"])
    if run is not None:
        return run(argv)
    cwd = str(options.runner_cwd) if options.runner_cwd is not None else None
    if runner is not None:
        return runner.run(argv, cwd=cwd, timeout=options.timeout, check=options.check)
    return proc.run(argv, cwd=cwd, timeout=options.timeout, check=options.check)


def repo_root_from_probe(result: RepoRootResult) -> Path | None:
    """Return a normalized root for a successful, non-empty probe result."""
    output = result.stdout.strip()
    if result.returncode != 0 or not output:
        return None
    return Path(output).resolve()


def consumer_repo_root(
    cwd: Path | str | None = None,
    *,
    runner: Runner | None = None,
    run: RepoRootRunner | None = None,
    git_bin: str = "git",
) -> Path | None:
    """Return the consumer repo's git toplevel, or ``None`` outside a work tree."""
    start = Path(cwd) if cwd is not None else Path.cwd()
    try:
        result = repo_root_probe(
            runner=runner,
            run=run,
            options=RepoRootProbeOptions(
                git_cwd=start,
                runner_cwd=start,
                git_bin=git_bin,
            ),
        )
    except OSError:
        return None
    return repo_root_from_probe(result)


def plugin_root(fallback: Path | str | None = None, *, use_env: bool = True) -> Path:
    """Return the configured plugin root, falling back to a caller-owned path."""
    configured = os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, "") if use_env else ""
    default = Path(__file__).resolve().parents[3]
    return Path(configured or fallback or default).resolve()


def larch_entrypoint(
    fallback: Path | str | None = None, *, use_env: bool = True
) -> Path:
    """Return the verified bootstrap entrypoint for Rust command cutovers.

    `scripts/larch.sh` refuses to run without `CLAUDE_PLUGIN_ROOT`, so resolving
    the entrypoint also publishes the root it resolved. `setdefault` never
    overrides an operator-supplied root, and it cannot disagree with one:
    :func:`plugin_root` already prefers that same variable when `use_env` is set.
    """
    root = plugin_root(fallback, use_env=use_env)
    _ = os.environ.setdefault(config.ENV_CLAUDE_PLUGIN_ROOT, str(root))
    return root / "scripts" / "larch.sh"


def larch_entrypoint_env(
    fallback: Path | str | None = None, *, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    """Return a child environment that names the plugin root the bootstrap needs.

    `scripts/larch.sh` refuses to run without `CLAUDE_PLUGIN_ROOT`, so a caller
    that resolves the entrypoint from a fallback path must also publish the root
    it resolved rather than relying on an ambient value.
    """
    root = plugin_root(fallback)
    environ = dict(os.environ if base is None else base)
    environ[config.ENV_CLAUDE_PLUGIN_ROOT] = str(root)
    return environ
