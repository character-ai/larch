## Goal
Restrict Codex reviewers to round 1 of review panels in both HARD and SIMPLE workflows

## Implementation Plan

Restrict Codex reviewers (generalist + voter) to round 1 of /implement and /fix-issue review panels (HARD and SIMPLE).

### Files to modify

**1. skills/review/scripts/dispatch-panel.sh**
ROUND_NUM is already parsed with default "1". Add round-1 guard around Codex slots:
- HARD panel: wrap the codex_specialists loop with `if [[ "$ROUND_NUM" == "1" ]]; then ... fi`
- SIMPLE panel: wrap `queue_external_generalist_slot codex ...` with the same guard

**2. scripts/dispatch-code-voters.sh**
Add `--round-num` support and gate the Codex voter slot:
- Add `ROUND_NUM="1"` default variable
- Add `--round-num` flag parsing in the while loop
- Add validation: `case "$ROUND_NUM" in ''|*[!0-9]*) exit 2 ;; esac`
- Gate the Codex voter manifest entry: only add voter-2 (Codex) to code-voter-slots.ndjson when ROUND_NUM==1
- When round != 1: VOTER_2_PATH="" VOTER_2_STATUS="skipped"
- When round != 1: outputs_arr[0] is the Cursor slot — assign to VOTER_3_PATH
- Fix the "Degraded panel" warning: use expected_judges (3 for round 1, 2 for round 2+)
- Fix parse-rate check to skip VOTER_2 when status is "skipped"

**3. skills/review/scripts/review-core.sh**
Add `--round-num "$ROUND_NUM"` to voter_args so dispatch-code-voters.sh receives ROUND_NUM.

**4. Sibling docs**
- scripts/dispatch-code-voters.md: document --round-num and 2-voter behavior in round 2+
- skills/review/scripts/dispatch-panel.md: document round-1-only Codex in SIMPLE and HARD

**5. docs/voting-process.md** and **docs/agents.md**: describe round-1-only Codex policy.

### Edge cases
- ROUND_NUM unset/empty handled by default "1" at variable init (standalone /review --diff gets full Codex)
- In round 2+ SIMPLE: panel is 6 Cursor specialists only (no Codex generalist)
- In round 2+ HARD: panel is 6 Cursor specialists only (no Codex specialists)
- In round 2+: voter panel is Claude + Cursor (2 judges); classify_result handles eligible=2
- collect-agent-results.sh: no change needed — manifest drives what gets collected
- Scorer dead-row section in tally-code-votes.sh: no change needed — manifest-driven

## Test plan
(no test plan section in plan-file)
