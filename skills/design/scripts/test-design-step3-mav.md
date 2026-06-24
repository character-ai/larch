# test-design-step3-mav.sh

Offline harness for `design-step3-mav.sh`.

## Coverage

- Pause gate execs `design-pause-save.sh` before MAV work and surfaces a missing `ISSUE_NUMBER` failure.
- Pre phase reads Step 3 result envs through `scripts/read-result-env.sh`, with primary precedence, secondary absent-key fill, session-env fallback, and symlink rejection.
- Pre phase emits `BALLOT_PATH` in the `DESIGN_STEP3_MAV_KV` frame, prefixes scope-anchor evidence lines, and propagates scope renderer failures.
- Post phase covers accepted findings, zero accepted findings, handled `tally-error` with `NEXT_ACTION=step3b-bypass`, readable malformed voter preservation, legacy single-mode phase preservation, and `ROUND_NUM` artifact precedence.
- Prose regression checks ensure `SKILL.md` and `plan-review.md` delegate MAV mechanics to the wrapper and do not reintroduce prompt-side re-tally anchor binding or raw timing commands.

## Run

```bash
bash skills/design/scripts/test-design-step3-mav.sh
```

Wired through `make test-design-step3-mav` and `test-harnesses-7`.
