## Plan

## Approach

Restore the dropped caution in the existing `Security findings` bullet under `## OOS triage gate before manifest`.

Use a terse clause, for example:

`If uncertain whether a finding is security, do not file publicly.`

Keep the change in `agents/_implementer-base.md` as the source. Regenerate both derived implementer prompts. Regenerate the skill-closure baseline because `panel-tier` includes the base and generated agent prompts.

Do not revisit other #5980 compression wording.

## Files to modify/create

### UPDATED: agents/_implementer-base.md

Append the caution to the existing security bullet in the OOS triage gate.

Target meaning:

- Security findings must not fold inline.
- Security findings must not enter OOS filing.
- Uncertain security classification must stay off public filing paths.

### UPDATED: agents/codex-implementer.md

Regenerate with:

`python3 python/cli.py generate codex-implementer`

Do not hand-edit this generated file.

### UPDATED: agents/cursor-implementer.md

Regenerate with:

`python3 python/cli.py generate cursor-implementer`

Do not hand-edit this generated file.

### UPDATED: python/skill-closure-baseline.json

Regenerate with:

`python3 python/cli.py lint skill-closure-growth --write`

Then verify the `panel-tier` token growth is at or under +40 tokens. Expect only small numeric baseline changes.

### MAY_UPDATE: SECURITY.md

Only edit this if the final wording introduces new behavior not already covered by the current security policy. The expected path is no edit, because this restores existing intended routing guidance.

## Edge cases

- Keep the caution on the existing bullet, not as a new paragraph, to limit prompt growth.
- Do not add broader security triage rules. `SECURITY.md` already documents private disclosure and OOS security routing.
- Avoid wording that implies public filing is safe after partial sanitization when classification is uncertain.

## Failure modes

- Generated prompts drift if the derived files are hand-edited or not regenerated.
- `generate check` can fail if generated artifacts are stale.
- `skill-closure-growth` can fail unless the baseline is intentionally regenerated.
- The token delta can exceed the +40 acceptance cap if the restored sentence is too long or duplicated outside the one bullet.

## Testing strategy

Run:

1. `grep -F "If uncertain whether a finding is security, do not file publicly." agents/_implementer-base.md agents/codex-implementer.md agents/cursor-implementer.md`
2. `python3 python/cli.py generate check`
3. `python3 python/cli.py lint skill-closure-growth --skill panel-tier`
4. Inspect `git diff python/skill-closure-baseline.json` and confirm the `panel-tier` token delta is at or under +40.
5. Optionally run `python3 python/cli.py checks run-relevant` if available in the implementation environment.

Note: in this read-only drafting sandbox, `generate check` could not complete because Python could not create a temporary directory. Run it during implementation in a write-enabled environment.

## Acceptance

Run:

1. `grep -F "If uncertain whether a finding is security, do not file publicly." agents/_implementer-base.md agents/codex-implementer.md agents/cursor-implementer.md`
2. `python3 python/cli.py generate check`
3. `python3 python/cli.py lint skill-closure-growth --skill panel-tier`
4. Inspect `git diff python/skill-closure-baseline.json` and confirm the `panel-tier` token delta is at or under +40.
5. Optionally run `python3 python/cli.py checks run-relevant` if available in the implementation environment.

Note: in this read-only drafting sandbox, `generate check` could not complete because Python could not create a temporary directory. Run it during implementation in a write-enabled environment.

review_status: complete
rounds_completed: 1
difficulty: MODERATE
diff_lines: 10
