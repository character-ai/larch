### OOS_1: [OUT_OF_SCOPE] Competition scoreboard parity for rescued neutrals
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Rescued neutrals are scored as `kind="oos"` / `oos_neutral`, so they no longer incur `NEUTRAL_FINDING_COST` in the competition scoreboard. Before this change, all neutrals (including would-be-rescued majors) were in-scope findings and penalized. That is a deliberate side effect of `score_kind = "oos"`, not a filing bug, but it changes reviewer incentives and is not locked by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Only if product wants parity, keep artifact rescue as-is but score rescued rows under `kind="finding"` with `result="neutral"` for penalty purposes.
  - From cursor-specialist-testing: Extend `test_tally_rescues_high_severity_neutral_findings_to_oos` to parse the scoreboard and confirm the proposer lands in `OOS-Neutral`, not `Neutral`.

### OOS_2: [OUT_OF_SCOPE] Duplicated `_finding_oos_reroute_marker` helper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `_finding_oos_reroute_marker` is duplicated in `review_tally.py` and `plan_review_tally.py` with slightly different latent regexes, risking future drift between code-review and plan-review paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Move to `voting.py` or a shared review helper to avoid future drift between code-review and plan-review paths.

### OOS_3: [OUT_OF_SCOPE] Rescue gates on judge vote severities only
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Rescue uses judge vote severities only, not finding-body `**Severity**`. A neutral with `YES SEVERITY=nit` will not rescue even if the finding body says `major`. Current behavior is fail-closed and consistent with panel-severity scoring elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document-only unless product wants body severity as a fallback; current behavior is fail-closed and consistent with panel-severity scoring elsewhere.

### OOS_4: [OUT_OF_SCOPE] Missing regression test for latent body + high-severity YES interaction
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: No regression locks the plan edge case where a finding has a **latent** body severity and a single **YES** with `blocker`/`major` vote. `_finding_oos_reroute_marker` prioritizes `latent-rerouted` over `neutral-rescued`, and `_record_tally` now writes `OUTCOME=oos` when `neutral_rescued` is true even on the latent path. That interaction is plausible in production but untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a two-finding test (latent body + YES major vs plain neutral-rescue) asserting the OOS marker stays `latent-rerouted` and tally env/ledger outcomes match expectations.

### OOS_5: [OUT_OF_SCOPE] Yield TSV shift lacks test signal
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The `score_kind="oos"` change removes rescued neutrals from archetype **yield TSV** totals (`_write_yield_tsv` only counts `kind == "finding"`). Dynamic-archetype yield ratios can shift without any test signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a small harness fixture with a scout manifest and assert yield totals before/after rescue, or document the intended yield semantics in a comment if exclusion is deliberate.

### OOS_6: [OUT_OF_SCOPE] Pre-existing latent-reroute tally drift
- **Reviewer(s)**: dyn-dyn-tally-parity
- **Severity**: latent
- **Concern**: Pre-existing latent-reroute neutrals (without rescue) still write `FINDING_*_OUTCOME=rejected` / `REJECTED_SUBTYPE=neutral` while living in `oos.md`; `emit-tally` can rebuild them into compact `rejected-findings.md`. This branch did not introduce that drift, though rescue now fixes tally `OUTCOME=oos` for latent+high-YES cases when gating is absent.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Design `round-meta.json` can disagree with rescued-neutral classification
- **Reviewer(s)**: dyn-dyn-prompt-sync
- **Severity**: latent
- **Concern**: `write_design_round_meta` never calls `_canonical_decomposition`, while plan-review now writes rescued neutrals as `scope=oos` in `findings-classification.tsv` but keeps `Result=neutral` in `voting-tally.md`. `_round_counts` prefers `_parse_tally_md` when the MD table has data, so design run-summary / `round-meta.json` can disagree with TSV and with code-review's `tally_canonical` path.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] OOS acceptance rubric does not distinguish neutral-rescued artifacts
- **Reviewer(s)**: dyn-dyn-prompt-sync
- **Severity**: nit
- **Concern**: Neutral-rescued in-scope findings land in `oos.md` with `(neutral-rescued)` but were never OOS-ballot items judged under the OOS materiality gate. Downstream filing is unchanged per plan, yet the rubric does not distinguish neutral-rescued OOS artifacts from voter-accepted OOS ballot rows; operators may misread filing intent.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] No regression guard for neutral-rescue rubric in `render voter`
- **Reviewer(s)**: dyn-dyn-prompt-sync
- **Severity**: nit
- **Concern**: `test_render_voter_includes_panel_severity_rubric` does not assert presence of the new "Neutral rescue" rubric line. `render voter` embeds the rubric file verbatim, so drift is unlikely today, but there is no regression guard for the propagation surface named in the rubric **Update triggers**.
- **Suggested revisions (informational for voters; coder decides)**:

