"""Shared guard helpers for write-capable coder fixers."""

from __future__ import annotations

import re
from pathlib import Path

from larch.core import config
from larch.git import git
from larch.core.proc import Runner


def capture_head(runner: Runner, *, cwd: str | None = None) -> str:
    return git.rev_parse(runner, "HEAD", cwd=cwd)


def head_changed_from_baseline( *,baseline_head: str, current_head: str) -> bool:
    return baseline_head != current_head


def tracked_dirty_paths(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    seen: set[str] = set()
    paths: list[str] = []
    for extra in ((), ("--cached",)):
        result = runner.run(["git", "diff", "--name-only", *extra], cwd=cwd)
        for raw in result.stdout.splitlines():
            path = raw.strip()
            if path and path not in seen:
                seen.add(path)
                paths.append(path)
    return tuple(paths)


def untracked_dirty_paths(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    result = runner.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def protected_repo_paths() -> tuple[str, ...]:
    return (config.PLUGIN_JSON_PATH,)


def coder_forbidden_paths(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys((".gitmodules", *protected_repo_paths(), *submodule_paths(runner, cwd=cwd))),
    )


def submodule_paths(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    seen: set[str] = set()
    paths: list[str] = []
    cwd_path = Path(cwd or ".")
    gitmodules = cwd_path / ".gitmodules"
    if gitmodules.is_file():
        result = runner.run(
            ["git", "config", "-f", ".gitmodules", "--get-regexp", r"^[^.]+\.path$"],
            cwd=cwd,
        )
        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[1] not in seen:  # noqa: PLR2004
                seen.add(parts[1])
                paths.append(parts[1])
        for line in gitmodules.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^\s*path\s*=\s*(.+)\s*$", line)
            if match:
                path = match.group(1).strip()
                if path and path not in seen:
                    seen.add(path)
                    paths.append(path)
    result = runner.run(["git", "submodule", "foreach", "--quiet", "echo $sm_path"], cwd=cwd)
    for raw in result.stdout.splitlines():
        path = raw.strip()
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return tuple(paths)


def path_matches_forbidden( *,path: str, forbidden: tuple[str, ...]) -> bool:
    for forbidden_path in forbidden:
        if not forbidden_path:
            continue
        if path == forbidden_path or path.startswith(f"{forbidden_path}/"):
            return True
    return False


def forbidden_paths_match_count( *,paths: tuple[str, ...], forbidden: tuple[str, ...]) -> int:
    return sum(1 for path in paths if path_matches_forbidden(path=path, forbidden=forbidden))


def staged_dirty_paths(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    result = runner.run(["git", "diff", "--name-only", "--cached"], cwd=cwd)
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def revert_forbidden_paths(
    runner: Runner,
    *,
    cwd: str | None,
    forbidden: tuple[str, ...],
    baseline_staged: tuple[str, ...] = (),
) -> int:
    current_tracked = tracked_dirty_paths(runner, cwd=cwd)
    current_untracked = untracked_dirty_paths(runner, cwd=cwd)
    baseline_staged_set = set(baseline_staged)
    revert_count = 0
    seen: set[str] = set()
    for path in (*current_tracked, *current_untracked):
        if not path or path in seen:
            continue
        seen.add(path)
        if not path_matches_forbidden(path=path, forbidden=forbidden):
            continue
        if path in current_untracked:
            _ = runner.run(["rm", "-f", "--", path], cwd=cwd)
        else:
            if path not in baseline_staged_set:
                _ = git.restore_staged(runner, path, cwd=cwd)
            _ = git.checkout_paths(runner, path, cwd=cwd)
        revert_count += 1
    return revert_count
