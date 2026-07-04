## Plan

Drafted from direct repository inspection because `approach-synthesis.txt` is `NO_SKETCHES`. The approved outline and round-1 decisions are binding.

## Approach

Add a narrow rule: orchestrator-facing grep-family probes must not use parent-directory ascents in path operands. Use absolute paths or known bounded roots such as `$CLAUDE_PLUGIN_ROOT/python/`.

Keep the implementation line-based and consistent with the current linter. Do not add a shell parser.

## Files to modify/create

### UPDATED: BASH_AUTHORING.md

Add a short "Bounded search roots" subsection under section 1.

State:

- Background grep-family probes must use absolute paths or known bounded roots.
- Do not derive search roots with `../` or `..` segments from tmpdir variables such as `$IMPLEMENT_TMPDIR`.
- Prefer direct bounded commands over discovery greps when a CLI can answer the question, for example `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" ... --help`.
- The same `# lint-bare-grep-probe: ok <reason>` pragma is only for rare fixtures or reviewed exceptions.

Keep the net line change small. The current file has 97 lines; the tier-1a cap is 97. Either keep the edit line-neutral (condense or remove equal lines elsewhere in section 1) or update `python/larch/lint/lint_tier1a.py` with the new cap.

### UPDATED: python/larch/lint/lint_tier1a.py

Update `TIER1A_LINE_CAPS["BASH_AUTHORING.md"]` from `97` to the actual post-edit line count. Run `make lint-tier1a-size` after the change to confirm the new count passes.

### UPDATED: skills/implement/references/stall-recovery.md

Add a note covering all prompt-side investigation probes across sub-steps 5-8 of Step 18a:

- Any prompt-side investigation probe during Step 18a (retry dispatch, token discovery, or any other sub-step) must follow `BASH_AUTHORING.md` bounded-root guidance.
- Use `$CLAUDE_PLUGIN_ROOT` anchored paths or direct `python/cli.py` calls. For token-value discovery, use `python/cli.py stall-recovery validate-token --token-kind trigger --value CANDIDATE` or refer to the listed owner tokens `step2-impl` and `step8-shippr`.
- Do not search via `../` ascents from `$IMPLEMENT_TMPDIR` at any sub-step.

Do not change stall-recovery ownership, recording, or filing semantics.

### UPDATED: scripts/lint-bare-grep-probe.sh

Extend the existing awk token analysis.

Add a new violation class for grep-family path operands that contain a parent-directory segment. Prefer a segment-aware helper such as:

- flag `../foo`
- flag `foo/../bar`
- flag `$IMPLEMENT_TMPDIR/../../../..`
- flag `foo/..`
- do not flag `..hidden`, `v1..2`, or option values that merely contain dots

Use a helper equivalent to `(^|/)\\.\\.(/|$)` on the token value.

Integrate with existing parsing:

- Reuse the current candidate command detection.
- Skip grep and ripgrep option values; skip the pattern operand.
- Treat the first positional as the pattern unless `-e`, `--regexp`, `-f`, or `--file` already supplied the pattern.
- Iterate ALL path operands after the pattern (reuse the existing option/pattern/`--` terminator rules) and flag any operand matching `(^|/)\\.\\.(/|$)`. Do not stop after the first path operand.
- Run the parent-ascent check before the `< /dev/null` no-path short-circuit, so `rg PATTERN ../root < /dev/null` still fails.
- Preserve current wrapper-trap behavior. A bare `grep` line may still report the wrapper violation first.
- Preserve same-line suppression with `# lint-bare-grep-probe: ok <reason>`.

Add a report message that tells the author to use an absolute path or a known bounded root instead of `../` ascents.

### UPDATED: scripts/test-lint-bare-grep-probe.sh

Add focused regression cases.

Violation cases:

- `command grep -r PATTERN "$IMPLEMENT_TMPDIR/../../../.."`
- `( command grep -rn PATTERN "$IMPLEMENT_TMPDIR/../../../.." ) || true`
- `rg -n PATTERN ../python`
- `ripgrep -n PATTERN skills/../python`
- `rg -n PATTERN python/..`
- `rg -n PATTERN -- ../python`
- `rg -n PATTERN ../python < /dev/null`
- `rg -n PATTERN "$CLAUDE_PLUGIN_ROOT/python" ../python` (safe first path, unsafe second path)

Allowed cases:

- `command grep -r PATTERN "$CLAUDE_PLUGIN_ROOT/python"`
- `rg -n PATTERN "$CLAUDE_PLUGIN_ROOT/python"`
- `rg -e "../pattern" python/`
- `command grep -e "../pattern" python/file.py`
- `rg -n PATTERN .`
- a same-line pragma suppressing one intentional ascent fixture

Assert the new stderr text for at least one violation.

### UPDATED: scripts/lint-bare-grep-probe.md

Update the contract doc to include the new parent-ascent rule.

Document:

- The linter rejects `..` path segments in any grep-family path operand.
- All path operands after the pattern are checked, not only the first.
- Absolute paths and known bounded roots are preferred.
- Pattern operands and option values are not path operands.
- Same-line pragma suppression remains available for reviewed exceptions.
- The limitation remains line-based.

### UPDATED: scripts/test-lint-bare-grep-probe.md

Add the new fixture families to the harness contract.

Mention:

- parent-ascent violations for `grep`, `rg`, and `ripgrep`
- multi-path violation where the first path is safe but a later one contains `../`
- option and pattern false-positive guards
- pragma suppression for a reviewed fixture

### UPDATED: docs/linting.md

Update the `Bare top-level grep in orchestrator markdown` row to mention parent-directory ascent detection in grep-family path operands.

Keep it concise. Do not change lint wiring, because the pre-commit hook and Makefile target already exist.

## Edge cases

- `-e "../pattern"` and `--regexp="../pattern"` are patterns, not paths.
- `--include="../*.py"` and similar option values should not trigger the path rule.
- `--` ends options, but the first following positional is still the pattern unless a pattern option already supplied it.
- Quoted paths still tokenize to values, so quoted `"$IMPLEMENT_TMPDIR/../../../.."` should fail.
- A command with a safe first path and a later `../` path (e.g., `rg PATTERN /safe ../bad`) must still fail.
- Existing multi-line and pipeline limitations remain. Do not widen the linter beyond the current line-based candidate model in this change.

## Failure modes

- A broad substring check can false-positive on non-path tokens. Use a path-segment check and only inspect path operands.
- Stopping after the first path operand leaves later `../` ascents undetected. Iterate all path operands.
- Changing option parsing can regress existing no-path detection. Keep current cases intact and add only targeted helpers.
- Docs can drift from the linter. Update the script contract, harness contract, and linting row with the behavior change.
- The BASH_AUTHORING.md tier-1a cap at 97 lines will fail if the net addition is not reflected in `lint_tier1a.py`.

## Testing strategy

Run focused checks:

```bash
bash scripts/test-lint-bare-grep-probe.sh
bash scripts/lint-bare-grep-probe.sh
make test-lint-bare-grep-probe
make lint-bare-grep-probe
make lint-bash32
make lint-tier1a-size
```

If Markdown lint runs locally, also run the relevant pre-commit hooks for changed Markdown.

## Acceptance

Run focused checks:

```bash
bash scripts/test-lint-bare-grep-probe.sh
bash scripts/lint-bare-grep-probe.sh
make test-lint-bare-grep-probe
make lint-bare-grep-probe
make lint-bash32
make lint-tier1a-size
```

If Markdown lint runs locally, also run the relevant pre-commit hooks for changed Markdown.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
diff_added: 150
diff_deleted: 20
mechanical_churn: false
diff_lines: 170
