"""Step 0 main-entry helpers: session setup, route, init, clarify, and cleanup."""
# pylint: disable=cyclic-import
# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false, reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable, Mapping, Sequence

from larch.core.ctx import Ctx
from larch.design import design_pause
from larch.git import gh
from larch.core import proc

from larch.design.design_core import _capture_contract_stream_to_paths, _cli_cmd, _append_failure
from larch.design.design_router import _parse_stdout_kv, _write_kv_file
from larch.state import bootstrap
from larch.design.design_step0_env import (
    _emit_parse_kvs,
    _emit_step0_init_rows,
    _emit_step0_route_rows,
    _load_wrapper_env,
    _parse_and_persist,
    _parse_wrapper_args,
    load_bash_quoted_env,
    require_plugin_root,
    INIT_RESULT_KEYS,
    PARSED_ENV_KEYS,
    ROUTE_RESULT_KEYS,
    ROUTE_STATE_KEYS,
    CONFIGURATION_ERROR_RC,
)
from larch.design.design_terminal import _replay_warn_error, phase_driver_read_result_env, stage_terminal_state_core
from larch.git.repo_roots import consumer_repo_root

def _derive_binary_found(env: dict[str, str]) -> None:
    if not env.get("CODEX_BINARY_FOUND"):
        env["CODEX_BINARY_FOUND"] = "true" if shutil.which("codex") else "false"
    if not env.get("CURSOR_BINARY_FOUND"):
        env["CURSOR_BINARY_FOUND"] = "true" if shutil.which("cursor") else "false"




def _run_best_effort(*, command: Sequence[str], env: Mapping[str, str] | None = None) -> None:
    with contextlib.suppress(OSError):
        subprocess.run(list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(env) if env is not None else None, check=False)


def _pause_args(
    *, design_tmpdir: str | Path,
    env: Mapping[str, str] | None = None,
    ctx: Ctx | None = None,
) -> list[str]:
    if ctx is not None:
        issue = ctx.issue_number
        repo = ctx.repo
    elif env is not None:
        issue = env.get("ISSUE_NUMBER", "")
        repo = env.get("REPO", "")
    else:
        issue = os.environ.get("ISSUE_NUMBER", "")
        repo = os.environ.get("REPO", "")
    args = ["--design-tmpdir", str(design_tmpdir), "--issue", issue]
    if repo:
        args.extend(["--repo", repo])
    return args


def _require_design_tmpdir(*, env: Mapping[str, str], design_tmpdir: str | Path | None = None) -> Path:
    raw = str(design_tmpdir or env.get("DESIGN_TMPDIR", ""))
    if not raw:
        print("/design wrapper: DESIGN_TMPDIR required", file=sys.stderr)
        raise SystemExit(1)
    path = Path(raw)
    if not path.is_absolute():
        print("/design wrapper: DESIGN_TMPDIR must be an absolute path", file=sys.stderr)
        raise SystemExit(1)
    if not path.is_dir():
        print(f"/design wrapper: DESIGN_TMPDIR is not an existing directory: {path}", file=sys.stderr)
        raise SystemExit(1)
    return path.resolve()


def _require_design_tmpdir_nonempty(*, env: Mapping[str, str], site: str) -> Path:
    raw = env.get("DESIGN_TMPDIR", "")
    if not raw:
        print(f"/design Step 5b {site}: DESIGN_TMPDIR required", file=sys.stderr)
        raise SystemExit(1)
    return Path(raw)


def check_pause_and_exit(*, env: Mapping[str, str], design_tmpdir: str | Path | None = None) -> None:
    raw = str(design_tmpdir or env.get("DESIGN_TMPDIR", ""))
    if not raw:
        return
    tmpdir = _require_design_tmpdir(env=env, design_tmpdir=design_tmpdir)
    if (tmpdir / ".pause-requested").is_file():
        rc = design_pause.pause_save_main(_pause_args(design_tmpdir=tmpdir, env=env))
        raise SystemExit(rc)


def relay_degraded_tools_gate_stdout(*, stdout: str, design_tmpdir: Path) -> dict[str, str]:
    state = {
        "DEGRADED": "false",
        "BOTH_DOWN": "false",
        "BOTH_DOWN_SEEN": "false",
        "DEGRADED_HARD_FAIL": "false",
        "PRESENCE_INPUT_EMPTY": "false",
    }
    in_explanation = False
    for line in stdout.splitlines():
        if line == "DEGRADED_EXPLANATION_BEGIN":
            in_explanation = True
            print(line)
        elif line == "DEGRADED_EXPLANATION_END":
            in_explanation = False
            print(line)
        elif line.startswith("DEGRADED="):
            state["DEGRADED"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith("BOTH_DOWN="):
            state["BOTH_DOWN"] = line.split("=", 1)[1]
            state["BOTH_DOWN_SEEN"] = "true"
            print(line)
        elif line.startswith("DEGRADED_HARD_FAIL="):
            state["DEGRADED_HARD_FAIL"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith("PRESENCE_INPUT_EMPTY="):
            state["PRESENCE_INPUT_EMPTY"] = line.split("=", 1)[1]
            print(line)
        elif line.startswith(("CODEX_STATE=", "CURSOR_STATE=")) or in_explanation:
            print(line)
    if state["PRESENCE_INPUT_EMPTY"] == "true":
        with contextlib.suppress(OSError):
            with (design_tmpdir / "execution-issues.md").open("a", encoding="utf-8") as handle:
                handle.write("- Step 0 degraded-tools gate: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)\n")
    step0_status = "ok"
    if state["DEGRADED"] == "true":
        if state["BOTH_DOWN_SEEN"] == "true" and state["BOTH_DOWN"] == "true":
            step0_status = "degraded-both-down-hard-fail"
        elif state["BOTH_DOWN_SEEN"] == "true" and state["BOTH_DOWN"] == "false" and (design_tmpdir / ".degraded-tools-gate-prompted").is_file():
            step0_status = "degraded-one-down"
        else:
            step0_status = "needs-degraded-decision"
    state["STEP0_STATUS"] = step0_status
    return state


def step0_session_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    plugin_root = require_plugin_root(ns.plugin_root)
    cache, parsed = _parse_and_persist(ns=ns, plugin_root=plugin_root)
    _emit_parse_kvs(cache=cache, data=parsed)
    _run_best_effort(command=_cli_cmd(plugin_root, "timing", "mark", "design Step 0: session setup"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
    bootstrap._install_statusline_best_effort()
    setup = subprocess.run(
        _cli_cmd(plugin_root, "session", "setup", "--prefix", "claude-design", "--skip-repo-check", "--check-reviewers"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if setup.stdout:
        print(setup.stdout, end="" if setup.stdout.endswith("\n") else "\n")
    if setup.returncode != 0:
        return setup.returncode
    kv = _parse_stdout_kv(setup.stdout)
    design_tmpdir = kv.get("SESSION_TMPDIR", [""])[-1]
    session_id = kv.get("SESSION_ID", [""])[-1]
    if not design_tmpdir or not session_id:
        print("**⚠ /design: session setup output missing SESSION_TMPDIR or SESSION_ID**", file=sys.stderr)
        return 1
    design_path = Path(design_tmpdir)
    (design_path / ".design-step0-parsed.env").write_bytes(cache.read_bytes())
    env: dict[str, str] = {**os.environ, "DESIGN_TMPDIR": design_tmpdir, "IMPLEMENT_TMPDIR": os.environ.get("IMPLEMENT_TMPDIR", "")}
    _run_best_effort(command=_cli_cmd(plugin_root, "token", "mark", "design Step 0: session setup"), env=env)
    codex_binary = kv.get("CODEX_BINARY_FOUND", [""])[-1]
    cursor_binary = kv.get("CURSOR_BINARY_FOUND", [""])[-1]
    repo_root = consumer_repo_root(Path.cwd()) or Path.cwd().resolve()
    wdce = _cli_cmd(plugin_root, "session", "write-design-env", "--output", str(design_path / "source-env.sh"), "--design-tmpdir", design_tmpdir, "--session-id", session_id, "--claude-pid", ns.claude_pid, "--repo-root", str(repo_root))
    if codex_binary:
        wdce.extend(["--codex-binary-found", codex_binary])
    if cursor_binary:
        wdce.extend(["--cursor-binary-found", cursor_binary])
    rc = subprocess.run(wdce, check=False).returncode
    if rc != 0:
        return rc
    gate = subprocess.run(
        _cli_cmd(
            plugin_root,
            "agent",
            "degraded-tools-gate",
            "--skill",
            "design",
            "--codex-present",
            kv.get("CODEX_PRESENT", ["false"])[-1] or "false",
            "--cursor-present",
            kv.get("CURSOR_PRESENT", ["false"])[-1] or "false",
            "--codex-binary-found",
            codex_binary or "false",
            "--cursor-binary-found",
            cursor_binary or "false",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    if gate.returncode != 0 or not any(line.startswith("DEGRADED=") for line in gate.stdout.splitlines()):
        with contextlib.suppress(OSError):
            with (design_path / "execution-issues.md").open("a", encoding="utf-8") as handle:
                if gate.returncode != 0:
                    handle.write(f"- Step 0 degraded-tools gate: subprocess exited {gate.returncode}\n")
                else:
                    handle.write("- Step 0 degraded-tools gate: stdout missing DEGRADED=\n")
                if gate.stderr.strip():
                    handle.write(f"  stderr: {gate.stderr.strip()}\n")
        print("**⚠ /design: degraded-tools gate failed; aborting Step 0**", file=sys.stderr)
        return gate.returncode if gate.returncode != 0 else 1
    state = relay_degraded_tools_gate_stdout(stdout=gate.stdout, design_tmpdir=design_path)
    print(f"STEP0_STATUS={state['STEP0_STATUS']}")
    print(f"DEGRADED={state['DEGRADED']}")
    print(f"BOTH_DOWN={state['BOTH_DOWN']}")
    if state["STEP0_STATUS"] == "degraded-both-down-hard-fail":
        print("DEGRADED_HARD_FAIL=true")
    if state["STEP0_STATUS"] == "needs-degraded-decision":
        print("DEGRADED_PROMPT_REQUIRED=true")
    return 0


def resolve_repo() -> str:
    return gh.resolve_repo(proc) or ""


def _read_json_issue(*, issue_number: str, repo: str) -> tuple[str, str, str]:
    command = ["gh", "issue", "view", issue_number]
    if repo:
        command.extend(["--repo", repo])
    command.extend(["--json", "body,labels,number,title"])
    last = subprocess.CompletedProcess(command, 1, "", "")
    for attempt in range(2):
        last = subprocess.run(command, capture_output=True, text=True, check=False)
        if last.returncode == 0:
            break
        if attempt == 0:
            time.sleep(1)
    if last.returncode != 0:
        raise RuntimeError("gh issue view failed")
    raw = json.loads(last.stdout or "{}")
    labels = raw.get("labels", [])
    has_clarify = any(isinstance(label, dict) and label.get("name") == "needs-design-clarification" for label in labels)
    return str(raw.get("title") or ""), str(raw.get("body") or ""), "true" if has_clarify else "false"


def _read_result_pairs(*, primary: Path, fallback: Path | None, allow: Iterable[str]) -> dict[str, str]:
    pairs: list[tuple[str, str]]
    try:
        pairs = phase_driver_read_result_env(path=primary, allow_keys=allow)
    except OSError:
        pairs = []
    if not pairs and fallback is not None and fallback.is_file() and not fallback.is_symlink():
        pairs = phase_driver_read_result_env(path=fallback, allow_keys=allow)
    return dict(pairs)


def _recover_resume_route_state_values(env: Mapping[str, str], design_tmpdir: Path) -> dict[str, str]:
    merged: dict[str, str] = {key: value for key in ROUTE_STATE_KEYS if (value := env.get(key, ""))}
    try:
        route_state = dict(phase_driver_read_result_env(path=design_tmpdir / ".design-step0-route-state.env", allow_keys=ROUTE_STATE_KEYS))
    except OSError:
        return merged
    for key, value in route_state.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


def _gap_fill_resume_route_state_values(env: dict[str, str], design_tmpdir: Path) -> None:
    recovered = _recover_resume_route_state_values(env, design_tmpdir)
    for key, value in recovered.items():
        if value and not env.get(key):
            env[key] = value


def _bind_step0_route_issue_env(*, env: dict[str, str], design_tmpdir: Path, issue_number_arg: str) -> int:
    if issue_number_arg:
        if re.match(r"^[0-9]+$", issue_number_arg):
            env["ISSUE_NUMBER"] = issue_number_arg
        else:
            print("**⚠ Step 0b: --issue-number requires numeric value; aborting /design**", file=sys.stderr)
            return 1
    kind = env.get("POSITIONAL_KIND", "none") or "none"
    if kind == "issue":
        if re.match(r"^[0-9]+$", env.get("POSITIONAL_VALUE", "")):
            env["ISSUE_NUMBER"] = env["POSITIONAL_VALUE"]
        else:
            print("**⚠ Step 0b: POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE; aborting /design**", file=sys.stderr)
            return 1
    if kind == "verbal" and not env.get("ISSUE_NUMBER"):
        print("**⚠ Step 0b: POSITIONAL_KIND=verbal requires ISSUE_NUMBER from /larch:issue before routing; aborting /design**", file=sys.stderr)
        return 1
    if not env.get("ISSUE_NUMBER"):
        _gap_fill_resume_route_state_values(env, design_tmpdir)
    if kind not in {"issue", "none", "verbal"}:
        print(f"**⚠ Step 0b: invalid POSITIONAL_KIND={kind or '<empty>'}; aborting /design**", file=sys.stderr)
        return 1
    return 0


def _materialize_step0_feature_description(*, design_tmpdir: Path, env: Mapping[str, str], init_route: str) -> None:
    if init_route not in {"proceed", "already-planned"}:
        return
    issue_body = design_tmpdir / "issue-body.txt"
    if issue_body.is_file():
        prefix = f"# {env.get('ISSUE_TITLE', '')}\n\n" if env.get("ISSUE_TITLE") else ""
        (design_tmpdir / "feature-description.txt").write_text(prefix + issue_body.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    elif env.get("POSITIONAL_KIND") == "verbal" and env.get("POSITIONAL_VALUE"):
        (design_tmpdir / "feature-description.txt").write_text(env["POSITIONAL_VALUE"] + "\n", encoding="utf-8")


def _step0_init_driver_cmd(*, plugin_root: Path, design_tmpdir: Path, env: Mapping[str, str], claude_pid: str) -> list[str]:
    cmd = _cli_cmd(
        plugin_root,
        "design",
        "init-runparams",
        "--design-tmpdir",
        str(design_tmpdir),
        "--issue",
        env.get("ISSUE_NUMBER", ""),
        "--session-id",
        env.get("SESSION_ID", ""),
        "--claude-pid",
        claude_pid,
        "--partition-requested",
        env.get("partition_requested", "false"),
        "--brainstorm-requested",
        env.get("brainstorm_requested", "false"),
        "--approve-requested",
        env.get("approve_requested", "false"),
        "--skip-approve-requested",
        env.get("skip_approve_requested", "false"),
        "--difficulty",
        env.get("difficulty", ""),
    )
    if env.get("REPO"):
        cmd.extend(["--repo", env["REPO"]])
    return cmd


def _validate_step0_init_driver_result(*, proc: subprocess.CompletedProcess[str] | None, result: Mapping[str, str], design_tmpdir: Path) -> int:
    if proc is None or not result:
        print("**⚠ Step 0b: read-result-env.sh failed for design-init-runparams result (exit 1); aborting /design**", file=sys.stderr)
        return 1
    init_status = result.get("INIT_STATUS", "")
    if proc.returncode == 0 and (init_status != "ok" or not (design_tmpdir / "run-params.json").is_file()):
        print("**⚠ Step 0b: design-init-runparams.sh exited 0 without INIT_STATUS=ok and run-params.json; aborting /design**", file=sys.stderr)
        return 1
    if proc.returncode == 1:
        if proc.stderr:
            print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
        print(f"**⚠ Step 0b: design-init-runparams.sh failed (INIT_STATUS={init_status or 'unknown'}); aborting /design**", file=sys.stderr)
        return 1
    return 0


def _run_step0_init_driver(
    *,
    plugin_root: Path,
    design_tmpdir: Path,
    env: Mapping[str, str],
    claude_pid: str,
    emit_stdout: bool,
) -> tuple[int, dict[str, str]]:
    with tempfile.NamedTemporaryFile(prefix="larch-init-stdout.", delete=False, mode="w+", encoding="utf-8", dir=design_tmpdir) as capture:
        capture_path = Path(capture.name)
    proc: subprocess.CompletedProcess[str] | None = None
    result: dict[str, str] = {}
    try:
        proc = subprocess.run(
            _step0_init_driver_cmd(plugin_root=plugin_root, design_tmpdir=design_tmpdir, env=env, claude_pid=claude_pid),
            capture_output=True,
            text=True,
            check=False,
        )
        capture_path.write_text(proc.stdout, encoding="utf-8")
        if proc.returncode == CONFIGURATION_ERROR_RC:
            if proc.stderr:
                print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
            print("**⚠ Step 0b: design-init-runparams.sh configuration error (exit 2); aborting /design**", file=sys.stderr)
            return 1, {}
        if proc.returncode not in {0, 1}:
            if proc.stderr:
                print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
            print(f"**⚠ Step 0b: design-init-runparams.sh failed (exit {proc.returncode}); aborting /design**", file=sys.stderr)
            return 1, {}
        result = _read_result_pairs(primary=design_tmpdir / ".design-init-runparams-result.env", fallback=capture_path, allow=INIT_RESULT_KEYS)
    finally:
        with contextlib.suppress(FileNotFoundError):
            capture_path.unlink()
    rc = _validate_step0_init_driver_result(proc=proc, result=result, design_tmpdir=design_tmpdir)
    if rc != 0:
        return rc, {}
    if emit_stdout:
        _emit_step0_init_rows(result)
    return 0, result


@dataclass(frozen=True)
class Step0RouteFinishContext:
    route: str
    resume_step: str
    route_env: Mapping[str, str]
    env: Mapping[str, str]
    design_tmpdir: Path
    plugin_root: Path
    claude_pid: str


def _refresh_resume_source_env(ctx: Step0RouteFinishContext) -> int:
    recovered = _recover_resume_route_state_values(ctx.env, ctx.design_tmpdir)
    session_id = ctx.env.get("SESSION_ID", "")
    issue_number = recovered.get("ISSUE_NUMBER", "")
    if not session_id:
        print("**⚠ Step 0b: resume route missing SESSION_ID; aborting /design**", file=sys.stderr)
        return 1
    if not issue_number or not issue_number.isdigit():
        print("**⚠ Step 0b: resume route could not recover numeric ISSUE_NUMBER; aborting /design**", file=sys.stderr)
        return 1
    command = _cli_cmd(
        ctx.plugin_root,
        "session",
        "write-design-env",
        "--output",
        str(ctx.design_tmpdir / "source-env.sh"),
        "--design-tmpdir",
        str(ctx.design_tmpdir),
        "--session-id",
        session_id,
        "--issue-number",
        issue_number,
        "--claude-pid",
        ctx.claude_pid,
    )
    repo = recovered.get("REPO", "")
    if repo:
        command.extend(["--repo", repo])
    result = proc.run(command, env={**os.environ, **ctx.env, "CLAUDE_PLUGIN_ROOT": str(ctx.plugin_root)})
    if result.returncode == 0:
        return 0
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
    print(f"**⚠ Step 0b: session write-design-env failed during resume refresh (exit {result.returncode}); aborting /design**", file=sys.stderr)
    return 1


def _finish_step0_route(ctx: Step0RouteFinishContext) -> int:
    rows = [
        ("ROUTE", ctx.route),
        *([("RESUME_STEP", ctx.resume_step)] if ctx.resume_step else []),
        ("HAS_CLARIFY_LABEL", ctx.env.get("HAS_CLARIFY_LABEL", "false")),
        ("ISSUE_NUMBER", ctx.env.get("ISSUE_NUMBER", "")),
        ("ISSUE_TITLE", ctx.env.get("ISSUE_TITLE", "")),
    ]
    if ctx.env.get("REPO"):
        rows.append(("REPO", ctx.env["REPO"]))
    if ctx.env.get("brainstorm_requested"):
        rows.append(("brainstorm_requested", ctx.env["brainstorm_requested"]))
    _write_kv_file(path=ctx.design_tmpdir / ".design-step0-route-state.env", rows=rows)
    if ctx.route == "proceed":
        check_pause_and_exit(env=ctx.env, design_tmpdir=ctx.design_tmpdir)
        _materialize_step0_feature_description(design_tmpdir=ctx.design_tmpdir, env=ctx.env, init_route="proceed")
        init_rc, init_result = _run_step0_init_driver(
            plugin_root=ctx.plugin_root,
            design_tmpdir=ctx.design_tmpdir,
            env=ctx.env,
            claude_pid=ctx.claude_pid,
            emit_stdout=False,
        )
        if init_rc != 0:
            return init_rc
        _emit_step0_route_rows(route=ctx.route, resume_step=ctx.resume_step, route_env=ctx.route_env, env=ctx.env)
        _emit_step0_init_rows(init_result)
        return 0
    if ctx.route.startswith("resume@"):
        refresh_rc = _refresh_resume_source_env(ctx)
        if refresh_rc != 0:
            return refresh_rc
    _emit_step0_route_rows(route=ctx.route, resume_step=ctx.resume_step, route_env=ctx.route_env, env=ctx.env)
    return 0


def step0_route_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = _require_design_tmpdir(env=env)
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    parsed = load_bash_quoted_env(path=design_tmpdir / ".design-step0-parsed.env", allow_keys=PARSED_ENV_KEYS)
    env.update(parsed)
    bind_rc = _bind_step0_route_issue_env(env=env, design_tmpdir=design_tmpdir, issue_number_arg=ns.issue_number)
    if bind_rc != 0:
        return bind_rc
    if env.get("ISSUE_NUMBER"):
        if not env.get("REPO"):
            env["REPO"] = resolve_repo()
        try:
            title, body, has_clarify = _read_json_issue(issue_number=env["ISSUE_NUMBER"], repo=env.get("REPO", ""))
        except (RuntimeError, json.JSONDecodeError):
            print(f"**⚠ Step 0b: gh issue view failed for issue {env['ISSUE_NUMBER']}; aborting /design**", file=sys.stderr)
            return 1
        env["ISSUE_TITLE"] = title
        env["HAS_CLARIFY_LABEL"] = has_clarify
        (design_tmpdir / "issue-body.txt").write_text(body, encoding="utf-8")
    with tempfile.NamedTemporaryFile(prefix="larch-route-stdout.", delete=False, mode="w+", encoding="utf-8", dir=design_tmpdir) as capture:
        capture_path = Path(capture.name)
    try:
        route_cmd = _cli_cmd(
            plugin_root,
            "design",
            "route",
            "--design-tmpdir",
            str(design_tmpdir),
            "--issue",
            env.get("ISSUE_NUMBER", ""),
            "--issue-title",
            env.get("ISSUE_TITLE", ""),
            "--issue-body-file",
            str(design_tmpdir / "issue-body.txt"),
            "--has-clarify-label",
            env.get("HAS_CLARIFY_LABEL", "false"),
            "--claude-pid",
            ns.claude_pid,
            "--session-id",
            env.get("SESSION_ID", ""),
            "--partition-requested",
            env.get("partition_requested", "false"),
            "--brainstorm-requested",
            env.get("brainstorm_requested", "false"),
            "--approve-requested",
            env.get("approve_requested", "false"),
            "--skip-approve-requested",
            env.get("skip_approve_requested", "false"),
            "--difficulty",
            env.get("difficulty", ""),
        )
        if env.get("REPO"):
            route_cmd.extend(["--repo", env["REPO"]])
        proc = subprocess.run(route_cmd, capture_output=True, text=True, check=False)
        capture_path.write_text(proc.stdout, encoding="utf-8")
        if proc.returncode == CONFIGURATION_ERROR_RC:
            if proc.stderr:
                print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
            print("**⚠ Step 0b: design-route.sh configuration error (exit 2); aborting /design**", file=sys.stderr)
            return 1
        if proc.returncode != 0:
            if proc.stderr:
                print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
            print(f"**⚠ Step 0b: design-route.sh failed (exit {proc.returncode}); aborting /design**", file=sys.stderr)
            return 1
        route_env = _read_result_pairs(primary=design_tmpdir / ".design-route-result.env", fallback=capture_path, allow=ROUTE_RESULT_KEYS)
    finally:
        with contextlib.suppress(FileNotFoundError):
            capture_path.unlink()
    if not route_env:
        print("**⚠ Step 0b: could not read design-route result env; aborting /design**", file=sys.stderr)
        return 1
    route = route_env.get("ROUTE", "")
    if route_env.get("BRAINSTORM_PREFIX") == "true":
        env["brainstorm_requested"] = "true"
        print("**ℹ /design: detected Brainstorm title prefix: auto-enabling brainstorm mode (run-params `brainstorm_requested=true`) even though --brainstorm was not on argv.**")  # noqa: RUF001
    if route == "cancel-pause-load":
        result_env_path = design_tmpdir / ".design-route-result.env"
        if result_env_path.is_file():
            _replay_warn_error(result_env_path)
        print("**⚠ /design: pause resume state could not be loaded safely; aborting before fresh routing. Inspect pause-load ERROR breadcrumbs above, fix the pause block, then re-invoke /design.**", file=sys.stderr)
        return 1
    resume_step = ""
    if route.startswith("resume@"):
        resume_step = route.removeprefix("resume@")
    valid = route in {"proceed", "clarify", "already-planned", "cancel-title-filter", "cancel-reentry-guard", "cancel-pause-load"} or (route.startswith("resume@") and bool(route.removeprefix("resume@")))
    if not valid:
        print("**⚠ Step 0b: missing or invalid ROUTE after design-route.sh; aborting /design**", file=sys.stderr)
        return 1
    return _finish_step0_route(
        Step0RouteFinishContext(
            route=route,
            resume_step=resume_step,
            route_env=route_env,
            env=env,
            design_tmpdir=design_tmpdir,
            plugin_root=plugin_root,
            claude_pid=ns.claude_pid,
        )
    )


def _load_route_result_route(design_tmpdir: Path) -> str:
    result = _read_result_pairs(primary=design_tmpdir / ".design-route-result.env", fallback=None, allow=["ROUTE"])
    return result.get("ROUTE", "")


def step0_init_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = _require_design_tmpdir(env=env)
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    env.update(load_bash_quoted_env(path=design_tmpdir / ".design-step0-parsed.env", allow_keys=PARSED_ENV_KEYS))
    with contextlib.suppress(OSError):
        env.update(dict(phase_driver_read_result_env(path=design_tmpdir / ".design-step0-route-state.env", allow_keys=ROUTE_STATE_KEYS)))
    init_route = _load_route_result_route(design_tmpdir)
    _materialize_step0_feature_description(design_tmpdir=design_tmpdir, env=env, init_route=init_route)
    rc, _result = _run_step0_init_driver(
        plugin_root=plugin_root,
        design_tmpdir=design_tmpdir,
        env=env,
        claude_pid=ns.claude_pid,
        emit_stdout=False,
    )
    return rc




def _step2b5_self_log(*, plugin_root: Path, design_tmpdir: Path, rc: int, stdout: str, stderr_tmp: Path) -> None:
    if rc == 0:
        return
    stderr = ""
    with contextlib.suppress(OSError):
        stderr = stderr_tmp.read_text(encoding="utf-8", errors="replace")
    combined = stdout
    if stderr:
        if combined and not combined.endswith("\n"):
            combined += "\n"
        combined += stderr
    output_file = design_tmpdir / "check-plan-size.validation.log"
    try:
        output_file.write_text(combined, encoding="utf-8")
    except OSError:
        return
    _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 2b.5", tool="python/cli.py plan check-size", exit_code=rc, category="Warnings", output_file=output_file)


def step0_clarify_hard_halt_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    if not env.get("DESIGN_TMPDIR"):
        print("/design Step 0b clarify hard halt: DESIGN_TMPDIR required", file=sys.stderr)
        return 1
    design_tmpdir = Path(env["DESIGN_TMPDIR"]).resolve()
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    detail = Path(ns.failure_detail_log or env.get("CLARIFY_FAILURE_LOG") or design_tmpdir / "clarify-loop.failure.log")
    try:
        resolved_detail = detail.resolve(strict=False)
        if design_tmpdir not in resolved_detail.parents and resolved_detail != design_tmpdir:
            detail = design_tmpdir / "clarify-loop.failure.log"
    except OSError:
        detail = design_tmpdir / "clarify-loop.failure.log"
    if not detail.is_file():
        detail.write_text("clarify loop hard halt\n", encoding="utf-8")
    stdout_log = design_tmpdir / "design-stage-terminal-state.stdout.log"
    stderr_log = design_tmpdir / "design-stage-terminal-state.stderr.log"
    stage_rc = _capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout_log,
        stderr_log,
        ["--design-tmpdir", str(design_tmpdir), "--outcome", "failed-clarify", "--step", "clarify", "--phase", "clarify-loop", "--site", "clarify-loop", "--trigger", "failed", "--bail-reason", "clarify-hard-halt", "--exit-code", ns.exit_code or "1", "--source-script", "clarify-loop", "--summary-outcome", "failed-clarify", "--failure-detail-log", str(detail)],
    )
    stdout_text = stdout_log.read_text(encoding="utf-8", errors="replace") if stdout_log.is_file() else ""
    if "STAGED=false" in stdout_text.splitlines():
        _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 0b clarify hard halt", tool="design-stage-terminal-state.sh", exit_code=0, category="Warnings", output_file=stdout_log)
    elif stage_rc != 0:
        _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 0b clarify hard halt", tool="design-stage-terminal-state.sh", exit_code=stage_rc, category="Warnings", output_file=stderr_log)
    return 0


def step0_abort_cleanup_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    if not env.get("DESIGN_TMPDIR"):
        print("/design Step 0 abort-cleanup: DESIGN_TMPDIR required", file=sys.stderr)
        return 1
    design_tmpdir = Path(env["DESIGN_TMPDIR"])
    print("**⚠ /design: aborted by operator: external tool unhealthy; re-run once it recovers.**")
    _append_failure(plugin_root=plugin_root, design_tmpdir=design_tmpdir, site="design Step 0", tool="degraded-tools-gate", exit_code=0, category="Warnings", output_file=design_tmpdir / "execution-issues.md")
    return subprocess.run(_cli_cmd(plugin_root, "session", "cleanup-tmpdir", "--dir", str(design_tmpdir)), check=False).returncode


def step0_ap_continue_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    design_tmpdir = _require_design_tmpdir(env=env)
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    for name in ("step-1c", "step-1d", "step-1d.5"):
        (completed / name).write_text("", encoding="utf-8")
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    return 0


def step0c_main(argv: Sequence[str]) -> int:
    ns = _parse_wrapper_args(argv)
    env = _load_wrapper_env(ns)
    plugin_root = require_plugin_root(env.get("CLAUDE_PLUGIN_ROOT", ns.plugin_root))
    _derive_binary_found(env)
    design_tmpdir = _require_design_tmpdir(env=env)
    check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-0c").write_text("", encoding="utf-8")
    _run_best_effort(command=_cli_cmd(plugin_root, "timing", "mark", "design folded discussion block"), env={**os.environ, "LARCH_TIMING_SKILL": "design"})
    return 0
