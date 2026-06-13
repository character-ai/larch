## Proposed Design Outline

### Goals
- Extract the 8-command clarify branch (Step 0b sub-step 3) into `design-clarify.sh --phase fetch` + `--phase publish`.
- Add a new `clarify comment-fetch` Python CLI verb to retrieve the request comment body by `LAST_REQUEST_ID`.
- Provide an offline harness covering plan-write failure, publish failure, empty `SESSION_ID`, and the happy path.

### Non-goals
- Do not change comment, label, or rename behavior (byte-compatible with current Step 0b sub-step 3).
- Do not move `AskUserQuestion` or the Write-tool response composition into the wrapper.
- Do not change the Final summary fence or the `SUMMARY_OUTCOME=cancelled-clarify` handoff semantics.
- Do not add new clarify states or extend the `python/clarify.py` state machine beyond the fetch verb.

### Approach sketch
- Add `clarify comment-fetch` to `python/clarify.py` + `python/cli.py`; reuse `issue_comments_list_read` to find the request comment by marker and write body to `--output-file`.
- Create `design-clarify.sh --phase fetch`: runs `clarify state`, then `clarify comment-fetch`; writes `$DESIGN_TMPDIR/clarify-request-body.md`; emits `STATE=`, `LAST_REQUEST_ID=`, `CLARIFY_REQUEST_BODY_PATH=`.
- Create `design-clarify.sh --phase publish`: reads `$DESIGN_TMPDIR/clarify-response.md` (fixed convention); runs redact → named-block write → publish → comment-post → label remove → conditional rename; exits 0 with status KVs.
- Update `SKILL.md` Step 0b sub-step 3 to two Bash calls + existing Final summary fence; add `design-clarify.sh` to wrapper contract inventory.

### Surfaces in scope
- `skills/design/scripts/design-clarify.sh` (new)
- `skills/design/scripts/design-clarify.md` (new)
- `skills/design/scripts/test-design-clarify.sh` (new)
- `skills/design/scripts/test-design-clarify.md` (new)
- `python/clarify.py` (add `clarify_comment_fetch_main`)
- `python/cli.py` (add `("clarify", "comment-fetch")` dispatch entry)
- `python/test_clarify.py` (add tests for `comment-fetch` verb)
- `skills/design/SKILL.md` (update Step 0b sub-step 3 + wrapper inventory)

### Open questions
- None.
