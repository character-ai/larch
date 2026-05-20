### FINDING_1: **correctness** `SECURITY.md:36-46` — The long “External tool delegation” paragraph at `SECURITY.md:36` still attributes omitted-`--coder` availability routing to “`/implement` **Step 2** implementation … Cursor → Codex → Claude”, while `skills/implement/SKILL.md:1009-1078` documents that routing under the Step 1 matrix row and `### Implementer waterfall`; the new standalone sentence at `SECURITY.md:46` correctly states that `diff_lines` / `diff-lines.txt` are informational and do not pick the main agent by plan size, but it does not tie selection to Step 1 either, so SECURITY and the SKILL can still be read as disagreeing about *where* in `/implement` the waterfall runs even though they agree on availability ordering and on `diff_lines` being non-routing. **Suggested fix:** Add a short cross-sentence qualifier in `SECURITY.md:36` or `SECURITY.md:46` that implementer resolution happens in `/implement` Step 1 before Step 2 dispatch, keeping the trust paragraph and the dedicated routing note aligned with `skills/implement/SKILL.md:1068-1098`.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - **correctness** `SECURITY.md:36-46` — The long “External tool delegation” paragraph at `SECURITY.md:36` still attributes omitted-`--coder` availability routing to “`/implement` **Step 2** implementation … Cursor → Codex → Claude”, while `skills/implement/SKILL.md:1009-1078` documents that routing under the Step 1 matrix row and `### Implementer waterfall`; the new standalone sentence at `SECURITY.md:46` correctly states that `diff_lines` / `diff-lines.txt` are informational and do not pick the main agent by plan size, but it does not tie selection to Step 1 either, so SECURITY and the SKILL can still be read as disagreeing about *where* in `/implement` the waterfall runs even though they agree on availability ordering and on `diff_lines` being non-routing. **Suggested fix:** Add a short cross-sentence qualifier in `SECURITY.md:36` or `SECURITY.md:46` that implementer resolution happens in `/implement` Step 1 before Step 2 dispatch, keeping the trust paragraph and the dedicated routing note aligned with `skills/implement/SKILL.md:1068-1098`.
- **Suggested revision**: Address the concern above.


### FINDING_17: architecture: skills/implement/SKILL.md:976
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-/design permitted-output list omits Implementer waterfall user-visible lines while matrix still requires that section. Strict NEVER #12 interpretation conflicts with required waterfall breadcrumbs before Step 1.r. Explicitly allow Implementer waterfall output lines or point the exception to that subsection.
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: scripts/test-implement-step2-routing.sh:2
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Header comment says Step 2 coder routing though the contract is Step 1 waterfall binding coder for Step 2. Mild navigational confusion when triaging harness failures vs SKILL sections. Update the comment to reference Step 1 implementer waterfall / Step 2 binding.
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `docs/linting.md:243` — The updated `make test-implement-step2-routing` row still describes the harness as “`/implement` **Step 2** default implementer routing” while it now pins the `### Implementer waterfall` prose in `skills/implement/SKILL.md`, which lives in the **Step 1** post-/design tail before the Step 2 implementation breadcrumb; the same Step-2 framing remains in `scripts/test-implement-step2-routing.md:3` and the header comment in `scripts/test-implement-step2-routing.sh:2`, so contributor-facing text and the authoritative SKILL disagree on which numbered step owns the waterfall. **Suggested fix:** Rephrase those strings to say Step 1 implementer selection / `### Implementer waterfall` (with Step 2 only consuming the resolved `--coder` in dispatch), or rename the harness in a follow-up so filenames, comments, and `docs/linting.md` all use one step label.
- **Reviewer**: dyn-cross-doc-consistency-output.txt
- **Concern**: - **correctness** `docs/linting.md:243` — The updated `make test-implement-step2-routing` row still describes the harness as “`/implement` **Step 2** default implementer routing” while it now pins the `### Implementer waterfall` prose in `skills/implement/SKILL.md`, which lives in the **Step 1** post-/design tail before the Step 2 implementation breadcrumb; the same Step-2 framing remains in `scripts/test-implement-step2-routing.md:3` and the header comment in `scripts/test-implement-step2-routing.sh:2`, so contributor-facing text and the authoritative SKILL disagree on which numbered step owns the waterfall. **Suggested fix:** Rephrase those strings to say Step 1 implementer selection / `### Implementer waterfall` (with Step 2 only consuming the resolved `--coder` in dispatch), or rename the harness in a follow-up so filenames, comments, and `docs/linting.md` all use one step label.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: skills/design/SKILL.md:367
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Tier 1 prose claims /implement Step 1 reads design-export diff-lines.txt for sizing. Downstream maintainers assume a Step 1 mechanical or scripted read that implement SKILL and implement scripts no longer describe or perform. Reword to export-only/optional context or add an explicit minimal read step in implement SKILL if read is intended.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/test-implement-step2-routing.sh:22-31
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Routing harness lost carve-out substring pins and only added a heading pin. Re-adding diff_lines<=3 routing copy to skills/implement/SKILL.md would still pass make test-implement-step2-routing, missing the regression the old pins caught. Add a denylist grep or extend test-implement-structure.sh to assert forbidden carve-out literals stay absent.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** `scripts/test-implement-step2-routing.sh:22-32` — The updated harness no longer asserts any substring that encodes the new contract that exported `diff_lines` / `diff-lines.txt` are informational for coder selection (it only pins `### Implementer waterfall`, the waterfall arrow text, explicit-coder bypass, fallback flags, and two `/design` export needles). A future edit could reintroduce a `diff_lines`-gated routing story in `skills/implement/SKILL.md` without failing this shard. **Suggested fix:** Add one `assert_contains` on `skills/implement/SKILL.md` for a stable clause from the new routing prose (for example the sentence at `skills/implement/SKILL.md:1074` stating that those artifacts do not select the implementer).
- **Reviewer**: dyn-stale-refs-output.txt
- **Concern**: - **correctness** `scripts/test-implement-step2-routing.sh:22-32` — The updated harness no longer asserts any substring that encodes the new contract that exported `diff_lines` / `diff-lines.txt` are informational for coder selection (it only pins `### Implementer waterfall`, the waterfall arrow text, explicit-coder bypass, fallback flags, and two `/design` export needles). A future edit could reintroduce a `diff_lines`-gated routing story in `skills/implement/SKILL.md` without failing this shard. **Suggested fix:** Add one `assert_contains` on `skills/implement/SKILL.md` for a stable clause from the new routing prose (for example the sentence at `skills/implement/SKILL.md:1074` stating that those artifacts do not select the implementer).
- **Suggested revision**: Address the concern above.


