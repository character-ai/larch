## Goal

Introduce structured JSON/TSV per-finding output for all reviewer agents, update the collector and voter prompts to parse the structured format, add a schema repair/validation pass, and strip Example A/B calibration blocks from external vendor render scripts while retaining them for the internal Claude subagent path.

## Implementation Plan: Structured JSON/TSV Reviewer Output and Calibration Removal (Sub-tasks A+C)

### Summary

This plan introduces per-finding structured output schemas for the reviewer pipeline (JSON/JSONL for internal Claude subagent paths, TSV for external Codex/Cursor specialist paths), adds a schema repair/validation pass in `collect-agent-results.sh` and `validate-research-output.sh`, and strips Example A/B calibration blocks from external vendor render scripts while retaining them in the internal Claude subagent path. Voter prompts keep their existing FINDING_N/OOS_N ballot format unchanged — ballot construction remains prose-driven for this PR.

**Post-review revisions (Findings 1–7, 9, 10, 12 accepted by vote):**
- FINDING_1: Callers wired explicitly in this PR (see §7)
- FINDING_2: Generic external reviewer prompts are out-of-scope for structured output; structured validation is scoped only to renderer-backed specialist slots
- FINDING_3: STRUCTURED_FILE dropped; validate-research-output.sh --write-structured added instead
- FINDING_4: JSONL detection uses jq with documented dependency; TSV detection uses exact line format
- FINDING_5: Corrected agent count from 6 to 7; full enumeration with active vs composite distinction
- FINDING_6: Exit code 5 reserved for structured-mode failures
- FINDING_7: --structured-reviewer-mode adds early bypass of word-count/citation gates on valid-record success
- FINDING_9: Structured records written to sidecar file, not appended to prose output
- FINDING_10: STRUCTURED_FILE field dropped (see FINDING_3 resolution); grammar unchanged
- FINDING_12: scripts/render-specialist-prompt.md added to modification list

The dialectic panel resolved three contested decisions:
- DECISION_1 (voted): Use a deterministic repair pass for TSV, not base64url encoding.
- DECISION_2 (voted): Exclude `skills/design/scripts/render-plan-review-prompt.sh` — it has no calibration block to remove.
- DECISION_3 (voted): No backward-compat Markdown fallback parser; repair pass is liberal, prompts are strict.

---

### Files to Modify / Create

#### 1. `skills/shared/reviewer-templates.md`
**Changes:**
- Retain `## Calibration examples` (Example A + Example B) — this drives the internal Claude subagent path.
- Add a new `## Structured Output Schema (JSON)` subsection within `## Output format`, after `## Output format` heading. This instructs the Claude subagent to write structured records to a sidecar file alongside normal prose output. The sidecar path is derived from the primary output path with a `.jsonl` suffix (e.g., `cursor-plan-arch-output.txt.jsonl`). Structured records go to the sidecar; the prose output file is unchanged.
- Schema fields per JSONL record (one record per line): `schema_version` (always `1`, integer), `scope` (`"in_scope"` or `"out_of_scope"`), `severity` (`"important"`, `"nit"`, or `"latent"`), `focus_area` (one of `"code-quality"`, `"risk-integration"`, `"correctness"`, `"architecture"`, `"security"`), `location` (file:line or plan section, string), `what` (finding text, string), `scenario_or_breakage` (concrete failing scenario or breakage path, or empty string), `suggested_fix` (string).
- `NO_ISSUES_FOUND` case: sidecar is empty (0 records).
- Keep all existing prose output format instructions unchanged. The sidecar is additional; it does not replace prose sections.

#### 2. `agents/code-reviewer.md`
**Changes:**
- Regenerate from `skills/shared/reviewer-templates.md` by running `bash scripts/generate-code-reviewer-agent.sh` after editing the template.
- No manual edits to `agents/code-reviewer.md` directly.

#### 3. `agents/reviewer-*.md` (all 7 specialist agents)
Active in /review launch set (5): `reviewer-structure.md`, `reviewer-correctness.md`, `reviewer-edge-cases.md`, `reviewer-testing.md`, `reviewer-security.md`
Composite/alternate (2): `reviewer-security-structure-tests.md`, `reviewer-correctness-edges.md`

**Changes for all 7:**
- Add a `## Structured Output (TSV Sidecar)` section at the end of the `## Output format` block. Instructs the specialist to write structured records to a sidecar file (`<output-basename>.tsv`). The sidecar uses a tab-delimited format with the same 8 fields as the JSONL schema above, one record per line, with a header line.
- TSV schema header: `schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix`
- Per record: `1\t<scope>\t<severity>\t<focus_area>\t<location>\t<what>\t<scenario_or_breakage>\t<suggested_fix>`
- Tab escaping: if a field value contains a literal tab character, replace it with a single space. If a field value contains a literal newline, replace it with a space.
- `NO_ISSUES_FOUND` case: sidecar is empty.
- Prose output (`### In-Scope Findings`, `### Out-of-Scope Observations`) is written to the primary output file and is unchanged by this addition.
- **Scope clarification (FINDING_2 resolution):** Structured sidecar output is added to all 7 specialist agents. Generic external reviewers (launched with inline prompts in skills/review/SKILL.md and skills/implement/SKILL.md generic Codex/Cursor slots) are NOT updated in this PR — they continue to emit prose-only output. Structured validation is scoped only to renderer-backed specialist slots.

#### 4. `scripts/render-specialist-prompt.sh`
**Changes:**
- Strip the `## Calibration examples` section from the agent body BEFORE emitting it.
- Mechanism: after `BODY` is extracted via the existing awk pattern (line 109: `awk 'BEGIN{n=0} /^---[[:space:]]*$/{n++; if(n==2){found=1; next}} found{print}' "$AGENT_FILE"`), apply a second `awk` pass that removes all lines from `^## Calibration examples` through (but not including) the next line matching `^## ` (any level-2 heading). This strip must be idempotent (if the section is absent, output unchanged).
- The strip is applied unconditionally since this script is only called for external Cursor paths.
- **Implementation note (FINDING_8 resolution):** Strip is applied to `BODY` at line 109, immediately before `printf '%s\n\n' "$BODY"` at line 145. Do NOT edit the TAGGING_* or competition-notice blocks.

#### 5. `scripts/render-specialist-prompt.md`
**Changes (FINDING_12 resolution):**
- Document the calibration-strip behavior: describe which section is stripped, when (always, for all external Cursor paths), and the awk range mechanism.
- Document that the strip is applied to `BODY` before emission.
- Add test expectation: running render-specialist-prompt.sh with any agent file that contains `## Calibration examples` must produce output that does NOT contain `example://calibration` or `Example A` / `Example B`.

#### 6. `scripts/render-reviewer-prompt.sh`
**Changes:**
- After Stage 1 body extraction (writes `$BODY_FILE`), add a `sed` or `awk` pass to strip the `## Calibration examples` block from `$BODY_FILE` before substitution. Range: `## Calibration examples` through (but not including) the next `## ` level-2 heading.
- This script is used for Codex/Cursor external paths in /research validation; strip is always applied.
- Update `scripts/render-reviewer-prompt.md` sibling: document the new calibration-strip behavior.

#### 7. `scripts/validate-research-output.sh`
**Changes (FINDING_3, FINDING_4, FINDING_6, FINDING_7 resolution):**

- Add `--structured-reviewer-mode` flag (orthogonal to `--validation-mode`).
- Add `--write-structured <path>` flag: when provided, write the normalized structured records (repaired and validated) to this path. If no valid records are found (or NO_ISSUES_FOUND), write an empty file.
- New exit code 5: `structured records not found after repair` (FINDING_6). Existing exit codes 0-4 unchanged.
- When `--structured-reviewer-mode` is active:
  1. **NO_ISSUES_FOUND short-circuit**: if trimmed content equals `NO_ISSUES_FOUND`, exit 0 and write empty sidecar to `--write-structured` path (if provided). No further checks.
  2. **Repair pass**: apply in order:
     a. Strip leading/trailing prose preamble (lines before the first valid record or header line).
     b. Strip markdown code fence wrappers (```` ``` ````..```` ``` ````): if the records appear inside a fenced block, extract the content.
     c. Normalize severity enum aliases: `Important` → `important`, `Nit` → `nit`, `Latent` → `latent` (case-insensitive matching).
     d. For TSV: replace embedded tab characters within field values with a single space; replace embedded newlines within field values with a space (FINDING_11 implementation note).
  3. **JSONL detection (FINDING_4 resolution)**: detect JSONL records by looking for lines that, when parsed by `jq -c '.'`, are valid JSON objects with `schema_version` equal to `1`. Requires `jq` as a documented dependency for structured mode. If `jq` is unavailable, fall back to a strict prefix match: lines must start with `{"schema_version":1,` (no spaces before the opening brace, no spaces around the colon or comma). Document both paths in the header.
  4. **TSV detection (FINDING_4 resolution)**: detect TSV records by looking for a header line matching exactly `schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix`, then validate that subsequent non-empty lines have exactly 8 tab-separated fields.
  5. **Early exit on valid records (FINDING_7 resolution)**: if at least one valid JSONL or TSV record is found, exit 0 **without applying the prose word-count or citation gates**. Write validated records to `--write-structured` path. The word-count and citation gates apply ONLY when structured mode is off.
  6. **No valid records**: if repair + detection finds no valid records, exit 5 with diagnostic `structured records not found after repair`.
- Update script header to document exit code 5 and the new flags.
- Update `scripts/validate-research-output.md` sibling to document new flags and behavior.

#### 8. `scripts/collect-agent-results.sh`
**Changes (FINDING_1, FINDING_3, FINDING_7 resolution):**

- Add `--structured-reviewer-validation` flag (separate from `--substantive-validation`).
- When `--structured-reviewer-validation` is passed, after section 3.5 (substantive validation), add section 3.6:
  1. For each STATUS=OK entry, derive the sidecar path: `<REVIEWER_FILE>.jsonl` for Claude-path outputs, `<REVIEWER_FILE>.tsv` for specialist outputs (heuristic: Cursor tool outputs use TSV, Codex tool outputs use TSV; Claude fallback outputs use JSONL).
  2. Call `validate-research-output.sh --structured-reviewer-mode --write-structured <sidecar-path>` on the REVIEWER_FILE.
  3. On exit 0: emit `STRUCTURED_SIDECAR=<sidecar-path>` as a new field appended before `FAILURE_REASON`. Update field-grammar documentation to show 7 fields with STRUCTURED_SIDECAR as field 6 and FAILURE_REASON as field 7 (trailing, may contain user content). This is an additive grammar change; consumers that parse by-name (KEY=value) are unaffected; consumers parsing by field position must be updated.
  4. On exit 5 or non-zero: rewrite the entry to `STATUS=NOT_SUBSTANTIVE` with diagnostic in FAILURE_REASON (same sanitization as section 3.5); call `set_tool_unhealthy`.
- **Caller wiring (FINDING_1 resolution)**:
  - `skills/design/references/plan-review.md` Step 3 collect call: add `--structured-reviewer-validation` for Cursor archetype slots (cursor-plan-arch, cursor-plan-edge). Codex archetype slots remain `--substantive-validation --validation-mode` only until their prompts are updated.
  - Note: Generic reviewer slots in skills/review/SKILL.md, skills/implement/SKILL.md, and skills/research/references/validation-phase.md are NOT updated in this PR (FINDING_2 resolution). Those slots continue to use only `--substantive-validation --validation-mode`.
- Update `scripts/collect-agent-results.md` sibling to document the new flag and field grammar change.
- Extend `scripts/test-collect-agent-retry.sh` (FINDING_13 resolution: correct test file reference) to add test cases for `--structured-reviewer-validation`.

---

### Approach

1. **Prompt contract changes** (reviewer-templates.md → code-reviewer.md + all 7 specialist agents): instruct reviewers to write structured records to a sidecar file. Sidecar is separate from prose output, so existing parsers are unaffected (FINDING_9 resolution).

2. **Calibration strip** (render-specialist-prompt.sh + render-reviewer-prompt.sh): strip `## Calibration examples` from BODY before emission for external Cursor/Codex paths. Strip is applied to BODY at the extraction point, not to the output instruction blocks (FINDING_8 resolution). render-plan-review-prompt.sh is excluded — no calibration block exists there (DECISION_2).

3. **Schema repair + validation** (validate-research-output.sh): new `--structured-reviewer-mode` flag with `--write-structured <path>`. Repair pass is liberal; detection uses jq (with prefix-match fallback). Early exit bypasses word-count/citation gates on valid-record success (FINDING_7). Exit code 5 for structured failures (FINDING_6).

4. **Collector integration** (collect-agent-results.sh): new `--structured-reviewer-validation` flag calls the new validator and emits STRUCTURED_SIDECAR field. Wired explicitly to plan-review Cursor slots only in this PR (FINDING_1 resolution). Grammar extended with new field before FAILURE_REASON (FINDING_10).

5. **Agent regeneration**: after editing reviewer-templates.md, regenerate agents/code-reviewer.md via `bash scripts/generate-code-reviewer-agent.sh`.

6. **Sibling doc updates**: render-specialist-prompt.md (FINDING_12), render-reviewer-prompt.md, validate-research-output.md, collect-agent-results.md updated with new behavior.

---

### Edge Cases

[TRUNCATED — plan-goals-test exceeded 14000 chars]
