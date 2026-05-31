### Warnings

- **Step design Step 3 — run-step3-review.sh (degraded-empty-collector) failed (exit 0)**:
  ```
Step 3 plan-review panel degraded: Codex unavailable (Step 0 health probe failed); rounds 1-4 ran Cursor-only and accepted 7 important findings (auto-applied), but round 5 returned zero successful collectors (empty Cursor structured output) -> LOOP_STATUS=degraded-empty-collector at round cap 5.
WARN=plan-review-tsv: empty or missing structured reviewer rows for cursor-plan-pragmatic-output.txt (round 5)
WARN=plan-review-panel: dispatch produced no reviewer paths (--no-fallback drops) (round 5)
Effect: Gate B and Step 3.6 skipped per branch matrix; review-round counter rolled back to 0 so Gate C still offers Re-run review panel. plan.txt reflects rounds 1-4 accepted revisions.
  ```
