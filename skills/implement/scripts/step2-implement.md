# step2-implement.sh

**Orchestrator wait contract**: the orchestrator MUST NOT call `ScheduleWakeup` while waiting on this dispatcher — `step2-implement.sh` blocks foreground until the implementer returns, so no wakeup is needed, and a non-sentinel `prompt` would re-fire as a `/loop` input on wakeup. See `skills/implement/SKILL.md` NEVER #9.

**Invariants**:
- Implementer-coder set: `{claude} ∪ external_tools`. `claude` is the implementer-only fallback path, never an external tool. The `TOOL=` envelope-line contract on external implementer paths continues to mean external implementer only.
- Cursor presence gate: `--cursor-present true|false|""` is accepted. Empty and missing values normalize to false. The gate runs after the `claude` early-return and before `REPO_ROOT` git-tree lookup, so `--coder=cursor --cursor-present false` emits `STATUS=claude_fallback` even outside a git work-tree and does not write baseline files. The orchestrator then runs the main-agent code-edit path the same way it would for `--coder=claude`.
- `--coder` is required. `/implement` Step 0 resolves the omitted operator flag in `scripts/implement-bootstrap.sh phase_coder_select`, and `run-step2-dispatch.sh` forwards that explicit value. A direct dispatcher call without `--coder` exits 2 before git resolution.
- Stdout is KV-only — `STATUS`, `TOOL`, `MANIFEST`, `QA_PENDING`, `REASON`, `TRANSCRIPT`, `SIDECAR_LOG`, `ORCHESTRATOR_EDIT_AUTHORITY`. The launcher's progress chatter is captured to the sidecar log; the implementer transcript is captured to disk; neither leaks to stdout. SKILL.md Step 2's parser is a fixed grammar.
- Spawn-time baseline files are written ONCE on the first invocation under `$TMPDIR_ARG`: `step2-baseline.txt` (HEAD SHA), `step2-spawn-branch.txt` (branch name), `step2-plugin-json-baseline.txt` (`git hash-object` of `.claude-plugin/plugin.json`). All resume invocations reuse them. The baseline SHA anchors the launcher-retry "clean state" guard (post-failure HEAD must equal baseline). The baseline-vs-HEAD diff cross-check that previously enforced manifest path-set equality was removed when the dispatcher took over committing — there is no longer a committed Codex diff to compare against.
- Immediately before launching the external implementer, the dispatcher writes malformed-manifest recovery baselines under `$TMPDIR_ARG`: `step2-prelaunch-porcelain.nul` (`git status --porcelain=v1 -z --untracked-files=all`), `step2-prelaunch-content-digests.txt` (SHA-256 snapshots for pre-dirty paths), and `step2-prelaunch-index.env` (`PRELAUNCH_INDEX_NONEMPTY=true|false`). If `$TMPDIR_ARG` is under the repo root, paths under that tmpdir are filtered from the recovery delta so harness scratch artifacts do not count as implementation work.
- Per-tool files under `$TMPDIR_ARG` use `${TOOL_TAG}-...` names: `${TOOL_TAG}-resume-count.txt`, `${TOOL_TAG}-impl-transcript.txt`, `${TOOL_TAG}-impl.log`, `${TOOL_TAG}-commit-message.txt`, and `${TOOL_TAG}-commit-stderr.txt`. `TOOL_TAG=codex` preserves the historical Codex filenames byte-for-byte.
- `$TMPDIR_ARG` is canonicalized with `cd "$TMPDIR_ARG" && pwd -P` immediately after validation and before any derived path is constructed. Manifest, QA, transcript, sidecar, baseline, raw-manifest, and resume-count paths therefore use canonical bytes, which keeps Codex `--add-dir` grants aligned with sandbox path resolution even when the caller supplied a symlinked or `..`-containing tmpdir spelling.
- Immediately after canonicalizing `$TMPDIR_ARG`, the dispatcher exports `IMPLEMENT_TMPDIR="$TMPDIR_ARG"`. If `$TMPDIR_ARG/session-id` exists and is non-empty, its trimmed contents overwrite any inherited `LARCH_TOKEN_SESSION_ID`; the canonical tmpdir file wins over stale environment state on external-implementer paths. If `$TMPDIR_ARG/claude-source.env` exists, `LARCH_CLAUDE_SOURCE_FILE` is exported to that snapshot path. The leaf launchers repeat the same overwrite defensively before spawning external tools.
- After the `claude` and cursor-presence fallback gates, the dispatcher marks `Step 2 — implementation` through `scripts/timing-ledger.sh` on the real external-implementer path. The same step label is written to `scripts/token-ledger.sh` from `scripts/launch-codex-implement.sh` / `scripts/launch-cursor-implement.sh` **after** the Step 2 token-budget preflight (`check-step-token-budget.sh`) succeeds, so a ledger `mark` row does not reset the vendor window before cap_hit can short-circuit. Both marks are best-effort and use the exported canonical `IMPLEMENT_TMPDIR` so they do not depend on prompt-side environment rehydration.
- Resume counter is incremented ONLY when `--answers PATH` is supplied. Cap is 5; the 6th `--answers` invocation emits `STATUS=bailed REASON=qa-loop-exceeded` without spawning the implementer.
- Launcher wrapper exit is captured separately from the implementer-reported `LAUNCHER_EXIT=` KV. Wrapper exit `2` is a validation failure and emits `STATUS=bailed REASON=wrapper-validation-failure` immediately without retrying. Wrapper exit `0` keeps the existing KV parsing behavior. Other non-zero wrapper exits enter the existing one-shot retry path only when no manifest was written and post-failure state is fully clean (`git status --porcelain` empty, no `.git/index.lock`, HEAD == `BASELINE_SHA`). Launcher stdout/stderr is captured to a temp file under the canonical `$TMPDIR_ARG`, capped to 65 KiB for bail-path parsing, and removed by an EXIT trap.
- The dispatcher does NOT `git reset`, NOT `git checkout`, NOT discard working-tree state. On `status=complete` it stages and commits implementer edits via `git add -A && git commit -F <commit-message-file>` — `commit_message` is taken from the manifest with no diff or subject cross-check, but IS piped through `scripts/redact-secrets.sh` immediately before `git commit -F` so the secrets-family scrubber that protects the canonical on-disk manifest also protects git history. After the successful dispatcher commit, it invokes `scripts/larch-log-flush.sh` best-effort so active `/implement` log writes are flushed behind the implementer commit. On any other status, the dispatcher leaves the working tree untouched. On `commit-failed`, `git add -A` has already run and the index stays staged — operators inspect `git status` and `$IMPLEMENT_TMPDIR/${TOOL_TAG}-commit-stderr.txt` (where the failed `git commit` stderr is captured) before deciding whether to `git reset` or amend. Implementer hard guard #1 (no destructive git ops) is mirrored here as "the dispatcher never destroys operator work either."
- Path validation rejects `..`, leading `/`, `.claude-plugin/plugin.json`, and any path under a submodule (per `git submodule status --recursive`). NUL bytes are rejected implicitly — bash variables cannot hold a NUL, so the `read -r` consuming the jq output terminates the field at any NUL upstream; an explicit `*$'\0'*` glob would expand to `**` (since `$'\0'` is empty in bash strings) and match every non-empty path, so the check must not be expressed that way. The reserved-file check is a defense-in-depth duplicate of `hooks/pre-commit-block-bump-version-edit.sh`'s contract.
- `manifest-schema-invalid` can recover to `STATUS=claude_fallback` only when the raw manifest parses as a JSON object, prior status is `complete` or empty with the legacy `{status, summary, checks}` fingerprint and no `schema_version`, the prelaunch index was empty, the post-launch NUL-safe delta is non-empty after tmpdir filtering and pre-dirty content-snapshot comparison, and post-implementer safety gates pass (branch unchanged, `.claude-plugin/plugin.json` unchanged, submodules clean including dirty paths under initialized submodules, Cursor HEAD unchanged). Recovery writes `step2-recovery-paths.nul`, quarantines `manifest-raw.json` to `manifest-raw.invalid.json`, and writes `recovery-metadata.json`.
- Exit code is 0 on every documented outcome (including `STATUS=bailed`). Exit 2 is reserved for caller-error (missing flag, bad path, bad enum value) before any Codex spawn.

**Stdout contract**:
```
STATUS=<complete|needs_qa|bailed|claude_fallback>
MANIFEST=<path>          # set ONLY when STATUS=complete or needs_qa, or when STATUS=bailed
                         # came from an implementer-authored manifest (status=bailed in the manifest
                         # itself, e.g. resume-incompatible). Dispatcher mechanical bails
                         # (commit-failed, manifest-schema-invalid, manifest-missing,
                         # branch-changed, protected-path-modified, submodule-dirty,
                         # qa-pending-missing, qa-loop-exceeded, redactor-not-executable,
                         # dirty-state-after-timeout, wrapper-validation-failure,
                         # codex-runtime-failure, cursor-runtime-failure,
                         # coder-mismatch-tmpdir-reuse) DO NOT emit
                         # MANIFEST= — and on commit-failed the manifest files are deleted
                         # from $IMPLEMENT_TMPDIR before bail to avoid leaving un-sanitized
                         # text on disk.
QA_PENDING=<path>        # set ONLY when STATUS=needs_qa
REASON=<token>           # set ONLY when STATUS=bailed
TRANSCRIPT=<path>        # set when launcher actually ran
SIDECAR_LOG=<path>       # set when launcher actually ran
ORCHESTRATOR_EDIT_AUTHORITY=<allowed|forbidden>
                         # ALWAYS emitted (every exit-0 outcome). `allowed` iff STATUS=claude_fallback;
                         # `forbidden` on every external-implementer outcome (complete/needs_qa/bailed).
                         # Mechanical gate for SKILL.md Step 2.4 main-agent Edit/Write authority.
RECOVERY_FROM=manifest-schema-invalid
RECOVERY_PRIOR_TOOL=<codex|cursor>
RECOVERY_PATHS_FILE=<path-to-step2-recovery-paths.nul>
                         # Optional all-or-none triplet emitted only with
                         # STATUS=claude_fallback on malformed-manifest recovery.
                         # The paths file is NUL-delimited and is the authoritative
                         # path list for recovery commit scoping.
```

**Flags**:

| Flag | Required | Purpose |
|------|----------|---------|
| `--tmpdir PATH` | yes | `$IMPLEMENT_TMPDIR` (where baseline / counter / manifest / transcript / sidecar log live) |
| `--plan-file PATH` | yes | The plan to implement (passed through to Codex) |
| `--feature-file PATH` | yes | The original feature description (passed through to Codex) |
| `--coder VALUE` | yes | `claude`, `codex`, or `cursor`. Resolved by `/implement` Step 0 and forwarded by `run-step2-dispatch.sh`. |
| `--codex-available VALUE` | optional (deprecated) | `true` (maps to `--coder codex`) or `false` (maps to `--coder claude`). Emits a stderr deprecation warning. Mutually exclusive with `--coder`. |
| `--cursor-present VALUE` | optional | `true`, `false`, or empty. Empty/missing normalizes to false. Consulted only on `--coder=cursor`; non-`true` falls back to `STATUS=claude_fallback` before `REPO_ROOT` lookup. |
| `--answers PATH` | optional | Operator answers to a prior `needs_qa` cycle; presence increments the resume counter |
| `--workflow VALUE` | optional (default `SIMPLE`) | `SIMPLE` or `HARD`; sets the coder timeout (`SIMPLE`=3600s, `HARD`=7200s). Invalid values exit 2. |

**Outcomes** (`STATUS` values):
- `complete` — all post-Codex mechanical checks passed; the dispatcher committed Codex's working-tree edits using `manifest.commit_message` (redacted via `scripts/redact-secrets.sh` immediately before `git commit -F`); the canonical manifest is sanitized and emitted at `$TMPDIR/manifest.json`.
- `needs_qa` — Codex wrote `qa-pending.json` with operator questions; SKILL.md Step 2 collects answers and re-invokes the dispatcher with `--answers`.
- `bailed` — Codex itself emitted `status=bailed`, OR the dispatcher overrode `complete` because mechanical validation failed. `REASON` token list is in `skills/implement/references/codex-manifest-schema.md` (Bail-reason tokens section). When the dispatcher overrides Codex, the dispatcher's reason wins.
- `claude_fallback` with `RECOVERY_FROM=manifest-schema-invalid` — external implementer produced a malformed manifest but left a recoverable working-tree delta. This is commit-only recovery: the orchestrator must not re-implement or rewrite those files, and must commit only the NUL-delimited recovery path list after plan-scope alignment.
- **`main-branch-prohibited`** — dispatcher-authored bail before the external launcher runs: spawn-time branch is `main` or `master`; `FORKED_TARGET` is not `true` (read from `$TMPDIR_ARG/session-env.sh` when that file exists; otherwise treated as `false`); and the run is issue-anchored — non-empty `ISSUE_NUMBER=` in `$TMPDIR_ARG/parent-issue.md` **or** `$TMPDIR_ARG/session-env.sh` exists (presence alone suffices; `ISSUE_NUMBER` may be absent in session-env). Harness runs with neither parent-issue nor session-env are not affected (external implementer may still run on `main`/`master` in those narrow harnesses — ship-time `bump-branch-guard` remains the non-negotiable backstop for mis-anchored production tmpdirs).
- **`detached-head-prohibited`** — same pre-launcher gate as `main-branch-prohibited`, but when the spawn-time symbolic branch is missing (detached HEAD / not on a branch) or legacy `step2-spawn-branch.txt` contains the literal `HEAD` from older `rev-parse --abbrev-ref` captures. Uses the same issue-anchored + non-fork predicates; fork mode skips via `FORKED_TARGET=true`.

**Bail-reason tokens emitted by the dispatcher** (set internally; full list in `codex-manifest-schema.md`):

**Call sites**:
- `skills/implement/SKILL.md` Step 2 — the only authorized caller.

**Edit-in-sync**:
- `skills/implement/references/codex-manifest-schema.md` — manifest schema and bail-reason tokens.
- `agents/_implementer-base.md` — inline `## Manifest JSON template` and self-validation prompt copied into both generated implementer prompts.
- `agents/codex-implementer.md` — the system prompt this dispatcher invokes.
- `skills/implement/SKILL.md` Step 2 — the caller; any change to the KV envelope must be mirrored in Step 2's parser.
- `skills/implement/scripts/test-step2-dispatch.sh` — the offline harness; any new outcome / reason token must be exercised.
- `scripts/extract-plan-scope-paths.sh` — shared `## Files to modify/create` scope grammar used by recovery plan-scope alignment.
- `scripts/check-recovery-paths-in-plan-scope.sh` — fail-closed recovery scope verifier for malformed-manifest preservation.
- `skills/implement/scripts/compute-step2-recovery-paths.sh` — shared recovery-delta recompute helper used by the dispatcher and Step 2.4 recovery path.
- `scripts/external-tool-registry.md` — update its "Sourced by" list when this script's source-list status changes.

**Makefile wiring**: `make test-step2-dispatch` (added in the same change that introduces the harness).
