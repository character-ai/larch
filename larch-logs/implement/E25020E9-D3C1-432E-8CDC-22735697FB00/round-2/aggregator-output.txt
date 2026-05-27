### FINDING_1: Loader deletes pause marker before restored artifacts are installed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Loader deletes the issue pause marker before copying staged snapshot artifacts into `DESIGN_TMPDIR`. If marker deletion succeeds and artifact install fails, resume state is lost even though recovery data may still exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Pause scripts use weaker local repo resolution
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `design-pause-save.sh` duplicates repo resolution logic without the `github-remote-repo.sh` fallback, so save/load/marker writes can omit or misresolve `--repo` when `gh repo view` fails but git remote resolution would work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Defensive pause prelude can target the wrong repo
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Defensive pause handling in `skills/design/SKILL.md` does not pass a stable `--repo` from session state, unlike Step 0b. In fork or multi-repo contexts, a mid-run pause can save/read/write markers against the wrong GitHub repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Duplicate completed-sentinel prose can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Per-step `.completed` sentinel instructions are duplicated across multiple step sections, increasing the chance future edits update one copy but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Design-pause marker parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Marker-stripping/parsing logic for design-pause blocks is duplicated in save and load scripts, so grammar changes in the writer can silently desynchronize save/load behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Pause skill writes unnecessary sentinel before synchronous save
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `/larch:pause` creates `.pause-requested` before running synchronous `design-pause-save.sh`. If the save fails or the process is interrupted, the stale sentinel can cause a later boundary to republish or re-enter defer behavior unexpectedly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] REPO is not persisted in design session env
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write-design-current-env.sh` does not write `REPO` into `source-env.sh`, forcing every Bash boundary to re-resolve the repository and preventing pause/resume from sourcing a stable repo value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Resume can skip lifecycle title validation and DESIGNING rename
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A successful pause load skips title eligibility filtering and Step 5.5 `[DESIGNING]` rename. If the pause happened before rename, resume can continue design work on an ineligible or still-`[IMPLEMENTING]` issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Save trusts named-block-write exit status without checking write result
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` can report `PAUSE_OK=true` based on `named-block-write` exit status without verifying stdout fields such as `WRITTEN=true` or `FAILED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Missing agent-lint excludes for new helper and harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New scripts/docs are missing from the `agent-lint` dead-script exclude list, so `make lint` can fail G004 for `scripts/named-block-write.sh` and `skills/design/scripts/test-design-pause-resume.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Loader does not bind snapshot contents to the requested issue
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `design-pause-load.sh` validates marker `ISSUE_NUMBER`/`REPO` but not that the fetched snapshot’s pause state or manifest belongs to the same issue. A marker can point to another run’s `RUN_ID` and restore foreign artifacts onto the current issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Empty-porcelain publish can ignore newer recovery branch state
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-log-publish.sh` can return `PUBLISH_OK=true` on empty porcelain when default already has a manifest, even if a newer pause snapshot exists only on the recovery branch. Resume may then restore stale default-branch state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Defensive prelude continues after failed pause save
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Bash prelude `exec`s `design-pause-save.sh`, which exits 0 even when `PAUSE_OK=false`. A failed publish or marker write can truncate the intended step body while `/design` continues as though the boundary succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Restore copy overlays instead of replacing tmpdir contents
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cp -R` merges restored snapshot files into `DESIGN_TMPDIR`, leaving pre-existing files that are absent from the snapshot and potentially confusing later resume or sentinel logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Save contract documentation conflicts with publish no-op behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.md` says no-op pause fails closed, but publish can succeed without a new commit when default already has a manifest. That documentation mismatch matters for the recovery-branch-ahead case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
