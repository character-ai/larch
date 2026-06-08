#!/usr/bin/env bash
# test-render-review-phase-detail.sh — harness for render-review-phase-detail.sh (issue #3774).
set -euo pipefail
export LARCH_QUIET_DISABLE=1
REPO="$(cd "$(dirname "$0")/.." && pwd -P)"
HELPER="$REPO/scripts/render-review-phase-detail.sh"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

command -v jq >/dev/null 2>&1 || { printf 'SKIP: jq unavailable\n'; exit 0; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/trrpd.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

ROOT="$WORK/run"
mkdir -p "$ROOT/round-1" "$ROOT/round-2" "$ROOT/round-3"

# round 1: 4 suggestions (2 acc, 1 rej, 1 exon), 2 OOS proposed (1 acc), 6 reviewers,
# one failed slot (codex generalist STATUS=ERROR).
cat >"$ROOT/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"2","REJECTED_COUNT":"1","EXONERATED_COUNT":"1","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"1","OOS_REJECTED_COUNT":"1"},"summary":{"panel":{"static_slot_count":5,"dynamic_slot_count":1,"total_slot_count":6},"finding_counts":{"total_accepted":2,"total_rejected":1,"total_exonerated":1,"total_neutral":0}},"collector":"REVIEWER_FILE=/t/round-1/cursor-specialist-structure-output.txt\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\nREVIEWER_FILE=/t/round-1/codex-generalist-output.txt\nTOOL=codex\nSTATUS=ERROR\nEXIT_CODE=1\nFAILURE_REASON=timeout\n"}
JSON
cat >"$ROOT/round-1/panel-manifest.ndjson" <<'JSON'
{"slot":"structure","tool":"cursor","output":"/t/round-1/cursor-specialist-structure-output.txt"}
{"slot":"correctness","tool":"cursor","output":"/t/round-1/cursor-specialist-correctness-output.txt"}
{"slot":"generic","tool":"codex","output":"/t/round-1/codex-generalist-output.txt"}
JSON

# round 2: 3 suggestions (all accepted), 0 OOS, reviewers via static+dynamic fallback (3+1=4), no failures.
cat >"$ROOT/round-2/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"3","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"static_slot_count":3,"dynamic_slot_count":1}},"collector":""}
JSON
cat >"$ROOT/round-2/panel-manifest.ndjson" <<'JSON'
{"slot":"correctness","tool":"cursor","output":"/t/round-2/cursor-specialist-correctness-output.txt"}
JSON

# round 3: dir present but NO round-meta.json -> must be skipped entirely.
: >"$ROOT/round-3/placeholder"

# findings: accepted attribution -> cursor/correctness x4, cursor/structure x1.
cat >"$ROOT/review-findings-full.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1"}
{"id":"FINDING_2","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"1"}
{"id":"OOS_C1_1","outcome":"out_of_scope","reviewer_slots":["codex-generalist-output.txt"],"round_num":"1"}
{"id":"REJ_C1_1","outcome":"rejected","reviewer_slots":["cursor-specialist-structure-output.txt"],"round_num":"1"}
{"id":"FINDING_3","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
{"id":"FINDING_4","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
{"id":"FINDING_5","outcome":"accepted","reviewer_slots":["cursor-specialist-correctness-output.txt"],"round_num":"2"}
JSON

# timing ledger: round 1 = 300s (5m), round 2 = 120s (2m).
printf 'v1\tround\t1700000000\timplement\tStep 5 — code review\t1\t1700000000\t1700000300\t300\t2\t1\t2\t-\n' >"$ROOT/timing-ledger.tsv"
printf 'v1\tround\t1700001000\timplement\tStep 5 — code review\t2\t1700001000\t1700001120\t120\t3\t0\t0\t-\n' >>"$ROOT/timing-ledger.tsv"

OUT="$WORK/section.md"
"$HELPER" --rounds-root "$ROOT" --findings-file "$ROOT/review-findings-full.jsonl" \
    --timing-ledger "$ROOT/timing-ledger.tsv" --skill implement --output "$OUT"

# --- Test 1: header + per-round rows + totals ---
grep -Fq -- '| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |' "$OUT" \
    || fail 'missing table header'
grep -Fq -- '| 1 | 4 | 2 | 2 | 1 | 5m 00s | — | 6 |' "$OUT" || fail "round-1 row wrong: $(grep -F '| 1 |' "$OUT" || true)"
grep -Fq -- '| 2 | 3 | 3 | 0 | 0 | 2m 00s | — | 4 |' "$OUT" || fail "round-2 row wrong: $(grep -F '| 2 |' "$OUT" || true)"
grep -Fq -- '| **Total** | **7** | **5** | **2** | **1** | **7m 00s** | — | **10** |' "$OUT" \
    || fail "total row wrong: $(grep -F 'Total' "$OUT" || true)"
pass 'per-round table + totals'

# --- Test 2: round-3 (no round-meta.json) is skipped ---
if grep -Eq '^\| 3 \|' "$OUT"; then fail 'round-3 without round-meta.json must be skipped'; fi
pass 'round dir without round-meta.json skipped'

# --- Test 3: top reviewers attributed by vendor/archetype ---
grep -Fq -- '1. cursor/correctness — 4' "$OUT" || fail "top reviewer #1 wrong: $(grep -F 'cursor/correctness' "$OUT" || true)"
grep -Fq -- 'cursor/structure — 1' "$OUT" || fail 'cursor/structure not attributed'
pass 'top reviewers by suggestions accepted'

# --- Test 4: failed reviewer slots by vendor/archetype ---
grep -Fq -- '**Reviewer slot failures**: 1' "$OUT" || fail "failure count wrong: $(grep -F 'failures' "$OUT" || true)"
grep -Fq -- '- codex/generic: 1' "$OUT" || fail 'failed slot not attributed to codex/generic'
pass 'reviewer slot failures attributed'

# --- Test 5: single-source dollar-line invariant (no $ / 💰; cost cells are em dash) ---
if grep -Fq -- '$' "$OUT"; then fail 'output must not contain a dollar sign (cost owned by render-run-summary.sh)'; fi
if grep -Fq -- '💰' "$OUT"; then fail 'output must not contain a cost emoji'; fi
grep -Fq -- 'cost is not separately instrumented' "$OUT" || fail 'missing cost footnote'
pass 'single-source cost invariant respected'

# --- Test 6: singular "reviewer" schema fallback ---
OLD="$WORK/old"
mkdir -p "$OLD/round-1"
cat >"$OLD/round-1/round-meta.json" <<'JSON'
{"tally":{"ACCEPTED_COUNT":"1","REJECTED_COUNT":"0","EXONERATED_COUNT":"0","NEUTRAL_COUNT":"0","OOS_ACCEPTED_COUNT":"0","OOS_REJECTED_COUNT":"0"},"summary":{"panel":{"total_slot_count":2}}}
JSON
cat >"$OLD/findings.jsonl" <<'JSON'
{"id":"FINDING_1","outcome":"accepted","reviewer":"cursor-specialist-edge-cases-output.txt","round_num":"1"}
JSON
OUT_OLD="$WORK/old-section.md"
"$HELPER" --rounds-root "$OLD" --findings-file "$OLD/findings.jsonl" --skill implement --output "$OUT_OLD"
grep -Fq -- 'cursor/edge-cases — 1' "$OUT_OLD" || fail "singular reviewer fallback wrong: $(cat "$OUT_OLD")"
# No timing ledger -> Time column is an em dash for the round.
grep -Fq -- '| 1 | 1 | 1 | 0 | 0 | — | — | 2 |' "$OUT_OLD" || fail "old-schema row wrong: $(grep -F '| 1 |' "$OUT_OLD" || true)"
pass 'singular reviewer fallback + missing-timing em dash'

# --- Test 7: no rounds -> empty output, exit 0 ---
EMPTY="$WORK/empty"
mkdir -p "$EMPTY"
EOUT="$WORK/empty.md"
"$HELPER" --rounds-root "$EMPTY" --skill implement --output "$EOUT"
[ ! -s "$EOUT" ] || fail 'no-rounds case must produce empty output'
pass 'no rounds -> empty output'

# --- Test 8: usage errors exit 2 ---
rc=0; "$HELPER" --skill implement >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "missing --rounds-root should exit 2 (got $rc)"
rc=0; "$HELPER" --rounds-root "$ROOT" --skill bogus >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || fail "invalid --skill should exit 2 (got $rc)"
pass 'usage errors exit 2'

# --- Test 9: stdout mode (no --output) prints the section ---
"$HELPER" --rounds-root "$ROOT" --findings-file "$ROOT/review-findings-full.jsonl" --skill implement \
    | grep -Fq -- '## Review Phase Detail' || fail 'stdout mode missing section heading'
pass 'stdout mode'

printf 'PASS: test-render-review-phase-detail.sh\n'
