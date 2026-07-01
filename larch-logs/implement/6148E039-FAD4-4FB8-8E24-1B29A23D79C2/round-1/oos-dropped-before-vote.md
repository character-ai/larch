### OOS_1: [OUT_OF_SCOPE] Plan fidelity and compression metrics verified (correctness checklist)
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Correctness reviewer confirmed in-scope diff scope (`0277feef6`), run-log policy for `9d9002cdc`, `discussion-rounds.md` byte/word reduction (~16.7% / ~18.1%) meeting the ~15% target, design-closure baseline token/line deltas, unchanged `/implement` closure metrics, preserved line-3 `readability-style.md`.**` anchor, step anchors, Q&A schemas, settle-dispatch adjacency, operator breadcrumbs, sprawl labels, prohibited substrings, Step 1c topic/batching/sprawl behavior, Step 1d sequential walk vs 1c batching with branch-count short-circuit and 7-call cap, Round 2 gates/cap/terse-answer rules, and plan-revision/settle/dialectic-clearing order—with no behavior-bearing semantic inversions reported in the reviewed compression edits.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Operator-visible discussion breadcrumbs not harness-pinned
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` does not pin operator-visible discussion breadcrumbs and sprawl option labels. A future prose-compression edit could reword strings like `⏩ 1d: discussion r1 — no scope decisions require discussion (<elapsed>)` and still pass CI, changing live `/design` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add optional contains assertions for the six verbatim operator-visible strings if mechanical protection is desired.

### OOS_3: [OUT_OF_SCOPE] `accepted-plan-findings.md` provenance cross-ref removed at line 88
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-discussion-contract
- **Severity**: nit
- **Concern**: Compression removed the accepted-plan-findings cross-ref to `plan-review.md` overwrite/OOS semantics while keeping the non-empty gate. On rare Gate A re-entry without fresh Step 3 context an orchestrator might treat stale `accepted-plan-findings` as authoritative. The non-empty gate remains; overwrite behavior still lives in `plan-review.md` inside the `/design` closure—this is documentation/provenance loss only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Restore the plan-review.md pointer only if that re-entry path is realistic in production.

### OOS_4: [OUT_OF_SCOPE] Aggregate closure ratchet does not isolate `discussion-rounds.md`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Token ratchet in `python/skill-closure-baseline.json` tracks aggregate `/design` closure, not `discussion-rounds.md` in isolation. Edits elsewhere in the design closure could mask future growth in this always-loaded reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider a per-file token ceiling lint if tighter isolation becomes a priority; current aggregate ratchet matches the plan.

### OOS_5: [OUT_OF_SCOPE] Branch includes out-of-plan `larch-logs` changes
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-discussion-contract
- **Severity**: important
- **Concern**: The branch has seven changed paths vs `origin/main`, but the scoped review diff covers only `discussion-rounds.md` and `python/skill-closure-baseline.json`. Commit `9d9002cdc` adds `larch-logs/design/6148E039-…/` artifacts. The plan acceptance criterion “No non-scope files changed” is not met on the full branch, even if the prose compression itself stays in scope. Run-log policy treats the flush as out of feature scope, not reviewed as a defect.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Plan-revision trailer rationale text trimmed
- **Reviewer(s)**: dyn-dyn-discussion-contract
- **Severity**: nit
- **Concern**: At `skills/design/references/discussion-rounds.md:113`, the plan-revision block still mandates trailer snapshot/settle commands, but no longer states why trailers must be preserved (“so accepted mechanical/deletion-heavy estimates do not collapse back to legacy total-churn-only gating”) or cross-references `approval-gates.md` / `SKILL.md` Step 1e. Mechanical commands remain and `approval-gates.md` still documents the guard—likely acceptable density trimming.
- **Suggested revisions (informational for voters; coder decides)**:

