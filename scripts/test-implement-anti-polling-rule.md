# test-implement-anti-polling-rule.sh

Regression harness pinning anti-polling-loop, Monitor-ban, and premature-notification recovery rules across `AGENTS.md`, `skills/implement/SKILL.md`, `/design` Step 3, `/design` Anti-patterns, and `skills/shared/orchestrator-never.md`.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. Issue #4110 adds the result-file variant for `/design` Step 3. Issue #4268 adds explicit Monitor-ban and premature-notification recovery-contract surfaces. The harness pins these surfaces:

- `AGENTS.md`: the canonical bullet covering Monitor, Bash polling loops, and narrow single-waiter recovery.
- `skills/implement/SKILL.md`: Step 5 delegates reviewer waiting to `python/cli.py review-and-fix step5` instead of ad-hoc polling loops, and the NEVER list bans Monitor fallback.
- `skills/design/SKILL.md`: both Step 3 immediate-background fences carry the result-file sleep-loop ban and consequence prose, and the Anti-patterns list bans Monitor fallback.
- `skills/shared/orchestrator-never.md`: the shared NEVER list carries the `run_in_background` result-file sleep-loop ban.

Family B background+monitor pairing assertions were removed in breadcrumbs Stage 3 (#3118); Stage 4 removes the remaining skill-fence prose.

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- The harness also pins the AGENTS.md per-turn output-file read ban (`poll the task output file once per turn`) on the `/implement` delivery path (issue #3195).
- `skills/implement/SKILL.md` Step 5 references `${CLAUDE_PLUGIN_ROOT}/python/cli.py review-and-fix step5`.
- `/design` Step 3 carries the exact literal ``NEVER poll `.step3-review-result.env` with a sleep loop.`` exactly twice, covering the initial fence and resume `--starting-round` fence.
- `skills/shared/orchestrator-never.md` carries the exact shared NEVER literal for `run_in_background` result-file sleep loops.
- `AGENTS.md` carries the exact narrow recovery wording `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter`.
- `skills/implement/SKILL.md` carries the exact Monitor-ban literal ``NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator``.
- `skills/implement/SKILL.md` carries the exact narrow recovery wording `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter`.
- `skills/implement/SKILL.md` carries the exact fallback ban `Do NOT fall back to Monitor`.
- `skills/design/SKILL.md` carries the exact Monitor-ban literal ``NEVER use the `Monitor` tool anywhere within the `/design` orchestrator``.
- `skills/design/SKILL.md` carries the exact narrow recovery wording `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter`.
- `skills/design/SKILL.md` carries the exact fallback ban `Do NOT fall back to Monitor`.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in exactly one `test-harnesses-N` shard target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.
