### FINDING_1: **correctness** `SECURITY.md:36-46` — The long “External tool delegation” paragraph at `SECURITY.md:36` still attributes omitted-`--coder` availability routing to “`/implement` **Step 2** implementation … Cursor → Codex → Claude”, while `skills/implement/SKILL.md:1009-1078` documents that routing under the Step 1 matrix row and `### Implementer waterfall`; the new standalone sentence at `SECURITY.md:46` correctly states that `diff_lines` / `diff-lines.txt` are informational and do not pick the main agent by plan size, but it does not tie selection to Step 1 either, so SECURITY and the SKILL can still be read as disagreeing about *where* in `/implement` the waterfall runs even though they agree on availability ordering and on `diff_lines` being non-routing. **Suggested fix:** Add a short cross-sentence qualifier in `SECURITY.md:36` or `SECURITY.md:46` that implementer resolution happens in `/implement` Step 1 before Step 2 dispatch, keeping the trust paragraph and the dedicated routing note aligned with `skills/implement/SKILL.md:1068-1098`.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - **correctness** `SECURITY.md:36-46` — The long “External tool delegation” paragraph at `SECURITY.md:36` still attributes omitted-`--coder` availability routing to “`/implement` **Step 2** implementation … Cursor → Codex → Claude”, while `skills/implement/SKILL.md:1009-1078` documents that routing under the Step 1 matrix row and `### Implementer waterfall`; the new standalone sentence at `SECURITY.md:46` correctly states that `diff_lines` / `diff-lines.txt` are informational and do not pick the main agent by plan size, but it does not tie selection to Step 1 either, so SECURITY and the SKILL can still be read as disagreeing about *where* in `/implement` the waterfall runs even though they agree on availability ordering and on `diff_lines` being non-routing. **Suggested fix:** Add a short cross-sentence qualifier in `SECURITY.md:36` or `SECURITY.md:46` that implementer resolution happens in `/implement` Step 1 before Step 2 dispatch, keeping the trust paragraph and the dedicated routing note aligned with `skills/implement/SKILL.md:1068-1098`.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `docs/linting.md:243` — The updated `make test-implement-step2-routing` row still describes the harness as “`/implement` **Step 2** default implementer routing” while it now pins the `### Implementer waterfall` prose in `skills/implement/SKILL.md`, which lives in the **Step 1** post-/design tail before the Step 2 implementation breadcrumb; the same Step-2 framing remains in `scripts/test-implement-step2-routing.md:3` and the header comment in `scripts/test-implement-step2-routing.sh:2`, so contributor-facing text and the authoritative SKILL disagree on which numbered step owns the waterfall. **Suggested fix:** Rephrase those strings to say Step 1 implementer selection / `### Implementer waterfall` (with Step 2 only consuming the resolved `--coder` in dispatch), or rename the harness in a follow-up so filenames, comments, and `docs/linting.md` all use one step label.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - **correctness** `docs/linting.md:243` — The updated `make test-implement-step2-routing` row still describes the harness as “`/implement` **Step 2** default implementer routing” while it now pins the `### Implementer waterfall` prose in `skills/implement/SKILL.md`, which lives in the **Step 1** post-/design tail before the Step 2 implementation breadcrumb; the same Step-2 framing remains in `scripts/test-implement-step2-routing.md:3` and the header comment in `scripts/test-implement-step2-routing.sh:2`, so contributor-facing text and the authoritative SKILL disagree on which numbered step owns the waterfall. **Suggested fix:** Rephrase those strings to say Step 1 implementer selection / `### Implementer waterfall` (with Step 2 only consuming the resolved `--coder` in dispatch), or rename the harness in a follow-up so filenames, comments, and `docs/linting.md` all use one step label.
- **Suggested revision**: Address the concern above.

### FINDING_3: **correctness** `scripts/test-implement-step2-routing.sh:22-32` — The updated harness no longer asserts any substring that encodes the new contract that exported `diff_lines` / `diff-lines.txt` are informational for coder selection (it only pins `### Implementer waterfall`, the waterfall arrow text, explicit-coder bypass, fallback flags, and two `/design` export needles). A future edit could reintroduce a `diff_lines`-gated routing story in `skills/implement/SKILL.md` without failing this shard. **Suggested fix:** Add one `assert_contains` on `skills/implement/SKILL.md` for a stable clause from the new routing prose (for example the sentence at `skills/implement/SKILL.md:1074` stating that those artifacts do not select the implementer).
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: - **correctness** `scripts/test-implement-step2-routing.sh:22-32` — The updated harness no longer asserts any substring that encodes the new contract that exported `diff_lines` / `diff-lines.txt` are informational for coder selection (it only pins `### Implementer waterfall`, the waterfall arrow text, explicit-coder bypass, fallback flags, and two `/design` export needles). A future edit could reintroduce a `diff_lines`-gated routing story in `skills/implement/SKILL.md` without failing this shard. **Suggested fix:** Add one `assert_contains` on `skills/implement/SKILL.md` for a stable clause from the new routing prose (for example the sentence at `skills/implement/SKILL.md:1074` stating that those artifacts do not select the implementer).
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: - **correctness** `.claude/skills/agnix-fix/SKILL.md:154` — The dev-only agnix-fix skill still tells operators `--coder=codex` is required so the “auto-route to the main agent for small surgical plans (per issue #1481)” does not fire, but `/implement` no longer performs that small-plan / `diff_lines`-driven main-agent auto-route at all, so the stated threat model is outdated and can mislead fork-CI operators. **Suggested fix:** Rewrite that sentence to cite the current contract (always use the coder / availability waterfall unless explicitly overridden) and keep `--coder=codex` as the agnix-specific implementer choice without referencing the removed auto-route.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: - **correctness** `CHANGELOG.md:1654` and `CHANGELOG.md:1738` — Historical entries for releases `17.0.16` / `17.0.0` still name the retired “Coder simplicity override” / small-plan main-agent routing; that is appropriate as versioned history, but it is no longer a description of current behavior after this branch. **Suggested fix:** Leave as-is unless the project wants a short “superseded by …” forward pointer in a living doc such as `README.md` or `docs/workflow-lifecycle.md` (not the dated changelog bullets).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Historical `CHANGELOG.md` entries and older `larch-logs/.../session-transcript.jsonl` fixtures that still mention the removed `diff_lines <= 3` auto-route behavior are legacy narrative, not newly introduced contradictions among `SECURITY.md`, `skills/implement/SKILL.md`, and `skills/design/SKILL.md` for the post-change contract.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - Historical `CHANGELOG.md` entries and older `larch-logs/.../session-transcript.jsonl` fixtures that still mention the removed `diff_lines <= 3` auto-route behavior are legacy narrative, not newly introduced contradictions among `SECURITY.md`, `skills/implement/SKILL.md`, and `skills/design/SKILL.md` for the post-change contract.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] The branch also adds committed run-log material under `larch-logs/implement/A44B9A2E-E8AD-4092-B98C-8FAE334B4869/` (per `diff.txt`); that is process/repo-hygiene noise for reviewers rather than a routing-contract defect, and it does not change the three-way `diff_lines`/waterfall story the scout notes targeted.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - The branch also adds committed run-log material under `larch-logs/implement/A44B9A2E-E8AD-4092-B98C-8FAE334B4869/` (per `diff.txt`); that is process/repo-hygiene noise for reviewers rather than a routing-contract defect, and it does not change the three-way `diff_lines`/waterfall story the scout notes targeted.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: CHANGELOG.md:1738
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Historical changelog entry documents superseded Coder simplicity / plan-size auto-route behavior. Pre-existing shipped release history; not modified by this branch diff. Optional new changelog entry if the project tracks semantic behavior changes there.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1198-1200
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Duplicated word 'unavailable or unavailable' in Cursor-fallback print bullet Low-grade operator confusion; looks accidental Normalize wording when next touching that ladder
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:1219
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Duplicate unavailable wording in Step 2.4 banner bullet. Pre-existing typo outside this PR’s hunks. Normalize wording on next edit.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] risk-integration: skills/design/references/plan-review.md:129
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Plan-review finalize step still says /implement reads diff-lines.txt for Step 1 coder routing Plan reviewers following plan-review.md get a false downstream contract when revising plans after this branch Rephrase to informational sizing / export hygiene; remove stale coder-routing claim
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/write-design-manifest.md:5
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Sibling contract still says diff-lines.txt is for /implement Step 1 coder routing Readers of the manifest writer doc infer routing behavior that skills/implement/SKILL.md no longer defines Update bullet to informational export/logs wording consistent with implement + design skills
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/write-design-manifest.md:5
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Contract still labels diff-lines export as Step 1 coder routing. Operators editing manifest behavior read routing language while design/implement skills now say informational-only; cross-doc confusion after merge. Rephrase the bullet to informational sizing consistent with write-design-manifest.sh consumers.
- **Suggested revision**: Address the concern above.

### FINDING_14: `7306be4a` — Fix missed `diff_lines <= 3` reference in `SECURITY.md` external-tool paragraph  
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: 1. `7306be4a` — Fix missed `diff_lines <= 3` reference in `SECURITY.md` external-tool paragraph
- **Suggested revision**: Address the concern above.

### FINDING_15: `7a7fa94a` — Remove `diff_lines` Step 1 carve-out; always waterfall to coder  
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: 3. `7a7fa94a` — Remove `diff_lines` Step 1 carve-out; always waterfall to coder   Diff (from `diff.txt`) touches: `SECURITY.md`, `docs/linting.md`, new files under `larch-logs/implement/A44B9A2E-.../`, `scripts/test-implement-step2-routing.{md,sh}`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`.
- **Suggested revision**: Address the concern above.

### FINDING_16: `d0075a39` — chore(larch-logs): flush implement run `A44B9A2E-...`  
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: 2. `d0075a39` — chore(larch-logs): flush implement run `A44B9A2E-...`
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: skills/implement/SKILL.md:976
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-/design permitted-output list omits Implementer waterfall user-visible lines while matrix still requires that section. Strict NEVER #12 interpretation conflicts with required waterfall breadcrumbs before Step 1.r. Explicitly allow Implementer waterfall output lines or point the exception to that subsection.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/test-implement-step2-routing.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comment says Step 2 coder routing though the contract is Step 1 waterfall binding coder for Step 2. Mild navigational confusion when triaging harness failures vs SKILL sections. Update the comment to reference Step 1 implementer waterfall / Step 2 binding.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: skills/design/scripts/write-design-manifest.md:5
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sibling contract still claims diff-lines.txt is for /implement Step 1 coder routing. Operators and maintainers following script-md siblings can believe diff_lines still gates coder choice after design-export cleanup. Rephrase the bullet to informational sizing only; align wording with skills/design/SKILL.md and skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: skills/design/SKILL.md:367
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Tier 1 prose claims /implement Step 1 reads design-export diff-lines.txt for sizing. Downstream maintainers assume a Step 1 mechanical or scripted read that implement SKILL and implement scripts no longer describe or perform. Reword to export-only/optional context or add an explicit minimal read step in implement SKILL if read is intended.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: skills/design/scripts/write-design-manifest.md:5
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Sibling contract still claims diff-lines.txt export is for Step 1 coder routing. Contributors or agent-lint readers following write-design-manifest.md as canonical will believe diff_lines still gates implementer choice, conflicting with implement/design SKILL and risking follow-up edits that reintroduce routing assumptions. Rephrase the bullet to informational sizing only (align with skills/design/SKILL.md manifest-helper and implement Step 1 prose).
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: skills/implement/SKILL.md:1074
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] New waterfall prose claims plan diff_lines and design-export/diff-lines.txt are informational sizing 'from /design' Quick/SIMPLE/both-down inline paths skip /design and often omit diff-lines.txt; plan.txt may still carry diff_lines without any /design export Orchestrators may assume both artifacts always exist and always come from /design; split provenance: optional diff_lines in plan.txt vs diff-lines.txt only when /design/manifest export created it
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: SECURITY.md:26-38;skills/implement/SKILL.md:1048-606
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Default omitted --coder routing always uses Cursor then Codex then Claude; diff_lines no longer selects main agent. Small planned changes that used to stay on the main Claude Edit/Write path can now invoke Cursor or Codex with workspace-write trust on the same tree. Document that operators who want main-agent-only implementation must pass --coder=claude (or ensure both externals are absent); optionally note the removed small-diff carve-out in permissions/trust docs.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-implement-step2-routing.sh:22-31
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Routing harness lost carve-out substring pins and only added a heading pin. Re-adding diff_lines<=3 routing copy to skills/implement/SKILL.md would still pass make test-implement-step2-routing, missing the regression the old pins caught. Add a denylist grep or extend test-implement-structure.sh to assert forbidden carve-out literals stay absent.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/test-implement-step2-routing.sh:29-36
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness weakened to heading + shortened strings only. Regression could remove waterfall body text without failing make target. Add substring pins on normative routing phrases without restoring the <=3 carve-out.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/test-implement-step2-routing.sh:29-36
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Harness no longer pins removed carve-out literals; only asserts the Implementer waterfall heading exists. A future edit could reintroduce diff_lines-based routing prose without failing this structural harness until caught elsewhere. Add a negative substring pin or assert absence of the old auto-route breadcrumb / diff_lines<=3 routing prose.
- **Suggested revision**: Address the concern above.

