#!/usr/bin/env bash
# Regression harness for scripts/get-issue-context.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SCRIPT="$REPO_ROOT/scripts/get-issue-context.sh"
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/larch-issue-context.XXXXXX")"
trap 'rm -rf "$TMPROOT"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

stub_dir="$TMPROOT/bin"
mkdir -p "$stub_dir"
cat > "$stub_dir/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${GH_LOG:?}"
if [[ "$1 $2" != "issue view" ]]; then
    echo "unexpected gh command" >&2
    exit 2
fi
if [[ "${FAIL_VIEW:-false}" == "true" ]]; then
    echo "not found" >&2
    exit 1
fi
printf '{"title":"Upstream title","body":"Upstream body"}\n'
GH
chmod +x "$stub_dir/gh"

out=$(GH_LOG="$TMPROOT/gh.log" PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo upstream/repo --tmpdir "$TMPROOT/session")
grep -Fxq "TITLE_FILE=$TMPROOT/session/upstream-issue-title.txt" <<<"$out" || fail "missing TITLE_FILE stdout"
grep -Fxq "BODY_FILE=$TMPROOT/session/upstream-issue-body.txt" <<<"$out" || fail "missing BODY_FILE stdout"
[[ "$(cat "$TMPROOT/session/upstream-issue-title.txt")" == "Upstream title" ]] || fail "title file mismatch"
[[ "$(cat "$TMPROOT/session/upstream-issue-body.txt")" == "Upstream body" ]] || fail "body file mismatch"
grep -Fq 'issue view 42 --repo upstream/repo --json title,body' "$TMPROOT/gh.log" \
    || fail "gh issue view did not target upstream repo"

set +e
GH_LOG="$TMPROOT/fail-gh.log" FAIL_VIEW=true PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo upstream/repo --tmpdir "$TMPROOT/fail" >"$TMPROOT/fail.out" 2>"$TMPROOT/fail.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing issue should fail"

set +e
PATH="$stub_dir:$PATH" "$SCRIPT" --issue 42 --repo '../bad' --tmpdir "$TMPROOT/bad" >"$TMPROOT/bad.out" 2>"$TMPROOT/bad.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "malformed repo should fail"

# Missing jq prereq (Round 1 FINDING_5): if `jq` is not on PATH, the
# script must fail fast with an explicit error message before invoking
# `gh` and before writing any `.tmp` file. Build a hermetic PATH that
# contains the gh stub but excludes the directory where `jq` lives.
# Round 2 FINDING_2: do NOT include /usr/bin or /bin in the PATH — on
# Linux `jq` is at /usr/bin/jq, so adding /usr/bin would defeat the
# missing-jq simulation. Invoke bash explicitly via an absolute path
# (resolved via $BASH or `command -v bash` BEFORE the hermetic PATH
# kicks in) rather than relying on `#!/usr/bin/env bash` shebang
# resolution — with PATH=$no_jq_dir, the kernel CAN exec /usr/bin/env
# but env then fails to find `bash` in the empty PATH and the script
# never starts. Resolving bash to an absolute path sidesteps that
# bootstrap problem; once bash is running, the script's pre-jq-check
# code path uses only bash builtins / shell syntax (no external
# commands), so the `command -v jq` check fires and exits 2 cleanly.
no_jq_dir="$TMPROOT/no-jq-bin"
mkdir -p "$no_jq_dir"
cp "$stub_dir/gh" "$no_jq_dir/gh"
BASH_BIN="${BASH:-$(command -v bash)}"
[[ -x "$BASH_BIN" ]] || fail "could not resolve bash binary for missing-jq sub-test"
set +e
PATH="$no_jq_dir" "$BASH_BIN" "$SCRIPT" --issue 42 --repo upstream/repo --tmpdir "$TMPROOT/no-jq" >"$TMPROOT/no-jq.out" 2>"$TMPROOT/no-jq.err"
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "missing jq should fail fast (FINDING_5)"
grep -Fq 'jq is required' "$TMPROOT/no-jq.err" \
    || fail "missing-jq error should mention 'jq is required' (FINDING_5)"
[[ ! -e "$TMPROOT/no-jq/upstream-issue-title.txt.tmp" ]] \
    || fail "missing-jq path should not have left a .tmp title file (FINDING_5)"
[[ ! -e "$TMPROOT/no-jq/upstream-issue-body.txt.tmp" ]] \
    || fail "missing-jq path should not have left a .tmp body file (FINDING_5)"

echo "PASS: test-get-issue-context.sh"
