#!/usr/bin/env bash
# Regression harness for cache-key-runtime-audit.py transcript classification.
set -euo pipefail
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0
TMPDIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

pass() {
  PASS=$((PASS + 1))
  printf 'PASS: %s\n' "$1"
}

fail() {
  FAIL=$((FAIL + 1))
  printf 'FAIL: %s\n' "$1" >&2
}

assert_contains() {
  local name="$1"
  local haystack="$2"
  local needle="$3"

  if [[ "$haystack" == *"$needle"* ]]; then
    pass "$name"
  else
    fail "$name"
    printf '  expected output to contain: %s\n' "$needle" >&2
  fi
}

write_baseline_fixture() {
  local root="$1"
  mkdir -p "$root/run1"
  cat >"$root/run1/session-transcript.jsonl" <<'JSONL'
{"type":"system","uuid":"sys1","parentUuid":null,"subtype":"init","message":{"content":"system prompt"}}
{"type":"user","uuid":"usr1","parentUuid":"sys1","message":{"content":"initial request"}}
{"type":"assistant","uuid":"ast1","parentUuid":"usr1","requestId":"req1","message":{"content":"assistant response"}}
JSONL
}

write_expected_growth_fixture() {
  local root="$1"
  mkdir -p "$root/run1"
  cat >"$root/run1/session-transcript.jsonl" <<'JSONL'
{"type":"system","uuid":"sys1","parentUuid":null,"subtype":"init","message":{"content":"system prompt"}}
{"type":"user","uuid":"usr1","parentUuid":"sys1","message":{"content":"initial request"}}
{"type":"assistant","uuid":"ast1","parentUuid":"usr1","requestId":"req1","message":{"content":"assistant response one"}}
{"type":"user","uuid":"usr2","parentUuid":"ast1","message":{"content":"follow-up request"}}
{"type":"assistant","uuid":"ast2","parentUuid":"usr2","requestId":"req2","message":{"content":"assistant response two"}}
JSONL
}

write_cache_invalidating_fixture() {
  local root="$1"
  mkdir -p "$root/run1"
  cat >"$root/run1/session-transcript.jsonl" <<'JSONL'
{"type":"system","uuid":"sys1","parentUuid":null,"subtype":"init","message":{"content":"system prompt"}}
{"type":"user","uuid":"usr1","parentUuid":"sys1","message":{"content":"initial request"}}
{"type":"assistant","uuid":"ast1","parentUuid":"usr1","requestId":"req1","message":{"content":"assistant response one"}}
{"type":"user","uuid":"usr3","parentUuid":"sys1","message":{"content":"changed initial request"}}
{"type":"assistant","uuid":"ast2","parentUuid":"usr3","requestId":"req2","message":{"content":"assistant response two"}}
JSONL
}

run_audit() {
  local root="$1"

  python3 "$REPO_ROOT/scripts/cache-key-runtime-audit.py" --log-root "$root" --runs 1
}

classification_sequence() {
  local transcript="$1"

  python3 - "$REPO_ROOT/scripts/cache-key-runtime-audit.py" "$transcript" <<'PY'
import importlib.util
import pathlib
import sys

script = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("cache_key_runtime_audit", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)
audit = module.audit_run(pathlib.Path(sys.argv[2]), 2000)
print(",".join(turn.classification for turn in audit.turns))
PY
}

baseline_root="$TMPDIR/baseline"
growth_root="$TMPDIR/expected-growth"
invalidating_root="$TMPDIR/cache-invalidating"

write_baseline_fixture "$baseline_root"
write_expected_growth_fixture "$growth_root"
write_cache_invalidating_fixture "$invalidating_root"

baseline_output="$(run_audit "$baseline_root")"
assert_contains "baseline report includes one assistant request" "$baseline_output" "- Assistant API requests: 1"
assert_contains "baseline report has no findings" "$baseline_output" "No cache-invalidating or expected-change findings."
if [[ "$(classification_sequence "$baseline_root/run1/session-transcript.jsonl")" == "BASELINE" ]]; then
  pass "baseline classification sequence"
else
  fail "baseline classification sequence"
fi

growth_output="$(run_audit "$growth_root")"
assert_contains "expected-growth report includes one comparison" "$growth_output" "- Turn-to-turn comparisons: 1"
assert_contains "expected-growth report stays cache-efficient" "$growth_output" "- Cache-efficient comparisons: 100.0%"
if [[ "$(classification_sequence "$growth_root/run1/session-transcript.jsonl")" == "BASELINE,EXPECTED-GROWTH" ]]; then
  pass "expected-growth classification sequence"
else
  fail "expected-growth classification sequence"
fi

invalidating_output="$(run_audit "$invalidating_root")"
assert_contains "cache-invalidating report counts finding" "$invalidating_output" "- CACHE-INVALIDATING findings: 1"
assert_contains "cache-invalidating report renders finding" "$invalidating_output" "### Turn 2: CACHE-INVALIDATING"
if [[ "$(classification_sequence "$invalidating_root/run1/session-transcript.jsonl")" == "BASELINE,CACHE-INVALIDATING" ]]; then
  pass "cache-invalidating classification sequence"
else
  fail "cache-invalidating classification sequence"
fi

missing_root="$TMPDIR/does-not-exist"
missing_output="$(
  set +e
  python3 "$REPO_ROOT/scripts/cache-key-runtime-audit.py" --log-root "$missing_root" --runs 1 2>&1
  printf 'exit:%d\n' "$?"
)"
assert_contains "missing log root exits 2" "$missing_output" "exit:2"
assert_contains "missing log root reports error" "$missing_output" "cache-key-runtime-audit: log root not found:"

if (( FAIL > 0 )); then
  printf '\n%s cache-key-runtime-audit harness failure(s); %s passed.\n' "$FAIL" "$PASS" >&2
  exit 1
fi

printf 'PASS: cache-key-runtime-audit harness (%d tests)\n' "$PASS"
