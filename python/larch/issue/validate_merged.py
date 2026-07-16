"""Validate recent first-parent merges for possible unfiled bugs.

The finder/refuter parser is deliberately shared with :mod:`analyze_bugs`.
That module owns filed-bug verification; this module owns merge selection,
durable state, reporting, and the public CLI surface.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, cast

from larch.core import config
from larch.issue import analyze_bugs as funnel

DEFAULT_MAX_MERGES: Final = 20
STATE_SCHEMA_VERSION: Final = 1
STATE_RELPATH: Final = config.VALIDATE_MERGED_STATE_RELPATH


class ValidateMergedError(RuntimeError):
    """A fail-closed merge-validation error."""


@dataclass(frozen=True)
class ValidateMergedState:
    schema_version: int
    repo: str
    last_successful_tip: str
    completed_at: str
    merge_watermark: str
    pending_merge_shas: tuple[str, ...]
    unresolved_candidates: tuple[dict[str, str], ...]


def _fail(message: str) -> int:
    print(f"validate-merged: {message}", file=sys.stderr)
    return 2


def _emit(rows: Mapping[str, object]) -> None:
    for key, value in rows.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif isinstance(value, (list, tuple, dict)):
            rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            rendered = str(value)
        print(f"{key}={rendered}")


def _full_sha(value: object, *, label: str) -> str:
    if not isinstance(value, str) or funnel.FULL_SHA_RE.fullmatch(value) is None:
        raise ValidateMergedError(f"{label} must be a full 40-character lowercase SHA")
    return value


def _timestamp(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not funnel.SWEEP_TIMESTAMP_RE.fullmatch(value):
        raise ValidateMergedError(f"{label} must be an ISO-8601 UTC timestamp ending in Z")
    return value


def state_path(root: Path) -> Path:
    return root.expanduser().resolve() / STATE_RELPATH


def _candidate_from_raw(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ValidateMergedError("unresolved candidate has unexpected fields")
    typed = cast("dict[str, object]", raw)
    if set(typed) != {
        "merge_sha", "file", "symbol", "description", "severity", "confidence"
    }:
        raise ValidateMergedError("unresolved candidate has unexpected fields")
    merge_sha = _full_sha(typed["merge_sha"], label="candidate merge_sha")
    fields = {key: value for key, value in typed.items() if key != "merge_sha"}
    if not all(isinstance(value, str) and value for value in fields.values()):
        raise ValidateMergedError("unresolved candidate fields must be non-empty strings")
    return {"merge_sha": merge_sha, **cast("dict[str, str]", fields)}


def load_state(path: Path, *, repo: str) -> ValidateMergedState | None:
    """Read only a complete, repo-matching committed marker."""
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidateMergedError(f"malformed committed state marker: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValidateMergedError("committed state marker has unexpected keys")
    data = cast("dict[str, object]", raw)
    if set(data) != {
        "schema_version", "repo", "last_successful_tip", "completed_at",
        "merge_watermark", "pending_merge_shas", "unresolved_candidates",
    }:
        raise ValidateMergedError("committed state marker has unexpected keys")
    if data["schema_version"] != STATE_SCHEMA_VERSION or data["repo"] != repo:
        raise ValidateMergedError("committed state marker has an unsupported schema or foreign repository")
    pending_raw = data["pending_merge_shas"]
    candidates_raw = data["unresolved_candidates"]
    if not isinstance(pending_raw, list) or not isinstance(candidates_raw, list):
        raise ValidateMergedError("committed state marker has malformed arrays")
    pending_values = cast("list[object]", pending_raw)
    candidate_values = cast("list[object]", candidates_raw)
    pending = tuple(_full_sha(item, label="pending merge SHA") for item in pending_values)
    if len(set(pending)) != len(pending):
        raise ValidateMergedError("committed state marker has duplicate pending merge SHAs")
    candidates = tuple(_candidate_from_raw(item) for item in candidate_values)
    return ValidateMergedState(
        schema_version=STATE_SCHEMA_VERSION,
        repo=repo,
        last_successful_tip=_full_sha(data["last_successful_tip"], label="last_successful_tip"),
        completed_at=_timestamp(data["completed_at"], label="completed_at"),
        merge_watermark=_full_sha(data["merge_watermark"], label="merge_watermark"),
        pending_merge_shas=pending,
        unresolved_candidates=candidates,
    )


def write_state(path: Path, state: ValidateMergedState) -> None:
    if state.schema_version != STATE_SCHEMA_VERSION:
        raise ValidateMergedError("refusing to write an unsupported state schema")
    if len(set(state.pending_merge_shas)) != len(state.pending_merge_shas):
        raise ValidateMergedError("refusing to write duplicate pending merge SHAs")
    payload = asdict(state)
    _ = path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _local_funnel_state(run_dir: Path, state: ValidateMergedState | None) -> Path:
    """Materialize only the merge frontier used by the shared low-level funnel."""
    _ = run_dir.mkdir(parents=True, exist_ok=True)
    ledger = run_dir / "validate-merged-ledger.jsonl"
    if state is None:
        return ledger
    funnel.write_sweep_state(
        funnel.sweep_state_path(ledger),
        funnel.SweepState(
            last_sweep_sha=state.merge_watermark,
            last_sweep_at=state.completed_at,
            schema_version=funnel.SWEEP_SCHEMA_VERSION,
            pending_shas=state.pending_merge_shas,
        ),
    )
    return ledger


def _resolve_repo(explicit: str) -> str:
    try:
        return funnel.resolve_repo(funnel.workflow_runner(), explicit)
    except funnel.AnalyzeBugsError as exc:
        raise ValidateMergedError(str(exc)) from exc


def prepare(*, root: Path, run_dir: Path, repo: str, max_merges: int) -> dict[str, object]:
    if max_merges <= 0:
        raise ValidateMergedError("--max-merges must be a positive integer")
    durable = load_state(state_path(root), repo=repo)
    ledger = _local_funnel_state(run_dir, durable)
    try:
        payload = funnel.sweep_prepare(
            runner=funnel.workflow_runner(), run_dir=run_dir, ledger_path=ledger, repo=repo,
            sweep_max=max_merges,
        )
    except funnel.AnalyzeBugsError as exc:
        raise ValidateMergedError(str(exc)) from exc
    payload["STATE_PATH"] = str(state_path(root))
    payload["STATE_SOURCE"] = "committed" if durable else "first-run-48-hours"
    return payload


def _artifact(run_dir: Path) -> funnel.SweepValidatedArtifact:
    try:
        validated = funnel.validated_merge_artifact(run_dir=run_dir)
    except funnel.AnalyzeBugsError as exc:
        raise ValidateMergedError(str(exc)) from exc
    if validated is None:
        raise ValidateMergedError("validated merge result is missing")
    return validated[0]


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def report(*, root: Path, run_dir: Path, repo: str) -> tuple[str, ValidateMergedState]:
    artifact = _artifact(run_dir)
    current = load_state(state_path(root), repo=repo)
    candidates = tuple(
        {
            "merge_sha": candidate.merge_sha,
            "file": candidate.file,
            "symbol": candidate.symbol,
            "description": candidate.description,
            "severity": candidate.severity,
            "confidence": candidate.confidence,
        }
        for candidate in artifact.candidates
    )
    # An unresolved candidate survives later validations until it is filed or
    # explicitly dismissed. De-duplicate by its stable evidence identity.
    prior = () if current is None else current.unresolved_candidates
    by_identity = {
        (item["merge_sha"], item["file"], item["symbol"], item["description"]): item
        for item in (*prior, *candidates)
    }
    state = ValidateMergedState(
        schema_version=STATE_SCHEMA_VERSION,
        repo=repo,
        last_successful_tip=artifact.pinned_tip,
        completed_at=_now(),
        merge_watermark=artifact.pinned_tip,
        pending_merge_shas=artifact.pending_shas,
        unresolved_candidates=tuple(by_identity[key] for key in sorted(by_identity)),
    )
    rows = [["Merge", "File", "Symbol", "Severity", "Confidence", "Description"]]
    rows.extend([
        [item["merge_sha"][:12], item["file"], item["symbol"], item["severity"], item["confidence"], item["description"]]
        for item in state.unresolved_candidates
    ])
    table = _markdown_table(rows) if state.unresolved_candidates else "None."
    report_text = "\n".join([
        "# Validate merged changes",
        "",
        "Recent first-parent merges were checked for possible unfiled bugs.",
        "",
        "## Possible unfiled bugs",
        "",
        table,
        "",
        f"Selected merges: {artifact.selected_count}",
        f"Pending merges: {len(state.pending_merge_shas)}",
        f"Unresolved candidates: {len(state.unresolved_candidates)}",
        "",
        "State is ready for publication only after this final report succeeds.",
        "",
    ])
    return report_text, state


def _markdown_table(rows: Sequence[Sequence[str]]) -> str:
    escaped = [[cell.replace("|", "\\|").replace("\n", " ") for cell in row] for row in rows]
    divider = ["---"] * len(escaped[0])
    return "\n".join(
        "| " + " | ".join(row) + " |" for row in [*escaped[:1], divider, *escaped[1:]]
    )


def prepare_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py validate-merged prepare", allow_abbrev=False)
    _ = parser.add_argument("--root", default=".")
    _ = parser.add_argument("--run-dir", required=True)
    _ = parser.add_argument("--repo", default="")
    _ = parser.add_argument("--max-merges", type=int, default=DEFAULT_MAX_MERGES)
    args = parser.parse_args(argv)
    try:
        repo = _resolve_repo(args.repo)
        payload = prepare(root=Path(args.root), run_dir=Path(args.run_dir), repo=repo, max_merges=args.max_merges)
    except ValidateMergedError as exc:
        return _fail(str(exc))
    _emit(payload)
    return 0


def ingest_finder_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py validate-merged ingest-finder", allow_abbrev=False)
    _ = parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    try:
        payload = funnel.sweep_ingest_finder(run_dir=Path(args.run_dir))
    except funnel.AnalyzeBugsError as exc:
        return _fail(str(exc))
    _emit(payload)
    return 0


def ingest_refuter_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py validate-merged ingest-refuter", allow_abbrev=False)
    _ = parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    try:
        payload = funnel.sweep_ingest_refuter(run_dir=Path(args.run_dir))
    except funnel.AnalyzeBugsError as exc:
        return _fail(str(exc))
    _emit(payload)
    return 0


def report_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py validate-merged report", allow_abbrev=False)
    _ = parser.add_argument("--root", default=".")
    _ = parser.add_argument("--run-dir", required=True)
    _ = parser.add_argument("--repo", default="")
    _ = parser.add_argument("--state-output", required=True)
    args = parser.parse_args(argv)
    try:
        repo = _resolve_repo(args.repo)
        text, state = report(root=Path(args.root), run_dir=Path(args.run_dir), repo=repo)
        write_state(Path(args.state_output), state)
    except ValidateMergedError as exc:
        return _fail(str(exc))
    print(text, end="")
    _emit({"STATE_OUTPUT": args.state_output, "STATE_RELPATH": STATE_RELPATH})
    return 0


def write_state_main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="python/cli.py validate-merged write-state", allow_abbrev=False)
    _ = parser.add_argument("--root", default=".")
    _ = parser.add_argument("--repo", required=True)
    _ = parser.add_argument("--state-input", required=True)
    args = parser.parse_args(argv)
    try:
        state = load_state(Path(args.state_input), repo=args.repo)
        if state is None:
            raise ValidateMergedError("state input is missing")
        write_state(state_path(Path(args.root)), state)
    except ValidateMergedError as exc:
        return _fail(str(exc))
    _emit({"STATE_RELPATH": STATE_RELPATH})
    return 0
