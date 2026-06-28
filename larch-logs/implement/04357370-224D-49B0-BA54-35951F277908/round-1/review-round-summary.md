# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Refresh re-fingerprints live diff but preserves stale Phase-A assessment text
- **Reviewer(s)**: cursor-specialist-correctness, codex-generalist
- **Severity**: important
- **Concern**: `refresh_staged_assessment_for_current_head()` reuses the staged Phase-A assessment body while rewriting diff fingerprint and `ASSESSED_HEAD_SHA` to match the current HEAD/live diff. After a rebase, CI fix, or other substantive code change between Step 7a staging and Phase-B pin, the retry can succeed with assessment prose that was never evaluated against the current diff (e.g. “no deviations” for diff A pinned against diff B), yielding architecturally misleading PR guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Refresh only when the old and live diffs can be proven assessment-equivalent, or trigger the existing Phase-A assessment path for the current diff before rewriting fingerprint/head metadata; otherwise keep the drop-notice path.


### FINDING_2: `_live_diff` materialization does not catch `OSError` / `FileNotFoundError`
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: `_live_diff` materialization only suppresses `RuntimeError`, not `OSError`/`FileNotFoundError`. A deleted or unreadable `repo_root` can make `subprocess.run(cwd=repo_root)` raise `FileNotFoundError`, crashing the refresh/retry path instead of failing closed into the drop-notice fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Catch OSError together with RuntimeError and return None so refresh fails closed on I/O failure


