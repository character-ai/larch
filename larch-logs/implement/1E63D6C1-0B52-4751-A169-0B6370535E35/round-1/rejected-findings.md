### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Tier-1 /design recovery order still probes before repeat carve-out
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: The Tier-1 /design guidance still presents the foreground probe for non-empty output before the repeat silent-yield carve-out, so prefix-identical repeats can reach the probe path before the repeat rule is applied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Qualify probe to new or changed non-empty and state ordered empty → repeat → probe contract
  - From cursor-specialist-edge-cases: Rewrite in evaluation order and limit probes to new or changed non-empty output, matching anti-pattern #5.
  - From dyn-dyn-contract-prose: Replace the three separate `/design` sentences with the same ordered contract used in `skills/design/SKILL.md:413` (empty → repeat → new/changed non-empty probe), or move the repeat carve-out before the probe sentence and qualify the probe with “new or changed.”


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: NEVER #3 still probes before its repeat carve-out
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: `skills/shared/orchestrator-never.md` still describes the probe trigger before the empty-output and prefix-identical-repeat silent-yield rules, so Tier-1 readers can still probe repeats when they follow NEVER #3 first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update NEVER #3/#4 to new or changed non-empty with explicit ordering
  - From cursor-specialist-edge-cases: Align NEVER #3 /design split with the ordered empty → repeat → probe contract.
  - From dyn-dyn-contract-prose: Align NEVER #3’s `/design` subsection with the ordered contract from anti-pattern #5, and change the probe trigger to “new or changed non-empty” rather than any non-empty.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Step 3 foreground-probe paragraph conflicts with repeat silent-yield rule
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: The Step 3 foreground-probe paragraph still says to probe after a premature notification with non-empty task output, but the repeat rule below requires silent yield for prefix-identical non-empty repeats, so the section can be read top-to-bottom as probe-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align line 29 with line 15 new/changed non-empty and ordered contract
  - From cursor-specialist-edge-cases: Rewrite line 29 to match the ordered contract in line 15.
  - From dyn-dyn-contract-prose: Rewrite line 29 to match anti-pattern #5 / Step 3 routing: evaluate empty first, then prefix-identical repeat (first 200 chars, same wait, sentinel absent), then probe only on **new or changed** non-empty output.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Anti-pattern #4 still authorizes probe-on-any-premature notification
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` anti-pattern #4 still tells orchestrators to probe on any premature notification, while anti-pattern #5 immediately below requires ordered empty → repeat → probe handling; a reader who stops at #4 can still probe repeats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Qualify anti-pattern #4 to new or changed non-empty; defer repeats to #5
  - From cursor-specialist-edge-cases: Qualify anti-pattern #4 to new or changed non-empty; defer repeats to #5
  - From dyn-dyn-contract-prose: Narrow anti-pattern #4 to “new or changed non-empty” probes and point to anti-pattern #5 (or `design-background-wait.md`) for empty/repeat silent-yield ordering.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Structural harness pins stale probe wording and misses ordered-contract coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-contract-prose
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` still pins stale non-empty probe literals and only partial repeat text, so CI can keep enforcing the conflicting probe/repeat wording instead of the ordered, new-or-changed contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Retarget contains pins to qualified probe wording; add ordered-contract pins
  - From cursor-specialist-edge-cases: Add contains pins for Tier-1 ordered contract or new-or-changed-non-empty wording in both structural harnesses.
  - From cursor-specialist-testing: Add contains/check_context pins in scripts/test-design-structure.sh and scripts/test-implement-anti-polling-rule.sh for A prefix-identical repeat (first 200 chars) for the same wait with `{terminal_sentinel}` absent also ends silently.
  - From dyn-dyn-contract-prose: Retarget the pin to the updated probe trigger (e.g. “new or changed non-empty”) and add a `contains` check for explicit ordered handling in the Step 3 boundary section; mirror the change in `scripts/test-implement-anti-polling-rule.sh:542-544`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

