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
    if [ -n "${GH_COMMENT_FAIL_COUNT:-}" ] && [ -n "${GH_COMMENT_COUNT_FILE:-}" ]; then
        count=$(( $(cat "$GH_COMMENT_COUNT_FILE" 2>/dev/null || echo 0) + 1 ))
        printf '%s\n' "$count" > "$GH_COMMENT_COUNT_FILE"
        if [ "$count" -le "${GH_COMMENT_FAIL_COUNT}" ]; then
            printf '%s\n' 'Could not resolve host: api.github.com' >&2
            exit 1
        fi
    fi
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
    echo "[DESIGNED] Existing title"
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

echo "=== append-comment does not retry transient gh failure ==="
export GH_COMMENT_FAIL_COUNT=1
export GH_COMMENT_COUNT_FILE="$TMP/comment-count"
set +e
out="$("$WRITE" append-comment --issue 42 --body-file "$body" --repo owner/repo 2>&1)"
rc=$?
set -e
[ "$rc" = "2" ] || fail "append transient exit $rc"
[[ "$out" == *"FAILED=true"* ]] || fail "append transient FAILED missing: $out"
[[ "$out" == *"Could not resolve host"* ]] || fail "append transient error missing: $out"
[[ "$(cat "$GH_COMMENT_COUNT_FILE")" == "1" ]] || fail "append transient comment count mismatch: $(cat "$GH_COMMENT_COUNT_FILE" 2>/dev/null || echo missing)"
unset GH_COMMENT_FAIL_COUNT GH_COMMENT_COUNT_FILE

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

echo "=== rename designed prefix from in-progress legacy title ==="
cat > "$stub/gh" <<'GHSTUB2'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then
    echo "owner/repo"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[IN PROGRESS] Feature title"
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
GHSTUB2
chmod +x "$stub/gh"
out="$("$WRITE" rename --issue 42 --state "designed" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "designed rename RENAMED: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[DESIGNED] Feature title" ] || fail "designed title was $(cat "$TITLE_CAPTURE")"

echo "=== rename designed idempotent when already canonical ==="
cat > "$stub/gh" <<'GHSTUB3'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[DESIGNED] Feature title"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "edit" ]; then exit 1; fi
exit 1
GHSTUB3
chmod +x "$stub/gh"
rm -f "$TITLE_CAPTURE"
out="$("$WRITE" rename --issue 42 --state "designed" --repo owner/repo)"
[[ "$out" == *"RENAMED=false"* ]] || fail "designed idempotent RENAMED: $out"
[[ ! -f "$TITLE_CAPTURE" ]] || fail "designed idempotent must not call gh issue edit"

echo "=== rename designing from no-prefix title ==="
cat > "$stub/gh" <<'GHSTUB3b'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "Feature title"
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
GHSTUB3b
chmod +x "$stub/gh"
out="$("$WRITE" rename --issue 42 --state "designing" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "designing rename RENAMED: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[DESIGNING] Feature title" ] || fail "designing title was $(cat "$TITLE_CAPTURE")"

echo "=== rename designed from legacy planned title (migration strip) ==="
cat > "$stub/gh" <<'GHSTUB3c'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[PLANNED] Feature title"
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
GHSTUB3c
chmod +x "$stub/gh"
out="$("$WRITE" rename --issue 42 --state "designed" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "legacy planned→designed RENAMED: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[DESIGNED] Feature title" ] || fail "legacy planned→designed title was $(cat "$TITLE_CAPTURE")"

echo "=== legacy in-progress state rejected ==="
set +e
bad_state="$("$WRITE" rename --issue 42 --state "in-progress" --repo owner/repo 2>&1)"
rc_state=$?
set -e
[ "$rc_state" = "1" ] || fail "in-progress exit $rc_state (expected 1)"
[[ "$bad_state" == *"FAILED=true"* ]] || fail "in-progress FAILED=true missing: $bad_state"
[[ "$bad_state" == *"invalid --state"* ]] || fail "in-progress error message missing: $bad_state"

echo "=== legacy planned state rejected ==="
set +e
bad_planned="$("$WRITE" rename --issue 42 --state "planned" --repo owner/repo 2>&1)"
rc_planned=$?
set -e
[ "$rc_planned" = "1" ] || fail "planned exit $rc_planned (expected 1)"
[[ "$bad_planned" == *"FAILED=true"* ]] || fail "planned FAILED=true missing: $bad_planned"
[[ "$bad_planned" == *"invalid --state"* ]] || fail "planned error message missing: $bad_planned"

echo "=== rename implementing from designed title ==="
cat > "$stub/gh" <<'GHSTUB_IMPL'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[DESIGNED] Feature title"
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
GHSTUB_IMPL
chmod +x "$stub/gh"
out="$("$WRITE" rename --issue 42 --state "implementing" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "implementing rename RENAMED: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[IMPLEMENTING] Feature title" ] || fail "implementing title was $(cat "$TITLE_CAPTURE")"

echo "=== rename implementing from in-progress legacy title ==="
cat > "$stub/gh" <<'GHSTUB_IMPL2'
#!/usr/bin/env bash
if [ "$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
    echo "[IN PROGRESS] Feature title"
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
GHSTUB_IMPL2
chmod +x "$stub/gh"
out="$("$WRITE" rename --issue 42 --state "implementing" --repo owner/repo)"
[[ "$out" == *"RENAMED=true"* ]] || fail "implementing from legacy RENAMED: $out"
[ "$(cat "$TITLE_CAPTURE")" = "[IMPLEMENTING] Feature title" ] || fail "implementing from legacy title was $(cat "$TITLE_CAPTURE")"

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
cp "$REPO_ROOT/scripts/lib-net.sh" "$FAKE_MISSING/scripts/lib-net.sh"
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
cp "$REPO_ROOT/scripts/lib-net.sh" "$FAKE_FAILING/scripts/lib-net.sh"
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

echo "=== redact_gh_error: truncation marker on stdout with exit 0 plus fake token ==="
FAKE_TRUNC_TOKEN="$TMP/fake-trunc-token-redact"
mkdir -p "$FAKE_TRUNC_TOKEN/scripts"
cp "$WRITE" "$FAKE_TRUNC_TOKEN/scripts/tracking-issue-write.sh"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_TRUNC_TOKEN/scripts/lib-quiet.sh"
cp "$REPO_ROOT/scripts/lib-net.sh" "$FAKE_TRUNC_TOKEN/scripts/lib-net.sh"
printf '#!/usr/bin/env bash\ncat\n' > "$FAKE_TRUNC_TOKEN/scripts/redact-tmpdir-paths.sh"
chmod +x "$FAKE_TRUNC_TOKEN/scripts/redact-tmpdir-paths.sh"
trunc_marker='[content truncated — unterminated PEM block; tail of body dropped for safety]'
token_trunc='sk-ant-FAKETRUNC-TOKEN-1234567890123456789AB'
cat > "$FAKE_TRUNC_TOKEN/scripts/redact-secrets.sh" <<SECRETS_TRUNC_TOKEN
#!/usr/bin/env bash
cat >/dev/null
printf '%s%s' "${trunc_marker}" "${token_trunc}"
SECRETS_TRUNC_TOKEN
chmod +x "$FAKE_TRUNC_TOKEN/scripts/redact-secrets.sh"
STUB_TRUNC_TOKEN="$TMP/stubs-trunc-token-redact"
mkdir -p "$STUB_TRUNC_TOKEN"
cat > "$STUB_TRUNC_TOKEN/gh" <<GHSTUB_TRUNC_TOKEN
#!/usr/bin/env bash
if [ "\$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "\$1" = "issue" ] && [ "\$2" = "view" ]; then
    echo "API error: something went wrong" >&2
    exit 1
fi
exit 1
GHSTUB_TRUNC_TOKEN
chmod +x "$STUB_TRUNC_TOKEN/gh"
set +e
out_trunc_token=$(PATH="$STUB_TRUNC_TOKEN:$ORIG_PATH" \
  bash "$FAKE_TRUNC_TOKEN/scripts/tracking-issue-write.sh" rename \
  --issue 42 --state 'done' --repo owner/repo 2>&1)
rc_trunc_token=$?
set -e
[ "$rc_trunc_token" = "2" ] || fail "trunc-token-redactor: expected exit 2, got $rc_trunc_token"
[[ "$out_trunc_token" == *"FAILED=true"* ]] || fail "trunc-token-redactor: FAILED=true missing: $out_trunc_token"
[[ "$out_trunc_token" == *"ERROR=gh failure: redaction unavailable"* ]] || fail "trunc-token-redactor: ERROR fallback missing: $out_trunc_token"
[[ "$out_trunc_token" != *"$token_trunc"* ]] || fail "trunc-token-redactor: fake token leaked in output: $out_trunc_token"

echo "=== redact_gh_error: truncation marker with exit 0 scrubs gh stderr ==="
FAKE_TRUNC_OK="$TMP/fake-trunc-ok-redact"
mkdir -p "$FAKE_TRUNC_OK/scripts"
cp "$WRITE" "$FAKE_TRUNC_OK/scripts/tracking-issue-write.sh"
cp "$REPO_ROOT/scripts/lib-quiet.sh" "$FAKE_TRUNC_OK/scripts/lib-quiet.sh"
cp "$REPO_ROOT/scripts/lib-net.sh" "$FAKE_TRUNC_OK/scripts/lib-net.sh"
printf '#!/usr/bin/env bash\ncat\n' > "$FAKE_TRUNC_OK/scripts/redact-tmpdir-paths.sh"
chmod +x "$FAKE_TRUNC_OK/scripts/redact-tmpdir-paths.sh"
secret_trunc_ok='sk-ant-FAKETRUNC-OK-1234567890123456789AB'
cat > "$FAKE_TRUNC_OK/scripts/redact-secrets.sh" <<SECRETS_TRUNC_OK
#!/usr/bin/env bash
# Consume stdin (would contain API error + secret); emit only documented marker.
cat >/dev/null
printf '%s' "${trunc_marker}"
SECRETS_TRUNC_OK
chmod +x "$FAKE_TRUNC_OK/scripts/redact-secrets.sh"
STUB_TRUNC_OK="$TMP/stubs-trunc-ok-redact"
mkdir -p "$STUB_TRUNC_OK"
cat > "$STUB_TRUNC_OK/gh" <<GHSTUB_TRUNC_OK
#!/usr/bin/env bash
if [ "\$1" = "repo" ]; then echo "owner/repo"; exit 0; fi
if [ "\$1" = "issue" ] && [ "\$2" = "view" ]; then
    echo "API error: token $secret_trunc_ok rejected" >&2
    exit 1
fi
exit 1
GHSTUB_TRUNC_OK
chmod +x "$STUB_TRUNC_OK/gh"
set +e
out_trunc_ok=$(PATH="$STUB_TRUNC_OK:$ORIG_PATH" \
  bash "$FAKE_TRUNC_OK/scripts/tracking-issue-write.sh" rename \
  --issue 42 --state 'done' --repo owner/repo 2>&1)
rc_trunc_ok=$?
set -e
[ "$rc_trunc_ok" = "2" ] || fail "trunc-ok-redactor: expected exit 2, got $rc_trunc_ok"
[[ "$out_trunc_ok" == *"FAILED=true"* ]] || fail "trunc-ok-redactor: FAILED=true missing: $out_trunc_ok"
[[ "$out_trunc_ok" == *"ERROR=gh failure: redaction unavailable"* ]] || fail "trunc-ok-redactor: ERROR fallback missing: $out_trunc_ok"
[[ "$out_trunc_ok" != *"$secret_trunc_ok"* ]] || fail "trunc-ok-redactor: gh stderr secret leaked in output: $out_trunc_ok"

echo "All assertions passed."
