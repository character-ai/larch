#!/usr/bin/env bash
# test-release-prepare.sh — Offline harness for release-prepare.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd -P)"
SUBJECT="$SCRIPT_DIR/release-prepare.sh"
REAL_GIT="$(command -v git)"
REAL_REPO="$(bash "$REPO_ROOT/scripts/github-remote-repo.sh" origin)"

PASS=0
FAIL=0
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

ok() { PASS=$((PASS + 1)); }
fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }

write_fake_gh() {
  local bin_dir=$1
  cat > "$bin_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  api)
    if [[ "${2:-}" == *"/releases" ]]; then
      cat "${GH_FIXTURE_RELEASES:?}"
      exit 0
    fi
    ;;
  release)
    if [[ "${2:-}" == "list" ]]; then
      cat "${GH_FIXTURE_RELEASES:?}"
      exit 0
    fi
    ;;
  pr)
    if [[ "${2:-}" == "view" ]]; then
      num="${3:-}"
      if [[ -f "${GH_FIXTURE_PR_DIR:?}/pr-${num}.json" ]]; then
        cat "${GH_FIXTURE_PR_DIR}/pr-${num}.json"
        exit 0
      fi
      exit 1
    fi
    if [[ "${2:-}" == "list" ]]; then
      printf '%s\n' "${GH_FIXTURE_OPEN_PRS:-[]}"
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
  fetch)
    if [[ "${GIT_FETCH_FAIL:-}" == "1" ]]; then
      exit 1
    fi
    exit 0
    ;;
  rev-parse)
    if [[ "${2:-}" == "--verify" ]]; then
      ref="${3:-}"
    else
      ref="${2:-}"
    fi
    ref="${ref%'^{commit}'}"
    if [[ "$ref" == "main" ]]; then
      echo "${GIT_MAIN_OID:?}"
      exit 0
    fi
    if [[ "$ref" == "origin/main" ]]; then
      echo "${GIT_ORIGIN_MAIN_OID:?}"
      exit 0
    fi
    if [[ "$ref" == "${GIT_BASELINE_TAG:?}" ]]; then
      echo "${GIT_BASELINE_OID:?}"
      exit 0
    fi
    ;;
  log)
    if [[ "${2:-}" == "${GIT_BASELINE_TAG:?}..origin/main" && "${3:-}" == "--format=%s" ]]; then
      printf '%s' "${GIT_LOG_SUBJECTS-}"
      exit 0
    fi
    exec "$REAL_GIT" "$@"
    ;;
  show)
    if [[ "${2:-}" == "origin/main:.claude-plugin/plugin.json" ]]; then
      printf '%s\n' "${GIT_ORIGIN_PLUGIN_JSON:-{\"version\":\"1.0.0\"}}"
      exit 0
    fi
    exec "$REAL_GIT" "$@"
    ;;
  diff|diff-tree|merge-base)
    exec "$REAL_GIT" "$@"
    ;;
  remote)
    exec "$REAL_GIT" "$@"
    ;;
esac
echo "unexpected git: $*" >&2
exit 9
GIT
  chmod +x "$bin_dir/git"
}

run_prepare() {
  local case_dir=$1
  shift
  REAL_GIT="$REAL_GIT" \
  GH_FIXTURE_RELEASES="$case_dir/releases.json" \
  GH_FIXTURE_PR_DIR="$case_dir/prs" \
  GH_FIXTURE_OPEN_PRS="${GH_FIXTURE_OPEN_PRS:-[]}" \
  GIT_MAIN_OID="${GIT_MAIN_OID:-deadbeef00000000000000000000000000000001}" \
  GIT_ORIGIN_MAIN_OID="${GIT_ORIGIN_MAIN_OID:-deadbeef00000000000000000000000000000001}" \
  GIT_BASELINE_TAG="${GIT_BASELINE_TAG:-v1.0.0}" \
  GIT_BASELINE_OID="${GIT_BASELINE_OID:-cafebabe00000000000000000000000000000001}" \
  GIT_LOG_SUBJECTS="${GIT_LOG_SUBJECTS:-}" \
  GIT_FETCH_FAIL="${GIT_FETCH_FAIL:-}" \
  GIT_ORIGIN_PLUGIN_JSON="${GIT_ORIGIN_PLUGIN_JSON:-}" \
  PATH="$case_dir/bin:$PATH" \
  bash "$SUBJECT" --repo "$REAL_REPO" --out-dir "$case_dir/out" "$@" 2>"$case_dir/stderr.log"
}

# Case 1: unique Latest → success KV
case_dir="$TMPDIR_BASE/c1"
mkdir -p "$case_dir/bin" "$case_dir/out" "$case_dir/prs"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
printf 'Feature (#42)\n' > "$case_dir/log-subjects.txt"
GIT_LOG_SUBJECTS="$(cat "$case_dir/log-subjects.txt")"
printf '{"number":42,"title":"Feature","labels":[{"name":"enhancement"}],"author":{"login":"alice"},"url":"https://example.invalid/42"}\n' \
  > "$case_dir/prs/pr-42.json"
set +e
out=$(cd "$REPO_ROOT" && run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^BASELINE_TAG=v1.0.0$' \
  && printf '%s\n' "$out" | grep -q '^PR_COUNT=1$' \
  && printf '%s\n' "$out" | grep -q '^BUMP_TYPE='; then
  ok
else
  fail "unique latest: rc=$rc out=$out"
fi

# Case 2: zero Latest
case_dir="$TMPDIR_BASE/c2"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$out" | grep -q 'ERROR=no-unique-latest-release'; then
  ok
else
  fail "zero latest: rc=$rc out=$out"
fi

# Case 3: multiple Latest
case_dir="$TMPDIR_BASE/c3"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true},{"tag_name":"v1.0.1","is_latest":true}]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$out" | grep -q 'ERROR=no-unique-latest-release'; then
  ok
else
  fail "multiple latest: rc=$rc out=$out"
fi

# Case 4: stale-local-main
case_dir="$TMPDIR_BASE/c4"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && \
  GIT_MAIN_OID="1111111111111111111111111111111111111111" \
  GIT_ORIGIN_MAIN_OID="2222222222222222222222222222222222222222" \
  run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$out" | grep -q 'ERROR=stale-local-main'; then
  ok
else
  fail "stale main: rc=$rc out=$out"
fi

# Case 5: --bump override
case_dir="$TMPDIR_BASE/c5"
mkdir -p "$case_dir/bin" "$case_dir/out" "$case_dir/prs"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && GIT_LOG_SUBJECTS="" run_prepare "$case_dir" --bump major)
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MAJOR$' \
  && printf '%s\n' "$out" | grep -q '^NEW_VERSION='; then
  ok
else
  fail "--bump major: $out"
fi

# Case 6: zero PR path
case_dir="$TMPDIR_BASE/c6"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && GIT_LOG_SUBJECTS="" run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^PR_COUNT=0$'; then
  ok
else
  fail "zero PR: $out"
fi

# Case 7: fetch fails → baseline-tag-unresolvable
case_dir="$TMPDIR_BASE/c7"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
set +e
out=$(cd "$REPO_ROOT" && GIT_FETCH_FAIL=1 run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$out" | grep -q 'ERROR=baseline-tag-unresolvable'; then
  ok
else
  fail "fetch fail: rc=$rc out=$out"
fi

# Case 8: missing PR metadata → pr-metadata-incomplete
case_dir="$TMPDIR_BASE/c8"
mkdir -p "$case_dir/bin" "$case_dir/out" "$case_dir/prs"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tag_name":"v1.0.0","is_latest":true}]\n' > "$case_dir/releases.json"
GIT_LOG_SUBJECTS=$'Missing (#99)\n'
set +e
out=$(cd "$REPO_ROOT" && run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 1 ]] && printf '%s\n' "$out" | grep -q 'ERROR=pr-metadata-incomplete'; then
  ok
else
  fail "missing pr: rc=$rc out=$out"
fi

total=$((PASS + FAIL))
echo "test-release-prepare: $PASS/$total passed"
[[ "$FAIL" -eq 0 ]] || exit 1
