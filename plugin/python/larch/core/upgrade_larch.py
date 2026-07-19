# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Python entrypoints for /upgrade-larch."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from contextlib import suppress
from pathlib import Path

from larch.core import config
from larch.core import logging_util
from larch.core import proc

LARCH_MARKETPLACE_SOURCE = "https://raw.githubusercontent.com/character-ai/larch/main/.claude-plugin/marketplace.json"
LARCH_SPARSE_DIRS = ".claude-plugin"
SAFE_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)*$")


def err(message: str = "") -> None:
    logging_util.BreadcrumbWriter().emit(message)


def is_safe_version(value: str | None) -> bool:
    return bool(value and SAFE_VERSION_RE.match(value))


def normalize_sparse_dirs() -> str:
    return "\n".join(sorted(part for part in LARCH_SPARSE_DIRS.split() if part))


def marketplace_clone_path(home: Path | None = None) -> Path | None:
    root: Path | None = (
        home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    )
    return (
        root / ".claude/plugins/marketplaces/larch-local"
        if root and root.is_absolute()
        else None
    )


def release_step7_cache_parent(home: Path | None = None) -> Path | None:
    root: Path | None = (
        home or Path(os.environ["HOME"]) if os.environ.get("HOME") else None
    )
    return (
        root / ".claude/plugins/cache/larch-local/larch"
        if root and root.is_absolute()
        else None
    )


def _installed_larch_entries() -> list[dict[str, object]]:
    result = proc.run(["claude", "plugin", "list", "--json"])
    if result.returncode != 0:
        return []
    try:
        payload: object = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [
        entry
        for entry in payload
        if isinstance(entry, dict) and entry.get("id") == "larch@larch-local"
    ]


def get_installed_larch_version() -> str:
    versions = {
        version
        for entry in _installed_larch_entries()
        if isinstance((version := entry.get("version")), str)
        and is_safe_version(version)
    }
    return versions.pop() if len(versions) == 1 else ""


def resolve_installed_larch_root(expected_version: str) -> Path | None:
    if not is_safe_version(expected_version):
        return None
    roots = {
        install_path
        for entry in _installed_larch_entries()
        if entry.get("version") == expected_version
        and isinstance((install_path := entry.get("installPath")), str)
        and install_path
    }
    if len(roots) != 1:
        return None
    root = Path(roots.pop())
    parent = release_step7_cache_parent()
    if (
        not root.is_absolute()
        or parent is None
        or root.is_symlink()
        or not root.is_dir()
    ):
        return None
    try:
        resolved = root.resolve(strict=True)
        resolved.relative_to(parent.resolve(strict=True))
    except (OSError, ValueError):
        return None
    manifest = resolved / ".claude-plugin/plugin.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return (
        resolved
        if isinstance(payload, dict) and payload.get("version") == expected_version
        else None
    )


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
    dirs: list[Path] = [
        entry
        for entry in parent.iterdir()
        if entry.is_dir() and is_safe_version(entry.name)
    ]
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


def _marketplace_source_matches() -> bool:
    result = proc.run(["claude", "plugin", "marketplace", "list", "--json"])
    if result.returncode != 0:
        return False
    try:
        payload: object = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, list):
        return False
    matches = [
        entry
        for entry in payload
        if isinstance(entry, dict) and entry.get("name") == "larch-local"
    ]
    return (
        len(matches) == 1
        and matches[0].get("source") == "url"
        and matches[0].get("url") == LARCH_MARKETPLACE_SOURCE
    )


def _gh_command(argv: list[str]) -> proc.CommandResult:
    from larch.git import gh  # noqa: PLC0415 - core leaf import stays function-local  # lint-layering: ok shared GitHub executable seam

    return gh.command(proc, argv)


def _get_stable_releases() -> list[str]:
    if shutil.which("gh") is None:
        err("Warning: gh is not available; upgrading without stable verification.")
        return []
    result = _gh_command(
        [
            "api",
            "--paginate",
            "repos/character-ai/larch/releases",
            "--jq",
            ".[] | select(.prerelease == false and .draft == false) | .tag_name",
        ]
    )
    if result.returncode != 0:
        err(
            f"Warning: failed to query GitHub stable releases via gh (exit {result.returncode}); upgrading without stable verification."
        )
        return []
    releases = [
        line.removeprefix("v")
        for line in result.stdout.splitlines()
        if is_safe_version(line.removeprefix("v"))
    ]
    if not releases:
        err(
            "Warning: gh returned no valid stable larch release tags; upgrading without stable verification."
        )
    return releases


def _recover_diagnostics() -> None:
    err("")
    err(
        "Recovery: retry /upgrade-larch. The running session and prior cache root remain usable."
    )
    err("If marketplace metadata is incomplete, run:")
    err(f"  claude plugin marketplace add {LARCH_MARKETPLACE_SOURCE}")
    err("  claude plugin install larch@larch-local")


def _refresh_marketplace() -> str:
    clone = marketplace_clone_path()
    if _marketplace_source_matches():
        err("Refreshing the runtime-only larch marketplace...")
        result = proc.run(["claude", "plugin", "marketplace", "update", "larch-local"])
        if result.returncode == 0:
            return "update"
        err("Marketplace refresh failed. The prior plugin cache root was not changed.")
        return ""
    err("Migrating the larch marketplace to the runtime-only remote source...")
    if clone is not None and clone.is_symlink():
        err("Marketplace migration refused a symlinked marketplace clone.")
        return ""
    removed = proc.run(["claude", "plugin", "marketplace", "remove", "larch-local"])
    if removed.returncode != 0:
        err(
            "Marketplace reconciliation stopped because the legacy registration could not be removed."
        )
        return ""
    if clone is not None and clone.exists():
        try:
            shutil.rmtree(clone)
        except OSError as exc:
            err(f"Warning: failed to remove marketplace clone '{clone}': {exc}")
            return ""
    add = proc.run(["claude", "plugin", "marketplace", "add", LARCH_MARKETPLACE_SOURCE])
    return "install" if add.returncode == 0 and _marketplace_source_matches() else ""


def _relay_output(result: proc.CommandResult) -> None:
    for line in result.stderr.splitlines():
        err(line)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")


def _plugin_data_path() -> str:
    value = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    return value if Path(value).is_absolute() else ""


def _preflight_release(*, version: str) -> bool:
    plugin_data = _plugin_data_path()
    script = Path(__file__).resolve().parents[3] / "scripts/larch.sh"
    if not plugin_data or not script.is_file() or script.is_symlink():
        err(
            "Upgrade preflight cannot resolve a safe bootstrap script and CLAUDE_PLUGIN_DATA path."
        )
        return False
    err(f"Preflighting immutable larch release v{version}...")
    result = proc.run(
        [str(script), "--preflight-release", version],
        timeout=600,
        env={**os.environ, "CLAUDE_PLUGIN_DATA": plugin_data},
    )
    _relay_output(result)
    return (
        result.returncode == 0
        and f"LARCH_PREFLIGHT_VERSION={version}" in result.stdout.splitlines()
    )


def _bootstrap_installed_root(*, root: Path, version: str) -> bool:
    plugin_data = _plugin_data_path()
    script = root / "scripts/larch.sh"
    binary = root / "bin/larch"
    if not plugin_data or not script.is_file() or script.is_symlink():
        err(
            "Installed plugin metadata resolved a root without a safe bootstrap script."
        )
        return False
    environment = {
        **os.environ,
        "CLAUDE_PLUGIN_ROOT": str(root),
        "CLAUDE_PLUGIN_DATA": plugin_data,
    }
    result = proc.run(
        [str(script), "bootstrap", "self-check"], timeout=600, env=environment
    )
    _relay_output(result)
    if (
        result.returncode != 0
        or not binary.is_file()
        or binary.is_symlink()
        or not os.access(binary, os.X_OK)
    ):
        return False
    direct = proc.run(
        [str(binary), "bootstrap", "self-check"], timeout=30, env=environment
    )
    if direct.returncode != 0 or direct.stdout != result.stdout:
        return False
    try:
        identity: object = json.loads(direct.stdout)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(identity, dict)
        and identity.get("schema_version") == 1
        and identity.get("version") == version
    )


def _restore_operator_stdout() -> None:
    if os.environ.get(config.ENV_LARCH_QUIET_PID) == str(os.getpid()):
        with suppress(OSError):
            os.dup2(3, 1)


def run_main(argv: list[str]) -> int:  # noqa: PLR0911 - each upgrade gate fails closed with its own recovery boundary
    if argv:
        err(f"ERROR=Unknown argument: {argv[0]}")
        return 1
    logging_util.quiet_init(argv0="upgrade-larch.sh")
    _restore_operator_stdout()
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path.cwd())).resolve()
    installed_version = plugin_root.name
    latest = (
        os.environ.get("LARCH_EXPECTED_STABLE_VERSION", "")
        if is_safe_version(os.environ.get("LARCH_EXPECTED_STABLE_VERSION", ""))
        else ""
    )
    if not latest:
        releases = _get_stable_releases()
        latest = releases[0] if releases else ""
    current = get_installed_larch_version() or installed_version
    marketplace_will_reconcile = not _marketplace_source_matches()
    if (
        latest
        and current == latest
        and not marketplace_will_reconcile
        and (not is_cache_shaped_larch_root(plugin_root) or plugin_root.name == latest)
    ):
        current_root = resolve_installed_larch_root(current)
        if current_root is None or not _bootstrap_installed_root(
            root=current_root, version=current
        ):
            _recover_diagnostics()
            return 1
        err("")
        err(
            f"Already at latest stable larch release ({current}). Binary verification passed. No upgrade needed."
        )
        return 0
    if (
        latest
        and current == latest
        and is_cache_shaped_larch_root(plugin_root)
        and plugin_root.name != latest
    ):
        err("")
        err(
            f"Installed metadata is already at latest stable larch release ({current}), "
            f"but this Claude Code session is still running cached larch {plugin_root.name}. "
            "Refreshing the install and requiring restart...",
        )
    elif latest and current == latest and marketplace_will_reconcile:
        err("")
        err(
            f"Already at latest stable larch release ({current}), but the marketplace still uses the legacy source. Migrating it to the runtime-only source and reinstalling..."
        )
    elif latest:
        err(f"Upgrading larch from {installed_version} to {latest}...")
    else:
        err(
            "Latest stable release could not be determined. Upgrade stopped before changing plugin state."
        )
        _recover_diagnostics()
        return 1
    if not _preflight_release(version=latest):
        err("Upgrade stopped because stable release preflight failed.")
        _recover_diagnostics()
        return 1
    refresh_mode = _refresh_marketplace()
    if not refresh_mode:
        _recover_diagnostics()
        return 1
    err("Installing the preflighted larch plugin release...")
    command = [
        "claude",
        "plugin",
        "install" if refresh_mode == "install" else "update",
        "larch@larch-local",
    ]
    install = proc.run(command)
    if install.returncode != 0:
        err("Plugin install failed. The prior cache root was not modified.")
        _recover_diagnostics()
        return install.returncode or 1
    actual = get_installed_larch_version()
    verified = bool(latest and actual == latest)
    new_root = resolve_installed_larch_root(actual) if verified else None
    if (
        not verified
        or new_root is None
        or not _bootstrap_installed_root(root=new_root, version=actual)
    ):
        err(
            f"Upgrade incomplete: expected plugin and binary version {latest} in the newly installed cache root."
        )
        _recover_diagnostics()
        return 1
    if marketplace_will_reconcile:
        err(
            f"LARCH_MARKETPLACE_RECONCILED={'true' if _marketplace_source_matches() else 'false'}"
        )
    err("LARCH_RESTART_REQUIRED=true")
    if actual != current:
        err("LARCH_NEW_VERSION_INSTALLED=true")
    err("")
    err("Installed larch plugin version:")
    listed = proc.run(["claude", "plugin", "list"])
    if listed.stdout:
        print(listed.stdout, end="")
    err("")
    err("Upgrade complete. Restart Claude Code to apply the new version.")
    return 0
