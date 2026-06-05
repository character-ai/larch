## Decision 1: Phased static Codex outputs (implement run logs)
- **Question**: The issue implies "static Codex = excluded", but a code comment (larch-log.sh:73-76) intentionally INCLUDES phased static Cursor/Codex fallback outputs for forensics, and the existing test asserts phased static Cursor is included (test:125). How should phased static Codex be treated?
- **Resolution**: Keep phased static fallback outputs INCLUDED (honor the existing intentional comment). Do NOT reverse this. The core deliverable is making dynamic-Codex INCLUSION explicit and adding the missing phased-dynamic-Codex test coverage — not changing static behavior.
- **Source**: user

## Decision 2: Change-surface scope
- **Question**: The issue names only scripts/larch-log.sh + scripts/test-larch-log-write-round.sh (implement run logs). The parallel design-log inclusion surface scripts/lib-design-round-artifacts.sh has its own different policy. In scope?
- **Resolution**: BOTH surfaces are in scope — implement logs (larch-log.sh + test) AND the design-log surface (lib-design-round-artifacts.sh + its tests).
- **Source**: user

## Decision 3: Meaning of "align" for the design-log surface
- **Question**: Design logs intentionally EXCLUDE all raw reviewer outputs (opposite of implement). Does "align" mean make the exclusion explicit/tested (keep excluding) or include dyn-Codex for forensic parity (behavior change)?
- **Resolution**: Make the exclusion EXPLICIT and tested, keeping the design-log EXCLUDE policy unchanged. Concretely: fix the dead `codex-plan-*-output.txt` pattern (actual outputs are `codex-primary-plan-*-output.txt`), add explicit dyn-Codex exclusion handling + a clarifying comment + fixtures. Do NOT start including raw dynamic reviewer outputs in design logs.
- **Source**: user

## Codebase findings (reported, not asked)
- **Implement logs**: `dyn-*-codex-output.txt` (phased + unphased) is currently INCLUDED only incidentally via the broad `*-output.txt` / `*-output-*.txt` allow rules (larch-log.sh:95) — the issue's "excluded" premise does not hold. Existing test already asserts unphased dyn-Codex inclusion (test:126-128) and unphased static Codex exclusion (test:124); phased dynamic Codex has NO test coverage.
- **Design logs**: the explicit exclusion pattern `codex-plan-*-output.txt` (lib-design-round-artifacts.sh:8) is DEAD — every Codex design output is named `codex-primary-plan-*-output.txt` (dispatch-plan-review-panel.sh:194 static, :226 dynamic), so static+dynamic Codex design outputs are excluded only via the catch-all `*)`.

## Non-goals
- Do NOT reverse the intentional phased-static-fallback inclusion in implement logs.
- Do NOT change the design-log EXCLUDE-all-raw-reviewer-outputs policy (no new inclusions in design logs).
- Do NOT touch unrelated allow/deny patterns beyond the Codex static/dynamic boundary.
