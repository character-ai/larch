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
RUN_STEP3_SH="$REPO_ROOT/python/plan_review.py"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
BRAINSTORM_MD="$REPO_ROOT/skills/design/references/brainstorm.md"
DECOMPOSE_PANEL_MD="$REPO_ROOT/skills/design/references/decompose-panel.md"

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
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text().splitlines()
launcher_prefix = '"$HOME/.cache/larch/sessions/design-run-$PPID.sh"'
explicit_step0 = '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step0-session.sh"'

def validate_launcher_line(line: str, label: str) -> str:
    if line.endswith('\\'):
        raise AssertionError(f"{label} has trailing backslash: {line}")
    if not line.startswith(f"{launcher_prefix} "):
        raise AssertionError(f"{label} must start with design-run launcher: {line}")
    rest = line[len(launcher_prefix):].strip()
    if not rest:
        raise AssertionError(f"{label} missing wrapper basename")
    script, _, remaining = rest.partition(' ')
    if script == 'design-step0-session.sh':
        raise AssertionError(f"{label} must not route design-step0-session.sh through the launcher")
    if '/' in script or '..' in script or not script.endswith('.sh'):
        raise AssertionError(f"{label} has invalid wrapper basename: {script}")
    if not re.match(r'^[A-Za-z0-9._-]+\.sh$', script):
        raise AssertionError(f"{label} has invalid wrapper basename characters: {script}")
    if '--session-env-path' in remaining:
        raise AssertionError(f"{label} must not pass --session-env-path through launcher: {line}")
    if '--claude-pid' in remaining:
        raise AssertionError(f"{label} must not pass --claude-pid through launcher: {line}")
    try:
        tokens = shlex.split(remaining)
    except ValueError as exc:
        raise AssertionError(f"{label} has invalid argv quoting: {exc}: {line}") from exc
    for token in tokens:
        if token in {';', '&&', '||', '|'} or '`' in token or '$(' in token:
            raise AssertionError(f"{label} has unsafe argv token: {token}")
    return script

fixtures = [
    ('accepts step3 resume', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND"', True),
    ('accepts braced site', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step2b-postplan.sh --site "${SITE:?}"', True),
    ('accepts quoted note', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-validator-autofix.sh --site "<SITE>" --note "quoted value"', True),
    ('rejects step0 routed', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step0-session.sh', False),
    ('rejects session env', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step2a.sh --session-env-path x', False),
    ('rejects claude pid', '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step2a.sh --claude-pid 123', False),
]
for label, line, should_accept in fixtures:
    try:
        validate_launcher_line(line, label)
        accepted = True
    except AssertionError:
        accepted = False
    if accepted != should_accept:
        print(f"launcher fixture {label} expected accept={should_accept} but got {accepted}: {line}", file=sys.stderr)
        sys.exit(1)

in_fence = False
body = []
start = 0
count = 0
step0_count = 0
for lineno, line in enumerate(lines, 1):
    if not in_fence and line.strip() == "```bash":
        in_fence = True
        body = []
        start = lineno
        continue
    if in_fence and line.strip() == "```":
        count += 1
        nonblank = [part for part in body if part.strip()]
        text = "\n".join(body).strip()
        if 'design-step0-session.sh' in text:
            if text.startswith(launcher_prefix):
                print(f"fence starting line {start} routes design-step0-session.sh through launcher:\n{text}", file=sys.stderr)
                sys.exit(1)
            logical = " ".join(part.strip().rstrip('\\').strip() for part in nonblank)
            if not logical.startswith(explicit_step0):
                print(f"fence starting line {start} must use explicit design-step0-session.sh form:\n{text}", file=sys.stderr)
                sys.exit(1)
            for required in ('--plugin-root "${CLAUDE_PLUGIN_ROOT}"', '--session-env-path "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh"', '--claude-pid "$PPID"', '-- <PUBLIC_ARGV_WORDS>'):
                if required not in logical:
                    print(f"fence starting line {start} missing Step 0a token {required!r}:\n{text}", file=sys.stderr)
                    sys.exit(1)
            step0_count += 1
        else:
            if len(nonblank) != 1:
                print(f"fence starting line {start} must be one physical launcher line:\n{text}", file=sys.stderr)
                sys.exit(1)
            try:
                validate_launcher_line(nonblank[0].strip(), f"fence starting line {start}")
            except AssertionError as exc:
                print(str(exc), file=sys.stderr)
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
if step0_count != 1:
    print(f"expected exactly one explicit design-step0-session.sh fence, found {step0_count}", file=sys.stderr)
    sys.exit(1)
print(f"checked {count} design launcher bash fences")
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
  scripts=$(python3 - "$SKILL_MD" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
fences = re.findall(r'```bash\n(.*?)\n```', text, flags=re.S)
found = set()
for fence in fences:
    found.update(re.findall(r'skills/design/scripts/([A-Za-z0-9._-]+\.sh)', fence))
    found.update(re.findall(r'"\$HOME/\.cache/larch/sessions/design-run-\$PPID\.sh"\s+([A-Za-z0-9._-]+\.sh)', fence))
for script in sorted(found):
    print(f"skills/design/scripts/{script}")
PY
)
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
  contains "$SCRIPT_DIR/design-step0-session.sh" 'agent degraded-tools-gate --skill design' 'Step 0 session wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-route.sh" '.design-route-result.env' 'Step 0 route wrapper missing route result env read'
  contains "$SCRIPT_DIR/design-step0-init.sh" '.design-init-runparams-result.env' 'Step 0 init wrapper missing init result env read'
  contains "$SCRIPT_DIR/design-step2a.sh" 'NO_SKETCHES' 'Step 2a wrapper missing NO_SKETCHES sentinel write'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-postplan-emit.sh' 'Step 2b postplan wrapper missing postplan driver'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--fallback-input "$_plan_review_stdout_file"' 'Step 3 review wrapper missing stdout fallback'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--starting-round "$STARTING_ROUND"' 'Step 3 review wrapper missing starting-round forwarding'
  contains "$SCRIPT_DIR/design-step3-review.sh" '_loop_pid=""' 'Step 3 review wrapper missing loop pid capture'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'set -m 2>/dev/null' 'Step 3 review wrapper missing monitor-mode enable'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'case $- in *m*)' 'Step 3 review wrapper missing monitor-mode verification'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'trap _step3_review_cleanup EXIT' 'Step 3 review wrapper missing process-group kill trap'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'wait "$_loop_pid"' 'Step 3 review wrapper missing loop wait'
  contains "$SCRIPT_DIR/design-step3-review.sh" '_step3_review_teardown_loop_group()' 'Step 3 review wrapper missing teardown helper'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'kill -- -"$_pid"' 'Step 3 review wrapper missing process-group kill'
  contains "$SCRIPT_DIR/design-step3-review.sh" '_step3_review_teardown_loop_group "$_loop_pid"' 'Step 3 review wrapper missing final process-group teardown'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STEP3_REVIEW_LOOP_STATUS=panel-failed' 'Step 3 review wrapper missing pre-launch panel-failed envelope'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'LOOP_STATUS=panel-failed' 'Step 3 review wrapper missing pre-launch loop panel-failed envelope'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'monitor-mode-unavailable' 'Step 3 review wrapper missing monitor-mode failure reason'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'rm -f "$_result_env"' 'Step 3 review wrapper may replay a stale result envelope'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'exit 0' 'Step 3 review wrapper monitor-mode failure must exit 0'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'DIAGRAM_REQUIRED=' 'Step 3b entry wrapper missing DIAGRAM_REQUIRED emit'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" '### NEW:' 'Step 3b entry classifier missing NEW heading token pin'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'Backtick normalization strips one surrounding pair before extension and SKILL.md checks.' 'Step 3b entry classifier missing backtick normalization pin'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'SKILL.md' 'Step 3b entry classifier missing SKILL.md architectural pin'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'architecture-diagram.skipped' 'Step 3b entry wrapper missing visible skipped sentinel'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'ACTION=FINALIZE' 'Step 3b entry wrapper missing inline FINALIZE'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" '.completed/step-3b' 'Step 3b entry wrapper missing step-3b completion sentinel'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '--input "$_candidate"' 'Step 3b sanitizer wrapper must use candidate path'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '---LARCH-DIAGRAM-BEGIN---' 'Step 3b sanitizer wrapper missing diagram begin marker'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '---LARCH-DIAGRAM-END---' 'Step 3b sanitizer wrapper missing diagram end marker'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" 'ACTION=FINALIZE' 'Step 3b sanitizer wrapper missing inline FINALIZE'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '.completed/step-3b' 'Step 3b sanitizer wrapper missing step-3b completion sentinel'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" '---LARCH-REJECTED-BEGIN---' 'Step 3b tail wrapper missing rejected begin marker'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" '---LARCH-REJECTED-END---' 'Step 3b tail wrapper missing rejected end marker'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" '--variant gatec' 'Step 3b tail wrapper missing Gate C preview call'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" '.pause-save-complete" ] && exit 0' 'Step 3b tail wrapper missing pause-save early exit after preview'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" 'SKIP_APPROVE_REQUESTED_GATEC=' 'Step 3b tail wrapper missing Gate C skip-approve emit'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" '.completed/step-4' 'Step 3b tail wrapper missing step-4 sentinel write'
  contains "$SCRIPT_DIR/design-step5c.sh" '${SKIP_VALIDATE:+--skip-validate}' 'Step 5c wrapper missing skip-validate reentry flag'
  contains "$SCRIPT_DIR/design-step5c.sh" '.design-step5c-status.env' 'Step 5c wrapper missing status sidecar write'
  contains "$SCRIPT_DIR/design-clarify.sh" '--phase fetch|publish' 'Clarify wrapper missing two-phase usage'
  contains "$SCRIPT_DIR/design-clarify.sh" 'clarify comment-fetch' 'Clarify wrapper missing comment-fetch helper call'
  contains "$SCRIPT_DIR/design-clarify.sh" '.design-step0-route-state.env' 'Clarify wrapper missing route-state repo fallback'
  contains "$SCRIPT_DIR/design-clarify.sh" 'PUBLISH_OK=false' 'Clarify wrapper missing fail-closed publish status'
  contains "$SCRIPT_DIR/design-clarify.sh" '--state designing' 'Clarify wrapper missing designing rename'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" '.design-step5c-status.env' 'Step 6 cleanup wrapper missing Step 5c status sidecar read'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" 'STEP5B_STATUS=' 'Step 5b prepare wrapper missing STEP5B_STATUS handoff'
  contains "$SCRIPT_DIR/design-step5b-annotate.sh" 'step-5b' 'Step 5b annotate wrapper missing step-5b sentinel write'
  contains "$SCRIPT_DIR/design-step5c.sh" '.completed/step-5b' 'Step 5c wrapper missing step-5b precondition'
  contains "$SCRIPT_DIR/design-step5c.sh" 'STEP5C_STATUS=validator-defects' 'Step 5c wrapper missing validator-defect handoff'
  contains "$SCRIPT_DIR/design-step5c.sh" 'CLEANUP_ELIGIBLE=' 'Step 5c wrapper missing cleanup eligibility sidecar field'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STEP3_REVIEW_LOOP_STATUS=' 'Step 3 review wrapper missing loop status emit'
  contains "$SCRIPT_DIR/design-step3-gate-b-bypass.sh" 'plan-review step3-state' 'Gate B bypass wrapper missing state helper delegation'
  contains "$SCRIPT_DIR/design-step3-continuation-entry.sh" 'auto-continuation-entry' 'Step 3 continuation wrapper missing auto-continuation entry'
  contains "$SCRIPT_DIR/design-step0-abort-cleanup.sh" 'session cleanup-tmpdir' 'Step 0 abort-cleanup wrapper missing tmpdir cleanup'
  contains "$SCRIPT_DIR/design-step0-parse.sh" 'step0-parsed-' 'Step 0 parse wrapper missing parsed env persistence'
  contains "$SCRIPT_DIR/design-step0-session.sh" '.design-step0-parsed.env' 'Step 0 session wrapper missing parsed env copy'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'design-step0-parse.sh' 'Step 0 session wrapper missing inline parse call'
  contains "$SCRIPT_DIR/design-step-validator-autofix.sh" '--validator-target-file' 'Validator autofix wrapper missing CLI target-file arg'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '_postplan_site' 'Step 2b postplan wrapper missing site-aware snapshot branch'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'pause-requested' 'Step 3b entry wrapper missing pause-check before skip/architectural mutations'
  contains "$SCRIPT_DIR/design-step1d5.sh" 'complete' 'Step 1d.5 wrapper missing complete mode sentinel write'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" '.design-step5c-status.env' 'Step 6 prelude wrapper missing Step 5c status read before step-5d'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'CLEANUP_ELIGIBLE' 'Step 6 prelude wrapper missing cleanup eligibility gate'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'PUBLISH_OK' 'Step 6 prelude wrapper missing publish gate before step-5d'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'gh issue view' 'Step 0 route wrapper missing issue fetch'
  contains "$SCRIPT_DIR/design-step0-route.sh" 'POSITIONAL_KIND' 'Step 0 route wrapper missing positional issue binding'
  contains "$SCRIPT_DIR/design-step0-parse.sh" '%q' 'Step 0 parse wrapper missing shell-quoted parsed env persistence'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_RC=' 'Step 2b postplan wrapper missing POSTPLAN_RC emit'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_STATUS=' 'Step 2b postplan wrapper missing POSTPLAN_STATUS emit'
  contains "$SCRIPT_DIR/design-step35-settle.sh" 'design-step2b-postplan.sh' 'Step 3.5 settle wrapper missing postplan delegation'
  contains "$SCRIPT_DIR/design-step35-settle.md" '| `gate-a` | `design-step2b-postplan.sh --site discussion-round2` |' 'Step 3.5 settle docs missing Gate A mapping'
  contains "$SCRIPT_DIR/design-step35-settle.md" '| `discussion-round2` | `design-step2b-postplan.sh --site discussion-round2` |' 'Step 3.5 settle docs missing discussion mapping'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'SCOPE_ANCHOR_FILE=' 'Step 3 review wrapper missing scope anchor emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'TALLY_PLAN_REVIEW_STATUS=' 'Step 3 review wrapper missing tally status emit'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STARTING_ROUND_SEEN=true' 'Step 3 review wrapper missing starting-round seen guard'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'design-step3-review.sh: --starting-round requires a non-empty positive integer' 'Step 3 review wrapper missing empty starting-round rejection'
  contains "$SCRIPT_DIR/design-step3-entry.sh" '--reentry) REENTRY=true' 'Step 3 entry wrapper missing --reentry parser'
  contains "$SCRIPT_DIR/design-step3-entry.sh" ': > "$DESIGN_TMPDIR/.step3-reentry"' 'Step 3 entry --reentry must write reentry marker'
  ! grep -Fq '.step3-entry-plan-printed' "$SCRIPT_DIR/design-step3-entry.sh" \
    || fail 'Step 3 entry --reentry must not clear .step3-entry-plan-printed'
  contains "$SCRIPT_DIR/design-step3-continuation-entry.sh" 'rm -f "$DESIGN_TMPDIR/.step3-entry-plan-printed"' 'Step 3 continuation wrapper must own preview clear'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '--write-completion-only) WRITE_COMPLETION_ONLY=true' 'Step 2b postplan wrapper missing --write-completion-only parser'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '--include-step2b) INCLUDE_STEP2B=true' 'Step 2b postplan wrapper missing --include-step2b parser'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '--write-step2b-completion-only) WRITE_STEP2B_COMPLETION_ONLY=true' 'Step 2b postplan wrapper missing --write-step2b-completion-only parser'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--phase)' 'Step 3 review wrapper missing --phase parser'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--findings-file)' 'Step 3 review wrapper missing --findings-file parser'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--postplan-operator-continue)' 'Step 3 review wrapper missing --postplan-operator-continue parser'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'step3_review_validate_resume_state' 'Step 3 review wrapper missing resume-state validation helper'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'step3_review_write_resume_state' 'Step 3 review wrapper missing resume-state write helper'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STEP3_REVIEW_HAS_RESUME_STATE" = false' 'Step 3 review wrapper missing no-flag pause branch'
  contains "$SKILL_MD" 'Step 3 resume fence (all mid-loop returns)' 'SKILL missing Step 3 background resume fence'
  contains "$SKILL_MD" 'STEP3_RESUME_ROUND' 'SKILL missing non-empty Step 3 resume round binding'
  contains "$SKILL_MD" 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation' 'SKILL missing wrapper-owned Step 3 continuation resume wording'
  ! grep -Fq 'run-step3-review.sh --design-tmpdir "$DESIGN_TMPDIR" --mode loop --starting-round' "$SKILL_MD" \
    || fail 'SKILL must not route mid-loop resumes directly through run-step3-review.sh'
  contains "$SKILL_MD" 'design-step3-gate-b-bypass.sh' 'SKILL missing gate-b-bypass wrapper bash fence'
  contains "$SKILL_MD" 'design-step3-continuation-entry.sh' 'SKILL missing continuation-entry wrapper bash fence'
  ! grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5b"' "$SCRIPT_DIR/design-step5c.sh" \
    || fail 'Step 5c wrapper must not synthesize step-5b sentinel'
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh' 'Immediate-background required' 'Step 3 review missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh' 'timeout: 21600000' 'Step 3 review missing timeout pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh' '<task-notification>' 'Step 3 review missing task-notification wait' 1700
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh' 'Immediate-background required' 'Step 5c publish missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh' 'timeout: 21600000' 'Step 5c publish missing timeout pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh' '<task-notification>' 'Step 5c publish missing task-notification wait' 1700
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-final-summary.sh' 'Immediate-background required' 'Final summary missing immediate-background pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-final-summary.sh' 'timeout: 21600000' 'Final summary missing timeout pin' 900
  contains_near "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-final-summary.sh' '<task-notification>' 'Final summary missing task-notification wait' 1700
  contains "$SKILL_MD" 'END THE TURN' 'SKILL missing immediate-background END THE TURN directive'
  contains "$SKILL_MD" 'yielding is NOT a halt' 'SKILL missing immediate-background yield-not-halt directive'
  contains "$SKILL_MD" '<task-notification> is the only resume trigger' 'SKILL missing task-notification-only resume directive'
  contains "$SKILL_MD" 'ignore the launch ack' 'SKILL missing launch ack ignore directive'
  contains "$SKILL_MD" 'twice-per-wait reviewer status cadence' 'SKILL missing twice-per-wait reviewer status cadence'
  contains "$REPO_ROOT/skills/shared/orchestrator-never.md" 'ZERO progress-observation tool calls' 'orchestrator-never missing zero progress-observation intent rule'
  contains "$REPO_ROOT/skills/shared/orchestrator-never.md" 'sleep N &&' 'orchestrator-never missing sleep probe ban'
  contains "$REPO_ROOT/skills/shared/orchestrator-never.md" 'TaskOutput' 'orchestrator-never missing TaskOutput ban'
  contains "$REPO_ROOT/skills/shared/orchestrator-never.md" '1890FD62-0DA8-4259-B652-BE9FFD962A76' 'orchestrator-never missing incident run id'
  contains "$SCRIPT_DIR/design-step3-review.sh" '.bg-wait-active' 'Step 3 review wrapper missing bg wait marker'
  contains "$SCRIPT_DIR/design-step3-review.sh" 'STEP=design-step3-review' 'Step 3 review wrapper missing marker step id'
  contains "$SCRIPT_DIR/design-step-final-summary.sh" 'STEP=design-step-final-summary' 'Final summary wrapper missing marker step id'
  contains "$SCRIPT_DIR/design-step5c.sh" 'STEP=design-step5c' 'Step 5c wrapper missing marker step id'
  contains "$SCRIPT_DIR/design-step5c.sh" 'design_bg_wait_marker_start design-step5c || true' 'Step 5c wrapper missing fail-soft bg wait marker call'
  contains "$SCRIPT_DIR/design-step-final-summary.sh" 'pause-requested' 'Final summary wrapper missing pause-check before bg wait marker'
  contains "$REPO_ROOT/python/plan_review.py" 'reviewer-status.tsv' 'plan_review missing round reviewer status artifact'
  contains "$REPO_ROOT/python/plan_review.py" 'latest-reviewer-status.tsv' 'plan_review missing latest reviewer status artifact'
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
    '--mode complete',
    '#### Step 2b drafter',
    '#### Step 2b postplan',
    'terminal postplan fence',
    '> **🔶 /design 3b: arch diagram**',
    'Step 3 resume fence (all mid-loop returns)',
    '**MainAgent vote boundary**',
    '**Gate A "Ready for review" / Gate C "Re-run review panel" re-entry only**',
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
  ! grep -Fq 'design-step0-degraded.sh' "$SKILL_MD" \
    || fail 'SKILL must not reference deleted degraded-tools wrapper'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'agent degraded-tools-gate --skill design' 'Step 0 session wrapper missing gate call'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'STEP0_STATUS=' 'Step 0 session wrapper missing STEP0_STATUS emit'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'DEGRADED_PROMPT_REQUIRED=true' 'Step 0 session wrapper missing prompt-required emit'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'needs-degraded-decision' 'Step 0 session wrapper missing needs-degraded-decision branch'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'BOTH_DOWN_SEEN' 'Step 0 session wrapper missing BOTH_DOWN parse presence tracking'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'degraded-both-down-auto' 'Step 0 session wrapper missing non-interactive both-down branch'
  contains "$SCRIPT_DIR/design-step0-session.sh" '.degraded-tools-gate-prompted' 'Step 0 session wrapper missing prompted sentinel write'
  contains "$SCRIPT_DIR/design-step0-session.sh" '-f "$DESIGN_TMPDIR/.degraded-tools-gate-prompted"' 'Step 0 session wrapper missing sentinel short-circuit'
  contains "$SCRIPT_DIR/design-step0-session.sh" 'LARCH_SKILL_NON_INTERACTIVE' 'Step 0 session wrapper missing explicit non-interactive signal'
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
  contains "$SCRIPT_DIR/design-step3-entry-state.sh" 'plan-review step3-state' 'Step 3 entry-state wrapper missing state helper call'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" 'STEP5B_NEEDS_ANNOTATE=true' 'Step 5b prepare wrapper missing annotate recovery handoff'
  contains "$SKILL_MD" 'STEP0_STATUS' 'SKILL missing STEP0_STATUS consume prose'
  contains "$SCRIPT_DIR/design-step3-entry.sh" '.pause-save-complete' 'Step 3 combined entry wrapper missing pause-save stop guard'
  contains "$SCRIPT_DIR/design-step3-entry.sh" 'rm -f "$DESIGN_TMPDIR/.pause-save-complete"' 'Step 3 combined entry wrapper missing stale pause-save sentinel clear'
  contains "$SCRIPT_DIR/design-step3b-tail.sh" 'rm -f "$DESIGN_TMPDIR/.pause-save-complete"' 'Step 3b tail wrapper missing stale pause-save sentinel clear'
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
    'design-step3-entry-state.sh:plan-review step3-state' \
    'design-step3b-sanitize.sh:mermaid sanitize' \
    'design-step3b-entry.sh:architecture-diagram.skipped' \
    'design-step3b-tail.sh:design Step 4 — rejected findings' \
    'design-step35-settle.sh:plan-review gate-b-dedup'
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
  contains "$APPROVAL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b' 'approval-gates.md missing launcher-form Gate B settle reference'
  contains "$APPROVAL_MD" 'design-step35-settle.sh` calls `design-step2b-postplan.sh --site gate-b` internally' 'approval-gates.md missing Gate B internal postplan mapping'
  ! grep -Fq '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step2b-postplan.sh" --session-env-path "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh" --claude-pid "$PPID" --site gate-b' "$APPROVAL_MD" \
    || fail 'approval-gates.md must not keep inline Gate B transport args'
  ! grep -Fq 'with the canonical session-env / pause prelude' "$APPROVAL_MD" \
    || fail 'approval-gates.md must not instruct a separate postplan pause prelude'
  contains "$APPROVAL_MD" 'design-step5c.sh --skip-validate' 'approval-gates.md missing Step 5c skip-validate wrapper reference'
  contains "$APPROVAL_MD" 'emit-design-plan-preview.sh --design-tmpdir "$DESIGN_TMPDIR" --variant full' 'approval-gates.md missing Gate C full-plan helper reference'
  contains "$SKILL_MD" 'emit-design-plan-preview.sh --design-tmpdir "$DESIGN_TMPDIR" --variant full' 'SKILL.md missing Gate C full-plan helper reference'
  contains "$SCRIPT_DIR/emit-design-plan-preview.sh" 'step3|gatec|step2b|full' 'emit-design-plan-preview.sh usage missing full variant'
  contains "$SCRIPT_DIR/emit-design-plan-preview.sh" 'full)' 'emit-design-plan-preview.sh missing full case'
  contains "$SCRIPT_DIR/emit-design-plan-preview.sh" 'cat "$design_tmpdir/plan.txt"' 'emit-design-plan-preview.sh full variant must emit complete plan'
  ! grep -Fq 'cat `$DESIGN_TMPDIR/plan.txt`' "$APPROVAL_MD" \
    || fail 'approval-gates.md must use full-plan helper instead of raw Gate C cat'
  ! grep -Fq 'both paths `cat` `$DESIGN_TMPDIR/plan.txt`' "$SKILL_MD" \
    || fail 'SKILL.md must use full-plan helper instead of raw Gate C cat prose'
  contains "$DISCUSSION_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site discussion-round2' 'discussion-rounds.md missing launcher-form discussion-round2 settle reference'
  contains "$DISCUSSION_MD" '`gate-a` and `discussion-round2` both map to `design-step2b-postplan.sh --site discussion-round2` internally' 'discussion-rounds.md missing discussion internal postplan mapping'
  contains "$SKILL_MD" 'No migrated mid-loop resume uses `--starting-round` alone' 'SKILL missing no-bare migrated resume invariant'
  contains "$SKILL_MD" 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-apply' 'SKILL missing MAV accepted-findings apply resume'
  contains "$SKILL_MD" 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation' 'SKILL missing zero-findings continuation resume'
  contains "$SKILL_MD" 'design-step3-entry.sh --reentry' 'SKILL missing Step 3 entry reentry wrapper prose'
  awk '/^```bash$/,/^```$/ { if (/design-step3-entry\.sh --reentry/) found=1 } END { exit !found }' "$SKILL_MD" \
    || fail 'SKILL Step 3 re-entry bash fence missing --reentry'
  contains "$APPROVAL_MD" 'design-step3-entry.sh --reentry' 'approval-gates missing Step 3 entry reentry wrapper prose'
  contains "$APPROVAL_MD" 'design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation' 'approval-gates missing collapsed continuation resume prose'
  ! grep -Fq '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-step2b-postplan.sh" --session-env-path "$HOME/.cache/larch/sessions/current-design-env-$PPID.sh" --claude-pid "$PPID" --site discussion-round2' "$DISCUSSION_MD" \
    || fail 'discussion-rounds.md must not keep inline discussion-round2 transport args'
  ! grep -Fq 'with the canonical session-env / pause prelude' "$DISCUSSION_MD" \
    || fail 'discussion-rounds.md must not instruct a separate postplan pause prelude'
  contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-a' 'SKILL.md missing launcher-form Gate A settle reference'
  contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b' 'SKILL.md missing launcher-form Gate B settle reference'
  ! grep -Fq ':-current' "$SKILL_MD" \
    || fail 'SKILL.md must not use :-current Gate B marker fallback'
  ! grep -Fq '.gate-b-postapply-ready-current' "$SKILL_MD" \
    || fail 'SKILL.md must not probe .gate-b-postapply-ready-current'
  contains "$SKILL_MD" 'every post-Step-0a Bash fence invokes `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" <wrapper>.sh ...`' 'Anti-pattern #3 missing launcher-owned fence wording'
  contains "$SKILL_MD" 'Wrappers own source-env and pause-check behavior internally' 'Anti-pattern #3 missing wrapper-owned source-env wording'
  contains "$SKILL_MD" 'assert_wrapper_pause_before_work' 'Anti-pattern #3 missing wrapper pause enforcement anchor'
  ! grep -Fq 'NEVER omit the pause-check line from surviving source-env Bash fences' "$SKILL_MD" \
    || fail 'Anti-pattern #3 must not preserve direct source-env fence wording'
  ! grep -Fq 'assert_bash_fences_have_pause_check' "$SKILL_MD" \
    || fail 'Anti-pattern #3 must not point at obsolete fence-level pause-check assertions'
  contains "$FILE_OOS_MD" 'oos-issue.stdout.txt' 'file-design-oos.md missing issue stdout handoff contract'
}

assert_no_bare_settle_invocations() {
  python3 - "$SKILL_MD" "$APPROVAL_MD" "$DISCUSSION_MD" <<'PY'
import re
import sys
from pathlib import Path

launcher = 'design-run-$PPID.sh'
backtick_settle = re.compile(r'`design-step35-settle\.sh[^`]*`')
for path_str in sys.argv[1:]:
    path = Path(path_str)
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if 'design-step35-settle.sh' not in line or '--site' not in line:
            continue
        if launcher in line:
            continue
        if backtick_settle.search(line):
            continue
        print(
            f"FAIL: {path.name} line {lineno} has bare design-step35-settle.sh --site invocation: {line}",
            file=sys.stderr,
        )
        sys.exit(1)
PY
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


assert_step5_fold_and_summary_markers() {
  python3 - "$SKILL_MD" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
fences = re.findall(r'```bash\n(.*?)\n```', text, flags=re.S)
for fence in fences:
    if 'design-step5.sh' in fence:
        print('FAIL: skills/design/SKILL.md must not contain a design-step5.sh Bash fence', file=sys.stderr)
        sys.exit(1)
PY
  ! grep -Fq '### 5a — Update Reviewer Presence Status' "$SKILL_MD" \
    || fail 'SKILL.md must not contain the empty Step 5a heading'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" ': > "$DESIGN_TMPDIR/.completed/step-4b"' 'Step 5b prepare wrapper missing step-4b sentinel write'
  contains "$SCRIPT_DIR/design-step5b-prepare.sh" 'timing mark "design Step 5 — finalize"' 'Step 5b prepare wrapper missing Step 5 timing mark'
  contains "$SCRIPT_DIR/design-step5c.sh" 'LARCH_FINAL_SUMMARY_BEGIN' 'Step 5c wrapper missing final-summary begin marker'
  contains "$SCRIPT_DIR/design-step5c.sh" 'LARCH_FINAL_SUMMARY_END' 'Step 5c wrapper missing final-summary end marker'
  contains "$SCRIPT_DIR/design-step-final-summary.sh" 'LARCH_FINAL_SUMMARY_BEGIN' 'Final summary wrapper missing final-summary begin marker'
  contains "$SCRIPT_DIR/design-step-final-summary.sh" 'LARCH_FINAL_SUMMARY_END' 'Final summary wrapper missing final-summary end marker'
  contains "$SKILL_MD" 'using the first balanced `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` whole-line marker pair' 'SKILL missing final-summary marker extraction prose'
  contains "$SKILL_MD" 'fall back to reading `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` when the file is non-empty' 'SKILL missing final-summary file Read fallback prose'
  ! grep -Fq "printf '%s\\n' \"\$_issue_stdout\" > \"\$DESIGN_TMPDIR/oos-issue.stdout.txt\"" "$SKILL_MD" \
    || fail 'SKILL Step 5b OOS bridge must not instruct shell printf for issue stdout'
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
  contains "$SCRIPT_DIR/design-step6-prelude.sh" '.bg-wait-active' 'Step 6 prelude wrapper missing in-flight marker guard'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" '.bg-wait-active' 'Step 6 cleanup wrapper missing in-flight marker guard'
  contains "$SCRIPT_DIR/design-step6-prelude.sh" 'appears still in-flight' 'Step 6 prelude wrapper missing in-flight diagnostic'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" 'appears still in-flight' 'Step 6 cleanup wrapper missing in-flight diagnostic'
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


assert_design_failure_reporting_contract() {
  contains "$SKILL_MD" 'design-clarify.sh --phase fetch --issue "$ISSUE_NUMBER"' 'Step 0b clarify fetch must use launcher wrapper'
  contains "$SKILL_MD" 'design-clarify.sh --phase publish --issue "$ISSUE_NUMBER"' 'Step 0b clarify publish must use launcher wrapper'
  contains "$SKILL_MD" 'stages `failed-clarify`' 'Step 0b clarify fetch failure must stage failed-clarify'
  contains "$SKILL_MD" '$DESIGN_TMPDIR/clarify-plan.md' 'Step 0b clarify must use separate plan artifact'
  contains "$SKILL_MD" '$DESIGN_TMPDIR/clarify-response.md' 'Step 0b clarify must use separate response artifact'
  contains "$SKILL_MD" 'Clarify operator cancel remains `operator-action` or `cancelled-clarify`' 'Step 0b clarify cancel must remain operator action or cancelled-clarify'
  contains "$SKILL_MD" 'export `SUMMARY_OUTCOME` to one of `cancelled-already-planned` | `cancelled-clarify` | `cancelled-decompose` | `cancelled-outline` | `cancelled-plan-size` | `cancelled-sprawl` | `cancelled-title-filter` | `approved` | `approved-partition` | `failed-plan-write` | `failed-publish` | `failed-clarify` | `failed-postplan` | `failed-judge-panel` | `failed-publish-tail`' 'SUMMARY_OUTCOME enumeration must include design failure outcomes'
  contains "$SKILL_MD" 'On the second `PANEL_STATUS=panel-failed`, Split-path stages `failed-judge-panel` through `design-stage-terminal-state.sh`' 'Step 2b.5 second panel-failed must stage failed-judge-panel'
  contains "$SKILL_MD" 'runs the Final summary block before exit 1, preserves `$DESIGN_TMPDIR`, and does not delegate retry exhaustion to `design-step3-review.sh`' 'Step 2b.5 must own retry exhaustion and run final summary'
  contains "$SKILL_MD" 'Prompt-side orchestration must not call `record-escalation` for those statuses.' 'Step 3 prompt side must not record script-owned escalation'
  contains "$SKILL_MD" '`panel-failed`, `tally-error`, and `degraded-empty-collector` remain non-terminal Gate B bypass statuses' 'Step 3 panel degradation must be non-terminal'
  contains "$SKILL_MD" 'When `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, set `SUMMARY_OUTCOME=failed-postplan`' 'Step 3 postplan-failed must route prompt-side final summary'
  contains "$SKILL_MD" '`postplan-operator-required` is escalation evidence.' 'postplan-operator-required must be escalation trigger'
  if grep -Fq 'design-step-clarify.sh' "$SKILL_MD"; then
    fail 'SKILL.md must not reference non-existent design-step-clarify.sh'
  fi
  contains "$DECOMPOSE_PANEL_MD" '--outcome failed-judge-panel' 'decompose-panel retry exhaustion command must use failed-judge-panel'
  contains "$DECOMPOSE_PANEL_MD" '--trigger decompose-panel-retry-exhausted' 'decompose-panel retry exhaustion command must use decompose trigger'
}

assert_wrapper_fence_ordering() {
  local wrapper first_line second_line
  wrapper='design-step3-entry-state.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'plan-review step3-state' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before direct-review state mutation"

  wrapper='design-step3b-tail.sh'
  first_line=$(grep -nF 'SKIP_APPROVE_REQUESTED_GATEC=' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF '.completed/step-4' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must write step-4 only after Gate C skip read"
  wrapper='design-step5c.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'design-publish.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before publish"
  wrapper='design-step6-cleanup.sh'
  first_line=$(grep -nF 'design-pause-save.sh' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  second_line=$(grep -nF 'session cleanup-tmpdir' "$SCRIPT_DIR/$wrapper" | head -1 | cut -d: -f1)
  (( first_line < second_line )) || fail "$wrapper must pause-check before cleanup"
}

assert_compact_reviewer_table_step3_scoped() {
  contains "$SKILL_MD" '⏳ 5c: writing plan to GitHub' 'SKILL missing plain Step 5c immediate-background breadcrumb'
  contains "$SKILL_MD" '⏳ final-summary: writing final summary' 'SKILL missing plain final-summary immediate-background breadcrumb'
  ! grep -Fq 'each immediate-background wait' "$SKILL_MD" \
    || fail 'SKILL compact-table rule must not fire for every immediate-background wait'
  ! grep -Fq 'permitted breadcrumb/status table' "$SKILL_MD" \
    || fail 'SKILL must not reference deprecated "permitted breadcrumb/status table" phrasing'
}

assert_step2b_drafter_folded_postplan_contract() {
  contains "$SKILL_MD" 'design-step2b-drafter.sh` now owns Step 2a exact sentinel validation' 'SKILL missing folded prelude ownership'
  contains "$SKILL_MD" 'design-step2b-postplan.sh --site step2b --snapshot-original --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" --plugin-root "$CLAUDE_PLUGIN_ROOT"' 'SKILL missing delegated postplan transport argv'
  contains "$SKILL_MD" 'Use `timeout: 2100000` on the Bash tool call for this drafter subprocess fence.' 'SKILL missing increased Step 2b drafter timeout'
  contains "$SKILL_MD" 'Parse `POSTPLAN_RC=` and `POSTPLAN_STATUS=` from wrapper-owned rows after `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1`.' 'SKILL missing wrapper-owned postplan row parser'
  contains "$SKILL_MD" 'Require a subsequent whole-line `DRAFTER_STATUS=succeeded` marker before binding postplan rows.' 'SKILL missing DRAFTER_STATUS succeeded parser gate'
  contains "$SKILL_MD" 'Do not use the Bash tool exit code alone for drafter-success postplan routing.' 'SKILL missing no-exit-code-alone routing guard'
  contains "$SKILL_MD" 'Ignore `POSTPLAN_*` and `DRAFTER_STATUS=*` text in plan preview output.' 'SKILL missing preview machine-row ignore guard'
  contains "$SKILL_MD" '`_postplan_out` for internal postplan routing is sliced to the delegated postplan segment after `DRAFTER_STATUS=succeeded`, excluding the plan preview.' 'SKILL missing sliced internal postplan output binding'
  contains "$SKILL_MD" 'Fail closed when drafter success has missing postplan rows.' 'SKILL missing incomplete internal postplan fail-closed branch'
  contains "$SKILL_MD" 'The missing-row fail-safe may run the retained terminal postplan fence at most once when the drafter fence exited zero.' 'SKILL missing one-shot missing-row fail-safe'
  contains "$SKILL_MD" 'skip the retained terminal postplan fence for all complete internal-postplan outcomes when inline retry is not pending' 'SKILL missing normal-success skip retained postplan wording'
  contains "$SKILL_MD" 'The inline-retry gate can be triggered by either the drafter fence or terminal postplan fence.' 'SKILL missing dual-source inline retry gate'
  contains "$SKILL_MD" 'run the retained terminal postplan fence exactly once after the inline rewrite' 'SKILL missing exact one terminal postplan after inline retry'
  ! grep -Fq 'proceed directly to the retained terminal postplan fence' "$SKILL_MD" \
    || fail 'SKILL must not keep stale drafter-success retained-postplan wording'
  ! grep -Fq 'continue at the terminal postplan fence' "$SKILL_MD" \
    || fail 'SKILL must not keep stale continue-at-terminal-postplan wording'
  python3 - "$SKILL_MD" <<'PY'
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
start = text.index('<!-- step:2b')
end = text.index('### Step 2b.5', start)
section = text[start:end]
if 'design-step2b-prelude.sh' in section:
    print('Step 2b section must not call the standalone prelude wrapper', file=sys.stderr)
    sys.exit(1)
fences = re.findall(r'```bash\n(.*?)\n```', section, flags=re.S)
terminal = [f for f in fences if 'design-step2b-postplan.sh --site step2b --snapshot-original' in f]
if len(terminal) != 1:
    print(f'expected one retained terminal postplan fence, found {len(terminal)}', file=sys.stderr)
    sys.exit(1)
PY
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'step2b_exact_line_file()' 'drafter wrapper missing exact sentinel helper'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'approach-synthesis.txt" "NO_SKETCHES"' 'drafter wrapper missing approach sentinel check'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'contested-decisions.md" "NO_CONTESTED_DECISIONS"' 'drafter wrapper missing contested sentinel check'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'dialectic-resolutions.md' 'drafter wrapper missing dialectic sentinel check'
  ! grep -Fq 'design-step2b-prelude.sh' "$SCRIPT_DIR/design-step2b-drafter.sh" \
    || fail 'drafter wrapper must not source design-step2b-prelude.sh'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" ': > "$DESIGN_TMPDIR/.completed/step-2a"' 'drafter wrapper missing step-2a repair'
  python3 - "$SCRIPT_DIR/design-step2b-drafter.sh" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
repair = text.index(': > "$DESIGN_TMPDIR/.completed/step-2a"')
pause = text.index('design-pause-save.sh')
timing = text.index('timing mark "design Step 2b')
launch = text.index('launch-codex-drafter.sh')
if not (repair < pause < timing < launch):
    print('drafter wrapper order must be repair, pause, timing, launch', file=sys.stderr)
    sys.exit(1)
prelaunch = text[:launch]
if prelaunch.count('design-pause-save.sh') != 1:
    print('drafter wrapper must contain one active pause-save boundary before launch', file=sys.stderr)
    sys.exit(1)
PY
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'design-step2b-postplan.sh"' 'drafter wrapper missing delegated postplan exec'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" '--site step2b' 'drafter wrapper missing delegated --site step2b'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" '--snapshot-original' 'drafter wrapper missing delegated --snapshot-original'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" '--session-env-path "$SESSION_ENV_PATH"' 'drafter wrapper missing delegated --session-env-path'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" '--claude-pid "$CLAUDE_PID"' 'drafter wrapper missing delegated --claude-pid'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" '--plugin-root "$CLAUDE_PLUGIN_ROOT"' 'drafter wrapper missing delegated --plugin-root'
  ! grep -Fq 'design-postplan-emit.sh' "$SCRIPT_DIR/design-step2b-drafter.sh" \
    || fail 'drafter wrapper must not call design-postplan-emit.sh directly'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1' 'drafter wrapper missing wrapper row delimiter'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'DRAFTER_STATUS=' 'drafter wrapper missing DRAFTER_STATUS row'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" 'DRAFTER_VENDOR=' 'drafter wrapper missing DRAFTER_VENDOR row'
  contains "$SCRIPT_DIR/design-step2b-drafter.sh" "sed 's/^/[plan-preview] /'" 'drafter wrapper missing machine-safe preview prefix'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'case "${_postplan_rc:-1}" in' 'postplan wrapper missing retained rc matrix'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" '  11)' 'postplan wrapper missing rc 11 arm'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_RC=11' 'postplan wrapper missing rc11 row'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'POSTPLAN_STATUS=pause-save' 'postplan wrapper missing pause-save status row'
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
assert_no_bare_settle_invocations
assert_postplan_thin_fence "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-step2b-postplan.sh'
assert_publish_fence_guards
assert_step5_fold_and_summary_markers
assert_step6_cleanup_wrappers
assert_wrapper_fence_ordering
assert_step2b_drafter_folded_postplan_contract
assert_design_failure_reporting_contract
assert_no_direct_step3b_step4_routes 'SKILL Step 3b slice' "$SKILL_MD" '<!-- step:3b' '<!-- step:4 —'
assert_no_direct_step3b_step4_routes 'SKILL Step 3/Gate-B-bypass slice' "$SKILL_MD" '<!-- step:3 —' '<!-- step:3.5'
assert_no_direct_step3b_step4_routes 'approval-gates.md' "$APPROVAL_MD"
assert_no_direct_step3b_step4_routes 'plan_review.py' "$RUN_STEP3_SH"
assert_no_direct_step3b_step4_routes 'plan-review.md' "$PLAN_REVIEW_MD"
assert_no_direct_step3b_step4_routes 'flags.md' "$FLAGS_MD"
assert_compact_reviewer_table_step3_scoped
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$SKILL_MD" "SKILL.md" || fail "(3119) SKILL.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$BRAINSTORM_MD" "brainstorm.md" || fail "(3119) brainstorm.md still has removed Family-B fence tokens"
python3 "$REPO_ROOT/python/cli.py" lint p3119-fence-absence "$PLAN_REVIEW_MD" "plan-review.md" || fail "(3119) plan-review.md still has removed Family-B fence tokens"

printf 'ok - design SKILL uses wrapper-only Bash fences\n'
