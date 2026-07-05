## Proposed Design Outline

### Goals
- Extend parent-ascent detection to grep-family commands after `||`, `|`, `;`, and `&&`.
- Check `-f`/`--file` operand paths for `../` segments.
- Fix split-value option-parsing edge cases that let a parent-ascent operand bypass detection.
- Merge the two near-identical argv-walker functions to cut drift risk.

### Non-goals
- Multiline/continuation-line scanning (line-based limitation; document only).
- Absolute-root bounding (design decision; document only).
- Changing wrapper-exit trap logic or stdin-path behavior.
- Updating any CI workflow YAML or shard assignments.

### Approach sketch
- In `scripts/lint-bare-grep-probe.sh`: extend the awk script to scan tokens after `||`, `|`, `;`, `&&` for grep-family candidates (gap 1 and 3 together).
- Add `../` checks for `-f`/`--file` split-value operands in the path-inspection logic (gap 2).
- Audit and fix the `--include`/`--exclude` split-value tokenizer path to ensure `../` operands are not silently skipped (gap 4).
- Refactor `has_parent_ascent_path` and `has_explicit_path` to share a common inner token-walk helper (gap 5).
- Extend `## Limitations` in `lint-bare-grep-probe.md` for gaps 6 and 7.
- Add regression test cases in `scripts/test-lint-bare-grep-probe.sh`.

### Surfaces in scope
- `scripts/lint-bare-grep-probe.sh`
- `scripts/test-lint-bare-grep-probe.sh`
- `scripts/lint-bare-grep-probe.md`
- `scripts/test-lint-bare-grep-probe.md`

### Open questions
- Gap 4 exact trigger: identify the specific token sequence where `--include`/`--exclude` split-value form lets a `../` path slip through (requires tracing `option_takes_value` vs. `is_pattern_option` behavior in the awk tokenizer during drafting).
