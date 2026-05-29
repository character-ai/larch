Structured aggregator output (plain text; no empty-merge attestation because findings remain):

### FINDING_1: Stale `--simple` / `--hard` tier flags in plugin description
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-required update to `.claude-plugin/plugin.json` description was not applied. The shipped marketplace/plugin metadata still advertises removed tier argv (`--simple` alongside `--hard`), while the skill contract is issue-anchored `/design` with tier flag `--hard` only and default SIMPLE. That violates live-surface completeness (zero `--simple` outside exclusions), misleads installers/operators/automation, and leaves the only prominent non–larch-logs JSON surface out of sync with `skills/design/SKILL.md` and `flags.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Structure harness does not pin tier retirement (resolution, default reason, absent gates)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` pins default SIMPLE and approval-gates cleanup but not **Tier resolution**, the default-tier `write-run-params` reason string (`default tier: SIMPLE (no --hard)`), or absent retired strings (**Tier gate**, `cancelled-tier-gate`, tier `AskUserQuestion`). Step 0b could regress to an interactive tier gate or argv `tier: --simple` while existing contains/absent checks still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: No automated CI guard for live-surface `--simple` completeness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires zero live `--simple` mentions, but enforcement is manual grep only. `plugin.json` regressed while `make lint` and named harnesses still pass. Retired `--simple` rejection in `SKILL.md` is prose-only with no mechanical guard—future edits or misbehaving agents can reintroduce `--simple` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Arg-hint structure test allows `[--simple|--hard]` regression
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `scripts/test-design-structure.sh:33`, the argument-hint check only requires substring `[--hard]`. Restoring `[--simple|--hard]` on that line would still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: Driver test lacks negative guard for removed `--simple` table row
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/test-design-driver.sh` removed the `--simple` row assertion without an absent check. Re-adding a `| \`--simple\` |` table row would not fail the driver test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: `flags.md` tier section untested by structure harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The tier-section rewrite in `skills/design/references/flags.md` has no structure-test needles; `flags.md` can drift from the SKILL default / `--hard`-only contract without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: Disallowed `--simple` parsed after Step 0a despite “before Step 0” prose
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` documents disallowed-flag abort before Step 0 with no `DESIGN_TMPDIR`, but `/design --simple <issue>` runs session-setup in Step 0a then aborts in Step 0b, leaving an ambiguous cleanup contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] `cancelled-reentry-guard` missing from render-final-summary allowlist
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Pre-existing: `SKILL.md` emits `cancelled-reentry-guard` but `skills/design/scripts/render-final-summary.sh` (and related enums/docs) do not allow it. Re-entry guard runs the Final summary block, then the renderer rejects the unknown outcome and exits 2 instead of rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Historical CHANGELOG still documents `--simple` / `--hard` mutual exclusion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md` still references `--simple`/`--hard` mutual exclusion in old release notes; operators may believe `--simple` remains valid. Excluded from plan completeness grep by design; update when touching changelog for a release.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

**Merge notes (for voters, not part of machine output):**
- Six plugin.json findings → **FINDING_1** (severity **important**; security’s **latent** subsumed).
- Structure tier-pin gaps (inputs 2, 3, 5, 9) → **FINDING_2** (severity **latent**; nit+latent sources).
- Testing **FINDING_8** (completeness harness) kept separate from **FINDING_2** (different fix: repo-wide `rg` + Makefile vs SKILL needles).
- Testing’s plugin.json CI-grep note stayed in **FINDING_3** concern, not duplicated under **FINDING_1**.
- Three `cancelled-reentry-guard` OOS items → **FINDING_8** with `[OUT_OF_SCOPE]` retained (**important** over **latent**).
- Inputs 6/12/20 were duplicates; input 13 stands alone as **FINDING_9**.
