# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""/implement Step 2 dispatch, recovery paths, and Step 4 commit helpers."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import logging_util
import redact

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
_SAFE_CODERS = {"claude", "codex", "cursor"}
WRAPPER_VALIDATION_RC = 2
RESUME_CAP = 5
SUMMARY_BULLETS_MAX = 5
PORCELAIN_MIN_PARTS = 2
GIT_BIN = shutil.which("git") or "git"
BASH_BIN = shutil.which("bash") or "bash"


def _err(message: str) -> None:
    logging_util.diagnostic(message)


def _emit_kv(key: str, value: str | int) -> None:
    logging_util.emit_kv(key, str(value))


def _run(argv: Sequence[str], *, cwd: str | Path | None = None, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


def _git(repo: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        [GIT_BIN, "-C", str(repo), *args],
        capture_output=True,
        text=not binary,
        check=False,
    )


def _git_stdout(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    if result.returncode != 0:
        return ""
    return result.stdout.rstrip("\n")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Z0-9_]+", key):
            out.setdefault(key, value)
    return out


def _session_get(file: Path, key: str, default: str = "") -> str:
    if not file.is_file():
        return default
    prefix = key + "="
    for line in file.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return default



def _binary_available(session_env: Path, key: str, binary: str) -> str:
    value = _session_get(session_env, key, "")
    if value in {"true", "false"}:
        return value
    return "true" if shutil.which(binary) is not None else "false"

def _current_cli_path() -> Path:
    root = Path(os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT)
    return root / "python" / "cli.py"


def _invoke_cli(args: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return _run([sys.executable, str(_current_cli_path()), *args], cwd=cwd)


@dataclass
class RecoveryParse:
    tuples: set[tuple[str, str]]
    paths: set[str]


def _parse_porcelain_z(path: Path) -> RecoveryParse:
    raw = path.read_bytes() if path.exists() else b""
    items = raw.split(b"\0")
    tuples: set[tuple[str, str]] = set()
    paths: set[str] = set()
    idx = 0
    while idx < len(items):
        rec = items[idx]
        idx += 1
        if not rec:
            continue
        status = rec[:2].decode("ascii", "replace")
        rel = rec[3:].decode("utf-8", "surrogateescape")
        if ("R" in status or "C" in status) and idx < len(items):
            idx += 1
        tuples.add((status, rel))
        paths.add(rel)
    return RecoveryParse(tuples, paths)


def compute_recovery_paths(
    *,
    repo_root: Path,
    tmpdir: Path,
    prelaunch_porcelain: Path,
    postlaunch_porcelain: Path,
    prelaunch_digests: Path,
    out_file: Path,
) -> bool:
    pre = _parse_porcelain_z(prelaunch_porcelain)
    post = _parse_porcelain_z(postlaunch_porcelain)
    digests: dict[str, str] = {}
    if prelaunch_digests.exists():
        for line in prelaunch_digests.read_text(encoding="utf-8", errors="surrogateescape").splitlines():
            if "\t" in line:
                digest, rel = line.split("\t", 1)
                digests[rel] = digest
    tmp_rel: str | None = None
    try:
        repo_real = repo_root.resolve()
        tmp_real = tmpdir.resolve()
        if tmp_real == repo_real:
            tmp_rel = "."
        else:
            tmp_real.relative_to(repo_real)
            tmp_rel = os.path.relpath(tmp_real, repo_real)
    except (OSError, ValueError):
        tmp_rel = None

    def under_tmp(rel: str) -> bool:
        if tmp_rel is None:
            return False
        return rel == tmp_rel or rel.startswith(tmp_rel.rstrip("/") + "/")

    def current_digest(rel: str) -> str:
        try:
            return hashlib.sha256((repo_root / rel).read_bytes()).hexdigest()
        except OSError:
            return "missing"

    candidates: list[str] = []
    for status, rel in sorted(post.tuples, key=lambda item: item[1]):
        if under_tmp(rel):
            continue
        include = False
        if (status, rel) not in pre.tuples:
            include = True
        elif rel in pre.paths:
            include = current_digest(rel) != digests.get(rel, "")
        if include and rel not in candidates:
            candidates.append(rel)
    _write_bytes_atomic(out_file, b"".join(p.encode("utf-8", "surrogateescape") + b"\0" for p in candidates))
    return bool(candidates)


def recovery_paths_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement recovery-paths")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--prelaunch-porcelain", required=True)
    parser.add_argument("--postlaunch-porcelain", required=True)
    parser.add_argument("--prelaunch-digests", required=True)
    parser.add_argument("--out-file", required=True)
    args = parser.parse_args(argv)
    ok = compute_recovery_paths(
        repo_root=Path(args.repo_root),
        tmpdir=Path(args.tmpdir),
        prelaunch_porcelain=Path(args.prelaunch_porcelain),
        postlaunch_porcelain=Path(args.postlaunch_porcelain),
        prelaunch_digests=Path(args.prelaunch_digests),
        out_file=Path(args.out_file),
    )
    return 0 if ok else 1


def _commit_usage_fail(error: str) -> int:
    _err("Usage: implement commit --message MSG [--pathspec-from-file PATH [--pathspec-file-nul]] [files...]")
    _err("HINT: --stage-all belongs to review-and-fix commit-fixes (Step 5 review fixes); implementation commits name specific files or use --pathspec-from-file.")
    _emit_kv("COMMITTED", "false")
    _emit_kv("SHA", "")
    _emit_kv("ERROR", error)
    return 2


def commit_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    argv_list = list(argv if argv is not None else sys.argv[1:])
    known_flags = {"--message", "-m", "--pathspec-from-file", "--pathspec-file-nul", "--help", "-h"}
    idx = 0
    while idx < len(argv_list):
        arg = argv_list[idx]
        if arg in ("--help", "-h"):
            argparse.ArgumentParser(prog="cli.py implement commit").print_help()
            return 0
        if arg.startswith("-") and arg not in known_flags:
            return _commit_usage_fail(f"unknown option: {arg}")
        if arg in ("--message", "-m", "--pathspec-from-file"):
            if idx + 1 >= len(argv_list) or argv_list[idx + 1].startswith("-"):
                return _commit_usage_fail(f"{arg} requires a value")
            idx += 2
            continue
        if arg == "--pathspec-file-nul":
            idx += 1
            continue
        idx += 1
    parser = argparse.ArgumentParser(prog="cli.py implement commit", add_help=True)
    parser.add_argument("--message", "-m", default="")
    parser.add_argument("--pathspec-from-file", default="")
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args(argv_list)
    if not args.message.strip():
        return _commit_usage_fail("--message is required")

    env_file = Path(os.environ.get("IMPLEMENT_TMPDIR", "")) / "session-env.sh" if os.environ.get("IMPLEMENT_TMPDIR") else None
    if env_file and env_file.is_file():
        for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
            if not os.environ.get(key):
                value = _session_get(env_file, key, "")
                if value:
                    os.environ[key] = value
    _invoke_cli(["token", "mark", "Step 4 — commit implementation"])
    env = os.environ.copy()
    env["LARCH_TIMING_SKILL"] = "implement"
    subprocess.run([sys.executable, str(_current_cli_path()), "timing", "mark", "Step 4 — commit implementation"], env=env, check=False)

    git_commit = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(_PLUGIN_ROOT))) / "scripts" / "git-commit.sh"
    commit_args = [str(git_commit), "-m", args.message]
    if args.pathspec_from_file:
        commit_args.extend(["--only", "--pathspec-from-file", args.pathspec_from_file])
        if args.pathspec_file_nul:
            commit_args.append("--pathspec-file-nul")
    else:
        commit_args.extend(args.files)
    result = _run(commit_args)
    if result.returncode == 0:
        sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        _emit_kv("COMMITTED", "true")
        _emit_kv("SHA", sha)
        return 0
    error = (result.stderr or result.stdout).replace("\n", " ")[:500]
    _emit_kv("COMMITTED", "false")
    _emit_kv("SHA", "")
    _emit_kv("ERROR", error)
    return result.returncode


def run_dispatch_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement run-dispatch")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--coder", required=True)
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)
    tmp_arg = Path(args.implement_tmpdir)
    if not tmp_arg.is_dir():
        _err(f"implement run-dispatch: --implement-tmpdir not a directory: {tmp_arg}")
        return 2
    tmpdir = tmp_arg.resolve()
    session_env = tmpdir / "session-env.sh"
    feature_file = tmpdir / "feature-description.txt"
    plan_file = tmpdir / "plan.txt"
    if not session_env.is_file():
        _err(f"implement run-dispatch: session-env not readable: {session_env}")
        return 2
    if not feature_file.is_file():
        _err(f"implement run-dispatch: feature file not found: {feature_file}")
        return 2
    if not plan_file.is_file():
        _err(f"implement run-dispatch: plan file not found at conventional path: {plan_file}")
        return 2
    if args.answers and not Path(args.answers).is_file():
        _err(f"implement run-dispatch: --answers path does not exist: {args.answers}")
        return 2
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or _session_get(session_env, "LARCH_CLAUDE_PLUGIN_ROOT", "") or str(_PLUGIN_ROOT)
    if not Path(plugin_root).is_dir():
        _err(f"implement run-dispatch: plugin root not a directory: {plugin_root}")
        return 2
    cursor_binary_found = _binary_available(session_env, "CURSOR_BINARY_FOUND", "cursor")
    codex_binary_found = _binary_available(session_env, "CODEX_BINARY_FOUND", "codex")
    if args.coder == "cursor" and cursor_binary_found != "true":
        _err("implement run-dispatch: cursor coder selected at Step 0 but cursor binary is missing; refusing Step 2 dispatch")
        return 2
    if args.coder == "codex" and codex_binary_found != "true":
        _err("implement run-dispatch: codex coder selected at Step 0 but codex binary is missing; refusing Step 2 dispatch")
        return 2
    child = [
        sys.executable,
        str(Path(plugin_root) / "python" / "cli.py"),
        "implement",
        "step2-dispatch",
        "--tmpdir",
        str(tmpdir),
        "--plan-file",
        str(plan_file),
        "--feature-file",
        str(feature_file),
        "--coder",
        args.coder,
        "--cursor-binary-found",
        cursor_binary_found,
        "--codex-binary-found",
        codex_binary_found,
    ]
    if args.answers:
        child.extend(["--answers", args.answers])
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = plugin_root
    env["IMPLEMENT_TMPDIR"] = str(tmpdir)
    result = subprocess.run(child, text=True, capture_output=True, env=env, check=False)
    if result.stdout:
        stream = logging_util.contract_stream()
        stream.write(result.stdout)
        stream.flush()
    if result.stderr:
        _err(result.stderr.rstrip("\n"))
    return result.returncode


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
        _emit_kv("STATUS", "bailed")
        _emit_kv("REASON", reason)
        _emit_kv("TOOL", self.tool_tag)
        if manifest:
            _emit_kv("MANIFEST", str(self.manifest_path))
        if self.transcript_path.exists() and self.transcript_path.stat().st_size > 0:
            _emit_kv("TRANSCRIPT", str(self.transcript_path))
        if self.sidecar_log.exists() and self.sidecar_log.stat().st_size > 0:
            _emit_kv("SIDECAR_LOG", str(self.sidecar_log))
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden")
        return 0


def _clear_external_scout_state(tmpdir: Path) -> None:
    for path in (
        tmpdir / "scout-coder-manifest.json",
        tmpdir / "step2-external-scout-eligible.txt",
        tmpdir / "codex-step2-out" / "scout-coder-manifest.json",
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


def _path_under_submodule(rel: str, roots: Iterable[str]) -> bool:
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
            if _path_under_submodule(rel, roots):
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
    _write_bytes_atomic(st.prelaunch_porcelain, raw)
    index_nonempty = _git(st.repo_root, "diff", "--cached", "--quiet", "--no-ext-diff").returncode != 0
    _write_text_atomic(st.prelaunch_index_flag, f"PRELAUNCH_INDEX_NONEMPTY={str(index_nonempty).lower()}\n")
    parsed = _parse_porcelain_z(st.prelaunch_porcelain)
    lines: list[str] = []
    for rel in sorted(parsed.paths):
        full = st.repo_root / rel
        try:
            digest = hashlib.sha256(full.read_bytes()).hexdigest()
        except OSError:
            digest = "missing"
        lines.append(f"{digest}\t{rel}")
    _write_text_atomic(st.prelaunch_digests, "\n".join(lines) + ("\n" if lines else ""))


def _manifest_legacy_fingerprint(obj: object) -> bool:
    return isinstance(obj, dict) and "schema_version" not in obj and set(obj.keys()) <= {"status", "summary", "checks"}


def _json_load(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _emit_manifest_invalid_or_recover(st: DispatchState, status: str, raw_obj: object | None) -> int:
    if not isinstance(raw_obj, dict):
        return st.emit_bailed("manifest-schema-invalid")
    if status != "complete" and not (status == "" and _manifest_legacy_fingerprint(raw_obj)):
        return st.emit_bailed("manifest-schema-invalid")
    prelaunch_index_nonempty = "false"
    if st.prelaunch_index_flag.is_file():
        for line in st.prelaunch_index_flag.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("PRELAUNCH_INDEX_NONEMPTY="):
                prelaunch_index_nonempty = line.split("=", 1)[1]
                break
    if prelaunch_index_nonempty == "true":
        return st.emit_bailed("manifest-schema-invalid")
    post = _git(st.repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all", binary=True).stdout
    _write_bytes_atomic(st.postlaunch_porcelain, post)
    ok = compute_recovery_paths(
        repo_root=st.repo_root,
        tmpdir=st.tmpdir,
        prelaunch_porcelain=st.prelaunch_porcelain,
        postlaunch_porcelain=st.postlaunch_porcelain,
        prelaunch_digests=st.prelaunch_digests,
        out_file=st.recovery_paths_file,
    )
    if not ok:
        return st.emit_bailed("manifest-schema-invalid")
    roots = _submodule_roots(st.repo_root)
    for rel in st.recovery_paths_file.read_bytes().split(b"\0"):
        if not rel:
            continue
        path = rel.decode("utf-8", "surrogateescape")
        if _path_under_submodule(path, roots):
            return st.emit_bailed("submodule-dirty")
    reason = _post_implementer_safety_reason(st)
    if reason:
        return st.emit_bailed(reason)
    invalid = st.tmpdir / "manifest-raw.invalid.json"
    if st.manifest_raw_path.exists():
        st.manifest_raw_path.replace(invalid)
    _write_text_atomic(
        st.tmpdir / "recovery-metadata.json",
        json.dumps(
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
    _emit_kv("STATUS", "claude_fallback")
    _emit_kv("TOOL", st.tool_tag)
    if st.transcript_path.exists() and st.transcript_path.stat().st_size > 0:
        _emit_kv("TRANSCRIPT", str(st.transcript_path))
    if st.sidecar_log.exists() and st.sidecar_log.stat().st_size > 0:
        _emit_kv("SIDECAR_LOG", str(st.sidecar_log))
    _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed")
    _emit_kv("RECOVERY_FROM", "manifest-schema-invalid")
    _emit_kv("RECOVERY_PRIOR_TOOL", st.tool_tag)
    _emit_kv("RECOVERY_PATHS_FILE", str(st.recovery_paths_file))
    _clear_external_scout_state(st.tmpdir)
    return 0


def _manifest_complete_salvageable(path: Path) -> bool:
    obj = _json_load(path)
    return isinstance(obj, dict) and str(obj.get("schema_version", "")) == "1" and obj.get("status") == "complete"


def _normalize_scout(st: DispatchState) -> None:
    st.scout_status = "ok"
    result = _invoke_cli(["scout", "filter-manifest", str(st.launch_scout_manifest), str(st.scout_coder_manifest), "--max-archetypes", "3"])
    kv = _parse_kv(result.stdout)
    ok = result.returncode == 0 and kv.get("SCOUT_STATUS") in {"ok", "empty"}
    obj = _json_load(st.scout_coder_manifest) if st.scout_coder_manifest.exists() else None
    if not ok or not isinstance(obj, dict) or not isinstance(obj.get("archetypes"), list):
        _write_text_atomic(st.scout_coder_manifest, '{"archetypes":[]}\n')
        st.scout_status = "missing-or-invalid"
    _write_text_atomic(st.external_scout_marker, "eligible\n")
    _write_text_atomic(st.tmpdir / "step2-scout-coder-status.env", f"SCOUT_CODER_STATUS={st.scout_status}\nSCOUT_CODER_MANIFEST={st.scout_coder_manifest}\n")


def _validate_manifest_paths(st: DispatchState, obj: dict[str, Any]) -> str:
    roots = _submodule_roots(st.repo_root)
    paths = [
        item["path"]
        for item in obj.get("files_touched", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    ]
    paths.extend(item for item in obj.get("tests_added_or_modified", []) if isinstance(item, str))
    for p in paths:
        if "\x00" in p or p.startswith("/") or ".." in p or _path_under_submodule(p, roots):
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
        out = []
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


def _append_materialize_oos_failure(st: DispatchState, log: Path, exit_code: int) -> None:
    _invoke_cli([
        "run-log",
        "append-failure",
        "--log",
        str(st.tmpdir / "execution-issues.md"),
        "--site",
        "step2-materialize-manifest-oos",
        "--tool",
        "materialize-manifest-oos.sh",
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
    if count_str.isdigit() and int(count_str) > 0:
        return True
    return materialize_failed and oos_nonempty


def _materialize_oos(st: DispatchState, *, oos_observations_nonempty: bool = False) -> str:
    helper = st.plugin_root / "skills" / "implement" / "scripts" / "materialize-manifest-oos.sh"
    log = st.tmpdir / "materialize-manifest-oos.log"
    count = subprocess.run(
        [BASH_BIN, str(helper), "--count-only", "--manifest-path", str(st.manifest_path), "--implement-tmpdir", str(st.tmpdir)],
        capture_output=True,
        text=True,
        check=False,
    )
    count_str = count.stdout.strip()
    helper_runnable = helper.is_file() and os.access(helper, os.X_OK)
    if not helper_runnable:
        log.write_text(f"materialize helper missing or not executable: {helper}\n", encoding="utf-8")
        _append_materialize_oos_failure(st, log, 127)
        if _oos_materialize_should_bail(count_rc=count.returncode, count_str=count_str, oos_nonempty=oos_observations_nonempty, materialize_failed=True):
            return "manifest-oos-materialization-failed"
        return ""
    result = subprocess.run(
        [BASH_BIN, str(helper), "--manifest-path", str(st.manifest_path), "--implement-tmpdir", str(st.tmpdir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    log.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        _append_materialize_oos_failure(st, log, result.returncode)
        if _oos_materialize_should_bail(
            count_rc=count.returncode,
            count_str=count_str,
            oos_nonempty=oos_observations_nonempty,
            materialize_failed=True,
        ):
            return "manifest-oos-materialization-failed"
    return ""


def _dispatch_state(args: argparse.Namespace, repo_root: Path, tmpdir: Path, plugin_root: Path) -> DispatchState:
    tool = args.coder
    manifest_path = tmpdir / "manifest.json"
    qa_pending_path = tmpdir / "qa-pending.json"
    transcript = tmpdir / f"{tool}-impl-transcript.txt"
    launch_scout = tmpdir / "scout-coder-manifest.json"
    if tool == "codex":
        out_dir = tmpdir / "codex-step2-out"
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / "manifest.json"
        qa_pending_path = out_dir / "qa-pending.json"
        transcript = out_dir / f"{tool}-impl-transcript.txt"
        launch_scout = out_dir / "scout-coder-manifest.json"
    return DispatchState(
        repo_root=repo_root,
        tmpdir=tmpdir,
        plan_file=Path(args.plan_file),
        feature_file=Path(args.feature_file),
        coder=tool,
        cursor_present=args.cursor_present or "false",
        cursor_binary_found=args.cursor_binary_found or "",
        codex_binary_found=args.codex_binary_found or "",
        answers_file=Path(args.answers) if args.answers else None,
        plugin_root=plugin_root,
        tool_tag=tool,
        manifest_path=manifest_path,
        manifest_raw_path=tmpdir / "manifest-raw.json",
        qa_pending_path=qa_pending_path,
        transcript_path=transcript,
        sidecar_log=tmpdir / f"{tool}-impl.log",
        scout_coder_manifest=tmpdir / "scout-coder-manifest.json",
        launch_scout_manifest=launch_scout,
        external_scout_marker=tmpdir / "step2-external-scout-eligible.txt",
        baseline_file=tmpdir / "step2-baseline.txt",
        prelaunch_porcelain=tmpdir / "step2-prelaunch-porcelain.nul",
        postlaunch_porcelain=tmpdir / "step2-postlaunch-porcelain.nul",
        prelaunch_digests=tmpdir / "step2-prelaunch-content-digests.txt",
        prelaunch_index_flag=tmpdir / "step2-prelaunch-index.env",
        recovery_paths_file=tmpdir / "step2-recovery-paths.nul",
        resume_count_file=tmpdir / f"{tool}-resume-count.txt",
        spawn_branch_file=tmpdir / "step2-spawn-branch.txt",
        spawn_coder_file=tmpdir / "step2-spawn-coder.txt",
        runtime_failure_token=f"{tool}-runtime-failure",
        bailed_no_reason_token=f"{tool}-bailed-no-reason",
        requires_head_unchanged=(tool == "cursor"),
        nonzero_exit_warn_token="WARN_CODEX_NONZERO_EXIT" if tool == "codex" else "",
    )


def _launcher_args(st: DispatchState) -> list[str]:
    args = [
        "agent",
        f"launch-{st.tool_tag}-implement",
        "--transcript-path",
        str(st.transcript_path),
        "--sidecar-log",
        str(st.sidecar_log),
        "--manifest-path",
        str(st.manifest_path),
        "--qa-pending-path",
        str(st.qa_pending_path),
        "--scout-manifest-path",
        str(st.launch_scout_manifest),
        "--plan-file",
        str(st.plan_file),
        "--feature-file",
        str(st.feature_file),
        "--agent-prompt",
        str(st.plugin_root / "agents" / f"{st.tool_tag}-implementer.md"),
        "--timeout",
        "7200",
    ]
    cap = os.environ.get("LARCH_TOKEN_BUDGET_CAP_IMPLEMENT", "")
    if cap:
        args.extend(["--token-budget-cap", cap])
    if st.answers_file is not None:
        args.extend(["--answers-file", str(st.answers_file)])
    return args


def _run_launcher(st: DispatchState) -> tuple[int, dict[str, str], str]:
    result = _invoke_cli(_launcher_args(st), cwd=st.repo_root)
    out = (result.stdout or "")[:65536]
    return result.returncode, _parse_kv(out), out + (result.stderr or "")


def _append_warning(st: DispatchState, text: str) -> None:
    _invoke_cli(["run-log", "append-entry", "--log", str(st.tmpdir / "execution-issues.md"), "--category", "Warnings", "--entry", text])


def step2_dispatch_main(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="cli.py")
    parser = argparse.ArgumentParser(prog="cli.py implement step2-dispatch")
    parser.add_argument("--tmpdir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--feature-file", required=True)
    parser.add_argument("--coder", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--cursor-present", default="")
    parser.add_argument("--codex-present", default="")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--codex-binary-found", default="")
    parser.add_argument("--cursor-binary-found", default="")
    parser.add_argument("--answers", default="")
    args = parser.parse_args(argv)

    if args.coder and args.codex_available:
        _err("implement step2-dispatch: --coder and --codex-available are mutually exclusive")
        return 2
    if args.codex_available:
        if args.codex_available == "true":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder codex instead")
            args.coder = "codex"
        elif args.codex_available == "false":
            _err("implement step2-dispatch: WARNING: --codex-available is deprecated; pass --coder claude instead")
            args.coder = "claude"
        else:
            _err(f"implement step2-dispatch: --codex-available must be 'true' or 'false', got: {args.codex_available}")
            return 2
    if not args.coder:
        _err("implement step2-dispatch: --coder is required")
        return 2
    if args.coder not in _SAFE_CODERS:
        _err(f"implement step2-dispatch: --coder must be one of {{claude,codex,cursor}}, got: {args.coder}")
        return 2
    for flag_name in ("codex_present", "cursor_present", "cursor_available", "codex_binary_found", "cursor_binary_found"):
        value = getattr(args, flag_name)
        if value and value not in {"true", "false"}:
            _err(f"implement step2-dispatch: --{flag_name.replace('_', '-')} must be 'true', 'false', or empty, got: {value}")
            return 2
    tmpdir_raw = Path(args.tmpdir)
    if not tmpdir_raw.is_dir():
        _err(f"implement step2-dispatch: --tmpdir not a directory: {tmpdir_raw}")
        return 2
    tmpdir = tmpdir_raw.resolve()
    os.environ["IMPLEMENT_TMPDIR"] = str(tmpdir)
    if (tmpdir / "session-id").is_file():
        session_id = (tmpdir / "session-id").read_text(encoding="utf-8", errors="replace").strip()
        if session_id:
            os.environ["LARCH_TOKEN_SESSION_ID"] = session_id
    if (tmpdir / "claude-source.env").is_file():
        os.environ["LARCH_CLAUDE_SOURCE_FILE"] = str(tmpdir / "claude-source.env")
    if not Path(args.plan_file).is_file():
        _err(f"implement step2-dispatch: --plan-file not found: {args.plan_file}")
        return 2
    if not Path(args.feature_file).is_file():
        _err(f"implement step2-dispatch: --feature-file not found: {args.feature_file}")
        return 2
    if args.coder == "claude":
        _clear_external_scout_state(tmpdir)
        _emit_kv("STATUS", "claude_fallback")
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed")
        return 0
    session_env = tmpdir / "session-env.sh"
    if not args.cursor_binary_found:
        args.cursor_binary_found = _binary_available(session_env, "CURSOR_BINARY_FOUND", "cursor")
    if not args.codex_binary_found:
        args.codex_binary_found = _binary_available(session_env, "CODEX_BINARY_FOUND", "codex")
    if args.coder == "cursor" and args.cursor_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv("STATUS", "claude_fallback")
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed")
        return 0
    if args.coder == "codex" and args.codex_binary_found != "true":
        _clear_external_scout_state(tmpdir)
        _emit_kv("STATUS", "claude_fallback")
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "allowed")
        return 0

    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("LARCH_CLAUDE_PLUGIN_ROOT") or _PLUGIN_ROOT).resolve()
    repo_result = _run(["git", "rev-parse", "--show-toplevel"])
    if repo_result.returncode != 0 or not repo_result.stdout.strip():
        _err("implement step2-dispatch: must be invoked from within a git working tree (git rev-parse --show-toplevel failed)")
        return 2
    repo_root = Path(repo_result.stdout.strip()).resolve()
    _invoke_cli(["timing", "mark", "Step 2 — implementation"], cwd=repo_root)
    st = _dispatch_state(args, repo_root, tmpdir, plugin_root)
    if not (plugin_root / "agents" / f"{st.tool_tag}-implementer.md").is_file():
        _err(f"implement step2-dispatch: agent prompt missing: {plugin_root / 'agents' / (st.tool_tag + '-implementer.md')}")
        return 2

    if st.spawn_coder_file.is_file():
        if st.spawn_coder_file.read_text(encoding="utf-8", errors="replace").strip() != st.coder:
            return st.emit_bailed("coder-mismatch-tmpdir-reuse")
    else:
        _write_text_atomic(st.spawn_coder_file, st.coder + "\n")
    if not st.baseline_file.is_file():
        _write_text_atomic(st.baseline_file, _git_stdout(repo_root, "rev-parse", "HEAD") + "\n")
    st.baseline_sha = st.baseline_file.read_text(encoding="utf-8", errors="replace").strip()
    if not st.spawn_branch_file.is_file():
        _write_text_atomic(st.spawn_branch_file, _git_stdout(repo_root, "symbolic-ref", "-q", "--short", "HEAD") + "\n")
    st.spawn_branch = st.spawn_branch_file.read_text(encoding="utf-8", errors="replace").strip()
    session_env = tmpdir / "session-env.sh"
    parent_issue = tmpdir / "parent-issue.md"
    issue_from_parent = _session_get(parent_issue, "ISSUE_NUMBER", "") if parent_issue.is_file() else ""
    forked_target = _session_get(session_env, "FORKED_TARGET", "false") if session_env.is_file() else "false"
    issue_anchored = bool(issue_from_parent) or session_env.is_file()
    if forked_target != "true" and issue_anchored and (not st.spawn_branch or st.spawn_branch == "HEAD"):
        return st.emit_bailed("detached-head-prohibited")
    if forked_target != "true" and issue_anchored and st.spawn_branch in {"main", "master"}:
        return st.emit_bailed("main-branch-prohibited")

    resume_count = 0
    if st.resume_count_file.is_file():
        raw = st.resume_count_file.read_text(encoding="utf-8", errors="replace").strip()
        if raw.isdigit():
            resume_count = int(raw)
        else:
            return st.emit_bailed("manifest-schema-invalid")
    if st.answers_file is not None:
        if not st.answers_file.is_file():
            _err(f"implement step2-dispatch: --answers given but path does not exist: {st.answers_file}")
            return 2
        resume_count += 1
        _write_text_atomic(st.resume_count_file, f"{resume_count}\n")
    if resume_count > RESUME_CAP:
        return st.emit_bailed("qa-loop-exceeded")

    for path in (st.manifest_path, st.manifest_raw_path, st.qa_pending_path, st.transcript_path, st.sidecar_log, st.launch_scout_manifest):
        with contextlib.suppress(OSError):
            path.unlink()
    _clear_external_scout_state(tmpdir)
    _write_prelaunch_baseline(st)

    wrapper_rc, kv, _ = _run_launcher(st)
    if wrapper_rc == WRAPPER_VALIDATION_RC:
        return st.emit_bailed("wrapper-validation-failure")
    launcher_exit = kv.get("LAUNCHER_EXIT", "99")
    manifest_written = kv.get("MANIFEST_WRITTEN", "false")
    launcher_status = kv.get("STATUS", "")
    if launcher_status == "cap_hit":
        return st.emit_bailed("cap_hit")
    if (wrapper_rc != 0 or manifest_written != "true" or launcher_exit != "0") and manifest_written != "true":
        dirty = _git_stdout(repo_root, "status", "--porcelain")
        index_lock = repo_root / ".git" / "index.lock"
        current_head = _git_stdout(repo_root, "rev-parse", "HEAD")
        if dirty or index_lock.exists() or current_head != st.baseline_sha:
            return st.emit_bailed("dirty-state-after-timeout")
        wrapper_rc, kv, _ = _run_launcher(st)
        if wrapper_rc == WRAPPER_VALIDATION_RC:
            return st.emit_bailed("wrapper-validation-failure")
        launcher_exit = kv.get("LAUNCHER_EXIT", "99")
        manifest_written = kv.get("MANIFEST_WRITTEN", "false")
        launcher_status = kv.get("STATUS", "")
        if launcher_status == "cap_hit":
            return st.emit_bailed("cap_hit")
    if wrapper_rc != 0:
        return st.emit_bailed(st.runtime_failure_token)
    if manifest_written != "true":
        return st.emit_bailed(st.runtime_failure_token)
    warn_nonzero = False
    if launcher_exit != "0":
        if st.coder == "codex" and _manifest_complete_salvageable(st.manifest_path):
            warn_nonzero = True
            _append_warning(st, f"Step 4 — {st.tool_tag} exited non-zero (LAUNCHER_EXIT={launcher_exit}) after atomically writing a complete manifest; not discarding it — continuing to validation/commit ({st.nonzero_exit_warn_token}=true). A self-verification step likely failed after the implementation work completed.")
        else:
            return st.emit_bailed(st.runtime_failure_token)

    if not st.manifest_path.is_file() or st.manifest_path.stat().st_size == 0:
        return st.emit_bailed("manifest-missing")
    shutil.copyfile(st.manifest_path, st.manifest_raw_path)
    raw_obj = _json_load(st.manifest_raw_path)
    status = raw_obj.get("status", "") if isinstance(raw_obj, dict) and isinstance(raw_obj.get("status", ""), str) else ""
    schema_version = raw_obj.get("schema_version", "") if isinstance(raw_obj, dict) else ""
    if schema_version and str(schema_version) != "1":
        return st.emit_bailed("manifest-schema-invalid")
    if str(schema_version) != "1":
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    if status not in {"complete", "needs_qa", "bailed"}:
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    assert isinstance(raw_obj, dict)
    if status == "complete":
        if not _complete_schema_valid(raw_obj):
            return _emit_manifest_invalid_or_recover(st, status, raw_obj)
    elif status == "needs_qa":
        nq = raw_obj.get("needs_qa")
        questions = nq.get("questions") if isinstance(nq, dict) else None
        if not (isinstance(questions, list) and questions):
            repaired = False
            qa_obj = _json_load(st.qa_pending_path)
            if isinstance(qa_obj, dict) and isinstance(qa_obj.get("items"), list) and qa_obj["items"]:
                repaired_questions = []
                for idx, item in enumerate(qa_obj["items"]):
                    if isinstance(item, dict):
                        parts = [f"{label}: {item[key]}" for key, label in (("area", "Area"), ("risk", "Risk"), ("suggested_check", "Suggested check")) if item.get(key)]
                        repaired_questions.append({"id": f"q{idx + 1}", "text": ". ".join(parts)})
                if repaired_questions:
                    _write_text_atomic(st.qa_pending_path, json.dumps({"questions": repaired_questions}) + "\n")
                    repaired = True
            if not repaired:
                return st.emit_bailed("manifest-schema-invalid")
        qa_obj = _json_load(st.qa_pending_path)
        if not (isinstance(qa_obj, dict) and isinstance(qa_obj.get("questions"), list) and qa_obj["questions"]):
            return st.emit_bailed("qa-pending-missing")
    elif status == "bailed" and (not isinstance(raw_obj.get("bail_reason"), str) or not raw_obj["bail_reason"]):
        return _emit_manifest_invalid_or_recover(st, status, raw_obj)

    if status != "bailed":
        reason = _post_implementer_safety_reason(st)
        if reason:
            return st.emit_bailed(reason)
        _normalize_scout(st)

    if status == "complete":
        invalid = _validate_manifest_paths(st, raw_obj)
        if invalid:
            return st.emit_bailed(invalid)
        # Diagnostic-only undeclared path warning.
        wt = set(_git_stdout(repo_root, "diff", "--name-only", "HEAD").splitlines()) | set(_git_stdout(repo_root, "ls-files", "--others", "--exclude-standard").splitlines())
        declared = {item.get("path") for item in raw_obj.get("files_touched", []) if isinstance(item, dict)} | {p for p in raw_obj.get("tests_added_or_modified", []) if isinstance(p, str)}
        missing = sorted(p for p in wt if p and p not in declared)
        if missing:
            _append_warning(st, f"Step 7a.1 — {len(missing)} working-tree path(s) not declared in manifest files_touched/tests_added_or_modified (may include pre-existing dirty files). First 5:\n" + "\n".join(f"- {p}" for p in missing[:5]))
        commit_msg = redact.redact_secrets_only(str(raw_obj["commit_message"]))
        commit_msg_file = st.tmpdir / f"{st.tool_tag}-commit-message.txt"
        _write_text_atomic(commit_msg_file, commit_msg)
        commit_stderr = st.tmpdir / f"{st.tool_tag}-commit-stderr.txt"
        add = subprocess.run(
            [GIT_BIN, "-C", str(repo_root), "add", "-A"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if add.returncode != 0:
            commit_stderr.write_text(add.stderr or "git add failed", encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        commit = subprocess.run(
            [GIT_BIN, "-C", str(repo_root), "commit", "-F", str(commit_msg_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False
        )
        if commit.returncode != 0:
            commit_stderr.write_text(commit.stderr, encoding="utf-8", errors="replace")
            with contextlib.suppress(OSError):
                st.manifest_path.unlink()
            with contextlib.suppress(OSError):
                st.manifest_raw_path.unlink()
            return st.emit_bailed("commit-failed")
        with contextlib.suppress(OSError):
            commit_stderr.unlink()
        _invoke_cli(["run-log", "flush"], cwd=repo_root)

    sanitized = _sanitize_manifest_obj(raw_obj)
    _write_text_atomic(st.manifest_path, json.dumps(sanitized, indent=2, sort_keys=False) + "\n")
    if status == "complete":
        oos_obs = raw_obj.get("oos_observations")
        oos_nonempty = isinstance(oos_obs, list) and bool(oos_obs)
        reason = _materialize_oos(st, oos_observations_nonempty=oos_nonempty)
        if reason:
            return st.emit_bailed(reason)

    if status == "complete":
        _emit_kv("STATUS", "complete")
        _emit_kv("TOOL", st.tool_tag)
        _emit_kv("MANIFEST", str(st.manifest_path))
        _emit_kv("TRANSCRIPT", str(st.transcript_path))
        _emit_kv("SIDECAR_LOG", str(st.sidecar_log))
        _emit_kv("SCOUT_CODER_MANIFEST", str(st.scout_coder_manifest))
        _emit_kv("SCOUT_CODER_STATUS", st.scout_status)
        if warn_nonzero and st.nonzero_exit_warn_token:
            _emit_kv(st.nonzero_exit_warn_token, "true")
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden")
    elif status == "needs_qa":
        _emit_kv("STATUS", "needs_qa")
        _emit_kv("TOOL", st.tool_tag)
        _emit_kv("MANIFEST", str(st.manifest_path))
        _emit_kv("QA_PENDING", str(st.qa_pending_path))
        _emit_kv("TRANSCRIPT", str(st.transcript_path))
        _emit_kv("SIDECAR_LOG", str(st.sidecar_log))
        _emit_kv("SCOUT_CODER_MANIFEST", str(st.scout_coder_manifest))
        _emit_kv("SCOUT_CODER_STATUS", st.scout_status)
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden")
    else:
        reason = str(raw_obj.get("bail_reason") or st.bailed_no_reason_token)
        reason = re.sub(r"\s+", " ", "".join(ch for ch in reason if ch >= " " and ch != "\x7f")).strip()[:200] or st.bailed_no_reason_token
        _emit_kv("STATUS", "bailed")
        _emit_kv("REASON", reason)
        _emit_kv("TOOL", st.tool_tag)
        _emit_kv("MANIFEST", str(st.manifest_path))
        _emit_kv("TRANSCRIPT", str(st.transcript_path))
        _emit_kv("SIDECAR_LOG", str(st.sidecar_log))
        _emit_kv("ORCHESTRATOR_EDIT_AUTHORITY", "forbidden")
    return 0
