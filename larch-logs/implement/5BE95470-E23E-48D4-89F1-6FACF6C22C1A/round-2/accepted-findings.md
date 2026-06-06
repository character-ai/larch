### FINDING_1: step-5c sentinel deferred outside publish fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: The audit table and plan item 20 require a `PLAN_WRITE_OK=true`-gated `step-5c` write inside the `design-publish.sh` fence immediately after `PLAN_WRITE_OK` is parsed. Implementation writes `step-5c` at a separate orchestrator prose success boundary (Step 5c item 6) after the fence ends. A pause after successful publish but before that prose boundary leaves `step-5c` unset, so resume can replay publish/rename work and structure tests can pass while behavior diverges from the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Move gated step-5c write into design-publish fence after PLAN_WRITE_OK parse; update item 6 and assert_folded_sentinel_writes to require in-fence ordering
  - From cursor-specialist-plan-fidelity-output.txt: Append a PLAN_WRITE_OK=true-gated : > "$DESIGN_TMPDIR/.completed/step-5c" inside the design-publish.sh fence immediately after PLAN_WRITE_OK is resolved; update audit table and tests to match
  - From dyn-sentinel-ordering-output.txt: Append the gated `mkdir -p … && : > …/step-5c` block to the publish fence immediately after `PLAN_WRITE_OK` is parsed (still inside the `PLAN_WRITE_OK=true` branch), and extend `assert_folded_sentinel_writes` / `assert_publish_fence_guards` to assert ordering (parse → gated write → no second pause before fence exit), not merely that prose mentions the gate.


### FINDING_10: `assert_fence_write_before_pause` inadequately enforces before-pause ordering contract
- **Reviewer(s)**: dyn-sentinel-ordering-output.txt
- **Severity**: important
- **Concern**: `assert_backward_reentry_guards` only greps for the four Step 3 bypass-package restore lines and never calls `assert_fence_write_before_pause` for `step-2a`, `step-2a.5`, `step-2b`, or `step-2b.5`. Separately, `assert_fence_write_before_pause` matches only the exact substring `: > "$DESIGN_TMPDIR/.completed/${step_token}"`, so it would miss hosts using solely conditional restore forms without that exact `: >` tail. Phase 7's contract treats both unconditional and idempotent restore forms as load-bearing; a future edit could reorder writes after pause with no harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-sentinel-ordering-output.txt: Extend `assert_backward_reentry_guards` (or `assert_folded_sentinel_writes`) to call `assert_fence_write_before_pause` for each bypass sentinel on the Step 3 entry fence, or add explicit line-order checks that each restore line precedes the first `design-pause-save.sh` line.
  - From dyn-sentinel-ordering-output.txt: Teach `assert_fence_write_before_pause` to accept either `: > "$DESIGN_TMPDIR/.completed/step-X"` or `[ -f "$DESIGN_TMPDIR/.completed/step-X" ] || : > "$DESIGN_TMPDIR/.completed/step-X"`, apply it to all Step 3 bypass sentinels, and add a negative test that pure conditional-only variants without the canonical `: >` tail still fail if mis-ordered.


### FINDING_11: step-5c audit table contradicts implementation and tests
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-artifact-allow-ordering-output.txt
- **Severity**: latent
- **Concern**: The Phase 7 audit table and completion-sentinel prose list `step-5c` as hosted in the `design-publish.sh` fence when `PLAN_WRITE_OK=true`, but implementation writes it in orchestrator prose after the fence, and structure tests pin the prose gate while forbidding an in-fence write. This split contract is easy to mis-implement in a future edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Reconcile SKILL.md audit table with the chosen step-5c host (in-fence per plan or prose per current tests)
  - From dyn-artifact-allow-ordering-output.txt: Align the audit table and "Completion sentinels" prose with the actual host: "orchestrator Step 5c item 6 after `PLAN_WRITE_OK` parse; not inside `design-publish.sh` fence," and add a negative harness assertion that the publish fence must not contain `step-5c` (already partially present).


### FINDING_14: `render-plan-*` prompt files still top-level publishable
- **Reviewer(s)**: dyn-deny-list-gaps-output.txt
- **Severity**: important
- **Concern**: Issue #3534 adds deny arms for raw plan-review transcripts and `claude-plan-*.prompt`, but `render-plan-cursor-*.prompt`, `render-plan-codex-*.prompt`, and `render-plan-*-dyn-*.prompt` from `dispatch-plan-review-panel.sh` remain top-level publishable. Those files embed the same sensitive material the new arms exclude. `SECURITY.md` documents the new exclusions but does not call out this remaining surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deny-list-gaps-output.txt: Add deny arms for `render-plan-cursor-*.prompt`, `render-plan-codex-*.prompt`, and `render-plan-*-dyn-*.prompt` (or a single `render-plan-*.prompt` arm if basename shape allows), add matching deny-loop fixtures in `scripts/test-design-log-publish.sh`, and update `SECURITY.md` / `scripts/design-log-publish.md` so documented publication boundaries match code.


### FINDING_15: Missing deny-list test fixtures for Codex-primary and Claude `.tsv` sidecars
- **Reviewer(s)**: dyn-deny-list-gaps-output.txt
- **Severity**: latent
- **Concern**: Deny arms for `codex-primary-plan-*-output*.txt.tsv` and `claude-plan-*-output*.txt.tsv` exist in `design-log-publish.sh`, but the integration harness only creates and asserts denial for `cursor-plan-arch-output.txt.tsv`. A future edit that drops those case arms would still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-deny-list-gaps-output.txt: Add top-level fixtures such as `codex-primary-plan-arch-output.txt.tsv` and `claude-plan-generic-output.txt.tsv`, include them in the denied-basename loop, and ideally add direct `design_artifact_excluded` unit assertions so fixture drift cannot silently reopen TSV publication.


### FINDING_16: `t6e` live Codex probe lacks post-probe secret containment checks
- **Reviewer(s)**: dyn-probe-secret-containment-output.txt
- **Severity**: important
- **Concern**: The new `t6e` case runs a live env-key Codex probe with `OPENAI_API_KEY=<REDACTED-TOKEN>` but does not apply the same post-probe secret-containment checks added for sibling `t10-env-key-false`. Unlike `t10-env-key-false`, `t6e` has no recursive `grep -Fr '<REDACTED-TOKEN>'` scan and no `assert_no_probe_homes` call, so a regression that leaves the sentinel in probe sidecars or TMPDIR debris would not fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-secret-containment-output.txt: Mirror the `t10-env-key-false` tail: after the stamp assertions, add `if grep -Fr '<REDACTED-TOKEN>' "$SCRATCH/t6e" 2>/dev/null; then fail ...; fi` and `assert_no_probe_homes "codex env-key login-decoy cleanup" "$SCRATCH/t6e"`.


### FINDING_17: Legacy env-key strip test does not scan isolated HOME for sentinel leaks
- **Reviewer(s)**: dyn-probe-secret-containment-output.txt
- **Severity**: latent
- **Concern**: The legacy env-key strip leak guard only recursively scans the case TMPDIR, while the sentinel also lives under the isolated HOME fixture at `$SCRATCH/t-legacy-strip-home/.codex/config.toml`. A bug that wrote the stripped credential into a new file under HOME (outside the fixture path) would not be caught; the test only proves the fixture file is unchanged via `cmp`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-secret-containment-output.txt: Add a targeted HOME scan that excludes the known fixture, e.g. `find "$SCRATCH/t-legacy-strip-home" -type f ! -path "$_legacy_fixture" -print0 | xargs -0 grep -Fl '<REDACTED-TOKEN>'` and fail on any hit, or recursively grep the parent `$SCRATCH` while excluding the fixture copy path.


### FINDING_2: Step 2a entry writes discussion sentinels before validation guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 2a entry writes folded discussion completion sentinels (`step-1c` through `step-1e`) before `run-params.json` validation and SIMPLE conflict checks. On SIMPLE conflict or unreadable run-params, the fence exits 1 after marking those steps complete. Pause/resume then routes to Step 2a and can skip replaying sketches or discussion while artifacts are inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Move validation/conflict checks before folded sentinel writes, or delete sentinels on those exit paths.
  - From cursor-specialist-security-output.txt: Move sentinel writes after successful SIMPLE validation or delete folded sentinels on conflict exit before exit 1.
  - From cursor-specialist-edge-cases-output.txt: Move run-params/SIMPLE checks before folded sentinel writes, or roll back discussion markers on exit 1.


### FINDING_3: Missing harness coverage for Step 0b Q&A-only fence
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Check 21 in `scripts/test-design-structure.sh` never asserts the Step 0b already-planned Q&A-only bash fence that writes `step-1c`/`step-1d`/`step-1d.5` before pause-check. Removing or reordering `skills/design/SKILL.md:474-481` would not fail the structure harness; pause-resume duplicates the logic inline, so both tests could stay green while resume replays discussion on Q&A-only exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add assert_qa_only_contiguous_prefix using extract_bash_fence_after_marker on the Step 0b branch and assert_fence_write_before_pause for step-1c/1d/1d.5.


### FINDING_4: Step 3 entry unconditionally clears downstream state and fabricates bypass markers
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-allow-ordering-output.txt
- **Severity**: latent
- **Concern**: Step 3 entry prose limits downstream `rm`, `step-1e` write, and Step 2 bypass restoration to backward re-entry paths, but the Bash fence runs those operations on every Step 3 entry with no route guard. Unconditional clearing of `step-3` through `step-4b` and `[ -f … ] || : > …` restoration of `step-2a`/`step-2a.5`/`step-2b`/`step-2b.5` can fabricate completion on corrupt resume, manual tmpdir edit, or routing bug—letting pause/resume jump to review while skipping sketches/dialectic/plan gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Gate bypass restoration on explicit backward/direct-review route flags; require artifact checks before synthesizing Step 2 markers.
  - From cursor-specialist-plan-fidelity-output.txt: Gate rm/restore on an explicit re-entry sentinel or document unconditional idempotent clear in the audit table
  - From dyn-artifact-allow-ordering-output.txt: Gate the `rm`, `step-1e` write, and bypass-package restore behind an explicit re-entry predicate (e.g. backward-loop sentinel, absence of `step-2b.5` with `plan.txt` present, or a dedicated `$DESIGN_TMPDIR/.step3-reentry` flag set only by Gate A direct-review / Gate C re-run paths), and keep first-time Step 3 entry to source-env + pause-check + timing only.


### FINDING_6: Structure harness missing HARD/degraded branch guards on Step 2a.5 and 2b preludes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The structure harness does not assert HARD/degraded branch guards on Step 2a.5 and Step 2b prelude hosts required by plan testing strategy item 3. SIMPLE runs that incorrectly enter 2a.5/2b preludes could satisfy host-map tests while violating SIMPLE-vs-HARD host separation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add classification guards to the prelude fences and/or assert_fence_write_before_pause checks that require HARD/degraded guards and fail when writes are unconditional


