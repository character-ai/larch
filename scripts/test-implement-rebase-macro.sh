#!/usr/bin/env bash
# Rebase checkpoint macro harness for wrapperized /implement.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
ERRORS_FILE="$(mktemp "${TMPDIR:-/tmp}/test-implement-rebase-macro-errors.XXXXXX")"
trap 'rm -f "$ERRORS_FILE"' EXIT

add_error() {
  printf '%s\n' "$1" >>"$ERRORS_FILE"
}

require_text() {
  local text="$1"
  local needle="$2"
  local label="$3"
  if [[ "$text" != *"$needle"* ]]; then
    add_error "$label"
  fi
}

count_occurrences() {
  local text="$1"
  local needle="$2"
  local count=0
  local rest="$text"
  local before=
  while :; do
    before="${rest%%"$needle"*}"
    if [[ "$before" == "$rest" ]]; then
      break
    fi
    count=$((count + 1))
    rest="${rest#*"$needle"}"
  done
  printf '%s' "$count"
}

read_file() {
  cat "$1"
}

skill="$(read_file "$REPO_ROOT/skills/implement/SKILL.md")"
ref="$(read_file "$REPO_ROOT/skills/implement/references/rebase-checkpoint-routing.md")"
owner="$(read_file "$REPO_ROOT/crates/larch-cli/src/push_rebase.rs")"
bootstrap="$(read_file "$REPO_ROOT/crates/larch-cli/src/implement_bootstrap_continuation.rs")"
step7a="$(read_file "$REPO_ROOT/skills/implement/scripts/step-7a.sh")"
step7a_rs="$(read_file "$REPO_ROOT/crates/larch-cli/src/implement_review_commands.rs")"

if [[ "$(count_occurrences "$skill" 'larch-run.sh" scripts/larch.sh push checkpoint-probe 1.r')" -ne 0 ]]; then
  add_error 'SKILL.md must not call prompt-side 1.r probe'
fi
if [[ "$bootstrap" != *'fn run_1r_probe('* ]] || [[ "$bootstrap" != *'OsString::from("checkpoint-probe")'* ]]; then
  add_error 'Rust bootstrap continuation must invoke the Rust checkpoint probe for 1.r'
fi
if [[ "$bootstrap" != *'plan materialization'* ]]; then
  add_error 'Rust bootstrap continuation 1.r probe must use plan materialization label'
fi
if [[ "$bootstrap" != *'forked_target'* ]] || [[ "$bootstrap" != *'REBASE_RC'* ]]; then
  add_error 'Rust bootstrap continuation must pass forked_target and synthesize REBASE_RC'
fi
if [[ "$bootstrap" != *'"CHECKPOINT_NEXT"'* ]]; then
  add_error 'Rust bootstrap continuation must relay CHECKPOINT_NEXT'
fi
if [[ "$owner" != *'CHECKPOINT_NEXT'* ]] || [[ "$owner" != *'load-routing'* ]]; then
  add_error 'crates/larch-cli/src/push_rebase.rs must emit CHECKPOINT_NEXT continue/load-routing directives'
fi
for needle in \
  'CHECKPOINT_NEXT=continue|load-routing' \
  'CHECKPOINT_NEXT=continue` is the only macro no-op predicate' \
  'Missing or malformed `CHECKPOINT_NEXT` fails closed' \
  'DEGRADED_PROMPT_REQUIRED=true' \
  'The `7a.r` macro skip is `CHECKPOINT_NEXT`-only'
do
  if [[ "$skill" != *"$needle"* ]]; then
    add_error "SKILL.md missing CHECKPOINT_NEXT macro contract '$needle'"
  fi
done
if [[ "$(count_occurrences "$skill" 'larch-run.sh" scripts/larch.sh push checkpoint-probe 4.r')" -ne 0 ]]; then
  add_error '4.r standalone launcher probe call must be folded into the Step 3 composite'
fi
if [[ "$(count_occurrences "$skill" 'larch-run.sh" scripts/larch.sh push checkpoint-probe 7.r')" -ne 0 ]]; then
  add_error '7.r standalone launcher probe call must be folded into the Step 6 composite'
fi
if [[ "$(count_occurrences "$skill" 'skills/implement/scripts/run-step-checks.sh --site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"')" -ne 1 ]]; then
  add_error 'Step 3 composite launcher must carry --rebase-checkpoint-4r and --forked-target'
fi
if [[ "$(count_occurrences "$skill" 'skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}"')" -ne 1 ]]; then
  add_error 'Step 6 composite launcher must call step-6-entry.sh with --forked-target'
fi
if [[ "$skill" == *'BASE_ARGS=()'* ]]; then
  add_error 'SKILL.md still contains inline BASE_ARGS blocks'
fi
for needle in \
  '**Orchestrator contract: absorbed `1.r` (Step 0 envelope only)**' \
  '**Orchestrator contract: folded and direct probe relays (`4.r`, `7.r`, `7a.r`)**' \
  'CHECKPOINT_NEXT=continue|load-routing' \
  'CHECKPOINT_NEXT=load-routing' \
  'REBASE_OUTCOME=conflict' \
  '**⚠ Rebase onto main failed (non-conflict): $REBASE_ERROR. Bailing to cleanup.**' \
  '**⚠ Rebase onto main failed unexpectedly' \
  'Call-site registry' \
  'caller_kind=early_rebase' \
  '7a.r' \
  'Absorbed Step 1.r'
do
  if [[ "$ref" != *"$needle"* ]]; then
    add_error "rebase reference missing $needle"
  fi
done
if [[ "$owner" != *'--forked-target'* ]] || [[ "$owner" != *'FORKED_REMOTE'* ]] || [[ "$owner" != *'"upstream"'* ]] || [[ "$owner" != *'"main"'* ]]; then
  add_error 'crates/larch-cli/src/push_rebase.rs does not implement --forked-target upstream/main mapping'
fi
if [[ "$step7a" != *'implement step-7a'* ]] || [[ "$step7a" != *'scripts/larch.sh'* ]]; then
  add_error 'step-7a.sh must delegate to scripts/larch.sh implement step-7a'
fi
if [[ "$step7a_rs" != *'OsString::from("checkpoint-probe")'* ]] || [[ "$step7a_rs" != *'OsString::from("7a.r")'* ]]; then
  add_error 'implement_review_commands.rs must keep one internal 7a.r Rust probe invocation'
fi
if [[ "$step7a_rs" != *'"upstream".to_owned()'* ]] || [[ "$step7a_rs" != *'args.base_ref'* ]]; then
  add_error 'implement_review_commands.rs must keep its internal base derivation'
fi

if [[ -s "$ERRORS_FILE" ]]; then
  cat "$ERRORS_FILE" >&2
  exit 1
fi
printf '%s\n' 'PASS: test-implement-rebase-macro.sh (routing reference + absorbed 1.r + folded 4.r/7.r + --forked-target calls)'
