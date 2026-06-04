### FINDING_1: Run-statistics may be written before OOS checkpoint passes
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed OOS pipeline moves run-statistics writing ahead of the existing disposition checkpoint, so a later checkpoint failure could leave durable run statistics even though OOS disposition remains unresolved.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch, Codex-Pragmatic: Keep run-statistics owned by the existing post-checkpoint Step 8+ block, or move the checkpoint into the new reference before any run-statistics write.
  - From Codex-dyn-contract-drift: Change oos-pipeline.md step 7 to defer run-statistics to the existing post-checkpoint SKILL.md block; the pipeline should only expose counts/URLs for that later write


### FINDING_2: Duplicate /issue URLs are omitted from OOS disposition evidence
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed sentinel parsing records `ISSUE_<i>_URL` but not `/issue` duplicate-success fields such as `ISSUE_<i>_DUPLICATE_OF_URL`, so all-deduplicated OOS batches can succeed while leaving no URL evidence for recovery or disposition gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Parse ISSUE_<i>_DUPLICATE_OF_URL alongside ISSUE_<i>_URL and include those URLs in oos-issues-created.md and recovered tallies.
  - From Codex-Innovation: Update oos-pipeline.md Step 4/5 to parse ISSUE_<i>_DUPLICATE_OF_URL and ISSUE_<i>_DUPLICATE_OF_NUMBER as disposition URLs/numbers, matching the design helper precedent in skills/design/scripts/file-design-oos.sh:359-366
  - From Codex-dyn-contract-drift: Have oos-pipeline.md record both ISSUE_i_URL and ISSUE_i_DUPLICATE_OF_URL as disposition URLs in oos-issues-created.md; keep the table/tally wording neutral to created-or-deduplicated URLs


### FINDING_3: Design accepted-OOS source resolution is incomplete
- **Reviewer(s)**: Codex-Edge, Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The proposed pipeline only reads `$IMPLEMENT_TMPDIR/oos-accepted-design.md`, but existing contracts also resolve accepted design OOS from `$DESIGN_TMPDIR` and `$IMPLEMENT_TMPDIR/design-export`, causing filing to be skipped while the checkpoint still sees unresolved OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Revise oos-pipeline.md Step 1 to resolve the design accepted-OOS path the same way as the checkpoint: explicit design tmpdir / DESIGN_TMPDIR, then $IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md, then $IMPLEMENT_TMPDIR/oos-accepted-design.md
  - From Codex-dyn-contract-drift: Add the same design OOS resolution order to oos-pipeline.md: DESIGN_TMPDIR, then implement design-export, then implement-local fallback


### FINDING_4: Filed-URL-only early exit may leave required checkpoint input absent
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: If all accepted design OOS blocks already have `- **Filed URL**:`, the proposed pipeline filters them out and exits as if there were no OOS, but the checkpoint may still require an `oos-issues.ndjson` input and fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Revise Step 2 to distinguish true no-input from all-already-filed input; ensure the oos-issues batch/ndjson exists before returning to the checkpoint, or otherwise document the required existing ndjson on that branch
  - From Codex-Pragmatic: Document the filed-design-only path explicitly: either ensure an `oos-issues.ndjson` checkpoint input exists before returning, or update the checkpoint input contract to exclude Filed-URL design blocks / include the design sentinel; add a harness pin for that case


### FINDING_5: Partial /issue failures may still write a success sentinel
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The planned sentinel write does not say to suppress `oos-issues-created.md` when `/issue` exits non-zero or reports `ISSUES_FAILED>0`, so partial success could make reruns skip failed OOS items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a Step 4/5 branch: if /issue exits non-zero or ISSUES_FAILED>0, do not write $IMPLEMENT_TMPDIR/oos-issues-created.md; log/breadcrumb the partial failure and leave the checkpoint to block until missing dispositions are resolved


### FINDING_6: Guard only proves one SKILL.md load directive occurrence
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-guard-robustness
- **Severity**: important
- **Concern**: The planned structure test only checks that `oos-pipeline.md` appears once, but the plan requires mandatory loading at two Step 8+ OOS consumption points, so one runtime path could remain unwired while CI passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a fixed-string assertion that the exact mandatory directive occurs twice, or add two fixed-string checks covering the Exit 0 and OOS checkpoint wording without awk section extraction
  - From Codex-dyn-guard-robustness: Add a fixed-string count for the full mandatory directive phrase plus oos-pipeline.md path and require at least two occurrences


### FINDING_7: repo_unavailable carve-out may drop required audit row
- **Reviewer(s)**: Codex-dyn-contract-drift
- **Severity**: important
- **Concern**: The plan says `repo_unavailable` skips larch-log Accepted-OOS writes, conflicting with the current documented behavior that records `Skipped — repo unavailable` in the `oos-issues` batch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-contract-drift: Split the carve-out: forked_target skips accepted OOS log updates; repo_unavailable skips /issue but still writes the documented oos-issues Skipped — repo unavailable record


### FINDING_8: Sentinel guard does not pin required sentinel format
- **Reviewer(s)**: Codex-dyn-guard-robustness
- **Severity**: important
- **Concern**: The planned sentinel guard only checks for a heading, so a gutted `oos-pipeline.md` could pass while dropping table headers, filed tally, or URL-token shape needed by recovery and loose URL counting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-guard-robustness: Keep the heading grep, and add fixed-string greps for `| OOS title | Issue | URL |`, `- **Filed**: <N>`, and the `issues/<n>` URL-token shape


### FINDING_9: Helper assertions do not prove pipeline invocation wiring
- **Reviewer(s)**: Codex-dyn-guard-robustness
- **Severity**: latent
- **Concern**: Planned helper assertions can pass on helper-name mentions alone, without proving that the cap pre-pass or file-conflict dependency helper are actually wired into the pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-guard-robustness: Add minimal fixed-string greps for invocation fragments such as `oos-issue-cap.sh --input-file`, `oos-file-conflict-deps.sh --input-file`, and `--output "$IMPLEMENT_TMPDIR/oos-intra-batch-deps.tsv"`

