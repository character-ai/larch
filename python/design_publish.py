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
