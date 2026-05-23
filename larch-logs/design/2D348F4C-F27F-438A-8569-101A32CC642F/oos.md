### OOS_1: `scripts/ship-pr.md:82-84` doc drift — `git add -u` vs `collect_ci_stage_paths`
- **Description**: Invariant prose at `scripts/ship-pr.md:82-84` still says `run_ci_fix_vendor` runs `git add -u` before `git-commit.sh`, but the actual implementation at `scripts/ship-pr.sh:1263-1277` uses `collect_ci_stage_paths` + `git add -- "${stage_paths[@]}"`. Reviewers tagged it OOS but recommended fixing it during the same edit as the plan touches the nearby retry-math prose. Raised by 6 reviewers (multiple tagged OOS, multiple tagged in-scope nit).
- **Reviewer**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-Requirements
- **Phase**: design


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: Innovation alternative — keep `_max_fix=5` and add Claude as a 4th tier
- **Description**: Plan trades total recovery budget down from 15 (5 outer × 3 inner today) to 9 (3 outer × 3 inner) by reducing `_max_fix`. A counter-proposal: keep `_max_fix=5` and add Claude as a fourth tier (1 attempt each: Cursor → Codex → Claude → Claude-with-higher-budget, or just Cursor → Codex → Claude × 5 outer = 15 calls with Claude diversity). Operators who rely on retry repetition for transient flakes may prefer this. Worth tracking as a "rejected alternative" for follow-up if production stall-rate rises after #2632 lands. Raised by 1 reviewer: Cursor-Innovation.
- **Reviewer**: Cursor-Innovation
- **Phase**: design


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: `larch-logs/design/CC79D945-CB91-4C84-BF50-45D8466D452D/` artifacts may resurface superseded constraint C
- **Description**: Older /design design-log artifacts under that path still discuss leaving `run_ci_fix_vendor` structurally unchanged (constraint C). After #2632 lands, downstream issue filing may pattern-match against those artifacts and resurrect scope conflicts. Track so future /design runs against ship-pr know constraint C was intentionally reversed. Raised by 1 reviewer: Cursor-Pragmatic.
- **Reviewer**: Cursor-Pragmatic
- **Phase**: design


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: `skills/shared/topology.tsv` may need regeneration if `scripts/ship-pr.md` row-counts shift materially
- **Description**: Per repo norms, if `scripts/ship-pr.md` line-count or anchor count shifts beyond a sentence tweak, topology projection may need regeneration. Verify during `/implement` for #2632 if the doc diff is more than a sentence tweak. Raised by 1 reviewer: Cursor-Pragmatic.
- **Reviewer**: Cursor-Pragmatic
- **Phase**: design


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_5: `README.md` operator-facing retry math
- **Description**: If `README.md` mirrors `ship-pr.md`'s "5 retries" language anywhere, align in a follow-up. /implement should check this. Raised by 1 reviewer: Codex-Requirements.
- **Reviewer**: Codex-Requirements
- **Phase**: design


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_6: SECURITY.md may need explicit note about `--failure-log` forwarding to Claude tier
- **Description**: Separate from FINDING_11 (which proposes redaction of `--failure-log` content), the SECURITY.md document may need to explicitly enumerate `launch-claude-ci.sh` as a recipient of `--failure-log` so the trust-boundary documentation is complete. Decision belongs to a maintainer pass after implementation. Raised by 1 reviewer: Codex-Requirements.
- **Reviewer**: Codex-Requirements
- **Phase**: design

---

INSTRUCTIONS: For each finding (FINDING_1 through FINDING_22) and each OOS observation (OOS_1 through OOS_6), vote `YES`, `NO`, or `EXONERATE`. Write your decision per finding using this format:

```
FINDING_1: <YES|NO|EXONERATE>
FINDING_2: <YES|NO|EXONERATE>
...
OOS_1: <YES|NO|EXONERATE>
...
```

Voting standard:
- `YES` = this finding is correct, important, and worth revising the plan for (or for OOS: worth filing as a GitHub issue).
- `NO` = the finding is wrong, not applicable, or the cost of acting on it would exceed the value (proportionality).
- `EXONERATE` = the concern is legitimate but the proposed change would introduce more complexity than the issue warrants, or is out of scope for this PR.

Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

