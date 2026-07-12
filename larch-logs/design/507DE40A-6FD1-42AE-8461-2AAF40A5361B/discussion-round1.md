# Discussion Round 1 — /triage (#7080)

## Decision 1: Issue update mechanism
- **Question**: How should /triage write its verdict back to the issue?
- **Resolution**: **Rewrite the issue body** into a single unified, coherent design-ready spec (corrected root cause, evidence, scope split, fix outline). The original report is folded in/superseded so the body reads cleanly to subsequent /design, not appended as a marked section or left as a comment.
- **Source**: user (operator override of the issue's "append, don't rewrite" lean)

## Decision 2: blocked-by dependency edges
- **Question**: Apply or only recommend blocked-by edges?
- **Resolution**: **Apply near-certain** blocked-by edges directly via the existing /issue (or /larch:block-issue) machinery; recommend but do not apply uncertain edges in the write-up.
- **Source**: user

## Decision 3: Reproduction safety boundary
- **Question**: What repro safety boundary should /triage enforce?
- **Resolution**: **Read-only / idempotent probes only** (e.g. codex model one-liner, `git fetch`/`git show`, grep/Read). Never mutate repo state, never run destructive or externally-mutating commands. This is a hard constraint and a SECURITY.md rule.
- **Source**: user

## Hard constraints (from contract + codebase)
- **Never edit code.** Never author a plan (that stays in /design). File follow-up issues only through /issue.
- **Wrap all issue body/comment content as untrusted** (same convention as /issue Phase 2).
- **Distinguish observation from inference** in the write-up.
- **Say so when evidence is missing** (e.g. unflushed run log) instead of guessing.
- **Cross-repo** via `--repo OWNER/REPO` using standard `gh`.
- **Title handling**: leave the title alone on the valid/design-ready path (let /design do its own `[DESIGNING]` rename); restore the title only on close when a lifecycle rename is present.

## Non-goals
- /triage does NOT replace /design's own verify-first behavior; it is a standalone pre-/design front-load.
- /triage does NOT implement fixes or author plans.
- /triage does NOT replace /bug (files new bug issues) or /research (read-only research, no issue mutation).

## Scope boundary
- Verdicts: `valid` (root cause confirmed or corrected → design-ready), `already-fixed` / `non-material` / `invalid` (verify-comment + close NOT_PLANNED + restore title), `duplicate` (comment canonical + close). `invalid` folds into the non-material/not-planned branch.
