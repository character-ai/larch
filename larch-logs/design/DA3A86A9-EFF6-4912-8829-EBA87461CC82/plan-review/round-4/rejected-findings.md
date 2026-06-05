### [Plan Review] FINDING_3

### FINDING_3: New Step 3b completion fence may duplicate existing entry fence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: The plan adds a new Step 3b completion bash fence instead of folding FINALIZE into the existing Step 3b entry fence that already executes on every Step 3b path. This may add redundant harness and pause-check surface when FINALIZE only needs to run before Step 4 reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Fold ACTION=FINALIZE (set +e + exit on failure) into the existing Step 3b entry fence; keep a single end-of-3b step-3b sentinel write (prose or minimal bash) and retarget exit paths to enter Step 3b (running FINALIZE at entry) before Step 4


