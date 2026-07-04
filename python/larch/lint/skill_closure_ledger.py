"""Report per-merge skill-closure baseline deltas from git history."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.core.proc import ProcRunner
from larch.errors import ShipError
from larch.git import git
from larch.lint.lint_skill_closure_growth import BASELINE_RELPATH, TOOL_FAILURE_EXIT

_PR_SUFFIX_RE = re.compile(r"\(#(?P<number>[0-9]+)\)$")


class LedgerError(ValueError):
    """Raised when the historical baseline ledger cannot be built."""


@dataclass(frozen=True)
class TargetValue:
    target: str
    closure_estimated_tokens: int


@dataclass(frozen=True)
class BaselineSnapshot:
    values: tuple[TargetValue, ...]


@dataclass(frozen=True)
class TargetDelta:
    commit: str
    pr: str
    subject: str
    target: str
    previous: int | None
    current: int
    delta: int | None
    is_raise: bool


@dataclass(frozen=True)
class BaselineRevision:
    commit: git.PathCommit
    snapshot: BaselineSnapshot
    deltas: tuple[TargetDelta, ...]


@dataclass(frozen=True)
class SummaryRow:
    target: str
    start: int
    end: int
    delta: int
    raises: int
    largest_raise_commit: str
    largest_raise_delta: int | None


@dataclass
class _SummaryAccumulator:
    start: int
    current: int
    delta: int = 0
    raises: int = 0
    largest_raise_commit: str = ""
    largest_raise_delta: int | None = None

    def advance(self, *, commit: str, current: int) -> None:
        change = current - self.current
        if change == 0:
            return
        self.current = current
        self.delta += change
        if change <= 0:
            return
        self.raises += 1
        if self.largest_raise_delta is None or change > self.largest_raise_delta:
            self.largest_raise_delta = change
            self.largest_raise_commit = commit


def _new_summary_accumulator(*, target_delta: TargetDelta) -> _SummaryAccumulator:
    assert target_delta.previous is not None  # caller only builds an accumulator once previous is known
    acc = _SummaryAccumulator(start=target_delta.previous, current=target_delta.current, delta=target_delta.delta or 0)
    if target_delta.delta is not None and target_delta.delta > 0:
        acc.raises = 1
        acc.largest_raise_commit = target_delta.commit
        acc.largest_raise_delta = target_delta.delta
    return acc


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py skill-closure ledger",
        description=__doc__,
    )
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    range_group = parser.add_mutually_exclusive_group()
    _ = range_group.add_argument("--window", type=_positive_int, help="last N baseline-touching commits")
    _ = range_group.add_argument("--since-tag", help="select baseline-touching commits in TAG..HEAD")
    _ = parser.add_argument("--summary", action="store_true", help="print aggregate rows instead of per-commit rows")
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def _coerce_root(root_text: str) -> Path | None:
    root = Path(root_text).resolve()
    if not root.is_dir():
        print(f"skill-closure ledger: --root is not a directory: {root}", file=sys.stderr)
        return None
    return root


def _parse_pr(subject: str) -> str:
    match = _PR_SUFFIX_RE.search(subject)
    if match is None:
        return ""
    return f"#{match.group('number')}"


def _parse_snapshot(text: str, *, label: str) -> BaselineSnapshot:
    try:
        payload_obj: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{label}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload_obj, list):
        raise LedgerError(f"{label}: expected top-level JSON array")
    payload = cast("list[object]", payload_obj)

    order: list[str] = []
    values_by_target: dict[str, int] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        row = cast("dict[str, object]", item)
        target = row.get("skill")
        tokens = row.get("closure_estimated_tokens")
        if not isinstance(target, str):
            continue
        if isinstance(tokens, float):
            # Keep historical floats skipped rather than inventing integer token values.
            print(
                f"skill-closure ledger: {label}: skipping {target}: "
                "closure_estimated_tokens is not an integer",
                file=sys.stderr,
            )
            continue
        if not isinstance(tokens, int) or isinstance(tokens, bool):
            continue
        if target in values_by_target:
            # Retain last-wins compatibility for duplicate historical rows, but warn.
            print(
                f"skill-closure ledger: {label}: duplicate skill row for {target}; keeping last value",
                file=sys.stderr,
            )
        else:
            order.append(target)
        values_by_target[target] = tokens
    return BaselineSnapshot(
        values=tuple(TargetValue(target, values_by_target[target]) for target in order),
    )


def _load_snapshot(runner: ProcRunner, root: Path, commit: git.PathCommit) -> BaselineSnapshot:
    spec = f"{commit.sha}:{BASELINE_RELPATH.as_posix()}"
    result = git.show_file(runner, spec, cwd=str(root))
    if result.returncode != 0:
        detail = result.stderr.strip() or f"git show exited {result.returncode}"
        raise LedgerError(f"cannot read {BASELINE_RELPATH.as_posix()} at {commit.sha}: {detail}")
    return _parse_snapshot(result.stdout, label=f"{commit.sha}:{BASELINE_RELPATH.as_posix()}")


def _build_revisions(commits: Iterable[git.PathCommit], snapshots: dict[str, BaselineSnapshot]) -> tuple[BaselineRevision, ...]:
    last_values: dict[str, int] = {}
    revisions: list[BaselineRevision] = []
    for commit in commits:
        snapshot = snapshots[commit.sha]
        current_targets = {value.target for value in snapshot.values}
        deltas: list[TargetDelta] = []
        for value in snapshot.values:
            previous = last_values.get(value.target)
            delta = None if previous is None else value.closure_estimated_tokens - previous
            deltas.append(
                TargetDelta(
                    commit=commit.sha,
                    pr=_parse_pr(commit.subject),
                    subject=commit.subject,
                    target=value.target,
                    previous=previous,
                    current=value.closure_estimated_tokens,
                    delta=delta,
                    is_raise=delta is not None and delta > 0,
                ),
            )
            last_values[value.target] = value.closure_estimated_tokens
        for target in tuple(last_values):
            if target not in current_targets:
                del last_values[target]
        revisions.append(BaselineRevision(commit=commit, snapshot=snapshot, deltas=tuple(deltas)))
    return tuple(revisions)


def _load_full_revisions(runner: ProcRunner, root: Path) -> tuple[BaselineRevision, ...]:
    commits = git.log_path_commits(runner, BASELINE_RELPATH.as_posix(), cwd=str(root))
    if not commits:
        raise LedgerError(f"no git history found for {BASELINE_RELPATH.as_posix()}")
    snapshots = {commit.sha: _load_snapshot(runner, root, commit) for commit in commits}
    return _build_revisions(commits, snapshots)


def _since_tag_commits(runner: ProcRunner, root: Path, tag: str) -> tuple[git.PathCommit, ...]:
    try:
        _ = git.rev_parse_verify(runner, f"{tag}^{{commit}}", cwd=str(root))
    except ShipError as exc:
        raise LedgerError(f"--since-tag does not resolve to a commit: {tag}") from exc
    return git.log_path_commits(
        runner,
        BASELINE_RELPATH.as_posix(),
        rev_range=f"{tag}..HEAD",
        cwd=str(root),
    )


def _select_revisions(
    runner: ProcRunner,
    root: Path,
    revisions: tuple[BaselineRevision, ...],
    *,
    window: int | None,
    since_tag: str | None,
) -> tuple[BaselineRevision, ...]:
    if window is not None:
        return revisions[-window:]
    if since_tag is not None:
        selected_shas = {commit.sha for commit in _since_tag_commits(runner, root, since_tag)}
        return tuple(revision for revision in revisions if revision.commit.sha in selected_shas)
    return revisions


def _tsv(text: str) -> str:
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


def _print_detailed(revisions: Iterable[BaselineRevision]) -> None:
    print("commit\tpr\tsubject\ttarget\tprevious\tcurrent\tdelta\traise")
    for revision in revisions:
        for delta in revision.deltas:
            print(
                "\t".join(
                    (
                        delta.commit,
                        delta.pr,
                        _tsv(delta.subject),
                        _tsv(delta.target),
                        _optional_int(delta.previous),
                        str(delta.current),
                        _optional_int(delta.delta),
                        str(delta.is_raise).lower(),
                    ),
                ),
            )


def _summarize(revisions: Iterable[BaselineRevision]) -> tuple[SummaryRow, ...]:
    accumulators: dict[str, _SummaryAccumulator] = {}
    order: list[str] = []
    for revision in revisions:
        snapshot_values = {value.target: value.closure_estimated_tokens for value in revision.snapshot.values}
        for target, accumulator in accumulators.items():
            accumulator.advance(commit=revision.commit.sha, current=snapshot_values.get(target, 0))
        for delta in revision.deltas:
            if delta.delta is None or delta.previous is None:
                continue
            if delta.target not in accumulators:
                order.append(delta.target)
                accumulators[delta.target] = _new_summary_accumulator(target_delta=delta)
    return tuple(
        SummaryRow(
            target=target,
            start=accumulators[target].start,
            end=accumulators[target].current,
            delta=accumulators[target].delta,
            raises=accumulators[target].raises,
            largest_raise_commit=accumulators[target].largest_raise_commit,
            largest_raise_delta=accumulators[target].largest_raise_delta,
        )
        for target in order
    )


def _print_summary(revisions: Iterable[BaselineRevision]) -> None:
    print("target\tstart\tend\tdelta\traises\tlargest_raise_commit\tlargest_raise_delta")
    for row in _summarize(revisions):
        print(
            "\t".join(
                (
                    _tsv(row.target),
                    str(row.start),
                    str(row.end),
                    str(row.delta),
                    str(row.raises),
                    row.largest_raise_commit,
                    _optional_int(row.largest_raise_delta),
                ),
            ),
        )


def ledger_main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        return TOOL_FAILURE_EXIT
    root = _coerce_root(parsed.root)
    if root is None:
        return TOOL_FAILURE_EXIT

    runner = ProcRunner()
    try:
        revisions = _load_full_revisions(runner, root)
        selected = _select_revisions(
            runner,
            root,
            revisions,
            window=parsed.window,
            since_tag=parsed.since_tag,
        )
    except (LedgerError, ShipError) as exc:
        print(f"skill-closure ledger: {exc}", file=sys.stderr)
        return TOOL_FAILURE_EXIT

    if parsed.summary:
        _print_summary(selected)
    else:
        _print_detailed(selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(ledger_main())
