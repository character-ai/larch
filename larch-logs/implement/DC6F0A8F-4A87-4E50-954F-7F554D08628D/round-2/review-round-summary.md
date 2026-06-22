# Review Round 2

- Mode: `diff`
- 2 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Plan-review ledger omits latent-reroute `oos` mapping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-ledger-roundtrip-output.txt
- **Severity**: important
- **Concern**: Plan-review ledger rows only force `outcome=oos` for `OOS_*` ids, while the same tally reroutes latent in-scope findings to the OOS artifact path in `_render`. Those rerouted `FINDING_N` items are written to `findings-ledger.tsv` as `rejected`/`neutral`, not `oos`, diverging from code-review `review_tally` and the plan’s OOS outcome rule. Judges miss OOS-specific duplicate rules; round 2+ plan reviewers can treat repeats as generic rejected findings instead of already-tracked OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror review_tally._ledger_entry latent handling when assembling ledger outcome; add plan-review tally test for rejected latent → oos.
  - From cursor-specialist-edge-cases-output.txt: Mirror review_tally latent-reroute logic when assembling plan-review ledger entries.
  - From dyn-dyn-ledger-roundtrip-output.txt: mirror `python/review_tally.py` when assembling plan-review ledger entries: detect latent reroute (and any plan-review scope-drift/OOS routing already used for classification) and emit `outcome=oos` for those items before calling `findings_ledger.write_round`.


### FINDING_8: Claude phase-3 fallback rejects unknown `--session-env-path`
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `dispatch_waterfall` forwards `--session-env-path` through `_common_args()` to every launched tool, including Claude phase-3 fallback, but `agent launch-claude-review` does not accept that flag. In a review round with `SESSION_ENV_PATH` set where cursor/codex are absent or fail, phase-3 Claude fallback exits from argparse before producing reviewer output, so the review panel can fail exactly when fallback is needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Add `--session-env-path` support to `launch_claude_review_main` and pass it through to `render specialist`, or exclude the flag from Claude launch args until that launcher supports it.


