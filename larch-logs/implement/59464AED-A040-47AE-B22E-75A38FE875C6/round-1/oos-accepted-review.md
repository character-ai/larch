### OOS_1: [OUT_OF_SCOPE] Duplicate `_gh_pr_checks` after `gather_status` can false-trigger startup deadline
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: During the startup window each poll may issue a second `_gh_pr_checks` (and often `_read_pr_checks_text`) inside `_checks_rollup_empty` after `gather_status` already fetched checks. If GitHub returns in-flight rows on the first call and an empty rollup on the second within the same iteration, or a failed second fetch returns empty text/JSON while `gather_status` saw in-flight `pending` rows, deadline time can accumulate toward a false `NO_CHECKS` bail (~300s later), especially under `gh` rate limiting from duplicate calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: reuse the checks payload from `gather_status` when available, or treat classified `pending` with non-empty JSON as disabling the deadline without a second fetch.
  - From cursor-specialist-edge-cases-output.txt: Reuse the checks snapshot from `gather_status` for the same iteration, or treat non-zero `_gh_pr_checks` return codes in `_checks_rollup_empty` as "unknown" (do not count toward empty accumulation).


