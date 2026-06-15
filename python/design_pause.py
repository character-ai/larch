"""Python CLI entrypoints for /design pause save/load."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence

import gh
import proc


_PAUSE_START = "<!-- larch:design-pause:start -->"
_PAUSE_END = "<!-- larch:design-pause:end -->"
_PLAN_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_RUN_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _parse_args(argv: Sequence[str]) -> dict[str, str] | None:
    args = list(argv)
    out = {"--design-tmpdir": "", "--issue": "", "--repo": ""}
    i = 0
    while i < len(args):
        token = args[i]
        if token in out:
            if i + 1 >= len(args):
                return None
            out[token] = args[i + 1]
            i += 2
            continue
        if token in {"-h", "--help"}:
            return {}
        return None
    if not out["--design-tmpdir"] or not out["--issue"]:
        return None
    return out


def _source_env_get(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    prefix = f"export {key}="
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip("'\"")
    return ""


def _resolve_repo(repo_arg: str, source_env: Path) -> str:
    if repo_arg:
        return repo_arg
    from_source = _source_env_get(source_env, "REPO")
    if from_source:
        return from_source
    return gh.resolve_repo_gh_only(proc) or ""


def _determine_step(design_tmpdir: Path, plugin_root: Path) -> str:
    completed = design_tmpdir / ".completed"
    if (design_tmpdir / ".step3-reentry").is_file():
        return "3"
    if (completed / "step-3").is_file() and (completed / "step-3.5").is_file() and not (completed / "step-3b").is_file():
        return "3b"
    if (completed / "step-3").is_file() and not (completed / "step-3.5").is_file():
        return "3.5"
    if (completed / "step-5b").is_file() and not (completed / "step-5c").is_file():
        return "5c"
    registry = plugin_root / "skills" / "design" / "scripts" / "step-name-registry.tsv"
    if not registry.is_file():
        return "6"
    for line in registry.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("step\t"):
            continue
        step = line.split("\t", 1)[0]
        if step in {"0", "5"}:
            continue
        if not (completed / f"step-{step}").is_file():
            return step
    return "6"


def _strip_pause_markers(body: str) -> str:
    out: list[str] = []
    inside = False
    for line in body.splitlines():
        if line.strip() == _PAUSE_START:
            inside = True
            continue
        if line.strip() == _PAUSE_END:
            inside = False
            continue
        if not inside:
            out.append(line)
    return "\n".join(out) + ("\n" if body.endswith("\n") else "")


def _parse_pause_payload(body: str) -> dict[str, str] | None:
    start = body.find(_PAUSE_START)
    end = body.find(_PAUSE_END)
    if start < 0 and end < 0:
        return None
    if start < 0 or end < 0 or end < start:
        return {}
    payload = body[start + len(_PAUSE_START):end]
    data: dict[str, str] = {}
    for line in payload.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _emit(kv: list[tuple[str, str]]) -> None:
    for key, value in kv:
        print(f"{key}={value}")


def pause_save_main(argv: Sequence[str]) -> int:
    parsed = _parse_args(argv)
    if parsed is None:
        print("Usage: design-pause-save.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]")
        return 1
    if parsed == {}:
        return 0
    design_tmpdir = Path(parsed["--design-tmpdir"])
    if not design_tmpdir.is_dir():
        _emit([("PAUSE_OK", "false"), ("ERROR", "tmpdir-missing")])
        return 0
    issue = parsed["--issue"]
    if not issue.isdigit() or issue == "0":
        _emit([("PAUSE_OK", "false"), ("ERROR", "invalid-issue")])
        return 0
    plugin_root = Path(__file__).resolve().parents[1]
    source_env = design_tmpdir / "source-env.sh"
    repo = _resolve_repo(parsed["--repo"], source_env)
    if repo and not _PLAN_RE.fullmatch(repo):
        _emit([("PAUSE_OK", "false"), ("ERROR", "invalid-repo")])
        return 0
    run_id = _source_env_get(source_env, "SESSION_ID") or os.environ.get("SESSION_ID", "")
    if not run_id or not _RUN_RE.fullmatch(run_id):
        _emit([("PAUSE_OK", "false"), ("ERROR", "invalid-run-id")])
        return 0

    step = _determine_step(design_tmpdir, plugin_root)
    body = gh.issue_view_body(proc, issue, repo=repo or gh.resolve_repo(proc) or "")
    stripped = _strip_pause_markers(body)
    body_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    brainstorm_done = "true" if (design_tmpdir / ".brainstorm-done").is_file() else "false"
    state_lines = [
        f"STEP={step}",
        f"ISSUE_NUMBER={issue}",
        f"SESSION_ID={run_id}",
        f"RUN_ID={run_id}",
        *( [f"REPO={repo}"] if repo else [] ),
        f"BRAINSTORM_DONE={brainstorm_done}",
        f"BODY_HASH={body_hash}",
    ]
    state_file = design_tmpdir / "pause-state.txt"
    _ = state_file.write_text("\n".join(state_lines) + "\n", encoding="utf-8")

    publish = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "design",
            "log-publish",
            "--reason",
            "pause",
            "--design-tmpdir",
            str(design_tmpdir),
            "--run-id",
            run_id,
            "--issue",
            issue,
            *(["--repo", repo] if repo else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    publish_kv: dict[str, str] = {}
    for line in publish.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            publish_kv[key] = value
    if publish_kv.get("PUBLISH_OK") != "true":
        recovery = publish_kv.get("RECOVERY_BRANCH", "")
        if recovery:
            _emit([("PAUSE_OK", "false"), ("ERROR", "publish-local-recovery-only"), ("LOG_RECOVERY_BRANCH", recovery)])
            return 0
        _emit([("PAUSE_OK", "false"), ("ERROR", "publish-and-recovery-failed")])
        return 0

    marker_cmd = [
        sys.executable,
        str(plugin_root / "python" / "cli.py"),
        "named-block",
        "write",
        "--marker",
        "design-pause",
        "--content-file",
        str(state_file),
        "--issue",
        issue,
        *(["--repo", repo] if repo else []),
    ]
    marker = subprocess.run(marker_cmd, check=False)
    if marker.returncode != 0:
        _emit([("PAUSE_OK", "false"), ("ERROR", "marker-write-failed")])
        return 0
    (design_tmpdir / ".pause-requested").unlink(missing_ok=True)
    _ = (design_tmpdir / ".pause-save-complete").write_text("", encoding="utf-8")
    _emit([("PAUSE_OK", "true"), ("STEP", step), ("RUN_ID", run_id)])
    return 0


def pause_load_main(argv: Sequence[str]) -> int:
    parsed = _parse_args(argv)
    if parsed is None:
        print("Usage: design-pause-load.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]")
        return 1
    if parsed == {}:
        return 0
    design_tmpdir = Path(parsed["--design-tmpdir"])
    design_tmpdir.mkdir(parents=True, exist_ok=True)
    issue = parsed["--issue"]
    if not issue.isdigit() or issue == "0":
        _emit([("LOAD_OK", "false"), ("ERROR", "invalid-issue")])
        return 0
    repo = parsed["--repo"] or gh.resolve_repo(proc) or ""
    if repo and not _PLAN_RE.fullmatch(repo):
        _emit([("LOAD_OK", "false"), ("ERROR", "invalid-repo")])
        return 0
    body = gh.issue_view_body(proc, issue, repo=repo or gh.resolve_repo(proc) or "")
    payload = _parse_pause_payload(body)
    if payload is None:
        _emit([("LOAD_OK", "false"), ("ERROR", "no-pause-marker")])
        return 0
    if payload == {}:
        _emit([("LOAD_OK", "false"), ("ERROR", "malformed-pause-marker")])
        return 0
    run_id = payload.get("RUN_ID", "")
    step = payload.get("STEP", "")
    if payload.get("ISSUE_NUMBER") != issue:
        _emit([("LOAD_OK", "false"), ("ERROR", "issue-mismatch")])
        return 0
    if not _RUN_RE.fullmatch(run_id):
        _emit([("LOAD_OK", "false"), ("ERROR", "invalid-run-id")])
        return 0

    repo_top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S607
    if not repo_top:
        _emit([("LOAD_OK", "false"), ("ERROR", "not-git-worktree")])
        return 0
    recovery_branch = payload.get("LOG_RECOVERY_BRANCH", "")
    if recovery_branch:
        fetch = subprocess.run(["git", "-C", repo_top, "fetch", "origin", recovery_branch], check=False)  # noqa: S607
        if fetch.returncode != 0:
            _emit([("LOAD_OK", "false"), ("ERROR", "snapshot-not-found")])
            return 0
        snapshot_ref = "FETCH_HEAD"
    else:
        default = subprocess.run(
            ["git", "-C", repo_top, "symbolic-ref", "refs/remotes/origin/HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip().replace("refs/remotes/origin/", "") or "main"
        if subprocess.run(["git", "-C", repo_top, "fetch", "origin", default], check=False).returncode != 0:  # noqa: S607
            _emit([("LOAD_OK", "false"), ("ERROR", "snapshot-not-found")])
            return 0
        snapshot_ref = f"origin/{default}"

    restore_tmp = Path(tempfile.mkdtemp(prefix="design-pause-load-restore."))
    try:
        prefix = f"larch-logs/design/{run_id}/"
        ls = subprocess.run(
            ["git", "-C", repo_top, "ls-tree", "-r", "--name-only", snapshot_ref, "--", prefix],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        if ls.returncode != 0:
            _emit([("LOAD_OK", "false"), ("ERROR", "snapshot-extract-failed")])
            return 0
        files = [line.strip() for line in ls.stdout.splitlines() if line.strip()]
        if not files:
            _emit([("LOAD_OK", "false"), ("ERROR", "snapshot-not-found")])
            return 0
        for full_path in files:
            rel = full_path[len(prefix):]
            dest = restore_tmp / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            blob = subprocess.run(
                ["git", "-C", repo_top, "show", f"{snapshot_ref}:{full_path}"],  # noqa: S607
                capture_output=True,
                text=True,
                check=False,
            )
            if blob.returncode != 0:
                _emit([("LOAD_OK", "false"), ("ERROR", "snapshot-extract-failed")])
                return 0
            _ = dest.write_text(blob.stdout, encoding="utf-8")
        for required in ("manifest.json", "run-params.json", "pause-state.txt"):
            if not (restore_tmp / required).is_file():
                _emit([("LOAD_OK", "false"), ("ERROR", "missing-restored-artifact")])
                return 0
        if step not in {"1", "1d", "2", "2b", "3", "3.5", "3b", "4", "5", "5c", "6"}:
            _emit([("LOAD_OK", "false"), ("ERROR", "invalid-step")])
            return 0
        _ = (restore_tmp / ".resume-loaded").write_text("", encoding="utf-8")
        for child in restore_tmp.iterdir():
            target = design_tmpdir / child.name
            if child.is_dir():
                _ = shutil.copytree(child, target, dirs_exist_ok=True)
            else:
                _ = shutil.copy2(child, target)
        (design_tmpdir / ".pause-save-complete").unlink(missing_ok=True)
    finally:
        shutil.rmtree(restore_tmp, ignore_errors=True)

    out: list[tuple[str, str]] = [
        ("LOAD_OK", "true"),
        ("STEP", step),
        ("SESSION_ID", payload.get("SESSION_ID", run_id)),
        ("RUN_ID", run_id),
        ("BRAINSTORM_DONE", payload.get("BRAINSTORM_DONE", "false")),
    ]
    if repo:
        out.append(("REPO", repo))
    _emit(out)
    return 0
