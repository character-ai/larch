### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:951-957
- **Concern**: Plan flips the selector sentence but leaves the immediately preceding Step 8+ contract saying Steps 8-14 are mechanically delegated to scripts/ship-pr.sh. Scenario: After the PR, the default path is Python, but the same paragraph still states the default delegation is ship-pr.sh, so an orchestrator can follow the stale general contract and invoke the bash driver with LARCH_SHIP_PR_IMPL unset
- **Proposed resolution**: Update only that delegation sentence to make the selector authoritative, e.g. say Steps 8-14 are delegated by the driver selector below; default python uses python/ship.py, while LARCH_SHIP_PR_IMPL=bash uses the legacy ship-pr.sh contract below. Leave the bash invocation block byte-stable.

### FINDING_2:
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955; python/ship.py:523-561
- **Concern**: Python-default selector preserves an argv list that omits --no-logs-commit. Scenario: After the flip, /implement --no-logs-commit with unset LARCH_SHIP_PR_IMPL no longer passes the user flag into python/ship.py, so RunContext.no_logs_commit stays false unless an env var happens to be set and log commits/refreshes can run despite the explicit opt-out
- **Proposed resolution**: Add --no-logs-commit "$no_logs_commit" to the Python invocation/selector argv list instead of preserving that omission byte-for-byte

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:989-1040
- **Concern**: Default flip rewrites only the selector (line 955) but leaves the fenced Invoke block and post-return exit matrix bash-only (`ship-pr.sh`, `ship-pr-state.sh`). Scenario: With `LARCH_SHIP_PR_IMPL` unset, agents often copy the Invoke fenced block and bash exit routing instead of `python3 …/ship.py` plus JSON routing in the selector—CI grep pins selector tokens only, so this mis-route can pass `test-implement-structure`
- **Proposed resolution**: Add one sentence immediately before `Invoke:` (and/or after the selector): unless `LARCH_SHIP_PR_IMPL=bash`, use the Python foreground invocation and JSON exit routing from the selector; the fenced block documents the bash opt-in contract only

### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47,55-58
- **Concern**: Testing omits the stated empty-selector acceptance case. Scenario: The plan requires both unset and empty LARCH_SHIP_PR_IMPL to select Python, but validation only mentions unset and bash opt-in
- **Proposed resolution**: Add the empty-string case to the manual confirmation or selector-default pin: LARCH_SHIP_PR_IMPL= routes Step 8+ to python/ship.py

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-stale-ref-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:50-51
- **Concern**: Post-edit verification only greps `Default is \`bash\`` and `still uses bash`, but several live stale phrases use different wording.. Scenario: An implementer can pass the plan’s grep check while `docs/configuration-and-permissions.md:191` still says `Set LARCH_SHIP_PR_IMPL=python` / `during the soak`, `AGENTS.md:9` still says `dev/CI-only until Phase 7`, and `python/README.md:15-20` still says `dev/CI-only until Phase 7` / `not wired into the live \`/implement\` path until Phase 7`.
- **Proposed resolution**: Expand the Testing strategy / Failure modes verification to one repo-wide sweep, e.g. `rg -n 'LARCH_SHIP_PR_IMPL|during the soak|still uses bash|dev/CI-only until Phase 7|not wired into the live' --glob '!larch-logs/**'` (or document the same patterns in the implement step), not only the two bash-default strings.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-stale-ref-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/config.py:131
- **Concern**: Plan omits a source comment that still says PR/merge/logging is dev/CI until Phase 7, and the stated grep mitigation would miss it. Scenario: After the flip, python/ship.py is the default Step 8+ driver, but config.py would still frame these live PR/merge/logging constants as pre-cutover; grep for Default is bash or still uses bash does not catch dev/CI until Phase 7
- **Proposed resolution**: Add python/config.py to the light-touch update and make line 131 live/default-neutral; expand the final manual sweep to include Phase 7, during the soak, LARCH_SHIP_PR_IMPL=python cutover, still uses bash, and Default is bash, excluding historical larch-logs if they are intentionally immutable

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-rollout-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:7-37
- **Concern**: No consumer-facing release or upgrade warning in the file list. Scenario: Users who never set LARCH_SHIP_PR_IMPL get python Step 8+ on the next plugin install with no changelog, release-note, or upgrade-larch callout
- **Proposed resolution**: Add a minimal operator notice path to the plan (release-note bullet for the shipping version and/or a short docs/installation-and-setup.md or upgrade-larch note that the default flipped and bash is the escape hatch)

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-rollout-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:30-44
- **Concern**: Plan does not add an upgrade-facing warning for the silent Step 8+ default flip. Scenario: Users who never set LARCH_SHIP_PR_IMPL can run /upgrade-larch, restart, and have the next /implement Step 8+ switch to python without seeing the bash escape hatch
- **Proposed resolution**: Add one short Upgrade-section note that /implement Step 8+ now defaults to python and LARCH_SHIP_PR_IMPL=bash restores the legacy scripts/ship-pr.sh path

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-rollout-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/configuration-and-permissions.md:189-191; <TMPDIR>/plan.txt:20-21; <TMPDIR>/plan.txt:55-58
- **Concern**: The planned LARCH_SHIP_PR_IMPL docs and acceptance checks advertise bash as an opt-in path but not as recovery for python-path regressions despite the open soak blockers. Scenario: An operator hits a failed python-path Step 8+ run related to #3446/#3404/#3405/#3449 and the accepted plan leaves diagnosis/recovery entirely implicit
- **Proposed resolution**: Add a single recovery sentence to the planned config doc edit: if Step 8+ regresses on the python path, rerun with LARCH_SHIP_PR_IMPL=bash; include that guidance in the manual acceptance check.
