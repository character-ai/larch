# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false
"""Git commit operations for larch run-logs."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from larch.core import config
from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext
from larch.errors import ShipError
from larch.git import git

from larch.report.run_log_batch import (
    _QUIET_LOG_RE,
    _REPO_ROOT,
    _emit_larch_log_envelope,
    _larch_log_fail,
    _repo_run_dir,
    _resolve_log_root,
    _run_dir,
    _validate_slug,
    _warn_placeholder_run_id,
    is_placeholder_run_id,
    validate_run_id_slug,
)
from larch.report.run_log_manifest import (
    _manifest_cli_path,
    _resolve_consumer_repo_root,
    _update_manifest_v2,
    effective_run_id,
)

_VOLATILE_REFRESH_BASENAMES = frozenset({
    "token-report-refresh.json",
    "timing-report-refresh.json",
    "session-transcript-refresh.txt",
    "token-report-refresh.redacted.json",
    "timing-report-refresh.redacted.json",
    "session-transcript-refresh.redacted.txt",
})
_PORCELAIN_PATH_OFFSET = 3
_IMPLEMENT_RUN_REL_PARTS = 3


def _status_line_path(line: str) -> str:
    if len(line) <= _PORCELAIN_PATH_OFFSET:
        return ""
    path = line[_PORCELAIN_PATH_OFFSET:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[1]
    return path


def _volatile_file_paths(*, rel: str, cwd: str, status_stdout: str) -> tuple[str, ...] | None:
    if not rel.startswith("larch-logs/implement/") or len(rel.split("/")) != _IMPLEMENT_RUN_REL_PARTS:
        return None
    root = Path(cwd) / rel
    paths: list[str] = []
    for line in status_stdout.splitlines():
        path = _status_line_path(line)
        if not path:
            return None
        if path.rstrip("/") == rel and line.startswith("?? "):
            if not root.is_dir():
                return None
            for item in sorted(root.rglob("*")):
                if item.is_file():
                    item_rel = item.relative_to(Path(cwd)).as_posix()
                    if item.name not in _VOLATILE_REFRESH_BASENAMES:
                        return None
                    paths.append(item_rel)
            continue
        if not path.startswith(f"{rel}/"):
            return None
        if Path(path).name not in _VOLATILE_REFRESH_BASENAMES:
            return None
        paths.append(path)
    return tuple(dict.fromkeys(paths))


def _volatile_only_under_run_tree(*, rel: str, cwd: str, status_stdout: str) -> tuple[str, ...] | None:
    paths = _volatile_file_paths(rel=rel, cwd=cwd, status_stdout=status_stdout)
    if paths is None or not paths:
        return None
    return paths


def _run_git_cleanup(*, runner: Runner, argv: list[str], cwd: str | None) -> None:
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        msg = f"run-log volatile cleanup failed ({result.returncode}): {' '.join(argv)}"
        raise ShipError(msg)


def _cleanup_volatile_run_tree(
    *, runner: Runner,
    rel: str,
    paths: tuple[str, ...],
    status_stdout: str,
    cwd: str,
) -> None:
    lines = status_stdout.splitlines()
    has_staged = any(
        not line.startswith("?? ") and line[:1] != " "
        for line in lines
    )
    if has_staged:
        _run_git_cleanup(runner=runner, argv=["git", "reset", "HEAD", "--", rel], cwd=cwd)
    tracked_paths = tuple(
        path
        for line in lines
        if not line.startswith("?? ")
        for path in (_status_line_path(line),)
        if path in paths
    )
    if tracked_paths:
        _run_git_cleanup(
            runner=runner,
            argv=["git", "restore", "--worktree", "--staged", "--source=HEAD", "--", *tracked_paths],
            cwd=cwd,
        )
    clean_paths = tuple(
        clean_path
        for line in lines
        if line.startswith("?? ")
        for path in (_status_line_path(line),)
        for clean_path in (
            paths
            if path.rstrip("/") == rel
            else (path,)
        )
        if clean_path in paths
    )
    if clean_paths:
        _run_git_cleanup(runner=runner, argv=["git", "clean", "-fd", "--", *clean_paths], cwd=cwd)
    repo_status = git.status_porcelain(runner, cwd=cwd)
    if repo_status.returncode != 0:
        msg = "git status failed after volatile run-log cleanup"
        raise ShipError(msg)
    if repo_status.stdout.strip():
        snippet = "\n".join(repo_status.stdout.splitlines()[:20])
        msg = f"volatile run-log cleanup left dirty porcelain:\n{snippet}"
        raise ShipError(msg)


def _scrub_run_tree(directory: Path) -> tuple[int, int]:
    """Scrub secret-shaped values from every file under ``directory`` in place
    before commit (parity with python3 python/cli.py redact scrub-log-secrets).

    Returns ``(total_violations, files_scrubbed)``. Files with no secret are
    left byte-for-byte untouched. Fail-closed: raises :class:`ShipError` if a
    detected secret survives scrubbing, so the caller aborts rather than commits.
    """
    total = 0
    files_scrubbed = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scrubbed, findings = redact.scrub_log_secrets(original)
        if not findings:
            continue
        _, residual = redact.scrub_log_secrets(scrubbed)
        if residual:
            msg = f"secret survived scrubbing in {path}"
            raise ShipError(msg)
        _ = path.write_text(scrubbed, encoding="utf-8")
        total += sum(findings.values())
        files_scrubbed += 1
    return total, files_scrubbed


def _warn_secret_scrub(*, violations: int, files_scrubbed: int, directory: Path) -> None:
    """Emit a loud stderr warning when the pre-flush gate redacted a secret."""
    banner = (
        "\n"
        "#############################################################################\n"
        "##  !!  SECRETS DETECTED AND SCRUBBED FROM RUN LOGS BEFORE FLUSH  !!\n"
        "#############################################################################\n"
        f"## scrubbed {violations} secret-shaped value(s) across "
        f"{files_scrubbed} file(s) in:\n"
        f"##   {directory}\n"
        "## The flush proceeds with redacted content, but a credential was almost\n"
        "## certainly exposed in this run -- ROTATE it now and check chat/PRs for\n"
        "## the same value.\n"
        "#############################################################################\n"
    )
    logging_util.BreadcrumbWriter().emit(redact.redact_outbound(banner))


def _tree_backup_path(dest: Path) -> Path:
    return dest.parent / f".{dest.name}.removing"


def _remove_backup_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _validate_tree_destination(dest: Path) -> None:
    if dest.is_symlink():
        raise ValueError(f"refusing to replace symlink destination: {dest}")
    if dest.exists() and not dest.is_dir():
        raise ValueError(f"refusing to replace non-directory destination: {dest}")


def _restore_publish_backup(*, backup: Path, dest: Path) -> None:
    if not (backup.exists() or backup.is_symlink()):
        return
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError(f"refusing to restore non-directory backup: {backup}")
    backup.rename(dest)
    _validate_tree_destination(dest)


def _restore_publish_backup_after_failure(*, backup: Path, dest: Path) -> None:
    if backup.exists() and not dest.exists():
        with suppress(OSError):
            backup.rename(dest)


def _replace_tree_with_backup(*, staged: Path, dest: Path) -> None:
    _validate_tree_destination(dest)
    backup = _tree_backup_path(dest)
    backup_exists = backup.exists() or backup.is_symlink()
    if backup_exists and dest.exists():
        _remove_backup_path(backup)
    elif backup_exists:
        _restore_publish_backup(backup=backup, dest=dest)

    moved_to_backup = False
    if dest.exists():
        dest.rename(backup)
        moved_to_backup = True
    try:
        staged.rename(dest)
    except Exception:
        if moved_to_backup:
            _restore_publish_backup_after_failure(backup=backup, dest=dest)
        raise
    if backup.exists() or backup.is_symlink():
        _remove_backup_path(backup)


def _replace_staged_tree_or_error(*, staged: Path, dest: Path) -> str | None:
    backup = _tree_backup_path(dest)
    try:
        _validate_tree_destination(dest)
    except ValueError as exc:
        return str(exc)
    try:
        if dest.exists() or backup.exists() or backup.is_symlink():
            _replace_tree_with_backup(staged=staged, dest=dest)
        else:
            staged.replace(dest)
    except ValueError as exc:
        return str(exc)
    return None


def _safe_copy_run_tree(*, src: Path, dest: Path) -> None:
    """Copy run tree without preserving symlinks that escape the source root."""
    src_root = src.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        target = dest / rel
        if item.is_symlink():
            resolved = item.resolve()
            try:
                _ = resolved.relative_to(src_root)
            except ValueError as exc:
                msg = "refusing symlink escaping run log tree"
                raise ShipError(msg) from exc
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if resolved.is_file():
                    _ = shutil.copy2(resolved, target)
            continue
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.copy2(item, target)


def _publish_run_tree_to_repo(
    *, ctx: RunContext,
    log_root: Path,
    cwd: str | None,
) -> str:
    """Copy tmpdir run tree into repo larch-logs (python3 python/cli.py run-log commit parity)."""
    run_id = effective_run_id(ctx)
    if not validate_run_id_slug(run_id):
        return ""
    if is_placeholder_run_id(run_id):
        _warn_placeholder_run_id(run_id)
        return ""
    src = log_root / "implement" / run_id
    if not src.is_dir():
        return ""
    if cwd is None:
        return f"larch-logs/implement/{run_id}"
    # Always resolve destination from _REPO_ROOT (file-relative constant), never
    # from cwd — a CWD that is a repo subdirectory (e.g. python/) would otherwise
    # produce a stray tree at python/larch-logs/… instead of larch-logs/….
    dest = _REPO_ROOT / "larch-logs" / "implement" / run_id
    if src.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest.parent, prefix=f".{run_id}.") as tmp:
            tmp_dest = Path(tmp) / run_id
            _safe_copy_run_tree(src=src, dest=tmp_dest)
            backup = dest.parent / f".{run_id}.old"
            if backup.exists():
                shutil.rmtree(backup)
            if dest.exists():
                _ = dest.replace(backup)
            _ = tmp_dest.replace(dest)
            if backup.exists():
                shutil.rmtree(backup)
    return f"larch-logs/implement/{run_id}"


def _copy_tree_to_repo(
    *, log_root: Path,
    repo_root: Path,
    skill: str,
    run_id: str,
) -> tuple[list[str], Path, int, str | None]:
    src = _run_dir(log_root=log_root, skill=skill, run_id=run_id)
    dest = _repo_run_dir(repo_root=repo_root, skill=skill, run_id=run_id)
    rels: list[str] = []
    scrub_violations = 0
    if src.is_dir():
        if src.resolve() != dest.resolve():
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=dest.parent, prefix=f".{run_id}.") as tmp:
                tmp_dest = Path(tmp) / run_id
                _safe_copy_run_tree(src=src, dest=tmp_dest)
                try:
                    count, _files_scrubbed = _scrub_run_tree(tmp_dest)
                except ShipError as exc:
                    return [], dest, scrub_violations, str(exc)
                scrub_violations += count
                replace_error = _replace_staged_tree_or_error(staged=tmp_dest, dest=dest)
                if replace_error:
                    return [], dest, scrub_violations, replace_error
        rels.append(f"larch-logs/{skill}/{run_id}")
    shared_src = log_root / "shared"
    shared_dest = repo_root / "larch-logs" / "shared"
    if shared_src.is_dir():
        if shared_src.resolve() != shared_dest.resolve():
            shared_dest.mkdir(parents=True, exist_ok=True)
            for item in sorted(shared_src.iterdir()):
                if not item.exists() or item.is_symlink():
                    continue
                dest_item = shared_dest / item.name
                if item.is_dir():
                    _safe_copy_run_tree(src=item, dest=dest_item)
                elif item.is_file():
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_item)
            try:
                count, _files_scrubbed = _scrub_run_tree(shared_dest)
            except ShipError as exc:
                return [], dest, scrub_violations, str(exc)
            scrub_violations += count
        rels.append("larch-logs/shared")
    return rels, dest, scrub_violations, None


def _git_stdout(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=str(cwd), text=True, capture_output=True, check=False)


def _default_branches(repo_root: Path) -> set[str]:
    branches = {"main", "master"}
    origin_head = _git_stdout(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
    )
    if origin_head.returncode == 0 and origin_head.stdout.strip().startswith("origin/"):
        branches.add(origin_head.stdout.strip().split("/", 1)[1])
    return branches


def _update_commit_manifest_with_warning(manifest: Path) -> None:
    if not manifest.is_file():
        return
    try:
        _update_manifest_v2(path=manifest, updates={})
    except (OSError, json.JSONDecodeError, TypeError, ValueError, UnicodeError) as exc:
        print(f"WARN: larch-log commit manifest update failed: {exc}", file=sys.stderr)


def _commit_run(*, log_root: Path, skill: str, run_id: str, cwd: str | None, pre_scrub_violations: int = 0) -> CommandResult:
    sentinel = log_root.parent / "post-merge-sentinel"
    if sentinel.exists():
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            "refusing larch-log commit after post-merge sentinel\n",
            0.0,
        )
    repo_root = _resolve_consumer_repo_root(cwd)
    branch = _git_stdout(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if branch.returncode == 0 and branch.stdout.strip() in _default_branches(repo_root):
        return CommandResult(
            ("run-log", "commit"),
            1,
            "",
            f"refusing larch-log commit on default branch {branch.stdout.strip()}\n",
            0.0,
        )
    if is_placeholder_run_id(run_id):
        _warn_placeholder_run_id(run_id)
        return CommandResult(("true",), 0, "", "", 0.0)
    manifest = _manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    _update_commit_manifest_with_warning(manifest)
    rels, dest, copy_tree_violations, scrub_error = _copy_tree_to_repo(log_root=log_root, repo_root=repo_root, skill=skill, run_id=run_id)
    violations = pre_scrub_violations + copy_tree_violations
    if scrub_error:
        return CommandResult(("run-log", "commit"), 1, "", f"{scrub_error}\n", 0.0)
    if not rels:
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    _publish_breadcrumbs_with_warning(log_root=log_root, dest=dest)
    status = _git_stdout(["git", "status", "--porcelain", "--", *rels], cwd=repo_root)
    if status.returncode != 0:
        return CommandResult(tuple(status.args), status.returncode, status.stdout, status.stderr, 0.0)
    if not status.stdout.strip():
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    run_rel = f"larch-logs/{skill}/{run_id}"
    volatile_paths = _volatile_only_under_run_tree(rel=run_rel, cwd=str(repo_root), status_stdout=status.stdout)
    if volatile_paths is not None:
        _cleanup_volatile_run_tree(
            runner=proc,
            rel=run_rel,
            paths=volatile_paths,
            status_stdout=status.stdout,
            cwd=str(repo_root),
        )
        return CommandResult(("larch-log-volatile-only",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    add = _git_stdout(["git", "add", "--", *rels], cwd=repo_root)
    if add.returncode != 0:
        return CommandResult(tuple(add.args), add.returncode, add.stdout, add.stderr, 0.0)
    diff = _git_stdout(["git", "diff", "--cached", "--quiet", "--", *rels], cwd=repo_root)
    if diff.returncode == 0:
        return CommandResult(("true",), 0, f"SECRET_SCRUB_VIOLATIONS={violations}\n", "", 0.0)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{run_id}"
    commit = _git_stdout(["git", "commit", "-m", subject, "--", *rels], cwd=repo_root)
    if commit.returncode != 0:
        return CommandResult(tuple(commit.args), commit.returncode, commit.stdout, commit.stderr, 0.0)
    sha = _git_stdout(["git", "rev-parse", "HEAD"], cwd=repo_root)
    stdout = f"{sha.stdout.strip()}\nSECRET_SCRUB_VIOLATIONS={violations}\n"
    _ = dest
    return CommandResult(tuple(commit.args), 0, stdout, commit.stderr, 0.0)


def _larch_log_commit(
    *, runner: Runner,
    ctx: RunContext,
    log_root: Path,
    cwd: str | None = None,
) -> CommandResult:
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    if sentinel.exists():
        raise ShipError("refusing larch-log commit after post-merge sentinel")
    # Guard: refuse when the caller's cwd is not the repo root — staging
    # larch-logs/ from a subdirectory (e.g. python/) would create a stray tree
    # at python/larch-logs/… and silently pollute git history.
    if cwd is not None and Path(cwd).resolve() != _REPO_ROOT.resolve():
        raise ShipError(
            f"refusing larch-log commit: cwd {cwd!r} is not repo root {str(_REPO_ROOT)!r}"
        )
    git_root = str(_REPO_ROOT)
    if (_REPO_ROOT / ".git").exists():
        branch = git.try_current_branch(runner, cwd=git_root)
        default_branches = {"main", "master"}
        origin_head = runner.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=git_root,
        )
        if origin_head.returncode == 0 and origin_head.stdout.strip().startswith("origin/"):
            default_branches.add(origin_head.stdout.strip().split("/", 1)[1])
        if branch in default_branches:
            raise ShipError(f"refusing larch-log commit on default branch {branch}")
    rel = _publish_run_tree_to_repo(ctx=ctx, log_root=log_root, cwd=cwd)
    if not rel:
        return CommandResult(("true",), 0, "", "", 0.0)
    # Pre-flush secret gate: scrub Cursor keys et al. from the staged run tree
    # before commit (parity with python3 python/cli.py redact scrub-log-secrets). Fail-closed via
    # ShipError if a detected secret survives.
    violations = 0
    if cwd is not None:
        scrub_dir = _REPO_ROOT / rel
        if scrub_dir.is_dir():
            violations, files_scrubbed = _scrub_run_tree(scrub_dir)
            if violations > 0:
                _warn_secret_scrub(violations=violations, files_scrubbed=files_scrubbed, directory=scrub_dir)
    status = git.status_porcelain_paths(runner, rel, cwd=git_root)
    if status.returncode != 0:
        return status
    if not status.stdout.strip():
        return CommandResult(("true",), 0, "", "", 0.0)
    if cwd is not None:
        volatile_paths = _volatile_only_under_run_tree(rel=rel, cwd=git_root, status_stdout=status.stdout)
        if volatile_paths is not None:
            _cleanup_volatile_run_tree(
                runner=runner,
                rel=rel,
                paths=volatile_paths,
                status_stdout=status.stdout,
                cwd=git_root,
            )
            return CommandResult(("larch-log-volatile-only",), 0, "", "", 0.0)
    _ = git.add(runner, rel, cwd=git_root)
    if git.diff_quiet(runner, rel, cached=True, cwd=git_root):
        return CommandResult(("true",), 0, "", "", 0.0)
    subject = f"{config.FLUSH_COMMIT_SUBJECT_PREFIX}{effective_run_id(ctx)}"
    return git.commit(runner, subject, cwd=git_root)


def commit_larch_logs(
    *, runner: Runner,
    ctx: RunContext,
    log_root: Path,
    cwd: str | None,
) -> CommandResult:
    _ = runner
    return _commit_run(log_root=log_root, skill="implement", run_id=effective_run_id(ctx), cwd=cwd)


_BREADCRUMB_SOURCE_TMPDIR_ENV: tuple[str, ...] = (
    "IMPLEMENT_TMPDIR",
    "DESIGN_TMPDIR",
    "REVIEW_TMPDIR",
    "RESEARCH_TMPDIR",
)


def _breadcrumb_source_confined(source_root: Path) -> bool:
    """Defense-in-depth: is the breadcrumb source under a session tmpdir?

    Backs the SECURITY.md guarantee that a breadcrumbs hint outside the active
    session tmpdir is a publish-nothing no-op. The live caller always derives
    ``--source-dir`` from ``log_root.parent`` (the session tmpdir), so this
    never trips on the supported path; it guards a future caller that passes an
    operator-controlled or escaped ``--source-dir``. When no session tmpdir env
    var is set there is no reference root, so legacy behavior is preserved
    (treated as confined).
    """
    roots: list[Path] = []
    for key in _BREADCRUMB_SOURCE_TMPDIR_ENV:
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        with suppress(OSError):
            roots.append(Path(raw).resolve())
    if not roots:
        return True
    try:
        resolved = source_root.resolve()
    except OSError:
        return False
    return any(resolved == root or root in resolved.parents for root in roots)


def publish_breadcrumbs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log publish-breadcrumbs", add_help=False)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--dest-dir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    src = Path(args.source_dir)
    dest = Path(args.dest_dir)
    source_root = src.parent
    if not _breadcrumb_source_confined(source_root):
        # Per SECURITY.md: a breadcrumbs hint whose session root falls outside
        # every active session tmpdir is a publish-nothing no-op (defense-in-depth;
        # live callers always derive --source-dir from log_root.parent). This is a
        # no-op, not the removed source-directory-wide rejection — the per-file
        # symlink/hardlink/redaction guards below remain the fail-closed surface.
        return 0
    quiet_logs = sorted(
        item for item in source_root.iterdir() if _QUIET_LOG_RE.fullmatch(item.name)
    )
    if not quiet_logs:
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".breadcrumbs.") as tmp:
        staged = Path(tmp) / dest.name
        quiet_log = staged / "quiet.log"
        redacted_parts: list[str] = []
        for item in quiet_logs:
            if item.is_symlink():
                print(f"publish-breadcrumbs: refusing symlink quiet log: {item}", file=sys.stderr)
                return 1
            try:
                stat_result = item.stat()
            except OSError as exc:
                print(f"publish-breadcrumbs: cannot stat quiet log {item}: {exc}", file=sys.stderr)
                return 1
            if not item.is_file():
                continue
            if stat_result.st_nlink > 1:
                print(f"publish-breadcrumbs: refusing hardlinked quiet log: {item}", file=sys.stderr)
                return 1
            out = Path(tmp) / f"{item.name}.redacted"
            state = Path(tmp) / ".redact-state"
            redact.redact_breadcrumb_file(input_path=item, output_path=out, state_file=state)
            redacted_parts.append(f"=== {item.name} ===\n")
            redacted_parts.append(out.read_text(encoding="utf-8", errors="replace"))
        if not redacted_parts:
            return 0
        quiet_log.parent.mkdir(parents=True, exist_ok=True)
        quiet_log.write_text("".join(redacted_parts), encoding="utf-8")
        replace_error = _replace_staged_tree_or_error(staged=staged, dest=dest)
        rc = 0
        if replace_error:
            print(f"publish-breadcrumbs: {replace_error}", file=sys.stderr)
            rc = 1
    return rc


def _publish_breadcrumbs_with_warning(*, log_root: Path, dest: Path) -> None:
    bread_src = log_root.parent / "breadcrumbs"
    if log_root.name != "larch-logs":
        return
    try:
        breadcrumb_rc = publish_breadcrumbs_main(
            ["--source-dir", str(bread_src), "--dest-dir", str(dest / "breadcrumbs")],
        )
    except (OSError, ValueError, ShipError, UnicodeError) as exc:
        print(f"WARN: larch-log commit breadcrumb publish failed: {exc}", file=sys.stderr)
        return
    if breadcrumb_rc != 0:
        print(f"WARN: larch-log commit breadcrumb publish failed: rc={breadcrumb_rc}", file=sys.stderr)


def larch_log_commit_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log commit", add_help=False)
    parser.add_argument("--log-root", default="")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pre-scrub-violations", default="0")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return _larch_log_fail(code=1, message="invalid commit arguments")
    try:
        _validate_slug(label="skill", value=args.skill)
        _validate_slug(label="run-id", value=args.run_id)
        args.log_root_path = _resolve_log_root(getattr(args, "log_root", ""))
    except (ValueError, AttributeError) as exc:
        print(str(exc), file=sys.stderr)
        return _larch_log_fail(code=1, message="invalid commit arguments")
    if not str(args.pre_scrub_violations).isdigit():
        return _larch_log_fail(code=1, message="invalid --pre-scrub-violations: expected non-negative integer")
    try:
        result = _commit_run(
            log_root=args.log_root_path,
            skill=args.skill,
            run_id=args.run_id,
            cwd=str(Path.cwd()),
            pre_scrub_violations=int(args.pre_scrub_violations),
        )
    except ShipError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        return result.returncode
    commit_sha = ""
    extra: dict[str, str | int] = {}
    for line in result.stdout.splitlines():
        if re.fullmatch(r"[0-9a-f]{40}", line):
            commit_sha = line
        elif line.startswith("SECRET_SCRUB_VIOLATIONS="):
            extra["SECRET_SCRUB_VIOLATIONS"] = line.split("=", 1)[1]
    unchanged = result.argv in {("true",), ("larch-log-volatile-only",)}
    path = _repo_run_dir(repo_root=_resolve_consumer_repo_root(str(Path.cwd())), skill=args.skill, run_id=args.run_id)
    _emit_larch_log_envelope(
        path=path if path.exists() else None,
        written=bool(commit_sha),
        unchanged=unchanged,
        commit_sha=commit_sha,
        extra=extra,
    )
    return 0
