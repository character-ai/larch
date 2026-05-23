### OOS_1: `README.md` consumer feature matrix
- **Description**: If end users (consumers of the larch plugin) should discover `make lint-foreground` as part of the plugin's quality posture, a short README mention would close that discoverability gap. Affected file: `README.md` (no line range cited).
- **Reviewer**: Cursor-Arch
- **Phase**: design


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_2: `.claude/rules/timing-task-kind-allowlist.md` stale `(28g)` reference
- **Description**: The rule file claims assertion `(28g)` lives in `scripts/test-implement-structure.sh`, but that anchor is absent from the current tree (confirmed by reviewer searches; this is the same stale anchor cited in FINDING_4). Affected file: `.claude/rules/timing-task-kind-allowlist.md` (around the lines describing the assertion).
- **Reviewer**: Cursor-Edge
- **Phase**: design


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: Stronger alternative — machine-readable allow/deny manifest
- **Description**: An alternative architecture would maintain a machine-readable allow/deny map (e.g., generated from `scripts/*.sh` metadata or a small manifest consumed by CI) and fail closed when a new blocking script is added without classification. Would touch broader automation than issue #2641's doc+lint scope. No repo line range yet.
- **Reviewer**: Cursor-Innovation
- **Phase**: design


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_4: `.pre-commit-config.yaml` header comment vs reality
- **Description**: The header comment in `.pre-commit-config.yaml` claims "CI uses: make lint" while `.github/workflows/ci.yaml` actually runs `make lint-only` for the `lint` job (this is the underlying cause of FINDING_1's miscommunication). Affected file: `.pre-commit-config.yaml` (top-of-file comment block).
- **Reviewer**: Cursor-Pragmatic, Cursor-Requirements
- **Phase**: design

Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

