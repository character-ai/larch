#!/bin/bash
# Regression test for check-reviewers.sh probe acceptance logic.
# Tests the case-insensitive exact-match rule: after whitespace strip + lowercase,
# the probe reply must equal exactly "ok". Rejects substrings like "token", "broken".
#
# Wired into: make test-harnesses
# Exit codes: 0 all pass, 1 any failure

set -euo pipefail

# Tighten run-external-agent.sh's poll cadence so each Gemini-probe stub does
# not pay a 10s sleep cycle. Production probes (real Gemini) inherit the
# default 10s. See scripts/run-external-agent.md.
export RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05
# wait-for-reviewers.sh polls sentinel-files every 5s by default; that becomes
# the floor when the run-external-agent.sh polling above is already sub-second.
# Drop it to 0.05s for stub-binary tests.
export WAIT_FOR_REVIEWERS_POLL_INTERVAL=0.05
# lib-gemini-tool-drift.sh's slash-command discovery has a 5s default watchdog
# for the live `gemini /tools` call. The "hung" stub case below exercises that
# watchdog deliberately (single test); shrinking the watchdog to 1s is safe
# because the non-hung gemini stub completes printf-instantly. Production
# callers (real Gemini) inherit the 5s default. See scripts/lib-gemini-tool-drift.md.
export LARCH_GEMINI_TOOL_DISCOVERY_TIMEOUT=1

FAIL=0

fail() {
    echo "FAIL: $1" >&2
    FAIL=1
}

# Simulate the normalization pipeline from check-reviewers.sh:
# tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'
normalize_and_check() {
    local input="$1"
    local reply
    reply=$(printf '%s' "$input" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
    if [[ "$reply" == "ok" ]]; then
        echo "healthy"
    else
        echo "unhealthy"
    fi
}

# --- Should be healthy ---
check_healthy() {
    local label="$1" input="$2"
    local result
    result=$(normalize_and_check "$input")
    if [[ "$result" != "healthy" ]]; then
        fail "Expected healthy for '$label', got unhealthy"
    fi
}

# --- Should be unhealthy ---
check_unhealthy() {
    local label="$1" input="$2"
    local result
    result=$(normalize_and_check "$input")
    if [[ "$result" != "unhealthy" ]]; then
        fail "Expected unhealthy for '$label', got healthy"
    fi
}

# Positive cases (should pass probe)
check_healthy "exact OK"          "OK"
check_healthy "lowercase ok"      "ok"
check_healthy "mixed case Ok"     "Ok"
check_healthy "mixed case oK"     "oK"
check_healthy "with whitespace"   "  OK  "
check_healthy "with newline"      "OK
"
check_healthy "with tab"          "$(printf 'OK\t')"

# Negative cases (should fail probe)
check_unhealthy "empty"                  ""
check_unhealthy "token"                  "token"
check_unhealthy "broken"                 "broken"
check_unhealthy "NotOK"                  "NotOK"
check_unhealthy "OK with suffix"         "OK sure"
check_unhealthy "Sure OK"               "Sure OK"
check_unhealthy "error with ok substr"   "Please look at the docs"
check_unhealthy "wok"                    "wok"
check_unhealthy "okay"                   "okay"
check_unhealthy "OK."                    "OK."
check_unhealthy "auth error"             "Error: Password not found for account"
check_unhealthy "thinking prefix"        "Thinking about this... OK"

# Gemini probe integration: stub gemini JSON stdout and let check-reviewers.sh
# exercise run-external-agent.sh + jq .response extraction.
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
TMPDIR=$(mktemp -d /tmp/larch-test-check-reviewers-XXXXXX)
trap 'rm -rf "$TMPDIR"' EXIT
STUB_BIN="$TMPDIR/bin"
mkdir -p "$STUB_BIN"

STUB_PROBE_PID_LOG="$TMPDIR/probe-pids.log"
cat > "$STUB_BIN/codex" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$\$" >> "$STUB_PROBE_PID_LOG"
sleep 30
STUB
chmod +x "$STUB_BIN/codex"

cat > "$STUB_BIN/cursor" <<STUB
#!/usr/bin/env bash
printf '%s\n' "\$\$" >> "$STUB_PROBE_PID_LOG"
sleep 30
STUB
chmod +x "$STUB_BIN/cursor"

set +e
PATH="$STUB_BIN:$PATH" LARCH_TEST_PROBE_SLEEP_SECONDS=0 WAIT_FOR_REVIEWERS_POLL_INTERVAL=00 \
  "$REPO_ROOT/scripts/check-reviewers.sh" --probe >"$TMPDIR/infra.stdout" 2>"$TMPDIR/infra.stderr"
infra_code=$?
set -e
[[ "$infra_code" -eq 0 ]] \
  || fail "Expected probe infrastructure error path to exit 0, got $infra_code"
infra_stdout=$(cat "$TMPDIR/infra.stdout")
grep -q '^WAIT_INFRA_ERROR=' <<< "$infra_stdout" \
  || fail "Expected WAIT_INFRA_ERROR on wait preflight failure"
grep -q '^CODEX_HEALTHY=false$' <<< "$infra_stdout" \
  || fail "Expected CODEX_HEALTHY=false fail-closed value on wait preflight failure"
grep -q '^CURSOR_HEALTHY=false$' <<< "$infra_stdout" \
  || fail "Expected CURSOR_HEALTHY=false fail-closed value on wait preflight failure"
grep -q 'Probe infrastructure error:' "$TMPDIR/infra.stderr" \
  || fail "Expected probe infrastructure diagnostic on stderr"
if grep -q 'Retrying failed health probes (attempt 2 of 3' "$TMPDIR/infra.stderr"; then
  fail "Expected wait preflight failure to skip retry attempts"
fi
if [[ -s "$STUB_PROBE_PID_LOG" ]]; then
  fail "Expected wait preflight failure to launch no sleeping probe wrappers"
fi

PROBE_ARGV_LOG="$TMPDIR/gemini-probe-argv.log"
cat > "$STUB_BIN/gemini" <<STUB
#!/usr/bin/env bash
if [[ "\${1:-}" == "/tools" ]]; then
  case "\${GEMINI_TOOLS_MODE:-fixture}" in
    fixture)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content web_fetch web_search write_file
      ;;
    benign)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content tool_search web_fetch web_search write_file
      ;;
    write)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content super_write_v2 web_fetch web_search write_file
      ;;
    write_uppercase)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content web_fetch web_search WRITE_FILE
      ;;
    write_mixed)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content web_fetch web_search write_File
      ;;
    write_hyphen)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content write-file web_fetch web_search write_file
      ;;
    write_dot)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content file.write web_fetch web_search write_file
      ;;
    write_camel)
      printf '%s\n' delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content fileWrite web_fetch web_search write_file
      ;;
    writer_substring)
      printf '%s\n' delete_file edit edit_file metadata_writer_index read_file read_many_files replace run_shell_command search_file_content web_fetch web_search write_file
      ;;
    empty)
      :
      ;;
    hung)
      sleep 30
      ;;
  esac
  exit 0
fi
# Record argv to \$PROBE_ARGV_LOG (one element per line, --- between invocations)
# so the harness can pin the probe approval-mode value.
{
  for _arg in "\$@"; do
    printf '%s\n' "\$_arg"
  done
  printf -- '---\n'
} >> "$PROBE_ARGV_LOG"
case "\${GEMINI_STUB_MODE:-ok}" in
  ok) printf '{"response":"OK"}\n' ;;
  error) printf '{"error":"auth failed"}\n' ;;
  verbose) printf '{"response":"Thinking... OK"}\n' ;;
esac
STUB
chmod +x "$STUB_BIN/gemini"

run_gemini_probe() {
    local artifact_dir="${1:-$TMPDIR/gemini-artifacts-default}"
    shift || true
    PATH="$STUB_BIN:$PATH" LARCH_TEST_PROBE_SLEEP_SECONDS=0 \
      "$REPO_ROOT/scripts/check-reviewers.sh" --probe --include-gemini --skip-codex-probe --skip-cursor-probe --artifact-dir "$artifact_dir" "$@"
}

write_fixture() {
    local path="$1"
    shift
    local body="$path.body"
    printf '%s\n' "$@" > "$body"
    local checksum
    if command -v shasum >/dev/null 2>&1; then
        checksum=$(shasum -a 256 < "$body" | awk '{print $1}')
    else
        checksum=$(sha256sum < "$body" | awk '{print $1}')
    fi
    {
        echo "# checksum: $checksum"
        echo "# Refreshed: test fixture"
        cat "$body"
    } > "$path"
}

write_bad_fixture() {
    local path="$1"
    shift
    {
        echo "# checksum: bad"
        echo "# Refreshed: test fixture"
        printf '%s\n' "$@"
    } > "$path"
}

probe_output=$(WAIT_FOR_REVIEWERS_POLL_INTERVAL='key=value' GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-infra-error")
grep -q "^WAIT_INFRA_ERROR=.*key=value" <<< "$probe_output" \
  || fail "Expected WAIT_INFRA_ERROR value-side equals to survive"
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false on wait infrastructure failure"
if grep -q '^GEMINI_TOOL_DRIFT_ARTIFACT=' <<< "$probe_output"; then
  fail "Expected Gemini drift check to stay unrun on wait infrastructure failure"
fi

probe_output=$(GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-ok")
grep -q '^GEMINI_AVAILABLE=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_AVAILABLE=true with stub gemini"
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true for JSON .response OK"
grep -q '^GEMINI_TOOL_DRIFT_ARTIFACT=' <<< "$probe_output" \
  || fail "Expected drift artifact key for clean Gemini probe"
grep -q 'status=no drift' "$TMPDIR/gemini-artifacts-ok/gemini-tool-drift.txt" \
  || fail "Expected clean drift artifact to record no drift"
if grep -q '^GEMINI_TOOL_DRIFT_WARNING=' <<< "$probe_output"; then
  fail "Expected no drift warning for clean known catalog"
fi

# Pin probe approval-mode to plan (least privilege). The reviewer launcher
# uses --approval-mode yolo (test-launch-gemini-review.sh pins that). Probe
# and reviewer use intentionally different modes; without this assertion a
# future edit could re-align them silently and re-introduce probe yolo.
PROBE_APPROVAL_MODE_VALUE=$(awk 'prev=="--approval-mode"{print; exit} {prev=$0}' "$PROBE_ARGV_LOG")
[[ "$PROBE_APPROVAL_MODE_VALUE" == "plan" ]] \
  || fail "Expected gemini probe argv to include --approval-mode plan, got '$PROBE_APPROVAL_MODE_VALUE'"

probe_output=$(GEMINI_STUB_MODE=error run_gemini_probe "$TMPDIR/gemini-artifacts-error")
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false for JSON .error"
grep -q '^GEMINI_PROBE_ERROR=.*Gemini error' <<< "$probe_output" \
  || fail "Expected GEMINI_PROBE_ERROR for JSON .error"

probe_output=$(LARCH_TEST_FORCE_MISSING_JQ=true GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-missing-jq")
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false when jq is missing"
grep -q '^GEMINI_PROBE_ERROR=MISSING_JQ' <<< "$probe_output" \
  || fail "Expected MISSING_JQ diagnostic when jq is missing"

probe_output=$(GEMINI_TOOLS_MODE=benign GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-benign")
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true for benign unknown tool"
grep -q "^GEMINI_TOOL_DRIFT_WARNING=unknown tool 'tool_search' not in deny list$" <<< "$probe_output" \
  || fail "Expected drift warning for benign unknown tool"

probe_output=$(GEMINI_TOOLS_MODE=write GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-write")
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false for unknown write-style tool"
grep -q '^GEMINI_PROBE_ERROR=.*write-style tool(s) \[super_write_v2\] not in deny list' <<< "$probe_output" \
  || fail "Expected write-style drift probe error"

for raw_case in \
  "write_uppercase|WRITE_FILE" \
  "write_mixed|write_File"; do
  IFS='|' read -r mode tool_name <<< "$raw_case"
  probe_output=$(GEMINI_TOOLS_MODE="$mode" GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-$mode")
  grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
    || fail "Expected GEMINI_HEALTHY=true for normalized denied write-style tool $tool_name"
  if grep -q "^GEMINI_TOOL_DRIFT_WARNING=unknown tool '$tool_name' not in deny list$" <<< "$probe_output"; then
    fail "Expected no raw unknown-tool warning for normalized denied write-style tool $tool_name"
  fi
  if grep -q "^GEMINI_PROBE_ERROR=.*$tool_name" <<< "$probe_output"; then
    fail "Expected no write-style drift probe error for normalized denied write-style tool $tool_name"
  fi
done

for raw_case in \
  "write_hyphen|write-file" \
  "write_dot|file.write" \
  "write_camel|fileWrite"; do
  IFS='|' read -r mode tool_name <<< "$raw_case"
  probe_output=$(GEMINI_TOOLS_MODE="$mode" GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-$mode")
  grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
    || fail "Expected GEMINI_HEALTHY=false for unknown write-style tool $tool_name"
  grep -q "^GEMINI_TOOL_DRIFT_WARNING=unknown tool '$tool_name' not in deny list$" <<< "$probe_output" \
    || fail "Expected raw unknown-tool warning for $tool_name"
  grep -q "GEMINI_PROBE_ERROR=.*$tool_name" <<< "$probe_output" \
    || fail "Expected write-style drift probe error for $tool_name"
done

probe_output=$(GEMINI_TOOLS_MODE=writer_substring GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-writer-substring")
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true for metadata_writer_index substring-only write token"
grep -q "^GEMINI_TOOL_DRIFT_WARNING=unknown tool 'metadata_writer_index' not in deny list$" <<< "$probe_output" \
  || fail "Expected unknown warning for metadata_writer_index"
if grep -q '^GEMINI_PROBE_ERROR=.*metadata_writer_index' <<< "$probe_output"; then
  fail "Expected metadata_writer_index not to trigger write-style probe error"
fi

probe_output=$(GEMINI_TOOLS_MODE=empty GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-empty")
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true when live discovery is unavailable"
grep -q 'status=discovery unavailable; fixture-only check passed' "$TMPDIR/gemini-artifacts-empty/gemini-tool-drift.txt" \
  || fail "Expected fixture-only artifact when live discovery is unavailable"

MALFORMED_POLICY="$TMPDIR/malformed-policy.toml"
printf '%s\n' '[[rule]]' 'toolName = ["read_file"]' > "$MALFORMED_POLICY"
probe_output=$(LARCH_TEST_GEMINI_POLICY_PATH="$MALFORMED_POLICY" GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-policy-fail")
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false when policy parser sanity fails"
grep -q '^GEMINI_PROBE_ERROR=.*policy parser produced unexpected output' <<< "$probe_output" \
  || fail "Expected policy parser failure diagnostic"

BAD_FIXTURE="$TMPDIR/bad-fixture.txt"
write_bad_fixture "$BAD_FIXTURE" delete_file edit edit_file read_file replace write_file
probe_output=$(LARCH_TEST_GEMINI_FIXTURE_PATH="$BAD_FIXTURE" GEMINI_TOOLS_MODE=empty GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-bad-fixture")
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true for checksum mismatch with deny-list-only fallback"
grep -q '^GEMINI_TOOL_DRIFT_WARNING=fixture checksum mismatch - fixture untrusted$' <<< "$probe_output" \
  || fail "Expected fixture checksum mismatch warning"

UNDENIED_FIXTURE="$TMPDIR/undenied-write-fixture.txt"
write_fixture "$UNDENIED_FIXTURE" delete_file edit edit_file read_file read_many_files replace run_shell_command search_file_content super_create_v2 web_fetch web_search write_file
probe_output=$(LARCH_TEST_GEMINI_FIXTURE_PATH="$UNDENIED_FIXTURE" GEMINI_TOOLS_MODE=empty GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-undenied-fixture")
grep -q '^GEMINI_HEALTHY=false$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=false for fixture-known write-style tool missing from deny list"
grep -q '^GEMINI_PROBE_ERROR=.*super_create_v2' <<< "$probe_output" \
  || fail "Expected fixture write-style drift diagnostic"

SECONDS=0
probe_output=$(GEMINI_TOOLS_MODE=hung GEMINI_STUB_MODE=ok run_gemini_probe "$TMPDIR/gemini-artifacts-hung")
hung_elapsed=$SECONDS
grep -q '^GEMINI_HEALTHY=true$' <<< "$probe_output" \
  || fail "Expected GEMINI_HEALTHY=true when hung discovery falls back to fixture"
grep -q 'status=discovery unavailable; fixture-only check passed' "$TMPDIR/gemini-artifacts-hung/gemini-tool-drift.txt" \
  || fail "Expected fixture fallback artifact for hung discovery"
if (( hung_elapsed > 10 )); then
  fail "Expected hung discovery to return within 10s, took ${hung_elapsed}s"
fi

if [[ "$FAIL" -eq 1 ]]; then
    echo "FAIL: test-check-reviewers.sh — some probe acceptance tests failed" >&2
    exit 1
fi

echo "PASS: test-check-reviewers.sh — all probe acceptance tests passed"
exit 0
