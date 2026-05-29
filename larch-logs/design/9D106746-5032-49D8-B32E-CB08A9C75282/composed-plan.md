## Plan


Make SIMPLE the default `/design` tier and remove the retired SIMPLE-tier public argv flag entirely. Keep `--hard` as the sole tier flag (opt-in to HARD). No backward compatibility. Remove every live-surface mention of that retired argv token (runtime prose, references, docs, tests). Retire the now-dead `cancelled-tier-gate` outcome, because the interactive tier gate that produced it is removed.

Tier semantics do not change. SIMPLE still means no sketches, no dialectic, full review panel, 3 review runs. HARD still means 4 sketches, dialectic, full panel, 5 review runs. Only the default and the public flag surface change.

## Files to modify/create

### UPDATED: `skills/design/SKILL.md`
The core change. Edit sites (refer by anchor, not line number):
- Frontmatter `argument-hint`: replace the legacy tier-flag alternation with `[--hard] ...` only. Keep the rest of the hint byte-for-byte.
- **Flags** prose: drop the retired tier flag from the "Public argv allows only" list. Delete the sentence about the mutual-exclusion tier gate ("If no tier flag is set ... the orchestrator MUST run the tier `AskUserQuestion` gate"). State instead: the default tier is SIMPLE; `--hard` selects HARD; any unrecognized or disallowed leading public `--` flag is a hard error before Step 0 and is never treated as positional feature text.
- Flag table: delete the retired tier-flag row. Keep the `--hard` row; reword its Purpose to "opt into HARD (default is SIMPLE)".
- **Mutual exclusion** line: replace with the single-tier-flag rule plus generic disallowed-flag rejection before Step 0. Do not special-case retired flags.
- Step 0b resume-path "Parse public flags (`--hard`, ...)" prose: document only `--hard` in the tier-flag parse list (remove the retired token from that prose).
- Step 0b sub-step 5 (**Tier gate**): replace the interactive gate with a non-interactive **Tier resolution** step — `design_classification` is HARD when `--hard` was parsed, else SIMPLE (the default); no `AskUserQuestion`, no `cancelled-tier-gate`. Keep the existing sub-step numbering (5, 5.5, 5.5-bis, 6) to avoid renumber churn elsewhere.
- Step 0b sub-step 6 tier mapping: reframe the `simple:` mapping as the default — `design_classification=SIMPLE`, `design_classification_reason="default tier: SIMPLE (no --hard)"`, `design_classification_source=caller-forwarded`, `sketch_budget=0`, `review_budget=full`, `workflow_path=SIMPLE`. Keep the `hard:` mapping unchanged.
- Step 0b bash block: change the SIMPLE-branch `design_classification_reason` from the legacy argv-tier reason string to `"default tier: SIMPLE (no --hard)"`. The `if [[ "$design_classification" == SIMPLE ]] ... elif ... HARD` branch is otherwise unchanged (the orchestrator resolves the classification before this block).
- **Final summary block `When` clause** (`### Final summary block`): replace `tier-flag mutual-exclusion abort` with `disallowed public argv abort before Step 0` (no `DESIGN_TMPDIR` yet).
- SUMMARY_OUTCOME enum (Final summary block orchestrator contract): remove `cancelled-tier-gate`.
- Resume-path skip list that names "tier gate": change "tier gate" to "tier resolution".
- Verify the Anti-halt reminder's sub-step transition list still matches the kept numbering; no step numbers change.

### UPDATED: `skills/design/references/flags.md`
- Contract line: drop the retired tier flag from the public-argv list.
- Remove the retired tier bullet. Restructure the tier section: SIMPLE is the default (no flag); `--hard` is the only tier flag and maps to `design_classification=HARD`.
- Mutual-exclusion line: replace with the single-tier-flag rule and the generic "unrecognized or disallowed leading public flag is a hard error before Step 0" rule.
- Keep the `--hard` mapping and every non-tier flag entry unchanged.

### UPDATED: `skills/design/references/approval-gates.md`
- Cross-tier invariant: refer to SIMPLE and HARD tier names only; drop argv flag spellings from the invariant sentence.
- Per-tier behavior: first-time entry prose refers to both tiers (SIMPLE / HARD) without argv flag spellings.
- Gate C **`Other`** paragraph (~line 191): delete the Step 0 tier-gate `Other` contrast (that cancel path is retired with tier-gate removal). State only that Gate C `Other` re-prompts with the **same option set unchanged**, may `cat` the full plan when requested, and **never** cancels `/design` (contrast with structured `See full plan`, which drops itself on re-prompt).

### UPDATED: `scripts/test-design-structure.sh`
- Arg-hint assertion: expect `'[--hard]'` only; update the label text.
- Duplicate-tier assertion (`'if two or more tier flags appear'`): replace with assertions that pin default SIMPLE tier resolution and generic disallowed-public-flag rejection prose; structure-test needles must not embed the removed argv token; update the label.
- Flag-parse-prose pin: tier flag list is `--hard` only in the documented parse prose.
- `approval-gates.md` absent pin: no `Step 0 tier-gate` substring (retired Gate C contrast to removed Step 0 cancel path).
- Leave the SIMPLE-tier assertions (SIMPLE branch, `NO_SKETCHES_CLASSIFIED_SIMPLE`, carve-out, designer emphasis) and the `[--brainstorm] [--manual|-m] [--no-dedup]` pin unchanged.

### UPDATED: `skills/design/scripts/test-design-driver.sh`
- Remove the `simple_row` variable and its removed-tier table-row grep assertion. Keep the `--hard` row assertion and the `design_classification=SIMPLE` / `design_classification=HARD` mapping pins.

### UPDATED: `skills/design/scripts/render-final-summary.sh`
- Remove `cancelled-tier-gate` from the accepted-`--outcome` case branch. The gate (its only producer) is gone, so the outcome is dead.

### UPDATED: `skills/design/scripts/render-final-summary.md`
- **Callers** header count: decrement from twelve to eleven when removing the retired Step 0b caller.
- Step 0b callers bullet: remove `tier-gate cancel` (and its comma); keep title-filter, clarify exit, and already-planned cancel.
- `SUMMARY_OUTCOME` / cancelled-* note (~line 20): align with the post-retirement outcome set — no `cancelled-tier-gate`; same token set as `render-final-summary.sh` allowlist and SKILL.md Final summary enum.

### UPDATED: `skills/design/scripts/test-render-final-summary.sh`
- Empty-mode default block: swap `SUMMARY_OUTCOME=cancelled-tier-gate` for a surviving early-cancellation outcome (`cancelled-sprawl`); update the `## /design run ... — cancelled-...` title grep to match.
- All-outcomes acceptance loop: remove the `cancelled-tier-gate` entry.

### UPDATED: `scripts/render-run-summary.md`
- `/design` outcomes table row: remove `cancelled-tier-gate` from the list.

### UPDATED: `README.md`
- `/design` argument-hint cell: legacy tier alternation becomes `[--hard] ...` only.
- Adjacent prose: "The `--hard` flag selects HARD; the default tier is SIMPLE" while preserving the sketch/review-depth meaning.

### UPDATED: `docs/skills.md`
- Arguments line: tier alternation becomes `[--hard] ...` only.
- Prose: default-SIMPLE / `--hard` for HARD tier selection (reword tier-flag prose accordingly).

### UPDATED: `docs/workflow-lifecycle.md`
- `/design` usage line: `[--hard] ...` only. The following SIMPLE/HARD descriptive sentence stays.

### UPDATED: `docs/installation-and-setup.md`
- "`/design` (SIMPLE, the default) runs the full plan-review panel". Keep the timing and `LARCH_DESIGN_ROUND_CAP` discussion.

### UPDATED: `docs/issue-anchored-plan.md`
- "Design tier selection (`--hard` public argv; default SIMPLE; ...)".

### UPDATED: `.claude-plugin/plugin.json`
- Description string: "issue-anchored `/design` (tier flag `--hard`; default SIMPLE)".

## Approach
- Single-tier-flag model. The orchestrator resolves `design_classification` during flag parsing: HARD when `--hard` is present, SIMPLE otherwise. There is no interactive tier gate.
- Disallowed-flag rejection: rely on a generic "unrecognized or disallowed leading public `--` flag is a hard error before Step 0" rule so retired argv tokens are never swallowed as positional/verbal feature text. No removed-flag-specific message — honors complete excision of the retired token from the live surface while still preventing the footgun.
- Tier semantics are unchanged; only the default and the flag surface move. All SIMPLE-branch prose, the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, and per-tier emphasis stay.
- `cancelled-tier-gate` retirement is a bounded consequence of the Q1 gate removal. The gate is the outcome's only producer (verified), so the outcome becomes dead. Retire it across the SKILL enum, the renderer allowlist, the renderer sibling contract doc, that renderer's test, and the run-summary doc table to keep the outcome enum consistent (SKILL ↔ script ↔ sibling `.md` ↔ run-summary doc ↔ test). If reviewers prefer strict minimalism, this retirement is the one separable sub-change.
- Run-params layer is untouched. `write-run-params.sh` enum-validates only classification/budgets; `--reason` and `--source` are free text; its tests use `--hard` fixtures; `read-design-classification.sh` reads the SIMPLE/HARD enum. Only the SKILL default-SIMPLE `reason` string changes; `source=caller-forwarded` stays (it describes SKILL-to-script forwarding, still accurate).
- Keep the argument-hint and the flag table in sync; the skill-md flag-signature lint cross-validates them, and removing the retired tier flag from both preserves consistency.

## Edge cases
- `/design` with an unrecognized or disallowed leading public flag plus trailing text: hard error before Step 0; the trailing text is not turned into an issue.
- `/design` with multiple disallowed leading public flags: the first violation hard-errors before Step 0 (generic reject-before-Step-0; no run proceeds).
- `/design <issue-N>` or `/design <verbal>` with no tier flag: runs SIMPLE (the new default), no prompt.
- Resume of a run created under the old skill: the pause block stores the resolved tier (SIMPLE/HARD classification), not a retired argv token, so resume is unaffected by the flag removal.
- Completeness: after the edits, a live-surface grep for the retired tier argv token over `*.md`/`*.sh`/`*.json`/`*.txt`/`*.tsv`/`*.toml`, excluding `larch-logs/**`, `.git/`, and dated `CHANGELOG.md`, must return zero rows, mirroring the #3176 retired `--trivial` completeness gate.

## Failure modes
1. Incomplete removal — a stale retired-flag literal lingers in a doc or test. Earliest signal: the completeness grep gate or `test-design-structure.sh`. Mitigation: run the completeness grep before finishing.
2. Test pins drift from prose — `test-design-structure.sh`, `test-design-driver.sh`, or `test-render-final-summary.sh` fail in CI. Earliest signal: `make lint` / the named harnesses. Mitigation: edit the three test files in lock-step with the prose.
3. `cancelled-tier-gate` retired in the renderer allowlist but still documented or emitted — the renderer rejects the outcome, or the sibling contract doc still lists `tier-gate cancel`. Earliest signal: a design run that reaches the (removed) gate, or stale prose in `render-final-summary.md`. Mitigation: confirm the gate is the sole producer (verified), remove it fully from SKILL and scripts, and align `render-final-summary.md` Callers / `SUMMARY_OUTCOME` notes with the post-retirement set.
4. Stale Gate C tier-gate contrast — `approval-gates.md` still documents Step 0 tier-gate `Other` as a terminal cancel. Earliest signal: the new structure-test `absent` pin or a live-surface grep for `Step 0 tier-gate`. Mitigation: rewrite the Gate C `Other` paragraph per the approval-gates edit above.

## Testing strategy
- `bash scripts/test-design-structure.sh` — passes with the updated arg-hint, default-tier, disallowed-flag pins, and `approval-gates.md` absent pin for retired `Step 0 tier-gate` prose.
- `bash skills/design/scripts/test-design-driver.sh` — passes with the removed-tier table-row assertion removed.
- `bash skills/design/scripts/test-render-final-summary.sh` — passes with `cancelled-tier-gate` retired.
- `bash scripts/test-write-run-params.sh` — unchanged; must still pass.
- `bash scripts/relevant-checks.sh` (or `make lint`) — repo-wide lint, including `agent-lint`, the skill-md flag-signature lint, markdownlint, and drift checks.
- Contract doc: `skills/design/scripts/render-final-summary.md` Callers bullet has no `tier-gate cancel`; header count is eleven; cancelled-* note matches SKILL and shell allowlist.
- Completeness gate (manual): live-surface grep for the retired tier argv token (same exclusions as #3176); must return no rows.

## Acceptance

- With no `--hard` flag, `/design` runs SIMPLE (the new default); `--hard` runs HARD. No interactive tier-selection gate fires on a flagless run.
- Passing the removed tier flag (or any unrecognized/disallowed leading public flag) is a hard error before Step 0 and is never swallowed as positional feature text.
- The `cancelled-tier-gate` outcome is retired consistently across `skills/design/SKILL.md`, `skills/design/scripts/render-final-summary.sh`, `skills/design/scripts/render-final-summary.md`, `scripts/render-run-summary.md`, and `skills/design/scripts/test-render-final-summary.sh`.
- A live-surface grep for the removed tier argv token (over `*.md`/`*.sh`/`*.json`/`*.txt`/`*.tsv`/`*.toml`, excluding `larch-logs/**`, `.git/`, and dated `CHANGELOG.md`) returns zero rows.
- SIMPLE and HARD tier semantics are unchanged; the SKILL argument-hint and the flag table stay in sync.
- `bash scripts/test-design-structure.sh`, `bash skills/design/scripts/test-design-driver.sh`, `bash skills/design/scripts/test-render-final-summary.sh`, and `bash scripts/test-write-run-params.sh` pass.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes.

diff_lines: 114
