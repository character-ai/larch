## Decision 1: Nit-pruning is preserved when removing the /implement pre-vote OOS gate
- **Question**: When the OOS-drop gate is removed from `_prune_nit_then_pre_vote_gate`, should the bundled nit-pruning (which demotes pure nits to `[OUT_OF_SCOPE]`) also be removed?
- **Resolution**: Keep nit-pruning. Surgically remove ONLY the OOS-drop gate; keep invoking prune-nit in all three review branches (normal, validation-exhausted, empty-merge). Nit-demoted items then ride the ballot as OOS and are voted on under the loosened "legitimacy" rubric (pure style/noise still auto-rejected, landing in the rejected-OOS audit). Do NOT delete the nit-pruning path.
- **Source**: user

## Decision 2: The #6291 design aggregate-severity OOS promotion pool is kept as-is
- **Question**: This issue "supersedes" #6291, which added `_promote_aggregate_oos_pool` / `_aggregate_trigger_fires` in `design_oos.py`. Should that aggregate-promotion pool be removed?
- **Resolution**: Keep it as-is. Out of scope to remove; it is not in the issue's removal file-list. It only ADDS accepted items (dedup'd against accepted, never double-files) and coexists with the restored + loosened direct vote path. Do NOT remove the aggregate pool or its tests.
- **Source**: user

## Hard constraints carried from the issue (not re-litigated)
- Decision (C) is fixed: vote on OOS, then file survivors; no post-vote materiality/count filing gate.
- Loosen the OOS acceptance rubric to the "legitimacy" standard in BOTH code-review (implement) and plan-review (design) voters; still auto-reject pure style/polish/noise and speculation with no concrete trigger.
- Preserve `OOS_ISSUES_PER_RUN_CAP=1` single-issue rollup, semantic dedup across re-runs, and "empty accepted set -> file nothing" (no empty issue).
- `/design` has NO pre-vote gate to remove; only confirm the loosened rubric flows through `plan_review_round.py` / `plan_review_tally.py` -> `oos-accepted-design.md` -> Step 5b filing.
