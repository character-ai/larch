Here is the normalized aggregator output. In-scope items are merged by shared behavioral risk; `### OOS_*` blocks preserve `[OUT_OF_SCOPE]` where the source did. There is at least one `### FINDING_N:` block, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is not included.**

---

### FINDING_1: Semantic soft trigger missing from Step 2b.5 while flags.md still points to SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Post-plan-write “semantic” soft path (large multi-piece guesstimate) is not implemented in Step 2b.5; only mechanical thresholds and `--partition` drive the UI. `flags.md` still claims SKILL documents that semantic path, so cross-doc expectations are false and obvious sprawl below numeric thresholds never triggers the soft break-up offer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_2: CHANGELOG 42.0.21 omits #2670 /design plan-size and --partition work
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Shipped changelog bullets for 42.0.21 call out other work (e.g. anti-halt finalize) but not the major /design behavior change (plan-size thresholds, Step 2b.5, `-p`/`--partition` wiring), so consumers miss the feature in Keep a Changelog style notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_3: `check-plan-size.sh` uses exit 2 without a stable `PLAN_SIZE_STATUS` for non–plan-validation failures; doc and Step 2b.5 can mis-handle it
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Unknown argv / usage-style failures can exit `2` without `PLAN_SIZE_STATUS`, same as (or overlapping) input validation failures. Step 2b.5 then treats that like “missing plan” style validation and may continue without real threshold enforcement. Sibling doc `check-plan-size.md` only documents two meanings for `rc=2`, which can mislead integrators and tests if the script returns `2` in more cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_4: `.claude-plugin/plugin.json` /design description omits `-p`/`--partition`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Marketplace/discovery string for `/design` does not mention partition despite other argv docs; discoverability lags README and `docs/skills.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### FINDING_5: Branch stacks unrelated work (#2673 bump, logs, ship/dispatch) with #2670, raising review and rollback cost
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Multiple concerns interleaved on one branch makes bisect, attribution, and clean revert harder; bundled ship/dispatch changes add integration risk beyond plan-size tests alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_6: `test-check-plan-size.sh` case 15 largely duplicates earlier hard plan-body coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Redundant harness case increases maintenance cost without clear new behavioral coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

---

### FINDING_7: Step 5d guard 2 keys off argv `--repo character-ai/larch` while public /design argv docs omit `--repo`; deferral comment and sentinels can misfire or target wrong repo
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Guard is practically unsatisfiable under documented invocation, so gh issue comment paths (e.g. deferral to #2672) may never run; if `gh` defaults to another remote, a comment could still land on the wrong repo while guards/sentinels assume upstream—risking silent wrong-repo side effects and blocked retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Normatively require gh issue comment (or gh api) with explicit --repo character-ai/larch and pin it in FINDING_21 structural tests

---

### FINDING_8: `test-write-run-params.sh` no longer asserts rejection of obsolete `--source router-pre-design`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After test reshuffle, CI might regress to re-accepting the obsolete flag without a dedicated rejection case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### FINDING_9: Written edge case vs regex for `###NEW:` heading whitespace
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Prose says `###NEW:` should not count in some edge case, but regex may allow zero whitespace after `###`, so behavior and documented edge case can diverge for `FILES_COUNT` (and parallel logic in wrapper).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Either tighten regex in both places or fix the plan edge-case prose.

---

### FINDING_10: Harness does not cover plan-documented `diff_lines: 0` edge case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No fixture ending in `diff_lines: 0`; regressions in empty/zero handling could ship without `test-check-plan-size.sh` failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

### FINDING_11: `ship-pr.sh` classifies `admin_failed` via substring on `error_text` (“Base branch was modified”)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Fragile coupling to message text; future wording or rare collisions could mis-route recovery (skip stall or over-rebase).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### FINDING_12: On `write-run-params.sh` failure, Step 0b may drop `partition_requested` persistence
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier fields reset without carrying partition from argv through memory/retry; Step 2b.5 may never see `partition_requested=true` and skips forced soft UI without signaling the flag was dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### FINDING_13: Step 2b.5 references “steps 4–7” but procedure only has steps 4–6
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Minor operator confusion when tracing the flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### OOS_1: [OUT_OF_SCOPE] Bulk committed `larch-logs/**` in branch diff (policy / review noise)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Large design run logs in diff; reviewers treat as intentional per repo policy / noise for feature-focused review, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

---

### OOS_2: [OUT_OF_SCOPE] CHANGELOG 42.0.21 emphasis (#2681 vs #2670)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Editorial balance: body emphasizes anti-halt notes over #2670 summary; framed as optional alignment, not runtime behavior (distinct from in-scope missing #2670 bullets in **FINDING_2**).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

---

### OOS_3: [OUT_OF_SCOPE] Committed run logs and secret blast radius / redaction discipline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Large logs by design; reminder to keep redaction discipline per run-log policy—not a new trust boundary for this feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

### OOS_4: [OUT_OF_SCOPE] `dispatch-plan-voters.sh` YES vs EXONERATE voter prose expansion
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Expanded prompt text; reviewer states no new trust boundary beyond existing prompt generation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---

**Notes on merging**

- **FINDING_1** subsumes prior items 1, 8, and 25 (semantic soft vs Step 2b.5 vs `flags.md`).
- **FINDING_3** subsumes 3, 20, and 21 (exit code 2 / `PLAN_SIZE_STATUS` / doc contract); **FINDING_7** subsumes 7, 15, and 24 (`--repo` guard vs real invocation and gh target); **FINDING_4** subsumes 4 and 26 (`plugin.json` partition mention); **FINDING_5** subsumes 5 and 14 (unrelated work on branch).
- **FINDING_2** is **not** merged with **OOS_2**: one is “missing #2670 bullets” (in-scope **important**), the other is “emphasis / optional editorial” (**[OUT_OF_SCOPE] nit**).
- **OOS_1** merges log-diff noise from correctness (11) and edge-cases (23); **OOS_3** stays separate (secrets/redaction angle).
- Where multiple slots gave the exact string **“Address the concern above.”**, a single bullet lists those reviewers together per the identical-wording rule.
