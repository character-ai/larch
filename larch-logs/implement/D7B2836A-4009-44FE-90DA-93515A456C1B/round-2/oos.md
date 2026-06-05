### FINDING_7: [OUT_OF_SCOPE] risk-integration: (branch)
[latent] Branch diff bundles Phase 4 with OOS materialization release Step 7 publish fixes and other PRs. Reviewers may miss Phase 4 regressions among unrelated changes. Split PR or document commit ranges in the PR body.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: Branch diff (non-Phase-4 files)
[latent] Diff includes release, OOS pipeline, SECURITY, ship-pr, and other commits beyond Phase 4 scope. Phase 4 plan fidelity review cannot attest those changes; they need separate plan/issue review. Review under their owning issues/plans.

### FINDING_25: [OUT_OF_SCOPE] **Initial Step 2b embedded fence** (`skills/design/SKILL.md:889-936`) matches the plan for rc **0** (both sentinels), rc **12**/**13** entry (`step-2b` only), rc **10** Override prose (`step-2b` then retained Step 2b.5), and non-exiting Split (`step-2b` + `step-2b.5` at line 941). Pause/resume via `design-pause-save.sh` walking `step-name-registry.tsv` will correctly target `2b.5` when only `step-2b` was set (e.g. hard-trigger entry then cancel)—that is consistent, not a missing write.
- **Initial Step 2b embedded fence** (`skills/design/SKILL.md:889-936`) matches the plan for rc **0** (both sentinels), rc **12**/**13** entry (`step-2b` only), rc **10** Override prose (`step-2b` then retained Step 2b.5), and non-exiting Split (`step-2b` + `step-2b.5` at line 941). Pause/resume via `design-pause-save.sh` walking `step-name-registry.tsv` will correctly target `2b.5` when only `step-2b` was set (e.g. hard-trigger entry then cancel)—that is consistent, not a missing write.

### FINDING_26: [OUT_OF_SCOPE] **`discussion-rounds.md`** correctly limits discussion rc **12**/**13** non-exiting returns to `step-2b.5` only (no initial-site `step-2b` on entry), but telling implementers to reuse the “full Step 2b” `case` arms still runs rc **12**/**13** arms that write `step-2b`; that is redundant, not a resume hole.
- **`discussion-rounds.md`** correctly limits discussion rc **12**/**13** non-exiting returns to `step-2b.5` only (no initial-site `step-2b` on entry), but telling implementers to reuse the “full Step 2b” `case` arms still runs rc **12**/**13** arms that write `step-2b`; that is redundant, not a resume hole.

### FINDING_27: [OUT_OF_SCOPE] **Commits on branch:** `07e42d57c` (merge `--with-plan-size` + thin fence), `d31536913` (review follow-up); earlier commits in the range are unrelated release/implement work.
- **Commits on branch:** `07e42d57c` (merge `--with-plan-size` + thin fence), `d31536913` (review follow-up); earlier commits in the range are unrelated release/implement work.

### FINDING_31: [OUT_OF_SCOPE] **Driver precedence (verified sound):** In `design-postplan-emit.sh`, `VALIDATE_STATUS=defects-found` exits `10` before plan-size (`521-526`); hard is checked before partition in `_postplan_finish_merged_plan_size` (`363-375`); pause returns `11` after result-env flush (`422-425`). Harness cases cover defects→10, partition+hard→12, partition without jq→13, rc2/3→0 nonfatal (`test-design-postplan-emit.sh` D19–D22).
- **Driver precedence (verified sound):** In `design-postplan-emit.sh`, `VALIDATE_STATUS=defects-found` exits `10` before plan-size (`521-526`); hard is checked before partition in `_postplan_finish_merged_plan_size` (`363-375`); pause returns `11` after result-env flush (`422-425`). Harness cases cover defects→10, partition+hard→12, partition without jq→13, rc2/3→0 nonfatal (`test-design-postplan-emit.sh` D19–D22).

### FINDING_32: [OUT_OF_SCOPE] **Initial Step 2b fence (verified sound):** Executable fence has arms `0`, `10`, `11`, `12`, `13`, `2`, `1`, and `*)` (`skills/design/SKILL.md:889-935`); legacy fat-fence `_postplan_rc` 0/1-only guards were removed in this branch.
- **Initial Step 2b fence (verified sound):** Executable fence has arms `0`, `10`, `11`, `12`, `13`, `2`, `1`, and `*)` (`skills/design/SKILL.md:889-935`); legacy fat-fence `_postplan_rc` 0/1-only guards were removed in this branch.

### FINDING_33: [OUT_OF_SCOPE] **`plan-review-loop.sh` partition gating:** Direct `check-plan-size.sh` rc 2/3 returns early before `LOOP_STATUS=plan-size-trigger` (`617-641`), matching Step 2b.5 step 3 semantics.
- **`plan-review-loop.sh` partition gating:** Direct `check-plan-size.sh` rc 2/3 returns early before `LOOP_STATUS=plan-size-trigger` (`617-641`), matching Step 2b.5 step 3 semantics.

### FINDING_34: [OUT_OF_SCOPE] **Plan vs implementation:** The issue plan pins `--with-plan-size --force-validate` for discussion/Step 1e; the branch deliberately retires `--force-validate` (`test-design-structure.sh:621-623`, `test-design-postplan-emit.sh` D12). That is a spec drift choice, not an exit-code precedence bug.
- **Plan vs implementation:** The issue plan pins `--with-plan-size --force-validate` for discussion/Step 1e; the branch deliberately retires `--force-validate` (`test-design-structure.sh:621-623`, `test-design-postplan-emit.sh` D12). That is a spec drift choice, not an exit-code precedence bug.

### FINDING_35: [OUT_OF_SCOPE] **Pre-existing Gate B prose tension:** Passive-summary auto-continue vs “Step 2b.5 returns” predates this branch; `approval-gates.md` already treats passive-summary as skipping re-emit (not worsened by the driver merge).
- **Pre-existing Gate B prose tension:** Passive-summary auto-continue vs “Step 2b.5 returns” predates this branch; `approval-gates.md` already treats passive-summary as skipping re-emit (not worsened by the driver merge).

### FINDING_40: [OUT_OF_SCOPE] Fix-and-retry re-entry is correctly centralized in `skills/design/SKILL.md:1549` (same-site `--with-plan-size` fence; raw emit/validate reserved for Step 5c).
- Fix-and-retry re-entry is correctly centralized in `skills/design/SKILL.md:1549` (same-site `--with-plan-size` fence; raw emit/validate reserved for Step 5c).

### FINDING_41: [OUT_OF_SCOPE] Override-after-rc10 routing to retained Step 2b.5 is documented for initial Step 2b (`skills/design/SKILL.md:939`), Gate B (`skills/design/references/approval-gates.md:158`), and discussion (`skills/design/references/discussion-rounds.md:126`).
- Override-after-rc10 routing to retained Step 2b.5 is documented for initial Step 2b (`skills/design/SKILL.md:939`), Gate B (`skills/design/references/approval-gates.md:158`), and discussion (`skills/design/references/discussion-rounds.md:126`).

### FINDING_42: [OUT_OF_SCOPE] No merged site reintroduces stdout KV merge heredocs (`<<<"${_postplan_out:-}"`); structure tests enforce absence in Gate B and discussion-round2.
- No merged site reintroduces stdout KV merge heredocs (`<<<"${_postplan_out:-}"`); structure tests enforce absence in Gate B and discussion-round2.

### FINDING_43: [OUT_OF_SCOPE] `design-postplan-emit.sh` rc `10` writes validator context to `.design-postplan-emit-result.env` before exit (`skills/design/scripts/design-postplan-emit.sh:521-525`); the gap is orchestrator-side reads at non–Step-2b sites, not driver emission.
- `design-postplan-emit.sh` rc `10` writes validator context to `.design-postplan-emit-result.env` before exit (`skills/design/scripts/design-postplan-emit.sh:521-525`); the gap is orchestrator-side reads at non–Step-2b sites, not driver emission.

