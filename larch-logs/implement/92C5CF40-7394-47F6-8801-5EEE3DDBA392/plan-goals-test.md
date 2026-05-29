## Goal
Implement issue #3160: [IMPLEMENTING] Sibling router flags keep asymmetric invalid-argv parsing\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

SIMPLE-tier fix: normalize invalid-argv handling for the two sibling boolean flags in `scripts/write-run-params.sh` so they match `--manual-gate-b` (`exit 2` + `larch_err`), via one shared helper. Add symmetric negative tests and sync the contract doc.

### UPDATED: `scripts/write-run-params.sh`

Add a `require_value` helper beside `take_value`, then route all three boolean-flag `case` arms through it. The helper takes the flag name and the value passed as the nounset-safe `"${2-}"`; a missing value arrives as empty, so a single `-z` check covers both missing and empty — identical observable behavior to `--manual-gate-b` today. Call it directly (never inside `$(...)`) so `exit 2` stops the script; `take_value` only works today because its callers guard inline before calling it.

```text
# Require a flag's value to be present and non-empty; exit 2 otherwise.
# Call directly (never inside $(...)) so the exit terminates the script.
require_value() {
    local flag="$1"
    if [[ -z "${2-}" ]]; then
        larch_err "write-run-params.sh: $flag requires a value"
        exit 2
    fi
}
```

Replace the two `${2:?...}` arms and fold in `--manual-gate-b` so all three share the helper:

```text
        --partition-requested)
            require_value --partition-requested "${2-}"
            PARTITION_REQUESTED="$2"
            shift 2
            ;;
        --brainstorm-requested)
            require_value --brainstorm-requested "${2-}"
            BRAINSTORM_REQUESTED="$2"
            shift 2
            ;;
        --manual-gate-b)
            require_value --manual-gate-b "${2-}"
            MANUAL_GATE_B="$2"
            shift 2
            ;;
```

### UPDATED: `scripts/test-write-run-params.sh`

After the existing `manual-gate-b-empty` / `manual-gate-b-missing` cases, add four symmetric `assert_rejected_with` cases. Place the bare flag last for the `-missing` cases, matching the manual-gate-b pattern:

```text
assert_rejected_with partition-requested-empty 'write-run-params.sh: --partition-requested requires a value' \
    --classification SIMPLE \
    --partition-requested "" \
    --output "$TMPROOT/partition-requested-empty.json"

assert_rejected_with partition-requested-missing 'write-run-params.sh: --partition-requested requires a value' \
    --classification SIMPLE \
    --output "$TMPROOT/partition-requested-missing.json" \
    --partition-requested

assert_rejected_with brainstorm-requested-empty 'write-run-params.sh: --brainstorm-requested requires a value' \
    --classification SIMPLE \
    --brainstorm-requested "" \
    --output "$TMPROOT/brainstorm-requested-empty.json"

assert_rejected_with brainstorm-requested-missing 'write-run-params.sh: --brainstorm-requested requires a value' \
    --classification SIMPLE \
    --output "$TMPROOT/brainstorm-requested-missing.json" \
    --brainstorm-requested
```

### UPDATED: `scripts/write-run-params.md`

- Invariants: extend the boolean-flags bullet so it states that `--partition-requested` / `--brainstorm-requested` / `--manual-gate-b` each require a present, non-empty `true`/`false` value and reject missing or empty argv with `exit 2`. Contrast the nullable text flags above, which accept `""` → null.
- Harness: note that the missing/empty-value rejection cases now cover all three boolean flags, not just `--manual-gate-b`.

### Caller audit

The rc/message change touches only the missing/empty-value path; valid `true`/`false` calls are unchanged. Existing `write-run-params.sh` call sites, and whether each relied on the old Bash-nounset `rc=1` / stderr text:

- `skills/design/SKILL.md` Step 0b — passes `--partition-requested "$partition_requested"` (and the two siblings) with real values; treats any nonzero exit as contract drift and never inspects the rc value or stderr text. Unaffected.
- `scripts/test-step0b-router-flag-recovery.sh` — invokes the writer only with valid `true`/`false`. Unaffected.
- `scripts/test-lint-skill-md-flag-signature.sh` and `scripts/test-design-structure.sh` — inspect SKILL.md invocation/signature text only; they never run the writer with a missing value. Unaffected.
- `scripts/test-write-run-params.sh` — the only caller that asserts rc/message for these flags; it gains the four new `rc=2` + stderr cases above.

Conclusion: no caller relied on the old `rc=1` / message, so normalizing to `exit 2` + `larch_err` is safe.

### Approach

- One shared `require_value` helper removes the three-way duplication and aligns the two sibling flags' exit code (1→2) and message with `--manual-gate-b`.
- Surgical scope: leave `--reason` / `--source` / `--sketch-budget` / `--review-budget` / `--workflow-path` untouched. They use `take_value` and intentionally accept `""` → null.
- Behavior parity with `--manual-gate-b`: missing and empty both yield `exit 2` plus the same `requires a value` message; valid `true`/`false` and the `maybe` → enum-rejection path are unchanged.

### Edge cases

- Flag as the last argv token: `$2` unset → `"${2-}"` → `""` → reject. The post-guard `FOO="$2"` never runs, so `set -u` stays safe.
- `--flag ""`: empty value → reject.
- `--flag maybe`: passes the helper, then `require_enum` rejects (`exit 2`) — unchanged.
- Value that looks like a flag (`--flag --other`): passes the helper, then `require_enum` rejects — identical to `--manual-gate-b` today.

### Failure modes

- A future edit calling `require_value` inside `$(...)` would swallow `exit 2`. Earliest signal: a missing-value run that does not stop. Mitigation: the inline comment plus the direct-call pattern; the `take_value` precedent makes the hazard visible.
- Behavior drift from `--manual-gate-b`. Earliest signal: a reviewer or caller seeing different rc/message. Mitigation: the four new tests assert identical rc (2) and message substrings, so divergence fails CI.
- Stale contract doc. Mitigation: `write-run-params.md` is updated in the same change per the `.md`-sibling rule.

### Testing strategy

- `bash scripts/test-write-run-params.sh` — must pass with the four new negative cases and all existing cases (valid writes, enum rejection, nullable fields, triple-flag persistence).
- `bash scripts/relevant-checks.sh` (or `make lint`) — Bash 3.2 lint, shellcheck, `.md`-sibling check.
- Manual probe: run `scripts/write-run-params.sh --classification SIMPLE --output <abs-path> --partition-requested` (bare flag last, so `$2` is unset) and confirm `rc=2` with stderr line `write-run-params.sh: --partition-requested requires a value`.

## Acceptance

- `scripts/write-run-params.sh` rejects a missing or empty value for `--partition-requested`, `--brainstorm-requested`, and `--manual-gate-b` with `exit 2` and stderr `write-run-params.sh: <flag> requires a value`, routed through a single shared `require_value` helper called directly (not in a command substitution).
- Valid `true`/`false` values still parse; `maybe` still fails via `require_enum` (`exit 2`); `--reason` / `--source` / `--sketch-budget` / `--review-budget` / `--workflow-path` still accept `""` → JSON null (unchanged).
- `scripts/test-write-run-params.sh` adds four negative cases (`partition-requested` and `brainstorm-requested`, each empty and missing) asserting `rc=2` and the matching stderr substring; the harness passes.
- `scripts/write-run-params.md` documents that all three boolean flags require a present, non-empty `true`/`false` value and reject missing/empty argv with `exit 2`.
- `bash scripts/test-write-run-params.sh` passes and `make lint` (Bash 3.2, shellcheck, `.md`-sibling checks) passes.

diff_lines: 40

## Test plan
(no test plan section in plan-file)
