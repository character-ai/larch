## Decision 1: Rebase placement inside step-7a.sh
- **Question**: Where should `rebase-checkpoint-probe.sh 7a.r` be invoked relative to step-7a.sh?
- **Resolution**: Inside step-7a.sh as part of its body. step-7a.sh runs (in order): token/timing marks → small/non-runtime check → generate-code-flow-diagram.sh → compose summary-diagrams.md → tracking-issue-summary.sh upsert (larch:diagrams) → rebase-checkpoint-probe.sh 7a.r → flush-execution-issues.sh → token-report.sh + timing-report.sh + multiple larch-log.sh write → capture-session-transcript.sh → flush-execution-issues.sh post-transcript → larch-log.sh commit. SKILL.md Step 7a body collapses to ONE foreground Bash call invoking step-7a.sh. This preserves today's diagram→comment→rebase→flush execution order exactly. Issue OOS section explicitly permits this ("step-7a.sh can call rebase-checkpoint-probe.sh cleanly rather than inlining the rebase+probe logic").
- **Source**: user

## Decision 2: larch:diagrams comment-skip rule
- **Question**: When should step-7a.sh skip the `larch:diagrams` summary comment upsert?
- **Resolution**: Mirror current SKILL.md byte-for-byte. Today's behavior: comment is always posted (with placeholder text for missing diagrams) regardless of generate-code-flow-diagram.sh exit; ONLY skipped when the Mermaid sanitizer rejects the code-flow content. The ISSUE_NUMBER empty-gate is preserved as today (`[ -n "$ISSUE_NUMBER" ]`). Do not add new skip rules; do not tighten current behavior.
- **Source**: user

## Decision 3: Scope of pre-bump flush batches absorbed
- **Question**: The issue's Goal lists 4 batches (token-report, timing-report, execution-issues, session-transcript). Does step-7a.sh handle all current pre-bump flush batches (~10) or only those 4?
- **Resolution**: Mirror current SKILL.md byte-for-byte. step-7a.sh's flush phase absorbs ALL larch-log batches currently flushed at this checkpoint: token-report, timing-report, parent-issue, pre-review-head, pre-review-untracked, codex-impl-transcript (+meta+prompt), codex-commit-message, codex-impl-manifest-raw, session-transcript, plus execution-issues flushes (pre- and post-transcript). The 4 batches in the issue Goal are illustrative of the most prominent items, not an exhaustive whitelist. The acceptance "byte-identical output" requires preserving the full batch set.
- **Source**: codebase (skills/implement/SKILL.md "Pre-bump log flush" subsection lines 1457-1529)

## Decision 4: Hard constraints to preserve verbatim
- **Question**: What hard constraints must the implementation preserve?
- **Resolution**:
  - `larch:diagrams` summary comment content is byte-identical to current SKILL.md output (acceptance criterion).
  - lib-quiet.sh `emit_kv`/`emit` contract on FD 3 for machine output; no stdout pollution.
  - Bash 3.2 portability (no `declare -A`, `mapfile`, `&>>`, `${var^^}`, etc.).
  - Foreground markers: step-7a.sh added to `scripts/lint-foreground-markers.sh` DENYLIST; SKILL.md fence above the invocation block carries the §4 banner + per-anchor comment.
  - Sibling `.md` for both `step-7a.sh` and `test-step-7a.sh` (`.claude/rules/script-md-siblings.md`).
  - `make lint` must pass (lint-bash32, script-md-siblings, lint-foreground-markers, lint-skill-invocations, S030 path pins).
- **Source**: issue body + codebase rules (.claude/rules/*.md, BASH_AUTHORING.md)

## Decision 5: Non-goals
- **Question**: What is explicitly out of scope?
- **Resolution**:
  - Step 0 consolidation (issue #2732 family).
  - Rebase Macro 7a.r + post-rebase phantom probe CONSOLIDATION (companion issue produces `rebase-checkpoint-probe.sh`; this issue is blocked-by it). step-7a.sh CALLS rebase-checkpoint-probe.sh but does NOT re-implement rebase+probe logic.
  - ship-pr argv consolidation (items 9-10 in the issue's enumeration; separate companion issue).
  - Adding new larch-log batch slugs not already present at the pre-bump checkpoint.
  - Changing the small/non-runtime detector classifier (CHANGED_COUNT ≤ 2 AND all paths in `docs/` or `CHANGELOG*` or `.txt`/`.tsv`).
- **Source**: issue body (Scope section)
