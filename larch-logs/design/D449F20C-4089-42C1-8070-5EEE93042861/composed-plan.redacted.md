## Plan

SIMPLE tier. Minimum-change consistency + test pass. The assessor mechanics
(`assess-plan-round.sh`, `snapshot-plan-round.sh`) are NOT modified. Update
Step 3 / Step 3.5 / Step 3.6 ROUTING prose in two skill files, add one
structure pin, and expand one offline harness so every Step 3 exit path has an
explicit Step 3.6 disposition.

## Context

- The Step 3.6 plan-quality assessor is HARD-only and skips unless
  `ROUND_NUM >= 2`.
- Passive-summary already routes toward Step 3.6 in some prose, but the branch
  matrix still needs an explicit cross-reference.
- Step 3.5 entry prose must share the same Gate-B-bypass short-circuit list as
  Step 3 and Step 3.6.
- Short-circuit statuses need uniform Step 3.6 skip breadcrumbs.
- `main-agent-vote-required` also needs explicit routing after inline
  adjudication and re-tally, including current-round findings classification.
- The existing test gap is end-to-end cursor advancement across two Step 3
  entries, including round-2 assessor firing.

## Files

### UPDATED: `skills/design/SKILL.md`

Make Step 3.6 routing explicit on every Step 3 exit path. Preserve existing
`test-design-structure.sh` pinned substrings with append-only edits where
possible.

- `LOOP_STATUS=converged|cap-hit`: keep the pinned passive-summary prefix
  verbatim and append: "Passive-summary Continue routes through Step 3.6 before
  Step 3b."
- Step 3.5 entry blockquote: extend the exception beyond `cap-reached` to all
  Gate-B-bypass short-circuits, or cross-reference the branch matrix, and state
  that those paths bypass both Step 3.5 and Step 3.6 before Step 3b.
- `LOOP_STATUS=main-agent-vote-required`: add that successful inline
  adjudication re-runs tally, parses the re-tally output, and refreshes the
  active Step 3 result state before entering Gate B:
  `TALLY_PLAN_REVIEW_STATUS=ok`, `LOOP_STATUS=complete`, and the persisted
  `.step3-plan-review-result.env` values must reflect the re-tally result so
  Gate B does not read stale 0-judge fallback state. The re-tally command must
  pass `--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv"`
  before refreshing that state so round 2+ classification does not overwrite or
  reuse round 1 output. Then continue to Gate B as complete-equivalent; settled
  Gate B paths, including zero-findings and passive-summary Continue, proceed
  through Step 3.6 before Step 3b. If re-tally emits `tally-error`, use the
  `tally-error` short-circuit.
- `LOOP_STATUS=complete|revision-failed|emit-plan-failed`: name these as
  Gate-B-settled paths that proceed through Step 3.6 after Gate B and any
  Step 2b.5 return.
- `tally-error`: append `(skip Gate B **and Step 3.6**)` and print
  `⏩ 3.6: assessor — skipped (Step 3 tally-error short-circuit)`.
- `degraded-empty-collector`: keep existing Step 3.6 skip semantics and add
  `⏩ 3.6: assessor — skipped (Step 3 degraded-empty-collector short-circuit)`.
- `panel-failed`: add `(skip Gate B **and Step 3.6**)` and print
  `⏩ 3.6: assessor — skipped (Step 3 panel-failed short-circuit)`.
- `cap-reached` paragraph: append that Step 3.6 is skipped and print
  `⏩ 3.6: assessor — skipped (Step 3 cap-reached short-circuit)`. Where the
  per-tier cap prose currently implies a direct Gate C jump, replace it with the
  same Step 3b -> Step 4 -> Gate C route used by Gate C "When" prose.
- `plan-size-trigger|plan-validator-defects`: state that both skip Gate B and
  Step 3.6, with breadcrumbs:
  `⏩ 3.6: assessor — skipped (Step 3 plan-size-trigger short-circuit)` and
  `⏩ 3.6: assessor — skipped (Step 3 plan-validator-defects short-circuit)`.
- Add `panel-failed` to the follow-up sentence listing statuses that do not
  enter Gate B, and note that Step 3.6 is skipped on those short-circuits.
- Do not add `main-agent-vote-required` or `zero-findings-degraded-panel` to any
  skip list.

### UPDATED: `skills/design/references/approval-gates.md`

Make Gate B / Gate C routing match SKILL.md.

- Gate C "When" paragraph: add `panel-failed` to the existing bypass list that
  skips Gate B and therefore Step 3.6.
- Step 3.5 entry wording: align the exception list with the Gate-B-bypass
  short-circuit list and say those paths bypass Step 3.5 and Step 3.6 before
  Step 3b.
- Gate B multi-round outcomes bullet: add `panel-failed` and `cap-reached` to
  the Gate-B-bypassed list, noting Step 3.6 is skipped too.
- Gate B settled-path prose: explicitly name
  `complete|revision-failed|emit-plan-failed` as statuses that proceed through
  Step 3.6 after Gate B and any Step 2b.5 return.
- Add a minimal `main-agent-vote-required` clause: after successful MainAgent
  adjudication and re-tally, parse the re-tally output and refresh the active
  Step 3 result state, including `.step3-plan-review-result.env`, before
  continuing to Gate B as complete-equivalent. The re-tally must pass
  `--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv"`
  before refreshing the active state. Settled Gate B paths proceed through
  Step 3.6. If re-tally emits `tally-error`, use that short-circuit.
- Per-tier cap paragraph: remove or replace any wording that says `cap-reached`
  short-circuits directly to Gate C; use the Step 3b -> Step 4 -> Gate C route
  and note Step 3.6 is skipped.
- Keep `zero-findings-degraded-panel` out of skip lists.
- Keep passive-summary wording aligned with SKILL.md: Continue from the settled
  Gate B path routes through Step 3.6 before the next Step 3 entry / Step 3b.

### UPDATED: `scripts/test-design-structure.sh`

Own the prose pins here instead of coupling the assessor harness to approval
gate wording.

- Add a focused structural assertion for the Gate B settle leg: verify the
  passive-summary Continue prose still says it routes through Step 3.6 before
  Step 3b / the next Step 3 entry.
- Add a structural assertion that the Step 3.5 entry exception covers the full
  Gate-B-bypass short-circuit set and states that those paths bypass Step 3.5
  and Step 3.6 before Step 3b.

### UPDATED: `skills/design/scripts/test-assess-plan-round.sh`

Append one isolated integration case before the terminal `pass` line.

- Add a local cursor helper matching SKILL.md Step 3 HARD cursor advance:
  read cursor defaulting to `1`; if `plan-after-round-<cursor>.txt` exists,
  write `<cursor+1>`; echo the resulting cursor.
- Use a fresh `case_tmp="$(mktemp -d ...)"` for this case.
- Write `"$case_tmp/run-params.json"` directly, or add a parameterized helper
  such as `write_params_for "$case_tmp" HARD`; do not rely on the existing
  `write_params` helper if it only writes to global `$TMP`.
- Before Entry 1, reset only this case's artifacts:
  `plan-after-round-*.txt`, cursor, `assessor-verdict-*`, and related status
  files. Do not reset between Entry 1 and Entry 2, because Entry 2 depends on
  `plan-after-round-1.txt`.
- Restore deterministic default stubs before Entry 1 with case-local mocks, not
  inherited process-global overrides: create `mock-dispatch.sh` and
  `mock-monitor.sh` under `case_tmp`, export the dispatch and monitor
  `LARCH_*` paths to those case-local scripts, and explicitly set
  `LARCH_TALLY_PLAN_ASSESSOR_SH="$ROOT/skills/design/scripts/tally-plan-assessor.sh"`.
  This must happen immediately before Entry 1 so earlier cases cannot leak mock
  paths into the two-entry scenario.
- Entry 1:
  - create `plan.txt` and `feature-description.txt`;
  - run `snapshot-plan-round.sh write-original`;
  - run the cursor helper and assert cursor remains `1`;
  - run `snapshot-plan-round.sh write-after --round 1`;
  - run `assess-plan-round.sh --design-tmpdir "$case_tmp"`;
  - assert `ASSESSOR_STATUS=skipped`, `ASSESSOR_VERDICT=skipped`, and no
    `assessor-verdict-round-1.txt` exists.
- Entry 2:
  - overwrite `plan.txt` with revised content;
  - run the cursor helper and assert it advances to `2`;
  - run `snapshot-plan-round.sh write-after --round 2`;
  - assert round 1 and round 2 snapshots both exist and differ;
  - configure the case-local round-2 dispatch stub to produce a deterministic
    worse majority, and keep the case-local monitor stub active for the assess
    call;
  - run `assess-plan-round.sh --design-tmpdir "$case_tmp"`;
  - assert `ASSESSOR_STATUS=ok`, `ASSESSOR_VERDICT=worse-majority`,
    `EFFECTIVE_ASSESSORS=3`, and `assessor-verdict-round-2.txt` exists.
- Do not add approval-gate prose assertions here; keep this harness focused on
  cursor advance, snapshots, assessor dispatch, and assessor tally behavior.

### UPDATED: `skills/design/scripts/test-assess-plan-round.md`

Add one validated-behavior summary line for the two-entry integration case:
cursor advance → `write-after` → round-2 assessor firing across Step 3 entries.
Mention that the test uses case-local assessment mocks. Note that
passive-summary Gate B routing is covered separately by `scripts/test-design-structure.sh`.

## Approach

- Treat the prose work as routing consistency only.
- Enumerate Step 3.6 behavior for every Step 3 exit: either route through it or
  skip it with a status-specific breadcrumb.
- Treat the harness addition as the only behavioral guard.
- Keep approval-gate prose assertions in `scripts/test-design-structure.sh`,
  not in `test-assess-plan-round.sh`.
- Do not change assessor scoring, dispatch, tally, convergence, cap semantics,
  or Step 3 status validation.
- Keep MainAgent re-tally handling minimal: update only the Step 3 result state
  needed for Gate B to consume the successful re-tally, and fall back to the
  existing `tally-error` short-circuit on failure.

## Edge Cases

- `zero-findings-degraded-panel` still routes through Step 3.6.
- `main-agent-vote-required` is not a skip status; only a failed re-tally can
  fall into the existing `tally-error` skip path.
- MainAgent re-tally writes findings classification to the active round path,
  not a default or stale round-1 location.
- Gate-B-bypass statuses bypass Step 3.5 and Step 3.6 before Step 3b.
- SIMPLE/TRIVIAL still skip the assessor because `workflow_path != HARD`.
- Preserve round-1 snapshots through Entry 2.
- The integration case must not inherit mutated mocks from earlier cases.
- Gate B must not consume stale `.step3-plan-review-result.env` values after
  MainAgent adjudication re-tally.
- The passive-summary Continue route must remain pinned even if only by a
  structural assertion in `scripts/test-design-structure.sh` rather than a full
  interactive Gate B harness.

## Failure Modes

- Structural pin breakage: run `bash scripts/test-design-structure.sh`; it owns
  passive-summary and Step 3.5 bypass prose assertions.
- Markdown lint failure: keep code spans whitespace-clean and avoid new heading
  level jumps.
- Fail-open false positive: assert `ASSESSOR_STATUS=ok`,
  `ASSESSOR_VERDICT=worse-majority`, and `EFFECTIVE_ASSESSORS=3` with the real
  tally script path.
- Wrong tempdir params: write `run-params.json` into `case_tmp`.
- Over-resetting artifacts: reset before the case, not between Entry 1 and
  Entry 2.
- Mock leakage: export case-local dispatch and monitor stubs immediately before
  Entry 1, and do not rely on prior global `$TMP` stubs.
- Stale Gate B state: after MainAgent re-tally, rewrite or refresh the active
  Step 3 result state and active-round findings classification before entering
  Gate B.

## Testing Strategy

- `bash skills/design/scripts/test-assess-plan-round.sh`
- `bash scripts/test-design-structure.sh`
- `make lint`
- Manual read-through confirming every Step 3 exit names its Step 3.6
  disposition, including `main-agent-vote-required`, `plan-size-trigger`, and
  `plan-validator-defects`.
- Manual read-through confirming Step 3.5, Gate B, and Gate C bypass lists stay
  aligned.
- Confirm the passive-summary Continue structural assertion fails if the Step 3.6
  routing sentence is removed.


## Acceptance

- Every Step 3 `LOOP_STATUS` exit in `skills/design/SKILL.md` names its Step 3.6 disposition: `complete` / `converged` / `cap-hit` / `revision-failed` / `emit-plan-failed` / `zero-findings-degraded-panel` / `main-agent-vote-required` route THROUGH Step 3.6 (via Gate B); `tally-error` / `panel-failed` / `cap-reached` / `degraded-empty-collector` / `plan-size-trigger` / `plan-validator-defects` SKIP Step 3.6 with a status-specific `⏩ 3.6: assessor — skipped (Step 3 <status> short-circuit)` breadcrumb.
- `skills/design/references/approval-gates.md` bypass lists include `panel-failed` and stay aligned with SKILL.md (Gate C "When", Gate B multi-round outcomes, Step 3.5 entry); the same six Step 3.6 skip-breadcrumb literals appear byte-for-byte in both files.
- `main-agent-vote-required` is NOT in any skip list: after successful inline adjudication + re-tally (passing `--findings-classification-out` for the active round), the Step 3 result state (`.step3-plan-review-result.env`, `TALLY_PLAN_REVIEW_STATUS=ok`, `LOOP_STATUS=complete`) is refreshed before Gate B; a re-tally `tally-error` uses the `tally-error` short-circuit.
- `zero-findings-degraded-panel` continues to route THROUGH Step 3.6 (absent from every skip list).
- All existing `scripts/test-design-structure.sh` pinned substrings are preserved (edits are append-only where the substring is pinned); the cap breadcrumb pin `skipping panel and returning to Gate C.` stays literal or is updated in the same change.
- `scripts/test-design-structure.sh` gains a passive-summary Continue → Step 3.6 assertion and a Step 3.5 Gate-B-bypass coverage assertion.
- `skills/design/scripts/test-assess-plan-round.sh` gains an isolated two-entry integration case (case-local tmpdir + mocks): Entry 1 asserts the assessor skips on round 1; the cursor advances to 2; Entry 2 asserts the assessor fires (`ASSESSOR_STATUS=ok`, `ASSESSOR_VERDICT=worse-majority`, `EFFECTIVE_ASSESSORS=3`).
- `skills/design/scripts/test-assess-plan-round.md` documents the new integration case.
- `assess-plan-round.sh` / `snapshot-plan-round.sh` behavior is unchanged.
- Verification passes: `bash skills/design/scripts/test-assess-plan-round.sh`, `bash scripts/test-design-structure.sh`, and `make lint`.

diff_lines: 205
