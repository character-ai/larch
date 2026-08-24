#!/usr/bin/env bash
# Black-box contract for Rust-owned plan-review panel and voter dispatch.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

binary="${LARCH_BINARY:?set LARCH_BINARY to the test larch executable}"
repo_root="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)"
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/test-plan-review-dispatch.XXXXXX")"
trap 'rm -rf -- "$tmpdir"' EXIT

launcher="$tmpdir/plugin/scripts/larch.sh"
mkdir -p "$(dirname "$launcher")"
ln -s "$repo_root/python" "$tmpdir/plugin/python"
ln -s "$repo_root/skills" "$tmpdir/plugin/skills"
cat >"$launcher" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == render && "${2:-}" == plan-review ]]; then
    exec "${LARCH_BINARY:?}" "$@"
fi

if [[ "${1:-}" == render && "${2:-}" == voter ]]; then
    exec "${LARCH_BINARY:?}" "$@"
fi

if [[ "${1:-}" == review && "${2:-}" == reviewer-prune ]]; then
    out=""
    previous=""
    for argument in "$@"; do
        [[ "$previous" == --out ]] && out="$argument"
        previous="$argument"
    done
    : >"$out"
    printf '%s\n' 'PRUNED_COUNT=99' 'PANEL_PRUNED_EMPTY=true'
    exit 0
fi

out=""
previous=""
for argument in "$@"; do
    [[ "$previous" == --output ]] && out="$argument"
    previous="$argument"
done
[[ -n "$out" ]]
printf '%s\n' "$*" >>"$(dirname "$out")/launch-argv.log"
fail_once="$(dirname "$out")/FAIL-ONCE-$(basename "$out")"
fail_always="$(dirname "$out")/FAIL-$(basename "$out")"
if [[ -f "$fail_once" ]]; then
    rm -f "$fail_once" "$out" "$out.done"
    printf '124\n' >"$out.done"
    exit 124
fi
if [[ -f "$fail_always" ]]; then
    rm -f "$out" "$out.done"
    printf '7\n' >"$out.done"
    exit 7
fi
printf 'FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\n' >"$out"
printf '0\n' >"$out.done"
EOF
chmod +x "$launcher"

fast_plugin="$tmpdir/fast-plugin"
mkdir -p "$fast_plugin/scripts"
cp "$launcher" "$fast_plugin/scripts/larch.sh"
ln -s "$repo_root/skills" "$fast_plugin/skills"

run_larch() {
    env \
        CLAUDE_PLUGIN_ROOT="$tmpdir/plugin" \
        LARCH_VOTER_CALIBRATION_FEEDBACK=0 \
        DESIGN_TMPDIR="$1" \
        "$binary" "${@:2}"
}

run_larch_fast() {
    env \
        CLAUDE_PLUGIN_ROOT="$fast_plugin" \
        LARCH_VOTER_CALIBRATION_FEEDBACK=0 \
        DESIGN_TMPDIR="$1" \
        "$binary" "${@:2}"
}

design="$tmpdir/design"
mkdir -p "$design"
printf '# Plan\n' >"$design/plan.txt"
printf '# Feature\n' >"$design/feature.md"
printf '### FINDING_1: Keep the contract\n' >"$design/ballot.md"

panel_output="$(run_larch "$design" plan-review panel-dispatch \
    --design-tmpdir "$design" --round-num 1 \
    --codex-present true --cursor-present true \
    --plan-file "$design/plan.txt" --feature-file "$design/feature.md" \
    --tier MODERATE)"
grep -qx 'STATIC_SLOT_COUNT=8' <<<"$panel_output"
grep -qx 'DYNAMIC_SLOT_COUNT=0' <<<"$panel_output"
grep -qx 'PANEL_PRUNED_EMPTY=false' <<<"$panel_output"
grep -qx 'DISPATCH_OK=true' <<<"$panel_output"
panel_paths="$(sed -n 's/^PANEL_PATHS_FILE=//p' <<<"$panel_output")"
[[ -s "$panel_paths" ]]
python3 - "$design/plan-review-slots.ndjson" <<'PY'
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
expected = [
    (f"{tool}-plan-{archetype}", tool)
    for archetype in ("arch", "innovation", "pragmatic", "requirements")
    for tool in ("cursor", "codex")
]
assert [(row["slot"], row["tool"]) for row in rows] == expected
assert all(row["archetype"] != "generic" for row in rows if "archetype" in row)
assert all(row["resolved_model"] == "gpt-5.6-terra" for row in rows if row["tool"] == "codex")
assert all(row["payload_bytes"] > 0 for row in rows)
PY
env CLAUDE_PLUGIN_ROOT="$tmpdir/plugin" LARCH_VOTER_CALIBRATION_FEEDBACK=0 \
    "$binary" render plan-review \
    --archetype arch --vendor codex \
    --plan-file "$design/plan.txt" --design-tmpdir "$design" \
    --feature-file "$design/feature.md" \
    --findings-ledger-file "$design/findings-ledger.tsv" \
    --payload-bytes-output "$tmpdir/expected-panel.payload-bytes" \
    --difficulty MODERATE >"$tmpdir/expected-panel.prompt"
cmp "$tmpdir/expected-panel.prompt" "$design/render-plan-codex-arch.prompt"
grep -q -- '--site design Step 3' "$design/plan-review/round-1/launch-argv.log"

cat >"$design/scout-plan-manifest.json" <<'EOF'
{"archetypes":[{"name":"security","focus_area":"security","prompt_body":"Check trust boundaries."}]}
EOF
dynamic_output="$(run_larch "$design" plan-review panel-dispatch \
    --design-tmpdir "$design" --round-num 1 \
    --codex-present true --cursor-present false \
    --plan-file "$design/plan.txt" --feature-file "$design/feature.md" \
    --tier TRIVIAL)"
grep -qx 'STATIC_SLOT_COUNT=4' <<<"$dynamic_output"
grep -qx 'DYNAMIC_SLOT_COUNT=2' <<<"$dynamic_output"
grep -q '"slot":"dyn-cursor-plan-security"' "$design/plan-review-slots.ndjson"
grep -q 'Check trust boundaries.' "$design/plan-review/round-1/dyn-cursor-plan-security.prompt"
grep -q '<larch_plan_under_review>' "$design/plan-review/round-1/dyn-cursor-plan-security.prompt"

set +e
failure_output="$(run_larch_fast "$design" plan-review panel-dispatch \
    --design-tmpdir "$design" --round-num 1 \
    --codex-present true --cursor-present true \
    --plan-file "$design/plan.txt" --feature-file "$design/feature.md" \
    --timeout invalid 2>"$design/panel-failure.stderr")"
failure_rc=$?
set -e
[[ "$failure_rc" == 2 ]]
grep -qx 'PANEL_DISPATCH_EXIT_CODE=2' <<<"$failure_output"
failure_log="$(sed -n 's/^PANEL_FAILURE_DETAIL_LOG=//p' <<<"$failure_output")"
[[ "$(basename "$failure_log")" == plan-review-panel-failure.log ]]
grep -q 'dispatch-waterfall' "$failure_log"

mkdir -p "$design/plan-review/round-3"
: >"$design/plan-review/round-3/FAIL-cursor-plan-arch-output.txt"
dropped_output="$(run_larch_fast "$design" plan-review panel-dispatch \
    --design-tmpdir "$design" --round-num 3 --escalated-round true \
    --codex-present true --cursor-present true \
    --plan-file "$design/plan.txt" --feature-file "$design/feature.md")"
dropped_file="$(sed -n 's/^DROPPED_SLOTS_FILE=//p' <<<"$dropped_output" | tail -1)"
[[ -s "$dropped_file" ]]
awk -F '\t' '$1 == "cursor-plan-arch" && $3 != "" { found = 1 } END { exit(found ? 0 : 1) }' "$dropped_file"

pruned_output="$(run_larch_fast "$design" plan-review panel-dispatch \
    --design-tmpdir "$design" --round-num 2 \
    --codex-present true --cursor-present true \
    --plan-file "$design/plan.txt" --feature-file "$design/feature.md")"
grep -qx 'PANEL_PRUNED_EMPTY=true' <<<"$pruned_output"
pruned_paths="$(sed -n 's/^PANEL_PATHS_FILE=//p' <<<"$pruned_output")"
[[ "$(basename "$pruned_paths")" == plan-review-panel-paths.txt ]]

voter_output="$(run_larch "$design" plan-review voter-dispatch \
    --ballot-file "$design/ballot.md" --design-tmpdir "$design" \
    --codex-available true --cursor-available true --round-num 1)"
grep -qx 'VOTER_1_STATUS=launched' <<<"$voter_output"
grep -qx 'VOTER_2_STATUS=launched' <<<"$voter_output"
grep -qx 'VOTER_3_STATUS=launched' <<<"$voter_output"
grep -qx 'VOTER_1_PARSE_RATE_STATUS=OK' <<<"$voter_output"
grep -qx 'DISPATCH_OK=true' <<<"$voter_output"
grep -qx 'VOTER_1_RETRIED=false' <<<"$voter_output"
python3 - "$design/plan-voter-slots.ndjson" "$voter_output" <<'PY'
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
assert len(rows) == 3
assert all(set(row["prompt_files"]) == {"claude", "codex", "cursor"} for row in rows)
for row in rows:
    for tool, prompt in row["prompt_files"].items():
        sidecar = prompt + ".payload-bytes"
        with open(sidecar, encoding="utf-8") as handle:
            assert row["payload_files"][tool] == int(handle.read().strip() or "0")
keys = [line.partition("=")[0] for line in sys.argv[2].splitlines()]
assert keys[:13] == [
    "VOTER_1_PATH", "VOTER_1_TOOL", "VOTER_1_STATUS", "VOTER_1_PARSE_RATE_STATUS",
    "VOTER_2_PATH", "VOTER_3_PATH", "VOTER_PATHS_FILE",
    "VOTER_2_TOOL", "VOTER_3_TOOL", "VOTER_2_STATUS", "VOTER_3_STATUS",
    "VOTER_2_PARSE_RATE_STATUS", "VOTER_3_PARSE_RATE_STATUS",
]
PY
for voter_tool in codex cursor claude; do
    expected="$tmpdir/expected-plan-voter-$voter_tool.prompt"
    env CLAUDE_PLUGIN_ROOT="$tmpdir/plugin" LARCH_VOTER_CALIBRATION_FEEDBACK=0 \
        "$tmpdir/plugin/scripts/larch.sh" render voter \
        --ballot-file "$design/ballot.md" \
        --panel-role 'senior engineer on a voting panel deciding which proposed plan modifications should be accepted' \
        --id-grammar finding-oos --verification-context plan \
        --findings-ledger-file "$design/findings-ledger.tsv" \
        --payload-bytes-output "$expected.payload-bytes" \
        --voter-tool "$voter_tool" >"$expected"
    cmp "$expected" "$design/codex-validity-plan-voter-prompt-$voter_tool.txt"
done

floor_output="$(run_larch_fast "$design" plan-review voter-dispatch \
    --ballot-file "$design/ballot.md" --design-tmpdir "$design" \
    --codex-available false --cursor-available false --round-num 2)"
grep -qx 'VOTER_1_TOOL=claude' <<<"$floor_output"
grep -qx 'VOTER_2_STATUS=failed' <<<"$floor_output"
grep -qx 'VOTER_3_PARSE_RATE_STATUS=not-run' <<<"$floor_output"
grep -qx 'DEGRADED_PANEL=1' <<<"$floor_output"
grep -qx 'VOTER_1_RETRIED=false' <<<"$floor_output"
grep -q 'quota hit' <<<"$floor_output"
design_resolved="$(CDPATH='' cd -- "$design" && pwd -P)"
grep -qx "VOTER_1_PATH=$design_resolved/codex-validity-vote-output.txt" <<<"$floor_output"
grep -qx "$design_resolved/codex-validity-vote-output.txt" "$design/plan-voter-slots.ndjson.output-files"
grep -q -- '--timeout 1200' "$design/launch-argv.log"
[[ "$(wc -l <"$design/plan-voter-slots.ndjson" | tr -d ' ')" == 1 ]]

retry_design="$tmpdir/retry-design"
mkdir -p "$retry_design"
printf '### FINDING_1: Retry the floor\n' >"$retry_design/ballot.md"
: >"$retry_design/FAIL-ONCE-codex-validity-vote-output-phase3.txt"
retry_output="$(run_larch_fast "$retry_design" plan-review voter-dispatch \
    --ballot-file "$retry_design/ballot.md" --design-tmpdir "$retry_design" \
    --codex-available false --cursor-available false --round-num 1)"
grep -qx 'VOTER_1_RETRIED=true' <<<"$retry_output"
grep -qx 'VOTER_1_STATUS=launched' <<<"$retry_output"
grep -qx 'DISPATCH_OK=true' <<<"$retry_output"

set +e
python3 "$repo_root/python/cli.py" plan-review panel-dispatch --help >/dev/null 2>&1
python_panel_rc=$?
python3 "$repo_root/python/cli.py" plan-review voter-dispatch --help >/dev/null 2>&1
python_voter_rc=$?
set -e
[[ "$python_panel_rc" == 2 && "$python_voter_rc" == 2 ]]

printf '%s\n' 'PASS: test-plan-review-dispatch.sh'
