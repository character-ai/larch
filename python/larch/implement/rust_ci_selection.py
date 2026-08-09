"""Fail-closed Rust CI change selection.

The selector is the sole owner of partial-command construction and audited
supplementary-path ownership. CI runs this module from the trusted pull-request
base checkout, then passes its proposal to the workflow's effective-mode
resolver for the candidate checkout.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from larch.core import redact
from larch.core.proc import CommandResult, ProcRunner, Runner


_SCHEMA_VERSION: Final = 2
_SUPPORTED_SCHEMA_VERSIONS: Final = frozenset({1, _SCHEMA_VERSION})
_MAX_CHANGED_PATHS: Final = 200
_MAX_PATH_LENGTH: Final = 512
_GIT_TIMEOUT_SECONDS: Final = 30.0
_CARGO_METADATA_TIMEOUT_SECONDS: Final = 30.0
_SHA_RE: Final = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")
_EVENT_RE: Final = re.compile(r"^[a-z0-9_-]{1,64}$")
_PACKAGE_NAME_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_CHANGE_STATUS_RE: Final = re.compile(r"^(?:A|M|D|R[0-9]+|C[0-9]+)$")
_LIBRARY_TARGET_KINDS: Final = frozenset({"lib", "proc-macro"})
_REQUIRED_CONSUMER_PACKAGE_NAME: Final = "larch-cli"
_PUBLIC_REDACTION_FAILURE_TRIGGER: Final = "public-output-redaction-failed"
_REDACTION_TRUNCATION_MARKER: Final = "[content truncated"

# These root and prefix rules are deliberately ownership-based rather than
# extension-based. The named required jobs below still validate the changed
# content when Rust compilation is skipped.
_SKIP_EXACT_PATH_OWNERS: Final = {
    "AGENTS.md": "agent-lint plus trusted-main repository policy",
    "ARCHITECTURAL_GUIDELINES.md": "agent-lint plus trusted-main repository policy",
    "ARCHITECTURAL_INVARIANTS.md": "agent-lint plus trusted-main repository policy",
    "BASH_AUTHORING.md": "agent-lint plus trusted-main repository policy",
    "CLAUDE.md": "agent-lint plus trusted-main repository policy",
    "KARPATHY_CLAUDE.md": "agent-lint plus trusted-main repository policy",
    "README.md": "lint plus trusted-main repository policy and plugin validation",
    "SECURITY.md": "lint plus trusted-main repository policy and plugin validation",
    ".agnix.toml": "agent-lint plus trusted-main repository policy",
    ".gitleaks.toml": "lint plus trusted-main repository policy",
    ".markdownlint.json": "lint plus trusted-main repository policy",
    ".markdownlintignore": "lint plus trusted-main repository policy",
    "agent-lint.toml": "agent-lint plus trusted-main repository policy",
}
_SKIP_PREFIX_PATH_OWNERS: Final = (
    (".claude/", "agent-lint plus trusted-main repository policy"),
    ("agents/", "agent-lint plus trusted-main repository policy"),
    ("docs/", "lint plus trusted-main repository policy and plugin validation"),
    ("plugin/", "trusted-main plugin projection validation"),
    ("python/", "python-tests, python-pyright, and trusted-main repository policy"),
    ("skills/", "agent-lint, lintlang, and trusted-main repository policy"),
)


class _SelectionError(Exception):
    """A known fail-closed selection condition with an auditable token."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _PublicRedactionError(Exception):
    """The public artifact cannot safely carry the selector result."""


@dataclass(frozen=True)
class ChangedPath:
    """One normalized Git name-status record."""

    status: str
    paths: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        public = _redact_public_changed_path(self)
        return {"paths": list(public.paths), "status": public.status}


@dataclass(frozen=True)
class CommandPlan:
    """A future partial-lane command, represented without shell interpolation."""

    name: str
    argv: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        public = _redact_public_command_plan(self)
        return {"argv": list(public.argv), "name": public.name}


@dataclass(frozen=True)
class _Package:
    identifier: str
    name: str
    root_parts: tuple[str, ...]
    source_roots: tuple[tuple[str, ...], ...]
    has_library: bool
    dependencies: tuple[_Dependency, ...]


@dataclass(frozen=True)
class _Dependency:
    root_parts: tuple[str, ...]
    kind: str


@dataclass(frozen=True)
class Selection:
    """The complete deterministic selector result consumed by CI."""

    mode: str
    event_name: str
    base_sha: str | None
    head_sha: str | None
    base_source: str
    changed_paths: tuple[ChangedPath, ...]
    affected_packages: tuple[str, ...]
    reverse_dependents: tuple[str, ...]
    full_run_trigger: str | None
    skip_proof: str | None
    partial_commands: tuple[CommandPlan, ...]
    dependency_policy_required: bool
    dependency_policy_reason: str
    format_required: bool
    doctest_packages: tuple[str, ...] = ()
    validation_owners: tuple[str, ...] = ()

    def as_json(self) -> dict[str, object]:
        return _selection_as_json(_public_selection(self))

    def to_json(self) -> str:
        return json.dumps(self.as_json(), ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def select(
    *,
    event_name: object,
    base_sha: object,
    head_sha: object,
    repo_root: Path,
    runner: Runner,
) -> Selection:
    """Return one proposed mode, converting every failure into ``full``."""
    safe_event = _safe_event_name(event_name)
    display_base = _valid_sha_or_none(base_sha)
    display_head = _valid_sha_or_none(head_sha)
    if safe_event != "pull_request":
        return _public_selection(
            _full_selection(
                event_name=safe_event,
                base_sha=display_base,
                head_sha=display_head,
                base_source="not-applicable",
                reason=f"non-pull-request-event:{safe_event}",
            )
        )
    if display_base is None:
        return _public_selection(
            _full_selection(
                event_name=safe_event,
                base_sha=None,
                head_sha=display_head,
                base_source="unavailable",
                reason="missing-or-invalid-pr-base-sha",
            )
        )
    if display_head is None:
        return _public_selection(
            _full_selection(
                event_name=safe_event,
                base_sha=display_base,
                head_sha=None,
                base_source="unavailable",
                reason="missing-or-invalid-pr-head-sha",
            )
        )

    try:
        root = repo_root.resolve(strict=True)
        if not root.is_dir():
            raise _SelectionError("invalid-repository-root")
        return _public_selection(
            _select_pull_request(
                event_name=safe_event,
                base_sha=display_base,
                head_sha=display_head,
                repo_root=root,
                runner=runner,
            )
        )
    except _SelectionError as exc:
        return _public_selection(
            _full_selection(
                event_name=safe_event,
                base_sha=display_base,
                head_sha=display_head,
                base_source="unavailable",
                reason=exc.reason,
            )
        )
    except Exception:  # Defensive boundary: no implementation error may select a narrower lane.
        return _public_selection(
            _full_selection(
                event_name=safe_event,
                base_sha=display_base,
                head_sha=display_head,
                base_source="unavailable",
                reason="selector-internal-error",
            )
        )


def _select_pull_request(
    *,
    event_name: str,
    base_sha: str,
    head_sha: str,
    repo_root: Path,
    runner: Runner,
) -> Selection:
    resolved_base = _resolve_commit(runner, repo_root=repo_root, sha=base_sha, stage="base")
    resolved_head = _resolve_commit(runner, repo_root=repo_root, sha=head_sha, stage="head")
    checked_out_head = _resolve_head(runner, repo_root=repo_root)
    if checked_out_head != resolved_head:
        raise _SelectionError("checked-out-head-does-not-match-pr-head")
    _require_pr_base_ancestor(
        runner,
        repo_root=repo_root,
        base_sha=resolved_base,
        head_sha=resolved_head,
    )
    changes = _read_changes(
        runner,
        repo_root=repo_root,
        base_sha=resolved_base,
        head_sha=resolved_head,
    )
    try:
        skip_owners = _skip_validation_owners(changes)
        if skip_owners is not None:
            return Selection(
                mode="skip",
                event_name=event_name,
                base_sha=resolved_base,
                head_sha=resolved_head,
                base_source="github-pr-base",
                changed_paths=changes,
                affected_packages=(),
                reverse_dependents=(),
                full_run_trigger=None,
                skip_proof="all changed paths have audited non-Rust validation owners",
                partial_commands=(),
                dependency_policy_required=False,
                dependency_policy_reason="supplementary-only diff proves no dependency-policy input changed",
                format_required=False,
                validation_owners=skip_owners,
            )
        _require_rust_source_only(changes)
        packages = _read_workspace_packages(runner, repo_root=repo_root)
        changed_package_ids = _changed_package_ids(changes, packages=packages)
        closure_ids = _reverse_dependency_closure(changed_package_ids, packages=packages)
        packages_by_id = {package.identifier: package for package in packages}
        required_consumer = next(
            (package for package in packages if package.name == _REQUIRED_CONSUMER_PACKAGE_NAME),
            None,
        )
        if required_consumer is None or required_consumer.identifier not in closure_ids:
            raise _SelectionError("partial-does-not-build-policy-consumer")
        if len(closure_ids) == len(packages):
            raise _SelectionError("partial-closure-covers-entire-workspace")
        affected_packages = tuple(sorted(packages_by_id[identifier].name for identifier in closure_ids))
        changed_packages = {packages_by_id[identifier].name for identifier in changed_package_ids}
        reverse_dependents = tuple(name for name in affected_packages if name not in changed_packages)
        partial_commands, doctest_packages = _partial_commands(
            affected_packages=affected_packages,
            packages_by_id=packages_by_id,
            closure_ids=closure_ids,
        )
        return Selection(
            mode="partial",
            event_name=event_name,
            base_sha=resolved_base,
            head_sha=resolved_head,
            base_source="github-pr-base",
            changed_paths=changes,
            affected_packages=affected_packages,
            reverse_dependents=reverse_dependents,
            full_run_trigger=None,
            skip_proof=None,
            partial_commands=partial_commands,
            dependency_policy_required=False,
            dependency_policy_reason="rust-source-only-diff-proves-no-dependency-policy-input",
            format_required=True,
            doctest_packages=doctest_packages,
            validation_owners=(
                "rust-lint: workspace format plus selected-package Clippy",
                "rust-partial: selected tests, doctests, PR-built larch repository policy, plugin validation, and Python artifact",
            ),
        )
    except _SelectionError as exc:
        return _full_selection(
            event_name=event_name,
            base_sha=resolved_base,
            head_sha=resolved_head,
            base_source="github-pr-base",
            reason=exc.reason,
            changes=changes,
        )
    except Exception:
        return _full_selection(
            event_name=event_name,
            base_sha=resolved_base,
            head_sha=resolved_head,
            base_source="github-pr-base",
            reason="selector-internal-error",
            changes=changes,
        )


def _full_selection(  # noqa: PLR0913 - each field is a required, independently auditable decision input.
    *,
    event_name: str,
    base_sha: str | None,
    head_sha: str | None,
    base_source: str,
    reason: str,
    changes: tuple[ChangedPath, ...] = (),
) -> Selection:
    return Selection(
        mode="full",
        event_name=event_name,
        base_sha=base_sha,
        head_sha=head_sha,
        base_source=base_source,
        changed_paths=changes,
        affected_packages=(),
        reverse_dependents=(),
        full_run_trigger=reason,
        skip_proof=None,
        partial_commands=(),
        dependency_policy_required=True,
        dependency_policy_reason="full-mode-requires-the-existing-rust-deny-lane",
        format_required=True,
        validation_owners=(
            "rust-lint: workspace format and Clippy",
            "rust-deny: dependency policy",
            "rust-full: coverage, doctests, repository policy, plugin validation, and Python artifact",
        ),
    )


def _public_selection(selection: Selection) -> Selection:
    """Return the secret-scrubbed public form, or a static full fallback."""
    try:
        return _redact_public_selection(selection)
    except _PublicRedactionError:
        return _redaction_failure_selection()


def _redact_public_selection(selection: Selection) -> Selection:
    return Selection(
        mode=_redact_public_text(selection.mode),
        event_name=_redact_public_text(selection.event_name),
        base_sha=_redact_optional_public_text(selection.base_sha),
        head_sha=_redact_optional_public_text(selection.head_sha),
        base_source=_redact_public_text(selection.base_source),
        changed_paths=tuple(_redact_public_changed_path(change) for change in selection.changed_paths),
        affected_packages=tuple(_redact_public_text(package) for package in selection.affected_packages),
        reverse_dependents=tuple(_redact_public_text(package) for package in selection.reverse_dependents),
        full_run_trigger=_redact_optional_public_text(selection.full_run_trigger),
        skip_proof=_redact_optional_public_text(selection.skip_proof),
        partial_commands=tuple(_redact_public_command_plan(command) for command in selection.partial_commands),
        dependency_policy_required=selection.dependency_policy_required,
        dependency_policy_reason=_redact_public_text(selection.dependency_policy_reason),
        format_required=selection.format_required,
        doctest_packages=tuple(_redact_public_text(package) for package in selection.doctest_packages),
        validation_owners=tuple(_redact_public_text(owner) for owner in selection.validation_owners),
    )


def _redact_optional_public_text(value: str | None) -> str | None:
    return None if value is None else _redact_public_text(value)


def _redact_public_changed_path(change: ChangedPath) -> ChangedPath:
    return ChangedPath(
        status=_redact_public_text(change.status),
        paths=tuple(_redact_public_text(path) for path in change.paths),
    )


def _redact_public_command_plan(command: CommandPlan) -> CommandPlan:
    return CommandPlan(
        name=_redact_public_text(command.name),
        argv=tuple(_redact_public_text(argument) for argument in command.argv),
    )


def _redact_public_text(value: str) -> str:
    """Use the canonical redactor and prove no recognized secret survives."""
    try:
        path_scrubbed = redact.redact_tmpdir_paths(value)
        scrubbed = redact.scrub_log_secrets(path_scrubbed).scrubbed
        residual = redact.scrub_log_secrets(scrubbed).findings
        tmpdir_residual = redact.redact_tmpdir_paths(scrubbed) != scrubbed
    except _PublicRedactionError:
        raise
    except Exception as exc:  # Public egress must fail closed if the shared redactor fails.
        raise _PublicRedactionError from exc
    if (
        residual
        or tmpdir_residual
        or "\r" in scrubbed
        or "\n" in scrubbed
        or _REDACTION_TRUNCATION_MARKER in scrubbed
    ):
        raise _PublicRedactionError
    return scrubbed


def _redaction_failure_selection() -> Selection:
    return _full_selection(
        event_name="unrecognized",
        base_sha=None,
        head_sha=None,
        base_source="unavailable",
        reason=_PUBLIC_REDACTION_FAILURE_TRIGGER,
    )


def _selection_as_json(selection: Selection) -> dict[str, object]:
    """Serialize the already-redacted selection without a second egress pass."""
    return {
        "affected_packages": list(selection.affected_packages),
        "base_sha": selection.base_sha,
        "base_source": selection.base_source,
        "changed_paths": [
            {"paths": list(change.paths), "status": change.status} for change in selection.changed_paths
        ],
        "dependency_policy": {
            "reason": selection.dependency_policy_reason,
            "required": selection.dependency_policy_required,
        },
        "doctest_packages": list(selection.doctest_packages),
        "event_name": selection.event_name,
        "format_required": selection.format_required,
        "full_run_trigger": selection.full_run_trigger,
        "head_sha": selection.head_sha,
        "mode": selection.mode,
        "partial_commands": [
            {"argv": list(command.argv), "name": command.name} for command in selection.partial_commands
        ],
        "reverse_dependents": list(selection.reverse_dependents),
        "schema_version": _SCHEMA_VERSION,
        "skip_proof": selection.skip_proof,
        "validation_owners": list(selection.validation_owners),
    }


def _safe_event_name(value: object) -> str:
    return value if isinstance(value, str) and _EVENT_RE.fullmatch(value) else "unrecognized"


def _valid_sha_or_none(value: object) -> str | None:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        return None
    return value.lower()


def _resolve_commit(runner: Runner, *, repo_root: Path, sha: str, stage: str) -> str:
    output = _run_required(
        runner,
        repo_root=repo_root,
        argv=("git", "rev-parse", "--verify", f"{sha}^{{commit}}"),
        stage=f"{stage}-commit",
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    resolved = _single_sha(output, reason=f"invalid-{stage}-commit-output")
    if resolved != sha:
        raise _SelectionError(f"{stage}-commit-does-not-match-requested-sha")
    return resolved


def _resolve_head(runner: Runner, *, repo_root: Path) -> str:
    output = _run_required(
        runner,
        repo_root=repo_root,
        argv=("git", "rev-parse", "--verify", "HEAD^{commit}"),
        stage="checked-out-head",
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    return _single_sha(output, reason="invalid-checked-out-head-output")


def _require_pr_base_ancestor(
    runner: Runner,
    *,
    repo_root: Path,
    base_sha: str,
    head_sha: str,
) -> None:
    ancestor = runner.run(
        ("git", "merge-base", "--is-ancestor", base_sha, head_sha),
        cwd=str(repo_root),
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if ancestor.returncode == 0:
        return
    if ancestor.returncode == 1:
        # Cargo metadata is read from the checked-out PR head. A rewritten or
        # advanced base can contain a new dependent absent from that tree, so
        # a merge-base diff cannot safely justify a partial plan.
        raise _SelectionError("pr-base-is-not-an-ancestor-of-pr-head")
    raise _SelectionError("merge-base-ancestry-verification-failed")


def _read_changes(
    runner: Runner,
    *,
    repo_root: Path,
    base_sha: str,
    head_sha: str,
) -> tuple[ChangedPath, ...]:
    output = _run_required(
        runner,
        repo_root=repo_root,
        argv=(
            "git",
            "diff",
            "--no-ext-diff",
            "--name-status",
            "-z",
            "--find-renames=50%",
            "--find-copies=50%",
            f"{base_sha}..{head_sha}",
        ),
        stage="diff",
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    return _parse_name_status(output)


def _parse_name_status(output: str) -> tuple[ChangedPath, ...]:
    if not output or not output.endswith("\0"):
        raise _SelectionError("empty-or-malformed-diff")
    fields = output.split("\0")
    if fields.pop() != "":
        raise _SelectionError("malformed-diff-terminator")
    changes: list[ChangedPath] = []
    position = 0
    while position < len(fields):
        status = fields[position]
        position += 1
        if _CHANGE_STATUS_RE.fullmatch(status) is None:
            raise _SelectionError("unsupported-diff-status")
        path_count = 2 if status.startswith(("R", "C")) else 1
        if position + path_count > len(fields):
            raise _SelectionError("truncated-diff-record")
        paths = tuple(_normalize_repo_path(value) for value in fields[position : position + path_count])
        position += path_count
        changes.append(ChangedPath(status=status, paths=paths))
        if len(changes) > _MAX_CHANGED_PATHS:
            raise _SelectionError("diff-exceeds-auditable-path-limit")
    if not changes:
        raise _SelectionError("empty-diff")
    return tuple(sorted(changes, key=lambda change: (change.status, change.paths)))


def _normalize_repo_path(value: str) -> str:
    if not value or len(value) > _MAX_PATH_LENGTH or "\n" in value or "\r" in value or "\ufffd" in value:
        raise _SelectionError("unsafe-or-ambiguous-diff-path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise _SelectionError("unsafe-or-ambiguous-diff-path")
    return value


def _require_rust_source_only(changes: tuple[ChangedPath, ...]) -> None:
    for change in changes:
        for path in change.paths:
            trigger = _global_input_trigger(path)
            if trigger is not None:
                raise _SelectionError(trigger)
            if not path.endswith(".rs"):
                # No path family has a named replacement owner yet. The empty
                # skip allowlist therefore routes every supplementary change to
                # full rather than assuming file extensions are safe.
                raise _SelectionError("unknown-path-has-no-named-validation-owner")


def _skip_validation_owners(changes: tuple[ChangedPath, ...]) -> tuple[str, ...] | None:
    """Return named owners for a supplementary-only diff, if every path is safe."""
    owners: set[str] = set()
    for change in changes:
        for path in change.paths:
            trigger = _global_input_trigger(path)
            if trigger is not None:
                raise _SelectionError(trigger)
            if path.endswith(".rs"):
                return None
            owner = _skip_validation_owner(path)
            if owner is None:
                return None
            owners.add(owner)
    if not owners:
        raise _SelectionError("empty-supplementary-validation-owner-set")
    return tuple(sorted(owners))


def _skip_validation_owner(path: str) -> str | None:
    exact = _SKIP_EXACT_PATH_OWNERS.get(path)
    if exact is not None:
        return exact
    for prefix, owner in _SKIP_PREFIX_PATH_OWNERS:
        if path.startswith(prefix):
            return owner
    return None


_GLOBAL_PATH_TRIGGERS: Final = {
    "Cargo.lock": "global-input:cargo-lock",
    "rust-toolchain.toml": "global-input:rust-toolchain",
    "deny.toml": "global-input:dependency-policy",
    ".github/workflows/ci.yaml": "global-input:rust-ci-workflow",
    ".github/actions/rust-coverage/action.yaml": "global-input:rust-ci-workflow",
    "python/cli.py": "global-input:rust-selector",
    "python/larch/cli.py": "global-input:rust-selector",
    "python/larch/implement/rust_policy_candidate.py": "global-input:rust-ci-workflow",
    "python/larch/implement/rust_ci_selection.py": "global-input:rust-selector",
    "python/larch/core/proc.py": "global-input:rust-selector",
    "python/larch/core/redact.py": "global-input:rust-selector",
}
_GLOBAL_FILENAME_TRIGGERS: Final = {
    "Cargo.toml": "global-input:cargo-manifest",
    "Makefile": "global-input:rust-makefile",
    "build.rs": "global-input:build-script",
    "nextest.toml": "global-input:test-profile",
    "rust-ci-profile.toml": "global-input:test-profile",
}


def _global_input_trigger(path: str) -> str | None:
    exact = _GLOBAL_PATH_TRIGGERS.get(path)
    if exact is not None:
        return exact
    if path == ".cargo" or path.startswith(".cargo/"):
        return "global-input:cargo-configuration"
    return _GLOBAL_FILENAME_TRIGGERS.get(path.rsplit("/", 1)[-1])


def _read_workspace_packages(runner: Runner, *, repo_root: Path) -> tuple[_Package, ...]:
    output = _run_required(
        runner,
        repo_root=repo_root,
        argv=("cargo", "metadata", "--no-deps", "--format-version", "1", "--locked", "--offline"),
        stage="cargo-metadata",
        timeout=_CARGO_METADATA_TIMEOUT_SECONDS,
    )
    try:
        payload: object = json.loads(output)
    except json.JSONDecodeError as exc:
        raise _SelectionError("cargo-metadata-invalid-json") from exc
    metadata = _object(payload, reason="cargo-metadata-invalid-shape")
    workspace_root = _metadata_directory(
        _required_string(metadata, "workspace_root", reason="cargo-metadata-invalid-workspace-root"),
        repo_root=repo_root,
    )
    if workspace_root != repo_root:
        raise _SelectionError("cargo-metadata-workspace-root-mismatch")
    member_ids = tuple(
        _required_string(value, None, reason="cargo-metadata-invalid-workspace-members")
        for value in _list(metadata.get("workspace_members"), reason="cargo-metadata-invalid-workspace-members")
    )
    if not member_ids or len(set(member_ids)) != len(member_ids):
        raise _SelectionError("cargo-metadata-invalid-workspace-members")
    all_packages = tuple(
        _parse_package(value, repo_root=repo_root) for value in _list(metadata.get("packages"), reason="cargo-metadata-invalid-packages")
    )
    packages_by_id = {package.identifier: package for package in all_packages}
    if len(packages_by_id) != len(all_packages) or any(identifier not in packages_by_id for identifier in member_ids):
        raise _SelectionError("cargo-metadata-invalid-workspace-packages")
    packages = tuple(packages_by_id[identifier] for identifier in member_ids)
    package_names = [package.name for package in packages]
    roots = [package.root_parts for package in packages]
    if len(set(package_names)) != len(package_names) or len(set(roots)) != len(roots):
        raise _SelectionError("unsupported-workspace-package-identity")
    workspace_roots = {package.root_parts for package in packages}
    for package in packages:
        for dependency in package.dependencies:
            if dependency.root_parts not in workspace_roots:
                raise _SelectionError("unmapped-local-workspace-dependency")
    return tuple(sorted(packages, key=lambda package: package.name))


def _parse_package(value: object, *, repo_root: Path) -> _Package:
    package = _object(value, reason="cargo-metadata-invalid-package")
    identifier = _required_string(package, "id", reason="cargo-metadata-invalid-package")
    name = _required_string(package, "name", reason="cargo-metadata-invalid-package")
    if _PACKAGE_NAME_RE.fullmatch(name) is None:
        raise _SelectionError("unsupported-workspace-package-name")
    manifest_path = _required_string(package, "manifest_path", reason="cargo-metadata-invalid-manifest-path")
    root_parts = _manifest_root_parts(manifest_path, repo_root=repo_root)
    targets = _list(package.get("targets"), reason="cargo-metadata-invalid-targets")
    if not targets:
        raise _SelectionError("cargo-metadata-invalid-targets")
    has_library = False
    source_roots: list[tuple[str, ...]] = []
    for raw_target in targets:
        target = _object(raw_target, reason="cargo-metadata-invalid-targets")
        kinds = _list(target.get("kind"), reason="cargo-metadata-invalid-targets")
        if not kinds:
            raise _SelectionError("cargo-metadata-invalid-targets")
        target_kinds = {
            _required_string(item, None, reason="cargo-metadata-invalid-targets") for item in kinds
        }
        has_library = has_library or bool(_LIBRARY_TARGET_KINDS.intersection(target_kinds))
        target_source = _metadata_target_source_parts(
            _required_string(target, "src_path", reason="cargo-metadata-invalid-target-source"),
            repo_root=repo_root,
        )
        if not _parts_start_with(target_source, root_parts):
            raise _SelectionError("cargo-metadata-target-outside-package")
        source_roots.append(target_source[:-1])
    dependencies: list[_Dependency] = []
    for raw_dependency in _list(package.get("dependencies"), reason="cargo-metadata-invalid-dependencies"):
        dependency = _object(raw_dependency, reason="cargo-metadata-invalid-dependencies")
        raw_kind = dependency.get("kind")
        if raw_kind is None:
            kind = "normal"
        elif isinstance(raw_kind, str) and raw_kind in {"normal", "build", "dev"}:
            kind = raw_kind
        else:
            raise _SelectionError("unsupported-cargo-dependency-kind")
        dependency_path = dependency.get("path")
        if dependency_path is None:
            continue
        dependency_root = _metadata_directory(
            _required_string(dependency_path, None, reason="cargo-metadata-invalid-dependency-path"),
            repo_root=repo_root,
        )
        dependencies.append(
            _Dependency(root_parts=_path_parts(dependency_root.relative_to(repo_root)), kind=kind)
        )
    return _Package(
        identifier=identifier,
        name=name,
        root_parts=root_parts,
        source_roots=tuple(sorted(set(source_roots))),
        has_library=has_library,
        dependencies=tuple(
            sorted(set(dependencies), key=lambda dependency: (dependency.root_parts, dependency.kind))
        ),
    )


def _metadata_directory(value: str, *, repo_root: Path) -> Path:
    path = Path(value).resolve(strict=False)
    try:
        _ = path.relative_to(repo_root)
    except ValueError as exc:
        raise _SelectionError("cargo-metadata-path-outside-repository") from exc
    return path


def _manifest_root_parts(value: str, *, repo_root: Path) -> tuple[str, ...]:
    manifest = Path(value).resolve(strict=False)
    if manifest.name != "Cargo.toml":
        raise _SelectionError("cargo-metadata-invalid-manifest-path")
    try:
        return _path_parts(manifest.parent.relative_to(repo_root))
    except ValueError as exc:
        raise _SelectionError("cargo-metadata-path-outside-repository") from exc


def _metadata_target_source_parts(value: str, *, repo_root: Path) -> tuple[str, ...]:
    source = Path(value).resolve(strict=False)
    if source.suffix != ".rs":
        raise _SelectionError("unsupported-cargo-target-source")
    try:
        return _path_parts(source.relative_to(repo_root))
    except ValueError as exc:
        raise _SelectionError("cargo-metadata-path-outside-repository") from exc


def _path_parts(path: Path) -> tuple[str, ...]:
    return path.parts


def _parts_start_with(value: tuple[str, ...], prefix: tuple[str, ...]) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def _object(value: object, *, reason: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise _SelectionError(reason)
    raw_value = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw_value.items():
        if not isinstance(key, str):
            raise _SelectionError(reason)
        result[key] = item
    return result


def _list(value: object, *, reason: str) -> list[object]:
    if not isinstance(value, list):
        raise _SelectionError(reason)
    return cast("list[object]", value)


def _required_string(value: object, key: str | None, *, reason: str) -> str:
    candidate: object = _object(value, reason=reason).get(key) if key is not None else value
    if not isinstance(candidate, str) or not candidate:
        raise _SelectionError(reason)
    return candidate


def _changed_package_ids(changes: tuple[ChangedPath, ...], *, packages: tuple[_Package, ...]) -> frozenset[str]:
    changed: set[str] = set()
    for change in changes:
        for path in change.paths:
            changed.add(_package_for_path(path, packages=packages).identifier)
    if not changed:
        raise _SelectionError("empty-rust-package-selection")
    return frozenset(changed)


def _package_for_path(path: str, *, packages: tuple[_Package, ...]) -> _Package:
    path_parts = tuple(path.split("/"))
    package_matches = [
        package
        for package in packages
        if _parts_start_with(path_parts, package.root_parts)
    ]
    if not package_matches:
        raise _SelectionError("rust-path-not-owned-by-workspace-package")
    matches = [
        package
        for package in package_matches
        if any(_parts_start_with(path_parts, source_root) for source_root in package.source_roots)
    ]
    if not matches:
        raise _SelectionError("rust-path-not-owned-by-workspace-target")
    if len(matches) != 1:
        raise _SelectionError("ambiguous-workspace-package-ownership")
    return matches[0]


def _reverse_dependency_closure(
    changed_package_ids: frozenset[str],
    *,
    packages: tuple[_Package, ...],
) -> frozenset[str]:
    by_root = {package.root_parts: package.identifier for package in packages}
    reverse: dict[str, set[str]] = {package.identifier: set() for package in packages}
    for package in packages:
        for dependency in package.dependencies:
            dependency_id = by_root.get(dependency.root_parts)
            if dependency_id is None:
                raise _SelectionError("unmapped-local-workspace-dependency")
            reverse[dependency_id].add(package.identifier)
    closure = set(changed_package_ids)
    pending = sorted(changed_package_ids)
    while pending:
        current = pending.pop(0)
        for dependent in sorted(reverse[current]):
            if dependent not in closure:
                closure.add(dependent)
                pending.append(dependent)
    return frozenset(closure)


def _partial_commands(
    *,
    affected_packages: tuple[str, ...],
    packages_by_id: dict[str, _Package],
    closure_ids: frozenset[str],
) -> tuple[tuple[CommandPlan, ...], tuple[str, ...]]:
    if not affected_packages:
        raise _SelectionError("empty-rust-package-selection")
    package_args = tuple(argument for package in affected_packages for argument in ("--package", package))
    library_packages = tuple(
        sorted(packages_by_id[identifier].name for identifier in closure_ids if packages_by_id[identifier].has_library)
    )
    commands = [
        CommandPlan(name="format", argv=("cargo", "fmt", "--all", "--check")),
        CommandPlan(
            name="clippy",
            argv=(
                "cargo",
                "clippy",
                *package_args,
                "--all-targets",
                "--all-features",
                "--locked",
                "--",
                "-D",
                "warnings",
            ),
        ),
        CommandPlan(
            name="test",
            argv=("cargo", "test", *package_args, "--all-targets", "--all-features", "--locked"),
        ),
    ]
    if library_packages:
        doctest_args = tuple(argument for package in library_packages for argument in ("--package", package))
        commands.append(
            CommandPlan(
                name="doctests",
                argv=("cargo", "test", "--doc", *doctest_args, "--all-features", "--locked"),
            )
        )
    return tuple(commands), library_packages


def _run_required(
    runner: Runner,
    *,
    repo_root: Path,
    argv: Sequence[str],
    stage: str,
    timeout: float,
) -> str:
    result: CommandResult = runner.run(argv, cwd=str(repo_root), timeout=timeout)
    if result.returncode != 0:
        raise _SelectionError(f"{stage}-failed")
    return result.stdout


def _single_sha(output: str, *, reason: str) -> str:
    lines = output.splitlines()
    if len(lines) != 1:
        raise _SelectionError(reason)
    sha = _valid_sha_or_none(lines[0])
    if sha is None:
        raise _SelectionError(reason)
    return sha


def render_summary(selection: Selection) -> str:
    """Render a bounded, redacted, HTML-escaped GitHub step summary."""
    selection = _public_selection(selection)
    mode = _html_code(selection.mode)
    base = _html_code(selection.base_sha or "unavailable")
    head = _html_code(selection.head_sha or "unavailable")
    lines = [
        "## Rust CI selection",
        "",
        f"Proposed mode: {mode}. Non-full modes retain their named validation owners; main remains a full-run backstop.",
        "",
        f"- Base: {base} ({_html_code(selection.base_source)})",
        f"- Head: {head}",
        f"- Dependency policy: {_html_code(selection.dependency_policy_reason)}",
    ]
    if selection.full_run_trigger is not None:
        lines.append(f"- Full-run trigger: {_html_code(selection.full_run_trigger)}")
    if selection.skip_proof is not None:
        lines.append(f"- Skip proof: {_html_code(selection.skip_proof)}")
    if selection.affected_packages:
        lines.append(f"- Affected packages: {_html_code(', '.join(selection.affected_packages))}")
    if selection.reverse_dependents:
        lines.append(f"- Reverse dependents: {_html_code(', '.join(selection.reverse_dependents))}")
    if selection.doctest_packages:
        lines.append(f"- Doctest packages: {_html_code(', '.join(selection.doctest_packages))}")
    if selection.validation_owners:
        lines.extend(
            ["", "<details><summary>Validation owners</summary>", ""]
        )
        lines.extend(f"- {_html_code(owner)}" for owner in selection.validation_owners)
        lines.extend(["", "</details>"])
    lines.extend(_changed_paths_summary(selection.changed_paths))
    if selection.partial_commands:
        lines.extend(["", "<details><summary>Proposed partial commands</summary>", ""])
        lines.extend(
            f"- {_html_code(command.name)}: {_html_code(' '.join(command.argv))}"
            for command in selection.partial_commands
        )
        lines.extend(["", "</details>"])
    return "\n".join(lines) + "\n"


def _changed_paths_summary(changes: tuple[ChangedPath, ...]) -> list[str]:
    if not changes:
        return ["- Changed paths: unavailable because the selector chose full before a complete diff was proven."]
    lines = ["", f"<details><summary>Changed paths ({len(changes)})</summary>", ""]
    for change in changes:
        paths = " → ".join(_html_code(path) for path in change.paths)
        lines.append(f"- {_html_code(change.status)}: {paths}")
    lines.extend(["", "</details>"])
    return lines


def _html_code(value: str) -> str:
    return f"<code>{html.escape(value, quote=True)}</code>"


def rust_select_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Propose a fail-closed Rust CI selection.")
    _ = parser.add_argument("--event-name", default="unrecognized")
    _ = parser.add_argument("--base-sha", default="")
    _ = parser.add_argument("--head-sha", default="")
    _ = parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    selection = select(
        event_name=str(args.event_name),
        base_sha=str(args.base_sha),
        head_sha=str(args.head_sha),
        repo_root=Path(str(args.repo_root)),
        runner=ProcRunner(),
    )
    print(selection.to_json())
    return 0


def rust_select_summary_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a Rust CI selector observation summary.")
    _ = parser.add_argument("--result-file", required=True)
    args = parser.parse_args(argv)
    try:
        payload: object = json.loads(Path(str(args.result_file)).read_text(encoding="utf-8"))
        selection = _selection_from_json(payload)
    except (OSError, ValueError, _SelectionError):
        selection = _full_selection(
            event_name="unrecognized",
            base_sha=None,
            head_sha=None,
            base_source="unavailable",
            reason="selector-result-unavailable-or-invalid",
        )
    print(render_summary(selection), end="")
    return 0


def _selection_from_json(payload: object) -> Selection:
    source = _object(payload, reason="selector-result-invalid")
    schema_version = source.get("schema_version")
    if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise _SelectionError("selector-result-invalid")
    mode = _required_string(source, "mode", reason="selector-result-invalid")
    if mode not in {"full", "partial", "skip"}:
        raise _SelectionError("selector-result-invalid")
    event_name = _required_string(source, "event_name", reason="selector-result-invalid")
    base_sha = _optional_sha(source.get("base_sha"))
    head_sha = _optional_sha(source.get("head_sha"))
    base_source = _required_string(source, "base_source", reason="selector-result-invalid")
    changes = tuple(_changed_path_from_json(value) for value in _list(source.get("changed_paths"), reason="selector-result-invalid"))
    affected_packages = _string_tuple(source.get("affected_packages"), reason="selector-result-invalid")
    reverse_dependents = _string_tuple(source.get("reverse_dependents"), reason="selector-result-invalid")
    full_run_trigger = _optional_string(source.get("full_run_trigger"), reason="selector-result-invalid")
    skip_proof = _optional_string(source.get("skip_proof"), reason="selector-result-invalid")
    partial_commands = tuple(
        _command_from_json(value) for value in _list(source.get("partial_commands"), reason="selector-result-invalid")
    )
    policy = _object(source.get("dependency_policy"), reason="selector-result-invalid")
    required = policy.get("required")
    if not isinstance(required, bool):
        raise _SelectionError("selector-result-invalid")
    policy_reason = _required_string(policy, "reason", reason="selector-result-invalid")
    format_required = source.get("format_required")
    if not isinstance(format_required, bool):
        raise _SelectionError("selector-result-invalid")
    if schema_version == _SCHEMA_VERSION:
        doctest_packages = _string_tuple(source.get("doctest_packages"), reason="selector-result-invalid")
        validation_owners = _string_tuple(source.get("validation_owners"), reason="selector-result-invalid")
    else:
        doctest_packages = ()
        validation_owners = ()
    return Selection(
        mode=mode,
        event_name=event_name,
        base_sha=base_sha,
        head_sha=head_sha,
        base_source=base_source,
        changed_paths=changes,
        affected_packages=affected_packages,
        reverse_dependents=reverse_dependents,
        full_run_trigger=full_run_trigger,
        skip_proof=skip_proof,
        partial_commands=partial_commands,
        dependency_policy_required=required,
        dependency_policy_reason=policy_reason,
        format_required=format_required,
        doctest_packages=doctest_packages,
        validation_owners=validation_owners,
    )


def _optional_sha(value: object) -> str | None:
    if value is None:
        return None
    sha = _valid_sha_or_none(_required_string(value, None, reason="selector-result-invalid"))
    if sha is None:
        raise _SelectionError("selector-result-invalid")
    return sha


def _optional_string(value: object, *, reason: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, None, reason=reason)


def _string_tuple(value: object, *, reason: str) -> tuple[str, ...]:
    return tuple(_required_string(item, None, reason=reason) for item in _list(value, reason=reason))


def _changed_path_from_json(value: object) -> ChangedPath:
    source = _object(value, reason="selector-result-invalid")
    status = _required_string(source, "status", reason="selector-result-invalid")
    if _CHANGE_STATUS_RE.fullmatch(status) is None:
        raise _SelectionError("selector-result-invalid")
    paths = tuple(_normalize_repo_path(item) for item in _string_tuple(source.get("paths"), reason="selector-result-invalid"))
    if len(paths) != (2 if status.startswith(("R", "C")) else 1):
        raise _SelectionError("selector-result-invalid")
    return ChangedPath(status=status, paths=paths)


def _command_from_json(value: object) -> CommandPlan:
    source = _object(value, reason="selector-result-invalid")
    name = _required_string(source, "name", reason="selector-result-invalid")
    argv = _string_tuple(source.get("argv"), reason="selector-result-invalid")
    if not argv:
        raise _SelectionError("selector-result-invalid")
    return CommandPlan(name=name, argv=argv)
