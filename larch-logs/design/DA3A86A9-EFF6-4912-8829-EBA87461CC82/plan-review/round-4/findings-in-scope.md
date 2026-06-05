### FINDING_1: approval-gates.md retarget required but missing from file inventory
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-cross-doc-drift
- **Severity**: important
- **Concern**: The plan requires boundary-qualified Step 3b→Step 4 routing updates and adds harness checks against `skills/design/references/approval-gates.md`, but that file is not listed under Files to modify/create. Implementers may update only `SKILL.md` and tests, leaving stale normative Gate B/C prose and causing CI guard/pin failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add skills/design/references/approval-gates.md under Files to modify with the same boundary-qualified Step 3b→Step 4 wording used in SKILL.md
  - From Cursor-Edge: Add skills/design/references/approval-gates.md to Files to modify with the same boundary-qualified retarget applied to cap-breadcrumb, passive-summary auto-continue, zero-findings, Gate C When, and bypass routing lines (mirror the SKILL.md edits the plan already mandates)
  - From Cursor-Innovation: Add ### UPDATED: skills/design/references/approval-gates.md: retarget every Step 3b→Step 4 (and arrow/comma) routing line to name the Step 3b completion boundary before Step 4, matching the SKILL.md retarget pattern
  - From Cursor-Pragmatic: Add `### UPDATED: skills/design/references/approval-gates.md` with the same boundary-qualified retarget applied to every Step 3b→Step 4 chain (cap breadcrumb, zero-findings, passive-summary, shared post-apply item 9, Gate C When); update harness positive pins at `scripts/test-design-structure.sh:371-379` and `:1568` to match
  - From Cursor-Requirements: Add `### UPDATED: skills/design/references/approval-gates.md` retargeting cap breadcrumb, passive-summary auto-continue, zero-findings chain, and Gate C When bypass lines to name the Step 3b completion boundary before Step 4
  - From Cursor-dyn-cross-doc-drift: Add ### UPDATED: skills/design/references/approval-gates.md and rewrite those routing sequences to run the Step 3b completion boundary (FINALIZE + step-3b) before Step 4, matching SKILL.md

### FINDING_2: run-step3-review.sh cap breadcrumb retarget missing from file inventory
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-routing-completeness
- **Severity**: important
- **Concern**: The plan adds a harness assertion covering `skills/design/scripts/run-step3-review.sh`, but does not list the script for modification. Its cap-reached emit text may still imply direct Step 3b→Step 4 routing without the completion boundary, causing CI failure or stale operator-facing guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add skills/design/scripts/run-step3-review.sh to Files to modify (retarget the cap breadcrumb) or state explicitly that script stdout is exempt from the routing guard
  - From Cursor-dyn-routing-completeness: Add ### UPDATED: skills/design/scripts/run-step3-review.sh to retarget line 167 to name the Step 3b completion boundary before Step 4 (mirror approval-gates.md), or document an explicit harness exclusion if script text is intentionally out of band.

### FINDING_3: New Step 3b completion fence may duplicate existing entry fence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan adds a new Step 3b completion bash fence instead of folding FINALIZE into the existing Step 3b entry fence that already executes on every Step 3b path. This may add redundant harness and pause-check surface when FINALIZE only needs to run before Step 4 reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Fold ACTION=FINALIZE (set +e + exit on failure) into the existing Step 3b entry fence; keep a single end-of-3b step-3b sentinel write (prose or minimal bash) and retarget exit paths to enter Step 3b (running FINALIZE at entry) before Step 4

### FINDING_4: SIMPLE entry-fence pins may accidentally require SIMPLE sentinels on HARD paths
- **Reviewer(s)**: Cursor-dyn-harness-sync
- **Severity**: important
- **Concern**: The planned harness pins for the first Step 2a bash fence may assert SIMPLE sentinel/step substrings unconditionally. HARD runs keep that fence but should not write SIMPLE sentinels, so broad grep/awk checks could either fail CI or force incorrect HARD behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-sync: Scope the positive pin to a SIMPLE guard (e.g. `design_classification == SIMPLE` / `read-design-classification.sh` branch) or assert sentinels only in the `### SIMPLE branch` prose plus a negative `bash` check there, not bare literals in the shared entry fence
