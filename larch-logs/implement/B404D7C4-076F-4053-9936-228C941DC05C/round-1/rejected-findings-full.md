### [rejected] FINDING_1

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_1: **`implement-bootstrap-invoke.sh` self-derive** (`32:36:scripts/implement-bootstrap-invoke.sh`) — Derives `CLAUDE_PLUGIN_ROOT` from `dirname "$0"/..`, exports it, then executes `${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh`. Paths are quoted; there is no `eval`/unquoted expansion. This mirrors the existing self-derive in `implement-bootstrap.sh` (`22:25:scripts/implement-bootstrap.sh`). Normal `/implement` entry uses loader-expanded absolute paths, so the trust boundary is “which plugin tree you execute,” not a new injection primitive.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **`implement-bootstrap-invoke.sh` self-derive** (`32:36:scripts/implement-bootstrap-invoke.sh`) — Derives `CLAUDE_PLUGIN_ROOT` from `dirname "$0"/..`, exports it, then executes `${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh`. Paths are quoted; there is no `eval`/unquoted expansion. This mirrors the existing self-derive in `implement-bootstrap.sh` (`22:25:scripts/implement-bootstrap.sh`). Normal `/implement` entry uses loader-expanded absolute paths, so the trust boundary is “which plugin tree you execute,” not a new injection primitive.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: skills/implement/scripts/test-implement-bootstrap-invoke.sh:746-763
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New self-derive test only covers successful absolute-path invocation with unset env; fail-loud derivation failure is untested. A broken or relocated wrapper layout could regress to silent wrong behavior or an unexpected error shape without CI catching the documented :? abort path. Add a negative sandbox case where derivation yields empty and assert exit 1 with CLAUDE_PLUGIN_ROOT must be set on stderr.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_2: **`lib-implement-round-cap.sh` CLI** (`41:60:scripts/lib-implement-round-cap.sh`) — Direct-exec path only reads `round-N/review-and-fix.env` under the supplied tmpdir via quoted paths and awk; `current_round` is restricted to positive integers. No command execution or writes. The tmpdir trust model is unchanged from the already-sourced `count_prior_degraded_rounds` function.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`lib-implement-round-cap.sh` CLI** (`41:60:scripts/lib-implement-round-cap.sh`) — Direct-exec path only reads `round-N/review-and-fix.env` under the supplied tmpdir via quoted paths and awk; `current_round` is restricted to positive integers. No command execution or writes. The tmpdir trust model is unchanged from the already-sourced `count_prior_degraded_rounds` function.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: **architecture** `skills/implement/SKILL.md:784-795` — Banner math and launcher argv are split across prose and an adjacent fence with no single mechanical contract: prose hardcodes CLI round `1` and prompt-side `effective_round_cap=$((round_cap + prior_degraded_rounds))`, while the fence independently passes `--starting-round 1` to `run-step5-review.sh`. Runtime cap inflation in `skills/review-and-fix/scripts/review-implement-step5-loop.sh:162` uses `count_prior_degraded_rounds(IMPLEMENT_TMPDIR, STARTING_ROUND)`; any future edit that changes `--starting-round` without updating the prose literal will make operator-facing `effective_round_cap` diverge from the loop’s `entry_effective_cap` without CI failing. **Suggested fix:** Bind both sites to one shell variable in the existing fence (e.g. `STARTING_ROUND=1`, pass it to the CLI and `--starting-round`), or move banner emission into `run-step5-review.sh` / a `--print-banner-values` probe so cap math and `STARTING_ROUND` share one implementation.
- **Reviewer**: dyn-skill-prose-output.txt
- **Concern**: - **architecture** `skills/implement/SKILL.md:784-795` — Banner math and launcher argv are split across prose and an adjacent fence with no single mechanical contract: prose hardcodes CLI round `1` and prompt-side `effective_round_cap=$((round_cap + prior_degraded_rounds))`, while the fence independently passes `--starting-round 1` to `run-step5-review.sh`. Runtime cap inflation in `skills/review-and-fix/scripts/review-implement-step5-loop.sh:162` uses `count_prior_degraded_rounds(IMPLEMENT_TMPDIR, STARTING_ROUND)`; any future edit that changes `--starting-round` without updating the prose literal will make operator-facing `effective_round_cap` diverge from the loop’s `entry_effective_cap` without CI failing. **Suggested fix:** Bind both sites to one shell variable in the existing fence (e.g. `STARTING_ROUND=1`, pass it to the CLI and `--starting-round`), or move banner emission into `run-step5-review.sh` / a `--print-banner-values` probe so cap math and `STARTING_ROUND` share one implementation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_3: **`append-execution-issue.sh`** — Adds a static `USAGE=` line in `fail_usage`; no new user-controlled sinks.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **`append-execution-issue.sh`** — Adds a static `USAGE=` line in `fail_usage`; no new user-controlled sinks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_4: **`skills/implement/SKILL.md` Step 5** — Swaps prompt-side glob logic for a documented CLI call using `$IMPLEMENT_TMPDIR` and rehydrated `CLAUDE_PLUGIN_ROOT`; no new untrusted input path.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **`skills/implement/SKILL.md` Step 5** — Swaps prompt-side glob logic for a documented CLI call using `$IMPLEMENT_TMPDIR` and rehydrated `CLAUDE_PLUGIN_ROOT`; no new untrusted input path. No injection, authz bypass, secret leakage, path-traversal amplification, or unsafe deserialization introduced by this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

