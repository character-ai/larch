# aggregate-findings.sh contract

`skills/review/scripts/aggregate-findings.sh` runs an optional LLM aggregation pass on `findings.md` after `collect-findings.sh` and before the code-review voter dispatch (`review-core.sh`). It merges cross-reviewer `### FINDING_N` blocks that describe the same behavioral issue, rewrites stable `FINDING_N` ids in first-seen order, and lists every contributing reviewer slot on a single `- **Reviewer(s)**: …` line (comma-separated). Failures are non-fatal: the script leaves `findings.md` unchanged, appends a Warning under **External Reviewer Issues** in `execution-issues.md`, and exits `0`.

## CLI

```text
--findings-file PATH      (required) ballot path under $REVIEW_TMPDIR
--review-tmpdir DIR       (required) review tmpdir
--codex-present true|false
--cursor-present true|false
--mode diff|description
--session-env-path PATH   (optional) parent session env (execution-issues path)
--diff-file PATH          (optional) forwarded to dispatch-with-waterfall
--plan-file PATH          (optional) forwarded to dispatch-with-waterfall
--input-mode plan|code    (optional, default code) — `plan` relaxes merged-output severity validation for /design plan-review ballots (#2676); exports `LARCH_AGGREGATE_INPUT_MODE` for the embedded validator.
```

## Escape hatch

`LARCH_AGGREGATOR_DISABLED=1` — no-op pass-through: does not read or rewrite `findings.md` (no block-count probe, no LLM/dispatch); stdout includes `AGGREGATED=false`, `REASON=disabled`, and `INPUT_COUNT=0` / `MERGED_COUNT=0` (counts are intentionally not computed in this mode).

## Behavior summary

- Fewer than two `### FINDING_` blocks → pass-through, `REASON=insufficient-input`.
- Otherwise builds a prompt from `agents/orchestrator-aggregator.md` (YAML frontmatter stripped) plus the raw `findings.md` body, then runs an **outer waterfall** over available external tools **Cursor → Codex → Claude** (skips Codex when `--codex-present false`, skips Cursor when `--cursor-present false`; Claude is always the final outer phase via `dispatch-with-waterfall.sh`’s internal Claude lane when both externals are unavailable). Each outer attempt writes its dispatch capture to a distinct `output` path from the slot row (`aggregator-output.txt`, `aggregator-output-codex.txt`, `aggregator-output-claude.txt`). The script invokes `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.sh` (override for tests: `AGGREGATE_DISPATCH_SH`) once per outer phase with per-phase `--cursor-present` / `--codex-present` wiring. After each dispatch it reads `ALL_OUTPUT_TOOLS`; if the resolved tool does not match the outer phase name (e.g. internal Claude fallback during an outer Cursor attempt), that outer phase is treated as failed and the waterfall continues.
- **Narrow-trigger retry**: validator stderr `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` (zero structured `### FINDING_<digits>:` blocks in merge output while `aggregate-validate.py` detects a preamble contradiction signal) or `AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input` advances to the next outer phase without appending an execution-issues entry. The preamble signal fires on two patterns: (1) heading-format `### FINDING_[0-9N]` narrative references (e.g., "We have `### FINDING_N:` blocks"), and (2) bare numbered ID prose references such as `FINDING_24` or `(FINDING_1-3)`. Non-numeric prose like `### FINDING_ids` does not trip the preamble signal. Other validation failures keep the legacy single-shot behavior (`REASON=validation-failed`, one warning, original ballot unchanged). Optional `LARCH_AGGREGATE_MAX_OUTER_PHASES=<N>` caps outer attempts for tests (when the cap prevents further phases despite remaining waterfall capacity, the last narrow-trigger failure surfaces as `validation-failed`).
- When every outer phase fails a narrow-trigger check (or only tool-mismatches occur), the script emits `REASON=validation-exhausted`, optional stdout `PHASES_ATTEMPTED=<comma-list>` when more than one outer phase ran, and a **single** consolidated execution-issues entry. Recovering on a later outer phase emits `REASON=ok` and `PHASES_ATTEMPTED` only when multiple phases actually ran.
- On `DISPATCH_OK=false`, dispatch non-zero, or empty output → keep original `findings.md`, append execution issue, `REASON=dispatch-failed`.
- **Empty-merge attestation (runtime contract)**: The raw vendor token `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is the only recognized full-line empty-merge attestation marker. After successful validation, exact token lines are **stripped** before `findings.md` is replaced so voting UIs never show the token in the persisted ballot.
  - Lines whose trimmed text **starts with** the attestation token but is not **exactly** that token (suffix / format drift) are dropped by the validator and by the strip step so corrupted near-token lines cannot survive into the ballot.
  - When the input ballot has structured findings and aggregator output has zero structured findings, validation fails closed on three paths: (1) `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring` when the output contains narrative references to `### FINDING_[0-9N]` headings or bare `FINDING_N` ids (narrow-trigger, advances outer waterfall); (2) `AGGREGATOR_VALIDATION_FAILED=empty_merge_from_nonempty_input` when the exact attestation token is present but merge output is still empty (narrow-trigger, advances outer waterfall); (3) a human-readable missing-attestation diagnostic (no `AGGREGATOR_VALIDATION_FAILED=` machine token) when the token is absent and preamble does not trip — this is single-shot `REASON=validation-failed` with no outer-waterfall retry. There is no automatic attestation recovery.
- **Slot normalization (symmetric)**: Input reviewer membership, OOS-only slot sets, and merge-output slots all use the same rule: strip one trailing parenthetical suffix from each comma-separated slot token (e.g. `file.txt (via C.2 coverage gap)` → `file.txt`). Operators should not rely on two distinct reviewers whose labels differ only by `(...)` suffixes unless that collapse is intended.
- When output does contain finding blocks: every block has a reviewer attribution line (`**Reviewer(s)**` / `**Reviewer**` / `**Reviewers**` / unbolded `Reviewer(s):` / `Reviewer:` / `Reviewers:`); every comma-separated slot is matched against the normalized input reviewer set; every input reviewer label must appear in at least one output block; unknown slots fail validation. A reviewer label that appears exclusively on OOS-tagged input findings (never on a non-OOS input finding) must not appear in a non-OOS output block; reviewers with both OOS and in-scope input findings may appear in either kind of output block (issue #2491).
- **Suggested-revision traceability (advisory, non-cryptographic)**: After structural validation, the inline validator scans non-OOS merged blocks for `Suggested revisions` `From <slot>:` bullets (including continuation lines folded into the revision text) and legacy singular `- **Suggested revision**:` lines. Each revision must match **within a single** scoped input block: for `From <slot>:` bullets, candidate blocks are input findings that cite that slot **and** share at least one normalized reviewer label with the merged block's `- **Reviewer(s)**:` line — there is no fallback that widens to unrelated input findings for the same slot when that intersection is empty (such revisions surface as untraceable warnings). Singular revisions use the union of input blocks overlapping those merged reviewers; when both bullets and a legacy singular line appear, a dual-format advisory is printed and each form is traced separately. Matching prefers the full normalized revision as a substring of that one block; shorter runs fall back to a six-word prefix scan **within the same block**. Unknown `From` slot labels and untraceable revision text emit `warning:` lines on stderr (also captured under `$REVIEW_TMPDIR/aggregator-validate.stderr`). Set `LARCH_AGGREGATE_REVISION_TRACE_STRICT=1` to fail validation (same path as other validator failures) when any such advisory would have been printed. Continuation lines inside a `Suggested revisions` sub-list are not terminated by arbitrary `- **Capital…` lines — only by the next known top-level field header (`Reviewer` / `Concern` / `Justification` / `Suggested revision(s)`).

## Stdout

`KEY=value` lines only, including:

- `AGGREGATED=true|false`
- `INPUT_COUNT`, `MERGED_COUNT`
- `REASON` — `disabled` | `insufficient-input` | `dispatch-failed` | `validation-failed` | `validation-exhausted` | `ok`
- `PHASES_ATTEMPTED` — optional comma list (`cursor`, `codex`, `claude`); emitted only when more than one outer phase ran
- `FAILURE_LOG` — optional path to captured stderr / validator diagnostics

Harness: `skills/review/scripts/test-aggregate-findings.sh` (via `make test-aggregate-findings`).
