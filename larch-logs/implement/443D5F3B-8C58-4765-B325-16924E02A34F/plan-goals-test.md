## Goal
Drop session-persistent health flags; add static presence detection and three-phase waterfall fallback

## Implementation Plan

**Goal**: Drop session-persistent health flags (CODEX_HEALTHY/CURSOR_HEALTHY), replace with static presence detection at session-start (CODEX_PRESENT/CURSOR_PRESENT), and add a three-phase per-slot waterfall fallback (Phase 1: assigned tool, Phase 2: other present external tool, Phase 3: Claude) to every multi-slot dispatch.

---

### Phase 1: Delete health-flag machinery

**1a. `scripts/write-session-env.sh`**
- Remove `--codex-healthy` and `--cursor-healthy` options (parsing, validation, and write logic)
- Add `--codex-present` and `--cursor-present` options (same validation: must be `true` or `false`)
- In the written file, replace `CODEX_HEALTHY=` / `CURSOR_HEALTHY=` lines with `CODEX_PRESENT=` / `CURSOR_PRESENT=`
- Add `CODEX_PRESENT=` / `CURSOR_PRESENT=` to the written content block

**1b. `scripts/write-session-env.md`**
- Update header comment and option table: replace `--codex-healthy`/`--cursor-healthy` with `--codex-present`/`--cursor-present`

**1c. `scripts/collect-agent-results.sh`**
- Remove `--write-health <path>` option (lines ~145-157): argument parsing, `WRITE_HEALTH` variable, the "Read prior health state" block (~lines 223-231), the `CODEX_TOOL_HEALTHY`/`CURSOR_TOOL_HEALTHY` tracker variables (~lines 220-221), `get_tool_healthy`/`set_tool_unhealthy` helper calls, and the final `WRITE_HEALTH` output block (~lines 1011-1017)
- Remove `HEALTHY=` field from result record format (lines emitting `HEALTHY=true|false` in result entries)
- Keep all retry logic (`--meta` / `OUTER_LAUNCHER` reconstruction, empty-output retry) intact

**1d. `scripts/collect-agent-results.md`**
- Remove all `--write-health` references; remove `HEALTHY=` field from result record docs

**1e. `skills/implement/scripts/post-design-boundary.sh`**
- Delete `read_health_sidecar_value()` function (~lines 123-147)
- Delete `health_merge()` function (~lines 149-210)
- Delete the `health_merge` call at the end of the script
- Remove the `.health` sidecar variable (`local sidecar="${SESSION_ENV_PATH}.health"`) wherever referenced

**1f. `skills/implement/scripts/post-design-boundary.md`**
- Remove health-merge and `.health` sidecar documentation

---

### Phase 2: Repurpose check-reviewers.sh as presence probe

**2a. `scripts/check-reviewers.sh`**
Replace the current file with a simplified version that:
- Keeps `--skip-codex-probe` and `--skip-cursor-probe` flags (now renamed semantics: these skip the binary presence check entirely when set)
- Removes `--probe` flag and all health-probe machinery (pids, sentinels, wait-for-reviewers loops, evaluate_probe, start_probe, MAX_ATTEMPTS, SLEEP_BETWEEN, etc.)
- Changes output from `CODEX_HEALTHY=`/`CURSOR_HEALTHY=` to `CODEX_PRESENT=`/`CURSOR_PRESENT=`
- Logic: `command -v codex && CODEX_PRESENT=true || CODEX_PRESENT=false`; same for cursor
- Emits `CODEX_AVAILABLE=`/`CURSOR_AVAILABLE=` as backward-compat aliases (same values as PRESENT)

**2b. `scripts/check-reviewers.md`**
- Rewrite to document presence-only detection; remove all health-probe documentation

**2c. `scripts/test-check-reviewers.sh`**
- Rewrite for presence-only behavior: remove health-probe test cases (probe timeouts, retry loops, HEALTHY=false cases), keep binary-present/absent cases

---

### Phase 3: Update session-setup.sh

**3a. `scripts/session-setup.sh`**
- Remove `--write-health <path>` option (parsing + forwarding to check-reviewers.sh)
- Replace `check-reviewers.sh --probe` invocation with `check-reviewers.sh` (no --probe needed for presence detection)
- Replace reads of `CODEX_HEALTHY`/`CURSOR_HEALTHY` from caller-env with `CODEX_PRESENT`/`CURSOR_PRESENT`
- Update writes to session-env: emit `CODEX_PRESENT`/`CURSOR_PRESENT` (remove `CODEX_HEALTHY`/`CURSOR_HEALTHY`)
- Also emit `CODEX_AVAILABLE`/`CURSOR_AVAILABLE` (same values, for backward compat with callers that read these from session-env)
- Remove `--write-health` forwarding to write-session-env.sh

---

### Phase 4: Create new scripts

**4a. `scripts/launch-claude-review.sh`**
New script, analog to `launch-review.sh` for Claude-as-reviewer:
```bash
#!/usr/bin/env bash
# launch-claude-review.sh — Launch Claude as a code reviewer in a subprocess.
# Usage: launch-claude-review.sh --output <file> --agent-file <file> --mode diff|description
#   [--diff-file <file>] [--commit-count <N>] [--plan-file <file>] [--feature-file <file>]
#   [--scope-files <file>] [--description-text <text>] [--timeout <seconds>]
#   [--timing-task-kind <kind>]
# Writes output to --output; writes .done sentinel.
# Uses scripts/launch-claude-subprocess.sh with the same output-file contract.
```
Implementation: builds a prompt from agent-file + mode/diff/plan/feature context, calls `launch-claude-subprocess.sh --prompt-file <prompt> --output-file <output> --timeout <timeout> [context flags]`, writes `.done` sentinel on completion.

**4b. `scripts/launch-claude-review.md`**
Sibling contract for `launch-claude-review.sh`.

**4c. `scripts/dispatch-with-waterfall.sh`**
New script implementing three-phase waterfall:
```bash
#!/usr/bin/env bash
# dispatch-with-waterfall.sh — Three-phase per-slot waterfall dispatcher.
# 
# Usage:
#   dispatch-with-waterfall.sh \
#     --slots-file <ndjson-file> \       # {"slot":"<name>","tool":"codex|cursor","output":"<path>","agent":"<path>"}
#     --codex-present true|false \
#     --cursor-present true|false \
#     --mode diff|description \
#     [--diff-file <file>] [--commit-count <N>] \
#     [--plan-file <file>] [--feature-file <file>] \
#     [--scope-files <file>] [--description-text <text>] \
#     [--timeout <seconds>] \
#     [--fallback-counter-file <path>]  # incremented per Phase-3 (Claude) slot
#
# Output:
#   PHASE1_SLOTS=<space-separated output paths>
#   PHASE2_SLOTS=<space-separated output paths>
#   PHASE3_SLOTS=<space-separated output paths>
#   ALL_OUTPUT_FILES=<space-separated final output paths>
#   FALLBACK_COUNT=<N>
#   WARN=cost-fallback-exceeded-threshold  (when fallback_count > LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD, default 3)
```

Implementation:
1. Parse slots-file (ndjson), build array of (slot, tool, output, agent) tuples
2. **Phase 1 launch**: for each slot, if `*_PRESENT=true` for slot.tool, launch via `launch-review.sh --tool <tool> ...`; if `*_PRESENT=false`, add slot to p2_queue
3. **Phase 1 collect**: call `wait-for-reviewers.sh` on Phase 1 `.done` sentinels; call `collect-agent-results.sh --summary-only` on Phase 1 outputs; for each STATUS != OK, add slot to p2_queue (with phase1 output file to reuse path)
4. **Phase 2 launch**: for each slot in p2_queue, compute other_tool (if slot.tool=codex → try cursor; if slot.tool=cursor → try codex); if other_tool is PRESENT, launch via `launch-review.sh --tool <other_tool> ...` to a new output file; if other_tool also absent, add to p3_queue
5. **Phase 2 collect**: wait + collect; STATUS != OK → add to p3_queue
6. **Phase 3 launch**: for each slot in p3_queue, launch via `launch-claude-review.sh` to a new output file; increment fallback counter
7. **Phase 3 collect**: wait + collect; emit WARN if threshold exceeded
8. Build ALL_OUTPUT_FILES from final output per slot (Phase 3 result if available, else Phase 2, else Phase 1)
9. Emit KV output

Note: `collect-agent-results.sh --summary-only` already exists (line 167 in the current script). Use it to determine per-file STATUS without writing findings.

**4d. `scripts/dispatch-with-waterfall.md`**
Sibling contract for `dispatch-with-waterfall.sh`.

**4e. `scripts/test-dispatch-with-waterfall.sh`**
Tests:
1. `primary-fail-secondary-ok`: slot assigned to codex, codex present but fails → Phase 2 uses cursor (present), cursor succeeds
2. `primary-fail-secondary-fail-claude-ok`: slot fails Phase 1 and Phase 2 → Phase 3 Claude succeeds
3. `all-external-absent-claude-only`: codex-present=false, cursor-present=false → Phase 1 empty → Phase 3 Claude for all slots
4. `both-external-absent-claude-fail-hard-fail`: Phase 3 Claude also fails → slot hard-fails
5. `threshold-warning`: N Phase-3 fallbacks > LARCH_FALLBACK_CLAUDE_WARN_THRESHOLD → WARN emitted

**4f. `scripts/test-launch-claude-review.sh`**
Basic parity tests with test-launch-review.sh:
1. Successful launch writes output file and .done sentinel
2. Output passed through correctly
3. Non-zero timeout handled

---

### Phase 5: Update dispatch callers

**5a. `skills/review/scripts/dispatch-panel.sh`**
Replace the "both-down" and "one-down" fallback logic:
- Build a slots-manifest ndjson file under `$REVIEW_TMPDIR/slots-manifest.ndjson`
- Write one entry per slot: `{"slot":"<name>","tool":"cursor|codex","output":"<path>","agent":"<agent_path>"}`
- Call `dispatch-with-waterfall.sh --slots-file "$manifest" --codex-present "$CODEX_AVAILABLE" --cursor-present "$CURSOR_AVAILABLE" ... (mode, diff, plan args)`
- Parse `ALL_OUTPUT_FILES` and split into external_outputs/claude_outputs based on source tool (or just treat all as "external" since collect-agent-results.sh processes them uniformly)
- Remove the `panel_mode="both-down"` / `panel_mode="normal"` branches
- `PANEL_MODE` is now always `waterfall`

Note: `CODEX_AVAILABLE` and `CURSOR_AVAILABLE` are read from the session-env, and they are now equivalent to `CODEX_PRESENT`/`CURSOR_PRESENT`. The `--codex-available`/`--cursor-available` CLI interface remains (callers pass these).

**5b. `scripts/dispatch-code-voters.sh`**
Similar: build slots-manifest for voter slots (codex voter + cursor voter), call `dispatch-with-waterfall.sh`, parse output.

**5c. `scripts/dispatch-plan-voters.sh`**
Similar treatment.

---

### Phase 6: Update design references

**6a. `skills/design/references/heavy-worker.md`**
- In sketch dispatch section: use `dispatch-with-waterfall.sh` instead of direct launches
- In plan-review dispatch section: same
- Remove `--write-health` from all `collect-agent-results.sh` calls
- Change `CODEX_HEALTHY`/`CURSOR_HEALTHY` references to `CODEX_PRESENT`/`CURSOR_PRESENT`

**6b. `skills/design/references/plan-review.md`**
- Remove `--write-health` from collect-agent-results.sh invocations
- Update availability variable names (HEALTHY → PRESENT)

**6c. `skills/design/references/dialectic-execution.md`**
- Remove `--write-health /dev/null` from all collect-agent-results.sh calls
- Update availability checks (CODEX_HEALTHY → CODEX_PRESENT)

**6d. `skills/shared/dialectic-protocol.md`**
- Remove health-monotonicity prose
- Update any CODEX_HEALTHY/CURSOR_HEALTHY references

---

### Phase 7: Update SKILL.md documentation files

**7a. `skills/design/SKILL.md`**
- Remove `--write-health "${SESSION_ENV_PATH}.health"` from all session-setup.sh invocations (NEVER #4 section stays, just reword)
- Replace `CODEX_HEALTHY`/`CURSOR_HEALTHY` → `CODEX_PRESENT`/`CURSOR_PRESENT`

**7b. `skills/review/SKILL.md`**
- Remove health-state references; add PRESENT references

**7c. `skills/implement/SKILL.md`**
- Remove CODEX_HEALTHY/CURSOR_HEALTHY/AVAILABLE references from the Step 0 "Cross-Skill Health Propagation" section; update to presence model

**7d. `skills/research/SKILL.md`**
- Remove health references if any

---

### Phase 8: Update docs

**8a. `docs/external-reviewers.md`**
- Document waterfall and presence model
- Remove health-monotonicity prose

**8b. `skills/shared/external-reviewers.md`**
- Same

**8c. `scripts/external-tool-registry.md`**
- Remove health-envelope integration section; add presence-detection section

---

### Phase 9: Update existing tests

**9a. `scripts/test-collect-agent-results.sh`**
- Remove test cases that exercise `--write-health` (cases where health file is read/written)

**9b. `scripts/test-session-setup-health-defaults.sh` → rename to `test-session-setup-presence-defaults.sh`**
- Rewrite to test presence detection (CODEX_PRESENT/CURSOR_PRESENT output) instead of CODEX_HEALTHY/CURSOR_HEALTHY

**9c. `scripts/test-collect-agent-retry.sh`**
- Remove `--write-health` from all test invocations; confirm retry behavior is preserved

**9d. `scripts/test-design-structure.sh`**
- Remove assertions checking for `--write-health "${SESSION_ENV_PATH}.health"` in design SKILL.md

**9e. `skills/implement/scripts/test-post-design-boundary.sh`**
- Drop all `health_merge` test cases

**9f. `skills/review-and-fix/scripts/test-review-and-fix.sh`**
- Drop health-related test cases

---

### Acceptance criteria verification

After implementation, the following should hold:
- `git grep CODEX_HEALTHY` → no hits in skills/, scripts/, docs/, agents/, README.md, SECURITY.md
- `git grep CURSOR_HEALTHY` → same
- `git grep '\.health'` → no hits for session-env .health sidecar pattern
- `git grep health_merge` → zero hits

### Testing strategy

Run `/relevant-checks` after implementation to validate:
- pre-commit hooks pass
- agent-lint passes
- test scripts all pass (including new test-dispatch-with-waterfall.sh and test-launch-claude-review.sh)


## Test plan
(no test plan section in plan-file)
