"""Python CLI entrypoint for /design post-plan emission."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
import larch_io
from collections.abc import Sequence

from repo_roots import consumer_repo_root


# Drift-detection keys read from drift-baseline.env
_KEY_BASELINE_PLAN_LINES = "BASELINE_PLAN_LINES"
_KEY_BASELINE_DIFF_LINES = "BASELINE_DIFF_LINES"
# Emitted when current plan exceeds the baseline by the drift multiple
_KEY_DRIFT_TRIGGER_FIRED = "DRIFT_TRIGGER_FIRED"


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _write_result_env(*, path: Path, kvs: dict[str, str]) -> bool:
    try:
        larch_io.write_kvs(path=path, values=kvs, atomic=False, create_parent=False)
    except OSError:
        return False
    return True


def _run_cli(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "python" / "cli.py"), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _clear_stale_or_warn(*, root: Path, design_tmpdir: Path) -> None:
    """Clear stale dialectic artifacts after a plan rewrite, surfacing failures.

    Dialectic is fail-open and Gate C re-validates plan fingerprints, so a failed
    clear is reported loudly (CI signal) without aborting postplan.
    """
    clear = _run_cli(root, "design", "dialectic-clear-stale", "--design-tmpdir", str(design_tmpdir), "--reason", "plan-rewrite")
    if clear.returncode != 0:
        print("**⚠ design-postplan: dialectic-clear-stale failed after plan rewrite; stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**", file=sys.stderr)


def _self_log_check_size_failure(root: Path, *, design_tmpdir: Path, rc: int, stdout: str, stderr: str, site: str) -> None:  # noqa: PLR0913 - cohesive self-log helper; its context fields (tmpdir, rc, stdout, stderr, site) are not worth bundling for one call site
    combined = stdout
    if stderr:
        if combined and not combined.endswith("\n"):
            combined += "\n"
        combined += stderr
    output_file = design_tmpdir / "check-plan-size.validation.log"
    try:
        _ = output_file.write_text(combined, encoding="utf-8")
    except OSError:
        return
    _ = _run_cli(
        root,
        "run-log",
        "append-failure",
        "--log",
        str(design_tmpdir / "execution-issues.md"),
        "--site",
        site,
        "--tool",
        "python/cli.py plan check-size",
        "--exit-code",
        str(rc),
        "--category",
        "Warnings",
        "--output-file",
        str(output_file),
        "--redact",
    )


def postplan_emit_main(argv: Sequence[str]) -> int:
    args = list(argv)
    design_tmpdir_arg = ""
    snapshot_original = False
    with_plan_size = False
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--design-tmpdir":
            if i + 1 >= len(args):
                print("design-postplan-emit.sh: --design-tmpdir requires a value", file=sys.stderr)
                return 2
            design_tmpdir_arg = args[i + 1]
            i += 2
            continue
        if token == "--snapshot-original":
            snapshot_original = True
            i += 1
            continue
        if token == "--with-plan-size":
            with_plan_size = True
            i += 1
            continue
        if token in {"-h", "--help"}:
            print("Usage: design-postplan-emit.sh --design-tmpdir PATH [--snapshot-original] [--with-plan-size]", file=sys.stderr)
            return 0
        print(f"design-postplan-emit.sh: unknown option: {token}", file=sys.stderr)
        return 2

    if not design_tmpdir_arg:
        print("design-postplan-emit.sh: --design-tmpdir is required", file=sys.stderr)
        return 2
    design_tmpdir = Path(design_tmpdir_arg)
    if not design_tmpdir.is_dir():
        print(f"design-postplan-emit.sh: design tmpdir not a directory: {design_tmpdir}", file=sys.stderr)
        return 2

    root = _plugin_root()
    result_env = design_tmpdir / ".design-postplan-emit-result.env"
    run_params_path = design_tmpdir / "run-params.json"
    partition_requested = "false"
    if run_params_path.is_file():
        read_partition = _run_cli(root, "plan-review", "json-get-bool", "--path", str(run_params_path), "--key", "partition_requested", "--default", "false")
        if read_partition.returncode == 0:
            partition_requested = (read_partition.stdout or "false").strip() or "false"

    kvs: dict[str, str] = {
        "POSTPLAN_EMIT_STATUS": "pending",
        "EMIT_PLAN_STATUS": "not-run",
        "DIFF_LINES": "",
        "SNAPSHOT_STATUS": "not-run",
        "VALIDATE_STATUS": "not-run",
        "VALIDATE_DEFECT_COUNT": "0",
        "VALIDATE_SKIPPED_COUNT": "0",
        "VALIDATE_UNSAFE_TOKEN_COUNT": "0",
        "VALIDATE_LOG_FILE": "",
    }

    def flush() -> None:
        _write_result_env(path=result_env, kvs=kvs)  # pyright: ignore[reportUnusedCallResult]
        for key in (
            "POSTPLAN_EMIT_STATUS",
            "EMIT_PLAN_STATUS",
            "DIFF_LINES",
            "SNAPSHOT_STATUS",
            "VALIDATE_STATUS",
            "VALIDATE_DEFECT_COUNT",
            "VALIDATE_SKIPPED_COUNT",
            "VALIDATE_UNSAFE_TOKEN_COUNT",
            "VALIDATE_LOG_FILE",
            "PLAN_SIZE_STATUS",
            "SIZE_TRIGGER_FIRED",
            "TRIGGER_REASONS",
            "PLAN_LINES",
            "DIFF_ADDED",
            "DIFF_DELETED",
            "MECHANICAL_CHURN",
            "SOFT_ADVISORY",
            "DRIFT_TRIGGER_FIRED",
            "DRIFT_MULTIPLE",
            "DRIFT_PLAN_RATIO",
            "DRIFT_DIFF_RATIO",
            "BASELINE_PLAN_LINES",
            "BASELINE_DIFF_LINES",
            "PARTITION_REQUESTED",
        ):
            if key in kvs:
                print(f"{key}={kvs[key]}")

    plan_path = design_tmpdir / "plan.txt"
    entry_plan_hash = plan_path.read_bytes() if plan_path.is_file() else b""
    if not plan_path.is_file() or plan_path.stat().st_size == 0:
        kvs["POSTPLAN_EMIT_STATUS"] = "missing-plan"
        flush()
        return 1 if with_plan_size else 2

    if (design_tmpdir / ".pause-requested").is_file():
        kvs["POSTPLAN_EMIT_STATUS"] = "paused"
        if with_plan_size:
            flush()
            print("**⏸ /design Step 2b: pause requested; saving design state.**")
            return 11
        issue_number = os.environ.get("ISSUE_NUMBER", "")
        if not issue_number and (design_tmpdir / "source-env.sh").is_file():
            for line in (design_tmpdir / "source-env.sh").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("export ISSUE_NUMBER="):
                    issue_number = line.split("=", 1)[1].strip("'\"")
                    break
        if not issue_number:
            kvs["POSTPLAN_EMIT_STATUS"] = "pause-failed"
            flush()
            print("PAUSE_OK=false")
            print("ERROR=issue-unresolved")
            return 1
        pause = subprocess.run(
            [str(root / "scripts" / "design-pause-save.sh"), "--design-tmpdir", str(design_tmpdir), "--issue", issue_number],
            check=False,
        )
        return int(pause.returncode)

    emit = _run_cli(root, "plan-review", "emit", "--design-tmpdir", str(design_tmpdir))
    emit_kv = _parse_kv(emit.stdout)
    kvs["EMIT_PLAN_STATUS"] = emit_kv.get("EMIT_PLAN_STATUS", "not-run")
    kvs["DIFF_LINES"] = emit_kv.get("DIFF_LINES", "")
    if emit.returncode != 0 or kvs["EMIT_PLAN_STATUS"] != "ok":
        kvs["POSTPLAN_EMIT_STATUS"] = "missing-diff-lines" if kvs["EMIT_PLAN_STATUS"] == "missing-diff-lines" else "emit-failed"
        flush()
        return 1
    kvs["SNAPSHOT_STATUS"] = "skipped-suppressed"

    validate_env: dict[str, str] = os.environ.copy()
    validate_env["DESIGN_TMPDIR"] = str(design_tmpdir)
    validate_env["LARCH_QUIET_DISABLE"] = "1"
    # Resolve plan-command script existence against the consumer repo first (it
    # may carry scripts absent from the plugin cache), while preserving the
    # plugin cache as CLAUDE_PLUGIN_ROOT so plugin-only scripts still pass the
    # dual-root existence check in `plan validate` (#4490).
    validate_env["CLAUDE_PLUGIN_ROOT"] = str(root)
    repo_root_arg = consumer_repo_root() or root
    validate = _run_cli(
        root,
        "plan",
        "validate",
        "--plan-file",
        str(plan_path),
        "--design-tmpdir",
        str(design_tmpdir),
        "--repo-root",
        str(repo_root_arg),
        env=validate_env,
    )
    validate_kv = _parse_kv((validate.stdout or "") + "\n" + (validate.stderr or ""))
    for key in ("VALIDATE_STATUS", "VALIDATE_DEFECT_COUNT", "VALIDATE_SKIPPED_COUNT", "VALIDATE_UNSAFE_TOKEN_COUNT", "VALIDATE_LOG_FILE"):
        if key in validate_kv:
            kvs[key] = validate_kv[key]
    if (validate.returncode != 0 and kvs["VALIDATE_STATUS"] != "defects-found") or kvs["VALIDATE_STATUS"] in {"", "not-run"}:
        kvs["POSTPLAN_EMIT_STATUS"] = "validate-driver-failed"
        flush()
        return 1

    kvs["POSTPLAN_EMIT_STATUS"] = "ok"
    if plan_path.is_file() and plan_path.read_bytes() != entry_plan_hash:
        _clear_stale_or_warn(root=root, design_tmpdir=design_tmpdir)
    if not with_plan_size:
        flush()
        return 0

    check_size_env: dict[str, str] = os.environ.copy()
    check_size_env["LARCH_QUIET_DISABLE"] = "1"
    check_size = _run_cli(root, "plan", "check-size", "--design-tmpdir", str(design_tmpdir), env=check_size_env)
    size_kv = _parse_kv((check_size.stdout or "") + "\n" + (check_size.stderr or ""))
    kvs.update({
        "PLAN_SIZE_STATUS": size_kv.get("PLAN_SIZE_STATUS", "failed" if check_size.returncode else "ok"),
        "SIZE_TRIGGER_FIRED": size_kv.get("SIZE_TRIGGER_FIRED", "false"),
        "TRIGGER_REASONS": size_kv.get("TRIGGER_REASONS", ""),
        "PLAN_LINES": size_kv.get("PLAN_LINES", ""),
        "DIFF_ADDED": size_kv.get("DIFF_ADDED", ""),
        "DIFF_DELETED": size_kv.get("DIFF_DELETED", ""),
        "MECHANICAL_CHURN": size_kv.get("MECHANICAL_CHURN", "false"),
        "SOFT_ADVISORY": size_kv.get("SOFT_ADVISORY", "false"),
        "DRIFT_TRIGGER_FIRED": size_kv.get("DRIFT_TRIGGER_FIRED", "false"),
        "DRIFT_MULTIPLE": size_kv.get("DRIFT_MULTIPLE", os.environ.get("LARCH_DESIGN_DRIFT_MULTIPLE", "2")),
        "DRIFT_PLAN_RATIO": size_kv.get("DRIFT_PLAN_RATIO", "1"),
        "DRIFT_DIFF_RATIO": size_kv.get("DRIFT_DIFF_RATIO", "1"),
        "BASELINE_PLAN_LINES": size_kv.get("BASELINE_PLAN_LINES", ""),
        "BASELINE_DIFF_LINES": size_kv.get("BASELINE_DIFF_LINES", ""),
        "PARTITION_REQUESTED": partition_requested,
    })
    if check_size.returncode != 0:
        _self_log_check_size_failure(
            root,
            design_tmpdir=design_tmpdir,
            rc=check_size.returncode,
            stdout=check_size.stdout or "",
            stderr=check_size.stderr or "",
            site="design Step 2b",
        )
        flush()
        return 1
    if snapshot_original and kvs.get("PLAN_LINES") and kvs.get("DIFF_LINES"):
        _ = _run_cli(
            root,
            "plan-review",
            "drift-baseline",
            "write-once",
            "--design-tmpdir",
            str(design_tmpdir),
            "--plan-lines",
            kvs["PLAN_LINES"],
            "--diff-lines",
            kvs["DIFF_LINES"],
        )
    if kvs["VALIDATE_STATUS"] == "defects-found":
        kvs["PLAN_SIZE_STATUS"] = "skipped-defects"
        flush()
        return 10
    if kvs["SIZE_TRIGGER_FIRED"] == "true":
        kvs["PLAN_SIZE_STATUS"] = "plan-size-trigger"
        flush()
        return 12
    if partition_requested == "true":
        kvs["PLAN_SIZE_STATUS"] = "partition-requested"
        flush()
        return 13
    if kvs["DRIFT_TRIGGER_FIRED"] == "true":
        kvs["PLAN_SIZE_STATUS"] = "drift-advisory"
        flush()
        print(f"⏩ 2b.5: plan-size — drift advisory (PLAN_LINES={kvs.get('PLAN_LINES','')} DIFF_LINES={kvs.get('DIFF_LINES','')}); proceeding")
        return 0
    kvs["PLAN_SIZE_STATUS"] = "under-threshold"
    flush()
    print(f"⏩ 2b.5: plan-size — under thresholds (PLAN_LINES={kvs.get('PLAN_LINES','')} DIFF_LINES={kvs.get('DIFF_LINES','')})")
    return 0
