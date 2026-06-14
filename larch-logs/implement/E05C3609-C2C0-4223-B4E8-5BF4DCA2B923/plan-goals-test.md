## Goal
Implement issue #4340: [IMPLEMENTING] /design and /implement final-summary Gantt charts dropped: marker body emitted via tool call instead of plain chat text.

## Implementation Plan
## Plan

## Approach

Make the minimum prompt and harness change to eliminate the ambiguity that allows orchestrators to use Bash/Python tool calls to extract and print the final-summary body.

- Keep wrapper scripts and summary rendering unchanged.
- Add explicit delivery-channel prohibitions at every final-summary emit site in `skills/design/SKILL.md`.
- Fix `skills/implement/SKILL.md` Step 17 prose that currently sanctions `Bash cat`; add prohibitions at NEVER #17 and Step 18b.
- Add structural regression pins that fail CI if `LARCH_FINAL_SUMMARY_BEGIN` appears inside any bash fence in SKILL.md.

### Shared delivery-channel contract (define once; paste or cross-reference at every emit site)

```
Do NOT use a Bash tool call, Python script, or any other tool invocation to extract
or print the final-summary body — tool output lands in a collapsible block invisible
by default; write the extracted content directly as your own orchestrator text response.
```

## Files to modify/create

### UPDATED: `skills/design/SKILL.md`

Add the prohibition sentence at every final-summary emit site:

**Anti-halt reminder block**: append after the `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}` Read fallback mention: "Both the marker extraction and the Read-tool fallback must deliver the body as plain orchestrator text — never via a Bash or Python tool call."

**Final summary block section** (~line 349): after "emit that body verbatim as plain chat markdown (same mechanism as Step 5c item 5)", add: **"Do NOT use a Bash tool call, Python script, or any other tool invocation to extract or print the final-summary body — tool output lands in a collapsible block invisible by default; write the extracted content directly as your own orchestrator text response. Primary path: locate the markers in the task notification output text already in your context window and write the extracted body as plain text. Read-tool fallback: use the Read tool on `${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md}`; write the Read result as plain text — do not re-enter it into another tool call."**

Also replace `(same Read/`cat` mechanism; no paraphrase)` with `(same Read-to-orchestrator-text mechanism; no paraphrase)` for the REPORT_GATE_SIDECARS_FILE sidecar reference.

**Step 5c abort path** (~line 863): after "extract and emit the marked final-summary body from completed `design-step5c.sh` stdout using the first balanced `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` pair", add: "**Do NOT use a Bash tool call to extract or print this body — locate the markers in the task output text already in context and write the extracted body as plain orchestrator text.**"

**Step 5c item 5** (~line 867): after "Extract the final-summary body from the completed `design-step5c.sh` task output using the first balanced `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` whole-line marker pair, then emit that body verbatim as plain chat markdown.", add: "**Do NOT use a Bash tool call, Python script, or any other tool invocation to extract or print the final-summary body — tool output is collapsible; write the extracted content as your own orchestrator text response.**"

### UPDATED: `skills/implement/SKILL.md`

**NEVER #17** (~line 63): in the "How to apply" section, after "After the orchestrator actually emits the full body of summary-final.md verbatim as plain chat markdown", add: "**(Do NOT use a Bash `cat` or Python tool call to print the summary body — tool output is rendered in a collapsible block; write the file content as your own orchestrator text.)**"

**Step 17 prose** (~line 814): replace:
```
Mechanism: read `summary-final.md` (via Read, or via Bash `cat` whose output is then re-emitted as orchestrator text), emit the entire file body verbatim as plain markdown chat text
```
with:
```
Mechanism: read `summary-final.md` via the Read tool, then write the full file body directly as your own orchestrator text response. **Do NOT use a Bash `cat` or Python tool call to print the summary body** — tool output is rendered in a collapsible block, and users who do not expand it miss the per-agent cost breakdown. Emit the entire file body verbatim as plain markdown chat text
```

**Step 18b** (~line 866): after "the orchestrator MUST emit the full body of summary-final.md verbatim as plain chat markdown. Use the same collapse-resistant rule as Step 17", add: "**(Do NOT use a Bash tool call to print the body — write the Read result directly as orchestrator text.)**"

### UPDATED: `scripts/test-design-structure.sh`

Inside `assert_step5_fold_and_summary_markers`, add after the existing `contains "$SKILL_MD" ...` lines:

```bash
  # LARCH_FINAL_SUMMARY_BEGIN/END must not appear inside bash fences in SKILL.md
  python3 - "$SKILL_MD" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
fences = re.findall(r'```bash\n(.*?)\n```', text, flags=re.S)
for fence in fences:
    if 'LARCH_FINAL_SUMMARY_BEGIN' in fence:
        print('FAIL: skills/design/SKILL.md bash fence must not reference LARCH_FINAL_SUMMARY_BEGIN', file=sys.stderr)
        sys.exit(1)
    if 'LARCH_FINAL_SUMMARY_END' in fence:
        print('FAIL: skills/design/SKILL.md bash fence must not reference LARCH_FINAL_SUMMARY_END', file=sys.stderr)
        sys.exit(1)
PY
  contains "$SKILL_MD" 'Do NOT use a Bash tool call, Python script, or any other tool invocation to extract or print the final-summary body' 'SKILL missing final-summary delivery-channel prohibition'
  contains "$SKILL_MD" 'write the extracted content directly as your own orchestrator text response' 'SKILL missing final-summary orchestrator-text requirement'
```

### UPDATED: `scripts/test-implement-structure.sh`

Add to the Python block:

```python
# LARCH_FINAL_SUMMARY_BEGIN/END must not appear inside bash fences in implement SKILL.md
text_impl = Path(skill).read_text()
in_fence = False
fence_has_marker = False
for line in text_impl.splitlines():
    stripped = line.strip()
    if stripped == '```bash':
        in_fence = True
    elif stripped == '```':
        in_fence = False
    elif in_fence and ('LARCH_FINAL_SUMMARY_BEGIN' in line or 'LARCH_FINAL_SUMMARY_END' in line):
        fence_has_marker = True
        break
if fence_has_marker:
    checks.append('SKILL.md bash fence must not reference LARCH_FINAL_SUMMARY_BEGIN or LARCH_FINAL_SUMMARY_END')

# Step 17 delivery-channel prohibition must exist
require(skill, 'Do NOT use a Bash `cat` or Python tool call to print the summary body', 'SKILL missing Step 17 delivery-channel prohibition')
# Old Bash-cat mechanism text must be gone
forbid(skill, 'via Bash `cat` whose output is then re-emitted as orchestrator text', 'SKILL must not sanction Bash cat for summary emit')
```

## Edge cases

- `LARCH_FINAL_SUMMARY_BEGIN` may still appear in wrapper scripts (required) and in SKILL.md prose — only bash-fence appearances are forbidden.
- The Read-tool fallback is permitted; the prohibition targets re-entering the Read result into another Bash/Python tool call.
- Step 18b may refresh `summary-final.md` after Step 17; keep the `EMIT_BODY=true` gate unchanged.
- `(same Read/cat mechanism)` sidecar references must also be updated to avoid re-normalizing `cat` as acceptable.

## Failure modes

- If the prohibition text is not a verbatim substring in SKILL.md, the `contains` pin in the test will fail. Use the exact canonical phrase defined in the plan's Shared contract section.
- If `.step17-emitted` semantics change, confirm the sentinel contract remains: write after the orchestrator completes the top-chat emission.

## Testing strategy

- `make test-design-structure` — validates new bash-fence absence pins and prohibition prose `contains` checks.
- `make test-implement-structure` — validates the same for implement SKILL.md.
- `bash scripts/relevant-checks.sh` — repo-wide check suite.
- Negative checks: temporarily insert `LARCH_FINAL_SUMMARY_BEGIN` in a bash fence in each SKILL.md and confirm the corresponding structure test fails.

## Acceptance

- After the fix, `/design` and `/implement` run output contains the full `## Review Phase Detail` section in visible chat text, not inside a collapsed tool result.
- `make test-design-structure` and `make test-implement-structure` pass with the new pins active.

diff_lines: 174

## Test plan
(no test plan section in plan-file)
