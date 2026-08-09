"""larch-log: Rust-consumer facade for run-log initialization and entry writes.

`run-log init`, `write`, `write-round`, `append`, `append-entry`,
`append-failure`, `exists`, and `verify-completeness` are Rust-owned
(issue #8073). The helpers below are consumers: each one builds an argv and
executes the verified bootstrap script, then translates the command's exit code
into the `ValueError` / `OSError` contract its Python callers already handle.
No run-log entry write is performed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from larch.core import proc
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env


# The Rust owner exits 1 for a refusal (Python's historical `ValueError`) and 2
# for an I/O failure (Python's historical `OSError`).
_RC_REFUSED = 1


@dataclass(frozen=True)
class LogInitResult:
    """Result of :func:`log_init`: manifest path and idempotent write state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class RunParent:
    """Optional parent identity for a nested run-log invocation."""

    skill: str
    run_id: str


@dataclass(frozen=True)
class LogWriteResult:
    """Result of :func:`log_write`: batch path and idempotent write state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class LogAppendResult:
    """Result of :func:`log_append`: batch path and append state."""

    path: Path
    written: bool
    unchanged: bool


@dataclass(frozen=True)
class LogAppendFailureResult:
    """Result of :func:`log_append_failure`: execution-issue log path and append flag."""

    log: Path
    appended: bool


def _run_run_log(argv: list[str]) -> dict[str, str]:
    """Execute one Rust-owned `run-log` verb and return its KEY=value stdout.

    Callers pass the literal domain and verb so the command-registry caller
    scanner records exactly the verbs this module consumes.

    Raises ``ValueError`` for a refusal and ``OSError`` for an I/O failure, so
    callers keep the exception contract the retired Python owner published.
    """
    command = [str(larch_entrypoint()), *argv]
    result = proc.run(command, env=larch_entrypoint_env())
    envelope: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            envelope[key] = value
    if result.returncode != 0:
        message = envelope.get("ERROR") or result.stderr.strip() or f"{' '.join(argv)} failed"
        if result.returncode == _RC_REFUSED:
            raise ValueError(message)
        raise OSError(message)
    return envelope


def log_init(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    parent: RunParent | None = None,
    issue: str = "",
) -> LogInitResult:
    """Idempotently synthesize a v2 manifest for ``skill``/``run_id``.

    Raises ``ValueError`` for an invalid ``parent`` slug or non-numeric
    ``issue``. Returns an unchanged result when the manifest already exists.
    """
    arguments = ["run-log", "init", "--log-root", str(log_root), "--skill", skill, "--run-id", run_id]
    if parent is not None:
        arguments += ["--parent-skill", parent.skill, "--parent-run-id", parent.run_id]
    if issue:
        arguments += ["--issue", str(issue)]
    envelope = _run_run_log(arguments)
    return LogInitResult(
        path=Path(envelope.get("LOG_PATH", "")),
        written=envelope.get("LOG_WRITTEN") == "true",
        unchanged=envelope.get("UNCHANGED") == "true",
    )


def log_write(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    input_file: str,
) -> LogWriteResult:
    """Write a batch payload, returning its path and idempotent write state."""
    envelope = _run_run_log(
        [
            "run-log", "write", "--log-root", str(log_root), "--skill", skill, "--run-id", run_id,
            "--batch", batch, "--input-file", input_file,
        ],
    )
    return LogWriteResult(
        path=Path(envelope.get("LOG_PATH", "")),
        written=envelope.get("LOG_WRITTEN") == "true",
        unchanged=envelope.get("UNCHANGED") == "true",
    )


def log_append(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    batch: str,
    record_file: str,
) -> LogAppendResult:
    """Append a record to a batch, returning its path and append state."""
    envelope = _run_run_log(
        [
            "run-log", "append", "--log-root", str(log_root), "--skill", skill, "--run-id", run_id,
            "--batch", batch, "--record-file", record_file,
        ],
    )
    return LogAppendResult(
        path=Path(envelope.get("LOG_PATH", "")),
        written=envelope.get("LOG_WRITTEN") == "true",
        unchanged=envelope.get("UNCHANGED") == "true",
    )


def log_write_round(
    *,
    log_root: Path,
    skill: str,
    run_id: str,
    round_number: int,
    source_dir: Path,
) -> int:
    """Publish one review round's artifacts, returning the command exit code.

    Round publication is best-effort at every call site, so this consumer
    reports the exit code instead of raising.
    """
    command = [
        str(larch_entrypoint()), "run-log", "write-round",
        "--log-root", str(log_root), "--skill", skill, "--run-id", run_id,
        "--round", str(round_number), "--source-dir", str(source_dir),
    ]
    return proc.run(command, env=larch_entrypoint_env()).returncode


def log_append_failure(
    *,
    log: Path,
    site: str,
    tool: str,
    exit_code: str,
    category: str,
    output_file: Path,
    verdict: str = "",
    retry_count: str = "",
    transient_retry_count: str = "",
    redact_body: bool = False,
    status_label: str = "failed",
) -> LogAppendFailureResult:
    """Format and append a failure entry to an execution-issue log.

    Raises ``ValueError`` for an unsupported category or malformed integer
    fields, and ``OSError`` for an append failure.
    """
    arguments = [
        "run-log", "append-failure",
        "--log", str(log), "--site", site, "--tool", tool, "--exit-code", exit_code,
        "--category", category, "--output-file", str(output_file),
        "--status-label", status_label,
    ]
    if verdict:
        arguments += ["--verdict", verdict]
    if retry_count:
        arguments += ["--retry-count", retry_count]
    if transient_retry_count:
        arguments += ["--transient-retry-count", transient_retry_count]
    if redact_body:
        arguments.append("--redact")
    envelope = _run_run_log(arguments)
    return LogAppendFailureResult(log=log, appended=envelope.get("APPENDED") == "true")


def path_under_repo(*, repo_root: Path, rel_path: str) -> bool:
    if "\x00" in rel_path or rel_path.startswith("/") or ".." in rel_path.split("/"):
        return False
    try:
        resolved = (repo_root / rel_path).resolve()
        _ = resolved.relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True
