# test-implement-anti-polling-rule.sh

Regression harness pinning anti-polling-loop, Monitor-ban, and premature-notification recovery rules across `AGENTS.md`, `skills/implement/SKILL.md`, `skills/design/SKILL.md`, `skills/shared/design-background-wait.md`, and `skills/shared/orchestrator-never.md`.

## Purpose

Issue #1011 extended the original Monitor-only rule to forbid Bash `run_in_background` polling loops (`for`/`while`/`until` + `sleep`) used to wait on another `run_in_background` job. Issue #4110 adds the result-file variant for `/design` Step 3. Issue #4268 adds explicit Monitor-ban and premature-notification recovery-contract surfaces. The shared `/design` background-wait anchor keeps the hot-path Step 3 anti-polling literal and post-notification sequence out of repeated `SKILL.md` call sites.

The harness pins these surfaces:

- `AGENTS.md`: the canonical bullet covering Monitor, Bash polling loops, the foreground-terminal-sentinel-probe primary recovery path, and the background-recovery-waiter ban (#4725).
- `skills/implement/SKILL.md`: Step 5 delegates reviewer waiting to `skills/implement/scripts/step-5-review.sh` instead of ad-hoc polling loops, and the NEVER list bans Monitor fallback while keeping implement premature-notification recovery notification-driven.
- `skills/shared/design-background-wait.md`: the `/design` Step 3 result-file sleep-loop ban, background-recovery-waiter ban, exact compact-table missing warning, and post-notification sequence.
- `skills/design/SKILL.md`: the five `/design` hot-path loci use imperative `Read and apply ##` load contracts for `skills/shared/design-background-wait.md` instead of carrying full duplicated boilerplate.
- `skills/shared/orchestrator-never.md`: the shared NEVER list carries the `run_in_background` result-file sleep-loop ban, the foreground-terminal-sentinel-probe primary recovery wording, and the background-recovery-waiter ban (#4725).

Family B background+monitor pairing assertions were removed in breadcrumbs Stage 3 (#3118); Stage 4 removes the remaining skill-fence prose.

## Invariants asserted

- `AGENTS.md` carries the extended phrasing `Don't spawn a Monitor or a Bash` and explicitly mentions the `for`/`while`/`until` + `sleep` form.
- The harness also pins the AGENTS.md per-turn output-file read ban (`poll the task output file once per turn`) on the `/implement` delivery path (issue #3195).
- `skills/implement/SKILL.md` Step 5 references `skills/implement/scripts/step-5-review.sh`.
- `skills/shared/design-background-wait.md` carries the exact literal ``NEVER poll `.step3-review-result.env` with a sleep loop.`` exactly once.
- `skills/design/SKILL.md` carries zero copies of that Step 3 anti-polling literal.
- `skills/shared/design-background-wait.md` carries `NEVER launch a background recovery waiter` and the exact warning `**⚠ Reviewer status table omitted: pre-rendered table not found.**`.
- `skills/design/SKILL.md` references `skills/shared/design-background-wait.md` at these loci:
  - Verbosity Control, `Post-notification for Step 3 waits`.
  - Final summary block.
  - Step 3 first launch, `design-step3-review.sh` without `--starting-round`.
  - Step 3 resume, `design-step3-review.sh --starting-round`.
  - Step 5c, `design-step5c.sh`.
- Each shared-anchor locus carries the imperative `Read and apply ##` load contract with the expected section name.
- Step 3 launch and resume keep the `.completed/step-3-terminal` inline parameter.
- Final summary and Step 5c keep `confirmation purpose: completion` in their inline parameter blocks.
- `skills/design/SKILL.md` carries zero copies of extracted boilerplate markers: `**Immediate-background wait rule**:` and `1. **Completion gate**:`.
- `/design` Step 3 still pins the `.completed/step-3-terminal` sentinel for the sanctioned foreground recovery probe while keeping `.completed/step-3` as the Step 3b routing milestone.
- `/design` Step 3 still pins that `NEXT_ACTION` routing requires `.completed/step-3-terminal` before envelope parsing and `.completed/step-3` before Step 3b.
- `skills/shared/orchestrator-never.md` carries the exact shared NEVER literal for `run_in_background` result-file sleep loops.
- `skills/shared/orchestrator-never.md` carries the foreground-probe primary recovery wording `the sanctioned recovery path is one foreground terminal-sentinel probe per explicit recovery turn`.
- `skills/shared/orchestrator-never.md` carries the background-recovery-waiter ban `NEVER launch a background recovery waiter` (#4725).
- `AGENTS.md` carries the foreground-probe primary recovery wording `the sanctioned recovery path is one foreground non-sleeping` and the probe-form wording `one foreground non-sleeping [ -f … ] or test -f … probe against the relevant terminal completion sentinel`.
- `AGENTS.md` carries the background-recovery-waiter ban `NEVER launch a background recovery waiter` and the platform-assumption wording `the backgrounded task reliably re-fires a <task-notification> on completion` (#4725).
- `skills/implement/SKILL.md` carries the exact Monitor-ban literal ``NEVER use the `Monitor` tool anywhere within the `/implement` orchestrator``.
- `skills/implement/SKILL.md` tells operators to `end the turn and wait for the next <task-notification>` instead of probing `$DESIGN_TMPDIR` or design-only sentinels, and it documents that `/implement` does not write `$IMPLEMENT_TMPDIR/.completed/*-terminal` sentinels today.
- `skills/implement/SKILL.md` states that `/implement` notification-only recovery and `/design` foreground terminal-sentinel probing are intentionally different contracts, not contradictory guidance.
- `skills/implement/SKILL.md` carries the background-recovery-waiter ban `NEVER launch a background recovery waiter` (#4725).
- `skills/implement/SKILL.md` carries the exact fallback ban `Do NOT fall back to Monitor`.
- `skills/design/SKILL.md` carries the exact Monitor-ban literal ``NEVER use the `Monitor` tool anywhere within the `/design` orchestrator``.
- `skills/design/SKILL.md` carries the foreground-probe primary recovery wording `the sanctioned recovery path is one foreground, non-sleeping terminal-sentinel probe per recovery turn` and the foreground-probe wording `Foreground terminal-sentinel probe: after a premature notification with non-empty task output`.
- `skills/design/SKILL.md` carries the background-recovery-waiter ban `NEVER launch a background recovery waiter` (#4725).
- `skills/design/SKILL.md` carries the exact fallback ban `Do NOT fall back to Monitor`.

## Wiring

- `make test-implement-anti-polling-rule` runs the script.
- Listed in exactly one `test-harnesses-N` shard target in `Makefile`.

## Run manually

```bash
bash scripts/test-implement-anti-polling-rule.sh
```

Exits 0 on success, 1 on the first failed assertion.
