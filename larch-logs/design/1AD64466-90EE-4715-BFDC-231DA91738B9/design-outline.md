## Proposed Design Outline

### Goals
- Remove or demote vestigial MANDATORY file loads from the `/implement` happy path.
- Inline the one-sentence interactive predicate so `external-reviewers.md` is not loaded at runtime.
- Eliminate dead prose (empty section body, dangling telemetry sentences, overlong removed-NEVER stub).

### Non-goals
- Change any runtime behavior of the degraded-tools gate, phantom probe, or rebase checkpoint.
- Modify reference files (`phantom-probe.md`, `rebase-checkpoint-routing.md`).
- Remove the existing test harness checks or change what they enforce.

### Approach sketch
- Demote MANDATORY at line ~712 (Step 7a `summary-comment-template.md` load).
- Replace MANDATORY at line ~294 (phantom-probe.md) with a one-sentence advisory note referencing the file.
- Change MANDATORY at line ~143 (rebase-checkpoint-routing.md) to conditional on `ROUTE != continue`; emit `ROUTE=continue|conflict|bail` from `rebase-checkpoint-probe.sh`.
- Replace "Use the canonical interactive predicate from that shared procedure" with the inlined sentence.
- Add a one-sentence stub body to the empty `### Cross-Skill Presence Propagation` section.
- Remove the two dangling "close Step N telemetry:" sentences.
- Truncate NEVER #13 to match the one-line stub pattern of #2 and #10.
- Tighten Preflight item 6: "reasonable inspection" → "a single batched Bash probe block".

### Surfaces in scope
- `skills/implement/SKILL.md` (8 targeted edits)
- `scripts/rebase-checkpoint-probe.sh` (add `ROUTE=` KV emissions)
- `scripts/rebase-checkpoint-probe.md` (document new `ROUTE` KV)

### Open questions
- None.
