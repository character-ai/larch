# test-implement-anti-polling-rule.sh

Regression harness pinning the AGENTS.md anti-polling-loop rule and its mirror inside `skills/implement/SKILL.md` Step 5.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. Issue #2749 (FINDING_24) inverted the Step 5 half: the supported Family-B pattern is now a paired background+monitor Bash message instead of a single foreground call. The rule lives in two places:

- `AGENTS.md` — the canonical bullet covering both Monitor and Bash polling loops, plus the Family-B background+monitor carve-out.
- `skills/implement/SKILL.md` — Step 5 now delegates review rounds to the background `run-step5-review.sh` launcher paired in the same Bash message with foreground `breadcrumb-monitor.sh`. The harness guards that contract by requiring every `run_in_background: true` line in the Step 5 block to be paired with a `breadcrumb-monitor.sh` invocation in the same block.

Without the Step 5 background+monitor guard, future quick-mode review work could re-introduce unpaired polling loops under time pressure (the failure mode that motivated #1011 in the first place: a 30-minute stale poller waiting on a Codex run that had already failed).

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- `skills/implement/SKILL.md` Step 5 prose contains the literal `Step 5 invokes **one** background+monitor` and references `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`.
- Every `run_in_background: true` line in the Step 5 block is paired with at least one `breadcrumb-monitor.sh` invocation in the same block.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in exactly one `test-harnesses-N` shard target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.

## Edit-in-sync rules

When changing Step 5's launch contract (e.g. dropping or renaming the background launcher or the foreground monitor consumer), update this harness in the same PR. The rule's intent must be preserved: every Step 5 `run_in_background: true` launch is paired with a foreground `breadcrumb-monitor.sh` consumer in the same Bash message; no parent-side polling loop waits on a background review job.
