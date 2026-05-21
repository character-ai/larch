Structured aggregation of the supplied reviewer slots (merged where the same behavioral risk or fix direction applies; `[OUT_OF_SCOPE]` kept on merged headings only when every merged source carried it—here all OOS items stay separate).

```text
### FINDING_1: steps_ran.step9a1 not authoritative across skip paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Only `refresh-run-logs.sh` infers/persists `steps_ran.step9a1` from a narrow set of predicates and KV/disk signals; other orchestrated skips can leave it unset or mis-set (stale or conflicting flags vs reality). Downstream `audit-scan-run` / `verify-run-log-completeness` can then false-fail or false-pass relative to true Step 9a.1 execution.
- **Suggested revision**: Persist a single canonical boolean from the real Step 9a.1 decision (or batch writer) on every skip path; use refresh only to reconcile; add regression for an uncovered or conflicting KV-vs-disk skip mode.

### FINDING_2: Noisy committed plan artifact in run log
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Committed `plan-goals-test.md` exposes full internal planning draft and discarded options, cluttering audits of run logs.
- **Suggested revision**: Commit only the final executed plan body or strip internal deliberation before flush.

### FINDING_3: Ambiguous PR-body closing-keyword → wrong issue mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: First `Closes`/`Fixes`/`Resolves` match (e.g. `grep | head -1` / file order) can map a run to the wrong parent issue when multiple lines exist; order is not GitHub’s semantic priority.
- **Suggested revision**: Use a canonical rule (e.g. prefer `Closes` pass, or disambiguate using manifest `closes_issue` / parent-issue `ISSUE_NUMBER`), or detect ambiguity and refuse mapping like other ambiguous branches.

### FINDING_4: Duplicated manifest parsing in verify completeness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Separate Python one-shots each read `manifest.json` for related fields, increasing maintenance cost and drift risk between parsers.
- **Suggested revision**: Factor one shared manifest reader or one structured query feeding both helpers.

### FINDING_5: Missing positive render tests for Outcome on stalled/bailed paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: After conditional rendering changes, CI lacks fixtures proving stalled (and optionally bailed) outcomes still emit an **Outcome** line; regressions could drop that signal without failing tests.
- **Suggested revision**: Add render fixtures asserting **Outcome** is present for those outcome classes.

### FINDING_6: [OUT_OF_SCOPE] Ordering invariant: final-summary vs Step 9a.1 artifacts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 9a.1 gating that treats `final-summary.md` as a reach signal assumes implement ordering not shown in this diff; future paths could reorder writes vs artifacts.
- **Suggested revision**: Confirm ordering invariant in implement skill docs or add an ordering-sensitive test outside this diff review.

### FINDING_7: Non-boolean / numeric falsy values break skip semantics consistency (audit vs verify)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `jq` treats `0 == false`, so non-boolean `steps_ran` values can mark steps skipped in `audit-scan-run` while `verify-run-log-completeness` still treats only Python `False` as skipped—e.g. `step9a1: 0` yields divergent enforcement.
- **Suggested revision**: Align on one rule: require `type == "boolean"` and `value == false` in `jq`, or update verify and comments to the same canonical predicate.

### FINDING_8: Cross-cutting jq failure masks corruption as “healthy” flags
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: When cross-cutting `jq` evaluation fails, the script falls back to all-false integrity-style flags, so a corrupt manifest can look clean in NDJSON output.
- **Suggested revision**: On `jq` failure, emit an explicit error or non-clean defaults instead of silent all-false success-shaped output.

### FINDING_9: `gh pr view` failure breaks or obscures PR→run mapping (manifest fallback, operators, docs)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-gh-failure-policy-output.txt
- **Concern**: Mapping is gated on successful `gh` paths; when `gh pr view` fails, manifest-by-`pr_number` fallback may not run, yielding empty or misleading mappings offline/flaky networks. Documented flows that capture only stdout (`RUN_MAP_TSV=$(bash …)`) can miss stderr markers like `MAP_GH_PR_VIEW_FAILED`, exit 0 with empty `run_id`, and misclassify infrastructure failure as “unmapped PR.”
- **Suggested revision**: Add a manifest-primary or `gh`-failure fallback, exit non-zero or stdout machine-readable failure markers, and/or tighten SKILL orchestration (e.g. tee/capture stderr and abort on `MAP_GH_PR_VIEW_FAILED`); document the contract in `audit-map-runs.md` / skill prose.

### FINDING_10: v2 manifest omit-key semantics vs cross-cutting docs and consumer tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: For `schema_version >= 2`, `ended_at_null` / `pr_number_null` no longer mean “field absent” the same way as v1; typical flushed v2 manifests omit keys and report false for those flags, inverting prior NDJSON meaning. Shipped `audit-scan-run.md` (and examples) still describe the older “empty field” mental model, misleading dashboards/aggregators.
- **Suggested revision**: Add regression tests pinning v1 vs v2 cross-cutting lines; rewrite `audit-scan-run.md` (and examples) to spell out v1 vs v2 `has(...)` / null / omit semantics and how `manifest_pr_number_mismatch_with_audited_pr` behaves with present non-null `pr_number`.

### FINDING_11: Outcome bullet vs title / structured consumers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Title still embeds outcome strings while the **Outcome** bullet is suppressed for many cases; automation that parsed only the bullet loses signals (e.g. forked dry-run, merged, design-only).
- **Suggested revision**: Align UX/docs expectations or add a structured outcome field; extend conditional rendering if non-bailed outcomes should always surface a bullet.

### FINDING_12: final-summary reach signal and legacy / external snapshots
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Using `final-summary.md` to gate Step 9a.1 completeness without `pr_number`/status can newly fail older or external snapshots that wrote an early summary without 9a.1 artifacts unless `steps_ran.step9a1=false` is present.
- **Suggested revision**: Confirm product intent; document migration, or gate the `final-summary` arm (e.g. on `schema_version >= 2`) if legacy preservation matters.

### FINDING_13: [OUT_OF_SCOPE] `--repo` token validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `--repo` is not validated like other PR-list tokens; malformed values rely on `gh` handling—pre-existing surface.
- **Suggested revision**: Harden only if tightening the `gh` invocation contract is desired.

### FINDING_14: [OUT_OF_SCOPE] `manifest_field` hides JSON parse failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Helper can surface corrupt `manifest.json` as empty fields, silently skipping `pr_number`/status-driven gates.
- **Suggested revision**: Harden separately if desired.

### FINDING_15: [OUT_OF_SCOPE] SKILL summary vs v2 cross-cutting wording
- **Reviewer(s)**: dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: Skill-level summary still describes cross-cutting as flagging empty `ended_at`/`pr_number` without v2 `has(...)` nuance, easier to misread with default omit-key v2 manifests.
- **Suggested revision**: Align the bullet with v1/v2 distinction after script-level docs are corrected.

### FINDING_16: [OUT_OF_SCOPE] Historical dyn-* prompts in committed run logs
- **Reviewer(s)**: dyn-schema-v2-consumer-coverage-output.txt
- **Concern**: Frozen captured prompts still teach “grep manifest for pr_number first” while live tooling order has moved.
- **Suggested revision**: Treat as frozen run-log content unless explicitly refreshed; update only if maintained as living templates elsewhere.
```
