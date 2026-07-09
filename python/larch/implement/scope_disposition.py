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
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Mapping

from larch import io as larch_io
from larch.core import config, logging_util, proc
from larch.core.proc import CommandResult, Runner
from larch.errors import NeedsUserInput, ShipError
from larch.issue import issue_wire

CoverageBand = Literal["advisory", "middle", "high"]
Disposition = Literal["proceed-partial", "bail-rescope"]

COVERAGE_JSON = "plan-coverage.json"
COVERAGE_ENV = "plan-coverage.env"
UNTOUCHED_PATHS = "plan-coverage-untouched.txt"
TODOS_LEFT = "plan-coverage-todos-left.txt"
DISPOSITION_JSON = "scope-disposition.json"
DEFERRED_INVENTORY = "deferred-plan-inventory.md"
_MAX_TODO_ITEMS = 20
_MAX_TODO_CHARS = 4000
_MAX_UNTOUCHED_INVENTORY = 80


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


def _read_manifest_todos(manifest_path: Path | None) -> tuple[tuple[str, ...], int]:
    """Return (sanitized_display_items, raw_entry_count)."""
    if manifest_path is None or not manifest_path.is_file():
        return (), 0
    try:
        parsed: object = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return (), 0
    if not isinstance(parsed, dict):
        return (), 0
    raw = cast("Mapping[str, object]", parsed).get("todos_left")
    if not isinstance(raw, list):
        return (), 0
    raw_items = cast("list[object]", raw)
    raw_count = len(raw_items)
    lines: list[str] = []
    budget = _MAX_TODO_CHARS
    for item in raw_items[:_MAX_TODO_ITEMS]:
        line = _safe_line(item)
        if not line:
            continue
        if len(line) + 1 > budget:
            break
        lines.append(line)
        budget -= len(line) + 1
    if len(raw_items) > len(lines):
        lines.append(f"… {len(raw_items) - len(lines)} more todo item(s) omitted")
    return tuple(lines), raw_count


def _git(runner: Runner, argv: Sequence[str], *, cwd: Path) -> CommandResult:
    return runner.run(["git", *argv], cwd=str(cwd))


def _git_stdout(runner: Runner, argv: Sequence[str], *, cwd: Path) -> str:
    result = _git(runner, argv, cwd=cwd)
    if result.returncode != 0:
        raise ShipError(f"git {' '.join(argv)} failed")
    return result.stdout.strip()


def _baseline_sha(*, tmpdir: Path, repo_root: Path, runner: Runner) -> str:
    _ = repo_root
    baseline_file = tmpdir / "step2-baseline.txt"
    if baseline_file.is_file() and not baseline_file.is_symlink():
        raw = baseline_file.read_text(encoding="utf-8", errors="replace").strip()
        if raw:
            return raw
    raise ShipError("step2 baseline missing or unreadable")


def _porcelain_paths_z(stdout: str) -> set[str]:
    items = stdout.split("\0")
    paths: set[str] = set()
    idx = 0
    while idx < len(items):
        rec = items[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2]
        rel = rec[3:]
        if rel:
            paths.add(rel)
        if ("R" in status or "C" in status) and idx < len(items):
            old_rel = items[idx]
            idx += 1
            if old_rel:
                paths.add(old_rel)
    return paths


def touched_paths_since_baseline(*, tmpdir: Path, repo_root: Path, runner: Runner = proc) -> tuple[str, ...]:
    baseline = _baseline_sha(tmpdir=tmpdir, repo_root=repo_root, runner=runner)
    touched: set[str] = set()
    diff = _git(runner, ["diff", "--name-only", f"{baseline}..HEAD"], cwd=repo_root)
    if diff.returncode != 0:
        raise ShipError("baseline-to-HEAD diff failed")
    touched.update(line for line in diff.stdout.splitlines() if line)
    status = _git(runner, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=repo_root)
    if status.returncode != 0:
        raise ShipError("working-tree status failed")
    touched.update(_porcelain_paths_z(status.stdout))
    return tuple(sorted(touched))


def _firm_plan_paths(plan_file: Path) -> tuple[str, ...]:
    try:
        plan_text = plan_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ShipError(f"plan file unreadable: {plan_file}: {exc}") from exc
    return tuple(dict.fromkeys(issue_wire.extract_scope_paths(plan_text=plan_text, use_fallback=False, include_optional=False)))


def _coverage_band(*, total: int, untouched: int) -> CoverageBand:
    percent = int((untouched * 100) / total) if total > 0 else 0
    if total > 0 and (untouched >= config.PLAN_COVERAGE_HIGH_UNTOUCHED_COUNT or percent >= config.PLAN_COVERAGE_HIGH_UNTOUCHED_PERCENT):
        return "high"
    if total > 0 and (untouched >= config.PLAN_COVERAGE_MIDDLE_UNTOUCHED_COUNT or percent >= config.PLAN_COVERAGE_MIDDLE_UNTOUCHED_PERCENT):
        return "middle"
    return "advisory"


def _fingerprint(*, plan_paths: tuple[str, ...], touched_paths: tuple[str, ...], todos_left: tuple[str, ...]) -> str:
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
    touched = touched_paths_since_baseline(tmpdir=tmpdir, repo_root=repo_root, runner=runner)
    touched_set = set(touched)
    untouched_paths = tuple(path for path in plan_paths if path not in touched_set)
    total = len(plan_paths)
    untouched = len(untouched_paths)
    touched_count = total - untouched
    percent = int((untouched * 100) / total) if total > 0 else 0
    band = _coverage_band(total=total, untouched=untouched)
    todos_left, raw_todos_count = _read_manifest_todos(manifest_path)
    fingerprint = _fingerprint(plan_paths=plan_paths, touched_paths=touched, todos_left=todos_left)
    return PlanCoverage(
        total=total,
        touched=touched_count,
        untouched=untouched,
        untouched_percent=percent,
        band=band,
        plan_paths=plan_paths,
        touched_paths=touched,
        untouched_paths=untouched_paths,
        todos_left_count=raw_todos_count,
        todos_left=todos_left,
        fingerprint=fingerprint,
        disposition_required=band == "high" or raw_todos_count > 0,
        plan_fidelity_forced=band in {"middle", "high"},
        coverage_file=str(coverage_path(tmpdir)),
        untouched_file=str(tmpdir / UNTOUCHED_PATHS),
        todos_file=str(tmpdir / TODOS_LEFT),
    )


def write_coverage(coverage: PlanCoverage, *, tmpdir: Path) -> None:
    untouched_file = Path(coverage.untouched_file)
    todos_file = Path(coverage.todos_file)
    larch_io.atomic_write(untouched_file, "".join(f"{path}\n" for path in coverage.untouched_paths))
    larch_io.atomic_write(todos_file, "".join(f"- {line}\n" for line in coverage.todos_left))
    larch_io.atomic_write(coverage_path(tmpdir), _json_text(asdict(coverage)))
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
        ("PLAN_COVERAGE_DISPOSITION_REQUIRED", str(coverage.disposition_required).lower()),
        ("PLAN_FIDELITY_FORCED", str(coverage.plan_fidelity_forced).lower()),
    ]
    larch_io.atomic_write(coverage_env_path(tmpdir), larch_io.format_kvs(rows))


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


def load_coverage(tmpdir: Path) -> PlanCoverage | None:
    path = coverage_path(tmpdir)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    data = cast("Mapping[str, object]", parsed)
    try:
        return PlanCoverage(
            total=_as_int(data.get("total")),
            touched=_as_int(data.get("touched")),
            untouched=_as_int(data.get("untouched")),
            untouched_percent=_as_int(data.get("untouched_percent")),
            band=cast("CoverageBand", str(data.get("band") or "advisory")),
            plan_paths=tuple(str(item) for item in cast("Sequence[object]", data.get("plan_paths") or ())),
            touched_paths=tuple(str(item) for item in cast("Sequence[object]", data.get("touched_paths") or ())),
            untouched_paths=tuple(str(item) for item in cast("Sequence[object]", data.get("untouched_paths") or ())),
            todos_left_count=_as_int(data.get("todos_left_count")),
            todos_left=tuple(str(item) for item in cast("Sequence[object]", data.get("todos_left") or ())),
            fingerprint=str(data.get("fingerprint") or ""),
            disposition_required=_as_bool(data.get("disposition_required")),
            plan_fidelity_forced=_as_bool(data.get("plan_fidelity_forced")),
            coverage_file=str(data.get("coverage_file") or path),
            untouched_file=str(data.get("untouched_file") or tmpdir / UNTOUCHED_PATHS),
            todos_file=str(data.get("todos_file") or tmpdir / TODOS_LEFT),
        )
    except (TypeError, ValueError):
        return None


def load_disposition(tmpdir: Path) -> DispositionRecord | None:
    path = disposition_path(tmpdir)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    data = cast("Mapping[str, object]", parsed)
    disposition = str(data.get("disposition") or "")
    if disposition not in {"proceed-partial", "bail-rescope"}:
        return None
    return DispositionRecord(
        disposition=cast("Disposition", disposition),
        fingerprint=str(data.get("fingerprint") or ""),
        followup_issue_number=str(data.get("followup_issue_number") or ""),
        followup_issue_url=str(data.get("followup_issue_url") or ""),
        coverage_file=str(data.get("coverage_file") or ""),
    )


def render_deferred_inventory(coverage: PlanCoverage, disposition: DispositionRecord | None = None) -> str:
    if not coverage.untouched_paths and not coverage.todos_left:
        return ""
    lines = ["## Deferred plan inventory", ""]
    if disposition and disposition.followup_issue_number:
        lines.append(f"Follow-up issue: #{disposition.followup_issue_number}")
        lines.append("")
    if coverage.untouched_paths:
        lines.append("Untouched firm plan paths:")
        lines.extend(f"- `{path}`" for path in coverage.untouched_paths[:_MAX_UNTOUCHED_INVENTORY])
        if len(coverage.untouched_paths) > _MAX_UNTOUCHED_INVENTORY:
            lines.append(f"- … {len(coverage.untouched_paths) - _MAX_UNTOUCHED_INVENTORY} more path(s)")
        lines.append("")
    if coverage.todos_left:
        lines.append("Manifest todos left:")
        lines.extend(f"- {line}" for line in coverage.todos_left)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def disposition_link_kind(tmpdir: Path | None = None) -> str:
    raw_tmpdir = _optional_tmpdir(tmpdir)
    record = load_disposition(raw_tmpdir) if raw_tmpdir is not None else None
    return "part-of" if record and record.disposition == "proceed-partial" else "closes"


def disposition_deferred_inventory(tmpdir: Path | None = None) -> str:
    raw_tmpdir = _optional_tmpdir(tmpdir)
    if raw_tmpdir is None:
        return ""
    coverage = load_coverage(raw_tmpdir)
    if coverage is None:
        return ""
    return render_deferred_inventory(coverage, load_disposition(raw_tmpdir))


def _optional_tmpdir(tmpdir: Path | None) -> Path | None:
    if tmpdir is not None:
        return tmpdir
    raw = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    return Path(raw) if raw else None


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


def _require_cli_success(result: CommandResult, *, label: str) -> dict[str, str]:
    fields = _parse_cli_kv(result.stdout)
    failure_keys = {key for key, value in fields.items() if key.endswith("FAILED") and value == "true"}
    if result.returncode != 0 or failure_keys:
        detail = fields.get("ERROR") or result.stderr or result.stdout or f"{label} failed"
        raise ShipError(_safe_line(detail, limit=500))
    return fields


def _create_followup_issue(*, tmpdir: Path, repo: str, tracking_issue_number: str, coverage: PlanCoverage) -> FollowupIssue:
    body = tmpdir / "scope-disposition-followup-body.md"
    larch_io.atomic_write(
        body,
        "# Deferred /implement plan inventory\n\n"
        f"Parent tracking issue: #{tracking_issue_number}\n\n"
        + render_deferred_inventory(coverage),
    )
    created = _run_cli([
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
    ])
    fields = _require_cli_success(created, label="issue create-one")
    number = fields.get("ISSUE_NUMBER", "")
    url = fields.get("ISSUE_URL", "")
    if not number.isdigit() or not url:
        raise ShipError("issue create-one did not return ISSUE_NUMBER and ISSUE_URL")
    return FollowupIssue(number=number, url=url)


def _append_cross_links(*, tmpdir: Path, repo: str, tracking_issue_number: str, followup: FollowupIssue) -> None:
    parent_body = tmpdir / "scope-disposition-parent-link.md"
    child_body = tmpdir / "scope-disposition-followup-link.md"
    larch_io.atomic_write(parent_body, f"Partial-scope disposition recorded. Deferred plan work is tracked in #{followup.number}: {followup.url}\n")
    larch_io.atomic_write(child_body, f"Filed from partial-scope disposition on parent tracking issue #{tracking_issue_number}.\n")
    for issue, body in ((tracking_issue_number, parent_body), (followup.number, child_body)):
        result = _run_cli(["tracking-issue", "append-comment", "--issue", issue, "--body-file", str(body), "--repo", repo])
        _ = _require_cli_success(result, label="tracking-issue append-comment")


def _add_block_relation(*, repo: str, tracking_issue_number: str, followup: FollowupIssue) -> None:
    result = _run_cli([
        "issue",
        "add-blocked-by",
        "--client-issue",
        tracking_issue_number,
        "--blocker-issue",
        followup.number,
        "--repo",
        repo,
    ])
    _ = _require_cli_success(result, label="issue add-blocked-by")


def _write_scope_run_log(*, tmpdir: Path, run_id: str, record: DispositionRecord, coverage: PlanCoverage) -> None:
    if not run_id:
        return
    payload = tmpdir / "scope-disposition-run-log.json"
    larch_io.atomic_write(
        payload,
        _json_text({
            "coverage_fingerprint": coverage.fingerprint,
            "disposition": record.disposition,
            "followup_issue_number": record.followup_issue_number,
            "followup_issue_url": record.followup_issue_url,
            "todos_left_count": coverage.todos_left_count,
            "untouched_count": coverage.untouched,
            "total": coverage.total,
        }),
    )
    result = _run_cli([
        "run-log",
        "write",
        "--log-root",
        str(tmpdir / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        run_id,
        "--batch",
        "scope-disposition",
        "--input-file",
        str(payload),
    ])
    _ = _require_cli_success(result, label="run-log write scope-disposition")


def record_disposition(  # noqa: PLR0913
    *,
    tmpdir: Path,
    disposition: Disposition,
    repo: str = "",
    tracking_issue_number: str = "",
    run_id: str = "",
    coverage: PlanCoverage | None = None,
) -> DispositionRecord:
    active_coverage = coverage or load_coverage(tmpdir)
    if active_coverage is None:
        raise ShipError("scope disposition requires a readable coverage artifact")
    followup = FollowupIssue(number="", url="")
    if disposition == "proceed-partial":
        if not repo or not tracking_issue_number.isdigit():
            raise ShipError("proceed-partial requires --repo and --tracking-issue")
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
        _add_block_relation(repo=repo, tracking_issue_number=tracking_issue_number, followup=followup)
    record = DispositionRecord(
        disposition=disposition,
        fingerprint=active_coverage.fingerprint,
        followup_issue_number=followup.number,
        followup_issue_url=followup.url,
        coverage_file=active_coverage.coverage_file,
    )
    _write_scope_run_log(tmpdir=tmpdir, run_id=run_id, record=record, coverage=active_coverage)
    larch_io.atomic_write(disposition_path(tmpdir), _json_text(asdict(record)))
    return record


def validate_disposition_for_ship(
    *,
    tmpdir: Path,
    repo_root: Path,
    manifest_path: Path | None = None,
    runner: Runner = proc,
) -> ValidationResult:
    persisted_coverage = load_coverage(tmpdir)
    try:
        coverage = compute_and_write_coverage(
            tmpdir=tmpdir,
            repo_root=repo_root,
            manifest_path=manifest_path,
            runner=runner,
        )
    except ShipError as exc:
        if persisted_coverage is not None and not persisted_coverage.disposition_required:
            return ValidationResult(
                ok=True,
                required=False,
                reason=f"coverage-recompute-failed-advisory: {_safe_line(exc)}",
                coverage=persisted_coverage,
            )
        return ValidationResult(
            ok=False,
            required=True,
            reason=f"coverage-recompute-failed: {_safe_line(exc)}",
            coverage=persisted_coverage,
        )
    record = load_disposition(tmpdir)
    if record is not None and record.fingerprint != coverage.fingerprint:
        if record.disposition == "proceed-partial":
            return ValidationResult(
                ok=False,
                required=True,
                reason="scope-disposition-stale",
                coverage=coverage,
                disposition=record,
            )
        with contextlib.suppress(OSError):
            disposition_path(tmpdir).unlink()
        return ValidationResult(
            ok=not coverage.disposition_required,
            required=coverage.disposition_required,
            reason="scope-disposition-stale",
            coverage=coverage,
            disposition=record,
        )
    if not coverage.disposition_required:
        return ValidationResult(ok=True, required=False, coverage=coverage)
    if record is None:
        return ValidationResult(ok=False, required=True, reason="scope-disposition-missing", coverage=coverage)
    if record.disposition == "bail-rescope":
        return ValidationResult(ok=False, required=True, reason="scope-disposition-bail-rescope", coverage=coverage, disposition=record)
    return ValidationResult(ok=True, required=True, coverage=coverage, disposition=record)


def require_valid_disposition_for_ship(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None, runner: Runner = proc) -> None:
    result = validate_disposition_for_ship(
        tmpdir=tmpdir,
        repo_root=repo_root,
        manifest_path=manifest_path,
        runner=runner,
    )
    if not result.ok:
        raise NeedsUserInput(config.NEEDS_USER_SCOPE_DISPOSITION)


def invalidate_stale_disposition(*, tmpdir: Path, repo_root: Path, manifest_path: Path | None = None, runner: Runner = proc) -> ValidationResult:
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
        ("PLAN_COVERAGE_DISPOSITION_REQUIRED", str(coverage.disposition_required).lower()),
        ("PLAN_FIDELITY_FORCED", str(coverage.plan_fidelity_forced).lower()),
        ("PLAN_COVERAGE_FINGERPRINT", coverage.fingerprint),
    ):
        logging_util.emit_kv(key=key, value=str(value))


def scope_disposition_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement scope-disposition")
    _ = parser.add_argument("action", choices=("compute", "record", "validate-ship", "invalidate-if-stale", "render-deferred-inventory"))
    _ = parser.add_argument("--tmpdir", default=os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""))
    _ = parser.add_argument("--repo-root", default="")
    _ = parser.add_argument("--plan-file", default="")
    _ = parser.add_argument("--manifest-path", default="")
    _ = parser.add_argument("--disposition", choices=("proceed-partial", "bail-rescope"), default="proceed-partial")
    _ = parser.add_argument("--repo", default="")
    _ = parser.add_argument("--tracking-issue", default="")
    _ = parser.add_argument("--run-id", default="")
    args = parser.parse_args(argv)
    tmpdir = Path(args.tmpdir) if args.tmpdir else Path()
    if not args.tmpdir or not tmpdir.is_dir():
        print("implement scope-disposition: --tmpdir is required", file=sys.stderr)
        return config.EXIT_USAGE
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    manifest = Path(args.manifest_path) if args.manifest_path else None
    plan_file = Path(args.plan_file) if args.plan_file else None
    try:
        if args.action == "compute":
            coverage = compute_and_write_coverage(tmpdir=tmpdir, repo_root=repo_root, plan_file=plan_file, manifest_path=manifest)
            _emit_coverage(coverage)
            return config.EXIT_OK
        if args.action == "record":
            record = record_disposition(
                tmpdir=tmpdir,
                disposition=cast("Disposition", args.disposition),
                repo=args.repo,
                tracking_issue_number=args.tracking_issue,
                run_id=args.run_id,
            )
            logging_util.emit_kv(key="SCOPE_DISPOSITION_RECORDED", value="true")
            logging_util.emit_kv(key="SCOPE_DISPOSITION", value=record.disposition)
            if record.followup_issue_number:
                logging_util.emit_kv(key="FOLLOWUP_ISSUE_NUMBER", value=record.followup_issue_number)
                logging_util.emit_kv(key="FOLLOWUP_ISSUE_URL", value=record.followup_issue_url)
            return config.EXIT_OK
        if args.action == "render-deferred-inventory":
            _ = sys.stdout.write(disposition_deferred_inventory(tmpdir))
            return config.EXIT_OK
        result = (
            invalidate_stale_disposition(tmpdir=tmpdir, repo_root=repo_root, manifest_path=manifest)
            if args.action == "invalidate-if-stale"
            else validate_disposition_for_ship(tmpdir=tmpdir, repo_root=repo_root, manifest_path=manifest)
        )
        if result.coverage is not None:
            _emit_coverage(result.coverage)
        logging_util.emit_kv(key="SCOPE_DISPOSITION_VALID", value=str(result.ok).lower())
        logging_util.emit_kv(key="SCOPE_DISPOSITION_REQUIRED", value=str(result.required).lower())
        if result.reason:
            logging_util.emit_kv(key="SCOPE_DISPOSITION_REASON", value=result.reason)
        return config.EXIT_OK if result.ok else config.EXIT_NEEDS_USER_INPUT
    except (OSError, ShipError) as exc:
        print(f"implement scope-disposition: {_safe_line(exc)}", file=sys.stderr)
        return config.EXIT_STALLED
