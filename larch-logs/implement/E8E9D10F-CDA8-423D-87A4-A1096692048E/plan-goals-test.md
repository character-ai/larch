## Goal
Implement issue #3648: [IMPLEMENTING] PR2: Remove the plan-quality assessor (/design Step 3.6) entirely\n\n# PR2 — Remove the plan-quality assessor (totally).

## Implementation Plan
# PR2 — Remove the plan-quality assessor (totally)

> **Revised 2026-06-07** after PR #3641 (Fixes #3628) merged: the assessor surface grew — Step 3.6 now has a **Revert** path backed by `snapshot-plan-round.sh revert-round`, and Gate B's new **default auto-apply** is framed as "assessor-gated." A prior `/implement` run (run `2DA6BC30-…`, comments below) was stopped against the pre-revision body; **re-plan from this revision**. Work from current `main` (must include PR #3641).

**Part of a 3-PR split of #3644.** This PR is **independent** of the voting changes and can proceed in parallel with PR1 (#3647, EXONERATE) in a separate clone; PR3 (#3649) is blocked by both. This PR overlaps PR1/PR3 only on `skills/design/SKILL.md` and `scripts/test-design-structure.sh`, in different regions. Implementer: Sonnet.

Read `AGENTS.md`, `KARPATHY_CLAUDE.md`, `BASH_AUTHORING.md`, and `skills/design/references/approval-gates.md` before starting.

## Context

`/design` Step 3.6 runs a "plan-quality assessor": a HARD-only, round≥2 pass that judges whether the **whole-plan** delta is BETTER/WORSE/TIE vs the previous round, default-open, acting only on a WORSE-majority. It is expensive (time + tokens on every HARD round ≥2, whether or not it fires), information-poor (coarser than the per-finding judge panel that ran immediately before it, with no information that panel lacked), and only marginally useful. Remove it entirely, with **no replacement** — no meter, no holistic backstop.

**Post-#3628 nuance (PR #3641, merged 2026-06-07):** Gate B now **auto-applies accepted findings by default** (the `--approve` flag restores the explicit per-round prompt), and the assessor's WORSE-majority verdict — now an `AskUserQuestion` with **Continue / Revert this round's findings & proceed / Stop** — serves as the brake on that auto-apply, with `snapshot-plan-round.sh revert-round` doing the rollback. Removing the assessor removes that brake. That is intentional:

- **KEEP** Gate B default auto-apply and the `--approve` escape (deliberate behavior from #3628 — do not revert to ask-first).
- The durable protection becomes the necessity-gated judging in #3649; until #3649 lands there is a short window where auto-apply runs without the assessor brake — accepted (the brake is default-open and rarely fires; `--approve` remains the manual brake).

The assessor is `/design`-only; `/implement` has none.

## E1 — Delete (assessor-owned files)

```
skills/design/scripts/assess-plan-round.sh            (+ .md, test-assess-plan-round.sh + .md)
skills/design/scripts/dispatch-plan-assessors.sh      (+ .md, test-dispatch-plan-assessors.sh + .md)
skills/design/scripts/design-plan-quality-assessor.sh (+ .md, test-design-plan-quality-assessor.sh + .md)
skills/design/scripts/tally-plan-assessor.sh          (+ .md, test-tally-plan-assessor.sh + .md)
skills/shared/scripts/render-assessor-prompt.sh       (+ .md, test-render-assessor-prompt.sh + .md)
skills/design/references/assessor.md
```

## E2 — Edit (assessor-referencing files — do NOT delete)

- `skills/design/SKILL.md` — remove the entire Step 3.6 orchestration: the `_assessor_*` vars and `design-plan-quality-assessor.sh` call; the `rc == 10` WORSE-majority branch with its trusted-trailer parsing (`LARCH_ASSESSOR_TRUSTED_TRAILERS_BEGIN`, `LARCH_ASSESSOR_ROUND_NUM`); the **Continue / Revert / Stop** `AskUserQuestion` and all three branches — including the Revert fence that invokes `snapshot-plan-round.sh revert-round`, its `append-execution-issue.sh` `Warnings` entries, and the `step-3.6` marker writes; the `timing-ledger.sh mark "design Step 3.6 — assessor"` line; and the `⏩ 3.6: assessor — …` skip breadcrumbs. Route Gate B (Step 3.5) → Step 3b directly. Remove `cancelled-assessor-worse` from the `SUMMARY_OUTCOME` enum. **Do not renumber** other steps (3b, 4, …).
- `skills/design/references/approval-gates.md` — remove Step 3.6 references, the "Assessor Stop cancellation" item, the skip breadcrumbs, and the "assessor-gated" framing around Gate B default auto-apply. **Keep the default auto-apply behavior and `--approve`** — only the assessor-gate narrative goes. Fix the Gate-B → Step-3b flow prose.
- `skills/design/references/flags.md` — keep the `--approve` flag; strip its assessor mention.
- `skills/design/scripts/render-final-summary.sh` (+`.md`, `test-render-final-summary.sh`) — remove the `cancelled-assessor-worse` outcome branch/case.
- `Makefile` — remove the assessor test targets (`test-assess-plan-round`, `test-dispatch-plan-assessors`, `test-design-plan-quality-assessor`, `test-tally-plan-assessor`, `test-render-assessor-prompt`, and any other assessor-named registrations the grep shows — there are ~13 mentions).
- `scripts/launch-claude-subprocess.sh` (+`.md`, `scripts/test-launch-claude-subprocess.sh`) — remove the assessor launch-lane / timing-kind references.
- `scripts/lib-timing-kinds.sh` — remove assessor timing-task kinds (e.g. `*-plan-assessor`) from `TIMING_TASK_KINDS_ALLOWED` (see `.claude/rules/timing-task-kind-allowlist.md`).
- `skills/design/scripts/step-name-registry.tsv` — remove the Step 3.6 row.
- `scripts/test-design-structure.sh` (+`.md`) — remove assertions that grep for assessor anchors, `revert-round`, and `cancelled-assessor-worse`, including any Check-16 timing-kind pins that list assessor kinds.
- `skills/design/scripts/test-design-pause-resume.sh` — remove `step-3.6` marker expectations from the pause/resume state walk.
- Clean incidental mentions in: `docs/workflow-lifecycle.md`, `scripts/relevant-checks.sh`, `skills/design/scripts/design-postplan-emit.sh`, `skills/design/scripts/lib-phase-driver.md`, `scripts/degraded-tools-gate.sh`, `scripts/dispatch-with-waterfall.md`, `scripts/lib-scope-anchor-handoff.md`, `scripts/lib-untrusted-block.md`.

## E3 — PRESERVE (shared infra the assessor merely consumed) — with one orphan exception

- `skills/design/scripts/snapshot-plan-round.sh` (+`.md`, `test-snapshot-plan-round.sh`) — the round cursor and `plan.txt-original` / `plan-after-round-N.txt` snapshot machinery is used by `run-step3-review.sh`, `design-postplan-emit.sh`, `check-plan-size.sh`, and the **Gate-C re-run** path. **Keep all of that fully intact.**
- **Exception (orphan cleanup):** the `revert-round` subcommand (added by PR #3641) has exactly one caller — the Step 3.6 Revert fence this PR deletes. Remove the `revert-round` subcommand, its `test-snapshot-plan-round.sh` cases, and assessor-flavored comments; keep `read-cursor` and every other subcommand untouched.

This is the landmine in this PR: the assessor reads (and, since #3641, reverts) snapshots, so it is tempting to delete the snapshot machinery with it. Don't — snapshots are upstream shared infra; only `revert-round` is orphaned.

## Boundary with the other PRs

- **KEEP** Gate B default auto-apply and all `--approve` plumbing: `skills/design/scripts/parse-design-argv.sh`, `design-init-runparams.sh`, `scripts/write-run-params.sh`, `skills/design/scripts/test-gate-b-apply-mode.sh` (verified assessor-free) — only the assessor-gate framing is removed.
- **Do NOT touch** `skills/design/scripts/auto-fix-plan-commands.sh` / `.md` / `test-auto-fix-plan-commands.sh` (the cross-vendor validator auto-fix, Component D of #3628) — its follow-up coverage work is tracked separately in #3640.
- Do NOT touch voting, EXONERATE, the judge/voter prompts, reviewer templates, or scoring — those are #3647/#3649.
- Expect to share only `skills/design/SKILL.md` and `scripts/test-design-structure.sh` with #3647/#3649; edit different regions. If #3647 lands first, rebase those two files.

## Definition of done

1. `/design` runs with no Step 3.6 / assessor invocation; Gate B default auto-apply (and `--approve`) still works and routes to Step 3b; `snapshot-plan-round.sh` (minus `revert-round`) and the Gate-C re-run path still work.
2. Grep sweep: `grep -ri assessor` across `skills/ scripts/ docs/ Makefile .github` returns zero hits (committed `larch-logs/` run-history excluded); no `revert-round` references remain; `SUMMARY_OUTCOME` has no `cancelled-assessor-worse`; `step-name-registry.tsv` has no 3.6 row.
3. `bash scripts/relevant-checks.sh` and `make lint` pass; `scripts/test-design-structure.sh`, `test-render-final-summary.sh`, `test-design-pause-resume.sh`, `test-snapshot-plan-round.sh`, `test-launch-claude-subprocess.sh`, and the design suite pass; `make lint-bash32` clean.
4. `docs/topology.md` regenerated if any topology count changed (assessor slot/lane counts may drop).


## Test plan
(no test plan section in plan-file)
