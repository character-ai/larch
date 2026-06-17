### OOS_1: [OUT_OF_SCOPE] docs/external-reviewers.md:23-24 — stale line-number references
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Stale line-number references to `skills/review/SKILL.md` point past EOF. Readers following the documented canonical examples cannot find the referenced lines because `skills/review/SKILL.md` has only 106 lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Remove brittle line ranges or replace them with current section-level references.


### OOS_2: [OUT_OF_SCOPE] docs/external-reviewers.md:10 — runtime-probe-failed vs probe-failed terminology
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The prose says runtime-probe-failed, but the emitted gate state is probe-failed. Readers may look for a runtime-probe-failed state that the CLI never emits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Use probe-failed, or phrase it as plain prose: runtime probe failed.


### OOS_3: [OUT_OF_SCOPE] design-step0-session.md:17-18 — stale degraded-tools gate invariants
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/design-step0-session.md` lines 17–18 describe interactive both-down prompting and sentinel writes on both-down/non-interactive paths. Current behavior hard-fails both-down everywhere and writes `.degraded-tools-gate-prompted` only after explicit Continue on one-down. Maintainer docs contradict `design-step0-session.sh`, `skills/design/SKILL.md`, and `skills/shared/external-reviewers.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update bullets to match design-step0-session.sh and skills/shared/external-reviewers.md.
  - From codex-specialist-correctness-output.txt: align these bullets with `skills/shared/external-reviewers.md`.
  - From codex-specialist-edge-cases-output.txt: Align the invariants with skills/design/SKILL.md and skills/shared/external-reviewers.md.


### OOS_4: [OUT_OF_SCOPE] docs/external-reviewers.md:5 — stale session-setup.sh reference
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-existing stale cross-reference. `session-setup.sh --check-reviewers` no longer exists in the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: replace it with `python3 python/cli.py session setup --check-reviewers`.


### OOS_5: [OUT_OF_SCOPE] step-0-degraded-gate.md:3 — stale helper summary
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-existing stale helper summary. The script reads binary flags from session env and refreshes presence via `agent check-reviewers`; it does not read presence keys from session env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: update the summary to describe fresh presence probing.


### OOS_6: [OUT_OF_SCOPE] docs/skills.md:179 / skills/status/SKILL.md:29 — degraded note framed as /implement-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Degraded note is framed as `/implement`-only behavior; the same Step 0 gate contract also applies to `/design`, `/review`, and `/research`. The branch mirrors the status SKILL wording rather than introducing a new mismatch, but the catalog entry is system-wide incomplete.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_7: [OUT_OF_SCOPE] docs/external-reviewers.md:10 — omits PRESENCE_INPUT_EMPTY fail-safe
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Summary paragraph omits the `PRESENCE_INPUT_EMPTY` fail-safe path documented in `skills/shared/external-reviewers.md:33`. Pre-existing omission pattern; not introduced by this change.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_8: [OUT_OF_SCOPE] skills/shared/external-reviewers.md — missing explicit interactive predicate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Referenced as hosting a "canonical interactive predicate" by consumer skills (e.g. `skills/review/SKILL.md:33`), but the shared file only lists non-interactive contexts inline and does not define that predicate explicitly. Pre-existing doc gap adjacent to the updated surface.
- **Suggested revisions (informational for voters; coder decides)**:


