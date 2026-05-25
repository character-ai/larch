# Decomposition panel (Step 2b.5 Split-path)

**Consumer**: `/design` Step **2b.5 Split-path** only — after the operator chooses **Split** from a plan-size sprawl offer (hard trigger, soft trigger, semantic soft estimate, or `--partition` / `-p`). This file is **not** loaded during routine Step 2b plan emission, Step 3 plan review, or Gate A/B/C flows unless Split-path runs.

**Contract**: single normative source for **panel input selection**, **8-slot external dispatch** (`scripts/dispatch-with-waterfall.sh`), **3-stage `AskUserQuestion` presentation** (path → archetype → vendor), **aggregator delegation**, **cycle-checked batch filing** via `/larch:issue`, **annotating filed URLs**, **redacted original-issue close**, and **sentinel idempotency** under `$DESIGN_TMPDIR`. <!-- topology: 8 fixed -->

**When to load**: immediately when Step 2b.5 enters **Split-path (decomposition panel)** in `skills/design/SKILL.md` — read this entire file before invoking any helper below.

---

## 0) Idempotent re-entry

If `$DESIGN_TMPDIR/.decompose-original-closed` exists, print `⏩ 2b.5: decompose — original issue already closed; nothing to do.` and exit **0** (preserve tmpdir).

If `$DESIGN_TMPDIR/.decompose-issues-filed` exists but the original is not closed, continue in **resume-close** mode: skip re-dispatch and re-filing; only rerun `close-original` when the operator is ready (GitHub/API hiccup recovery).

---

## 1) Panel input artifact (`plan` vs `feature-only`)

Bind `PANEL_MODE=plan` when `test -f "$DESIGN_TMPDIR/plan.txt"`; otherwise `PANEL_MODE=feature-only` (Step **1c** / **1d** sprawl before plan materialization).

- **`plan`**: pass `--plan-file "$DESIGN_TMPDIR/plan.txt"` and `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` to the dispatcher.
- **`feature-only`**: pass `--feature-file "$DESIGN_TMPDIR/feature-description.txt"` and `--discussion-round1-file "$DESIGN_TMPDIR/discussion-round1.md"` when that file exists (omit the flag when absent — the helper treats missing discussion as an explicit “none” block in prompts).

Always pass `--design-tmpdir "$DESIGN_TMPDIR"` and the session’s `codex_present` / `cursor_present` booleans (same binding semantics as Step 3 plan-review).

---

## 2) Dispatch the fixed 8-slot panel

Run (stdout is KV-shaped; parse `PANEL_OUTPUTS_FILE`, `DEGRADED_PANEL`, `PANEL_STATUS`):

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/decompose-panel-dispatch.sh" \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --codex-present "$codex_present" \
  --cursor-present "$cursor_present" \
  --mode "$PANEL_MODE" \
  ${PANEL_MODE_PLAN_ARGS[@]+"${PANEL_MODE_PLAN_ARGS[@]}"} \
  --feature-file "$DESIGN_TMPDIR/feature-description.txt" \
  ${DISCUSSION_ROUND_ARGS[@]+"${DISCUSSION_ROUND_ARGS[@]}"} \
  --timeout 1800
```

Where:

- `PANEL_MODE_PLAN_ARGS` is `--plan-file "$DESIGN_TMPDIR/plan.txt"` only in `plan` mode (empty otherwise).
- `DISCUSSION_ROUND_ARGS` is `--discussion-round1-file "$DESIGN_TMPDIR/discussion-round1.md"` only when that file exists **and** you are in `feature-only` mode (optional in `plan` mode if you want the same discussion context appended — either choice is acceptable if you stay consistent within a run).

### Failure semantics

- `PANEL_STATUS=panel-failed` — zero outputs contain a parseable `## Recommendation` heading. Offer **`AskUserQuestion`**: **Retry panel** / **Cancel**. On **Retry**, rerun §2 **once**; a second `panel-failed` exits `/design` **1** and preserves `$DESIGN_TMPDIR`.
- `PANEL_STATUS=degraded` or `DEGRADED_PANEL=true` — include **degraded vendor counts** in option labels where it helps the operator (mirror Step 3 plan-review degraded presentation).

**Harness override**: `DECOMPOSE_PANEL_WATERFALL_SH` substitutes `scripts/dispatch-with-waterfall.sh` for offline tests (`skills/design/scripts/test-decompose-panel-dispatch.sh`).

---

## 3) Parse eight proposals into archetype bundles

Read `PANEL_OUTPUTS_FILE` (NDJSON: one JSON object per line with `archetype`, `vendor`, `output`, `status`). Group rows by `archetype` (four groups). Within each archetype, separate **cursor** vs **codex** proposals.

If exactly **one** vendor produced a parseable proposal for an archetype, **skip stage-2** for that archetype and auto-select the surviving vendor. Print:

`**ℹ archetype <name>: only <vendor> proposal available (other vendor failed after waterfall)**`

---

## 4) Three-stage `AskUserQuestion` flow

### Stage 0 — path picker

Options (labels may mention degraded counts per §2):

1. **Pick a single archetype’s split** → continue to stage 1.
2. **Let aggregator pick optimal split** → run §5 then return to stage 1 with the aggregator’s Markdown as the active “vendor proposal” for a synthetic **aggregator** row (operator still confirms in stage 2 if multiple vendors existed — for aggregator there is only one bundle).
3. **Refine plan myself (return to caller)** — jump back to the invoking step without filing (Step **2b.5** from Gate B returns toward Step 3 / Gate B per existing SKILL routing; sprawl from **1c**/**1d** returns to the sprawl gate that invoked this procedure).
4. **Cancel** — export `SUMMARY_OUTCOME=cancelled-decompose`, run the **Final summary block**, print `**ℹ /design cancelled by operator (decomposition panel).**`, exit **0**.

### Stage 1 — archetype picker

Present the four archetype summaries side-by-side (titles + first lines of `## Recommendation` / `## Pieces`). Include the **aggregator** pick when §5 succeeded.

If the aggregator run failed, print `**⚠ aggregator failed; falling back to manual archetype pick.**` and omit the aggregator option.

### Stage 2 — vendor picker (per archetype)

When both Cursor and Codex outputs are usable, ask which vendor’s file becomes the **chosen partition artifact** (path to a Markdown file saved under `$DESIGN_TMPDIR/decompose/`). When stage 2 is skipped per §3, use the surviving file directly.

---

## 5) Aggregator path (`decompose-aggregator.sh`)

Concatenate the eight panel outputs and merge into one canonical partition proposal:

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/decompose-aggregator.sh" \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --panel-outputs-file "$PANEL_OUTPUTS_FILE" \
  --codex-present "$codex_present" \
  --cursor-present "$cursor_present" \
  --output "$DESIGN_TMPDIR/decompose/aggregator-partition.md" \
  --timeout 1800
```

`aggregate-findings.sh` remains **finding-shaped** (### `FINDING_N` blocks with voting metadata). Partition merges therefore use this dedicated **single-slot Cursor → Codex → Claude waterfall** merger prompt — **not** the findings aggregator.

Parse stdout for `AGGREGATOR_STATUS=ok|failed` and consume `AGGREGATOR_OUTPUT` when `ok`.

**Harness override**: `DECOMPOSE_AGGREGATE_WATERFALL_SH` substitutes the waterfall entrypoint (`skills/design/scripts/test-decompose-aggregator.sh`).

---

## 6) `no-split` unanimous consensus

When **all four** archetypes’ usable proposals recommend `no-split` in `## Recommendation` (consensus text match on the line), print a short summary and **`AskUserQuestion`**: **Continue** / **Force split** / **Cancel**.

- **Continue** — return to the caller (no filing).
- **Force split** — collect a **manual** 2+ piece partition (free-form Markdown meeting the `## Pieces` template); write it to `$DESIGN_TMPDIR/decompose/operator-partition.md` and treat that as the chosen partition file for §7.
- **Cancel** — same as stage 0 **Cancel**.

---

## 7) Cycle check + `/larch:issue` batch + annotate

Chosen partition Markdown path is denoted `<PARTITION_FILE>` below (vendor output copy, aggregator output, or operator forced split).

### 7a `prepare`

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/decompose-file-issues.sh" prepare \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --partition-file "<PARTITION_FILE>" \
  ${ISSUE_NUMBER:+--issue-number "$ISSUE_NUMBER"}
```

Parse `DECOMPOSE_PARTITION_STATUS` from the quiet stream / helper stdout mirror:

- `cycle-detected` — print `**⚠ chosen partition has a dependency cycle: …**` (list the Kahn/Tarjan witness from the helper log if available) and re-prompt (**Pick a different proposal** / **Cancel**). Do **not** auto-fix edges.
- `ok` — continue.

Batch artifacts:

- `$DESIGN_TMPDIR/decompose/partition-input.txt` — `/larch:issue --input-file` body (generic `### <title>` items).
- `$DESIGN_TMPDIR/decompose/partition-deps.tsv` — `--intra-batch-deps-file` rows (`<blocker-1based>\t<blocked-1based>`). **Never** pass `--no-dedup` alongside this file — mutual exclusion is enforced inside `/larch:issue`.

### 7b Invoke `/larch:issue`

Run the Skill in batch mode with **dedup enabled** (default) and capture **stdout** to a file (e.g. `$DESIGN_TMPDIR/decompose/issue-run.stdout`).

### 7c `annotate`

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/decompose-file-issues.sh" annotate \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --issue-stdout-file "$DESIGN_TMPDIR/decompose/issue-run.stdout"
```

This writes `$DESIGN_TMPDIR/decompose/partition-filed.md` and `$DESIGN_TMPDIR/.decompose-issues-filed` **only when filing succeeds enough to record URLs** — when `ISSUES_FAILED>0`, **do not** close the original in §8; surface which items failed and preserve tmpdir for operator repair.

`annotate` is **idempotent**: a second run with an identical stdout and an existing sentinel matching all `ISSUE_<i>_URL` lines is a no-op (does not rewrite `partition-filed.md`).

---

## 8) Close original issue (redacted body file)

Only when **§7 succeeded with `ISSUES_FAILED=0`** (all pieces filed and URLs recorded):

```bash
"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/decompose-file-issues.sh" close-original \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --original-issue "$ISSUE_NUMBER" \
  --repo "$GITHUB_REPOSITORY"
```

The helper composes a **#2644-shaped** prose comment (partition rationale + per-piece bullets + blocked-by narrative), pipes the body through `scripts/redact-secrets.sh` into `$DESIGN_TMPDIR/decompose/close-comment.redacted.md`, posts with `gh issue comment --body-file` (never inline `--body`), then `gh issue close`. Success writes `$DESIGN_TMPDIR/.decompose-original-closed`.

**Harness override**: `DECOMPOSE_REDACT_SH` substitutes the redactor (`skills/design/scripts/test-decompose-file-issues.sh` asserts the redacted path is what `gh` receives).

On `gh` or redactor failure, the helper appends via `scripts/append-tool-failure.sh` under **External Reviewer Issues** in `execution-issues.md` and exits non-zero **without** writing the close sentinel so the operator can retry.

---

## 9) Terminal outcomes (Split-path)

- **Partition filed + original closed** — `export SUMMARY_OUTCOME=approved-partition`, run the **Final summary block**, print `**ℹ /design exited: partition into N pieces filed (see #<original> close-comment).**`, exit **0**.
- **Cancel paths** — already covered in §4 / §6.
- **Retry exhaustion** — §2 second `panel-failed` → exit **1** (preserve tmpdir).

---

## 10) Operator follow-through

Do **not** auto-chain `/design` on child issues. The operator runs `/design` independently on each filed piece after the partition lands.
