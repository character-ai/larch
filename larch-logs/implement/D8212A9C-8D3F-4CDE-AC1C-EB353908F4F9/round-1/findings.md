Normalized aggregator output from the supplied reviewer findings:

### FINDING_1: Step 3 structure pins incomplete (REPO on all pause-save lines; rc=2 / display / matrix grep)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `assert_thin_fence` in `scripts/test-design-structure.sh` only validates `${REPO:+--repo "$REPO"}` on the first Step 3 `design-pause-save.sh` line, not all three fences. Plan acceptance also called for grep/structure pins on rc=2 fail-closed ordering (banner then `exit 1` before safe-env load), display-pass suppression of the twelve keys plus `WARN=`, and the `_step3_safe_env_loaded` matrix intro. Future `SKILL.md` edits could drop REPO on preview/captured fences or weaken thin-fence behavior while CI stays green; stale `LOOP_STATUS=complete` could drive the branch matrix on configuration errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a Step 3 block scan requiring REPO on every design-pause-save.sh line, or extend assert_thin_fence for all guards in region.
  - From cursor-specialist-correctness-output.txt: Add grep pins from the plan file list; optionally assert every design-pause-save.sh in the Step 3 region includes REPO.
  - From cursor-specialist-testing-output.txt: Add grep pins in the Step 3 region for banner-then-exit-1 before safe-env load, display-loop suppression of twelve keys plus WARN, and the `_step3_safe_env_loaded` matrix intro sentence.
  - From cursor-specialist-edge-cases-output.txt: Add step3_block REPO count pin and exit-1-after-banner grep.
  - From cursor-specialist-plan-fidelity-output.txt: Extend Check 14c0 (or a new `step3_block` scan) to assert all pause-save lines in `<!-- step:3 —` … `<!-- step:3.5` include `${REPO:+--repo "$REPO"}`, and add `contains`/`grep -Fq` pins for `aborting plan review**` followed by `exit 1`, the display-loop `case "$_key" in` suppress pattern, and the matrix intro sentence with `_step3_safe_env_loaded`.

### FINDING_2: `test-run-step3-review.sh` missing plan-listed preview/sentinel cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Preview harness coverage is incomplete versus plan acceptance: missing tests for renderer nonzero exit with non-header body (no sentinel touch, no abort), exact missing-plan warning plus sentinel on allowlisted tmpdir, stale sentinel on invalid/disallowed tmpdir (warnings still emitted), and related edge paths. Regressions in sentinel touch rules, `|| true` preview behavior, or warning strings could ship without failing `make lint` / `make test-run-step3-review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add the three stub/integration cases from the plan acceptance bullets.
  - From cursor-specialist-correctness-output.txt: Add the three cases from the plan acceptance/testing strategy.
  - From cursor-specialist-testing-output.txt: Add three stub-based cases covering exit 1 non-header (no sentinel), exact missing-plan warning (sentinel yes), and stale sentinel on disallowed tmpdir (warnings still emitted).
  - From cursor-specialist-edge-cases-output.txt: Add allowlisted-tmpdir tests: empty plan.txt with real emit script; stub exit 1 non-header no sentinel.
  - From cursor-specialist-plan-fidelity-output.txt: Add the missing stub/integration cases from the plan’s `test-run-step3-review.sh` section (nonzero-exit stub with `exit 1`, exact-warning stub, invalid-allowlist tmpdir with pre-existing sentinel, and a two-call non-header→header sequence).

### FINDING_3: Twelve-key allowlist duplicated across SKILL and harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The twelve-key allowlist is duplicated across display pass, file parse, and stdout parse in `SKILL.md` and mirrored in `test-step3-orchestrator-fence.sh`. Adding a 13th driver KV requires many manual edits; one site will be missed and precedence/display will drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize allowlist documentation and grep pins, or extract a shared key list for harness-only use in a follow-up.

### FINDING_4: Duplicate H1 in `emit-design-plan-preview.md`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Contract doc has a duplicate top-level `# emit-design-plan-preview.sh` heading; redundant title line only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Delete the duplicate # emit-design-plan-preview.sh line.
  - From cursor-specialist-testing-output.txt: Remove the duplicate # emit-design-plan-preview.sh line.
  - From cursor-specialist-edge-cases-output.txt: Remove duplicate heading.
  - From cursor-specialist-plan-fidelity-output.txt: Remove the extra `# emit-design-plan-preview.sh` line so the doc has a single H1.

### FINDING_5: Preview-only Step 3 fence lacks exit-2 handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Preview-only driver fence has no exit-2 handling unlike the captured `--no-preview` fence. `run-step3-review.sh --preview-only` can exit 2 (e.g. bad plugin root); behavior is inconsistent with the review path (banner + exit 1) and may not fail closed under errexit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add set +e rc capture and the same configuration banner + exit 1 as the review fence before --no-preview.

### FINDING_6: Preview sentinel uses `-e` instead of `-f`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Sentinel re-entry check uses `-e` not `-f`. `.step3-entry-plan-printed` created as a directory would suppress preview forever without a valid preview file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use [[ -f ... ]] for re-entry suppression.

### FINDING_7: Thin fence file-first precedence when driver fails to refresh env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: On `rc!=0`, an existing safe `.step3-review-result.env` is treated as authoritative and stdout does not override `LOOP_STATUS`/`TALLY` even when the driver failed to refresh the file. A prior run can leave `LOOP_STATUS=complete`; the current run prints `LOOP_STATUS=panel-failed` on stdout but `phase_driver_write_result_env` fails, so the orchestrator may enter Gate B instead of the panel-failed short-circuit to Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document as residual risk or narrow file-first rule when write failed (WARN/refusal) or file is older than this invocation.

### FINDING_8: Preview sentinel path not canonicalized vs review tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Preview sentinel uses raw `--design-tmpdir` while `--no-preview` canonicalizes with `cd`/`pwd -P`. Symlink or non-canonical `DESIGN_TMPDIR` can place `.step3-entry-plan-printed` on a different path than review artifacts; re-entry may skip preview while `plan.txt` changes on the canonical tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Canonicalize for sentinel touch after allowlist check, or require canonical DESIGN_TMPDIR everywhere and test symlink tmpdirs.

### FINDING_9: Symlinked `.step3-review-result.env` skipped without breadcrumb
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Symlinked `.step3-review-result.env` is skipped silently with no operator breadcrumb; operators may see stdout override with no explanation when a stale symlinked env exists beside a safe file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit one info line on -L skip or document in Step 3 prose.

### FINDING_10: `rc=2` from `run-step3-review.sh` aborts full `/design`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `rc=2` (e.g. invalid `LARCH_DESIGN_ROUND_CAP`) now maps to `exit 1` and aborts the entire `/design` session instead of a panel-failed short-circuit to Step 3b. UX may be harsher than intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Confirm intended UX or map exit 2 to a documented terminal outcome.

### FINDING_11: `RUN_STEP3_EMIT_PREVIEW_SH` override without path validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_STEP3_EMIT_PREVIEW_SH` is invoked without path validation or a production opt-in gate. A stale or attacker-influenced shell export could run arbitrary code with design-session privileges during `/design` `--preview-only`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document as harness-only in SECURITY.md; optionally require an explicit opt-in env flag and/or restrict overrides to paths under PLUGIN_ROOT.

### FINDING_12: Integration harness omits explicit `--no-preview`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-design-multi-round-integration.sh` omits explicit `--no-preview` on the `run-step3-review.sh` call; default-mode changes would not be signaled by the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Pass --no-preview on the run-step3-review.sh integration call.

### FINDING_13: `D_WARN` harness contradicts SKILL WARN display/parse contract
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` case `D_WARN` is titled “replayed once in parse” but asserts no `WARN=` anywhere in captured `apply_step3_handoff` output, contradicting `SKILL.md` and the harness parse loops that `printf` `WARN=` after suppressing it only in the display pass. The harness reportedly fails (`FAIL: WARN= should be suppressed from display pass output`) while claiming acceptance coverage for WARN behavior; only `D_DISP` exercises non-KV display suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-display-parse-sync-output.txt: Split display vs parse capture (e.g. tee display output to a temp file, or add a `DISPLAY_ONLY=1` mode to `apply_step3_handoff`), assert zero `WARN=` in display-only output, and assert exactly one `WARN=some-warning` from parse replay; optionally add a case with the same `WARN=` in `.step3-review-result.env` and stdout to lock dedup behavior.
  - From dyn-display-parse-sync-output.txt: Replace `D_WARN` with (1) display-only suppression check, (2) `grep -c`/`awk` asserting exactly one `WARN=` in full handoff output after parse, and (3) optional file+stdout duplicate case above; keep `D_DISP` as the non-KV breadcrumb guard.

### FINDING_14: Step 3 fence WARN replay lacks dedup vs Step 0b/postplan
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: latent
- **Concern**: WARN handling replays from both safe result-env read and stdout parse with no dedup, unlike Step 0b route/publish and `design-postplan-emit.md`. Today the driver does not persist `WARN=` to `.step3-review-result.env`, but double-emit is latent if WARN appears in file and stdout (symlink-fallback / partial-write).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-display-parse-sync-output.txt: Mirror postplan/Step 0b: collect WARN bodies in an array during file parse, then replay stdout `WARN=` only when that body was not already emitted; extend `test-step3-orchestrator-fence.sh` with a file+stdout duplicate WARN case expecting a single chat line.

### OOS_1: [OUT_OF_SCOPE] `_has_header` name misleading for missing-plan warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_has_header` is true for missing-plan warning text as well as the review header; misleading name only, no functional bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Rename when editing sentinel logic.

### OOS_2: [OUT_OF_SCOPE] `D6B`-style test covers `LOOP_STATUS` only, not `TALLY_PLAN_REVIEW_STATUS`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Safe-env `rc!=0` precedence test covers `LOOP_STATUS` only; tally status could be clobbered from stdout on `rc!=0` while file precedence for `LOOP_STATUS` remains tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend D6B-style case to assert TALLY_PLAN_REVIEW_STATUS file wins as well.

### OOS_3: [OUT_OF_SCOPE] `run-step3-review.md` exit-code table ambiguity for `--preview-only`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Exit-code table describes exit `0` as “normal completion (any settled `LOOP_STATUS`)” but does not call out `--preview-only` always exiting `0` after preview render; doc clarity only, not a plan-required functional regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Optional plan grep pins for display-pass / rc=2 banner not added
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: nit
- **Concern**: Branch adds thin-fence and `_step3_safe_env_loaded` pins but not the plan’s optional grep pins for display-pass suppression logic or `exit 1` immediately after the Step 3 rc=2 banner; doc/plan drift rather than display/parse list mismatch (SKILL.md and harness lists already match).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge summary**: 31 raw inputs → **14 in-scope** `FINDING_*` blocks and **4** `OOS_*` blocks. Major consolidations: structure/REPO/grep pins (1, 10, 11, 13, 23, 25, partial 31); preview harness gaps (2, 9, 12, 19, 24); duplicate H1 (4, 15, 22, 26); `D_WARN` test vs WARN dedup split (28+30 vs 29). No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
