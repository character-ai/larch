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
  contains "$SCRIPT_DIR/design-step2a3-collect.sh" 'collect-agent-results.sh --timeout 1260' 'Step 2a.3 wrapper missing collector timeout'
  contains "$SCRIPT_DIR/design-step2b-postplan.sh" 'design-postplan-emit.sh' 'Step 2b postplan wrapper missing postplan driver'
  contains "$SCRIPT_DIR/design-step3-review.sh" '--fallback-input "$_plan_review_stdout_file"' 'Step 3 review wrapper missing stdout fallback'
  contains "$SCRIPT_DIR/design-step3b-sanitize.sh" '--input "$DESIGN_TMPDIR/architecture-diagram.candidate.md"' 'Step 3b sanitizer wrapper must use DESIGN_TMPDIR candidate path'
  contains "$SCRIPT_DIR/design-step3b-entry.sh" 'architecture-diagram.skipped' 'Step 3b entry wrapper missing visible skipped sentinel'
  contains "$SCRIPT_DIR/design-step5c.sh" '${SKIP_VALIDATE:+--skip-validate}' 'Step 5c wrapper missing skip-validate reentry flag'
  contains "$SCRIPT_DIR/design-step5c.sh" '.design-step5c-status.env' 'Step 5c wrapper missing status sidecar write'
  contains "$SCRIPT_DIR/design-step6-cleanup.sh" '.design-step5c-status.env' 'Step 6 cleanup wrapper missing Step 5c status sidecar read'
}

assert_reference_updates() {
  contains "$PLAN_REVIEW_MD" 'Deferred main-agent adjudication' 'plan-review.md missing deferred adjudication section'
  contains "$APPROVAL_MD" 'design-step2b-postplan.sh' 'approval-gates.md missing postplan wrapper reference'
  contains "$APPROVAL_MD" 'design-step5c.sh --skip-validate' 'approval-gates.md missing Step 5c skip-validate wrapper reference'
  contains "$DISCUSSION_MD" 'design-step2b-postplan.sh --site discussion-round2' 'discussion-rounds.md missing discussion-round2 wrapper reference'
  contains "$FILE_OOS_MD" 'oos-issue.stdout.txt' 'file-design-oos.md missing issue stdout handoff contract'
}

assert_design_skill_bash_fences_are_wrappers
assert_no_inline_bash_tokens_in_skill_fences
assert_direct_wrappers_are_executable_and_documented
assert_no_direct_state_helper_in_skill_fences
assert_wrapper_contract_pins
assert_reference_updates

printf 'ok - design SKILL uses wrapper-only Bash fences\n'
