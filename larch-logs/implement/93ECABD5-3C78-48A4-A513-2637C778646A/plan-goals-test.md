## Goal
Implement issue #3176: [IMPLEMENTING] Eliminate remaining --trivial flag references from /design\n\nThe `--trivial` tier flag for `/design` was removed (tier consolidation, #2956), but stale references remain across the live runtime/docs/test surface — and they are internally contradictory:.

## Implementation Plan
## Plan

Remove every remaining reference to the removed `/design` `--trivial` tier flag and its `TRIVIAL_DOC_ONLY` classification token from the live runtime, docs, and test surface. The flag is unsupported and **no backward-compatibility affordances are kept** — the Pre-Step-0 friendly hard-error, the `design-pause-load.sh` legacy-tier acceptance, and the negative tests that assert the flag/classification stay rejected are all removed (or generalized when doing so preserves unrelated coverage). After this change `--trivial` is an ordinary unrecognized token; the existing `--simple`/`--hard` duplicate-tier mutual-exclusion stays enforced before `session-setup.sh`.

**Scope boundary (do NOT touch):** committed `larch-logs/**` run artifacts (immutable history); dated `CHANGELOG.md` entries (historical record — e.g. lines mentioning "removed TRIVIAL/quick-review routing"); and the ordinary English word "trivial"/"non-trivial" everywhere it appears (`KARPATHY_CLAUDE.md`, `SECURITY.md`, `skills/implement/references/conflict-resolution.md`, `skills/shared/voting-protocol.md`, `scripts/git-checkout-ours.*`, `scripts/generate-topology-docs.sh`, etc.). The completeness gate below scans for the literal tokens `--trivial` and `TRIVIAL_DOC_ONLY` only, never bare `trivial`.

**Intentionally retained (NOT a `--trivial` flag mention — do not delete):** `scripts/test-design-structure.sh:75` `absent "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_TRIVIAL'` guards a *different* legacy sketch-sentinel token; it protects against that token returning and must stay. `scripts/test-design-structure.sh:33` `contains "$SKILL_MD" '[--simple|--hard]'` is the positive guard that already keeps `--trivial` out of the SKILL argument hint (the substring `[--simple|--hard]` does not appear inside `[--trivial|--simple|--hard]`); it stays as the structural backstop after the negative assertions are removed.

**Group A — docs/prose that wrongly present `--trivial` as a live tier**

### UPDATED: `skills/design/references/flags.md`
- Line 5: drop `--trivial` from the public-argv contract list → `(--simple, --hard, --partition / -p, --brainstorm, --manual / -m, --no-dedup, --run-id)`.
- Line 15: delete the entire `--trivial:` bullet (the `design_classification=TRIVIAL_DOC_ONLY` / `review_budget=quick` mapping).
- Line 20 (`--partition` bullet): delete the clause "Mutually exclusive with `--trivial` (reject before `session-setup.sh` per `SKILL.md` Pre-Step-0 gate)." `--partition` no longer has a tier mutual-exclusion; keep the rest of the bullet.
- Line 21 (`--brainstorm` bullet): delete the "**`--trivial` + `--brainstorm`** is not an argv hard-error … Upgrade to `--simple` / Cancel flow" sentences.
- Line 26 (Mutual exclusion): rewrite to "at most one of `--simple` / `--hard` on argv; duplicate tier flags → hard error before Step 0. `--manual` / `-m` is independent of all other public flags." Drop the `--trivial`+`--partition` and `--trivial`+`--brainstorm` clauses.

### UPDATED: `README.md`
- Line 59: change the argument hint `[--trivial|--simple|--hard]` → `[--simple|--hard]`.
- Line 61: delete "(`--trivial` is the quick-budget tier; `--simple` / `--hard` use larger sketch fan-outs …)" and reword "`-p`/`--partition` is mutually exclusive with `--trivial` and routes Step 2b.5 …" → "`-p`/`--partition` routes Step 2b.5 directly to the decomposition panel when no hard plan-size threshold trips".

### UPDATED: `docs/skills.md`
- Line 51: change the argument hint → `[--simple|--hard]`.
- Line 55: "Tier flags (`--trivial` / `--simple` / `--hard`)" → "Tier flags (`--simple` / `--hard`)"; delete "(mutually exclusive with `--trivial`)" after `-p` / `--partition`.

### UPDATED: `docs/workflow-lifecycle.md`
- Line 81: change the argument hint `[--trivial|--simple|--hard]` → `[--simple|--hard]`.

### UPDATED: `skills/design/references/approval-gates.md`
- Line 43: "first-time entry across all three tiers (`--trivial` / `--simple` / `--hard`)" → "first-time entry across both tiers (`--simple` / `--hard`)".

**Group B — enforcement machinery, dead branches, and tests**

### UPDATED: `skills/design/SKILL.md`
- Line 12 (Flags intro): delete the sentence "`--trivial` has been removed and is a Pre-Step-0 hard error."
- Line 24 (Mutual exclusion): delete the sentence "If `--trivial` appears anywhere in the tier-flag scan, print the removal warning in Pre-Step-0 and abort before `session-setup.sh`." KEEP "at most one of `--simple` / `--hard` may be set; if two or more tier flags appear, print a clear error and abort before Step 0."
- Lines 119–121 (`## Pre-Step-0 — argv gate` section): the section's only concrete action today is the `--trivial` rejection. **Recommended:** delete the entire Pre-Step-0 section — the `--simple`/`--hard` duplicate-tier mutual-exclusion still lives in the Flags-section parsing rule (line 24) and in the Step 0b tier gate, so duplicate-tier rejection survives. (Alternative if a reviewer prefers an explicit gate: keep a slimmed Pre-Step-0 section that performs ONLY the `--simple`/`--hard` duplicate-tier check, with all `--trivial` scanning/printing/exit removed.) Whichever is chosen, no `--trivial` token may remain. Before deleting the header, `grep -n 'Pre-Step-0' skills/design/` to confirm no other live reference dangles (the only one — `flags.md:20` — is removed in Group A).

### UPDATED: `skills/design/scripts/render-final-summary.sh`
- Line 247: remove the dead `case "$MODE_STR" in *--trivial*|*trivial*) PLAN_LINE="skipped (trivial)" ;; *) PLAN_LINE="0 findings" ;; esac` branch. `MODE_STR` is now only `SIMPLE`/`HARD`/`N/A`, so the trivial arm is unreachable. Replace the whole `if [ ! -f voting-tally.md ]` true-branch body with the unconditional `PLAN_LINE="0 findings"` already used elsewhere in the same block.

### UPDATED: `scripts/design-pause-load.sh`
- Line 168: remove `TRIVIAL_DOC_ONLY` from the accepted-tier `case` → `SIMPLE|HARD|unknown) ;;`. (A pre-consolidation paused run with `TIER=TRIVIAL_DOC_ONLY` now resolves `invalid-tier` on resume — intended; no backward-compat.)

### UPDATED: `scripts/test-design-structure.sh`
- Line 34: delete the `contains "$SKILL_MD" '--trivial flag removed; tier consolidation in #2956. Use --simple or --hard.'` assertion (it pins prose being removed from SKILL.md). KEEP line 33 and line 75 (see "Intentionally retained" above).

### UPDATED: `scripts/test-design-structure.md`
- Line 5: reword the harness summary to drop "rejects `--trivial`" (e.g. "…exposes only SIMPLE/HARD tier routing, uses the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, runs plan validation unconditionally…").

### UPDATED: `skills/design/scripts/test-design-driver.sh`
- Lines 104–106: delete the `if grep -Fq "| \`--trivial\` |" … fail "design SKILL still exposes trivial tier row"` negative check. The positive `simple_row`/`hard_row` presence checks at 107–108 remain.
- Lines 113–118: delete the Pre-Step-0 `--trivial`-gate ordering block (`trivial_line=…` through the two `(( trivial_line < … ))` assertions). It depends on the removed gate header and the `trivial_line` variable. Remove `trivial_line` entirely; if `step0_line`/`session_setup_line` become unused after this deletion, remove them too so the script stays `set -u`-clean.

### UPDATED: `skills/design/scripts/test-assess-plan-round.sh`
- Lines 66–68: delete the redundant `write_params TRIVIAL` / `ASSESSOR_VERDICT=skipped` block. The `write_params SIMPLE` block (62–64) already covers "non-HARD tier skips." (`write_params` is a local helper that writes `run-params.json` directly, so no enum writer is involved.)

### UPDATED: `scripts/test-write-run-params.sh`
- Lines 66–77: delete the `--classification TRIVIAL_DOC_ONLY` rejection block. The generic `--classification MEDIUM` rejection block (60–64) retains "invalid classification → reject" coverage.

### UPDATED: `scripts/test-write-run-params.md`
- Lines 8 and 24: drop "including `TRIVIAL_DOC_ONLY`" from the rejection-coverage descriptions; keep the generic enum-rejection wording.

### UPDATED: `scripts/write-run-params.md`
- Lines 16 and 24: reword the `TRIVIAL_DOC_ONLY`-specific phrasing → "Validates `--classification` as `SIMPLE` or `HARD`; any other value is rejected (exit 2)." and the harness summary likewise (drop "including `TRIVIAL_DOC_ONLY`").

### UPDATED: `scripts/test-read-design-classification.sh`
- Line 35: generalize the invalid-classification fixture value `TRIVIAL_DOC_ONLY` → a neutral invalid token (e.g. `BOGUS`). KEEP the test — it asserts "invalid classification → default to HARD with warning"; only the sample value changes (the warning text at line 39 is value-agnostic).

### UPDATED: `scripts/test-timing-report.sh`
- Line 86: change the v1-schema fixture's `"design_classification":"TRIVIAL_DOC_ONLY"` → `"SIMPLE"`. The test asserts `workflow_path: SIMPLE` (line 89/92), not the classification, so the value is incidental; KEEP the test.

### UPDATED: `scripts/test-render-run-summary.sh`
- Line 364: change the `--plan-review-line 'skipped (trivial)'` fixture to a neutral representative value (e.g. `'0 findings'`). `render-final-summary.sh` will no longer emit "skipped (trivial)"; the test exercises generic `--plan-review-line` passthrough, so update the sample and any line that asserts the rendered output contains the old string.

**Sibling `.md` sync** (per `.claude/rules/script-md-siblings.md`): for every `.sh` edited above, review its sibling `.md` in the same change and strip any stale `--trivial`/`TRIVIAL_DOC_ONLY` text: `skills/design/scripts/render-final-summary.md`, `scripts/design-pause-load.md`, `skills/design/scripts/test-design-driver.md`, `skills/design/scripts/test-assess-plan-round.md`, `scripts/test-read-design-classification.md`, `scripts/test-timing-report.md`, `scripts/test-render-run-summary.md`. (Most carry no such text and need no edit; `write-run-params.md`, `test-write-run-params.md`, and `test-design-structure.md` already have explicit edits above.) Confirm with the completeness gate rather than assuming.

**Verification commands** (run from repo root):
- Targeted harnesses pass: `bash scripts/test-design-structure.sh`, `bash skills/design/scripts/test-design-driver.sh`, `bash skills/design/scripts/test-assess-plan-round.sh`, `bash scripts/test-write-run-params.sh`, `bash scripts/test-read-design-classification.sh`, `bash scripts/test-timing-report.sh`, `bash scripts/test-render-run-summary.sh`.
- Repo-wide gate: `bash scripts/relevant-checks.sh` (or `make lint`) is green — this exercises `test-design-structure.sh` and the bash-authoring linters.
- Completeness gate (must each return ZERO hits): `rg -n --fixed-strings -e '--trivial' --glob '!larch-logs/**' --glob '!.git' --glob '!CHANGELOG.md' .` and `rg -n --fixed-strings -e 'TRIVIAL_DOC_ONLY' --glob '!larch-logs/**' --glob '!.git' --glob '!CHANGELOG.md' .`.

## Acceptance

1. The two completeness `rg` sweeps above return **zero** hits — no `--trivial` or `TRIVIAL_DOC_ONLY` token remains anywhere outside `larch-logs/**` and `CHANGELOG.md`.
2. The `/design` argument hint reads `[--simple|--hard]` in `skills/design/SKILL.md` (already), `README.md`, `docs/skills.md`, and `docs/workflow-lifecycle.md`.
3. `skills/design/references/flags.md` no longer lists `--trivial` as a public tier, contains no `TRIVIAL_DOC_ONLY` mapping, and its Mutual-exclusion text references only `--simple`/`--hard` (+ `--manual` independence).
4. The Pre-Step-0 `--trivial` hard-error is gone, **and** running `/design` with two tier flags (`--simple --hard`) is still rejected before `session-setup.sh`.
5. `scripts/design-pause-load.sh` accepts only `SIMPLE|HARD|unknown` resume tiers.
6. `skills/design/scripts/render-final-summary.sh` has no `*trivial*` `MODE_STR` branch.
7. All listed harnesses pass and `make lint` is green. Preserved coverage still exists via generalized fixtures: generic invalid-classification rejection (`test-write-run-params.sh` `MEDIUM` block), invalid→default-HARD (`test-read-design-classification.sh`), v1-schema timing read (`test-timing-report.sh`), and `--plan-review-line` passthrough (`test-render-run-summary.sh`).
8. The ordinary word "trivial"/"non-trivial" and the `NO_SKETCHES_CLASSIFIED_TRIVIAL` absent-guard (`test-design-structure.sh:75`) are untouched.

diff_lines: 90

## Test plan
(no test plan section in plan-file)
