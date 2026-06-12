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

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

contains_near() {
  local file="$1" anchor="$2" needle="$3" label="$4" radius="${5:-900}"
  python3 - "$file" "$anchor" "$needle" "$label" "$radius" <<'PY'
import sys
from pathlib import Path
path, anchor, needle, label, radius = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
text = Path(path).read_text()
idx = text.find(anchor)
if idx < 0:
    print(f"FAIL: {label}: missing anchor {anchor!r}", file=sys.stderr)
    sys.exit(1)
window = text[max(0, idx - radius):idx + radius]
if needle not in window:
    print(f"FAIL: {label}: missing {needle!r} near {anchor!r}", file=sys.stderr)
    sys.exit(1)
PY
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
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'agent degraded-tools-gate --skill design' 'Step 0 degraded wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-route.sh" '.design-route-result.env' 'Step 0 route wrapper missing route result env read'
  contains "$SCRIPT_DIR/design-step0-init.sh" '.design-init-runparams-result.env' 'Step 0 init wrapper missing init result env read'
  contains "$SCRIPT_DIR/design-step2a.sh" 'NO_SKETCHES' 'Step 2a wrapper missing NO_SKETCHES sentinel write'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-postplan-emit.sh' 'Step 2b postplan wrapper missing postplan driver'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--fallback-input "$_plan_review_stdout_file"' 'Step 3 review wrapper missing stdout fallback'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--starting-round "$STARTING_ROUND"' 'Step 3 review wrapper missing starting-round forwarding'
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
  contains "$SCRIPT_DIR/design-step0-parse.sh" '%q' 'Step 0 parse wrapper missing shell-quoted parsed env persistence'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_RC=' 'Step 2b postplan wrapper missing POSTPLAN_RC emit'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_STATUS=' 'Step 2b postplan wrapper missing POSTPLAN_STATUS emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'SCOPE_ANCHOR_FILE=' 'Step 3 review wrapper missing scope anchor emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'TALLY_PLAN_REVIEW_STATUS=' 'Step 3 review wrapper missing tally status emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STARTING_ROUND_SEEN=true' 'Step 3 review wrapper missing starting-round seen guard'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'design-step3-review.sh: --starting-round requires a non-empty positive integer' 'Step 3 review wrapper missing empty starting-round rejection'
  contains "$SKILL_MD" 'Step 3 resume fence (all mid-loop returns)' 'SKILL missing Step 3 background resume fence'
  contains "$SKILL_MD" 'STEP3_RESUME_ROUND' 'SKILL missing non-empty Step 3 resume round binding'
  contains "$SKILL_MD" 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"' 'SKILL missing wrapper-owned Step 3 resume wording'
  ! grep -Fq 'run-step3-review.sh --design-tmpdir "$DESIGN_TMPDIR" --mode loop --starting-round' "$SKILL_MD" \
    || fail 'SKILL must not route mid-loop resumes directly through run-step3-review.sh'
  contains "$SKILL_MD" 'design-step3-gate-b-bypass.sh' 'SKILL missing gate-b-bypass wrapper bash fence'
  contains "$SKILL_MD" 'design-step3-continuation-entry.sh' 'SKILL missing continuation-entry wrapper bash fence'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5b"' "$SCRIPT_DIR/design-step5c.sh" \
    || fail 'Step 5c wrapper must not synthesize step-5b sentinel'
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step3-review.sh"' 'Immediate-background required' 'Step 3 review missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step3-review.sh"' 'timeout: 21600000' 'Step 3 review missing timeout pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step3-review.sh"' '<task-notification>' 'Step 3 review missing task-notification wait' 1700
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step5c.sh"' 'Immediate-background required' 'Step 5c publish missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step5c.sh"' 'timeout: 21600000' 'Step 5c publish missing timeout pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step5c.sh"' '<task-notification>' 'Step 5c publish missing task-notification wait' 1700
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step-final-summary.sh"' 'Immediate-background required' 'Final summary missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step-final-summary.sh"' 'timeout: 21600000' 'Final summary missing timeout pin' 900
  contains_near "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step-final-summary.sh"' '<task-notification>' 'Final summary missing task-notification wait' 1700
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
    '> **🔶 /design 3b: arch diagram**',
    'branch-local skip fence below',
    'architectural entry cleanup fence below',
    'Step 3 resume fence (all mid-loop returns)',
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
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'agent degraded-tools-gate' 'Step 0 degraded wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'STEP0_STATUS=' 'Step 0 degraded wrapper missing STEP0_STATUS emit'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'needs-degraded-decision' 'Step 0 degraded wrapper missing needs-degraded-decision branch'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'BOTH_DOWN_SEEN' 'Step 0 degraded wrapper missing BOTH_DOWN parse presence tracking'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" 'degraded-both-down-auto' 'Step 0 degraded wrapper missing non-interactive both-down branch'
  contains "$SCRIPT_DIR/design-step0-degraded.sh" '.degraded-tools-gate-prompted' 'Step 0 degraded wrapper missing prompted sentinel write'
  contains "$SCRIPT_DIR/design-step0-init.sh" 'feature-description.txt' 'Step 0 init wrapper missing feature-description write'
  contains "$SCRIPT_DIR/design-step0-route.sh" "printf 'ROUTE=%s" 'Step 0 route wrapper missing ROUTE stdout emit'
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
assert_no_direct_step3b_step4_routes 'SKILL Step 3b slice' "$SKILL_MD" '<!-- step:3b' '<!-- step:4 —'
assert_no_direct_step3b_step4_routes 'SKILL Step 3/Gate-B-bypass slice' "$SKILL_MD" '<!-- step:3 —' '<!-- step:3.5'
assert_no_direct_step3b_step4_routes 'approval-gates.md' "$APPROVAL_MD"
assert_no_direct_step3b_step4_routes 'run-step3-review.sh' "$RUN_STEP3_SH"
assert_no_direct_step3b_step4_routes 'plan-review.md' "$PLAN_REVIEW_MD"
assert_no_direct_step3b_step4_routes 'flags.md' "$FLAGS_MD"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$SKILL_MD" "SKILL.md" || fail "(3119) SKILL.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$BRAINSTORM_MD" "brainstorm.md" || fail "(3119) brainstorm.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$PLAN_REVIEW_MD" "plan-review.md" || fail "(3119) plan-review.md still has removed Family-B fence tokens"

printf 'ok - design SKILL uses wrapper-only Bash fences\n'
