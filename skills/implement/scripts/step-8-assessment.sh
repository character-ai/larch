#!/usr/bin/env bash
# step-8-assessment.sh — blocking bgjob adapter for Piece 2 architectural-assessment run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

STEP="implement-step8-assessment"
BUDGET_S=2100
WAIT_CHUNK_S=270
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
STARTED_PRINTED=false

while [ $# -gt 0 ]; do
  case "$1" in
    --bgjob-child) BGJOB_CHILD=true; shift ;;
    --merge-result-env)
      [ $# -ge 2 ] || { printf '%s\n' 'step-8-assessment.sh: --merge-result-env requires a path' >&2; exit 2; }
      MERGE_RESULT_ENV=$2
      shift 2
      ;;
    --help)
      printf '%s\n' 'Usage: step-8-assessment.sh [--bgjob-child --merge-result-env PATH]'
      exit 0
      ;;
    *)
      printf '%s\n' "step-8-assessment.sh: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

rehydrate_plugin_root() {
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
    # shellcheck source=/dev/null
    . "$IMPLEMENT_TMPDIR/plugin-root.env"
  fi
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
  fi
  export CLAUDE_PLUGIN_ROOT
}

die() {
  printf 'step-8-assessment.sh: %s\n' "$1" >&2
  exit 2
}

reject_nl() {
  case "$1" in
    *$'\n'*|*$'\r'*) return 1 ;;
    *) return 0 ;;
  esac
}

read_env_key() {
  local key=$1 file=$2 line
  [ -f "$file" ] || return 0
  [ ! -L "$file" ] || return 0
  line=$(grep "^${key}=" "$file" 2>/dev/null | tail -n 1 || true)
  if [ -n "$line" ]; then
    printf '%s\n' "${line#*=}"
  fi
}

safe_path_under_tmpdir() {
  python3 - "$1" "$IMPLEMENT_TMPDIR" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
root = Path(sys.argv[2])
try:
    resolved = path.resolve()
    root_resolved = root.resolve()
except OSError:
    raise SystemExit(1)
if path.is_symlink() or not path.is_file():
    raise SystemExit(1)
try:
    _ = resolved.relative_to(root_resolved)
except ValueError:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

safe_regular_path_under_tmpdir() {
  python3 - "$1" "$IMPLEMENT_TMPDIR" <<'PY'
from pathlib import Path
import stat
import sys

path = Path(sys.argv[1])
root = Path(sys.argv[2])
try:
    raw_root = root.absolute()
    raw_path = path.absolute()
    relative = raw_path.relative_to(raw_root)
    if any(part == ".." for part in relative.parts):
        raise ValueError
    if stat.S_ISLNK(raw_root.lstat().st_mode) or not stat.S_ISDIR(raw_root.lstat().st_mode):
        raise ValueError
    current = raw_root
    for part in relative.parts[:-1]:
        current /= part
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ValueError
    mode = raw_path.lstat().st_mode
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError
    _ = raw_path.resolve().relative_to(raw_root.resolve())
except (OSError, ValueError):
    raise SystemExit(1)
raise SystemExit(0)
PY
}

safe_truncate() {
  local path=$1 parent tmp
  parent=${path%/*}
  if [ -L "$parent" ]; then
    die "refusing symlinked parent for $path"
  fi
  if [ -L "$path" ]; then
    die "refusing symlinked file $path"
  fi
  if [ -e "$path" ] && [ ! -f "$path" ]; then
    die "refusing non-regular file $path"
  fi
  tmp=$(mktemp "${path}.tmp.XXXXXX") || exit 2
  : >"$tmp"
  chmod 0600 "$tmp" 2>/dev/null || true
  mv -f "$tmp" "$path" 2>/dev/null || { rm -f "$tmp" 2>/dev/null || true; exit 2; }
}

safe_unlink() {
  local path=$1
  safe_regular_path_under_tmpdir "$path" || {
    [ ! -e "$path" ] && [ ! -L "$path" ] || die "unsafe stale file $path"
    return 0
  }
  if [ -L "$path" ]; then
    die "refusing to unlink symlink $path"
  fi
  if [ -e "$path" ] && [ ! -f "$path" ]; then
    die "refusing to unlink non-regular $path"
  fi
  rm -f "$path" || die "failed removing stale file $path"
  [ ! -e "$path" ] && [ ! -L "$path" ] || die "stale file remains after cleanup $path"
}

write_merge_kvs() {
  local path=$1
  shift
  local tmp key value
  safe_regular_path_under_tmpdir "$path" || die "unsafe merge-result-env"
  tmp=$(mktemp "${path}.tmp.XXXXXX") || exit 2
  {
    while [ $# -gt 0 ]; do
      key=$1
      value=$2
      shift 2
      case "$key" in
        BGJOB_PID|BGJOB_OWNER_PID|BGJOB_STATUS|BGJOB_RC|BGJOB_ELAPSED_S|STEP)
          rm -f "$tmp" 2>/dev/null || true
          die "refusing daemon-reserved merge key $key"
          ;;
      esac
      reject_nl "$value" || { rm -f "$tmp" 2>/dev/null || true; die "newline in merge value for $key"; }
      printf '%s=%s\n' "$key" "$value"
    done
  } >"$tmp" || { rm -f "$tmp" 2>/dev/null || true; exit 2; }
  chmod 0600 "$tmp" 2>/dev/null || true
  safe_regular_path_under_tmpdir "$path" || { rm -f "$tmp" 2>/dev/null || true; die "merge-result-env changed before replacement"; }
  mv -f "$tmp" "$path" || { rm -f "$tmp" 2>/dev/null || true; exit 2; }
}

resolve_repo_root() {
  local root
  root=$(read_env_key REPO_ROOT "$IMPLEMENT_TMPDIR/session-env.sh")
  [ -n "$root" ] || die "missing REPO_ROOT in session-env.sh"
  reject_nl "$root" || die "REPO_ROOT contains newline"
  [ -d "$root" ] || die "REPO_ROOT is not a directory"
  [ ! -L "$root" ] || die "REPO_ROOT must not be a symlink"
  [ -d "$root/.git" ] || [ -f "$root/.git" ] || die "REPO_ROOT missing .git"
  printf '%s\n' "$root"
}

parse_requested_kinds() {
  local handoff detail detail_file raw token seen rest
  handoff="$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env"
  [ -f "$handoff" ] || die "missing .ship-route-exit-handoff.env"
  [ ! -L "$handoff" ] || die "refusing symlinked handoff env"
  next_action=$(read_env_key NEXT_ACTION "$handoff")
  [ "$next_action" = "assessments" ] || die "NEXT_ACTION must be assessments"
  detail=$(read_env_key DETAIL "$handoff")
  detail_file=$(read_env_key DETAIL_FILE "$handoff")
  raw=$detail
  if [ -z "$raw" ] && [ -n "$detail_file" ]; then
    safe_path_under_tmpdir "$detail_file" || die "DETAIL_FILE unsafe or missing"
    raw=$(tr -d '\r' <"$detail_file" | tr '\n' ',' | sed 's/,$//')
  fi
  [ -n "$raw" ] || die "empty assessment kind list"
  seen=""
  rest=$raw
  REQUESTED_RAW=""
  while [ -n "$rest" ]; do
    case "$rest" in
      *,*)
        token=${rest%%,*}
        rest=${rest#*,}
        ;;
      *)
        token=$rest
        rest=""
        ;;
    esac
    token=$(printf '%s' "$token" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "$token" ] || die "empty assessment kind token"
    case "$token" in
      invariants|guidelines) ;;
      *) die "unsupported assessment kind: $token" ;;
    esac
    case ",$seen," in
      *",$token,"*) die "duplicate assessment kind: $token" ;;
    esac
    seen="${seen}${seen:+,}${token}"
    REQUESTED_RAW="${REQUESTED_RAW}${REQUESTED_RAW:+,}${token}"
  done
  [ -n "$REQUESTED_RAW" ] || die "empty assessment kind list after parse"
}

compute_launch_identity() {
  local out
  export ASSESSMENT_RAW_KINDS="$REQUESTED_RAW"
  export REPO_ROOT
  out=$(python3 <<'PY'
import hashlib
import os
import sys
from pathlib import Path

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
from larch.implement.architectural_assessment import normalize_kinds, validate_materialization

raw = [part for part in os.environ["ASSESSMENT_RAW_KINDS"].split(",") if part]
try:
    kinds = normalize_kinds(raw)
except ValueError as exc:
    print(f"ASSESSMENT_ERROR={exc}", file=sys.stderr)
    raise SystemExit(2)
repo = Path(os.environ["REPO_ROOT"])
tmpdir = Path(os.environ["IMPLEMENT_TMPDIR"])
lines = []
for kind in kinds:
    try:
        evidence = validate_materialization(kind=kind, repo_root=repo, implement_tmpdir=tmpdir)
    except (OSError, TypeError, ValueError) as exc:
        print(f"ASSESSMENT_ERROR={exc}", file=sys.stderr)
        raise SystemExit(2)
    lines.append(f"{kind}|{evidence.head_sha}|{evidence.base_ref}|{evidence.diff_fingerprint}")
preimage = "\n".join(lines)
digest = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
print(f"ASSESSMENT_REQUESTED_KINDS={','.join(kinds)}")
print(f"ASSESSMENT_COVERED_FINGERPRINT={digest}")
PY
  ) || die "launch identity computation failed"
  ASSESSMENT_REQUESTED_KINDS=$(printf '%s\n' "$out" | sed -n 's/^ASSESSMENT_REQUESTED_KINDS=//p' | tail -n 1)
  ASSESSMENT_COVERED_FINGERPRINT=$(printf '%s\n' "$out" | sed -n 's/^ASSESSMENT_COVERED_FINGERPRINT=//p' | tail -n 1)
  [ -n "$ASSESSMENT_REQUESTED_KINDS" ] || die "missing ASSESSMENT_REQUESTED_KINDS"
  case "$ASSESSMENT_COVERED_FINGERPRINT" in
    *[!0-9a-f]*|'') die "invalid ASSESSMENT_COVERED_FINGERPRINT" ;;
  esac
  [ "${#ASSESSMENT_COVERED_FINGERPRINT}" -eq 64 ] || die "ASSESSMENT_COVERED_FINGERPRINT must be 64 hex chars"
}

registry_inspect() {
  python3 <<'PY'
from pathlib import Path
import os
import sys

plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
try:
    from larch.bgjob import registry  # noqa: E402

    path, entry = registry.read_for(tmpdir=Path(os.environ["IMPLEMENT_TMPDIR"]), step="implement-step8-assessment")
    if entry is None:
        print("REGISTRY_STATE=absent")
        raise SystemExit(0)
    live = registry.child_liveness(entry).live or registry.daemon_liveness(entry).live
    if live:
        print("REGISTRY_STATE=live")
        raise SystemExit(0)
    print("REGISTRY_STATE=dead")
    print(f"REGISTRY_PATH={path}")
    raise SystemExit(0)
except SystemExit:
    raise
except Exception as exc:
    print(f"ASSESSMENT_ERROR=registry-check-failed:{exc}", file=sys.stderr)
    raise SystemExit(2)
PY
}

read_identity_from_env() {
  local file=$1
  local kinds fp attempt status results
  kinds=$(read_env_key ASSESSMENT_REQUESTED_KINDS "$file")
  fp=$(read_env_key ASSESSMENT_COVERED_FINGERPRINT "$file")
  attempt=$(read_env_key ASSESSMENT_ATTEMPT "$file")
  status=$(read_env_key ASSESSMENT_STATUS "$file")
  results=$(read_env_key ASSESSMENT_RESULTS "$file")
  ENV_KINDS=$kinds
  ENV_FP=$fp
  ENV_ATTEMPT=$attempt
  ENV_STATUS=$status
  ENV_RESULTS=$results
}

identity_matches() {
  [ "${1:-}" = "$ASSESSMENT_REQUESTED_KINDS" ] && [ "${2:-}" = "$ASSESSMENT_COVERED_FINGERPRINT" ]
}

validate_results_coverage() {
  local results=$1
  local kinds=$2
  python3 - "$results" "$kinds" <<'PY'
import sys
results = sys.argv[1]
kinds = [k for k in sys.argv[2].split(",") if k]
if not results:
    raise SystemExit(1)
tokens = results.split(",")
seen = []
for token in tokens:
    if ":" not in token:
        raise SystemExit(1)
    kind, state = token.split(":", 1)
    if kind in seen:
        raise SystemExit(1)
    seen.append(kind)
    if state not in {
        "deterministic-clean",
        "handled",
        "clean",
        "deviation",
        "violation",
        "log-pending",
        "unavailable",
        "re-author-required",
    }:
        raise SystemExit(1)
if seen != kinds:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

result_env_path() {
  printf '%s\n' "$IMPLEMENT_TMPDIR/bgjob/$STEP.result.env"
}

merge_env_path() {
  printf '%s\n' "$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
}

clear_stale_state() {
  local result_env merge_env
  result_env=$(result_env_path)
  merge_env=$(merge_env_path)
  safe_unlink "$result_env"
  safe_unlink "$merge_env"
  [ ! -e "$result_env" ] && [ ! -L "$result_env" ] || die "stale result env remains"
  [ ! -e "$merge_env" ] && [ ! -L "$merge_env" ] || die "stale merge env remains"
  : >"$merge_env" || die "failed creating fresh merge env"
  chmod 0600 "$merge_env" 2>/dev/null || true
  safe_regular_path_under_tmpdir "$merge_env" || die "unsafe fresh merge env"
  MERGE_RESULT_ENV=$merge_env
}

seed_merge_for_attempt() {
  local attempt=$1
  local status=""
  MERGE_RESULT_ENV=$(merge_env_path)
  if [ "$attempt" = "2" ]; then
    status=fail-closed
    write_merge_kvs "$MERGE_RESULT_ENV" \
      ASSESSMENT_REQUESTED_KINDS "$ASSESSMENT_REQUESTED_KINDS" \
      ASSESSMENT_COVERED_FINGERPRINT "$ASSESSMENT_COVERED_FINGERPRINT" \
      ASSESSMENT_ATTEMPT "$attempt" \
      ASSESSMENT_STATUS "$status"
  else
    write_merge_kvs "$MERGE_RESULT_ENV" \
      ASSESSMENT_REQUESTED_KINDS "$ASSESSMENT_REQUESTED_KINDS" \
      ASSESSMENT_COVERED_FINGERPRINT "$ASSESSMENT_COVERED_FINGERPRINT" \
      ASSESSMENT_ATTEMPT "$attempt"
  fi
}

start_bgjob_child() {
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s "$BUDGET_S" \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    -- \
    bash "$SCRIPT_DIR/step-8-assessment.sh" \
    --bgjob-child \
    --merge-result-env "$MERGE_RESULT_ENV"
}

print_started_once() {
  local line=$1
  if [ "$STARTED_PRINTED" = false ]; then
    printf '%s\n' "$line"
    STARTED_PRINTED=true
  fi
}

wait_probe_zero() {
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --max-wait-s 0
}

wait_until_terminal() {
  local out
  while true; do
    set +e
    out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
      --step "$STEP" \
      --tmpdir "$IMPLEMENT_TMPDIR" \
      --max-wait-s "$WAIT_CHUNK_S")
    set -e
    case "$out" in
      *BGJOB_STATUS=WAIT*)
        continue
        ;;
      *)
        printf '%s\n' "$out"
        return 0
        ;;
    esac
  done
}

extract_kv() {
  local key=$1 text=$2
  printf '%s\n' "$text" | tr ' ' '\n' | sed -n "s/^${key}=//p" | tail -n 1
}

load_terminal_envelope() {
  local wait_out=$1
  local result_env
  result_env=$(result_env_path)
  WAIT_OUT=$wait_out
  TERM_BGJOB_STATUS=$(extract_kv BGJOB_STATUS "$wait_out")
  TERM_BGJOB_RC=$(extract_kv BGJOB_RC "$wait_out")
  if [ -f "$result_env" ] && [ ! -L "$result_env" ]; then
    [ -z "$TERM_BGJOB_RC" ] && TERM_BGJOB_RC=$(read_env_key BGJOB_RC "$result_env")
    TERM_STEP=$(read_env_key STEP "$result_env")
    TERM_KINDS=$(read_env_key ASSESSMENT_REQUESTED_KINDS "$result_env")
    TERM_FP=$(read_env_key ASSESSMENT_COVERED_FINGERPRINT "$result_env")
    TERM_STATUS=$(read_env_key ASSESSMENT_STATUS "$result_env")
    TERM_ATTEMPT=$(read_env_key ASSESSMENT_ATTEMPT "$result_env")
    TERM_RESULTS=$(read_env_key ASSESSMENT_RESULTS "$result_env")
  else
    TERM_STEP=$(extract_kv STEP "$wait_out")
    TERM_KINDS=$(extract_kv ASSESSMENT_REQUESTED_KINDS "$wait_out")
    TERM_FP=$(extract_kv ASSESSMENT_COVERED_FINGERPRINT "$wait_out")
    TERM_STATUS=$(extract_kv ASSESSMENT_STATUS "$wait_out")
    TERM_ATTEMPT=$(extract_kv ASSESSMENT_ATTEMPT "$wait_out")
    TERM_RESULTS=$(extract_kv ASSESSMENT_RESULTS "$wait_out")
  fi
  [ -n "$TERM_STEP" ] || TERM_STEP=$(extract_kv STEP "$wait_out")
}

emit_terminal_stdout() {
  local result_env
  result_env=$(result_env_path)
  if [ -f "$result_env" ] && [ ! -L "$result_env" ]; then
    # Prefer canonical result env rows; keep wait status line first when present.
    if [ -n "${TERM_BGJOB_STATUS:-}" ]; then
      printf 'BGJOB_STATUS=%s\n' "$TERM_BGJOB_STATUS"
    fi
    if [ -n "${TERM_BGJOB_RC:-}" ]; then
      printf 'BGJOB_RC=%s\n' "$TERM_BGJOB_RC"
    fi
    printf 'STEP=%s\n' "$STEP"
    printf 'ASSESSMENT_REQUESTED_KINDS=%s\n' "$(read_env_key ASSESSMENT_REQUESTED_KINDS "$result_env")"
    printf 'ASSESSMENT_COVERED_FINGERPRINT=%s\n' "$(read_env_key ASSESSMENT_COVERED_FINGERPRINT "$result_env")"
    printf 'ASSESSMENT_STATUS=%s\n' "$(read_env_key ASSESSMENT_STATUS "$result_env")"
    printf 'ASSESSMENT_ATTEMPT=%s\n' "$(read_env_key ASSESSMENT_ATTEMPT "$result_env")"
    results=$(read_env_key ASSESSMENT_RESULTS "$result_env")
    if [ -n "$results" ]; then
      printf 'ASSESSMENT_RESULTS=%s\n' "$results"
    fi
    return 0
  fi
  printf '%s\n' "$WAIT_OUT"
}

terminal_is_success() {
  [ "${TERM_BGJOB_STATUS:-}" = "DONE" ] || return 1
  [ "${TERM_STEP:-}" = "$STEP" ] || return 1
  identity_matches "${TERM_KINDS:-}" "${TERM_FP:-}" || return 1
  [ "${TERM_STATUS:-}" = "complete" ] || return 1
  case "${TERM_ATTEMPT:-}" in 1|2) ;; *) return 1 ;; esac
  [ "${TERM_BGJOB_RC:-}" = "0" ] || return 1
  validate_results_coverage "${TERM_RESULTS:-}" "$ASSESSMENT_REQUESTED_KINDS" || return 1
  return 0
}

terminal_is_reauthor_required() {
  [ "${TERM_BGJOB_STATUS:-}" = "DONE" ] || return 1
  [ "${TERM_STEP:-}" = "$STEP" ] || return 1
  identity_matches "${TERM_KINDS:-}" "${TERM_FP:-}" || return 1
  [ "${TERM_STATUS:-}" = "re-author-required" ] || return 1
  case "${TERM_ATTEMPT:-}" in 1|2) ;; *) return 1 ;; esac
  [ "${TERM_BGJOB_RC:-}" = "0" ] || return 1
  validate_results_coverage "${TERM_RESULTS:-}" "$ASSESSMENT_REQUESTED_KINDS" || return 1
  case ",${TERM_RESULTS:-}," in *:re-author-required,*) return 0 ;; *) return 1 ;; esac
}

terminal_is_fail_closed() {
  [ "${TERM_BGJOB_STATUS:-}" = "DONE" ] || return 1
  [ "${TERM_STEP:-}" = "$STEP" ] || return 1
  identity_matches "${TERM_KINDS:-}" "${TERM_FP:-}" || return 1
  [ "${TERM_STATUS:-}" = "fail-closed" ] || return 1
  [ "${TERM_ATTEMPT:-}" = "2" ] || return 1
  [ -n "${TERM_BGJOB_RC:-}" ] && [ "${TERM_BGJOB_RC:-}" != "0" ] || return 1
  return 0
}

terminal_retryable() {
  # Identity-matching attempt-1 failure that may be retried.
  identity_matches "${TERM_KINDS:-}" "${TERM_FP:-}" || return 1
  [ "${TERM_ATTEMPT:-}" = "1" ] || [ -z "${TERM_ATTEMPT:-}" ] || return 1
  if terminal_is_success; then
    return 1
  fi
  return 0
}

handle_terminal_outcome() {
  # Sets HANDLE_ACTION=emit-success|emit-fail-closed|retry|fresh-identity|error
  if terminal_is_success; then
    HANDLE_ACTION=emit-success
    return 0
  fi
  if terminal_is_reauthor_required; then
    HANDLE_ACTION=emit-reauthor
    return 0
  fi
  if terminal_is_fail_closed; then
    HANDLE_ACTION=emit-fail-closed
    return 0
  fi
  if { [ -n "${TERM_KINDS:-}" ] || [ -n "${TERM_FP:-}" ]; } && ! identity_matches "${TERM_KINDS:-}" "${TERM_FP:-}"; then
    # Inputs drifted relative to the finished job; recompute and restart.
    HANDLE_ACTION=fresh-identity
    return 0
  fi
  if [ "${TERM_ATTEMPT:-}" = "2" ]; then
    HANDLE_ACTION=emit-fail-closed
    return 0
  fi
  if [ -z "${TERM_KINDS:-}" ] && [ -z "${TERM_FP:-}" ] && { [ "${TERM_ATTEMPT:-}" = "1" ] || [ -z "${TERM_ATTEMPT:-}" ]; }; then
    HANDLE_ACTION=retry
    return 0
  fi
  if terminal_retryable; then
    HANDLE_ACTION=retry
    return 0
  fi
  HANDLE_ACTION=emit-fail-closed
}

run_wait_validate_path() {
  # Assumes a job is live or just started. Probe optional.
  local probe_first=$1
  local out
  if [ "$probe_first" = true ]; then
    set +e
    out=$(wait_probe_zero)
    set -e
    case "$out" in
      *BGJOB_STATUS=WAIT*)
        out=$(wait_until_terminal)
        ;;
      *BGJOB_STATUS=DONE*|*BGJOB_STATUS=DEAD*)
        :
        ;;
      *)
        out=$(wait_until_terminal)
        ;;
    esac
  else
    out=$(wait_until_terminal)
  fi
  load_terminal_envelope "$out"
  parse_requested_kinds
  compute_launch_identity
  handle_terminal_outcome
}

publish_fail_closed_terminal() {
  local attempt=${1:-2}
  local rc=${TERM_BGJOB_RC:-}
  local merge_env result_env
  merge_env=$(merge_env_path)
  result_env=$(result_env_path)
  write_merge_kvs "$merge_env" \
    ASSESSMENT_REQUESTED_KINDS "$ASSESSMENT_REQUESTED_KINDS" \
    ASSESSMENT_COVERED_FINGERPRINT "$ASSESSMENT_COVERED_FINGERPRINT" \
    ASSESSMENT_ATTEMPT "$attempt" \
    ASSESSMENT_STATUS "fail-closed"
  # Ensure result env carries fail-closed when daemon left incomplete rows.
  if [ -f "$result_env" ] && [ ! -L "$result_env" ]; then
    local existing_rc
    existing_rc=$(read_env_key BGJOB_RC "$result_env")
    [ -n "$existing_rc" ] && [ "$existing_rc" != "0" ] && rc=$existing_rc
  fi
  [ -n "$rc" ] && [ "$rc" != "0" ] || rc=1
  {
    printf 'BGJOB_RC=%s\n' "$rc"
    printf 'STEP=%s\n' "$STEP"
    printf 'ASSESSMENT_REQUESTED_KINDS=%s\n' "$ASSESSMENT_REQUESTED_KINDS"
    printf 'ASSESSMENT_COVERED_FINGERPRINT=%s\n' "$ASSESSMENT_COVERED_FINGERPRINT"
    printf 'ASSESSMENT_STATUS=fail-closed\n'
    printf 'ASSESSMENT_ATTEMPT=%s\n' "$attempt"
  } >"${result_env}.tmp" || die "failed writing fail-closed result"
  chmod 0600 "${result_env}.tmp" 2>/dev/null || true
  mv -f "${result_env}.tmp" "$result_env"
  TERM_BGJOB_STATUS=DONE
  TERM_BGJOB_RC=$rc
  WAIT_OUT=$(printf 'BGJOB_STATUS=DONE\nBGJOB_RC=%s\nSTEP=%s\n' "$rc" "$STEP")
  emit_terminal_stdout
}

run_child() {
  local kinds_csv attempt fp out status envelope_status results line status_seen results_seen
  [ -n "$MERGE_RESULT_ENV" ] || die "--merge-result-env is required in child mode"
  safe_regular_path_under_tmpdir "$MERGE_RESULT_ENV" || die "unsafe merge-result-env"
  kinds_csv=$(read_env_key ASSESSMENT_REQUESTED_KINDS "$MERGE_RESULT_ENV")
  attempt=$(read_env_key ASSESSMENT_ATTEMPT "$MERGE_RESULT_ENV")
  fp=$(read_env_key ASSESSMENT_COVERED_FINGERPRINT "$MERGE_RESULT_ENV")
  [ -n "$kinds_csv" ] || die "child missing ASSESSMENT_REQUESTED_KINDS"
  [ -n "$fp" ] || die "child missing ASSESSMENT_COVERED_FINGERPRINT"
  [ -n "$attempt" ] || attempt=1
  REPO_ROOT=$(resolve_repo_root)
  set --
  old_ifs=$IFS
  IFS=,
  # shellcheck disable=SC2086
  set -- $kinds_csv
  IFS=$old_ifs
  cmd=(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" architectural-assessment run
    --repo-root "$REPO_ROOT"
    --implement-tmpdir "$IMPLEMENT_TMPDIR")
  for kind in "$@"; do
    cmd+=(--kind "$kind")
  done
  set +e
  out=$("${cmd[@]}")
  child_rc=$?
  set -e
  status=""
  results=""
  status_seen=false
  results_seen=false
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ARCHITECTURAL_ASSESSMENT_STATUS=*)
        [ "$status_seen" = false ] || die "duplicate child status"
        status=${line#ARCHITECTURAL_ASSESSMENT_STATUS=}
        status_seen=true
        ;;
      ARCHITECTURAL_ASSESSMENT_RESULTS=*)
        [ "$results_seen" = false ] || die "duplicate child results"
        results=${line#ARCHITECTURAL_ASSESSMENT_RESULTS=}
        results_seen=true
        ;;
      *) die "malformed or unknown child stdout record" ;;
    esac
  done <<EOF
$out
EOF
  if [ "$child_rc" -ne 0 ] || [ "$status_seen" != true ] || [ "$results_seen" != true ] || { [ "$status" != "ok" ] && [ "$status" != "re-author-required" ]; }; then
    printf 'step-8-assessment.sh: child assessment failed status=%s rc=%s\n' "${status:-missing}" "$child_rc" >&2
    exit 1
  fi
  reject_nl "$results" || die "newline in assessment results"
  envelope_status=complete
  [ "$status" != "re-author-required" ] || envelope_status=re-author-required
  validate_results_coverage "$results" "$kinds_csv" || {
    printf 'step-8-assessment.sh: ASSESSMENT_RESULTS coverage mismatch\n' >&2
    exit 1
  }
  write_merge_kvs "$MERGE_RESULT_ENV" \
    ASSESSMENT_REQUESTED_KINDS "$kinds_csv" \
    ASSESSMENT_COVERED_FINGERPRINT "$fp" \
    ASSESSMENT_ATTEMPT "$attempt" \
    ASSESSMENT_STATUS "$envelope_status" \
    ASSESSMENT_RESULTS "$results"
  exit 0
}

# --- main ---
rehydrate_plugin_root
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$BGJOB_CHILD" = true ]; then
  run_child
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
  die "refusing symlinked bgjob directory"
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob"
RESULT_ENV=$(result_env_path)
MERGE_RESULT_ENV=$(merge_env_path)
if [ -L "$RESULT_ENV" ] || { [ -e "$RESULT_ENV" ] && [ ! -f "$RESULT_ENV" ]; }; then
  die "refusing invalid bgjob result env"
fi
if [ -L "$MERGE_RESULT_ENV" ] || { [ -e "$MERGE_RESULT_ENV" ] && [ ! -f "$MERGE_RESULT_ENV" ]; }; then
  die "refusing invalid merge-result env"
fi

REPO_ROOT=$(resolve_repo_root)
export REPO_ROOT
parse_requested_kinds
compute_launch_identity

set +e
reg_out=$(registry_inspect)
reg_rc=$?
set -e
[ "$reg_rc" -eq 0 ] || exit 2
REGISTRY_STATE=$(printf '%s\n' "$reg_out" | sed -n 's/^REGISTRY_STATE=//p' | tail -n 1)

if [ "$REGISTRY_STATE" = "live" ]; then
  read_identity_from_env "$MERGE_RESULT_ENV"
  if [ -z "${ENV_KINDS:-}" ] || [ -z "${ENV_FP:-}" ]; then
    read_identity_from_env "$RESULT_ENV"
  fi
  if [ -z "${ENV_KINDS:-}" ] || [ -z "${ENV_FP:-}" ]; then
    printf 'ASSESSMENT_ERROR=missing-launch-identity\n'
    exit 2
  fi
  if identity_matches "${ENV_KINDS:-}" "${ENV_FP:-}"; then
    run_wait_validate_path true
    case "$HANDLE_ACTION" in
      emit-success)
        emit_terminal_stdout
        exit 0
        ;;
      emit-reauthor)
        emit_terminal_stdout
        exit 0
        ;;
      emit-fail-closed)
        if [ "${TERM_STATUS:-}" = "fail-closed" ] && [ "${TERM_ATTEMPT:-}" = "2" ]; then
          emit_terminal_stdout
        else
          publish_fail_closed_terminal 2
        fi
        exit 0
        ;;
      retry)
        # Fall through to attempt-2 path below with CURRENT_ATTEMPT=2
        CURRENT_ATTEMPT=2
        clear_stale_state
        ;;
      fresh-identity)
        parse_requested_kinds
        compute_launch_identity
        CURRENT_ATTEMPT=1
        clear_stale_state
        ;;
      *)
        die "unexpected handle action after live rejoin: $HANDLE_ACTION"
        ;;
    esac
  else
    printf 'ASSESSMENT_ERROR=active-stale-identity-mismatch\n'
    exit 2
  fi
elif [ "$REGISTRY_STATE" = "dead" ]; then
  reg_path=$(printf '%s\n' "$reg_out" | sed -n 's/^REGISTRY_PATH=//p' | tail -n 1)
  if [ -n "$reg_path" ] && [ ! -L "$reg_path" ]; then
    rm -f "$reg_path" || die "failed removing stale bgjob registry"
    [ ! -e "$reg_path" ] && [ ! -L "$reg_path" ] || die "stale bgjob registry remains after cleanup"
  fi
fi

# Completed rejoin (no live registry).
if [ "${CURRENT_ATTEMPT:-}" = "" ]; then
  if [ -f "$RESULT_ENV" ] && [ ! -L "$RESULT_ENV" ]; then
    read_identity_from_env "$RESULT_ENV"
    if identity_matches "${ENV_KINDS:-}" "${ENV_FP:-}"; then
      run_wait_validate_path true
      case "$HANDLE_ACTION" in
        emit-success)
          emit_terminal_stdout
          exit 0
          ;;
        emit-reauthor)
        emit_terminal_stdout
        exit 0
        ;;
      emit-fail-closed)
          if terminal_is_fail_closed; then
            emit_terminal_stdout
          else
            publish_fail_closed_terminal 2
          fi
          exit 0
          ;;
        retry)
          CURRENT_ATTEMPT=2
          clear_stale_state
          ;;
        fresh-identity)
          CURRENT_ATTEMPT=1
          clear_stale_state
          ;;
        *)
          publish_fail_closed_terminal 2
          exit 0
          ;;
      esac
    else
      # Stale completed envelope for different identity.
      clear_stale_state
    fi
  fi
fi

# Fresh attempt loop (attempt 1, optional in-invocation attempt 2).
CURRENT_ATTEMPT=${CURRENT_ATTEMPT:-1}
while :; do
  if [ "$CURRENT_ATTEMPT" -gt 2 ]; then
    die "attempt 3 is forbidden"
  fi
  # Recompute identity before each attempt so input drift restarts at attempt 1.
  PRIOR_KINDS=$ASSESSMENT_REQUESTED_KINDS
  PRIOR_FP=$ASSESSMENT_COVERED_FINGERPRINT
  parse_requested_kinds
  compute_launch_identity
  if [ "$CURRENT_ATTEMPT" = "2" ]; then
    if ! identity_matches "$PRIOR_KINDS" "$PRIOR_FP"; then
      CURRENT_ATTEMPT=1
    fi
  fi
  clear_stale_state
  seed_merge_for_attempt "$CURRENT_ATTEMPT"
  set +e
  start_out=$(start_bgjob_child)
  start_rc=$?
  set -e
  [ "$start_rc" -eq 0 ] || die "bgjob start failed"
  print_started_once "$start_out"
  run_wait_validate_path false
  case "$HANDLE_ACTION" in
    emit-success)
      emit_terminal_stdout
      exit 0
      ;;
    emit-fail-closed)
      if [ "${TERM_STATUS:-}" = "fail-closed" ] && [ "${TERM_ATTEMPT:-}" = "2" ]; then
        emit_terminal_stdout
      else
        publish_fail_closed_terminal 2
      fi
      exit 0
      ;;
    retry)
      if [ "$CURRENT_ATTEMPT" = "1" ]; then
        CURRENT_ATTEMPT=2
        continue
      fi
      publish_fail_closed_terminal 2
      exit 0
      ;;
    fresh-identity)
      CURRENT_ATTEMPT=1
      continue
      ;;
    *)
      if [ "$CURRENT_ATTEMPT" = "1" ]; then
        CURRENT_ATTEMPT=2
        continue
      fi
      publish_fail_closed_terminal 2
      exit 0
      ;;
  esac
done
