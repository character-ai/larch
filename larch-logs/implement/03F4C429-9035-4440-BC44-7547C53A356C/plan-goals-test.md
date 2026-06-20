## Goal
Implement issue #4841: [IMPLEMENTING] [BUG] Dynamic plan-review prompts skip the render scaffold (raw prompt_body sent).

## Implementation Plan
## Summary

In `/design` Step 3 plan review, optional dynamic scout-proposed reviewer slots are dispatched with **only the scout's raw `prompt_body`** as their entire prompt. They never receive the `render plan-review` scaffold that static slots get (explicit plan-file path, "AFTER this PR lands" framing, the mandatory TSV/sentinel output contract, and the scope anchor). One unified defect produces two observed failures: dynamic reviewers review the wrong `plan.txt`, and dynamic reviewers emit prose that is dropped as `NOT_SUBSTANTIVE`.

## Original report

Observed during a live `/design` run (larch 51.1.9) on a small plan. Round 1 launched 8 static slots (Cursor + Codex x arch/innovation/pragmatic/requirements) plus 4 dynamic scout slots (`semantics-guard`, `scope-guard` x Cursor + Codex). All 8 static slots returned OK. 3 of the 4 dynamic slots were dropped `NOT_SUBSTANTIVE`, and dynamic-slot findings cited committed `larch-logs/design/<other-run>/plan.txt` artifacts from unrelated runs instead of the plan under review. Outcome was not corrupted (the panel voted those findings down), but dynamic reviewer coverage was effectively lost and the ballot was polluted with off-target findings.

## Reproduction scenario

1. Run `/design <issue>` on an issue whose Step 2b drafter scout emits a non-empty `$DESIGN_TMPDIR/scout-plan-manifest.json` (one or more dynamic archetypes).
2. Let Step 3 plan review run with both Codex and Cursor present.
3. Inspect the rendered dynamic prompts at `$DESIGN_TMPDIR/plan-review/round-1/dyn-*-plan-*.prompt` and compare to a static `*-plan-arch-output.txt.prompt`.
4. Inspect `$DESIGN_TMPDIR/plan-review/round-1/round-summary.env` and the per-slot collector statuses.

Observed: dynamic `.prompt` files contain only the scout `prompt_body`; static `.prompt` files contain the full reviewer scaffold. Several dynamic slots come back `NOT_SUBSTANTIVE`, and dynamic findings reference `larch-logs/design/*/plan.txt` paths.

## Expected behavior

Dynamic plan-review slots should be rendered through the same scaffold as static slots: the explicit `$DESIGN_TMPDIR/plan.txt` path to review, the "plan describes the codebase AFTER this PR lands" framing, the mandatory TSV-header / `{"no_issues_found": true}` sentinel output contract, and the binding scope anchor. The scout's `prompt_body` should replace only the role line, per the documented design in `skills/design/references/plan-review.md` ("dynamic prompts use the same renderer with per-slug bodies"; "dynamic assembly uses `tail -n +2` so only the role line is stripped").

## Observed behavior

- Dynamic slot prompts are the raw scout `prompt_body` only. Example rendered dynamic prompt is a single sentence ending "...follow the output-format rules from your outer wrapper exactly" — but there is no outer wrapper supplying those rules; that sentence is the whole prompt.
- Symptom 1 (wrong-file grounding): with no plan path in the prompt, the reviewer greps the repo and reviews a committed `larch-logs/design/<other-run>/plan.txt`. In the observed run, `dyn-codex-plan-scope-guard` reported "Scope creep found in `larch-logs/design/04E1791D-…/plan.txt`" (a different issue's committed plan), and ballot items cited `larch-logs/design/091F33CE-…/plan.txt` line numbers. Off-target references reached `ballot.txt` and `findings-in-scope.md`.
- Symptom 2 (`NOT_SUBSTANTIVE` drops): with no TSV/sentinel contract, reviewers emit prose. `round-summary.env` showed `COLLECT_OK_COUNT=9 COLLECT_FAILURE_COUNT=3`; the 3 failures were all dynamic (`dyn-cursor-plan-semantics-guard`, `dyn-cursor-plan-scope-guard`, `dyn-codex-plan-scope-guard`), each `STATUS=NOT_SUBSTANTIVE`, `FAILURE_REASON=structured records not found after repair`. Only `dyn-codex-plan-semantics-guard` survived among the four dynamic slots, which indicates non-deterministic format compliance rather than a hard per-vendor rule.

## Root cause analysis

Single root cause: dynamic slots bypass `render plan-review`. Concretely:

- `python/plan_review_panel.py` `_static_slot_rows` (function near the top of the file) shells out to `render plan-review --archetype <X> --vendor <v> --plan-file <plan> --design-tmpdir <d> --feature-file <f>` per static slot; `proc.stdout` is the full rendered scaffold.
- `python/plan_review_panel.py` `_load_dynamic_rows` sets `prompt = str(archetype.get("prompt_body") or "").strip()` and returns 4-tuples `(tool, slot, focus, prompt)`. The panel-build merge loop then writes that raw string straight to the slot `.prompt` via `_slot_row(...)` — no `render plan-review` call, no `--plan-file`, no output contract.
- `python/rendering.py` `render plan-review` requires `--archetype` to be one of the fixed `_PLAN_REVIEW_ROLES` (arch / innovation / pragmatic / requirements) and emits the fixed role line. It has no flag to inject a dynamic/custom body, so the `tail -n +2` role-line-swap design documented in `plan-review.md` is not actually wired up.

Static slots are unaffected because they carry both the explicit plan path (correct file) and the explicit output contract (structured records).

## Evidence

- Rendered dynamic prompt (`$DESIGN_TMPDIR/plan-review/round-1/dyn-cursor-plan-scope-guard.prompt`) is one sentence (the scout `prompt_body`); the static `cursor-plan-arch` prompt is the full multi-section scaffold with the plan path and TSV contract.
- `$DESIGN_TMPDIR/plan-review/round-1/round-summary.env`: `COLLECT_OK_COUNT=9 COLLECT_FAILURE_COUNT=3`, `AGGREGATOR_STATUS=ok`, `ACCEPTED_COUNT=0`.
- `execution-issues.md` recorded three `collect-results … NOT_SUBSTANTIVE` entries, all dynamic slots, `FAILURE_REASON=structured records not found after repair`.
- Dynamic findings and ballot text contain `larch-logs/design/<run-id>/plan.txt` cross-run references.
- `python/plan_review_panel.py`: `_static_slot_rows` (render-backed) vs `_load_dynamic_rows` (raw `prompt_body`); the merge loop calls `_slot_row(tool, slot, focus, …/{slot}.txt, …/{slot}.prompt, prompt)` for dynamic rows.
- `python/rendering.py`: `render plan-review` argument parser rejects any `--archetype` not in `_PLAN_REVIEW_ROLES`.
- `skills/design/references/plan-review.md`: documents the intended (but unimplemented) renderer-based dynamic assembly.

NOT a bug (separately assessed, not part of this issue): `python/review_aggregate.py` "input reviewers missing from merge output" is the aggregator validation guard working as designed. In the observed run it caught a transient merge-LLM drop of a static reviewer (`Cursor-Arch`) and forced a retry that recovered cleanly (`AGGREGATOR_STATUS=ok`, that reviewer present on the final ballot).

## Affected files

- `python/plan_review_panel.py` — `_load_dynamic_rows` and the panel-build merge loop produce dynamic slot prompts from the raw scout `prompt_body`; primary fix site.
- `python/rendering.py` — `render plan-review` cannot accept a dynamic body; needs a mode to substitute a scout body into the scaffold (or the scaffold must be assembled in `plan_review_panel.py`).
- `skills/design/references/plan-review.md` — documents the intended dynamic-renderer design that does not match the implementation; update to match the fix.

## Suggested fix(es)

Route dynamic slots through the same scaffold as static slots. Either:

- (a) Add a `render plan-review` mode that accepts a dynamic role/body (for example `--archetype-name` + `--role-line` or `--body-file`) and substitutes the scout `prompt_body` for the fixed role line while keeping the plan-file path, AFTER-PR framing, TSV/sentinel output contract, and scope anchor (matches the documented `tail -n +2` design); or
- (b) Assemble the dynamic prompt in `plan_review_panel.py` by prepending the same scaffold blocks the static renderer emits, with the scout `prompt_body` as the role line.

Then update `skills/design/references/plan-review.md` so the documented design matches the implementation.

Hardening note (same PR or follow-up): reviewer prompts instruct agents to "Explore the codebase following file paths named in the plan", and committed `larch-logs/design/*/plan.txt` artifacts share the basename `plan.txt`. Consider explicitly pinning reviewers to the exact `$DESIGN_TMPDIR/plan.txt` and forbidding reading other `plan.txt` files under `larch-logs/`, as defense in depth for any repo-grepping reviewer.

Acceptance criteria:

- Dynamic plan-review slots receive the full scaffold: explicit `$DESIGN_TMPDIR/plan.txt` path, AFTER-PR framing, TSV-header/sentinel output contract, and scope anchor.
- A regression test asserts a rendered dynamic slot prompt contains the plan-file path and the structured-output contract (TSV header / `no_issues_found` sentinel), not just the raw scout `prompt_body`.
- `skills/design/references/plan-review.md` dynamic-prompt prose matches the actual implementation.

## Open questions

- Should the fix extend `render plan-review` (option a) or assemble the scaffold in `plan_review_panel.py` (option b)? Option (a) keeps a single rendering authority and matches the documented `tail -n +2` design.
- Should the `larch-logs/*/plan.txt` grounding hardening apply to all reviewer prompts (including static and `/review`, `/implement` panels) rather than only dynamic plan-review slots? Static slots stayed on target this run, so this may be a separate hardening issue.

## Test plan
(no test plan section in plan-file)
