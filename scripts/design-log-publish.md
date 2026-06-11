# design-log-publish.sh contract

`scripts/design-log-publish.sh` flushes a completed `/design` session directory
(`$DESIGN_TMPDIR`) into `larch-logs/design/<RUN_ID>/` on the repository default
branch by:

1. Validating `--run-id` with the same slug rules as `python3 python/cli.py run-log`
   (`larch_log_slug_is_valid` / `larch_log_validate_slug` family: ASCII letters,
   digits, `.`, `_`, `-`; reject empty, `..`, `/`, `\`, leading `.`).
2. Resolving `REPO_ROOT` via `git rev-parse --show-toplevel` and the default
   base branch via `git symbolic-ref refs/remotes/origin/HEAD` (same family as
   `python3 python/cli.py run-log commit`'s default-branch guard — not a `main`-only string
   compare).
3. Creating a disposable git worktree on branch `larch-log-design-<RUN_ID>`
   from `origin/<default>`. Before `git worktree add`, the script refuses to
   start when that branch name is already checked out in another worktree, and
   it does not ignore a failed `git branch -D` for an existing local branch with
   the same name. Unlike `/implement` and `/fix-issue`, `/design` does not
   globally serialize publishers: two concurrent runs must not share the same
   `RUN_ID` slug on one clone, or they will collide on this branch/worktree slot.
4. Running `python3 python/cli.py run-log init` under `larch-logs/` in that worktree (schema v2
   `manifest.json` for skill `design`).
5. Copying design artifacts: top-level regular files (maxdepth 1), the strict
   `plan-review/` round-artifact allowlist documented below, plus all
   regular files under `render-cache/` (recursive). Symlinks at the top level
   are skipped; `plan-review/` and `render-cache/` subtrees fail closed on any
   symlink anywhere in them.
   Files whose basename matches `design_artifact_excluded` are skipped before
   any trim/redact work. The deny-list is exclusion-only: it never adds files
   to the publish set, so per-run flushed design-log bytes cannot increase
   when new deny arms land. The Python bridge stderr scratch log
   (`design-log-ship.stderr.log`) is excluded. Shared operational-scratch
   suffixes (also present in `round_artifact_included` for `/implement`):
   `*.sidecar`, `*.dirty-tree`,
   `*.untracked-baseline`, `*.done`, `*.diag`, `*.events.jsonl`,
   `*-output.txt.prompt`, `*-output-*.txt.prompt`. Plan-review-specific
   exclusions (#3534) deny raw transcripts (`cursor-plan-*-output*.txt`,
   `codex-primary-plan-*-output*.txt`, `claude-plan-*-output*.txt`; phased
   `-output-phase2.txt` / dynamic slugs match `*-output*.txt`), producer-backed
   sidecars (Cursor: `.meta`, `.json`, `.cap-hit`, `.tsv`, `.launch-stderr`,
   `.stderr-tail`; Codex primary: `.meta`, `.json`, `.cap-hit`, `.tsv`,
   `.launch-stderr`, `.stderr-tail`; Claude: `.meta`, `.tsv`, `.launch-stderr`,
   `.stderr`, `.stderr-tail`, `.jsonl` — not Cursor/Codex `.stderr` or
   cursor/codex `.jsonl`, which have no producers), and diagnostics
   (`claude-plan-*.prompt`, `render-plan-*.prompt`, slot-named `*-collector.failure.log` patterns,
   `plan-review-collector.stderr`,
   `plan-review-slots.ndjson.output-files.dropped-slots`). Other
   `/implement`-specific deny patterns (`coder-output.log`, `coder-codex.log`,
   `cursor-specialist-*-output.txt`, `*-vote-prompt.txt`, the known empty
   placeholders) are intentionally NOT included — those basenames do not
   appear in design tmpdirs. Derived/duplicate artifacts excluded per #3705:
   `aggregate-validate.py`, `findings.md.tmp`, `composed-plan.redacted.md`,
   `ballot.txt` (derived from `findings-in-scope.md` + `findings-oos.md`),
   `*-plan-voter-prompt.txt`, `aggregator-prompt.md`, `aggregate-untagged-input.md`,
   `findings-in-scope.pre-dedup.md`, `findings-in-scope.pre-aggregation.md`,
   `scout-plan-manifest.json.raw`, `scout-plan-manifest.json.raw.prompt`,
   `*-vote-output.txt.meta`, `*-vote-output.txt.json`. Phase 3d exclusions per
   #3721: `issue-body.txt` (raw tracking-issue body; canonical home is the
   GitHub issue), `issue.json` (JSON snapshot of the same issue), and
   `architecture-diagram.md` (same Mermaid body lives in the `larch:diagrams`
   issue comment). The exclusion list is
   also consulted for round-level files encountered in the round staging loop
   (so ballot.txt, panel-manifest.ndjson, and round-meta.json in a round
   directory are silently skipped rather than erroring).
   All other top-level basenames pass through (deny-only model). `findings.md` /
   `voting-tally.md` under `plan-review/` remain canonical.
   **Top-level dedup**: after computing the last round source directory, the
   top-level staging loop skips any file that is byte-identical (`cmp -s`) to
   the final round's copy. SIMPLE-tier runs with no `plan-review/` keep all
   top-level files.
   **`plan.txt` round-1-only / `plan.diff` rounds ≥ 2**: the round staging loop
   skips `plan.txt` for rounds ≥ 2. After the round staging loop, the publisher
   generates a unified diff (`plan.diff`) of round N's plan vs round N-1's plan
   for each round ≥ 2 where both source `plan.txt` files exist, then stages
   that diff with redaction. Each included file is trimmed then redacted:
   `*.meta` strips leading `CMD_JSON=`
   lines (`larch_redact_strip_meta_cmd_json`); files whose names match
   `*-output*.json` delete a top-level `.result` object when valid JSON
   (`larch_redact_strip_json_result`, fail-closed on trim error); other paths
   copy through without that JSON trim; then `python3 python/cli.py redact tmpdir-paths` and
   `python3 python/cli.py redact secrets` (in-process pipeline, same redactors as
   `larch_log_redact_file` without the larch-log stdout contract).
6. Committing `larch-logs/design/<RUN_ID>/`. The commit subject carries no
   `[skip ci]` marker, so CI runs on the publish PR. `--reason pause` uses
   `pause design run` in the subject; the default `--reason final` uses
   `flush design run`.
7. Pushing the disposable branch, creating a PR with `gh pr create --head`
   (not `create-pr.sh`), resolving the repository slug for the CI/merge gate,
   then running a two-phase required-check gate before `git worktree remove --force`:
   - Registration wait: the script records the post-push commit and polls until
     required checks are reported for that pushed head. Registration requires
     both a parseable, non-empty `gh pr checks --required --json bucket` array
     and `gh pr view --json headRefOid` matching the pushed commit. "No checks
     reported yet" and checks attached to a stale prior PR head are transient
     within the bounded grace, not CI failures.
   - Completion wait: only after registration does it delegate to
     `python/cli.py ship design-log` (`python/design_log_ship.py`). The Python
     helper polls required checks only (`ci_monitor.checks_status(required=True)`,
     equivalent to `gh pr checks --required`) and uses checks-only / PR-state-only
     probes; it deliberately does not call the full `poll_ci()` / `gather_status()`
     path because those run git fetch, behind-count, and merge-state probes that
     are irrelevant to an already-green log-only PR.
   Required-mode classification fails closed: admin merge happens only when every
   required row is explicitly pass/success. Cancelled, skipped/skipping, unknown,
   missing-bucket, pending, empty/no-checks, read-error, and any other non-pass
   classification do not merge.
   Design-log PRs get one bounded failed-run rerun using
   `CI_MONITOR_TRANSIENT_RERUN_MAX=1`, only when failed logs contain a transient
   network signature. Failed logs are collected for diagnostics and readiness;
   ready logs without a transient signature fail closed without spending a rerun.
   Failed-log readiness polling and post-rerun stale-row settle polling are both bounded by the
   checks wait budget derived from `CI_WAIT_TIMEOUT_SEC / CI_WAIT_POLL_INTERVAL_SEC`,
   so an immediately re-observed stale failed check row does not prematurely
   exhaust the rerun path while GitHub propagates the rerun.
   The squash admin merge is also owned by Python, wraps
   `gh pr merge --admin --squash --delete-branch` in transient retry, and runs
   from the consumer repository root (`$REPO_ROOT`), not the disposable worktree
   and not the plugin checkout.
   `--admin` is retained because the repo's review ruleset has no bot reviewer,
   so a server-side `--auto` merge would be enabled but never complete; the gate
   bypasses review only after CI is registered for the current head and passes.
   The registration budget is derived from the timeout and interval constants as
   `ceil(timeout/interval)+1` probes, including the initial t=0 probe, so tests
   can stub sleep without waiting on wall clock. Registration probes capture
   stdout under `set +e` and parse the JSON array regardless of `gh`'s exit code;
   `jq -e` output is redirected away from stdout so boolean probe results never
   leak onto the `KEY=value` contract stream. Registration timeout emits a
   dedicated `did not register within` diagnostic with the timeout/probe budget,
   redacts the last captured checks/head diagnostics, sets `merge_rc=1`, and
   skips the Python completion helper. A completion failure preserves
   `PUBLISH_OK=false` and recovery metadata; `already_merged` races are treated
   as idempotent `PUBLISH_OK=true`. If repository resolution fails before the
   merge gate, the script logs a clear error and does not invoke Python with an
   empty repo. Direct Python CLI calls with an explicit invalid non-empty
   `--repo` are usage errors (exit 2) and do not fall back to cwd repo resolution.

## Empty Porcelain (Final)

For `--reason final`, an empty `git status --porcelain -- larch-logs/design/<RUN_ID>`
after staging is treated as an idempotent success only when `origin/<default>`
already contains at least one path below that run directory. In that case the
script emits `PUBLISH_OK=true` with empty PR fields and does not create or merge
a flush PR. If the default branch does not contain the run directory, the same
empty-porcelain state is a fail-closed publish (`PUBLISH_OK=false`) because no
fresh log snapshot can be proven to exist.

## Pause Reason

`--reason final|pause` defaults to `final`. Pause callers MUST pass
`--reason pause`.

Pause publishes differ in four ways:

- Commit subject: `chore(larch-logs): pause design run <RUN_ID>`.
- Manifest: when there is a non-empty commit to publish, `manifest.json` is
  updated with `.paused = true`. The empty-porcelain early-exit path does not
  force a manifest rewrite; the issue-body `larch:design-pause` marker remains
  the canonical paused signal.
- Branch reuse: the script best-effort fetches an existing
  `origin/larch-log-design-<RUN_ID>` ref before creating the disposable worktree
  and pushes with `git push --force-with-lease`.
- `.completed/`: regular files under `$DESIGN_TMPDIR/.completed/` with
  `step-*` basenames, plus the exact driver phase-sentinel basenames
  `emit_plan`, `tally`, `finalize`, and `validate_plan_commands`, are staged to
  `larch-logs/design/<RUN_ID>/.completed/` through the normal redaction path.
  The phase-sentinel list is sourced from `skills/design/scripts/design-driver.sh`
  accepted actions and must stay in sync with that driver list.

## PR creation exception

This script is the documented disposable-worktree exception to the repository's
default PR creation path. It pushes a custom `larch-log-design-<RUN_ID>` branch
from a temporary worktree and owns its own PR lookup, merge, recovery-branch,
and cleanup semantics, so it invokes `gh pr create --head` directly instead of
delegating to `scripts/create-pr.sh`.

The PR body is still file-backed: the script writes the short body into a
`mktemp` file before `git push` and passes that path via `--body-file`. Writing
the body file before push ensures a local temp-file failure cannot leave a
pushed branch that never had a valid PR body prepared.

## Output

On stdout (parseable `KEY=value` lines):

**Exit code**: `PUBLISH_OK=true|false` remains the stdout contract. Exit `0` on
all expected failures before a successful `git push`, and on post-push paths
that still parse cleanly via stdout alone. Exit `1` on `git push` failure,
`gh pr create` failure after push (when list recovery also fails), required-check
registration timeout for the pushed head, a required status check that does not
pass during the Python required-check completion gate (the publish refuses to
merge), and merge failure after a successful create — while still emitting
`PUBLISH_OK=false` (and `RECOVERY_BRANCH=…` when applicable). Callers that
already parse `PUBLISH_OK` need no change; callers that want fail-closed
signaling can additionally check the exit code.

Per-script `larch-quiet-*-*.log` files in `$DESIGN_TMPDIR` are excluded from
top-level artifact staging (`design_artifact_excluded`); they are published
exclusively under `breadcrumbs/` via `larch_log_publish_breadcrumbs_shared`.

| Key | Meaning |
|-----|---------|
| `PUBLISH_OK` | `true` when the publish succeeded and the squash `--admin` merge completed after the required CI checks passed; `false` on validation failure, init/copy/redact failure, git/gh errors, a required check that did not pass during the CI-wait gate, or merge refusal. |
| `PR_NUMBER` | GitHub PR number when known (may be set when `PUBLISH_OK=false` if create succeeded but merge failed). |
| `PR_URL` | PR URL when known. |
| `RECOVERY_BRANCH` | Recovery ref name when `PUBLISH_OK=false`: `larch-log-design-<RUN_ID>` after a successful push that still needs cleanup, or `larch-log-design-recovery-<RUN_ID>` when push failed and the local commit was preserved only in the consumer clone. |

`--dry-run` validates arguments, confirms `--design-tmpdir` exists, requires
`git` and `gh` on `PATH`, resolves `git rev-parse --show-toplevel` and
`origin/HEAD` read-only (same as a real publish preflight), skips the `jq`
requirement and all mutating git/gh steps, and emits `PUBLISH_OK=true` with
empty `PR_NUMBER` / `PR_URL`.

## Security and token scope

Validates `$DESIGN_TMPDIR` is under the allowlist via `larch_design_tmpdir_validate` immediately after the required-arg check and before any worktree or log-root mkdir; failure routes through `emit_publish_result false; exit 0` to preserve `PUBLISH_OK=false`.

Design log bytes follow the same tmpdir + secrets redaction pipeline as
implement round artifacts. Dropping the `[skip ci]` marker means CI runs on the publish PR; the script
first waits for required checks to register on the pushed commit head, then
delegates the required-check-only completion wait, single bounded failed-run
rerun, and transient-retried merge to `python/cli.py ship design-log`. It
refuses to merge on registration timeout, head mismatch within the grace,
required-check failure after the bounded rerun path, unresolved repository, or
merge failure. The merge itself is `gh pr merge --squash --admin --delete-branch`:
`--admin` bypasses the review-required branch protection (this
repo's review ruleset has no bot reviewer, so a server-side `--auto` merge
would enable but never complete), and requires a `gh` OAuth token with `repo`
(or equivalent) including admin-merge privileges. It bypasses only review — not
CI, which the registration-plus-Python-required-check gate has already enforced. Orgs that
forbid admin merges see `PUBLISH_OK=false` while the disposable branch may still
exist remotely — operators reconcile manually. When `git push` succeeds but
registration, Python completion, PR create, or merge fails, stderr notes the remote
branch and stdout may include `RECOVERY_BRANCH=…` for automation. See
`SECURITY.md` for the consolidated note.

## plan-review allowlist

`$DESIGN_TMPDIR/plan-review/` is optional. A missing path is success and stages
no files. When present, including as a symlink path caught by the `-L` guard,
it is fail-closed:

- `plan-review` must be a real directory, not a symlink and not a regular file.
- Any symlink anywhere below the resolved physical `plan-review` root fails the
  publish before regular-file enumeration. This catches both symlinked files
  and symlinked intermediate directories; `find -type f -not -type l` is not
  sufficient because `find` does not traverse symlinked directories without
  `-L`.
- Each enumerated file must pass the under-root prefix guard against the
  resolved physical root, matching the `render-cache/` guard.
- A per-file `[[ -L "$f" ]]` recheck immediately before staging closes the
  find-to-stage race window at the leaf-component slot.
- `design_publish_ancestor_within_root` re-resolves each file's parent physical
  path immediately before staging and fails closed when any ancestor directory
  was swapped for a symlink after the `find -type l` scan (closes the
  parent-directory TOCTOU the leaf recheck left open). The guard runs in all
  three subtree staging loops (`plan-review/`, `render-cache/`, `.completed/`).
- Top-level round files must match `^round-[1-9][0-9]*/[A-Za-z0-9._+-]+$` and pass
  `design_round_artifact_included(basename)` from `scripts/lib-design-round-artifacts.sh`,
  OR be known-excluded per `design_artifact_excluded(basename)` (silently skipped).
  `plan.txt` for round ≥ 2 is skipped before the inclusion check; `plan.diff` is
  generated and staged by the publisher after the main round-file loop.
- Files under `^round-[1-9][0-9]*/revise/` are rejected. Step 3 no longer
  runs inter-round revise, so newly published logs must not carry revise
  prompts, outputs, or candidate patches.
- Any other path under `plan-review/` emits `larch_err` and `PUBLISH_OK=false`.
- Round numbers are positive integers with no leading zero; `round-0` and `round-01` are rejected.

Edit-in-sync: any allowlist change updates `lib-design-round-artifacts.sh`, this doc,
`plan-review-loop.md`, `scripts/lib-design-round-artifacts.md`, and
`scripts/test-lib-design-round-artifacts.sh` in the same change. The current
`round-N/revise/` has an empty include set.

Allowed files are staged through the same trim/redact pipeline as other design
artifacts at `larch-logs/design/<RUN_ID>/plan-review/<relpath>`.

## render-cache symlink rejection

`$DESIGN_TMPDIR/render-cache/` is optional. A missing directory is success and
stages no files. When present, including as a symlink path caught by the `-L`
guard, it is fail-closed against symlinks:

- `render-cache` must be a real directory, not a symlink (including dangling)
  and not a regular file.
- Any symlink anywhere below the resolved physical `render-cache` root fails the
  publish before regular-file enumeration. Same rationale as `plan-review/`:
  this catches both symlinked files, which `find -type f` would silently skip,
  and symlinked intermediate directories, which `find` does not traverse without
  `-L`.
- Each enumerated file must pass the under-root prefix guard against the
  resolved physical root.
- A per-file `[[ -L "$f" ]]` recheck immediately before staging closes the
  find-to-stage race window at the leaf-component slot.
- `design_publish_ancestor_within_root` runs per file before staging (same
  parent-directory TOCTOU backstop as `plan-review/` above).
- No filename allowlist is enforced because render-cache content schema is open.
  The suffix deny-list inside `design_publish_stage_file` (`*.sidecar`,
  `*.events.jsonl`, etc.) is preserved unchanged.

Allowed files are staged through the same trim/redact pipeline at
`larch-logs/design/<RUN_ID>/render-cache/<relpath>`.

## Tests

Offline harness: `scripts/test-design-log-publish.sh` (Makefile target
`test-design-log-publish`).

## Recent contract coverage

- `--repo` is validated as `OWNER/REPO`; malformed values exit 1 before `gh` / network work and do not emit a success envelope.

## Vendor failure-diagnostics carrier exclusions (#3713)

`design_artifact_excluded` keeps raw per-attempt diagnostic archives out of git —
`*.sidecar`, `*.diag`, `*.events.jsonl`, plus the `#3713` additions
`*.sidecar.history`, `*.events.history`, the scout tier raw stems `*.raw.cursor` /
`*.raw.claude`, and `scout-plan-manifest.json.raw.{meta,stderr,prompt}`. None of
those arms end in `.failure-diag`, so the composed `*.failure-diag` carrier falls
through to the default-include path and is staged + redacted like any other
committed artifact. See `docs/vendor-agent-diagnostics-audit.md`.
## Concise prune/log audit update

Default design publishing keeps root `plan.txt` but stages only the exhaustive concise per-round plan-review set: `round-summary.env`, `findings-classification.tsv`, `prune-decision.env`, and `prune-nit.env`. `plan.diff`, `composed-plan.diff`, votes, manifests, and raw reviewer prose require `LARCH_FLUSH_DEBUG=1`.
