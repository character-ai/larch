#!/usr/bin/env bash
# Offline structural harness for /rejected-analysis.
# shellcheck disable=SC2016  # single-quoted backtick patterns are intentional literals
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SKILL="$ROOT/skills/rejected-analysis/SKILL.md"
WRAPPER="$ROOT/skills/rejected-analysis/scripts/rejected-analysis.sh"
CLI="$ROOT/python/larch/cli.py"
PYTHON_CORE="$ROOT/python/larch/issue/rejected_analysis.py"
RUST_CORE="$ROOT/crates/larch-core/src/rejected_analysis.rs"

PASS=0
FAIL=0

contains_file() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file"; then
        PASS=$((PASS + 1))
        printf '  ok: %s\n' "$label"
    else
        FAIL=$((FAIL + 1))
        printf '  FAIL: %s (missing %s)\n' "$label" "$needle" >&2
    fi
}

not_contains_file() {
    local file="$1" needle="$2" label="$3"
    if grep -Fq -- "$needle" "$file"; then
        FAIL=$((FAIL + 1))
        printf '  FAIL: %s (unexpected %s)\n' "$label" "$needle" >&2
    else
        PASS=$((PASS + 1))
        printf '  ok: %s\n' "$label"
    fi
}

printf '== skill contract ==\n'
contains_file "$SKILL" 'argument-hint: "--n DAYS"' 'frontmatter exposes --n DAYS'
contains_file "$SKILL" 'Accept exactly two tokens: `--n` and a positive integer day count.' 'skill accepts no extra public flags'
contains_file "$SKILL" 'After **every** `${CLAUDE_PLUGIN_ROOT}/skills/rejected-analysis/scripts/rejected-analysis.sh` fence, parse whole-line `KEY=value` rows from stdout before any later Bash, Agent, or Skill step.' 'wrapper KV parsing mandated after every fence'
contains_file "$SKILL" '`WORK_DIR`' 'WORK_DIR binding listed'
contains_file "$SKILL" '`VERDICTS_FILE`' 'VERDICTS_FILE binding listed'
contains_file "$SKILL" '`INGEST_STATUS_FILE`' 'INGEST_STATUS_FILE binding listed'
contains_file "$SKILL" '`ISSUE_SENTINEL`' 'ISSUE_SENTINEL binding listed'
contains_file "$SKILL" '`ISSUE_BATCH_FILE`' 'ISSUE_BATCH_FILE binding listed'
contains_file "$SKILL" '`ISSUE_CLUSTER_MAP_FILE`' 'ISSUE_CLUSTER_MAP_FILE binding listed'
contains_file "$SKILL" '`ledger-pending.tsv` rows merge into repository-scoped analyzer state.' 'VERIFY_COUNT=0 still finalizes and records'
contains_file "$SKILL" '`finalize` re-runs the security-sensitive classifier before issue rendering.' 'security refilter documented'
contains_file "$SKILL" 'Never file `scope=oos`, `scope=out_of_scope`, or `OOS_*` deferred findings.' 'OOS deferred skip documented'
contains_file "$SKILL" 'rm -f "<parsed ISSUE_SENTINEL>"' 'sentinel cleared before issue'
contains_file "$SKILL" '/issue --input-file "<parsed ISSUE_BATCH_FILE>" --sentinel-file "<parsed ISSUE_SENTINEL>"' 'issue invoked through Skill text'
contains_file "$SKILL" 'Capture exact `/issue` stdout immediately after the Skill returns.' 'issue stdout captured durably'
contains_file "$SKILL" 'Do **not** pass `--sandbox` or other unsupported launcher flags.' 'unsupported sandbox flag forbidden'
contains_file "$SKILL" 'When `LAUNCHER_EXIT=0`, read `${OUTPUT}.dirty-tree`.' 'dirty-tree sidecar read'
contains_file "$SKILL" 'Never prompt-side `json.loads` launcher output files. Use `ingest-verdict`.' 'prompt-side JSON parse forbidden'
contains_file "$SKILL" 'Every ingest call appends exactly one durable row to `ingest-status.jsonl`, including `launch-failed` and `parse-failed`.' 'durable ingest status documented'
contains_file "$SKILL" 'It never ledgers `launch-failed` as `verification-failed`.' 'launch-failed remains retryable'
contains_file "$SKILL" 'parsed `ISSUES_FAILED>0`.' 'issues failed exits non-zero'
contains_file "$SKILL" '`ISSUE_VERIFIED=false` after `/issue` ran.' 'issue verified false exits non-zero'
contains_file "$SKILL" '`LAUNCH_FAILURES>0`.' 'launch failures exits non-zero'
contains_file "$SKILL" 'The frozen `finding_hash` excludes run-local `FINDING_N`.' 'finding hash excludes ballot id'
contains_file "$SKILL" 'It never uses live filesystem existence to choose the hash path.' 'hash path does not use filesystem existence'
contains_file "$SKILL" 'Never include `/design` plan-review findings in v1.' 'design plan review excluded'

printf '== launch-review block ==\n'
contains_file "$SKILL" '--timing-task-kind rejected-analysis-verify' 'timing task kind documented'
contains_file "$SKILL" '--prompt-file "<parsed prompt path>"' 'prompt-file flag documented'
not_contains_file "$SKILL" '--implement-tmpdir' 'dirty-tree sidecar does not use implement tmpdir'

printf '== wrapper and cli ==\n'
contains_file "$WRAPPER" 'args+=(--days "$2")' 'wrapper translates --n to --days'
contains_file "$WRAPPER" 'exec "$ROOT/scripts/larch.sh" rejected-analysis prepare' 'wrapper delegates prepare to Rust'
contains_file "$WRAPPER" 'exec "$ROOT/scripts/larch.sh" rejected-analysis ingest-verdict' 'wrapper delegates ingest to Rust'
contains_file "$WRAPPER" 'exec "$ROOT/scripts/larch.sh" rejected-analysis finalize' 'wrapper delegates finalize to Rust'
contains_file "$WRAPPER" 'exec "$ROOT/scripts/larch.sh" rejected-analysis record' 'wrapper delegates record to Rust'
not_contains_file "$CLI" '("rejected-analysis", "prepare")' 'prepare removed from Python registration'
not_contains_file "$CLI" '("rejected-analysis", "ingest-verdict")' 'ingest removed from Python registration'
not_contains_file "$CLI" '("rejected-analysis", "finalize")' 'finalize removed from Python registration'
not_contains_file "$CLI" '("rejected-analysis", "record")' 'record removed from Python registration'
contains_file "$RUST_CORE" 'fn finding_hash' 'Rust core owns the frozen finding hash'
contains_file "$RUST_CORE" 'pub fn prepare_artifacts' 'Rust core owns preparation artifacts'
contains_file "$RUST_CORE" 'pub fn ingest_artifact' 'Rust core owns verdict ingestion'
contains_file "$RUST_CORE" 'pub fn finalize_artifacts' 'Rust core owns finalization artifacts'
contains_file "$RUST_CORE" 'pub fn record_plan' 'Rust core owns recording decisions'
if [ ! -e "$PYTHON_CORE" ]; then
    PASS=$((PASS + 1))
    printf '  ok: superseded Python rejected_analysis module removed\n'
else
    FAIL=$((FAIL + 1))
    printf '  FAIL: superseded Python rejected_analysis module still present\n' >&2
fi

printf '== wrapper behavior ==\n'
if "$WRAPPER" prepare --days 1 >/tmp/rejected-analysis-wrapper.out 2>/tmp/rejected-analysis-wrapper.err; then
    FAIL=$((FAIL + 1))
    printf '  FAIL: wrapper rejects public --days\n' >&2
else
    PASS=$((PASS + 1))
    printf '  ok: wrapper rejects public --days\n'
fi

if (( FAIL > 0 )); then
    printf 'FAIL: %d failed, %d passed\n' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: %d assertions\n' "$PASS"
