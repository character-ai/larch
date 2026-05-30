# test-implement-anti-polling-rule.sh

Regression harness pinning the AGENTS.md anti-polling-loop rule and the Step 5 script-delegation literal in `skills/implement/SKILL.md`.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. The rule lives in two places:

- `AGENTS.md` — the canonical bullet covering both Monitor and Bash polling loops.
- `skills/implement/SKILL.md` — Step 5 delegates reviewer waiting to `scripts/run-step5-review.sh` instead of ad-hoc polling loops.

Family B background+monitor pairing assertions were removed in breadcrumbs Stage 3 (#3118); Stage 4 removes the remaining skill-fence prose.

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- The harness also pins the AGENTS.md per-turn output-file read ban (`poll the task output file once per turn`) on the `/implement` delivery path (issue #3195).
- `skills/implement/SKILL.md` Step 5 references `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh`.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in exactly one `test-harnesses-N` shard target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.
