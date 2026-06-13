### OOS_1: [OUT_OF_SCOPE] Pre-existing label divergence for `dyn-*` basenames
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-review-phase-detail.sh` `derive.awk` maps `dyn-…` to `dynamic/…`, while `progress_report._derive_progress_label()` has no `dyn-` branch and falls back to `unknown/…`. Progress and final reports can disagree on those labels. The plan explicitly defers label parity; bars still render.
- **Suggested revisions (informational for voters; coder decides)**:


