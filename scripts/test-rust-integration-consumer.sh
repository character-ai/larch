#!/usr/bin/env bash
# Exercise the CI-selected Rust executable through the shipped bootstrap.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT"

fail() {
    printf 'FAIL: %s\n' "$1" >&2
    exit 1
}

required_env() {
    local name=$1
    [ -n "${!name:-}" ] || fail "$name is required"
}

read_kv() {
    local file=$1
    local key=$2
    "$REPO_ROOT/scripts/larch.sh" kv get --file "$file" --key "$key"
}

required_env LARCH_TEST_RUST_BINARY
required_env LARCH_TEST_RUST_BINARY_SHA256
required_env RUST_CI_MODE
case "$RUST_CI_MODE" in
    full|partial|skip) ;;
    *) fail "RUST_CI_MODE must be full, partial, or skip" ;;
esac

BINARY=$LARCH_TEST_RUST_BINARY
[ -f "$BINARY" ] || fail "selected Rust executable is not a regular file"
[ ! -L "$BINARY" ] || fail "selected Rust executable must not be a symlink"
[ -x "$BINARY" ] || fail "selected Rust executable is not executable"
BINARY=$(cd "$(dirname "$BINARY")" && pwd -P)/$(basename "$BINARY")

if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL_SHA256=$(sha256sum "$BINARY")
elif command -v shasum >/dev/null 2>&1; then
    ACTUAL_SHA256=$(shasum -a 256 "$BINARY")
else
    fail "no SHA-256 utility is available"
fi
ACTUAL_SHA256=${ACTUAL_SHA256%% *}
[ "$ACTUAL_SHA256" = "$LARCH_TEST_RUST_BINARY_SHA256" ] \
    || fail "selected Rust executable checksum does not match"

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-rust-consumer.XXXXXX")
case "$TEST_ROOT" in
    "${TMPDIR:-/tmp}"/larch-rust-consumer.*) ;;
    *) fail "mktemp returned an unexpected path" ;;
esac
trap 'rm -rf -- "$TEST_ROOT"' EXIT

CLIENT_REPO="$TEST_ROOT/client"
PROFILE_DIR="$TEST_ROOT/profiles"
mkdir -p "$CLIENT_REPO" "$PROFILE_DIR" "$TEST_ROOT/home" \
    "$TEST_ROOT/cache" "$TEST_ROOT/config" "$TEST_ROOT/state"
git -C "$CLIENT_REPO" init --quiet
git -C "$CLIENT_REPO" remote add origin https://github.com/example/client.git

export HOME="$TEST_ROOT/home"
export XDG_CACHE_HOME="$TEST_ROOT/cache"
export XDG_CONFIG_HOME="$TEST_ROOT/config"
export XDG_STATE_HOME="$TEST_ROOT/state"
export LARCH_BINARY="$BINARY"
export LLVM_PROFILE_FILE="$PROFILE_DIR/larch-rust-%p.profraw"

START_ENV="$TEST_ROOT/start.env"
FINAL_ENV="$TEST_ROOT/final.env"
"$REPO_ROOT/scripts/larch.sh" run-log lifecycle-start \
    --repo-root "$CLIENT_REPO" \
    --skill review \
    --run-id rust-consumer >"$START_ENV"

[ "$(read_kv "$START_ENV" RUN_LOG_STORAGE)" = disabled ] \
    || fail "lifecycle start did not disable unconfigured storage"
[ "$(read_kv "$START_ENV" LIFECYCLE_STARTED)" = true ] \
    || fail "lifecycle start did not report success"
CONTEXT_FILE=$(read_kv "$START_ENV" CONTEXT_FILE)
[ -f "$CONTEXT_FILE" ] || fail "lifecycle start did not create its context"

"$REPO_ROOT/scripts/larch.sh" run-log lifecycle-finalize \
    --repo-root "$CLIENT_REPO" \
    --skill review \
    --run-id rust-consumer >"$FINAL_ENV"

[ "$(read_kv "$FINAL_ENV" OUTCOME)" = success ] \
    || fail "lifecycle finalize did not preserve the outcome"
[ "$(read_kv "$FINAL_ENV" RUN_LOG_STORAGE)" = disabled ] \
    || fail "lifecycle finalize changed the storage mode"
[ "$(read_kv "$FINAL_ENV" RUN_LOG_PUBLICATION)" = skipped-disabled ] \
    || fail "lifecycle finalize did not skip disabled publication"
[ "$(read_kv "$FINAL_ENV" LIFECYCLE_TERMINALIZED)" = true ] \
    || fail "lifecycle finalize did not report terminalization"

if [ "$RUST_CI_MODE" != partial ]; then
    set -- "$PROFILE_DIR"/larch-rust-*.profraw
    [ -f "$1" ] || fail "coverage-built Rust executable did not write a profile"
fi
if find "$CLIENT_REPO" -type f -name 'default_*.profraw' -print -quit | grep -q .; then
    fail "Rust coverage escaped into the client repository"
fi

printf 'PASS: selected Rust lifecycle consumer\n'
