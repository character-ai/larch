#!/usr/bin/env bash
# test-tracking-issue-write.sh — regression harness for tracking-issue-write.sh.

set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WRITE="$REPO_ROOT/scripts/tracking-issue-write.sh"

[ -x "$WRITE" ] || { echo "FAIL: $WRITE not executable" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-tracking-issue-write.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

ORIG_PATH="$PATH"
BODY_CAPTURE="$TMP/body.txt"
TITLE_CAPTURE="$TMP/title.txt"
export BODY_CAPTURE TITLE_CAPTURE

stub="$TMP/stub"
mkdir -p "$stub"
cat > "$stub/gh" <<'GHSTUB'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then
    echo "owner/repo"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
    for ((i=1; i<=$#; i++)); do
        if [ "${!i}" = "--body-file" ]; then
            next=$((i + 1))
            cp "${!next}" "$BODY_CAPTURE"
        fi
    done
    echo "https://github.com/owner/repo/issues/42"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "comment" ]; then
    for ((i=1; i<=$#; i++)); do
        if [ "${!i}" = "--body-file" ]; then
            next=$((i + 1))
            cp "${!next}" "$BODY_CAPTURE"
        fi
    done
    echo "https://github.com/owner/repo/issues/42#issuecomment-7001"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[IN PROGRESS] Existing title"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "edit" ]; then
    for ((i=1; i<=$#; i++)); do
        if [ "${!i}" = "--title" ]; then
            next=$((i + 1))
            printf '%s' "${!next}" > "$TITLE_CAPTURE"
        fi
    done
    exit 0
fi
exit 1
GHSTUB
chmod +x "$stub/gh"
export PATH="$stub:$ORIG_PATH"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

token='sk-ant-abcdefghijklmnopqrstuvwxyz0123456789ABCD'

echo "=== create-issue redacts body ==="
body="$TMP/create.md"
printf 'body %s\n' "$token" > "$body"
out="$("$WRITE" create-issue --title "Title $token" --body-file "$body" --repo owner/repo)"
[[ "$out" == *"ISSUE_NUMBER=42"* ]] || fail "create ISSUE_NUMBER missing: $out"
grep -q '<REDACTED-TOKEN>' "$BODY_CAPTURE" || fail "create body not redacted"

echo "=== append-comment lifecycle marker ==="
printf 'comment\n' > "$body"
out="$("$WRITE" append-comment --issue 42 --body-file "$body" --lifecycle-marker pr-opened --repo owner/repo)"
[[ "$out" == *"COMMENT_ID=7001"* ]] || fail "append COMMENT_ID missing: $out"
grep -q '^<!-- larch:lifecycle-marker:pr-opened -->$' "$BODY_CAPTURE" || fail "lifecycle marker missing"

echo "=== lifecycle marker rejects comment terminator ==="
set +e
bad="$("$WRITE" append-comment --issue 42 --body-file "$body" --lifecycle-marker 'bad--marker' --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "bad lifecycle exit $rc"
[[ "$bad" == *"contains the substring '--'"* ]] || fail "bad lifecycle error missing: $bad"

echo "=== rename updates lifecycle prefix ==="
out="$("$WRITE" rename --issue 42 --state "done" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "rename RENAMED missing: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[DONE] Existing title" ] || fail "rename title was $(cat "$TITLE_CAPTURE")"

echo "=== removed anchor subcommands are rejected ==="
set +e
removed="$("$WRITE" find-anchor --issue 42 --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "1" ] || fail "find-anchor exit $rc"
[[ "$removed" == *"Unknown subcommand: find-anchor"* ]] || fail "find-anchor rejection missing"

echo "=== redact_gh_error: redactor binary missing ==="
# Fake tree: tracking-issue-write.sh + lib-quiet.sh; redact helpers intentionally absent.
# rename subcommand reaches emit_gh_failure before any body/title redact calls.
FAKE_MISSING="$TMP/fake-missing-redact"
mkdir -p "$FAKE_MISSING/scripts"
cp "$WRITE" "$FAKE_MISSING/scripts/tracking-issue-write.sh"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_MISSING/scripts/lib-quiet.sh"
STUB_MISSING="$TMP/stubs-missing-redact"
mkdir -p "$STUB_MISSING"
secret_missing='sk-ant-FAKESECRET-MISSING-1234'
cat > "$STUB_MISSING/gh" <<GHSTUB_MISSING
#!/usr/bin/env bash
if [ "\$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "\$1" = "issue" ] && [ "\$2" = "view" ]; then
    echo "API error: token $secret_missing rejected" >&2
    exit 1
fi
exit 1
GHSTUB_MISSING
chmod +x "$STUB_MISSING/gh"
set +e
out_missing=$(PATH="$STUB_MISSING:$ORIG_PATH" \
  bash "$FAKE_MISSING/scripts/tracking-issue-write.sh" rename \
  --issue 42 --state 'done' --repo owner/repo 2>&1)
set -e
[[ "$out_missing" == *"FAILED=true"* ]] || fail "missing-redactor: FAILED=true missing: $out_missing"
[[ "$out_missing" == *"ERROR=gh failure: redaction unavailable"* ]] || fail "missing-redactor: ERROR fallback missing: $out_missing"
[[ "$out_missing" != *"$secret_missing"* ]] || fail "missing-redactor: raw secret leaked in output: $out_missing"

echo "=== redact_gh_error: redactor exits non-zero ==="
# Fake tree: passthrough redact-tmpdir-paths.sh; redact-secrets.sh exits 1.
FAKE_FAILING="$TMP/fake-failing-redact"
mkdir -p "$FAKE_FAILING/scripts"
cp "$WRITE" "$FAKE_FAILING/scripts/tracking-issue-write.sh"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_FAILING/scripts/lib-quiet.sh"
printf '#!/usr/bin/env bash\ncat\n' > "$FAKE_FAILING/scripts/redact-tmpdir-paths.sh"
chmod +x "$FAKE_FAILING/scripts/redact-tmpdir-paths.sh"
printf '#!/usr/bin/env bash\nexit 1\n' > "$FAKE_FAILING/scripts/redact-secrets.sh"
chmod +x "$FAKE_FAILING/scripts/redact-secrets.sh"
STUB_FAILING="$TMP/stubs-failing-redact"
mkdir -p "$STUB_FAILING"
secret_failing='sk-ant-FAKESECRET-NONZERO-5678'
cat > "$STUB_FAILING/gh" <<GHSTUB_FAILING
#!/usr/bin/env bash
if [ "\$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "\$1" = "issue" ] && [ "\$2" = "view" ]; then
    echo "API error: token $secret_failing rejected" >&2
    exit 1
fi
exit 1
GHSTUB_FAILING
chmod +x "$STUB_FAILING/gh"
set +e
out_failing=$(PATH="$STUB_FAILING:$ORIG_PATH" \
  bash "$FAKE_FAILING/scripts/tracking-issue-write.sh" rename \
  --issue 42 --state 'done' --repo owner/repo 2>&1)
set -e
[[ "$out_failing" == *"FAILED=true"* ]] || fail "failing-redactor: FAILED=true missing: $out_failing"
[[ "$out_failing" == *"ERROR=gh failure: redaction unavailable"* ]] || fail "failing-redactor: ERROR fallback missing: $out_failing"
[[ "$out_failing" != *"$secret_failing"* ]] || fail "failing-redactor: raw secret leaked in output: $out_failing"

echo "All assertions passed."
