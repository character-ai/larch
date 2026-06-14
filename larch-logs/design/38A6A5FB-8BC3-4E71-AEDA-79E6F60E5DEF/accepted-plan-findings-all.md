### FINDING_1: Scope-anchor helper must not include brainstorm in binding anchor
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-shell-env-safety
- **Severity**: important
- **Concern**: The planned scope-anchor materialization lists or merges `brainstorm.md` into binding anchor inputs. That conflicts with the live contract: brainstorm belongs only in optional non-binding `plan-review-feature-context.txt`, while `plan-review-scope-anchor.txt` must carry issue narrative (with `larch:plan` stripped) plus approved outline. Merging brainstorm into the binding anchor would over-weight ideation in reviewer, voter, and MainAgent prompts and widen scope beyond the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove brainstorm.md from the scope-anchor materialization inputs; keep brainstorm on the existing feature-context path only
  - From Cursor-dyn-shell-env-safety: Remove `brainstorm.md` from the scope-anchor helper inputs, or state explicitly that this helper never reads/writes brainstorm and that feature-context staging stays separate; add a test that brainstorm content is absent from `plan-review-scope-anchor.txt`


### FINDING_2: already-planned → Replace path does not reliably produce feature-description.txt
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-shell-env-safety
- **Severity**: important
- **Concern**: Bug 6 hardening is incomplete on the `already-planned → Replace via full flow` path. SKILL Step 0b runs Sub-steps 5–6 and `design-step0-init.sh` only when `ROUTE=proceed`, so Replace may never invoke init at all. Even when init runs, `design-step0-init.sh` writes `feature-description.txt` only when `_init_route == proceed` while Replace keeps `ROUTE=already-planned`, and the plan does not name a durable replace marker. Step 2b/Step 3 inputs can therefore proceed without `feature-description.txt`, and the post-init missing-file guard never fires on the exact failing path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add SKILL Step 0b prose for the Replace branch to run design-step0-init.sh or write feature-description.txt before Step 0c and extend design-init-runparams.md caller contract
  - From Cursor-dyn-shell-env-safety: Have Step 0b write an explicit sentinel (for example `$DESIGN_TMPDIR/.already-planned-replace`) or pass `--replace-requested true` into `design-step0-init.sh`; treat `proceed OR replace sentinel` as the write guard; keep the post-init missing-file abort


### FINDING_4: monitor-mode-unavailable prelaunch path still emits panel-failed with zero rounds
- **Reviewer(s)**: Cursor-dyn-zero-review-gates
- **Severity**: important
- **Concern**: The plan does not retarget the monitor-mode-unavailable prelaunch path in `design-step3-review.sh`. `_step3_review_write_prelaunch_failure` still writes `STEP3_REVIEW_LOOP_STATUS=panel-failed` with `ROUNDS_COMPLETED=0` and `REVIEW_ROUND_COUNT=0`, then exits 0. When process-group isolation is unavailable, Step 3 never launches reviewers but still returns a Gate-B-bypass `panel-failed` envelope, so `/design` can reach Gate C and Step 5c with zero review coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-zero-review-gates: In _step3_review_write_prelaunch_failure, emit panel-init-failed (or normalize to it before stdout) with zero-round KVs; add a harness case mirroring REASON=monitor-mode-unavailable


### FINDING_8: Preflight review_status / rounds_completed parsing can false-refuse on plan body matches
- **Reviewer(s)**: Cursor-dyn-shell-env-safety
- **Severity**: important
- **Concern**: Preflight `review_status:` / `rounds_completed:` parsing is unspecified and can scan the whole plan body. Step 5c will prepend provenance lines, then a blank line, then the plan body. A whole-file grep/scan can false-refuse when the plan text legitimately contains `rounds_completed: 0` or `review_status: panel-init-failed` in prose or examples.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-env-safety: Parse only the leading provenance header before the first blank line (or reuse a small Python helper shared with publish), validate `review_status` against an allowlist and `rounds_completed` as a non-negative integer; ignore matches in the plan body; add legacy and false-positive tests in `scripts/test-implement-preflight.sh`


### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-entry-state.sh:90-91
- **Concern**: [SCOPE-REDUCTION] Scope-anchor materialization has no shell-callable CLI route. The plan adds a Python helper in `python/plan_review.py` and tells `design-step3-entry-state.sh` to invoke it, but `python/cli.py` has no new `plan-review` verb for that helper.. Scenario: Entry-state cannot call the helper without a new subcommand or ad-hoc `python -c` import. Step 3 may still launch with a missing anchor, reproducing Bug 2.
- **Proposed resolution**: Register one verb (for example `plan-review materialize-scope-anchor`) in `python/cli.py`, or fold materialization into `plan-review step3-state` stdout/KVs. Have `design-step3-entry-state.sh` call only that registered CLI surface.



### FINDING_1: `panel-init-failed` lacks terminal wrapper contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan introduces `panel-init-failed` but does not mirror the `postplan-failed` terminal handoff in `design-step3-review.sh` (`SUMMARY_OUTCOME` export, non-zero exit, `design-stage-terminal-state.sh` staging). Orchestrators and harnesses may still treat the wrapper as a Gate-B-bypass success (exit 0) or fail to write durable terminal state before Final summary / auto-reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror `postplan-failed`: stage via `design-stage-terminal-state.sh` with `--outcome failed-panel-init`, print `SUMMARY_OUTCOME=failed-panel-init`, exit non-zero; add harness assertions like `test-design-step3-review.sh` postplan case.
  - From Cursor-Pragmatic: After allowlist normalization, when `STEP3_REVIEW_LOOP_STATUS=panel-init-failed`, print `SUMMARY_OUTCOME=failed-panel-init` and exit 1 (including prelaunch paths), parallel to `postplan-failed`.
  - From Cursor-Requirements: Wire `panel-init-failed` like `postplan-failed`/`failed-judge-panel`: invoke `design-stage-terminal-state.sh` with `--outcome failed-panel-init`, `--trigger panel-init-failed`, `--summary-outcome failed-panel-init` from `design-step3-review.sh` and/or prompt-side SKILL Step 3 terminal branch; add `test-design-stage-terminal-state.sh` coverage.


### FINDING_2: Stall-recovery token allowlists omit `panel-init-failed` tokens
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The plan adds terminal `SUMMARY_OUTCOME=failed-panel-init` and `design-stage-terminal-state.sh` staging but does not update `stall-recovery-report.sh` token allowlists. `safe_outcome_value` rejects `failed-panel-init`; `safe_trigger_value` rejects `panel-init-failed`; generic bail validation may reject tokens such as `missing-scope-anchor`. Terminal staging then fails validation, `design-failure-terminal-state.env` is not written, and the failure reporter falls back to `compose-status-missing` again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `skills/implement/scripts/stall-recovery-report.sh` (and its harness) to the plan: allowlist `failed-panel-init` in `safe_outcome_value`, `panel-init-failed` in `safe_trigger_value`, and the chosen bail token (e.g. `missing-scope-anchor` or reuse an existing generic bail token).
  - From Cursor-Requirements: Add `failed-panel-init` (and `panel-init-failed` trigger/bail tokens if used) to `stall-recovery-report.sh` outcome and related `validate-token` allowlists; extend `test-stall-recovery-report` / `test-design-stage-terminal-state` coverage.
  - From Codex-Generic: Add `failed-panel-init` to `safe_outcome_value`, generic bail/trigger allowlists as needed, and mirror in `test-design-stage-terminal-state.sh` / `test-render-final-summary.sh`.


### FINDING_3: Postplan emit harness D37 not updated for `mechanical_churn` normalization
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan changes `mechanical_churn` parsing in Python but omits the `test-design-postplan-emit.sh` harness that currently requires numeric values to fail. The D37 case expects `PLAN_SIZE_STATUS=invalid-mechanical-churn` for `mechanical_churn: 35`; `relevant-checks` routes `plan_quality.py` changes through `make test-design-postplan-emit`, so CI will fail after a Python-only test update.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `skills/design/scripts/test-design-postplan-emit.sh` (and `design-postplan-emit.md` sync note) to the plan: flip D37 to expect normalized true / rc 0, or document an explicit exception if numeric input should still fail at the merged emit layer.


### FINDING_4: `SKILL.md` omits `failed-panel-init` from orchestrator outcome enumerations
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `SKILL.md` orchestrator contracts still omit `failed-panel-init` from the Final summary `SUMMARY_OUTCOME` export list and the terminal auto-report outcome list. An implementer can add the renderer outcome in `render-final-summary.sh` yet still leave the orchestrator without a legal `SUMMARY_OUTCOME` or `design-failure-report` terminal path for `panel-init-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the `SKILL.md` edits to add `failed-panel-init` beside `failed-postplan` in the Final summary block export list, the Step 3 report-gate routing paragraph, and the `/design` auto error reporting terminal-outcome list (matching `design-failure-report.sh`).


### FINDING_5: Scope-anchor materialization omits `redact-secrets` staging
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `materialize_scope_anchor` omits the redact-secrets staging step required by `SECURITY.md`. Writing raw `issue-body.txt` (plus outline) into `plan-review-scope-anchor.txt` can send unredacted secrets to external reviewers and log-publish copies of the anchor file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pipe stripped scope (and outline append) through `python/cli.py redact secrets` before writing `plan-review-scope-anchor.txt`; add a test that a secret-bearing issue body is redacted in the staged file.


### FINDING_6: Entry-time scope-anchor failure lacks orchestrator terminal branch
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan hard-stops in entry-state but does not define orchestrator handling when `materialize-scope-anchor` fails before the background review launch. `design-step3-entry.sh` uses `set -e`; a non-zero `materialize-scope-anchor` exit aborts Step 3 entry with only stderr, not `SUMMARY_OUTCOME=failed-panel-init`, terminal-state staging, or Final summary, repeating the silent-failure pattern this issue fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a `SKILL.md` Step 3 entry branch: on `design-step3-entry.sh` / entry-state non-zero after `materialize-scope-anchor`, stage terminal state, export `SUMMARY_OUTCOME=failed-panel-init`, run Final summary, preserve `DESIGN_TMPDIR`, and do not launch `design-step3-review.sh`.




### FINDING_2: panel-init-failed normalization may never run (dead Python path + missing shell rewrite)
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan assigns post-loop `panel-failed` → `panel-init-failed` normalization to `plan_review.py` `run_main`, but `run_main` only delegates to `run_step3_review` and never parses `--mode loop`, so embedded `review-design-step3-loop.sh` can still write `panel-failed` with `REVIEW_ROUND_COUNT=0`. Separately, `design-step3-review.sh` lacks an explicit zero-round rewrite between result-env parse and stdout emit; harness updates assume `panel-init-failed` but handoff code may still emit `panel-failed` for rc=1 with `REVIEW_ROUND_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add normalization in design-step3-review.sh after result-env load (if panel-failed and no plan-review/round-1/ or REVIEW_ROUND_COUNT=0 rewrite to panel-init-failed), or restructure run_main to own --mode loop before legacy delegation; regenerate _LEGACY_ASSETS only if loop-internal anchor logic must change
  - From Cursor-Innovation: Add explicit rewrite in design-step3-review.sh between result-env parse and stdout emit; do not rely only on plan_review.py run_main lines 55-56

---


### FINDING_3: Embedded loop can conflict with or overwrite Step 3 entry scope anchor
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Scope-anchor materialization moves to Step 3 entry via `materialize-scope-anchor`, but the plan does not update embedded `plan-review-loop.sh` / `review-design-step3-loop.sh` in `_LEGACY_ASSETS`. Loop init may still strip issue-body independently (empty-anchor `panel-failed`), duplicate or conflict with entry-time logic, or overwrite the entry-time redacted `plan-review-scope-anchor.txt` with unredacted issue text, violating `SECURITY.md` staging and reintroducing secret leakage into reviewer prompts. When `plan-review-scope-anchor.txt` already exists, the loop can still run its own strip-body or append-outline path, fail on empty stripped bodies, or double-append outline content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: State in plan-review.md and loop contract: skip in-loop anchor creation when plan-review-scope-anchor.txt already exists, or regenerate legacy blobs to call materialize-scope-anchor / no-op when file present
  - From Cursor-Pragmatic: In the same change, update the embedded loop (or intercept in `run_step3_review` before `_run_legacy`) so that when `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` is present and valid, the loop does not recreate it; if recreation is still needed, call `plan-review materialize-scope-anchor` instead of duplicating strip/compose logic.
  - From Cursor-Requirements: Document and implement loop behavior to require a pre-validated anchor (skip recreate when the file is present and non-empty) or update the embedded loop asset in the same change

---


### FINDING_4: panel-init-failed terminal handoff ordering vs degradation escalation path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan retargets prelaunch failure to `panel-init-failed` and exit non-zero but does not fix ordering relative to the degradation evidence case at `design-step3-review.sh` lines 526–533. Today `monitor-mode-unavailable` exits 0 with `panel-failed`, bypassing Gate B; partial edits could record `panel-init-failed` as escalation evidence or still exit 0 instead of hard-stopping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Apply terminal handoff (stage state, SUMMARY_OUTCOME=failed-panel-init, exit 1) for panel-init-failed immediately after normalization and before the panel-failed escalation case; mirror postplan-failed block at lines 535-538

---


### FINDING_7: Step 5c publish guard must fail-closed on missing round artifacts
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Step 5c publish guard keys only on `rounds_completed=0` and `panel-init-failed`. The #4168 failure had `ROUNDS_COMPLETED=1` with no `plan-review/round-1/`; a `rounds_completed=0` check alone would still publish if normalization is missed or stale env lies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add a fail-closed publish guard: refuse when plan-review/round-1/ is absent unless review_status is an explicitly allowed degraded path with real round artifacts (e.g. cap-hit after prior launched rounds); do not trust ROUNDS_COMPLETED or REVIEW_ROUND_COUNT alone




### FINDING_2: Codex drafter prompt omits boolean-only `mechanical_churn:` rule
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Bug 1 fix updates Step 2b prose in `skills/design/SKILL.md` but the default path launches `design-step2b-drafter.sh`, whose drafting requirements block still describes optional `mechanical_churn` without boolean-only grammar. Codex can keep emitting `mechanical_churn: 1100` and trigger `PLAN_SIZE_STATUS=invalid-mechanical-churn` postplan failures despite SKILL.md and `plan_quality.py` tolerance changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Cursor-Pragmatic: Add the same boolean-only mechanical_churn rule to design-step2b-drafter.sh (and any drafter harness assertions); treat SKILL-only wording as insufficient for Bug 1
  - From Cursor-Requirements: Add the same boolean-only mechanical_churn: rule to the design-step2b-drafter.sh drafting requirements block (and sync design-step2b-drafter.md if kept as contract).


### FINDING_3: No fail-closed guard when `feature-description.txt` is missing past Step 0
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Bug 6 also requires aborting when `/design` proceeds past Step 0 toward Step 1c/1d/2b without `feature-description.txt`; the plan only adds a post-init guard inside `design-step0-init.sh` when init runs. Resume paths skip Step 0 init, and a missed replace-path init call would still reach Step 0c/1c with a missing `feature-description.txt`, reproducing silent downstream failures in Step 2b/3 inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a fail-closed check in design-step0c.sh (or the Step 1c entry fence) that errors when feature-description.txt is absent or empty before continuing past Step 0.


### FINDING_4: Prelaunch `panel-init-failed` paths skip terminal handoff helper
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Prelaunch failure paths do not call the shared terminal handoff helper. The plan retargets `_step3_review_write_prelaunch_failure` and the new missing-anchor guard to emit `panel-init-failed` and exit non-zero, but the `design-stage-terminal-state.sh` + `SUMMARY_OUTCOME=failed-panel-init` block is only described after post-loop normalization. Early exits never reach that tail, so monitor-mode and scope-anchor prelaunch failures can return `panel-init-failed` KVs without staging terminal state or emitting `SUMMARY_OUTCOME`, and the orchestrator may not run the Final summary / hard-stop path (mirrors pre-`postplan-failed` wiring).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Extract one `_step3_review_terminal_panel_init_failed` helper (normalize KVs, stage via `design-stage-terminal-state.sh`, print `SUMMARY_OUTCOME=failed-panel-init`, `exit 1`) and call it from `_step3_review_write_prelaunch_failure`, the missing-anchor prelaunch guard, and the post-loop normalization path.




### FINDING_1: Terminal staging helper omits required `--exit-code`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `_step3_review_terminal_panel_init_failed` helper is expected to call `design-stage-terminal-state.sh` without `--exit-code` (and without mirroring `stage_design_terminal_state` in `design-publish.sh`). `design-stage-terminal-state.sh` rejects empty `--exit-code` (lines 74–77), so staging can emit `STAGED=false`, stall-recovery tokens never validate, and `design-failure-report.sh` falls back to `compose-status-missing` instead of filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `--exit-code 1` (or the real wrapper rc) and `--summary-outcome failed-panel-init` to every `design-stage-terminal-state.sh` invocation in the helper; extend test-design-step3-review.sh runtime staging to assert EXIT_CODE is written, not only invoke the stage helper in isolation.


### FINDING_2: Zero-round normalization must run before `panel-failed` coercion
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned `_step3_review_normalize_zero_round_status` must not run after empty/invalid status is already coerced to `panel-failed`. Today `design-step3-review.sh` maps missing/invalid `STEP3_REVIEW_LOOP_STATUS` to `panel-failed` at lines 473–506, then records escalation evidence for `panel-failed` at lines 526–533. If normalization is inserted too late, init failures (missing anchor, monitor-mode-unavailable, empty result env) stay on the Gate B bypass `panel-failed` path and Bug 3 recurs. Reviewers disagree on the exact insertion point relative to the LOOP_STATUS→STEP3 derivation block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and implement ordering explicitly: load env → derive STEP3 from LOOP_STATUS (473-491) → `_step3_review_normalize_zero_round_status` → if `panel-init-failed`, call terminal helper and exit 1 → only then allowlist/emit KVs and escalation evidence for true degraded `panel-failed`.
  - From Cursor-Innovation: Call normalization immediately after `_safe_step3_env` load (~line 450) and before the `STEP3_REVIEW_LOOP_STATUS` empty/invalid branches; when it yields `panel-init-failed`, invoke `_step3_review_terminal_panel_init_failed` and never reach the `panel-failed` allowlist or escalation `case` at lines 526-533.


### FINDING_3: Zero-round normalization must key on `round-1/` presence, not counters alone
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Zero-round normalization that ORs on `REVIEW_ROUND_COUNT=0` or `ROUNDS_COMPLETED=0` can misclassify a degraded but real review run when `plan-review/round-1/` exists but env counters are stale or partial. That would rewrite `panel-failed` to `panel-init-failed`, run terminal handoff, and block a run that did launch reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Treat `plan-review/round-1/` as ground truth: normalize to `panel-init-failed` only when that directory is absent; do not key on `REVIEW_ROUND_COUNT=0` or `ROUNDS_COMPLETED=0` alone when `round-1/` exists


### FINDING_6: Gate C `--skip-approve` bypasses mandatory `panel-failed` acknowledgment
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Gate C `panel-failed` acknowledgment is only specified for `skip_approve_requested=false`. The existing `--skip-approve` auto-approve path never fires the Gate C prompt. A degraded `panel-failed` run that reaches Step 4b with `--skip-approve` still auto-approves and proceeds to Step 5c with no acknowledgment surface, recreating silent approval risk for partial review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Extend approval-gates.md and skills/design/SKILL.md Step 4b: when review env shows degraded panel-failed, disable --skip-approve auto-approve (force the Gate C prompt with the mandatory warning) or add a separate acknowledgment gate before Step 5

---

**Merge notes**

| Input | Disposition |
|-------|-------------|
| FINDING_2 + FINDING_5 | Merged → **FINDING_2** (same Bug 3 ordering risk; conflicting insertion points kept as separate verbatim bullets) |
| FINDING_6 | Renumbered → **FINDING_3** (distinct false-positive risk vs ordering) |
| FINDING_3 | Renumbered → **FINDING_4** |
| FINDING_4 | Renumbered → **FINDING_5** |
| FINDING_7 | Renumbered → **FINDING_6** |
| FINDING_1 | Unchanged → **FINDING_1** |



