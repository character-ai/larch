#!/usr/bin/env bash
# test-file-failure-report-cross-repo.sh — offline harness for cross-repo failure filing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SCRIPT="$SCRIPT_DIR/file-failure-report-cross-repo.sh"
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-cross-repo-report.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }
contains() { local file=$1 needle=$2 label=$3; if grep -Fq -- "$needle" "$file"; then pass "$label"; else fail "$label" "missing: $needle" "$(cat "$file" 2>/dev/null || true)"; fi; }
not_contains() { local file=$1 needle=$2 label=$3; if grep -Fq -- "$needle" "$file"; then fail "$label" "unexpected: $needle" "$(cat "$file")"; else pass "$label"; fi; }
assert_eq() { local exp=$1 act=$2 label=$3; if [ "$exp" = "$act" ]; then pass "$label"; else fail "$label" "expected=$exp actual=$act"; fi; }
kv() { awk -v k="$1" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$2"; }

MARKER_HASH=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
LIVE_CONTEXT="$TMPROOT/claude-implement-test/session-env.sh"
mkdir -p "$(dirname "$LIVE_CONTEXT")"
printf 'LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run-1\n' >"$LIVE_CONTEXT"

make_case() {
    local name=$1 dir
    dir="$TMPROOT/$name"
    mkdir -p "$dir/bin"
    cat >"$dir/body.md" <<EOF2
### [Bug] /implement terminal: fixture

<!-- larch-stall:signature=$MARKER_HASH -->

Full report body sentinel.
EOF2
    cat >"$dir/attempts.md" <<'EOF2'
| Attempt | Class |
|---|---|
| `1` | `transient-infra` |
EOF2
    cat >"$dir/escalation.md" <<'EOF2'
- site=`ship-pr` trigger=`main-agent-required`
EOF2
    cat >"$dir/root.md" <<'EOF2'
verdict=larch-defect
confidence=high
summary=bounded finding

Bounded root-cause slice.
EOF2
    cat >"$dir/stall-recovery-sensitive-corpus.env" <<'EOF2'
client-secret-token
EOF2
    cat >"$dir/bin/gh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$GH_STUB_LOG"
if [ "$1" = api ] && [ "${2:-}" = --paginate ]; then
    case "${GH_STUB_CASE:-create}" in
        create)
            printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
            ;;
        dedup|comment-fail|comment-no-url|tier-b-accept|tier-b-unsafe|tier-b-sensitive)
            printf '{"number":7,"body":"contains <!-- larch-stall:signature=%s --> marker","pull_request":null}\n' "$GH_MARKER_HASH"
            ;;
        page2)
            printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
            printf '{"number":9,"body":"page 2 <!-- larch-stall:signature=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef -->","pull_request":null}'
            ;;
        pr-ignore)
            printf '{"number":3,"body":"<!-- larch-stall:signature=%s -->","pull_request":{}}\n' "$GH_MARKER_HASH"
            ;;
        lookup-fail)
            echo lookup failed >&2
            exit 2
            ;;
    esac
    exit 0
fi
if [ "$1" = api ] && [ "${2:-}" = --method ]; then
    input=""
    prev=""
    for arg in "$@"; do
        if [ "$prev" = --input ]; then input=$arg; fi
        prev=$arg
    done
    [ -n "$input" ] && cp "$input" "$GH_COMMENT_CAPTURE"
    if [ "${GH_STUB_CASE:-}" = comment-fail ]; then
        echo comment failed >&2
        exit 1
    fi
    if [ "${GH_STUB_CASE:-}" = comment-no-url ]; then
        printf '%s\n' '{}'
        exit 0
    fi
    printf '%s\n' '{"html_url":"https://github.com/owner/repo/issues/7#issuecomment-99"}'
    exit 0
fi
if [ "$1" = issue ] && [ "${2:-}" = create ]; then
    if [ "${GH_STUB_CASE:-}" = create-fail ]; then
        echo create failed >&2
        exit 1
    fi
    printf '%s\n' 'https://github.com/owner/repo/issues/42'
    exit 0
fi
echo unexpected gh: "$*" >&2
exit 9
STUB
    chmod +x "$dir/bin/gh"
    printf '%s\n' "$dir"
}

run_script() {
    local dir=$1 out=$2; shift 2
    set +e
    PATH="$dir/bin:$PATH" GH_STUB_CASE="${GH_STUB_CASE:-}" GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_ISSUE_MUTATION_DENY="" "$SCRIPT" "$@" --mutation-context "$LIVE_CONTEXT" --run-id run-1 >"$out" 2>"$out.err"
    local rc=$?
    set -e
    return "$rc"
}

run_script_dry() {
    local dir=$1 out=$2; shift 2
    set +e
    PATH="$dir/bin:$PATH" GH_STUB_CASE="${GH_STUB_CASE:-}" GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_ISSUE_MUTATION_DENY="" "$SCRIPT" "$@" >"$out" 2>"$out.err"
    local rc=$?
    set -e
    return "$rc"
}

dir=$(make_case create)
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "create: status filed"
assert_eq https://github.com/owner/repo/issues/42 "$(kv FILE_FAILURE_REPORT_URL "$dir/out")" "create: issue URL normalized"
contains "$dir/gh.log" 'issue create -R owner/repo --title Report title --body-file' "create: uses gh issue create -R with title"

dir=$(make_case dedup)
GH_STUB_CASE=dedup; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --attempts-file "$dir/attempts.md" --escalation-ledger-file "$dir/escalation.md" --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: status comment"
assert_eq https://github.com/owner/repo/issues/7#issuecomment-99 "$(kv FILE_FAILURE_REPORT_URL "$dir/out")" "dedup: comment URL preserved"
contains "$dir/comment.json" '+1 occurrence' "dedup: comment includes occurrence line"
contains "$dir/comment.json" 'Bounded root-cause slice.' "dedup: comment includes root cause"
not_contains "$dir/comment.json" 'Full report body sentinel.' "dedup: comment does not repost body"
not_contains "$dir/gh.log" 'issue create' "dedup: skips create"

dir=$(make_case page2)
GH_STUB_CASE=page2; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: match after first page found"

dir=$(make_case pr-ignore)
GH_STUB_CASE=pr-ignore; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: pull request marker ignored"

dir=$(make_case no-match)
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --dedup-only
assert_eq no-match "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup-only: no match"

dir=$(make_case lookup-fail)
GH_STUB_CASE=lookup-fail; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --dedup-only
assert_eq lookup-failed-open "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup-only: lookup failure fails open"

missing=$(make_case missing-marker)
printf 'no marker\n' >"$missing/body.md"
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$missing" "$missing/out" --repo owner/repo --body-file "$missing/body.md" --dedup-only
assert_eq lookup-failed-open "$(kv FILE_FAILURE_REPORT_STATUS "$missing/out")" "dedup-only: missing marker fails open"
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$missing" "$missing/out2" --repo owner/repo --body-file "$missing/body.md" --title 'Report title'
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$missing/out2")" "create: missing marker falls back"

dir=$(make_case comment-fail)
GH_STUB_CASE=comment-fail; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: comment failure falls back"
not_contains "$dir/gh.log" 'issue create' "dedup: comment failure does not create duplicate"

dir=$(make_case comment-no-url)
GH_STUB_CASE=comment-no-url; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: comment success without URL falls back"
assert_eq comment-url-missing "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out")" "dedup: missing comment URL reason"
not_contains "$dir/out" 'FILE_FAILURE_REPORT_URL=' "dedup: missing comment URL omits URL"

dir=$(make_case create-fail)
GH_STUB_CASE=create-fail; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "create: failure falls back"

dir=$(make_case symlink-body)
ln -sf "$dir/body.md" "$dir/body-link.md"
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body-link.md" --title 'Report title'
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "validation: body symlink fails closed"

dir=$(make_case missing-structured)
GH_STUB_CASE=dedup; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --attempts-file "$dir/missing.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "validation: missing structured payload fails closed"

dir=$(make_case dry-run)
GH_STUB_CASE=dedup; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --dry-run
assert_eq dry-run "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dry-run: status"
if [ ! -e "$dir/gh.log" ]; then pass "dry-run: no gh calls"; else fail "dry-run: no gh calls" "$(cat "$dir/gh.log")"; fi

dir=$(make_case tier-b-accept)
GH_STUB_CASE=tier-b-accept; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --attempts-file "$dir/attempts.md" --escalation-ledger-file "$dir/escalation.md" --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: bounded public slices accepted"

dir=$(make_case tier-b-unsafe)
printf '### [Bug] /implement terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"
GH_STUB_CASE=tier-b-unsafe; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: raw body comment rejected"

dir=$(make_case tier-b-sensitive)
printf 'client-secret-token\n' >"$dir/root.md"
GH_STUB_CASE=tier-b-sensitive; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: sensitive-token rejection reused"

dir=$(make_case tier-b-missing-corpus)
rm -f "$dir/stall-recovery-sensitive-corpus.env"
GH_STUB_CASE=tier-b-sensitive; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: missing sensitive corpus falls back"
assert_eq unsafe-tier-b-comment "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out")" "tier-b: missing sensitive corpus reports unsafe comment"

dir=$(make_case tier-b-missing-validator)
fake_root="$dir/fake-plugin"
mkdir -p "$fake_root/scripts"
cp "$SCRIPT" "$fake_root/scripts/file-failure-report-cross-repo.sh"
chmod +x "$fake_root/scripts/file-failure-report-cross-repo.sh"
mkdir -p "$fake_root/python"
cp "$SCRIPT_DIR/../python/cli.py" "$fake_root/python/cli.py"
cp -R "$SCRIPT_DIR/../python/larch" "$fake_root/python/"
rm "$fake_root/python/larch/state/_report.py"
GH_STUB_CASE=tier-b-sensitive; export GH_STUB_CASE
set +e
PATH="$dir/bin:$PATH" GH_STUB_CASE="$GH_STUB_CASE" GH_STUB_LOG="$dir/gh-validator.log" GH_COMMENT_CAPTURE="$dir/comment-validator.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_ISSUE_MUTATION_DENY="" "$fake_root/scripts/file-failure-report-cross-repo.sh" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md" --mutation-context "$LIVE_CONTEXT" --run-id run-1 >"$dir/out-validator" 2>"$dir/out-validator.err"
rc=$?
set -e
assert_eq 0 "$rc" "tier-b: missing validator exits 0"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-validator")" "tier-b: missing validator falls back"
assert_eq unsafe-tier-b-comment "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-validator")" "tier-b: missing validator reports unsafe comment"



dir=$(make_case design-prefix-dedup)
sed 's#/implement#/design#g' "$dir/body.md" >"$dir/design-body.md"
printf 'design-only-secret\n' >"$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE=dedup; export GH_STUB_CASE; run_script "$dir" "$dir/out-design" --repo owner/repo --body-file "$dir/design-body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$dir/design-failure-sensitive-corpus.env" --attempts-file "$dir/attempts.md" --escalation-ledger-file "$dir/escalation.md" --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design")" "design-prefix: duplicate comments with explicit corpus"
contains "$dir/comment.json" '+1 occurrence' "design-prefix: comment includes occurrence line"

dir=$(make_case design-prefix-raw-heading)
printf '### [Bug] /design terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"
printf 'design-only-secret\n' >"$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE=tier-b-unsafe; export GH_STUB_CASE; run_script "$dir" "$dir/out-design-raw" --repo owner/repo --body-file "$dir/body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$dir/design-failure-sensitive-corpus.env" --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design-raw")" "design-prefix: raw /design heading rejected"

dir=$(make_case design-prefix-missing-corpus)
missing_corpus="$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE=tier-b-sensitive; export GH_STUB_CASE; run_script "$dir" "$dir/out-design-missing" --repo owner/repo --body-file "$dir/body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$missing_corpus" --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design-missing")" "design-prefix: missing explicit corpus falls back"
assert_eq invalid-sensitive-corpus-file "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-design-missing")" "design-prefix: missing explicit corpus reason"

dir=$(make_case tier-b-create-sensitive)
printf 'client-secret-token\n' >>"$dir/body.md"
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out-create-sensitive" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-create-sensitive")" "tier-b: create path rejects sensitive body"
assert_eq unsafe-tier-b-body "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-create-sensitive")" "tier-b: create path reports unsafe body"
not_contains "$dir/gh.log" 'issue create' "tier-b: sensitive create skips gh issue create"

if [ "$FAIL" -ne 0 ]; then
    echo "FAILURES: $FAIL"
    exit 1
fi
echo "PASS: $PASS"
