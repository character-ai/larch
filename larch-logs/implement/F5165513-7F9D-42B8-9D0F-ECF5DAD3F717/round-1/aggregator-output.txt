Here is the normalized structured finding list (merged by theme, first-seen order, sources preserved).

```text
### FINDING_1: Strict-mode mismatch between `##` and `### FINDING_` handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: With `strict_cat=1`, non-canonical `##` lines use `next` so scanning can continue, but the `### FINDING_` branch still always ends with `exit` on first match even when strict mode produced no category, so strict semantics differ between `##` and `###` paths in one function.
- **Suggested revision**: Align strict-mode control flow for the `###` stanza with the `##` stanza, or explicitly document that strict scanning applies only to `##` lines.

### FINDING_2: Plan alignment, completeness, and contradiction check (informational)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The strict `##` awk behavior matches the stated plan (non-canonical `##` uses `next` instead of falling through to `exit`, later canonical `## tag: …` can win; canonical matches still print and exit). Checklist items are satisfied (extract_category, strict_cat for plan-review accepted, fixture/assertion, doc paragraph). No contradiction between feature text, plan, and diff; reviewer notes `flush_pending` synthetic `##` title plus generic `###` handling make interaction with accepted-plan bodies unlikely in practice (verification not run in reviewer context).
- **Suggested revision**: None required for merge readiness; retain as a verification record.

### FINDING_3: Empty `category` when no canonical `##` — tests, contracts, and consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-coverage-output.txt
- **Concern**: Coverage only exercises plan-review `accepted` when a canonical `## <focus-area>:` appears after the synthetic prose `##` title; the strict-scan path that exhausts lines and yields an empty `category`, multi-skip ordering, and “wrong order” regressions are not asserted. Accepted rows can legitimately have `category=""` while `prose_body` still carries the finding; tooling or analytics that assumed non-empty `category` may mis-bucket, miscount, or drop rows.
- **Suggested revision**: Add a plan-review `accepted` fixture with only non-canonical `##` lines (and optionally multiple junk `##` lines before a canonical tag) asserting `category` is empty; document the producer contract and/or validate downstream handling; optionally document an authoring expectation when consumers require a non-empty category.

### FINDING_4: [OUT_OF_SCOPE] `docs/run-logs.md` omits plan-review accepted strict-scanning nuance
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: High-level category narrative does not spell out plan-review accepted strict scanning; minor imprecision versus producer contract and not introduced by this diff.
- **Suggested revision**: Optional one-line clarification or rely on the existing link to `scripts/compose-review-findings.md`.

### FINDING_5: Historical JSONL/analytics impact from stricter shared `##` scanning for `out_of_scope`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The shared strict-mode `##` scan now continues past the first non-canonical `##` for `out_of_scope` as well as plan-review `accepted`; rare OOS markdown with a junk first `##` and a later canonical `##` may now emit a non-empty category where older runs produced `""`.
- **Suggested revision**: Note the behavior change in `CHANGELOG` and/or the review-findings batch contract if historical JSONL comparisons matter.

### FINDING_6: [OUT_OF_SCOPE] Pre-existing early exit on inner `### FINDING_` headings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The `### FINDING_` awk rule still exits after the first matching inner heading, so later `##` lines are ignored in that edge shape; pre-existing and unchanged in this diff; only relevant if such inner headings appear inside composed bodies.
- **Suggested revision**: No PR-scoped change unless doing a broader `extract_category` refactor.

### FINDING_7: Tests assert `category` but not `prose_body` shape for the same rows
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Concern**: Assertions validate `category` for representative IDs only; they would not catch regressions where `category` is correct but `prose_body` is truncated, merged, or otherwise wrong relative to the “don’t treat prose as category” intent.
- **Suggested revision**: Add lightweight substring checks (for example via `grep -qF`) against `prose_body` for distinctive canonical `##` lines and bullet text while keeping `category` checks primary.

### FINDING_8: [OUT_OF_SCOPE] Ancillary review context (fixture intent, loose mode, branch noise, commits)
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Concern**: (1) Code-review `accepted` loose-mode assertions remain consistent with documented synthetic `## <title>` behavior. (2) Fixture ordering intentionally places the canonical `##` inside `pending_body` after `flush_pending` prepends the synthetic title, exercising skip-then-match rather than “canonical first line only.” (3) Branch diff includes `larch-logs/implement/...` artifacts orthogonal to compose correctness, widening review surface. (4) Read-only commit listing noted for context.
- **Suggested revision**: None required for the compose fix itself; optionally trim unrelated artifacts from the change surface if policy dictates.
```
