"""Changed-path Cargo Clippy selection for bounded local Rust checks."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, cast

from larch.core import config, proc
from larch.core.proc import CommandResult, Runner
from larch.core.repo_roots import RepoRootProbeOptions, repo_root_probe

_WORKSPACE_INPUTS: Final[frozenset[str]] = frozenset(
    {"Cargo.lock", "Cargo.toml", "deny.toml", "rust-toolchain.toml"}
)
_TARGET_KINDS: Final[frozenset[str]] = frozenset({"bin", "test", "example", "bench"})
_TARGET_FLAG_BY_KIND: Final[dict[str, str]] = {
    "bin": "--bin",
    "test": "--test",
    "example": "--example",
    "bench": "--bench",
}
_TARGET_KIND_ORDER: Final[dict[str, int]] = {
    "bin": 0,
    "test": 1,
    "example": 2,
    "bench": 3,
}


class RustClippyError(RuntimeError):
    """Raised when changed Rust paths cannot be selected safely."""


@dataclass(frozen=True)
class CargoTarget:
    name: str
    kinds: tuple[str, ...]
    source_path: str

    @property
    def selection_kind(self) -> str | None:
        matches = tuple(kind for kind in self.kinds if kind in _TARGET_KINDS)
        if len(matches) == 1:
            return matches[0]
        return None


@dataclass(frozen=True)
class CargoPackage:
    package_id: str
    name: str
    manifest_path: str
    root_path: str
    targets: tuple[CargoTarget, ...]


@dataclass(frozen=True)
class CargoWorkspace:
    packages: tuple[CargoPackage, ...]


@dataclass(frozen=True)
class TargetSelection:
    kind: str
    name: str


@dataclass(frozen=True)
class PackageSelection:
    package: CargoPackage
    defaults: bool
    targets: tuple[TargetSelection, ...]


@dataclass(frozen=True)
class RustClippyPlan:
    changed_paths: tuple[str, ...]
    workspace: bool
    packages: tuple[PackageSelection, ...]

    def commands(self) -> tuple[tuple[str, ...], ...]:
        if self.workspace:
            return ((config.CARGO_CLI, "clippy", "--locked", "--workspace", "--", "-D", "warnings"),)
        return tuple(_package_command(selection) for selection in self.packages)

    def selected_packages(self) -> tuple[str, ...]:
        if self.workspace:
            return ("workspace",)
        return tuple(selection.package.name for selection in self.packages)

    def selected_targets(self) -> tuple[str, ...]:
        if self.workspace:
            return ("workspace:default-production",)
        labels: list[str] = []
        for selection in self.packages:
            if selection.defaults:
                labels.append(f"{selection.package.name}:default-production")
            labels.extend(
                f"{selection.package.name}:{target.kind}:{target.name}" for target in selection.targets
            )
        return tuple(labels)


def is_rust_relevant_path(path: str) -> bool:
    """Whether a repository-relative path needs the bounded Rust selector."""
    return (
        path in _WORKSPACE_INPUTS
        or path.startswith(".cargo/")
        or (path.startswith("crates/") and path.endswith((".rs", "/Cargo.toml")))
    )


def _normalize_changed_path(raw: str) -> str:
    if not raw or raw.startswith("/") or "\\" in raw:
        raise RustClippyError(f"changed path must be repository-relative: {raw!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RustClippyError(f"changed path is not normalized: {raw!r}")
    return PurePosixPath(raw).as_posix()


def _relative_metadata_path(*, raw: object, repo_root: Path, field: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise RustClippyError(f"Cargo metadata {field} is missing")
    path = Path(raw)
    if not path.is_absolute():
        raise RustClippyError(f"Cargo metadata {field} is not absolute: {raw!r}")
    try:
        resolved = path.resolve(strict=False)
        return resolved.relative_to(repo_root).as_posix()
    except (OSError, ValueError) as exc:
        raise RustClippyError(f"Cargo metadata {field} escapes the repository: {raw!r}") from exc


def _required_string(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise RustClippyError(f"Cargo metadata package {key} is missing")
    return value


def _metadata_mapping(*, raw: object, label: str) -> Mapping[str, object]:
    if not isinstance(raw, dict):
        raise RustClippyError(f"Cargo metadata {label} is malformed")
    return cast("dict[str, object]", raw)


def _metadata_string_list(*, raw: object, label: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise RustClippyError(f"Cargo metadata {label} is malformed")
    raw_list = cast("list[object]", raw)
    values: list[str] = []
    for item in raw_list:
        if not isinstance(item, str):
            raise RustClippyError(f"Cargo metadata {label} is malformed")
        values.append(item)
    return tuple(values)


def _metadata_document(*, text: str) -> tuple[frozenset[str], list[Mapping[str, object]]]:
    try:
        document: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RustClippyError("Cargo metadata is not valid JSON") from exc
    document_map = _metadata_mapping(raw=document, label="root")
    members_raw: object = document_map.get("workspace_members")
    packages_raw: object = document_map.get("packages")
    members = _metadata_string_list(raw=members_raw, label="workspace_members")
    if not isinstance(packages_raw, list):
        raise RustClippyError("Cargo metadata packages is malformed")
    package_list = cast("list[object]", packages_raw)
    packages: list[Mapping[str, object]] = [
        _metadata_mapping(raw=package_raw, label="package") for package_raw in package_list
    ]
    return frozenset(members), packages


def _cargo_target_from_metadata(*, raw: Mapping[str, object], package_id: str, repo_root: Path) -> CargoTarget:
    name = _required_string(raw, "name")
    kinds_raw: object = raw.get("kind")
    kinds = _metadata_string_list(raw=kinds_raw, label=f"target kind for {package_id}")
    source_path = _relative_metadata_path(raw=raw.get("src_path"), repo_root=repo_root, field="target src_path")
    return CargoTarget(name=name, kinds=kinds, source_path=source_path)


def _cargo_package_from_metadata(
    *,
    raw: Mapping[str, object],
    workspace_members: frozenset[str],
    repo_root: Path,
) -> CargoPackage | None:
    package_id = _required_string(raw, "id")
    if package_id not in workspace_members:
        return None
    manifest_path = _relative_metadata_path(raw=raw.get("manifest_path"), repo_root=repo_root, field="manifest_path")
    root = PurePosixPath(manifest_path).parent.as_posix()
    targets_raw: object = raw.get("targets")
    if not isinstance(targets_raw, list):
        raise RustClippyError(f"Cargo metadata targets are malformed for {package_id}")
    target_list = cast("list[object]", targets_raw)
    targets: list[CargoTarget] = []
    for target_raw in target_list:
        target = _metadata_mapping(raw=target_raw, label=f"target for {package_id}")
        targets.append(_cargo_target_from_metadata(raw=target, package_id=package_id, repo_root=repo_root))
    return CargoPackage(
        package_id=package_id,
        name=_required_string(raw, "name"),
        manifest_path=manifest_path,
        root_path="" if root == "." else root,
        targets=tuple(targets),
    )


def _workspace_from_metadata(*, text: str, repo_root: Path) -> CargoWorkspace:
    members, package_rows = _metadata_document(text=text)
    packages: list[CargoPackage] = []
    for raw in package_rows:
        package = _cargo_package_from_metadata(raw=raw, workspace_members=members, repo_root=repo_root)
        if package is not None:
            packages.append(package)
    if not packages:
        raise RustClippyError("Cargo metadata contains no workspace packages")
    names = [package.name for package in packages]
    if len(names) != len(set(names)):
        raise RustClippyError("Cargo workspace contains duplicate package names")
    return CargoWorkspace(packages=tuple(sorted(packages, key=lambda package: (package.name, package.manifest_path))))


def _path_in_package(*, path: str, package: CargoPackage) -> bool:
    return (
        path == package.manifest_path
        or not package.root_path
        or path == package.root_path
        or path.startswith(f"{package.root_path}/")
    )


def _package_for_path(*, path: str, workspace: CargoWorkspace) -> CargoPackage:
    candidates: list[CargoPackage] = [
        package for package in workspace.packages if _path_in_package(path=path, package=package)
    ]
    ordered: list[CargoPackage] = sorted(candidates, key=lambda package: (-len(package.root_path), package.manifest_path))
    if not ordered:
        raise RustClippyError(f"unmappable Rust path: {path}")
    if len(ordered) > 1 and len(ordered[0].root_path) == len(ordered[1].root_path):
        raise RustClippyError(f"ambiguous Cargo package for Rust path: {path}")
    return ordered[0]


def _nested_target_match(*, path: str, target: CargoTarget) -> bool:
    kind = target.selection_kind
    if kind is None:
        return False
    source = PurePosixPath(target.source_path)
    if source.suffix != ".rs":
        return False
    if kind == "bin" and "/src/bin/" not in f"/{target.source_path}":
        return False
    target_specific_parent = any(
        marker in f"/{source.parent.as_posix()}/"
        for marker in ("/tests/", "/examples/", "/benches/", "/src/bin/")
    )
    if target_specific_parent and source.name in {"lib.rs", "main.rs", "mod.rs"}:
        module_dir = source.parent
    else:
        module_dir = source.parent / source.stem
    return path.startswith(f"{module_dir.as_posix()}/")


def _target_for_path(*, path: str, package: CargoPackage) -> TargetSelection | None:
    exact = tuple(target for target in package.targets if target.source_path == path)
    if exact:
        target = exact[0]
        kind = target.selection_kind
        if kind is not None:
            return TargetSelection(kind=kind, name=target.name)
        return None
    nested = tuple(target for target in package.targets if _nested_target_match(path=path, target=target))
    if len(nested) > 1:
        raise RustClippyError(f"ambiguous Cargo target for Rust path: {path}")
    if nested:
        target = nested[0]
        kind = target.selection_kind
        assert kind is not None
        return TargetSelection(kind=kind, name=target.name)
    return None


def _is_default_production_source(*, path: str, package: CargoPackage) -> bool:
    prefix = f"{package.root_path}/" if package.root_path else ""
    return path == f"{prefix}build.rs" or path.startswith(f"{prefix}src/")


def _shared_target_selections(*, path: str, package: CargoPackage) -> tuple[TargetSelection, ...]:
    prefix = f"{package.root_path}/" if package.root_path else ""
    for directory, kind in (("tests", "test"), ("examples", "example"), ("benches", "bench")):
        if not path.startswith(f"{prefix}{directory}/"):
            continue
        return tuple(
            TargetSelection(kind=kind, name=target.name)
            for target in package.targets
            if target.selection_kind == kind
        )
    return ()


def _path_selection(*, path: str, package: CargoPackage) -> tuple[TargetSelection, ...] | None:
    if path == package.manifest_path:
        return None
    target = _target_for_path(path=path, package=package)
    if target is not None:
        return (target,)
    shared_targets = _shared_target_selections(path=path, package=package)
    if shared_targets:
        return shared_targets
    if _is_default_production_source(path=path, package=package):
        return None
    raise RustClippyError(f"unmappable Rust path: {path}")


def build_rust_clippy_plan(*, metadata_text: str, repo_root: Path, changed_paths: Sequence[str]) -> RustClippyPlan:
    normalized = tuple(sorted({_normalize_changed_path(path) for path in changed_paths}))
    if not normalized:
        raise RustClippyError("no changed Rust paths were supplied")
    if any(not is_rust_relevant_path(path) for path in normalized):
        invalid = next(path for path in normalized if not is_rust_relevant_path(path))
        raise RustClippyError(f"path is not Rust-relevant: {invalid}")
    if any(path in _WORKSPACE_INPUTS or path.startswith(".cargo/") for path in normalized):
        return RustClippyPlan(changed_paths=normalized, workspace=True, packages=())
    workspace = _workspace_from_metadata(text=metadata_text, repo_root=repo_root)
    defaults: set[str] = set()
    targets: dict[str, set[TargetSelection]] = {}
    package_by_id = {package.package_id: package for package in workspace.packages}
    for path in normalized:
        package = _package_for_path(path=path, workspace=workspace)
        path_targets = _path_selection(path=path, package=package)
        if path_targets is None:
            defaults.add(package.package_id)
        else:
            targets.setdefault(package.package_id, set()).update(path_targets)
    selected_ids = sorted({*defaults, *targets}, key=lambda package_id: (package_by_id[package_id].name, package_id))
    packages: list[PackageSelection] = []
    for package_id in selected_ids:
        selected_targets = tuple(
            sorted(
                targets.get(package_id, set()),
                key=lambda target: (_TARGET_KIND_ORDER[target.kind], target.name),
            )
        )
        packages.append(
            PackageSelection(
                package=package_by_id[package_id],
                defaults=package_id in defaults,
                targets=selected_targets,
            )
        )
    return RustClippyPlan(changed_paths=normalized, workspace=False, packages=tuple(packages))


def _default_target_args(package: CargoPackage) -> tuple[str, ...]:
    args: list[str] = []
    if any("lib" in target.kinds for target in package.targets):
        args.append("--lib")
    args.extend(
        argument
        for target in sorted(package.targets, key=lambda candidate: candidate.name)
        if target.selection_kind == "bin"
        for argument in ("--bin", target.name)
    )
    return tuple(args)


def _package_command(selection: PackageSelection) -> tuple[str, ...]:
    command: list[str] = [config.CARGO_CLI, "clippy", "--locked", "--package", selection.package.name]
    if selection.defaults and selection.targets:
        command.extend(_default_target_args(selection.package))
    for target in selection.targets:
        command.extend((_TARGET_FLAG_BY_KIND[target.kind], target.name))
    command.extend(("--", "-D", "warnings"))
    return tuple(command)


def bounded_cargo_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return the single non-incremental, no-debug local Cargo configuration."""
    env = dict(os.environ if base is None else base)
    env.update(
        {
            config.ENV_CARGO_INCREMENTAL: "0",
            config.ENV_CARGO_PROFILE_DEV_DEBUG: "0",
            config.ENV_CARGO_PROFILE_TEST_DEBUG: "0",
        }
    )
    return env


def _emit_command_output(result: CommandResult) -> None:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def run_changed_rust_clippy(
    runner: Runner,
    *,
    repo_root: Path,
    changed_paths: Sequence[str],
    env: Mapping[str, str] | None = None,
) -> int:
    """Run the bounded Clippy configuration for the supplied changed Rust paths."""
    child_env = bounded_cargo_env(env)
    metadata = runner.run(
        [config.CARGO_CLI, "metadata", "--locked", "--format-version", "1", "--no-deps"],
        cwd=str(repo_root),
        env=child_env,
    )
    if metadata.returncode != 0:
        _emit_command_output(metadata)
        print("RUST_CLIPPY_HOOK_RAN=false REASON=cargo-metadata-failed", file=sys.stderr)
        return metadata.returncode or 1
    try:
        plan = build_rust_clippy_plan(
            metadata_text=metadata.stdout,
            repo_root=repo_root,
            changed_paths=changed_paths,
        )
    except RustClippyError as exc:
        print(f"ERROR: bounded Rust Clippy selection failed: {exc}", file=sys.stderr)
        print("RUST_CLIPPY_HOOK_RAN=false REASON=selection-failed", file=sys.stderr)
        return config.EXIT_USAGE
    print(f"RUST_CLIPPY_CHANGED_PATHS={','.join(plan.changed_paths)}")
    print(f"RUST_CLIPPY_SELECTED_PACKAGES={','.join(plan.selected_packages())}")
    print(f"RUST_CLIPPY_SELECTED_TARGETS={','.join(plan.selected_targets())}")
    for command in plan.commands():
        print(f"RUST_CLIPPY_COMMAND={shlex.join(command)}")
        result = runner.run(command, cwd=str(repo_root), env=child_env)
        _emit_command_output(result)
        if result.returncode != 0:
            print("RUST_CLIPPY_HOOK_RAN=false REASON=clippy-failed", file=sys.stderr)
            return result.returncode
    print("RUST_CLIPPY_HOOK_RAN=true")
    return config.EXIT_OK


def _resolve_repo_root(*, runner: Runner, raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = candidate.resolve()
    if candidate.is_symlink() or not candidate.is_dir():
        raise RustClippyError("repository root must be a non-symlink directory")
    result = repo_root_probe(
        runner=runner,
        options=RepoRootProbeOptions(git_cwd=candidate, runner_cwd=candidate),
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RustClippyError("repository root is not a Git work tree")
    resolved = Path(result.stdout.strip()).resolve()
    if resolved != candidate.resolve():
        raise RustClippyError("repository root is not the Git toplevel")
    return resolved


def _git_lines(*, runner: Runner, argv: Sequence[str], cwd: str) -> tuple[str, ...]:
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def changed_paths_from_git(*, runner: Runner, cwd: str) -> tuple[str, ...]:
    """Return the common branch, index, worktree, and untracked change set."""
    branch_diff: tuple[str, ...] = ()
    if runner.run(["git", "rev-parse", "--verify", "origin/main"], cwd=cwd).returncode == 0:
        branch_diff = _git_lines(runner=runner, argv=["git", "diff", "--name-only", "origin/main...HEAD"], cwd=cwd)
    elif runner.run(["git", "rev-parse", "--verify", "main"], cwd=cwd).returncode == 0:
        branch_diff = _git_lines(runner=runner, argv=["git", "diff", "--name-only", "main...HEAD"], cwd=cwd)
    staged = _git_lines(runner=runner, argv=["git", "diff", "--cached", "--name-only"], cwd=cwd)
    unstaged = _git_lines(runner=runner, argv=["git", "diff", "--name-only"], cwd=cwd)
    untracked = _git_lines(runner=runner, argv=["git", "ls-files", "--others", "--exclude-standard"], cwd=cwd)
    return tuple(sorted({*branch_diff, *staged, *unstaged, *untracked}))


def rust_clippy_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py checks rust-clippy")
    _ = parser.add_argument("--repo-root", required=True)
    _ = parser.add_argument("--changed-from-git", action="store_true")
    _ = parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    if args.changed_from_git and args.paths:
        parser.error("--changed-from-git cannot be combined with explicit paths")
    if not args.changed_from_git and not args.paths:
        parser.error("supply changed Rust paths or --changed-from-git")
    try:
        repo_root = _resolve_repo_root(runner=proc, raw=args.repo_root)
    except RustClippyError as exc:
        print(f"ERROR: bounded Rust Clippy selection failed: {exc}", file=sys.stderr)
        return config.EXIT_USAGE
    raw_paths = changed_paths_from_git(runner=proc, cwd=str(repo_root)) if args.changed_from_git else tuple(args.paths)
    rust_paths = tuple(path for path in raw_paths if is_rust_relevant_path(path))
    if args.changed_from_git and not rust_paths:
        print("RUST_CLIPPY_HOOK_RAN=false REASON=no-rust-changes")
        return config.EXIT_OK
    return run_changed_rust_clippy(proc, repo_root=repo_root, changed_paths=rust_paths)
