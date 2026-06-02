#!/usr/bin/env bash
# test-promote-release.sh — Offline harness for promote-release.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBJECT="$SCRIPT_DIR/promote-release.sh"

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
    if [[ "${2:-}" == "view" ]]; then
      [[ -n "${GH_FIXTURE_VIEW_JSON:-}" ]] || exit 1
      printf '%s\n' "$GH_FIXTURE_VIEW_JSON"
      exit 0
    fi
    if [[ "${2:-}" == "list" ]]; then
      printf '%s\n' "$GH_FIXTURE_LIST_JSON"
      exit 0
    fi
    if [[ "${2:-}" == "edit" ]]; then
      exit 0
    fi
    ;;
esac
echo "unexpected gh: $*" >&2
exit 9
GH
  chmod +x "$bin_dir/gh"
}

# Case 1: default repo path (no --repo)
case_dir="$TMPDIR_BASE/c1"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
export GH_FIXTURE_VIEW_JSON='{"isPrerelease":false}'
export GH_FIXTURE_LIST_JSON='[{"tagName":"v1.0.0","isLatest":true}]'
set +e
PATH="$case_dir/bin:$PATH" bash "$SUBJECT" 1.0.0 2>"$case_dir/stderr.log" >/dev/null
rc=$?
set -e
if [[ $rc -eq 0 ]]; then
  ok
else
  fail "default path: rc=$rc stderr=$(cat "$case_dir/stderr.log" 2>/dev/null || true)"
fi

# Case 2: explicit --repo
case_dir="$TMPDIR_BASE/c2"
mkdir -p "$case_dir/bin"
write_fake_gh "$case_dir/bin"
export GH_FIXTURE_VIEW_JSON='{"isPrerelease":true}'
export GH_FIXTURE_LIST_JSON='[{"tagName":"v1.2.0","isLatest":true}]'
set +e
PATH="$case_dir/bin:$PATH" bash "$SUBJECT" 1.2.0 --repo test/hub 2>"$case_dir/stderr.log" >/dev/null
rc=$?
set -e
if [[ $rc -eq 0 ]]; then
  ok
else
  fail "--repo path: rc=$rc"
fi

# Case 3: invalid --repo rejected
case_dir="$TMPDIR_BASE/c3"
mkdir -p "$case_dir"
set +e
bash "$SUBJECT" 1.0.0 --repo 'not-valid' 2>"$case_dir/stderr.log" >/dev/null
rc=$?
set -e
if [[ $rc -eq 2 ]]; then
  ok
else
  fail "invalid --repo should exit 2: rc=$rc"
fi

total=$((PASS + FAIL))
echo "test-promote-release: $PASS/$total passed"
[[ "$FAIL" -eq 0 ]] || exit 1
