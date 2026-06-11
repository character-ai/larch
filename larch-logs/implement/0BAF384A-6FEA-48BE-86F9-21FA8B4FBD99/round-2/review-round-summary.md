# Review Round 2

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Closed-window cutoff uses UTC date instead of local date
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `list_issues` uses a UTC calendar date for the closed-window cutoff, which can exclude issues still inside the bash local-date window for US evening operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Missing gh can crash issue helpers
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Issue helpers let `FileNotFoundError` escape when `gh` cannot be spawned, bypassing documented failure output for list, fetch, and create paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Missing gh can crash upgrade release lookup
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_get_stable_releases` calls `gh` unconditionally, removing the old no-gh fallback and crashing before status keys or recovery handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Worktree scan no longer skips prunable records
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Python fork setup worktree scan includes prunable git worktree records that bash skipped, so stale metadata can block setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Marketplace refresh can traceback after uninstall
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_refresh_marketplace` can raise from `shutil.rmtree` after uninstalling the plugin, leaving no installed plugin and no recovery diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Parse-input shell harness cases were not ported
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-parse-input.sh` coverage for issues #129, #131, and #132 was not ported to pytest, so batch item-boundary parsing regressions may ship without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Issue publication redactor rewrites non-secret paths
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `issue create-one` uses a redactor that rewrites tmpdir and operator repo paths, violating `scripts/redact-secrets.sh` parity and corrupting issue content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Empty required fields can trigger duplicate issue creation
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A valid JSON create response with empty required fields falls through to fallback creation, which can create a second issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Interactive mirror-sync confirmation was removed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Python fork setup path always requires `--mirror-confirmed`, removing the bash TTY prompt for diverged fork main branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


