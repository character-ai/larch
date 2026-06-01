## Decision 1: Change scope
- **Question**: Should this single change add `scripts/step-telemetry-mark.sh` AND collapse the per-step ledger telemetry preambles in `skills/implement/SKILL.md`, plus update tests — or defer the SKILL.md rewrite?
- **Resolution**: Full change in one PR — add the helper, convert every eligible step-ENTRY mark site, and update the rehydration tests. #3292 (plugin-root awk fence collapse) already landed, so the per-step preamble sweep is unblocked.
- **Source**: user

## Decision 2: Never-fatal telemetry invariant
- **Question**: What must not break in the telemetry behavior?
- **Resolution**: The helper and every converted call site MUST preserve best-effort `|| true` semantics — telemetry failures never abort a step. The helper itself exits 0 even when `session-env.sh`, keys, or the ledger scripts are missing.
- **Source**: codebase (issue Risk/caveats)

## Decision 3: Step 18 closing cap stays inline
- **Question**: Are all `*-ledger.sh mark` sites eligible for the helper?
- **Resolution**: No. Only step-ENTRY marks are in scope. The Step 18 closing `Step 18 — done` mark MUST stay orchestrator-emitted/inline because `token-report.sh`'s vendor table slices the last mark with `$end == null` and the closing cap must land after the `--since-last-mark` calls. Audit each mark site against this.
- **Source**: codebase (issue Risk/caveats)

## Decision 4: Branchy / conditional mark sites
- **Question**: How are sites where the token-ledger mark is emitted inside conditional branches (e.g. Step 2's coder `case`), separate from the trailing timing-ledger mark, handled?
- **Resolution**: The helper emits BOTH marks together, so it only fits sites where an unconditional token+timing mark pair is adjacent. Branchy/conditional mark sites (where token-mark appears in multiple `case` branches separate from the single timing-mark) are left inline / not collapsed by this helper. Convert only the cleanly-adjacent unconditional step-entry sites.
- **Source**: codebase (skills/implement/SKILL.md Step 2 dispatch block)

## Decision 5: Helper interface scope (non-goal: generality)
- **Question**: Should the helper be /implement-specific or generic for future /design /review reuse?
- **Resolution**: /implement-specific per the issue: `step-telemetry-mark.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step N — name"`, reading the three keys from `$IMPLEMENT_TMPDIR/session-env.sh`. No speculative `--session-env <file>` generality (Simplicity First; /design and /review use a different mark shape via `LARCH_TIMING_SKILL`).
- **Source**: codebase + Simplicity First

## Decision 6: Keep tests green
- **Question**: What test surface must stay green / be updated?
- **Resolution**: `scripts/test-implement-timing-rehydration.sh` and the run-step1 / run-step5 rehydration tests must stay green; any assertion that pins the inline mark form must be updated to the new helper-call form. Add focused unit coverage for the new helper.
- **Source**: codebase (issue Risk/caveats)
