# skills/implement/scripts/post-design-boundary.sh — contract

`post-design-boundary.sh` is the mandatory mechanical gate immediately after `/design` returns in `/implement` Step 1 normal mode. It delegates manifest validation to `skills/design/scripts/read-design-manifest.sh --emit-load-breadcrumb`, captures the current branch, and ends successful stdout with an imperative continuation directive.

Inputs:
- `--implement-tmpdir <path>` is required. It must be an absolute path to an existing directory and must not contain ASCII control characters.
- `--session-env <path>` is optional. Non-empty values are trusted caller-controlled paths from `/implement`'s own session machinery; the script still rejects non-absolute paths and ASCII control characters.
- `--design-only true|false` is optional and defaults to `false`.
- `--hook-mode true|false` is optional and defaults to `false`. When `true`, the halt-protection sentinel (`.boundary-gate-passed`) is NOT written and `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` is emitted instead of `POST_DESIGN_BOUNDARY_OK=true`. Used exclusively by `hook-post-design.sh` so that the Stop hook remains armed (sentinel absent) until the orchestrator's mandatory Bash wrapper call runs. See "Halt-Protection Sentinel" below.

Logical failures are fail-closed envelopes, not process failures: the script exits 0 with `MANIFEST_FAILED=true` and `ERROR=<token>`. `invalid-tmpdir`, `invalid-session-env`, manifest-reader failures, `manifest-reader-no-status`, persistent branch-capture failure, and `boundary-gate-sentinel-write-failed` all emit ONLY the failure envelope on stdout — no `MANIFEST_OK=true` line, no `📥` reader breadcrumb, no `POST_DESIGN_BOUNDARY_OK=true`, and no `➡️` continuation line. The reader's success block (if produced) is buffered until every hard gate passes, so a late branch-capture or sentinel-write failure cannot leave a contradictory dual envelope on stdout. Unexpected internal errors are caught by the `ERR` trap and reported as `ERROR=internal-error`, matching the reader's contract.

Security invariants:
- The wrapper never `source`s `manifest.env` or `session-env.sh`.
- Reader output is classified only with anchored lines: `^MANIFEST_FAILED=true$` and `^MANIFEST_OK=true$`. A path containing the literal text `MANIFEST_FAILED=true` must not affect classification.
- Branch capture parses only anchored `BRANCH=<name>` output from `scripts/git-current-branch.sh`.

Branch capture uses `scripts/git-current-branch.sh`, retries once on failure, and emits `BRANCH=<name>` using the same token as the helper. If both attempts fail, the wrapper emits `MANIFEST_FAILED=true ERROR=branch-capture-failed` and exits 0. `skills/implement/SKILL.md` parses this wrapper-emitted `BRANCH=` and binds `BRANCH_NAME`; it must not re-run the branch helper on the post-`/design` path.

## Halt-Protection Sentinel

The Stop hook (`hook-stop-fail-close.sh`) blocks a session stop when `manifest.env` is present and `.boundary-gate-passed` is absent. This window covers the period between `/design` returning and the orchestrator successfully running its mandatory Bash wrapper call.

**Normal mode** (orchestrator-driven, `--hook-mode false`): after branch capture and before emitting the buffered success envelope, the wrapper writes `$IMPLEMENT_TMPDIR/.boundary-gate-passed`. This signals the Stop hook that the boundary was crossed and a later session stop is legitimate. Failure to write the sentinel emits `MANIFEST_FAILED=true ERROR=boundary-gate-sentinel-write-failed` and suppresses all success markers.

**Hook mode** (`--hook-mode true`): the sentinel is NOT written. The Stop hook therefore remains armed after the PostToolUse hook fires. If the orchestrator ignores the injected `➡️` directive and halts, the Stop hook detects the absent sentinel and blocks the stop, giving the orchestrator one more chance to run the Bash wrapper. The hook emits `POST_DESIGN_BOUNDARY_HOOK_INJECTED=true` (not `POST_DESIGN_BOUNDARY_OK=true`) to prevent the orchestrator from thinking the boundary was already passed without running the wrapper. Only `hook-post-design.sh` passes `--hook-mode true`; the orchestrator's own Bash call always uses the default `--hook-mode false`.

`NEXT_ACTION` is audit-only. The orchestrator must not use it as a parsing gate; the load-bearing continuation signal is the final `➡️` line. The default (non-hook-mode) variants are:

`➡️ 1: design plan — boundary gate passed; NEXT REQUIRED: write larch-log batches → Step 1.r rebase → Step 2 entry`

`➡️ 1: design plan — boundary gate passed (design-only); NEXT REQUIRED: write plan-goals-test + plan-review-tally log batches → post larch:diagrams summary comment → Step 9a.1 OOS pipeline`

Hook-mode variants begin with `➡️ 1: design plan — hook injected boundary context` and instruct the orchestrator to invoke the Bash wrapper immediately.

The design-only wording mirrors `skills/implement/SKILL.md` ordering: `plan-goals-test` and `plan-review-tally` are written first in all modes, then the `larch:diagrams` summary comment is posted (to the tracking issue only, not to larch-logs) on the design-only branch before Step 9a.1.

The manifest reader remains the schema authority. This wrapper buffers the reader's stdout and emits it only when every hard gate (manifest read, session-env validation, branch capture) passes; on success the reader's `📥 1: design plan — manifest loaded (plan=<basename>)` breadcrumb is preserved as a verification artifact. On reader failure the wrapper re-emits the reader's failure envelope verbatim. The wrapper then appends the branch, audit key, success key, warnings, and the imperative `➡️` line on the success path. Late failures (branch capture, internal errors) emit only the failure envelope — they do not also emit the buffered reader success block.

Edit-in-sync: update this file with `post-design-boundary.sh`, `skills/implement/SKILL.md` Step 1 normal mode, `scripts/test-implement-post-design-boundary.sh`, `skills/implement/scripts/test-post-design-boundary.sh`, and the hook scripts that consume `.boundary-gate-passed`. The repo-root harness owns SKILL.md and reader-pin assertions; the skill-local harness owns wrapper and hook integration behavior.
