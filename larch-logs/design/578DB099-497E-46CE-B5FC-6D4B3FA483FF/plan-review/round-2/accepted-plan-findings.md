### FINDING_1: Codex fallback can duplicate existing Codex twin static reviewers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Static Codex peer rows plus the default waterfall Codex fallback can double-run the same archetype when Cursor fails, adding cost/noise and undermining the intended panel collapse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: When both CURSOR_AVAILABLE and CODEX_AVAILABLE are true, pass --no-fallback to dispatch-with-waterfall.sh (match dispatch-plan-review-panel.sh) or document and test that phase-2 Codex fallback is intentionally disabled for static/dynamic rows that already have a Codex twin; drop the line-27 “Phase-2 fallback” goal if peers are the contract


### FINDING_2: collaborative-sketches fallback matrix remains stale
- **Reviewer(s)**: Codex-Edge, Codex-dyn-vendor-flag-reentry
- **Severity**: important
- **Concern**: The Codex/Cursor integration documentation still describes /review as skipping unavailable specialist slots or launching no slots when both externals are down, contradicting the new availability-gated Cursor/Codex layout and both-down Claude fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the Code review row to the new availability-gated both-vendor layout and both-down Claude fallback, or point it at skills/review/scripts/dispatch-panel.md as the authority
  - From Codex-dyn-vendor-flag-reentry: Update the /review row to the new 4-archetype per-available-vendor layout and state that both-down emits Claude-fallback rows rather than no slots


### FINDING_3: intended-slot denominator guidance is ambiguous and can skew failure thresholds
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-vendor-flag-reentry, Cursor-dyn-availability-math
- **Severity**: important
- **Concern**: The plan/review-core guidance offers conflicting or unsafe ways to derive `--intended-slots` from availability flags versus emitted static row counts. This can create bash arithmetic errors, phantom never-launched failures, or hidden never-launched failures, causing the >50% panel-failure gate to misfire.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pass `--intended-slots "$static_slot_count"` (same KV as `--launched-slots`) and drop the availability formula from review-core; keep availability logic only in dispatch-panel emission
  - From Cursor-Requirements: Pass `STATIC_SLOT_COUNT` from dispatch-panel into `--intended-slots`, or convert each flag to 0/1 before multiplying; add/keep harness cases at 4 and 8 intended slots
  - From Cursor-dyn-vendor-flag-reentry: Remove the STATIC_SLOT_COUNT alternative for --intended-slots; compute intended only from availability (4 times vendor count, floor 4) or have dispatch-panel.sh emit a separate INTENDED_STATIC_SLOTS KV
  - From Cursor-dyn-availability-math: In review-core.sh set `intended_slots="$static_slot_count"` (same KV as `--launched-slots`) and pass `--intended-slots "$intended_slots"`; drop the parallel availability formula from the plan


### FINDING_4: dynamic scout prompt still names removed static archetypes
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The scout prompt still lists six static reviewers, including folded structure and plan-fidelity lanes, so dynamic archetype selection may under-cover or mis-target after the four-archetype collapse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Change the prompt line to name only the four surviving static slugs (security, correctness, edge-cases, testing) plus generic; keep the jq reserved list at six slugs so folded names cannot reappear as dynamics


### FINDING_5: runtime /review skill prompt remains stale
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: `skills/review/SKILL.md` still describes dynamic archetypes as Cursor-primary, so direct /review runs may load stale orchestration guidance after dispatch changes to availability-gated Cursor/Codex twin rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add skills/review/SKILL.md to the UPDATED list and change Step 2 to the 4-archetype per-available-vendor static layout plus matching dynamic twin/fallback behavior.


### FINDING_6: folded testing lane may not receive the plan outside generic diffs
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan claims testing preserves plan-fidelity coverage, but `render-specialist-prompt.sh` only injects the implementation plan for generic diffs, leaving docs-only/test-only/generated-only testing reviewers without plan context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add scripts/render-specialist-prompt.sh and its prompt-render test to the plan, with a minimal reviewer-testing-specific plan injection when PLAN_FILE is present, or narrow the stated plan-fidelity coverage claim to generic diffs only


### FINDING_7: write-round harness still expects excluded static Codex metadata
- **Reviewer(s)**: Cursor-dyn-log-exclude-coverage
- **Severity**: important
- **Concern**: The write-round harness still asserts committed `codex-specialist` metadata exists, which conflicts with adding static Codex specialist exclusions and can fail CI or pressure a revert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-log-exclude-coverage: Name scripts/test-larch-log-write-round.sh in the plan; flip meta to assert_not_file; add a raw codex-specialist-*-output.txt fixture with assert_not_file; drop or relocate CMD_JSON assertions that only applied to excluded meta


### FINDING_8: larch-log tests do not protect dynamic Codex twin outputs from over-broad exclusion
- **Reviewer(s)**: Codex-dyn-log-exclude-coverage
- **Severity**: important
- **Concern**: The larch-log regression plan covers static `codex-specialist-*` exclusion but not new `dyn-*-codex-output.txt` naming, so an over-broad Codex deny could silently drop dynamic Codex reviewer outputs from committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-log-exclude-coverage: Add one minimal larch-log regression fixture for dyn-api-contract-codex-output.txt and expected sidecar behavior, while keeping the static deny precise to codex-specialist-*-output.txt and matching sidecars. Update scripts/larch-log.md to state static Codex specialist raw outputs are excluded but dyn-*-codex-output.txt follows the existing dynamic/output allow-list behavior.

