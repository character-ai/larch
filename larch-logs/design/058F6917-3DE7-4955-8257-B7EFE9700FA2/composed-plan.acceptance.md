
## Acceptance

- After any failed coder apply (edit failure, commit failure, or all coders exhausted), `git status --porcelain` reports a clean tree (no staged and no unstaged tracked residue), so the next rebase (step 4.r / 7.r / 8 pre-ship) does not abort.
- A commit failure no longer returns rc=2 `coder-failed`. It cleans the tree and falls through to the next coder, then to rc=4 `main-agent-required`, which drives the existing main-agent apply plus autonomous resume at round N+1.
- Pre-existing tracked work and MAV head-only carryover (#3272) are preserved. Cleanup never runs a blanket `git reset --hard HEAD`.
- `submodule-violation` stays terminal (rc=3) but leaves a clean tree.
- `no-changes` (rc=0) and `applied` (rc=0) semantics are unchanged.
- `_cleanup_failed_coder_attempt` returns a verified-clean result. On verification failure the run stops at rc=2 with no staged and no unstaged residue.
- New and rewritten tests in `python/test_review_and_fix.py` pass, and `make lint`, `make py-lint`, and `make py-test` pass.
