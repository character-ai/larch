# Review Round 5

- Mode: `diff`
- 2 accepted, 8 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: Stdout fallback omits `coder` / `coder_fallback` in parse script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sourced-scope-leak-output.txt
- **Severity**: important
- **Concern**: `_inv_apply_routing_line_if_empty` in `scripts/parse-bootstrap-routing-envelope.sh` (roughly lines 72–104) has no `coder` / `coder_fallback` arms, while `_inv_apply_routing_line` assigns them via `printf -v`. When `bootstrap-routing.env` is skipped (symlink / non-regular file per `implement-bootstrap-invoke.sh`) or missing keys, only the stdout envelope in `_inv_out` remains; `coder` and `coder_fallback` stay unset after the initial `unset` even though the wrapper stdout includes `coder=…` from phase selection. Step 0 routing can miss the continue row or pick the wrong implementer — a regression vs the old `_ib_kv_scan` path that parsed every stdout line including `coder=*`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add coder/coder_fallback to if-empty case or printf -v when empty; add symlink+parse harness coverage
  - From cursor-specialist-correctness-output.txt: Add coder/coder_fallback branches to _inv_apply_routing_line_if_empty (or reuse _inv_apply_routing_line for empty keys) and test parse after the symlink wrapper harness case.
  - From cursor-specialist-testing-output.txt: Add coder and coder_fallback to _inv_apply_routing_line_if_empty assignment case with the same non-empty guard used in _inv_apply_routing_line
  - From cursor-specialist-edge-cases-output.txt: Add coder/coder_fallback to _inv_apply_routing_line_if_empty or unify apply helpers; add parse+symlink harness case
  - From dyn-sourced-scope-leak-output.txt: Add `coder` and `coder_fallback` arms to `_inv_apply_routing_line_if_empty` (e.g. `[ -z "${coder:-}" ] && coder="$_inv_value"` with the same empty-value skip and `--preserve-coder` early-return as the file path), or call `_inv_apply_routing_line` for the stdout loop when the file pass was skipped; add a harness case that sources the parse script against a symlinked `bootstrap-routing.env` and asserts `coder` is exported.


### FINDING_5: No end-to-end test for symlink stdout path through parse script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Documented symlink / stdout-only routing path is covered at the wrapper level (`skills/implement/scripts/test-implement-bootstrap-invoke.sh` ~301–318 / ~1808–1827) but harness does not source `parse-bootstrap-routing-envelope.sh` afterward. CI can pass while the parse step drops `coder` on the documented fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Test wrapper then source parse-bootstrap-routing-envelope.sh with symlinked bootstrap-routing.env
  - From cursor-specialist-testing-output.txt: Add harness case that sources parse-bootstrap-routing-envelope.sh after wrapper success with symlinked bootstrap-routing.env and asserts coder and REPO from _inv_out
  - From cursor-specialist-edge-cases-output.txt: Add sourced-parse test with symlinked bootstrap-routing.env asserting exported coder


