# Review Round 1

- Mode: `diff`
- 2 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_2: `cursor_preread_service_token` logs keychain failure but launch proceeds without `CURSOR_API_KEY`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: important
- **Concern**: `cursor_preread_service_token` logs `-w` read failure but does not abort; `_review_launch_cursor` still launches Cursor afterward. Preflight may pass, then preread leaves `CURSOR_API_KEY` unset; Cursor launches unauthenticated, retries, and may return a canned `no_issues_found` before postprocess downgrades. Work item 2 requested abort-at-launch, not post-hoc mitigation alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return failure from preread or reuse preflight token and short-circuit launch like the preflight-fail path
  - From codex-specialist-correctness-output.txt: Make preread return a failure or raise, and short-circuit the Cursor launchers when the token read fails.
  - From codex-specialist-edge-cases-output.txt: return a failure flag or raise on preread failure and short-circuit the launch, or fold preread into preflight and remove the second read
  - From dyn-dyn-cursor-degraded-calibration-output.txt: After `cursor_preread_service_token()`, treat an empty/unset `CURSOR_API_KEY` on Darwin (when no valid env key was already present) as a hard preflight failure: write the preflight bundle, return `verdict.rc`, and do not spawn Cursor.


### FINDING_7: Auth preflight and preread treat security `-w` exit 0 as success without requiring non-empty token
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: important
- **Concern**: Auth preflight and preread treat security `-w` exit 0 as success without requiring a non-empty token. If keychain returns 0 with blank stdout (corrupt entry, whitespace-only secret, or tooling edge case), preflight passes, `CURSOR_API_KEY` stays unset, and launch proceeds credential-less with no diagnostic. That is the same silent-auth-drop class #5518 targeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Require non-empty stripped token after successful -w; fail closed in preread and abort launch when token is missing
  - From dyn-dyn-cursor-degraded-calibration-output.txt: Require a non-empty stripped token from the `-w` read in both functions; on empty stdout with `rc==0`, return `AuthVerdict(ok=False, rc=2)` in preflight and treat preread as `read_failed` with the same abort path as a non-zero exit.


