## Proposed Design Outline

### Goals
- Add full signal-aware detach-and-reattach to `step-5-review.sh` so SIGTERM does not stamp a false "review done" terminal sentinel
- Add an orphan-cap `--orphan-timeout-s` to both Step 3 and Step 5 detached loops so an unattended loop self-terminates after a configurable wall-clock bound
- Document Step 8's persist-and-resume pattern as the intended and sufficient signal-resilience design

### Non-goals
- Changing Step 5 or Step 3 review logic, round structure, or coder dispatch
- Adding orchestrator-side (SKILL.md Bash) signal handling; wrappers own it
- Migrating Step 8 to full detach-and-reattach

### Approach sketch
- Refactor `step-5-review.sh` to run `review-and-fix step5 --new-process-group` in background (`&`), write loop identity, trap TERM/HUP/INT, write detached marker on signal, and reattach on next invocation
- Add Python support: `--new-process-group` in `review-and-fix step5`, new CLI verbs `review-and-fix write-loop-identity` / `await-loop-identity` / `normalize-status` using new `IMPLEMENT_STEP5_*` config constants
- Add `--orphan-timeout-s` to `review-and-fix step5 --mode loop` and `plan-review run --mode loop`; loop emits `orphan-timeout` status and stops if wrapper has not reattached within the bound
- Pass `--orphan-timeout-s 7200` from the shell wrappers when launching detached loops; update `design-step3-review.sh` similarly
- Update `step-8-ship.md` to explicitly document persist-and-resume as the intentional signal-resilience design

### Surfaces in scope
- `skills/implement/scripts/step-5-review.sh` + `step-5-review.md`
- `skills/design/scripts/design-step3-review.sh`
- `skills/implement/scripts/step-8-ship.md`
- `python/larch/core/config.py`
- `python/larch/review/review_and_fix.py`
- `python/larch/cli.py`
- Test harness (new): `skills/implement/scripts/test-step-5-review.sh` + `.md`
- Test harness (update): `skills/design/scripts/test-design-step3-review.sh`

### Open questions
- Default orphan timeout: recommend 7200s (2 hours), shorter than TIMEOUT_S=21600 so stranded loops stop well before session expiry.
