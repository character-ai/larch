### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_publish.py:402-443
- **Concern**: The scrub-fatal gate keys only on `publish.returncode != 0` with no `RECOVERY_BRANCH`, but `log_publish_main` already exits **1** for argv/validation faults (`design_log_publish_flow.py:365-377,395`) with no stdout KVs. Scenario: After the tail fix, a bad `--repo` (or other early `return 1`) from `design log-publish` is indistinguishable from a scrub abort and `design publish` returns **5** / Step 5c `failed-publish-tail`, even though no scrub ran
- **Proposed resolution**: Make subprocess exit codes scrub-specific: reserve non-zero for `SecretScrubFailure` only; change existing `return 1` paths in `log_publish_main` to emit `PUBLISH_OK=false` and return **0**, or emit an explicit scrub-fatal KV (e.g. `SCRUB_FATAL=true`) and gate `design_publish` on that instead of bare returncode; add a regression test for invalid `--repo` / argv failure not mapping to rc **5**



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:46
- **Concern**: [SCOPE-REDUCTION] Item 1 doc work largely duplicates existing NEVER #8 carve-out text. Scenario: NEVER #8 already states implement has no terminal sentinels, forbids design sentinel probes, and calls foreground probing a `/design`-only carve-out; adding three more bullets risks redundant NEVER growth without new operator signal
- **Proposed resolution**: Add at most one short intentional-asymmetry clause (not a contradiction) if the anti-polling harness still needs a new pinned literal; do not restate the existing carve-out sentences



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_log_publish_flow.py:311-313
- **Concern**: Item 3 describes classifying run-log commit scrub faults separately but does not require doing so before the existing blanket recoverable return. Scenario: A `run-log commit` scrub failure today returns exit 1 with stderr like `secret survived scrubbing in …`; the current `if commit.returncode != 0 or not head_sha or head_sha == base_sha` block still maps that to recoverable `(False, "", "", "", "0")` and `log_publish_main` exits 0, so Step 5c can treat publish as success while logs are uncommitted or partially scrubbed
- **Proposed resolution**: Add an explicit implementation step: immediately after the commit subprocess, detect scrub faults in `commit.stderr`/`commit.stdout` (for example `secret survived scrubbing`) and raise `SecretScrubFailure` before the line 311-313 recoverable return; add a regression test where scrub stderr is present and assert the recoverable tuple is not returned



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_publish.py:420-443
- **Concern**: The new `design publish` branching covers scrub-fatal (`returncode != 0` without `RECOVERY_BRANCH`) and recoverable push/PR misses (`returncode == 0` with `RECOVERY_BRANCH`), but not the third live path: `returncode == 0`, `PUBLISH_OK=false`, and no `RECOVERY_BRANCH`. Scenario: Worktree/init failures and other non-scrub publish misses in `design_log_publish_flow.py` already exit 0 with `PUBLISH_OK=false` and no recovery branch; an implementer following only steps 1-4 could mis-route these cases or drop `PUBLISH_OK=false` from the result env while still returning 0
- **Proposed resolution**: Add an explicit recoverable branch: when `publish.returncode == 0`, parsed `PUBLISH_OK=false`, and `RECOVERY_BRANCH` is absent, preserve today's exit 0 behavior (no rotation warning unless publish actually succeeded with `SECRET_SCRUB_VIOLATIONS > 0`) and regression-test a worktree/init failure fixture



