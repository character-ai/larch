#!/usr/bin/env bash
# test-design-step3-entry.sh — scope-anchor materialization harness for design-step3-entry.sh
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
ENTRY="$ROOT/skills/design/scripts/design-step3-entry.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

# The wrappers reach the Rust session verbs through the verified bootstrap,
# which refuses to install inside a source checkout. Supply a version-matched
# fake so the harness stays offline; the verbs themselves are pinned by the
# Rust unit tests and the session-lifecycle parity goldens.
FAKE_BIN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-bin.XXXXXX")"
FAKE_BIN_DIR="$(cd "$FAKE_BIN_DIR" && pwd -P)"
trap 'rm -rf "$FAKE_BIN_DIR"' EXIT
BASH_BIN="$(command -v bash)"
PLUGIN_VERSION="$(awk -F '"' '$2 == "version" { print $4 }' "$ROOT/.claude-plugin/plugin.json")"
case "$(uname -s):$(uname -m)" in
    Darwin:arm64|Darwin:aarch64) LARCH_TARGET=aarch64-apple-darwin ;;
    Darwin:x86_64|Darwin:amd64) LARCH_TARGET=x86_64-apple-darwin ;;
    Linux:arm64|Linux:aarch64) LARCH_TARGET=aarch64-unknown-linux-gnu ;;
    Linux:x86_64|Linux:amd64) LARCH_TARGET=x86_64-unknown-linux-gnu ;;
    *) echo "FAIL: unsupported harness target" >&2; exit 1 ;;
esac
export LARCH_BINARY="$FAKE_BIN_DIR/larch-fixture"
cat >"$LARCH_BINARY" <<EOF_LARCH
#!$BASH_BIN
set -u
if [[ "\${1:-}" == --version ]]; then printf '%s\n' 'larch $PLUGIN_VERSION'; exit 0; fi
if [[ "\${1:-}" == bootstrap && "\${2:-}" == self-check ]]; then
    printf '%s\n' '{"schema_version":1,"version":"$PLUGIN_VERSION","target":"$LARCH_TARGET"}'
    exit 0
fi
if [[ "\${1:-}" == session ]]; then
    case "\${2:-}" in
        require-plugin-root|validate-design-tmpdir) exit 0 ;;
    esac
fi
if [[ "\${1:-}" == plan-review ]]; then
    case "\${2:-}" in
        step3-entry|step3-entry-state|step3-entry-preview|prelaunch-failure)
            exec "$ROOT/target/debug/larch" "\$@"
            ;;
    esac
fi
if [[ "\${1:-}" == plan-review && "\${2:-}" == snapshot-pre-review ]]; then
    shift 2
    _design=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --design-tmpdir) _design="\${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "\$_design" ]] || exit 2
    cp "\$_design/plan.txt" "\$_design/plan-before-review.txt" || exit 1
    printf '%s\n' 'SNAPSHOT_PRE_REVIEW_STATUS=ok'
    exit 0
fi
# The Rust owner strips the sole unfenced larch:plan block (#8171). The entry
# script only reads the stripped artifact, so the double drops the marker pair
# and the lines it bounds.
if [[ "\${1:-}" == plan-block && "\${2:-}" == strip-body ]]; then
    shift 2
    _file=""
    _output=""
    while [[ \$# -gt 0 ]]; do
        case "\$1" in
            --file) _file="\${2:-}"; shift 2 ;;
            --output) _output="\${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "\$_file" && -n "\$_output" ]] || exit 2
    awk '
        \$0 == "<!-- larch:plan:start -->" { inside = 1; next }
        \$0 == "<!-- larch:plan:end -->" { inside = 0; next }
        !inside
    ' "\$_file" >"\$_output" || exit 1
    exit 0
fi
exit 2
EOF_LARCH
chmod +x "$LARCH_BINARY"

prepare_entry_tmpdir() {
  local d="$1"
  printf 'plan body\n' >"$d/plan.txt"
  : >"$d/.step3-entry-plan-printed"
}

D_OK=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-ok.XXXXXX")
prepare_entry_tmpdir "$D_OK"
cat >"$D_OK/issue-body.txt" <<'EOF'
Feature request text
<!-- larch:plan:start -->
old plan
<!-- larch:plan:end -->
EOF
set +e
env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_OK" ISSUE_NUMBER=9 ISSUE_TITLE='Feature' \
  "$ENTRY" 2>"$D_OK/stderr.log"
ok_rc=$?
set -e
[[ "$ok_rc" -eq 0 ]] || fail "entry ok rc=$ok_rc stderr=$(cat "$D_OK/stderr.log")"
grep -Fq 'Feature request text' "$D_OK/plan-review-scope-anchor.txt" || fail 'successful entry must write stripped scope anchor'
rm -rf "$D_OK"
pass 'Step 3 entry writes scope anchor from stripped issue body'

D_REENTRY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-reentry.XXXXXX")
prepare_entry_tmpdir "$D_REENTRY"
printf 'stale aggregate pool\n' >"$D_REENTRY/oos-aggregate-pool.md"
cat >"$D_REENTRY/issue-body.txt" <<'EOF'
Feature request text
EOF
set +e
env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_REENTRY" ISSUE_NUMBER=9 ISSUE_TITLE='Feature' \
  "$ENTRY" --reentry 2>"$D_REENTRY/stderr.log"
reentry_rc=$?
set -e
[[ "$reentry_rc" -eq 0 ]] || fail "entry reentry rc=$reentry_rc stderr=$(cat "$D_REENTRY/stderr.log")"
if [[ -s "$D_REENTRY/oos-aggregate-pool.md" ]]; then
  fail 'reentry must remove or empty stale oos-aggregate-pool.md'
fi
rm -rf "$D_REENTRY"
pass 'Step 3 reentry resets stale OOS aggregate pool'

D_EMPTY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-entry-empty.XXXXXX")
prepare_entry_tmpdir "$D_EMPTY"
cat >"$D_EMPTY/issue-body.txt" <<'EOF'
<!-- larch:plan:start -->
old plan only
<!-- larch:plan:end -->
EOF
printf 'raw feature-description with plan\n' >"$D_EMPTY/feature-description.txt"
set +e
empty_out=$(env CLAUDE_PLUGIN_ROOT="$ROOT" DESIGN_TMPDIR="$D_EMPTY" ISSUE_NUMBER=9 \
  "$ENTRY" 2>"$D_EMPTY/stderr.log")
empty_rc=$?
set -e
[[ "$empty_rc" -eq 1 ]] || fail "entry empty rc=$empty_rc stdout=$empty_out stderr=$(cat "$D_EMPTY/stderr.log")"
grep -Fxq 'SUMMARY_OUTCOME=failed-judge-panel' <<<"$empty_out" || fail 'empty anchor should emit failed-judge-panel summary'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$empty_out" || fail 'empty anchor should emit panel-init-failed envelope'
if [[ -f "$D_EMPTY/plan-review-scope-anchor.txt" ]] && grep -Fq 'raw feature-description' "$D_EMPTY/plan-review-scope-anchor.txt"; then
  fail 'plan-only issue must not fall back to raw feature-description.txt'
fi
rm -rf "$D_EMPTY"
pass 'Step 3 entry aborts empty stripped body without feature-description fallback'

pass 'design-step3-entry.sh checks passed'
