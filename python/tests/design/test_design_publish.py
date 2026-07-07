"""Tests for /design publish port."""
# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportMissingParameterType=false
# pyright: reportUnknownParameterType=false

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from larch.calibration import difficulty
from larch.design import design_publish
from larch.design import design_step5c

if TYPE_CHECKING:
    import pytest


def _write_fake_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
args = sys.argv[1:]
call_log = os.environ.get("FAKE_CLI_CALL_LOG")
if call_log:
    with open(call_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\\n")
if args[:2] == ["plan","validate"]:
    plan_path = args[args.index("--plan-file") + 1]
    plan_text = open(plan_path, encoding="utf-8", errors="replace").read()
    trailer_re = re.compile(r"^(review_status: .+|rounds_completed: [0-9]+|difficulty: (TRIVIAL|MODERATE|HARD)|diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+|oversize_override: operator|diff_lines: [0-9]+)$")
    difficulty_re = re.compile(r"^difficulty: (TRIVIAL|MODERATE|HARD)$")
    lines = plan_text.splitlines()
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    start = end
    while start > 0 and trailer_re.fullmatch(lines[start - 1]):
        start -= 1
    trailing_difficulty = ""
    if start != end:
        for line in reversed(lines[start:end]):
            match = difficulty_re.fullmatch(line.strip())
            if match:
                trailing_difficulty = match.group(1)
                break
    if os.environ.get("FAKE_CLI_REQUIRE_DIFFICULTY") == "1" and os.environ.get("LARCH_REQUIRE_PLAN_DIFFICULTY") == "1" and not trailing_difficulty:
        print("VALIDATE_STATUS=defects-found")
        print("VALIDATE_DEFECT_COUNT=1")
        print("VALIDATE_SKIPPED_COUNT=0")
        print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
        print("VALIDATE_LOG_FILE=/tmp/validate.log")
        raise SystemExit(1)
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    print("VALIDATE_SKIPPED_COUNT=0")
    print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
    print("VALIDATE_LOG_FILE=/tmp/validate.log")
    raise SystemExit(0)
if args[:2] == ["plan","check-size"]:
    if os.environ.get("FAKE_CLI_CHECK_SIZE_FAIL"):
        print("PLAN_SIZE_STATUS=failed")
        raise SystemExit(1)
    print("PLAN_SIZE_STATUS=ok")
    size_trigger_fired = os.environ.get("FAKE_CLI_SIZE_TRIGGER_FIRED")
    if size_trigger_fired != "__omit__":
        print("SIZE_TRIGGER_FIRED=" + (size_trigger_fired if size_trigger_fired is not None else "false"))
    raise SystemExit(0)
if args[:2] == ["redact","secrets"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
if args[:2] == ["named-block","write"]:
    noise = os.environ.get("FAKE_CLI_NAMED_BLOCK_STDOUT")
    if noise:
        print(noise)
    if os.environ.get("FAKE_CLI_NAMED_BLOCK_FAIL"):
        raise SystemExit(1)
    raise SystemExit(0)
if args[:2] == ["tracking-issue","rename"]:
    print("RENAMED=true")
    print("NEW_TITLE=[DESIGNED] Example")
    raise SystemExit(0)
if args[:2] == ["token","claude-source"]:
    if os.environ.get("FAKE_CLI_TOKEN_SOURCE_FAIL"):
        raise SystemExit(1)
    transcript = os.environ.get("FAKE_CLI_TRANSCRIPT_PATH", "/tmp/transcript.jsonl")
    session_dir = os.environ.get("FAKE_CLI_SESSION_DIR", "/tmp")
    print("TRANSCRIPT_PATH=" + transcript)
    print("SESSION_DIR=" + session_dir)
    print("SESSION_UUID=" + os.environ.get("FAKE_CLI_SESSION_UUID", "RUN1"))
    raise SystemExit(0)
if args[:2] == ["session","write-design-env"]:
    output = args[args.index("--output") + 1]
    design_tmpdir = args[args.index("--design-tmpdir") + 1]
    session_id = args[args.index("--session-id") + 1]
    source_file = args[args.index("--claude-source-file") + 1] if "--claude-source-file" in args else ""
    with open(output, "w", encoding="utf-8") as f:
        f.write("DESIGN_TMPDIR=" + design_tmpdir + "\\nSESSION_TMPDIR=" + design_tmpdir + "\\nSESSION_ID=" + session_id + "\\n")
        if source_file:
            f.write("LARCH_CLAUDE_SOURCE_FILE=" + source_file + "\\n")
    raise SystemExit(0)
if args[:2] == ["run-log","capture-transcript"]:
    if os.environ.get("FAKE_CLI_CAPTURE_SKIP"):
        print("SESSION_TRANSCRIPT_STATUS=render-empty")
        raise SystemExit(0)
    log_root = args[args.index("--log-root") + 1]
    skill = args[args.index("--skill") + 1]
    run_id = args[args.index("--run-id") + 1]
    dest = os.path.join(log_root, skill, run_id, "session-transcript.jsonl")
    if os.environ.get("FAKE_CLI_CAPTURE_NO_FILE") != "1":
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write('{"v":3}\\n')
    print("SESSION_TRANSCRIPT_STATUS=captured")
    raise SystemExit(0)
if args[:2] == ["mermaid","sanitize"]:
    if os.environ.get("FAKE_CLI_MERMAID_REJECT"):
        print("STATUS=rejected")
        print("REASON_TOKEN=pipe-in-node-label fence=1 line=2")
        if os.environ.get("FAKE_CLI_MERMAID_LEAK"):
            print("graph TD; SECRET-->B;")
        raise SystemExit(1)
    print("STATUS=ok")
    print("FENCE_COUNT=1")
    raise SystemExit(0)
if args[:3] == ["design","log-publish","--design-tmpdir"] or args[:2] == ["design","log-publish"]:
    import os
    _rc = int(os.environ.get("FAKE_CLI_LOG_PUBLISH_RC", "0"))
    if os.environ.get("FAKE_CLI_LOG_PUBLISH_PARTIAL") != "1":
        print("PUBLISH_OK=" + os.environ.get("FAKE_CLI_LOG_PUBLISH_OK", "true"))
        if os.environ.get("FAKE_CLI_LOG_PUBLISH_PR", "1") == "1":
            print("PR_NUMBER=99")
            print("PR_URL=https://github.com/owner/repo/pull/99")
        _recovery = os.environ.get("FAKE_CLI_LOG_PUBLISH_RECOVERY_BRANCH")
        if _recovery:
            print("RECOVERY_BRANCH=" + _recovery)
    _scrub = os.environ.get("FAKE_CLI_SCRUB_VIOLATIONS")
    if _scrub:
        print("SECRET_SCRUB_VIOLATIONS=" + _scrub)
    raise SystemExit(_rc)
if args[:2] == ["diagrams","upsert"]:
    import json, os
    log = os.environ.get("FAKE_CLI_UPSERT_LOG")
    if log:
        with open(log, "w", encoding="utf-8") as f:
            json.dump(args, f)
    if os.environ.get("FAKE_CLI_UPSERT_FAIL"):
        sys.stderr.write("simulated upsert failure\\n")
        print("UPSERT_STATUS=failed")
        raise SystemExit(1)
    print("UPSERT_STATUS=ok")
    print("ARCHITECTURE_SOURCE=cleared" if "--clear-architecture" in args else "ARCHITECTURE_SOURCE=new")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_recording_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
args = sys.argv[1:]
if args[:2] == ["plan","validate"]:
    repo_root = ""
    for i, arg in enumerate(args):
        if arg == "--repo-root" and i + 1 < len(args):
            repo_root = args[i + 1]
    with open(os.environ["RECORD_FILE"], "w", encoding="utf-8") as f:
        f.write("REPO_ROOT=" + repo_root + "\\n")
        f.write("CLAUDE_PLUGIN_ROOT=" + os.environ.get("CLAUDE_PLUGIN_ROOT", "") + "\\n")
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    print("VALIDATE_SKIPPED_COUNT=0")
    print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
    print("VALIDATE_LOG_FILE=/tmp/validate.log")
    raise SystemExit(0)
if args[:2] == ["plan","check-size"]:
    print("PLAN_SIZE_STATUS=ok")
    print("SIZE_TRIGGER_FIRED=false")
    raise SystemExit(0)
if args[:2] == ["redact","secrets"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
if args[:2] == ["named-block","write"]:
    raise SystemExit(0)
if args[:2] == ["tracking-issue","rename"]:
    print("RENAMED=true")
    print("NEW_TITLE=[DESIGNED] Example")
    raise SystemExit(0)
if args[:2] == ["token","claude-source"]:
    if os.environ.get("FAKE_CLI_TOKEN_SOURCE_FAIL"):
        raise SystemExit(1)
    transcript = os.environ.get("FAKE_CLI_TRANSCRIPT_PATH", "/tmp/transcript.jsonl")
    session_dir = os.environ.get("FAKE_CLI_SESSION_DIR", "/tmp")
    print("TRANSCRIPT_PATH=" + transcript)
    print("SESSION_DIR=" + session_dir)
    print("SESSION_UUID=" + os.environ.get("FAKE_CLI_SESSION_UUID", "RUN1"))
    raise SystemExit(0)
if args[:2] == ["session","write-design-env"]:
    output = args[args.index("--output") + 1]
    design_tmpdir = args[args.index("--design-tmpdir") + 1]
    session_id = args[args.index("--session-id") + 1]
    source_file = args[args.index("--claude-source-file") + 1] if "--claude-source-file" in args else ""
    with open(output, "w", encoding="utf-8") as f:
        f.write("DESIGN_TMPDIR=" + design_tmpdir + "\\nSESSION_TMPDIR=" + design_tmpdir + "\\nSESSION_ID=" + session_id + "\\n")
        if source_file:
            f.write("LARCH_CLAUDE_SOURCE_FILE=" + source_file + "\\n")
    raise SystemExit(0)
if args[:2] == ["run-log","capture-transcript"]:
    if os.environ.get("FAKE_CLI_CAPTURE_SKIP"):
        print("SESSION_TRANSCRIPT_STATUS=render-empty")
        raise SystemExit(0)
    log_root = args[args.index("--log-root") + 1]
    skill = args[args.index("--skill") + 1]
    run_id = args[args.index("--run-id") + 1]
    dest = os.path.join(log_root, skill, run_id, "session-transcript.jsonl")
    if os.environ.get("FAKE_CLI_CAPTURE_NO_FILE") != "1":
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write('{"v":3}\\n')
    print("SESSION_TRANSCRIPT_STATUS=captured")
    raise SystemExit(0)
if args[:2] == ["mermaid","sanitize"]:
    print("STATUS=ok")
    print("FENCE_COUNT=1")
    raise SystemExit(0)
if args[:3] == ["design","log-publish","--design-tmpdir"] or args[:2] == ["design","log-publish"]:
    print("PUBLISH_OK=true")
    print("PR_NUMBER=99")
    print("PR_URL=https://github.com/owner/repo/pull/99")
    raise SystemExit(0)
if args[:2] == ["diagrams","upsert"]:
    print("UPSERT_STATUS=ok")
    print("ARCHITECTURE_SOURCE=cleared" if "--clear-architecture" in args else "ARCHITECTURE_SOURCE=new")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_difficulty_recording_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path
args = sys.argv[1:]
call_log = os.environ.get("FAKE_CLI_CALL_LOG")
if call_log:
    with open(call_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\\n")
if args[:2] == ["plan","validate"]:
    repo_root = ""
    for i, arg in enumerate(args):
        if arg == "--repo-root" and i + 1 < len(args):
            repo_root = args[i + 1]
    plan_path = Path(args[args.index("--plan-file") + 1])
    plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
    record_file = os.environ.get("RECORD_FILE")
    if record_file:
        with open(record_file, "w", encoding="utf-8") as f:
            f.write("REPO_ROOT=" + repo_root + "\\n")
            f.write("CLAUDE_PLUGIN_ROOT=" + os.environ.get("CLAUDE_PLUGIN_ROOT", "") + "\\n")
            f.write("LARCH_REQUIRE_PLAN_DIFFICULTY=" + os.environ.get("LARCH_REQUIRE_PLAN_DIFFICULTY", "") + "\\n")
    trailer_re = re.compile(r"^(review_status: .+|rounds_completed: [0-9]+|difficulty: (TRIVIAL|MODERATE|HARD)|diff_added: [0-9]+|diff_deleted: [0-9]+|mechanical_churn: .+|oversize_override: operator|diff_lines: [0-9]+)$")
    difficulty_re = re.compile(r"^difficulty: (TRIVIAL|MODERATE|HARD)$")
    lines = plan_text.splitlines()
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    start = end
    while start > 0 and trailer_re.fullmatch(lines[start - 1]):
        start -= 1
    trailing_difficulty = ""
    if start != end:
        for line in reversed(lines[start:end]):
            match = difficulty_re.fullmatch(line.strip())
            if match:
                trailing_difficulty = match.group(1)
                break
    if os.environ.get("FAKE_CLI_REQUIRE_DIFFICULTY") == "1" and os.environ.get("LARCH_REQUIRE_PLAN_DIFFICULTY") == "1" and not trailing_difficulty:
        print("VALIDATE_STATUS=defects-found")
        print("VALIDATE_DEFECT_COUNT=1")
        print("VALIDATE_SKIPPED_COUNT=0")
        print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
        print("VALIDATE_LOG_FILE=/tmp/validate.log")
        raise SystemExit(1)
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    print("VALIDATE_SKIPPED_COUNT=0")
    print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
    print("VALIDATE_LOG_FILE=/tmp/validate.log")
    raise SystemExit(0)
if args[:2] == ["plan","check-size"]:
    print("PLAN_SIZE_STATUS=ok")
    print("SIZE_TRIGGER_FIRED=false")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _write_missing_script_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import os
import sys
args = sys.argv[1:]
if args[:2] == ["plan","validate"]:
    log = os.environ["VALIDATE_LOG"]
    with open(log, "w", encoding="utf-8") as f:
        f.write("DEFECT script=scripts/a.sh kind=missing-script\\n")
        f.write("DEFECT script=scripts/b.sh kind=missing-script\\n")
        f.write("DEFECT script=scripts/c.sh kind=unsafe-token token=<redacted>\\n")
    print("VALIDATE_STATUS=defects-found")
    print("VALIDATE_DEFECT_COUNT=3")
    print("VALIDATE_SKIPPED_COUNT=0")
    print("VALIDATE_UNSAFE_TOKEN_COUNT=1")
    print("VALIDATE_LOG_FILE=" + log)
    raise SystemExit(1)
if args[:2] == ["plan","check-size"]:
    print("PLAN_SIZE_STATUS=ok")
    print("SIZE_TRIGGER_FIRED=false")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_publish_with_fake_cli(
    tmp_path: Path,
    env_overrides: dict[str, str],
) -> tuple[subprocess.CompletedProcess[str], Path]:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env.update(env_overrides)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return result, design



def test_sanitize_diagram_candidate_missing_candidate(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)

    design_publish._sanitize_diagram_candidate(design_tmpdir=design, plugin_root=plugin_root)

    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / "architecture-diagram.skipped").is_file()
    assert not (design / "architecture-diagram.md").is_file()


def test_sanitize_diagram_candidate_accepted(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / "architecture-diagram.candidate.md").write_text(
        "## Arch\n```mermaid\ngraph TD; A-->B;\n```\n", encoding="utf-8"
    )

    design_publish._sanitize_diagram_candidate(design_tmpdir=design, plugin_root=plugin_root)

    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / "architecture-diagram.md").is_file()
    assert not (design / "architecture-diagram.candidate.md").is_file()
    assert not (design / "architecture-diagram.skipped").is_file()


def test_sanitize_diagram_candidate_rejected(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / "architecture-diagram.candidate.md").write_text(
        "## Arch\n```mermaid\ngraph TD; A-->B;\n```\n", encoding="utf-8"
    )
    orig_env = os.environ.copy()
    os.environ["FAKE_CLI_MERMAID_REJECT"] = "1"
    try:
        design_publish._sanitize_diagram_candidate(design_tmpdir=design, plugin_root=plugin_root)
    finally:
        os.environ.clear()
        os.environ.update(orig_env)

    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / "architecture-diagram.skipped").is_file()
    assert not (design / "architecture-diagram.md").is_file()
    assert not (design / "architecture-diagram.candidate.md").is_file()


def test_publish_main_completes_step5b5_with_missing_candidate(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (design / "architecture-diagram.md").write_text("stale diagram\n", encoding="utf-8")
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / "architecture-diagram.skipped").is_file()
    assert not (design / "architecture-diagram.md").exists()
    recorded = json.loads(upsert_log.read_text(encoding="utf-8"))
    assert "--clear-architecture" in recorded
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "candidate-missing" in issues


def test_publish_requires_composed_plan(tmp_path: Path) -> None:
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "PLAN_WRITE_OK=false" in result.stdout
    assert "VALIDATE_STATUS=defects-found" in result.stdout


def test_publish_rejects_missing_difficulty_when_validation_enforces_it(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_difficulty_recording_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("## Plan\nbody\n\ndiff_lines: 1\n", encoding="utf-8")
    call_log = tmp_path / "calls.ndjson"
    record_file = tmp_path / "validate-invocation.env"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)
    env["FAKE_CLI_REQUIRE_DIFFICULTY"] = "1"
    env["RECORD_FILE"] = str(record_file)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 4
    recorded = dict(line.split("=", 1) for line in record_file.read_text(encoding="utf-8").splitlines() if "=" in line)
    assert recorded["LARCH_REQUIRE_PLAN_DIFFICULTY"] == "1"
    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    assert all(call[:2] != ["named-block", "write"] for call in calls)


def test_publish_recovers_auto_composed_embedded_difficulty_without_raw_sidecar(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-3").write_text("", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=2\n",
        encoding="utf-8",
    )
    _ = (design / "plan.txt").write_text(
        """## Plan

## Approach

Implement the fix.

## Testing strategy

Run targeted publish validation.

## Edge cases

Keep strict final-trailer validation.

difficulty: MODERATE
confidence: high
diff_lines: 12
""",
        encoding="utf-8",
    )
    assert not (design / difficulty.DESIGN_RAW_RATING_BASENAME).exists()

    design_step5c._auto_compose_plan_md(design)
    composed_before = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert difficulty.trailing_plan_difficulty(composed_before) == ""
    assert difficulty.plan_difficulty(composed_before) == "MODERATE"

    call_log = tmp_path / "calls.ndjson"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)
    env["FAKE_CLI_REQUIRE_DIFFICULTY"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    lines = composed.splitlines()
    diff_idx = next(i for i, line in enumerate(lines) if line.startswith("diff_lines:"))
    assert lines[diff_idx - 3] == "review_status: complete"
    assert lines[diff_idx - 2] == "rounds_completed: 2"
    assert lines[diff_idx - 1] == "difficulty: MODERATE"
    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    sync = next(call for call in calls if call[:2] == ["difficulty", "sync-labels"])
    assert sync[sync.index("--tier") + 1] == "MODERATE"
    record = next(call for call in calls if call[:2] == ["difficulty", "write-record"])
    assert record[record.index("--design-tier") + 1] == "MODERATE"


def test_step5c_auto_compose_preserves_oversize_override(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / "plan.txt").write_text(
        "## Plan\n\nBody.\n\n## Testing strategy\n\nRun tests.\n\ndifficulty: MODERATE\noversize_override: operator\ndiff_lines: 12\n",
        encoding="utf-8",
    )

    design_step5c._auto_compose_plan_md(design)  # pyright: ignore[reportPrivateUsage]

    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "oversize_override: operator\ndiff_lines: 12\n" in composed


def test_publish_prefers_raw_sidecar_adjusted_tier_over_wire_plan_tier(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("## Plan\nbody\n\ndifficulty: HARD\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / difficulty.DESIGN_RAW_RATING_BASENAME).write_text(
        '{"predicted_tier":"TRIVIAL","confidence":"low","rationale":"raw sidecar"}\n',
        encoding="utf-8",
    )
    call_log = tmp_path / "calls.ndjson"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "difficulty: MODERATE" in (design / "composed-plan.md").read_text(encoding="utf-8")
    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    sync = next(call for call in calls if call[:2] == ["difficulty", "sync-labels"])
    assert sync[sync.index("--tier") + 1] == "MODERATE"
    record = next(call for call in calls if call[:2] == ["difficulty", "write-record"])
    assert record[record.index("--design-tier") + 1] == "MODERATE"


def test_publish_rejects_invalid_raw_sidecar_before_label_or_record_writes(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("## Plan\nbody\n\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / difficulty.DESIGN_RAW_RATING_BASENAME).write_text("{invalid-json}\n", encoding="utf-8")
    call_log = tmp_path / "calls.ndjson"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 5
    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    assert calls == [["plan", "check-size", "--design-tmpdir", str(design), "--plan-file", str(design / "plan.txt")]]


def test_publish_passes_consumer_repo_root_and_preserves_plugin_root(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_recording_cli(plugin_root / "python" / "cli.py")
    recorder = tmp_path / "validate-invocation.env"

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _ = subprocess.run(["git", "init", "-q", str(consumer)], check=True)
    script = consumer / "scripts" / "consumer-only.sh"
    script.parent.mkdir()
    _ = script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    script.chmod(0o755)

    design = consumer / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text(
        "## Plan\n\n```bash\nbash scripts/consumer-only.sh\n```\n\ndiff_lines: 1\n",
        encoding="utf-8",
    )

    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["RECORD_FILE"] = str(recorder)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(consumer),
    )

    assert result.returncode == 0, result.stderr
    recorded = dict(
        line.split("=", 1) for line in recorder.read_text(encoding="utf-8").splitlines() if "=" in line
    )
    assert Path(recorded["REPO_ROOT"]).resolve() == consumer.resolve()
    assert Path(recorded["CLAUDE_PLUGIN_ROOT"]).resolve() == plugin_root.resolve()
    assert "PLAN_WRITE_OK=true" in result.stdout
    assert "VALIDATE_STATUS=ok" in result.stdout
    assert "PUBLISH_RC=4" not in result.stdout


def test_publish_reports_missing_script_count_from_validate_log(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_missing_script_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    log = tmp_path / "validate-plan-commands.log"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["VALIDATE_LOG"] = str(log)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 4
    assert "VALIDATE_MISSING_SCRIPT_COUNT=2" in result.stdout
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert "VALIDATE_MISSING_SCRIPT_COUNT=2" in result_env


def test_publish_success_writes_result_env(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
            "--repo",
            "owner/repo",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PLAN_WRITE_OK=true" in result.stdout
    assert "PUBLISH_OK=true" in result.stdout
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "review_status:" not in composed.split("diff_lines:")[0]
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert "PR_NUMBER=99" in result_env


def test_publish_suppresses_named_block_stdout_noise(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_NAMED_BLOCK_STDOUT"] = "NAMED_BLOCK_STDOUT_SENTINEL"

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "NAMED_BLOCK_STDOUT_SENTINEL" not in result.stdout
    assert "PLAN_WRITE_OK=true" in result.stdout
    assert "PUBLISH_OK=true" in result.stdout


def test_publish_present_empty_session_id_skips_log_publish(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    call_log = tmp_path / "fake-cli-calls.ndjson"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    calls = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]
    assert result.returncode == 0, result.stderr
    assert "PLAN_WRITE_OK=true" in result.stdout
    assert "PUBLISH_OK=true" not in result.stdout
    assert all(call[:2] != ["design", "log-publish"] for call in calls)


def test_publish_omitted_session_id_fails_closed_before_plan_write(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    call_log = tmp_path / "fake-cli-calls.ndjson"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_CALL_LOG"] = str(call_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 5
    assert not call_log.exists()
    assert not (design / "composed-plan.redacted.md").exists()
    assert not (design / ".design-publish-result.env").exists()


def test_publish_refuses_cap_hit_without_step3_sentinel(tmp_path: Path) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=cap-hit\nLOOP_STATUS=cap-reached\nROUNDS_COMPLETED=5\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "cap-hit without .completed/step-3" in result.stdout


def test_publish_refuses_complete_without_step3_sentinel(tmp_path: Path) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\nROUNDS_COMPLETED=3\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "complete without .completed/step-3" in result.stdout


def test_publish_splices_provenance_above_diff_lines(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-3").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text(
        "## Plan\nbody\n\ndiff_lines: 3\n",
        encoding="utf-8",
    )
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=2\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    lines = composed.splitlines()
    diff_idx = next(i for i, line in enumerate(lines) if line.startswith("diff_lines:"))
    assert lines[diff_idx - 2] == "review_status: complete"
    assert lines[diff_idx - 1] == "rounds_completed: 2"
    assert lines[0] == "## Plan"


def test_publish_upserts_architecture_diagram_when_present(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (design / "architecture-diagram.md").write_text(
        "## Architecture Diagram\n```mermaid\ngraph TD; A-->B;\n```\n", encoding="utf-8"
    )
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
            "--repo",
            "owner/repo",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    recorded = json.loads(upsert_log.read_text(encoding="utf-8"))
    assert recorded[:2] == ["diagrams", "upsert"]
    assert "--architecture-file" in recorded
    assert str(design / "architecture-diagram.md") in recorded
    assert "--issue" in recorded
    assert "--repo" in recorded
    assert "owner/repo" in recorded
    assert "--clear-architecture" not in recorded
    assert "UPSERT_STATUS=ok" in result.stdout
    assert "ARCHITECTURE_SOURCE=new" in result.stdout
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert "UPSERT_STATUS=ok" in result_env
    assert "ARCHITECTURE_SOURCE=new" in result_env


def test_publish_promotes_valid_candidate_before_upsert(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    candidate = design / "architecture-diagram.candidate.md"
    diagram = "## Architecture Diagram\n```mermaid\ngraph TD; A-->B;\n```\n"
    _ = candidate.write_text(diagram, encoding="utf-8")
    _ = (design / "architecture-diagram.skipped").write_text("", encoding="utf-8")
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (design / ".completed" / "step-5b.5").is_file()
    assert not candidate.exists()
    assert not (design / "architecture-diagram.skipped").exists()
    assert (design / "architecture-diagram.md").read_text(encoding="utf-8") == diagram
    recorded = json.loads(upsert_log.read_text(encoding="utf-8"))
    assert "--architecture-file" in recorded
    assert str(design / "architecture-diagram.md") in recorded
    assert "ARCHITECTURE_SOURCE=new" in result.stdout


def test_publish_rejected_candidate_skips_and_sanitizes_logs(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (design / "architecture-diagram.candidate.md").write_text(
        "## Architecture Diagram\n```mermaid\ngraph TD; SECRET-->B;\n```\n",
        encoding="utf-8",
    )
    _ = (design / "architecture-diagram.md").write_text("stale diagram\n", encoding="utf-8")
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)
    env["FAKE_CLI_MERMAID_REJECT"] = "1"
    env["FAKE_CLI_MERMAID_LEAK"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert (design / ".completed" / "step-5b.5").is_file()
    assert (design / "architecture-diagram.skipped").is_file()
    assert not (design / "architecture-diagram.candidate.md").exists()
    assert not (design / "architecture-diagram.md").exists()
    recorded = json.loads(upsert_log.read_text(encoding="utf-8"))
    assert "--clear-architecture" in recorded
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    failure_log = (design / "architecture-diagram-sanitizer.failure.log").read_text(encoding="utf-8")
    assert "sanitizer-rejected:pipe-in-node-label" in issues
    assert "sanitizer-rejected:pipe-in-node-label" in failure_log
    assert "SECRET" not in result.stdout
    assert "SECRET" not in issues
    assert "graph TD" not in issues


def test_publish_clears_architecture_when_skipped(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    # DIAGRAM_REQUIRED=false leaves an empty architecture-diagram.skipped marker
    # and no architecture-diagram.md; the publish tail must clear the section.
    _ = (design / "architecture-diagram.skipped").write_text("", encoding="utf-8")
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    recorded = json.loads(upsert_log.read_text(encoding="utf-8"))
    assert recorded[:2] == ["diagrams", "upsert"]
    assert "--clear-architecture" in recorded
    assert "--architecture-file" not in recorded
    assert "ARCHITECTURE_SOURCE=cleared" in result.stdout


def test_publish_skips_upsert_when_no_diagram(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    upsert_log = tmp_path / "upsert-invocation.json"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_LOG"] = str(upsert_log)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert not upsert_log.exists()
    assert "UPSERT_STATUS=" not in result.stdout
    issues = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "diagram-artifact-missing-after-step5b5" in issues
    assert "clear-architecture" not in issues


def test_publish_nonfatal_when_architecture_upsert_fails(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (design / "architecture-diagram.md").write_text(
        "## Architecture Diagram\n```mermaid\ngraph TD; A-->B;\n```\n", encoding="utf-8"
    )
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_UPSERT_FAIL"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    # A failed architecture upsert is non-fatal: the plan block was already
    # written, so publish still completes and reports the failed status.
    assert result.returncode == 0, result.stderr
    assert "UPSERT_STATUS=failed" in result.stdout
    assert "PLAN_WRITE_OK=true" in result.stdout


def test_publish_warns_rotate_on_secret_scrub_violations(tmp_path: Path) -> None:
    # A non-zero SECRET_SCRUB_VIOLATIONS from log-publish means a secret-shaped
    # value was scrubbed from the committed design logs; the publish tail must warn
    # the operator to rotate the exposed credential (#4782).
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_SCRUB_VIOLATIONS"] = "2"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ROTATE it now" in result.stdout
    assert "redacted 2 secret-shaped value(s)" in result.stdout
    assert "PLAN_WRITE_OK=true" in result.stdout


def test_publish_no_rotate_warning_when_zero_violations(tmp_path: Path) -> None:
    # Zero violations (the common case) emits no rotate warning (#4782).
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["FAKE_CLI_SCRUB_VIOLATIONS"] = "0"
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "ROTATE it now" not in result.stdout


def test_publish_scrub_failure_explicit_kvs_returns_rc5_without_rotate_warning(tmp_path: Path) -> None:
    result, design = _run_publish_with_fake_cli(
        tmp_path,
        {
            "FAKE_CLI_LOG_PUBLISH_RC": "1",
            "FAKE_CLI_LOG_PUBLISH_OK": "false",
            "FAKE_CLI_SCRUB_VIOLATIONS": "2",
        },
    )

    assert result.returncode == 5
    assert "PUBLISH_OK=false" in result.stdout
    assert "ROTATE it now" not in result.stdout
    assert "PUBLISH_OK=false" in (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert 5 not in {0, 1, 3, 4}


def test_publish_scrub_failure_partial_stdout_returns_rc5(tmp_path: Path) -> None:
    result, _design = _run_publish_with_fake_cli(
        tmp_path,
        {
            "FAKE_CLI_LOG_PUBLISH_RC": "1",
            "FAKE_CLI_LOG_PUBLISH_PARTIAL": "1",
        },
    )

    assert result.returncode == 5
    assert "PUBLISH_OK=false" in result.stdout
    assert "ROTATE it now" not in result.stdout


def test_publish_recoverable_non_push_failure_returns_zero_without_rotate_warning(tmp_path: Path) -> None:
    result, design = _run_publish_with_fake_cli(
        tmp_path,
        {
            "FAKE_CLI_LOG_PUBLISH_OK": "false",
            "FAKE_CLI_LOG_PUBLISH_PR": "0",
            "FAKE_CLI_SCRUB_VIOLATIONS": "0",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=false" in result.stdout
    assert "ROTATE it now" not in result.stdout
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert "PUBLISH_OK=false" in result_env


def test_publish_recoverable_push_or_pr_failure_returns_zero_with_recovery_branch(tmp_path: Path) -> None:
    result, _design = _run_publish_with_fake_cli(
        tmp_path,
        {
            "FAKE_CLI_LOG_PUBLISH_OK": "false",
            "FAKE_CLI_LOG_PUBLISH_RECOVERY_BRANCH": "larch-logs/design-RUN1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=false" in result.stdout
    assert "RECOVERY_BRANCH=larch-logs/design-RUN1" in result.stdout
    assert "LOG_RECOVERY_BRANCH=larch-logs/design-RUN1" in result.stdout
    assert "ROTATE it now" not in result.stdout


def test_publish_recoverable_failure_still_warns_rotate_on_scrub_violations(tmp_path: Path) -> None:
    result, _design = _run_publish_with_fake_cli(
        tmp_path,
        {
            "FAKE_CLI_LOG_PUBLISH_OK": "false",
            "FAKE_CLI_LOG_PUBLISH_RECOVERY_BRANCH": "larch-logs/design-RUN1",
            "FAKE_CLI_SCRUB_VIOLATIONS": "1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=false" in result.stdout
    assert "RECOVERY_BRANCH=larch-logs/design-RUN1" in result.stdout
    assert "ROTATE it now" in result.stdout
    assert "redacted 1 secret-shaped value(s)" in result.stdout


def test_review_provenance_remains_importable() -> None:
    from larch.design.design_publish import review_provenance  # noqa: PLC0415

    assert callable(review_provenance)


def test_review_provenance_falls_back_to_round_count_file_when_keys_absent(tmp_path: Path) -> None:
    # #5210: a result env that omits ROUNDS_COMPLETED/REVIEW_ROUND_COUNT must recover
    # the launched-round count from review-round-count.txt rather than read rounds=0
    # and let publish_core refuse a cleanly-reviewed plan.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "LOOP_STATUS=zero-findings-degraded-panel\nTALLY_PLAN_REVIEW_STATUS=ok\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    assert design_publish.review_provenance(tmp_path) == ("ok", 2, True)


def test_review_provenance_prefers_explicit_keys_over_round_count_file(tmp_path: Path) -> None:
    # Explicit round-count keys win; the fallback file is not consulted when present.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=3\n",
        encoding="utf-8",
    )
    _ = (tmp_path / "review-round-count.txt").write_text("9\n", encoding="utf-8")
    assert design_publish.review_provenance(tmp_path) == ("complete", 3, True)


def test_review_provenance_round_count_fallback_absent_file_stays_zero(tmp_path: Path) -> None:
    # No round-count keys and no fallback file: rounds stays 0 (no behavior change).
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=panel-failed\n",
        encoding="utf-8",
    )
    assert design_publish.review_provenance(tmp_path) == ("panel-failed", 0, True)


def test_publish_main_delegates_to_core_usage_rc() -> None:
    assert design_publish.publish_main([]) == design_publish.publish_core([]) == 5


def test_publish_refuses_oversize_without_override(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "plan.txt").write_text("body\ndiff_lines: 1\n", encoding="utf-8")
    (design / "composed-plan.md").write_text("body\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    (design / ".step3-review-result.env").write_text("STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_size = os.environ.get("FAKE_CLI_SIZE_TRIGGER_FIRED")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = "true"
    try:
        rc = design_publish.publish_core(["--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"])
    finally:
        if old_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_size is None:
            os.environ.pop("FAKE_CLI_SIZE_TRIGGER_FIRED", None)
        else:
            os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = old_size
    out = capsys.readouterr().out
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert rc == 4
    assert "PUBLISH_REFUSE_REASON=oversize-no-override" in out
    assert "PUBLISH_REFUSE_REASON=oversize-no-override" in result_env


def test_publish_refuses_size_check_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "plan.txt").write_text("body\ndiff_lines: 1\n", encoding="utf-8")
    (design / "composed-plan.md").write_text("body\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_fail = os.environ.get("FAKE_CLI_CHECK_SIZE_FAIL")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_CHECK_SIZE_FAIL"] = "1"
    try:
        rc = design_publish.publish_core(["--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"])
    finally:
        if old_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_fail is None:
            os.environ.pop("FAKE_CLI_CHECK_SIZE_FAIL", None)
        else:
            os.environ["FAKE_CLI_CHECK_SIZE_FAIL"] = old_fail
    out = capsys.readouterr().out
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert rc == 4
    assert "PUBLISH_REFUSE_REASON=size-check-failed" in out
    assert "PUBLISH_REFUSE_REASON=size-check-failed" in result_env


@pytest.mark.parametrize("size_trigger_fired", ["__omit__", "maybe"])
def test_publish_refuses_size_check_without_valid_trigger_fails_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    size_trigger_fired: str,
) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "plan.txt").write_text("body\ndiff_lines: 1\n", encoding="utf-8")
    (design / "composed-plan.md").write_text("body\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    (design / ".step3-review-result.env").write_text("STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_size = os.environ.get("FAKE_CLI_SIZE_TRIGGER_FIRED")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = size_trigger_fired
    try:
        rc = design_publish.publish_core(["--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"])
    finally:
        if old_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_size is None:
            os.environ.pop("FAKE_CLI_SIZE_TRIGGER_FIRED", None)
        else:
            os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = old_size
    out = capsys.readouterr().out
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert rc == 4
    assert "PUBLISH_REFUSE_REASON=size-check-failed" in out
    assert "PUBLISH_REFUSE_REASON=size-check-failed" in result_env


def test_publish_refuses_review_provenance_records_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "plan.txt").write_text("body\ndiff_lines: 1\n", encoding="utf-8")
    (design / "composed-plan.md").write_text("body\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    (design / ".step3-review-result.env").write_text("STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_size = os.environ.get("FAKE_CLI_SIZE_TRIGGER_FIRED")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = "false"
    try:
        rc = design_publish.publish_core(["--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"])
    finally:
        if old_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_size is None:
            os.environ.pop("FAKE_CLI_SIZE_TRIGGER_FIRED", None)
        else:
            os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = old_size
    out = capsys.readouterr().out
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert rc == 4
    assert "review provenance indicates complete without .completed/step-3" in out
    assert "PUBLISH_REFUSE_REASON=review-provenance:complete without .completed/step-3" in result_env


def test_splice_plan_provenance_preserves_oversize_override() -> None:
    text = "body\noversize_override: operator\ndiff_lines: 1\n"

    spliced = design_publish._splice_plan_provenance(  # pyright: ignore[reportPrivateUsage]
        text=text,
        review_status="complete",
        rounds_completed=2,
    )

    assert "review_status: complete\nrounds_completed: 2\noversize_override: operator\ndiff_lines: 1\n" in spliced


def test_publish_refreshes_composed_plan_before_size_guard(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "plan.txt").write_text(
        "## Plan\n\nBody.\n\n## Testing strategy\n\nRun tests.\n\ndifficulty: MODERATE\ndiff_lines: 12\n",
        encoding="utf-8",
    )
    (design / "composed-plan.md").write_text("# stale\n", encoding="utf-8")
    assert design_step5c.plan_quality.set_oversize_override_main(["--design-tmpdir", str(design)]) == 0
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_size = os.environ.get("FAKE_CLI_SIZE_TRIGGER_FIRED")
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = "false"
    try:
        rc = design_publish.publish_core(["--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"])
    finally:
        if old_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_size is None:
            os.environ.pop("FAKE_CLI_SIZE_TRIGGER_FIRED", None)
        else:
            os.environ["FAKE_CLI_SIZE_TRIGGER_FIRED"] = old_size
    _ = capsys.readouterr()
    assert rc == 0
    assert "oversize_override: operator" in (design / "composed-plan.md").read_text(encoding="utf-8")


def test_publish_result_env_write_failure_returns_3_with_stdout_rows(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    (design / ".design-publish-result.env").mkdir()
    old_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    old_fail = os.environ.get("FAKE_CLI_NAMED_BLOCK_FAIL")
    events: list[str] = []
    os.environ["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    os.environ["FAKE_CLI_NAMED_BLOCK_FAIL"] = "1"
    def fake_proc_run(cmd: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if len(cmd) >= 4 and cmd[2:4] == ["design", "log-publish"]:
            assert not events
            events.append("log_publish")
            return subprocess.CompletedProcess(cmd, 0, stdout="PUBLISH_OK=true\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    def fake_write_result_env(**_kwargs: object) -> bool:
        assert events == ["log_publish"]
        events.append("write_result_env")
        return False

    monkeypatch.setattr(design_publish.proc, "run", fake_proc_run)
    monkeypatch.setattr(design_publish, "_write_result_env", fake_write_result_env)
    try:
        rc = design_publish.publish_core(
            [
                "--design-tmpdir",
                str(design),
                "--issue",
                "9",
                "--session-id",
                "RUN1",
                "--claude-pid",
                "11",
            ]
        )
    finally:
        if old_root is None:
            _ = os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = old_root
        if old_fail is None:
            _ = os.environ.pop("FAKE_CLI_NAMED_BLOCK_FAIL", None)
        else:
            os.environ["FAKE_CLI_NAMED_BLOCK_FAIL"] = old_fail
    out = capsys.readouterr().out
    assert rc == 3
    assert "PLAN_WRITE_OK=false" in out
    assert "VALIDATE_STATUS=ok" in out
    assert events == ["log_publish", "write_result_env"]


def test_publish_validator_defects_keep_rc4_when_result_env_write_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / ".design-publish-result.env").mkdir()
    rc = design_publish.publish_core(
        [
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 4
    assert "VALIDATE_STATUS=defects-found" in out


def _run_publish_capture_case(tmp_path: Path, env_overrides: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    (design / "source-env.sh").write_text("SESSION_ID=RUN1\n", encoding="utf-8")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    call_log = tmp_path / "calls.jsonl"
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            "FAKE_CLI_CALL_LOG": str(call_log),
            "FAKE_CLI_TRANSCRIPT_PATH": str(transcript),
            "FAKE_CLI_SESSION_DIR": str(session_dir),
        }
    )
    env.update(env_overrides)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return result, design, call_log


def _call_args(call_log: Path) -> list[list[str]]:
    return [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines()]


def test_publish_delegates_to_log_publish_without_inline_capture(tmp_path: Path) -> None:
    result, design, call_log = _run_publish_capture_case(tmp_path, {})

    assert result.returncode == 0, result.stderr
    assert not (design / "session-transcript.jsonl").exists()
    calls = _call_args(call_log)
    log_publish_calls = [args for args in calls if args[:2] == ["design", "log-publish"]]
    assert log_publish_calls
    assert log_publish_calls[0][log_publish_calls[0].index("--outcome") + 1] == "approved"
    assert all(args[:2] != ["run-log", "capture-transcript"] for args in calls)
    assert all(args[:2] != ["token", "claude-source"] for args in calls)


def test_publish_capture_does_not_read_session_env(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    (design / ".completed" / "step-5b.5").write_text("", encoding="utf-8")
    (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    (design / "source-env.sh").write_text("SESSION_ID=RUN1\n", encoding="utf-8")
    (design / "session-env.sh").mkdir()
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "publish", "--design-tmpdir", str(design), "--issue", "9", "--session-id", "RUN1", "--claude-pid", "11"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root), "FAKE_CLI_TRANSCRIPT_PATH": str(tmp_path / "t.jsonl"), "FAKE_CLI_SESSION_DIR": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr


def _capture_case(
    tmp_path: Path,
    env_overrides: dict[str, str],
    *,
    warning_step_label: str = "5c",
) -> tuple[bool, Path, Path]:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    design.mkdir(parents=True)
    (design / "source-env.sh").write_text("SESSION_ID=RUN1\n", encoding="utf-8")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    call_log = tmp_path / "calls.jsonl"
    old_env = os.environ.copy()
    os.environ.update(
        {
            "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            "FAKE_CLI_CALL_LOG": str(call_log),
            "FAKE_CLI_TRANSCRIPT_PATH": str(transcript),
            "FAKE_CLI_SESSION_DIR": str(session_dir),
        }
    )
    os.environ.update(env_overrides)
    try:
        ok = design_publish._capture_design_transcript(
            ctx=design_publish._TranscriptCaptureContext(
                design_tmpdir=design,
                plugin_root=plugin_root,
                session_id="RUN1",
                issue="9",
                repo="",
                claude_pid="11",
                warning_step_label=warning_step_label,
            )
        )
    finally:
        os.environ.clear()
        os.environ.update(old_env)
    return ok, design, call_log


def test_capture_design_transcript_persists_source_and_hoists(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ok, design, call_log = _capture_case(tmp_path, {})

    assert ok
    assert (design / "session-transcript.jsonl").is_file()
    assert "LARCH_CLAUDE_SOURCE_FILE=" in (design / "source-env.sh").read_text(encoding="utf-8")
    calls = _call_args(call_log)
    capture_args = next(args for args in calls if args[:2] == ["run-log", "capture-transcript"])
    assert capture_args[capture_args.index("--source-file") + 1] == str(design / "claude-source.env")
    assert capture_args[capture_args.index("--warning-step-label") + 1] == "5c"
    assert "SESSION_TRANSCRIPT_STATUS=captured" in capsys.readouterr().out


def test_capture_design_transcript_accepts_distinct_claude_session_uuid(tmp_path: Path) -> None:
    ok, design, call_log = _capture_case(tmp_path, {"FAKE_CLI_SESSION_UUID": "claude-session-uuid"})

    assert ok
    assert (design / "session-transcript.jsonl").is_file()
    assert any(args[:2] == ["run-log", "capture-transcript"] for args in _call_args(call_log))
    warning_log = design / "execution-issues.md"
    if warning_log.exists():
        assert "snapshot-skipped" not in warning_log.read_text(encoding="utf-8")


def test_cached_claude_source_snapshot_reuse_does_not_require_session_dir(tmp_path: Path) -> None:
    transcript = tmp_path / "claude-session.jsonl"
    transcript.write_text('{"type":"user"}\n', encoding="utf-8")
    snapshot = tmp_path / "claude-source.env"
    snapshot.write_text(
        f"TRANSCRIPT_PATH={transcript}\nSESSION_DIR={tmp_path / 'nonexistent-session-dir'}\nSESSION_UUID=claude-session\n",
        encoding="utf-8",
    )

    assert design_publish._reuse_cached_claude_source_snapshot(snapshot=snapshot) == snapshot  # pyright: ignore[reportPrivateUsage]


def test_capture_removes_stale_root_transcript_before_capture(tmp_path: Path) -> None:
    ok, design, _ = _capture_case(tmp_path, {})

    assert ok
    assert (design / "session-transcript.jsonl").read_text(encoding="utf-8") == '{"v":3}\n'


def test_capture_aborts_when_stale_root_removal_fails(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    design.mkdir()
    (design / "source-env.sh").write_text("SESSION_ID=RUN1\n", encoding="utf-8")
    (design / "session-transcript.jsonl").mkdir()

    ok = design_publish._capture_design_transcript(
        ctx=design_publish._TranscriptCaptureContext(
            design_tmpdir=design,
            plugin_root=plugin_root,
            session_id="RUN1",
            issue="9",
            repo="",
            claude_pid="11",
            warning_step_label="pause",
        )
    )

    assert not ok
    warning_log = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step pause session-transcript stale-root-removal-failed" in warning_log
    assert "design Step 5c session-transcript stale-root-removal-failed" not in warning_log


def test_capture_session_id_drift_uses_warning_label(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    design.mkdir()
    (design / "source-env.sh").write_text("SESSION_ID=OLD-RUN\n", encoding="utf-8")

    ok = design_publish._capture_design_transcript(
        ctx=design_publish._TranscriptCaptureContext(
            design_tmpdir=design,
            plugin_root=plugin_root,
            session_id="RUN1",
            issue="9",
            repo="",
            claude_pid="11",
            warning_step_label="pause",
        )
    )

    assert ok
    warning_log = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step pause session-transcript session-id-drift" in warning_log
    assert "design Step 5c session-transcript session-id-drift" not in warning_log


def test_capture_snapshot_failure_or_capture_skip_keeps_root_absent(tmp_path: Path) -> None:
    fail_ok, fail_design, fail_log = _capture_case(
        tmp_path / "fail",
        {"FAKE_CLI_TOKEN_SOURCE_FAIL": "1"},
        warning_step_label="pause",
    )
    assert fail_ok
    assert not (fail_design / "session-transcript.jsonl").exists()
    assert all(args[:2] != ["run-log", "capture-transcript"] for args in _call_args(fail_log))
    warning_log = (fail_design / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step pause session-transcript snapshot-skipped" in warning_log
    assert "design Step 5c session-transcript snapshot-skipped" not in warning_log

    skip_ok, skip_design, skip_log = _capture_case(tmp_path / "skip", {"FAKE_CLI_CAPTURE_SKIP": "1"})
    assert skip_ok
    assert not (skip_design / "session-transcript.jsonl").exists()
    assert any(args[:2] == ["run-log", "capture-transcript"] for args in _call_args(skip_log))


def test_capture_aborts_when_capture_succeeds_but_hoist_fails(tmp_path: Path) -> None:
    ok, design, call_log = _capture_case(tmp_path, {"FAKE_CLI_CAPTURE_NO_FILE": "1"})

    assert not ok
    assert not (design / "session-transcript.jsonl").exists()
    assert any(args[:2] == ["run-log", "capture-transcript"] for args in _call_args(call_log))

    warning_log = (design / "execution-issues.md").read_text(encoding="utf-8")
    assert "design Step 5c session-transcript hoist-failed" in warning_log
