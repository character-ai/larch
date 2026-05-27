# Review Round 2

- Mode: `diff`
- 7 accepted, 7 rejected (3 exonerated)

## Accepted Findings

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


### FINDING_15: Save contract documentation conflicts with publish no-op behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.md` says no-op pause fails closed, but publish can succeed without a new commit when default already has a manifest. That documentation mismatch matters for the recovery-branch-ahead case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Defensive pause prelude can target the wrong repo
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Defensive pause handling in `skills/design/SKILL.md` does not pass a stable `--repo` from session state, unlike Step 0b. In fork or multi-repo contexts, a mid-run pause can save/read/write markers against the wrong GitHub repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Resume can skip lifecycle title validation and DESIGNING rename
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A successful pause load skips title eligibility filtering and Step 5.5 `[DESIGNING]` rename. If the pause happened before rename, resume can continue design work on an ineligible or still-`[IMPLEMENTING]` issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


