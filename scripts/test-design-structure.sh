#!/usr/bin/env bash
# Structural regression guard for the /design wrapper-only SKILL.md contract.
# shellcheck disable=SC2016 # Harness pins literal shell snippets.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
SCRIPT_DIR="$REPO_ROOT/skills/design/scripts"
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
FILE_OOS_MD="$REPO_ROOT/skills/design/scripts/file-design-oos.md"
RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/run-step3-review.sh"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
BRAINSTORM_MD="$REPO_ROOT/skills/design/references/brainstorm.md"
DIALEXEC_MD="$REPO_ROOT/skills/design/references/dialectic-execution.md"
DIALPROTO_MD="$REPO_ROOT/skills/design/references/dialectic-debate.md"
# shellcheck source=scripts/lib-p3119-fence-absence.sh
. "$REPO_ROOT/scripts/lib-p3119-fence-absence.sh"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

assert_design_skill_bash_fences_are_wrappers() {
  python3 - "$SKILL_MD" <<'PY'
import re
import sys
from pathlib import Path
path = Path(sys.argv[1])
lines = path.read_text().splitlines()
in_fence = False
body = []
start = 0
count = 0
for lineno, line in enumerate(lines, 1):
    if not in_fence and line.strip() == "```bash":
        in_fence = True
        body = []
        start = lineno
        continue
    if in_fence and line.strip() == "```":
        count += 1
        text = "\n".join(body).strip()
        logical = " ".join(part.strip() for part in text.split("\\\n"))
        if not re.match(r'^"\$\{CLAUDE_PLUGIN_ROOT\}/skills/design/scripts/[A-Za-z0-9._-]+\.sh"(\s+(--|<PUBLIC_ARGV_WORDS>|(--[A-Za-z0-9._-]+)(\s+(("[^"]*"|<PUBLIC_ARGV_WORDS>|[A-Za-z0-9._:-]+)))?))*\s*$', logical):
            print(f"fence starting line {start} is not a single design wrapper call:\n{text}", file=sys.stderr)
            sys.exit(1)
        if '--session-env-path' not in logical:
            print(f"fence starting line {start} missing --session-env-path:\n{text}", file=sys.stderr)
            sys.exit(1)
        if '--claude-pid' not in logical:
            print(f"fence starting line {start} missing --claude-pid:\n{text}", file=sys.stderr)
            sys.exit(1)
        if 'design-step0-' in logical or 'design-step5c.sh' in logical:
            if '"$PPID"' not in logical and '"$CLAUDE_PID"' not in logical:
                print(f"fence starting line {start} must pass --claude-pid \"$PPID\" on Step 0 / Step 5c wrappers:\n{text}", file=sys.stderr)
                sys.exit(1)
            if 'current-design-env-$PPID.sh' not in logical:
                print(f"fence starting line {start} must pass current-design-env-$PPID.sh on Step 0 / Step 5c wrappers:\n{text}", file=sys.stderr)
                sys.exit(1)
        in_fence = False
        continue
    if in_fence:
        body.append(line)
if in_fence:
    print("unclosed bash fence", file=sys.stderr)
    sys.exit(1)
if count == 0:
    print("no bash fences found", file=sys.stderr)
    sys.exit(1)
print(f"checked {count} wrapper bash fences")
PY
}

assert_no_inline_bash_tokens_in_skill_fences() {
  local tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/design-fences.XXXXXX")
  awk '
    /^```bash$/ { in_fence=1; next }
    in_fence && /^```$/ { in_fence=0; next }
    in_fence { print }
  ' "$SKILL_MD" >"$tmp"
  if grep -Eq '(^|[[:space:]])(if|then|fi|case|esac|for|while|do|done|source|export|python3|gh|jq|grep|awk|sed|cat|printf|rm|mkdir|:)([[:space:];]|$)' "$tmp"; then
    rm -f "$tmp"
    fail 'skills/design/SKILL.md bash fences must not contain inline Bash tokens'
  fi
  rm -f "$tmp"
}

assert_direct_wrappers_are_executable_and_documented() {
  local scripts script rel md
  scripts=$(awk '
    /^```bash$/ { in_fence=1; next }
    in_fence && /^```$/ { in_fence=0; next }
    in_fence {
      while (match($0, /skills\/design\/scripts\/[A-Za-z0-9._-]+\.sh/)) {
        print substr($0, RSTART, RLENGTH)
        $0 = substr($0, RSTART + RLENGTH)
      }
    }
  ' "$SKILL_MD" | sort -u)
  [ -n "$scripts" ] || fail 'no direct design wrappers found in SKILL.md fences'
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    script="$REPO_ROOT/$rel"
    md="${script%.sh}.md"
    [ -x "$script" ] || fail "direct wrapper is not executable: $rel"
    [ -f "$md" ] || fail "direct wrapper missing sibling md: ${rel%.sh}.md"
    if grep -Fq '$PPID' "$script"; then
      fail "direct wrapper must not derive root Claude PID from PPID: $rel"
    fi
    bash -n "$script" || fail "direct wrapper has invalid Bash syntax: $rel"
  done <<<"$scripts"
}

assert_no_direct_state_helper_in_skill_fences() {
  if awk '
    /^```bash$/ { in_fence=1; next }
    in_fence && /^```$/ { in_fence=0; next }
    in_fence && /design-step3-state\.sh/ { found=1 }
    END { exit found ? 0 : 1 }
  ' "$SKILL_MD"; then
    fail 'SKILL.md bash fences must not call design-step3-state.sh directly'
  fi
}

assert_wrapper_contract_pins() {
  contains "$SCRIPT_DIR/design-step0-parse.sh" 'parse-design-argv.sh' 'Step 0 parse wrapper missing parser call'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'session setup' 'Step 0 session wrapper missing session setup call'
  contains "$SCRIPT_DIR/design-step0-session.sh" '--claude-pid "$CLAUDE_PID"' 'Step 0 session wrapper must use explicit --claude-pid argument'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'degraded-tools-gate.sh" --skill design' 'Step 0 degraded wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-route.sh" '.design-route-result.env' 'Step 0 route wrapper missing route result env read'
  contains "$SCRIPT_DIR/design-step0-init.sh" '.design-init-runparams-result.env' 'Step 0 init wrapper missing init result env read'
  contains "$SCRIPT_DIR/design-step2a.sh" 'NO_SKETCHES_CLASSIFIED_SIMPLE' 'Step 2a wrapper missing SIMPLE sentinel write'
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" 'collect-agent-results.sh' 'Step 2a.3 wrapper missing collector call'
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" '--timeout 1260' 'Step 2a.3 wrapper missing collector timeout'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-postplan-emit.sh' 'Step 2b postplan wrapper missing postplan driver'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--fallback-input "$_plan_review_stdout_file"' 'Step 3 review wrapper missing stdout fallback'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '--input "$DESIGN_TMPDIR/architecture-diagram.candidate.md"' 'Step 3b sanitizer wrapper must use DESIGN_TMPDIR candidate path'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'architecture-diagram.skipped' 'Step 3b entry wrapper missing visible skipped sentinel'
  contains "$SCRIPT_DIR/design-step5c.sh" '${SKIP_VALIDATE:+--skip-validate}' 'Step 5c wrapper missing skip-validate reentry flag'
  contains "$SCRIPT_DIR/design-step5c.sh" '.design-step5c-status.env' 'Step 5c wrapper missing status sidecar write'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" '.design-step5c-status.env' 'Step 6 cleanup wrapper missing Step 5c status sidecar read'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" 'STEP5B_STATUS=' 'Step 5b prepare wrapper missing STEP5B_STATUS handoff'
  contains "$SCRIPT_DIR/design-step5b-annotate.sh" 'step-5b' 'Step 5b annotate wrapper missing step-5b sentinel write'
  contains "$SCRIPT_DIR/design-step5c.sh" '.completed/step-5b' 'Step 5c wrapper missing step-5b precondition'
  contains "$SCRIPT_DIR/design-step5c.sh" 'STEP5C_STATUS=validator-defects' 'Step 5c wrapper missing validator-defect handoff'
  contains "$SCRIPT_DIR/design-step5c.sh" 'CLEANUP_ELIGIBLE=' 'Step 5c wrapper missing cleanup eligibility sidecar field'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STEP3_REVIEW_LOOP_STATUS=' 'Step 3 review wrapper missing loop status emit'
  contains "$SCRIPT_DIR/design-step3-gate-b-bypass.sh" 'design-step3-state.sh' 'Gate B bypass wrapper missing state helper delegation'
  contains "$SCRIPT_DIR/design-step3-continuation-entry.sh" 'auto-continuation-entry' 'Step 3 continuation wrapper missing auto-continuation entry'
  contains "$SCRIPT_DIR/design-step0-abort-cleanup.sh" 'session cleanup-tmpdir' 'Step 0 abort-cleanup wrapper missing tmpdir cleanup'
  contains "$SCRIPT_DIR/design-step0-parse.sh" 'step0-parsed-' 'Step 0 parse wrapper missing parsed env persistence'
  contains "$SCRIPT_DIR/design-step0-session.sh" '.design-step0-parsed.env' 'Step 0 session wrapper missing parsed env copy'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'design-step0-parse.sh' 'Step 0 session wrapper missing inline parse call'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'design_source_env_optional' 'Step 0 degraded wrapper must rehydrate before DESIGN_TMPDIR validation'
  contains "$SCRIPT_DIR/design-step-validator-autofix.sh" '--validator-target-file' 'Validator autofix wrapper missing CLI target-file arg'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '_postplan_site' 'Step 2b postplan wrapper missing site-aware snapshot branch'
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" '_collect_paths' 'Step 2a.3 collector wrapper missing launched-slot path assembly'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'pause-requested' 'Step 3b entry wrapper missing pause-check before skip/architectural mutations'
  contains "$SCRIPT_DIR/design-step1d5.sh" 'complete' 'Step 1d.5 wrapper missing complete mode sentinel write'
  contains "$SCRIPT_DIR/design-step4b.sh" 'step-4' 'Step 4b wrapper missing step-4 sentinel write'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-4"' "$SCRIPT_DIR/design-step4.sh" \
    || fail 'Step 4 entry wrapper must not write step-4 sentinel'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" '.design-step5c-status.env' 'Step 6 prelude wrapper missing Step 5c status read before step-5d'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'CLEANUP_ELIGIBLE' 'Step 6 prelude wrapper missing cleanup eligibility gate'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'PUBLISH_OK' 'Step 6 prelude wrapper missing publish gate before step-5d'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'gh issue view' 'Step 0 route wrapper missing issue fetch'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'POSITIONAL_KIND' 'Step 0 route wrapper missing positional issue binding'
  contains "$SCRIPT_DIR/design-step0-init.sh" 'design_classification=HARD' 'Step 0 init wrapper missing HARD classification derivation'
  contains "$SCRIPT_DIR/design-step0-parse.sh" '%q' 'Step 0 parse wrapper missing shell-quoted parsed env persistence'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_RC=' 'Step 2b postplan wrapper missing POSTPLAN_RC emit'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_STATUS=' 'Step 2b postplan wrapper missing POSTPLAN_STATUS emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'SCOPE_ANCHOR_FILE=' 'Step 3 review wrapper missing scope anchor emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'TALLY_PLAN_REVIEW_STATUS=' 'Step 3 review wrapper missing tally status emit'
  contains "$SKILL_MD" 'design-step3-gate-b-bypass.sh' 'SKILL missing gate-b-bypass wrapper bash fence'
  contains "$SKILL_MD" 'design-step3-continuation-entry.sh' 'SKILL missing continuation-entry wrapper bash fence'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5b"' "$SCRIPT_DIR/design-step5c.sh" \
    || fail 'Step 5c wrapper must not synthesize step-5b sentinel'
}

assert_no_consecutive_executable_script_call_fences() {
  python3 - "$SKILL_MD" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text().splitlines()
fences = []
in_fence = False
start = 0
end = 0
for lineno, line in enumerate(lines, 1):
    if not in_fence and line.strip() == '```bash':
        in_fence = True
        start = lineno
        continue
    if in_fence and line.strip() == '```':
        end = lineno
        fences.append((start, end))
        in_fence = False
        continue

boundary_markers = (
    'AskUserQuestion',
    '/larch:issue',
    'Agent tool',
    'Task tool',
    'MANDATORY — READ ENTIRE FILE',
    '**Mechanical Gate C plan emit**',
    '**Legacy heuristic multi-round continuation check',
    '### Step 3.5',
    '**Degraded-tools gate',
    'In a separate Bash block from Step 0a',
    'and stop (run no further steps)',
    '### Final summary block',
    '2.5. **Route driver**',
    '5. **Tier resolution**',
    '4. **Already-planned branch**',
    '3. **Clarify loop**',
    'Before every Gate-B-bypass jump',
    '**If the sanitizer returns',
    'At the Step 3b completion boundary',
    '**Legacy heuristic multi-round continuation check',
    '**MANDATORY — READ ENTIRE FILE before composing rejected findings',
    '**Optional trailer guard',
    '**Invariant (anti-pattern):**',
    'On `PLAN_REVIEW_CONTINUE=true`',
    '### 0c —',
    '<!-- step:0c',
    '<!-- step:1d.5',
    '<!-- step:1d.7',
    '<!-- step:1e',
    '<!-- step:2a',
    '<!-- step:2b',
    '<!-- step:3',
    '<!-- step:3b',
    '<!-- step:4',
    '<!-- step:4b',
    '<!-- step:5',
    '<!-- step:6',
    '**Regular mode**',
    '**Quick mode**',
    'zero-sketch degraded fence',
    '**Zero-sketches guard',
    'discussion-round2',
    'site discussion-round2',
    '--site step2b',
    '--mode entry',
    '--mode repair',
    '--mode skip',
    '--mode architectural',
    '--mode complete',
    '#### Step 2b drafter',
    '#### Step 2b postplan',
    'terminal postplan fence',
    '> **🔶 /design 2a.5: dialectic**',
    '> **🔶 /design 3b: arch diagram**',
    'branch-local skip fence below',
    'architectural entry cleanup fence below',
    '--mode skip',
    '--mode architectural',
)

for (_start_a, end_a), (start_b, _end_b) in zip(fences, fences[1:]):
    between = '\n'.join(lines[end_a:start_b - 1])
    if any(marker in between for marker in boundary_markers):
        continue
    if '<!-- step:' in between:
        continue
    print(
        f"adjacent executable bash fences ending near line {end_a} and starting at line {start_b} lack a pinned real boundary",
        file=sys.stderr,
    )
    sys.exit(1)
print(f"checked {len(fences)} fences for consecutive-script-call boundaries")
PY
}

assert_degraded_tools_gate_fence() {
  contains "$SKILL_MD" 'design-step0-degraded.sh' 'SKILL missing degraded-tools wrapper fence'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'degraded-tools-gate.sh' 'Step 0 degraded wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'STEP0_STATUS=' 'Step 0 degraded wrapper missing STEP0_STATUS emit'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'needs-degraded-decision' 'Step 0 degraded wrapper missing needs-degraded-decision branch'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'BOTH_DOWN_SEEN' 'Step 0 degraded wrapper missing BOTH_DOWN parse presence tracking'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'degraded-both-down-auto' 'Step 0 degraded wrapper missing non-interactive both-down branch'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" '.degraded-tools-gate-prompted' 'Step 0 degraded wrapper missing prompted sentinel write'
  contains "$SCRIPT_DIR/design-step0-init.sh" 'feature-description.txt' 'Step 0 init wrapper missing feature-description write'
  contains "$SCRIPT_DIR/design-step0-route.sh" "printf 'ROUTE=%s" 'Step 0 route wrapper missing ROUTE stdout emit'
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" 'sketch-launched-paths.txt' 'Step 2a.3 collector missing launched-path sidecar read'
  contains "$SCRIPT_DIR/design-step2a2-record-launches.sh" 'sketch-launched-paths.txt' 'Step 2a.2 record-launches wrapper missing launched-path sidecar write'
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" 'sketch-launched-paths.txt missing' 'Step 2a.3 collector missing launched-path sidecar requirement'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'VALIDATE_STATUS=' 'Step 2b postplan wrapper missing VALIDATE_STATUS emit on rc 10'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'design-pause-save.sh' 'Step 0 route wrapper missing pause-check'
  contains "$SCRIPT_DIR/design-step0-init.sh" 'design-pause-save.sh' 'Step 0 init wrapper missing pause-check'
  contains "$SCRIPT_DIR/design-step0-route.sh" '.design-step0-route-state.env' 'Step 0 route wrapper missing route state sidecar write'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'ISSUE_TITLE=%s' 'Step 0 route wrapper missing route state ISSUE_TITLE sidecar write'
  contains "$SCRIPT_DIR/design-step0-route.sh" '--issue-number' 'Step 0 route wrapper missing verbal issue-number handoff arg'
  contains "$SCRIPT_DIR/design-step0-init.sh" '.design-step0-route-state.env' 'Step 0 init wrapper missing route state sidecar read'
  contains "$SCRIPT_DIR/design-step0-init.sh" 'read-result-env.sh' 'Step 0 init wrapper missing safe route state sidecar read'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'LARCH_SKILL_NON_INTERACTIVE' 'Step 0 degraded wrapper missing explicit non-interactive signal'
  contains "$SCRIPT_DIR/design-step3-entry-state.sh" 'design-step3-state.sh' 'Step 3 entry-state wrapper missing state helper call'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" 'STEP5B_NEEDS_ANNOTATE=true' 'Step 5b prepare wrapper missing annotate recovery handoff'
  contains "$SKILL_MD" 'STEP0_STATUS' 'SKILL missing STEP0_STATUS consume prose'
  contains "$SCRIPT_DIR/design-step3-entry.sh" '.pause-save-complete' 'Step 3 combined entry wrapper missing pause-save stop guard'
  contains "$SCRIPT_DIR/design-step3-entry.sh" 'rm -f "$DESIGN_TMPDIR/.pause-save-complete"' 'Step 3 combined entry wrapper missing stale pause-save sentinel clear'
  contains "$SCRIPT_DIR/design-step4b.sh" 'rm -f "$DESIGN_TMPDIR/.pause-save-complete"' 'Step 4b combined wrapper missing stale pause-save sentinel clear'
  contains "$SCRIPT_DIR/design-step6.sh" 'rm -f "$DESIGN_TMPDIR/.pause-save-complete"' 'Step 6 combined wrapper missing stale pause-save sentinel clear'
  contains "$SCRIPT_DIR/design-step2a-zero-sketch.sh" 'NO_SKETCHES_DEGRADED_HARD' 'Step 2a zero-sketch wrapper missing degraded synthesis sentinel'
}

assert_gate_b_bypass_branch_sentinels() {
  local start_line end_line subject
  start_line=$(grep -nF -- '**Post-loop branch matrix**' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
  end_line=$(grep -nF -- '<!-- step:3.5' "$SKILL_MD" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
  [ -n "$start_line" ] || fail 'SKILL missing post-loop branch matrix start'
  [ -n "$end_line" ] || fail 'SKILL missing Step 3.5 marker after branch matrix'
  subject=$(mktemp "${TMPDIR:-/tmp}/test-design-structure-gate-b-bypass.XXXXXX")
  sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD" >"$subject"
  grep -Fq -- 'design-step3-gate-b-bypass.sh' "$subject" || fail 'branch matrix missing gate-b-bypass wrapper'
  grep -Fq -- 'refused-partial-gate-b-bypass' "$subject" || fail 'branch matrix missing refused partial state handling'
  grep -Fq -- 'STEP3_STATE=' "$subject" || fail 'branch matrix missing STEP3_STATE parse'
  rm -f "$subject"
}

assert_wrapper_pause_before_work() {
  local wrapper label
  for entry in \
    'design-step0-route.sh:gh issue view' \
    'design-step0-init.sh:design-init-runparams.sh' \
    'design-step2a3-collect.sh:collect-agent-results.sh' \
    'design-step3-entry-state.sh:design-step3-state.sh' \
    'design-step3b-sanitize.sh:mermaid sanitize' \
    'design-step3b-entry.sh:architecture-diagram.skipped'
  do
    wrapper="${entry%%:*}"
    label="${entry#*:}"
    grep -Fq 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" \
      || fail "$wrapper missing pause-check before work"
    grep -Fq "$label" "$SCRIPT_DIR/$wrapper" \
      || fail "$wrapper missing expected work marker: $label"
    _pause_line=$(grep -m 1 -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | cut -d: -f1)
    _work_line=$(grep -m 1 -nF "$label" "$SCRIPT_DIR/$wrapper" | cut -d: -f1)
    [ -n "$_pause_line" ] && [ -n "$_work_line" ] || fail "$wrapper missing pause/work lines for ordering check"
    [ "$_pause_line" -lt "$_work_line" ] \
      || fail "$wrapper must pause-check before $label"
  done
}

assert_reference_updates() {
  contains "$PLAN_REVIEW_MD" 'Deferred main-agent adjudication' 'plan-review.md missing deferred adjudication section'
  contains "$APPROVAL_MD" 'design-step2b-postplan.sh' 'approval-gates.md missing postplan wrapper reference'
  contains "$APPROVAL_MD" 'design-step5c.sh --skip-validate' 'approval-gates.md missing Step 5c skip-validate wrapper reference'
  contains "$DISCUSSION_MD" 'design-step2b-postplan.sh --site discussion-round2' 'discussion-rounds.md missing discussion-round2 wrapper reference'
  contains "$FILE_OOS_MD" 'oos-issue.stdout.txt' 'file-design-oos.md missing issue stdout handoff contract'
}

assert_no_direct_step3b_step4_routes() {
  local label="$1" subject_file="$2" start_marker="${3:-}" end_marker="${4:-}" tmp scoped=false bad
  tmp="$subject_file"
  if [[ -n "$start_marker" || -n "$end_marker" ]]; then
    [[ -n "$start_marker" && -n "$end_marker" ]] || fail "$label route guard markers must be paired"
    local start_line end_line
    start_line=$(grep -nF -- "$start_marker" "$subject_file" | head -1 | cut -d: -f1 || true)
    end_line=$(grep -nF -- "$end_marker" "$subject_file" | awk -F: -v s="${start_line:-0}" '$1 > s {print $1; exit}' || true)
    [[ -n "$start_line" && -n "$end_line" ]] || fail "$label route guard missing marker"
    tmp=$(mktemp "${TMPDIR:-/tmp}/step3b-route.XXXXXX")
    sed -n "${start_line},$((end_line - 1))p" "$subject_file" >"$tmp"
    scoped=true
  fi
  bad=$(awk '
    {
      line = $0
      lower = tolower($0)
    }
    lower ~ /step 3b completion boundary/ { next }
    lower ~ /step 3b[[:space:]]*(->|→|⇒|, then|,|\/)[[:space:]]*step 4/ { print line; next }
    lower ~ /step 3b\/4/ { print line; next }
    lower ~ /step 3b[[:space:]]+\/[[:space:]]+step 4/ { print line; next }
    lower ~ /(continue|proceed|auto-continue|route|jump|enter|go)/ && lower ~ /step 3b/ && lower ~ /step 4/ { print line; next }
  ' "$tmp")
  [[ -z "$bad" ]] || fail "$label has direct Step 3b-to-Step 4 route without completion boundary: $bad"
  [[ "$scoped" == false ]] || rm -f "$tmp"
}

assert_postplan_thin_fence() {
  local file="$1" label="$2"
  local emit_sh="$SCRIPT_DIR/design-postplan-emit.sh"
  grep -Fq 'set +e' "$file" || fail "$label missing set +e child capture"
  grep -Fq '$?' "$file" || fail "$label missing explicit rc capture"
  grep -Fq -- '--with-plan-size' "$file" || fail "$label missing --with-plan-size"
  grep -Fq -- 'env LARCH_QUIET_DISABLE=1' "$file" || fail "$label missing LARCH_QUIET_DISABLE display capture"
  # shellcheck disable=SC2016
  grep -Fq '${_postplan_out:-}' "$file" || fail "$label missing postplan out display variable"
  # shellcheck disable=SC2016
  grep -Fq 'case "${_postplan_rc:-1}" in' "$file" || fail "$label missing postplan rc case"
  for arm in 0 10 11 12 13 2 1; do
    grep -Fq "  ${arm})" "$file" || fail "$label missing case arm ${arm}"
  done
  grep -Fq '  *)' "$file" || fail "$label missing default-abort *) arm"
  grep -Fq '${REPO:+--repo "$REPO"}' "$file" || fail "$label pause-save must thread REPO"
  grep -Fq 'design-postplan-emit.sh' "$file" || fail "$label missing postplan driver delegation"
  grep -Fq 'DRIFT_TRIGGER_FIRED' "$emit_sh" || fail 'design-postplan-emit.sh missing drift trigger parse'
  grep -Fq 'BASELINE_PLAN_LINES' "$emit_sh" || fail 'design-postplan-emit.sh missing drift baseline parse'
}

assert_publish_fence_guards() {
  contains "$SCRIPT_DIR/design-step5c.sh" 'design-publish.sh' 'Step 5c wrapper missing design-publish call'
  contains "$SCRIPT_DIR/design-step5c.sh" 'read-result-env.sh' 'Step 5c wrapper missing read-result-env handoff'
  contains "$SCRIPT_DIR/design-step5c.sh" '.design-publish-result.env.rc3-primary-missing' 'Step 5c wrapper missing rc 3 stdout fallback path'
  contains "$SCRIPT_DIR/design-step5c.sh" 'STEP5C_STATUS=validator-defects' 'Step 5c wrapper missing rc 4 validator handoff'
  contains "$SCRIPT_DIR/design-step5c.sh" 'PLAN_WRITE_OK:-}" == true' 'Step 5c wrapper missing PLAN_WRITE_OK gate'
  contains "$SCRIPT_DIR/design-step5c.sh" '.design-step5c-status.env' 'Step 5c wrapper missing status sidecar write'
  contains "$SCRIPT_DIR/design-step5c.sh" 'CLEANUP_ELIGIBLE=' 'Step 5c wrapper missing cleanup eligibility emit'
  contains "$SCRIPT_DIR/design-step5c.sh" '${SKIP_VALIDATE:+--skip-validate}' 'Step 5c wrapper missing skip-validate flag'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5b"' "$SCRIPT_DIR/design-step5c.sh" \
    || fail 'Step 5c wrapper must not synthesize step-5b sentinel'
}

assert_step6_cleanup_wrappers() {
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" 'CLEANUP_STATUS=preserved' 'Step 6 cleanup wrapper missing preserve exit status'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'STEP6_PRELUDE_STATUS=skipped' 'Step 6 prelude wrapper missing skip exit status'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" 'session cleanup-tmpdir' 'Step 6 cleanup wrapper missing cleanup call'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" '.design-step5c-status.env' 'Step 6 prelude wrapper missing Step 5c status read'
}

assert_route_integration_pins() {
  contains "$SCRIPT_DIR/design-step0-route.sh" 'cancel-pause-load' 'Step 0 route wrapper missing cancel-pause-load branch'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'cancel-title-filter' 'Step 0 route wrapper missing cancel-title-filter branch'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'resume@' 'Step 0 route wrapper missing resume routing'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'read-result-env.sh' 'Step 0 route wrapper missing KV-only route result read'
}

assert_route_state_sidecar_quoting() {
  local tmp sidecar safe
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/test-design-route-state.XXXXXX")
  sidecar="$tmp/.design-step0-route-state.env"
  safe="$tmp/safe.env"
  {
    printf 'ISSUE_TITLE=%s\n' 'title with spaces'
    printf 'ISSUE_NUMBER=%s\n' '42'
    printf 'ROUTE=%s\n' 'proceed'
  } >"$sidecar"
  "$REPO_ROOT/scripts/read-result-env.sh" \
    --input "$sidecar" \
    --allow ISSUE_TITLE \
    --allow ISSUE_NUMBER \
    --allow ROUTE \
    --output "$safe"
  # shellcheck source=/dev/null
  . "$safe"
  [[ "$ISSUE_TITLE" == 'title with spaces' && "$ISSUE_NUMBER" == '42' && "$ROUTE" == proceed ]] \
    || fail "quoted route state sidecar read mismatch (ISSUE_TITLE=${ISSUE_TITLE:-<empty>})"
  {
    printf 'ISSUE_TITLE=%s\n' '$(echo injected)'
    printf 'ROUTE=%s\n' 'proceed'
  } >"$sidecar"
  "$REPO_ROOT/scripts/read-result-env.sh" \
    --input "$sidecar" \
    --allow ISSUE_TITLE \
    --allow ROUTE \
    --output "$safe"
  # shellcheck source=/dev/null
  . "$safe"
  [[ "$ISSUE_TITLE" == '$(echo injected)' ]] || fail "route state sidecar must not execute shell metacharacters in ISSUE_TITLE"
  rm -rf "$tmp"
}

assert_behavioral_harness_pins() {
  contains "$SCRIPT_DIR/design-step0-session.sh" 'session setup' 'Step 0 session wrapper missing session setup call'
  contains "$SCRIPT_DIR/design-step5c.sh" 'PUBLISH_OK' 'Step 5c wrapper missing publish rc handoff'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'CLEANUP_ELIGIBLE:-}" == false' 'Step 6 prelude wrapper missing cleanup skip on publish failure'
  contains "$SKILL_MD" 'design-step2b-postplan.sh' 'SKILL missing Gate B postplan wrapper reference'
  contains "$REPO_ROOT/skills/design/scripts/test-step3-orchestrator-fence.sh" 'invoke_step3_review_wrapper' 'Step 3 handoff harness must exercise design-step3-review.sh'
}

assert_wrapper_fence_ordering() {
  local wrapper first_line second_line
  wrapper='design-step3-entry-state.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'design-step3-state.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before direct-review state mutation"
  wrapper='design-step2a3-collect.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'collect-agent-results.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before collect"
  wrapper='design-step2a-zero-sketch.sh'
  first_line=$(grep -nF 'NO_SKETCHES_DEGRADED_HARD' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF '.completed/step-2a' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must write degraded artifacts before step-2a sentinel"
  wrapper='design-step4b.sh'
  first_line=$(grep -nF 'design-step4b-read.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'step-4' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must write step-4 only after Gate C read"
  wrapper='design-step5c.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'design-publish.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before publish"
  wrapper='design-step6-cleanup.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'session cleanup-tmpdir' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before cleanup"
}

assert_design_skill_bash_fences_are_wrappers
assert_no_consecutive_executable_script_call_fences
assert_no_inline_bash_tokens_in_skill_fences
assert_direct_wrappers_are_executable_and_documented
assert_no_direct_state_helper_in_skill_fences
assert_degraded_tools_gate_fence
assert_gate_b_bypass_branch_sentinels
assert_wrapper_pause_before_work
assert_route_integration_pins
assert_behavioral_harness_pins
assert_route_state_sidecar_quoting
assert_wrapper_contract_pins
assert_reference_updates
assert_postplan_thin_fence "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-step2b-postplan.sh'
assert_publish_fence_guards
assert_step6_cleanup_wrappers
assert_wrapper_fence_ordering
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unless `design_classification == SIMPLE`, where the user-confirmed no-sketch carve-out applies' 'SKILL missing SIMPLE Design Mindset carve-out'
contains "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_SIMPLE' 'SKILL missing SIMPLE sketch sentinel'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'Skip sketches only when `design_classification == SIMPLE`' 'SKILL missing Anti-pattern #1 SIMPLE carve-out prose'
contains "$SKILL_MD" 'This is a SIMPLE-tier design. Bias the plan toward the **smallest change that achieves the goal**.' 'SKILL missing SIMPLE designer emphasis'
contains "$SKILL_MD" 'This is a HARD-tier design. Bias the plan toward **thoroughness**.' 'SKILL missing HARD designer emphasis'
contains "$RUN_STEP3_SH" 'review-round-count.txt' 'run-step3-review.sh missing review-round counter'
# shellcheck disable=SC2016 # Removed flag must not be forwarded to the inner loop.
_removed_round_cap_flag='--round-'"cap"
absent "$RUN_STEP3_SH" "$_removed_round_cap_flag" 'run-step3-review.sh must not mention removed round-cap flag'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
absent "$RUN_STEP3_SH" '--convergence-threshold "$CONVERGENCE_THRESHOLD"' 'run-step3-review.sh must NOT forward convergence-threshold to plan-review-loop'
absent "$SKILL_MD" '--convergence-threshold' 'SKILL.md must NOT pass convergence-threshold to run-step3-review.sh'
absent "$SKILL_MD" 'LARCH_DESIGN_CONVERGENCE_THRESHOLD' 'SKILL.md must NOT reference LARCH_DESIGN_CONVERGENCE_THRESHOLD'
# shellcheck disable=SC2016 # Removed env var must not remain in Step 3 launch fence.
_removed_design_cap_var='LARCH_DESIGN_'"ROUND_CAP"
absent "$SKILL_MD" "$_removed_design_cap_var" 'SKILL must not reference removed design round-cap env var'
TR_RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/test-run-step3-review.sh"
contains "$TR_RUN_STEP3_SH" 'driver argv matches plan-review-loop contract' \
  'test-run-step3-review.sh missing plan-review-loop integration-seam case'
_plan_forward_flags=(--design-tmpdir --plan-file --feature-file --codex-present --cursor-present --round-num)
for _pf in "${_plan_forward_flags[@]}"; do
  grep -Fq -- "$_pf" "$PLAN_LOOP_SH" \
    || fail "plan-review-loop.sh missing $_pf in argv parser"
  grep -Fq -- "$_pf" "$RUN_STEP3_SH" \
    || fail "run-step3-review.sh missing $_pf forward to plan-review-loop"
  grep -Fq -- "$_pf" "$TR_RUN_STEP3_SH" \
    || fail "test-run-step3-review.sh integration-seam stub missing $_pf (sync with plan-review-loop.sh)"
done
contains "$RUN_STEP3_SH" '.step3-plan-review-result.env' 'run-step3-review.sh must read step3 plan-review result env'
contains "$RUN_STEP3_SH" 'result env is a symlink; ignoring it and using stdout fallback only' 'run-step3-review.sh missing symlink-safe step3 result env warning'
contains "$SKILL_MD" 'invoke-plan-validator.sh' 'SKILL missing renamed validator helper'
contains "$RUN_STEP3_SH" 'session read-classification' 'run-step3-review.sh missing classification reader'
contains "$RUN_STEP3_SH" '.step3-review-cap.env' 'run-step3-review.sh missing persisted Step 3 cap state file'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_CAP_REACHED=false' 'run-step3-review.sh missing persisted cap-false state'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_ROUND_NUM=' 'run-step3-review.sh missing persisted Step 3 round number state'
contains "$SKILL_MD" 'run-step3-review.sh' 'SKILL must invoke run-step3-review.sh'
contains "$SKILL_MD" '--input "$DESIGN_TMPDIR/.step3-review-result.env"' 'SKILL must read allowlisted KVs from .step3-review-result.env via read-result-env.sh'
[[ -x "$RUN_STEP3_SH" ]] || fail 'run-step3-review.sh must be executable'
[[ -f "$RUN_STEP3_MD" ]] || fail "run-step3-review.md missing: $RUN_STEP3_MD"
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'including `LOOP_STATUS=panel-failed`' 'SKILL missing panel-failed counter-consumption contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' 'SKILL missing tally-error counter-skip contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=complete` — proceed to Gate B' 'SKILL missing complete branch matrix entry'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
absent "$SKILL_MD" '`LOOP_STATUS=emit-plan-failed`' 'SKILL should remove emit-plan-failed branch matrix entry'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" 'review-round cap (${_round_cap}) reached for ${_tier}' 'run-step3-review.sh missing Step 3 cap breadcrumb emit'
contains "$SKILL_MD" 'skip Gate B, and jump to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C with existing artifacts' 'SKILL missing boundary-qualified cap short-circuit Gate B bypass'
contains "$SKILL_MD" 'Gate B would otherwise re-surface stale accepted findings from an earlier round' 'SKILL missing stale-finding cap rationale'
contains "$SKILL_MD" 'The Step 3.5 continuation block below is bypassed on this path.' 'SKILL missing explicit Step 3.5 bypass prose'
contains "$SKILL_MD" 'the four primary options are **Approve final design** / **See full plan** / **Discuss further** / **Re-run review panel**' 'SKILL missing Gate C four-option prose'
contains "$SKILL_MD" 'Gate C MUST omit **Re-run review panel** and offer only **Approve final design** / **See full plan** / **Discuss further**' 'SKILL missing Gate C cap-omission prose with See full plan'
contains "$SKILL_MD" 'plan review MUST ALWAYS run the full Step 3 panel' 'SKILL missing full-panel Step 3 contract'
# shellcheck disable=SC2016 # Markdown literals intentionally pin unexpanded shell snippets.
contains "$SKILL_MD" 'After successful re-tally, read `$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/round-start-s`' 'SKILL missing deferred MAV round-start-s read'
# shellcheck disable=SC2016 # Markdown literals intentionally pin unexpanded shell snippets.
contains "$SKILL_MD" 'record-plan-review-round-timing.sh --design-tmpdir "$DESIGN_TMPDIR" --round "${ROUNDS_COMPLETED:-$ROUND_NUM}" --start-s "$round_start_s" --end-s "$end_s" || true' 'SKILL missing deferred MAV timing helper invocation'
# shellcheck disable=SC2016 # Markdown literal intentionally checks backticked status token.
step3_main_agent_line=$(grep -nF 'If `TALLY_PLAN_REVIEW_STATUS` is `main-agent-vote-required`' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step3_mav_order_ok=$(awk -v s="${step3_main_agent_line:-0}" '
  NR >= s && /re-run `tally-plan-review\.sh`/ && /record-plan-review-round-timing\.sh --design-tmpdir/ {
    print (index($0, "re-run `tally-plan-review.sh`") < index($0, "record-plan-review-round-timing.sh --design-tmpdir")) ? "1" : "0"
    exit
  }
' "$SKILL_MD")
[[ -n "$step3_main_agent_line" && "$step3_mav_order_ok" == "1" ]] \
  || fail 'SKILL deferred MAV timing helper must run after re-tally'

grep -Fq 'sketch_budget=0' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh must pin SIMPLE sketch_budget=0'
contains "$SKILL_MD" 'design-postplan-emit.sh' 'SKILL missing postplan driver quick validator skip owner'
absent "$SKILL_MD" 'invoke-plan-validator-if-not-quick.sh' 'SKILL must not reference old validator helper'
absent "$SKILL_MD" 'read-design-review-budget.sh' 'SKILL must not reference old budget reader'
absent "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_TRIVIAL' 'SKILL must not reference old trivial sentinel'
absent "$SKILL_MD" 'plan-review-quick.md' 'SKILL must not reference deleted quick review reference'
absent "$SKILL_MD" 'design-l3-velocity-notified-2670' 'SKILL must not retain Step 5d velocity comment sentinel'
contains "$DESIGN_INIT_SH" 'contract drift' 'design-init-runparams.sh missing Step 0b contract-drift abort prose'
contains "$DESIGN_INIT_SH" 'aborting before silent tier downgrade' 'design-init-runparams.sh missing silent tier downgrade abort pin'
contains "$DESIGN_INIT_SH" 'python -m pytest python/test_session_env.py' 'design-init-runparams.sh missing contract-drift repro command'
grep -Fq 'refusing to recreate it with fallback defaults' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh missing no-fallback run-params warning'
absent "$SKILL_MD" 'run-params write failed; router-flag recovery' 'SKILL must not retain old HARD fallback recovery reason'

contains "$FLAGS_MD" 'design-postplan-emit.sh' 'flags.md missing postplan driver validator contract'
contains "$FLAGS_MD" 'Validation is unconditional: there is no quick-skip path and no force flag.' 'flags.md missing unconditional validator contract'
contains "$APPROVAL_MD" 'Cap: 5 (both tiers).' 'approval-gates.md missing flat cap'
contains "$APPROVAL_MD" 'review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C.' 'approval-gates.md missing canonical boundary-qualified Step 3 cap breadcrumb'
contains "$APPROVAL_MD" 'auto-applying N accepted finding(s)' 'approval-gates.md missing Gate B auto-apply default breadcrumb'
contains "$APPROVAL_MD" 'Apply all / Go through each / Switch to discussion mode prompt below' 'approval-gates.md missing --per-round-approval explicit Gate B option wording'
contains "$APPROVAL_MD" 'Gate B prompts explicitly before any finding changes' 'approval-gates.md missing explicit Gate B apply boundary (--per-round-approval path)'
contains "$APPROVAL_MD" 'Step 3b → Step 3b completion boundary → Step 4 → Step 4b (Gate C) run in normal sequence' 'approval-gates.md missing zero-findings Step 3b boundary-qualified forward link'
contains "$APPROVAL_MD" 'proceed to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b); Step 4 and Gate C follow in normal sequence.' 'approval-gates.md missing shared post-apply Step 3b forward link'
contains "$APPROVAL_MD" '(default) — auto-apply.' 'approval-gates.md missing Gate B auto-apply default branch'
contains "$APPROVAL_MD" 'Re-run review panel' 'approval-gates.md missing Gate C rerun option contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 're-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`)' 'approval-gates.md missing Gate A See-full-plan re-prompt contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.' 'approval-gates.md missing Gate A missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Any Gate C re-prompt after `Other` must preserve those three at-cap options' 'approval-gates.md missing Gate C cap re-prompt omission contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" '- **See full plan** — Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header' 'approval-gates.md missing Gate C See-full-plan bullet'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), print `**⚠ plan.txt missing or empty; nothing to show.**` and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option.' 'approval-gates.md missing Gate C structured missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'the `Other` re-prompt preserves the **same option set unchanged**' 'approval-gates.md missing Gate C Other-path unchanged-option-set contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'when `plan.txt` is missing or empty, print `**⚠ plan.txt missing or empty; nothing to show.**` instead and still re-fire the same prompt' 'approval-gates.md missing Gate C Other missing-plan recovery contract'
contains "$APPROVAL_MD" 'offer this option only when the current review-round count is still below the flattened cap of 5' 'approval-gates.md missing Gate C cap-aware rerun contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Step 3 always runs the full panel via `plan-review-loop.sh`' 'plan-review.md missing full-panel consumer line'
contains "$PLAN_REVIEW_MD" 'injects the SIMPLE-emphasis or HARD-emphasis text immediately after the role line' 'plan-review.md missing tier-emphasis injection contract'
contains "$PLAN_REVIEW_MD" 'vote YES or NO on proposed modifications' 'plan-review.md missing voter YES/NO instruction line'
contains "$PLAN_REVIEW_MD" 'Treat any suggested remedy in the item body as *informational only*' 'plan-review.md missing OOS remedy informational-only pin'
contains "$PLAN_REVIEW_MD" 'Security-tagged findings are held locally and NEVER written to this public OOS issue artifact' 'plan-review.md missing SECURITY.md OOS exclusion pin'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Security-tagged accepted OOS findings are held locally per SECURITY.md and are NOT included in `oos.md`.' 'plan-review.md missing SECURITY.md oos.md exclusion pin'
contains "$DISCUSSION_MD" 'design-postplan-emit.sh' 'discussion-rounds.md missing postplan validator driver helper'

if grep -Eq 'grep .*review-round-count\.txt|review-round-count\.txt.*grep' "$PLAN_LOOP_SH"; then
  fail 'plan-review-loop.sh must not grep review-round-count.txt'
fi
contains "$PLAN_LOOP_SH" '--round-num is a stateless integer supplied by the caller' 'plan-review-loop.sh missing stateless round comment'

absent "$MAKEFILE" 'test-read-design-review-budget-invoke' 'Makefile must not reference deleted read-design-review-budget harness'

# Gate B auto-apply default + --per-round-approval explicit pins are covered above and by current branch-matrix checks.
# Check 15d: design SKILL must not chat-print token/timing summaries.
if grep -nF 'token-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke token-report.sh --summary"
fi
if grep -nF 'timing-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke timing-report.sh --summary"
fi

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "1" ]] \
  || fail "(14a) SKILL.md must keep exactly 1 focus-area enum anchor comment; found $focus_anchor_count"
grep -Fq 'design-postplan-emit.sh' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing design-postplan-emit.sh invocation"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'run-step3-review.sh' "$SKILL_MD" \
  || fail "(14c0) SKILL.md missing run-step3-review.sh Step 3 driver invocation"
grep -Fq 'set +e' "$RUN_STEP3_SH" \
  || fail "(14c0b) run-step3-review.sh missing set +e guard around plan-review-loop.sh"
grep -Fq '_plan_review_rc=$?' "$SKILL_MD" \
  || fail "(14c0c) SKILL.md missing _plan_review_rc capture for run-step3-review.sh"
# shellcheck disable=SC2016 # Markdown/bash excerpt literal; $DESIGN_TMPDIR must not expand here.
contains "$SKILL_MD" '--fallback-input "$_plan_review_stdout_file"' 'SKILL must pass Step 3 stdout as read-result-env fallback'
contains "$SKILL_MD" 'if [[ "$_step3_primary_regular" == true ]]; then' 'SKILL must retain narrow stdout WARN replay for Step 3'
contains "$SKILL_MD" 'missing or invalid LOOP_STATUS after run-step3-review.sh; treating plan review as panel-failed' 'SKILL must default missing LOOP_STATUS to panel-failed (not hard abort on driver exit 1)'
contains "$SKILL_MD" 'configuration error (exit 2)' 'SKILL must warn on run-step3-review.sh exit 2'
grep -Fq 'scout-plan-archetypes-wrapper.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c1) plan-review-loop.sh missing scout-plan-archetypes-wrapper.sh"
grep -Fq 'dispatch-plan-review-panel.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c2) plan-review-loop.sh missing dispatch-plan-review-panel.sh"
grep -Fq 'PANEL_PATHS_FILE' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c3) plan-review-loop.sh missing PANEL_PATHS_FILE handling"
[[ -x "$PLAN_REVIEW_LOOP_SH" ]] \
  || fail "(14c4) plan-review-loop.sh must be executable"
PR_LOOP_MD="$REPO_ROOT/skills/design/scripts/plan-review-loop.md"
[[ -f "$PR_LOOP_MD" ]] || fail "(14c5) plan-review-loop.md missing: $PR_LOOP_MD"
grep -Fqe '--input-mode plan' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c6) plan-review-loop.sh missing --input-mode plan aggregate invocation"
grep -Fq 'tally-plan-review.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c7) plan-review-loop.sh missing tally-plan-review.sh"
grep -Fq 'dispatch-plan-voters.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c8) plan-review-loop.sh missing dispatch-plan-voters.sh"
grep -Fq 'aggregate-findings.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c9) plan-review-loop.sh missing aggregate-findings.sh"
grep -Fq 'check-mid-run-dirty-tree.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c10) plan-review-loop.sh missing check-mid-run-dirty-tree.sh"
grep -Fq 'compose-collector-failure-log.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c11) plan-review-loop.sh missing compose-collector-failure-log.sh"
grep -Fq 'launch-claude-review.sh' "$REPO_ROOT/scripts/dispatch-plan-voters.sh" \
  || fail "(14c12) dispatch-plan-voters.sh missing launch-claude-review.sh (Voter 1)"
TR_LOOP_SH="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.sh"
TR_LOOP_MD="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.md"
[[ -x "$TR_LOOP_SH" ]] || fail "(14c13) test-plan-review-loop.sh missing or not executable"
[[ -f "$TR_LOOP_MD" ]] || fail "(14c14) test-plan-review-loop.md missing"

[[ -x "$PARSE_DESIGN_ARGV_SH" ]] || fail 'parse-design-argv.sh must be executable'
contains "$PARSE_DESIGN_ARGV_SH" 'VALIDATION_ERROR=' 'parse-design-argv.sh missing validation-error output'
contains "$PARSE_DESIGN_ARGV_SH" 'POSITIONAL_KIND=' 'parse-design-argv.sh missing positional-kind output'
grep -Fq 'parse-design-argv.sh' "$SKILL_MD" || fail 'SKILL.md missing parse-design-argv.sh Step 0-pre wiring'
if ! grep -Fq 'POSITIONAL_KIND' "$SKILL_MD" || grep -Fq 'remaining tokens after flags' "$SKILL_MD"; then
  fail 'Step 0b must consume POSITIONAL_KIND from 0-pre, not re-parse argv tail'
fi
step0pre_block=$(awk '/^### 0-pre /,/^### 0a /' "$SKILL_MD")
printf '%s\n' "$step0pre_block" | grep -Fq 'set +e' \
  || fail 'Step 0-pre fence missing set +e around parse-design-argv.sh capture'
printf '%s\n' "$step0pre_block" | grep -Fq '_argv_rc=$?' \
  || fail 'Step 0-pre fence missing explicit _argv_rc capture'
printf '%s\n' "$step0pre_block" | grep -Fq 'VALIDATION_ERROR' \
  || fail 'Step 0-pre fence missing VALIDATION_ERROR handling'
printf '%s\n' "$step0pre_block" | grep -Fq '<PUBLIC_ARGV_WORDS>' \
  || fail 'Step 0-pre fence must invoke parse-design-argv.sh via <PUBLIC_ARGV_WORDS> substitution'
if printf '%s\n' "$step0pre_block" | grep -Fq "\$ARGUMENTS"; then
  fail "Step 0-pre fence must not re-parse \$ARGUMENTS"
fi
printf '%s\n' "$step0pre_block" | grep -Fq 'unexpanded template literal' \
  || fail 'Step 0-pre must reject unexpanded CLAUDE_PLUGIN_ROOT template literal'
printf '%s\n' "$step0pre_block" | grep -Fq 'parse-design-argv.sh not executable' \
  || fail 'Step 0-pre must verify parse-design-argv.sh is executable before invoke'
# shellcheck disable=SC2016 # Markdown literal; ${CLAUDE_PLUGIN_ROOT} must stay unexpanded in the forbidden pattern.
if printf '%s\n' "$step0pre_block" | grep -Fq "= '\${CLAUDE_PLUGIN_ROOT}'"; then
  fail 'Step 0-pre must not compare CLAUDE_PLUGIN_ROOT against a bare ${CLAUDE_PLUGIN_ROOT} sentinel (loader expands it; use a de-tokenized literal)'
fi
contains "$PARSE_DESIGN_ARGV_SH" 'assert_safe_kv_value' 'parse-design-argv.sh missing newline guard on emitted values'
[[ -x "$READ_RESULT_ENV_SH" ]] || fail 'read-result-env.sh must exist and be executable'

argv_call_block=$(printf '%s\n' "$step0pre_block" | awk '
  index($0, "parse-design-argv.sh") && index($0, "${CLAUDE_PLUGIN_ROOT}") { in_call=1 }
  in_call { print }
  in_call && /_argv_rc=\$\?/ { exit }
')
[ -n "$argv_call_block" ] || fail 'Step 0-pre parse-design-argv invocation block extraction failed'
argv_output_line=$(printf '%s\n' "$argv_call_block" | awk '/--output "\$_argv_env"/ {print NR; exit}')
argv_placeholder_line=$(printf '%s\n' "$argv_call_block" | awk '/<PUBLIC_ARGV_WORDS>/ {print NR; exit}')
[[ -n "$argv_output_line" && -n "$argv_placeholder_line" && "$argv_output_line" -lt "$argv_placeholder_line" ]] \
  || fail 'Step 0-pre must pass --output "$_argv_env" before <PUBLIC_ARGV_WORDS>'
argv_stderr_line=$(printf '%s\n' "$argv_call_block" | awk '/2>"\$_argv_err_file"/ {print NR; exit}')
[[ -n "$argv_stderr_line" && -n "$argv_placeholder_line" && "$argv_stderr_line" -lt "$argv_placeholder_line" ]] \
  || fail 'Step 0-pre must redirect parser stderr before <PUBLIC_ARGV_WORDS>'
printf '%s\n' "$argv_call_block" | grep -Fq '>/dev/null' \
  || fail 'Step 0-pre must suppress parser stdout when using --output'
if printf '%s\n' "$argv_call_block" | awk 'seen && /--output/ {found=1} /<PUBLIC_ARGV_WORDS>/ {seen=1} END {exit found ? 0 : 1}'; then
  fail 'Step 0-pre must not pass trailing --output after <PUBLIC_ARGV_WORDS>'
fi
printf '%s\n' "$step0pre_block" | grep -Fq '. "$_argv_env"' \
  || fail 'Step 0-pre must source $_argv_env'
if printf '%s\n' "$step0pre_block" | grep -Fq '_argv_out'; then
  fail 'Step 0-pre must not reference _argv_out after stdout capture removal'
fi
if printf '%s\n' "$step0pre_block" | grep -Fq '_success_kv_count'; then
  fail 'Step 0-pre must not retain _success_kv_count'
fi
if printf '%s\n' "$step0pre_block" | grep -Fq '_seen_'; then
  fail 'Step 0-pre must not retain _seen_ parse-loop sentinels'
fi
if printf '%s\n' "$step0pre_block" | grep -Fq 'while IFS= read -r'; then
  fail 'Step 0-pre must not retain an inline KV parse loop'
fi
printf '%s\n' "$step0pre_block" | grep -Fq "printf 'HARD_REQUESTED=%s\nPARTITION_REQUESTED=%s\nBRAINSTORM_REQUESTED=%s\nAPPROVE_REQUESTED=%s\nSKIP_APPROVE_REQUESTED=%s\nNO_DEDUP_REQUESTED=%s\nRUN_ID=%s\nPOSITIONAL_KIND=%s\nPOSITIONAL_VALUE=%s\n'" \
  || fail 'Step 0-pre must print sourced-value diagnostic from lowercase bindings'
printf '%s\n' "$step0pre_block" | grep -Fq 'parse-design-argv.sh reported VALIDATION_ERROR but exited ${_argv_rc}; aborting before session setup.' \
  || fail 'Step 0-pre must retain VALIDATION_ERROR/non-3 mismatch guard'
argv_err_capture_line=$(printf '%s\n' "$step0pre_block" | awk '/_argv_err="\$\(cat "\$_argv_err_file"/ {print NR; exit}')
argv_literal_guard_line=$(printf '%s\n' "$step0pre_block" | awk '/\*PUBLIC_ARGV_WORDS\*/ {print NR; exit}')
[[ -n "$argv_err_capture_line" && -n "$argv_literal_guard_line" && "$argv_err_capture_line" -lt "$argv_literal_guard_line" ]] \
  || fail 'Step 0-pre must keep literal PUBLIC_ARGV_WORDS stderr guard after _argv_err capture'
printf '%s\n' "$step0pre_block" | grep -Fq 'printf '\''%s %s\n'\'' "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.**" "$VALIDATION_ERROR" >&2' \
  || fail 'Step 0-pre rc=3 branch must retain with-token warning printf'
printf '%s\n' "$step0pre_block" | grep -Fq 'printf '\''%s\n'\'' "**⚠ /design: unrecognized or disallowed public flag — aborting before session setup.**" >&2' \
  || fail 'Step 0-pre rc=3 branch must retain without-token warning printf'

step0b_route_block=$(
  awk '
    /_route_stdout_file=.*mktemp/ { in_block=1 }
    in_block { print }
    in_block && /^[[:space:]]*```[[:space:]]*$/ { exit }
  ' "$SKILL_MD"
)
[ -n "$step0b_route_block" ] || fail 'Step 0b route fenced block extraction failed'
printf '%s\n' "$step0b_route_block" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh' \
  || fail 'Step 0b route block must call read-result-env.sh'
printf '%s\n' "$step0b_route_block" | grep -Fq -- '--input "$DESIGN_TMPDIR/.design-route-result.env"' \
  || fail 'Step 0b route block must pass design-route result env as --input'
printf '%s\n' "$step0b_route_block" | grep -Fq -- '--fallback-input "$_route_stdout_file"' \
  || fail 'Step 0b route block must pass captured stdout as fallback input'
for _route_key in ROUTE BRAINSTORM_PREFIX TITLE_FILTER_REASON TITLE_FILTER_MARKER MARKER_AGE MARKER_TTL DESIGN_REENTRY_MARKER_PATH RESUME_STEP SESSION_ID RUN_ID TIER BRAINSTORM_DONE MARKER_CLEARED; do
  printf '%s\n' "$step0b_route_block" | grep -Fq -- "--allow $_route_key" \
    || fail "Step 0b route block must allowlist $_route_key"
done
printf '%s\n' "$step0b_route_block" | grep -Fq -- '--output "$_safe_route_env"' \
  || fail 'Step 0b route block must write safe route env output'
printf '%s\n' "$step0b_route_block" | grep -Fq '. "$_safe_route_env"' \
  || fail 'Step 0b route block must source safe route env'
printf '%s\n' "$step0b_route_block" | grep -Fq '>"$_route_stdout_file"' \
  || fail 'Step 0b route block must capture design-route.sh stdout'
if printf '%s\n' "$step0b_route_block" | grep -Fq '_route_out'; then
  fail 'Step 0b route block must not reference _route_out'
fi
if printf '%s\n' "$step0b_route_block" | grep -Fq 'while IFS= read -r'; then
  fail 'Step 0b route block must not retain an inline KV parse loop'
fi

step0b_init_block=$(
  awk '
    /_init_stdout_file=.*mktemp/ { in_block=1 }
    in_block { print }
    in_block && /^[[:space:]]*```[[:space:]]*$/ { exit }
  ' "$SKILL_MD"
)
[ -n "$step0b_init_block" ] || fail 'Step 0b init fenced block extraction failed'
printf '%s\n' "$step0b_init_block" | grep -Fq '${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh' \
  || fail 'Step 0b init block must call read-result-env.sh'
printf '%s\n' "$step0b_init_block" | grep -Fq -- '--input "$DESIGN_TMPDIR/.design-init-runparams-result.env"' \
  || fail 'Step 0b init block must pass design-init result env as --input'
printf '%s\n' "$step0b_init_block" | grep -Fq -- '--fallback-input "$_init_stdout_file"' \
  || fail 'Step 0b init block must pass captured stdout as fallback input'
for _init_key in INIT_STATUS RENAMED RUN_PARAMS_PATH DESIGN_CLASSIFICATION; do
  printf '%s\n' "$step0b_init_block" | grep -Fq -- "--allow $_init_key" \
    || fail "Step 0b init block must allowlist $_init_key"
done
printf '%s\n' "$step0b_init_block" | grep -Fq -- '--output "$_safe_init_env"' \
  || fail 'Step 0b init block must write safe init env output'
printf '%s\n' "$step0b_init_block" | grep -Fq '. "$_safe_init_env"' \
  || fail 'Step 0b init block must source safe init env'
printf '%s\n' "$step0b_init_block" | grep -Fq '>"$_init_stdout_file"' \
  || fail 'Step 0b init block must capture design-init-runparams stdout'
if printf '%s\n' "$step0b_init_block" | grep -Fq '_init_out'; then
  fail 'Step 0b init block must not reference _init_out'
fi
if printf '%s\n' "$step0b_init_block" | grep -Fq 'while IFS= read -r'; then
  fail 'Step 0b init block must not retain an inline KV parse loop'
fi

DESIGN_DRIVER_SH="$REPO_ROOT/skills/design/scripts/design-driver.sh"
[[ -x "$DESIGN_POSTPLAN_EMIT_SH" ]] || fail "design-postplan-emit.sh must be executable"
contains "$DESIGN_POSTPLAN_EMIT_SH" 'ACTION=EMIT_PLAN' 'design-postplan-emit.sh missing EMIT_PLAN dispatch'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'snapshot-plan-round.sh' 'design-postplan-emit.sh missing snapshot helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'write-original' 'design-postplan-emit.sh missing write-original call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'invoke-plan-validator.sh' 'design-postplan-emit.sh missing validator helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_resolve_issue' 'design-postplan-emit.sh missing issue resolver'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_pause_checkpoint' 'design-postplan-emit.sh missing pause checkpoint'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_write_result_and_emit' 'design-postplan-emit.sh missing result flush helper'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'set +e' 'design-postplan-emit.sh missing child set +e capture'
contains "$DESIGN_POSTPLAN_EMIT_SH" '--with-plan-size' 'design-postplan-emit.sh missing --with-plan-size flag'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 10' 'design-postplan-emit.sh missing exit 10 defects'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 11' 'design-postplan-emit.sh missing exit 11 pause'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 12' 'design-postplan-emit.sh missing exit 12 hard'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'exit 13' 'design-postplan-emit.sh missing exit 13 partition'
postplan_emit_line=$(grep -nF 'ACTION=EMIT_PLAN' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
postplan_val_line=$(grep -nF 'invoke-plan-validator.sh' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$postplan_emit_line" && -n "$postplan_val_line" && "$postplan_emit_line" -le "$postplan_val_line" ]]   || fail "design-postplan-emit.sh must dispatch EMIT at or before validator"
contains "$SKILL_MD" '.design-postplan-emit-result.env' 'SKILL.md missing postplan result env read'
contains "$SKILL_MD" 'design-postplan-emit.sh configuration error (exit 2)' 'SKILL.md missing postplan exit-2 abort prose'
assert_postplan_thin_fence "$SKILL_MD" 'SKILL Step 2b thin-fence' '<!-- step:2b ' '### Step 2b.5'
run_postplan_thin_fence_self_tests
assert_postplan_reference_thin_fence "$APPROVAL_MD" 'approval-gates Gate B postplan fence' '### Shared post-apply pipeline' '### Gate B plan revision and Step 2b.5'
assert_postplan_reference_thin_fence "$DISCUSSION_MD" 'discussion-round2 postplan fence' '**Plan revision authority**' '## Cap'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
contains "$APPROVAL_MD" 'case "${_postplan_rc:-1}" in' 'approval-gates Gate B postplan fence missing rc case'
contains "$APPROVAL_MD" 'default-abort' 'approval-gates Gate B postplan fence missing default-abort arm'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
contains "$DISCUSSION_MD" 'case "${_postplan_rc:-1}" in' 'discussion-round2 postplan fence missing rc case'
contains "$DISCUSSION_MD" 'default-abort' 'discussion-round2 postplan fence missing default-abort arm'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
absent "$APPROVAL_MD" '<<<"${_postplan_out:-}"' 'approval-gates Gate B postplan fence must not merge stdout KVs via heredoc'
# shellcheck disable=SC2016 # Markdown literal contains unexpanded shell syntax.
absent "$DISCUSSION_MD" '<<<"${_postplan_out:-}"' 'discussion-round2 postplan fence must not merge stdout KVs via heredoc'
# shellcheck disable=SC2016 # Markdown literal; $PPID must remain unexpanded.
contains "$SKILL_MD" 'current-design-env-$PPID.sh' 'SKILL.md Step 2b postplan fence missing canonical prelude'
DESIGN_POSTPLAN_STEP2B=$(awk '/^<!-- step:2b /,/^### Step 2b\.5/' "$SKILL_MD")
if printf '%s\n' "$DESIGN_POSTPLAN_STEP2B" | grep -Fq 'ACTION=EMIT_PLAN'; then
  fail "(FINDING_1) Step 2b block must not retain bare ACTION=EMIT_PLAN outside shared validator failure prose"
fi
step1e_block=$(awk '/Optional trailer guard \(Gate A re-entry rewrites\)/,/^<!-- step:2a /' "$SKILL_MD")
printf '%s\n' "$step1e_block" | grep -Fq 'design-postplan-emit.sh' \
  || fail "(14c14i) Gate A optional-trailer guard missing design-postplan-emit.sh"
printf '%s\n' "$step1e_block" | grep -Fq 'Plan command validator failure' \
  || fail "(14c14i) Gate A optional-trailer guard missing shared defects-found routing"
grep -Fq 'VALIDATE_PLAN_COMMANDS' "$DESIGN_DRIVER_SH" \
  || fail "(14b5) design-driver.sh missing VALIDATE_PLAN_COMMANDS"
grep -Fq 'validate-plan.sh' "$DESIGN_DRIVER_SH" \
  || fail "(14b6) design-driver.sh missing validate-plan.sh dispatch arm"
grep -Fq 'ACTION=VALIDATE_PLAN_COMMANDS' "$SKILL_MD" \
  || fail "(14b7) SKILL.md missing ACTION=VALIDATE_PLAN_COMMANDS"
grep -Fq 'Fix-and-retry' "$SKILL_MD" \
  || fail "(14b8) SKILL.md missing Fix-and-retry validator option label"
grep -Fq 'Override' "$SKILL_MD" \
  || fail "(14b9a) SKILL.md missing Override validator option label"
grep -Fq 'Cancel' "$SKILL_MD" \
  || fail "(14b9b) SKILL.md missing Cancel validator option label"
grep -Fq 'auto-fix-plan-commands.sh' "$SKILL_MD" \
  || fail "(FINDING_14) SKILL.md missing validator auto-fix helper invocation"
grep -Fq '.plan-command-autofix-${_autofix_cycle_key:-site}.attempted' "$SKILL_MD" \
  || fail "(FINDING_23) SKILL.md missing durable auto-fix cycle cap sentinel"
grep -Fq 'ORIGINAL_VALIDATE_LOG_FILE' "$SKILL_MD" \
  || fail "(FINDING_11) SKILL.md missing original validator evidence handoff"
grep -Fq 'Missing/unknown `AUTOFIX_STATUS` never continues silently' "$SKILL_MD" \
  || fail "(FINDING_4) SKILL.md missing auto-fix unknown-status fallback"
grep -Fq 'continue the surrounding success path without prompting' "$SKILL_MD" \
  || fail "(FINDING_17) SKILL.md missing auto-fix ok prompt-suppression contract"
grep -Fq 'Always** append a `Warnings` entry noting that defects occurred and auto-fix did not resolve them' "$SKILL_MD" \
  || fail "(FINDING_17) SKILL.md missing auto-fix fallback warning contract"
grep -Fq -- '--repo-root "$PWD"' "$SKILL_MD" \
  || fail "(FINDING_5) SKILL.md missing consumer repo-root forwarding"
step2b_mark=$(grep -nF 'mark "design Step 2b — plan"' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
postplan_line=$(awk -v s="$step2b_mark" 'NR>s && /design-postplan-emit\.sh/ {print NR; exit}' "$SKILL_MD" || true)
step2b5_line=$(awk -v s="$step2b_mark" 'NR>s && /### Step 2b\.5/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$step2b_mark" && -n "$postplan_line" && -n "$step2b5_line" && "$step2b5_line" -gt "$postplan_line" ]] \
  || fail "(14b10) design-postplan-emit.sh must precede Step 2b.5 in Step 2b block"

AG_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DR_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
[[ -f "$AG_MD" ]] || fail "(14c14a) approval-gates.md missing: $AG_MD"
[[ -f "$DR_MD" ]] || fail "(14c14b) discussion-rounds.md missing: $DR_MD"
grep -Fq 'design-postplan-emit.sh' "$AG_MD" \
  || fail "(14c14c) approval-gates.md missing design-postplan-emit.sh pin"
grep -Fq 'VALIDATE_STATUS' "$AG_MD" \
  || fail "(14c14d) approval-gates.md must reference VALIDATE_STATUS (validator routing through driver)"
grep -Fq -- '--with-plan-size' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing --with-plan-size"
grep -Fq '_postplan_rc=10' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing _postplan_rc=10 handling"
grep -Fq '_postplan_rc=12' "$AG_MD" \
  || fail "(14c14e) approval-gates.md missing _postplan_rc=12 handling"
# shellcheck disable=SC2016 # Markdown literal references SKILL case arms.
grep -Fq 'case` arms as `SKILL.md` Step 2b' "$AG_MD" \
  || fail "(14c14e) approval-gates.md must delegate to SKILL Step 2b case arms"
grep -Fq 'design-postplan-emit.sh' "$DR_MD" \
  || fail "(14c14f) discussion-rounds.md missing design-postplan-emit.sh pin"
grep -Fq -- '--with-plan-size' "$DR_MD" \
  || fail "(14c14g) discussion-rounds.md missing merged --with-plan-size"
if grep -Fq -- '--force-validate' "$DR_MD"; then
  fail "(14c14h) discussion-rounds.md must not mention retired --force-validate"
fi
grep -Fq '_postplan_rc=10' "$DR_MD" \
  || fail "(14c14h) discussion-rounds.md missing _postplan_rc=10 handling"
grep -Fq '_postplan_rc=0' "$DR_MD" \
  || fail "(14c14h) discussion-rounds.md missing _postplan_rc=0 sentinel handling"
printf '%s\n' "$step1e_block" | grep -Fq -- '--with-plan-size' \
  || fail "(14c14i) Gate A optional-trailer guard missing --with-plan-size"
if printf '%s\n' "$step1e_block" | grep -Fq -- '--force-validate'; then
  fail "(14c14i) Gate A optional-trailer guard must not mention retired --force-validate"
fi

# Check 16: dialectic waterfall + per-side assignment contract pins (#2620).
DIALPROTO_MD="$REPO_ROOT/skills/shared/dialectic-protocol.md"
DEBATE_MD="$REPO_ROOT/skills/design/references/dialectic-debate.md"
TIMING_KINDS_SH="$REPO_ROOT/scripts/lib-timing-kinds.sh"
grep -Fq '## Per-side waterfall retry' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing '## Per-side waterfall retry' section header"
grep -Fq 'Debater quorum gate (six tags)' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing six-tag eligibility gate anchor"
grep -Fq '<steelman>' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing <steelman> in six-tag gate text"
grep -Fq '5. **Per-side waterfall retry**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 5 Per-side waterfall retry header"
grep -Fq 'waterfall' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing waterfall token (step 5 contract)"
grep -Fq '1. **Per-side external tool assignment**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 1 per-side external tool assignment header"
grep -Fq 'launch-codex-exec.sh' "$DIALEXEC_MD" \
  || fail "(codex judge) dialectic-execution.md must reference launch-codex-exec.sh for Codex judge"
grep -Fq 'OUTPUT FORMAT' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing OUTPUT FORMAT header"
grep -Fq 'SELF-CHECK BEFORE STOPPING' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing SELF-CHECK BEFORE STOPPING directive"
grep -Fq '2nd-retry' "$SKILL_MD" \
  || fail "(16) design SKILL.md NEVER #2 missing 2nd-retry Claude exception token"
for kind in \
  cursor-debate-thesis-retry1 \
  cursor-debate-antithesis-retry1 \
  codex-debate-thesis-retry1 \
  codex-debate-antithesis-retry1 \
  claude-debate-thesis-retry2 \
  claude-debate-antithesis-retry2
do
  grep -Fq "$kind" "$TIMING_KINDS_SH" \
    || fail "(16) scripts/lib-timing-kinds.sh missing timing kind: $kind"
done

grep -Fq $'2b\tfull plan' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b\\tfull plan row"
grep -Fq $'2b.5\tplan size' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b.5\\tplan size row"
grep -Fq $'5\tfinalize' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 5\\tfinalize row"
grep -Fq $'6\tcleanup' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 6\\tcleanup row"
grep -Fq '> **🔶 /design 5: finalize**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 5 finalize breadcrumb"
grep -Fq '> **🔶 /design 6: cleanup**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 6 cleanup breadcrumb"
step5b_line=$(grep -nF '### 5b — File accepted OOS issues' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step5c_line=$(grep -nF "### 5c — Write \`larch:plan\` to GitHub + publish" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step5b_line" && -n "$step5c_line" ]] || fail "(15b) missing Step 5b or 5c sub-step headers"
if (( step5b_line >= step5c_line )); then
  fail "(15b) Step 5b must appear before Step 5c in SKILL.md"
fi
publish_red_line=$(grep -n 'redact secrets.*composed-plan\.md\|redact-secrets\.sh.*composed-plan\.md' "$REPO_ROOT/skills/design/scripts/design-publish.sh" | head -1 | cut -d: -f1 || true)
publish_val_line=$(grep -n 'invoke-plan-validator\.sh.*composed-plan\.md' "$REPO_ROOT/skills/design/scripts/design-publish.sh" | head -1 | cut -d: -f1 || true)
[[ -n "$publish_red_line" && -n "$publish_val_line" && "$publish_val_line" -lt "$publish_red_line" ]] \
  || fail "(14b11) design-publish.sh validator must appear before redact-secrets on composed-plan.md"
# shellcheck disable=SC2016  # literal backticks + $DESIGN_TMPDIR token must match SKILL.md prose
needle='preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup'
grep -Fq "$needle" "$SKILL_MD" \
  || fail "(14b12) Step 5c validator cancel must preserve tmpdir and skip cleanup"
grep -Fq '5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(15b) anti-halt reminder must mention 5c.5→5c.7→5c.8→6 step boundary (intra-Step-5 through rename)"

DESIGN_PUBLISH_SH="$REPO_ROOT/skills/design/scripts/design-publish.sh"
[[ -x "$DESIGN_PUBLISH_SH" ]] || fail "design-publish.sh must be executable"
publish_plan_line=$(grep -nF 'plan-block-write.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_upsert_line=$(grep -nF 'python/cli.py diagrams upsert' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_log_line=$(grep -nF 'design-log-publish.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$publish_plan_line" && -n "$publish_upsert_line" && -n "$publish_log_line" && "$publish_plan_line" -lt "$publish_upsert_line" && "$publish_upsert_line" -lt "$publish_log_line" ]] \
  || fail "(15b) design-publish.sh must call plan-block-write.sh before python/cli.py diagrams upsert before design-log-publish.sh"
grep -Fq 'architecture-diagram.skipped' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must handle architecture-diagram.skipped sentinel"
grep -Fq -- '--clear-architecture' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must invoke --clear-architecture when skipped sentinel present"
step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step4_line=$(grep -nF '<!-- step:4 —' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step3b_line" && -n "$step4_line" ]] || fail "(15b) missing Step 3b or Step 4 marker"
step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step3b_between" \
  || fail "(15b) Step 3b must document architecture-diagram.skipped sentinel creation"
assert_step3b_finalize_boundary
assert_step2a_entry_simple_guard
assert_simple_branch_has_no_sentinel_fence
assert_no_direct_step3b_step4_routes 'SKILL Step 3b slice' "$SKILL_MD" '<!-- step:3b' '<!-- step:4 —'
assert_no_direct_step3b_step4_routes 'SKILL Step 3/Gate-B-bypass slice' "$SKILL_MD" '<!-- step:3 —' '<!-- step:3.5'
assert_no_direct_step3b_step4_routes 'approval-gates.md' "$APPROVAL_MD"
assert_no_direct_step3b_step4_routes 'run-step3-review.sh' "$RUN_STEP3_SH"
assert_no_direct_step3b_step4_routes 'plan-review.md' "$PLAN_REVIEW_MD"
assert_no_direct_step3b_step4_routes 'flags.md' "$FLAGS_MD"
assert_p3119_family_b_fence_absent "$SKILL_MD" "SKILL.md"
assert_p3119_family_b_fence_absent "$BRAINSTORM_MD" "brainstorm.md"
assert_p3119_family_b_fence_absent "$DIALEXEC_MD" "dialectic-execution.md"
assert_p3119_family_b_fence_absent "$PLAN_REVIEW_MD" "plan-review.md"
assert_p3119_family_b_fence_absent "$DIALPROTO_MD" "dialectic-protocol.md"

printf 'ok - design SKILL uses wrapper-only Bash fences\n'
