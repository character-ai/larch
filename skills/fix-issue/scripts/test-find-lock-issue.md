# skills/fix-issue/scripts/test-find-lock-issue.sh — contract

`skills/fix-issue/scripts/test-find-lock-issue.sh` is the offline regression harness for `skills/fix-issue/scripts/find-lock-issue.sh` (the explicit-target Lock + Rename pipeline). It uses a PATH-prepended `gh` stub under a per-fixture tmpdir plus a sterile git repository wrapper for script invocations, validating the script's exit-code matrix and unified stdout contract without network access or dependence on the caller's checkout state.

## Fixtures

1. **Eligible + lock OK + rename OK** → exit 0; `ELIGIBLE=true`, `ISSUE_NUMBER=N`, `LOCK_ACQUIRED=true`, `RENAMED=true`. Auxiliary delegate keys (`COMMENTED`, `NEW_TITLE`) are filtered from stdout.
2. **Eligible + lock fail** → exit 3; `ELIGIBLE=true LOCK_ACQUIRED=false ERROR=...`. Simulated by failing the IN PROGRESS comment post inside `cmd_comment`.
3. **Eligible + lock OK + rename fails best-effort** → exit 0; `LOCK_ACQUIRED=true RENAMED=false` + stderr `WARNING: title rename failed`. Validates that a rename API failure does not undo the lock and is surfaced as a non-fatal warning.
4. **Idempotent rename no-op** — coverage deferred to `scripts/test-tracking-issue-write.sh`. The eligibility filter rejects `[IN PROGRESS]`-prefixed titles before the rename call is ever made in production.
5. **Ineligible (managed prefix in explicit mode)** → exit 2; `ELIGIBLE=false ERROR=Issue #N has a managed lifecycle title prefix...`. Lock is never attempted (`LOCK_ACQUIRED` absent from stdout).
9. **Explicit-issue mode with a GHE-style host** → exit 0; `ISSUE_NUMBER=55 LOCK_ACQUIRED=true RENAMED=true`. The script is invoked with a full URL whose host is `ghe.example.com` (not `github.com`); the repo-ownership parser must accept any `https://<host>/<owner>/<repo>/issues/<n>` as long as `<owner>/<repo>` matches the current repo. Closes #766.
10. **Explicit-target umbrella with `[IN PROGRESS]` managed-prefix title** → exit 5; `ELIGIBLE=false IS_UMBRELLA=true UMBRELLA_ACTION=no-eligible-child UMBRELLA_NUMBER=N`. Closes #819. Pins the explicit-target reorder (umbrella detection runs BEFORE the managed-prefix early-reject).
11. **E2E umbrella dispatch with prose-blocked first child + ready second child** → exit 0; `IS_UMBRELLA=true UMBRELLA_ACTION=dispatched UMBRELLA_NUMBER=1100 ISSUE_NUMBER=1102 LOCK_ACQUIRED=true RENAMED=true`. Closes #768. End-to-end integration covering `find-lock-issue.sh → umbrella-handler.sh → blocker-helpers.sh`. Stateful-comments are enabled via per-fixture `RUNTIME_COMMENTS_DIR` so the lock post-check can find the just-posted IN PROGRESS comment by id.
13. **Explicit-target umbrella detect failure exits 2** → exit 2; `ELIGIBLE=false ERROR=umbrella-handler.sh detect failed for issue #300...`. Closes #891. When `umbrella-handler.sh detect` fails in explicit-target mode, the script must surface the error.
16. **Explicit-target dirty-tree abort** → exit 2; `ELIGIBLE=false`, dirty-tree guidance in `ERROR=`, no `LOCK_ACQUIRED=`, no `gh issue comment`, and no rename call.
18. **Umbrella dispatch dirty-tree abort** → exit 2 before child lock; stdout includes `IS_UMBRELLA=true`, `UMBRELLA_NUMBER`, `UMBRELLA_TITLE`, child `ISSUE_NUMBER`, child `ISSUE_TITLE`, `LOCK_ACQUIRED=false`, and the dirty-tree `ERROR=` prefix.
19. **Git-shim probe failure** → exit 2 with `ERROR=Cannot determine working-tree cleanliness:` and no lock comment. Uses a PATH-prepended `git` shim that fails only `git status --porcelain`.
22. **Explicit-target lock path (empty comment list)** → exit 0; `ISSUE_NUMBER=220 LOCK_ACQUIRED=true RENAMED=true`. Requires `RUNTIME_COMMENTS_DIR` for the lock post-check.
24. **Explicit-target refuses audit-report labeled issue** → exit 2; `ELIGIBLE=false`, error mentions `audit-report`. Closes #2462.
25. **No-arg invocation** → exit 2; `ELIGIBLE=false`, `ERROR=` contains usage hint. Confirms the mandatory-argument requirement.

## Sterile git wrapper

The harness runs each subject invocation through `with_sterile_repo`, which creates a per-fixture `git init` repository and runs `find-lock-issue.sh` from that directory. Clean-path fixtures are unaffected by ambient developer or CI dirt. Dirty-path fixtures write an untracked file into their sterile repo immediately before invocation, so the pre-lock probe sees controlled dirt.

Fixture 19 layers a `git` shim ahead of the normal PATH after the sterile repo exists. The shim passes every git subcommand through to the real binary except `git status --porcelain`, which exits 1 with multi-line stderr.

## Stub design

The stub `gh` dispatches on positional + `--json` args. Each fixture writes a stub state file under a per-fixture tmpdir; the stub `source`s the file to decide what to emit. State variables:

- `ISSUE_STATE` — fixture-controlled value for `gh issue view --json state`.
- `ISSUE_TITLE` — fixture-controlled value for `gh issue view --json title`.
- `ISSUE_URL_HOST` — fixture-controlled host (defaults to `github.com`) embedded in the `url` field returned by `gh issue view --json url`. Used by Fixture 9 to exercise host-generic URL parsing for GitHub Enterprise / self-hosted GHE deployments.
- `COMMENTS_JSON` — page-array JSON for `gh api --paginate --slurp .../comments`. Single-quoted in the state file so JSON braces survive `source`.
- `OPEN_ISSUES_JSON` — JSONL for `gh api repos/.../issues?state=open`.
- `RENAME_FAIL=true` — makes `gh issue edit --title` exit non-zero (used by Fixture 3).
- `COMMENT_FAIL=true` — makes `gh issue comment --body` exit non-zero (used by Fixture 2).

The stub emits an unhandled-invocation diagnostic to stderr and exits 99 if it sees a `gh` shape outside the supported subcommand set. This catches upstream call-shape changes that would otherwise silently break the harness.

## Out-of-scope coverage

- End-to-end gh API behavior (rate limits, auth flow, real network).
- Stateful concurrent-runner race conditions (the duplicate-IN-PROGRESS post-check inside `cmd_comment` uses `sleep 1` + re-fetch). The stub returns the same comment list per call; full coverage of the race path is exercised in production logs and via the indirect harness `test-issue-lifecycle.sh`.
- Title-prefix idempotency — covered by `scripts/test-tracking-issue-write.sh`.

## Wiring

The harness is wired into `make lint` via the `test-find-lock-issue` target in `Makefile`. Both `.sh` and `.md` are added to `agent-lint.toml`'s `exclude` list because agent-lint's dead-script and S030/orphaned-skill-files rules do not follow Makefile-only references.

## Edit-in-sync

If `find-lock-issue.sh`'s stdout contract gains new keys, changes exit-code semantics, or alters the delegate-stdout filtering policy, update this harness AND this contract in the same PR. If the delegate scripts (`issue-lifecycle.sh comment --lock`, `tracking-issue-write.sh rename`) gain new stdout keys that need explicit filtering at the `find-lock-issue.sh` boundary, extend the relevant fixture's `assert_not_contains` set.
