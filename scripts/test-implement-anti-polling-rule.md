# test-implement-anti-polling-rule.sh

Regression harness pinning the AGENTS.md anti-polling-loop rule and its mirror inside `skills/implement/SKILL.md` Step 5.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. The rule lives in two places:

- `AGENTS.md` — the canonical bullet covering both Monitor and Bash polling loops.
- `skills/implement/SKILL.md` — Step 5 now delegates review rounds to the foreground `run-step5-review.sh` launcher, which invokes `review-and-fix.sh`. The harness guards that contract and checks the Step 5 block does not reintroduce `run_in_background: true`.

Without the Step 5 foreground-call guard, future quick-mode review work could re-introduce the same anti-pattern under time pressure (the failure mode that motivated #1011 in the first place: a 30-minute stale poller waiting on a Codex run that had already failed).

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- `skills/implement/SKILL.md` contains the foreground-call wording for `run-step5-review.sh`.
- The Step 5 block does not contain `run_in_background: true`.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in exactly one `test-harnesses-N` shard target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.

## Edit-in-sync rules

If you legitimately need to reintroduce background reviewer launches in Step 5, update this harness and document the non-polling wait point in the same PR. The rule's intent must be preserved: no parent-side polling loop waits on a background review job.
