# test-implement-anti-polling-rule.sh

Regression harness pinning the AGENTS.md anti-polling-loop rule and its mirror inside `skills/implement/SKILL.md` Step 5.3 launch sites.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. The rule lives in two places:

- `AGENTS.md` — the canonical bullet covering both Monitor and Bash polling loops.
- `skills/implement/SKILL.md` — inline reminders at the two Step 5 quick-mode parallel-Bash-spawning sites (`5.3-rounds1to3` and `5.3-generic`) that `collect-agent-results.sh` is the wait point.

Without the inline reminders, future quick-mode review work tends to re-introduce the same anti-pattern under time pressure (the failure mode that motivated #1011 in the first place: a 30-minute stale poller waiting on a Codex run that had already failed).

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- `skills/implement/SKILL.md` contains the literal `Do NOT add a Bash polling loop to wait` at least twice (one occurrence per Step 5.3 site).
- The same file references `collect-agent-results.sh` as the wait point.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in the `test-harnesses` aggregate target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.

## Edit-in-sync rules

If you legitimately need to rename `collect-agent-results.sh` or rephrase the Step 5.3 reminder, update both this harness and the corresponding literal in the same PR. The rule's intent must be preserved — only its surface phrasing may evolve.
