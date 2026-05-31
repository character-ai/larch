### FINDING_1: external-reviewers.md intro contradicts BOTH_DOWN=false auto-proceed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cross-skill-consistency-output.txt
- **Severity**: important
- **Concern**: The §Degraded-tools gate opener (Issue #3207) still requires the operator to choose whenever any external tool is unhealthy, which conflicts with the same section’s `BOTH_DOWN=false` branch (notice + auto-proceed without `AskUserQuestion` when exactly one tool is down). Orchestrators that follow only line 26 may still call `AskUserQuestion` on single-tool-down interactive `/design` or `/implement` runs and block the intended warn-and-continue path (#3291).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-skill-consistency-output.txt: Rewrite the §Degraded-tools gate intro to state that interactive runs prompt only when both tools are down (`BOTH_DOWN` not exactly `false`), and that a single-tool outage prints the explanation as a notice and proceeds automatically.


### FINDING_10: Harness contract docs omit BOTH_DOWN and Cases 13–14
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-degraded-tools-gate.md` and `scripts/degraded-tools-gate.md` harness sections omit `BOTH_DOWN` and Cases 13–14, drifting from `scripts/test-degraded-tools-gate.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update test-degraded-tools-gate.md to list BOTH_DOWN and closing-line cases.
  - From cursor-specialist-testing-output.txt: Extend harness description in degraded-tools-gate.md.
  - From cursor-specialist-edge-cases-output.txt: Mention BOTH_DOWN KV and Cases 13–14 in the harness blurb.


### FINDING_12: Sentinel write asymmetry on BOTH_DOWN=true Continue path
- **Reviewer(s)**: dyn-cross-skill-consistency-output.txt
- **Severity**: important
- **Concern**: All four SKILL gate bullets explicitly write `.degraded-tools-gate-prompted` on the `BOTH_DOWN` exactly `false` branch, but the `BOTH_DOWN` true/empty/unset `AskUserQuestion` branch only covers presenting the prompt and **Abort**; sentinel creation on **Continue** is deferred to the trailing guard sentence. That conflicts with plan acceptance (“sentinel on both sub-branches”) and `external-reviewers.md:39` (explicit write on notice path only). Resume/re-entry (e.g. `/implement` dirty-tree / `resume-plan-tail`) can re-fire the gate if sentinel is written on auto-proceed but not after **Continue**.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-skill-consistency-output.txt: In `external-reviewers.md` and each SKILL gate bullet, add an explicit step on the `BOTH_DOWN=true` path: after **Continue**, write `$<SKILL>_TMPDIR/.degraded-tools-gate-prompted` (mirror the notice-path wording).


### FINDING_13: Cases 5–9 (and Case 7) lack BOTH_DOWN=false assertions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-test-gap-analysis-output.txt
- **Severity**: latent
- **Concern**: Cases 5–9 assert `DEGRADED=true` but not `BOTH_DOWN=false` despite single-tool-down fixtures (`unavailable`, `binary-missing`, `probe-failed`, present-only matrix). Regressions in `classify_state` / `norm_tristate` could flip `BOTH_DOWN` while Cases 2–3 still pass. Case 7 additionally lacks explanation-tail assertions for a documented real caller shape (`present-only`, review skill).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-gap-analysis-output.txt: Add `assert_contains "$out" "BOTH_DOWN=false"` to Cases 5–9 (and Case 7b at 130–133).
  - From cursor-specialist-edge-cases-output.txt: Add BOTH_DOWN=false and proceeding automatically / no Continue assertions to Case 7.


### FINDING_14: Case 4 (review, both-down) lacks non-design explanation-footer assertions
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-test-gap-analysis-output.txt
- **Severity**: latent
- **Concern**: Case 4 uses `--skill review` and asserts `BOTH_DOWN=true` but not explanation-footer text. The non-design both-down footer at `degraded-tools-gate.sh:157–159` has no assertion anywhere; Cases 13–14 only duplicate design-branch checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Assert Continue prompt and no proceeding automatically on Case 4 or add implement/review both-down case.
  - From dyn-test-gap-analysis-output.txt: Extend Case 4 with `assert_contains` for `(backup waterfall)` and the two-line Continue question, plus `assert_not_contains` for `proceeding automatically`.


### FINDING_2: degraded-tools-gate.sh header misstates unconditional prompting
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The file header (lines 9–12) still claims the orchestrator always asks when `DEGRADED=true`, which is misleading after `BOTH_DOWN`-gated behavior (prompt only when both tools are down; single-tool-down uses notice + auto-proceed). Contributors or agents reading only the header may implement unconditional prompting for all degraded sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update header comment to describe conditional prompt (both down) vs auto-proceed notice (one down).


### FINDING_3: degraded-tools-gate.md intro/Purpose still unconditional AskUserQuestion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-cross-skill-consistency-output.txt
- **Severity**: important
- **Concern**: Contract documentation (`degraded-tools-gate.md` intro/Purpose, ~lines 10–16) still says the orchestrator asks via `AskUserQuestion` whenever `DEGRADED=true`, with no `BOTH_DOWN` split. That disagrees with `skills/shared/external-reviewers.md` Output semantics and script behavior; readers may reintroduce always-prompt on any degraded run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-skill-consistency-output.txt: Document the `BOTH_DOWN` KV and state that interactive prompting applies only when both tools are down; single-tool-down runs print the explanation (including the auto-proceed notice) and proceed without `AskUserQuestion`.


### FINDING_6: Harness lacks non-design explanation-footer coverage (Cases 13–14 design-only)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-test-gap-analysis-output.txt
- **Severity**: latent
- **Concern**: Cases 13–14 only exercise `--skill design`, so they cover the design footer in `degraded-tools-gate.sh` but not the `else` branch used by implement/review (two-line “Continue in this degraded mode (backup waterfall)” prompt). A regression in the non-design `BOTH_DOWN` conditional or footer text could pass CI while design-only cases stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add parallel Cases 13b/14b with `--skill implement` or `review` asserting the backup-waterfall Continue lines and auto-proceed notice.
  - From dyn-test-gap-analysis-output.txt: Add paired cases (e.g. 15–16) mirroring 13–14 with `--skill implement` or `--skill review`: single-down must contain `proceeding automatically` and must not contain `Continue in this degraded mode`; both-down must contain `Continue in this degraded mode (backup waterfall)` and must not contain `proceeding automatically`.


### FINDING_7: Case 3 does not assert non-design single-tool-down closing text
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Case 3 does not assert single-tool-down explanation closing text on the non-design (`--skill implement`) branch. A bug only in the else-branch closing emit could ship; CI stays green while `/implement` still shows Continue-or-abort on one-tool-down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add proceeding-automatically / no-Continue assertions to Case 3 or a dedicated non-design case.


