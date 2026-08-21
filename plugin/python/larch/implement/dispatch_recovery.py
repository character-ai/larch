# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Recovery-path library helpers.

The `implement recovery-paths` CLI is Rust-owned. This module keeps the
in-process `compute_recovery_paths` helper for still-Python dispatch callers
until those commands cut over.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from larch.implement.dispatch_helpers import (
    RecoveryParse,
    _parse_porcelain_z,
    _write_bytes_atomic,
    resolve_tmpdir_path,
)


@dataclass(frozen=True)
class RecoveryPorcelainInputs:
    prelaunch_porcelain: Path
    postlaunch_porcelain: Path
    prelaunch_digests: Path


def _resolve_tmpdir_path(*, tmpdir: Path, raw: str, default_relpath: str) -> Path:
    return resolve_tmpdir_path(tmpdir=tmpdir, raw=raw, default_relpath=default_relpath)


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
        include = _recovery_path_included(
            status=status, rel=rel, pre=pre, digests=digests, repo_root=repo_root
        )
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
    candidates = _collect_recovery_candidates(
        repo_root=repo_root, tmp_rel=tmp_rel, pre=pre, post=post, digests=digests
    )
    _write_bytes_atomic(
        path=out_file,
        data=b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in candidates),
    )
    return bool(candidates)
