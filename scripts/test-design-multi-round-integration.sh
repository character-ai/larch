#!/usr/bin/env bash
# Cross-script integration: plan-review-loop multi-round output vs design-log-publish staging.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PLR="$ROOT/skills/design/scripts/plan-review-loop.sh"
PUBLISH="$ROOT/scripts/design-log-publish.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }

make_gh_stub() {
    local d="$1"
    mkdir -p "$d"
    cat >"$d/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$1" == "repo" && "$2" == "view" ]]; then
    printf '{"nameWithOwner":"owner/repo"}\n'
    exit 0
fi
if [[ "$1" == "pr" ]]; then
    case "$2" in
        create) echo "https://github.com/owner/repo/pull/101"; exit 0 ;;
        merge)
            if [[ -n "${TEST_CLONE_ROOT:-}" && -n "${TEST_MERGE_BRANCH:-}" ]]; then
                git -C "$TEST_CLONE_ROOT" fetch origin "$TEST_MERGE_BRANCH" >/dev/null 2>&1 || true
                git -C "$TEST_CLONE_ROOT" merge FETCH_HEAD -m "test merge design log" >/dev/null 2>&1 || true
                git -C "$TEST_CLONE_ROOT" push origin main >/dev/null 2>&1 || true
            fi
            exit 0
            ;;
        view) echo '{"url":"https://github.com/owner/repo/pull/101"}'; exit 0 ;;
        list) echo '101'; exit 0 ;;
    esac
fi
exit 99
EOF
    chmod +x "$d/gh"
}

setup_clone_with_origin_head() {
    local root="$1"
    local bare="$root/upstream.git"
    local clone="$root/consumer"
    rm -rf "$bare" "$clone"
    mkdir -p "$bare"
    git init -q --bare "$bare"
    git clone -q "$bare" "$clone"
    git -C "$clone" config user.email "t@t"
    git -C "$clone" config user.name "t"
    printf 'init\n' >"$clone/README.md"
    git -C "$clone" add README.md
    git -C "$clone" commit -q -m "init"
    git -C "$clone" branch -M main
    git -C "$clone" push -q -u origin main
    git -C "$clone" remote set-head origin main
    printf '%s\n' "$clone"
}

expected_round_paths() {
    local root="$1"
    (
        cd "$root/plan-review" || exit 1
        find . -type f | LC_ALL=C sort | sed 's#^\./##'
    )
}

published_round_paths() {
    local clone="$1" run_id="$2"
    (
        cd "$clone/larch-logs/design/$run_id/plan-review" || exit 1
        find . -type f | LC_ALL=C sort | sed 's#^\./##'
    )
}

run_loop_fixture() {
    local design_dir="$1"
    shift
    export CLAUDE_PLUGIN_ROOT="$ROOT"
    export LARCH_QUIET_DISABLE=1
    export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
    export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
    export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
    export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
    export LARCH_AGGREGATOR_DISABLED=1
    bash "$PLR" \
        --design-tmpdir "$design_dir" \
        --plan-file "$design_dir/plan.txt" \
        --feature-file "$design_dir/feature-description.txt" \
        --codex-present true \
        --cursor-present true \
        "$@"
}

assert_env_has_keys() {
    local path="$1"
    shift
    local key
    for key in "$@"; do
        grep -q "^${key}=" "$path" || fail "missing ${key}= in $path"
    done
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-design-mr-int.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
STUB="$TMP/stub-bin"
mkdir -p "$STUB" "$TMP/design" "$TMP/stage"

printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$TMP/design/plan.txt"
printf 'feat\n' >"$TMP/design/feature-description.txt"

cat >"$STUB/scout-plan-archetypes-wrapper.sh" <<'EOS'
#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
    case "$1" in --output) out="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
printf '%s\n' '{"archetypes":[]}' >"$out"
EOS
chmod +x "$STUB/scout-plan-archetypes-wrapper.sh"

cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 2 ;; esac
done
state_file="$DESIGN_TMPDIR/.dispatch-round-count"
round=1
if [[ -f "$state_file" ]]; then
    round=$(( $(cat "$state_file") + 1 ))
fi
printf '%s\n' "$round" >"$state_file"
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
combined=0
if [[ "$round" == "1" ]]; then
    combined=1
fi
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=%s\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\n' "$combined" "$PATHS"
EOS
chmod +x "$STUB/dispatch-plan-review-panel.sh"

cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" >"$tsv"
    printf '%s\n' "in_scope	nit	correctness	src/a	concern text here	scenario	fix" >>"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"

cat >"$STUB/dispatch-plan-voters.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
v1="$DESIGN_TMPDIR/v1.txt"
v2="$DESIGN_TMPDIR/v2.txt"
printf 'FINDING_1: YES\n' >"$v1"
printf 'FINDING_1: YES\n' >"$v2"
printf 'DISPATCH_OK=true\nVOTER_1_PATH=%s\nVOTER_1_TOOL=claude\nVOTER_1_STATUS=launched\nVOTER_2_PATH=%s\nVOTER_2_TOOL=codex\nVOTER_2_STATUS=launched\n' "$v1" "$v2"
EOS
chmod +x "$STUB/dispatch-plan-voters.sh"

cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 2 ;; esac
done
mkdir -p "$DESIGN_TMPDIR/plan-review/round-1/revise"
printf 'prompt\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/prompt.txt"
printf 'patch\n' >"$DESIGN_TMPDIR/plan-review/round-1/revise/cursor-output-candidate.patch"
printf 'REVISE_STATUS=ok\nREVISE_WINNING_TIER=stub\n'
exit 0
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"

export CLAUDE_PLUGIN_ROOT="$ROOT"
export LARCH_QUIET_DISABLE=1
export LARCH_PLAN_REVIEW_SCOUT_SH="$STUB/scout-plan-archetypes-wrapper.sh"
export LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH="$STUB/dispatch-plan-review-panel.sh"
export LARCH_PLAN_REVIEW_COLLECT_SH="$STUB/collect-agent-results.sh"
export LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH="$STUB/dispatch-plan-voters.sh"
export LARCH_PLAN_REVIEW_REVISE_SH="$STUB/revise-plan-with-waterfall.sh"
export LARCH_AGGREGATOR_DISABLED=1

out=$(run_loop_fixture "$TMP/design" --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out" | grep -q '^LOOP_STATUS=converged$' || fail "expected converged from integration loop"

[[ -d "$TMP/design/plan-review/round-1" ]] || fail "round-1 missing"
[[ -d "$TMP/design/plan-review/round-2" ]] || fail "round-2 missing"
[[ -d "$TMP/design/plan-review/round-3" ]] || fail "round-3 missing"
[[ -f "$TMP/design/plan-review/round-1/round-summary.env" ]] || fail "round-summary missing"
grep -q '^DEGRADED_PANEL=1$' "$TMP/design/plan-review/round-1/round-summary.env" || fail "round-1 summary should record degraded panel"
grep -q '^LOOP_STATUS=converged$' "$TMP/design/plan-review/round-3/round-summary.env" || fail "round-3 summary should record converged"
cmp -s "$TMP/design/plan.txt" "$TMP/design/plan-review/round-3/plan.txt" || fail "round-3 snapshot plan must match final plan"
[[ -f "$TMP/design/plan-review/round-3/findings-classification.tsv" ]] || fail "round-3 classification TSV missing"
assert_env_has_keys "$TMP/design/.step3-plan-review-result.env" LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED REASON REVISE_STATUS CONVERGENCE_STREAK AGGREGATOR_STATUS TALLY_PLAN_REVIEW_STATUS VOTING_TALLY_FILE VOTER_1_PARSE_RATE_STATUS COLLECT_OK_COUNT COLLECT_FAILURE_COUNT

# shellcheck source=scripts/lib-design-round-artifacts.sh
source "$ROOT/scripts/lib-design-round-artifacts.sh"
design_round_artifact_included unknown.bin && fail "unknown.bin must be excluded by allowlist"
design_round_artifact_included findings.md || fail "findings.md must be included"
design_round_revise_artifact_included prompt.txt || fail "prompt.txt must be included in revise/"
design_round_revise_artifact_included cursor-output-candidate.patch || fail "candidate patch must be included in revise/"
design_round_revise_artifact_included extra.log && fail "extra.log must be excluded from revise/"

# Raw reviewer output at session root must not appear in round snapshot.
[[ ! -f "$TMP/design/plan-review/round-1/cursor-plan-arch-output.txt" ]] || fail "raw reviewer output must not snapshot"

echo "=== publish parity against loop output ==="
PUBROOT="$TMP/publish"
clone=$(setup_clone_with_origin_head "$PUBROOT")
stub_publish="$PUBROOT/stub"
make_gh_stub "$stub_publish"
export PATH="$stub_publish:$PATH"
export TEST_CLONE_ROOT="$clone"
export TEST_MERGE_BRANCH="larch-log-design-RUNMRINT1"
(
    cd "$clone" || exit 1
    publish_out=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNMRINT1" --issue 42 --repo owner/repo)
    [[ "$publish_out" == *"PUBLISH_OK=true"* ]] || fail "publish parity run should succeed: $publish_out"
)
git -C "$clone" pull -q origin main
expected_paths=$(expected_round_paths "$TMP/design")
actual_paths=$(published_round_paths "$clone" "RUNMRINT1")
[[ "$expected_paths" == "$actual_paths" ]] || fail "published plan-review file list must match loop snapshot"

echo "=== publish fails closed on unknown.bin ==="
printf 'x\n' >"$TMP/design/plan-review/round-1/unknown.bin"
(
    cd "$clone" || exit 1
    publish_bad=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNMRBAD1" --issue 42 --repo owner/repo 2>/dev/null || true)
    [[ "$publish_bad" == *"PUBLISH_OK=false"* ]] || fail "unknown.bin should fail publish"
)
rm -f "$TMP/design/plan-review/round-1/unknown.bin"

echo "=== publish fails closed on unexpected revise artifact ==="
printf 'x\n' >"$TMP/design/plan-review/round-1/revise/extra.log"
(
    cd "$clone" || exit 1
    publish_revise_bad=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNMRREV1" --issue 42 --repo owner/repo 2>/dev/null || true)
    [[ "$publish_revise_bad" == *"PUBLISH_OK=false"* ]] || fail "unexpected revise artifact should fail publish"
)
rm -f "$TMP/design/plan-review/round-1/revise/extra.log"

echo "=== publish fails closed on symlink inside plan-review ==="
ln -s "$TMP/design/plan.txt" "$TMP/design/plan-review/round-1/linked.txt"
(
    cd "$clone" || exit 1
    publish_link=$(bash "$PUBLISH" --design-tmpdir "$TMP/design" --run-id "RUNMRSYM1" --issue 42 --repo owner/repo 2>/dev/null || true)
    [[ "$publish_link" == *"PUBLISH_OK=false"* ]] || fail "symlink under plan-review should fail publish"
)
rm -f "$TMP/design/plan-review/round-1/linked.txt"

echo "=== converge path writes passive-summary status ==="
DCONV="$TMP/converged"
mkdir -p "$DCONV"
printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$DCONV/plan.txt"
printf 'feat\n' >"$DCONV/feature-description.txt"
cat >"$STUB/dispatch-plan-review-panel.sh" <<'EOS'
#!/usr/bin/env bash
DESIGN_TMPDIR=""
while [[ $# -gt 0 ]]; do
    case "$1" in --design-tmpdir) DESIGN_TMPDIR="${2:?}"; shift 2 ;; *) shift 2 ;; esac
done
OUT="$DESIGN_TMPDIR/cursor-plan-arch-output.txt"
printf '%s\n' '{"slot":"cursor-plan-arch","tool":"cursor","output":"'"$OUT"'"}' >"$DESIGN_TMPDIR/plan-review-slots.ndjson"
: >"$OUT"
PATHS="$DESIGN_TMPDIR/panel-paths.txt"
printf '%s\n' "$OUT" >"$PATHS"
printf 'DISPATCH_OK=true\nFALLBACK_COUNT=0\nCOMBINED_FALLBACK_COUNT=0\nSTATIC_DISPATCH_OK=true\nPANEL_PATHS_FILE=%s\n' "$PATHS"
EOS
chmod +x "$STUB/dispatch-plan-review-panel.sh"
cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix" >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
out_conv=$(run_loop_fixture "$DCONV" --round-cap 3 --convergence-threshold 3)
printf '%s\n' "$out_conv" | grep -q '^LOOP_STATUS=converged$' || fail "zero-findings collector-ok path should converge"
grep -q '^LOOP_STATUS=converged$' "$DCONV/plan-review/round-1/round-summary.env" || fail "converged summary missing"

echo "=== manual Gate B stops after one round ==="
DMAN="$TMP/manual"
mkdir -p "$DMAN"
printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$DMAN/plan.txt"
printf 'feat\n' >"$DMAN/feature-description.txt"
printf '{"manual_gate_b":true}\n' >"$DMAN/run-params.json"
cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	nit	correctness	src/a	manual finding	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
echo "manual Gate B should not auto-revise" >&2
exit 99
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
out_man=$(run_loop_fixture "$DMAN" --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_man" | grep -q '^REASON=manual-gate-b$' || fail "manual Gate B should short-circuit with manual-gate-b"
[[ -d "$DMAN/plan-review/round-1" ]] || fail "manual Gate B should still snapshot round-1"
[[ ! -d "$DMAN/plan-review/round-2" ]] || fail "manual Gate B should stop after one round"

echo "=== revision-failed path stays on final-round findings route ==="
DRV="$TMP/revision-failed"
mkdir -p "$DRV"
printf '## Plan\n\nDo thing.\n\ndiff_lines: 3\n' >"$DRV/plan.txt"
printf 'feat\n' >"$DRV/feature-description.txt"
cat >"$STUB/collect-agent-results.sh" <<'EOS'
#!/usr/bin/env bash
paths=""
while [[ $# -gt 0 ]]; do
    case "$1" in --paths-file) paths="${2:?}"; shift 2 ;; *) shift 1 ;; esac
done
while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    tsv="${p}.tsv"
    {
        printf '%s\n' "scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix"
        printf '%s\n' "in_scope	important	correctness	src/a	revision fail finding	scenario	fix"
    } >"$tsv"
    printf 'REVIEWER_FILE=%s\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n' "$p"
done <"$paths"
EOS
chmod +x "$STUB/collect-agent-results.sh"
cat >"$STUB/revise-plan-with-waterfall.sh" <<'EOS'
#!/usr/bin/env bash
printf 'REVISE_STATUS=failed-no-patch\nREVISE_WINNING_TIER=\n'
EOS
chmod +x "$STUB/revise-plan-with-waterfall.sh"
out_rv=$(run_loop_fixture "$DRV" --round-cap 2 --convergence-threshold 3)
printf '%s\n' "$out_rv" | grep -q '^LOOP_STATUS=revision-failed$' || fail "revision-failed integration path missing"
grep -q '^LOOP_STATUS=revision-failed$' "$DRV/.step3-plan-review-result.env" || fail "revision-failed env missing"

printf '%s\n' 'test-design-multi-round-integration: ok'
