## Proposed Design Outline

### Goals
- Lift `with_transient_retry()` from `scripts/ship-pr.sh` into `scripts/lib-net.sh` as a public, generic, return-style helper next to `is_transient_net_signature()`.
- Wrap every network-touching git/gh callsite enumerated in the issue audit (Tier 1 + Tier 2 + Tier 3 hard-fails), so transient gh/GitHub hiccups no longer leave operators with a divergent local commit and a published remote branch.
- Fix `design-log-publish.sh` to unconditionally clean up the pushed remote branch when `gh pr create` retries are exhausted, eliminating the non-fast-forward trap from the original incident.

### Non-goals
- No new retry helper API beyond `with_transient_retry` + `transient_envelope_predicate_none`; ship-pr's existing envelope predicates stay in ship-pr.
- No migration of bare-push callsites to `scripts/git-push.sh` (kept as-is — separate helper with jittered backoff).
- No wrapping of the 14 tolerant `git fetch ... --quiet 2>/dev/null || true` callsites or `git remote add/set-url`.

### Approach sketch
- Move `with_transient_retry()` into `lib-net.sh`; have the lifted helper `return $_WTR_RC` (no `exit_transient_net`) and add a fixed 2s/4s sleep between attempts. Add `transient_envelope_predicate_none()` alongside.
- Keep `ship-pr.sh`'s terminal-exit semantics via a thin `ship_pr_with_transient_retry()` wrapper that calls the lifted helper and routes a non-zero return whose envelope matches `is_transient_net_signature` through `exit_transient_net`. Existing 7 ship-pr callsites switch to this wrapper.
- For every gap callsite (Tier 1 push/pr verbs, Tier 2 issue/api writes, Tier 3 hard-fail fetch/pull/ls-remote/clone/submodule), source `lib-net.sh` if not already, allocate a `fail_file`, and call `with_transient_retry transient_envelope_predicate_none "$fail_file" <verb> <args>` in place of the bare verb. Nested-retry callsites (`rebase-push.sh:274`, `create-pr.sh:129`) get wrapped per the Round 1 user decision.
- In `design-log-publish.sh`'s gh-pr-create-failed branch, run `git -C "$WT_DIR" push origin --delete "$WT_BRANCH" 2>/dev/null || true` (best-effort, unconditional) before emitting the failure, then drop the old "remote branch may need manual cleanup" log.
- Add `scripts/test-lib-net.sh` exercising `with_transient_retry`: rc=0 short-circuit, rc!=0 + transient signature retries 3x, rc!=0 + non-transient returns immediately, custom predicate matches rc=0 envelope-error, 2s/4s sleep between attempts (stubbed `sleep`).

### Surfaces in scope
- `scripts/lib-net.sh`, `scripts/lib-net.md`
- `scripts/ship-pr.sh` (delete local helper, add thin wrapper, update 7 callsites)
- `scripts/design-log-publish.sh`, `scripts/create-pr.sh`, `scripts/rebase-push.sh`, `scripts/merge-pr.sh`, `scripts/gh-pr-body-update.sh`, `scripts/check-remote-branch.sh`, `scripts/preflight.sh`, `scripts/create-branch.sh`, `scripts/local-cleanup.sh`, `scripts/tracking-issue-write.sh`, `scripts/tracking-issue-summary.sh`, `scripts/clarify-label.sh`, `scripts/clarify-comment-post.sh`, `scripts/named-block-write.sh`, `scripts/upsert-diagrams-comment.sh`
- `skills/set-up-forked-open-source-repo/scripts/setup-forked-open-source-repo.sh`
- `skills/design/scripts/decompose-file-issues.sh`
- `skills/issue/scripts/cleanup-failed-issue.sh`, `skills/issue/scripts/create-one.sh`
- `.claude/skills/combine-issues/scripts/apply-combination.sh`
- `.claude/skills/audit-runs/scripts/audit-preflight.sh`, `.claude/skills/audit-runs/scripts/audit-close-priors.sh`
- New: `scripts/test-lib-net.sh`, `scripts/test-lib-net.md`; Makefile target `test-lib-net` if a convention exists

### Open questions
- None.
