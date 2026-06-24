"""Shared helpers for review CLI pytest harnesses."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"
GIT = shutil.which("git") or "git"


def run_review(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    quiet_disable: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    for key in ("IMPLEMENT_TMPDIR", "SESSION_ENV_PATH"):
        _ = merged.pop(key, None)
    if quiet_disable:
        merged["LARCH_QUIET_DISABLE"] = "1"
    else:
        _ = merged.pop("LARCH_QUIET_DISABLE", None)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "review", *args],
        cwd=cwd or ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def kv_get(*, stdout: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def write_executable(*, path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def write_review_core_stubs(stub_dir: Path) -> dict[str, Path]:
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
        "aggregate_exhausted": stub_dir / "aggregate-exhausted-stub.sh",
        "aggregate_zero": stub_dir / "aggregate-zero-success-stub.sh",
    }
    write_executable(
        path=paths["gather"],
        body="""#!/usr/bin/env bash
set -euo pipefail
mode=""
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) mode="$2"; shift 2 ;;
    --output-dir) out="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$out"
printf 'DIFF_FILE=%s/diff.patch\\n' "$out"
printf 'FILE_LIST_FILE=%s/scope-files.txt\\n' "$out"
printf 'COMMIT_LOG_FILE=%s/commits.txt\\n' "$out"
printf 'COMMIT_COUNT=1\\n'
printf 'SCOPE_FILES_COUNT=%s\\n' "${TEST_SCOPE_COUNT:-1}"
printf 'MODE=%s\\n' "$mode"
""",
    )
    write_executable(
        path=paths["dispatch"],
        body="""#!/usr/bin/env bash
set -euo pipefail
if [[ "${TEST_DISPATCH_FAIL:-false}" == "true" ]]; then
  exit 3
fi
tmp=""
panel="hard"
round_num="1"
prune_ledger=""
pre_scouted=""
site=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --panel) panel="$2"; shift 2 ;;
    --round-num) round_num="$2"; shift 2 ;;
    --prune-ledger) prune_ledger="$2"; shift 2 ;;
    --pre-scouted-manifest) pre_scouted="$2"; shift 2 ;;
    --site) site="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$tmp"
external="$tmp/codex-specialist-correctness-output.txt"
claude="$tmp/claude-generic-output.txt"
printf 'reviewer finding\\n' > "$external"
printf 'claude finding\\n' > "$claude"
printf '0\\n' > "$claude.done"
external_outputs="$external"
if [[ "${TEST_EXTERNAL_STATIC_OUTPUTS:-false}" == "true" ]]; then
  external_outputs=""
  for slot in correctness edge-cases testing; do
    file="$tmp/codex-specialist-${slot}-output.txt"
    printf 'external static %s\\n' "$slot" > "$file"
    printf 'STATUS=clean\\n' > "$file.dirty-tree"
    external_outputs="${external_outputs}${external_outputs:+ }$file"
  done
fi
if [[ "${TEST_CLAUDE_STATIC_OUTPUTS:-false}" == "true" ]]; then
  claude_outputs=""
  for slot in correctness edge-cases testing; do
    file="$tmp/cursor-specialist-${slot}-output-phase3.txt"
    printf 'claude static %s\\n' "$slot" > "$file"
    printf '0\\n' > "$file.done"
    claude_outputs="${claude_outputs}${claude_outputs:+ }$file"
  done
else
  claude_outputs="$claude"
fi
printf 'STATUS=clean\\n' > "$external.dirty-tree"
printf 'STATUS=clean\\n' > "$claude.dirty-tree"
if [[ "${TEST_PANEL_PRUNED_EMPTY:-false}" == "true" ]]; then
  : > "$tmp/panel-manifest.ndjson"
  printf 'EXTERNAL_OUTPUT_FILES=\\nCLAUDE_OUTPUT_FILES=\\nPANEL_MODE=normal\\nPANEL_SHAPE=%s\\n' "$panel"
  printf 'PANEL_PRUNED_EMPTY=true\\nPRUNE_STATUS=pruned-empty\\nSTATIC_SLOT_COUNT=0\\nSLOT_COUNT=0\\nDYNAMIC_SLOTS=0\\n'
  [[ -n "${TEST_PRUNED_COMBOS:-}" ]] && printf 'PRUNED_COMBOS=%s\\n' "$TEST_PRUNED_COMBOS"
  printf 'PANEL_MANIFEST=%s/panel-manifest.ndjson\\nDISPATCH_OK=true\\n' "$tmp"
  exit 0
fi
printf 'EXTERNAL_OUTPUT_FILES=%s\\n' "$external_outputs"
printf 'CLAUDE_OUTPUT_FILES=%s\\n' "$claude_outputs"
printf 'PANEL_MODE=%s\\n' "${TEST_PANEL_MODE:-normal}"
printf 'PANEL_SHAPE=%s\\n' "$panel"
printf 'SCOUT_STATUS=%s\\n' "${TEST_SCOUT_STATUS:-na}"
[[ -n "${TEST_SCOUT_FAIL_REASON:-}" ]] && printf 'SCOUT_FAIL_REASON=%s\\n' "$TEST_SCOUT_FAIL_REASON"
printf 'DYNAMIC_SLOTS=%s\\n' "${TEST_DYNAMIC_SLOTS:-0}"
printf 'STATIC_SLOT_COUNT=%s\\n' "${TEST_STATIC_SLOT_COUNT:-1}"
printf 'SLOT_COUNT=%s\\n' "$(( ${TEST_STATIC_SLOT_COUNT:-1} + ${TEST_DYNAMIC_SLOTS:-0} ))"
[[ -n "${TEST_PRUNED_COMBOS:-}" ]] && printf 'PRUNED_COMBOS=%s\\n' "$TEST_PRUNED_COMBOS"
printf 'PANEL_MANIFEST=%s/panel-manifest.ndjson\\nDISPATCH_OK=true\\n' "$tmp"
if [[ "${TEST_FULL_STATIC_MANIFEST:-false}" == "true" ]]; then
  : > "$tmp/panel-manifest.ndjson"
  for slot in correctness edge-cases testing; do
    printf '{"slot":"%s","tool":"codex","output":"%s/codex-specialist-%s-output.txt","agent":"agents/reviewer-%s.md"}\\n' "$slot" "$tmp" "$slot" "$slot" >> "$tmp/panel-manifest.ndjson"
  done
elif [[ "${TEST_EXTERNAL_STATIC_OUTPUTS:-false}" == "true" ]]; then
  : > "$tmp/panel-manifest.ndjson"
  for slot in correctness edge-cases testing; do
    printf '{"slot":"%s","tool":"codex","output":"%s/codex-specialist-%s-output.txt","agent":"agents/reviewer-%s.md"}\\n' "$slot" "$tmp" "$slot" "$slot" >> "$tmp/panel-manifest.ndjson"
  done
else
  cat > "$tmp/panel-manifest.ndjson" <<EOF
{"slot":"correctness","tool":"codex","output":"$external","agent":"agents/reviewer-correctness.md"}
EOF
fi
if [[ -n "${TEST_DISPATCH_ARGV_LOG:-}" ]]; then
  printf 'round=%s\\nprune_ledger=%s\\npre_scouted=%s\\nsite=%s\\n' "$round_num" "$prune_ledger" "$pre_scouted" "$site" >> "$TEST_DISPATCH_ARGV_LOG"
fi
""",
    )
    write_executable(
        path=paths["collect"],
        body="""#!/usr/bin/env bash
set -euo pipefail
findings=""
oos=""
rtmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --review-tmpdir) rtmp="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
rtmp="${rtmp:-$(dirname "$findings")}"
: > "$oos"
case "${TEST_COLLECTOR_VARIANT:-ok-all}" in
  empty-with-oos)
    : > "$rtmp/collector-results.env"
    cat > "$oos" <<'EOF'
### OOS_1: [OUT_OF_SCOPE] parseable observation
- **Reviewer(s)**: stub
- **Concern**: unrelated observation
- **Suggested revision**: follow up separately
EOF
    ;;
  external-files-only)
    cat > "$rtmp/collector-results.env" <<EOF
REVIEWER_FILE=$rtmp/codex-specialist-correctness-output.txt
STATUS=ERROR

REVIEWER_FILE=$rtmp/codex-specialist-edge-cases-output.txt
STATUS=ERROR

REVIEWER_FILE=$rtmp/codex-specialist-testing-output.txt
STATUS=ERROR

EOF
    ;;
  missing-testing)
    cat > "$rtmp/collector-results.env" <<EOF
REVIEWER_FILE=$rtmp/codex-specialist-correctness-output.txt
STATUS=OK

REVIEWER_FILE=$rtmp/codex-specialist-edge-cases-output.txt
STATUS=OK

EOF
    ;;
  *)
    if [[ "${TEST_STATIC_SLOT_COUNT:-1}" == "1" ]]; then
      cat > "$rtmp/collector-results.env" <<EOF
REVIEWER_FILE=$rtmp/codex-specialist-correctness-output.txt
STATUS=OK

EOF
    else
      cat > "$rtmp/collector-results.env" <<EOF
REVIEWER_FILE=$rtmp/codex-specialist-correctness-output.txt
STATUS=OK

REVIEWER_FILE=$rtmp/codex-specialist-edge-cases-output.txt
STATUS=OK

REVIEWER_FILE=$rtmp/codex-specialist-testing-output.txt
STATUS=OK

EOF
    fi
    ;;
esac
if [[ "${TEST_FINDINGS:-0}" -eq 0 ]]; then
  : > "$findings"
else
  cat > "$findings" <<'EOF'
### FINDING_1: Example
- **Reviewer**: stub
- **Concern**: concern
- **Suggested revision**: fix it
EOF
fi
printf 'FINDINGS_COUNT=%s\\n' "${TEST_FINDINGS:-0}"
case "${TEST_COLLECTOR_VARIANT:-ok-all}" in
  empty-with-oos) printf 'OOS_COUNT=1\\n' ;;
  *) printf 'OOS_COUNT=0\\n' ;;
esac
printf 'DIRTY_DETECTED=false\\nCOLLECT_OK=true\\nCOLLECTOR_OUTPUT_FILE=collector.env\\n'
""",
    )
    write_executable(
        path=paths["tally"],
        body="""#!/usr/bin/env bash
set -euo pipefail
tmp=""
voter_count=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do voter_count=$((voter_count + 1)); shift; done ;;
    *) shift 2 ;;
  esac
done
if [[ "${TEST_TALLY_FAIL:-false}" == "true" ]]; then
  exit 1
fi
accepted="${TEST_ACCEPTED:-0}"
rejected="${TEST_REJECTED:-0}"
status="${TEST_TALLY_STATUS:-ok}"
round_num="${TEST_ROUND_NUM:-1}"
emit_classification="${TEST_TALLY_EMIT_CLASSIFICATION:-true}"
if [[ "$voter_count" -eq 0 && -z "${TEST_TALLY_STATUS:-}" ]]; then
  status="main-agent-vote-required"
  accepted=0
  rejected=0
fi
printf 'FINDING_1_ACCEPTED=%s\\n' "$([[ "$accepted" -gt 0 ]] && printf true || printf false)" > "$tmp/review-tally.env"
if [[ "$accepted" -gt 0 ]]; then
  printf '### FINDING_1: Example\\n- **Concern**: concern\\n' > "$tmp/accepted-findings.md"
else
  : > "$tmp/accepted-findings.md"
fi
: > "$tmp/rejected-findings.md"
printf '# tally\\n' > "$tmp/voting-tally.md"
if [[ "$emit_classification" == "true" ]]; then
  printf 'finding_id\\treviewer_slots\\tvoting_result\\n' > "$tmp/findings-classification-round-${round_num}.tsv"
  if [[ "$status" == "main-agent-vote-required" && "${TEST_FINDINGS:-0}" -gt 0 ]]; then
    printf 'FINDING_1\\t%s/codex-specialist-correctness-output.txt\\trejected\\n' "$tmp" >> "$tmp/findings-classification-round-${round_num}.tsv"
  fi
fi
printf 'TALLY_STATUS=%s\\nACCEPTED_COUNT=%s\\nREJECTED_COUNT=%s\\nTALLY_FILE=%s/review-tally.env\\n' "$status" "$accepted" "$rejected" "$tmp"
printf 'ACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\\n' "$tmp" "$tmp"
printf 'VOTING_TALLY_FILE=%s/voting-tally.md\\nTALLY_OK=true\\n' "$tmp"
if [[ -n "${TEST_PARSE_FAILED_COUNT:-}" ]]; then
  printf 'PARSE_FAILED_COUNT=%s\\n' "$TEST_PARSE_FAILED_COUNT"
fi
if [[ "$emit_classification" == "true" ]]; then
  printf 'FINDINGS_CLASSIFICATION_TSV_FILE=%s/findings-classification-round-%s.tsv\\n' "$tmp" "$round_num"
fi
""",
    )
    write_executable(
        path=paths["emit"],
        body="""#!/usr/bin/env bash
set -euo pipefail
tmp=""
scout_status="na"
dynamic_slots="0"
static_slot_count="0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --scout-status) scout_status="$2"; shift 2 ;;
    --dynamic-slots) dynamic_slots="$2"; shift 2 ;;
    --static-slot-count) static_slot_count="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
if [[ "${TEST_EMIT_FAIL:-false}" == "true" ]]; then
  printf 'emit failed\\n' >&2
  exit 7
fi
printf '{"schema_version":2,"accepted_count":0,"rejected_count":0,"panel":{"scout_status":"%s","dynamic_slot_count":%s,"static_slot_count":%s,"total_slot_count":%s}}\\n' \\
  "$scout_status" "$dynamic_slots" "$static_slot_count" "$(( static_slot_count + dynamic_slots ))" > "$tmp/review-summary.json"
printf 'EMIT_OK=true\\nREVIEW_SUMMARY_FILE=%s/review-summary.json\\n' "$tmp"
""",
    )
    write_executable(
        path=paths["check_dirty"],
        body="""#!/usr/bin/env bash
set -euo pipefail
printf 'STATUS=%s\\nMODE=checkpoint\\n' "${TEST_CHECKPOINT_STATUS:-clean}"
""",
    )
    write_executable(
        path=paths["check_threshold"],
        body="""#!/usr/bin/env bash
set -euo pipefail
intended=""
launched=""
dropped=""
reviewer_files=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --intended-slots) intended="$2"; shift 2 ;;
    --launched-slots) launched="$2"; shift 2 ;;
    --dropped-slots-file) dropped="$2"; shift 2 ;;
    --reviewer-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do reviewer_files+=("$1"); shift; done ;;
    *) shift 2 ;;
  esac
done
if [[ -n "${TEST_THRESHOLD_ARGV_LOG:-}" ]]; then
  {
    printf 'intended=%s\\n' "$intended"
    printf 'launched=%s\\n' "$launched"
    printf 'dropped=%s\\n' "$dropped"
    printf 'reviewer_files=%s\\n' "${reviewer_files[*]-}"
  } >> "$TEST_THRESHOLD_ARGV_LOG"
fi
ok="${TEST_THRESHOLD_OK:-true}"
printf 'INTENDED_SLOTS=%s\\nSUCCEEDED_SLOTS=12\\nFAILED_SLOTS=0\\nCOUNTED_SLOTS=4\\n' "${intended:-12}"
printf 'DROPPED_STATIC_SLOTS=%s\\nTHRESHOLD_OK=%s\\nTHRESHOLD_REASON=\\nNOT_SUBSTANTIVE_SLOTS=%s\\n' \\
  "$([[ -n "$dropped" ]] && printf 1 || printf 0)" "$ok" "${TEST_NOT_SUBSTANTIVE_SLOTS:-0}"
""",
    )
    write_executable(
        path=paths["dispatch_voters"],
        body="""#!/usr/bin/env bash
set -euo pipefail
review_tmpdir=""
site=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) review_tmpdir="$2"; shift 2 ;;
    --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    --site) site="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$review_tmpdir"
if [[ -n "${TEST_VOTERS_ARGV_LOG:-}" ]]; then
  printf 'site=%s\\n' "$site" >> "$TEST_VOTERS_ARGV_LOG"
fi
printf 'FINDING_1: YES\\n' > "$review_tmpdir/claude-vote-output.txt"
printf 'FINDING_1: YES\\n' > "$review_tmpdir/codex-vote-output.txt"
printf 'FINDING_1: YES\\n' > "$review_tmpdir/cursor-vote-output.txt"
printf 'VOTER_1_PATH=%s/claude-vote-output.txt\\nVOTER_1_TOOL=claude\\nVOTER_1_STATUS=launched\\n' "$review_tmpdir"
printf 'VOTER_2_PATH=%s/codex-vote-output.txt\\nVOTER_2_TOOL=codex\\nVOTER_2_STATUS=launched\\n' "$review_tmpdir"
printf 'VOTER_3_PATH=%s/cursor-vote-output.txt\\nVOTER_3_TOOL=cursor\\nVOTER_3_STATUS=launched\\n' "$review_tmpdir"
printf 'DISPATCH_OK=true\\n'
""",
    )
    write_executable(
        path=paths["aggregate_exhausted"],
        body="""#!/usr/bin/env bash
printf 'AGGREGATED=false\\nINPUT_COUNT=2\\nMERGED_COUNT=0\\nREASON=validation-exhausted\\n'
""",
    )
    write_executable(
        path=paths["aggregate_zero"],
        body="""#!/usr/bin/env bash
set -euo pipefail
findings=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
: > "${findings:?}"
printf 'AGGREGATED=true\\nINPUT_COUNT=2\\nMERGED_COUNT=0\\nREASON=ok\\n'
""",
    )
    return paths


def build_review_core_env(*, _stub_dir: Path, stubs: dict[str, Path], **overrides: str) -> dict[str, str]:
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "LARCH_AGGREGATOR_DISABLED": "1",
        "TEST_STATIC_SLOT_COUNT": "1",
        "REVIEW_CORE_GATHER_CONTEXT_SH": str(stubs["gather"]),
        "REVIEW_CORE_DISPATCH_PANEL_SH": str(stubs["dispatch"]),
        "REVIEW_CORE_COLLECT_FINDINGS_SH": str(stubs["collect"]),
        "REVIEW_CORE_TALLY_VOTES_SH": str(stubs["tally"]),
        "REVIEW_CORE_EMIT_TALLY_SH": str(stubs["emit"]),
        "REVIEW_CORE_CHECK_DIRTY_TREE_SH": str(stubs["check_dirty"]),
        "REVIEW_CORE_CHECK_THRESHOLD_SH": str(stubs["check_threshold"]),
        "REVIEW_CORE_DISPATCH_VOTERS_SH": str(stubs["dispatch_voters"]),
    }
    env.update(overrides)
    return env


def run_review_core(*,
    tmp_path: Path,
    outdir_name: str,
    round_num: int = 1,
    panel: str = "simple",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    stubs = write_review_core_stubs(tmp_path / "stubs")
    outdir = tmp_path / outdir_name
    outdir.mkdir(parents=True, exist_ok=True)
    env = build_review_core_env(_stub_dir=tmp_path / "stubs", stubs=stubs)
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
        panel,
        "--round-num",
        str(round_num),
        env=env,
    )


def write_aggregate_dispatch_stub(path: Path, *, merge_kind: str = "merge", mode: str = "ok") -> None:
    exhausted_output = """Aggregator narrative: pseudo-heading plus attestation must fail validation.

### FINDING_1 not-a-valid-heading-line

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

"""
    write_executable(
        path=path,
        body=f"""#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${{2:?}}"; shift 2 ;;
    --codex-present|--cursor-present|--mode|--diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
    --require-result-pattern) shift 2 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
stub_mode="{mode}"
case "$stub_mode" in
  fail_dispatch)
    printf 'DISPATCH_OK=false\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_FILES_PATH=\\nALL_OUTPUT_TOOLS=\\n'
    ;;
  ok)
    case "{merge_kind}" in
      merge)
        cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
        ;;
      malformed)
        cat > "$out" <<'EOF'
### FINDING_1: bad
- **Concern**: missing reviewer line
- **Suggested revision**: n/a

EOF
        ;;
      validation_exhausted)
        cat > "$out" <<'EOF'
{exhausted_output.rstrip()}
EOF
        ;;
    esac
    paths_out="${{slots}}.output-files"
    printf '%s\\n' "$out" > "$paths_out"
    printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "$paths_out"
    ;;
esac
""",
    )


def write_aggregate_counting_dispatch_stub(
    path: Path,
    *,
    counter_file: Path,
    fail_attempts: int,
    fail_body: str,
    success_body: str,
) -> None:
    """Dispatch stub that emits ``fail_body`` for the first ``fail_attempts`` invocations, then
    ``success_body``. Each invocation increments ``counter_file`` so a test can assert how many
    aggregator dispatches the bounded validation-retry loop performed.
    """
    write_executable(
        path=path,
        body=f"""#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${{2:?}}"; shift 2 ;;
    --require-result-pattern) shift 2 ;;
    --codex-present|--cursor-present|--mode|--diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
counter="{counter_file}"
n=0
[[ -f "$counter" ]] && n=$(cat "$counter")
n=$((n + 1))
printf '%s' "$n" > "$counter"
if [[ "$n" -le {fail_attempts} ]]; then
  cat > "$out" <<'FAILBODY'
{fail_body}
FAILBODY
else
  cat > "$out" <<'OKBODY'
{success_body}
OKBODY
fi
paths_out="${{slots}}.output-files"
printf '%s\\n' "$out" > "$paths_out"
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "$paths_out"
""",
    )


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _ = subprocess.run([GIT, "init", "-q"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "user.email", "test@example.com"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "user.name", "Test User"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "commit.gpgsign", "false"], cwd=path, check=True)
    _ = (path / "src").mkdir(exist_ok=True)
    _ = (path / "src" / "main.py").write_text("original\n", encoding="utf-8")
    _ = subprocess.run([GIT, "add", "src/main.py"], cwd=path, check=True)
    _ = subprocess.run([GIT, "commit", "-qm", "init"], cwd=path, check=True)
    _ = (path / "src" / "main.py").write_text("changed\n", encoding="utf-8")
    _ = subprocess.run([GIT, "add", "src/main.py"], cwd=path, check=True)
    _ = subprocess.run([GIT, "commit", "-qm", "feature"], cwd=path, check=True)


def review_core_uses_agent_dispatch_voters_by_default() -> bool:
    text = (ROOT / "python" / "review_pipeline.py").read_text(encoding="utf-8")
    return (
        '["agent", "dispatch-voters", *voter_args]' in text
        and ("PLUGIN_ROOT/scripts/" + "dispatch-code-" + "voters.sh") not in text
    )
