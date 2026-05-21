# skills/fix-issue/scripts/find-lock-issue.sh — contract

`skills/fix-issue/scripts/find-lock-issue.sh` is the explicit-target Lock + Rename pipeline invoked by `/fix-issue` Step 0. The positional issue number or URL is mandatory. The title rename to `[IN PROGRESS]` is applied immediately on lock acquisition rather than minutes later when `/implement` Step 0.5 Branch 2 ran.

## Operations, in order

1. **Verify** — explicit-issue verification. For the non-umbrella path: open state, no `IN PROGRESS` lock present, no managed lifecycle title prefix (`[IN PROGRESS]` / `[DONE]` / `[STALLED]`), no `[... Report]` title pattern (e.g. `[Weekly Report]`, `[AUDIT REPORT]`, `[analysis report]` — case-insensitive), no `audit-report` GitHub label, and no open blocking dependencies (native + prose). `[ROUND-TRIP]` alone is intentionally not a managed-prefix gate: titles like `[ROUND-TRIP] Foo` remain eligible while lifecycle-prefixed titles like `[IN PROGRESS] [ROUND-TRIP] Foo`, `[DONE] [ROUND-TRIP] Foo`, and `[STALLED] [ROUND-TRIP] Foo` are rejected. The script resolves `REPO` once with `scripts/resolve-repo.sh` and passes `--repo "$REPO"` to direct `gh issue view` calls. When the explicit-target argument is a full URL, the repo-ownership check parses `owner/repo` and issue number from the URL before the fetch, rejects cross-repo URLs, then fetches the numeric issue under `--repo "$REPO"`; the cross-repo guard, not the host, is the actual safety net.

   **Umbrella detection**: runs BEFORE both the managed-prefix early-reject AND the report-prefix reject via `umbrella-handler.sh detect`. A non-zero exit from `detect` is fatal — emits `ELIGIBLE=false` with the propagated error and exits 2 (closes #891). If the issue is an umbrella, both gates are BYPASSED. Detection is title-only post-#846 — `umbrella-handler.sh detect` consults the title (the post-#819 bracket-prefix peel grammar) and does NOT consult the body. Issue #819 DECISION_1 (voted, 2-1) reordered umbrella detection ahead of the managed-prefix gate so umbrella titles carrying a managed prefix (e.g. `[IN PROGRESS] Umbrella: foo`) remain explicitly targetable. The umbrella's own blocker check still applies — a blocked umbrella exits 2 just like a blocked ordinary issue — but parsed children of the umbrella are filtered out of the **native** blocker set first, then unioned with the **prose** blocker set before the eligibility decision. The umbrella branch calls `native_open_blockers` and `prose_open_blockers` independently, applies the children-filter only to the native set, then unions the filtered native set with prose.

2. **Pre-lock dirty-tree probe** — immediately before the lock delegate runs, the script calls `scripts/check-clean-tree.sh --fail-closed`. A dirty tree exits 2 with `ERROR=Working tree is not clean. Commit or stash changes, then re-run /fix-issue. No issue was locked.` A failed `git status --porcelain` probe exits 2 with `ERROR=Cannot determine working-tree cleanliness: ...`. This probe is intentionally local-only: it does not fetch, rebase, create a session tmpdir, or mutate `larch-stalled-run.txt`.

   The probe is fail-closed here. `scripts/preflight.sh` also calls the same helper with `--fail-closed` (wrapped in `|| true` for `set -e` compatibility), so both callers share fail-closed semantics. Do not reintroduce `2>/dev/null` around this pre-lock probe; doing so would silently reopen the dirty-tree-after-lock failure class.

3. **Lock** — delegates to `skills/fix-issue/scripts/issue-lifecycle.sh comment --issue $N --body "IN PROGRESS" --lock` (for both ordinary issues and umbrella children). Refuses if the tail is already `IN PROGRESS`, snapshots a duplicate-detection anchor BEFORE posting, excludes the runner's own just-posted comment id from the post-check, and uses `>= snapshot_ts` for the comparator. See `issue-lifecycle.md` for the full contract.

   The lock is the **correctness invariant**: it serializes concurrent `/fix-issue` runners. Lock semantics live in `issue-lifecycle.sh`'s `cmd_comment` and are NOT re-implemented here.

4. **Rename** — best-effort delegation to `scripts/tracking-issue-write.sh rename --issue $N --state in-progress --repo "$REPO"` (or, on the umbrella-dispatch path, `--issue $C` for the chosen child). Applied AFTER the lock. Rename failure does NOT undo the lock (no compensating rollback) — the script still exits 0 with `LOCK_ACQUIRED=true RENAMED=false`. `/implement` Step 0.5 Branch 2's idempotent rename re-attempts on the next run-segment.

5. **Umbrella outcomes** (umbrella explicit-issue path only): when the explicit issue is detected as an umbrella, two non-lock outcomes are possible in addition to the dispatch-then-lock path:
   - **All children CLOSED** → exit 4. SKILL.md Step 0 invokes `finalize-umbrella.sh` (rename umbrella to `[DONE]`, post closing comment, close).
   - **No eligible child** (some open children exist but none pickable; OR zero parseable children — FINDING_3) → exit 5. SKILL.md Step 0 prints a warning and skips to Step 8.

## Stdout contract

KEY=value lines on stdout. The script captures delegate stdout into local shell variables and parses key-by-key — never streams. Only the keys below appear on stdout; auxiliary delegate keys (`COMMENTED`, `FAILED`, `NEW_TITLE`, etc.) are filtered.

| Key | Emitted when | Value |
|-----|--------------|-------|
| `ELIGIBLE` | always | `true` (eligibility pass) or `false` (ineligibility, umbrella no-eligible-child, or error) |
| `ISSUE_NUMBER` | `ELIGIBLE=true` | the candidate issue number. **On the umbrella-dispatch path (`UMBRELLA_ACTION=dispatched`, exit 0), this is the CHOSEN CHILD's number — not the umbrella's.** On the umbrella-complete path (exit 4), `ISSUE_NUMBER` is the umbrella's own number (the operator targeted the umbrella, and the next stage is finalizing it). On exit 5 (`UMBRELLA_ACTION=no-eligible-child`), `ISSUE_NUMBER` is omitted — `UMBRELLA_NUMBER` carries the umbrella's identity. |
| `ISSUE_TITLE` | `ELIGIBLE=true` | the candidate issue title (chosen child's title on dispatch; umbrella's own title on complete). |
| `LOCK_ACQUIRED` | `ELIGIBLE=true` | `true` (exit 0 — child or non-umbrella issue locked) or `false` (exit 3 — child lock failed; or exit 4 — umbrella complete, no lock attempted). |
| `RENAMED` | `LOCK_ACQUIRED=true` | `true` (rename succeeded) or `false` (idempotent no-op OR rename API failure — distinguished only by stderr WARNING). |
| `ERROR` | `ELIGIBLE=false` (exit 2 / exit 5) or `LOCK_ACQUIRED=false` (exit 3) | the failure reason. On umbrella exit-3 paths, `ERROR` includes the umbrella context (e.g., `Failed to lock chosen child #C of umbrella #U: <reason>`). |
| `IS_UMBRELLA` | only on umbrella paths (exit 0 dispatch / exit 3 child-lock-fail / exit 4 complete / exit 5 no-eligible-child / exit 2 umbrella-blocked) | `true`. **Absent on non-umbrella explicit-issue paths** (FINDING_1 invariant). |
| `UMBRELLA_NUMBER` | only when `IS_UMBRELLA=true` | the umbrella issue number. |
| `UMBRELLA_TITLE` | only when `IS_UMBRELLA=true` AND the umbrella was successfully detected (exit 0/3/4 paths; absent on exit-2-blocked-umbrella path because the title isn't load-bearing for that error) | the umbrella's title. |
| `UMBRELLA_ACTION` | only when `IS_UMBRELLA=true` AND not exit 2 | one of `dispatched` (exit 0 — child locked), `complete` (exit 4 — finalize), `no-eligible-child` (exit 5 — skip). |

Stderr carries diagnostics from this script and its delegates (for example: rename-failure `WARNING` lines when `tracking-issue-write.sh rename` fails best-effort; `WARNING` when `umbrella-handler.sh list-children` fails during umbrella blocker filtering; stderr merged from `issue-lifecycle.sh` / `gh` on lock and rename paths because those delegates are invoked with stdout+stderr captured together). Stderr is not part of the stdout KEY=value contract.

## Stdout-contract sub-cases for exit 2

Exit 2 covers several failure classes. Consumers that need to distinguish them must substring-match `ERROR=`.

- `gh` API failure or explicit issue not eligible: `ELIGIBLE=false ERROR=<reason>`.
- Pre-lock dirty-tree abort on ordinary paths: `ELIGIBLE=false ERROR=Working tree is not clean. Commit or stash changes, then re-run /fix-issue. No issue was locked.`
- Pre-lock dirty-tree abort on umbrella child paths: `ELIGIBLE=false IS_UMBRELLA=true UMBRELLA_NUMBER=<U> UMBRELLA_TITLE=<T> ISSUE_NUMBER=<C> ISSUE_TITLE=<child-title> LOCK_ACQUIRED=false ERROR=Working tree is not clean...`
- Pre-lock probe failure: `ELIGIBLE=false ERROR=Cannot determine working-tree cleanliness: <summary>`. The umbrella child path includes the same umbrella and child keys as the dirty-tree abort.
- Umbrella detect failure, umbrella blocked by dependencies, or pick-child failure: existing umbrella error shape; `UMBRELLA_TITLE` is absent unless the umbrella was already detected and a child dispatch reached the pre-lock probe.

Stable prefixes for dirty-tree automation are `ERROR=Working tree is not clean.` for porcelain-non-empty failures and `ERROR=Cannot determine working-tree cleanliness:` for probe failures.

## Exit codes

| Exit | Meaning |
|------|---------|
| `0` | Eligible issue found AND comment lock acquired. Rename may have succeeded or failed best-effort — `RENAMED=true` vs `RENAMED=false` distinguishes. **Umbrella sub-case** (`UMBRELLA_ACTION=dispatched`): `ISSUE_NUMBER` refers to the chosen CHILD; `UMBRELLA_NUMBER` carries the umbrella's identity for downstream Step 6 finalization hooks in `/fix-issue` SKILL.md. |
| `2` | Error: missing argument, `gh` CLI failure, explicit-issue request rejected (not open, has managed prefix, has report prefix, has `audit-report` label, locked by concurrent run, blocked by open dependencies — INCLUDING the umbrella's own blockers when the explicit target is an umbrella), or pre-lock dirty-tree / probe-failure abort before any GitHub mutation. |
| `3` | Eligibility passed but comment lock could not be acquired. For ordinary issues: concurrent runner won the race, or `gh` API failure during lock acquisition. **Umbrella sub-case**: child lock failed; `ERROR` carries `Failed to lock chosen child #C of umbrella #U: <reason>`. See "Recovery semantics on exit 3" below. |
| `4` | **Umbrella complete**: the explicit issue is an umbrella, all parsed children are `CLOSED`, AND at least one child was parsed (zero-children does NOT trigger this — see FINDING_3 in the umbrella-PR plan review; that case routes to exit 5). `ELIGIBLE=true`, `LOCK_ACQUIRED=false`, `UMBRELLA_ACTION=complete`. SKILL.md Step 0 invokes `finalize-umbrella.sh finalize --issue $UMBRELLA_NUMBER`. |
| `5` | **Umbrella has no eligible child**: explicit issue is an umbrella with at least one open child, but none are pickable (all blocked / locked / managed-prefixed) — OR zero parseable children were found in the umbrella body (FINDING_3). `ELIGIBLE=false`, `UMBRELLA_ACTION=no-eligible-child`, `ERROR` carries the blocking reason. SKILL.md Step 0 prints a warning and skips to Step 8. |

## Recovery semantics on exit 3

Exit 3 spans two sub-cases that differ in remote-state mutation. The script does NOT differentiate them on stdout — operators should consult `skills/fix-issue/SKILL.md` Known Limitations "Stale IN PROGRESS lock" for the per-case recovery flow.

- **--lock path — IN PROGRESS post failed** — `gh issue comment --body "IN PROGRESS"` fails. Comment stream UNCHANGED. Recovery: re-run `/fix-issue <N>`.
- **--lock path — duplicate-IN-PROGRESS post-check** — `cmd_comment` succeeds at post, but its post-write re-fetch detects 2+ `IN PROGRESS` comments at or after the snapshot timestamp (concurrent runner race). Recovery: manually delete the duplicate `IN PROGRESS` comments.

## set -e / set -o pipefail propagation

The script runs with `set -euo pipefail`. The two delegate calls are wrapped with `|| <var>=$?` so a non-zero exit from `issue-lifecycle.sh` or `tracking-issue-write.sh` does NOT prematurely abort `find-lock-issue.sh` before its unified contract is emitted. The `lock_exit` and `rename_exit` variables capture the delegate exit codes for downstream conditional logic.

This is load-bearing: without the guard, a `LOCK_ACQUIRED=false` outcome would not produce stdout at all, leaving `/fix-issue`'s Step 0 parser with empty input.

## Best-effort rename rationale

The rename failure mode is non-fatal because:
- The comment lock is the actual concurrency invariant; the title prefix is a visual-display lifecycle.
- `/implement` consistently treats title renames as best-effort across Step 0.5 Branches 1/2/3, Step 12a/12b (terminal `[DONE]`), and Step 18 (terminal `[STALLED]`), all logging to `Tool Failures` and continuing on rename failure.
- `/implement` Step 0.5 Branch 2's idempotent rename serves as the safety net: when `/fix-issue` invokes `/implement` with `--issue $ISSUE_NUMBER`, Branch 2 re-attempts the rename and short-circuits with `RENAMED=false` if the title is already prefixed.
- A compensating rollback (delete IN PROGRESS) would itself involve more `gh` API writes that can fail, widening the failure surface to fix a cosmetic inconsistency.

## Edit-in-sync rules

- If `issue-lifecycle.sh comment --lock`'s stdout contract changes (e.g., new keys added beyond `LOCK_ACQUIRED` / `COMMENTED` / `ERROR`), update the awk-based key extraction in `lock_and_rename_then_emit`.
- If `tracking-issue-write.sh rename`'s stdout contract changes on omit-`--round-trip` call paths (e.g., new keys beyond `RENAMED` / `NEW_TITLE` / `FAILED` / `ERROR`), update the awk-based key extraction. This script intentionally omits `--round-trip`, so `ROUND_TRIP_APPLIED` is not emitted here.
- If `scripts/check-clean-tree.sh`'s stdout contract changes, update `_emit_dirty_tree_pre_lock_abort`, `scripts/preflight.md`, and `scripts/check-clean-tree.md` together.
- If the unified stdout contract grows (new keys), update SKILL.md Step 0's parser, the new test harness `test-find-lock-issue.sh`, and this contract file in lockstep.
- The exit-3 reservation (lock-acquired-false-after-eligibility-pass) is consumed by `skills/fix-issue/SKILL.md` Step 0; both must change together if the meaning shifts.

## Test harness

`skills/fix-issue/scripts/test-find-lock-issue.sh` is the offline regression harness. It uses a PATH-prepended `gh` stub and a per-fixture sterile git repository so the pre-lock cleanliness probe is independent of the developer or CI checkout. It covers the explicit-target lock+rename matrix plus dirty explicit-target, dirty umbrella-dispatch, and git-shim probe-failure pre-lock aborts, and the mandatory-argument usage error. Wired into `make lint` via the `test-find-lock-issue` target. Both `.sh` and `.md` are in `agent-lint.toml`'s `exclude` list per the Makefile-only-reference pattern.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
