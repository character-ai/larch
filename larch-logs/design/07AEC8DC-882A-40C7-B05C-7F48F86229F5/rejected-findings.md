### [Plan Review] FINDING_8

### FINDING_8: Rewrite `[[ -n "$v" ]] && X="$v"` as `if [[ -n "$v" ]]; then X="$v"; fi` to guarantee zero exit per iteration

- **Concern**: Cursor-Arch argues that after fixing `step5_parse_kv_tokens`, the final per-iteration `[[ -n "$v" ]] && X="$v"` line can return non-zero (when `$v` is empty), bash adopts that as the while compound's exit status, and `set -e` may exit before the post-loop stderr runs.
- **Proposed resolution**: Rewrite each per-iteration assignment as `if [[ -n "$v" ]]; then X="$v"; fi`, or append `; true` per iteration, so the while body always exits zero.
- **Reviewers**: Cursor-Arch (1 reviewer).
- **Empirical evidence (post-finding)**: Verified at design time with a minimal repro: bash 3.2 + `set -e` + helper returning 0 + the existing `[[ -n "$v" ]] && X="$v"` pattern reaches the post-loop code without exiting. The `&&` list is exempt from `set -e` per the bash manual ("any command in an AND or OR list other than the command following the final && or ||"), and the while compound's non-zero status from an exempt failure does not trigger `set -e` exit. The pattern is widely used in larch under `set -e` and works.

---


