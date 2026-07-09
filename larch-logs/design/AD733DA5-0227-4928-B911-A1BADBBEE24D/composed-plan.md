## Plan

## Approach

Implement the approved combined Step 8 assessment round with minimal routing churn and one authoritative token contract. Freeze the compose-time diff snapshot once per combined gate pass so invariant and guideline materializations always share identical evidence.

### Canonical combined-assessment contract

| Field | Value |
|-------|-------|
| Python `needs_user_reason` | `architectural-assessments` |
| Dispatch `NEXT_ACTION` | `assessments` |
| Resume `PHASE` | `assessments` |
| `ShipResult.detail` / handoff `DETAIL` | Comma-separated kind list built only as `",".join(assessment_kinds)` where each element is exactly `invariants` or `guidelines` (no spaces). Allowed values: `invariants`, `guidelines`, `invariants,guidelines`. |

Orchestrator reads `DETAIL` from `$IMPLEMENT_TMPDIR/.ship-route-exit-handoff.env`, then falls back to `DETAIL_FILE` when present. Parse by splitting on `,`, trim each token, reject empty, unknown, or duplicate tokens with Tool Failure before running any writer or relaunching Step 8. Reserve per-gate `detail` strings for back-compat per-kind reasons and violation paths only.

### Shared compose-time snapshot

Before either gate evaluates `needs_assessment`, resolve and freeze one shared snapshot per combined pass:

1. Resolve `compose_head_sha` from current `HEAD` once.
2. Resolve `compose_base_ref` once (`origin/<base>` or `upstream/<base>` from fork state).
3. Resolve the diff base once via `resolve_diff_base` and materialize the implementation diff once via `materialize_implementation_diff` (or reuse an existing shared helper such as `_materialize_live_diff`).
4. Compute `diff_fingerprint` once from that frozen diff text.
5. Optionally resolve the base commit SHA once for metadata parity.

Thread the frozen tuple `(compose_head_sha, compose_base_ref, diff_text, diff_fingerprint)` into both gate evaluations. Do not let each gate independently call `resolve_diff_base` / `materialize_implementation_diff` on the combined path. When only one kind needs assessment, still use the same combined action and snapshot path.

Write both `architectural-invariant-materialized-diff.txt` / `architectural-invariant-materialize.env` and `architectural-guideline-materialized-diff.txt` / `architectural-guideline-materialize.env` from that single frozen diff when both kinds need materialization. Both env sidecars must record the same `HEAD_SHA`, `BASE_REF`, and `DIFF_FINGERPRINT`.

### Combined compose-time gate helper

Add `_compose_assessment_gate_before_pr` (or equivalent private helper) in `ship.py`:

1. Build the shared snapshot once as above.
2. Run the invariant gate first against that frozen snapshot (thread snapshot args into `_invariants_gate_before_pr` / `load_or_prepare_invariants_note`, or add snapshot-aware prepare helpers that accept pre-materialized diff text).
3. Short-circuit only on `architectural-invariants-violation` (unchanged path).
4. Run the guideline gate against the same frozen snapshot even when invariants need assessment, so both materialized inputs exist before one combined pause.
5. Build `assessment_kinds: list[str]` — append `invariants` when `invariants_gate.needs_assessment`; append `guidelines` when `guidelines_gate.needs_assessment`.
6. When the list is non-empty, return `ShipResult(Outcome.NEEDS_USER_INPUT, needs_user_reason="architectural-assessments", detail=",".join(assessment_kinds))`.
7. Preserve absent, invalid, dropped, redaction, and outcome-sidecar behavior per gate.
8. Preserve both durable notes, write wrappers, outcome JSON sidecars, and PR-body sections.

Remove the pre-guidelines `needs_assessment` early return on the combined pre-PR and post-rebase refresh paths. Replace the current two-phase state writes with one `_write_ship_state(..., phase="assessments", ...)` before the combined gate pass.

### Orchestrator relaunch semantics

Under `NEXT_ACTION=assessments`, the SKILL branch owns relaunch timing. Per-reference relaunch lines apply only to back-compat `invariants-assessment` and `guidelines-assessment` branches. When `DETAIL` lists more than one kind, defer all Step 8 relaunch until every DETAIL-requested writer succeeds; do not relaunch after the first writer.

### Back-compat

Keep dispatch mappings for `architectural-invariants-assessment` → `invariants-assessment` and `architectural-guidelines-assessment` → `guidelines-assessment`. Keep old SKILL branches for one release. Add the new `assessments` branch before them.

## Files to modify/create

### UPDATED: python/larch/implement/ship.py

Add `_compose_assessment_gate_before_pr` with snapshot-once, evaluate-both-gates, single-return shape above.

Suggested flow inside the helper:

- Snapshot `compose_head_sha`, `compose_base_ref`, frozen `diff_text`, and `diff_fingerprint` once.
- Call invariant then guideline gate evaluation against that shared snapshot.
- Violation short-circuit before building `assessment_kinds`.
- Build `assessment_kinds` from each gate's `needs_assessment`.
- Return combined `ShipResult` when non-empty; otherwise return both gate results for PR-body composition.

Keep `architectural-invariants-violation` before PR compose and before guideline PR-body composition. Keep `_compose_pr_body_for_pr_create(... architectural_invariants_note=..., architectural_guidelines_note=...)`.

Update both call sites:

- Initial pre-PR compose path (replace separate `phase="invariants-assessment"` / `phase="guidelines-assessment"` writes and per-kind early returns).
- Post-rebase refresh path in `_refresh_guidelines_gate_after_rebase`.

Avoid changing sidecar schemas or note writer contracts.

### MAY_UPDATE: python/larch/implement/ship_guidelines.py

If `_invariants_gate_before_pr` / `_guidelines_gate_before_pr` cannot accept a frozen snapshot without duplicating prepare logic, add thin snapshot-aware entry points on `load_or_prepare_invariants_note` / `load_or_prepare_guidelines_note` (or shared helpers they call) that accept optional pre-materialized `(diff_text, diff_fingerprint, compose_head_sha, compose_base_ref)` and skip independent `resolve_diff_base` / `materialize_implementation_diff` when provided.

### MAY_UPDATE: python/larch/core/architectural_guidelines.py

If needed for minimal duplication, add a small shared compose-snapshot helper (for example `materialize_compose_snapshot(...) -> ComposeSnapshot`) plus snapshot-aware variants of `prepare_compose_assessment` / `prepare_invariant_compose_assessment` that write per-kind diff/env files from one frozen diff. Keep existing standalone prepare entry points unchanged for back-compat and non-combined callers.

### UPDATED: python/larch/implement/dispatch_ship.py

Add `architectural-assessments` to `_classify_ship_needs_user_reason` and map it to `assessments` before the legacy mappings.

Keep existing mappings:

- `architectural-invariants-assessment` → `invariants-assessment`
- `architectural-guidelines-assessment` → `guidelines-assessment`

Ensure `.ship-route-exit-handoff.env` still writes `DETAIL=<comma-separated kinds>` without widening the wire grammar.

### UPDATED: python/larch/implement/ship_resume.py

Include `assessments` in the no-PR pre-compose resume phase set alongside:

- `invariants-assessment`
- `guidelines-assessment`

### UPDATED: skills/implement/SKILL.md

Add a new post-driver branch before the legacy per-kind branches:

- **`assessments`**: read `DETAIL` (then `DETAIL_FILE`) from `.ship-route-exit-handoff.env`; parse allowed tokens `invariants` and/or `guidelines`; Tool Failure on empty, unknown, or duplicate tokens.
- **MANDATORY: READ ENTIRE FILE**: read both present-reference files completely when their kind is listed in `DETAIL`.
- When `DETAIL` contains `invariants`, author invariants and run `step-architectural-invariants-write-compose.sh` first.
- When `DETAIL` contains `guidelines`, author guidelines and run `step-architectural-guidelines-write-compose.sh` after any invariant writer succeeds.
- **Combined-path supremacy**: under `NEXT_ACTION=assessments`, ignore per-reference relaunch lines until every DETAIL-listed writer succeeds; relaunch `step-8-ship.sh` through the Step 8 bgjob start/wait pair exactly once after all requested writers succeed.
- Continue to Step 8, not Step 16. Do not ask for an operator override.

Keep the old `invariants-assessment` and `guidelines-assessment` branches below as back-compat (each retains its own per-kind relaunch).

### UPDATED: skills/implement/references/ship-pr-exit-matrix.md

Document the canonical contract:

- `architectural-assessments` maps to `assessments`.
- `DETAIL` is a comma-separated kind list (`invariants`, `guidelines`, or `invariants,guidelines`; trim tokens; no spaces).
- Read `DETAIL` from `.ship-route-exit-handoff.env`, then `DETAIL_FILE` when needed.
- The `assessments` branch consumes invariant and/or guideline materialization files based on `DETAIL`, authors invariants first, writes both requested durable notes through existing wrappers, and relaunches Step 8 once after all listed writers succeed.
- Both requested materializations are produced during the combined pause from one frozen diff snapshot.
- Old per-kind mappings remain accepted for one release under explicit back-compat bullets.

### UPDATED: skills/implement/references/architectural-invariants-present.md

Cross-link to the combined `assessments` action.

Update **Consumer** and **When to load** to include:

- Primary: `NEXT_ACTION=assessments` with `DETAIL` containing `invariants`.
- Back-compat: `NEXT_ACTION=invariants-assessment`.

Update **Required artifacts** for the combined path:

- `NEEDS_USER_REASON=architectural-assessments` and `DETAIL` containing `invariants` (retain old reason line under an explicit back-compat sub-bullet).

Add **combined-path carve-out**: on `NEXT_ACTION=assessments`, follow SKILL ordering; do not relaunch after the invariant writer; defer Step 8 relaunch to the parent `assessments` branch until every DETAIL-listed writer succeeds. Per-reference relaunch text below applies only to back-compat `invariants-assessment`.

Keep the required artifacts, clean text, violation text, and write wrapper unchanged.

### UPDATED: skills/implement/references/architectural-guidelines-present.md

Update **Consumer** to include:

- Primary: `/implement` Step 8+ `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, loaded by the main agent after `ship.py` materializes compose-time guideline inputs.
- Back-compat: `/implement` Step 8+ `NEXT_ACTION=guidelines-assessment`.

Replace **When to load**:

- Primary combined path: MANDATORY on `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, after `ship.py` has materialized `$IMPLEMENT_TMPDIR/architectural-guideline-materialize.env` and `$IMPLEMENT_TMPDIR/architectural-guideline-materialized-diff.txt`, regardless of invariant authoring status.
- Back-compat: retain the existing prerequisite that invariant assessment has completed cleanly or been absent/invalid/empty only for `NEXT_ACTION=guidelines-assessment`.
- On combined paths where both kinds are listed, invariants are authored first when both are in `DETAIL`.

Update **Required artifacts**:

- `NEEDS_USER_REASON=architectural-assessments` and `DETAIL` containing `guidelines` (retain old `NEEDS_USER_REASON=architectural-guidelines-assessment` line under back-compat).

Add **combined-path carve-out**: on `NEXT_ACTION=assessments`, follow SKILL ordering; do not relaunch after the guideline writer alone; defer Step 8 relaunch until all DETAIL-listed writers succeed. Per-reference relaunch text below applies only to back-compat `guidelines-assessment`.

Keep the required artifacts, deviation warning helper, durable wrapper, and failure behavior unchanged.

### UPDATED: python/tests/implement/test_ship.py

Add route and behavior coverage:

- Both gates need assessment: `needs_user_reason == "architectural-assessments"`, `detail == "invariants,guidelines"`, both materialized diff/env files present, single snapshot used.
- Only invariants: `detail == "invariants"`.
- Only guidelines: `detail == "guidelines"`.
- Post-rebase refresh returns combined reason when both gates need assessment.
- Invariant violation remains `architectural-invariants-violation`.
- Existing old-token resume test remains valid; add `PHASE=assessments` no-PR resume coverage.

**Migrate existing compose-path assertions** that currently expect legacy per-kind tokens on the main combined flow. Update tests such as `test_open_pr_resume_guidelines_gate_needs_assessment_skips_flush_and_ensure_pr`, the stale-guidelines reassessment test near line 7168, and the merge-rebase guidelines assessment test near line 6611 to expect:

- `needs_user_reason == "architectural-assessments"`
- kind-only `detail` values (`"invariants"`, `"guidelines"`, or `"invariants,guidelines"`)

Do not keep legacy `needs_user_reason=architectural-guidelines-assessment` / `architectural-invariants-assessment` assertions on paths that now emit the combined action. Reserve legacy-reason expectations only where the test explicitly exercises back-compat dispatch or resume on an old per-kind `PHASE`.

**Snapshot assertions** (FINDING_6):

- Monkeypatch or inspect both gates/prepare helpers and assert they receive the same frozen snapshot inputs.
- Assert both materialize env files record identical `DIFF_FINGERPRINT` and `BASE_REF` (and matching `HEAD_SHA`) when both kinds materialize.
- Prefer fingerprint/base equality over argument-equality alone.

Prefer focused monkeypatch tests for branch routing, plus one real materialization test if existing helpers make it cheap.

### UPDATED: python/tests/implement/test_implement_dispatch.py

Add a parameter row for:

- rc `3`
- `needs_user_reason="architectural-assessments"`
- expected `NEXT_ACTION=assessments`

Assert `DETAIL=invariants,guidelines` is preserved in the handoff env in one direct test.

Keep existing legacy per-kind parametrization rows for back-compat dispatch (`architectural-invariants-assessment` → `invariants-assessment`, `architectural-guidelines-assessment` → `guidelines-assessment`).

### UPDATED: skills/implement/scripts/test-architectural-guidelines-step.sh

Update pinned strings for the combined Step 8 contract. Add assertions for:

- SKILL has an `assessments` branch.
- Branch reads both reference files when both kinds are listed.
- Combined-path carve-out in both present refs (defer relaunch to parent `assessments` branch).
- Guidelines present-ref **When to load** no longer requires completed invariant authoring on the combined path.
- Invariant write before guideline write before exactly one Step 8 relaunch in the `assessments` branch.
- Exit matrix documents `architectural-assessments`, `DETAIL`, shared snapshot semantics, and single-relaunch behavior.

Replace harness pins at lines 55/64 that assert unconditional per-ref relaunch with carve-out pins for the combined path; keep per-ref relaunch pins scoped to back-compat branches where applicable.

Keep old per-kind assertions for back-compat branches.

### UPDATED: scripts/test-implement-structure.sh

Update pinned references that still expect only `NEXT_ACTION=guidelines-assessment` after compose-time reassessment. Accept `NEXT_ACTION=assessments` as the current path while keeping old tokens where the test verifies back-compat.

### UPDATED: scripts/test-implement-fence-shape.sh

Add an `assessments`-slice assertion:

- `assessments` branch exists before legacy per-kind branches.
- Invariant compose write before guideline compose write before exactly one Step 8 bgjob relaunch.
- Pin combined-path ordering distinct from legacy `guidelines-assessment` slice checks.

## Edge cases

- Both files present and both notes stale: one pause, `DETAIL=invariants,guidelines`, one relaunch after both writers; both materializations share one `DIFF_FINGERPRINT`.
- One file absent or invalid: the other file can still request assessment through the combined action with a single-kind `DETAIL`.
- Invariant violation: keep old `architectural-invariants-violation` behavior; short-circuit before combined assessment return.
- Old paused run: old per-kind `NEXT_ACTION` still completes with per-kind relaunch.
- `HEAD` changes after materialization: existing write wrappers still fail and force Step 8 rematerialization.
- Outcome sidecar write or dropped outcome failure: keep fail-closed stall behavior before PR compose.
- `DETAIL` with one kind: same combined action and single relaunch after that one writer.
- Base resolution drift between gates: prevented by single `resolve_diff_base` + `materialize_implementation_diff` per combined pass.

## Failure modes

- Missing or malformed `DETAIL` for `assessments`: SKILL handler fails closed as Tool Failure; do not guess kinds.
- Unknown or duplicate `DETAIL` tokens: Tool Failure before any writer or relaunch.
- One writer fails: do not run later writers or relaunch Step 8 with a partial stale note.
- Both writers succeed: relaunch Step 8 exactly once; do not relaunch after the first writer.
- Route-exit emits an old per-kind action: run the old handler with per-kind relaunch; do not require `DETAIL`.
- Snapshot drift between gates: prevented by single frozen diff per combined gate pass; tests must pin matching `DIFF_FINGERPRINT` / `BASE_REF`, not only matching HEAD/base-ref call arguments.

## Testing strategy

Run changed-file tests only:

```bash
python3 -m pytest python/tests/implement/test_ship.py python/tests/implement/test_implement_dispatch.py
bash skills/implement/scripts/test-architectural-guidelines-step.sh
bash scripts/test-implement-structure.sh
bash scripts/test-implement-fence-shape.sh
```

Also run targeted lint for changed Python files through the repo's normal changed-file flow.

## Acceptance

Run changed-file tests only:

```bash
python3 -m pytest python/tests/implement/test_ship.py python/tests/implement/test_implement_dispatch.py
bash skills/implement/scripts/test-architectural-guidelines-step.sh
bash scripts/test-implement-structure.sh
bash scripts/test-implement-fence-shape.sh
```

Also run targeted lint for changed Python files through the repo's normal changed-file flow.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 360
