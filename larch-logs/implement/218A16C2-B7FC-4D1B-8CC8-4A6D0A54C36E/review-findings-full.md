### REJ_C1: Cursor-Correctness (round 1) [code-review/rejected]

**Finding**: Branch diff adds three new files under larch-logs/implement/218A16C2-.../ not listed in the plan (manifest.json, plan-goals-test.md, plan-review-tally.json). Manifest embeds absolute operator filesystem paths.
**Reason not implemented**: larch-logs/implement/ artifacts are committed by design — this is the larch workflow's run-log contract documented in scripts/larch-log.md and docs/run-logs.md. Absolute paths in manifest.json are intentional metadata. Not a defect.

### REJ_C2: Cursor-Testing (round 1) [code-review/rejected]

**Finding**: No new test harness case that advances refs/heads/main on a bare remote, leaves refs/remotes/origin/main stale, and asserts the tracking ref updates correctly before git diff/rev-list logic runs.
**Reason not implemented**: Nit-level enhancement. The existing test suite runs /relevant-checks and passes. Adding a test for this specific refspec scenario is a separate improvement.

### REJ_C3: Cursor-Testing (round 1) — latent non-FF refspec [code-review/rejected]

**Finding**: Explicit refspec without '+' would reject a non-fast-forward update of refs/remotes/origin/main if that ref were corrupted or diverged from the remote.
**Reason not implemented**: Extremely unlikely edge case (remote-tracking refs should track the remote). Both scripts already handle fetch failure gracefully (capture-session-transcript.sh records push-skipped-fetch-failed; local-cleanup.sh prints a warning and continues). No change warranted.

### REJ_C4: Codex-Generic (round 1) — local-cleanup.sh:97 [code-review/rejected]

**Finding**: After updating origin/main via the refspec, git diff --name-only origin/main HEAD would include remote-side changes if remote main advanced, making _larch_log_diff_only=false and causing the flush-orphan reset to be skipped before git pull.
**Reason not implemented**: The described behavior is MORE correct after the fix. With a stale origin/main, the script would incorrectly believe it could reset/push when remote has advanced. With the fix, it correctly detects the situation and skips the operation, surfacing the conflict to the operator via the git pull failure path.

### REJ_C5: Codex-Generic (round 1) — capture-session-transcript.sh:177 [code-review/rejected]

**Finding**: git diff --name-only origin/main HEAD now includes remote-side changes when remote main has advanced, causing push-skipped-non-flush-diff instead of an attempted push.
**Reason not implemented**: Same reasoning as local-cleanup.sh:97 — this is the correct behavior. With a stale origin/main, the script would attempt to push or reset against an outdated base. After the fix, it correctly avoids pushing when remote has advanced.

