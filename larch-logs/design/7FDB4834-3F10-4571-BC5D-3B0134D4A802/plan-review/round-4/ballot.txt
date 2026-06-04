### FINDING_1: Run-statistics guards are overbroad or insufficiently exact
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-guard-efficacy, Codex-dyn-guard-efficacy
- **Severity**: important
- **Concern**: The planned structure assertions around NEVER #5 and post-checkpoint `run-statistics` both conflict with the intended ownership sentence and may still fail to prove that sentinel recovery does not write run statistics before the OOS checkpoint succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Scope the guard: e.g. assert `batch run-statistics` is absent only between `idempotent-rerun` and the fork carve-out, or pin a positive sentinel-only phrase such as `append … --batch oos-issues` without a paired `write … --batch run-statistics` on that branch.
  - From Cursor-dyn-guard-efficacy: Pin the exact narrowed NEVER #5 How to apply sentence as one positive fixed string; treat post-checkpoint ownership pins as necessary not sufficient
  - From Codex-dyn-guard-efficacy: Replace proof wording with exact fixed-string pins in the runtime reference, plus one negative fixed-string check for the old NEVER #5 sentinel-recovery run-statistics fragment.

### FINDING_2: Manifest-only OOS observations do not trigger the OOS pipeline
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed manifest harvest occurs inside the OOS pipeline, but the runtime predicates enter that pipeline only when accepted-OOS markdown files already exist. Manifest-only `oos_observations` can therefore be skipped entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the manifest harvest before the ship-pr/python OOS trigger decision or update both trigger paths to materialize/check manifest.oos_observations using the same source-resolution contract before deciding no OOS is pending
  - From Codex-Pragmatic: Materialize or detect MANIFEST_PATH oos_observations before the existing OOS_PENDING or Python OOS gate decision, or write them to oos-accepted-main-agent.md during the dispatcher so the existing file-based trigger fires

### FINDING_3: Python oos-filing dispatch covers only `/issue`, not the full OOS checkpoint sequence
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Python `oos-filing` path is described as invoking only the `/issue` pipeline, which can skip manifest harvest, grouping/cap/dependency pre-passes, `oos-issues` writes, checkpoint handoff, and post-checkpoint statistics sequencing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: In the Python driver selector (and matching plan bullet), require the full Step 9a.1 procedure from `oos-pipeline.md` (steps 1–7), not “`/issue` pipeline” alone; state that `oos-filing` must mirror the **OOS checkpoint** sequencing (pipeline → checkpoint → post-checkpoint `run-statistics` when checkpoint exits 0) before reinvoking `python3 …/ship.py`

### FINDING_4: Manifest harvest conflicts with the manifest parsing contract
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The proposed OOS pipeline would have prompt-side orchestration parse `MANIFEST_PATH`, while the manifest schema says the orchestrator handles only the path and does not parse manifest JSON in-prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: For this minimum-change PR, drop the manifest harvest and its structure pin from oos-pipeline; if harvest is materially required, move it into an existing helper or dispatcher path and update codex-manifest-schema.md in the same change

### FINDING_5: Empty dependency TSV is conflated with helper failure
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Step 3.5 treats exit-0 empty TSV output like non-zero helper failure, even though a successful no-conflict pre-pass should be a normal path that simply omits `--intra-batch-deps-file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split step 3.5: exit 0 + empty TSV → omit --intra-batch-deps-file (normal); non-zero → warning + Tool Failures + omit flag. Keep step 4 gate unchanged.

### FINDING_6: OOS combine step lacks the canonical grouping rules
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Step 3.4 names the combine cascade but does not require restoring the executable Rule A/B, criteria 1–6, or worksheet contract from the deleted anchor, leaving grouping behavior under-specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In `### NEW: skills/implement/references/oos-pipeline.md` step 3.4, explicitly require reconstructing Rule A, Rule B, criteria 1-6, and the grouping-worksheet format from the git skeleton (gate-aligned security predicate, no anchor/PR-body surfaces), or cross-reference a single in-repo section that already contains that full text; add at least one fixed-string guard for a distinctive Rule A or worksheet anchor if hollow 3.4 prose is a concern.

### FINDING_7: Load-directive count is inconsistent
- **Reviewer(s)**: Cursor-dyn-reference-traceability
- **Severity**: important
- **Concern**: The plan’s failure-mode text says there are two load directives, while the testing strategy requires at least three, risking under-wiring of the Python `oos-filing` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-reference-traceability: Align Failure modes and Approach guard text with assertion 2: three mandatory load directives (Exit 0 OOS branch, OOS checkpoint block, Python needs_user_reason=oos-filing)

### FINDING_8: Rejected sub-block cites the wrong source contract
- **Reviewer(s)**: Codex-dyn-reference-traceability
- **Severity**: latent
- **Concern**: The plan cites `scripts/larch-log-batches.md` for Rejected sub-block behavior, but that file documents compact NDJSON shape rather than the rejected-marker contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-reference-traceability: In the proposed oos-pipeline.md step 6 text, cite SKILL.md OOS carve-outs / Terminal disposition invariant and oos-disposition-gate.md Counting rules for the Rejected sub-block; keep scripts/larch-log-batches.md only for the compact NDJSON record schema.

### FINDING_9: Partial-failure URL suppression guard is too weak
- **Reviewer(s)**: Cursor-dyn-guard-efficacy, Codex-dyn-guard-efficacy
- **Severity**: important
- **Concern**: Assertion 8b relies on generic prose greps and may not prevent partial-batch issue URLs from being appended to `oos-issues.ndjson`, which can falsely satisfy the disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-efficacy: Add a fixed-string pin on the combined suppression fragment (e.g. do not append accepted disposition URL rows plus oos-issues NDJSON) or accept this as doc-only and drop 8b efficacy claims
  - From Codex-dyn-guard-efficacy: Replace proof wording with exact fixed-string pins in the runtime reference, plus one negative fixed-string check for the old NEVER #5 sentinel-recovery run-statistics fragment.

### FINDING_10: Design-source resolution order lacks a structure assertion
- **Reviewer(s)**: Cursor-dyn-guard-efficacy, Codex-dyn-guard-efficacy
- **Severity**: important
- **Concern**: The plan lists checkpoint-aligned design-source ordering as a failure mode, but no assertion pins the required `DESIGN_TMPDIR` → design export → tmpdir resolution order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-efficacy: Add minimal fixed-string pins for the three-path design-source order, already-filed URL evidence branch, and treat duplicate-of URLs as valid disposition URLs
  - From Codex-dyn-guard-efficacy: Add minimal fixed-string pins for the three design-source paths and the all-already-filed materialize checkpoint-visible evidence sentence.

### FINDING_11: Already-filed URL evidence lacks a structure assertion
- **Reviewer(s)**: Cursor-dyn-guard-efficacy, Codex-dyn-guard-efficacy
- **Severity**: important
- **Concern**: The all-already-filed branch can be omitted while planned assertions still pass, leaving existing Filed URL evidence unavailable to the checkpoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-efficacy: Add minimal fixed-string pins for the three-path design-source order, already-filed URL evidence branch, and treat duplicate-of URLs as valid disposition URLs
  - From Codex-dyn-guard-efficacy: Add minimal fixed-string pins for the three design-source paths and the all-already-filed materialize checkpoint-visible evidence sentence.

### FINDING_12: Duplicate-of URLs are not pinned as valid disposition evidence
- **Reviewer(s)**: Cursor-dyn-guard-efficacy, Codex-dyn-guard-efficacy
- **Severity**: important
- **Concern**: The duplicate-disposition assertion pins output variable names but not their operative use as checkpoint-visible disposition URLs, so all-deduplicated batches can pass tests while lacking valid evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-efficacy: Add minimal fixed-string pins for the three-path design-source order, already-filed URL evidence branch, and treat duplicate-of URLs as valid disposition URLs
  - From Codex-dyn-guard-efficacy: Add one fixed-string assertion for the operative contract, such as Treat both created URLs and duplicate-of URLs as valid disposition URLs, scoped to skills/implement/references/oos-pipeline.md.

### FINDING_13: Security focus-area predicate assertion is too loose
- **Reviewer(s)**: Cursor-dyn-guard-efficacy
- **Severity**: important
- **Concern**: Assertion 10 can pass by merely mentioning `- **focus-area**:` without pinning the actual awk/gate predicate: field-line focus area begins with security, excluding Description prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-guard-efficacy: Pin the full predicate fragment (begins with security plus does not mark for Description prose) or a negative pin rejecting bare focus-area=security as the exclusion rule
