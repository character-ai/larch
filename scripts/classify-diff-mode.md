# classify-diff-mode.sh

**Purpose**: Classify a pre-computed git diff by its `diff --git` path headers so specialist review prompts can use a narrower mode when every changed file is documentation-only, test-only, or generated-only. Mixed, empty, malformed, renamed-across-category, or unknown paths are conservative and emit `DIFF_MODE=generic`.

**Invariants**:
- Deterministic: no timestamps, no git state, no locale-dependent output (`LC_ALL=C`).
- All diagnostics on stderr; the only successful stdout shape is `DIFF_MODE=<mode>`.
- `set -euo pipefail` by default.
- Classification is path-only and conservative. Any ambiguity returns `generic` rather than a narrowed prompt.

**Arguments**:
- `<diff-file>` (required): Path to a pre-computed unified git diff. The file must exist.

**Modes**:
- `docs-only`: all `diff --git` paths are recognized documentation surfaces such as `docs/*`, root docs, or script sibling `.md` files.
- `test-only`: all paths are recognized test harnesses or test directories.
- `generated-only`: all paths are registered generated artifacts in `scripts/generators.tsv`.
- `generic`: empty diffs, unknown paths, mixed categories, malformed `diff --git` headers, or any other ambiguous case.

**Output**: One line: `DIFF_MODE=generic`, `DIFF_MODE=docs-only`, `DIFF_MODE=test-only`, or `DIFF_MODE=generated-only`.

**Exit codes**:
- 0: classification emitted
- 2: usage error or missing diff file

**Primary caller**: `scripts/render-specialist-prompt.sh`, which falls back to `generic` if this helper fails.

**Harness**: Covered by `scripts/test-render-specialist-prompt.sh` because the classifier only exists to drive renderer prompt selection.

**Edit-in-sync**: When changing the mode enum, generated-artifact source, or path classification rules, update `scripts/render-specialist-prompt.sh`, `scripts/render-specialist-prompt.md`, and `scripts/test-render-specialist-prompt.sh` in the same PR.
