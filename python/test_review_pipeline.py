from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import config
import logging_util
import review_pipeline

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"
REVIEW_CORE = ROOT / "python" / "legacy_review_shell" / "review-core.sh"
PRUNE_NITS = ROOT / "skills" / "review" / "scripts" / "prune-nit-findings.sh"


def run_review(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "review", *args],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_executable(path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _write_review_core_stubs(stub_dir: Path) -> dict[str, Path]:
    stub_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "gather": stub_dir / "gather.sh",
        "dispatch": stub_dir / "dispatch.sh",
        "collect": stub_dir / "collect.sh",
        "tally": stub_dir / "tally.sh",
        "emit": stub_dir / "emit.sh",
        "check_dirty": stub_dir / "check-dirty.sh",
        "check_threshold": stub_dir / "check-threshold.sh",
        "dispatch_voters": stub_dir / "dispatch-voters.sh",
    }
    _write_executable(
        paths["gather"],
        """#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) out="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$out"
echo "DIFF_FILE=$out/diff.patch"
echo "FILE_LIST_FILE=$out/scope-files.txt"
echo "COMMIT_LOG_FILE=$out/commits.txt"
echo "COMMIT_COUNT=1"
echo "SCOPE_FILES_COUNT=1"
echo "MODE=diff"
""",
    )
    _write_executable(
        paths["dispatch"],
        """#!/usr/bin/env bash
set -euo pipefail
tmp=""
panel="simple"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --panel) panel="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$tmp"
external="$tmp/codex-specialist-correctness-output.txt"
claude="$tmp/claude-generic-output.txt"
printf 'reviewer finding\\n' > "$external"
printf 'claude finding\\n' > "$claude"
printf '0\\n' > "$claude.done"
printf 'STATUS=clean\\n' > "$external.dirty-tree"
printf 'STATUS=clean\\n' > "$claude.dirty-tree"
cat > "$tmp/panel-manifest.ndjson" <<EOF
{"slot":"correctness","tool":"codex","output":"$external","agent":"agents/reviewer-correctness.md"}
EOF
echo "EXTERNAL_OUTPUT_FILES=$external"
echo "CLAUDE_OUTPUT_FILES=$claude"
echo "PANEL_MODE=normal"
echo "PANEL_SHAPE=$panel"
echo "PANEL_PRUNED_EMPTY=false"
echo "SCOUT_STATUS=na"
echo "DYNAMIC_SLOTS=0"
echo "STATIC_SLOT_COUNT=1"
echo "SLOT_COUNT=1"
echo "PANEL_MANIFEST=$tmp/panel-manifest.ndjson"
echo "DISPATCH_OK=true"
""",
    )
    _write_executable(
        paths["collect"],
        """#!/usr/bin/env bash
set -euo pipefail
findings=""
oos=""
rtmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
rtmp="$(dirname "$findings")"
: > "$oos"
cat > "$rtmp/collector-results.env" <<'EOF'
REVIEWER_FILE=stub-output.txt
STATUS=OK
EOF
if [[ "${TEST_FINDINGS:-0}" -eq 0 ]]; then
  : > "$findings"
else
  cat > "$findings" <<'EOF'
### FINDING_1: Example
- **Reviewer**: stub
- **Severity**: important
- **Concern**: concern
- **Suggested revision**: fix it
EOF
fi
echo "FINDINGS_COUNT=${TEST_FINDINGS:-0}"
echo "OOS_COUNT=0"
echo "DIRTY_DETECTED=false"
echo "COLLECT_OK=true"
echo "COLLECTOR_OUTPUT_FILE=collector.env"
""",
    )
    _write_executable(
        paths["tally"],
        """#!/usr/bin/env bash
set -euo pipefail
tmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
accepted="${TEST_ACCEPTED:-0}"
echo "FINDING_1_ACCEPTED=$([[ "$accepted" -gt 0 ]] && echo true || echo false)" > "$tmp/review-tally.env"
if [[ "$accepted" -gt 0 ]]; then
  printf '### FINDING_1: Example\n- **Concern**: concern\n' > "$tmp/accepted-findings.md"
else
  : > "$tmp/accepted-findings.md"
fi
: > "$tmp/rejected-findings.md"
: > "$tmp/voting-tally.md"
echo "ACCEPTED_COUNT=$accepted"
echo "REJECTED_COUNT=0"
echo "EXONERATED_COUNT=0"
echo "NEUTRAL_COUNT=0"
echo "OUT_OF_SCOPE_DRIFT_COUNT=0"
""",
    )
    _write_executable(
        paths["emit"],
        """#!/usr/bin/env bash
set -euo pipefail
echo "EMIT_OK=true"
""",
    )
    _write_executable(
        paths["check_dirty"],
        """#!/usr/bin/env bash
set -euo pipefail
echo "STATUS=clean"
""",
    )
    _write_executable(
        paths["check_threshold"],
        """#!/usr/bin/env bash
set -euo pipefail
echo "THRESHOLD_OK=true"
""",
    )
    _write_executable(
        paths["dispatch_voters"],
        """#!/usr/bin/env bash
set -euo pipefail
tmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
: > "$tmp/voter-1-output.txt"
echo "VOTER_COUNT=1"
""",
    )
    return paths


def _run_review_core(
    tmp_path: Path,
    *,
    round_num: int = 1,
    findings: int = 1,
    accepted: int = 0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    outdir = tmp_path / "review-core"
    outdir.mkdir()
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "LARCH_AGGREGATOR_DISABLED": "1",
        "TEST_FINDINGS": str(findings),
        "TEST_ACCEPTED": str(accepted),
        "REVIEW_CORE_GATHER_CONTEXT_SH": str(stubs["gather"]),
        "REVIEW_CORE_DISPATCH_PANEL_SH": str(stubs["dispatch"]),
        "REVIEW_CORE_COLLECT_FINDINGS_SH": str(stubs["collect"]),
        "REVIEW_CORE_TALLY_VOTES_SH": str(stubs["tally"]),
        "REVIEW_CORE_EMIT_TALLY_SH": str(stubs["emit"]),
        "REVIEW_CORE_CHECK_DIRTY_TREE_SH": str(stubs["check_dirty"]),
        "REVIEW_CORE_CHECK_THRESHOLD_SH": str(stubs["check_threshold"]),
        "REVIEW_CORE_DISPATCH_VOTERS_SH": str(stubs["dispatch_voters"]),
    }
    if extra_env:
        env.update(extra_env)
    return run_review(
        "core",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--round-num",
        str(round_num),
        env=env,
    )


def test_gather_context_help_routes_through_review_cli() -> None:
    result = run_review("gather-context", "--help")

    assert result.returncode == 0
    assert "Usage: gather-context.sh" in result.stderr


def test_check_reviewer_failure_threshold_zero_static_slots(tmp_path: Path) -> None:
    collector = tmp_path / "collector.tsv"
    _ = collector.write_text("", encoding="utf-8")
    result = run_review(
        "check-reviewer-failure-threshold",
        "--collector-results-file",
        str(collector),
        "--panel",
        "hard",
        "--intended-slots",
        "0",
        "--launched-slots",
        "0",
    )

    assert result.returncode == 0, result.stderr
    assert "THRESHOLD_OK=true" in result.stdout


def test_dispatch_panel_python_surface_does_not_import_agents_waterfall() -> None:
    text = (ROOT / "python" / "review_pipeline.py").read_text(encoding="utf-8")
    assert "agents.run_waterfall" not in text


def test_review_core_default_prune_nits_sh_points_at_skills_script() -> None:
    text = REVIEW_CORE.read_text(encoding="utf-8")
    match = re.search(
        r'PRUNE_NITS_SH="\$\{REVIEW_CORE_PRUNE_NITS_SH:-([^}]+)\}"',
        text,
    )
    assert match is not None
    default = match.group(1)
    assert "skills/review/scripts/prune-nit-findings.sh" in default
    assert PRUNE_NITS.is_file()


def test_review_core_prune_nit_subprocess_succeeds(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    collect = stubs["collect"]
    _write_executable(
        collect,
        """#!/usr/bin/env bash
set -euo pipefail
findings=""
oos=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
rtmp="$(dirname "$findings")"
: > "$oos"
cat > "$rtmp/collector-results.env" <<'EOF'
REVIEWER_FILE=stub-output.txt
STATUS=OK
EOF
cat > "$findings" <<'EOF'
### FINDING_1: Important finding
- **Reviewer(s)**: stub
- **Severity**: important
- **Concern**: real issue
- **Suggested revision**: fix it

### FINDING_2: Nit finding
- **Reviewer(s)**: stub
- **Severity**: nit
- **Concern**: style nit
- **Suggested revision**: trim whitespace
EOF
echo "FINDINGS_COUNT=2"
echo "OOS_COUNT=0"
echo "DIRTY_DETECTED=false"
echo "COLLECT_OK=true"
echo "COLLECTOR_OUTPUT_FILE=collector.env"
""",
    )
    outdir = tmp_path / "review-core-prune"
    outdir.mkdir()
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "LARCH_AGGREGATOR_DISABLED": "1",
        "TEST_ACCEPTED": "0",
        "REVIEW_CORE_GATHER_CONTEXT_SH": str(stubs["gather"]),
        "REVIEW_CORE_DISPATCH_PANEL_SH": str(stubs["dispatch"]),
        "REVIEW_CORE_COLLECT_FINDINGS_SH": str(collect),
        "REVIEW_CORE_TALLY_VOTES_SH": str(stubs["tally"]),
        "REVIEW_CORE_EMIT_TALLY_SH": str(stubs["emit"]),
        "REVIEW_CORE_CHECK_DIRTY_TREE_SH": str(stubs["check_dirty"]),
        "REVIEW_CORE_CHECK_THRESHOLD_SH": str(stubs["check_threshold"]),
        "REVIEW_CORE_DISPATCH_VOTERS_SH": str(stubs["dispatch_voters"]),
    }
    result = run_review(
        "core",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--round-num",
        "1",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    prune_env = outdir / "prune-nit.env"
    assert prune_env.is_file(), result.stdout
    prune_text = prune_env.read_text(encoding="utf-8")
    assert "STATUS=" in prune_text
    assert "PRUNED_COUNT=" in prune_text


def test_review_core_cap_reached_round_5_with_accepted_findings(tmp_path: Path) -> None:
    result = _run_review_core(tmp_path, round_num=5, findings=1, accepted=1)

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=cap-reached" in result.stdout


def test_run_legacy_relays_stdout_kv_without_quiet_disable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "emit-kv.sh"
    _write_executable(script, """#!/usr/bin/env bash
printf 'PIPELINE_KV=relayed\\n'
""")
    logging_util.reset_quiet_state()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setattr(
        review_pipeline,
        "_LEGACY_DIR",
        tmp_path,
        raising=False,
    )
    script_in_legacy = tmp_path / "emit-kv.sh"
    captured: list[str] = []

    def fake_emit(line: str) -> None:
        captured.append(line)

    monkeypatch.setattr(review_pipeline.logging_util, "emit", fake_emit)
    rc = review_pipeline.run_legacy("emit-kv.sh", [])

    assert rc == 0
    assert captured == ["PIPELINE_KV=relayed"]


def test_dispatch_panel_pre_scouted_valid_dynamic_slots(tmp_path: Path) -> None:
    case_dir = tmp_path / "pre-scouted-valid"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    manifest = tmp_path / "pre-scouted-valid.json"
    _ = manifest.write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "api-contract",
                        "focus_area": "correctness",
                        "weight": 4,
                        "rationale": "API changes are central.",
                        "prompt_body": "Check API contract compatibility.",
                    },
                    {
                        "name": "api-contract",
                        "focus_area": "risk-integration",
                        "weight": 3,
                        "rationale": "Duplicate must be normalized out.",
                        "prompt_body": "Duplicate should not survive.",
                    },
                    {
                        "name": "cli-flow",
                        "focus_area": "risk-integration",
                        "weight": 3,
                        "rationale": "CLI behavior changed.",
                        "prompt_body": "Check command flow and user-visible behavior.",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    scout_must_not_run = tmp_path / "scout-must-not-run.sh"
    _write_executable(
        scout_must_not_run,
        """#!/usr/bin/env bash
echo "scout must not run" >&2
exit 99
""",
    )
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_executable(
        stub_bin / "codex",
        """#!/usr/bin/env bash
out=""
for arg in "$@"; do [[ "${last:-}" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
printf 'codex review\\n' > "$out"
""",
    )
    _write_executable(
        stub_bin / "cursor",
        """#!/usr/bin/env bash
printf '{"result":"cursor review","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n'
""",
    )
    _write_executable(
        stub_bin / "claude",
        """#!/usr/bin/env bash
cat >/dev/null
printf '{"type":"result","subtype":"success","is_error":false,"result":"claude review","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}\\n'
""",
    )
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "SCOUT_DYNAMIC_ARCHETYPES_SH": str(scout_must_not_run),
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
    }
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "hard",
        "--plan-file",
        str(case_dir / "plan.md"),
        "--dynamic-archetypes",
        "2",
        "--pre-scouted-manifest",
        str(manifest),
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=pre-scouted" in result.stdout
    assert "DYNAMIC_SLOTS=4" in result.stdout
    assert "SLOT_COUNT=10" in result.stdout
