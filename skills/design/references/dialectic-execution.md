# Dialectic Execution Choreography

**Consumer**: `/design` Step 2a.5 — loaded after the short-circuit + zero-externals guardrail check when contested decisions exist. This file owns the dialectic-execution mechanics: per-decision prompt rendering, parallel debater launch, collection, **per-side waterfall retries**, eligibility gate, judge presence check, ballot construction, judge launch, tally, and resolution writing.

**Contract**: single normative source for dialectic-execution mechanics, including the nested MANDATORY pointer to `references/dialectic-debate.md`, the externals-primary debate-path carve-out with a **Claude-only 2nd-retry waterfall exception** (GitHub issue #98), the Option B snapshot pattern via `dialectic_*_available` shadow flags, and the `dialectic-resolutions.md` schema for voted / fallback-to-synthesis / bucket-skipped / over-cap dispositions.

**When to load**: once Step 2a.5 has passed the short-circuit (`NO_CONTESTED_DECISIONS`) check. Do NOT load when `contested-decisions.md` contains only `NO_CONTESTED_DECISIONS`. On the zero-externals guardrail path (step 5 of Step 2a.5 in SKILL.md): debate-execution mechanics in this file MUST NOT fire (no debaters, no judges, no ballot) — skip loading entirely if the orchestrator already has the `dialectic-resolutions.md` schema in context from a prior run; otherwise a one-time load of this file is acceptable solely to consult the schema, but the per-decision prompt rendering, parallel debater launch, collection, waterfall retries, eligibility gate, judge presence check, ballot construction, judge launch, and tally steps remain suppressed. This mirrors the conditional permission granted by the SKILL.md caller contract at Step 2a.5.

**Binding convention**: This file is the single normative source for dialectic-execution mechanics. SKILL.md Step 2a.5 retains only the short-circuit, GH#98 carve-out banner, per-side assignment summary, and zero-externals guardrail summary; the full execution procedure lives here. Shared variable references (`$DESIGN_TMPDIR`, `${CLAUDE_PLUGIN_ROOT}`, `{SYNTHESIS_TEXT}`, `{FEATURE_DESCRIPTION}`, `{DECISION_BLOCK}`, etc.) and warning-string literals MUST stay semantically aligned with SKILL.md where both files mention the same contract — they are **not** maintained as a byte-identical pre-split copy; edits land here first for execution detail, then SKILL.md summaries are updated when the surface-level contract changes.

**Caller binding for shared dialectic protocol**: This file is the `/design` caller of `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md`. The shared protocol writes its path placeholders in terms of `$DIALECTIC_TMPDIR`; the caller binding for `/design` is **`DIALECTIC_TMPDIR=$DESIGN_TMPDIR`**. This is a *semantic correspondence between two markdown files*, not a shell-level alias — the body of this file uses `$DESIGN_TMPDIR` directly in its bash and prompts, and nothing in those snippets depends on `DIALECTIC_TMPDIR` being set in any shell environment at runtime. The binding describes the *substitution rule* the orchestrator applies when copying text from the shared protocol: any literal `$DIALECTIC_TMPDIR` token in such copied text becomes `$DESIGN_TMPDIR` at prompt-construction time (matching the orchestrator's pre-existing `$DESIGN_TMPDIR`-to-actual-path substitution convention; external CLIs do not expand shell variables in prompt arguments, so substitution must happen at construction time, not in the receiving CLI). The protocol's filename defaults (`dialectic-ballot.txt`, `dialectic-resolutions.md`, `cursor-judge-output.txt`, `codex-judge-output.txt`) are kept verbatim in the body's bash blocks because `/design` is the protocol's design-context caller.

---

**Thesis/antithesis prompt templates**: these are loaded from the reference file below. Template bodies come from `dialectic-debate.md` (same placeholders and tag wrappers as Phase 1); only the delivery channel changes (external CLI via `run-external-agent.sh` rather than the Agent tool). Reasoning effort is handled by the launcher wrappers.

**MANDATORY — READ ENTIRE FILE before rendering debate prompts (step 2 in the numbered sequence below)**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/dialectic-debate.md` completely. It contains the Thesis agent template and Antithesis agent template with `{FEATURE_DESCRIPTION}`, `{SYNTHESIS_TEXT}`, `{DECISION_BLOCK}`, `{CHOSEN}`, `{ALTERNATIVE}`, `{TENSION}`, `{AFFECTED_FILES}` substitution placeholders plus the `<debater_synthesis>` and `<debater_decision>` reference-block wrappers.

**Do NOT Load when contested-decisions.md contains only NO_CONTESTED_DECISIONS** — the short-circuit print at the top of Step 2a.5 in SKILL.md exits before reaching this file, so the `dialectic-debate.md` reference file is naturally never loaded on the no-contest path.

**Numbering bridge**: The **1–6** sequence below is internal to this file only. Map it to `skills/design/SKILL.md` Step **2a.5** as: **1** ↔ SKILL item **3** (per-side tool assignment); **2–4** ↔ rendering, launch, and initial collection nested under that same Step 2a.5 block; **5** ↔ per-side waterfall (**GH#98** Claude 2nd-retry tier); **6** ↔ launch-time `STATUS != OK` routing into the waterfall. Cap ranking (`over-cap`) and skip semantics (`bucket-skipped`, zero-externals guardrail) remain anchored to SKILL items **1–2** and **4–5** respectively — not renumbered here.

---

1. **Per-side external tool assignment** (normative detail for Step 2a.5 item 3 in `skills/design/SKILL.md`). For each capped decision index `N` (1-based among the Step 2a.5 selected decisions), assign **two** tools — one for thesis, one for antithesis — so both sides are normally debated by **different** externals:

   - **Odd N** (first, third, … selected decision among the cap): thesis → **Cursor** (requires `dialectic_cursor_available`); antithesis → **Codex** (requires `dialectic_codex_available`).
   - **Even N**: thesis → **Codex**; antithesis → **Cursor**.

   **Degraded mode** (exactly one external is `dialectic_*_available=true` at original launch time): assign **both** thesis and antithesis launches to that **sole available** external. The per-side waterfall (step **5** below) then targets the **missing** external as the 1st-retry tool when a presence re-check shows it back online; otherwise skip directly to the Claude 2nd-retry tier.

   **Zero-externals guardrail**: unchanged — see SKILL.md Step 2a.5 item 5 (no debate launches).

   **Original-launch output paths**: `$DESIGN_TMPDIR/debate-<n>-<cursor|codex>-<thesis|antithesis>.txt` must match the tool that actually runs each side (`<n>` is the decision index printed in `contested-decisions.md`, not the rank-within-cap ordinal — stay consistent with existing run artifacts).

2. **Per-decision prompt-file rendering**. For each queued decision, render the thesis and antithesis prompts (loaded from `references/dialectic-debate.md` loaded via this file's header MANDATORY directive) with `{FEATURE_DESCRIPTION}`, `{SYNTHESIS_TEXT}`, `{DECISION_BLOCK}`, `{CHOSEN}`, `{ALTERNATIVE}`, `{TENSION}`, `{AFFECTED_FILES}` substituted. Before launching each debater, read `skills/design/references/readability-style.md` once and substitute every literal `<READABILITY_STYLE>` token in the rendered prompt body with the full preamble contents. Then use the **Write tool** (not heredoc/cat) to write each rendered prompt to its own file:
   - `$DESIGN_TMPDIR/debate-<n>-thesis-prompt.txt`
   - `$DESIGN_TMPDIR/debate-<n>-antithesis-prompt.txt`
   File-based prompt delivery eliminates shell-quoting hazards from synthesis/decision content that may contain `"`, `$()`, backticks, or newlines.

**MANDATORY — READ ENTIRE FILE before rendering dialectic prompts: `skills/design/references/readability-style.md`.**

3. **Parallel launch** — issue all queued launches in a **single Bash message** (up to 10 background calls: 5 decisions × 2 sides). Each launch uses `launch-review.sh` with `run_in_background: true` and `timeout: 1860000`. Substitute the `--timing-task-kind` literal directly per launch (do NOT use the `VAR=value cmd ... "$VAR"` env-prefix anti-pattern documented below).

   Per decision `N`, use the tools assigned in **step 1** above. Thesis always reads `$DESIGN_TMPDIR/debate-<n>-thesis-prompt.txt` in its bootstrap `--prompt`; antithesis reads `…-antithesis-prompt.txt`. Each launch's `--output` basename must be `debate-<n>-<cursor|codex>-<thesis|antithesis>.txt` matching the tool running that side.

   **Worked example — odd N** (thesis=Cursor, antithesis=Codex):

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool cursor \
     --output "$DESIGN_TMPDIR/debate-<n>-cursor-thesis.txt" \
     --timeout 1800 \
     --timing-task-kind cursor-debate-thesis \
     --prompt "Read the dialectic-debate task description from $DESIGN_TMPDIR/debate-<n>-thesis-prompt.txt and follow it exactly to produce the structured tagged output it requests."
   ${CLAUDE_PLUGIN_ROOT}/scripts/launch-review.sh --tool codex \
     --output "$DESIGN_TMPDIR/debate-<n>-codex-antithesis.txt" \
     --timeout 1800 \
     --timing-task-kind codex-debate-antithesis \
     --prompt "Read the dialectic-debate task description from $DESIGN_TMPDIR/debate-<n>-antithesis-prompt.txt and follow it exactly to produce the structured tagged output it requests."
   ```

   **Worked example — even N** (thesis=Codex, antithesis=Cursor): swap `--tool`, `--output` basenames (`debate-<n>-codex-thesis.txt` / `debate-<n>-cursor-antithesis.txt`), and `--timing-task-kind` values (`codex-debate-thesis` / `cursor-debate-antithesis`) relative to the odd-N block.

   **Degraded mode (single external)**: launch **both** sides with that tool — two launches, both `--tool` the same, outputs `debate-<n>-<cursor|codex>-thesis.txt` and `debate-<n>-<cursor|codex>-antithesis.txt` (still distinct files).

   **Anti-pattern — do NOT use `VAR=value cmd ... "$VAR"` env-var-prefix idiom for these launches.** Bash expands `"$VAR"` in the parent shell BEFORE the env-var-prefix scope takes effect, so `"$VAR"` evaluates to empty in the parent (the assignment is only visible to `cmd`'s own environment). The launcher then receives `--timing-task-kind` followed immediately by the next flag (the empty value disappears under shell tokenization), which collapses argv into `--timing-task-kind --prompt "..."` and either passes `--prompt` as the timing-task-kind value or hits the unknown-flag branch — neither is the intended behavior. Always substitute the timing-task-kind literal directly per launch as shown above; do not factor it into a variable.

   Reasoning effort is handled by the launcher wrappers (`--risk high` by default).

4. **Collect** dialectic debate outputs (Option B enforcement):

   ```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1860 \
  <each launched output path>
```
   The collector no longer updates cross-skill reviewer state; the dialectic phase keeps debate failures scoped to its local availability variables. Invoke the collector as a foreground Bash tool call.

   Immediately after this collection returns, run the Mid-Run Dirty-Tree Probe Contract from `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` for `STAGE=dialectic-debate-collection`.

5. **Per-side waterfall retry** (quorum recovery). After step **4**'s initial collection + dirty-tree probe, **do not** immediately finalize `Disposition: fallback-to-synthesis` for debater-quorum failures. Instead, evaluate each **side** (thesis vs antithesis) independently against the debate quorum gate in the **Eligibility gate** section below. Any side that fails **any** quorum check (including `no_output` when that side's collector `STATUS != OK`) enters the waterfall queue for that side.

   **Retry trigger**: a side enters the waterfall whenever the quorum gate would have classified that side as failing (reason tokens: `no_output`, `missing_tag`, `bad_recommend`, `missing_citation`, `role_mismatch`, `substantive_empty`).

   **Per-side retry order** (max 2 retries / 3 launches per side including the original):

   - **1st retry** targets the **other** external tool relative to that side's **original** launch tool (Cursor ↔ Codex). If that target is unavailable at retry time (per the pre-wave presence re-check below), **skip** straight to the 2nd retry.
   - **2nd retry** targets **Claude** (Agent-tool inline debater — final slot only). If the Agent tool is unavailable, the side cannot be recovered.

   Concretely by original assignment:

   - Thesis originally Cursor → 1st retry Codex → 2nd retry Claude.
   - Thesis originally Codex → 1st retry Cursor → 2nd retry Claude.
   - Antithesis originally Codex → 1st retry Cursor → 2nd retry Claude.
   - Antithesis originally Cursor → 1st retry Codex → 2nd retry Claude.

   **Parallelism across sides**: when both thesis and antithesis need a 1st retry, issue **both** relaunches in the **same** Bash message. Same for coordinated 2nd-retry waves.

   **Sequentialism within a side**: do **not** launch a side's 2nd retry until that side's 1st retry has been collected and re-checked against the quorum gate.

   **Pre-launch presence re-check** (before **each** retry wave): run `${CLAUDE_PLUGIN_ROOT}/scripts/check-reviewers.sh` and refresh **only** `dialectic_codex_available` / `dialectic_cursor_available` from its output. Do **not** mutate orchestrator-wide `codex_available` / `cursor_available`.

   **Operator breadcrumb**: before each retry wave, print `⏩ 2a.5: waterfall retry <1|2> — <K> sides retrying` so long-running `/design` sessions show liveness.

   **Corrective prompt files** via `${CLAUDE_PLUGIN_ROOT}/scripts/render-debate-retry-prompt.sh` (stdout is KV `RENDERED=true` / `OUTPUT_FILE=…`; write prompts to a deterministic path, e.g. `$DESIGN_TMPDIR/debate-<n>-<cursor|codex|claude>-<thesis|antithesis>-retry<1|2>-prompt.txt`). Pass `--original-prompt-file` pointing at the **same** thesis or antithesis prompt file the failed launch used, `--previous-output-file` pointing at that side's most recent output attempt, `--failure-reason` as a comma-separated token list, `--retry-tool` matching the relaunch tool, and `--output` the new prompt path. External relaunches use the same bootstrap pattern as step **3** but read the **retry** prompt path. **Claude 2nd retry**: run the Agent tool with the rendered retry prompt (inlined or via Read), then **Write** the model's structured output to `$DESIGN_TMPDIR/debate-<n>-claude-<thesis|antithesis>-retry2.txt` so downstream steps have a filesystem path consistent with externals.

   **Timing-task-kind literals** for retries (substitute literally per launch): `cursor-debate-thesis-retry1`, `cursor-debate-antithesis-retry1`, `codex-debate-thesis-retry1`, `codex-debate-antithesis-retry1`, `claude-debate-thesis-retry2`, `claude-debate-antithesis-retry2`.

   **Collector discipline**: after each retry wave's **external** relaunches, invoke `collect-agent-results.sh` synchronously on the new `debate-<n>-<cursor|codex>-<side>-retry1.txt` output paths in the **same** Bash message as those launches (see `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` "Wait Discipline"). **Carve-out — Claude 2nd retry**: the Agent-tool Claude tier does **not** use `collect-agent-results.sh`; completion is authoritative from the Agent return plus the mandatory **Write** to `$DESIGN_TMPDIR/debate-<n>-claude-<thesis|antithesis>-retry2.txt` (same split pattern as inline judges — no sentinel path to poll).

   **Deterministic retry artifact basenames** (collector basename heuristic): 1st external retry → `$DESIGN_TMPDIR/debate-<n>-<retry-tool>-<side>-retry1.txt` where `<retry-tool>` is `cursor` or `codex`; 2nd Claude retry output → `$DESIGN_TMPDIR/debate-<n>-claude-<side>-retry2.txt`.

   **Waterfall trace string** (for resolutions): for each side, record compact `tool=result` segments joined by ` → ` for original + retry1 + retry2 (e.g., `cursor=missing_tag → codex=ok-but-still-missing_tag → claude=ok`). Use this when emitting `fallback-to-synthesis` after exhaustion (see **Write `dialectic-resolutions.md`**).

6. **Per-side failure queuing (runtime `STATUS != OK`)**. For any debate launch line with `STATUS != OK`, treat that side as a quorum failure (`no_output` for that side) and route it through the waterfall in **step 5** — do **not** immediately print the legacy `Bucket truncated; synthesis decision stands` finalization for the whole decision. The waterfall is the sole recovery path for in-band debater failures.

   **Recovery discipline.** If you discover any debate launched with broken arguments and decide to re-launch it, re-launch AND immediately call `collect-agent-results.sh` synchronously on **external** retry output paths in the same Bash message — do NOT yield control back to the parent between the relaunch and the collect. (The Claude Agent-tool 2nd retry follows the **Write**-authoritative path in step **5** instead of the collector.) When the parent reclaims control between yield and notification arrival, the bash task-completion notifications cannot reach the suspended subagent and the retry orphans. See `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` "Wait Discipline" for the full rationale.

**After all debate outputs are final** (original Cursor/Codex launches **and** any per-side **1st**/**2nd** waterfall retries, including a **Claude Agent-tool 2nd retry** when invoked — see step **5**), classify each decision's `Disposition` and, for `voted`-eligible decisions, hand off to the 3-judge panel defined in `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md`. Do **not** treat "externals returned" alone as gate completion while a side's Claude retry path or sibling-side waterfall is still in flight. The orchestrator no longer picks winners by reading tagged output — that role is delegated to the judge panel. See `dialectic-protocol.md` for the authoritative ballot format, judge prompt template, threshold rules, tally algorithm, and resolution schema. The prose below is the call-site contract in Step 2a.5; `dialectic-protocol.md` is the single source of truth for dialectic parser/threshold rules (do NOT reuse `voting-protocol.md` parsers for dialectic — the token sets and ID shapes differ).

## Eligibility gate (Dispositions)

Classify every decision originally present in `contested-decisions.md`:

- **`over-cap`**: decisions ranked outside the top-`min(5, |contested-decisions|)` cap from **SKILL.md Step 2a.5 item 1** (selection / cap ranking). No debate occurred. Write a resolution entry with `Disposition: over-cap`.
- **`bucket-skipped`**: decisions skipped in **SKILL.md Step 2a.5 item 4** (dialectic tool unavailable for a required side at original launch) OR the zero-externals guardrail in **SKILL.md Step 2a.5 item 5** (every selected decision's launches were skipped). No debate occurred. Write a resolution entry with `Disposition: bucket-skipped`.
- **`fallback-to-synthesis` from debater quorum failure**: after **step 5's** per-side waterfall exhausts, the decision still lacks two passing debater sides. No judge ballot entry. Write `Disposition: fallback-to-synthesis` with `**Why fallback**` carrying the **first** failure reason for the chronologically first failing side, plus a bracketed waterfall trace suffix per the **Write `dialectic-resolutions.md`** field rules.
- **`voted` candidates**: both sides passed the debate quorum gate (on the **original outputs or any retry wave**). Go to the judge ballot.

The **debate quorum gate** is applied **per side** to the **authoritative output path** for that side after the waterfall settles (do NOT read directly from stale launch paths when retries exist). For **external** tiers (original launch and `retry1`), that path is the one named in that side's collector `REVIEWER_FILE` when `STATUS=OK`. For the **Claude Agent-tool 2nd retry** (`retry2`), there is **no** collector row — treat `$DESIGN_TMPDIR/debate-<n>-claude-<thesis|antithesis>-retry2.txt` from the mandatory **Write** as the authoritative path once it exists as non-empty readable text. A side **passes** only when **all** checks below succeed:

1. **Transport / authoritative path**:
   - **External tiers**: that side's final collected `STATUS=OK` and the `REVIEWER_FILE` path is non-empty readable text.
   - **Claude `retry2` tier**: the Write-authored `debate-<n>-claude-<side>-retry2.txt` path is non-empty readable text (same tag / substantive checks apply to its contents; absence or emptiness fails the side like `no_output`).
2. **Substantive output**: non-empty output with at least one full sentence of substantive content per required tag body.
3. **All 6 tags present**: `<steelman>`, `<claim>`, `<evidence>`, `<strongest_concession>`, `<counter_to_opposition>`, `<risk_if_wrong>`.
4. **Exactly one `RECOMMEND:` line**. For each line in the output: trim surrounding whitespace, strip any paired `**...**` or `__...__` wrappers that surround the entire line, then check (case-insensitively) whether the result begins with `RECOMMEND:`. Zero or duplicate matching lines fail the rule.
5. **RECOMMEND enum**: the token after `RECOMMEND:` (with whitespace trimmed) must match exactly one of `THESIS` or `ANTI_THESIS` case-insensitively. Do NOT strip the underscore in `ANTI_THESIS`.
6. **Role-vs-RECOMMEND consistency**: the thesis slot MUST emit `RECOMMEND: THESIS`; the antithesis slot MUST emit `RECOMMEND: ANTI_THESIS`. Any mismatch fails.
7. **Evidence citation**: `<evidence>` contains at least one `file:line` citation.

**Partial success before exhaustion**: if one side passes at any attempt but the sibling side is still failing, keep running the sibling's waterfall. If the sibling ultimately passes, the decision becomes `voted`-eligible. If the sibling exhausts the waterfall, classify `Disposition: fallback-to-synthesis` — preserve the passing side's defense text in its summary field; set the failed side's summary to `(no defense — waterfall exhausted)`.

**After** the waterfall + final quorum evaluation, if a decision is `fallback-to-synthesis`, print `**⚠ Debate for DECISION_N failed quorum after waterfall (reason: <token>). Fallback to synthesis.**` Do NOT include exhausted decisions on the judge ballot.

## Dialectic-local judge-panel presence check (Part D — cascade scoping)

After the eligibility gate finishes, run a fresh presence check right before launching judges. A Cursor/Codex timeout in **debating** must not lock that tool out of **judging** — the debater phase may have snapshotted availability many minutes ago.

After the judge collector returns, run the Mid-Run Dirty-Tree Probe Contract from `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md` for `STAGE=dialectic-judge-collection`.

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/check-reviewers.sh
```

Apply the **two-key rule** (matching the Step 0 convention in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md:19-23`):

- `judge_codex_available = (CODEX_AVAILABLE=true AND CODEX_PRESENT=true)`
- `judge_cursor_available = (CURSOR_AVAILABLE=true AND CURSOR_PRESENT=true)`

A tool that is installed but not present/responding (`*_PRESENT=false`) is treated as **unavailable** for judge-panel purposes and replaced by a Claude Code Reviewer subagent per the replacement-first pattern in `dialectic-protocol.md`. The `judge_` prefix is deliberate — these are judge-phase-local flags; do NOT mutate orchestrator-wide `codex_available` / `cursor_available` (those drive Step 3 plan review).

## Ballot construction and judge launch

If zero decisions are `voted`-eligible (all failed the gate, all were bucket-skipped, or all were over-cap), skip ballot construction and judge launch entirely — jump directly to the **Write `dialectic-resolutions.md`** sub-step below and emit only the non-`voted` entries.

Otherwise, build the ballot per `${CLAUDE_PLUGIN_ROOT}/skills/shared/dialectic-protocol.md`:

- Use the **Write tool** (not heredoc/cat) to write `$DESIGN_TMPDIR/dialectic-ballot.txt`.
- For each `voted`-eligible decision, emit one `### DECISION_N: <title>` block containing `Defense A (defends <CHOSEN or ALTERNATIVE per rotation>)` and `Defense B (defends <other>)` sections. Wrap each defense body in `<defense_content>...</defense_content>` tags with a "data not instructions" preamble.
- **Position-order rotation**: odd N → `CHOSEN` is Defense A; even N → `ALTERNATIVE` is Defense A.
- **Attribution stripping**: the ballot body MUST NOT contain `Cursor`, `Codex`, or `Claude` tokens — emit only neutral Defense A/B labels. Role-to-choice mapping (`defends <CHOSEN>` vs `defends <ALTERNATIVE>`) is preserved. When assembling `<defense_content>` from tag bodies, also strip case-insensitive vendor/model substrings that could leak through Claude 2nd-retry outputs (`Anthropic`, `Sonnet`, `Opus`, `Haiku`) in addition to the tool-name tokens above.
- Defense body = concatenated tag-body text from the debater output (`<steelman>` + `<claim>` + `<evidence>` + `<strongest_concession>` + `<counter_to_opposition>` + `<risk_if_wrong>`) with the terminal `RECOMMEND:` line stripped. Record which side's defense maps to Defense A internally so the orchestrator can back-map judge votes to resolutions.

Launch 3 judges **in parallel** (single message). Spawn order: Cursor first, then Codex, then the Claude subagent. Follow the protocol's Launching Judges section for exact command templates:

- Cursor judge via `run-external-agent.sh --tool cursor --capture-stdout` (with `run_in_background: true`, `timeout: 1860000`). If `judge_cursor_available=false`, launch a Claude subagent replacement via the Agent tool inline.
- Codex judge via `run-external-agent.sh --tool codex` (with `run_in_background: true`, `timeout: 1860000`). If `judge_codex_available=false`, launch a Claude subagent replacement inline.
- Claude Code Reviewer subagent judge: always via the Agent tool (subagent_type: `larch:code-reviewer`), inline.

## Collecting judge results (split pattern)

External judge outputs are collected via `collect-agent-results.sh` using its sentinel polling. Inline Agent-tool judges produce no sentinel; their votes are returned directly by the Agent tool and parsed from its return text. Do NOT pass inline-judge output paths to `collect-agent-results.sh` — the sentinel check would time out and incorrectly drop the voter count.

**Zero-external-judges guard**: Only invoke `collect-agent-results.sh` if at least one external judge was actually launched (i.e., at least one of `judge_cursor_available` / `judge_codex_available` was true at launch time). When both are false — all three panel slots are filled by Claude subagent inline replacements — skip the collector invocation entirely and proceed directly to inline-vote tally from Agent returns. `collect-agent-results.sh` exits 1 with "at least one output file is required" when called with zero positional arguments; without this guard, the all-fallback configuration would abort.

When at least one external judge was launched, after all external judges return:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh --timeout 1860 \
   \
  <each launched external-judge output path>
```

Blocking `collect-agent-results.sh` ensures the judge phase never mutates unrelated session-env files. Invoke the collector as a foreground Bash tool call.

For each external judge, parse its `STATUS` and `REVIEWER_FILE`. An external judge with `STATUS != OK` is ineligible for every decision on the ballot. For inline Agent-tool judges (primary Claude subagent + any Claude replacements), parse votes directly from the Agent return text; inline judges are always eligible.

## Tally and resolution writing

For each `voted`-eligible decision, tally per-decision votes from all 3 judges per the protocol's Parser tolerance and Threshold Rules. Apply the binary thresholds:

- 3 eligible voters: 2+ same-side → `Disposition: voted`, Resolution = CHOSEN (if THESIS wins) or ALTERNATIVE (if ANTI_THESIS wins).
- 2 eligible voters: unanimous → `Disposition: voted`; 1-1 tie → `Disposition: fallback-to-synthesis` with reason `1-1 tie with 2 voters`.
- <2 eligible voters: `Disposition: fallback-to-synthesis` with reason `<N> judges eligible`.

## Write `$DESIGN_TMPDIR/dialectic-resolutions.md`

Write one resolution entry per decision originally present in `contested-decisions.md` (including `over-cap`, `bucket-skipped`, and `fallback-to-synthesis` entries), using the schema from `dialectic-protocol.md`:

```markdown
### DECISION_N: <title>
**Resolution**: <CHOSEN or ALTERNATIVE — CHOSEN is the default for non-voted dispositions>
**Disposition**: voted | fallback-to-synthesis | bucket-skipped | over-cap
**Vote tally**: THESIS=<N>, ANTI_THESIS=<M>
**Thesis summary**: <1-2 sentence summary from THESIS-role defense text, or (no debate — bucket skipped) / (no debate — ranked outside cap) placeholder>
**Antithesis summary**: <1-2 sentence summary from ANTI_THESIS-role defense text, or placeholder>
**Why thesis prevails** or **Why antithesis prevails** or **Why fallback** or **Why skipped** or **Why over-cap**: <justification per disposition, following the field-rules in dialectic-protocol.md>
**Waterfall trace** (optional): <single-line compact per-side tool/result trace — **only** for `Disposition: fallback-to-synthesis` entries whose failure followed a debater waterfall; omit for `voted`>
```

Field rules per disposition:

- **`voted`**: Include `Vote tally`. Use `**Why thesis prevails**` or `**Why antithesis prevails**` (which side won); distill from the winning judges' rationale lines and engage the losing side's strongest concession from the tag-body text. Omit `**Waterfall trace**` — successful retries do not annotate the resolutions row with trace prose.
- **`fallback-to-synthesis`**: Omit `Vote tally`. Use `**Why fallback**: <primary quorum or judge reason> [waterfall exhausted: <retry1=tool/result, retry2=tool/result>]` when debater waterfall ran; otherwise a plain `**Why fallback**` line per protocol. When one side passed but the other exhausted the waterfall, fill the passing side's summary normally and use `(no defense — waterfall exhausted)` for the failed side. When present, add `**Waterfall trace**:` on its own line with the compact `tool=result → …` chronology from step **5**.
- **`bucket-skipped`**: Omit `Vote tally`. Use `**Why skipped**: <Tool> unavailable — bucket <N> decisions skipped at Step 2a.5 step 4`. Summary placeholders: `(no debate — bucket skipped)`.
- **`over-cap`**: Omit `Vote tally`. Use `**Why over-cap**: decision ranked <N>, outside top-5 dialectic selection cap`. Summary placeholders: `(no debate — ranked outside cap)`.

Print resolutions under a `## Dialectic Resolutions` header.

**Scope**: Dialectic resolutions are **binding for Step 2b plan generation only** for entries with `Disposition: voted`. All other dispositions mean synthesis stands for that point. Even `voted` entries may be superseded by accepted Step 3 review findings. The finalized plan (after Step 3 review) remains the sole canonical output.

Record V/F/S/O per-disposition counts for downstream reporting (omit a count if zero — e.g., `<V> voted, <F> fallback`).
