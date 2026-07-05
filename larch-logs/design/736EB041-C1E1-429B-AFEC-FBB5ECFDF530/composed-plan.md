## Plan

## Approach

Make the smallest prose and harness update that covers the approved scope.

- Treat the repeat rule as a prompt contract, not a runtime change.
- Use one consistent wording for Step 3 repeats: prefix-identical repeat, first 200 chars.
- Keep the Step 5c rule parallel to the shared immediate-background wait rule.
- Add structural `contains` and `not_contains` pins for the new and removed literals.

## Files to modify/create

### UPDATED: `AGENTS.md`

Add the repeat carve-out to the `/design` notification convention paragraph.

- Keep the existing empty-output sentence.
- Add that prefix-identical repeat notifications (first 200 chars) for the same wait also end silently when the relevant terminal sentinel is absent.
- Do not expand the paragraph beyond this contract.

### UPDATED: `skills/shared/orchestrator-never.md`

Update NEVER #3 for `/design` premature notification recovery.

- Add the same repeat carve-out near the existing empty-output rule.
- Say the repeat is prefix-identical over the first 200 chars.
- Preserve the one foreground probe rule for new or changed non-empty output.

### UPDATED: `skills/shared/design-background-wait.md`

Clarify the Step 3 fingerprint contract.

- Replace the ambiguous `byte-identical` wording with `prefix-identical`.
- State that the fingerprint is the first 200 chars.
- Keep the silent-yield action unchanged: no tool call, `ScheduleWakeup`, or prose when `.completed/step-3-terminal` is absent.

### UPDATED: `skills/design/SKILL.md`

Update the `/design` prompt contract in three places:

1. **Anti-pattern #5**: rename the title to cover both empty-output and prefix-identical-repeat notifications. Update the body to use `prefix-identical` and `first 200 chars`. In the body, replace the hardcoded `step-3-terminal` sentinel with the active wait's terminal sentinel reference (or point to `design-background-wait.md` for the generalized rule). Add an explicit ordered Apply block to anti-pattern #5: empty output → silent yield; prefix-identical repeat (first 200 chars) with absent terminal sentinel → silent yield; new or changed non-empty → at most one foreground probe.

2. **Step 3 post-loop routing preamble**: rewrite the premature-notification handling paragraph before the `NEXT_ACTION` table to use the same ordered contract: empty output → silent yield; prefix-identical repeat (first 200 chars) with absent `.completed/step-3-terminal` → silent yield; new or changed non-empty premature output → at most one foreground probe; proceed to post-notification sequence only after the terminal sentinel is present.

3. **Step 5c routing prose**: add an inline repeat carve-out sentence so repeat notification handling is explicit, not implied by the shared reference.

### UPDATED: `scripts/test-design-structure.sh`

Pin the new contract literals and remove stale ones.

- Add `AGENTS_MD="$ROOT/AGENTS.md"`.
- Add `contains "$AGENTS_MD"` for the Tier-1 repeat carve-out literal (pinning a substring that can only pass with the new carve-out text).
- Add `contains "$ORCH_NEVER_MD"` for the shared NEVER repeat carve-out literal.
- Add `contains "$SHARED_DESIGN_WAIT_MD"` for `prefix-identical` and `first 200 chars` in the Step 3 fingerprint paragraph.
- Add `not_contains "$SHARED_DESIGN_WAIT_MD" 'byte-identical'` so stale wording cannot survive alongside the new term in that paragraph.
- Add `contains "$SKILL_MD"` for the renamed anti-pattern #5 title.
- Add `contains "$SKILL_MD"` for the ordered Apply block in anti-pattern #5 (a substring present only in that ordered rule).
- Add `contains "$SKILL_MD"` for the Step 3 post-loop routing update (a substring unique to the rewritten ~line-413 preamble, not satisfiable by anti-pattern #5 alone).
- Add `contains "$SKILL_MD"` for the Step 5c repeat routing prose.
- Keep labels specific enough to identify the missing surface.

### UPDATED: `scripts/test-implement-anti-polling-rule.sh`

Retarget the anchor for anti-pattern #5 after the heading rename.

- Update the heading substring the test anchors on to match the new anti-pattern #5 title.
- Add or update a pin for `prefix-identical` or `first 200 chars` so a prose regression fails CI.

### UPDATED: `scripts/test-implement-anti-polling-rule.md`

Update sibling contract to note the heading retarget and added prefix-identical pin.

### UPDATED: `scripts/test-design-structure.md`

Update the harness description.

- Note that the harness pins the repeat-fingerprint silent-yield contract across Tier-1 prose, shared wait prose, and `/design` Step 3 post-loop routing and Step 5c routing.

## Edge cases

- Do not imply a new runtime fingerprint algorithm. The prose must match the existing first-200-chars prefix behavior.
- Do not remove the existing empty-output `#5240` contract while adding the repeat case.
- Keep `.completed/step-5c` listed as not completion.
- The anti-pattern #5 body must not bind to a single hardcoded terminal sentinel; use the active wait's terminal sentinel name or a generic reference.
- The Step 3 post-loop routing preamble update must use ordered handling (empty → repeat → probe), not unordered.
- The `contains` pin for Step 3 post-loop routing must anchor on a substring unique to that paragraph, not satisfiable by anti-pattern #5 text alone.

## Failure modes

- A future reader may still follow the old probe-on-any-non-empty rule if AGENTS.md lacks the carve-out.
- A future edit may regress the contract if the harness pins only the empty-output path.
- Ambiguous `byte-identical` wording may make first-200-char prefix matches look like full-output matches.
- If the anti-polling harness still anchors on the old heading, it will silently pass even after the heading rename.
- If the Step 3 post-loop preamble is not updated, readers can still probe on repeat notifications even after anti-pattern #5 and Step 5c are fixed.

## Testing strategy

Run only the changed-file harness path.

1. `make test-design-structure`
2. `make test-implement-anti-polling-rule`
3. If Markdown lint is available and relevant checks are desired, run `python3 python/cli.py checks run-relevant` after implementation.

## Notes for implementer

- This is docs and harness work only.
- Do not change `scripts/hook-bg-poll-guard.sh` or any Python behavior.
- No `SECURITY.md` update is needed because this does not change secret handling or permissions.

difficulty: MODERATE
confidence: high

## Acceptance

Run only the changed-file harness path.

1. `make test-design-structure`
2. `make test-implement-anti-polling-rule`
3. If Markdown lint is available and relevant checks are desired, run `python3 python/cli.py checks run-relevant` after implementation.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_lines: 30
