### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (operator override) failed (exit 0)**:
  ```
Operator explicitly overrode the Step 2b.5 hard plan-size trigger (diff-added=2700 > 2000).
Chose "Other: No, override -- continue as per plan" instead of Split / Cancel.
Phase 1 is a deliberately-scoped foundation phase (1 of 7); full-surface depth was chosen in Round 1.
Proceeded to Step 3 plan review with the current plan.txt unchanged. No partition, no cancel.
  ```

- **Step design Step 3 post-loop — plan-review-loop.sh (plan-size-trigger; operator standing override) failed (exit 0)**:
  ```
Step 3 plan-review loop exited LOOP_STATUS=plan-size-trigger after auto-applying 6 accepted findings
(the revised plan still trips diff-added > 2000). Operator gave an explicit standing override of this
exact hard plan-size gate at Step 2b.5 ("Other: No, override -- continue as per plan"). Honored the
standing override: skipped the Split/Cancel re-prompt, skipped Gate B and Step 3.6 per the
plan-size-trigger branch matrix, and continued to Step 3b. Final control remains at Gate C (Step 4b).
6 accepted findings already applied to plan.txt by the loop; 3 findings exonerated.
  ```
