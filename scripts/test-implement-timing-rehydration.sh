#!/usr/bin/env bash
# Structural timing/telemetry rehydration checks for /implement.

# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
skill_file="$REPO_ROOT/skills/implement/SKILL.md"
ERRORS_FILE="$(mktemp "${TMPDIR:-/tmp}/test-implement-timing-rehydration-errors.XXXXXX")"
trap 'rm -f "$ERRORS_FILE"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

add_error() {
  printf '%s\n' "$1" >>"$ERRORS_FILE"
}

# Invariant A: stale two-key exports must not return.
if ( command grep -Fq 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE' "$skill_file" ); then
  fail 'SKILL.md still exports the stale two-key token context without LARCH_TIMING_LEDGER'
fi

# Invariant B/D: SKILL.md fences do not inline telemetry/read-key work.
blocked_tokens=(
  'session read-key'
  'scripts/larch.sh timing report'
  'scripts/larch.sh timing telemetry-mark'
)
in_fence=0
start=0
line_num=0
while IFS= read -r line || [[ -n "$line" ]]; do
  line_num=$((line_num + 1))
  trimmed="${line#"${line%%[![:space:]]*}"}"
  if [[ "$trimmed" == '```bash'* ]]; then
    in_fence=1
    start=$line_num
  elif [[ "$in_fence" -eq 1 && "$trimmed" == '```'* ]]; then
    in_fence=0
  elif [[ "$in_fence" -eq 1 ]]; then
    for token in "${blocked_tokens[@]}"; do
      if [[ "$line" == *"$token"* ]]; then
        add_error "fence starting ${start}: inline telemetry/read-key token '${token}'"
      fi
    done
  fi
done <"$skill_file"
if [[ -s "$ERRORS_FILE" ]]; then
  cat "$ERRORS_FILE" >&2
  exit 1
fi

# Invariant B: the Rust commit-route owner rehydrates the telemetry session
# triplet (#8611), the Rust Step 5 review owner marks the review-handoff timing,
# and the Step 18 wrapper owns closing telemetry.
command grep -Fq 'LARCH_TOKEN_SESSION_ID' "$REPO_ROOT/crates/larch-cli/src/implement_commit_route_commands.rs" || fail 'Rust commit owner does not rehydrate telemetry session keys'
command grep -Fq 'fn record_step5_handoff_timing' "$REPO_ROOT/crates/larch-cli/src/implement_review_commands.rs" || fail 'Rust Step 5 review owner does not mark review-handoff timing'
command grep -Fq 'OsString::from("Step 5: review handoff")' "$REPO_ROOT/crates/larch-cli/src/implement_review_commands.rs" || fail 'Rust Step 5 review owner does not mark implement timing'
command grep -Fq 'LARCH_TIMING_LEDGER' "$REPO_ROOT/crates/larch-cli/src/implement_commit_route_commands.rs" || fail 'Rust commit owner does not resolve LARCH_TIMING_LEDGER'
command grep -Fq 'rehydrate_session(&tmpdir)' "$REPO_ROOT/crates/larch-cli/src/implement_terminal_commands.rs" || fail 'step-18 Rust owner does not rehydrate telemetry keys'
command grep -Fq 'ChildEnvironment::LarchTimingSkill' "$REPO_ROOT/crates/larch-cli/src/implement_terminal_commands.rs" || fail 'step-18 Rust owner does not mark implement timing'
command grep -Fq 'implement step-18 "$@"' "$REPO_ROOT/skills/implement/scripts/step-18.sh" || fail 'step-18.sh does not delegate to the Rust step-18'

# `implement run-dispatch` is Rust-owned (#8623).
command grep -Fq 'rehydrate_session(&tmpdir)' "$REPO_ROOT/crates/larch-cli/src/implement_step2_commands.rs" || fail 'run-dispatch does not rehydrate telemetry keys'
command grep -Fq '.step2-telemetry-marked' "$REPO_ROOT/crates/larch-cli/src/implement_step2_commands_impl.rs" || fail 'run-dispatch does not guard Step 2 telemetry once-only'
command grep -Fq 'answers.is_empty()' "$REPO_ROOT/crates/larch-cli/src/implement_step2_commands.rs" || fail 'run-dispatch does not skip telemetry on answers redispatch'

# Invariant C: every plugin-rooted Bash fence carries the same-fence source guard.
source_guard='[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"'
tmpdir_export='export IMPLEMENT_TMPDIR'
in_fence=0
start=0
line_num=0
guard_count=0
root_fallback_count=0
fence_body=()
while IFS= read -r line || [[ -n "$line" ]]; do
  line_num=$((line_num + 1))
  trimmed="${line#"${line%%[![:space:]]*}"}"
  if [[ "$trimmed" == '```bash'* ]]; then
    in_fence=1
    start=$line_num
    fence_body=()
  elif [[ "$in_fence" -eq 1 && "$trimmed" == '```'* ]]; then
    text="$(printf '%s\n' "${fence_body[@]}")"
    if [[ "$text" == *'${CLAUDE_PLUGIN_ROOT}'* ]] && [[ "$text" != *"$source_guard"* ]]; then
      add_error "fence starting ${start}: missing canonical plugin-root source guard"
    fi
    if [[ "$text" == *'${CLAUDE_PLUGIN_ROOT}'* ]] && [[ "$text" == *'$IMPLEMENT_TMPDIR'* ]] && [[ "$text" != *"$tmpdir_export"* ]]; then
      add_error "fence starting ${start}: missing IMPLEMENT_TMPDIR export"
    fi
    for raw in "${fence_body[@]}"; do
      stripped="${raw#"${raw%%[![:space:]]*}"}"
      stripped="${stripped%"${stripped##*[![:space:]]}"}"
      if [[ "$stripped" == "$source_guard" ]]; then
        guard_count=$((guard_count + 1))
      fi
      if [[ "$raw" == *'--print-plugin-root'* ]]; then
        root_fallback_count=$((root_fallback_count + 1))
      fi
    done
    in_fence=0
  elif [[ "$in_fence" -eq 1 ]]; then
    fence_body[${#fence_body[@]}]="$line"
  fi
done <"$skill_file"
if [[ "$guard_count" -eq 0 ]]; then
  add_error 'no plugin-root source guards found'
fi
if [[ "$root_fallback_count" -lt 1 ]]; then
  add_error "expected at least one pre-bootstrap plugin-root fallback to remain, found ${root_fallback_count}"
fi
if [[ -s "$ERRORS_FILE" ]]; then
  cat "$ERRORS_FILE" >&2
  exit 1
fi
printf 'plugin-root guards=%s root-fallbacks=%s\n' "$guard_count" "$root_fallback_count"

# Invariant E (#3425): closing marks stay inside Step 18 before terminal
# snapshot preparation, while teardown remains Step 19-owned.
terminal="$REPO_ROOT/crates/larch-cli/src/implement_terminal_commands.rs"
done_mark_line="$(awk '/Step 18 — logs flush/ {print NR; exit}' "$terminal")"
snapshot_call_line="$(awk '/complete_terminal_run_log\(root, tmpdir/ {print NR; exit}' "$terminal")"
[[ -n "$done_mark_line" ]] || fail 'implement_terminal_commands.rs lacks Step 18 logs-flush mark'
[[ -n "$snapshot_call_line" ]] || fail 'implement_terminal_commands.rs lacks terminal snapshot call'
[[ "$done_mark_line" -lt "$snapshot_call_line" ]] || fail 'Step 18 logs-flush mark must precede terminal snapshot preparation'
finalize_invocations="$(command grep -Fc '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" skills/implement/scripts/step-18.sh' "$skill_file" || true)"
[[ "$finalize_invocations" -eq 1 ]] || fail "expected one step-18.sh invocation in SKILL.md, found $finalize_invocations"
command grep -Fq '"$HOME/.cache/larch/sessions/implement-run-$PPID.sh" scripts/larch.sh implement step-18-gate-logs-flush' "$skill_file" || fail 'SKILL.md lacks composite Step 18 launcher'
command grep -Fq 'FinalizePhase::Teardown' "$terminal" || fail 'implement_terminal_commands.rs lacks in-process teardown dispatch'
command grep -Fq '"final-report",' "$terminal" || fail 'implement_terminal_commands.rs lacks live step18b argv'
command grep -Fq 'fn print_summary_markers' "$terminal" || fail 'implement_terminal_commands.rs lacks marker helper'
command grep -Fq 'implement step-18 "$@"' "$REPO_ROOT/skills/implement/scripts/step-18.sh" || fail 'step-18.sh must remain a thin larch delegate'
command grep -Fq 'implement step-19 "$@"' "$REPO_ROOT/skills/implement/scripts/step-19.sh" || fail 'step-19.sh must remain a thin larch delegate'

# Invariant F (#4286): round timing duplicate probe returns success when the row exists.
step5_owner="$REPO_ROOT/crates/larch-cli/src/implement_review_commands.rs"
step5_text="$(cat "$step5_owner")"
required='cols[4] == "Step 5 — code review"'
forbidden='END { exit found }'
step5_errors=0
if [[ "$step5_text" != *"$required"* ]]; then
  printf '%s lacks %s\n' "$step5_owner" "'$required'" >&2
  step5_errors=1
fi
if [[ "$step5_text" == *"$forbidden"* ]]; then
  printf '%s still uses bare %s\n' "$step5_owner" "'$forbidden'" >&2
  step5_errors=1
fi
[[ "$step5_errors" -eq 0 ]] || exit 1

printf 'PASS: test-implement-timing-rehydration.sh (Rust commit owner rehydrates telemetry; closing marks line %s < terminal snapshot line %s; teardown is Step 19-owned)\n' "$done_mark_line" "$snapshot_call_line"
