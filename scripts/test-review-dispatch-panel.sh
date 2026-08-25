#!/usr/bin/env bash
# Black-box contract for Rust-owned `review dispatch-panel`.
unset IMPLEMENT_TMPDIR DESIGN_TMPDIR REVIEW_TMPDIR RESEARCH_TMPDIR SESSION_TMPDIR
set -euo pipefail

binary="${LARCH_BINARY:?set LARCH_BINARY to the test larch executable}"
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/larch-review-dispatch-panel.XXXXXX")"
trap 'rm -rf -- "$tmpdir"' EXIT

launcher="$tmpdir/plugin/scripts/larch.sh"
mkdir -p "$(dirname "$launcher")"
cat >"$launcher" <<'EOF'
#!/usr/bin/env bash
set -uo pipefail
if [[ "$1 $2" == "run-log append-entry" ]]; then
    shift 2
    log=
    entry=
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            --log) shift; log="$1" ;;
            --entry) shift; entry="$1" ;;
        esac
        shift
    done
    printf '%s\n' "$entry" >> "$log"
    exit 0
fi
for arg in "$@"; do [[ "${previous:-}" == --output ]] && out="$arg"; previous="$arg"; done
printf '%s\n' "$*" >> "$(dirname "$out")/launch-argv.log"
[[ -f "$(dirname "$out")/FAIL-$(basename "$out")" ]] && exit 7
printf '## Recommendation\nfine\n' > "$out"
printf '0\n' > "$out.done"
EOF
chmod +x "$launcher"

run_panel() {
    local round="$1" plan="$2" codex="$3" cursor="$4"
    shift 4
    env -u LARCH_CODEX_REVIEW_MODEL -u LARCH_CURSOR_MODEL \
        CLAUDE_PLUGIN_ROOT="$tmpdir/plugin" "$binary" review dispatch-panel \
        --mode diff --review-tmpdir "$round" --plan-file "$plan" \
        --codex-available "$codex" --cursor-available "$cursor" --tier MODERATE "$@"
}

assert_slots() {
    python3 - "$1" "$2" <<'PY'
import json
import sys

rows = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
expected = [
    ("correctness", "cursor"), ("correctness", "codex"),
    ("edge-cases", "cursor"), ("edge-cases", "codex"),
    ("testing", "cursor"), ("testing", "codex"),
]
if sys.argv[2] == "full":
    assert [(row["slot"], row["tool"]) for row in rows] == expected
else:
    assert len(rows) == 3 and all(row["tool"] == "cursor" for row in rows)
PY
}

for round in round-1 round-2 round-3 round-4; do
    mkdir -p "$tmpdir/$round"
    printf '# plan\n' > "$tmpdir/$round.md"
done

output="$(run_panel "$tmpdir/round-1" "$tmpdir/round-1.md" true true)"
grep -qx 'PANEL_MODE=waterfall' <<<"$output"
grep -qx 'STATIC_SLOT_COUNT=6' <<<"$output"
grep -qx 'DISPATCH_OK=true' <<<"$output"
assert_slots "$tmpdir/round-1/panel-manifest.ndjson" full

: > "$tmpdir/round-2/FAIL-cursor-specialist-edge-cases-output.txt"
output="$(run_panel "$tmpdir/round-2" "$tmpdir/round-2.md" true true)"
grep -qx 'STATIC_DISPATCH_OK=false' <<<"$output"
dropped="$(sed -n 's/^DROPPED_SLOTS_FILE=//p' <<<"$output")"
grep -q 'edge-cases' "$dropped"
[[ ! -e "$tmpdir/round-2/cursor-specialist-edge-cases-output.txt-phase2" ]]

output="$(run_panel "$tmpdir/round-3" "$tmpdir/round-3.md" false true)"
grep -qx 'STATIC_SLOT_COUNT=3' <<<"$output"
assert_slots "$tmpdir/round-3/panel-manifest.ndjson" reduced

cat > "$tmpdir/pre-scouted.json" <<'EOF'
{"archetypes":[{"name":"architecture","focus_area":"architecture","weight":3,"rationale":"Architecture changes merit focused review: café.","prompt_body":"Check boundaries and data flow for naïve callers."}]}
EOF
output="$(run_panel "$tmpdir/round-4" "$tmpdir/round-4.md" false true --dynamic-archetypes 1 --pre-scouted-manifest "$tmpdir/pre-scouted.json")"
grep -qx 'SCOUT_STATUS=pre-scouted' <<<"$output"
grep -qx 'DYNAMIC_SLOTS=1' <<<"$output"
grep -qx 'SLOT_COUNT=4' <<<"$output"
grep -q '"slot":"dyn-architecture"' "$tmpdir/round-4/panel-manifest.ndjson"
grep -q '# Dynamic Reviewer: architecture' "$tmpdir/round-4/dynamic-archetypes/dyn-architecture-prompt.md"
python3 - "$tmpdir/round-4/panel-manifest.ndjson" "$tmpdir/round-4/dynamic-archetypes/dyn-architecture-prompt.payload-bytes" <<'PY'
import json
import sys
from pathlib import Path

rows = [json.loads(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()]
row = next(row for row in rows if row["slot"] == "dyn-architecture")
rendered_payload = int(Path(sys.argv[2]).read_text(encoding="utf-8").strip())
scout_payload = "Architecture changes merit focused review: café.Check boundaries and data flow for naïve callers. Cite specific file paths and line ranges for any issues found, and follow the output-format rules from your outer wrapper exactly.".encode("utf-8")
assert row["payload_bytes"] - rendered_payload == len(scout_payload)
PY

mkdir -p "$tmpdir/reuse"
printf '# plan\n' > "$tmpdir/reuse.md"
cat > "$tmpdir/reuse/scout-round1-manifest.json" <<'EOF'
{"archetypes":[{"name":"architecture","focus_area":"architecture","weight":3,"rationale":"Architecture changes merit focused review.","prompt_body":"Check boundaries and data flow."}]}
EOF
output="$(run_panel "$tmpdir/reuse" "$tmpdir/reuse.md" false true --dynamic-archetypes 1)"
grep -qx 'SCOUT_STATUS=parse-failed' <<<"$output"
grep -qx 'SCOUT_FAIL_REASON=missing_status_sidecar' <<<"$output"
grep -qx 'DYNAMIC_SLOTS=0' <<<"$output"

mkdir -p "$tmpdir/reuse-invalid"
printf '# plan\n' > "$tmpdir/reuse-invalid.md"
cat > "$tmpdir/reuse-invalid/scout-round1-manifest.json" <<'EOF'
{"archetypes":[{"name":"architecture","focus_area":"architecture","weight":3,"rationale":"Architecture changes merit focused review.","prompt_body":"Check boundaries and data flow."},{"name":"xx","focus_area":"architecture","weight":3,"rationale":"Malformed reviewer.","prompt_body":"This must not launch."}]}
EOF
printf 'SCOUT_STATUS=ok\n' > "$tmpdir/reuse-invalid/scout-round1-status.env"
output="$(run_panel "$tmpdir/reuse-invalid" "$tmpdir/reuse-invalid.md" false true --dynamic-archetypes 1)"
grep -qx 'SCOUT_STATUS=ok' <<<"$output"
grep -qx 'DYNAMIC_SLOTS=0' <<<"$output"

if run_panel "$tmpdir/reuse" "$tmpdir/reuse.md" false true --dynamic-archetypes 2 >/dev/null 2>&1; then
    printf '%s\n' 'expected an invalid dynamic-archetypes value to fail' >&2
    exit 1
fi

mkdir -p "$tmpdir/producer-missing" "$tmpdir/implement"
printf '# plan\n' > "$tmpdir/producer-missing.md"
output="$(IMPLEMENT_TMPDIR="$tmpdir/implement" run_panel \
    "$tmpdir/producer-missing" "$tmpdir/producer-missing.md" false true \
    --dynamic-archetypes 1 --site 'implement Step 5')"
grep -qx 'SCOUT_STATUS=producer-missing' <<<"$output"
grep -q 'coder-produced dynamic-archetype manifest missing' \
    "$tmpdir/implement/execution-issues.md"
[[ -f "$tmpdir/implement/.producer-scout-warning-logged" ]]

# The sentinel keeps a repeated panel dispatch from duplicating the warning.
IMPLEMENT_TMPDIR="$tmpdir/implement" run_panel \
    "$tmpdir/producer-missing" "$tmpdir/producer-missing.md" false true \
    --dynamic-archetypes 1 --site 'implement Step 5' >/dev/null
[[ "$(wc -l < "$tmpdir/implement/execution-issues.md")" -eq 1 ]]

printf '%s\n' 'PASS: test-review-dispatch-panel.sh'
