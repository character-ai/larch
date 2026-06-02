#!/usr/bin/env bash
# test-release-finish.sh — Offline harness for release-finish.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/release-finish.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
REAL_GIT="$(command -v git)"
REAL_REPO="$(bash "$REPO_ROOT/scripts/github-remote-repo.sh" origin)"

PASS=0
FAIL=0
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

sleep_stub_dir="$TMPDIR_BASE/sleep-stub"
mkdir -p "$sleep_stub_dir"
cat > "$sleep_stub_dir/sleep" <<'SLEEP'
#!/usr/bin/env bash
exit 0
SLEEP
chmod +x "$sleep_stub_dir/sleep"

ok() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

write_fake_gh() {
  local bin_dir=$1
  cat > "$bin_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  pr)
    if [[ "${2:-}" == "view" ]]; then
      if [[ "${GH_FIXTURE_MERGE_EMPTY:-}" == "1" ]]; then
        printf '\n'
        exit 0
      fi
      printf '%s\n' "${GH_FIXTURE_MERGE_OID:-deadbeef00000000000000000000000000000001}"
      exit 0
    fi
    ;;
  release)
    if [[ "${2:-}" == "view" ]]; then
      [[ "${GH_FIXTURE_RELEASE_EXISTS:-}" == "1" ]] && exit 0 || exit 1
    fi
    if [[ "${2:-}" == "create" || "${2:-}" == "edit" ]]; then
      exit 0
    fi
    ;;
esac
echo "unexpected gh: $*" >&2
exit 9
GH
  chmod +x "$bin_dir/gh"
}

write_fake_git() {
  local bin_dir=$1
  cat > "$bin_dir/git" <<'GIT'
#!/usr/bin/env bash
set -euo pipefail
: "${REAL_GIT:?}"
case "$1" in
  fetch) exit 0 ;;
  show)
    if [[ "${2:-}" == *":.claude-plugin/plugin.json" ]]; then
      if [[ -f "${GIT_PLUGIN_JSON_FILE:-}" ]]; then
        cat "${GIT_PLUGIN_JSON_FILE}"
      elif [[ -n "${GIT_PLUGIN_JSON:-}" ]]; then
        printf '%s\n' "$GIT_PLUGIN_JSON"
      else
        printf '%s\n' '{"version":"1.1.0"}'
      fi
      exit 0
    fi
    ;;
  ls-remote)
    printf '%s\n' "${GIT_LS_REMOTE_OUT-}"
    exit 0
    ;;
  rev-parse)
    if [[ "${2:-}" == "--verify" ]]; then
      ref="${3:-}"
      ref="${ref%'^{commit}'}"
      if [[ "$ref" == "${GIT_TARGET_OID:?}" ]]; then
        echo "$ref"
        exit 0
      fi
      if [[ "${GIT_LOCAL_TAG_EXISTS:-}" == "1" && "$ref" == "${GIT_TAG:?}" ]]; then
        echo "${GIT_LOCAL_TAG_OID:-${GIT_TARGET_OID:?}}"
        exit 0
      fi
      exit 1
    fi
    if [[ "${2:-}" == "origin/main^{commit}" ]]; then
      echo "${GIT_ORIGIN_MAIN_OID:-${GIT_TARGET_OID:?}}"
      exit 0
    fi
    if [[ "${2:-}" == "${GIT_TAG:?}^{commit}" ]]; then
      echo "${GIT_LOCAL_TAG_OID:-${GIT_TARGET_OID:?}}"
      exit 0
    fi
    if [[ "${2:-}" == "${GIT_TARGET_OID:?}^{commit}" ]]; then
      echo "${GIT_TARGET_OID:?}"
      exit 0
    fi
    ;;
  tag) exit 0 ;;
  push) exit "${GIT_PUSH_RC:-0}" ;;
  remote) exec "$REAL_GIT" "$@" ;;
esac
echo "unexpected git: $*" >&2
exit 9
GIT
  chmod +x "$bin_dir/git"
}

write_fake_promote() {
  local path=$1
  cat > "$path" <<'PROMO'
#!/usr/bin/env bash
exit "${PROMOTE_RC:-0}"
PROMO
  chmod +x "$path"
}

write_fake_redact() {
  local bin_dir=$1
  cat > "$bin_dir/redact-secrets.sh" <<'RED'
#!/usr/bin/env bash
cat
RED
  chmod +x "$bin_dir/redact-secrets.sh"
}

run_finish() {
  local case_dir=$1
  local fake_promote=$2
  shift 2
  # Pre-compute before subshell so ${GIT_ORIGIN_MAIN_OID} can reference
  # GIT_TARGET_OID without SC2097/SC2098 (inline-assignment visibility).
  local _run_git_target="${GIT_TARGET_OID:-deadbeef00000000000000000000000000000001}"
  local _run_origin_main="${GIT_ORIGIN_MAIN_OID:-${GIT_TARGET_OID:-deadbeef00000000000000000000000000000001}}"
  (cd "$REPO_ROOT" && \
    LARCH_RELEASE_FINISH_PROMOTE_SCRIPT="$fake_promote" \
    LARCH_RELEASE_FINISH_ORIGIN_REPO="$REAL_REPO" \
    LARCH_RELEASE_FINISH_AT_VERSION="${LARCH_RELEASE_FINISH_AT_VERSION:-}" \
    REAL_GIT="$REAL_GIT" \
    PATH="$case_dir/bin:$sleep_stub_dir:$PATH" \
    GH_FIXTURE_PR_JSON="$case_dir/pr.json" \
    GH_FIXTURE_MERGE_OID="${GH_FIXTURE_MERGE_OID:-deadbeef00000000000000000000000000000001}" \
    GH_FIXTURE_RELEASE_EXISTS="${GH_FIXTURE_RELEASE_EXISTS:-}" \
    GIT_TARGET_OID="$_run_git_target" \
    GIT_ORIGIN_MAIN_OID="$_run_origin_main" \
    GIT_PLUGIN_JSON="${GIT_PLUGIN_JSON:-}" \
    GIT_PLUGIN_JSON_FILE="${GIT_PLUGIN_JSON_FILE:-}" \
    GIT_TAG="${GIT_TAG:-v1.1.0}" \
    GIT_LS_REMOTE_OUT="${GIT_LS_REMOTE_OUT-}" \
    GIT_LOCAL_TAG_EXISTS="${GIT_LOCAL_TAG_EXISTS:-}" \
    GIT_LOCAL_TAG_OID="${GIT_LOCAL_TAG_OID:-}" \
    GIT_PUSH_RC="${GIT_PUSH_RC:-0}" \
    PROMOTE_RC="${PROMOTE_RC:-0}" \
    bash "$SUBJECT" --version 1.1.0 --notes-file "$case_dir/notes.md" --repo "$REAL_REPO" --pr 1 "$@")
}

# Case 1: create path + full KV after promote
case_dir="$TMPDIR_BASE/c1"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf '{"mergeCommit":{"oid":"deadbeef00000000000000000000000000000001"}}\n' > "$case_dir/pr.json"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"1.1.0"}\n' > "$case_dir/plugin.json"
set +e
out=$(GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" run_finish "$case_dir" "$fake_promote")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^RELEASE_ACTION=create$' \
  && printf '%s\n' "$out" | grep -q '^TARGET_OID=' \
  && printf '%s\n' "$out" | grep -q '^VERSION=1.1.0$'; then
  ok
else
  fail "create path: rc=$rc out=$out"
fi

# Case 2: version mismatch at TARGET_OID
case_dir="$TMPDIR_BASE/c2"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf '{"mergeCommit":{"oid":"deadbeef00000000000000000000000000000001"}}\n' > "$case_dir/pr.json"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"9.9.9"}\n' > "$case_dir/plugin.json"
set +e
out=$(GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" run_finish "$case_dir" "$fake_promote")
rc=$?
set -e
if [[ $rc -eq 1 ]]; then
  ok
else
  fail "version mismatch should fail: rc=$rc out=$out"
fi

# Case 3: remote tag wrong OID
case_dir="$TMPDIR_BASE/c3"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf '{"mergeCommit":{"oid":"deadbeef00000000000000000000000000000001"}}\n' > "$case_dir/pr.json"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"1.1.0"}\n' > "$case_dir/plugin.json"
set +e
out=$( \
  GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" \
  GIT_LS_REMOTE_OUT=$'badbadbadbadbadbadbadbadbadbadbadbadbadbad\trefs/tags/v1.1.0^{}\n' \
  run_finish "$case_dir" "$fake_promote")
rc=$?
set -e
if [[ $rc -eq 1 ]]; then
  ok
else
  fail "wrong remote tag should fail: rc=$rc"
fi

# Case 4: edit path when release exists
case_dir="$TMPDIR_BASE/c4"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf '{"mergeCommit":{"oid":"deadbeef00000000000000000000000000000001"}}\n' > "$case_dir/pr.json"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"1.1.0"}\n' > "$case_dir/plugin.json"
set +e
out=$(GH_FIXTURE_RELEASE_EXISTS=1 GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" run_finish "$case_dir" "$fake_promote")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^RELEASE_ACTION=edit$'; then
  ok
else
  fail "edit path: rc=$rc out=$out"
fi

# Case 5: merge-commit-missing with no origin/main version match → exit 1
case_dir="$TMPDIR_BASE/c5"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"9.9.9"}\n' > "$case_dir/plugin.json"
set +e
out=$(GH_FIXTURE_MERGE_EMPTY=1 GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" run_finish "$case_dir" "$fake_promote" 2>"$case_dir/stderr.log")
rc=$?
stderr=$(cat "$case_dir/stderr.log" 2>/dev/null || true)
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$stderr" | grep -q 'ERROR=merge-commit-missing'; then
  ok
else
  fail "merge-commit-missing: rc=$rc stderr=$stderr"
fi

# Case 6: local tag wrong OID → exit 1
case_dir="$TMPDIR_BASE/c6"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"1.1.0"}\n' > "$case_dir/plugin.json"
set +e
out=$( \
  GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" \
  GIT_LOCAL_TAG_EXISTS=1 \
  GIT_LOCAL_TAG_OID="cafebabe00000000000000000000000000000001" \
  run_finish "$case_dir" "$fake_promote" 2>"$case_dir/stderr.log")
rc=$?
stderr=$(cat "$case_dir/stderr.log" 2>/dev/null || true)
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$stderr" | grep -q 'ERROR=local tag'; then
  ok
else
  fail "local tag wrong OID: rc=$rc stderr=$stderr"
fi

# Case 7: merge-commit-missing but origin/main version matches → success via fallback
case_dir="$TMPDIR_BASE/c7"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
write_fake_redact "$case_dir/bin"
fake_promote="$case_dir/fake-promote.sh"
write_fake_promote "$fake_promote"
printf 'notes\n' > "$case_dir/notes.md"
printf '{"version":"1.1.0"}\n' > "$case_dir/plugin.json"
set +e
out=$(GH_FIXTURE_MERGE_EMPTY=1 GIT_PLUGIN_JSON_FILE="$case_dir/plugin.json" run_finish "$case_dir" "$fake_promote")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^TARGET_OID='; then
  ok
else
  fail "origin/main fallback: rc=$rc out=$out"
fi

total=$((PASS + FAIL))
echo "test-release-finish: $PASS/$total passed"
[[ "$FAIL" -eq 0 ]] || exit 1
