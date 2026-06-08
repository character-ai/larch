### Warnings

- **Step design Step 2b — check-plan-size (operator-forced override of non-overridable hard size brake) failed (exit 0)**:
  ```
OPERATOR OVERRIDE — initial Step 2b hard size brake forced through.
Operator chose 'Force the full plan through' at the hard-size AskUserQuestion.
This gate is non-overridable by skill design; bypass is at explicit operator direction.
HARD_TRIGGER_FIRED=true TRIGGER_REASONS=diff-added
PLAN_LINES=205 DIFF_ADDED=2500 DIFF_DELETED=6500 DIFF_LINES=9000 (threshold: diff_added>2000)
Consequence: very large PR; size management shifts to /implement.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size (operator-forced Override of hard size brake) failed (exit 0)**:
  ```
OPERATOR OVERRIDE (Gate B) — hard size brake forced through (carrying forward the standing force-through decision).
HARD_TRIGGER_FIRED=true TRIGGER_REASONS=diff-added PLAN_LINES=210 DIFF_ADDED=3000 DIFF_DELETED=3800 (threshold diff_added>2000)
Plan grew after auto-applying 15 accepted plan-review findings. Override per operator direction; size management shifts to /implement.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size (operator-forced Override, round 2) failed (exit 0)**:
  ```
OPERATOR OVERRIDE (Gate B round 2) — hard size brake forced through (standing force-through decision).
Plan grew after auto-applying 12 round-2 findings.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size (operator-forced Override, round 3) failed (exit 0)**:
  ```
OPERATOR OVERRIDE (Gate B r3) — hard brake forced (standing decision); plan grew after 14 r3 findings.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size (operator-forced Override, round 4) failed (exit 0)**:
  ```
OPERATOR OVERRIDE (Gate B r4) — hard brake forced (standing decision); applied 1 r4 finding.
  ```


- **Step design Step 3.5 / Gate B — check-plan-size (operator-forced Override, round 5) failed (exit 0)**:
  ```
OPERATOR OVERRIDE (Gate B r5) — hard brake forced (standing decision); applied r5 findings (cap round).
  ```

- **Step design Step 5b — oos-curation (dedup + stale-drop) failed (exit 0)**:
  ```
Step 5b OOS curation: prepared combined had 5 capped entries with a stale item (OOS_2 ci-decide/check-main-sync exit codes — fixed in final plan round 5) and ~4x duplicate companion-module observations.
Curated to 2 distinct non-stale items (dual-stack drift; CLI module structure). Dropped caller intra-batch deps TSV (item set changed) → /larch:issue runs its own dep analysis (graceful degrade).
  ```
### External Reviewer Issues

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.
