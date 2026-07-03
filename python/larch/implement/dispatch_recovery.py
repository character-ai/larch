# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Recovery paths computation and implement-commit entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import logging_util
from larch.implement.dispatch_helpers import (
    RecoveryParse,
    _capture_postlaunch_porcelain,
    _current_cli_path,
    _emit_kv,
    _err,
    _invoke_cli,
    _parse_porcelain_z,
    _run,
    _session_get,
    _write_bytes_atomic,
)


@dataclass(frozen=True)
class RecoveryPorcelainInputs:
    prelaunch_porcelain: Path
    postlaunch_porcelain: Path
    prelaunch_digests: Path


def _load_digest_map(path: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    if not path.exists():
        return digests
    for line in path.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
        if "\t" in line:
            digest, rel = line.split("\t", 1)
            digests[rel] = digest
    return digests


def _tmpdir_rel_in_repo(repo_root: Path, tmpdir: Path) -> str | None:
    try:
        repo_real = repo_root.resolve()
        tmp_real = tmpdir.resolve()
        if tmp_real == repo_real:
            return "."
        tmp_real.relative_to(repo_real)
        return os.path.relpath(tmp_real, repo_real)
    except (OSError, ValueError):
        return None


def _rel_under_tmp(rel: str, tmp_rel: str | None) -> bool:
    if tmp_rel is None:
        return False
    return rel == tmp_rel or rel.startswith(tmp_rel.rstrip("/") + "/")


def _sha256_file(repo_root: Path, rel: str) -> str:
    try:
        return hashlib.sha256((repo_root / rel).read_bytes()).hexdigest()
    except OSError:
        return "missing"


def _recovery_path_included(
    *,
    status: str,
    rel: str,
    pre: RecoveryParse,
    digests: dict[str, str],
    repo_root: Path,
) -> bool:
    if (status, rel) not in pre.tuples:
        return True
    if rel in pre.paths:
        return _sha256_file(repo_root, rel) != digests.get(rel, "")
    return False


def _collect_recovery_candidates(
    *,
    repo_root: Path,
    tmp_rel: str | None,
    pre: RecoveryParse,
    post: RecoveryParse,
    digests: dict[str, str],
) -> list[str]:
    candidates: list[str] = []
    for status, rel in sorted(post.tuples, key=lambda item: item[1]):
        if _rel_under_tmp(rel, tmp_rel):
            continue
        include = _recovery_path_included(status=status, rel=rel, pre=pre, digests=digests, repo_root=repo_root)
        if include and rel not in candidates:
            candidates.append(rel)
    return candidates


def compute_recovery_paths(
    *,
    repo_root: Path,
    tmpdir: Path,
    porcelain: RecoveryPorcelainInputs,
    out_file: Path,
) -> bool:
    pre = _parse_porcelain_z(porcelain.prelaunch_porcelain)
    post = _parse_porcelain_z(porcelain.postlaunch_porcelain)
    digests = _load_digest_map(porcelain.prelaunch_digests)
    tmp_rel = _tmpdir_rel_in_repo(repo_root, tmpdir)
    candidates = _collect_recovery_candidates(repo_root=repo_root, tmp_rel=tmp_rel, pre=pre, post=post, digests=digests)
    _write_bytes_atomic(path=out_file, data=b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in candidates))
    return bool(candidates)


def recovery_paths_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement recovery-paths")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--tmpdir", default="")
    parser.add_argument("--capture-postlaunch", action="store_true")
    parser.add_argument("--prelaunch-porcelain", required=True)
    parser.add_argument("--postlaunch-porcelain", required=True)
    parser.add_argument("--prelaunch-digests", required=True)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    raw_tmpdir = args.tmpdir or os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_tmpdir:
        _err("implement recovery-paths: --tmpdir is required or IMPLEMENT_TMPDIR must be set")
        return 2
    tmpdir = Path(raw_tmpdir)
    if args.capture_postlaunch:
        rc = _capture_postlaunch_porcelain(repo_root=repo_root, implement_tmpdir=tmpdir)
        if rc != 0:
            return rc
    ok = compute_recovery_paths(
        repo_root=repo_root,
        tmpdir=tmpdir,
        porcelain=RecoveryPorcelainInputs(
            prelaunch_porcelain=Path(args.prelaunch_porcelain),
            postlaunch_porcelain=Path(args.postlaunch_porcelain),
            prelaunch_digests=Path(args.prelaunch_digests),
        ),
        out_file=Path(args.out_file),
    )
    return 0 if ok else 1


def _commit_usage_fail(error: str) -> int:
    _err("Usage: implement commit --message MSG [--pathspec-from-file PATH [--pathspec-file-nul]] [files...]")
    _err("HINT: --stage-all belongs to review-and-fix commit-fixes (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file.")
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return 2


def _scan_commit_argv(argv_list: list[str]) -> int | None:
    known_flags = {"--message", "-m", "--pathspec-from-file", "--pathspec-file-nul", "--help", "-h"}
    idx = 0
    while idx < len(argv_list):
        arg = argv_list[idx]
        if arg in ("--help", "-h"):
            argparse.ArgumentParser(prog="cli.py implement commit").print_help()
            return 0
        if arg.startswith("-") and arg not in known_flags:
            return _commit_usage_fail(f"unknown option: {arg}")
        if arg in ("--message", "-m", "--pathspec-from-file"):
            if idx + 1 >= len(argv_list) or argv_list[idx + 1].startswith("-"):
                return _commit_usage_fail(f"{arg} requires a value")
            idx += 2
            continue
        if arg == "--pathspec-file-nul":
            idx += 1
            continue
        idx += 1
    return None


def _rehydrate_commit_session_from_tmpdir() -> None:
    env_file = Path(os.environ.get("IMPLEMENT_TMPDIR", "")) / "session-env.sh" if os.environ.get("IMPLEMENT_TMPDIR") else None
    if env_file and env_file.is_file():
        for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
            if not os.environ.get(key):
                value = _session_get(file=env_file, key=key, default="")
                if value:
                    os.environ[key] = value


def _mark_commit_timing() -> None:
    _invoke_cli(["token", "mark", "Step 4 — commit implementation"])
    env = os.environ.copy()
    env["LARCH_TIMING_SKILL"] = "implement"
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 4 — commit implementation"], env=env, check=False)


def _build_commit_args(args: argparse.Namespace) -> list[str]:
    commit_args = [sys.executable, str(_current_cli_path()), "git", "commit", "-m", args.message]
    if args.pathspec_from_file:
        commit_args.extend(["--only", "--pathspec-from-file", args.pathspec_from_file])
        if args.pathspec_file_nul:
            commit_args.append("--pathspec-file-nul")
    else:
        commit_args.extend(args.files)
    return commit_args


def _emit_commit_result(result: subprocess.CompletedProcess[str]) -> int:
    if result.returncode == 0:
        sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        _emit_kv(key="COMMITTED", value="true")
        _emit_kv(key="SHA", value=sha)
        return 0
    error = (result.stderr or result.stdout).replace("\n", " ")[:500]
    _emit_kv(key="COMMITTED", value="false")
    _emit_kv(key="SHA", value="")
    _emit_kv(key="ERROR", value=error)
    return result.returncode


def commit_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    argv_list = list(argv if argv is not None else sys.argv[1:])
    scan_rc = _scan_commit_argv(argv_list)
    if scan_rc is not None:
        return scan_rc
    parser = argparse.ArgumentParser(prog="cli.py implement commit", add_help=True)
    parser.add_argument("--message", "-m", default="")
    parser.add_argument("--pathspec-from-file", default="")
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv_list)
    if not args.message.strip():
        return _commit_usage_fail("--message is required")
    _rehydrate_commit_session_from_tmpdir()
    _mark_commit_timing()
    return _emit_commit_result(_run(_build_commit_args(args)))
