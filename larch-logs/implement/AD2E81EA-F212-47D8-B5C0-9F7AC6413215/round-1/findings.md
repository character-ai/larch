### FINDING_1: **Important** `risk-integration` `scripts/test-implement-step2-routing.sh:22` — The routing regression harness still pins the old `diff_lines < 30` / `>=30` strings, so this branch breaks `make lint` through `test-harnesses-6`. Concrete failure: `bash scripts/test-implement-step2-routing.sh` exits with `FAIL: implement carve-out missing: diff_lines < 30`. Update the assertions at `scripts/test-implement-step2-routing.sh:22-27` to the new `diff_lines <= 3` and `>=4` contract, and update the sibling harness docs (`scripts/test-implement-step2-routing.md`, `docs/linting.md`) to match.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-implement-step2-routing.sh:22` — The routing regression harness still pins the old `diff_lines < 30` / `>=30` strings, so this branch breaks `make lint` through `test-harnesses-6`. Concrete failure: `bash scripts/test-implement-step2-routing.sh` exits with `FAIL: implement carve-out missing: diff_lines < 30`. Update the assertions at `scripts/test-implement-step2-routing.sh:22-27` to the new `diff_lines <= 3` and `>=4` contract, and update the sibling harness docs (`scripts/test-implement-step2-routing.md`, `docs/linting.md`) to match.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `skills/design/SKILL.md:553` — `/design` runtime prompt text still says the estimate drives `/implement`’s `diff_lines < 30` carve-out, with the same stale threshold also at `skills/design/SKILL.md:367` and `skills/design/SKILL.md:847`. This is now misleading for future design/debugging runs. Update those references to `diff_lines <= 3`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/design/SKILL.md:553` — `/design` runtime prompt text still says the estimate drives `/implement`’s `diff_lines < 30` carve-out, with the same stale threshold also at `skills/design/SKILL.md:367` and `skills/design/SKILL.md:847`. This is now misleading for future design/debugging runs. Update those references to `diff_lines <= 3`.
- **Suggested revision**: Address the concern above.

### FINDING_3: **`risk-integration` — blocking.** [`scripts/test-implement-step2-routing.sh:22-27`](scripts/test-implement-step2-routing.sh) still `grep -Fq`s literals removed from [`skills/implement/SKILL.md`](skills/implement/SKILL.md): `'diff_lines < 30'`, `` `>=30` ``, and the `` `diff_lines < 30` carve-out `` fragment inside the explicit-coder bullet. **Concrete breakage:** `bash scripts/test-implement-step2-routing.sh` exits 1 with `FAIL: implement carve-out missing: diff_lines < 30`. **`make lint` / `make test-implement-step2-routing`** (see [`docs/linting.md:239`](docs/linting.md)) will fail until needles match the new contract (`diff_lines <= 3`, `` `>=4` ``, updated carve-out phrase). **Suggested fix:** Update those `assert_contains` needles (and the harness comment header) to the new threshold strings; re-run the harness. **Source:** plan called for `/relevant-checks` ([`larch-logs/.../plan-goals-test.md:69-71`](larch-logs/implement/AD2E81EA-F212-47D8-B5C0-9F7AC6413215/plan-goals-test.md)) but the diff does not include harness updates, so plan verification is incomplete.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **`risk-integration` — blocking.** [`scripts/test-implement-step2-routing.sh:22-27`](scripts/test-implement-step2-routing.sh) still `grep -Fq`s literals removed from [`skills/implement/SKILL.md`](skills/implement/SKILL.md): `'diff_lines < 30'`, `` `>=30` ``, and the `` `diff_lines < 30` carve-out `` fragment inside the explicit-coder bullet. **Concrete breakage:** `bash scripts/test-implement-step2-routing.sh` exits 1 with `FAIL: implement carve-out missing: diff_lines < 30`. **`make lint` / `make test-implement-step2-routing`** (see [`docs/linting.md:239`](docs/linting.md)) will fail until needles match the new contract (`diff_lines <= 3`, `` `>=4` ``, updated carve-out phrase). **Suggested fix:** Update those `assert_contains` needles (and the harness comment header) to the new threshold strings; re-run the harness. **Source:** plan called for `/relevant-checks` ([`larch-logs/.../plan-goals-test.md:69-71`](larch-logs/implement/AD2E81EA-F212-47D8-B5C0-9F7AC6413215/plan-goals-test.md)) but the diff does not include harness updates, so plan verification is incomplete.
- **Suggested revision**: Address the concern above.

### FINDING_4: **`risk-integration` — important.** [`SECURITY.md:46`](SECURITY.md) states omitted-`--coder` routing “narrows Claude inline implementation” to plans whose exported `diff_lines` is **below 30**. After this branch, the authoritative orchestrator contract in [`skills/implement/SKILL.md`](skills/implement/SKILL.md) is **≤3** (and “no carve-out” at **≥4**). **Impact:** security/trust documentation misstates when the main agent self-implements vs external coders. **Suggested fix:** Align that sentence with `diff_lines <= 3` (and optional note that absence/invalid/`>=4` skips the carve-out).
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **`risk-integration` — important.** [`SECURITY.md:46`](SECURITY.md) states omitted-`--coder` routing “narrows Claude inline implementation” to plans whose exported `diff_lines` is **below 30**. After this branch, the authoritative orchestrator contract in [`skills/implement/SKILL.md`](skills/implement/SKILL.md) is **≤3** (and “no carve-out” at **≥4**). **Impact:** security/trust documentation misstates when the main agent self-implements vs external coders. **Suggested fix:** Align that sentence with `diff_lines <= 3` (and optional note that absence/invalid/`>=4` skips the carve-out).
- **Suggested revision**: Address the concern above.

### FINDING_5: **`risk-integration` — latent.** [`skills/design/SKILL.md:367`](skills/design/SKILL.md), [`:553`](skills/design/SKILL.md), and [`:847`](skills/design/SKILL.md) still describe `/implement` Step 1 as using a **`diff_lines < 30`** carve-out. **Impact:** `/design` operators get the wrong mental model for what `diff_lines: <N>` triggers downstream. **Suggested fix:** Rephrase to `diff_lines <= 3` / “trivial plan” wording consistent with implement Step 1.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **`risk-integration` — latent.** [`skills/design/SKILL.md:367`](skills/design/SKILL.md), [`:553`](skills/design/SKILL.md), and [`:847`](skills/design/SKILL.md) still describe `/implement` Step 1 as using a **`diff_lines < 30`** carve-out. **Impact:** `/design` operators get the wrong mental model for what `diff_lines: <N>` triggers downstream. **Suggested fix:** Rephrase to `diff_lines <= 3` / “trivial plan” wording consistent with implement Step 1.
- **Suggested revision**: Address the concern above.

### FINDING_6: **`risk-integration` — nit.** [`docs/linting.md:239`](docs/linting.md) still describes `make test-implement-step2-routing` as pinning **`diff_lines < 30`**. **Impact:** contributor-facing lint docs drift from harness + skill text after fixes land. **Suggested fix:** Update the table cell to `diff_lines <= 3`.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 4. **`risk-integration` — nit.** [`docs/linting.md:239`](docs/linting.md) still describes `make test-implement-step2-routing` as pinning **`diff_lines < 30`**. **Impact:** contributor-facing lint docs drift from harness + skill text after fixes land. **Suggested fix:** Update the table cell to `diff_lines <= 3`.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: skills/design/SKILL.md:367,553,847
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] /design documentation still describes the implement carve-out as diff_lines < 30. File not changed on this branch; cross-skill text becomes inconsistent with implement after merge. Edit those references to the new <=3-line threshold in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: SECURITY.md:47; docs/linting.md:239
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Security and operator docs still state the below-30 bound for Claude inline routing under omitted --coder. Files not in diff; post-merge documentation misstates actual routing. Refresh SECURITY.md and the linting matrix row when updating the harness and threshold wording.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: skills/design/SKILL.md:367,553,847; SECURITY.md:47; docs/linting.md:239; scripts/test-implement-step2-routing.md:5
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cross-skill and policy docs still say `/implement` uses a `diff_lines < 30` (or below-30) carve-out. Post-merge, design skill / SECURITY / linting doc readers assume up-to-29-line plans may inline on Claude; `skills/implement/SKILL.md` now limits that to <=3 lines — documentation is stale, not executable routing logic. Follow-up edits to align all cited locations with `<= 3` / `>= 4` (or equivalent `diff_lines < 4`) semantics.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-implement-step2-routing.sh:22-27
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Structural harness needles still assert removed `diff_lines < 30` / ``>=30`` / explicit-bypass prose from `skills/implement/SKILL.md`. `bash scripts/test-implement-step2-routing.sh` fails on `assert_contains`, so `make lint` / relevant-checks paths that run this shard likely fail despite SKILL edits matching the plan. Update the three `assert_contains` needles (and sibling contract doc if desired) to `diff_lines <= 3`, the ``>=4` value as "no carve-out"`` wording, and the updated explicit-coder bypass line.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: skills/design/SKILL.md:367,553,847; SECURITY.md:47; docs/linting.md:239; scripts/test-implement-step2-routing.md:5-7
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Downstream docs still describe the old below-30 carve-out. Operators read inconsistent routing rules between `/design` / security / lint docs and `/implement` Step 1 after this branch. Reword to the `<=3` / `>=4` contract once implement text is final; update lint table wording after harness pins change.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: docs/linting.md:239
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Linting docs still describe the carve-out as diff_lines < 30. Operators and reviewers read stale routing semantics next to the harness entry. Align table text with diff_lines <= 3 (and >=4 no-carve-out if documented).
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-implement-step2-routing.md:5-8
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Harness sibling doc still pins diff_lines < 30. Mismatch with implement SKILL after threshold change. Update markdown contract to the new threshold wording.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-implement-step2-routing.sh:22-27
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Structural harness still asserts legacy diff_lines < 30 and >=30 substrings in skills/implement/SKILL.md. make test-implement-step2-routing (lint shard) fails because the needles no longer exist after the SKILL.md edit. Update assert_contains strings and scripts/test-implement-step2-routing.md to match diff_lines <= 3, >=4, and the updated explicit-coder bypass sentence.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/design/SKILL.md:367,553,847
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Design skill still documents diff_lines < 30 for the same carve-out implement now scopes to <=3. Misaligned mental model when authoring plans and interpreting diff-lines.txt export rationale. Update design SKILL cross-references to <=3 / >=4 or threshold-neutral wording consistent with implement.
- **Suggested revision**: Address the concern above.

