"""Operator-approved recovery helpers for the implement ship driver."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.core import config, proc
from larch.errors import ShipError
from larch.git import gh
from larch.implement.ship_state import _tmpdir_under_allowed_root  # pyright: ignore[reportPrivateUsage] # internal ship-state helpers reused within the larch.implement package

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _emit(*, key: str, value: object) -> None:
    print(f"{key}={value}")


def _trusted_tmpdir(raw: str) -> Path:
    if not _tmpdir_under_allowed_root(raw):
        raise ValueError("unsafe-implement-tmpdir")
    tmpdir = Path(raw)
    _ = larch_io.validate_trusted_directory(tmpdir)
    return tmpdir


def _read_layer(*, tmpdir: Path, name: str, required: bool = False) -> dict[str, str]:
    path = tmpdir / name
    if not larch_io.trusted_file_present(path, root=tmpdir):
        if required:
            raise ValueError(f"{name}-missing")
        return {}
    text = larch_io.read_trusted_text(path, root=tmpdir, reject_cr=True)
    return larch_io.parse_kv(text, key_pattern=_KEY_RE, skip_comments=True)


def _session_run_id(tmpdir: Path) -> str:
    session = _read_layer(tmpdir=tmpdir, name="session-env.sh", required=True)
    run_id = session.get("LARCH_RUN_ID", "").strip()
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid-run-id")
    return run_id


def _parse_kinds(raw: str) -> tuple[str, ...]:
    values = tuple(raw.split(","))
    if not values or any(not value or value.strip() != value for value in values):
        raise ValueError("invalid-kinds")
    if len(set(values)) != len(values) or any(
        value not in config.ASSESSMENT_WAIVER_KINDS for value in values
    ):
        raise ValueError("invalid-kinds")
    return tuple(
        kind
        for kind in (
            config.ASSESSMENT_KIND_INVARIANTS,
            config.ASSESSMENT_KIND_GUIDELINES,
        )
        if kind in values
    )


def load_assessment_waiver(implement_tmpdir: str) -> frozenset[str]:
    """Return valid run-bound waived kinds, or an empty set for any invalid artifact."""
    try:
        tmpdir = _trusted_tmpdir(implement_tmpdir)
        run_id = _session_run_id(tmpdir)
        path = tmpdir / config.ASSESSMENT_OPERATOR_WAIVER_FILENAME
        if not larch_io.trusted_file_present(path, root=tmpdir):
            return frozenset()
        raw = json.loads(larch_io.read_trusted_text(path, root=tmpdir, reject_cr=True))
        if not isinstance(raw, dict):
            return frozenset()
        data = cast("dict[str, object]", raw)
        kinds_raw = data.get("kinds")
        valid_header = (
            str(data.get("schema_version", ""))
            == config.ASSESSMENT_OPERATOR_WAIVER_SCHEMA_VERSION
            and data.get("run_id") == run_id
            and isinstance(kinds_raw, list)
            and all(isinstance(kind, str) for kind in cast("list[object]", kinds_raw))
        )
        kinds = cast("list[str]", kinds_raw) if valid_header else []
        if (
            not kinds
            or len(set(kinds)) != len(kinds)
            or any(kind not in config.ASSESSMENT_WAIVER_KINDS for kind in kinds)
        ):
            return frozenset()
        return frozenset(kinds)
    except (OSError, ValueError, json.JSONDecodeError):
        return frozenset()


def waive_assessment_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ship waive-assessment")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--kinds", required=True)
    try:
        args = parser.parse_args(argv)
        tmpdir = _trusted_tmpdir(args.implement_tmpdir)
        kinds = _parse_kinds(args.kinds)
        run_id = _session_run_id(tmpdir)
        body = {
            "schema_version": config.ASSESSMENT_OPERATOR_WAIVER_SCHEMA_VERSION,
            "kinds": list(kinds),
            "run_id": run_id,
        }
        larch_io.trusted_atomic_write(
            tmpdir / config.ASSESSMENT_OPERATOR_WAIVER_FILENAME,
            json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n",
            root=tmpdir,
        )
    except SystemExit:
        _emit(key="WAIVER_STATUS", value=config.ASSESSMENT_WAIVER_STATUS_FAILED)
        _emit(key="ERROR", value="usage")
        return config.EXIT_INTERNAL_ERROR
    except (OSError, ValueError) as exc:
        _emit(key="WAIVER_STATUS", value=config.ASSESSMENT_WAIVER_STATUS_FAILED)
        _emit(key="ERROR", value=str(exc).replace("\n", " ")[:200])
        return config.EXIT_INTERNAL_ERROR
    _emit(key="WAIVER_STATUS", value=config.ASSESSMENT_WAIVER_STATUS_OK)
    return config.EXIT_OK


def _write_terminal_layer(
    *, tmpdir: Path, name: str, updates: Mapping[str, str]
) -> None:
    values = _read_layer(tmpdir=tmpdir, name=name, required=name == "session-env.sh")
    values.update(dict(config.RECONCILE_TERMINAL_DONE_CLEAR_FIELDS))
    values.update(updates)
    larch_io.trusted_atomic_write(
        tmpdir / name,
        larch_io.format_kvs(values, sort_keys=True),
        root=tmpdir,
    )


def _validate_run_identity(
    *, run_id: str, layers: tuple[dict[str, str], ...]
) -> None:
    for layer in layers:
        for key in ("RUN_ID", "LARCH_RUN_ID"):
            value = layer.get(key, "").strip()
            if value and (not _RUN_ID_RE.fullmatch(value) or value != run_id):
                raise ValueError("run-id-mismatch")


def _manifest_path(*, tmpdir: Path, run_id: str) -> Path:
    return tmpdir / "larch-logs" / "implement" / run_id / "manifest.json"


def _validate_manifest_run_identity(*, tmpdir: Path, run_id: str) -> None:
    path = _manifest_path(tmpdir=tmpdir, run_id=run_id)
    if not larch_io.trusted_file_present(path, root=tmpdir):
        return
    raw = json.loads(larch_io.read_trusted_text(path, root=tmpdir, reject_cr=True))
    if not isinstance(raw, dict):
        raise TypeError("manifest-invalid")
    data = cast("dict[str, object]", raw)
    if data.get("run_id", run_id) != run_id:
        raise ValueError("manifest-run-mismatch")


def _write_manifest(*, tmpdir: Path, run_id: str, pr_number: int) -> None:
    path = _manifest_path(tmpdir=tmpdir, run_id=run_id)
    if not larch_io.trusted_file_present(path, root=tmpdir):
        raise ValueError("manifest-missing")
    raw = json.loads(larch_io.read_trusted_text(path, root=tmpdir, reject_cr=True))
    if not isinstance(raw, dict):
        raise TypeError("manifest-invalid")
    data = cast("dict[str, object]", raw)
    if data.get("run_id", run_id) != run_id:
        raise ValueError("manifest-run-mismatch")
    data["status"] = config.MANIFEST_STATUS_DONE
    data["pr_number"] = pr_number
    larch_io.trusted_atomic_write(path, json.dumps(data, indent=2) + "\n", root=tmpdir)


def _has_overlay(values: Mapping[str, str]) -> bool:
    if (
        values.get("BAIL_REASON", "").strip()
        or values.get("IMPLEMENT_BAIL_REASON", "").strip()
    ):
        return True
    if (
        values.get("BAIL_FAILURE_DETAIL_LOG", "").strip()
        or values.get("FAILED_RUN_ID", "").strip()
    ):
        return True
    if values.get("BAIL_NEEDS_USER_INPUT", "").strip().lower() in _TRUTHY:
        return True
    if (
        values.get("STALL_TRACKING", "").strip().lower() in _TRUTHY
        or values.get("STALL_STEP", "").strip()
    ):
        return True
    if values.get("PHASE", "").strip() == "stalled":
        return True
    exit_code = values.get("EXIT_CODE", "").strip()
    return bool(exit_code and exit_code != "0")


def _verify_no_bail_overlay(
    ship: Mapping[str, str],
    finalize_state: Mapping[str, str],
    session: Mapping[str, str],
) -> bool:
    return not any(_has_overlay(layer) for layer in (ship, finalize_state, session))


def _verify_reconciliation(
    *,
    tmpdir: Path,
    run_id: str,
    pr: gh.PullRequest,
    repo: str,
) -> str:
    layers = (
        _read_layer(tmpdir=tmpdir, name="ship-pr-state.sh", required=True),
        _read_layer(tmpdir=tmpdir, name="finalize-state.sh", required=True),
        _read_layer(tmpdir=tmpdir, name="session-env.sh", required=True),
    )
    try:
        _validate_run_identity(run_id=run_id, layers=layers)
    except ValueError:
        return "run-id-mismatch"
    if not _verify_no_bail_overlay(*layers):
        return "bail-overlay-remains"
    layers_match = all(
        layer.get("PHASE") == "done"
        and layer.get("MERGE_RESULT") == config.MERGE_RESULT_MERGED
        and layer.get("PR_NUMBER") == str(pr.number)
        and layer.get("PR_CLOSED") == "true"
        and layer.get("PR_URL") == pr.url
        and layer.get("REPO") == repo
        for layer in layers
    )
    if not layers_match:
        return "reconciliation-postcondition-failed"
    sentinel = larch_io.read_trusted_text(
        tmpdir / "post-merge-sentinel", root=tmpdir, reject_cr=True
    )
    manifest_raw = json.loads(
        larch_io.read_trusted_text(
            _manifest_path(tmpdir=tmpdir, run_id=run_id), root=tmpdir, reject_cr=True
        )
    )
    manifest = (
        cast("dict[str, object]", manifest_raw)
        if isinstance(manifest_raw, dict)
        else None
    )
    postconditions_match = (
        sentinel == "MERGE_RESULT=merged\n"
        and manifest is not None
        and manifest.get("status") == config.MANIFEST_STATUS_DONE
        and manifest.get("pr_number") == pr.number
    )
    if not postconditions_match:
        return "reconciliation-postcondition-failed"
    return ""


def _merged_pr(*, number: int, repo: str) -> gh.PullRequest:
    try:
        pr = gh.pr_view(proc, number, repo=repo)
    except ShipError as exc:
        raise ValueError("pr-probe-failed") from exc
    if pr.state.upper() != "MERGED" or not pr.merged_at:
        raise ValueError("pr-not-merged")
    if pr.number != number or pr.url != f"https://github.com/{repo}/pull/{number}":
        raise ValueError("pr-identity-mismatch")
    return pr


def reconcile_manual_merge_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py ship reconcile-manual-merge")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--pr", required=True, type=int)
    _ = parser.add_argument("--repo")
    try:
        args = parser.parse_args(argv)
        if args.pr <= 0:
            raise ValueError("invalid-pr")
        tmpdir = _trusted_tmpdir(args.implement_tmpdir)
        run_id = _session_run_id(tmpdir)
        layers = (
            _read_layer(tmpdir=tmpdir, name="ship-pr-state.sh"),
            _read_layer(tmpdir=tmpdir, name="finalize-state.sh"),
            _read_layer(tmpdir=tmpdir, name="session-env.sh", required=True),
        )
        _validate_run_identity(run_id=run_id, layers=layers)
        _validate_manifest_run_identity(tmpdir=tmpdir, run_id=run_id)
        persisted_repos = {
            layer.get("REPO", "") for layer in layers if layer.get("REPO", "")
        }
        repo = args.repo or next(iter(persisted_repos), "")
        if not _REPO_RE.fullmatch(repo):
            raise ValueError("invalid-repo")
        if any(saved != repo for saved in persisted_repos):
            raise ValueError("repository-mismatch")
        pr = _merged_pr(number=args.pr, repo=repo)
        updates = {
            "PHASE": "done",
            "PR_CLOSED": "true",
            "PR_NUMBER": str(pr.number),
            "PR_URL": pr.url,
            "MERGE_RESULT": config.MERGE_RESULT_MERGED,
            "REPO": repo,
            "REPO_UNAVAILABLE": "false",
            "RUN_ID": run_id,
        }
        _write_terminal_layer(
            tmpdir=tmpdir,
            name="ship-pr-state.sh",
            updates=updates | {"IMPLEMENT_TMPDIR": str(tmpdir)},
        )
        _write_terminal_layer(tmpdir=tmpdir, name="finalize-state.sh", updates=updates)
        _write_terminal_layer(
            tmpdir=tmpdir,
            name="session-env.sh",
            updates=updates | {"LARCH_RUN_ID": run_id},
        )
        larch_io.trusted_atomic_write(
            tmpdir / "post-merge-sentinel", "MERGE_RESULT=merged\n", root=tmpdir
        )
        _write_manifest(tmpdir=tmpdir, run_id=run_id, pr_number=pr.number)
        verification_error = _verify_reconciliation(
            tmpdir=tmpdir,
            run_id=run_id,
            pr=pr,
            repo=repo,
        )
        if verification_error:
            raise ShipError(verification_error)
    except SystemExit:
        _emit(key="RECONCILE_STATUS", value="failed")
        _emit(key="ERROR", value="usage")
        return config.EXIT_INTERNAL_ERROR
    except (OSError, TypeError, ValueError, ShipError, json.JSONDecodeError) as exc:
        _emit(key="RECONCILE_STATUS", value="failed")
        _emit(key="ERROR", value=str(exc).replace("\n", " ")[:200])
        return config.EXIT_INTERNAL_ERROR
    _emit(key="RECONCILE_STATUS", value="ok")
    _emit(key="PR_NUMBER", value=args.pr)
    _emit(key="MERGE_RESULT", value=config.MERGE_RESULT_MERGED)
    return config.EXIT_OK
