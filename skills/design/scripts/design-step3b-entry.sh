#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
MODE=""
SITE=""
SUMMARY_OUTCOME="${SUMMARY_OUTCOME:-}"
SKIP_VALIDATE=""
PUBLIC_ARGV_WORDS=()

DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_TMPDIR="${SESSION_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
ISSUE_TITLE="${ISSUE_TITLE:-}"
HAS_CLARIFY_LABEL="${HAS_CLARIFY_LABEL:-false}"
REPO="${REPO:-}"
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
VALIDATE_STATUS="${VALIDATE_STATUS:-}"
VALIDATE_DEFECT_COUNT="${VALIDATE_DEFECT_COUNT:-}"
VALIDATE_UNSAFE_TOKEN_COUNT="${VALIDATE_UNSAFE_TOKEN_COUNT:-}"
VALIDATE_SKIPPED_COUNT="${VALIDATE_SKIPPED_COUNT:-}"
VALIDATE_LOG_FILE="${VALIDATE_LOG_FILE:-}"
_validator_target_file="${_validator_target_file:-}"
PUBLISH_OK="${PUBLISH_OK:-}"
PLAN_WRITE_OK="${PLAN_WRITE_OK:-}"
STANDALONE_HEAVY_FAILED="${STANDALONE_HEAVY_FAILED:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --site) SITE="$2"; shift 2 ;;
    --snapshot-original) SNAPSHOT_ORIGINAL=true; shift ;;
    --outcome) SUMMARY_OUTCOME="$2"; shift 2 ;;
    --skip-validate) SKIP_VALIDATE=1; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

design_require_plugin_root() {
  _cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort" >&2
    exit 1
  fi
  if [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal ${_cpr_literal}; abort" >&2
    exit 1
  fi
  export CLAUDE_PLUGIN_ROOT
}

design_source_env_optional() {
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_pause_check() {
  if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  fi
}

run_step3b_finalize() {
  _finalize_stdout="$DESIGN_TMPDIR/step3b-finalize-driver.stdout"
  _finalize_stderr="$DESIGN_TMPDIR/step3b-finalize-driver.stderr"
  set +e
  printf '%s\n' 'ACTION=FINALIZE' \
    | python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design driver --design-tmpdir "$DESIGN_TMPDIR" \
      >"$_finalize_stdout" 2>"$_finalize_stderr"
  _finalize_rc=$?
  set -e
  if [ "$_finalize_rc" -ne 0 ]; then
    printf '%s\n' '**⚠ FINALIZE failed; repair the missing artifact before Step 5.**' >&2
    if [ -s "$_finalize_stderr" ]; then
      cat "$_finalize_stderr" >&2
    fi
    exit "$_finalize_rc"
  fi
}

run_step4_mode_probe() {
  _probe_stdout="$DESIGN_TMPDIR/dialectic-gatec-probe.stdout"
  _probe_stderr="$DESIGN_TMPDIR/dialectic-gatec-probe.stderr"
  set +e
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --probe-only \
    >"$_probe_stdout" 2>"$_probe_stderr"
  _probe_rc=$?
  set -e
  if [ "$_probe_rc" -ne 0 ]; then
    printf '%s\n' '**⚠ dialectic Gate C probe failed; repair before Step 4.**' >&2
    if [ -s "$_probe_stderr" ]; then
      cat "$_probe_stderr" >&2
    fi
    exit "$_probe_rc"
  fi

  set +e
  _probe_value="$(
    awk '
      /^DIALECTIC_GATEC_DEBATE_REQUIRED=(true|false)$/ {
        count += 1
        value = $0
        sub(/^DIALECTIC_GATEC_DEBATE_REQUIRED=/, "", value)
        next
      }
      /^DIALECTIC_GATEC_DEBATE_REQUIRED=/ { bad = 1 }
      END {
        if (count == 1 && bad != 1) {
          print value
          exit 0
        }
        exit 1
      }
    ' "$_probe_stdout"
  )"
  _probe_parse_rc=$?
  set -e
  if [ "$_probe_parse_rc" -ne 0 ]; then
    printf '%s\n' '**⚠ dialectic Gate C probe did not emit exactly one valid debate-required row; repair before Step 4.**' >&2
    exit 1
  fi

  case "$_probe_value" in
    true) _step4_mode=background ;;
    false) _step4_mode=foreground ;;
    *) printf '%s\n' "design-step3b-entry.sh: invalid probe value: $_probe_value" >&2; exit 1 ;;
  esac

  printf 'STEP4_MODE=%s\n' "$_step4_mode" > "$DESIGN_TMPDIR/.step4-mode.env.tmp"
  mv "$DESIGN_TMPDIR/.step4-mode.env.tmp" "$DESIGN_TMPDIR/.step4-mode.env"
  printf 'STEP4_MODE=%s\n' "$_step4_mode"
  mkdir -p "$DESIGN_TMPDIR/.completed"
  : > "$DESIGN_TMPDIR/.completed/step-3b"
}

classify_diagram_required() {
  python3 - "$DESIGN_TMPDIR/plan.txt" <<'PY'
import os
import re
import sys

plan_file = sys.argv[1]
allowed_exts = {
    '.md', '.txt', '.rst', '.adoc',
    '.json', '.jsonl', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.tsv', '.csv',
}
# Classifier examples pinned by scripts/test-design-structure.sh: ### NEW:, ### UPDATED:, ### REWRITTEN:, ### MAY_UPDATE:.
# Backtick normalization strips one surrounding pair before extension and SKILL.md checks.
heading_re = re.compile(r'^###[ \t]+(NEW|UPDATED|REWRITTEN|MAY_UPDATE)[ \t]*:(.*)$')

def token_from_tail(tail: str) -> str:
    tail = tail.strip()
    if not tail:
        return ''
    if tail.startswith('`'):
        end = tail.find('`', 1)
        if end >= 0:
            return tail[1:end].strip()
        return ''
    return tail.split()[0].strip()

def normalize(token: str) -> str:
    token = token.strip()
    if len(token) >= 2 and token.startswith('`') and token.endswith('`'):
        token = token[1:-1].strip()
    return token

def is_architectural(path: str) -> bool:
    if not path:
        return True
    parts = [part for part in path.replace('\\', '/').split('/') if part]
    if any(part == 'SKILL.md' for part in parts):
        return True
    base = parts[-1] if parts else path
    if '.' not in base or base.endswith('.'):
        return True
    ext = os.path.splitext(base)[1].lower()
    if ext in ('.sh', '.py'):
        return True
    return ext not in allowed_exts

try:
    if not os.path.getsize(plan_file):
        print('true')
        raise SystemExit
except OSError:
    print('true')
    raise SystemExit

found = False
required = False
try:
    with open(plan_file, encoding='utf-8') as handle:
        for line in handle:
            match = heading_re.match(line.rstrip('\n'))
            if not match:
                continue
            found = True
            path = normalize(token_from_tail(match.group(2)))
            if is_architectural(path):
                required = True
                break
except UnicodeDecodeError:
    required = True

if not found:
    required = True
print('true' if required else 'false')
PY
}

design_source_env_optional
design_require_plugin_root

case "${MODE:-}" in
  entry|finalize)
    mkdir -p "$DESIGN_TMPDIR/.completed"
    rm -f "$DESIGN_TMPDIR/.completed/step-3b" \
      "$DESIGN_TMPDIR/.step4-mode.env" \
      "$DESIGN_TMPDIR/.step4-mode.env.tmp"
    : > "$DESIGN_TMPDIR/.completed/step-3.5"
    design_pause_check
    LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 3b — finalize" >/dev/null 2>&1 || true
    run_step3b_finalize
    run_step4_mode_probe
    ;;
  diagram)
    mkdir -p "$DESIGN_TMPDIR/.completed"
    if [ ! -f "$DESIGN_TMPDIR/.completed/step-4" ]; then
      printf '%s\n' "**⚠ 5b.5: missing .completed/step-4 — Gate C approval incomplete; repair Step 4 before diagram" >&2
      exit 1
    fi
    if [ ! -f "$DESIGN_TMPDIR/.completed/step-5b" ]; then
      printf '%s\n' "**⚠ 5b.5: missing .completed/step-5b — OOS filing incomplete; repair Step 5b before diagram" >&2
      exit 1
    fi
    design_pause_check
    SECONDS=0
    LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 5b.5 — arch diagram" || true
    _diagram_required="$(classify_diagram_required)"
    case "$_diagram_required" in
      true)
        rm -f "$DESIGN_TMPDIR/architecture-diagram.md" \
          "$DESIGN_TMPDIR/architecture-diagram.candidate.md" \
          "$DESIGN_TMPDIR/architecture-diagram.skipped" \
          "$DESIGN_TMPDIR/architecture-diagram-generation.failure.log" \
          "$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log"
        printf '%s\n' 'DIAGRAM_REQUIRED=true'
        ;;
      false)
        rm -f "$DESIGN_TMPDIR/architecture-diagram.md" \
          "$DESIGN_TMPDIR/architecture-diagram.candidate.md" \
          "$DESIGN_TMPDIR/architecture-diagram-generation.failure.log" \
          "$DESIGN_TMPDIR/architecture-diagram-sanitizer.failure.log"
        : > "$DESIGN_TMPDIR/architecture-diagram.skipped"
        : > "$DESIGN_TMPDIR/.completed/step-5b.5"
        printf '%s\n' 'DIAGRAM_REQUIRED=false'
        printf '⏩ 5b.5: arch diagram status=skip reason=no-architectural-change elapsed=%ss\n' "$SECONDS"
        ;;
      *)
        printf '%s\n' "design-step3b-entry.sh: classifier returned invalid value: $_diagram_required" >&2
        exit 1
        ;;
    esac
    ;;
  *) printf '%s\n' "$0: --mode finalize|diagram required" >&2; exit 2 ;;
esac
