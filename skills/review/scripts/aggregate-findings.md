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
```

## Escape hatch

`LARCH_AGGREGATOR_DISABLED=1` — no-op pass-through: does not read or rewrite `findings.md` (no block-count probe, no LLM/dispatch); stdout includes `AGGREGATED=false`, `REASON=disabled`, and `INPUT_COUNT=0` / `MERGED_COUNT=0` (counts are intentionally not computed in this mode).

## Behavior summary

- Fewer than two `### FINDING_` blocks → pass-through, `REASON=insufficient-input`.
- Otherwise builds a prompt from `agents/orchestrator-aggregator.md` (YAML frontmatter stripped) plus the raw `findings.md` body, writes a one-row NDJSON slot (`slot=aggregator`, `tool=cursor`, `output=$REVIEW_TMPDIR/aggregator-output.txt`, `prompt_file=…`), and invokes `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.sh` (override for tests: `AGGREGATE_DISPATCH_SH`).
- On `DISPATCH_OK=false`, dispatch non-zero, empty output, or Python validation failure → keep original `findings.md`, append execution issue, `REASON=dispatch-failed` or `validation-failed`.
- **Empty-merge attestation (runtime contract)**: When the input ballot still has structured `### FINDING_` blocks but aggregator output has **zero** such blocks, validation requires an exact full-line token `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` in the raw vendor output (prevents replacing the ballot with narrative-only text). This is a mechanical guardrail, not a cryptographic proof against a hostile model: a mis-prompted merge could still satisfy the string check while clearing findings; treat that as policy/monitoring (`REASON=ok` on success paths). After validation, that line is **stripped** before `findings.md` is replaced so voting UIs never show the token in the persisted ballot.
- **Slot normalization (symmetric)**: Input reviewer membership, OOS-only slot sets, and merge-output slots all use the same rule: strip one trailing parenthetical suffix from each comma-separated slot token (e.g. `file.txt (via C.2 coverage gap)` → `file.txt`). Operators should not rely on two distinct reviewers whose labels differ only by `(...)` suffixes unless that collapse is intended.
- When output does contain finding blocks: every block has a reviewer attribution line (`**Reviewer(s)**` / `**Reviewer**` / `**Reviewers**` / unbolded `Reviewer(s):` / `Reviewer:` / `Reviewers:`); every comma-separated slot is matched against the normalized input reviewer set; every input reviewer label must appear in at least one output block; unknown slots fail validation. A reviewer label that appears exclusively on OOS-tagged input findings (never on a non-OOS input finding) must not appear in a non-OOS output block; reviewers with both OOS and in-scope input findings may appear in either kind of output block (issue #2491).

## Stdout

`KEY=value` lines only, including:

- `AGGREGATED=true|false`
- `INPUT_COUNT`, `MERGED_COUNT`
- `REASON` — `disabled` | `insufficient-input` | `dispatch-failed` | `validation-failed` | `ok`
- `FAILURE_LOG` — optional path to captured stderr / validator diagnostics

Harness: `skills/review/scripts/test-aggregate-findings.sh` (via `make test-aggregate-findings`).
