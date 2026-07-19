"""Build the runtime-only Claude plugin projection."""

from __future__ import annotations

import argparse
import filecmp
import json
import shutil
from pathlib import Path
from typing import cast

from larch.core import proc

_DIRECT_FILES = frozenset(
    {
        ".claude-plugin/plugin.json",
        "LICENSE",
        "docs/configuration-and-permissions.md",
        "docs/difficulty-floor-globs.tsv",
        "docs/external-reviewers.md",
        "docs/installation-and-setup.md",
        "docs/issue-anchored-plan.md",
        "docs/linting.md",
        "docs/python-migration.md",
        "docs/review-agents.md",
        "docs/run-log-batches.md",
        "docs/run-log-cli.md",
        "docs/run-logs-required-files.tsv",
        "docs/run-logs.md",
        "docs/skills.md",
        "python/cli.py",
        "python/stall-recovery-report.md",
        "scripts/block-submodule-edit.sh",
        "scripts/check-stale-plugin.sh",
        "scripts/cleanup-sessionstart.sh",
        "scripts/deny-edit-write.sh",
        "scripts/dry-runnable-scripts.tsv",
        "scripts/file-failure-report-cross-repo.sh",
        "scripts/flush-vendor-failure-diagnostics.sh",
        "scripts/generators.tsv",
        "scripts/hook-anti-read-poll.sh",
        "scripts/hook-deny-run-in-background.sh",
        "scripts/larch.sh",
        "scripts/read-result-env.sh",
        "scripts/resolve-upstream-larch-repo.sh",
        "scripts/sessionstart-health.sh",
        "scripts/sessionstart-statusline.sh",
        "scripts/sleep-seconds.sh",
        "scripts/sweep-design-logs.sh",
    }
)

_DEV_ONLY_PYTHON = frozenset(
    {
        "python/larch/calibration/calibration_replay.py",
        "python/larch/core/residual_bash.py",
        "python/larch/report/retro_fix_cursor.py",
        "python/larch/report/retro_v3_sweep.py",
    }
)


def _is_test_path(path: str) -> bool:
    return any(
        part in {"fixtures", "tests"} or part.startswith(("test-", "test_"))
        for part in Path(path).parts
    )


def runtime_paths(root: Path) -> tuple[str, ...]:
    """Return the tracked files copied into the installed plugin cache."""
    result = proc.run(["git", "-C", str(root), "ls-files", "-z"], timeout=30)
    if result.returncode != 0:
        raise RuntimeError("plugin runtime projection requires a readable git index")
    selected: set[str] = set()
    for path in result.stdout.split("\0"):
        if (
            not path
            or path.startswith("plugin/")
            or path in _DEV_ONLY_PYTHON
            or "__pycache__" in Path(path).parts
        ):
            continue
        if (
            path in _DIRECT_FILES
            or path.startswith(("agents/", "hooks/"))
            or (path.startswith("skills/") and not _is_test_path(path))
        ):
            selected.add(path)
        elif path.startswith("python/larch/") and not _is_test_path(path):
            package = Path(path).parts[2]
            if package not in {"lint", "release"}:
                selected.add(path)
    missing = sorted(path for path in _DIRECT_FILES if path not in selected)
    if missing:
        raise RuntimeError(
            f"plugin runtime projection inputs are missing: {', '.join(missing)}"
        )
    unsafe = sorted(
        path
        for path in selected
        if (root / path).is_symlink() or not (root / path).is_file()
    )
    if unsafe:
        raise RuntimeError(
            f"plugin runtime projection inputs are unsafe: {', '.join(unsafe)}"
        )
    return tuple(sorted(selected))


def _validate_root(root: Path) -> None:
    manifest = root / ".claude-plugin/plugin.json"
    authority = root / "python/larch/release/plugin_runtime.py"
    try:
        payload: object = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "plugin runtime projection requires the larch repository root"
        ) from error
    if not isinstance(payload, dict):
        raise RuntimeError(  # noqa: TRY004 - malformed repository manifest is an external-state failure
            "plugin runtime projection requires the larch repository root"
        )
    manifest_data = cast("dict[str, object]", payload)
    if (
        manifest_data.get("name") != "larch"
        or not (root / ".git").exists()
        or authority.resolve() != Path(__file__).resolve()
    ):
        raise RuntimeError(
            "plugin runtime projection requires the larch repository root"
        )


def projection_errors(root: Path) -> list[str]:
    """Return projection drift without changing the worktree."""
    expected = set(runtime_paths(root))
    projection = root / "plugin"
    if projection.is_symlink():
        return ["runtime projection root must be a real directory"]
    actual: set[str] = (
        {
            path.relative_to(projection).as_posix()
            for path in projection.rglob("*")
            if path.is_symlink() or path.is_file()
        }
        if projection.is_dir()
        else set()
    )
    errors = [
        f"missing runtime projection: {path}" for path in sorted(expected - actual)
    ]
    errors.extend(
        f"unexpected runtime projection: {path}" for path in sorted(actual - expected)
    )
    for source in sorted(expected & actual):
        copy = projection / source
        if (
            copy.is_symlink()
            or not copy.is_file()
            or not filecmp.cmp(root / source, copy, shallow=False)
        ):
            errors.append(f"runtime projection differs from its source: {source}")
    return errors


def sync(root: Path) -> None:
    """Replace only the repository's bounded ``plugin/`` projection."""
    _validate_root(root)
    projection = root / "plugin"
    if projection.exists() or projection.is_symlink():
        if (
            projection.is_symlink()
            or not projection.is_dir()
            or projection.parent != root
        ):
            raise RuntimeError("refusing to replace an unsafe plugin projection path")
        shutil.rmtree(projection)
    for source in runtime_paths(root):
        destination = projection / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(root / source, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py release plugin-runtime")
    _ = parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    if args.check:
        errors = projection_errors(root)
        if errors:
            print("\n".join(errors))
            return 1
        return 0
    sync(root)
    return 0
