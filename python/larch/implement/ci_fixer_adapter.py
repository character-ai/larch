"""Typed Step 8 CI-fixer adapter and synchronous finalization."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Never

from larch import io as larch_io
from larch.bgjob import adapt, daemon, model
from larch.core import config, external_defaults
from larch.core.proc import run as proc_run
from larch.git import push
from larch.implement import ci_fixer_lane, invariant_evidence
from larch.report.progress_file import resolve_owned_run_id

_HEX_HEAD_RE = re.compile(r"[0-9a-f]{40,64}")
_RUN_ID_RE = re.compile(r"[A-Za-z0-9._-]+")
_ASCII_CONTROL_LIMIT = 32
_ASCII_DELETE = 127
_LINEAGE_FIELD_COUNT = 6


class CiFixerAdapterError(RuntimeError):
    """Operator-bail reason safe for the public machine grammar."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        _ = message
        raise CiFixerAdapterError("invalid-mode")


@dataclass(frozen=True)
class Launch:
    mode: str
    run_id: str
    starting_head: str
    input_fingerprint: str
    tier: str
    attempt: int
    step: str
    lineage: Path

    def rows(self) -> tuple[tuple[str, str], ...]:
        return (
            ("MODE", self.mode),
            ("RUN_ID", self.run_id),
            ("STARTING_HEAD", self.starting_head),
            ("INPUT_FINGERPRINT", self.input_fingerprint),
            ("TIER", self.tier),
            ("ATTEMPT", str(self.attempt)),
            ("STEP", self.step),
            ("LINEAGE", str(self.lineage)),
        )


@dataclass(frozen=True)
class Context:
    tmpdir: Path
    handoff_dir: Path
    bgjob_dir: Path
    repo_root: Path
    repo: str


def _fail(reason: str) -> int:
    safe = reason.replace("\n", " ").replace("\r", " ")
    print("RESULT=operator-bail")
    print(f"REASON={safe}")
    return 0


def _safe_dir(path: Path, *, parent: Path | None = None) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise CiFixerAdapterError("unsafe-tmpdir")
    if parent is not None and path.parent.resolve() != parent.resolve():
        raise CiFixerAdapterError("unsafe-handoff-dir")
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise CiFixerAdapterError("unsafe-handoff-dir")
    return path.resolve()


def _safe_file(path: Path, *, root: Path, reason: str) -> Path:
    try:
        resolved = path.resolve()
        _ = resolved.relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise CiFixerAdapterError(reason) from exc
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise CiFixerAdapterError(reason)
    parent = path.parent
    while parent != root:
        if parent.is_symlink() or not parent.is_dir():
            raise CiFixerAdapterError(reason)
        parent = parent.parent
    return resolved


def _upper_rows(path: Path, *, root: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    safe = _safe_file(path, root=root, reason="invalid-env-file")
    try:
        text = larch_io.read_trusted_text(safe, root=root, reject_cr=True, errors="strict")
    except (OSError, UnicodeError, ValueError) as exc:
        raise CiFixerAdapterError("invalid-env-file") from exc
    rows: dict[str, str] = {}
    for raw in text.splitlines():
        if not raw or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key) is None:
            continue
        if key in rows or any(
            ord(char) < _ASCII_CONTROL_LIMIT or ord(char) == _ASCII_DELETE
            for char in value
        ):
            raise CiFixerAdapterError("invalid-env-file")
        rows[key] = value
    return rows


def _required(rows: dict[str, str], key: str, reason: str) -> str:
    value = rows.get(key, "")
    if not value:
        raise CiFixerAdapterError(reason)
    return value


def _context(tmpdir: Path) -> Context:
    root = _safe_dir(tmpdir)
    handoff = _safe_dir(root / "ci-fixer", parent=root)
    bgjob = _safe_dir(root / "bgjob", parent=root)
    session = _upper_rows(root / "session-env.sh", root=root)
    state = _upper_rows(root / "ship-pr-state.sh", root=root)
    repo_raw = os.environ.get("REPO_ROOT", "") or _required(session, "REPO_ROOT", "missing-repo-root")
    repo_root = Path(repo_raw)
    if not repo_root.is_absolute() or repo_root.is_symlink() or not (repo_root / ".git").exists():
        raise CiFixerAdapterError("missing-repo-root")
    repo = os.environ.get(config.ENV_REPO, "") or _required(state, "REPO", "missing-repo")
    return Context(root, handoff, bgjob, repo_root.resolve(), repo)


def _git_text(context: Context, *args: str, reason: str) -> str:
    result = proc_run(["git", "-C", str(context.repo_root), *args], cwd=str(context.repo_root))
    if result.returncode != 0:
        raise CiFixerAdapterError(reason)
    return result.stdout


def _launch_path(context: Context, step: str) -> Path:
    return _safe_file(
        context.handoff_dir / f"launch-{model.validate_slug(step, label='step')}.env",
        root=context.handoff_dir,
        reason="unsafe-launch-envelope",
    )


def _read_launch(context: Context, step: str) -> Launch:
    path = _launch_path(context, step)
    if not path.is_file():
        raise CiFixerAdapterError("missing-launch-envelope")
    rows = _upper_rows(path, root=context.handoff_dir)
    try:
        launch = Launch(
            mode=_required(rows, "MODE", "invalid-launch-envelope"),
            run_id=_required(rows, "RUN_ID", "invalid-launch-envelope"),
            starting_head=_required(rows, "STARTING_HEAD", "invalid-launch-envelope"),
            input_fingerprint=_required(rows, "INPUT_FINGERPRINT", "invalid-launch-envelope"),
            tier=_required(rows, "TIER", "invalid-launch-envelope"),
            attempt=int(_required(rows, "ATTEMPT", "invalid-launch-envelope")),
            step=_required(rows, "STEP", "invalid-launch-envelope"),
            lineage=Path(_required(rows, "LINEAGE", "invalid-launch-envelope")),
        )
    except ValueError as exc:
        raise CiFixerAdapterError("invalid-launch-envelope") from exc
    if launch.step != step:
        raise CiFixerAdapterError("launch-step-mismatch")
    _ = _safe_file(launch.lineage, root=context.handoff_dir, reason="unsafe-lineage")
    return launch


def _lineage_rows(path: Path) -> list[tuple[str, ...]]:
    if not path.exists():
        return []
    try:
        text = larch_io.read_trusted_text(
            path,
            root=path.parent,
            errors="strict",
            reject_cr=True,
        )
        rows = [tuple(line.split("\t")) for line in text.splitlines()]
    except (OSError, UnicodeError, ValueError) as exc:
        raise CiFixerAdapterError("invalid-lineage") from exc
    if any(len(row) != _LINEAGE_FIELD_COUNT for row in rows):
        raise CiFixerAdapterError("invalid-lineage")
    deduplicated: dict[str, tuple[str, ...]] = {}
    for row in rows:
        prior = deduplicated.get(row[0])
        if prior is not None and prior != row:
            raise CiFixerAdapterError("invalid-lineage")
        _ = deduplicated.setdefault(row[0], row)
    return list(deduplicated.values())


def _start_identity(context: Context) -> tuple[str, str]:
    head = _git_text(context, "rev-parse", "HEAD", reason="invalid-head").strip()
    if _HEX_HEAD_RE.fullmatch(head) is None:
        raise CiFixerAdapterError("invalid-head")
    diff = _git_text(context, "diff", "--binary", "HEAD", reason="invalid-head")
    return head, hashlib.sha256(diff.encode("utf-8", errors="surrogateescape")).hexdigest()


def _select_route(context: Context) -> tuple[str, str]:
    route = _upper_rows(context.tmpdir / ".ship-route-exit-handoff.env", root=context.tmpdir)
    if route.get("NEEDS_USER_REASON") == "architectural-invariants-violation":
        session = _upper_rows(context.tmpdir / "session-env.sh", root=context.tmpdir)
        run_id = _required(session, "LARCH_RUN_ID", "invalid-session-env")
        if _RUN_ID_RE.fullmatch(run_id) is None:
            raise CiFixerAdapterError("invalid-invariant-run-id")
        return "invariant-primary", run_id
    scope = _required(route, "CI_FAILURE_SCOPE", "invalid-route-handoff")
    failed = route.get("FAILED_RUN_ID", "")
    main = _upper_rows(context.tmpdir / "main-health.env", root=context.tmpdir).get("MAIN_FAILED_RUN_ID", "")
    if failed and not failed.isdigit():
        raise CiFixerAdapterError("malformed-pr-run-id")
    if main and not main.isdigit():
        raise CiFixerAdapterError("malformed-main-run-id")
    if failed and main and failed != main:
        raise CiFixerAdapterError("conflicting-run-ids")
    if scope not in {"pr", "main"}:
        raise CiFixerAdapterError("unknown-ci-failure-scope")
    run_id = failed if scope == "pr" else main
    if not run_id or not run_id.isdigit():
        raise CiFixerAdapterError("invalid-selected-run-id")
    return "ci", run_id


def _new_launch(context: Context) -> Launch:
    starting_head, fingerprint = _start_identity(context)
    mode, run_id = _select_route(context)
    lineage_key = hashlib.sha256(f"{mode}\0{run_id}".encode()).hexdigest()[:20]
    lineage = _safe_file(
        context.handoff_dir / f"lineage-{lineage_key}.tsv",
        root=context.handoff_dir,
        reason="unsafe-lineage",
    )
    rows = _lineage_rows(lineage)
    selected = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        (row[1] for row in rows),
        codex_present=shutil.which("codex") is not None,
        cursor_present=shutil.which("cursor") is not None,
        claude_present=shutil.which("claude") is not None,
    )
    if selected.action != config.FIXER_TIER_ACTION_SELECTED:
        raise CiFixerAdapterError("ci-fix-exhausted")
    attempt = len(rows) + 1
    material = f"{mode}\0{run_id}\0{attempt}\0{selected.selected_tier}\0{starting_head}\0{fingerprint}"
    suffix = hashlib.sha256(material.encode()).hexdigest()[:16]
    step = f"implement-step8-ci-fixer-{attempt}-{selected.selected_tier}-{suffix}"
    launch = Launch(mode, run_id, starting_head, fingerprint, selected.selected_tier, attempt, step, lineage)
    path = _launch_path(context, step)
    larch_io.trusted_atomic_write(
        path=path,
        text=larch_io.format_kvs(launch.rows()),
        root=context.handoff_dir,
        mode=0o600,
    )
    return launch


def _lane_args(context: Context, launch: Launch, merge_env: Path) -> list[str]:
    args = [
        "--mode", launch.mode,
        "--repo-root", str(context.repo_root),
        "--implement-tmpdir", str(context.tmpdir),
        "--handoff-dir", str(context.handoff_dir),
        "--repo", context.repo,
        "--run-id", launch.run_id,
        "--tier", launch.tier,
        "--attempt", str(launch.attempt),
        "--starting-head", launch.starting_head,
        "--input-fingerprint", launch.input_fingerprint,
        "--bgjob-result-env", str(merge_env),
    ]
    if launch.mode == "invariant-primary":
        args.extend(("--invariant-evidence", str(context.tmpdir / "architectural-invariants.md")))
    return args


def _child(context: Context, args: argparse.Namespace) -> int:
    if not args.step or not args.merge_result_env or not args.bgjob_result_env:
        raise CiFixerAdapterError("invalid-child-arguments")
    merge = model.validate_merge_result_env(path=Path(args.merge_result_env), tmpdir=context.tmpdir)
    lane_merge = model.validate_merge_result_env(path=Path(args.bgjob_result_env), tmpdir=context.tmpdir)
    if merge != lane_merge:
        raise CiFixerAdapterError("result-env-mismatch")
    launch = _read_launch(context, args.step)
    return ci_fixer_lane.main(_lane_args(context, launch, merge))


def _start(context: Context) -> int:
    launch = _new_launch(context)
    merge_env = model.validate_merge_result_env(
        path=context.bgjob_dir / f"{launch.step}.merge.env",
        tmpdir=context.tmpdir,
    )
    if launch.mode == "invariant-primary":
        rc = invariant_evidence.main([
            "--implement-tmpdir", str(context.tmpdir),
            "--route-handoff", str(context.tmpdir / ".ship-route-exit-handoff.env"),
            "--mode", launch.mode,
            "--run-id", launch.run_id,
            "--starting-head", launch.starting_head,
            "--input-fingerprint", launch.input_fingerprint,
            "--tier", launch.tier,
            "--attempt", str(launch.attempt),
            "--step", launch.step,
        ])
        if rc != 0:
            raise CiFixerAdapterError("invariant-evidence-failed")
    log_dir, _, _ = model.log_paths(tmpdir=context.tmpdir, log_dir=None, step=launch.step)
    try:
        owner = daemon.owner_identity_from_env(
            os.environ.get("LARCH_CLAUDE_PID", "") or str(os.getppid())
        )
    except RuntimeError:
        owner = model.OwnerIdentity(recorded=None)
    cli_path = Path(__file__).resolve().parents[2] / "cli.py"
    spec = model.JobSpec(
        step=launch.step,
        tmpdir=context.tmpdir,
        log_dir=log_dir,
        budget_s=5400,
        command=(
            sys.executable, str(cli_path), "implement", "step-8-ci-fixer", "--start",
            "--step", launch.step, "--bgjob-result-env", str(merge_env),
        ),
        run_id=resolve_owned_run_id(explicit=None, tmpdir=context.tmpdir)
        or model.default_run_id(tmpdir=context.tmpdir, clone_path=Path.cwd().resolve()),
        owner=owner,
        merge_result_env=merge_env,
    )
    captured = io.StringIO()
    try:
        with contextlib.chdir(context.repo_root), contextlib.redirect_stdout(captured):
            rc = adapt.start_or_reattach(spec)
    except adapt.AdaptError as exc:
        raise CiFixerAdapterError(f"bgjob-{exc.token}") from exc
    if rc != 0:
        raise CiFixerAdapterError("bgjob-start-failed")
    print("BGJOB_STATUS=STARTED")
    print(f"STEP={launch.step}")
    print(f"MODE={launch.mode}")
    print(f"RUN_ID={launch.run_id}")
    print(f"TIER={launch.tier}")
    print(f"ATTEMPT={launch.attempt}")
    return 0


def _completed_bgjob_rows(context: Context, step: str) -> dict[str, str]:
    result_path = _safe_file(
        context.bgjob_dir / f"{step}.result.env",
        root=context.bgjob_dir,
        reason="unsafe-bgjob-result",
    )
    if not result_path.is_file():
        raise CiFixerAdapterError("missing-bgjob-result")
    result = _upper_rows(result_path, root=context.bgjob_dir)
    if result.get("STEP") != step or not result.get(config.BGJOB_RC_KEY):
        raise CiFixerAdapterError("invalid-bgjob-result")
    elapsed = result.get(config.BGJOB_ELAPSED_KEY, "")
    if not elapsed.isdigit():
        raise CiFixerAdapterError("invalid-bgjob-result")
    return result


def _validated_fixer_rows(context: Context, launch: Launch) -> dict[str, str]:
    merge = _safe_file(
        context.bgjob_dir / f"{launch.step}.merge.env",
        root=context.bgjob_dir,
        reason="unsafe-merge-result",
    )
    status = _safe_file(
        context.handoff_dir / "fixer-status.env",
        root=context.handoff_dir,
        reason="missing-result",
    )
    if not merge.is_file() or not status.is_file():
        raise CiFixerAdapterError("missing-result")
    left = _upper_rows(merge, root=context.bgjob_dir)
    if left != _upper_rows(status, root=context.handoff_dir):
        raise CiFixerAdapterError("merge-status-disagreement")
    expected = dict(launch.rows())
    identity_keys = (
        "MODE", "STEP", "RUN_ID", "ATTEMPT", "TIER",
        "STARTING_HEAD", "INPUT_FINGERPRINT",
    )
    if any(left.get(key) != expected[key] for key in identity_keys):
        raise CiFixerAdapterError("merge-status-disagreement")
    if left.get("RESULT", "") not in {"reship", "retry-next-tool", "operator-bail"}:
        raise CiFixerAdapterError("merge-status-disagreement")
    if _HEX_HEAD_RE.fullmatch(left.get("FINAL_HEAD", "")) is None:
        raise CiFixerAdapterError("invalid-final-head")
    return left


def _record_lineage(*, context: Context, launch: Launch, rows: dict[str, str]) -> None:
    lineage_row = (
        str(launch.attempt),
        launch.tier,
        launch.starting_head,
        launch.input_fingerprint,
        rows["RESULT"],
        rows["FINAL_HEAD"],
    )
    existing = _lineage_rows(launch.lineage)
    same_attempt = [row for row in existing if row[0] == str(launch.attempt)]
    if same_attempt and same_attempt != [lineage_row]:
        raise CiFixerAdapterError("lineage-conflict")
    if same_attempt:
        return
    text = "\n".join("\t".join(row) for row in [*existing, lineage_row]) + "\n"
    larch_io.trusted_atomic_write(
        path=launch.lineage,
        text=text,
        root=context.handoff_dir,
        mode=0o600,
    )


def _finalize(context: Context, step: str) -> int:
    launch = _read_launch(context, step)
    result = _completed_bgjob_rows(context, step)
    if result[config.BGJOB_RC_KEY] != "0":
        return ci_fixer_lane.main([
            "--finalize-crash", "--repo-root", str(context.repo_root),
            "--implement-tmpdir", str(context.tmpdir), "--handoff-dir", str(context.handoff_dir),
            "--step", step,
        ])
    left = _validated_fixer_rows(context, launch)
    outcome = left["RESULT"]
    final_head = left["FINAL_HEAD"]
    live_head = _git_text(context, "rev-parse", "HEAD", reason="invalid-live-head").strip()
    if live_head != final_head:
        raise CiFixerAdapterError("final-head-drift")
    _record_lineage(context=context, launch=launch, rows=left)
    if outcome == "reship":
        with contextlib.chdir(context.repo_root):
            if push.branch_main([]) != 0:
                raise CiFixerAdapterError("fixer-reship-push-failed")
    for key in (
        "RESULT", "REASON", "MODE", "RUN_ID", "ATTEMPT", "TIER",
        "STARTING_HEAD", "INPUT_FINGERPRINT", "FINAL_HEAD",
    ):
        print(f"{key}={left.get(key, '')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(prog="cli.py implement step-8-ci-fixer")
    modes = parser.add_mutually_exclusive_group(required=True)
    _ = modes.add_argument("--start", action="store_true")
    _ = modes.add_argument("--finalize", action="store_true")
    _ = parser.add_argument("--step", default="")
    _ = parser.add_argument("--bgjob-child", action="store_true")
    _ = parser.add_argument("--merge-result-env", default="")
    _ = parser.add_argument("--bgjob-result-env", default="")
    try:
        args = parser.parse_args(argv)
        context = _context(Path(os.environ[config.ENV_IMPLEMENT_TMPDIR]))
        if args.bgjob_child:
            return _child(context, args)
        if args.finalize:
            if not args.step:
                raise CiFixerAdapterError("invalid-finalize-arguments")
            return _finalize(context, args.step)
        if args.step or args.bgjob_result_env:
            raise CiFixerAdapterError("invalid-start-arguments")
        return _start(context)
    except (KeyError, OSError, RuntimeError, UnicodeError, ValueError, CiFixerAdapterError) as exc:
        reason = str(exc) or "ci-fixer-adapter-failed"
        return _fail(reason)
