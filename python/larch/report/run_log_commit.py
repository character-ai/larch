# pyright: reportUnusedCallResult=false, reportPrivateUsage=false
"""Archive preparation for larch run-logs.

`run-log publish-breadcrumbs` is Rust-owned (issue #8074).
:func:`_publish_breadcrumbs_with_warning` is a consumer: it builds an argv and
executes the verified bootstrap script. The superseded Git-commit
implementation this module used to own was deleted in the same cutover; the
shared run lifecycle and `run-log publish` own run terminalization now.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from larch.core import logging_util
from larch.core import proc
from larch.core import redact
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env
from larch.errors import ShipError

from larch.report.run_log_batch import (
    _run_dir,
    _validate_slug,
)
from larch.report.run_log_manifest import (
    _manifest_cli_path,
    _update_manifest_v2,
    verify_run_log_completeness,
)


@dataclass(frozen=True)
class PreparedArchiveRun:
    """Final sanitized run directory ready for immutable archive publication."""

    run_dir: Path
    secret_scrub_violations: int


def _scrub_run_tree(directory: Path) -> tuple[int, int]:
    """Scrub secret-shaped values and local paths from a publication tree.

    Returns ``(total_violations, files_scrubbed)``. Files needing no redaction
    are left byte-for-byte untouched. Fail-closed: raises :class:`ShipError` if a
    detected value survives scrubbing, so the caller aborts publication.
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
        path_scrubbed: str = redact.redact_tmpdir_paths(original)
        scrub_result = redact.scrub_log_secrets(path_scrubbed)
        scrubbed = scrub_result.scrubbed
        findings = scrub_result.findings
        if scrubbed == original and not findings:
            continue
        residual = redact.scrub_log_secrets(scrubbed).findings
        if residual:
            msg = f"secret survived scrubbing in {path}"
            raise ShipError(msg)
        if redact.redact_tmpdir_paths(scrubbed) != scrubbed:
            msg = f"tmpdir path survived scrubbing in {path}"
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


def prepare_run_for_archive(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    repo_root: Path,
    pre_scrub_violations: int = 0,
) -> PreparedArchiveRun:
    """Finalize one staged run without copying to or mutating a Git worktree."""
    if pre_scrub_violations < 0:
        raise ValueError("pre-scrub violations must be non-negative")
    _validate_slug(label="skill", value=skill)
    _validate_slug(label="run-id", value=run_id)
    run_dir: Path = _run_dir(log_root=log_root, skill=skill, run_id=run_id)
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ShipError(f"run-log staging directory is missing or unsafe: {run_dir}")
    manifest: Path = _manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)
    try:
        _update_manifest_v2(path=manifest, updates={})
    except (OSError, json.JSONDecodeError, TypeError, ValueError, UnicodeError) as exc:
        raise ShipError(f"run-log manifest finalization failed: {exc}") from exc
    complete, missing = verify_run_log_completeness(
        run_dir=run_dir,
        skill=skill,
        repo_root=repo_root,
    )
    if not complete:
        raise ShipError(f"run-log incomplete: {', '.join(missing)}")
    _publish_breadcrumbs_with_warning(log_root=log_root, dest=run_dir)
    violations, files_scrubbed = _scrub_run_tree(run_dir)
    if violations > 0:
        _warn_secret_scrub(
            violations=violations,
            files_scrubbed=files_scrubbed,
            directory=run_dir,
        )
    return PreparedArchiveRun(
        run_dir=run_dir,
        secret_scrub_violations=pre_scrub_violations + violations,
    )


def _publish_breadcrumbs_with_warning(*, log_root: Path, dest: Path) -> None:
    """Publish session breadcrumbs into ``dest``, warning instead of failing.

    Breadcrumb publication is best-effort decoration on an otherwise complete
    run, so a Rust-owner refusal or a spawn failure warns and leaves the staged
    tree untouched.
    """
    if log_root.name != "larch-logs":
        return
    bread_src = log_root.parent / "breadcrumbs"
    try:
        command: list[str] = [
            str(larch_entrypoint()),
            "run-log",
            "publish-breadcrumbs",
            "--source-dir",
            str(bread_src),
            "--dest-dir",
            str(dest / "breadcrumbs"),
        ]
        result = proc.run(command, env=larch_entrypoint_env())
    except OSError as exc:
        print(f"WARN: run-log breadcrumb publish failed: {exc}", file=sys.stderr)
        return
    if result.returncode != 0:
        detail = result.stderr.strip() or f"rc={result.returncode}"
        print(f"WARN: run-log breadcrumb publish failed: {detail}", file=sys.stderr)
