# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /upgrade-larch."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from contextlib import suppress
from pathlib import Path

from larch.core import config
from larch.core import logging_util
from larch.core import proc

LARCH_SPARSE_DIRS = ".claude-plugin agents docs hooks python scripts skills"
SAFE_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")
KEEP_VERSIONS = 8
DEV_TOP_LEVEL_CLEANUP_DIRS = (
    ".claude",
    ".github",
    ".gemini",
    "tests",
)
TEST_FILE_CLEANUP_PATTERNS = (
    "python/test_*.py",
    "python/conftest.py",
    "python/pyproject.toml",
    "python/ruff.toml",
    "python/requirements-test.txt",
    "python/requirements-dev.txt",
    "python/pyrightconfig.json",
    "python/.pylintrc",
    "python/review_test_support.py",
    "python/harness_*.py",
    "scripts/test-*.sh",
    "scripts/test-*.md",
    "parallel-tests.py",
    "Makefile",
    ".pre-commit-config.yaml",
    ".markdownlint.json",
    ".markdownlintignore",
    "agent-lint.toml",
    ".agnix.toml",
    ".gitleaks.toml",
)
SKILL_HARNESS_CLEANUP_GLOBS = (
    "skills/*/scripts/test-*.sh",
    "skills/*/scripts/test-*.md",
)


def err(message: str = "") -> None:
    logging_util.BreadcrumbWriter().emit(message)


def is_safe_version(value: str | None) -> bool:
    return bool(value and SAFE_VERSION_RE.match(value))


def normalize_sparse_dirs() -> str:
    return "\n".join(sorted(part for part in LARCH_SPARSE_DIRS.split() if part))


def marketplace_clone_path(home: Path | None = None) -> Path | None:
    root: Path | None = home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    return root / ".claude/plugins/marketplaces/larch-local" if root else None


def release_step7_cache_parent(home: Path | None = None) -> Path | None:
    root: Path | None = home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    return root / ".claude/plugins/cache/larch-local/larch" if root else None


def _resolve_confined_version_dir(version: str) -> Path | None:
    if not is_safe_version(version):
        err("Skipping dev/test cache cleanup: installed version is missing or unsafe.")
        return None
    cache_parent = release_step7_cache_parent()
    if cache_parent is None or not cache_parent.exists():
        err("Skipping dev/test cache cleanup: larch cache parent is missing.")
        return None
    version_dir = cache_parent / version
    if version_dir.is_symlink():
        err(f"Skipping dev/test cache cleanup for larch {version}: cache version directory is a symlink.")
        return None
    if not version_dir.is_dir():
        err(f"Skipping dev/test cache cleanup for larch {version}: cache version directory is missing or not a directory.")
        return None
    try:
        version_root = version_dir.resolve()
        cache_root = cache_parent.resolve()
        version_root.relative_to(cache_root)
    except (OSError, ValueError):
        err(f"Skipping dev/test cache cleanup for larch {version}: cache version directory escaped the larch cache parent.")
        return None
    return version_root


def _is_confined_cleanup_candidate(*, candidate: Path, version_root: Path) -> bool:
    if not candidate.exists():
        return False
    try:
        resolved_candidate = candidate.resolve()
        resolved_version_root = version_root.resolve()
        resolved_candidate.relative_to(resolved_version_root)
    except (OSError, ValueError):
        return False
    return True


def _is_confined_direct_child_dir(*, candidate: Path, version_root: Path) -> bool:
    if candidate.parent != version_root or not candidate.exists() or candidate.is_symlink() or not candidate.is_dir():
        return False
    try:
        resolved_candidate = candidate.resolve()
        resolved_version_root = version_root.resolve()
        resolved_candidate.relative_to(resolved_version_root)
    except (OSError, ValueError):
        return False
    return True


def _glob_cache_cleanup(*, version_root: Path, pattern: str) -> list[Path]:
    try:
        return list(version_root.glob(pattern))
    except OSError as exc:
        err(f"Warning: failed to scan dev/test cache cleanup pattern '{pattern}': {exc}")
        return []


def clean_test_files_from_cache(version: str) -> None:
    version_root = _resolve_confined_version_dir(version)
    if version_root is None:
        err("Dev/test cache cleanup skipped.")
        return
    file_candidates: set[Path] = set()
    for pattern in TEST_FILE_CLEANUP_PATTERNS:
        for candidate in _glob_cache_cleanup(version_root=version_root, pattern=pattern):
            if candidate.is_file() or candidate.is_symlink():
                file_candidates.add(candidate)
    for pattern in SKILL_HARNESS_CLEANUP_GLOBS:
        for candidate in _glob_cache_cleanup(version_root=version_root, pattern=pattern):
            if candidate.is_file() or candidate.is_symlink():
                file_candidates.add(candidate)
    dir_candidates = [version_root / name for name in DEV_TOP_LEVEL_CLEANUP_DIRS]
    if not file_candidates and not any(candidate.exists() for candidate in dir_candidates):
        err("No dev/test cache cleanup candidates matched.")
    removed_files = 0
    for candidate in sorted(file_candidates, key=lambda path: path.as_posix()):
        if not _is_confined_cleanup_candidate(candidate=candidate, version_root=version_root):
            continue
        try:
            candidate.unlink()
            removed_files += 1
        except OSError as exc:
            err(f"Warning: failed to remove dev/test cache file '{candidate}': {exc}")
    removed_dirs = 0
    for candidate in dir_candidates:
        if not _is_confined_direct_child_dir(candidate=candidate, version_root=version_root):
            continue
        try:
            shutil.rmtree(candidate)
            removed_dirs += 1
        except OSError as exc:
            err(f"Warning: failed to remove dev/test cache directory '{candidate}': {exc}")
    err(f"Removed {removed_files} dev/test cache files.")
    err(f"Removed {removed_dirs} dropped dev top-level directories.")


def get_installed_larch_version() -> str:
    result = proc.run(["claude", "plugin", "list"])
    if result.returncode == 0:
        lines = result.stdout.splitlines()
        for index, line in enumerate(lines):
            if "larch@larch-local" not in line:
                continue
            for next_line in lines[index + 1 : index + 8]:
                stripped = next_line.strip()
                if stripped.startswith("Version:"):
                    version = stripped.removeprefix("Version:").strip()
                    if is_safe_version(version):
                        return version
    home = os.environ.get("HOME")
    if not home:
        return ""
    installed = Path(home) / ".claude/plugins/installed_plugins.json"
    try:
        data: object = json.loads(installed.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    text = json.dumps(data)
    match = re.search(r'"larch@larch-local".*?"version"\s*:\s*"([0-9.]+)"', text)
    if match and is_safe_version(match.group(1)):
        return match.group(1)
    return ""


def is_cache_shaped_larch_root(root: str | Path | None) -> bool:
    if not root:
        return False
    path = Path(root)
    parent = release_step7_cache_parent()
    if parent is None:
        return False
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return path.is_dir() and is_safe_version(path.name)


def single_larch_cache_version_dir() -> Path | None:
    parent = release_step7_cache_parent()
    if parent is None or not parent.is_dir():
        return None
    dirs: list[Path] = [entry for entry in parent.iterdir() if entry.is_dir() and is_safe_version(entry.name)]
    return dirs[0] if len(dirs) == 1 else None


def resolve_release_step7_root(current_version: str = "") -> Path | None:
    active = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if is_cache_shaped_larch_root(active):
        return Path(active)
    parent = release_step7_cache_parent()
    if parent is None:
        return None
    installed_version = get_installed_larch_version()
    if is_safe_version(installed_version) and (parent / installed_version).is_dir():
        return parent / installed_version
    if is_safe_version(current_version):
        current_root = parent / current_version
        sole = single_larch_cache_version_dir()
        if current_root.is_dir() and sole == current_root:
            return current_root
    sole = single_larch_cache_version_dir()
    if is_safe_version(current_version) and sole == parent / current_version:
        return sole
    return None



def sparse_dirs_main(argv: list[str] | None = None) -> int:
    """Emit the normalized sparse checkout allowlist."""
    argparse.ArgumentParser(prog="cli.py upgrade-larch sparse-dirs").parse_args(argv)
    print(normalize_sparse_dirs())
    return 0

def release_step7_root_main(argv: list[str]) -> int:
    current_version = ""
    index = 0
    while index < len(argv):
        if argv[index] == "--current-version" and index + 1 < len(argv):
            current_version = argv[index + 1]
            index += 2
        elif not argv[index].startswith("-") and not current_version:
            current_version = argv[index]
            index += 1
        else:
            err(f"ERROR=Unknown argument: {argv[index]}")
            return 1
    root = resolve_release_step7_root(current_version)
    if root is None:
        err("ERROR=Unable to resolve larch cache root")
        return 1
    print(f"RESOLVED_ROOT={root}")
    return 0


def stat_mtime(path: Path) -> int:
    try:
        return int(path.stat().st_mtime)
    except OSError:
        return 0


def read_install_stamp(version_dir: Path) -> int | None:
    try:
        value = (version_dir / ".larch-installed-at").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return int(value) if value.isdigit() else None


def write_install_stamp(*, cache_dir: Path, version: str) -> None:
    version_dir = cache_dir / version
    if not version_dir.is_dir():
        return
    try:
        (version_dir / ".larch-installed-at").write_text(f"{int(time.time())}\n", encoding="utf-8")
    except OSError:
        err(f"Warning: failed to write install stamp for cached larch version '{version}'.")


def list_cached_versions_by_install_stamp(cache_dir: Path) -> list[str]:
    rows: list[tuple[int, int, str]] = []
    if not cache_dir.is_dir():
        return []
    for version_dir in cache_dir.iterdir():
        if not version_dir.is_dir() or not is_safe_version(version_dir.name):
            continue
        stamp = read_install_stamp(version_dir)
        if stamp is None:
            rows.append((0, stat_mtime(version_dir), version_dir.name))
        else:
            rows.append((1, stamp, version_dir.name))
    rows.sort(key=lambda row: (row[0], row[1], tuple(int(part) for part in row[2].split("."))), reverse=True)
    return [row[2] for row in rows]


def backfill_install_stamps(cache_dir: Path) -> None:
    if not cache_dir.is_dir():
        return
    for version_dir in cache_dir.iterdir():
        if not version_dir.is_dir() or not is_safe_version(version_dir.name) or read_install_stamp(version_dir) is not None:
            continue
        mtime = stat_mtime(version_dir)
        if mtime > 0:
            try:
                (version_dir / ".larch-installed-at").write_text(f"{mtime}\n", encoding="utf-8")
            except OSError:
                err(f"Warning: failed to write install stamp for cached larch version '{version_dir.name}'.")


def prune_cached_versions(*, cache_dir: Path, target_version: str, installed_version: str = "") -> None:
    err("Pruning old larch versions (keeping up to 8 most-recently-installed)...")
    backfill_install_stamps(cache_dir)
    retained: list[str] = []
    for protected in (target_version, installed_version):
        if protected and is_safe_version(protected) and (cache_dir / protected).is_dir() and protected not in retained:
            retained.append(protected)
    for version in list_cached_versions_by_install_stamp(cache_dir):
        if version not in retained:
            retained.append(version)
        if len(retained) >= KEEP_VERSIONS:
            break
    removed = 0
    if cache_dir.is_dir():
        for version_dir in cache_dir.iterdir():
            if not version_dir.is_dir() or not is_safe_version(version_dir.name) or version_dir.name in retained:
                continue
            try:
                shutil.rmtree(version_dir)
                removed += 1
            except OSError:
                err(f"Warning: failed to prune cached larch version '{version_dir.name}'.")
    if removed == 0:
        err("  No old versions to prune.")


def _marketplace_sparse_cone_matches() -> bool:
    clone = marketplace_clone_path()
    if clone is None or not (clone / ".git").exists() or (clone / "larch-logs").exists():
        return False
    result = proc.run(["git", "-C", str(clone), "sparse-checkout", "list"])
    configured = "\n".join(sorted(line for line in result.stdout.splitlines() if line.strip()))
    return result.returncode == 0 and configured == normalize_sparse_dirs()


def _get_stable_releases() -> list[str]:
    if shutil.which("gh") is None:
        err("Warning: gh is not available; upgrading without stable verification.")
        return []
    result = proc.run(["gh", "api", "--paginate", "repos/character-ai/larch/releases", "--jq", ".[] | select(.prerelease == false and .draft == false) | .tag_name"])
    if result.returncode != 0:
        err(f"Warning: failed to query GitHub stable releases via gh (exit {result.returncode}); upgrading without stable verification.")
        return []
    releases = [line.removeprefix("v") for line in result.stdout.splitlines() if is_safe_version(line.removeprefix("v"))]
    if not releases:
        err("Warning: gh returned no valid stable larch release tags; upgrading without stable verification.")
    return releases


def _recover_diagnostics() -> None:
    clone = marketplace_clone_path()
    err("")
    err("Recovery: run these commands manually to reinstall:")
    err("  claude plugin marketplace remove larch-local")
    if clone is not None:
        err(f"  rm -rf {clone}")
    else:
        err("  rm -rf ~/.claude/plugins/marketplaces/larch-local")
    err(f"  claude plugin marketplace add character-ai/larch --sparse {LARCH_SPARSE_DIRS}")
    err("  claude plugin install larch@larch-local")


def _refresh_marketplace() -> bool:
    clone = marketplace_clone_path()
    if _marketplace_sparse_cone_matches():
        err("Refreshing larch marketplace in place (sparse clone present)...")
        result = proc.run(["claude", "plugin", "marketplace", "update", "larch-local"])
        if result.returncode == 0:
            return True
        err("marketplace update failed; falling back to sparse re-add...")
    else:
        err("Adding larch marketplace (sparse checkout; excludes dev-only top-level directories and larch-logs)...")
    proc.run(["claude", "plugin", "marketplace", "remove", "larch-local"])
    if clone is not None and clone.exists():
        try:
            shutil.rmtree(clone)
        except OSError as exc:
            err(f"Warning: failed to remove marketplace clone '{clone}': {exc}")
            return False
    add = proc.run(["claude", "plugin", "marketplace", "add", "character-ai/larch", "--sparse", *LARCH_SPARSE_DIRS.split()])
    return add.returncode == 0


def _restore_operator_stdout() -> None:
    if os.environ.get(config.ENV_LARCH_QUIET_PID) == str(os.getpid()):
        with suppress(OSError):
            os.dup2(3, 1)


def run_main(argv: list[str]) -> int:
    if argv:
        err(f"ERROR=Unknown argument: {argv[0]}")
        return 1
    logging_util.quiet_init(argv0="upgrade-larch.sh")
    _restore_operator_stdout()
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path.cwd())).resolve()
    cache_dir = plugin_root.parent
    installed_version = plugin_root.name
    latest = os.environ.get("LARCH_EXPECTED_STABLE_VERSION", "") if is_safe_version(os.environ.get("LARCH_EXPECTED_STABLE_VERSION", "")) else ""
    if not latest:
        releases = _get_stable_releases()
        latest = releases[0] if releases else ""
    current = get_installed_larch_version() or installed_version
    cone_will_reconcile = not _marketplace_sparse_cone_matches()
    active_root_stale = False
    if latest and current == latest and not cone_will_reconcile and (not is_cache_shaped_larch_root(plugin_root) or plugin_root.name == latest):
        write_install_stamp(cache_dir=cache_dir, version=current)
        clean_test_files_from_cache(current)
        prune_cached_versions(cache_dir=cache_dir, target_version=current, installed_version=installed_version)
        err("")
        err(f"Already at latest stable larch release ({current}). No upgrade needed.")
        return 0
    if (
        latest
        and current == latest
        and is_cache_shaped_larch_root(plugin_root)
        and plugin_root.name != latest
    ):
        active_root_stale = True
        err("")
        err(
            f"Installed metadata is already at latest stable larch release ({current}), "
            f"but this Claude Code session is still running cached larch {plugin_root.name}. "
            "Refreshing the install and requiring restart...",
        )
    elif latest and current == latest and cone_will_reconcile:
        err("")
        err(f"Already at latest stable larch release ({current}), but the sparse checkout is out of date (allowlist changed). Reconciling the marketplace cone and reinstalling...")
    elif latest:
        err(f"Upgrading larch from {installed_version} to {latest}...")
    else:
        err("Latest stable release could not be determined; upgrading unconditionally...")
    err("Uninstalling larch plugin...")
    proc.run(["claude", "plugin", "uninstall", "larch@larch-local"])
    if not _refresh_marketplace():
        _recover_diagnostics()
        err("LARCH_RESTART_REQUIRED=true")
        return 1
    err("Installing larch plugin...")
    install = proc.run(["claude", "plugin", "install", "larch@larch-local"])
    if install.returncode != 0:
        _recover_diagnostics()
        err("LARCH_RESTART_REQUIRED=true")
        return install.returncode or 1
    actual = get_installed_larch_version()
    clean_test_files_from_cache(actual)
    verified = bool(latest and actual == latest)
    if cone_will_reconcile:
        if _marketplace_sparse_cone_matches():
            err("LARCH_CONE_RECONCILED=true")
        else:
            err("LARCH_CONE_RECONCILED=false")
        err("LARCH_RESTART_REQUIRED=true")
    if not latest or active_root_stale:
        err("LARCH_RESTART_REQUIRED=true")
    elif verified and actual != current:
        err("LARCH_NEW_VERSION_INSTALLED=true")
    elif not verified:
        err("LARCH_RESTART_REQUIRED=true")
    if verified:
        write_install_stamp(cache_dir=cache_dir, version=actual)
        prune_cached_versions(cache_dir=cache_dir, target_version=actual, installed_version=installed_version)
    else:
        err("Skipping prune because the expected stable version was not verified.")
    err("")
    err("Installed larch plugin version:")
    listed = proc.run(["claude", "plugin", "list"])
    if listed.stdout:
        print(listed.stdout, end="")
    err("")
    if latest and not verified:
        err(f"Upgrade incomplete: expected stable version {latest} was not verified.")
        return 1
    err("Upgrade complete. Restart Claude Code to apply the new version.")
    return 0
