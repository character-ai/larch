"""Age-based retention for committed larch run-log directories."""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import logging_util

SKILLS = ("design", "implement", "review")
COMMON_KEEP = {"manifest.json", "final-summary.md", "gc-slimmed"}
SKILL_KEEP = {
    "implement": {"token-report.json", "timing-report.json", "review-findings-full.jsonl", "execution-issues.ndjson", "run-statistics.md"},
    # session-id disambiguates multiple larch-tokens-*.jsonl ledgers for report_tokens_scan.
    "design": {"token-report-final.json", "timing-report-final.json", "run-params.json", "plan.txt", "session-id"},
    "review": set(),
}


@dataclass(frozen=True)
class PlannedDir:
    skill: str
    path: Path
    run_date: str


# Mutable accumulator: counters are incremented in place during the scan.
@dataclass
class Counters:
    scanned: int = 0
    qualifying: int = 0
    slimmed: int = 0
    deleted: int = 0
    skipped: int = 0
    bytes_freed: int = 0


def _emit_kv(*, key: str, value: str | int) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _run(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def _git(repo: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    argv = ["git"]
    if repo is not None:
        argv.extend(["-C", str(repo)])
    argv.extend(args)
    return _run(argv)


def _repo_root() -> Path | None:
    result = _git(None, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _parse_started_at(manifest: Path) -> str:
    try:
        parsed: object = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(parsed, dict) and isinstance(parsed.get("started_at"), str):
        return str(parsed["started_at"])
    return ""


def _resolve_run_date(*, repo_root: Path, run_dir: Path) -> str:
    started_at = _parse_started_at(run_dir / "manifest.json")
    if started_at:
        return started_at
    result = _git(repo_root, "log", "--diff-filter=A", "--format=%aI", "--", f"{run_dir}/")
    if result.returncode == 0:
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if lines:
            return lines[-1]
    return ""


def _iter_run_dirs(*, logs_root: Path, skill: str) -> list[Path]:
    skill_dir = logs_root / skill
    if not skill_dir.is_dir():
        return []
    dirs: list[Path] = []
    try:
        with os.scandir(skill_dir) as entries:
            dirs.extend(Path(entry.path) for entry in entries if entry.is_dir(follow_symlinks=False))
    except OSError:
        return []
    return sorted(dirs)


def _is_under(*, path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def _has_escape_symlink(*, path: Path, logs_root: Path) -> bool:
    if not _is_under(path=path, root=logs_root):
        return True
    try:
        for root, dirs, files in os.walk(path, followlinks=False):
            root_path = Path(root)
            for name in list(dirs) + files:
                child = root_path / name
                if child.is_symlink() and not _is_under(path=child, root=logs_root):
                    return True
    except OSError:
        return True
    return False


def _keep_file(*, filename: str, skill: str) -> bool:
    if filename in COMMON_KEEP or filename in SKILL_KEEP.get(skill, set()):
        return True
    # Design runs that never reached finalization lack token-report-final.json;
    # their committed token ledger is the only priceable source (issue #5133), so
    # retain it through slimming to keep cost recovery durable.
    return skill == "design" and filename.startswith("larch-tokens-") and filename.endswith(".jsonl")


def _dir_bytes(path: Path) -> int:
    total = 0
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
        for name in files:
            child = Path(root) / name
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _plan(*, repo_root: Path, logs_root: Path, older_than: int, delete: bool = False) -> tuple[Counters, list[PlannedDir], str]:
    counters = Counters()
    cutoff = datetime.now(UTC) - timedelta(days=older_than)
    cutoff_dt = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    plan: list[PlannedDir] = []
    _err(f"Cutoff date: {cutoff_dt} (runs started before this are qualifying)")
    for skill in SKILLS:
        for run_dir in _iter_run_dirs(logs_root=logs_root, skill=skill):
            counters.scanned += 1
            run_name = run_dir.name
            if (run_dir / "pause-state.txt").is_file():
                counters.skipped += 1
                _err(f"  skip (paused): {skill}/{run_name}")
                continue
            if (run_dir / "gc-slimmed").is_file():
                counters.skipped += 1
                _err(f"  skip (already-slimmed): {skill}/{run_name}")
                continue
            run_date = _resolve_run_date(repo_root=repo_root, run_dir=run_dir)
            if not run_date:
                counters.skipped += 1
                _err(f"  skip (no-date): {skill}/{run_name}")
                continue
            try:
                parsed_date = datetime.fromisoformat(run_date)
            except ValueError:
                parsed_date = None
            is_recent = False
            if parsed_date is not None:
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=UTC)
                try:
                    is_recent = parsed_date >= cutoff
                except TypeError:
                    is_recent = run_date >= cutoff_dt
            else:
                is_recent = run_date >= cutoff_dt
            if is_recent:
                continue
            if _has_escape_symlink(path=run_dir, logs_root=logs_root):
                counters.skipped += 1
                _err(f"  skip (escape-symlink): {skill}/{run_name}")
                continue
            counters.qualifying += 1
            plan.append(PlannedDir(skill, run_dir, run_date))
            action = "delete" if delete else "slim"
            _err(f"  plan {action}:   {skill}/{run_name} (date: {run_date})")
    _err("")
    _err(f"Scan complete: {counters.scanned} scanned, {counters.qualifying} qualifying, {counters.skipped} skipped")
    return counters, plan, cutoff_dt


def _remove_tree(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _slim_dir(*, logs_root: Path, item: PlannedDir) -> int:
    if not _is_under(path=item.path, root=logs_root):
        raise RuntimeError(f"target escapes larch-logs: {item.path}")
    before = _dir_bytes(item.path)
    try:
        entries: list[os.DirEntry[str]] = list(os.scandir(item.path))
    except OSError:
        return 0
    for entry in entries:
        path = Path(entry.path)
        if not _is_under(path=path, root=logs_root):
            continue
        if entry.is_dir(follow_symlinks=False):
            _remove_tree(path)
        elif entry.is_file(follow_symlinks=False) and not _keep_file(filename=path.name, skill=item.skill):
            path.unlink()
    (item.path / "gc-slimmed").write_text(item.run_date + "\n", encoding="utf-8")
    after = _dir_bytes(item.path)
    return max(0, before - after)


def _apply(*, repo_root: Path, logs_root: Path, plan: list[PlannedDir], counters: Counters, older_than: int, delete: bool, cutoff_dt: str) -> str:
    branch = f"gc-run-logs/slim-{datetime.now(UTC).strftime('%Y%m%d')}"
    result = _git(repo_root, "checkout", "-b", branch)
    if result.returncode != 0:
        raise RuntimeError(f"failed to create branch {branch}")
    for item in plan:
        if not item.path.exists():
            continue
        if not _is_under(path=item.path, root=logs_root):
            raise RuntimeError(f"target escapes larch-logs: {item.path}")
        if delete:
            counters.bytes_freed += _dir_bytes(item.path)
            shutil.rmtree(item.path)
            counters.deleted += 1
        else:
            counters.bytes_freed += _slim_dir(logs_root=logs_root, item=item)
            counters.slimmed += 1
    result = _git(repo_root, "add", "-A", "--", f"{logs_root}/")
    if result.returncode != 0:
        raise RuntimeError("failed to stage larch-logs")
    if delete:
        message = f"gc-run-logs: delete run dirs older than {older_than}d ({counters.deleted} dirs)"
    else:
        message = f"gc-run-logs: slim run dirs older than {older_than}d to consumer core ({counters.slimmed} dirs)"
    if _git(repo_root, "commit", "-m", message).returncode != 0:
        raise RuntimeError("failed to commit GC changes")
    if _git(repo_root, "push", "-u", "origin", branch).returncode != 0:
        raise RuntimeError("failed to push GC branch")
    if delete:
        title = f"gc-run-logs: delete run dirs older than {older_than}d"
        body = (
            f"Log-only maintenance PR created by `/gc-run-logs --delete --older-than {older_than}`.\n\n"
            f"**Dirs deleted**: {counters.deleted} (fully removed from working tree; content recoverable via git history)\n"
            f"**Threshold**: {older_than} days (cutoff: {cutoff_dt})\n\n"
            "Operator must review and merge. See `docs/run-logs.md` Retention section for policy."
        )
    else:
        title = f"gc-run-logs: slim run dirs older than {older_than}d to consumer core"
        body = (
            f"Log-only maintenance PR created by `/gc-run-logs --older-than {older_than}`.\n\n"
            f"**Dirs slimmed**: {counters.slimmed} (consumer-core files preserved; round-level forensic detail removed)\n"
            f"**Threshold**: {older_than} days (cutoff: {cutoff_dt})\n"
            f"**Bytes freed (approx)**: {counters.bytes_freed}\n\n"
            "Consumer-core keep set preserved per `docs/run-logs.md` Retention section. Slimmed dirs carry a `gc-slimmed` marker. Operator must review and merge."
        )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="gc-run-logs-body-", dir="/tmp", delete=False) as body_file:
        body_file.write(body)
        body_path = body_file.name
    try:
        gh = _run(["gh", "pr", "create", "--title", title, "--body-file", body_path, "--base", "main", "--head", branch], cwd=repo_root)
    finally:
        Path(body_path).unlink()
    if gh.returncode != 0:
        raise RuntimeError("failed to create PR")
    return gh.stdout.strip()


def _emit_final(counters: Counters, *, dry_run: bool, pr_url: str, status: str) -> None:
    _emit_kv(key="DIRS_SCANNED", value=counters.scanned)
    _emit_kv(key="DIRS_QUALIFYING", value=counters.qualifying)
    _emit_kv(key="DIRS_SLIMMED", value=counters.slimmed)
    _emit_kv(key="DIRS_DELETED", value=counters.deleted)
    _emit_kv(key="DIRS_SKIPPED", value=counters.skipped)
    _emit_kv(key="BYTES_FREED", value=counters.bytes_freed)
    _emit_kv(key="DRY_RUN", value=str(dry_run).lower())
    _emit_kv(key="PR_URL", value=pr_url)
    _emit_kv(key="STATUS", value=status)


def run_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py gc-run-logs run")
    parser.add_argument("--older-than", type=int, default=90)
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        _emit_kv(key="STATUS", value="error")
        return int(exc.code) if isinstance(exc.code, int) else 2
    if args.older_than < 1:
        _err("gc-run-logs: --older-than must be >= 1")
        _emit_kv(key="STATUS", value="error")
        return 2
    repo_root = _repo_root()
    if repo_root is None:
        _err("gc-run-logs: not inside a git repository")
        _emit_kv(key="STATUS", value="error")
        return 2
    logs_root = repo_root / "larch-logs"
    if not logs_root.is_dir():
        _err(f"gc-run-logs: larch-logs/ not found at {repo_root}")
        _emit_kv(key="STATUS", value="error")
        return 2
    if _git(repo_root, "status", "--porcelain").stdout.strip():
        _err("gc-run-logs: working tree is dirty — ensure no /implement or /design session is active before running GC")
        _emit_kv(key="STATUS", value="error")
        return 2
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != "main":
        _err(f"gc-run-logs: must be run from the main branch (currently on: {branch or 'detached'})")
        _emit_kv(key="STATUS", value="error")
        return 2
    counters, plan, cutoff_dt = _plan(repo_root=repo_root, logs_root=logs_root, older_than=args.older_than, delete=args.delete)
    if not plan or args.dry_run:
        _emit_final(counters, dry_run=args.dry_run, pr_url="", status="ok")
        return 0
    try:
        pr_url = _apply(repo_root=repo_root, logs_root=logs_root, plan=plan, counters=counters, older_than=args.older_than, delete=args.delete, cutoff_dt=cutoff_dt)
    except Exception as exc:  # pylint: disable=broad-except
        _err(f"gc-run-logs: {exc}")
        _err("gc-run-logs: recovery: run 'git checkout main' to abandon the partial GC branch")
        _emit_kv(key="STATUS", value="error")
        return 2
    _emit_final(counters, dry_run=False, pr_url=pr_url, status="ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_main(sys.argv[1:]))
