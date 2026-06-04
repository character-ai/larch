### FINDING_19: [OUT_OF_SCOPE] architecture: skills/design/SKILL.md:1027-1041
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Sentinel suppresses preview on every Step 3 re-entry without checking whether plan.txt was repaired after an earlier missing-plan warning. Operator fixes plan.txt then triggers Gate C re-run; preview fence exits quietly; review runs with no refreshed ## Plan Candidate for Review and no repeated warning. Consider future enhancement: tie re-entry suppression to plan.txt presence/mtime, or clear sentinel when plan.txt becomes non-empty.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:1029-1074
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Uncaptured preview and captured review read plan.txt at different times if the tree mutates between fences. Operator sees preview from revision N while plan-review-loop reviews revision N+1; confusing triage of review findings vs chat preview. Document for operators; optional follow-up to invalidate sentinel or re-preview on plan.txt change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] correctness: skills/design/scripts/run-step3-review.sh:86-88
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Preview-mode canonicalization uses bare cd under set -e. Rare cd failure after validate passes aborts the whole Step 3 preview Bash block instead of degrading with a warning. Wrap cd in set +e; on failure skip sentinel touch and still run renderer on raw --design-tmpdir.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_25: **architecture** `docs/topology.md:24` and `skills/shared/topology.tsv:14` — Topology still lists `emit-design-plan-preview.sh` as the sole runtime authority for Step 3 plan-candidate preview, while the plan’s operator contract is `run-step3-review.sh --preview-only` (renderer remains `emit-design-plan-preview.sh` under the driver). **Suggested fix:** If step 6’s drift sweep is meant to include generated topology, extend the row (or add a companion row) so projection matches the new entrypoint; otherwise document in the issue/PR that topology update is intentionally deferred.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **architecture** `docs/topology.md:24` and `skills/shared/topology.tsv:14` — Topology still lists `emit-design-plan-preview.sh` as the sole runtime authority for Step 3 plan-candidate preview, while the plan’s operator contract is `run-step3-review.sh --preview-only` (renderer remains `emit-design-plan-preview.sh` under the driver). **Suggested fix:** If step 6’s drift sweep is meant to include generated topology, extend the row (or add a companion row) so projection matches the new entrypoint; otherwise document in the issue/PR that topology update is intentionally deferred. --- ### Traceability summary (plan → diff) | Plan requirement | Status | |------------------|--------| | `--preview-only` / `--no-preview`, mutual exclusion (exit 2), default `--no-preview` | Done in `run-step3-review.sh` + tests | | Preview before `--round-cap` / `cd` | Preview branch returns before review validation | | Sentinel owned by driver; allowlist-gated touch; exact header or exact missing-plan warning | Done; broad harness coverage in `test-run-step3-review.sh` | | `step3` pure renderer; `gatec` unchanged | Done in `emit-design-plan-preview.sh` | | `SKILL.md`: live preview fence, captured `--no-preview`, REPO on all pause-save lines | Done | | Thin fence: rc=2 → banner + `exit 1` before load/parse; display pass; `-f && ! -L`; file-first precedence; qualified rc≠0 override | Done; mirrored in `test-step3-orchestrator-fence.sh` | | `assert_thin_fence` on Step 3; obsolete fat pins removed | Done in `test-design-structure.sh` | | Docs: `configuration-and-permissions.md`, `issue-anchored-plan.md`, `linting.md`, `SECURITY.md` | Done | | `test-emit-design-plan-preview.sh`, `test-run-step3-review.sh`, `test-step3-orchestrator-fence.sh` | Done | | Optional `test-design-multi-round-integration.sh --no-preview` | Not added; **OK** — omitted flags default to `--no-preview` (`scripts/test-design-multi-round-integration.sh:498-500`) | | Original “remove one preview turn per Step 3 entry” | **Explicitly deferred** in plan; implementation matches deferred acceptance | ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] **Pre-existing quiet/capture contract** — The display pass replays non-KV lines from `_plan_review_out` only. Cap-reached prose must still land in the captured stream (FD 3 / quiet dup behavior). That predates this phase; not introduced by this diff.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Pre-existing quiet/capture contract** — The display pass replays non-KV lines from `_plan_review_out` only. Cap-reached prose must still land in the captured stream (FD 3 / quiet dup behavior). That predates this phase; not introduced by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_27: [OUT_OF_SCOPE] **`make test-run-step3-review` linting row** — Plan asked for harness prose updates; `docs/linting.md` folds new coverage into the `test-emit-design-plan-preview` row rather than expanding a dedicated `test-run-step3-review` table entry. Makefile already registers `test-run-step3-review` in `test-harnesses-8`; behavior is documented, just not in a separate linting table row.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **`make test-run-step3-review` linting row** — Plan asked for harness prose updates; `docs/linting.md` folds new coverage into the `test-emit-design-plan-preview` row rather than expanding a dedicated `test-run-step3-review` table entry. Makefile already registers `test-run-step3-review` in `test-harnesses-8`; behavior is documented, just not in a separate linting table row. --- **Verdict:** Implementation is **complete and correct against the supplied implementation plan**. The only material follow-up is optional topology/doc projection alignment if you want consumer docs to name the driver entrypoint, not only the renderer script.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

