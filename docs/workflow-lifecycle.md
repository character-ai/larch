# Workflow Lifecycle
How skills compose to form the end-to-end development workflow in Larch.

## Skill Orchestration Hierarchy

Skills are not invoked in a flat sequence. They form a hierarchical call graph where higher-level **stateful orchestrators** invoke lower-level skills and continue execution based on their side effects. The diagram below shows true orchestrators and their direct sub-skills; pure forwarders (`/im`, `/f`, `/fm`, `/block-issue`) are covered separately in the [Delegation Topology](#delegation-topology) subsection because they run no post-delegation logic. `/alias` is a hybrid (validate → delegate → verify) — it also appears in the Delegation Topology subsection.

```text
graph TD
    DESIGN["/design"]
    DESIGN -.->|issue-body larch:plan| IMPLEMENT["/implement"]
    IMPLEMENT -->|runs helper for| STEP5["review-and-fix step5"]
    IMPLEMENT -->|runs helper for| CHECKS["project relevant-checks script"]
    IMPLEMENT -->|invokes| ISSUE_OOS["/issue (OOS filing)"]
```

- **`/implement`** — top-level orchestrator. Runs the full design → code → review → PR workflow by default; Step 2 supplies valid `ARCHITECTURAL_INVARIANTS.md` before valid `ARCHITECTURAL_GUIDELINES.md` to external coders as untrusted, plan-scoped evidence and requires a manifest acknowledgment when knowledge was present. Step 5 invokes `review-and-fix step5`, which uses a fixed round cap of **2** rounds (hard ceiling), does **not** forward `--panel` on the public argv, and applies the panel only inside `review-and-fix CLI` → `review core` (see [Review Agents](review-agents.md) Note A for the **review panel**, **specialists per vendor**, round 2 pruned on round-1 productivity, no generic Codex row, and `--no-fallback` reviewer-dispatch contract). Step 8 architectural assessment is authored by a read-only `larch:arch-assessor` subagent (invariants before guidelines) and persisted fail-closed by `architectural-assessment submit`; an invariant `violation` or guideline `deviation` routes through the subagent fix ladder (a `larch:claude-implementer` coder, then the main agent), an unresolved invariant `violation` hard-stops the run with `invariant-violation-unresolved` and creates no PR, and an unresolved guideline `deviation` needs a documented `Exception:` block to clear the ship gate. With the `--merge` flag, also runs the CI+rebase+merge loop and local cleanup after PR creation. Preflight runs `python/cli.py admission gate` before Step 0; Step 0 resolves tracking-issue state (sentinel reuse, positional issue adoption, or `Closes #<N>` recovery from the current branch's PR body) and materializes the plan from the issue body. **Phase 1 (#3364):** `/implement` does not invoke `/release` or write `release notes` on the ship path — versioning and release notes updates move to the operator-run `/release` skill (Phase 3). The published run archive is the single source of truth for full report content (voting tallies, rejected findings, diagrams, OOS observation links, execution issues, run statistics), with the PR body as a slim projection (Summary + diagrams + Test plan + `Closes #<N>` — diagrams appear in both places by design). Step 9a.1 additionally invokes `/issue` in batch mode to file accepted OOS findings as GitHub issues.

## Delegation Topology

Pure forwarders are **not** orchestrators — they validate input (when applicable), call the Skill tool exactly once, and exit. They run no logic after the child returns. This subsection also documents `/alias`, which is a hybrid: it validates, delegates to `/implement`, and then performs a mechanical sentinel-file verification (see `/alias` Step 4). Edges are labeled with the **arguments passed on that edge** (what the immediate child receives), not the final expansion — for single-hop delegation (`/im`, `/alias`) this is also what `/implement` sees.

```text
graph LR
    IM["/im"] -->|merge args| IMPLEMENT["/implement"]
    ALIAS["/alias"] -->|args| IMPLEMENT
```

- **`/im`** — prepends `--merge` to `$ARGUMENTS` and forwards to `/implement`. Equivalent to `/implement --merge <tail>` where `<tail>` is the forwarded argv (positional `<issue-N>` for PR-shaped flows).
- **`/f`** — prepends `--force --self-review --self-implement` and forwards to `/implement`.
- **`/fm`** — prepends `--force --self-review --self-implement --merge` and forwards to `/implement` (same as `/f --merge`).
- **`/alias`** — hybrid: validates alias name, delegates to `/implement` (and any preset flags) to scaffold a new alias skill, then performs a sentinel-file verification (Step 4) that the expected `SKILL.md` was actually written. Auto-resolves the target directory: inside a Claude plugin source repo (two-file predicate `.claude-plugin/plugin.json` + `skills/implement/SKILL.md` at the git repo root) the alias goes under `skills/<n>/`; anywhere else, under `.claude/skills/<n>/`. Accepts optional `--merge` to merge the alias-creation PR and `--private` to force `.claude/skills/<n>/` even in a plugin repo (no-op in non-plugin repos).
- **`/block-issue`** — pure delegator. Accepts two issue numbers (`ISSUE_A ISSUE_B`), resolves their GitHub GraphQL node IDs, calls the native `addBlockedBy` mutation, and verifies the dependency was recorded. Thin wrapper around `python/cli.py block-issue add-blocked-by`. No sub-skill delegation.

Pure forwarders (`/im`, `/f`, `/fm`, `/block-issue`) are exempt from the post-invocation-verification and anti-halt-continuation rules defined in `skills/shared/subskill-invocation.md`. `/alias` is NOT exempt — it carries both the post-invocation sentinel check and the anti-halt banner/micro-reminder. See that document for the full classification rules.

## End-to-End Flow

The full lifecycle when running `/implement <issue-N>`:

```text
flowchart TD
    START([Start]) --> DESIGN_DONE["Prerequisite: /design wrote larch:plan in the issue body"]

    DESIGN_DONE --> IMPL_PHASE

    subgraph IMPL_PHASE["Implementation Phase"]
        CODE[Implement feature] --> VALIDATE1[Validation checks]
        VALIDATE1 --> COMMIT1[First commit]
        COMMIT1 --> CODE_REVIEW[Code review panel]
        CODE_REVIEW --> VOTE2[Voting panel adjudicates findings]
        VOTE2 --> FIX[Implement accepted fixes]
        FIX --> VALIDATE2[Validation checks]
        VALIDATE2 --> COMMIT2[Second commit]
        COMMIT2 --> PR[Create PR]
        PR --> CI_MONITOR[Monitor CI + fix failures (rebase before push)]
    end

    IMPL_PHASE --> MERGE_FLAG{Merge flag set}
    MERGE_FLAG -->|No| POST_ISSUE
    MERGE_FLAG -->|Yes| MERGE_PHASE
    POST_ISSUE[Update tracking issue]

    subgraph MERGE_PHASE["Merge Phase"]
        CI_WAIT[Wait for CI to pass] --> REBASE{Main advanced?}
        REBASE -->|Yes| DO_REBASE[Rebase + push]
        DO_REBASE --> CI_WAIT
        REBASE -->|No| MERGE[Merge PR]
        MERGE --> CLEANUP[Local cleanup]
        CLEANUP --> VERIFY[Verify main]
    end

    POST_ISSUE --> DONE([Complete])
```

## Standalone Usage

Not every task requires the full `/implement` pipeline. Skills can be used independently:

- **`/design [-p|--partition] [--brainstorm] [--per-round-approval] [--skip-approve|-s] <issue-N | feature description>`** — Author or refresh an issue-anchored implementation plan in GitHub (`larch:plan` markers in the issue body per [Issue-anchored plan](issue-anchored-plan.md)). After Round 1 discussion (and optional Step 1d.5 brainstorm), the **Step 1d.7 outline-approval gate** presents a 5-section design outline for operator Approve / Refine / Cancel before launching plan writing; `--skip-approve`/`-s` auto-approves this outline and the Gate C final plan approval without prompting. `/design` uses a single direct-drafting flow: Step 2a prepares sentinels, Step 2b drafts the plan, and Step 3 runs its multi-round plan-review loop via `design-step3-review.sh` (process-group wrapper around `python/cli.py plan-review run --mode loop`), applying accepted findings with `python/cli.py plan revise-waterfall`. Gate B auto-applies accepted findings by default; `--per-round-approval` restores the explicit per-round prompt, and the former `--approve` flag is rejected. Finalize (**Step 5**) includes optional OOS filing (**5b**) before the `larch:plan` write (**5c**) and tmpdir cleanup (**Step 6**). The `[DESIGNED]` prefix is an `/implement` admission signal, not a global "design finished" mutex.
- **Step 3 external-stop recovery** — If the Claude Code harness stops the immediate-background Step 3 wrapper while the detached plan-review loop is still running, the wrapper records `.step3-wrapper-detached` and leaves the loop plus reviewer dispatches alive. The next Step 3 wrapper entry reattaches to the validated loop identity or persisted result env, normalizes the original result, and avoids spending another review round. Normal loop completion and explicit abort cleanup still own full process teardown.
- **Step 5 external-stop recovery** — If a signal-induced Step 5 wrapper stop detaches the review worker, the wrapper records `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`, keeps the worker alive, and withholds a complete Step 5 result env. The next Step 5 wrapper entry reattaches to the recorded identity, normalizes the captured stdout, performs tmpdir-scoped cleanup, and records completion through `bgjob/implement-step5-review.result.env`. Normal completion and explicit abort cleanup still own full process teardown.
- **`/review [--diff] [<description>]`** — Supports `--diff`, which reviews the current branch's changes (implements accepted fixes in a recursive loop), and positional `<description>`, which reviews existing code. Description mode records voting outcomes and OOS artifacts locally; use `/issue` manually when you want GitHub tracking for follow-ups.
- **`/research [--no-issue] <topic>`** — Best-effort read-only-repo investigation with the fixed-shape topology documented in the research skill: a planner pre-pass (always on) decomposes the question into focused subquestions, then Codex-first research lanes by angle fan out, followed by the validation panel. Step 2.5 (citation validation, unconditional) runs between validation and synthesis: a deterministic shell validator extracts cited URLs / DOIs / file:line references, HEAD-fetches URLs under SSRF guards, validates DOIs, spot-checks file:line ranges against the git tree, and writes the PASS / FAIL / UNKNOWN ledger sidecar that Step 3 splices into the final report — fail-soft (the report is never blocked). On a TTY, the planner pauses after subquestion proposal so the operator can review, edit, or abort; on non-TTY, the run continues without prompting. Does not create branches or make commits. The skill-scoped `scripts/deny-edit-write.sh research` PreToolUse hook mechanically guards Claude's `Edit`/`Write`/`NotebookEdit` tool surface only while a fresh `research-*` activation sentinel exists. While active, it permits only paths under canonical `/tmp` or the larch cache sessions root; stale sentinels expire after about 360 minutes, and leaked tokenless registrations stay inactive. **The hook does not cover Bash or external reviewers** (Cursor/Codex launch directly against `$PWD` with full filesystem access — non-modification is prompt-enforced only). See [the canonical research boundary](security/workflow-trust-and-mutations.md#research) for the full residual-risk framing. Step 3.5 auto-archives the full report as a GitHub issue on each successful run (via `/issue` single mode); `--no-issue` skips this step. May also invoke `/issue` via the Skill tool when the research brief calls for filing findings as issues.
- **`/block-issue <ISSUE_A> <ISSUE_B>`** — Express a native GitHub blocked-by relationship between two issues using the `addBlockedBy` GraphQL mutation. Both arguments are plain issue numbers. Auto-detects the repo from `gh repo view`; accepts optional `--repo owner/name` to override. Verifies the relationship was recorded before confirming.
- **`/set-up-forked-open-source-repo --upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]`** — Configure the current checkout for upstream/fork OSS contribution. Verifies the fork and parent, optionally syncs fork branches and tags from upstream after explicit confirmation, rewires local remotes so `origin` is the fork and `upstream` is upstream, disables upstream pushes, and sets `main` to track `origin/main`. Single-clone only; refuses dirty, non-`main`, ahead, diverged, and ambiguous remote states.
- **`/issue [--input-file F] [--title-prefix P] [--label L]... [<desc>]`** — Create one or more GitHub issues with 2-phase LLM-based semantic duplicate detection.
- **`/report-tokens`** — Synchronize and analyze repository-scoped cached token-report JSON for `--skill=design|implement`. It optionally plots trends and posts a skill-prefixed report issue. Observability-only; no tracked run-log writes.
- **`/cleanup`** — Remove stale larch session temp directories from `~/.cache/larch/sessions/`, `/tmp`, and the OS temp root `$TMPDIR` resolves to (a per-user path distinct from `/tmp` on macOS) (`LARCH_CLEANUP_RETENTION_DAYS`, default 7); a directory is deleted only when the bounded `find -maxdepth 5` nested-activity scan finds no file newer than the cutoff — a directory with fresh deep activity (≤ 5 levels) is retained even when its top-level mtime is old. Reaps dangling `current-design-env-*.sh` symlinks. Always runnable; reports removal counts and an informational `SESSION_COUNT`. No git writes, no PRs — filesystem cleanup only.

Shortcut aliases (covered in [Delegation Topology](#delegation-topology)):
- **`/im <args>`** ≡ `/implement --merge <args>`
## Flags

Flags modify behavior across the skill hierarchy:

| Flag | Available on | Effect |
|---|---|---|
| `--no-issue` | `/research` | Skips the Step 3.5 auto-archive that files the full report as a GitHub issue. Default off (issue is filed). |

## Conditional Steps

Certain steps in the workflow depend on configuration prerequisites and are skipped when unavailable:

- **CI monitoring** — Requires repository identification. When unavailable, CI monitoring is skipped.
- **Version bump / release notes** — Not part of `/implement` after Phase 1 (#3364). Use the `/release` skill (Phase 3) when the repo defines versioning; legacy `/release` under `.claude/skills/` remains available for manual or release-driven bumps but is not invoked from the `/implement` ship path.
- **External reviewers (Cursor, Codex)**: Voter, coder, and `/research` research/validation lanes still use waterfall or Claude backfill where documented in [agents.md](agents.md), [review-agents.md](review-agents.md). In `/review`, `/implement` Step 5, and `/design` plan-review **reviewer** panels dispatch with `--no-fallback`: missing or failed vendor rows drop instead of cross-vendor or Claude reviewer backfill; round 2 prunes on round-1 productivity and may converge prune-to-empty under the fixed cap of 2. Code-review voters are separate: when both external tools are unavailable, the code-review voter panel falls back to a single Claude floor voter rather than keeping its three-voter shape (see [review-agents.md](review-agents.md)).

## Run-log lifecycle

Every shipped skill resolves `.larch/config.toml` or `LARCH_LOGS_URI`, validates
the storage root, and performs the provider bucket-root preflight before run
work. Each invocation owns one skill name, run ID, staging tree, durable context,
and terminal publication. Specialized design, implement, and review owners adopt
their rich staging trees into that same lifecycle. Nested and alias calls publish
separate parent-linked archives; nested review is a child of its implement run.

Terminal paths sanitize the final staging tree and publish exactly one
create-only object at `<URI>/run-logs/<skill>/<run-id>.tar.gz`. Success also
requires a validated unpacked cache directory. Failure returns nonzero and
keeps a content-pinned pending archive for retry. No run-log path creates a Git
branch, commit, push, pull request, or merge.

The enforceable owner registry is
`skills/shared/run-lifecycle-ownership.tsv`. Its specialized row replaces the
generic prompt owner for that boundary; the specialized code may stage richer
artifacts but may not invoke a second archive publisher.

Analysis skills synchronize the repository corpus at most once per invocation.
They keep the returned cache path and use ordinary local reads for every later
file and analysis wave. Mutable analyzer state stays in the XDG state tree. See
[Run-log storage contracts](run-log-archive.md) and
[Analyzer state](analysis-state.md).
## Main-health gate and post-merge push watch

`/implement` records `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and `MAIN_HEALTH_DETAIL` during preflight and materializes them into `$IMPLEMENT_TMPDIR/main-health.env`. If Step 2 sees red default-branch CI, `step2-main-health-fix.md` repairs it on the feature branch before dispatch and records `MAIN_HEALTH_REPAIR_*` ownership fields. Step 8 blocks new or different default-branch failures, but may merge when that marker covers the same failed run and base SHA and PR checks pass.

Repository tests or lints that fail and then pass without an authored fix are nondeterminism defects, not harmless transients. They route as `flaky-defect-unfixed` to CI-fix. After merge, the push workflow must be watched for the merged commit SHA; a failure enters `postmerge-repair` and the `postmerge-emergency-repair.md` state machine instead of finalizing success.

## Shared-owner admission and implementation leases

Migration plans that create or reuse a shared launcher, adapter, registry, resolver, client, or state machine include one canonical `larch:owners` block. Preflight validates its sorted rows, safe targets, `REUSE` source receipts, and native blocker edges. It scans open `[IMPLEMENTING]` issues and blocks a duplicate `CREATE` with `active-owner-conflict owner=<key> issue=#N` before lifecycle adoption.

Step 0 creates and reads back the run's `larch:implementation-lease` after the branch exists and before it adds `[IMPLEMENTING]`. Existing marker-keyed tracking-summary boundaries refresh only that run's lease. Terminal cleanup updates the lease and title together, which clears active ownership on done and stalled routes. A report-only watchdog emits `stale-implementation-lease issue=#N age_hours=<N>` after 12 hours only when the recorded branch has no open PR. It prints one cleanup command and never edits GitHub state.

## Migration governance aggregate

`python3 python/cli.py issue migration-audit` composes migration admission,
receipt, blocker, owner, lease, command-registry, retirement, clean-install, and
runtime checks. It captures one immutable GitHub and repository snapshot, then
passes that snapshot to every issue check. It emits JSON and a short count table
without changing GitHub or repository state.

Scheduled automation may archive the JSON and project it into one marker-keyed
Chief issue comment. The workflow owns that write. See
[Migration Governance Audit](migration-governance.md) for the report contract
and failure behavior.

## CI-fix push sequencing

When a required CI run fails, the active Step 8+ driver (`python/cli.py ship pr` delegating to `python/larch/implement/ship.py`) distills the failure to `$IMPLEMENT_TMPDIR/ci-errors-<run-id>.md` and bails to `NEXT_ACTION=ci-fix` without committing a fix. The `/implement` Step 8 ci-fixer subagent (`agents/ci-fixer.md`) reads the digest, commits the repair as `CI fix round <N>: <summary>`, and pushes via `python/cli.py push branch`. The pre-fix rebase gate runs before the round loop, so the subagent pushes onto a current branch and the next `ci-wait` poll should see `BEHIND_COUNT=0`. A compose-time architectural-invariant violation (`NEXT_ACTION=invariants-assessment`) does not use the ci-fixer loop; it re-enters the Step 8 fix ladder (materialize, tier-1 coder fix, fresh-assessor re-judge, tier-2 main agent), and the coder/main-agent fixes commit and push via `python/cli.py push branch`.

The pre-ship checks-repair fallback uses the same subagent in `MODE=checks`. `checks fixer-evidence` materializes a bounded, redacted `$IMPLEMENT_TMPDIR/checks-errors-<site>-<round>.md`; the main agent passes only its path, never reads it, and never edits repository files. A `FIXER_RESULT=committed` repair is committed but not pushed, then re-enters the site-specific checks composite. Ten rounds or an unsuccessful fixer result follow the existing terminal stall route.

## Pre-push Clean-Tree Invariant

Before guarded push wrappers invoked by `/implement` — initial PR creation (`python/cli.py pr create`) and force-push during rebase recovery (`python/cli.py push force`) — the script asserts that `git status --porcelain` is empty. If uncommitted working-tree changes are present, the push aborts with exit 1 and a message listing the dirty paths, so the orchestrator routes to the bail path (Step 12d / Step 18). This prevents silent data loss when inline fixes (e.g., OOS-fold edits) land in the working tree between commit boundaries and would otherwise be excluded from the merged PR.

## Resolution Protocols

Different skills use different protocols for resolving review findings:

| Protocol | Used by | Mechanism |
|---|---|---|
| [Voting](voting-process.md) | `/design`, `/review` (both diff and description modes) | The voting panel votes YES/NO using the thresholds documented in the voting protocol. |
| Negotiation | `/research` | Up to N rounds of back-and-forth with external reviewers. Claude makes the final call. |

See [Voting Process](voting-process.md) for full details on the voting protocol.

## /design teardown reporting

During post-phase final summary, `/design` runs a one-issue report gate before final render and summary upsert. Terminal failures and escalation-success runs use the same shared reporting core as `/implement` with the `design-failure` artifact prefix.

Hard-fail paths stage terminal state before abort when safe. Step 0b clarify hard halts stage `failed-clarify`. Step 3 `postplan-failed` stages state in the script, then prompt-side orchestration runs final-summary routing so KV stdout stays clean. Step 2b.5 decompose-panel retry exhaustion is terminal `failed-judge-panel` and routes through Split-path final-summary orchestration.

Ordinary Step 3 panel degradation continues the run. It may become escalation-success evidence only after an approved outcome. Successful runs without escalation do not file. Operator-action skips are audited in chat and run logs but do not file.

### Difficulty-tiered review loops

Design, review, and implement review loops resolve a starting difficulty tier, apply the 1:30 audit for below-HARD runs, and use a fixed cap of 2 for every tier. Substantial code-review rounds escalate one tier at a time; substantial design-review rounds escalate directly to HARD.

## Bgjob completion artifacts

Long-running migrated steps write completion through `$TMPDIR/bgjob/<step>.result.env`. Existing `.completed/*` and handoff sentinels remain as transition routing compatibility markers, but migrated orchestrator text treats the bgjob result env and `BGJOB_RC=0` as the completion source of truth.

Each start truncates or recreates its merge-input env before invoking `bgjob start --merge-result-env`, so stale KVs from a prior attempt cannot satisfy a fresh wait. `BGJOB_STATUS=WAIT` means the orchestrator repeats the identical `bgjob wait` with no progress probes. `BGJOB_STATUS=DONE` is only a readiness signal until the final stdout and result env contain `BGJOB_RC=0` plus the step's required KVs.

Bgjob diagnostics live beside the result env under `$TMPDIR/bgjob/`: daemon stdout and stderr logs, registry rows, and copied result KVs. Run-log capture records the published summaries after those diagnostics and result envs have driven routing. Step 8 is the narrow exception to the generic success gate: `ship route-exit` follows the current `.step-8-ship-handoff.rc` and `.step-8-ship-handoff.json` sidecars, so a numeric driver rc is route data rather than generic bgjob failure. Timeout or orphaned bgjob results still block routing.

Concurrent external lanes use unique `--step` slugs, for example per-reviewer or per-research-lane names. Shared slugs would clobber registry rows, daemon logs, and `$TMPDIR/bgjob/<step>.result.env`.

### #6516 sentinel disposition record

This committed record is the operator-directed substitute for editing already-merged PR #6706. It satisfies #6516's audit intent without changing that PR description.

| Sentinel | Decision | Evidence |
|---|---|---|
| design `.completed/step-3-terminal` | DELETE | zero refs outside `larch-logs/`; Step 3 routes on `bgjob/design-step3-review.result.env` |
| `.completed/step-4` | KEEP | boundary-local compatibility sentinel per `skills/design/references/sentinel-host-table.md`; consumers: `python/larch/design/design_step3b.py` diagram gate, `plan_review_loop.py` downstream clear |
| `.completed/step-5c-terminal` | DELETE | zero refs; Step 6 uses `bgjob/design-step5c.result.env` plus registry liveness |
| `.completed/step-final-summary` | DELETE | zero refs |
| implement `.completed/step-3-terminal` | DELETE | zero refs |
| `.completed/step-5-terminal` | DELETE | zero refs |
| `.completed/step-5-resume-terminal` | DELETE | zero refs |
| `.completed/step-5-self-review-terminal` | DELETE | zero refs |
| `.completed/step-6-terminal` | DELETE | zero refs |
| `.completed/step-7a-terminal` | DELETE | zero refs |
| `.step3-terminal-persisted-this-run` | DELETE | zero refs |
| `.step-8-ship-handoff.rc` | KEEP | route-exit consumer `python/larch/implement/dispatch_ship.py`; plan carve-out keeps the driver rc in the sidecar |
### Plan-coverage scope disposition

`/implement` compares the live work against the Step 0 materialized plan at `$IMPLEMENT_TMPDIR/plan.txt`. It counts firm `### NEW:`, `### UPDATED:`, and `### REWRITTEN:` paths. It excludes `### MAY_UPDATE:`.

Bands:

- `advisory`: below the middle thresholds. The run may continue with warning KVs.
- `middle`: at least 20 percent untouched or at least 10 untouched firm paths. Step 5 gets a forced plan-fidelity reviewer with `prune_exempt=true`.
- `high`: at least 50 percent untouched or at least 30 untouched firm paths. Ship and direct PR mutation require a recorded scope disposition.

Non-empty implementer `todos_left` also requires disposition, even when file coverage is complete.

On external `STATUS=complete`, the dispatcher computes coverage first, but the prompt runs only after `step-2-post-dispatch.sh` emits `POST_DISPATCH_NEXT=continue`. Main-agent fallback and recovery paths compute coverage after main-agent edits and before Step 3.

The operator choices are:

- `proceed-partial`: file a follow-up issue, cross-link it, mark the tracking issue blocked by that follow-up, then record the disposition.
- `bail-rescope`: record the disposition and route to the Step 12d rescope path.

The coverage fingerprint covers plan paths, touched paths, and bounded `todos_left`. Step 5 commits, Step 7 commits, checks repair, ship pre-driver, and PR mutation recompute coverage. If the fingerprint changes, the old disposition is stale and the operator must choose again. Ship route-exit maps this to `halt-scope-disposition`.

Partial scope changes completion surfaces. The PR footer uses `Part of #N` instead of a closing keyword, the PR body includes a bounded deferred inventory, `[DONE]` rename is suppressed, and the final summary includes plan coverage and `todos_left` count.
