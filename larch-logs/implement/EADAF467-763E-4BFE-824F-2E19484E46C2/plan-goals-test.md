## Goal
Implement issue #4783: [IMPLEMENTING] [port-drift] [BUG] Run-log and ship port-parity gaps: cli.py pr create redaction, verify-completeness step9a1, breadcrumb confinement.

## Implementation Plan
## Summary

Three low-severity, latent or audit-only parity gaps from the #3672 / #3690 run-log and ship-pr ports. None are on a live exploitable path today; grouped as one cleanup. Found by the post-#4766 migration-wave audit.

## Findings

- **Dormant `cli.py pr create` lacks body redaction.** The bash `create-pr.sh` piped the PR body through `redact tmpdir-paths` then `redact secrets`, fail-closed, and its doc states the create path redacts the body. `python/pr.py` `create_main` reads `--body-file` raw and passes it to `gh.pr_create` with no redaction. This is currently inert: the live ship driver uses `compose_pr_body` / `ensure_pr` (which DO redact, verified), and `cli.py pr create` has no live caller. Risk realizes only if a future consumer repoints `cli.py pr create` as the create path. Fix: route `create_main` through the same redaction as `compose_pr_body`, or document it as redaction-free and not for outbound use; add a parity test.
- **verify-run-log-completeness step9a1 divergence.** `verify_completeness_main` `step9a1` condition was simplified (bash OR-ed `run-statistics.md` / `oos-issues.ndjson` / PR-number / status=done / `final-summary.md`; Python returns just `run-statistics.md` plus a new `steps_ran.step9a1` short-circuit). Audit-only (does not change which files are committed/redacted) and likely intentional (introduced by #4427, with a test asserting the new behavior). Fix: confirm intentional and note it, or restore the broader condition.
- **Breadcrumb tmpdir-confinement not re-checked.** Bash refused to stage any breadcrumb source file not under IMPLEMENT/DESIGN/REVIEW/RESEARCH_TMPDIR. `python/run_logs.py` `publish_breadcrumbs_main` trusts the derived `--source-dir`. Defense-in-depth only — the source is always derived from `log_root.parent`, never operator-supplied, and the load-bearing symlink + hardlink + name-allowlist guards are preserved. Fix: re-add the under-session-tmpdir assertion as defense-in-depth, or document why it is unnecessary.

## Affected files

- `python/pr.py` (`create_main`), `python/run_logs.py` (`verify_completeness_main` step9a1; `publish_breadcrumbs_main`), and the matching `python/test_pr.py` / `python/test_run_logs.py`.

## Suggested fix

Per finding above; each is small and independent. Prioritize the `cli.py pr create` redaction parity since it is the one with an outbound-secret angle if ever wired live.

## Related

Directly relevant to #4642 (sh-to-py G13 ci/pr/merge/push cutover): its "confirm parity per verb before delete" gate must catch this `create_main` vs `create-pr.sh` body-redaction gap before `create-pr.sh` is deleted. The verify-completeness and breadcrumb items are #3672-era run-log residue, unrelated to #4642.

## Test plan
(no test plan section in plan-file)
