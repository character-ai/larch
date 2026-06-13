## Proposed Design Outline

### Goals
- Replace ~7 mechanical MAV commands in `SKILL.md` prose with two Bash calls (`--phase pre`, `--phase post`).
- Keep the LLM vote action (read ballot, cast YES/NO, write `voter-main-agent.txt`) in SKILL.md prose.
- Verify byte-compatible outputs (env files, phase files) for `tally-error` and zero-accepted paths via test harness.

### Non-goals
- No change to `persist-retally-step3-env.sh`, `tally-plan-review.sh`, or `record-plan-review-round-timing.sh`.
- No change to the legacy `--mode single` harness path or Gate B flow.
- No automation of the LLM vote judgment step itself.

### Approach sketch
- Create `design-step3-mav.sh` with `--phase pre` (render scope anchor, emit `BALLOT_PATH`) and `--phase post` (tally, persist, timing, Warnings entry, phase write; emit `ACCEPTED_COUNT`, `PHASE`, `TALLY_PLAN_REVIEW_STATUS`).
- Wire the script into `design-run-$PPID.sh` launcher pattern (same as other design step wrappers).
- Update `SKILL.md` MAV block: preserve `_RETALLY_SCOPE_ANCHOR_IN`, call `--phase pre`, LLM votes, call `--phase post`, parse results, then resume fence unchanged.
- Create sibling `.md` contract and `test-design-step3-mav.sh` harness; add Makefile target.

### Surfaces in scope
- `skills/design/scripts/design-step3-mav.sh` (new)
- `skills/design/scripts/design-step3-mav.md` (new)
- `skills/design/scripts/test-design-step3-mav.sh` (new)
- `skills/design/scripts/test-design-step3-mav.md` (new)
- `skills/design/SKILL.md` (MAV block update + wrapper contract inventory)
- `Makefile` (new `test-design-step3-mav` target)

### Open questions
- None.
