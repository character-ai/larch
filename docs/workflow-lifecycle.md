# Workflow Lifecycle
How skills compose to form the end-to-end development workflow in Larch.

## Skill Orchestration Hierarchy

Skills are not invoked in a flat sequence. They form a hierarchical call graph where higher-level **stateful orchestrators** invoke lower-level skills and continue execution based on their side effects. The diagram below shows true orchestrators and their direct sub-skills; pure forwarders (`/im`, `/block-issue`) are covered separately in the [Delegation Topology](#delegation-topology) subsection because they run no post-delegation logic. `/alias` is a hybrid (validate → delegate → verify) — it also appears in the Delegation Topology subsection.

```text
graph TD
    DESIGN["/design"]
    DESIGN -.->|issue-body larch:plan| IMPLEMENT["/implement"]
    IMPLEMENT -->|runs helper for| STEP5["review-and-fix step5"]
    IMPLEMENT -->|runs helper for| CHECKS["project relevant-checks script"]
    IMPLEMENT -->|invokes| ISSUE_OOS["/issue (OOS filing)"]
```

- **`/implement`** — top-level orchestrator. Runs the full design → code → review → PR workflow by default; Step 2 supplies valid `ARCHITECTURAL_INVARIANTS.md` before valid `ARCHITECTURAL_GUIDELINES.md` to external coders as untrusted, plan-scoped evidence and requires a manifest acknowledgment when knowledge was present. Step 5 invokes `review-and-fix step5`, which uses a fixed round cap of **2** rounds (hard ceiling), does **not** forward `--panel` on the public argv, and applies the panel only inside `review-and-fix CLI` → `review core` (see [Review Agents](review-agents.md) Note A for the **review panel**, **specialists per vendor**, round 2 pruned on round-1 productivity, no generic Codex row, and `--no-fallback` reviewer-dispatch contract). Review prompts receive the same valid architecture files as untrusted documented policy: `I-*` violations are blocking when concrete and in scope, while `G-*` violations are fix-required when a safe proportional fix exists. Step 8 compose-time gates check invariants before guidelines; invariant violations route through the CI-fix style remediation loop, while guideline deviations remain warning-backed. With the `--merge` flag, also runs the CI+rebase+merge loop and local cleanup after PR creation. Preflight runs `python/cli.py admission gate` before Step 0; Step 0 resolves tracking-issue state (sentinel reuse, positional issue adoption, or `Closes #<N>` recovery from the current branch's PR body) and materializes the plan from the issue body. **Phase 1 (#3364):** `/implement` does not invoke `/release` or write `release notes` on the ship path — versioning and release notes updates move to the operator-run `/release` skill (Phase 3). Committed larch-log batches remain the single source of truth for full report content (voting tallies, rejected findings, diagrams, OOS observation links, execution issues, run statistics), with the PR body as a slim projection (Summary + diagrams + Test plan + `Closes #<N>` — diagrams appear in both places by design). Step 9a.1 additionally invokes `/issue` in batch mode to file accepted OOS findings as GitHub issues.

## Delegation Topology

Pure forwarders are **not** orchestrators — they validate input (when applicable), call the Skill tool exactly once, and exit. They run no logic after the child returns. This subsection also documents `/alias`, which is a hybrid: it validates, delegates to `/implement`, and then performs a mechanical sentinel-file verification (see `/alias` Step 4). Edges are labeled with the **arguments passed on that edge** (what the immediate child receives), not the final expansion — for single-hop delegation (`/im`, `/alias`) this is also what `/implement` sees.

```text
graph LR
    IM["/im"] -->|merge args| IMPLEMENT["/implement"]
    ALIAS["/alias"] -->|args| IMPLEMENT
```

- **`/im`** — prepends `--merge` to `$ARGUMENTS` and forwards to `/implement`. Equivalent to `/implement --merge <tail>` where `<tail>` is the forwarded argv (positional `<issue-N>` for PR-shaped flows).
- **`/alias`** — hybrid: validates alias name, delegates to `/implement` (and any preset flags) to scaffold a new alias skill, then performs a sentinel-file verification (Step 4) that the expected `SKILL.md` was actually written. Auto-resolves the target directory: inside a Claude plugin source repo (two-file predicate `.claude-plugin/plugin.json` + `skills/implement/SKILL.md` at the git repo root) the alias goes under `skills/<n>/`; anywhere else, under `.claude/skills/<n>/`. Accepts optional `--merge` to merge the alias-creation PR and `--private` to force `.claude/skills/<n>/` even in a plugin repo (no-op in non-plugin repos).
- **`/block-issue`** — pure delegator. Accepts two issue numbers (`ISSUE_A ISSUE_B`), resolves their GitHub GraphQL node IDs, calls the native `addBlockedBy` mutation, and verifies the dependency was recorded. Thin wrapper around `python/cli.py block-issue add-blocked-by`. No sub-skill delegation.

Pure forwarders (`/im`, `/block-issue`) are exempt from the post-invocation-verification and anti-halt-continuation rules defined in `skills/shared/subskill-invocation.md`. `/alias` is NOT exempt — it carries both the post-invocation sentinel check and the anti-halt banner/micro-reminder. See that document for the full classification rules.

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
- **Step 5 external-stop recovery** — If a signal-induced Step 5 wrapper stop detaches the review worker, the wrapper records `$IMPLEMENT_TMPDIR/.step5-wrapper-detached`, keeps the worker alive, and withholds `.completed/step-5-terminal`. The next Step 5 wrapper entry reattaches to the recorded identity, normalizes the captured stdout, performs tmpdir-scoped cleanup, and writes `.completed/step-5-terminal`. Normal completion and explicit abort cleanup still own full process teardown.
- **`/review [--diff] [<description>]`** — Supports `--diff`, which reviews the current branch's changes (implements accepted fixes in a recursive loop), and positional `<description>`, which reviews existing code. Description mode records voting outcomes and OOS artifacts locally; use `/issue` manually when you want GitHub tracking for follow-ups.
- **`/research [--no-issue] <topic>`** — Best-effort read-only-repo investigation with the fixed-shape topology documented in the research skill: a planner pre-pass (always on) decomposes the question into focused subquestions, then Codex-first research lanes by angle fan out, followed by the validation panel. Step 2.5 (citation validation, unconditional) runs between validation and synthesis: a deterministic shell validator extracts cited URLs / DOIs / file:line references, HEAD-fetches URLs under SSRF guards, validates DOIs, spot-checks file:line ranges against the git tree, and writes the PASS / FAIL / UNKNOWN ledger sidecar that Step 3 splices into the final report — fail-soft (the report is never blocked). On a TTY, the planner pauses after subquestion proposal so the operator can review, edit, or abort; on non-TTY, the run continues without prompting. Does not create branches or make commits. The skill-scoped `scripts/deny-edit-write.sh research` PreToolUse hook mechanically guards Claude's `Edit`/`Write`/`NotebookEdit` tool surface only while a fresh `research-*` activation sentinel exists. While active, it permits only paths under canonical `/tmp`; stale sentinels expire after about 360 minutes, and leaked tokenless registrations stay inactive. **The hook does not cover Bash or external reviewers** (Cursor/Codex launch directly against `$PWD` with full filesystem access — non-modification is prompt-enforced only). See [`SECURITY.md` § External reviewer write surface in /research](../SECURITY.md#external-reviewer-write-surface-in-research) for the full residual-risk framing. Step 3.5 auto-archives the full report as a GitHub issue on each successful run (via `/issue` single mode); `--no-issue` skips this step. May also invoke `/issue` via the Skill tool when the research brief calls for filing findings as issues.
- **`/block-issue <ISSUE_A> <ISSUE_B>`** — Express a native GitHub blocked-by relationship between two issues using the `addBlockedBy` GraphQL mutation. Both arguments are plain issue numbers. Auto-detects the repo from `gh repo view`; accepts optional `--repo owner/name` to override. Verifies the relationship was recorded before confirming.
- **`/set-up-forked-open-source-repo --upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]`** — Configure the current checkout for upstream/fork OSS contribution. Verifies the fork and parent, optionally syncs fork branches and tags from upstream after explicit confirmation, rewires local remotes so `origin` is the fork and `upstream` is upstream, disables upstream pushes, and sets `main` to track `origin/main`. Single-clone only; refuses dirty, non-`main`, ahead, diverged, and ambiguous remote states.
- **`/issue [--input-file F] [--title-prefix P] [--label L]... [<desc>]`** — Create one or more GitHub issues with 2-phase LLM-based semantic duplicate detection.
- **`/report-tokens`** — Analyze committed `larch-logs/<skill>/*/` token-report JSON for `--skill=design|implement`. Prices runs through `python/larch/report/report_tokens_cost.py`, writes a durable `Cache JSON:` NDJSON snapshot, optionally plots trends, and optionally posts a skill-prefixed report issue. Both skills use one aggregate graph/table set. Observability-only; no repo writes except the optional GitHub issue.
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
## Main-health gate and post-merge push watch

`/implement` records `MAIN_CI_STATUS`, `MAIN_FAILED_RUN_ID`, `MAIN_HEALTH_HEAD_SHA`, and `MAIN_HEALTH_DETAIL` during preflight and materializes them into `$IMPLEMENT_TMPDIR/main-health.env`. If Step 2 sees red default-branch CI, `step2-main-health-fix.md` repairs it on the feature branch before dispatch and records `MAIN_HEALTH_REPAIR_*` ownership fields. Step 8 blocks new or different default-branch failures, but may merge when that marker covers the same failed run and base SHA and PR checks pass.

Repository tests or lints that fail and then pass without an authored fix are nondeterminism defects, not harmless transients. They route as `flaky-defect-unfixed` to CI-fix. After merge, the push workflow must be watched for the merged commit SHA; a failure enters `postmerge-repair` and the `postmerge-emergency-repair.md` state machine instead of finalizing success.

## CI-fix push sequencing

When the active Step 8+ driver (`python/cli.py ship pr` delegating to `python/ship.py`) commits a CI-fix locally, it checks staleness via `python/cli.py ci behind-count` (shared with `python/cli.py ci status`) before pushing. If the branch is behind `origin/main` (or `upstream/main` on forked targets), it reuses `run_rebase_rebump` with deferred push, re-verifies failed jobs and lint on the rebased tree, then pushes with `python/cli.py push force` (force-with-lease). When already current, it uses plain `python/cli.py push branch`. The next `ci-wait` poll should see `BEHIND_COUNT=0`, so the separate `ACTION=rebase` path remains a no-op fallback rather than a second rebase.

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

Long-running migrated steps write completion through `$TMPDIR/bgjob/<step>.result.env`. Existing `.completed/*` and handoff sentinels remain as transition routing compatibility markers, but migrated orchestrator text should treat the bgjob result env and `BGJOB_RC=0` as the completion source of truth.
