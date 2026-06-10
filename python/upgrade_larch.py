# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /upgrade-larch."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import proc

LARCH_SPARSE_DIRS = ".claude .claude-plugin .gemini .github agents docs hooks python scripts skills tests"
SAFE_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")
KEEP_VERSIONS = 8


def err(message: str = "") -> None:
    print(message, file=sys.stderr)


def is_safe_version(value: str | None) -> bool:
    return bool(value and SAFE_VERSION_RE.match(value))


def normalize_sparse_dirs() -> str:
    return "\n".join(sorted(part for part in LARCH_SPARSE_DIRS.split() if part))


def marketplace_clone_path(home: Path | None = None) -> Path | None:
    root = home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    return root / ".claude/plugins/marketplaces/larch-local" if root else None


def release_step7_cache_parent(home: Path | None = None) -> Path | None:
    root = home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    return root / ".claude/plugins/cache/larch-local/larch" if root else None


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
        data = json.loads(installed.read_text(encoding="utf-8"))
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
    dirs = [entry for entry in parent.iterdir() if entry.is_dir() and is_safe_version(entry.name)]
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


def write_install_stamp(cache_dir: Path, version: str) -> None:
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


def prune_cached_versions(cache_dir: Path, target_version: str, installed_version: str = "") -> None:
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
    result = proc.run(["gh", "api", "--paginate", "repos/character-ai/larch/releases", "--jq", ".[] | select(.prerelease == false and .draft == false) | .tag_name"])
    if result.returncode != 0:
        return []
    return [line.removeprefix("v") for line in result.stdout.splitlines() if is_safe_version(line.removeprefix("v"))]


def _refresh_marketplace() -> None:
    clone = marketplace_clone_path()
    if _marketplace_sparse_cone_matches():
        err("Refreshing larch marketplace in place (sparse clone present)...")
        result = proc.run(["claude", "plugin", "marketplace", "update", "larch-local"])
        if result.returncode == 0:
            return
        err("marketplace update failed; falling back to sparse re-add...")
    else:
        err("Adding larch marketplace (sparse checkout; excludes larch-logs)...")
    proc.run(["claude", "plugin", "marketplace", "remove", "larch-local"])
    if clone is not None and clone.exists():
        shutil.rmtree(clone)
    proc.run(["claude", "plugin", "marketplace", "add", "character-ai/larch", "--sparse", *LARCH_SPARSE_DIRS.split()])


def run_main(argv: list[str]) -> int:
    if argv:
        err(f"ERROR=Unknown argument: {argv[0]}")
        return 1
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path.cwd())).resolve()
    cache_dir = plugin_root.parent
    installed_version = plugin_root.name
    latest = os.environ.get("LARCH_EXPECTED_STABLE_VERSION", "") if is_safe_version(os.environ.get("LARCH_EXPECTED_STABLE_VERSION", "")) else ""
    if not latest:
        releases = _get_stable_releases()
        latest = releases[0] if releases else ""
    current = get_installed_larch_version() or installed_version
    cone_will_reconcile = not _marketplace_sparse_cone_matches()
    if latest and current == latest and not cone_will_reconcile and (not is_cache_shaped_larch_root(plugin_root) or plugin_root.name == latest):
        write_install_stamp(cache_dir, current)
        prune_cached_versions(cache_dir, current, installed_version)
        err("")
        err(f"Already at latest stable larch release ({current}). No upgrade needed.")
        return 0
    if latest and current == latest and cone_will_reconcile:
        err("")
        err(f"Already at latest stable larch release ({current}), but the sparse checkout is out of date (allowlist changed). Reconciling the marketplace cone and reinstalling...")
    elif latest:
        err(f"Upgrading larch from {installed_version} to {latest}...")
    else:
        err("Latest stable release could not be determined; upgrading unconditionally...")
    err("Uninstalling larch plugin...")
    proc.run(["claude", "plugin", "uninstall", "larch@larch-local"])
    _refresh_marketplace()
    err("Installing larch plugin...")
    install = proc.run(["claude", "plugin", "install", "larch@larch-local"])
    actual = get_installed_larch_version()
    verified = bool(latest and actual == latest)
    if cone_will_reconcile:
        if _marketplace_sparse_cone_matches():
            err("LARCH_CONE_RECONCILED=true")
        else:
            err("LARCH_CONE_RECONCILED=false")
        err("LARCH_RESTART_REQUIRED=true")
    if not latest:
        err("LARCH_RESTART_REQUIRED=true")
    elif verified and actual != current:
        err("LARCH_NEW_VERSION_INSTALLED=true")
    elif not verified:
        err("LARCH_RESTART_REQUIRED=true")
    if verified:
        write_install_stamp(cache_dir, actual)
        prune_cached_versions(cache_dir, actual, installed_version)
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
        return install.returncode or 1
    err("Upgrade complete. Restart Claude Code to apply the new version.")
    return 0
