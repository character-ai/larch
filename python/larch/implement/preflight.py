"""/implement preflight gates for the Python CLI."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn, cast

from larch import io as larch_io
from larch.calibration import difficulty
from larch.design import plan_grammar
from larch.core import config, proc
from larch.errors import ShipError
from larch.git import gh
from larch.git import git
from larch.core.repo_roots import consumer_repo_root, larch_entrypoint, plugin_root as resolve_plugin_root
from larch.implement import main_health
from larch.issue import issue_wire, migration_governance

SUCCESS_ENVELOPE_KEYS = (
    "ADMISSION_RESULT",
    "RESUME",
    "TITLE",
    "BLOCK_PRESENT",
    "PLAN_PATH",
    "ISSUE_JSON_PATH",
    "BYPASS_COUNT",
    "DESIGN_DIFFICULTY",
    "MAIN_CI_STATUS",
    "MAIN_FAILED_RUN_ID",
    "MAIN_HEALTH_HEAD_SHA",
    "MAIN_HEALTH_DETAIL",
)
MAIN_HEALTH_KEYS = (
    "MAIN_CI_STATUS",
    "MAIN_FAILED_RUN_ID",
    "MAIN_HEALTH_HEAD_SHA",
    "MAIN_HEALTH_DETAIL",
)
_RECOGNIZED_TRAILER_PREFIX_RE = re.compile(
    r"^(?:" + "|".join(plan_grammar.TRAILER_KEYS) + r"):"
)


def _usage() -> str:
    return "Usage: cli.py implement preflight --issue N [--repo R] [--force] --preflight-tmpdir D"


def _die_usage(message: str = "") -> NoReturn:
    if message:
        print(message, file=sys.stderr)
    print(_usage(), file=sys.stderr)
    raise SystemExit(2)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cli.py implement preflight",
        usage="%(prog)s --issue N [--repo R] [--force] --preflight-tmpdir D",
        add_help=True,
    )
    parser.add_argument("--issue", required=True)
    parser.add_argument("--repo", default="")
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--preflight-tmpdir", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        raise
    issue = str(args.issue)
    if not issue.isdigit() or int(issue) <= 0:
        _die_usage()
    return args


def _single_line(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")


def _read_json_field(*, path: Path, field: str) -> str:
    with path.open(encoding="utf-8") as handle:
        loaded: object = json.load(handle)
    data: Mapping[str, object] = cast("Mapping[str, object]", loaded) if isinstance(loaded, dict) else cast("Mapping[str, object]", {})
    value: object = data.get(field, "")
    return "" if value is None else str(value)


def _preflight_json_read_failure(issue: str) -> int:
    print(f"**❌ /implement preflight: gh issue view failed for issue #{issue}.**")
    return 2


def _preflight_write_failure(message: str) -> int:
    print(f"**❌ /implement preflight: {message}**")
    return 2


def _read_kv_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _main_health_status_display() -> str:
    statuses = main_health.MAIN_HEALTH_STATUS_ORDER
    return f"{', '.join(statuses[:-1])}, or {statuses[-1]}"


def _write_text(*, path: Path, text: str) -> None:
    larch_io.write_text(path=path, text=text)


def _append_bypass(*, preflight_tmpdir: Path, kind: str, issue: str) -> None:
    try:
        with (preflight_tmpdir / "force-bypass.log").open("a", encoding="utf-8") as handle:
            handle.write(f"BYPASS kind={kind} issue={issue}\n")
    except OSError as exc:
        msg = f"cannot append force bypass log: {exc}"
        raise OSError(msg) from exc


def _bypass_count(preflight_tmpdir: Path) -> int:
    path = preflight_tmpdir / "force-bypass.log"
    if not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _can_read(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8"):
            return True
    except OSError:
        return False


def _success_data(rows: list[tuple[str, str]]) -> tuple[dict[str, str], str]:
    seen: set[str] = set()
    data: dict[str, str] = {}
    for key, value in rows:
        if key in seen:
            return data, f"duplicate key {key}"
        seen.add(key)
        data[key] = value
    missing = [key for key in SUCCESS_ENVELOPE_KEYS if key not in data]
    if missing:
        return data, f"missing key {missing[0]}"
    return data, ""


def _success_path_error(
    data: dict[str, str],
    *,
    preflight_tmpdir: Path,
    plan_path: Path,
    issue_json_path: Path,
) -> str:
    expected_plan = preflight_tmpdir / "plan-from-issue.txt"
    expected_issue_json = preflight_tmpdir / "issue.json"
    if data["PLAN_PATH"] != str(expected_plan) or plan_path != expected_plan:
        return "PLAN_PATH must match preflight tmpdir"
    if data["ISSUE_JSON_PATH"] != str(expected_issue_json) or issue_json_path != expected_issue_json:
        return "ISSUE_JSON_PATH must match preflight tmpdir"
    return ""


def _success_readability_error(data: dict[str, str]) -> str:
    if not _can_read(Path(data["PLAN_PATH"])):
        return "PLAN_PATH must be readable"
    if not _can_read(Path(data["ISSUE_JSON_PATH"])):
        return "ISSUE_JSON_PATH must be readable"
    return ""


def _validate_success_envelope(
    rows: list[tuple[str, str]],
    *,
    preflight_tmpdir: Path,
    plan_path: Path,
    issue_json_path: Path,
) -> str:
    data, error = _success_data(rows)
    if not error and data["RESUME"] not in {"true", "false"}:
        error = "RESUME must be true or false"
    if not error and ("\n" in data["TITLE"] or "\r" in data["TITLE"]):
        error = "TITLE must be single-line"
    if not error:
        error = _success_path_error(
            data,
            preflight_tmpdir=preflight_tmpdir,
            plan_path=plan_path,
            issue_json_path=issue_json_path,
        )
    if not error:
        error = _success_readability_error(data)
    if not error and not data["BYPASS_COUNT"].isdigit():
        error = "BYPASS_COUNT must be numeric"
    if not error and data["MAIN_CI_STATUS"] not in main_health.MAIN_HEALTH_STATUSES:
        error = f"MAIN_CI_STATUS must be {_main_health_status_display()}"
    if not error:
        for key in MAIN_HEALTH_KEYS:
            if "\n" in data[key] or "\r" in data[key]:
                error = f"{key} must be single-line"
                break
    return error


def _success_envelope_rows(values: Mapping[str, str]) -> list[tuple[str, str]]:
    return [(key, values[key]) for key in SUCCESS_ENVELOPE_KEYS]


def _emit_success_envelope(rows: list[tuple[str, str]], *, preflight_tmpdir: Path, plan_path: Path, issue_json_path: Path) -> int:
    validation_error = _validate_success_envelope(
        rows,
        preflight_tmpdir=preflight_tmpdir,
        plan_path=plan_path,
        issue_json_path=issue_json_path,
    )
    if validation_error:
        print(f"**❌ /implement preflight: malformed success envelope: {validation_error}.**")
        return 2
    for key, value in rows:
        print(f"{key}={value}")
    return 0


def _plugin_root_fallback() -> Path:
    implement_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if implement_tmpdir:
        env_file = Path(implement_tmpdir) / "plugin-root.env"
        root = larch_io.read_kv(
            path=env_file,
            key="CLAUDE_PLUGIN_ROOT",
            duplicate_policy="first",
            reject_symlink=True,
            on_error_default=True,
            errors="replace",
        )
        if root:
            return Path(root)
    return Path(__file__).resolve().parents[3]


def _base_env() -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    implement_tmpdir = env.get("IMPLEMENT_TMPDIR", "")
    if implement_tmpdir:
        env["IMPLEMENT_TMPDIR"] = implement_tmpdir
        if not env.get("RUN_ID"):
            parent = Path(implement_tmpdir) / "parent-issue.md"
            run_id = larch_io.read_kv(
                path=parent,
                key="RUN_ID",
                duplicate_policy="first",
                reject_symlink=True,
                on_error_default=True,
                errors="replace",
            )
            if run_id:
                env["RUN_ID"] = run_id
    return env


def _bounded_main_health_detail(text: str) -> str:
    compact = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return compact[: config.MAIN_HEALTH_DETAIL_MAX_CHARS]


def _main_health_error_rows(detail: str) -> dict[str, str]:
    return {
        "MAIN_CI_STATUS": "error",
        "MAIN_FAILED_RUN_ID": "",
        "MAIN_HEALTH_HEAD_SHA": "",
        "MAIN_HEALTH_DETAIL": _bounded_main_health_detail(detail),
    }


def _resolve_repo_for_main_health(*, cli_path: Path, env: dict[str, str], repo: str, preflight_tmpdir: Path) -> tuple[str, str]:
    if repo:
        return repo, ""
    stdout_path = preflight_tmpdir / "resolve-repo.stdout"
    stderr_path = preflight_tmpdir / "resolve-repo.stderr"
    rc = _run_capture(
        argv=[str(larch_entrypoint(Path(__file__).resolve().parents[3])), "gh", "resolve-repo"],
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
    )
    _ = cli_path
    if rc != 0:
        detail = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
        return "", f"repo resolution failed: {detail or rc}"
    resolved = stdout_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
    return (resolved[0].strip(), "") if resolved and resolved[0].strip() else ("", "repo resolution produced no repo")


def _read_main_health_rows(*, cli_path: Path, env: dict[str, str], repo: str, preflight_tmpdir: Path) -> dict[str, str]:
    resolved_repo, resolve_error = _resolve_repo_for_main_health(
        cli_path=cli_path,
        env=env,
        repo=repo,
        preflight_tmpdir=preflight_tmpdir,
    )
    if resolve_error or not resolved_repo:
        return _main_health_error_rows(resolve_error or "repo resolution failed")
    stdout_path = preflight_tmpdir / "main-health.stdout"
    stderr_path = preflight_tmpdir / "main-health.stderr"
    rc = _run_capture(
        argv=[
            sys.executable,
            str(cli_path),
            "ci",
            "main-health",
            "--repo",
            resolved_repo,
            "--base-ref",
            "main",
        ],
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        env=env,
    )
    if rc != 0:
        detail = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.is_file() else ""
        return _main_health_error_rows(f"main-health probe failed: {detail or rc}")
    parsed = _read_kv_lines(stdout_path.read_text(encoding="utf-8", errors="replace"))
    if not all(key in parsed for key in MAIN_HEALTH_KEYS):
        return _main_health_error_rows("main-health probe omitted required keys")
    return {key: _single_line(parsed.get(key, "")) for key in MAIN_HEALTH_KEYS}


def _write_main_health_env(*, preflight_tmpdir: Path, rows: Mapping[str, str]) -> None:
    text = "".join(f"{key}={_single_line(rows.get(key, ''))}\n" for key in MAIN_HEALTH_KEYS)
    _write_text(path=preflight_tmpdir / "main-health.env", text=text)


def _materialize_main_health_rows(cli_path: Path, env: dict[str, str], repo: str, preflight_tmpdir: Path) -> dict[str, str]:
    rows = _read_main_health_rows(
        cli_path=cli_path,
        env=env,
        repo=repo,
        preflight_tmpdir=preflight_tmpdir,
    )
    try:
        _write_main_health_env(preflight_tmpdir=preflight_tmpdir, rows=rows)
    except OSError:
        rows = _main_health_error_rows("cannot write main-health.env")
    return rows


def _run_capture(*, argv: list[str], stdout_path: Path, stderr_path: Path, env: dict[str, str] | None = None) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
        completed = subprocess.run(argv, stdout=out, stderr=err, text=True, env=env, check=False)
    return completed.returncode


def _print_admission_refusal(kv: dict[str, str]) -> None:
    admission_error = kv.get("ADMISSION_ERROR", "")
    admission_result = kv.get("ADMISSION_RESULT", "missing") or "missing"
    if admission_error:
        print(f"**❌ /implement preflight: admission blocked: `ADMISSION_ERROR={admission_error}`**")
        return
    print(f"**❌ /implement preflight: admission blocked: `ADMISSION_RESULT={admission_result}`**")
    if admission_result in {"missing-designed-prefix", "managed-prefix", "report-title"}:
        title = kv.get("TITLE", "")
        if title:
            print(f"TITLE={title}")
    elif admission_result == "has-blockers":
        blockers = kv.get("BLOCKERS", "")
        if blockers:
            print(f"BLOCKERS={blockers}")


def _refuse_plan_contract(*, issue: str, defects: tuple[str, ...], force: bool) -> int:
    tokens = ",".join(defects)
    if force:
        print(
            f"**❌ /implement --force: issue #{issue} failed executable-plan admission: "
            f"`{tokens}`.**"
        )
        print(plan_grammar.FORCE_PLAN_CONTRACT_ERROR)
    else:
        print(
            f"**❌ Issue #{issue} failed executable-plan admission: `{tokens}`. "
            f"Run /design {issue} to repair the plan block before retrying /implement.**"
        )
    return 2


def _plan_review_meta_value(*, plan_path: Path, key: str) -> str:
    text = plan_path.read_text(encoding="utf-8", errors="replace")
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    if not trailers.matches:
        return ""
    match = trailers.get(cast("plan_grammar.TrailerKey", key))
    return match.value if match is not None else ""


def _malformed_terminal_metadata(*, plan_path: Path) -> str:
    """Return the first malformed recognized trailer adjacent to terminal metadata."""
    lines = plan_path.read_text(encoding="utf-8", errors="replace").splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    last = plan_grammar.match_trailer_line(lines[-1])
    if last is None or last.key != "diff_lines":
        return ""
    for line in reversed(lines):
        if not _RECOGNIZED_TRAILER_PREFIX_RE.match(line):
            break
        if plan_grammar.match_trailer_line(line) is None:
            return line
    return ""


def _refuse_malformed_terminal_metadata(*, plan_path: Path, issue: str) -> None:
    malformed = _malformed_terminal_metadata(plan_path=plan_path)
    if not malformed:
        return
    key, value = malformed.split(":", 1)
    rendered = f"{key}={value.strip()}"
    print(
        f"**❌ /implement preflight: malformed plan review metadata: `{rendered}`. Re-run /design {issue} before retrying /implement.**"
    )
    raise SystemExit(2)


def _validate_design_difficulty(*, plan_path: Path, issue: str, force: bool) -> str:
    tier = _plan_review_meta_value(plan_path=plan_path, key="difficulty")
    if not tier:
        return ""
    if difficulty.tier_valid(tier):
        return tier
    message = f"malformed difficulty metadata: `difficulty={tier}`"
    if force:
        print(f"**⚠ /implement --force: {message}; ignoring the design prior for issue #{issue}.**")
        return ""
    print(f"**❌ /implement preflight: {message}. Re-run /design {issue} before retrying /implement.**")
    raise SystemExit(2)


def _refuse_unreviewed_plan(*, plan_path: Path, issue: str) -> None:
    review_status = _plan_review_meta_value(plan_path=plan_path, key="review_status")
    rounds_completed = _plan_review_meta_value(plan_path=plan_path, key="rounds_completed")
    if review_status in {"panel-init-failed", "panel-skipped"}:
        print(
            f"**❌ /implement preflight: plan review did not run: `review_status={review_status}`. Re-run /design {issue} before retrying /implement.**"
        )
        raise SystemExit(2)
    if rounds_completed:
        if not rounds_completed.isdigit():
            print(
                f"**❌ /implement preflight: malformed plan review metadata: `rounds_completed={rounds_completed}`. Re-run /design {issue} before retrying /implement.**"
            )
            raise SystemExit(2)
        if int(rounds_completed) == 0:
            print(
                f"**❌ /implement preflight: plan review did not run: `rounds_completed=0`. Re-run /design {issue} before retrying /implement.**"
            )
            raise SystemExit(2)


def _refuse_governance_gate(*, site: str, verdict: migration_governance.GovernanceGateVerdict) -> int:
    print(migration_governance.format_gate_refusal(site=site, verdict=verdict))
    return 2


def _migration_governance_status(
    *,
    issue: str,
    repo: str,
    issue_body: str,
    repo_root: Path,
    forked_target: bool,
) -> int | None:
    gate_repo = repo or (gh.resolve_repo(proc) or "")
    if not gate_repo:
        print("**❌ /implement preflight: repository slug required for migration governance.**")
        return 2
    try:
        base_target = "upstream/main" if forked_target else "origin/main"
        base_target_sha = git.rev_parse(
            proc, base_target, cwd=str(repo_root)
        )
        gate = migration_governance.evaluate_governance_gate(
            proc,
            issue=issue,
            repo=gate_repo,
            body=issue_body,
            repo_root=repo_root,
            head_sha=base_target_sha,
        )
    except ShipError as exc:
        print(f"**❌ /implement preflight: migration governance read failed: {exc}.**")
        return 2
    if not gate.ok:
        return _refuse_governance_gate(site="/implement preflight", verdict=gate)
    for token, command in zip(gate.owners.report_only, gate.owners.cleanup_commands, strict=True):
        print(f"**⚠ /implement preflight: `{token}`. Cleanup: `{command}`.**")
    return None


def preflight_main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv=argv)
    issue = str(args.issue)
    repo = str(args.repo or "")
    preflight_tmpdir = Path(args.preflight_tmpdir)
    try:
        preflight_tmpdir.mkdir(parents=True, exist_ok=True)
    except OSError:
        print("**❌ /implement preflight: cannot create preflight tmpdir.**")
        return 2
    try:
        write_test = preflight_tmpdir / ".write-test"
        write_test.write_text("", encoding="utf-8")
        write_test.unlink(missing_ok=True)
    except OSError:
        print("**❌ /implement preflight: preflight tmpdir is not writable.**")
        return 2

    plugin_root = resolve_plugin_root(_plugin_root_fallback())
    cli_path = plugin_root / "python" / "cli.py"
    if not cli_path.is_file():
        print("**❌ /implement preflight: cannot resolve CLAUDE_PLUGIN_ROOT/python/cli.py.**")
        return 2
    env = _base_env()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

    admission_stdout = preflight_tmpdir / "admission.stdout"
    admission_stderr = preflight_tmpdir / "admission.stderr"
    admission_argv = [str(larch_entrypoint(plugin_root)), "admission", "gate", "--issue", issue]
    if repo:
        admission_argv.extend(["--repo", repo])
    admission_env: dict[str, str] = {**env, "LARCH_QUIET_DISABLE": "1"}
    admission_rc = _run_capture(argv=admission_argv, stdout_path=admission_stdout, stderr_path=admission_stderr, env=admission_env)
    admission_kv = _read_kv_lines(admission_stdout.read_text(encoding="utf-8", errors="replace"))
    admission_result = admission_kv.get("ADMISSION_RESULT", "")
    if admission_rc != 0:
        if admission_result == "missing-designed-prefix" and args.force:
            print(
                f"**⚠ /implement --force: admission gate blocked on missing [DESIGNED] prefix for issue #{issue} (title: {admission_kv.get('TITLE', '')}); bypassing and proceeding.**"
            )
            try:
                _append_bypass(preflight_tmpdir=preflight_tmpdir, kind="missing-designed-prefix", issue=issue)
            except OSError:
                return _preflight_write_failure("cannot append force bypass log.")
        else:
            _print_admission_refusal(admission_kv)
            return 2
    elif admission_result != "pass":
        _print_admission_refusal(admission_kv)
        return 2

    issue_json_path = preflight_tmpdir / "issue.json"
    gh_stderr = preflight_tmpdir / "gh-issue-view.stderr"
    view_result = gh.issue_view_field_read(
        proc,
        issue,
        "body,labels,number,title,state,updatedAt",
        repo=repo or None,
    )
    try:
        issue_json_path.write_text(view_result.stdout, encoding="utf-8")
        gh_stderr.write_text(view_result.stderr, encoding="utf-8")
    except OSError:
        return _preflight_write_failure("cannot write issue view artifacts.")
    if view_result.returncode != 0:
        print(f"**❌ /implement preflight: gh issue view failed for issue #{issue}.**")
        return 2

    try:
        title = _single_line(_read_json_field(path=issue_json_path, field="title"))
        issue_body = _read_json_field(path=issue_json_path, field="body")
    except (OSError, json.JSONDecodeError):
        return _preflight_json_read_failure(issue)
    plan_path = preflight_tmpdir / "plan-from-issue.txt"
    plan_stdout = preflight_tmpdir / "plan-block.stdout"
    plan_stderr = preflight_tmpdir / "plan-block.stderr"
    plan_argv = [str(larch_entrypoint(plugin_root)), "plan-block", "read", "--issue", issue, "--output", str(plan_path)]
    if repo:
        plan_argv.extend(["--repo", repo])
    plan_rc = _run_capture(argv=plan_argv, stdout_path=plan_stdout, stderr_path=plan_stderr, env=admission_env)
    plan_kv = _read_kv_lines(plan_stdout.read_text(encoding="utf-8", errors="replace"))
    block_present = plan_kv.get("BLOCK_PRESENT", "")
    malformed = plan_kv.get("MALFORMED", "")
    if plan_rc != 0 and not (plan_rc == 1 and malformed):
        print(f"**❌ /implement preflight: plan-block read failed for issue #{issue}.**")
        return 2

    repo_root = consumer_repo_root() or Path.cwd()
    contract = issue_wire.validate_issue_plan(issue_body=issue_body, repo_root=repo_root)
    if not contract.ok:
        return _refuse_plan_contract(issue=issue, defects=contract.defects, force=args.force)

    inner, _inner_malformed = issue_wire.parse_named_block(body=issue_body, marker="plan")
    if inner is None:
        return _refuse_plan_contract(issue=issue, defects=("missing-plan-block",), force=args.force)
    try:
        _write_text(path=plan_path, text=inner)
    except OSError:
        return _preflight_write_failure("cannot write extracted plan.")
    block_present = "true"

    governance_status = _migration_governance_status(
        issue=issue,
        repo=repo,
        issue_body=issue_body,
        repo_root=repo_root,
        forked_target=bool(repo),
    )
    if governance_status is not None:
        return governance_status

    design_difficulty = ""
    try:
        _refuse_malformed_terminal_metadata(plan_path=plan_path, issue=issue)
        _refuse_unreviewed_plan(plan_path=plan_path, issue=issue)
        design_difficulty = _validate_design_difficulty(plan_path=plan_path, issue=issue, force=args.force)
    except SystemExit as exc:
        return int(exc.code or 2)

    resume = "true" if admission_kv.get("RESUME") == "true" else "false"
    rows = _success_envelope_rows({
        "ADMISSION_RESULT": admission_result,
        "RESUME": resume,
        "TITLE": title,
        "BLOCK_PRESENT": block_present,
        "PLAN_PATH": str(plan_path),
        "ISSUE_JSON_PATH": str(issue_json_path),
        "BYPASS_COUNT": str(_bypass_count(preflight_tmpdir)),
        "DESIGN_DIFFICULTY": design_difficulty,
        **_materialize_main_health_rows(cli_path, env, repo, preflight_tmpdir),
    })
    return _emit_success_envelope(
        rows,
        preflight_tmpdir=preflight_tmpdir,
        plan_path=plan_path,
        issue_json_path=issue_json_path,
    )
