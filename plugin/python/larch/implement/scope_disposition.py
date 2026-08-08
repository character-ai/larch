"""Mechanical plan-coverage disposition helpers for /implement."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

from larch import io as larch_io
from larch.core import config, logging_util, proc
from larch.core.proc import CommandResult, Runner
from larch.core.repo_roots import larch_entrypoint, larch_entrypoint_env
from larch.errors import NeedsUserInput, ShipError
from larch.implement.dispatch_helpers import porcelain_status_paths_z
from larch.state.session_env import run_log_write_argv

CoverageBand = Literal["advisory", "middle", "high"]
Disposition = Literal["proceed-partial", "bail-rescope"]

COVERAGE_JSON = "plan-coverage.json"
COVERAGE_ENV = "plan-coverage.env"
UNTOUCHED_PATHS = "plan-coverage-untouched.txt"
TODOS_LEFT = "plan-coverage-todos-left.txt"
DISPOSITION_JSON = "scope-disposition.json"
DEFERRED_INVENTORY = "deferred-plan-inventory.md"
FALLBACK_PROVENANCE = "scope-fallback-provenance.json"
_MAX_TODO_ITEMS = 20
_MAX_TODO_CHARS = 4000
_MAX_UNTOUCHED_INVENTORY = 80
_SHIP_PR_STATE = "ship-pr-state.sh"
_SESSION_ENV = "session-env.sh"
_FULL_SUITE_TOKENS: Final[frozenset[str]] = frozenset({"suite", "suites"})
_UNRUN_VALIDATION_TOKENS: Final[frozenset[str]] = frozenset(
    {"incomplete", "skipped", "uncompleted", "unexecuted", "unrun"}
)
_NEGATED_VALIDATION_ACTION_TOKENS: Final[frozenset[str]] = frozenset(
    {"completed", "executed", "finished", "ran", "run"}
)
_VALIDATION_BLOCKER_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "added",
        "broken",
        "error",
        "errors",
        "fail",
        "failed",
        "failing",
        "fails",
        "failure",
        "fixed",
        "fixes",
        "finish",
        "fix",
        "missing",
        "unimplemented",
        "write",
        "writing",
    }
)
_VALIDATION_COMMAND_TOKENS: Final[tuple[tuple[str, ...], ...]] = (
    ("make", "py", "lint"),
    ("make", "py", "test"),
)
_FOCUSED_TESTS_PASSED_TOKENS: Final[tuple[tuple[str, ...], ...]] = (
    ("focused", "tests", "passed"),
    ("focused", "test", "passed"),
)


@dataclass(frozen=True)
class PlanCoverage:
    total: int
    touched: int
    untouched: int
    untouched_percent: int
    band: CoverageBand
    plan_paths: tuple[str, ...]
    touched_paths: tuple[str, ...]
    untouched_paths: tuple[str, ...]
    todos_left_count: int
    todos_left: tuple[str, ...]
    fingerprint: str
    disposition_required: bool
    plan_fidelity_forced: bool
    coverage_file: str
    untouched_file: str
    todos_file: str


@dataclass(frozen=True)
class DispositionRecord:
    disposition: Disposition
    fingerprint: str
    followup_issue_number: str = ""
    followup_issue_url: str = ""
    coverage_file: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    required: bool
    reason: str = ""
    coverage: PlanCoverage | None = None
    disposition: DispositionRecord | None = None


@dataclass(frozen=True)
class FollowupIssue:
    number: str
    url: str


@dataclass(frozen=True)
class FallbackProvenance:
    session_id: str
    anchor_head: str
    path_signatures: dict[str, str]


@dataclass(frozen=True)
class BaselineResolution:
    """Internal baseline provenance for plan-coverage attribution.

    ``committed_paths_trustworthy`` is True only for a live merge-base against
    the selected remote default branch. Frozen Step 2 fallback never attributes
    ``baseline..HEAD`` committed paths.
    """

    sha: str
    committed_paths_trustworthy: bool
    frozen_fallback_active: bool
    remote: str
    diagnostic: str = ""


def coverage_path(tmpdir: Path) -> Path:
    return tmpdir / COVERAGE_JSON


def coverage_env_path(tmpdir: Path) -> Path:
    return tmpdir / COVERAGE_ENV


def disposition_path(tmpdir: Path) -> Path:
    return tmpdir / DISPOSITION_JSON


def _json_text(data: object) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _safe_line(value: object, *, limit: int = 300) -> str:
    text = re.sub(r"[\r\n]+", " ", str(value)).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _artifact_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _trusted_input_root(path: Path) -> Path:
    """Return the narrow deterministic root that owns a workflow input."""
    return path.parent


def _load_manifest_todos_raw(manifest_path: Path) -> list[object]:
    """Read, parse, and validate manifest; return raw todos_left list."""
    try:
        raw_text = larch_io.read_trusted_text(
            manifest_path, root=_trusted_input_root(manifest_path), errors="replace"
        )
    except OSError as exc:
        raise ShipError(f"resolved manifest unreadable: {manifest_path}") from exc
    try:
        parsed: object = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ShipError(f"resolved manifest malformed: {manifest_path}") from exc
    if not isinstance(parsed, dict):
        raise ShipError(f"resolved manifest schema-invalid: {manifest_path}")
    raw = cast("Mapping[str, object]", parsed).get("todos_left")
    if not isinstance(raw, list):
        raise ShipError(f"resolved manifest schema-invalid: {manifest_path}")
    return cast("list[object]", raw)


def _word_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.lower()))


def _contains_token_sequence(
    tokens: tuple[str, ...], sequence: tuple[str, ...]
) -> bool:
    sequence_len = len(sequence)
    return any(
        tokens[index : index + sequence_len] == sequence
        for index in range(len(tokens) - sequence_len + 1)
    )


def _mentions_full_suite_validation(tokens: tuple[str, ...]) -> bool:
    return (
        "full" in tokens
        and any(token in _FULL_SUITE_TOKENS for token in tokens)
        and any(
            _contains_token_sequence(tokens, sequence)
            for sequence in _VALIDATION_COMMAND_TOKENS
        )
    )


def _mentions_unrun_validation(tokens: tuple[str, ...]) -> bool:
    if any(token in _UNRUN_VALIDATION_TOKENS for token in tokens):
        return True
    for index, token in enumerate(tokens):
        if token not in _NEGATED_VALIDATION_ACTION_TOKENS:
            continue
        prior_tokens = tokens[max(0, index - 3) : index]
        if "not" in prior_tokens or "never" in prior_tokens:
            return True
    return False


def _mentions_focused_tests_passed(tokens: tuple[str, ...]) -> bool:
    return any(
        _contains_token_sequence(tokens, sequence)
        for sequence in _FOCUSED_TESTS_PASSED_TOKENS
    )


def _is_nonblocking_full_suite_validation_todo(value: str) -> bool:
    tokens = _word_tokens(value)
    return (
        not any(token in _VALIDATION_BLOCKER_TOKENS for token in tokens)
        and _mentions_full_suite_validation(tokens)
        and _mentions_unrun_validation(tokens)
        and _mentions_focused_tests_passed(tokens)
    )


def _read_manifest_todos(manifest_path: Path | None) -> tuple[tuple[str, ...], int]:
    """Return (sanitized_display_items, blocking_entry_count)."""
    if manifest_path is None:
        return (), 0
    if not _artifact_present(manifest_path):
        return (), 0
    raw_items = _load_manifest_todos_raw(manifest_path)
    blocking_items: list[str] = []
    for item in raw_items:
        if not isinstance(item, str):
            raise ShipError(f"resolved manifest schema-invalid: {manifest_path}")
        if not _is_nonblocking_full_suite_validation_todo(item):
            blocking_items.append(item)
    lines: list[str] = []
    budget = _MAX_TODO_CHARS
    for item in blocking_items[:_MAX_TODO_ITEMS]:
        line = _safe_line(item)
        if not line:
            continue
        if len(line) + 1 > budget:
            break
        lines.append(line)
        budget -= len(line) + 1
    if len(blocking_items) > len(lines):
        lines.append(f"… {len(blocking_items) - len(lines)} more todo item(s) omitted")
    return tuple(lines), len(blocking_items)


def _git(runner: Runner, argv: Sequence[str], *, cwd: Path) -> CommandResult:
    return runner.run(["git", *argv], cwd=str(cwd))


def _read_forked_target_flag(path: Path, *, tmpdir: Path) -> bool:
    try:
        text = larch_io.read_trusted_text(path, root=tmpdir, errors="replace")
    except OSError:
        return False
    try:
        data = larch_io.parse_kv(text, skip_comments=True, cr_strip="strip")
    except ValueError:
        return False
    return data.get("FORKED_TARGET") == "true"


def _forked_target_from_trusted_state(tmpdir: Path) -> bool:
    """Return FORKED_TARGET from trusted run-state files only.

    ``ship-pr-state.sh`` wins whenever present (even when the key is missing or
    malformed). Otherwise ``session-env.sh`` is consulted. Ambient ``os.environ``
    is never read.
    """
    ship = tmpdir / _SHIP_PR_STATE
    if _artifact_present(ship):
        return _read_forked_target_flag(ship, tmpdir=tmpdir)
    session = tmpdir / _SESSION_ENV
    if _artifact_present(session):
        return _read_forked_target_flag(session, tmpdir=tmpdir)
    return False


def _selected_coverage_remote(tmpdir: Path) -> str:
    return "upstream" if _forked_target_from_trusted_state(tmpdir) else "origin"


def _validate_remote_symbolic_ref(value: str, *, remote: str) -> str | None:
    """Return a safe ``<remote>/<branch>`` ref, or None when unusable in Git argv."""
    text = value.strip()
    prefix = f"{remote}/"
    if not text.startswith(prefix):
        return None
    branch = text[len(prefix) :]
    if not _is_safe_refname(branch):
        return None
    return text


def _is_safe_refname(refname: str) -> bool:
    """Accept a conservative subset of Git refnames without revision syntax."""
    if not refname or refname.startswith("-") or refname.endswith("/"):
        return False
    if ".." in refname:
        return False
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/+\-]*", refname):
        return False
    return all(
        component
        and not component.startswith(".")
        and not component.endswith(".")
        and not component.endswith(".lock")
        for component in refname.split("/")
    )


def _resolve_selected_remote_head(
    *, repo_root: Path, remote: str, runner: Runner
) -> str | None:
    result = _git(
        runner,
        ["symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"],
        cwd=repo_root,
    )
    if result.returncode != 0:
        return None
    return _validate_remote_symbolic_ref(result.stdout, remote=remote)


def _step2_baseline_sha(tmpdir: Path) -> str:
    baseline_file = tmpdir / "step2-baseline.txt"
    try:
        raw = larch_io.read_trusted_text(
            baseline_file, root=tmpdir, errors="replace"
        ).strip()
    except OSError as exc:
        raise ShipError("step2 baseline missing or unreadable") from exc
    if raw:
        return raw
    raise ShipError("step2 baseline missing or unreadable")


def _emit_frozen_fallback_diagnostic(*, remote: str, baseline_sha: str) -> None:
    short_sha = _safe_line(baseline_sha, limit=64)
    print(
        "scope-disposition: unresolved "
        f"{remote}/HEAD; using frozen step2 baseline "
        f"{short_sha} (porcelain-only attribution)",
        file=sys.stderr,
    )


def resolve_baseline(
    *, tmpdir: Path, repo_root: Path, runner: Runner = proc
) -> BaselineResolution:
    """Resolve the coverage baseline with live vs frozen provenance.

    A resolved selected-remote default branch uses ``git merge-base`` and marks
    committed-path attribution trustworthy. Merge-base failure raises
    ``ShipError``. Only unresolved/invalid remote HEAD falls back to the frozen
    Step 2 baseline with porcelain-only attribution.
    """
    remote = _selected_coverage_remote(tmpdir)
    remote_head = _resolve_selected_remote_head(
        repo_root=repo_root, remote=remote, runner=runner
    )
    if remote_head is None:
        sha = _step2_baseline_sha(tmpdir)
        diagnostic = f"unresolved {remote}/HEAD; frozen step2 baseline"
        _emit_frozen_fallback_diagnostic(remote=remote, baseline_sha=sha)
        return BaselineResolution(
            sha=sha,
            committed_paths_trustworthy=False,
            frozen_fallback_active=True,
            remote=remote,
            diagnostic=diagnostic,
        )
    merge = _git(runner, ["merge-base", remote_head, "HEAD"], cwd=repo_root)
    if merge.returncode != 0:
        detail = _safe_line(merge.stderr or merge.stdout or "merge-base failed")
        raise ShipError(f"merge-base failed for {remote_head}: {detail}")
    sha = merge.stdout.strip()
    if not sha:
        raise ShipError(f"merge-base returned empty SHA for {remote_head}")
    return BaselineResolution(
        sha=sha,
        committed_paths_trustworthy=True,
        frozen_fallback_active=False,
        remote=remote,
        diagnostic=f"live merge-base against {remote_head}",
    )


def _fallback_provenance_path(tmpdir: Path) -> Path:
    return tmpdir / FALLBACK_PROVENANCE


def _read_fallback_provenance(tmpdir: Path) -> FallbackProvenance | None:
    path = _fallback_provenance_path(tmpdir)
    if not _artifact_present(path):
        return None
    try:
        raw_text = larch_io.read_trusted_text(path, root=tmpdir, errors="replace")
        parsed: object = json.loads(raw_text)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return _parse_fallback_provenance(parsed)


def _parse_fallback_provenance(parsed: object) -> FallbackProvenance | None:
    if not isinstance(parsed, dict):
        return None
    data = cast("Mapping[str, object]", parsed)
    session_id = data.get("session_id")
    anchor_head = data.get("anchor_head")
    raw_signatures = data.get("path_signatures")
    if (
        not isinstance(session_id, str)
        or not session_id
        or not isinstance(anchor_head, str)
        or not re.fullmatch(r"[0-9a-f]{40,64}", anchor_head)
    ):
        return None
    if not isinstance(raw_signatures, dict):
        return None
    signatures = cast("dict[object, object]", raw_signatures)
    path_signatures: dict[str, str] = {}
    for path, signature in signatures.items():
        if (
            not isinstance(path, str)
            or not isinstance(signature, str)
            or not path
            or "\0" in path
            or not re.fullmatch(r"[0-9a-f]{64}|missing|unreadable", signature)
        ):
            return None
        path_signatures[path] = signature
    return FallbackProvenance(
        session_id=session_id,
        anchor_head=anchor_head,
        path_signatures=path_signatures,
    )


def _write_fallback_provenance(tmpdir: Path, provenance: FallbackProvenance) -> None:
    payload = {
        "schema_version": "3",
        "session_id": provenance.session_id,
        "anchor_head": provenance.anchor_head,
        "path_signatures": provenance.path_signatures,
    }
    larch_io.trusted_atomic_write(
        _fallback_provenance_path(tmpdir),
        _json_text(payload),
        root=tmpdir,
    )


def _fallback_path_signature(*, repo_root: Path, path: str) -> str:
    try:
        target = (repo_root / path).resolve()
        root = repo_root.resolve()
        if root not in target.parents or not target.is_file() or target.is_symlink():
            return "missing"
        return hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        return "unreadable"


def _firm_path_covered_by(firm_path: str, touched_path: str) -> bool:
    """Return True when *touched_path* covers firm plan path *firm_path*.

    Exact matches always count. Only firm paths ending in ``/`` also accept
    descendants with that exact prefix; similarly prefixed siblings do not.
    """
    if touched_path == firm_path:
        return True
    return firm_path.endswith("/") and touched_path.startswith(firm_path)


def _map_touched_to_firm_paths(
    plan_paths: Sequence[str], raw_touched: Sequence[str]
) -> tuple[str, ...]:
    """Map raw touched paths onto ordered firm plan paths via coverage predicate."""
    return tuple(
        firm
        for firm in plan_paths
        if any(_firm_path_covered_by(firm, touched) for touched in raw_touched)
    )


def _frozen_fallback_touched_paths(
    *,
    tmpdir: Path,
    repo_root: Path,
    runner: Runner,
    plan_paths: frozenset[str],
) -> tuple[str, ...]:
    """Attribute coverage from current porcelain and this run's commits only."""
    status = _git(
        runner,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
    )
    if status.returncode != 0:
        raise ShipError("working-tree status failed")
    porcelain = _porcelain_paths_z(status.stdout)
    # Keep raw porcelain child paths for provenance/signature inputs; coverage
    # mapping to firm plan-path spelling happens later in compute_coverage.
    porcelain_plan = {
        path
        for path in porcelain
        if any(_firm_path_covered_by(firm, path) for firm in plan_paths)
    }

    session_id = _fallback_session_id(tmpdir)
    head = _git(runner, ["rev-parse", "HEAD"], cwd=repo_root)
    if head.returncode != 0 or not re.fullmatch(
        r"[0-9a-f]{40,64}", head.stdout.strip()
    ):
        return tuple(sorted(porcelain_plan))
    current_head = head.stdout.strip()
    provenance = _read_fallback_provenance(tmpdir)
    active_provenance = (
        provenance
        if provenance is not None and provenance.session_id == session_id
        else None
    )
    committed_plan: set[str] = set()
    if active_provenance is not None:
        diff = _git(
            runner,
            ["diff", "--name-only", f"{active_provenance.anchor_head}..{current_head}"],
            cwd=repo_root,
        )
        if diff.returncode != 0:
            raise ShipError("frozen fallback anchor-to-HEAD diff failed")
        committed_plan.update(
            path
            for path in diff.stdout.splitlines()
            if (
                path in active_provenance.path_signatures
                and _fallback_path_signature(repo_root=repo_root, path=path)
                == active_provenance.path_signatures[path]
            )
        )
    if session_id:
        path_signatures = (
            dict(active_provenance.path_signatures) if active_provenance else {}
        )
        path_signatures.update(
            {
                path: _fallback_path_signature(repo_root=repo_root, path=path)
                for path in porcelain_plan
            }
        )
        _write_fallback_provenance(
            tmpdir,
            FallbackProvenance(
                session_id=session_id,
                anchor_head=(
                    active_provenance.anchor_head if active_provenance else current_head
                ),
                path_signatures=path_signatures,
            ),
        )
    verified_porcelain: set[str] = porcelain_plan if session_id else set()
    return tuple(sorted(verified_porcelain | committed_plan))


def _fallback_session_id(tmpdir: Path) -> str:
    try:
        session_id = larch_io.read_trusted_text(
            tmpdir / "session-id", root=tmpdir, errors="replace"
        ).strip()
    except OSError:
        return ""
    return session_id if session_id and "\0" not in session_id else ""


def _live_touched_paths(
    *, repo_root: Path, baseline_sha: str, runner: Runner
) -> tuple[str, ...]:
    touched: set[str] = set()
    diff = _git(runner, ["diff", "--name-only", f"{baseline_sha}..HEAD"], cwd=repo_root)
    if diff.returncode != 0:
        raise ShipError("baseline-to-HEAD diff failed")
    touched.update(line for line in diff.stdout.splitlines() if line)
    status = _git(
        runner,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
    )
    if status.returncode != 0:
        raise ShipError("working-tree status failed")
    touched.update(_porcelain_paths_z(status.stdout))
    return tuple(sorted(touched))


def touched_paths_since_baseline(
    *,
    tmpdir: Path,
    repo_root: Path,
    runner: Runner = proc,
    plan_paths: Sequence[str] | None = None,
) -> tuple[str, ...]:
    """Return candidate touched paths since the resolved coverage baseline.

    Live merge-base resolution attributes committed ``baseline..HEAD`` paths plus
    porcelain status. Frozen remote-HEAD fallback never runs that committed
    diff; it unions porcelain plan paths with verified internal provenance.
    """
    resolution = resolve_baseline(tmpdir=tmpdir, repo_root=repo_root, runner=runner)
    if resolution.frozen_fallback_active:
        plan_set = frozenset(plan_paths or ())
        return _frozen_fallback_touched_paths(
            tmpdir=tmpdir,
            repo_root=repo_root,
            runner=runner,
            plan_paths=plan_set,
        )
    return _live_touched_paths(
        repo_root=repo_root, baseline_sha=resolution.sha, runner=runner
    )


def _porcelain_paths_z(stdout: str) -> set[str]:
    return set(porcelain_status_paths_z(stdout))


def _firm_plan_paths(plan_file: Path) -> tuple[str, ...]:
    from larch.issue import issue_wire  # noqa: PLC0415  # lint-layering: ok scope extraction lives in issue-wire; function-level import avoids gh/body-edit cycle.

    try:
        plan_text = larch_io.read_trusted_text(
            plan_file, root=_trusted_input_root(plan_file), errors="replace"
        )
    except OSError as exc:
        raise ShipError(f"plan file unreadable: {plan_file}: {exc}") from exc
    return tuple(
        dict.fromkeys(
            issue_wire.extract_scope_paths(
                plan_text=plan_text, use_fallback=False, include_optional=False
            )
        )
    )


def _coverage_band(*, total: int, untouched: int) -> CoverageBand:
    percent = int((untouched * 100) / total) if total > 0 else 0
    if total > 0 and (
        untouched >= config.PLAN_COVERAGE_HIGH_UNTOUCHED_COUNT
        or percent >= config.PLAN_COVERAGE_HIGH_UNTOUCHED_PERCENT
    ):
        return "high"
    if total > 0 and (
        untouched >= config.PLAN_COVERAGE_MIDDLE_UNTOUCHED_COUNT
        or percent >= config.PLAN_COVERAGE_MIDDLE_UNTOUCHED_PERCENT
    ):
        return "middle"
    return "advisory"


def _fingerprint(
    *,
    plan_paths: tuple[str, ...],
    touched_paths: tuple[str, ...],
    todos_left: tuple[str, ...],
) -> str:
    payload = {
        "plan_paths": list(plan_paths),
        "todos_left": list(todos_left),
        "touched_paths": list(touched_paths),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_coverage(
    *,
    tmpdir: Path,
    repo_root: Path,
    plan_file: Path | None = None,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> PlanCoverage:
    effective_plan = plan_file or tmpdir / "plan.txt"
    plan_paths = _firm_plan_paths(effective_plan)
    raw_touched = touched_paths_since_baseline(
        tmpdir=tmpdir,
        repo_root=repo_root,
        runner=runner,
        plan_paths=plan_paths,
    )
    # Coverage and its fingerprint must stay stable across relaunches. The raw
    # touched set can include the selected remote's own evolution plus the ship
    # driver's larch-logs flush commits, so it drifts on every relaunch and
    # would invalidate a recorded disposition. Keep only firm plan paths: map
    # raw touched files (including directory descendants) onto ordered firm
    # plan-path spelling. Non-plan paths cannot affect plan coverage.
    # Frozen fallback never attributes committed upstream churn at all.
    touched = _map_touched_to_firm_paths(plan_paths, raw_touched)
    touched_set = set(touched)
    untouched_paths = tuple(path for path in plan_paths if path not in touched_set)
    total = len(plan_paths)
    untouched = len(untouched_paths)
    touched_count = total - untouched
    percent = int((untouched * 100) / total) if total > 0 else 0
    band = _coverage_band(total=total, untouched=untouched)
    todos_left, blocking_todos_count = _read_manifest_todos(manifest_path)
    fingerprint = _fingerprint(
        plan_paths=plan_paths, touched_paths=touched, todos_left=todos_left
    )
    return PlanCoverage(
        total=total,
        touched=touched_count,
        untouched=untouched,
        untouched_percent=percent,
        band=band,
        plan_paths=plan_paths,
        touched_paths=touched,
        untouched_paths=untouched_paths,
        todos_left_count=blocking_todos_count,
        todos_left=todos_left,
        fingerprint=fingerprint,
        disposition_required=band == "high" or blocking_todos_count > 0,
        plan_fidelity_forced=band in {"middle", "high"},
        coverage_file=str(coverage_path(tmpdir)),
        untouched_file=str(tmpdir / UNTOUCHED_PATHS),
        todos_file=str(tmpdir / TODOS_LEFT),
    )


def write_coverage(coverage: PlanCoverage, *, tmpdir: Path) -> None:
    _ = larch_io.validate_trusted_directory(tmpdir)
    untouched_file = Path(coverage.untouched_file)
    todos_file = Path(coverage.todos_file)
    larch_io.trusted_atomic_write(
        untouched_file,
        "".join(f"{path}\n" for path in coverage.untouched_paths),
        root=tmpdir,
    )
    larch_io.trusted_atomic_write(
        todos_file,
        "".join(f"- {line}\n" for line in coverage.todos_left),
        root=tmpdir,
    )
    larch_io.trusted_atomic_write(
        coverage_path(tmpdir), _json_text(asdict(coverage)), root=tmpdir
    )
    rows: list[tuple[str, object]] = [
        ("PLAN_COVERAGE_TOTAL", coverage.total),
        ("PLAN_COVERAGE_TOUCHED", coverage.touched),
        ("PLAN_COVERAGE_UNTOUCHED", coverage.untouched),
        ("PLAN_COVERAGE_UNTOUCHED_PERCENT", coverage.untouched_percent),
        ("PLAN_COVERAGE_BAND", coverage.band),
        ("PLAN_COVERAGE_FILE", coverage.coverage_file),
        ("PLAN_COVERAGE_UNTOUCHED_FILE", coverage.untouched_file),
        ("TODOS_LEFT_COUNT", coverage.todos_left_count),
        ("TODOS_LEFT_FILE", coverage.todos_file),
        ("PLAN_COVERAGE_FINGERPRINT", coverage.fingerprint),
        (
            "PLAN_COVERAGE_DISPOSITION_REQUIRED",
            str(coverage.disposition_required).lower(),
        ),
        ("PLAN_FIDELITY_FORCED", str(coverage.plan_fidelity_forced).lower()),
    ]
    # The env file is the completion artifact and is published only after its companions.
    larch_io.trusted_atomic_write(
        coverage_env_path(tmpdir), larch_io.format_kvs(rows), root=tmpdir
    )


def compute_and_write_coverage(
    *,
    tmpdir: Path,
    repo_root: Path,
    plan_file: Path | None = None,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> PlanCoverage:
    coverage = compute_coverage(
        tmpdir=tmpdir,
        repo_root=repo_root,
        plan_file=plan_file,
        manifest_path=manifest_path,
        runner=runner,
    )
    write_coverage(coverage, tmpdir=tmpdir)
    return coverage


def _coverage_from_mapping(data: Mapping[str, object], *, tmpdir: Path) -> PlanCoverage:
    expected_coverage = coverage_path(tmpdir)
    expected_untouched = tmpdir / UNTOUCHED_PATHS
    expected_todos = tmpdir / TODOS_LEFT
    coverage = PlanCoverage(
        total=_as_int(data.get("total")),
        touched=_as_int(data.get("touched")),
        untouched=_as_int(data.get("untouched")),
        untouched_percent=_as_int(data.get("untouched_percent")),
        band=cast("CoverageBand", str(data.get("band") or "")),
        plan_paths=tuple(
            str(item) for item in cast("Sequence[object]", data.get("plan_paths") or ())
        ),
        touched_paths=tuple(
            str(item)
            for item in cast("Sequence[object]", data.get("touched_paths") or ())
        ),
        untouched_paths=tuple(
            str(item)
            for item in cast("Sequence[object]", data.get("untouched_paths") or ())
        ),
        todos_left_count=_as_int(data.get("todos_left_count")),
        todos_left=tuple(
            str(item) for item in cast("Sequence[object]", data.get("todos_left") or ())
        ),
        fingerprint=str(data.get("fingerprint") or ""),
        disposition_required=_as_bool(data.get("disposition_required")),
        plan_fidelity_forced=_as_bool(data.get("plan_fidelity_forced")),
        coverage_file=str(data.get("coverage_file") or ""),
        untouched_file=str(data.get("untouched_file") or ""),
        todos_file=str(data.get("todos_file") or ""),
    )
    if coverage.band not in {"advisory", "middle", "high"}:
        raise ShipError("coverage artifact has an invalid band")
    if (
        Path(coverage.coverage_file) != expected_coverage
        or Path(coverage.untouched_file) != expected_untouched
        or Path(coverage.todos_file) != expected_todos
    ):
        raise ShipError("coverage artifact contains mismatched companion paths")
    expected_untouched_paths = tuple(
        path
        for path in coverage.plan_paths
        if not any(
            _firm_path_covered_by(path, touched) for touched in coverage.touched_paths
        )
    )
    expected_percent = (
        int((coverage.untouched * 100) / coverage.total) if coverage.total else 0
    )
    inconsistencies = [
        coverage.total != len(coverage.plan_paths),
        coverage.untouched_paths != expected_untouched_paths,
        coverage.untouched != len(expected_untouched_paths),
        coverage.touched != coverage.total - coverage.untouched,
        coverage.untouched_percent != expected_percent,
        coverage.band
        != _coverage_band(total=coverage.total, untouched=coverage.untouched),
        coverage.todos_left_count < len(coverage.todos_left),
        coverage.fingerprint
        != _fingerprint(
            plan_paths=coverage.plan_paths,
            touched_paths=coverage.touched_paths,
            todos_left=coverage.todos_left,
        ),
        coverage.disposition_required
        != (coverage.band == "high" or coverage.todos_left_count > 0),
        coverage.plan_fidelity_forced != (coverage.band in {"middle", "high"}),
    ]
    if any(inconsistencies):
        raise ShipError("coverage artifact is internally inconsistent")
    return coverage


def load_coverage(tmpdir: Path) -> PlanCoverage | None:
    paths = (
        coverage_path(tmpdir),
        coverage_env_path(tmpdir),
        tmpdir / UNTOUCHED_PATHS,
        tmpdir / TODOS_LEFT,
    )
    lexical_present = tuple(path.exists() or path.is_symlink() for path in paths)
    if not any(lexical_present):
        return None
    try:
        present = tuple(
            larch_io.trusted_file_present(path, root=tmpdir) for path in paths
        )
    except OSError as exc:
        raise ShipError(f"unsafe coverage artifact: {_safe_line(exc)}") from exc
    if not all(present):
        raise ShipError("coverage artifact set is partial")
    try:
        parsed: object = json.loads(
            larch_io.read_trusted_text(paths[0], root=tmpdir, errors="replace")
        )
        if not isinstance(parsed, dict):
            raise ShipError("coverage artifact schema-invalid")
        coverage = _coverage_from_mapping(
            cast("Mapping[str, object]", parsed), tmpdir=tmpdir
        )
        untouched_text = larch_io.read_trusted_text(
            paths[2], root=tmpdir, errors="replace"
        )
        todos_text = larch_io.read_trusted_text(paths[3], root=tmpdir, errors="replace")
        env = larch_io.parse_kv(
            larch_io.read_trusted_text(paths[1], root=tmpdir, errors="replace")
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ShipError(
            f"coverage artifact unreadable or malformed: {_safe_line(exc)}"
        ) from exc
    if untouched_text != "".join(f"{path}\n" for path in coverage.untouched_paths):
        raise ShipError("coverage untouched inventory mismatch")
    if todos_text != "".join(f"- {line}\n" for line in coverage.todos_left):
        raise ShipError("coverage todo inventory mismatch")
    expected_env = {
        "PLAN_COVERAGE_TOTAL": str(coverage.total),
        "PLAN_COVERAGE_TOUCHED": str(coverage.touched),
        "PLAN_COVERAGE_UNTOUCHED": str(coverage.untouched),
        "PLAN_COVERAGE_UNTOUCHED_PERCENT": str(coverage.untouched_percent),
        "PLAN_COVERAGE_BAND": coverage.band,
        "PLAN_COVERAGE_FILE": coverage.coverage_file,
        "PLAN_COVERAGE_UNTOUCHED_FILE": coverage.untouched_file,
        "TODOS_LEFT_COUNT": str(coverage.todos_left_count),
        "TODOS_LEFT_FILE": coverage.todos_file,
        "PLAN_COVERAGE_FINGERPRINT": coverage.fingerprint,
        "PLAN_COVERAGE_DISPOSITION_REQUIRED": str(
            coverage.disposition_required
        ).lower(),
        "PLAN_FIDELITY_FORCED": str(coverage.plan_fidelity_forced).lower(),
    }
    if any(env.get(key) != value for key, value in expected_env.items()):
        raise ShipError("coverage env companion mismatch")
    return coverage


def load_live_coverage(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> PlanCoverage | None:
    persisted = load_coverage(tmpdir)
    if persisted is None:
        return None
    live = compute_coverage(
        tmpdir=tmpdir,
        repo_root=repo_root,
        manifest_path=resolve_implement_manifest(tmpdir, manifest_path),
        runner=runner,
    )
    if persisted != live:
        raise ShipError("coverage artifact does not match live repository inputs")
    return persisted


def load_disposition(
    tmpdir: Path, *, coverage: PlanCoverage | None = None
) -> DispositionRecord | None:
    path = disposition_path(tmpdir)
    if not path.exists() and not path.is_symlink():
        return None
    try:
        if not larch_io.trusted_file_present(path, root=tmpdir):
            raise ShipError("scope disposition is not a trusted regular file")
        parsed: object = json.loads(
            larch_io.read_trusted_text(path, root=tmpdir, errors="replace")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ShipError(
            f"scope disposition unreadable or unsafe: {_safe_line(exc)}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ShipError("scope disposition schema-invalid")
    data = cast("Mapping[str, object]", parsed)
    disposition = str(data.get("disposition") or "")
    if disposition not in {"proceed-partial", "bail-rescope"}:
        raise ShipError("scope disposition has invalid disposition")
    record = DispositionRecord(
        disposition=cast("Disposition", disposition),
        fingerprint=str(data.get("fingerprint") or ""),
        followup_issue_number=str(data.get("followup_issue_number") or ""),
        followup_issue_url=str(data.get("followup_issue_url") or ""),
        coverage_file=str(data.get("coverage_file") or ""),
    )
    if coverage is not None and (
        record.fingerprint != coverage.fingerprint
        or record.coverage_file != coverage.coverage_file
    ):
        raise ShipError("scope disposition does not match trusted coverage")
    return record


def render_deferred_inventory(
    coverage: PlanCoverage, disposition: DispositionRecord | None = None
) -> str:
    if not coverage.untouched_paths and not coverage.todos_left:
        return ""
    lines = ["## Deferred plan inventory", ""]
    if disposition and disposition.followup_issue_number:
        lines.append(f"Follow-up issue: #{disposition.followup_issue_number}")
        lines.append("")
    if coverage.untouched_paths:
        lines.append("Untouched firm plan paths:")
        lines.extend(
            f"- `{path}`"
            for path in coverage.untouched_paths[:_MAX_UNTOUCHED_INVENTORY]
        )
        if len(coverage.untouched_paths) > _MAX_UNTOUCHED_INVENTORY:
            lines.append(
                f"- … {len(coverage.untouched_paths) - _MAX_UNTOUCHED_INVENTORY} more path(s)"
            )
        lines.append("")
    if coverage.todos_left:
        lines.append("Manifest todos left:")
        lines.extend(f"- {line}" for line in coverage.todos_left)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def resolve_implement_manifest(
    tmpdir: Path, manifest_path: Path | None = None
) -> Path | None:
    if manifest_path is not None:
        if not _artifact_present(manifest_path):
            raise ShipError("declared implement manifest is missing")
        return manifest_path
    for candidate in (
        tmpdir / "manifest.json",
        tmpdir / "codex-step2-out" / "manifest.json",
    ):
        if _artifact_present(candidate):
            return candidate
    return None


def is_pr_mutation_gate_relevant(
    *, tmpdir: Path, manifest_path: Path | None = None
) -> bool:
    return (
        any(
            _artifact_present(candidate)
            for candidate in (
                tmpdir / "plan.txt",
                coverage_path(tmpdir),
                disposition_path(tmpdir),
            )
        )
        or resolve_implement_manifest(tmpdir, manifest_path) is not None
    )


@dataclass(frozen=True)
class ValidatedImplementContext:
    tmpdir: Path
    manifest_path: Path | None


def _validated_implement_context(
    tmpdir: Path | None, *, manifest_path: Path | None = None
) -> ValidatedImplementContext | None:
    env_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    declared = tmpdir is not None or bool(env_tmpdir) or manifest_path is not None
    if not declared:
        return None
    effective_tmpdir = (
        tmpdir if tmpdir is not None else (Path(env_tmpdir) if env_tmpdir else None)
    )
    if effective_tmpdir is None:
        raise ShipError("declared implement context requires a trusted tmpdir")
    try:
        trusted_tmpdir = larch_io.validate_trusted_directory(effective_tmpdir)
    except OSError as exc:
        raise ShipError(
            f"declared implement tmpdir is invalid: {_safe_line(exc)}"
        ) from exc
    return ValidatedImplementContext(
        tmpdir=trusted_tmpdir,
        manifest_path=resolve_implement_manifest(trusted_tmpdir, manifest_path),
    )


def require_pr_mutation_scope_disposition(
    *,
    tmpdir: Path | None,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> None:
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None or not is_pr_mutation_gate_relevant(
        tmpdir=context.tmpdir, manifest_path=context.manifest_path
    ):
        return
    require_valid_disposition_for_ship(
        tmpdir=context.tmpdir,
        repo_root=repo_root,
        manifest_path=context.manifest_path,
        runner=runner,
    )


def disposition_link_kind(
    tmpdir: Path | None = None,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None:
        return "closes"
    if repo_root is None:
        raise ShipError("repository root is required to load scope disposition")
    coverage = load_live_coverage(
        tmpdir=context.tmpdir,
        repo_root=repo_root,
        manifest_path=context.manifest_path,
    )
    if coverage is None and _artifact_present(disposition_path(context.tmpdir)):
        _ = load_disposition(context.tmpdir, coverage=None)
        raise ShipError("scope disposition exists without trusted coverage")
    record = load_disposition(context.tmpdir, coverage=coverage)
    return "part-of" if record and record.disposition == "proceed-partial" else "closes"


def disposition_deferred_inventory(
    tmpdir: Path | None = None,
    *,
    repo_root: Path | None = None,
    manifest_path: Path | None = None,
) -> str:
    context = _validated_implement_context(tmpdir, manifest_path=manifest_path)
    if context is None:
        return ""
    if repo_root is None:
        raise ShipError("repository root is required to load deferred inventory")
    coverage = load_live_coverage(
        tmpdir=context.tmpdir,
        repo_root=repo_root,
        manifest_path=context.manifest_path,
    )
    if coverage is None:
        if _artifact_present(disposition_path(context.tmpdir)):
            _ = load_disposition(context.tmpdir, coverage=None)
            raise ShipError("scope disposition exists without trusted coverage")
        return ""
    return render_deferred_inventory(
        coverage, load_disposition(context.tmpdir, coverage=coverage)
    )


def _parse_cli_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, cr_strip="strip")


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    return default


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _run_cli(argv: Sequence[str]) -> CommandResult:
    cli = Path(__file__).resolve().parents[2] / "cli.py"
    return proc.run([sys.executable, str(cli), *argv])


def _run_larch(argv: Sequence[str]) -> CommandResult:
    """Invoke one Rust-owned command through the verified bootstrap script."""
    root = Path(__file__).resolve().parents[3]
    return proc.run([str(larch_entrypoint(root)), *argv], env=larch_entrypoint_env(root))


def _require_cli_success(result: CommandResult, *, label: str) -> dict[str, str]:
    fields = _parse_cli_kv(result.stdout)
    failure_keys = {
        key
        for key, value in fields.items()
        if key.endswith("FAILED") and value == "true"
    }
    if result.returncode != 0 or failure_keys:
        detail = (
            fields.get("ERROR") or result.stderr or result.stdout or f"{label} failed"
        )
        raise ShipError(_safe_line(detail, limit=500))
    return fields


def _session_mutation_auth_args(tmpdir: Path) -> list[str]:
    """Return the session authorization argv for a nested issue mutation."""
    session_env_path = tmpdir / "session-env.sh"
    if not session_env_path.is_file():
        return []
    run_id = (
        session_env_path.read_text(encoding="utf-8", errors="replace")
        .split("LARCH_RUN_ID=", 1)[-1]
        .splitlines()[0]
        .strip()
    )
    return [
        "--context-file",
        str(session_env_path),
        "--run-id",
        run_id,
        "--trusted-root",
        str(tmpdir),
    ]


def _create_followup_issue(
    *, tmpdir: Path, repo: str, tracking_issue_number: str, coverage: PlanCoverage
) -> FollowupIssue:
    body = tmpdir / "scope-disposition-followup-body.md"
    larch_io.atomic_write(
        body,
        "# Deferred /implement plan inventory\n\n"
        f"Parent tracking issue: #{tracking_issue_number}\n\n"
        + render_deferred_inventory(coverage),
    )
    create_args = [
        "issue",
        "create-one",
        "--title",
        "Complete deferred /implement plan work",
        "--title-prefix",
        "[FOLLOW-UP]",
        "--body-file",
        str(body),
        "--repo",
        repo,
    ]
    create_args.extend(_session_mutation_auth_args(tmpdir))
    created = _run_larch(create_args)
    fields = _require_cli_success(created, label="issue create-one")
    number = fields.get("ISSUE_NUMBER", "")
    url = fields.get("ISSUE_URL", "")
    if not number.isdigit() or not url:
        raise ShipError("issue create-one did not return ISSUE_NUMBER and ISSUE_URL")
    return FollowupIssue(number=number, url=url)


def _append_cross_links(
    *, tmpdir: Path, repo: str, tracking_issue_number: str, followup: FollowupIssue
) -> None:
    parent_body = tmpdir / "scope-disposition-parent-link.md"
    child_body = tmpdir / "scope-disposition-followup-link.md"
    larch_io.atomic_write(
        parent_body,
        f"Partial-scope disposition recorded. Deferred plan work is tracked in #{followup.number}: {followup.url}\n",
    )
    larch_io.atomic_write(
        child_body,
        f"Filed from partial-scope disposition on parent tracking issue #{tracking_issue_number}.\n",
    )
    for issue, body in (
        (tracking_issue_number, parent_body),
        (followup.number, child_body),
    ):
        result = _run_cli(
            [
                "tracking-issue",
                "append-comment",
                "--issue",
                issue,
                "--body-file",
                str(body),
                "--repo",
                repo,
            ]
        )
        _ = _require_cli_success(result, label="tracking-issue append-comment")


def _add_block_relation(
    *, tmpdir: Path, repo: str, tracking_issue_number: str, followup: FollowupIssue
) -> None:
    args = [
        "issue",
        "add-blocked-by",
        "--client-issue",
        tracking_issue_number,
        "--blocker-issue",
        followup.number,
        "--repo",
        repo,
    ]
    args.extend(_session_mutation_auth_args(tmpdir))
    result = _run_larch(args)
    _ = _require_cli_success(result, label="issue add-blocked-by")


def _write_scope_run_log(
    *, tmpdir: Path, run_id: str, record: DispositionRecord, coverage: PlanCoverage
) -> None:
    if not run_id:
        return
    payload = tmpdir / "scope-disposition-run-log.json"
    larch_io.atomic_write(
        payload,
        _json_text(
            {
                "coverage_fingerprint": coverage.fingerprint,
                "disposition": record.disposition,
                "followup_issue_number": record.followup_issue_number,
                "followup_issue_url": record.followup_issue_url,
                "todos_left_count": coverage.todos_left_count,
                "untouched_count": coverage.untouched,
                "total": coverage.total,
            }
        ),
    )
    result = _run_larch(run_log_write_argv(
        log_root=tmpdir / "larch-logs", run_id=run_id,
        batch="scope-disposition", input_file=payload,
    ))
    _ = _require_cli_success(result, label="run-log write scope-disposition")


def _existing_matching_followup(tmpdir: Path, fingerprint: str) -> FollowupIssue | None:
    """Return a previously filed proceed-partial follow-up for this coverage.

    Guards the scope-disposition loop: if ``record`` is invoked repeatedly for
    the same plan coverage (identical fingerprint), reuse the follow-up issue
    already filed instead of opening a new one. Returns None when no durable
    proceed-partial disposition exists or its fingerprint differs.
    """
    try:
        record = load_disposition(tmpdir)
    except ShipError:
        return None
    if (
        record is None
        or record.disposition != "proceed-partial"
        or record.fingerprint != fingerprint
        or not record.followup_issue_number
    ):
        return None
    return FollowupIssue(
        number=record.followup_issue_number, url=record.followup_issue_url
    )


def record_disposition(  # noqa: PLR0913
    *,
    tmpdir: Path,
    disposition: Disposition,
    repo_root: Path,
    repo: str = "",
    tracking_issue_number: str = "",
    run_id: str = "",
    coverage: PlanCoverage | None = None,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> DispositionRecord:
    if coverage is not None:
        active_coverage = coverage
    else:
        active_coverage = load_live_coverage(
            tmpdir=tmpdir,
            repo_root=repo_root,
            manifest_path=manifest_path,
            runner=runner,
        )
        if active_coverage is None:
            raise ShipError("scope disposition requires a readable coverage artifact")
    followup = FollowupIssue(number="", url="")
    if disposition == "proceed-partial":
        if not repo or not tracking_issue_number.isdigit():
            raise ShipError("proceed-partial requires --repo and --tracking-issue")
        existing = _existing_matching_followup(tmpdir, active_coverage.fingerprint)
        if existing is not None:
            followup = existing
        else:
            followup = _create_followup_issue(
                tmpdir=tmpdir,
                repo=repo,
                tracking_issue_number=tracking_issue_number,
                coverage=active_coverage,
            )
            _append_cross_links(
                tmpdir=tmpdir,
                repo=repo,
                tracking_issue_number=tracking_issue_number,
                followup=followup,
            )
            _add_block_relation(
                tmpdir=tmpdir,
                repo=repo,
                tracking_issue_number=tracking_issue_number,
                followup=followup,
            )
    record = DispositionRecord(
        disposition=disposition,
        fingerprint=active_coverage.fingerprint,
        followup_issue_number=followup.number,
        followup_issue_url=followup.url,
        coverage_file=active_coverage.coverage_file,
    )
    _write_scope_run_log(
        tmpdir=tmpdir, run_id=run_id, record=record, coverage=active_coverage
    )
    larch_io.trusted_atomic_write(
        disposition_path(tmpdir), _json_text(asdict(record)), root=tmpdir
    )
    return record


def validate_disposition_for_ship(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> ValidationResult:
    effective_manifest = resolve_implement_manifest(tmpdir, manifest_path)
    gate_relevant = is_pr_mutation_gate_relevant(
        tmpdir=tmpdir, manifest_path=effective_manifest
    )
    try:
        coverage = load_live_coverage(
            tmpdir=tmpdir,
            repo_root=repo_root,
            manifest_path=effective_manifest,
            runner=runner,
        )
        if coverage is None:
            coverage = compute_and_write_coverage(
                tmpdir=tmpdir,
                repo_root=repo_root,
                manifest_path=effective_manifest,
                runner=runner,
            )
    except ShipError as exc:
        reason = (
            "scope-disposition-stale"
            if "does not match live repository inputs" in str(exc)
            and _artifact_present(disposition_path(tmpdir))
            else f"coverage-recompute-failed: {_safe_line(exc)}"
        )
        return ValidationResult(
            ok=False,
            required=gate_relevant or reason == "scope-disposition-stale",
            reason=reason,
        )
    try:
        record = load_disposition(tmpdir, coverage=coverage)
    except ShipError as exc:
        reason = (
            "scope-disposition-stale"
            if "does not match trusted coverage" in str(exc)
            else f"scope-disposition-invalid: {_safe_line(exc)}"
        )
        return ValidationResult(
            ok=False, required=True, reason=reason, coverage=coverage
        )
    if not coverage.disposition_required:
        return ValidationResult(ok=True, required=False, coverage=coverage)
    if record is None:
        return ValidationResult(
            ok=False,
            required=True,
            reason="scope-disposition-missing",
            coverage=coverage,
        )
    if record.disposition == "bail-rescope":
        return ValidationResult(
            ok=False,
            required=True,
            reason="scope-disposition-bail-rescope",
            coverage=coverage,
            disposition=record,
        )
    return ValidationResult(
        ok=True, required=True, coverage=coverage, disposition=record
    )


def require_valid_disposition_for_ship(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> None:
    result = validate_disposition_for_ship(
        tmpdir=tmpdir,
        repo_root=repo_root,
        manifest_path=manifest_path,
        runner=runner,
    )
    if not result.ok:
        raise NeedsUserInput(config.NEEDS_USER_SCOPE_DISPOSITION)


def invalidate_stale_disposition(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> ValidationResult:
    result = validate_disposition_for_ship(
        tmpdir=tmpdir,
        repo_root=repo_root,
        manifest_path=manifest_path,
        runner=runner,
    )
    if result.reason == "scope-disposition-stale":
        with contextlib.suppress(OSError):
            disposition_path(tmpdir).unlink()
    return result


def _emit_coverage(coverage: PlanCoverage) -> None:
    for key, value in (
        ("PLAN_COVERAGE_TOTAL", coverage.total),
        ("PLAN_COVERAGE_TOUCHED", coverage.touched),
        ("PLAN_COVERAGE_UNTOUCHED", coverage.untouched),
        ("PLAN_COVERAGE_UNTOUCHED_PERCENT", coverage.untouched_percent),
        ("PLAN_COVERAGE_BAND", coverage.band),
        ("PLAN_COVERAGE_FILE", coverage.coverage_file),
        ("PLAN_COVERAGE_UNTOUCHED_FILE", coverage.untouched_file),
        ("TODOS_LEFT_COUNT", coverage.todos_left_count),
        ("TODOS_LEFT_FILE", coverage.todos_file),
        (
            "PLAN_COVERAGE_DISPOSITION_REQUIRED",
            str(coverage.disposition_required).lower(),
        ),
        ("PLAN_FIDELITY_FORCED", str(coverage.plan_fidelity_forced).lower()),
        ("PLAN_COVERAGE_FINGERPRINT", coverage.fingerprint),
    ):
        logging_util.emit_kv(key=key, value=str(value))


def scope_disposition_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement scope-disposition")
    _ = parser.add_argument(
        "action",
        choices=(
            "compute",
            "record",
            "validate-ship",
            "invalidate-if-stale",
            "render-deferred-inventory",
        ),
    )
    _ = parser.add_argument(
        "--tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    )
    _ = parser.add_argument("--repo-root", default="")
    _ = parser.add_argument("--plan-file", default="")
    _ = parser.add_argument("--manifest-path", default="")
    _ = parser.add_argument(
        "--disposition",
        choices=("proceed-partial", "bail-rescope"),
        default="proceed-partial",
    )
    _ = parser.add_argument("--repo", default="")
    _ = parser.add_argument("--tracking-issue", default="")
    _ = parser.add_argument("--run-id", default="")
    args = parser.parse_args(argv)
    raw_tmpdir = str(args.tmpdir)
    tmpdir = Path(raw_tmpdir) if raw_tmpdir else Path()
    if not raw_tmpdir or not tmpdir.is_dir():
        print("implement scope-disposition: --tmpdir is required", file=sys.stderr)
        return config.EXIT_USAGE
    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    )
    manifest = Path(args.manifest_path) if args.manifest_path else None
    plan_file = Path(args.plan_file) if args.plan_file else None
    try:
        if args.action == "compute":
            coverage = compute_and_write_coverage(
                tmpdir=tmpdir,
                repo_root=repo_root,
                plan_file=plan_file,
                manifest_path=manifest,
            )
            _emit_coverage(coverage)
            return config.EXIT_OK
        if args.action == "record":
            record = record_disposition(
                tmpdir=tmpdir,
                disposition=cast("Disposition", args.disposition),
                repo_root=repo_root,
                manifest_path=manifest,
                repo=args.repo,
                tracking_issue_number=args.tracking_issue,
                run_id=args.run_id,
            )
            logging_util.emit_kv(key="SCOPE_DISPOSITION_RECORDED", value="true")
            logging_util.emit_kv(key="SCOPE_DISPOSITION", value=record.disposition)
            if record.followup_issue_number:
                logging_util.emit_kv(
                    key="FOLLOWUP_ISSUE_NUMBER", value=record.followup_issue_number
                )
                logging_util.emit_kv(
                    key="FOLLOWUP_ISSUE_URL", value=record.followup_issue_url
                )
            return config.EXIT_OK
        if args.action == "render-deferred-inventory":
            _ = sys.stdout.write(
                disposition_deferred_inventory(tmpdir, repo_root=repo_root)
            )
            return config.EXIT_OK
        result = (
            invalidate_stale_disposition(
                tmpdir=tmpdir, repo_root=repo_root, manifest_path=manifest
            )
            if args.action == "invalidate-if-stale"
            else validate_disposition_for_ship(
                tmpdir=tmpdir, repo_root=repo_root, manifest_path=manifest
            )
        )
        if result.coverage is not None:
            _emit_coverage(result.coverage)
        logging_util.emit_kv(
            key="SCOPE_DISPOSITION_VALID", value=str(result.ok).lower()
        )
        logging_util.emit_kv(
            key="SCOPE_DISPOSITION_REQUIRED", value=str(result.required).lower()
        )
        if result.reason:
            logging_util.emit_kv(key="SCOPE_DISPOSITION_REASON", value=result.reason)
        return config.EXIT_OK if result.ok else config.EXIT_NEEDS_USER_INPUT
    except (OSError, ShipError) as exc:
        print(f"implement scope-disposition: {_safe_line(exc)}", file=sys.stderr)
        return config.EXIT_STALLED
