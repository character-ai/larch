#!/usr/bin/env bash
# test-release-prepare.sh — Offline harness for release-prepare.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/release-prepare.sh"
REAL_GIT="$(command -v git)"

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
  diff|show|diff-tree|merge-base)
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
  GIT_MAIN_OID="${GIT_MAIN_OID:-deadbeef00000000000000000000000000000001}" \
  GIT_ORIGIN_MAIN_OID="${GIT_ORIGIN_MAIN_OID:-deadbeef00000000000000000000000000000001}" \
  GIT_BASELINE_TAG="${GIT_BASELINE_TAG:-v1.0.0}" \
  GIT_BASELINE_OID="${GIT_BASELINE_OID:-cafebabe00000000000000000000000000000001}" \
  GIT_LOG_SUBJECTS="${GIT_LOG_SUBJECTS:-}" \
  PATH="$case_dir/bin:$PATH" \
  bash "$SUBJECT" --repo test/repo --out-dir "$case_dir/out" "$@" 2>"$case_dir/stderr.log"
}

setup_classify_repo() {
  local repo=$1
  mkdir -p "$repo/.claude-plugin" "$repo/skills/base"
  git -C "$repo" init -q -b main
  git -C "$repo" config user.email test@test.com
  git -C "$repo" config user.name Test
  printf '{"version":"1.0.0"}\n' > "$repo/.claude-plugin/plugin.json"
  cat > "$repo/skills/base/SKILL.md" <<'SK'
---
name: base
description: base
---
SK
  git -C "$repo" add -A
  git -C "$repo" commit -q -m "init"
  git -C "$repo" tag v1.0.0
}

# Case 1: unique Latest → success KV
case_dir="$TMPDIR_BASE/c1"
mkdir -p "$case_dir/bin" "$case_dir/out" "$case_dir/prs"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tagName":"v1.0.0","isLatest":true}]\n' > "$case_dir/releases.json"
printf 'Feature (#42)\n' > "$case_dir/log-subjects.txt"
GIT_LOG_SUBJECTS="$(cat "$case_dir/log-subjects.txt")"
printf '{"number":42,"title":"Feature","labels":[{"name":"enhancement"}],"author":{"login":"alice"},"url":"https://example.invalid/42"}\n' \
  > "$case_dir/prs/pr-42.json"
classify_repo="$TMPDIR_BASE/c1repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && run_prepare "$case_dir")
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
classify_repo="$TMPDIR_BASE/c2repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && run_prepare "$case_dir")
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
printf '[{"tagName":"v1.0.0","isLatest":true},{"tagName":"v1.0.1","isLatest":true}]\n' > "$case_dir/releases.json"
classify_repo="$TMPDIR_BASE/c3repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && run_prepare "$case_dir")
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
printf '[{"tagName":"v1.0.0","isLatest":true}]\n' > "$case_dir/releases.json"
classify_repo="$TMPDIR_BASE/c4repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && \
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
printf '[{"tagName":"v1.0.0","isLatest":true}]\n' > "$case_dir/releases.json"
classify_repo="$TMPDIR_BASE/c5repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && GIT_LOG_SUBJECTS="" run_prepare "$case_dir" --bump major)
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^BUMP_TYPE=MAJOR$' \
  && printf '%s\n' "$out" | grep -q '^NEW_VERSION=2.0.0$'; then
  ok
else
  fail "--bump major: $out"
fi

# Case 6: zero PR path
case_dir="$TMPDIR_BASE/c6"
mkdir -p "$case_dir/bin" "$case_dir/out"
write_fake_gh "$case_dir/bin"
write_fake_git "$case_dir/bin"
printf '[{"tagName":"v1.0.0","isLatest":true}]\n' > "$case_dir/releases.json"
classify_repo="$TMPDIR_BASE/c6repo"
setup_classify_repo "$classify_repo"
set +e
out=$(cd "$classify_repo" && GIT_LOG_SUBJECTS="" run_prepare "$case_dir")
rc=$?
set -e
if [[ $rc -eq 0 ]] && printf '%s\n' "$out" | grep -q '^PR_COUNT=0$'; then
  ok
else
  fail "zero PR: $out"
fi

total=$((PASS + FAIL))
echo "test-release-prepare: $PASS/$total passed"
[[ "$FAIL" -eq 0 ]] || exit 1
