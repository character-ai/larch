# Workflow Lifecycle

How skills compose to form the end-to-end development workflow in Larch.

## Skill Orchestration Hierarchy

Skills are not invoked in a flat sequence. They form a hierarchical call graph where higher-level **stateful orchestrators** invoke lower-level skills and continue execution based on their side effects. The diagram below shows true orchestrators and their direct sub-skills; pure forwarders (`/im`, `/block-issue`) are covered separately in the [Delegation Topology](#delegation-topology) subsection because they run no post-delegation logic. `/alias` is a hybrid (validate → delegate → verify) — it also appears in the Delegation Topology subsection.

```text
graph TD
    DESIGN["/design"]
    DESIGN -.->|issue-body larch:plan| IMPLEMENT["/implement"]
    IMPLEMENT -->|runs helper for| STEP5["run-step5-review.sh"]
    IMPLEMENT -->|runs helper for| CHECKS["project relevant-checks script"]
    IMPLEMENT -->|invokes| BUMP["/bump-version"]
    IMPLEMENT -->|invokes| ISSUE_OOS["/issue (OOS filing)"]
```

- **`/implement`** — top-level orchestrator. Runs the full design → code → review → PR workflow by default; Step 5 invokes `run-step5-review.sh`, which derives `effective_round_cap` from base cap **5** plus degraded-round inflation, does **not** forward `--panel` on the public argv, and applies the panel only inside `review-and-fix.sh` → `review-core.sh` (see [Review Agents](review-agents.md) Note A for the **3-judge panel on every round**, **review panel**, and **6 Cursor specialists** contract). With the `--merge` flag, also runs the CI+rebase+merge loop and local cleanup after PR creation. Preflight runs `scripts/implement-admission.sh` before Step 0; Step 0 resolves tracking-issue state (sentinel reuse, positional issue adoption, or `Closes #<N>` recovery from the current branch's PR body) and materializes the plan from the issue body. Committed larch-log batches are the single source of truth for full report content (voting tallies, rejected findings, version-bump reasoning, diagrams, OOS observation links, execution issues, run statistics), with the PR body as a slim projection (Summary + diagrams + Test plan + `Closes #<N>` — diagrams appear in both places by design). Step 9a.1 additionally invokes `/issue` in batch mode to file accepted OOS findings as GitHub issues.

## Delegation Topology

Pure forwarders are **not** orchestrators — they validate input (when applicable), call the Skill tool exactly once, and exit. They run no logic after the child returns. This subsection also documents `/alias`, which is a hybrid: it validates, delegates to `/implement`, and then performs a mechanical sentinel-file verification (see `/alias` Step 4). Edges are labeled with the **arguments passed on that edge** (what the immediate child receives), not the final expansion — for single-hop delegation (`/im`, `/alias`) this is also what `/implement` sees.

```text
graph LR
    IM["/im"] -->|merge args| IMPLEMENT["/implement"]
    ALIAS["/alias"] -->|args| IMPLEMENT
```

- **`/im`** — prepends `--merge` to `$ARGUMENTS` and forwards to `/implement`. Equivalent to `/implement --merge <tail>` where `<tail>` is the forwarded argv (positional `<issue-N>` for PR-shaped flows).
- **`/alias`** — hybrid: validates alias name, delegates to `/implement` (and any preset flags) to scaffold a new alias skill, then performs a sentinel-file verification (Step 4) that the expected `SKILL.md` was actually written. Auto-resolves the target directory: inside a Claude plugin source repo (two-file predicate `.claude-plugin/plugin.json` + `skills/implement/SKILL.md` at the git repo root) the alias goes under `skills/<n>/`; anywhere else, under `.claude/skills/<n>/`. Accepts optional `--merge` to merge the alias-creation PR and `--private` to force `.claude/skills/<n>/` even in a plugin repo (no-op in non-plugin repos).
- **`/block-issue`** — pure delegator. Accepts two issue numbers (`ISSUE_A ISSUE_B`), resolves their GitHub GraphQL node IDs, calls the native `addBlockedBy` mutation, and verifies the dependency was recorded. Thin wrapper around `skills/block-issue/scripts/add-blocked-by.sh`. No sub-skill delegation.

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
        COMMIT2 --> VERSION[Version bump]
        VERSION --> PR[Create PR]
        PR --> CI_MONITOR[Monitor CI + fix failures]
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

- **`/design [--trivial|--simple|--hard] [-p|--partition] [--brainstorm] [--manual|-m] <issue-N | feature description>`** — Author or refresh an issue-anchored implementation plan in GitHub (`larch:plan` markers in the issue body per [Issue-anchored plan](issue-anchored-plan.md)). After Round 1 discussion (and optional Step 1d.5 brainstorm), the **Step 1d.7 outline-approval gate** presents a 5-section design outline (Goals / Non-goals / Approach sketch / Surfaces in scope / Open questions) for operator Approve / Refine / Cancel before launching sketches + plan. SIMPLE uses 0 sketches but still runs full plan review; HARD runs 4 sketches plus dialectic and the same full review. `--manual` / `-m` restores the Gate B review prompt; by default Gate B auto-applies accepted findings before final approval. Finalize (**Step 5**) includes optional OOS filing (**5b**) before the `larch:plan` write (**5c**) and tmpdir cleanup (**Step 6**).
- **`/review [--diff] [<description>]`** — Supports `--diff`, which reviews the current branch's changes (implements accepted fixes in a recursive loop), and positional `<description>`, which reviews existing code. Description mode records voting outcomes and OOS artifacts locally; use `/issue` manually when you want GitHub tracking for follow-ups.
- **`/research [--no-issue] <topic>`** — Best-effort read-only-repo investigation with the fixed-shape topology documented in the research skill: a planner pre-pass (always on) decomposes the question into focused subquestions, then Codex-first research lanes by angle fan out, followed by the validation panel. Step 2.5 (citation validation, unconditional) runs between validation and synthesis: a deterministic shell validator extracts cited URLs / DOIs / file:line references, HEAD-fetches URLs under SSRF guards, validates DOIs, spot-checks file:line ranges against the git tree, and writes the PASS / FAIL / UNKNOWN ledger sidecar that Step 3 splices into the final report — fail-soft (the report is never blocked). On a TTY, the planner pauses after subquestion proposal so the operator can review, edit, or abort; on non-TTY, the run continues without prompting. Does not create branches or make commits. The skill-scoped `scripts/deny-edit-write.sh` PreToolUse hook mechanically guards Claude's `Edit`/`Write`/`NotebookEdit` tool surface, permitting only paths under canonical `/tmp`; **the hook does not cover Bash or external reviewers** (Cursor/Codex launch directly against `$PWD` with full filesystem access — non-modification is prompt-enforced only). See [`SECURITY.md` § External reviewer write surface in /research](../SECURITY.md#external-reviewer-write-surface-in-research) for the full residual-risk framing. Step 3.5 auto-archives the full report as a GitHub issue on each successful run (via `/issue` single mode); `--no-issue` skips this step. May also invoke `/issue` via the Skill tool when the research brief calls for filing findings as issues.
- **`/block-issue <ISSUE_A> <ISSUE_B>`** — Express a native GitHub blocked-by relationship between two issues using the `addBlockedBy` GraphQL mutation. Both arguments are plain issue numbers. Auto-detects the repo from `gh repo view`; accepts optional `--repo owner/name` to override. Verifies the relationship was recorded before confirming.
- **`/set-up-forked-open-source-repo --upstream <owner/repo> --fork <owner/repo> [--mirror-confirmed] [--init-submodules]`** — Configure the current checkout for upstream/fork OSS contribution. Verifies the fork and parent, optionally syncs fork branches and tags from upstream after explicit confirmation, rewires local remotes so `origin` is the fork and `upstream` is upstream, disables upstream pushes, and sets `main` to track `origin/main`. Single-clone only; refuses dirty, non-`main`, ahead, diverged, and ambiguous remote states.
- **`/issue [--input-file F] [--title-prefix P] [--label L]... [<desc>]`** — Create one or more GitHub issues with 2-phase LLM-based semantic duplicate detection.
- **`/report-tokens`** — Analyze closed GitHub issues in the current larch repo that contain structured token-report comments. Fetches matching issues with `gh`, caches raw issue JSON under a temp directory, estimates Claude/Codex/Cursor costs from grand-total rows, plots SIMPLE and HARD cost trends, and prints the top SIMPLE costs, HARD phase breakdown, cache-read dominance, and cost-reduction suggestions. Observability-only; no repo writes.
- **`/cleanup`** — Remove leftover larch session temp directories from `~/.cache/larch/sessions/` and `/tmp`. Runs a singleton guard at startup: aborts if more than one `claude` process is detected, and skips cache dirs with an active `.larch-keepalive` sentinel. Reports counts removed from each location. No git writes, no PRs — filesystem cleanup only.

Shortcut aliases (covered in [Delegation Topology](#delegation-topology)):
- **`/im <args>`** ≡ `/implement --merge <args>`
## Flags

Flags modify behavior across the skill hierarchy:

| Flag | Available on | Effect |
|---|---|---|
| `--manual` / `-m` | `/design` | Restores Gate B manual review prompts; default Gate B mode auto-applies accepted findings. |
| `--no-issue` | `/research` | Skips the Step 3.5 auto-archive that files the full report as a GitHub issue. Default off (issue is filed). |

## Conditional Steps

Certain steps in the workflow depend on configuration prerequisites and are skipped when unavailable:

- **CI monitoring** — Requires repository identification. When unavailable, CI monitoring is skipped.
- **Version bump** — Requires a `/bump-version` skill defined in the repo. When absent, the version bump step is skipped with a warning.
- **External reviewers (Cursor, Codex)** — When unavailable, Claude Code Reviewer subagent fallbacks replace them so the per-skill lane/voter shapes remain constant in most phases (see [agents.md](agents.md), [review-agents.md](review-agents.md), and [collaborative-sketches.md](collaborative-sketches.md)). In `/review`, all slots go through a three-phase waterfall: Phase 1 uses the primary tool (Cursor or Codex); Phase 2 tries the alternate external tool when Phase 1 fails or is absent; Phase 3 launches a Claude subprocess for any slot still unresolved. This means the panel always produces output — when both external tools are absent, all specialist slots fall through to Phase 3 Claude reviewers (see [review-agents.md](review-agents.md)). The review still lands regardless of external tool availability.
- **Dialectic debate buckets (`/design` Step 2a.5)** — Unlike the phases above, the dialectic **debate** phase does NOT replace an unavailable tool with a Claude subagent. When the assigned external tool (Cursor for odd-indexed decisions, Codex for even) is unavailable, the bucket is **skipped entirely** and a `Disposition: bucket-skipped` resolution is written (the synthesis decision stands for that point). This carve-out applies to debate execution only — the post-debate **judge panel** uses replacement-first normally. See [External Reviewers](external-reviewers.md#dialectic-specific-behavior) and `skills/shared/dialectic-protocol.md` for details.

## Pre-push Clean-Tree Invariant

Before guarded push wrappers invoked by `/implement` — initial PR creation (`scripts/create-pr.sh`) and force-push during rebase recovery (`scripts/git-force-push.sh`) — the script asserts that `git status --porcelain` is empty. If uncommitted working-tree changes are present, the push aborts with exit 1 and a message listing the dirty paths, so the orchestrator routes to the bail path (Step 12d / Step 18). This prevents silent data loss when inline fixes (e.g., OOS-fold edits) land in the working tree between commit boundaries and would otherwise be excluded from the merged PR.

## Resolution Protocols

Different skills use different protocols for resolving review findings:

| Protocol | Used by | Mechanism |
|---|---|---|
| [Voting](voting-process.md) | `/design`, `/review` (both diff and description modes) | The voting panel votes YES/NO/EXONERATE using the thresholds documented in the voting protocol. |
| Negotiation | `/research` | Up to N rounds of back-and-forth with external reviewers. Claude makes the final call. |

See [Voting Process](voting-process.md) for full details on the voting protocol.
