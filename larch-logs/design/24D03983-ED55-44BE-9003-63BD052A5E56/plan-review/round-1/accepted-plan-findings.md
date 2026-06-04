### FINDING_1: Stale bash Step 8+ prose can override the Python-default selector
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The selector flip can still be contradicted by nearby Step 8+ prose, the bash-only invoke block, and bash exit routing. With `LARCH_SHIP_PR_IMPL` unset, an orchestrator may follow the stale general contract or copy the fenced bash block and invoke `scripts/ship-pr.sh` instead of the default Python driver and JSON routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update only that delegation sentence to make the selector authoritative, e.g. say Steps 8-14 are delegated by the driver selector below; default python uses python/ship.py, while LARCH_SHIP_PR_IMPL=bash uses the legacy ship-pr.sh contract below. Leave the bash invocation block byte-stable.
  - From Cursor-Innovation: Add one sentence immediately before `Invoke:` (and/or after the selector): unless `LARCH_SHIP_PR_IMPL=bash`, use the Python foreground invocation and JSON exit routing from the selector; the fenced block documents the bash opt-in contract only


### FINDING_2: Python selector drops `--no-logs-commit`
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Python-default selector keeps an argv list that omits `--no-logs-commit`. After the flip, `/implement --no-logs-commit` with unset `LARCH_SHIP_PR_IMPL` will not pass the user flag into `python/ship.py`, so `RunContext.no_logs_commit` can remain false and log commits or refreshes can still run despite the explicit opt-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge, Codex-Innovation, Codex-Pragmatic: Add --no-logs-commit "$no_logs_commit" to the Python invocation/selector argv list instead of preserving that omission byte-for-byte


### FINDING_3: Empty-string selector case is missing from validation
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The plan requires both unset and empty `LARCH_SHIP_PR_IMPL` to select Python, but validation only mentions unset and bash opt-in, leaving the empty-string acceptance case untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the empty-string case to the manual confirmation or selector-default pin: LARCH_SHIP_PR_IMPL= routes Step 8+ to python/ship.py


### FINDING_4: Stale Phase 7/bash-default references can survive the planned grep checks
- **Reviewer(s)**: Cursor-dyn-stale-ref-sweep, Codex-dyn-stale-ref-sweep
- **Severity**: important
- **Concern**: The planned verification only greps narrow bash-default phrases and can miss live stale references that describe Python PR/merge/logging as dev/CI-only, soak-only, or not wired into `/implement`. That includes documentation and source comments such as `AGENTS.md`, `python/README.md`, `docs/configuration-and-permissions.md`, and `python/config.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stale-ref-sweep: Expand the Testing strategy / Failure modes verification to one repo-wide sweep, e.g. `rg -n 'LARCH_SHIP_PR_IMPL|during the soak|still uses bash|dev/CI-only until Phase 7|not wired into the live' --glob '!larch-logs/**'` (or document the same patterns in the implement step), not only the two bash-default strings.
  - From Codex-dyn-stale-ref-sweep: Add python/config.py to the light-touch update and make line 131 live/default-neutral; expand the final manual sweep to include Phase 7, during the soak, LARCH_SHIP_PR_IMPL=python cutover, still uses bash, and Default is bash, excluding historical larch-logs if they are intentionally immutable


### FINDING_5: Default flip lacks an upgrade-facing/operator notice
- **Reviewer(s)**: Cursor-dyn-rollout-contract, Codex-dyn-rollout-contract
- **Severity**: important
- **Concern**: The plan does not add a consumer-facing release, changelog, upgrade, or operator notice for the silent Step 8+ default flip. Users who never set `LARCH_SHIP_PR_IMPL` can upgrade and have the next `/implement` switch to Python without seeing that bash remains the escape hatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-rollout-contract: Add a minimal operator notice path to the plan (release-note bullet for the shipping version and/or a short docs/installation-and-setup.md or upgrade-larch note that the default flipped and bash is the escape hatch)
  - From Codex-dyn-rollout-contract: Add one short Upgrade-section note that /implement Step 8+ now defaults to python and LARCH_SHIP_PR_IMPL=bash restores the legacy scripts/ship-pr.sh path


