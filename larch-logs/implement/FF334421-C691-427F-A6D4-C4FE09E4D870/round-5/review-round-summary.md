# Review Round 5

- Mode: `diff`
- 18 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Infrastructure ShipErrors are always classified as stalls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shipstate-output.txt
- **Severity**: important
- **Concern**: `_is_infrastructure_ship_error()` is a stub returning false, so infrastructure state/contract failures map to `STALLED` and can write terminal stall/finalize state instead of returning `INTERNAL_ERROR` without finalize persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-shipstate-output.txt: Implement `_is_infrastructure_ship_error()` for state I/O / contract failures (matching the error text or error subclass), map those to `Outcome.INTERNAL_ERROR`, and skip terminal stall persistence for that class.


### FINDING_10: Transient-stall retry persistence has split authority and unsafe rewrite guidance
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python transient retry state, orchestrator retry counters, terminal stall persistence, and SKILL-directed key rewrites can diverge on the 4th transient failure, causing wrong exit routing, missing stall state, double rewrites, or ad-hoc prompt-side state-file mutation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Python 3.11 support and CI coverage are inconsistent with the 3.12 ship gate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` now hard-requires Python 3.12 while some docs/tooling still reference 3.11 support, and CI no longer catches report-tokens behavior on 3.11.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Checks-stall tests do not assert terminal finalize state
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Checks-phase stall coverage can pass even if `finalize-state.sh` stops being written with `STALL_TRACKING=true` and `EXIT_CODE=4`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_15: Existing ship-state merge can ingest unsafe existing content
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-promptsafe-output.txt
- **Severity**: important
- **Concern**: `_write_ship_state` merges pre-existing `ship-pr-state.sh` contents without a key allowlist and reads before symlink rejection, allowing same-UID symlink/content injection to influence later classify or context hydration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-promptsafe-output.txt: Fail closed before read when `Path(ctx.state_file).is_symlink()` (or open with `O_NOFOLLOW`) and mirror the write-side symlink rejection in `SECURITY.md`.


### FINDING_18: Phantom probe registry still names `ship-pr.sh` instead of active Step 8+ driver
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-selector-output.txt
- **Severity**: important
- **Concern**: The Phantom Untracked Probe registry says it runs before `ship-pr.sh` first invocation, which can cause default Python runs to skip or mis-order the probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-selector-output.txt: Mirror line 998 in the registry (“active Step 8+ driver unless `LARCH_SHIP_PR_IMPL=bash`”) and add a `test-implement-structure.sh` grep pin.


### FINDING_2: Atomic state writers diverge and stale temp files can block progress
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `ship-pr-state.sh` and `finalize-state.sh` use separate atomic-write implementations; stale `.tmp` handling and symlink hardening can diverge, including a fresh orphaned `ship-pr-state.sh.tmp` blocking all state writes until manual cleanup or timeout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Match finalize.py tmp handling (unlink before write) or fail open on stale tmp; add a regression test for leftover .tmp.


### FINDING_23: Python-default run-log refresh docs mention only bash internals
- **Reviewer(s)**: dyn-selector-output.txt
- **Severity**: latent
- **Concern**: Pre-ship/retry refresh prose attributes retry log refresh exclusively to `scripts/refresh-run-logs.sh` inside `ship-pr.sh`, omitting Python’s `run_logs.flush_logs_pre` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-selector-output.txt: Document both surfaces: bash opt-in → `refresh-run-logs.sh` Triggers A–C in `ship-pr.sh`; default Python → `run_logs.flush_logs_pre` at CI/rebase boundaries, with orchestrator autonomous CI-fix still calling `refresh-run-logs.sh` per line 1108.


### FINDING_24: Config docs describe version-file env vars as bash-only
- **Reviewer(s)**: dyn-selector-output.txt
- **Severity**: latent
- **Concern**: `LARCH_VERSION_FILES` / `LARCH_BUMP_FILES` docs mention only `ship-pr.sh`, while Python rebase code also reads the env vars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-selector-output.txt: Qualify that both drivers honor the variable (bash via `ship-pr.sh` / `run_rebase_rebump`; Python via `python/rebase.py` and the `ship_pr_pre_push` handoff), or point to a single shared env contract section.


### FINDING_25: Postbump degradation docs mention only bash driver
- **Reviewer(s)**: dyn-selector-output.txt
- **Severity**: latent
- **Concern**: Postbump conflict/degradation text names only `scripts/ship-pr.sh`, so Python-default operators may look at the wrong recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-selector-output.txt: Name the active driver in the postbump notice (“Python ship driver unless `LARCH_SHIP_PR_IMPL=bash`”) and cite the equivalent Python stall behavior.


### FINDING_29: Final-report line-count persistence can abort despite non-fatal contract
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` wraps line-count computation as best-effort but calls `merge_replace_state_keys` under `set -e`, so state rewrite failures can abort final-report generation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Wrap the merge call in `set +e` / `set -e` (or append `|| true` with a stderr breadcrumb), matching the non-fatal contract used for `compute-pr-line-counts.sh`.


### FINDING_30: Structure harness bash-matrix window anchor no longer matches
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `bash_matrix_gate_window` anchors on removed `**Exit 5**` prose, so the awk window can run to EOF and make greps depend on unrelated trailing SKILL content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Retarget the end anchor to a line that still exists and bounds only the bash exit matrix (for example `**Exit 6**:` or the OOS checkpoint heading), and document that anchor in `scripts/test-implement-structure.md`.


### FINDING_34: Scope-reduction marker detection is inconsistent across dedup/voting paths
- **Reviewer(s)**: dyn-votesemantics-output.txt
- **Severity**: important
- **Concern**: Plan-review dedup and scope-reduction detection inspect different text fields/severity prefixes, so `[SCOPE-REDUCTION]` findings can be wrongly merged, missed, or sent through normal voting instead of the special withhold path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-votesemantics-output.txt: Reuse the same candidate extraction as `check-scope-reduction-marker.sh` inside the embedded dedup helper (or call the helper per block) so `problem_text` and `is_scope_reduction_block()` agree on which text constitutes the finding; add a harness case where the marker appears only on `what:` and dedup must not collapse an untagged sibling.
  - From dyn-votesemantics-output.txt: Either extend `norm()` to strip any leading `[word]` token (with tests), or document and enforce a single severity vocabulary across reviewer templates and the detector.


### FINDING_38: Scope-anchor prompt rendering lacks size caps in plan-review paths
- **Reviewer(s)**: dyn-promptsafe-output.txt
- **Severity**: important
- **Concern**: Plan-review reviewer prompts and MainAgent fallback inline untrusted scope anchors without the 64 KiB cap used for voter prompts, enabling context stuffing/run-cost amplification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-promptsafe-output.txt: Apply the same hard bound used in `render-voter-prompt.sh` (`validate_scope_anchor_file`, 64 KiB fail-closed) to `--feature-file` in `render-plan-review-prompt.sh`, and optionally enforce the same limit when writing `plan-review-scope-anchor.txt` in `plan-review-loop.sh` so oversize anchors fail before dispatch.
  - From dyn-promptsafe-output.txt: Reuse the shared 64 KiB validation helper (or duplicate the exact `wc -c` / fail-closed check) before streaming the anchor block.


### FINDING_4: Step 8+ routing prose mixes Python-default and bash-only contracts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-selector-output.txt, dyn-votesemantics-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md` labels shared exit routing as bash-only while also including Python JSON/finalize/state-file branches, so orchestrators may skip Python CI-fix steps or incorrectly parse bash-only state on the default Python path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-selector-output.txt: Retitle/reframe: e.g. “Shared Step 8+ exit routing (both drivers; path-specific sub-clauses below)” and move the bash-only qualifier to bullets that truly require `ship-pr-state.sh` continuation parsing. Duplicate or cross-link the autonomous CI-fix steps 1–12 inside the Python driver selector paragraph.
  - From dyn-votesemantics-output.txt: Split the section into two explicit subsections (“Python selector routing” vs “Bash exit matrix”) with no shared bullet list, or move all Python branches back under the Python selector block and keep the gated block bash-only.


### FINDING_6: `--state-file` hydration gap clears seeded stall/resume metadata
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shipstate-output.txt
- **Severity**: important
- **Concern**: `_ctx_from_args` binds `--state-file` after `RunContext.from_env()` without rehydrating from that file. The first routine `_write_ship_state` can therefore run with default-false stall flags and clear orchestrator-seeded `STALL_*`, `RESUME_PHASE`, `CALLER_KIND`, and related markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-shipstate-output.txt: After applying CLI overrides, re-hydrate from `ctx.state_file` (same helpers as `RunContext.from_env()`, or a shared `overlay_from_state_file(ctx)`), and use that in `_hydrate_resume_context` for open-pr resumes as well.
  - From dyn-shipstate-output.txt: Fix context hydration first; if stale-clearing remains desired for genuinely fresh runs, gate clearing on an explicit “healthy/fresh” signal rather than default-false context on the production CLI path.


### FINDING_7: Optional stall evidence validation hard-aborts instead of falling back
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: `stall-recovery-report.sh` duplicates validation logic and treats oversize/symlinked optional evidence files inconsistently, sometimes aborting classification with exit 3 instead of skipping invalid optional layers and continuing with remaining evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-bash32-output.txt: On oversize/non-regular optional evidence files, return 1 and skip that layer (same as missing file), reserving `exit 3` for `ship-pr-state.sh` symlink/syntax-invalid cases already handled at lines 605–612; or apply the 64KiB cap consistently on both KV-read and evidence paths.
  - From dyn-bash32-output.txt: For `finalize-state.sh` / `session-env.sh`, treat validation failures like missing evidence (`return 1`); only emit `exit 3` for the dedicated `ship-pr-state.sh` guards already at lines 605–612.


### FINDING_9: Pre-push conflict handoff has finalize/resume contract gaps on Python default
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-votesemantics-output.txt
- **Severity**: important
- **Concern**: `PrePushConflictHandoff` exits 4 with resume/conflict markers in `ship-pr-state.sh` but no `finalize-state.sh`, while SKILL prose can steer consumers toward finalize-first stall reads. Python resume can also reject documented bash-style phase-14 handoffs without the expected flag file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-votesemantics-output.txt: Teach `_resume_plan()` to honor the same `ship_pr_pre_push` / `ship-pr-rrr-phase14` handoff as bash (recreate or trust the flag, or accept resume tokens when `CONFLICT_FILES` was cleared by conflict-resolution), and add an integration test that simulates post–conflict-resolution re-entry.
  - From dyn-votesemantics-output.txt: Either write a minimal stall-shaped `finalize-state.sh` on `PrePushConflictHandoff` (without treating the run as fully terminal), or narrow SKILL Step 18a/Exit 4 prose to state that `ship_pr_pre_push` stalls are finalize-absent by design and classify only from `ship-pr-state.sh`.


