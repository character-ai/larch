"""Python CLI entrypoint for /design publish."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


def _emit_rows(rows: list[tuple[str, str]]) -> None:
    for key, value in rows:
        print(f"{key}={value}")


def _parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key] = value
    return out


def _is_repo(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", value))


_PROVENANCE_META_KEYS = ("review_status", "rounds_completed")
_OPTIONAL_TRAILER_RE = re.compile(
    r"^(diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+)$"
)
_TERMINAL_STATUSES_REQUIRING_SENTINEL = frozenset({"complete", "cap-hit"})


def _is_trailer_region_line(line: str) -> bool:
    stripped = line.rstrip("\n")
    if any(stripped.startswith(f"{key}: ") for key in _PROVENANCE_META_KEYS):
        return True
    return bool(_OPTIONAL_TRAILER_RE.fullmatch(stripped))


def _review_provenance(design_tmpdir: Path) -> tuple[str, int, bool]:
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
    provenance_present = bool(status or rounds_raw.strip())
    return status, rounds, provenance_present


def _splice_plan_provenance(text: str, review_status: str, rounds_completed: int) -> str:
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


def publish_main(argv: Sequence[str]) -> int:
    args = list(argv)
    parsed = {
        "--design-tmpdir": "",
        "--issue": "",
        "--session-id": "",
        "--claude-pid": "",
        "--repo": "",
    }
    skip_validate = False
    i = 0
    while i < len(args):
        token = args[i]
        if token in parsed:
            if i + 1 >= len(args):
                return 5
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
    if not parsed["--design-tmpdir"] or not parsed["--issue"] or not parsed["--session-id"] or not parsed["--claude-pid"]:
        return 5
    if not parsed["--issue"].isdigit() or parsed["--issue"] == "0":
        return 5
    if not parsed["--claude-pid"].isdigit() or parsed["--claude-pid"] == "0":
        return 5
    if parsed["--repo"] and not _is_repo(parsed["--repo"]):
        return 5

    design_tmpdir = Path(parsed["--design-tmpdir"]).resolve()
    plugin_root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    result_env = design_tmpdir / ".design-publish-result.env"
    final_summary_path = design_tmpdir / "final-summary.md"
    kvs: list[tuple[str, str]] = [
        ("PLAN_WRITE_OK", "false"),
        ("VALIDATE_STATUS", "not-run"),
        ("VALIDATE_DEFECT_COUNT", "0"),
        ("VALIDATE_SKIPPED_COUNT", "0"),
        ("VALIDATE_UNSAFE_TOKEN_COUNT", "0"),
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
        kvs[5] = ("VALIDATE_LOG_FILE", str(design_tmpdir / "validate-plan-commands.log"))
        _emit_rows(kvs)
        _ = result_env.write_text("\n".join(f"{k}={v}" for k, v in kvs) + "\n", encoding="utf-8")
        return 4

    review_status, rounds_completed, provenance_present = _review_provenance(design_tmpdir)
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
        _ = result_env.write_text("\n".join(f"{k}={v}" for k, v in kvs) + "\n", encoding="utf-8")
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

    if review_status or rounds_completed:
        original = composed_plan.read_text(encoding="utf-8", errors="replace")
        _ = composed_plan.write_text(
            _splice_plan_provenance(original, review_status, rounds_completed),
            encoding="utf-8",
        )

    if skip_validate:
        kvs[1] = ("VALIDATE_STATUS", "skipped")
    else:
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
                str(plugin_root),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "DESIGN_TMPDIR": str(design_tmpdir), "LARCH_QUIET_DISABLE": "1"},
        )
        parsed_validate = _parse_kv((validate.stdout or "") + "\n" + (validate.stderr or ""))
        kvs[1] = ("VALIDATE_STATUS", parsed_validate.get("VALIDATE_STATUS", "not-run"))
        kvs[2] = ("VALIDATE_DEFECT_COUNT", parsed_validate.get("VALIDATE_DEFECT_COUNT", "0"))
        kvs[3] = ("VALIDATE_SKIPPED_COUNT", parsed_validate.get("VALIDATE_SKIPPED_COUNT", "0"))
        kvs[4] = ("VALIDATE_UNSAFE_TOKEN_COUNT", parsed_validate.get("VALIDATE_UNSAFE_TOKEN_COUNT", "0"))
        kvs[5] = ("VALIDATE_LOG_FILE", parsed_validate.get("VALIDATE_LOG_FILE", ""))
        if kvs[1][1] == "defects-found":
            _emit_rows(kvs)
            _ = result_env.write_text("\n".join(f"{k}={v}" for k, v in kvs) + "\n", encoding="utf-8")
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
        check=False,
    )
    if block.returncode != 0:
        _emit_rows(kvs)
        return 1
    kvs[0] = ("PLAN_WRITE_OK", "true")

    rename = subprocess.run(
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

    publish = subprocess.run(
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
    _ = result_env.write_text("\n".join(f"{k}={v}" for k, v in kvs) + "\n", encoding="utf-8")
    _emit_rows(kvs)
    return 0
