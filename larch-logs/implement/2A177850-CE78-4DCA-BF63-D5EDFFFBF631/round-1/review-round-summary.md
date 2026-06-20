# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Recoverable `PUBLISH_OK=false` early return skips secret rotation warning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-scrub-boundary-output.txt
- **Severity**: important
- **Concern**: When `log-publish` scrubs secrets (`SECRET_SCRUB_VIOLATIONS > 0`) and then push or `gh pr create` fails with `PUBLISH_OK=false` and `RECOVERY_BRANCH`, `design_publish` returns 0 at lines 441–443 before the rotation-warning block at 449–457. Operators may exit successfully without being told to rotate exposed credentials, contradicting `SECURITY.md` and existing tests that do not cover `SECRET_SCRUB_VIOLATIONS > 0` on recoverable paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On recoverable publish failures still print the rotation warning when SECRET_SCRUB_VIOLATIONS>0, or split branch-3 push/PR handling from branch-4 non-push handling so only the latter suppresses the warning.
  - From codex-specialist-correctness-output.txt: Split recoverable handling so recovery-branch cases still emit the scrub warning when SECRET_SCRUB_VIOLATIONS is positive.
  - From codex-specialist-edge-cases-output.txt: Emit the existing rotation warning before returning from recoverable PUBLISH_OK=false paths whenever publish.returncode is 0 and SECRET_SCRUB_VIOLATIONS is positive.
  - From dyn-scrub-boundary-output.txt: Emit the rotation warning whenever parsed SECRET_SCRUB_VIOLATIONS is a positive integer, including on recoverable PUBLISH_OK=false paths; only skip it on scrub-fatal rc 5 (publish.returncode != 0 without RECOVERY_BRANCH). Add a regression test with PUBLISH_OK=false, RECOVERY_BRANCH set, and SECRET_SCRUB_VIOLATIONS > 0 that asserts the warning still appears.


