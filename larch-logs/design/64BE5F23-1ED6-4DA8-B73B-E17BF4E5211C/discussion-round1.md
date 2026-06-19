# Round 1 scope decisions (operator Q&A)

## Decision 1: Plan grouping
- **Question**: Keep the 10 OOS items as one combined plan, or split into separate issues?
- **Resolution**: Keep one combined plan. Do not partition. Honors the `/combine-issues --oos` intent. Items remain implementable piecemeal.
- **Source**: user

## Decision 2: Probe default behavior (Item 1)
- **Question**: Should the timeout-retry fix preserve current default health-gate latency, or change default probe behavior?
- **Resolution**: Opt-in only. Add a new env knob (default off) so default probe latency is unchanged. Do not change default behavior. Auth and transient retry budgets stay independent.
- **Source**: user

## Decision 3: Self-flagged items 4, 6, 7
- **Question**: How to handle items the issue flags as "verify against the working tree, then pin or drop with evidence"?
- **Resolution**: Re-verify each against the current tree at drafting. Pin a concrete defect or drop with recorded evidence. Do not implement speculatively.
- **Source**: codebase (verification deferred to Step 2b)

## Decision 4: Item 10 redaction vs the just-merged panel-failure log path
- **Question**: Is item 10 (unredacted vendor stderr on plan-review waterfall failure) still a real defect after #4765/#4747 touched `plan_review_panel.py`?
- **Resolution**: Re-verify against the current `plan_review_panel.py` failure branch. Route `proc.stderr` through `redact.redact` before writing the failure log and before re-surfacing on stderr; preserve the durable-log shape and KV contract from #4747.
- **Source**: codebase (verification deferred to Step 2b)

## Decision 5: Item 3 Python/Bash launcher parity scope
- **Question**: Does the Cursor keychain mutex fix need Bash parity in `scripts/lib-cursor-auth.sh`?
- **Resolution**: Verify retirement status of `scripts/lib-cursor-auth.sh` (prior run flagged it retired per `python/migrated-scripts.tsv`). Keep parity across current Python launcher surfaces and docs only; do not edit retired Bash surfaces.
- **Source**: codebase (verification deferred to Step 2b)

## Scope summary
- In scope: fix items 1, 2, 3, 10; verify-then-pin-or-drop items 4, 6, 7; add tests for items 8, 9; lightweight docs sync for item 5.
- Hard constraints: preserve default probe latency; keep auth/transient/timeout retry budgets independent; preserve the #4747/#4765 panel-failure log + KV contract; preserve existing diagnostic headings and byte caps.
- Non-goals: changing default probe behavior; re-splitting the bundle; editing retired Bash launcher surfaces.
