"""Checks bgjob result-input identity: HEAD + worktree fingerprint (I-Stale-1)."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from larch import io as larch_io
from larch.core import config
from larch.core.proc import Runner, run as proc_run

_HEX_SHA_RE: Final = re.compile(r"^[0-9a-f]{7,64}$")
_HEX_FP_RE: Final = re.compile(r"^[0-9a-f]{64}$")
ResultState = Literal["matching", "stale", "incomplete", "unsafe", "absent"]


class ChecksIdentityError(RuntimeError):
    """Fail-closed identity computation or root validation failure."""


@dataclass(frozen=True)
class ChecksInputIdentity:
    head_sha: str
    tree_fingerprint: str
    fingerprint_schema: str
    repo_root: Path

    def as_rows(self) -> list[tuple[str, str]]:
        return [
            (config.CHECKS_INPUT_HEAD_SHA_KEY, self.head_sha),
            (config.CHECKS_INPUT_TREE_FP_KEY, self.tree_fingerprint),
            (config.CHECKS_INPUT_FP_SCHEMA_KEY, self.fingerprint_schema),
        ]


@dataclass(frozen=True)
class Classification:
    state: ResultState
    reason: str = ""


def validate_repo_root(repo_root: str | Path, *, runner: Runner | None = None) -> Path:
    """Resolve and validate a persisted repository root for checks identity."""
    raw = Path(repo_root)
    if not raw.is_absolute():
        raise ChecksIdentityError("repo root must be an absolute path")
    if raw.is_symlink() or not raw.is_dir():
        raise ChecksIdentityError("repo root must be a non-symlink directory")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise ChecksIdentityError(f"repo root could not be resolved: {exc}") from exc
    if resolved.is_symlink() or not resolved.is_dir():
        raise ChecksIdentityError("resolved repo root must be a non-symlink directory")
    if runner is None:
        result = proc_run(["git", "-C", str(resolved), "rev-parse", "--show-toplevel"], cwd=str(resolved))
    else:
        result = runner.run(["git", "-C", str(resolved), "rev-parse", "--show-toplevel"], cwd=str(resolved))
    if result.returncode != 0 or not result.stdout.strip():
        raise ChecksIdentityError("repo root is not a git repository")
    toplevel = Path(result.stdout.strip()).resolve()
    if toplevel != resolved:
        raise ChecksIdentityError("repo root is not the git toplevel")
    return resolved


def compute_identity(*, repo_root: Path, runner: Runner | None = None) -> ChecksInputIdentity:
    """Compute HEAD + worktree fingerprint for the validated repository."""
    root = validate_repo_root(repo_root, runner=runner)
    if runner is None:
        head_result = proc_run(["git", "-C", str(root), "rev-parse", "HEAD"], cwd=str(root))
    else:
        head_result = runner.run(["git", "-C", str(root), "rev-parse", "HEAD"], cwd=str(root))
    if head_result.returncode != 0:
        raise ChecksIdentityError("git rev-parse HEAD failed")
    head = head_result.stdout.strip()
    if not _HEX_SHA_RE.fullmatch(head):
        raise ChecksIdentityError("HEAD SHA is malformed")
    # Binary diffs must not go through text decode.
    staged = _git_bytes_binary(root, ["diff", "--cached", "--binary", "--no-ext-diff"])
    unstaged = _git_bytes_binary(root, ["diff", "--binary", "--no-ext-diff"])
    porcelain = _git_bytes_binary(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    untracked_blob = _untracked_content_blob(root=root, porcelain=porcelain)
    hasher = hashlib.sha256()
    hasher.update(config.CHECKS_INPUT_FP_SCHEMA_V1.encode("ascii"))
    hasher.update(b"\0head\0")
    hasher.update(head.encode("ascii"))
    hasher.update(b"\0staged\0")
    hasher.update(staged)
    hasher.update(b"\0unstaged\0")
    hasher.update(unstaged)
    hasher.update(b"\0untracked\0")
    hasher.update(untracked_blob)
    return ChecksInputIdentity(
        head_sha=head,
        tree_fingerprint=hasher.hexdigest(),
        fingerprint_schema=config.CHECKS_INPUT_FP_SCHEMA_V1,
        repo_root=root,
    )


def identities_match(left: ChecksInputIdentity, right: ChecksInputIdentity) -> bool:
    return (
        left.head_sha == right.head_sha
        and left.tree_fingerprint == right.tree_fingerprint
        and left.fingerprint_schema == right.fingerprint_schema
        and left.repo_root == right.repo_root
    )


def identity_from_rows(
    rows: dict[str, str],
    *,
    repo_root: Path,
) -> ChecksInputIdentity | None:
    head = rows.get(config.CHECKS_INPUT_HEAD_SHA_KEY, "")
    tree_fp = rows.get(config.CHECKS_INPUT_TREE_FP_KEY, "")
    schema = rows.get(config.CHECKS_INPUT_FP_SCHEMA_KEY, "")
    if not head or not tree_fp or not schema:
        return None
    if not _HEX_SHA_RE.fullmatch(head):
        return None
    if not _HEX_FP_RE.fullmatch(tree_fp):
        return None
    if schema != config.CHECKS_INPUT_FP_SCHEMA_V1:
        return None
    return ChecksInputIdentity(
        head_sha=head,
        tree_fingerprint=tree_fp,
        fingerprint_schema=schema,
        repo_root=repo_root,
    )


def result_identity_matches(rows: dict[str, str], *, live: ChecksInputIdentity) -> bool:
    """True when a result env's identity rows match the live repository identity.

    For result grammars without a terminal ``NEXT_ACTION`` row (e.g. Step 5), where
    ``classify_completed_result`` does not apply.
    """
    persisted = identity_from_rows(rows, repo_root=live.repo_root)
    return persisted is not None and identities_match(persisted, live)


def read_env_rows(path: Path) -> dict[str, str]:
    """Parse a checks result/merge env through larch.io; raise on unsafe files."""
    if path.is_symlink():
        raise ChecksIdentityError("env path must not be a symlink")
    if path.exists() and not path.is_file():
        raise ChecksIdentityError("env path must be a regular file")
    if not path.exists():
        return {}
    try:
        return larch_io.read_kvs(
            path,
            first_wins=False,
            reject_symlink=True,
            reject_cr=True,
            key_pattern=r"^[A-Z0-9_]+$",
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise ChecksIdentityError(f"env parse failed: {exc}") from exc


def classify_completed_result(
    *,
    result_env: Path,
    step: str,
    live: ChecksInputIdentity,
    terminal_actions: frozenset[str] | None = None,
) -> Classification:
    """Classify a completed checks result env for rejoin."""
    actions = terminal_actions if terminal_actions is not None else config.CHECKS_TERMINAL_ACTIONS
    if result_env.is_symlink() or (result_env.exists() and not result_env.is_file()):
        return Classification(state=config.CHECKS_RESULT_STATE_UNSAFE, reason="non-regular-result-env")
    if not result_env.exists():
        return Classification(state=config.CHECKS_RESULT_STATE_ABSENT, reason="missing")
    try:
        rows = read_env_rows(result_env)
    except ChecksIdentityError as exc:
        return Classification(state=config.CHECKS_RESULT_STATE_UNSAFE, reason=str(exc))
    return _classify_completed_rows(rows=rows, step=step, live=live, actions=actions)


def _classify_completed_rows(
    *,
    rows: dict[str, str],
    step: str,
    live: ChecksInputIdentity,
    actions: frozenset[str],
) -> Classification:
    if not rows:
        return Classification(state=config.CHECKS_RESULT_STATE_INCOMPLETE, reason="empty")
    next_action = rows.get("NEXT_ACTION", "")
    incomplete_reason = ""
    if rows.get(config.BGJOB_RC_KEY) != "0":
        incomplete_reason = "bgjob-rc"
    elif not next_action:
        incomplete_reason = "missing-next-action"
    elif next_action not in actions:
        incomplete_reason = "unsupported-next-action"
    if incomplete_reason:
        return Classification(state=config.CHECKS_RESULT_STATE_INCOMPLETE, reason=incomplete_reason)
    if rows.get("STEP") != step:
        return Classification(state=config.CHECKS_RESULT_STATE_STALE, reason="step-mismatch")
    persisted = identity_from_rows(rows, repo_root=live.repo_root)
    if persisted is None:
        return Classification(state=config.CHECKS_RESULT_STATE_STALE, reason="missing-identity")
    if (
        persisted.fingerprint_schema != live.fingerprint_schema
        or persisted.head_sha != live.head_sha
        or persisted.tree_fingerprint != live.tree_fingerprint
    ):
        reason = "schema-mismatch" if persisted.fingerprint_schema != live.fingerprint_schema else "identity-mismatch"
        return Classification(state=config.CHECKS_RESULT_STATE_STALE, reason=reason)
    return Classification(state=config.CHECKS_RESULT_STATE_MATCHING)


def classify_live_seed(
    *,
    merge_env: Path,
    live: ChecksInputIdentity,
) -> Classification:
    """Classify a live job's seeded merge-env identity against the live repository."""
    if merge_env.is_symlink() or (merge_env.exists() and not merge_env.is_file()):
        return Classification(state=config.CHECKS_RESULT_STATE_UNSAFE, reason="non-regular-merge-env")
    if not merge_env.exists():
        return Classification(state=config.CHECKS_RESULT_STATE_INCOMPLETE, reason="missing-merge-env")
    try:
        rows = read_env_rows(merge_env)
    except ChecksIdentityError as exc:
        return Classification(state=config.CHECKS_RESULT_STATE_UNSAFE, reason=str(exc))
    persisted = identity_from_rows(rows, repo_root=live.repo_root)
    if persisted is None:
        return Classification(state=config.CHECKS_RESULT_STATE_INCOMPLETE, reason="missing-identity")
    if not identities_match(persisted, live):
        return Classification(state=config.CHECKS_RESULT_STATE_STALE, reason="identity-mismatch")
    return Classification(state=config.CHECKS_RESULT_STATE_MATCHING)


def validate_child_identity(
    *,
    repo_root: Path,
    expected: ChecksInputIdentity,
    runner: Runner | None = None,
) -> ChecksInputIdentity:
    """Recompute identity and require an exact match with the immutable launch identity."""
    current = compute_identity(repo_root=repo_root, runner=runner)
    if not identities_match(current, expected):
        raise ChecksIdentityError("checks input identity drifted from launch seed")
    return current


def integrity_failure_rows(*, step: str, reason: str) -> list[tuple[str, str]]:
    """Non-reusable terminal rows for child identity drift."""
    safe_reason = reason.replace("\n", " ").replace("\r", " ")
    return [
        ("STEP", step),
        (config.BGJOB_RC_KEY, "1"),
        ("NEXT_ACTION", config.CHECKS_IDENTITY_INTEGRITY_FAILED_ACTION),
        ("FAILURE_REASON", safe_reason or "identity-integrity-failed"),
    ]


def _git_bytes_binary(root: Path, args: list[str]) -> bytes:
    git_bin = shutil.which("git") or "git"
    # lint-subprocess-via-runner: ok binary git diff/porcelain bytes must not be text-decoded by the Runner seam
    completed = subprocess.run(
        [git_bin, "-C", str(root), *args],
        cwd=str(root),
        capture_output=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        raise ChecksIdentityError(f"git {' '.join(args)} failed")
    return completed.stdout


def _untracked_content_blob(*, root: Path, porcelain: bytes) -> bytes:
    entries = porcelain.split(b"\0")
    untracked: list[str] = []
    idx = 0
    while idx < len(entries):
        rec = entries[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2].decode("ascii", "replace")
        rel = rec[3:].decode("utf-8", "surrogateescape")
        if ("R" in status or "C" in status) and idx < len(entries):
            idx += 1
        if status == "??":
            untracked.append(rel)
    hasher = hashlib.sha256()
    for rel in sorted(untracked):
        hasher.update(rel.encode("utf-8", errors="surrogateescape"))
        hasher.update(b"\0")
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise ChecksIdentityError(f"untracked path is not a regular file: {rel}")
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ChecksIdentityError(f"untracked path unreadable: {rel}") from exc
        hasher.update(digest.encode("ascii"))
        hasher.update(b"\0")
    return hasher.digest()


def resolve_session_repo_root(implement_tmpdir: Path) -> Path:
    """Resolve and validate REPO_ROOT from the implement session env."""
    session = implement_tmpdir / "session-env.sh"
    if not session.is_file() or session.is_symlink():
        raise ChecksIdentityError("session-env.sh is missing or unsafe")
    raw = larch_io.read_kv(
        path=session,
        key="REPO_ROOT",
        default="",
        first_match=True,
        reject_symlink=True,
    ).strip().strip("'\"")
    if not raw:
        raise ChecksIdentityError("REPO_ROOT missing from session-env.sh")
    return validate_repo_root(raw)


def _emit_rows(rows: list[tuple[str, str]]) -> None:
    print(larch_io.format_kvs(rows), end="")


def _parse_terminal_actions(raw: str) -> frozenset[str]:
    if not raw.strip():
        return config.CHECKS_TERMINAL_ACTIONS
    return frozenset(part for part in raw.split(",") if part)


def checks_result_identity_main(argv: list[str] | None = None) -> int:
    """CLI: compute / classify / validate-child for checks result identity."""
    parser = argparse.ArgumentParser(prog="cli.py implement checks-result-identity")
    sub = parser.add_subparsers(dest="verb", required=True)

    compute_p = sub.add_parser("compute")
    _ = compute_p.add_argument("--repo-root", required=True)

    classify_p = sub.add_parser("classify")
    _ = classify_p.add_argument("--result-env", required=True)
    _ = classify_p.add_argument("--step", required=True)
    _ = classify_p.add_argument("--repo-root", required=True)
    _ = classify_p.add_argument("--terminal-actions", default="")
    _ = classify_p.add_argument("--mode", choices=("completed", "live-seed"), default="completed")
    _ = classify_p.add_argument("--merge-env", default="")

    validate_p = sub.add_parser("validate-child")
    _ = validate_p.add_argument("--repo-root", required=True)
    _ = validate_p.add_argument("--expected-head", required=True)
    _ = validate_p.add_argument("--expected-fp", required=True)
    _ = validate_p.add_argument("--expected-schema", default=config.CHECKS_INPUT_FP_SCHEMA_V1)

    resolve_p = sub.add_parser("resolve-repo-root")
    _ = resolve_p.add_argument("--implement-tmpdir", required=True)

    args = parser.parse_args(argv)
    try:
        return _dispatch_identity_verb(args)
    except ChecksIdentityError as exc:
        print(f"ERROR={exc}", file=sys.stderr)
        return 2


def _dispatch_identity_verb(args: argparse.Namespace) -> int:
    if args.verb == "resolve-repo-root":
        root = resolve_session_repo_root(Path(args.implement_tmpdir))
        print(f"REPO_ROOT={root}")
        return 0
    if args.verb == "compute":
        identity = compute_identity(repo_root=Path(args.repo_root))
        _emit_rows(identity.as_rows())
        return 0
    if args.verb == "validate-child":
        root = validate_repo_root(Path(args.repo_root))
        expected = ChecksInputIdentity(
            head_sha=args.expected_head,
            tree_fingerprint=args.expected_fp,
            fingerprint_schema=args.expected_schema,
            repo_root=root,
        )
        _ = validate_child_identity(repo_root=root, expected=expected)
        print("MATCH=true")
        return 0
    root = validate_repo_root(Path(args.repo_root))
    live = compute_identity(repo_root=root)
    actions = _parse_terminal_actions(args.terminal_actions)
    if args.mode == "live-seed":
        if not args.merge_env:
            raise ChecksIdentityError("--merge-env is required for live-seed mode")
        classification = classify_live_seed(merge_env=Path(args.merge_env), live=live)
    else:
        classification = classify_completed_result(
            result_env=Path(args.result_env),
            step=args.step,
            live=live,
            terminal_actions=actions,
        )
    _emit_rows(
        [
            ("STATE", classification.state),
            ("REASON", classification.reason),
            *live.as_rows(),
        ]
    )
    if classification.state == config.CHECKS_RESULT_STATE_UNSAFE:
        return 2
    if classification.state == config.CHECKS_RESULT_STATE_MATCHING:
        return 0
    return 1
