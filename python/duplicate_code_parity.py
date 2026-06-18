# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false
"""Legacy vs new duplicate-code parity helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import duplicate_code


@dataclass(frozen=True)
class ParityResult:
    legacy_exit: int
    new_exit: int
    legacy_digest: str
    new_digest: str


def legacy_pylint_exit(root: Path, rcfile: Path) -> int:
    result = subprocess.run(
        [
            "pylint",
            "--rcfile",
            str(rcfile),
            "--disable=all",
            "--enable=duplicate-code",
            "--persistent=no",
            "-j",
            "1",
            ".",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return int(result.returncode)


def legacy_cluster_digest(root: Path, rcfile: Path) -> str:
    """Extract a reportable-cluster digest via pylint's native ``_iter_sims`` path."""
    config = duplicate_code.DuplicateCodeConfig.load(root=root.resolve(), rcfile=rcfile.resolve())
    backend = duplicate_code._import_pylint_backend()
    if not config.root.is_dir():
        raise duplicate_code.DuplicateCodeError(f"missing root: {config.root}")
    with duplicate_code._pushd(config.root):
        linter, checker, fileitems = duplicate_code._bootstrap_linter(config, backend)
        duplicate_code._ingest_files(linter, checker, fileitems, backend)
        commonalities = list(checker._iter_sims())
        clusters = duplicate_code._clusters_from_commonalities(checker, commonalities)
    return duplicate_code._render_digest(clusters)


def parity_exit_code(rc: int, *, legacy: bool) -> int:
    if not legacy:
        return rc
    if rc == 0:
        return 0
    if rc & 0b11:
        return rc
    if rc & 8:
        return 1
    return rc


def run_parity(root: Path, rcfile: Path, *, jobs: int = 1) -> ParityResult:
    legacy_exit = legacy_pylint_exit(root, rcfile)
    legacy_digest = legacy_cluster_digest(root, rcfile)
    new = duplicate_code.run_duplicate_code(root=root, rcfile=rcfile, jobs=jobs)
    return ParityResult(
        legacy_exit=legacy_exit,
        new_exit=new.exit_code,
        legacy_digest=legacy_digest,
        new_digest=new.digest,
    )


def assert_parity(root: Path, rcfile: Path, *, jobs: int = 1) -> None:
    result = run_parity(root, rcfile, jobs=jobs)
    normalized_legacy = parity_exit_code(result.legacy_exit, legacy=True)
    if normalized_legacy != result.new_exit:
        raise AssertionError(
            "exit-code mismatch: "
            f"legacy={result.legacy_exit} (normalized={normalized_legacy}) "
            f"new={result.new_exit}"
        )
    if result.legacy_digest != result.new_digest:
        raise AssertionError(
            "digest mismatch:\n"
            f"legacy={result.legacy_digest}\n"
            f"new={result.new_digest}"
        )
