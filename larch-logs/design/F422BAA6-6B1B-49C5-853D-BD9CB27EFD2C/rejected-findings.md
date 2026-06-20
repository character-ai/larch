### [Plan Review] FINDING_1

### FINDING_1: Scrub-fatal gate conflates non-scrub exit 1 with scrub abort
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The scrub-fatal gate keys only on `publish.returncode != 0` with no `RECOVERY_BRANCH`, but `log_publish_main` already exits **1** for argv/validation faults (`design_log_publish_flow.py:365-377,395`) with no stdout KVs. After the tail fix, a bad `--repo` (or other early `return 1`) from `design log-publish` is indistinguishable from a scrub abort and `design publish` returns **5** / Step 5c `failed-publish-tail`, even though no scrub ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make subprocess exit codes scrub-specific: reserve non-zero for `SecretScrubFailure` only; change existing `return 1` paths in `log_publish_main` to emit `PUBLISH_OK=false` and return **0**, or emit an explicit scrub-fatal KV (e.g. `SCRUB_FATAL=true`) and gate `design_publish` on that instead of bare returncode; add a regression test for invalid `--repo` / argv failure not mapping to rc **5**


### [Plan Review] FINDING_2

### FINDING_2: Run-log commit scrub failure still maps to recoverable success
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Item 3 describes classifying run-log commit scrub faults separately but does not require doing so before the existing blanket recoverable return. A `run-log commit` scrub failure today returns exit 1 with stderr like `secret survived scrubbing in …`; the current `if commit.returncode != 0 or not head_sha or head_sha == base_sha` block still maps that to recoverable `(False, "", "", "", "0")` and `log_publish_main` exits 0, so Step 5c can treat publish as success while logs are uncommitted or partially scrubbed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit implementation step: immediately after the commit subprocess, detect scrub faults in `commit.stderr`/`commit.stdout` (for example `secret survived scrubbing`) and raise `SecretScrubFailure` before the line 311-313 recoverable return; add a regression test where scrub stderr is present and assert the recoverable tuple is not returned


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:46
- **Concern**: [SCOPE-REDUCTION] Item 1 doc work largely duplicates existing NEVER #8 carve-out text. Scenario: NEVER #8 already states implement has no terminal sentinels, forbids design sentinel probes, and calls foreground probing a `/design`-only carve-out; adding three more bullets risks redundant NEVER growth without new operator signal
- **Proposed resolution**: Add at most one short intentional-asymmetry clause (not a contradiction) if the anti-polling harness still needs a new pinned literal; do not restate the existing carve-out sentences


