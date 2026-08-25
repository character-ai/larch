#!/usr/bin/env bash
# test-file-failure-report-cross-repo.sh — offline harness for cross-repo failure filing.

unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_SCRIPT="$SCRIPT_DIR/file-failure-report-cross-repo.sh"
TMPROOT=$(mktemp -d "${TMPDIR:-/tmp}/larch-cross-repo-report.XXXXXX")
trap 'rm -rf "$TMPROOT"' EXIT

HARNESS_PLUGIN_ROOT="$TMPROOT/plugin"
mkdir -p "$HARNESS_PLUGIN_ROOT/scripts"
cp "$SOURCE_SCRIPT" "$HARNESS_PLUGIN_ROOT/scripts/file-failure-report-cross-repo.sh"
cat >"$HARNESS_PLUGIN_ROOT/scripts/larch.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
# The Rust `session check-live-mutation-auth` owner stands in here the same way
# the Tier-B validator does below. Its real containment and run-identity rules
# are covered by crates/larch-adapters/src/github/mutation_auth.rs and the
# session-check-live-mutation-auth-* parity goldens; this stub only has to make
# the refusal matrix's accept and refuse cases reachable.
if [ "${1:-}" = session ] && [ "${2:-}" = check-live-mutation-auth ]; then
    shift 2
    context_file=""
    run_id=""
    trusted_root=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --context-file) context_file=${2:-}; shift 2 ;;
            --run-id) run_id=${2:-}; shift 2 ;;
            --trusted-root) trusted_root=${2:-}; shift 2 ;;
            *) shift ;;
        esac
    done
    [ "${LARCH_ISSUE_MUTATION_DENY:-}" = true ] && exit 5
    [ -n "$context_file" ] && [ -n "$run_id" ] && [ -n "$trusted_root" ] || exit 5
    [ -f "$context_file" ] && [ ! -L "$context_file" ] || exit 5
    [ -d "$trusted_root" ] || exit 5
    case "$(basename "$trusted_root")" in
        claude-design-*|claude-implement-*) ;;
        *) exit 5 ;;
    esac
    [ "$(cd "$(dirname "$context_file")" && pwd -P)" = "$(cd "$trusted_root" && pwd -P)" ] || exit 5
    grep -qx "LARCH_LIVE_MUTATION_OK=true" "$context_file" || exit 5
    grep -qx "LARCH_RUN_ID=$run_id" "$context_file" || exit 5
    exit 0
fi
if [ "${1:-}" = stall-recovery ] && [ "${2:-}" = rewind-public-fd ]; then
    shift 2
    [ "${1:-}" = --public-fd ] || exit 2
    python3 -c 'import os,sys; os.lseek(int(sys.argv[1]), 0, os.SEEK_SET)' "$2"
    exit 0
fi
if [ "${1:-}" = stall-recovery ] && [ "${2:-}" = compose-comment-request ]; then
    shift 2
    public_fd=""
    snapshot_fd=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --public-fd) public_fd=${2:-}; shift 2 ;;
            --snapshot-fd) snapshot_fd=${2:-}; shift 2 ;;
            *) shift ;;
        esac
    done
    python3 - "$public_fd" "$snapshot_fd" <<'PY'
import json
import os
import sys

public_fd = int(sys.argv[1])
snapshot_fd = int(sys.argv[2])
os.lseek(public_fd, 0, os.SEEK_SET)
with os.fdopen(os.dup(public_fd), encoding="utf-8") as source:
    request = json.dumps({"body": source.read()})
os.lseek(snapshot_fd, 0, os.SEEK_SET)
os.ftruncate(snapshot_fd, 0)
os.write(snapshot_fd, request.encode())
os.lseek(snapshot_fd, 0, os.SEEK_SET)
PY
    exit 0
fi
if [ "${1:-}" = stall-recovery ] && [ "${2:-}" = comment-url-from-response ]; then
    shift 2
    response_file=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --response-file) response_file=${2:-}; shift 2 ;;
            *) shift 2 ;;
        esac
    done
    python3 - "$response_file" <<'PY'
import json
import re
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as response:
        url = json.load(response).get("html_url", "")
except Exception:
    url = ""
if isinstance(url, str) and re.fullmatch(r"https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+#issuecomment-[0-9]+", url):
    print(url)
PY
    exit 0
fi
if [ "${1:-}" = stall-recovery ] && [ "${2:-}" = find-open-stall-issue ]; then
    shift 2
    marker=""
    issues_file=""
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --marker) marker=${2:-}; shift 2 ;;
            --issues-file) issues_file=${2:-}; shift 2 ;;
            *) shift 2 ;;
        esac
    done
    python3 - "$marker" "$issues_file" <<'PY'
import json
import sys

marker = f"<!-- larch-stall:signature={sys.argv[1]} -->"
with open(sys.argv[2], encoding="utf-8", errors="replace") as issues:
    for line in issues:
        if not line.strip():
            continue
        issue = json.loads(line)
        if issue.get("pull_request") is not None:
            continue
        if marker in (issue.get("body") or ""):
            print(issue.get("number") or "")
            sys.exit(0)
sys.exit(1)
PY
    exit $?
fi
[ "${1:-}" = stall-recovery ] && [ "${2:-}" = validate-tier-b-public-file ] || exit 2
shift 2
public_file=""
public_fd=""
corpus_file=""
publication_tier="tier-b"
snapshot_fd=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --public-file) public_file=${2:-}; shift 2 ;;
        --public-fd) public_fd=${2:-}; shift 2 ;;
        --sensitive-corpus-file) corpus_file=${2:-}; shift 2 ;;
        --publication-tier) publication_tier=${2:-}; shift 2 ;;
        --snapshot-fd) snapshot_fd=${2:-}; shift 2 ;;
        --profile|--artifact-prefix|--implement-tmpdir) shift 2 ;;
        *) shift ;;
    esac
done
should_mutate_public_file() {
    local candidate=$1 basename
    basename=$(basename "$candidate")
    if [ -n "${LARCH_STUB_MUTATE_BASENAME:-}" ] && [ "$LARCH_STUB_MUTATE_BASENAME" = "$basename" ]; then
        return 0
    fi
    if [ -n "${LARCH_STUB_MUTATE_BASENAME_PREFIX:-}" ]; then
        case "$basename" in
            "$LARCH_STUB_MUTATE_BASENAME_PREFIX"*) return 0 ;;
        esac
    fi
    return 1
}
mutate_public_file_after_snapshot() {
    local candidate=$1
    case "${LARCH_STUB_MUTATE_AFTER_SNAPSHOT:-}" in
        pathname-replace)
            printf 'late-public-secret\n' >"$candidate.replacement"
            mv "$candidate.replacement" "$candidate"
            ;;
        append)
            printf 'late-public-secret\n' >>"$candidate"
            ;;
        truncate)
            : >"$candidate"
            ;;
        symlink-substitute)
            mv "$candidate" "$candidate.original"
            printf 'late-public-secret\n' >"$candidate.replacement"
            ln -s "$(basename "$candidate.replacement")" "$candidate"
            ;;
    esac
}
if [ -n "$public_fd" ]; then
    case "$public_fd" in
        3|4|5|6|7|8|9) public_file="/dev/fd/$public_fd" ;;
        *) exit 1 ;;
    esac
fi
printf '%s\n' "$public_file" >>"${LARCH_STUB_LOG:?}"
if [ -n "$public_fd" ]; then
    python3 - "$public_fd" <<'PY'
import os
import stat
import sys

try:
    mode = os.fstat(int(sys.argv[1])).st_mode
except OSError:
    sys.exit(1)
sys.exit(0 if stat.S_ISREG(mode) else 1)
PY
else
    [ -f "$public_file" ] && [ ! -L "$public_file" ] || exit 1
fi
if [ "$publication_tier" = tier-b ]; then
    [ -f "$corpus_file" ] && [ ! -L "$corpus_file" ] || exit 1
    while IFS= read -r token; do
        [ -n "$token" ] || continue
        if grep -Fq -- "$token" "$public_file"; then
            printf '%s\n' 'PUBLIC_FILE_VALID=false'
            exit 1
        fi
    done <"$corpus_file"
fi
if [ -n "$public_fd" ]; then
    python3 -c 'import os,sys; os.lseek(int(sys.argv[1]), 0, os.SEEK_SET)' "$public_fd"
fi
if [ -n "$snapshot_fd" ]; then
    case "$snapshot_fd" in
        3|4|5|6|7|8|9) ;;
        *) exit 1 ;;
    esac
    cat "$public_file" >"/dev/fd/$snapshot_fd"
    if should_mutate_public_file "$public_file"; then
        mutate_public_file_after_snapshot "$public_file"
        [ "${LARCH_STUB_REJECT_AFTER_MUTATION:-}" = true ] && exit 1
    fi
fi
if [ -n "$snapshot_fd" ]; then
    printf 'PUBLIC_FILE_SNAPSHOT_FD=%s\n' "$snapshot_fd"
fi
printf '%s\n' 'PUBLIC_FILE_VALID=true'
STUB
chmod +x "$HARNESS_PLUGIN_ROOT/scripts/file-failure-report-cross-repo.sh" "$HARNESS_PLUGIN_ROOT/scripts/larch.sh"
SCRIPT="$HARNESS_PLUGIN_ROOT/scripts/file-failure-report-cross-repo.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; shift || true; [ "$#" -gt 0 ] && printf '%s\n' "$*" | sed 's/^/    /'; }
contains() { local file=$1 needle=$2 label=$3; if grep -Fq -- "$needle" "$file"; then pass "$label"; else fail "$label" "missing: $needle" "$(cat "$file" 2>/dev/null || true)"; fi; }
not_contains() { local file=$1 needle=$2 label=$3; if grep -Fq -- "$needle" "$file"; then fail "$label" "unexpected: $needle" "$(cat "$file")"; else pass "$label"; fi; }
assert_eq() { local exp=$1 act=$2 label=$3; if [ "$exp" = "$act" ]; then pass "$label"; else fail "$label" "expected=$exp actual=$act"; fi; }
kv() { awk -v k="$1" 'BEGIN{p=k"="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$2"; }

MARKER_HASH=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
LIVE_ROOT="$TMPROOT/claude-implement-test"
LIVE_CONTEXT="$LIVE_ROOT/session-env.sh"
mkdir -p "$LIVE_ROOT"
printf 'LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run-1\n' >"$LIVE_CONTEXT"

make_case() {
    local name=$1 dir
    dir="$TMPROOT/$name"
    mkdir -p "$dir/bin"
    cat >"$dir/body.md" <<EOF2
### [BUG] /implement terminal: fixture

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
if [ "$1" = api ] && [ "${2:-}" = --jq ]; then
    case "${GH_STUB_CASE:-create}" in
        create)
            printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
            ;;
        dedup|comment-fail|comment-no-url|tier-b-accept|tier-b-unsafe|tier-b-sensitive)
            printf '{"number":7,"body":"contains <!-- larch-stall:signature=%s --> marker","pull_request":null}\n' "$GH_MARKER_HASH"
            ;;
        page2)
            printf '%s\n' '{"number":1,"body":"different","pull_request":null}'
            ;;
        pr-ignore)
            printf '{"number":3,"body":"<!-- larch-stall:signature=%s -->","pull_request":{}}\n' "$GH_MARKER_HASH"
            ;;
        full-page-with-prs)
            index=1
            while [ "$index" -le 100 ]; do
                printf '{"number":%s,"body":"different","pull_request":{}}\n' "$index"
                index=$((index + 1))
            done
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
    body_file=""
    previous=""
    for argument in "$@"; do
        if [ "$previous" = --body-file ]; then body_file=$argument; fi
        previous=$argument
    done
    [ -n "$body_file" ] && cp "$body_file" "$GH_BODY_CAPTURE"
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
    PATH="$dir/bin:$PATH" GH_STUB_CASE="${GH_STUB_CASE:-}" GH_STUB_LOG="$dir/gh.log" GH_BODY_CAPTURE="$dir/create-body.md" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_STUB_LOG="$dir/larch.log" LARCH_ISSUE_MUTATION_DENY="" "$SCRIPT" "$@" --mutation-context "$LIVE_CONTEXT" --run-id run-1 --trusted-root "$LIVE_ROOT" >"$out" 2>"$out.err"
    local rc=$?
    set -e
    return "$rc"
}

run_script_dry() {
    local dir=$1 out=$2; shift 2
    set +e
    PATH="$dir/bin:$PATH" GH_STUB_CASE="${GH_STUB_CASE:-}" GH_STUB_LOG="$dir/gh.log" GH_BODY_CAPTURE="$dir/create-body.md" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_STUB_LOG="$dir/larch.log" LARCH_ISSUE_MUTATION_DENY="" "$SCRIPT" "$@" >"$out" 2>"$out.err"
    local rc=$?
    set -e
    return "$rc"
}

dir=$(make_case create)
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "create: status filed"
assert_eq https://github.com/owner/repo/issues/42 "$(kv FILE_FAILURE_REPORT_URL "$dir/out")" "create: issue URL normalized"
contains "$dir/gh.log" 'issue create -R owner/repo --title /implement terminal: fixture --body-file' "create: uses the approved report title"

assert_create_snapshot_race() {
    local tier=$1 mutation=$2 label=$3 expected_title
    local race_dir
    race_dir=$(make_case "snapshot-$label")
    GH_STUB_CASE=create; export GH_STUB_CASE
    LARCH_STUB_MUTATE_BASENAME=body.md
    LARCH_STUB_MUTATE_AFTER_SNAPSHOT=$mutation
    export LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT
    run_script "$race_dir" "$race_dir/out" --repo owner/repo --body-file "$race_dir/body.md" --title 'Report title' --publication-tier "$tier"
    assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$race_dir/out")" "snapshot-$label: status filed"
    contains "$race_dir/create-body.md" 'Full report body sentinel.' "snapshot-$label: captures approved body"
    not_contains "$race_dir/create-body.md" 'late-public-secret' "snapshot-$label: never publishes replacement bytes"
    expected_title='/implement terminal: fixture'
    if [ "$tier" = tier-b ]; then
        expected_title='[BUG] /implement terminal: fixture'
    fi
    contains "$race_dir/gh.log" "issue create -R owner/repo --title $expected_title --body-file" "snapshot-$label: title stays bound to approved body"
    unset LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT
}

assert_create_snapshot_race tier-a pathname-replace tier-a-pathname-replace
assert_create_snapshot_race tier-a append tier-a-in-place-append
assert_create_snapshot_race tier-b pathname-replace tier-b-pathname-replace
assert_create_snapshot_race tier-b append tier-b-in-place-append
assert_create_snapshot_race tier-b truncate tier-b-in-place-truncate

assert_snapshot_handoff_refusal() {
    local mutation=$1 label=$2 refusal_dir
    refusal_dir=$(make_case "snapshot-refusal-$label")
    GH_STUB_CASE=create; export GH_STUB_CASE
    LARCH_STUB_MUTATE_BASENAME=body.md
    LARCH_STUB_MUTATE_AFTER_SNAPSHOT=$mutation
    LARCH_STUB_REJECT_AFTER_MUTATION=true
    export LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT LARCH_STUB_REJECT_AFTER_MUTATION
    run_script "$refusal_dir" "$refusal_dir/out" --repo owner/repo --body-file "$refusal_dir/body.md" --title 'Report title'
    assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$refusal_dir/out")" "snapshot-refusal-$label: mutation falls back"
    assert_eq invalid-body-snapshot "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$refusal_dir/out")" "snapshot-refusal-$label: mutation reason"
    if [ -f "$refusal_dir/gh.log" ]; then
        not_contains "$refusal_dir/gh.log" '.*' "snapshot-refusal-$label: skips gh"
    else
        pass "snapshot-refusal-$label: skips gh"
    fi
    unset LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT LARCH_STUB_REJECT_AFTER_MUTATION
}

assert_snapshot_handoff_refusal pathname-replace pathname-replace
assert_snapshot_handoff_refusal append in-place-append
assert_snapshot_handoff_refusal truncate in-place-truncate
assert_snapshot_handoff_refusal symlink-substitute symlink-substitute

dir=$(make_case snapshot-tier-b-comment-symlink)
GH_STUB_CASE=dedup; export GH_STUB_CASE
LARCH_STUB_MUTATE_BASENAME_PREFIX=.larch-public-comment.
LARCH_STUB_MUTATE_AFTER_SNAPSHOT=symlink-substitute
export LARCH_STUB_MUTATE_BASENAME_PREFIX LARCH_STUB_MUTATE_AFTER_SNAPSHOT
run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "snapshot-tier-b-comment-symlink: status comment"
contains "$dir/comment.json" 'Bounded root-cause slice.' "snapshot-tier-b-comment-symlink: captures approved comment"
not_contains "$dir/comment.json" 'late-public-secret' "snapshot-tier-b-comment-symlink: never publishes replacement bytes"
unset LARCH_STUB_MUTATE_BASENAME_PREFIX LARCH_STUB_MUTATE_AFTER_SNAPSHOT

dir=$(make_case snapshot-tier-b-comment-append)
GH_STUB_CASE=dedup; export GH_STUB_CASE
LARCH_STUB_MUTATE_BASENAME_PREFIX=.larch-public-comment.
LARCH_STUB_MUTATE_AFTER_SNAPSHOT=append
export LARCH_STUB_MUTATE_BASENAME_PREFIX LARCH_STUB_MUTATE_AFTER_SNAPSHOT
run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "snapshot-tier-b-comment-append: status comment"
contains "$dir/comment.json" 'Bounded root-cause slice.' "snapshot-tier-b-comment-append: captures approved comment"
not_contains "$dir/comment.json" 'late-public-secret' "snapshot-tier-b-comment-append: never publishes appended bytes"
unset LARCH_STUB_MUTATE_BASENAME_PREFIX LARCH_STUB_MUTATE_AFTER_SNAPSHOT

dir=$(make_case snapshot-marker-lookup)
GH_STUB_CASE=dedup; export GH_STUB_CASE
LARCH_STUB_MUTATE_BASENAME=body.md
LARCH_STUB_MUTATE_AFTER_SNAPSHOT=pathname-replace
export LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT
run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "snapshot-marker-lookup: approved marker still deduplicates"
not_contains "$dir/gh.log" 'issue create' "snapshot-marker-lookup: replacement marker cannot create"
unset LARCH_STUB_MUTATE_BASENAME LARCH_STUB_MUTATE_AFTER_SNAPSHOT

for refusal_case in missing-context missing-trusted-root invalid-context outside-root ambient-only test-denied; do
    dir=$(make_case "refusal-$refusal_case")
    case "$refusal_case" in
        missing-context)
            run_script_dry "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
            ;;
        missing-trusted-root)
            PATH="$dir/bin:$PATH" GH_STUB_CASE=create GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" "$SCRIPT" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --mutation-context "$LIVE_CONTEXT" --run-id run-1 >"$dir/out" 2>"$dir/out.err" || true
            ;;
        invalid-context)
            printf 'LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=wrong\n' >"$LIVE_ROOT/invalid-context.sh"
            PATH="$dir/bin:$PATH" GH_STUB_CASE=create GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" "$SCRIPT" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --mutation-context "$LIVE_ROOT/invalid-context.sh" --run-id run-1 --trusted-root "$LIVE_ROOT" >"$dir/out" 2>"$dir/out.err" || true
            ;;
        outside-root)
            outside_root="$TMPROOT/claude-implement-attacker"
            mkdir -p "$outside_root"
            printf 'LARCH_LIVE_MUTATION_OK=true\nLARCH_RUN_ID=run-1\n' >"$outside_root/session-env.sh"
            PATH="$dir/bin:$PATH" GH_STUB_CASE=create GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" "$SCRIPT" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --mutation-context "$outside_root/session-env.sh" --run-id run-1 --trusted-root "$LIVE_ROOT" >"$dir/out" 2>"$dir/out.err" || true
            ;;
        ambient-only)
            LARCH_LIVE_MUTATION_OK=true run_script_dry "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
            ;;
        test-denied)
            set +e
            PATH="$dir/bin:$PATH" GH_STUB_CASE=create GH_STUB_LOG="$dir/gh.log" GH_COMMENT_CAPTURE="$dir/comment.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_ISSUE_MUTATION_DENY=true "$SCRIPT" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --mutation-context "$LIVE_CONTEXT" --run-id run-1 --trusted-root "$LIVE_ROOT" >"$dir/out" 2>"$dir/out.err"
            set -e
            ;;
    esac
    assert_eq mutation-refused "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "refusal-$refusal_case: mutation refused"
    if [ -f "$dir/gh.log" ]; then
        not_contains "$dir/gh.log" '.*' "refusal-$refusal_case: skips gh"
    else
        pass "refusal-$refusal_case: skips gh"
    fi
done

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
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: older pages are not searched"
contains "$dir/gh.log" 'state=open&sort=created&direction=desc&per_page=100' "dedup: requests the newest 100 rows"
not_contains "$dir/gh.log" '--paginate' "dedup: does not paginate beyond the cap"

dir=$(make_case pr-ignore)
GH_STUB_CASE=pr-ignore; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: pull request marker ignored"

dir=$(make_case full-page-with-prs)
GH_STUB_CASE=full-page-with-prs; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title'
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup: full pull-request page has no issue match"
contains "$dir/out.err" 'WARN: stall-report dedup reached the 100-record recent-open cap' "dedup: full raw page reports omitted history"

dir=$(make_case no-match)
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --dedup-only
assert_eq no-match "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup-only: no match"

dir=$(make_case lookup-fail)
GH_STUB_CASE=lookup-fail; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --dedup-only
assert_eq lookup-failed-open "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "dedup-only: lookup failure fails open"

dir=$(make_case lookup-fail-create)
GH_STUB_CASE=lookup-fail; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-a --create-on-lookup-failure
assert_eq filed "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-a: lookup failure creates from approved snapshot"
contains "$dir/create-body.md" 'Full report body sentinel.' "tier-a: lookup failure captures approved create body"
contains "$dir/gh.log" 'issue create -R owner/repo' "tier-a: lookup failure reaches create"

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
GH_STUB_CASE='tier-b-accept'; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --attempts-file "$dir/attempts.md" --escalation-ledger-file "$dir/escalation.md" --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: bounded public slices accepted"
contains "$dir/larch.log" ".larch-public-comment." "tier-b: validation routes through larch runtime"

dir=$(make_case tier-b-unsafe)
printf '### [BUG] /implement terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"
GH_STUB_CASE='tier-b-unsafe'; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: raw body comment rejected"

dir=$(make_case tier-b-unsafe-legacy-bug)
printf '### [Bug] /implement terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"  # lint-prefix-case-variant: ok intentional legacy wrong-case heading fixture
GH_STUB_CASE='tier-b-unsafe'; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: legacy [Bug] raw heading rejected"  # lint-prefix-case-variant: ok paired assertion for legacy wrong-case heading fixture

dir=$(make_case tier-b-sensitive)
printf 'client-secret-token\n' >"$dir/root.md"
GH_STUB_CASE='tier-b-sensitive'; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: sensitive-token rejection reused"

dir=$(make_case tier-b-missing-corpus)
rm -f "$dir/stall-recovery-sensitive-corpus.env"
GH_STUB_CASE='tier-b-sensitive'; export GH_STUB_CASE; run_script "$dir" "$dir/out" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out")" "tier-b: missing sensitive corpus falls back"
assert_eq unsafe-tier-b-comment "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out")" "tier-b: missing sensitive corpus reports unsafe comment"

dir=$(make_case tier-b-missing-validator)
fake_root="$dir/fake-plugin"
mkdir -p "$fake_root/scripts"
cp "$SOURCE_SCRIPT" "$fake_root/scripts/file-failure-report-cross-repo.sh"
chmod +x "$fake_root/scripts/file-failure-report-cross-repo.sh"
cp "$HARNESS_PLUGIN_ROOT/scripts/larch.sh" "$fake_root/scripts/larch.sh"
chmod +x "$fake_root/scripts/larch.sh"
GH_STUB_CASE='tier-b-sensitive'; export GH_STUB_CASE
set +e
PATH="$dir/bin:$PATH" GH_STUB_CASE="$GH_STUB_CASE" GH_STUB_LOG="$dir/gh-validator.log" GH_COMMENT_CAPTURE="$dir/comment-validator.json" GH_MARKER_HASH="$MARKER_HASH" LARCH_ISSUE_MUTATION_DENY="" "$fake_root/scripts/file-failure-report-cross-repo.sh" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b --root-cause-file "$dir/root.md" --mutation-context "$LIVE_CONTEXT" --run-id run-1 --trusted-root "$LIVE_ROOT" >"$dir/out-validator" 2>"$dir/out-validator.err"
rc=$?
set -e
assert_eq 0 "$rc" "tier-b: missing validator exits 0"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-validator")" "tier-b: missing validator falls back"
assert_eq invalid-body-snapshot "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-validator")" "tier-b: missing validator blocks body snapshot"



dir=$(make_case design-prefix-dedup)
sed 's#/implement#/design#g' "$dir/body.md" >"$dir/design-body.md"
printf 'design-only-secret\n' >"$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE=dedup; export GH_STUB_CASE; run_script "$dir" "$dir/out-design" --repo owner/repo --body-file "$dir/design-body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$dir/design-failure-sensitive-corpus.env" --attempts-file "$dir/attempts.md" --escalation-ledger-file "$dir/escalation.md" --root-cause-file "$dir/root.md"
assert_eq dedup-comment "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design")" "design-prefix: duplicate comments with explicit corpus"
contains "$dir/comment.json" '+1 occurrence' "design-prefix: comment includes occurrence line"

dir=$(make_case design-prefix-raw-heading)
printf '### [BUG] /design terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"
printf 'design-only-secret\n' >"$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE='tier-b-unsafe'; export GH_STUB_CASE; run_script "$dir" "$dir/out-design-raw" --repo owner/repo --body-file "$dir/body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$dir/design-failure-sensitive-corpus.env" --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design-raw")" "design-prefix: raw /design heading rejected"

dir=$(make_case design-prefix-raw-heading-legacy-bug)
printf '### [Bug] /design terminal: raw\n\n<!-- larch-stall:signature=%s -->\n' "$MARKER_HASH" >"$dir/root.md"  # lint-prefix-case-variant: ok intentional legacy wrong-case heading fixture
printf 'design-only-secret\n' >"$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE='tier-b-unsafe'; export GH_STUB_CASE; run_script "$dir" "$dir/out-design-raw-legacy" --repo owner/repo --body-file "$dir/body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$dir/design-failure-sensitive-corpus.env" --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design-raw-legacy")" "design-prefix: legacy [Bug] raw /design heading rejected"  # lint-prefix-case-variant: ok paired assertion for legacy wrong-case heading fixture

dir=$(make_case design-prefix-missing-corpus)
missing_corpus="$dir/design-failure-sensitive-corpus.env"
GH_STUB_CASE='tier-b-sensitive'; export GH_STUB_CASE; run_script "$dir" "$dir/out-design-missing" --repo owner/repo --body-file "$dir/body.md" --title 'Design report title' --publication-tier tier-b --sensitive-corpus-file "$missing_corpus" --root-cause-file "$dir/root.md"
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-design-missing")" "design-prefix: missing explicit corpus falls back"
assert_eq invalid-sensitive-corpus-file "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-design-missing")" "design-prefix: missing explicit corpus reason"

dir=$(make_case tier-b-create-sensitive)
printf 'client-secret-token\n' >>"$dir/body.md"
GH_STUB_CASE=create; export GH_STUB_CASE; run_script "$dir" "$dir/out-create-sensitive" --repo owner/repo --body-file "$dir/body.md" --title 'Report title' --publication-tier tier-b
assert_eq fallback-print-required "$(kv FILE_FAILURE_REPORT_STATUS "$dir/out-create-sensitive")" "tier-b: create path rejects sensitive body"
assert_eq unsafe-tier-b-body "$(kv FILE_FAILURE_REPORT_FALLBACK_REASON "$dir/out-create-sensitive")" "tier-b: create path reports unsafe body"
not_contains "$dir/gh.log" 'issue create' "tier-b: sensitive create skips gh issue create"

if grep -q 'python3' "$SOURCE_SCRIPT"; then
    fail "runtime helper is Python-free"
else
    pass "runtime helper is Python-free"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "FAILURES: $FAIL"
    exit 1
fi
echo "PASS: $PASS"
