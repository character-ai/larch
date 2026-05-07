# skills/implement/scripts/post-design-boundary.sh — contract

`post-design-boundary.sh` is the mandatory mechanical gate immediately after `/design` returns in `/implement` Step 1 normal mode. It delegates manifest validation to `skills/design/scripts/read-design-manifest.sh --emit-load-breadcrumb`, propagates child-skill health degradation, captures the current branch, and ends successful stdout with an imperative continuation directive.

Inputs:
- `--implement-tmpdir <path>` is required. It must be an absolute path to an existing directory and must not contain ASCII control characters.
- `--session-env <path>` is optional. Empty means no health propagation. Non-empty values are trusted caller-controlled paths from `/implement`'s own session machinery; the script still rejects non-absolute paths and ASCII control characters.
- `--design-only true|false` is optional and defaults to `false`.

Logical failures are fail-closed envelopes, not process failures: the script exits 0 with `MANIFEST_FAILED=true` and `ERROR=<token>`. `invalid-tmpdir`, `invalid-session-env`, manifest-reader failures, `manifest-reader-no-status`, and persistent branch-capture failure all emit ONLY the failure envelope on stdout — no `MANIFEST_OK=true` line, no `📥` reader breadcrumb, no `POST_DESIGN_BOUNDARY_OK=true`, and no `➡️` continuation line. The reader's success block (if produced) is buffered until every hard gate passes, so a late branch-capture failure cannot leave a contradictory dual envelope on stdout. Unexpected internal errors are caught by the `ERR` trap and reported as `ERROR=internal-error`, matching the reader's contract.

Security invariants:
- The wrapper never `source`s `manifest.env`, `session-env.sh`, or `.health` sidecars.
- Reader output is classified only with anchored lines: `^MANIFEST_FAILED=true$` and `^MANIFEST_OK=true$`. A path containing the literal text `MANIFEST_FAILED=true` must not affect classification.
- Health sidecars are parsed line-by-line for anchored `KEY=value` records. Only `CODEX_HEALTHY`, `CURSOR_HEALTHY`, and `GEMINI_HEALTHY` are read, and only literal `true` or `false` values are accepted. Malformed values emit `WARN=health-value-invalid:<KEY>` and preserve the prior session-env value.
- Branch capture parses only anchored `BRANCH=<name>` output from `scripts/git-current-branch.sh`.

Cross-Skill Health Propagation is mechanical here. When `--session-env` is non-empty and `<session-env>.health` exists, the wrapper reads the existing session-env file for `SLACK_OK`, `SLACK_MISSING`, `REPO`, `REPO_UNAVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`, and `GEMINI_HEALTHY`. It applies monotonic health semantics: a tool may degrade `true -> false`, but it may not recover `false -> true` during the session. It calls `scripts/write-session-env.sh` only when at least one health flag actually flips after merging with the sidecar, preserving the four non-health keys. A write failure emits `WARN=health-merge-failed` and remains non-fatal; health propagation is auxiliary and must not block the post-design boundary gate.

Branch capture uses `scripts/git-current-branch.sh`, retries once on failure, and emits `BRANCH=<name>` using the same token as the helper. If both attempts fail, the wrapper emits `MANIFEST_FAILED=true ERROR=branch-capture-failed` and exits 0. `skills/implement/SKILL.md` parses this wrapper-emitted `BRANCH=` and binds `BRANCH_NAME`; it must not re-run the branch helper on the post-`/design` path.

`NEXT_ACTION` is audit-only. The orchestrator must not use it as a parsing gate; the load-bearing continuation signal is the final `➡️` line. The default variant is:

`➡️ 1: design plan — boundary gate passed; NEXT REQUIRED: write anchor-section fragments → Step 1.r rebase → Step 2 entry`

The design-only variant is:

`➡️ 1: design plan — boundary gate passed (design-only); NEXT REQUIRED: write plan-goals-test + plan-review-tally anchor fragments → write diagrams anchor fragment → Step 9a.1 OOS pipeline`

The design-only wording mirrors `skills/implement/SKILL.md` ordering: `plan-goals-test` and `plan-review-tally` are written first in all modes, then `diagrams` is written only on the design-only branch before Step 9a.1.

The manifest reader remains the schema authority. This wrapper buffers the reader's stdout and emits it only when every hard gate (manifest read, session-env validation, branch capture) passes; on success the reader's `📥 1: design plan — manifest loaded (plan=<basename>)` breadcrumb is preserved as a verification artifact. On reader failure the wrapper re-emits the reader's failure envelope verbatim. The wrapper then appends the branch, audit key, success key, warnings, and the imperative `➡️` line on the success path. Late failures (branch capture, internal errors) emit only the failure envelope — they do not also emit the buffered reader success block.

Edit-in-sync: update this file with `post-design-boundary.sh`, `skills/implement/SKILL.md` Step 1 normal mode, `scripts/test-implement-post-design-boundary.sh`, and `skills/implement/scripts/test-post-design-boundary.sh`. The repo-root harness owns SKILL.md and reader-pin assertions; the skill-local harness owns wrapper integration behavior.
