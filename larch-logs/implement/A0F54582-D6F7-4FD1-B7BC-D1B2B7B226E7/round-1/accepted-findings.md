### FINDING_1: Semantic soft trigger missing from Step 2b.5 while flags.md still points to SKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Post-plan-write “semantic” soft path (large multi-piece guesstimate) is not implemented in Step 2b.5; only mechanical thresholds and `--partition` drive the UI. `flags.md` still claims SKILL documents that semantic path, so cross-doc expectations are false and obvious sprawl below numeric thresholds never triggers the soft break-up offer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---


### FINDING_10: Harness does not cover plan-documented `diff_lines: 0` edge case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No fixture ending in `diff_lines: 0`; regressions in empty/zero handling could ship without `test-check-plan-size.sh` failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

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


