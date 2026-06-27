"""Python CLI entrypoint for /design publish."""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path
from larch import io as larch_io
from collections.abc import Sequence

from larch.report import design_diagram_log
from larch.core import proc
from larch.report import run_logs
from larch.git.repo_roots import consumer_repo_root


def _emit_rows(rows: list[tuple[str, str]]) -> None:
    for key, value in rows:
        print(f"{key}={value}")


def _write_result_env(*, path: Path, rows: list[tuple[str, str]]) -> bool:
    try:
        larch_io.write_kvs(path=path, values=rows, atomic=False, create_parent=False)
    except OSError:
        return False
    return True


def _parse_kv(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _replace_kv(*, rows: list[tuple[str, str]], key: str, value: str) -> None:
    for idx in range(len(rows) - 1, -1, -1):
        if rows[idx][0] == key:
            rows[idx] = (key, value)
            return
    rows.append((key, value))


def _count_missing_script_defects(log_file: str) -> str:
    path = Path(log_file) if log_file else None
    if path is None or not path.is_file() or path.is_symlink():
        return "0"
    try:
        count = sum(
            1
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if "kind=missing-script" in line
        )
    except OSError:
        return "0"
    return str(count)


def _is_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


_PROVENANCE_META_KEYS = ("review_status", "rounds_completed")
_OPTIONAL_TRAILER_RE = re.compile(
    r"^(diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+)$"
)
_TERMINAL_STATUSES_REQUIRING_SENTINEL = frozenset({"complete", "cap-hit"})
_REASON_TOKEN_RE = re.compile(r"REASON_TOKEN=([^ \t);,]+)")


def _is_trailer_region_line(line: str) -> bool:
    stripped = line.rstrip("\n")
    if any(stripped.startswith(f"{key}: ") for key in _PROVENANCE_META_KEYS):
        return True
    return bool(_OPTIONAL_TRAILER_RE.fullmatch(stripped))


def _read_review_round_count(design_tmpdir: Path) -> int:
    """Return the launched-round count from review-round-count.txt (0 if absent/invalid).

    Mirrors plan_review._read_count. Used as a defense-in-depth fallback by
    review_provenance when a result-env writer omits the round-count keys (#5210).
    """
    path = design_tmpdir / "review-round-count.txt"
    if not path.is_file() or path.is_symlink():
        return 0
    try:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return 0
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def _touch_step5b5_sentinel(design_tmpdir: Path) -> None:
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-5b.5").touch()


def _write_diagram_sanitizer_failure(
    *,
    design_tmpdir: Path,
    reason: str,
    exit_code: int | str,
) -> None:
    failure_log = design_tmpdir / "architecture-diagram-sanitizer.failure.log"
    safe_reason = re.sub(r"[^A-Za-z0-9._:-]+", "-", reason).strip("-") or "unknown"
    _ = failure_log.write_text(
        f"reason={safe_reason}\nexit-code={exit_code}\nsite=design Step 5b.5\n",
        encoding="utf-8",
    )
    _ = design_diagram_log.write_bounded_diagram_failure_log(
        design_tmpdir,
        site="design Step 5b.5",
        reason=safe_reason,
        exit_code=exit_code,
        raw_capture_path=failure_log,
    )
    run_logs.append_execution_issue(
        log_file=design_tmpdir / "execution-issues.md",
        category="Warnings",
        entry=design_diagram_log.bounded_diagram_warning_body(
            reason=safe_reason,
            exit_code=exit_code,
        ),
    )


def _skip_diagram_candidate(
    *,
    design_tmpdir: Path,
    reason: str,
    exit_code: int | str,
) -> bool:
    try:
        with contextlib.suppress(OSError):
            (design_tmpdir / "architecture-diagram.md").unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            (design_tmpdir / "architecture-diagram.candidate.md").unlink(missing_ok=True)
        _ = (design_tmpdir / "architecture-diagram.skipped").write_text("", encoding="utf-8")
        _write_diagram_sanitizer_failure(
            design_tmpdir=design_tmpdir,
            reason=reason,
            exit_code=exit_code,
        )
        _touch_step5b5_sentinel(design_tmpdir)
    except OSError:
        return False
    return True


def _sanitize_diagram_candidate(*, design_tmpdir: Path, plugin_root: Path) -> bool:
    """Complete the Step 5b.5 diagram sanitize gate before publishing."""
    sentinel = design_tmpdir / ".completed" / "step-5b.5"
    if sentinel.is_file():
        return True

    candidate = design_tmpdir / "architecture-diagram.candidate.md"
    accepted = design_tmpdir / "architecture-diagram.md"
    skipped = design_tmpdir / "architecture-diagram.skipped"
    failure_log = design_tmpdir / "architecture-diagram-sanitizer.failure.log"
    try:
        if not candidate.is_file() or not os.access(candidate, os.R_OK):
            return _skip_diagram_candidate(
                design_tmpdir=design_tmpdir,
                reason="candidate-missing",
                exit_code=2,
            )

        sanitizer = proc.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "mermaid",
                "sanitize",
                "--input",
                str(candidate),
                "--from-md",
                "--warnings-step",
                "5b.5",
            ],
            check=False,
        )
        sanitizer_output = (sanitizer.stdout or "") + "\n" + (sanitizer.stderr or "")
        status = _parse_kv(sanitizer_output).get("STATUS", "")
        if sanitizer.returncode == 0 and status != "rejected":
            with contextlib.suppress(OSError):
                skipped.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                failure_log.unlink(missing_ok=True)
            with contextlib.suppress(OSError):
                (design_tmpdir / "architecture-diagram-generation.failure.log").unlink(missing_ok=True)
            _ = candidate.replace(accepted)
            _touch_step5b5_sentinel(design_tmpdir)
            return True

        match = _REASON_TOKEN_RE.search(sanitizer_output)
        reason_token = match.group(1) if match else "unknown"
        return _skip_diagram_candidate(
            design_tmpdir=design_tmpdir,
            reason=f"sanitizer-rejected:{reason_token}",
            exit_code=sanitizer.returncode,
        )
    except OSError:
        return False
    except BaseException as exc:
        return _skip_diagram_candidate(
            design_tmpdir=design_tmpdir,
            reason=f"sanitizer-exception:{exc.__class__.__name__}",
            exit_code=1,
        )


def review_provenance(design_tmpdir: Path) -> tuple[str, int, bool]:
    """Return (review_status, rounds_completed, provenance_present) from .step3-review-result.env."""
    result_env = design_tmpdir / ".step3-review-result.env"
    if not result_env.is_file() or result_env.is_symlink():
        return "", 0, False
    kv: dict[str, str] = {}
    for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k] = v
    status = kv.get("STEP3_REVIEW_LOOP_STATUS", "")
    if not status:
        loop = kv.get("LOOP_STATUS", "")
        tally = kv.get("TALLY_PLAN_REVIEW_STATUS", "")
        if loop == "complete":
            status = "complete"
        elif loop in {"cap-reached", "cap-hit"}:
            status = "cap-hit"
        elif loop in {
            "panel-failed", "panel-init-failed", "panel-skipped",
            "tally-error", "degraded-empty-collector",
            "main-agent-vote-required", "postplan-failed",
        }:
            status = loop
        elif tally:
            status = tally
    rounds_raw = kv.get("ROUNDS_COMPLETED", "") or kv.get("REVIEW_ROUND_COUNT", "")
    try:
        rounds = int(rounds_raw) if rounds_raw.strip().isdigit() else 0
    except (ValueError, AttributeError):
        rounds = 0
    if not rounds_raw.strip():
        # #5210 defense-in-depth: when a result-env writer omits both ROUNDS_COMPLETED
        # and REVIEW_ROUND_COUNT, recover the launched-round count from the durable
        # review-round-count.txt so a cleanly-reviewed plan is not refused as rounds=0.
        rounds = _read_review_round_count(design_tmpdir)
    provenance_present = bool(status or rounds_raw.strip())
    return status, rounds, provenance_present


def _splice_plan_provenance(*, text: str, review_status: str, rounds_completed: int) -> str:
    """Insert or replace review provenance above optional size trailers and before diff_lines."""
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"
    diff_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        if re.fullmatch(r"diff_lines: \d+", lines[idx].rstrip("\n")):
            diff_idx = idx
            break
    provenance = [
        f"review_status: {review_status}\n",
        f"rounds_completed: {rounds_completed}\n",
    ]
    if diff_idx < 0:
        trailer_start = len(lines)
        idx = len(lines) - 1
        while idx >= 0 and _is_trailer_region_line(lines[idx]):
            trailer_start = idx
            idx -= 1
        head = lines[:trailer_start]
        optional = [
            line
            for line in lines[trailer_start:]
            if _OPTIONAL_TRAILER_RE.fullmatch(line.rstrip("\n"))
        ]
        return "".join(head) + "".join(provenance) + "".join(optional)
    trailer_start = diff_idx
    optional_lines: list[str] = []
    idx = diff_idx - 1
    while idx >= 0 and _is_trailer_region_line(lines[idx]):
        stripped = lines[idx].rstrip("\n")
        if _OPTIONAL_TRAILER_RE.fullmatch(stripped):
            optional_lines.insert(0, lines[idx])
        trailer_start = idx
        idx -= 1
    return (
        "".join(lines[:trailer_start])
        + "".join(provenance)
        + "".join(optional_lines)
        + "".join(lines[diff_idx:])
    )


def publish_core(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {
        "--design-tmpdir": "",
        "--issue": "",
        "--session-id": "",
        "--claude-pid": "",
        "--repo": "",
    }
    skip_validate = False
    session_id_provided = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in parsed:
            if i + 1 >= len(args):
                return 5
            if token == "--session-id":
                session_id_provided = True
            parsed[token] = args[i + 1]
            i += 2
            continue
        if token == "--skip-validate":
            skip_validate = True
            i += 1
            continue
        if token in {"-h", "--help"}:
            return 0
        return 5
    if not parsed["--design-tmpdir"] or not parsed["--issue"] or not session_id_provided or not parsed["--claude-pid"]:
        return 5
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        return 5
    if not parsed["--claude-pid"].isdigit() or parsed["--claude-pid"] == "0":
        return 5
    if parsed["--repo"] and not _is_repo(parsed["--repo"]):
        return 5

    design_tmpdir = Path(parsed["--design-tmpdir"]).resolve()
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[3]))
    result_env = design_tmpdir / ".design-publish-result.env"
    final_summary_path = design_tmpdir / "final-summary.md"
    kvs: list[tuple[str, str]] = [
        ("PLAN_WRITE_OK", "false"),
        ("VALIDATE_STATUS", "not-run"),
        ("VALIDATE_DEFECT_COUNT", "0"),
        ("VALIDATE_SKIPPED_COUNT", "0"),
        ("VALIDATE_UNSAFE_TOKEN_COUNT", "0"),
        ("VALIDATE_MISSING_SCRIPT_COUNT", "0"),
        ("VALIDATE_LOG_FILE", ""),
        ("FINAL_SUMMARY_PATH", str(final_summary_path)),
        ("DESIGNED_ADMISSION_READY", "false"),
    ]
    if not (design_tmpdir / ".completed" / "step-5b").is_file():
        return 5
    composed_plan = design_tmpdir / "composed-plan.md"
    if not composed_plan.is_file() or composed_plan.stat().st_size == 0:
        kvs[1] = ("VALIDATE_STATUS", "defects-found")
        kvs[2] = ("VALIDATE_DEFECT_COUNT", "1")
        kvs[6] = ("VALIDATE_LOG_FILE", str(design_tmpdir / "validate-plan-commands.log"))
        _emit_rows(kvs)
        _ = _write_result_env(path=result_env, rows=kvs)
        return 4

    review_status, rounds_completed, provenance_present = review_provenance(design_tmpdir)
    step3_sentinel = (design_tmpdir / ".completed" / "step-3").is_file()
    _BLOCKED_STATUSES = {"panel-init-failed", "panel-skipped"}
    blocked_reason = ""
    if review_status in _BLOCKED_STATUSES:
        blocked_reason = review_status
    elif provenance_present and rounds_completed == 0:
        blocked_reason = "rounds_completed=0"
    elif review_status in _TERMINAL_STATUSES_REQUIRING_SENTINEL and not step3_sentinel:
        blocked_reason = f"{review_status} without .completed/step-3"
    if blocked_reason:
        print(
            f"**⚠ 5c: publish refused — review provenance indicates {blocked_reason};"
            " plan review did not complete; re-run /design**",
            flush=True,
        )
        kvs[1] = ("VALIDATE_STATUS", "defects-found")
        kvs[2] = ("VALIDATE_DEFECT_COUNT", "1")
        _emit_rows(kvs)
        _ = _write_result_env(path=result_env, rows=kvs)
        return 4

    if (design_tmpdir / ".pause-requested").is_file():
        pause = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "design",
                "pause-save",
                "--design-tmpdir",
                str(design_tmpdir),
                "--issue",
                parsed["--issue"],
                *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
            ],
            check=False,
        )
        return int(pause.returncode)

    if not _sanitize_diagram_candidate(design_tmpdir=design_tmpdir, plugin_root=plugin_root):
        return 5

    if review_status or rounds_completed:
        original = composed_plan.read_text(encoding="utf-8", errors="replace")
        _ = composed_plan.write_text(
            _splice_plan_provenance(text=original, review_status=review_status, rounds_completed=rounds_completed),
            encoding="utf-8",
        )

    if skip_validate:
        kvs[1] = ("VALIDATE_STATUS", "skipped")
    else:
        validate_env: dict[str, str] = {
            **os.environ,
            "DESIGN_TMPDIR": str(design_tmpdir),
            "LARCH_QUIET_DISABLE": "1",
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        }
        repo_root_arg = consumer_repo_root() or plugin_root
        validate = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "plan",
                "validate",
                "--plan-file",
                str(composed_plan),
                "--source-kind",
                "composed",
                "--design-tmpdir",
                str(design_tmpdir),
                "--repo-root",
                str(repo_root_arg),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=validate_env,
        )
        parsed_validate = _parse_kv((validate.stdout or "") + "\n" + (validate.stderr or ""))
        kvs[1] = ("VALIDATE_STATUS", parsed_validate.get("VALIDATE_STATUS", "not-run"))
        kvs[2] = ("VALIDATE_DEFECT_COUNT", parsed_validate.get("VALIDATE_DEFECT_COUNT", "0"))
        kvs[3] = ("VALIDATE_SKIPPED_COUNT", parsed_validate.get("VALIDATE_SKIPPED_COUNT", "0"))
        kvs[4] = ("VALIDATE_UNSAFE_TOKEN_COUNT", parsed_validate.get("VALIDATE_UNSAFE_TOKEN_COUNT", "0"))
        kvs[6] = ("VALIDATE_LOG_FILE", parsed_validate.get("VALIDATE_LOG_FILE", ""))
        kvs[5] = ("VALIDATE_MISSING_SCRIPT_COUNT", _count_missing_script_defects(kvs[6][1]))
        if kvs[1][1] == "defects-found":
            _emit_rows(kvs)
            _ = _write_result_env(path=result_env, rows=kvs)
            return 4
        if validate.returncode != 0 or kvs[1][1] != "ok":
            return 5

    redacted_plan = design_tmpdir / "composed-plan.redacted.md"
    redact = subprocess.run(
        [sys.executable, str(plugin_root / "python" / "cli.py"), "redact", "secrets"],
        input=composed_plan.read_text(encoding="utf-8", errors="replace"),
        text=True,
        capture_output=True,
        check=False,
    )
    if redact.returncode != 0 or not redact.stdout:
        return 5
    _ = redacted_plan.write_text(redact.stdout, encoding="utf-8")

    block = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "named-block",
            "write",
            "--marker",
            "plan",
            "--issue",
            parsed["--issue"],
            "--content-file",
            str(redacted_plan),
            *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
        ],
        stdout=subprocess.DEVNULL,
        check=False,
    )
    if block.returncode != 0:
        _emit_rows(kvs)
        return 1 if _write_result_env(path=result_env, rows=kvs) else 3
    kvs[0] = ("PLAN_WRITE_OK", "true")

    # Upsert the architecture diagram into the shared larch:diagrams comment.
    # Step 5c consumes post-approval artifacts written by Step 5b.5. It clears
    # Architecture content only when Step 5b.5 wrote an explicit skip marker; a
    # missing tmpdir file after the sentinel is warning-only and must not wipe a
    # valid issue diagram.
    arch_file = design_tmpdir / "architecture-diagram.md"
    arch_skipped = design_tmpdir / "architecture-diagram.skipped"
    upsert_args: list[str] = ["--issue", parsed["--issue"]]
    if parsed["--repo"]:
        upsert_args += ["--repo", parsed["--repo"]]
    run_upsert = False
    if arch_file.is_file() and arch_file.stat().st_size > 0:
        run_upsert = True
        upsert_args += ["--architecture-file", str(arch_file)]
    elif arch_skipped.is_file():
        run_upsert = True
        upsert_args += ["--clear-architecture"]
    else:
        run_logs.append_execution_issue(
            log_file=design_tmpdir / "execution-issues.md",
            category="Warnings",
            entry=design_diagram_log.bounded_diagram_warning_body(
                reason="diagram-artifact-missing-after-step5b5",
                exit_code=0,
            ),
        )
    if run_upsert:
        upsert = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "diagrams",
                "upsert",
                *upsert_args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        upsert_stderr_file = design_tmpdir / "diagrams-architecture-upsert.stderr"
        _ = upsert_stderr_file.write_text(upsert.stderr or "", encoding="utf-8")
        _ = (design_tmpdir / "diagrams-architecture-upsert.stdout").write_text(
            upsert.stdout or "", encoding="utf-8"
        )
        upsert_kv = _parse_kv(upsert.stdout)
        upsert_status = upsert_kv.get("UPSERT_STATUS", "")
        if upsert_status:
            kvs.append(("UPSERT_STATUS", upsert_status))
        if upsert_kv.get("ARCHITECTURE_SOURCE"):
            kvs.append(("ARCHITECTURE_SOURCE", upsert_kv["ARCHITECTURE_SOURCE"]))
        if upsert_status == "failed" or upsert.returncode != 0:
            _ = subprocess.run(
                [
                    sys.executable,
                    str(plugin_root / "python" / "cli.py"),
                    "run-log",
                    "append-failure",
                    "--log",
                    str(design_tmpdir / "execution-issues.md"),
                    "--site",
                    "design Step 5c.5",
                    "--tool",
                    "python/cli.py diagrams upsert architecture",
                    "--exit-code",
                    str(upsert.returncode),
                    "--category",
                    "Warnings",
                    "--output-file",
                    str(upsert_stderr_file),
                    "--redact",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    rename: subprocess.CompletedProcess[str] = subprocess.run(
        [
            sys.executable,
            str(plugin_root / "python" / "cli.py"),
            "tracking-issue",
            "rename",
            "--issue",
            parsed["--issue"],
            "--state",
            "designed",
            *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    renamed = _parse_kv(rename.stdout)
    renamed_value = renamed.get("RENAMED", "")
    new_title = renamed.get("NEW_TITLE", "")
    if renamed_value:
        kvs.append(("RENAMED", renamed_value))
    if new_title:
        kvs.append(("NEW_TITLE", new_title))
    if renamed_value == "true" or new_title.startswith("[DESIGNED] "):
        kvs[-1] = ("DESIGNED_ADMISSION_READY", "true")

    if parsed["--session-id"]:
        publish: subprocess.CompletedProcess[str] = subprocess.run(
            [
                sys.executable,
                str(plugin_root / "python" / "cli.py"),
                "design",
                "log-publish",
                "--design-tmpdir",
                str(design_tmpdir),
                "--run-id",
                parsed["--session-id"],
                "--issue",
                parsed["--issue"],
                *(["--repo", parsed["--repo"]] if parsed["--repo"] else []),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        publish_kv = _parse_kv(publish.stdout)
        if "PUBLISH_OK" in publish_kv:
            kvs.append(("PUBLISH_OK", publish_kv["PUBLISH_OK"]))
        for key in ("PR_NUMBER", "PR_URL", "RECOVERY_BRANCH"):
            if publish_kv.get(key):
                kvs.append((key, publish_kv[key]))
                if key == "RECOVERY_BRANCH":
                    kvs.append(("LOG_RECOVERY_BRANCH", publish_kv[key]))
        if publish.returncode != 0 and not publish_kv.get("RECOVERY_BRANCH"):
            _replace_kv(rows=kvs, key="PUBLISH_OK", value="false")
            _emit_rows(kvs)
            _ = _write_result_env(path=result_env, rows=kvs)
            return 5
        # Re-surface the dropped secret-rotation warning: the design log is scrubbed
        # before commit, and a non-zero SECRET_SCRUB_VIOLATIONS count from log-publish
        # means a secret-shaped value was redacted from the committed logs. Warn the
        # operator to rotate it (the scrub itself prevents the leak; the operator was
        # no longer being told to rotate after the #3681 port). Emit on recoverable
        # PUBLISH_OK=false paths too; only scrub-fatal rc 5 above suppresses it.
        scrub_violations = publish_kv.get("SECRET_SCRUB_VIOLATIONS", "0")
        if scrub_violations.isdigit() and int(scrub_violations) > 0:
            print(
                f"**⚠ SECURITY: redact scrub-log-secrets redacted {scrub_violations} "
                "secret-shaped value(s) from this /design run's logs before flush. "
                "A credential was almost certainly exposed in the session; ROTATE it now "
                "and check chat/PRs for the same value.**",
                flush=True,
            )
        if publish.returncode == 0 and publish_kv.get("PUBLISH_OK") == "false":
            _emit_rows(kvs)
            return 0 if _write_result_env(path=result_env, rows=kvs) else 3
    _emit_rows(kvs)
    return 0 if _write_result_env(path=result_env, rows=kvs) else 3


def publish_main(argv: Sequence[str]) -> int:
    return publish_core(argv)
