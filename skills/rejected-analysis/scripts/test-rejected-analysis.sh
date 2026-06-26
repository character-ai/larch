#!/usr/bin/env bash
# Offline structural harness for /rejected-analysis.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SKILL="$ROOT/skills/rejected-analysis/SKILL.md"
WRAPPER="$ROOT/skills/rejected-analysis/scripts/rejected-analysis.sh"
CLI="$ROOT/python/cli.py"
CORE="$ROOT/python/rejected_analysis.py"

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
contains_file "$SKILL" 'Still run Step 6 `finalize` and Step 8 `record` so prepare-owned `ledger-pending.tsv` rows merge into the committed ledger.' 'VERIFY_COUNT=0 still finalizes and records'
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
contains_file "$WRAPPER" 'exec python3 "$CLI" rejected-analysis prepare' 'wrapper delegates prepare to cli'
contains_file "$WRAPPER" 'exec python3 "$CLI" rejected-analysis "$cmd" "$@"' 'wrapper delegates other verbs to cli'
contains_file "$CLI" '("rejected-analysis", "prepare")' 'prepare registered'
contains_file "$CLI" '("rejected-analysis", "ingest-verdict")' 'ingest registered'
contains_file "$CLI" '("rejected-analysis", "finalize")' 'finalize registered'
contains_file "$CLI" '("rejected-analysis", "record")' 'record registered'
contains_file "$CORE" 'FINDING_HASH_FIELDS = ("file_path", "concern")' 'hash fields frozen in core'
contains_file "$CORE" 'repo_root is accepted for API symmetry' 'extractor documents repo_root non-use'

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
