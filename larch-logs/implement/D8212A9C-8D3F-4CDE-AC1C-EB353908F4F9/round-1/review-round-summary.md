# Review Round 1

- Mode: `diff`
- 6 accepted, 8 rejected (8 exonerated)

## Accepted Findings

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


### FINDING_13: `D_WARN` harness contradicts SKILL WARN display/parse contract
- **Reviewer(s)**: dyn-display-parse-sync-output.txt
- **Severity**: important
- **Concern**: `test-step3-orchestrator-fence.sh` case `D_WARN` is titled “replayed once in parse” but asserts no `WARN=` anywhere in captured `apply_step3_handoff` output, contradicting `SKILL.md` and the harness parse loops that `printf` `WARN=` after suppressing it only in the display pass. The harness reportedly fails (`FAIL: WARN= should be suppressed from display pass output`) while claiming acceptance coverage for WARN behavior; only `D_DISP` exercises non-KV display suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-display-parse-sync-output.txt: Split display vs parse capture (e.g. tee display output to a temp file, or add a `DISPLAY_ONLY=1` mode to `apply_step3_handoff`), assert zero `WARN=` in display-only output, and assert exactly one `WARN=some-warning` from parse replay; optionally add a case with the same `WARN=` in `.step3-review-result.env` and stdout to lock dedup behavior.
  - From dyn-display-parse-sync-output.txt: Replace `D_WARN` with (1) display-only suppression check, (2) `grep -c`/`awk` asserting exactly one `WARN=` in full handoff output after parse, and (3) optional file+stdout duplicate case above; keep `D_DISP` as the non-KV breadcrumb guard.


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


### FINDING_8: Preview sentinel path not canonicalized vs review tmpdir
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Preview sentinel uses raw `--design-tmpdir` while `--no-preview` canonicalizes with `cd`/`pwd -P`. Symlink or non-canonical `DESIGN_TMPDIR` can place `.step3-entry-plan-printed` on a different path than review artifacts; re-entry may skip preview while `plan.txt` changes on the canonical tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Canonicalize for sentinel touch after allowlist check, or require canonical DESIGN_TMPDIR everywhere and test symlink tmpdirs.


