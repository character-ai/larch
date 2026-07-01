# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""DispatchState, manifest validation, normalize-coder-scout, and OOS materialization."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from larch.core import redact
from larch.issue import file_oos
from larch.implement.dispatch_helpers import (
    _emit_kv,
    _git,
    _git_stdout,
    _invoke_cli,
    _parse_kv,
    _rehydrate_plugin_root,
    _write_bytes_atomic,
    _write_prelaunch_digests,
    _write_text_atomic,
    PORCELAIN_MIN_PARTS,
    SUMMARY_BULLETS_MAX,
)
from larch.implement.dispatch_recovery import RecoveryPorcelainInputs, compute_recovery_paths


# Mutable state: scout_status / baseline_sha / spawn_branch are filled in as dispatch proceeds.
@dataclass
class DispatchState:
    repo_root: Path
    tmpdir: Path
    plan_file: Path
    feature_file: Path
    coder: str
    cursor_present: str
    cursor_binary_found: str
    codex_binary_found: str
    answers_file: Path | None
    plugin_root: Path
    tool_tag: str
    manifest_path: Path
    manifest_raw_path: Path
    qa_pending_path: Path
    transcript_path: Path
    sidecar_log: Path
    scout_coder_manifest: Path
    launch_scout_manifest: Path
    external_scout_marker: Path
    baseline_file: Path
    prelaunch_porcelain: Path
    postlaunch_porcelain: Path
    prelaunch_digests: Path
    prelaunch_index_flag: Path
    recovery_paths_file: Path
    resume_count_file: Path
    spawn_branch_file: Path
    spawn_coder_file: Path
    runtime_failure_token: str
    bailed_no_reason_token: str
    requires_head_unchanged: bool
    nonzero_exit_warn_token: str = ""
    baseline_sha: str = ""
    spawn_branch: str = ""
    scout_status: str = ""

    def emit_bailed(self, reason: str, *, manifest: bool = False) -> int:
        _emit_kv(key="STATUS", value="bailed")
        _emit_kv(key="REASON", value=reason)
        _emit_kv(key="TOOL", value=self.tool_tag)
        if manifest:
            _emit_kv(key="MANIFEST", value=str(self.manifest_path))
        if self.transcript_path.exists() and self.transcript_path.stat().st_size > 0:
            _emit_kv(key="TRANSCRIPT", value=str(self.transcript_path))
        if self.sidecar_log.exists() and self.sidecar_log.stat().st_size > 0:
            _emit_kv(key="SIDECAR_LOG", value=str(self.sidecar_log))
        _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="forbidden")
        return 0


def _clear_external_scout_state(tmpdir: Path) -> None:
    for path in (
        tmpdir / "scout-coder-manifest.json",
        tmpdir / "step2-external-scout-eligible.txt",
        tmpdir / "step2-scout-coder-status.env",
        tmpdir / "scout-coder-manifest.raw.json",
        tmpdir / ".producer-scout-warning-logged",
        tmpdir / "codex-step2-out" / "scout-coder-manifest.json",
        tmpdir / "cursor-step2-out" / "scout-coder-manifest.json",
    ):
        with contextlib.suppress(OSError):
            path.unlink()


def _submodule_roots(repo: Path) -> list[str]:
    out = _git_stdout(repo, "submodule", "status", "--recursive")
    roots: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= PORCELAIN_MIN_PARTS:
            roots.append(parts[1].rstrip("/"))
    return roots


def _path_under_submodule(*, rel: str, roots: Iterable[str]) -> bool:
    return any(rel == root or rel.startswith(root + "/") for root in roots if root)


def _post_implementer_safety_reason(st: DispatchState) -> str:
    current_branch = _git_stdout(st.repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if current_branch != st.spawn_branch:
        return "branch-changed"
    sub_status = _git_stdout(st.repo_root, "submodule", "status", "--recursive")
    if sub_status and re.search(r"^[+\-U]", sub_status, re.MULTILINE):
        return "submodule-dirty"
    roots = _submodule_roots(st.repo_root)
    if roots:
        raw = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--ignore-submodules=none", binary=True)
        if raw.returncode != 0:
            return "submodule-dirty"
        for rec in raw.stdout.split(b"\0"):
            if not rec:
                continue
            rel = rec[3:].decode("utf-8", "surrogateescape")
            if _path_under_submodule(rel=rel, roots=roots):
                return "submodule-dirty"
    if st.requires_head_unchanged:
        current_head = _git_stdout(st.repo_root, "rev-parse", "HEAD")
        if current_head != st.baseline_sha:
            return f"{st.tool_tag}-modified-history"
    return ""


def _write_prelaunch_baseline(st: DispatchState) -> None:
    if st.answers_file is not None or st.prelaunch_porcelain.exists():
        return
    raw = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True).stdout
    _write_bytes_atomic(path=st.prelaunch_porcelain, data=cast("bytes", raw))
    index_nonempty = _git(st.repo_root, "diff", "--cached", "--quiet", "--no-ext-diff").returncode != 0
    _write_text_atomic(path=st.prelaunch_index_flag, text=f"PRELAUNCH_INDEX_NONEMPTY={str(index_nonempty).lower()}\n")
    _write_prelaunch_digests(
        repo_root=st.repo_root,
        porcelain_file=st.prelaunch_porcelain,
        digests_file=st.prelaunch_digests,
    )


def _manifest_legacy_fingerprint(obj: object) -> bool:
    return isinstance(obj, dict) and "schema_version" not in obj and set(obj.keys()) <= {"status", "summary", "checks"}


def _json_load(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _coder_scout_archetype_count(path: Path) -> int | None:
    obj = _json_load(path)
    if not isinstance(obj, dict) or not isinstance(obj.get("archetypes"), list):
        return None
    return len(obj["archetypes"])


def _write_coder_scout_status(*, tmpdir: Path, status: str, manifest: Path, producer: str) -> None:
    _write_text_atomic(
        path=tmpdir / "step2-scout-coder-status.env",
        text=f"SCOUT_CODER_STATUS={status}\n"
        f"SCOUT_CODER_MANIFEST={manifest}\n"
        f"SCOUT_CODER_PRODUCER={producer}\n",
    )


def _warn_invalid_coder_scout(producer: str) -> None:
    producer_label = "main agent" if producer == "main-agent" else "external coder"
    print(
        f"**⚠ implement Step 2: {producer_label} dynamic-archetype manifest missing or invalid; Step 5 will use static reviewers only.**",
        file=sys.stderr,
    )


def normalize_coder_scout(
    *,
    tmpdir: Path,
    input_path: Path,
    producer: str = "external",
) -> str:
    """Normalize a coder-produced scout manifest for /implement Step 5."""
    scout_manifest = tmpdir / "scout-coder-manifest.json"
    marker = tmpdir / "step2-external-scout-eligible.txt"
    filtered_tmp = tmpdir / f"scout-coder-manifest.filtered.{os.getpid()}.json"
    raw_count = _coder_scout_archetype_count(input_path)
    status = "missing-or-invalid"
    try:
        if raw_count is not None:
            result = _invoke_cli(
                [
                    "scout",
                    "filter-manifest",
                    str(input_path),
                    str(filtered_tmp),
                    "--max-archetypes",
                    "1",
                    "--mode",
                    "review",
                ]
            )
            kv = _parse_kv(result.stdout)
            filtered_count = _coder_scout_archetype_count(filtered_tmp)
            filter_status = kv.get("SCOUT_STATUS", "")
            filter_ok = result.returncode == 0 and filter_status in {"ok", "empty"} and filtered_count is not None
            if filter_ok and (raw_count == 0 or (filtered_count or 0) > 0):
                status = "ok"
                filtered_tmp.replace(scout_manifest)
            else:
                _write_text_atomic(path=scout_manifest, text='{"archetypes":[]}\n')
        else:
            _write_text_atomic(path=scout_manifest, text='{"archetypes":[]}\n')
    finally:
        with contextlib.suppress(OSError):
            filtered_tmp.unlink()
    if status == "ok":
        _write_text_atomic(path=marker, text="eligible\n")
    else:
        with contextlib.suppress(OSError):
            marker.unlink()
        _warn_invalid_coder_scout(producer)
    _write_coder_scout_status(tmpdir=tmpdir, status=status, manifest=scout_manifest, producer=producer)
    return status


def normalize_coder_scout_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement normalize-coder-scout")
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--producer", choices=("external", "main-agent"), default="external")
    args = parser.parse_args(argv)
    tmpdir = Path(args.tmpdir)
    if not tmpdir.is_dir():
        print(f"implement normalize-coder-scout: --tmpdir not a directory: {tmpdir}", file=sys.stderr)
        return 2
    _rehydrate_plugin_root(tmpdir)
    status = normalize_coder_scout(tmpdir=tmpdir, input_path=Path(args.input), producer=args.producer)
    _emit_kv(key="SCOUT_CODER_STATUS", value=status)
    _emit_kv(key="SCOUT_CODER_MANIFEST", value=str(tmpdir / "scout-coder-manifest.json"))
    return 0


def _read_prelaunch_index_nonempty(st: DispatchState) -> str:
    if not st.prelaunch_index_flag.is_file():
        return "false"
    for line in st.prelaunch_index_flag.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("PRELAUNCH_INDEX_NONEMPTY="):
            return line.split("=", 1)[1]
    return "false"


def _recovery_paths_submodule_clean(st: DispatchState) -> bool:
    roots = _submodule_roots(st.repo_root)
    for rel in st.recovery_paths_file.read_bytes().split(b"\0"):
        if not rel:
            continue
        path = rel.decode("utf-8", "surrogateescape")
        if _path_under_submodule(rel=path, roots=roots):
            return False
    return True


def _finalize_manifest_invalid_recovery(st: DispatchState) -> None:
    invalid = st.tmpdir / "manifest-raw.invalid.json"
    if st.manifest_raw_path.exists():
        st.manifest_raw_path.replace(invalid)
    _write_text_atomic(
        path=st.tmpdir / "recovery-metadata.json",
        text=json.dumps(
            {
                "schema_version": 1,
                "recovery_from": "manifest-schema-invalid",
                "prior_tool": st.tool_tag,
                "recovery_paths_file": st.recovery_paths_file.name,
            },
            separators=(",", ":"),
        )
        + "\n",
    )
    _emit_kv(key="STATUS", value="claude_fallback")
    _emit_kv(key="TOOL", value=st.tool_tag)
    if st.transcript_path.exists() and st.transcript_path.stat().st_size > 0:
        _emit_kv(key="TRANSCRIPT", value=str(st.transcript_path))
    if st.sidecar_log.exists() and st.sidecar_log.stat().st_size > 0:
        _emit_kv(key="SIDECAR_LOG", value=str(st.sidecar_log))
    _emit_kv(key="ORCHESTRATOR_EDIT_AUTHORITY", value="allowed")
    _emit_kv(key="RECOVERY_FROM", value="manifest-schema-invalid")
    _emit_kv(key="RECOVERY_PRIOR_TOOL", value=st.tool_tag)
    _emit_kv(key="RECOVERY_PATHS_FILE", value=str(st.recovery_paths_file))
    _clear_external_scout_state(st.tmpdir)


def _manifest_invalid_bail_reason(*, st: DispatchState, status: str, raw_obj: object | None) -> str | None:
    if not isinstance(raw_obj, dict):
        return "manifest-schema-invalid"
    if status != "complete" and not (status == "" and _manifest_legacy_fingerprint(raw_obj)):
        return "manifest-schema-invalid"
    if _read_prelaunch_index_nonempty(st) == "true":
        return "manifest-schema-invalid"
    post = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True).stdout
    _write_bytes_atomic(path=st.postlaunch_porcelain, data=cast("bytes", post))
    ok = compute_recovery_paths(
        repo_root=st.repo_root,
        tmpdir=st.tmpdir,
        porcelain=RecoveryPorcelainInputs(
            prelaunch_porcelain=st.prelaunch_porcelain,
            postlaunch_porcelain=st.postlaunch_porcelain,
            prelaunch_digests=st.prelaunch_digests,
        ),
        out_file=st.recovery_paths_file,
    )
    if not ok:
        return "manifest-schema-invalid"
    if not _recovery_paths_submodule_clean(st):
        return "submodule-dirty"
    return _post_implementer_safety_reason(st) or None


def _emit_manifest_invalid_or_recover(*, st: DispatchState, status: str, raw_obj: object | None) -> int:
    if (bail := _manifest_invalid_bail_reason(st=st, status=status, raw_obj=raw_obj)) is not None:
        return st.emit_bailed(bail)
    _finalize_manifest_invalid_recovery(st)
    return 0


def _manifest_complete_salvageable(path: Path) -> bool:
    obj = _json_load(path)
    return isinstance(obj, dict) and str(obj.get("schema_version", "")) == "1" and obj.get("status") == "complete"


def _normalize_scout(st: DispatchState) -> None:
    st.scout_status = normalize_coder_scout(
        tmpdir=st.tmpdir,
        input_path=st.launch_scout_manifest,
        producer="external",
    )


def _validate_manifest_paths(*, st: DispatchState, obj: dict[str, Any]) -> str:
    roots = _submodule_roots(st.repo_root)
    paths = [
        item["path"]
        for item in obj.get("files_touched", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    paths.extend(item for item in obj.get("tests_added_or_modified", []) if isinstance(item, str))
    for p in paths:
        if "\x00" in p or p.startswith("/") or ".." in p or _path_under_submodule(rel=p, roots=roots):
            return "protected-path-modified"
    return ""


def _complete_schema_valid(obj: dict[str, Any]) -> bool:
    return (
        isinstance(obj.get("files_touched"), list)
        and len(obj["files_touched"]) > 0
        and all(isinstance(item, dict) and isinstance(item.get("path"), str) for item in obj["files_touched"])
        and isinstance(obj.get("commit_message"), str)
        and len(obj["commit_message"]) > 0
        and isinstance(obj.get("summary_bullets"), list)
        and 1 <= len(obj["summary_bullets"]) <= SUMMARY_BULLETS_MAX
        and isinstance(obj.get("tests_added_or_modified"), list)
        and isinstance(obj.get("todos_left"), list)
        and isinstance(obj.get("oos_observations"), list)
    )


def _sanitize_manifest_obj(obj: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(obj)
    for key in ("commit_message",):
        if isinstance(sanitized.get(key), str):
            sanitized[key] = redact.redact_secrets_only(sanitized[key])
    for key in ("summary_bullets", "todos_left"):
        if isinstance(sanitized.get(key), list):
            sanitized[key] = [redact.redact_secrets_only(v) if isinstance(v, str) else v for v in sanitized[key]]
    if isinstance(sanitized.get("oos_observations"), list):
        out: list[Any] = []
        for item in sanitized["oos_observations"]:
            if not isinstance(item, dict):
                out.append(item)
                continue
            new = dict(item)
            for key in ("title", "description", "focus-area", "focus_area"):
                if isinstance(new.get(key), str):
                    new[key] = redact.redact_secrets_only(new[key])
            out.append(new)
        sanitized["oos_observations"] = out
    return sanitized


def _append_materialize_oos_failure(*, st: DispatchState, log: Path, exit_code: int) -> None:
    _invoke_cli([
        "run-log",
        "append-failure",
        "--log",
        str(st.tmpdir / "execution-issues.md"),
        "--site",
        "step2-materialize-manifest-oos",
        "--tool",
        "cli.py oos materialize-manifest",
        "--exit-code",
        str(exit_code),
        "--category",
        "Tool Failures",
        "--output-file",
        str(log),
        "--redact",
    ], cwd=st.repo_root)


def _oos_materialize_should_bail(*, count_rc: int, count_str: str, oos_nonempty: bool, materialize_failed: bool) -> bool:
    if count_rc != 0:
        return True
    if materialize_failed and count_str.isdigit() and int(count_str) > 0:
        return True
    return materialize_failed and oos_nonempty


def _materialize_oos(st: DispatchState, *, oos_observations_nonempty: bool = False) -> str:
    log = st.tmpdir / "materialize-manifest-oos.log"
    log.write_text("", encoding="utf-8")
    count_rc = 0
    count_str = ""
    materialize_failed = False

    try:
        count_result = file_oos.materialize_manifest_oos(st.manifest_path, st.tmpdir, count_only=True)
        count_str = str(count_result)
        count_rc = 0
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        log.write_text(str(exc) + "\n", encoding="utf-8")
        count_rc = 1

    try:
        _ = file_oos.materialize_manifest_oos(st.manifest_path, st.tmpdir, count_only=False)
    except (TypeError, ValueError, RuntimeError, OSError) as exc:
        with log.open("a", encoding="utf-8") as handle:
            handle.write(str(exc) + "\n")
        materialize_failed = True

    if materialize_failed:
        _append_materialize_oos_failure(st=st, log=log, exit_code=1)
    if _oos_materialize_should_bail(
        count_rc=count_rc,
        count_str=count_str,
        oos_nonempty=oos_observations_nonempty,
        materialize_failed=materialize_failed,
    ):
        return "manifest-oos-materialization-failed"
    return ""
