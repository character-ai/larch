Aggregating reviewer findings into a merged structured list. Verifying a few source details in the codebase for accurate normalization.
### FINDING_1: external-reviewers.md intro contradicts BOTH_DOWN=false auto-proceed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cross-skill-consistency-output.txt
- **Severity**: important
- **Concern**: The §Degraded-tools gate opener (Issue #3207) still requires the operator to choose whenever any external tool is unhealthy, which conflicts with the same section’s `BOTH_DOWN=false` branch (notice + auto-proceed without `AskUserQuestion` when exactly one tool is down). Orchestrators that follow only line 26 may still call `AskUserQuestion` on single-tool-down interactive `/design` or `/implement` runs and block the intended warn-and-continue path (#3291).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cross-skill-consistency-output.txt: Rewrite the §Degraded-tools gate intro to state that interactive runs prompt only when both tools are down (`BOTH_DOWN` not exactly `false`), and that a single-tool outage prints the explanation as a notice and proceeds automatically.

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

### FINDING_4: Duplicated BOTH_DOWN tail in degraded-tools-gate.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Identical `BOTH_DOWN` if/else tail is duplicated in the design and non-design explanation branches (lines 142–162), increasing edit-drift risk (two copies of the same auto-proceed warning).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate shared tail after the skill-specific prose block.

### FINDING_5: test Case 13 duplicates Case 2 fixture
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Case 13 (lines 270–275) duplicates the Case 2 fixture; future Case 2 changes may not update Case 13.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Merge assertions into Case 2 or share a fixture helper.

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

### FINDING_8: Fail-safe empty BOTH_DOWN parse not pinned in CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No test or lint pins fail-safe parse behavior (empty `BOTH_DOWN` must prompt). A future edit could drop exact-string `BOTH_DOWN==false` checks from SKILL prose without CI failure, allowing silent auto-proceed on empty parse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep/contract test on gate paragraphs or document explicit acceptance of prose-only enforcement.

### FINDING_9: End-to-end orchestrator BOTH_DOWN branching not harness-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Auto-proceed vs `AskUserQuestion` is only covered via `degraded-tools-gate.sh` output, not skill orchestration (`skills/design/SKILL.md:200` and peers). Detector and skill docs can diverge in production; single-tool-down sessions may still block on user prompt despite green unit tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Accept per plan or add orchestration integration test later.

### FINDING_10: Harness contract docs omit BOTH_DOWN and Cases 13–14
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-degraded-tools-gate.md` and `scripts/degraded-tools-gate.md` harness sections omit `BOTH_DOWN` and Cases 13–14, drifting from `scripts/test-degraded-tools-gate.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update test-degraded-tools-gate.md to list BOTH_DOWN and closing-line cases.
  - From cursor-specialist-testing-output.txt: Extend harness description in degraded-tools-gate.md.
  - From cursor-specialist-edge-cases-output.txt: Mention BOTH_DOWN KV and Cases 13–14 in the harness blurb.

### FINDING_11: Stale four-flag env may yield BOTH_DOWN=false auto-proceed without consent
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Interactive auto-proceed on `BOTH_DOWN=false` skips `AskUserQuestion` for single-tool-down runs. Misclassified both-down (e.g. stale `CURSOR_PRESENT`/`CODEX_PRESENT` from a long-lived shell when flags omitted) yields `BOTH_DOWN=false`; the operator proceeds without explicit consent while external review diversity is reduced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require explicit four-flag argv before auto-proceed (detector KV or stderr WARNING guard), or prompt whenever stale-env warnings appear; keep empty BOTH_DOWN on prompt path.

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

### OOS_1: [OUT_OF_SCOPE] Consumer docs/external-reviewers.md still unconditional prompt
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Top-level `docs/external-reviewers.md` (~line 10) still says interactive runs always prompt when either tool is down. Operators reading consumer docs see old policy; not in branch diff. Runtime follows updated `skills/shared` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update docs/external-reviewers.md in a follow-up (not required by this plan’s file list).

### OOS_2: [OUT_OF_SCOPE] Implement Continue label vs waterfall degradation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md:455` Continue label says “reduced panel” though implement uses waterfall degradation. Pre-existing label/plan choice; not regressed by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider relabeling in a separate UX pass if confusing.

### OOS_3: [OUT_OF_SCOPE] relevant-checks does not map gate prose edits to harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/relevant-checks.sh` does not map SKILL/`external-reviewers` edits to `test-degraded-tools-gate`. Prose-only `BOTH_DOWN` regression may not run the gate harness on local pre-commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Map shared gate docs/skills to test-degraded-tools-gate or rely on full make lint in CI.

### OOS_4: [OUT_OF_SCOPE] Case 1 optional BOTH_DOWN=false on healthy path
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: Case 1 (`DEGRADED=false`) does not assert `BOTH_DOWN=false` though the script emits it before early exit; low risk given Cases 2–4; not part of this branch’s plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional assert_contains BOTH_DOWN=false in Case 1.

### OOS_5: [OUT_OF_SCOPE] --skill accepts unvalidated SKILL_LABEL
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--skill` accepts unvalidated `SKILL_LABEL` in explanation text (display-only interpolation at lines 53, 129). Pre-existing; not changed by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Validate --skill against allowlist {design,implement,review,research} if hardening desired (separate change).

### OOS_6: [OUT_OF_SCOPE] Per-skill interactive detection and Abort handling differences
- **Reviewer(s)**: dyn-cross-skill-consistency-output.txt
- **Severity**: nit
- **Concern**: Per-skill differences in interactive detection (`[[ -t 0 ]]` for `/research`, “non-subagent” for `/review`, plain “interactive” for `/design` and `/implement`) and Abort handling (`cleanup-tmpdir.sh` vs `STALL_TRACKING` + Step 18 for `/implement`) predate this branch and appear intentional; not regressions from `BOTH_DOWN` work.

### OOS_7: [OUT_OF_SCOPE] Four SKILL callers largely aligned; minor implement AskUserQuestion wording
- **Reviewer(s)**: dyn-cross-skill-consistency-output.txt
- **Severity**: nit
- **Concern**: The four SKILL.md callers align on fail-safe prose, per-skill Continue labels match `external-reviewers.md:40`, and Cases 13–14 cover explanation last-line divergence. Minor formatting only: `/implement` uses `fire AskUserQuestion` (**Continue…**) without “with”, unlike the other three skills.

### OOS_8: [OUT_OF_SCOPE] No automated test of skill-side BOTH_DOWN parsing
- **Reviewer(s)**: dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: No automated test that skill orchestrators parse `BOTH_DOWN` and branch on `[[ "$BOTH_DOWN" == "false" ]]`; coverage is prose-only in shared doc and four SKILL gate bullets (acceptable per plan, not exercised by `test-degraded-tools-gate.sh`).

### OOS_9: [OUT_OF_SCOPE] degraded-tools-gate.sh header comment drift (runtime OK)
- **Reviewer(s)**: dyn-test-gap-analysis-output.txt
- **Severity**: nit
- **Concern**: File header still says orchestrator always asks on `DEGRADED=true`; behavior is now split by `BOTH_DOWN` in callers — comment drift, not a runtime defect (overlaps in-scope FINDING_2 for files touched in-branch).
