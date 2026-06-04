### FINDING_1: Boolean `partition_requested` is misread without `jq`
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The merged `--with-plan-size` path plans to read `partition_requested` with a helper whose sed fallback only parses quoted strings, while `run-params.json` writes the field as an unquoted JSON boolean. Without `jq`, `/design --partition` can be silently treated as not partitioned and skip the rc13 Split route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the helper or this call to parse unquoted true/false booleans in the fallback, and add the partition rc13 test with jq hidden from PATH
  - From Codex-Edge: Before using this helper for partition_requested, extend its fallback to parse unquoted true/false booleans, or fail closed when jq is unavailable for this boolean; add a jq-absent partition_requested=true test in test-design-postplan-emit.sh
  - From Codex-Pragmatic: Add a tiny boolean-capable reader or extend the sed fallback to parse bare true/false before defaulting false, and cover this in the new --with-plan-size partition test
  - From Codex-Requirements: Extend the helper or add a boolean-specific reader that parses unquoted true/false, and add a --with-plan-size test that forces the no-jq fallback for partition_requested=true.

### FINDING_2: Legacy fat-fence rc guards can preempt merged driver handlers
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The thin-fence rewrite does not explicitly remove or adapt legacy guards that only accept rc 0/1. New driver action codes such as rc 10/11/12/13 can still hit mandatory-key or final abort checks before the intended `case` handlers run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the collapsed Step 2b / Gate B / discussion / Gate A fences, mirror Step 3.6: `echo` display, `case "$_postplan_rc"`, handle 10/11/12/13/2/1 explicitly, and delete the catch-all abort plus the rc 0-or-1-only mandatory-key gate (or extend it to action codes)

### FINDING_3: Step 1e may incorrectly inherit `--force-validate`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan pins Step 1e to the discussion-round2 template, which implies `--force-validate`; Gate A optional-trailer re-entry currently does not use that flag, so copying the template would change quick `review_budget` behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify Step 1e uses --with-plan-size only (match Gate B); reserve --force-validate for discussion-round2; pin argv separately in test-design-structure.sh

### FINDING_4: rc10 validator context can be lost after removing stdout KV merge
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan removes fat stdout KV parsing but puts validator state only in `.design-postplan-emit-result.env`; rc10 Fix-and-retry/Override paths still need `VALIDATE_*` values and can proceed with empty defect context unless those keys are read explicitly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After echo "$out", read allowlisted keys from .design-postplan-emit-result.env in rc 10 and Override arms only (never source); document in design-postplan-emit.md and thin-fence SKILL.md prose
  - From Cursor-Pragmatic: In `design-postplan-emit.md` orchestrator handoff and each merged thin-fence site, specify an allowlisted read of `.design-postplan-emit-result.env` on rc 10 (and Override continuation), mirroring Step 3.6’s rc-specific state handling—not the removed fat stdout merge loop

### FINDING_5: Structure tests still pin retired fat-fence artifacts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The migration retires inline parse/fat-fence behavior, but existing `scripts/test-design-structure.sh` checks still look for `.design-postplan-emit-result.env`, `_postplan_out` heredoc parsing, and literal `check-plan-size.sh` placement that may no longer exist in the collapsed Step 2b region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: List explicit retirements: lines 515-517, 689-694, and any pin requiring stdout KV merge or literal check-plan-size.sh in the Step 2b region; replace with --with-plan-size and assert_thin_fence pins per plan lines 155-167
  - From Cursor-Requirements: Add an explicit test-design-structure.sh task: drop or repoint lines 515-516 for merged sites; keep only pins still valid on thin fences (for example rc=2 abort prose at 517 if retained in the case arm)

### FINDING_6: Nonfatal plan-size logging can leak helper KVs
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The rc2/rc3 nonfatal path may call `append-tool-failure.sh`, whose success KVs such as `APPENDED=` and `LOG=` can appear in captured driver output and violate the no-KV/display-only contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Capture or redirect append-tool-failure.sh output in the --with-plan-size rc2/3 block, and add the nonfatal rc2/3 test assertion that stdout has no APPENDED= or LOG= lines

### FINDING_7: Shared validator retry prose still uses legacy emit/validate flow
- **Reviewer(s)**: Cursor-dyn-contract-matrix
- **Severity**: important
- **Concern**: The shared Plan command validator failure section still tells Fix-and-retry to run raw `ACTION=EMIT_PLAN` plus `ACTION=VALIDATE_PLAN_COMMANDS`, which bypasses same-site `--with-plan-size` re-entry and its plan-size mapping/sentinel behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-contract-matrix: Update Fix-and-retry/Override bullets (and edit-in-sync list) to name --with-plan-size re-entry per site; retain raw emit/validate only for Step 5c composed-plan path

### FINDING_8: Gate B rc12 Override may skip the Step 2b.5 sentinel
- **Reviewer(s)**: Codex-dyn-contract-matrix, Codex-dyn-sentinel-lifecycle
- **Severity**: important
- **Concern**: When Gate B hard-size handling moves into the merged rc12 arm, the Override path can continue without passing through the old standalone Step 2b.5 success boundary, leaving `.completed/step-2b.5` unwritten for pause/resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-matrix: Add the same .completed/step-2b.5 write/update to the Gate B rc12 Override arm before Step 3.6, and pin that arm in scripts/test-design-structure.sh
  - From Codex-dyn-sentinel-lifecycle: Add a narrow Gate B rc12 Override arm requirement: before continuing to Step 3.6, run mkdir -p "$DESIGN_TMPDIR/.completed" and : > "$DESIGN_TMPDIR/.completed/step-2b.5"; add a matching scripts/test-design-structure.sh pin for Gate B hard Override.

### FINDING_9: Site-aware hard-size prompt options are not consistently documented or pinned
- **Reviewer(s)**: Codex-dyn-contract-matrix, Codex-dyn-harness-contract
- **Severity**: important
- **Concern**: Existing/public docs and proposed structure tests may preserve a global Split/Cancel contract and fail to pin where Override must remain available, creating conflicts across initial/discussion, Gate B, and plan-review-loop hard-size prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-matrix: Update flags.md’s plan-size prose to say hard prompts are site-aware: initial and discussion use Split/Cancel; Gate B and plan-review-loop use Split/Override/Cancel
  - From Codex-dyn-harness-contract: Add narrow structure assertions that retained plan-review-loop and Gate B hard-size prompts include Split / Override / Cancel, while initial/discussion retained prompts stay Split / Cancel

### FINDING_10: Retained plan-review-loop does not handle rc2/rc3 nonfatally
- **Reviewer(s)**: Codex-dyn-contract-matrix
- **Severity**: latent
- **Concern**: `plan-review-loop.sh` still calls `check-plan-size.sh` directly under `set -e`; rc2/rc3 can terminate the loop before it writes the documented `LOOP_STATUS` handoff, despite the plan preserving those codes as nonfatal diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-matrix: Add a minimal set +e capture around the plan-review-loop check-plan-size call and handle rc2/rc3 as warning-and-continue, matching the standalone Step 2b.5 diagnostic contract without changing check-plan-size.sh

### FINDING_11: Refine-return sentinel is missing from normative Split-path doc
- **Reviewer(s)**: Cursor-dyn-sentinel-lifecycle
- **Severity**: important
- **Concern**: The plan pins Refine `.completed/step-2b.5` writes in several places but omits `decompose-panel.md`, which is normative for Split-path entry; implementers could miss the sentinel write on merged rc12/rc13 Refine returns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sentinel-lifecycle: Add `skills/design/references/decompose-panel.md` to Files to modify/create; in §4 Stage 0 option 3 (and §9 terminal outcomes), require `mkdir -p "$DESIGN_TMPDIR/.completed" && : > "$DESIGN_TMPDIR/.completed/step-2b.5"` before return when the caller used `--with-plan-size` (merged fence), matching SKILL.md Refine arms

### FINDING_12: Soft-advisory plus hard-trigger output variant is underspecified
- **Reviewer(s)**: Cursor-dyn-stream-contract
- **Severity**: important
- **Concern**: The output discipline covers advisory-only FD3 display but not the combined case where `SOFT_ADVISORY=true` and `HARD_TRIGGER_FIRED=true`; the merged rc12 path can omit the breadcrumb that explains the downgrade context before the hard prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stream-contract: Pin both soft-advisory emit strings in design-postplan-emit.md and the driver spec: advisory-only on clean rc0; advisory plus hard-section preamble before exit 12 when both flags are true

### FINDING_13: rc3 diagnostics can be lost under stdout-only capture
- **Reviewer(s)**: Codex-dyn-stream-contract, Codex-dyn-harness-contract
- **Severity**: important
- **Concern**: The plan requires stdout-only KV capture while promising rc3 diagnostics preservation, but `check-plan-size` writes rc3 diagnostics to stderr; validation logs and execution issue entries can omit the actual diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stream-contract: Capture stderr separately for nonzero plan-size runs, keep stdout-only KV parsing, and combine stdout plus stderr only for the validation log and append-tool-failure entry.
  - From Codex-dyn-harness-contract: Capture stderr to a sidecar for nonzero plan-size exits without parsing it as KVs, append that file for rc 3, and assert the rc 3 stderr text appears in the validation log

### FINDING_14: Shared post-apply flow still assumes standalone Step 2b.5 after driver rc0
- **Reviewer(s)**: Cursor-dyn-harness-contract
- **Severity**: important
- **Concern**: Shared post-apply steps still key clean/defect continuation on driver exit 0 and a follow-on standalone Step 2b.5 call, which conflicts with `--with-plan-size` returning rc10 for defects and folding plan-size handling into rc0/rc12/rc13.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-contract: Rewrite steps 7-9 for --with-plan-size: rc 10 to shared validator failure (same-site re-entry), rc 0 to sentinel write then Step 3.6 without standalone 2b.5, rc 12/13 to Split arms; keep standalone Step 2b.5 only for Override and LOOP_STATUS=plan-size-trigger

### FINDING_15: Hard+partition precedence is untested
- **Reviewer(s)**: Codex-dyn-harness-contract
- **Severity**: important
- **Concern**: The planned harness covers hard and partition routes separately but not their co-occurrence, so an implementation that checks partition before hard can pass while violating the hard-wins contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-contract: Add one minimal --with-plan-size test with partition_requested=true and a hard-sized plan, asserting rc 12 and not rc 13
