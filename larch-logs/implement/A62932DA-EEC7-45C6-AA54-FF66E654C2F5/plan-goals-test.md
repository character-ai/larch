## Goal
Implement issue #3471: [IMPLEMENTING] [OOS] Harden /design skill: Gate-B bypass sentinel pins + --repo threading in pause guards + WARN= on classification non-zero exit\n\n## Out-of-Scope Observations (combined).

## Implementation Plan
## Plan

Hardening of the `/design` skill — four accepted OOS findings combined from #3467 (Part A) and #3468 (Part B). All targets live in this repo's dev tree (`skills/design/...`, `scripts/...`); the running plugin under the cache is regenerated from these. The issue body fully specifies the approach; every change is mechanical and additive (no behavior change on the common path).

### UPDATED: `scripts/test-design-structure.sh`

Covers **Part A** (Gate-B-bypass sentinel pins + negative self-tests) and the **Part B.1 test pin**.

**Part A — generalize `assert_gate_b_bypass_branch_sentinels`:**

- Today the function extracts only the single `LOOP_STATUS=plan-size-trigger` bullet (an awk span from the `LOOP_STATUS=plan-size-trigger` marker to the `LOOP_STATUS=plan-validator-defects` marker) and asserts the four literals: `mkdir -p "$DESIGN_TMPDIR/.completed"`, `: > "$DESIGN_TMPDIR/.completed/step-3"`, `: > "$DESIGN_TMPDIR/.completed/step-3.5"`, `: > "$DESIGN_TMPDIR/.completed/step-3.6"`.
- Rewrite it to iterate over **every** Gate-B-bypass branch token that carries the triple-sentinel-write prose in SKILL.md Step 3's Post-loop branch matrix and the cap-reached paragraph: `cap-reached`, `tally-error`, `panel-failed`, `skipped-cap-reached`, `degraded-empty-collector`, `plan-validator-defects`, and `plan-size-trigger`.
- For each token, locate the SKILL.md line that carries **both** the branch token (`LOOP_STATUS=<token>`, or `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached` for the cap pair) **and** the literal sentinel-write `: > "$DESIGN_TMPDIR/.completed/step-3"`; assert that line contains all four literals (mkdir + step-3 + step-3.5 + step-3.6). Fail with a token-specific message identifying the branch and missing sentinel.
- Key the match on the literal `: >` sentinel-write form so the descriptive Step 3.5/summary sentence (`write the triple-sentinel bypass layout (step-3, step-3.5, and step-3.6)`), which lists the names but does not contain the literal write, does NOT satisfy the pin.
- (Acceptable alternative per the issue: centralize one shared SKILL.md excerpt and assert every branch references it. The per-branch line assertion above is preferred — it matches the existing harness style and needs no SKILL.md restructuring.)

**Part A — negative self-tests:**

- Add a self-test routine mirroring the existing `run_thin_fence_self_tests` structure (`mktemp -d`, `trap 'rm -rf …' RETURN`, synthetic fixtures, run the assertion inside a subshell `( … ) 2>/dev/null` and call `fail` if it unexpectedly passes).
- Positive control: a fixture where every listed branch carries the full quadruple of writes → `assert_gate_b_bypass_branch_sentinels` passes.
- Negative controls: for at least two non-`plan-size-trigger` branches (e.g. `tally-error` and `panel-failed`), drop one sentinel write (e.g. remove the `step-3.5` line) and assert the assertion FAILS. This is the regression guard the issue requires.
- Invoke the new routine alongside the existing `run_thin_fence_self_tests` call.

**Part B.1 — Step 3b entry-guard REPO pin (new — none exists today):**

- `assert_thin_fence` runs only for the Step 3.6 region, so the Step 3b entry-guard REPO threading added below is currently unpinned. `assert_thin_fence` is unsuitable for Step 3b directly because that region contains more than one bash fence (entry-guard + mermaid sanitizer).
- Add a region-scoped pin: slice the Step 3b region (between the `<!-- step:3b` and `<!-- step:4 —` markers, matching the existing region-extraction helper used for the Step 3b architecture-diagram pins), find the first line matching `.pause-requested` AND `design-pause-save.sh`, and assert it contains the literal `${REPO:+--repo "$REPO"}`. Do NOT use a bare repo-wide `contains` (it would match the Step 3.6 occurrence and give false confidence).

### UPDATED: `skills/design/SKILL.md`

**Part B.1** — In the Step 3b entry-guard bash fence (the first fence under the `<!-- step:3b — Architecture Diagram -->` marker — the `[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec … design-pause-save.sh --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER"` line), append ` ${REPO:+--repo "$REPO"}` so the line is byte-identical to the already-correct Step 3.6 entry guard. Single-line change; touch no other pause-save fence.

### UPDATED: `skills/design/scripts/design-postplan-emit.sh`

Covers **Part B.2** (thread REPO through the internal pause checkpoint) and **Part B.3** (synthetic classification WARN).

**Part B.2:**

- The script has no `REPO` in scope. Add a `_postplan_resolve_repo()` helper mirroring the existing `_postplan_resolve_issue()`: awk-extract `export REPO=<value>` from `$DESIGN_TMPDIR/source-env.sh` (stripping surrounding single or double quotes), print the value. Use awk-only extraction — do NOT `source` source-env.sh (same arbitrary-code-execution security note already documented on `_postplan_resolve_issue`).
- In `_postplan_pause_checkpoint`, resolve `local _repo; _repo="$(_postplan_resolve_repo)"` and change the `exec … design-pause-save.sh --design-tmpdir "$DESIGN_TMPDIR" --issue "$_issue"` line to append `${_repo:+--repo "$_repo"}`. Empty REPO ⇒ flag omitted (safe no-op; matches today's behavior on non-fork runs). `write-design-current-env.sh` already writes `export REPO=` into source-env.sh when the orchestrator passes `--repo` (forked / explicit-repo runs), so the value resolves for exactly the cases that need it.

**Part B.3:**

- In the `read-design-classification.sh` block, the `if [[ "$_classification_rc" -ne 0 ]]` arm forces `WORKFLOW_PATH=HARD`. When that arm fires after the script produced **no** stderr output, no `WARN_LINES` entry is recorded and the HARD default is silent. Fix: guarantee that a non-zero classification exit always yields at least one `WARN_LINES` entry — capture the warn count before the stderr-read loop and, in the `_classification_rc -ne 0` arm, append a synthetic `WARN_LINES` line (e.g. noting the non-zero exit code and that classification defaulted to HARD) when the stderr read added none. (Gating on "no stderr warn captured" avoids duplicating a genuine stderr diagnostic; unconditionally appending is also acceptable.)
- Scope: the non-zero-exit arm only. The `else` arm (script absent / not executable, which also forces HARD) is **out of scope** for this issue.

### UPDATED: `skills/design/scripts/design-postplan-emit.md`

Document the new pause-checkpoint `--repo` threading (via source-env.sh `REPO` extraction) and the synthetic classification WARN guarantee, per the `script-md-siblings` rule (update in the same change as the behavior change).

### UPDATED: `skills/design/scripts/test-design-postplan-emit.sh`

Add offline coverage for the two Part B behaviors:

1. **Pause `--repo` threading**: with `$DESIGN_TMPDIR/source-env.sh` containing `export REPO=owner/name` and a `.pause-requested` sentinel present, assert the pause path threads `--repo owner/name` to the (stubbed) `design-pause-save.sh` invocation, and that an empty/absent REPO omits the flag.
2. **Synthetic classification WARN**: stub `read-design-classification.sh` to exit non-zero with empty stderr; assert the driver output / result-env carries a `WARN=` line and `WORKFLOW_PATH=HARD`.

### UPDATED (only if the documented contract changes): `scripts/test-design-structure.md`

If the harness's documented contract is materially extended, note the all-branches Gate-B-bypass sentinel pin and the Step 3b entry-guard REPO pin in the sibling stub.

## Acceptance

- `make test-design-structure` passes, including: the all-branches Gate-B-bypass sentinel pins (every listed `LOOP_STATUS` branch + the cap pair), the new negative self-tests, and the Step 3b entry-guard REPO pin.
- `make test-design-postplan-emit` passes, including the new pause `--repo` threading and synthetic-WARN coverage.
- Regression evidence (negative checks behave as designed): removing `${REPO:+--repo "$REPO"}` from the SKILL.md Step 3b entry guard makes `make test-design-structure` FAIL; removing a `step-3.5` sentinel write from the `tally-error` or `panel-failed` branch makes it FAIL.
- `make lint-bash32` passes for the edited shell scripts (no Bash 4+ constructs introduced).
- shellcheck is clean on `design-postplan-emit.sh` and `test-design-structure.sh`; `bash scripts/relevant-checks.sh` (or `make lint`) passes repo-wide.
- No behavior change on the common path: empty `REPO` ⇒ `--repo` omitted from the pause-save exec; successful classification ⇒ no synthetic WARN. The `else` (non-executable) classification arm is unchanged.

diff_lines: 200

## Test plan
(no test plan section in plan-file)
