#!/usr/bin/env bash
# Regression harness for rebase-push.sh --no-push transient fetch retry.
set -euo pipefail

export LARCH_QUIET_DISABLE=1

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SCRIPT="$REPO_ROOT/scripts/rebase-push.sh"
REAL_GIT="$(command -v git)"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

configure_repo() {
  git -C "$1" config user.name "Larch Test"
  git -C "$1" config user.email "larch-test@example.invalid"
}

setup_fresh_repo() {
  local root="$1"
  local origin="$root/origin.git"
  local seed="$root/seed"
  local work="$root/work"

  mkdir -p "$origin" "$seed" "$work"
  git init --bare "$origin" >/dev/null

  git -C "$seed" init >/dev/null
  configure_repo "$seed"
  git -C "$seed" checkout -b main >/dev/null 2>&1
  printf 'base\n' > "$seed/file.txt"
  git -C "$seed" add file.txt
  git -C "$seed" commit -m "Initial main" >/dev/null
  git -C "$seed" remote add origin "$origin"
  git -C "$seed" push origin main >/dev/null 2>&1
  git -C "$origin" symbolic-ref HEAD refs/heads/main

  git -C "$work" init >/dev/null
  configure_repo "$work"
  git -C "$work" remote add origin "$origin"
  git -C "$work" fetch origin main --quiet
  git -C "$work" checkout -b feature origin/main >/dev/null 2>&1
}

TMPDIR_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-rebase-no-push-fetch.XXXXXX")
trap 'rm -rf "$TMPDIR_ROOT"' EXIT

sleep_stub="$TMPDIR_ROOT/sleep-stub"
mkdir -p "$sleep_stub"
cat > "$sleep_stub/sleep-seconds.sh" <<'SLEEPSTUB'
#!/usr/bin/env bash
exit 0
SLEEPSTUB
chmod +x "$sleep_stub/sleep-seconds.sh"

write_git_stub() {
  local stub_dir="$1"
  local mode="$2"
  local count_file="$3"
  cat > "$stub_dir/git" <<STUB
#!/usr/bin/env bash
set -u
REAL_GIT="${REAL_GIT}"
MODE="${mode}"
COUNT_FILE="${count_file}"
case "\${1:-}" in
  fetch)
    if [[ "\${2:-}" == "origin" && "\${3:-}" == "main" ]]; then
      _count=0
      if [[ -f "\$COUNT_FILE" ]]; then
        _count=\$(cat "\$COUNT_FILE")
      fi
      _count=\$((_count + 1))
      printf '%s\n' "\$_count" > "\$COUNT_FILE"
      if [[ "\$MODE" == "transient" && "\$_count" -eq 1 ]]; then
        echo "fatal: unable to access 'https://github.com/example.invalid/repo.git/': Could not resolve host" >&2
        exit 1
      fi
      if [[ "\$MODE" == "persistent" ]]; then
        echo "fatal: unable to access 'https://github.com/example.invalid/repo.git/': Could not resolve host" >&2
        exit 1
      fi
    fi
    ;;
esac
exec "\$REAL_GIT" "\$@"
STUB
  chmod +x "$stub_dir/git"
}

# Transient fetch failure then success → exit 0 (SKIPPED_ALREADY_FRESH).
setup_fresh_repo "$TMPDIR_ROOT/transient"
transient_repo="$TMPDIR_ROOT/transient/work"
transient_stub="$TMPDIR_ROOT/transient/bin"
mkdir -p "$transient_stub"
fetch_count_file="$TMPDIR_ROOT/transient/fetch-count"
printf '0\n' >"$fetch_count_file"
write_git_stub "$transient_stub" "transient" "$fetch_count_file"
set +e
transient_output=$(cd "$transient_repo" && SLEEP_SCRIPT_DIR="$sleep_stub" PATH="$transient_stub:$PATH" "$SCRIPT" --no-push 2>"$TMPDIR_ROOT/transient.err")
transient_rc=$?
set -e
[[ "$transient_rc" == "0" ]] || fail "transient fetch retry expected exit 0, got $transient_rc (stderr: $(cat "$TMPDIR_ROOT/transient.err"))"
[[ "$transient_output" == "SKIPPED_ALREADY_FRESH=true" ]] || fail "transient fetch retry expected SKIPPED_ALREADY_FRESH, got: $transient_output"
fetch_calls=$(cat "$fetch_count_file")
[[ "$fetch_calls" -ge 2 ]] || fail "transient fetch should retry (got $fetch_calls fetch calls)"

# Persistent fetch failure → exit 3 with REBASE_ERROR.
setup_fresh_repo "$TMPDIR_ROOT/persistent"
persistent_repo="$TMPDIR_ROOT/persistent/work"
persistent_stub="$TMPDIR_ROOT/persistent/bin"
mkdir -p "$persistent_stub"
persistent_count_file="$TMPDIR_ROOT/persistent/fetch-count"
printf '0\n' >"$persistent_count_file"
write_git_stub "$persistent_stub" "persistent" "$persistent_count_file"
set +e
(cd "$persistent_repo" && SLEEP_SCRIPT_DIR="$sleep_stub" PATH="$persistent_stub:$PATH" "$SCRIPT" --no-push) \
  >"$TMPDIR_ROOT/persistent.out" 2>"$TMPDIR_ROOT/persistent.err"
persistent_rc=$?
set -e
[[ "$persistent_rc" == "3" ]] || fail "persistent fetch failure expected exit 3, got $persistent_rc"
if ! grep -Fq 'REBASE_ERROR=git fetch origin main failed (network/auth issue)' \
  "$TMPDIR_ROOT/persistent.out" "$TMPDIR_ROOT/persistent.err"; then
  fail "persistent fetch failure should preserve REBASE_ERROR (stdout: $(cat "$TMPDIR_ROOT/persistent.out"); stderr: $(cat "$TMPDIR_ROOT/persistent.err"))"
fi
fetch_calls=$(cat "$persistent_count_file")
[[ "$fetch_calls" -ge 3 ]] || fail "persistent fetch should exhaust retry budget (got $fetch_calls fetch calls)"

echo "PASS: test-rebase-push-no-push-fetch-retry.sh"
