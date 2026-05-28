## Proposed Design Outline

### Goals
- Reconcile reference docs and contracts with the now-landed multi-round design plan-review loop (PR #3142 / INT-2871) — only items still missing after the integration absorbed most of the original #2667 work.
- Surface the structured `- **Severity**: important|latent|nit` field that the loop already emits to Gate B presentation prose (no behavior change).
- Document the patch-apply security surface introduced by `revise-plan-with-waterfall.sh` and the per-round artifact tree under `larch-logs/design/<RUN_ID>/plan-review/round-<N>/`.

### Non-goals
- No new scripts; no behavioral code changes; no test harness rewrites.
- No reference to artifacts that never landed (`applied-plan-findings.md`, `MAIN_AGENT_VOTE_REQUIRED_DEFERRED`, `lib-voter-coverage.sh`, `LARCH_DESIGN_VOTER_COVERAGE_FRACTION`, `plan-review-rounds-summary.md`).
- No SKILL.md Step 3 sweep removing `TALLY_PLAN_REVIEW_STATUS` / `VOTER_1_PATH` — both are load-bearing in the loop-driver wiring.
- No Gate C re-review copy change: current "no preserved findings" prose is correct for cross-Gate-C-re-run behavior.

### Approach sketch
- Update `skills/design/references/plan-review.md` FINDING_N + OOS_N templates to include the structured fields the loop already emits (`- **Reviewer(s)**:`, `- **Severity**:`, `- **Focus area**:`, `- **Location**:`). Document within-loop cumulation of `oos-accepted-design.md` across rounds.
- Update `skills/design/references/approval-gates.md`: extend Severity classification rubric with structured-field precedence (`important → High`, `latent → Medium`, `nit → Low`, fallback to Concern-text rubric); update Gate B `AskUserQuestion` text to use structured counts when present; carve out loop-internal mechanical revision in State invariants #2 and #4.
- Add a SECURITY.md paragraph for the `revise-plan-with-waterfall.sh` patch-apply surface (LLM-authored unified diffs / section-replace blocks, `$DESIGN_TMPDIR/plan.txt`-only target, size cap, snapshot+revert).
- Add per-round artifact enumeration to `docs/run-logs.md` (allowlist from `lib-design-round-artifacts.sh`).
- Add SIMPLE-tier cost note to `docs/installation-and-setup.md`.
- Document `LARCH_DESIGN_CONVERGENCE_THRESHOLD` and `LARCH_DESIGN_ROUND_CAP` env vars in `skills/design/references/flags.md` (canonical) and cross-reference from `docs/configuration-and-permissions.md` if it has a comparable section.
- Add topology rows for `plan-review-loop.sh`, `revise-plan-with-waterfall.sh`, `dispatch-plan-voters.sh`, `lib-design-round-artifacts.sh` to `skills/shared/topology.tsv` then regenerate `docs/topology.md` via `scripts/generate-topology-docs.sh`.
- Verify `agent-lint.toml` registration of any not-yet-registered Piece 2 harness siblings.
- Add 2 structure-test assertions in `scripts/test-design-structure.sh`: severity-precedence prose in approval-gates.md; FINDING_N template lists the structured fields in plan-review.md.

### Surfaces in scope
- `skills/design/references/plan-review.md`, `skills/design/references/approval-gates.md`, `skills/design/references/discussion-rounds.md`, `skills/design/references/flags.md`.
- `SECURITY.md`, `docs/run-logs.md`, `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md` (only if it already has env-var section), `docs/topology.md` (generated).
- `skills/shared/topology.tsv`, `agent-lint.toml`, `scripts/test-design-structure.sh`.

### Open questions
- None.
